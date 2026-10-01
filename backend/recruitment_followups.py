"""Stage-aware recruitment recovery and the 24-hour campaign amplification offer."""
import html
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from opportunity_emails import _send, _wrap
from recruit_free_routes import QUESTION_KEYS

logger = logging.getLogger(__name__)
ORIGIN = "https://nonprofitboardbuilder.com"


def origin() -> str:
    return (os.environ.get("PUBLIC_ORIGIN") or ORIGIN).rstrip("/")


async def send_recruitment_recovery(db, now: datetime) -> int:
    cutoff = (now - timedelta(hours=1)).isoformat()
    keys = [f"answers.{key}" for key in QUESTION_KEYS.values()]
    assessments = await db.recruitment_free_assessments.find(
        {"state.paid": {"$ne": True}, "updated_at": {"$lte": cutoff}, "$or": [
            {"recovery.partial_status": {"$exists": False},
             "$or": [{key: {"$in": [None, ""]}} for key in keys]},
            {"recovery.complete_status": {"$exists": False},
             "$and": [{key: {"$nin": [None, ""]}} for key in keys]},
        ]},
        {"_id": 0},
    ).sort("updated_at", -1).to_list(200)
    sent = 0
    for doc in assessments:
        if not doc.get("email") or not doc.get("token"):
            continue
        paid = await db.payment_transactions.find_one(
            {"lead_id": doc.get("lead_id"), "payment_status": "paid"}, {"_id": 0, "session_id": 1})
        if paid:
            continue
        answers = doc.get("answers") or {}
        complete = all(str(answers.get(key) or "").strip() for key in QUESTION_KEYS.values())
        stage = "complete" if complete else "partial"
        claim = await db.recruitment_free_assessments.update_one(
            {"token": doc["token"], f"recovery.{stage}_status": {"$exists": False}},
            {"$set": {f"recovery.{stage}_status": "Sending", f"recovery.{stage}_attempt_at": now.isoformat()}},
        )
        if not claim.modified_count:
            continue
        first = html.escape((doc.get("name") or "there").split(" ")[0])
        organization = html.escape(doc.get("organization") or "your organization")
        link = f"{origin()}/recruit/{'walkthrough' if complete else 'questions'}?token={doc['token']}"
        if complete:
            subject = f"Your Board Recruitment assessment for {doc.get('organization') or 'your organization'} is ready"
            message = (f"<p>Hi {first},</p><p>Your six answers for {organization} are saved. We have the context to identify the board profiles your organization needs.</p>"
                       "<p>Unlocking your campaign gives you the recommended profiles, materials built for your organization and a guided path to launch recruitment in the next 30 minutes.</p>")
            button = "UNLOCK MY CAMPAIGN"
        else:
            subject = "Continue your saved Board Recruitment assessment"
            message = (f"<p>Hi {first},</p><p>Your recruitment assessment for {organization} is saved. "
                       "Continue from the next question whenever you are ready.</p>")
            button = "CONTINUE MY ANSWERS"
        body = message + f"<p><a href='{html.escape(link, quote=True)}' style='display:inline-block;background:#087e5b;color:white;padding:12px 18px;text-decoration:none'>{button}</a></p>"
        try:
            email_id = await _send("NONPROFIT_SENDER", doc["email"], subject, _wrap("Your Recruitment Campaign", body))
            await db.recruitment_free_assessments.update_one({"token": doc["token"]},
                {"$set": {f"recovery.{stage}_status": "Sent", f"recovery.{stage}_sent_at": now.isoformat(),
                          f"recovery.{stage}_email_id": email_id}})
            sent += 1
        except Exception as exc:
            logger.exception("Recruitment assessment recovery email failed")
            await db.recruitment_free_assessments.update_one({"token": doc["token"]},
                {"$set": {f"recovery.{stage}_status": "Failed", f"recovery.{stage}_error": str(exc)[:300]}})
    return sent


async def send_amplify_followups(db, now: datetime) -> int:
    cutoff = (now - timedelta(hours=24)).isoformat()
    opportunities = await db.opportunities.find(
        {"status": "Published", "published_at": {"$lte": cutoff}, "amplify_followup_status": {"$exists": False}},
        {"_id": 0, "opportunity_id": 1, "user_id": 1, "organization_name": 1},
    ).to_list(100)
    sent = 0
    for item in opportunities:
        owner = await db.members.find_one({"user_id": item["user_id"]}, {"_id": 0, "email": 1, "first_name": 1, "review_mode": 1, "internal_client_test": 1}) or {}
        if not owner.get("email") or owner.get("review_mode") or owner.get("internal_client_test"):
            continue
        token = secrets.token_urlsafe(32)
        claim = await db.opportunities.update_one(
            {"opportunity_id": item["opportunity_id"], "amplify_followup_status": {"$exists": False}},
            {"$set": {"amplify_followup_status": "Sending", "amplify_token": token}},
        )
        if not claim.modified_count:
            continue
        link = f"{origin()}/recruit/amplify?token={token}"
        first = html.escape(owner.get("first_name") or "there")
        org = html.escape(item.get("organization_name") or "your organization")
        body = (f"<p>Hi {first},</p><p>Your recruitment campaign for {org} is live through Nonprofit Board Builder.</p>"
                "<p>If you want to reach an even larger pool of potential board candidates, we can amplify your campaign across additional channels and help you attract more applicants.</p>"
                f"<p><a href='{html.escape(link, quote=True)}' style='display:inline-block;background:#087e5b;color:white;padding:12px 18px;text-decoration:none'>AMPLIFY MY CAMPAIGN — $497</a></p>"
                "<p>You can review the price and complete payment securely through Stripe.</p>")
        try:
            email_id = await _send("NONPROFIT_SENDER", owner["email"],
                f"Reach More Board Applicants For {item.get('organization_name') or 'Your Campaign'}", _wrap("Amplify Your Campaign", body))
            await db.opportunities.update_one({"opportunity_id": item["opportunity_id"]},
                {"$set": {"amplify_followup_status": "Sent", "amplify_followup_at": now.isoformat(), "amplify_followup_email_id": email_id}})
            sent += 1
        except Exception as exc:
            logger.exception("Amplification follow-up failed")
            await db.opportunities.update_one({"opportunity_id": item["opportunity_id"]},
                {"$set": {"amplify_followup_status": "Failed", "amplify_followup_error": str(exc)[:300]}})
    return sent
