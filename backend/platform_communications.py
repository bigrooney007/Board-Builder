"""Immediate communication for clean-house homepage leads.

This module deliberately does not own the slower nurture cadence. It sends the first
transactional return email immediately after a valid homepage lead is captured and
alerts the site owner at the same moment. Existing nurture/drip systems continue to
operate independently.
"""
import html
import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import resend

logger = logging.getLogger(__name__)

PATHWAYS = {
    "recruitment": {
        "name": "Board Recruitment",
        "owner_subject": "New Board Recruitment Website Lead",
        "prospect_subject": "Continue Your Board Recruitment Process",
    },
    "board-fundraising-game": {
        "name": "Board Fundraising Game",
        "owner_subject": "New Board Fundraising Game Website Lead",
        "prospect_subject": "Continue Your Board Fundraising Game",
    },
    "strategic-planning": {
        "name": "Strategic Planning",
        "owner_subject": "New Strategic Planning Website Lead",
        "prospect_subject": "Continue Your Strategic Planning Process",
    },
    "board-recommitment": {
        "name": "Board Recommitment",
        "owner_subject": "New Board Recommitment Website Lead",
        "prospect_subject": "Continue Your Board Recommitment Process",
    },
}


def public_origin(value: str = "") -> str:
    candidate = (value or os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com").strip().rstrip("/")
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "https://nonprofitboardbuilder.com"
    return candidate


def _button(url: str, label: str) -> str:
    return (
        f"<p style='margin:24px 0'><a href='{html.escape(url, quote=True)}' "
        "style='display:inline-block;background:#312e81;color:#ffffff;padding:13px 20px;"
        "border-radius:8px;text-decoration:none;font-weight:800'>"
        f"{html.escape(label)}</a></p>"
    )


def _shell(body: str) -> str:
    return (
        "<div style='max-width:640px;margin:auto;font-family:Arial,Helvetica,sans-serif;"
        "color:#111827;line-height:1.65'>"
        + body
        + "<p style='margin-top:28px'>Rooney Akpesiri<br/>Nonprofit Board Builder</p></div>"
    )


async def _event(db, event_key: str, pathway: str, source_id: str, lead: dict) -> dict:
    existing = await db.platform_email_events.find_one({"event_key": event_key}, {"_id": 0})
    if existing:
        return existing
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "event_key": event_key,
        "event_type": "homepage_lead",
        "pathway": pathway,
        "source_id": source_id,
        "email": str(lead.get("email") or "").lower(),
        "owner_status": "Pending",
        "prospect_status": "Pending",
        "created_at": now,
        "updated_at": now,
    }
    try:
        await db.platform_email_events.insert_one(doc.copy())
        return doc
    except Exception:
        return await db.platform_email_events.find_one({"event_key": event_key}, {"_id": 0}) or doc


