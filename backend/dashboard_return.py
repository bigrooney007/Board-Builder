"""Private, revocable dashboard links issued only to a paid account owner."""

import hashlib
import html
import os
import secrets
from datetime import datetime, timezone

import resend


PRODUCTS = {
    "recruitment": ("recruitment_self_guided", "/app/board-recruitment", "Board Recruitment"),
    "game": ("board_fundraising_game", "/game/dashboard", "Board Fundraising Game"),
    "strategic-planning": ("strategic_planning_497", "/strategic-planning/dashboard", "Strategic Planning"),
    "board-recommitment": ("reactivation_self_guided", "/board-recommitment/dashboard", "Board Recommitment"),
}


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def send_dashboard_return(db, member: dict, product: str, origin: str, session_id: str = "") -> bool:
    """Issue a bookmarkable link after a meaningful milestone. Never email previews."""
    if member.get("internal_client_test") or member.get("internal_dashboard_preview") or member.get("review_mode"):
        return False
    entitlement, _, label = PRODUCTS[product]
    if entitlement not in member.get("entitlements", []):
        return False
    if product in {"strategic-planning", "board-recommitment"}:
        tx = await db.payment_transactions.find_one({"session_id": session_id,
            "claimed_by_user_id": member["user_id"], "payment_status": "paid"}, {"_id": 0})
        if not tx or tx.get("purchase_source") != ("strategic_planning_497" if product == "strategic-planning" else "board_recommitment_497"):
            return False
    if await db.dashboard_return_tokens.find_one({"user_id": member["user_id"], "product": product,
                                                  "session_id": session_id, "revoked": False}, {"_id": 1}):
        return True
    token = secrets.token_urlsafe(40)
    digest = token_digest(token)
    link = f"{origin.rstrip('/')}/return/{token}"
    record = {
        "digest": digest, "user_id": member["user_id"], "product": product,
        "session_id": session_id, "created_at": datetime.now(timezone.utc).isoformat(),
        "revoked": False,
    }
    await db.dashboard_return_tokens.insert_one(record)
    try:
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        await resend.Emails.send_async({
            "from": os.environ["NONPROFIT_SENDER"], "to": [member["email"]],
            "subject": f"Your private {label} dashboard link",
            "html": ("<div style='max-width:600px;margin:auto;font-family:Arial,sans-serif;line-height:1.6'>"
                     f"<h2>Return to {html.escape(label)}</h2><p>Save or bookmark this private link. "
                     "It opens your dashboard directly whenever you want to return. "
                     "Anyone with this link can access your workspace, so keep it private.</p>"
                     f"<p><a href='{html.escape(link, quote=True)}'>OPEN MY DASHBOARD</a></p>"
                     "<p>Keep this email so you can return whenever you need it.</p></div>"),
        })
    except Exception:
        await db.dashboard_return_tokens.delete_one({"digest": digest})
        raise
    return True
