import asyncio
import html
import logging
import os
from datetime import datetime, timedelta, timezone

import resend
import stripe

from content_templates import checkout_recovery_email

logger = logging.getLogger("checkout_recovery")

RECOVERY_DELAY_MINUTES = 60
CHECK_INTERVAL_SECONDS = 300

OFFER_PAGES = {
    "direct_diy_board_recruitment": ("Recruit New Board Members", "/offer/recruitment"),
    "direct_board_recruitment_project": ("Recruit New Board Members", "/offer/recruitment"),
    "direct_diy_board_reactivation": ("Reactivate Your Board", "/offer/reactivation"),
    "direct_board_reactivation_project": ("Reactivate Your Board", "/offer/reactivation"),
    "direct_diy_board_activation": ("Build a Fundraising Board", "/offer/activation"),
    "direct_board_activation_project": ("Build a Fundraising Board", "/offer/activation"),
}


def recovery_enabled() -> bool:
    return os.environ.get("CHECKOUT_RECOVERY_ENABLED", "false").strip().lower() == "true"


async def lead_checkout_context(db, result_token: str) -> dict:
    context = {"lead_id": "", "lead_email": "", "lead_name": "", "lead_organization": ""}
    if not result_token:
        return context
    lead = await db.funnel_leads.find_one({"result_token": result_token}, {"_id": 0})
    if lead:
        context.update({
            "lead_id": lead.get("lead_id", ""), "lead_email": lead.get("email", ""),
            "lead_name": lead.get("name", ""), "lead_organization": lead.get("organization", ""),
        })
    return context


def build_recovery_html(body: str, offer_link: str) -> str:
    paragraphs = []
    for block in body.split("\n\n"):
        if block.strip() == offer_link:
            safe = html.escape(offer_link)
            paragraphs.append(f'<p style="margin:0 0 16px;"><a href="{safe}" style="color:#087e5b;font-weight:700;">{safe}</a></p>')
        else:
            paragraphs.append(f'<p style="margin:0 0 16px;">{html.escape(block).replace(chr(10), "<br>")}</p>')
    return (
        '<div style="font-family:Arial,sans-serif;color:#17241c;line-height:1.6;max-width:620px;margin:auto;">'
        + "".join(paragraphs) + "</div>"
    )


async def process_abandoned_checkouts(db) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=RECOVERY_DELAY_MINUTES)).isoformat()
    cursor = db.payment_transactions.find({
        "payment_status": "pending",
        "lead_email": {"$nin": ["", None]},
        "recovery_email_status": {"$exists": False},
        "created_at": {"$lt": cutoff},
        "offer_source": {"$in": list(OFFER_PAGES)},
    }, {"_id": 0})
    sent = 0
    async for txn in cursor:
        session_id = txn["session_id"]
        try:
            stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
            session = await asyncio.to_thread(stripe.checkout.Session.retrieve, session_id)
            if session.payment_status == "paid" or session.status == "complete":
                await db.payment_transactions.update_one(
                    {"session_id": session_id},
                    {"$set": {"payment_status": "paid", "status": "completed", "updated_at": datetime.now(timezone.utc).isoformat()}})
                continue
        except Exception:
            logger.warning("Could not re-check Stripe session %s before recovery email", session_id)
        email = txn["lead_email"]
        has_paid = await db.payment_transactions.find_one({"lead_email": email, "payment_status": "paid"})
        already_sent = await db.payment_transactions.find_one({"lead_email": email, "recovery_email_status": "sent"})
        if has_paid or already_sent:
            await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"recovery_email_status": "skipped"}})
            continue
        offer_name, offer_path = OFFER_PAGES[txn["offer_source"]]
        offer_link = f"{(txn.get('origin_url') or '').rstrip('/')}{offer_path}"
        first_name = (txn.get("lead_name") or "").strip().split(" ")[0]
        message = checkout_recovery_email(first_name, txn.get("lead_organization", ""), offer_name, offer_link)
        try:
            resend.api_key = os.environ["RESEND_API_KEY"]
            response = await asyncio.to_thread(resend.Emails.send, {
                "from": os.environ["SENDER_EMAIL"], "to": [email],
                "subject": message["subject"],
                "html": build_recovery_html(message["body"], offer_link),
            })
            await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {
                "recovery_email_status": "sent",
                "recovery_email_id": (response or {}).get("id", ""),
                "recovery_email_at": datetime.now(timezone.utc).isoformat(),
            }})
            sent += 1
        except Exception as exc:
            await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {
                "recovery_email_status": "failed", "recovery_email_error": str(exc)[:300],
            }})
            logger.exception("Recovery email failed for session %s", session_id)
    return sent


async def checkout_recovery_loop(db) -> None:
    while True:
        try:
            if recovery_enabled():
                await process_abandoned_checkouts(db)
        except Exception:
            logger.exception("Checkout recovery cycle failed")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