async def notify_homepage_lead(
    db,
    *,
    pathway: str,
    source_id: str,
    name: str,
    email: str,
    organization: str,
    continue_url: str,
    details: dict | None = None,
) -> dict:
    """Send one owner alert and one immediate prospect return email per captured lead record.

    Email failures never block the website journey. Failed halves can be retried by
    calling the function again with the same source_id.
    """
    meta = PATHWAYS.get(pathway)
    if not meta:
        return {"owner_status": "Skipped", "prospect_status": "Skipped"}
    normalized_email = str(email or "").strip().lower()
    if "@" not in normalized_email:
        return {"owner_status": "Skipped", "prospect_status": "Skipped"}

    lead = {
        "name": str(name or "").strip(),
        "email": normalized_email,
        "organization": str(organization or "").strip(),
    }
    detail_rows = {str(k): str(v) for k, v in (details or {}).items() if str(v or "").strip()}
    event_key = f"homepage_lead:{pathway}:{source_id}"
    event = await _event(db, event_key, pathway, source_id, lead)
    now = datetime.now(timezone.utc).isoformat()
    resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
    sender = os.environ.get("NONPROFIT_SENDER") or os.environ.get("SENDER_EMAIL")
    owner = os.environ.get("OWNER_NOTIFICATION_EMAIL") or os.environ.get("OWNER_EMAIL")

    owner_status = event.get("owner_status", "Pending")
    if owner_status != "Sent" and sender and owner:
        rows = [
            ("Pathway", meta["name"]),
            ("Name", lead["name"] or "Not provided"),
            ("Email", lead["email"]),
            ("Organization", lead["organization"] or "Not provided"),
        ] + [(key.replace("_", " ").title(), value) for key, value in detail_rows.items()]
        table = "".join(
            "<tr>"
            f"<td style='padding:9px;border-bottom:1px solid #e5e7eb;font-weight:700;vertical-align:top'>{html.escape(label)}</td>"
            f"<td style='padding:9px;border-bottom:1px solid #e5e7eb'>{html.escape(value)}</td>"
            "</tr>"
            for label, value in rows
        )
        try:
            response = await resend.Emails.send_async({
                "from": sender,
                "to": [owner],
                "subject": f"{meta['owner_subject']} — {lead['organization'] or lead['name'] or lead['email']}",
                "html": _shell(
                    f"<h1 style='font-size:26px'>{html.escape(meta['owner_subject'])}</h1>"
                    "<p>Someone has entered their details on the website.</p>"
                    f"<table style='width:100%;border-collapse:collapse'>{table}</table>"
                    + _button(public_origin() + "/admin", "OPEN ADMIN")
                ),
            })
            owner_status = "Sent"
            await db.platform_email_events.update_one(
                {"event_key": event_key},
                {"$set": {
                    "owner_status": "Sent",
                    "owner_email_id": str(response.get("id") if isinstance(response, dict) else getattr(response, "id", "")),
                    "owner_sent_at": now,
                    "updated_at": now,
                }},
            )
        except Exception as exc:
            owner_status = "Failed"
            logger.exception("Homepage owner notification failed for %s", event_key)
            await db.platform_email_events.update_one(
                {"event_key": event_key},
                {"$set": {"owner_status": "Failed", "owner_error": str(exc)[:400], "updated_at": now}},
            )

    prospect_status = event.get("prospect_status", "Pending")
    if prospect_status != "Sent" and sender and continue_url:
        first_name = (lead["name"].split(" ")[0] if lead["name"] else "there")
        try:
            response = await resend.Emails.send_async({
                "from": sender,
                "to": [lead["email"]],
                "subject": meta["prospect_subject"],
                "html": _shell(
                    f"<h2>Continue your {html.escape(meta['name'])} process</h2>"
                    f"<p>Hi {html.escape(first_name)},</p>"
                    f"<p>You started the {html.escape(meta['name'])} process for "
                    f"<strong>{html.escape(lead['organization'] or 'your organization')}</strong>.</p>"
                    "<p>This email gives you a direct way back to the exact next step. "
                    "If you were interrupted, you do not need to start the process from scratch.</p>"
                    + _button(continue_url, "CONTINUE WHERE I STOPPED")
                    + "<p>You may also receive the normal follow-up sequence later if you do not complete the process. "
                      "This message is simply the immediate return link you can use now.</p>"
                ),
            })
            prospect_status = "Sent"
            await db.platform_email_events.update_one(
                {"event_key": event_key},
                {"$set": {
                    "prospect_status": "Sent",
                    "prospect_email_id": str(response.get("id") if isinstance(response, dict) else getattr(response, "id", "")),
                    "prospect_sent_at": now,
                    "continue_url": continue_url,
                    "updated_at": now,
                }},
            )
        except Exception as exc:
            prospect_status = "Failed"
            logger.exception("Homepage prospect return email failed for %s", event_key)
            await db.platform_email_events.update_one(
                {"event_key": event_key},
                {"$set": {
                    "prospect_status": "Failed",
                    "prospect_error": str(exc)[:400],
                    "continue_url": continue_url,
                    "updated_at": now,
                }},
            )

    return {"owner_status": owner_status, "prospect_status": prospect_status, "event_key": event_key}
