"""Scoped transactional delivery for current planning and fundraising workflows.

Synthetic admin journeys capture mail. Real deliveries use the existing Resend
account and stable event keys; a failed delivery can be retried without approving
or generating a second document.
"""
import hashlib
import html
import os
from datetime import datetime, timezone, timedelta
import resend


def now():
    return datetime.now(timezone.utc).isoformat()


async def deliver_once(db, user_id, event_key, recipient, subject, text, link, *, unsubscribe_url=None, secondary_links=None, cta_label="OPEN YOUR RESOURCE"):
    recipient = str(recipient or "").strip().lower()
    key = hashlib.sha256(f"{user_id}:{event_key}:{recipient}".encode()).hexdigest()
    events = db.workflow_email_deliveries
    owner = await db.members.find_one({"user_id": user_id}, {"_id": 0}) or {}
    from admin_test_safety import _scope
    captured = bool(_scope.get() or owner.get("internal_dashboard_preview") or user_id.startswith("admin-dashboard-preview-") or recipient.endswith(".internal"))
    await events.update_one({"_id": key}, {"$setOnInsert": {"user_id": user_id, "event_key": event_key, "recipient": recipient, "subject": subject,
        "text": text, "link": link, "cta_label":cta_label, "secondary_links":secondary_links or [], "status": "pending", "created_at": now()}}, upsert=True)
    # Recover a worker interrupted after claiming delivery. The provider receives
    # the same idempotency key on every attempt.
    await events.update_one({"_id":key,"status":"sending","updated_at":{"$lt":(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()}}, {"$set":{"status":"failed"}})
    doc = await events.find_one({"_id": key})
    subject,text,link=doc['subject'],doc['text'],doc['link']
    cta_label=doc.get('cta_label', 'OPEN YOUR RESOURCE')
    secondary_links=doc.get('secondary_links') or []
    if doc.get("status") in {"sent", "captured", "sending"}:
        return {"recipient": recipient, "status": doc["status"], "provider_id": doc.get("provider_id", "")}
    claimed = await events.update_one({"_id": key, "status": {"$in": ["pending", "failed"]}}, {"$set": {"status": "sending", "updated_at": now()}})
    if not claimed.modified_count: return {"recipient": recipient, "status": "sending"}
    try:
        if captured:
            status, provider_id = "captured", ""
        else:
            if "@" not in recipient: raise ValueError("A valid recipient is required")
            resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
            footer = ("<p><a href='" + html.escape(unsubscribe_url, quote=True) + "'>Unsubscribe from these follow-up emails</a></p>") if unsubscribe_url else ""
            headers = {"List-Unsubscribe": "<" + unsubscribe_url + ">", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"} if unsubscribe_url else {}
            extra=''.join("<p><a href='"+html.escape(item['url'],quote=True)+"'>"+html.escape(item['label'])+"</a></p>" for item in secondary_links if str(item.get('url','')).startswith('https://'))
            response = await resend.Emails.send_async({"headers": headers,"from": os.environ["NONPROFIT_SENDER"], "to": [recipient], "subject": subject,
                "html": "<div style='max-width:640px;margin:auto;font-family:Arial;line-height:1.6;text-align:center'><p>" + html.escape(text).replace("\n", "<br>") + "</p><p><a href='" + html.escape(link, quote=True) + "'>"+html.escape(cta_label)+"</a></p>"+extra+"<p>Add our sending address to your contacts and mark important emails as favorites so you can find these links again.</p>" + footer + "</div>"},
                {"idempotency_key": key})
            provider_id = response.get("id", "") if isinstance(response, dict) else getattr(response, "id", "")
            if not provider_id: raise ValueError("The email provider did not confirm acceptance")
            status = "sent"
        await events.update_one({"_id": key}, {"$set": {"status": status, "provider_id": provider_id, "updated_at": now(), "error": ""}})
        return {"recipient": recipient, "status": status, "provider_id": provider_id}
    except Exception as exc:
        await events.update_one({"_id": key}, {"$set": {"status": "failed", "error": str(exc)[:400], "updated_at": now()}})
        return {"recipient": recipient, "status": "failed"}
