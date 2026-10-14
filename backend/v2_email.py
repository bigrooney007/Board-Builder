"""Durable transactional delivery using Board Builder's existing Resend service.

Every event has one database key and one provider idempotency key. Approved
attachments are immutable snapshots, not documents rebuilt during a retry.
"""
import asyncio
import html
import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from v2_core import digest, find_journey, internal_path, is_enabled, issue_owner_link, new_id, now_iso, origin

PUBLIC_ACTIONS = ("/v2/forms/", "/v2/meeting/", "/v2/shared/", "/v2/marketplace")
CONTACT_REMINDER = "Please add our sending address to your contacts and mark important Board Builder emails as favorites so you can find them when you need them."


async def queue_email(db, event_key, to, subject, body, journey_id="", action_path="", resource_id="", revision=None, attachments=None, metadata=None, ready=True):
    existing = await db.v2_email_outbox.find_one({"event_key": event_key}, {"_id": 0})
    if existing:
        return existing
    action_url = ""
    if action_path:
        action_path = internal_path(action_path)
        if action_path.startswith(PUBLIC_ACTIONS):
            action_url = origin() + action_path
        elif journey_id:
            journey = await find_journey(db, journey_id)
            if str(to).lower() != journey["email"]:
                raise HTTPException(422, "A private action link can only be sent to the organization leader.")
            action_url = await issue_owner_link(db, journey_id, action_path)
        else:
            action_url = origin() + action_path
    paragraphs = "".join("<p>" + html.escape(part).replace("\n", "<br>") + "</p>" for part in str(body).split("\n\n"))
    if action_url:
        paragraphs += "<p><a style='display:inline-block;background:#3730a3;color:white;padding:14px 22px;text-decoration:none;border-radius:7px' href='" + html.escape(action_url, quote=True) + "'>OPEN THIS ACTION →</a></p>"
    paragraphs += "<p style='font-size:13px;color:#4b5563'>" + CONTACT_REMINDER + "</p>"
    from email_template import wrap_email
    payload = {"to": [str(to).lower()], "subject": str(subject), "html": wrap_email(str(subject), paragraphs, separator=" | ")}
    if attachments:
        payload["attachments"] = attachments
    record = {"event_id": new_id(), "event_key": event_key, "journey_id": journey_id,
              "resource_id": resource_id, "revision": revision, "to": str(to).lower(), "subject": str(subject),
              "payload": payload, "provider_key": "nbb-v2-" + digest(event_key), "status": "pending" if ready else "assembling", "attempts": 0,
              "created_at": now_iso(), "updated_at": now_iso(), "next_attempt_at": now_iso()}
    if metadata:
        record.update({key: value for key, value in metadata.items() if key in {
            "purpose", "network_applicant_id", "network_mode", "campaign_revision", "sender_env", "unsubscribe_digest", "unsubscribe_expires_at",
        }})
    await db.v2_email_outbox.update_one({"event_key": event_key}, {"$setOnInsert": record}, upsert=True)
    return await db.v2_email_outbox.find_one({"event_key": event_key}, {"_id": 0})


def test_recipients():
    return {email.strip().lower() for email in os.environ.get("NBB_V2_TEST_EMAILS", "").split(",") if email.strip()}


async def send_provider(payload, idempotency_key):
    import resend
    resend.api_key = os.environ["RESEND_API_KEY"]
    params = {"from": os.environ["NONPROFIT_SENDER"], **payload}
    response = await resend.Emails.send_async(params, {"idempotency_key": idempotency_key})
    return response.get("id") if isinstance(response, dict) else getattr(response, "id", "")


async def process_email(db, event_id, transport=None):
    record = await db.v2_email_outbox.find_one({"event_id": event_id}, {"_id": 0})
    if not record or record.get("status") == "sent":
        return record
    if record.get("status") == "sending" and record.get("lease_until", "") > now_iso():
        return record
    if record.get("status") not in {"pending", "failed", "blocked", "sending"}:
        return record
    if record.get("purpose") == "board-opportunity":
        from v2_campaigns import opted_in
        applicant = await db.board_applicants.find_one({"applicant_id": record.get("network_applicant_id"), "email": record["to"]}, {"_id": 0})
        journey = await db.v2_journeys.find_one({"journey_id": record.get("journey_id")}, {"_id": 0})
        reason = ""
        if not applicant or not opted_in(applicant):
            reason = "This contact no longer permits board opportunity announcements."
        elif not journey or journey.get("campaign_status") != "active":
            reason = "This recruitment campaign is not active."
        elif record.get("network_mode") == "live":
            if os.environ.get("NBB_V2_NETWORK_LIVE_ENABLED", "false").lower() != "true":
                reason = "Live applicant network announcements are disabled in this preview."
            else:
                try:
                    import resend
                    resend.api_key = os.environ["RESEND_API_KEY"]
                    contact_id = applicant.get("resend_contact_id")
                    if not contact_id:
                        raise ValueError("Missing registered contact")
                    contact = await resend.Contacts.get_async(id=contact_id)
                    unsubscribed = contact.get("unsubscribed") if isinstance(contact, dict) else getattr(contact, "unsubscribed", None)
                    if unsubscribed is not False:
                        reason = "The provider's subscription permission could not be confirmed."
                    topic_id = os.environ.get("RESEND_BOARD_OPPORTUNITIES_TOPIC_ID")
                    if not topic_id:
                        raise ValueError("Missing opportunity topic")
                    topics = await resend.ContactsTopics.list_async({"email": record["to"]})
                    topic_rows = topics.get("data", []) if isinstance(topics, dict) else getattr(topics, "data", [])
                    if not any((item.get("id") if isinstance(item, dict) else getattr(item, "id", None)) == topic_id
                               and (item.get("subscription") if isinstance(item, dict) else getattr(item, "subscription", None)) == "opt_in" for item in topic_rows):
                        reason = "This contact is not opted in to board opportunity announcements."
                except Exception:
                    reason = "The provider's opportunity subscription permission could not be confirmed."
        if reason:
            await db.v2_email_outbox.update_one({"event_id": event_id}, {"$set": {"status": "suppressed", "error": reason, "updated_at": now_iso()}})
            return await db.v2_email_outbox.find_one({"event_id": event_id}, {"_id": 0})
    # An automatic retry outside the provider's 24-hour deduplication window
    # needs an administrator to reconcile the earlier attempt first.
    if record.get("first_attempt_at") and record.get("attempts", 0) and datetime.fromisoformat(record["first_attempt_at"]) < datetime.now(timezone.utc) - timedelta(hours=23):
        await db.v2_email_outbox.update_one({"event_id": event_id}, {"$set": {"status": "needs_review", "error": "Reconcile the earlier delivery before retrying this email."}})
        return await db.v2_email_outbox.find_one({"event_id": event_id}, {"_id": 0})
    if os.environ.get("NBB_V2_EMAIL_TEST_MODE", "false").lower() == "true" and record["to"] not in test_recipients():
        await db.v2_email_outbox.update_one({"event_id": event_id}, {"$set": {"status": "blocked", "error": "This preview only sends email to the configured test contacts.", "updated_at": now_iso()}})
        return await db.v2_email_outbox.find_one({"event_id": event_id}, {"_id": 0})
    claimed = await db.v2_email_outbox.update_one(
        {"event_id": event_id, "status": record["status"], "attempts": record.get("attempts", 0)},
        {"$set": {"status": "sending", "lease_until": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
                  "first_attempt_at": record.get("first_attempt_at") or now_iso(), "updated_at": now_iso()}, "$inc": {"attempts": 1}},
    )
    if not claimed.modified_count:
        return await db.v2_email_outbox.find_one({"event_id": event_id}, {"_id": 0})
    try:
        payload = dict(record["payload"])
        if record.get("sender_env"):
            payload["from"] = os.environ[record["sender_env"]]
        provider_id = await (transport or send_provider)(payload, record["provider_key"])
        if not provider_id:
            raise RuntimeError("The email provider did not confirm receipt.")
        await db.v2_email_outbox.update_one({"event_id": event_id, "status": "sending"},
            {"$set": {"status": "sent", "provider_id": str(provider_id), "sent_at": now_iso(), "updated_at": now_iso(), "error": ""}, "$unset": {"lease_until": ""}})
    except Exception as exc:
        attempts = record.get("attempts", 0) + 1
        # Do not log payloads, secure links or private resource contents.
        summary = "Email delivery could not be confirmed. Check the sending configuration and retry."
        if isinstance(exc, KeyError):
            summary = "The email sending service needs to be configured."
        await db.v2_email_outbox.update_one({"event_id": event_id, "status": "sending"},
            {"$set": {"status": "failed" if attempts < 5 else "needs_review", "error": summary,
                      "next_attempt_at": (datetime.now(timezone.utc) + timedelta(seconds=min(30 * 2 ** attempts, 1800))).isoformat(),
                      "updated_at": now_iso()}, "$unset": {"lease_until": ""}})
    return await db.v2_email_outbox.find_one({"event_id": event_id}, {"_id": 0})


async def retry_email(db, event_id, journey_id=None):
    query = {"event_id": event_id}
    if journey_id:
        query["journey_id"] = journey_id
    record = await db.v2_email_outbox.find_one(query, {"_id": 0})
    if not record:
        raise HTTPException(404, "This delivery record was not found.")
    if record["status"] == "needs_review":
        raise HTTPException(409, "An administrator must reconcile the earlier attempt before sending again.")
    if record["status"] in {"failed", "blocked"}:
        await db.v2_email_outbox.update_one(query, {"$set": {"status": "pending", "next_attempt_at": now_iso(), "updated_at": now_iso()}})
    return await db.v2_email_outbox.find_one(query, {"_id": 0})


async def generate_journey(db, journey):
    from v2_resources import generate_pending_resources
    try:
        await generate_pending_resources(db, journey)
        failures = await db.v2_resources.count_documents({"journey_id": journey["journey_id"], "status": "failed"})
        pending = await db.v2_resources.count_documents({"journey_id": journey["journey_id"], "status": "preparing"})
        await db.v2_journeys.update_one({"journey_id": journey["journey_id"]},
            {"$set": {"generation_status": "pending" if pending else "complete_with_errors" if failures else "complete", "updated_at": now_iso()}, "$unset": {"generation_lease_until": ""}})
        if journey["product"] == "recruit" and not failures:
            await queue_email(db, "pack-ready:" + journey["journey_id"], journey["email"], "Your Board Recruitment Pack Is Ready",
                "Your customized recruitment resources are ready to review. Open each resource, make any changes you need, and approve it. We will email the exact approved version to you.",
                journey_id=journey["journey_id"], action_path="/v2/resources/" + journey["journey_id"])
    except Exception:
        await db.v2_journeys.update_one({"journey_id": journey["journey_id"]},
            {"$set": {"generation_status": "failed", "technical_issue": "Resource generation needs a retry.", "updated_at": now_iso()}, "$unset": {"generation_lease_until": ""}})


async def queue_meeting_reminders(db):
    journeys = await db.v2_journeys.find({"state": "paid", "product": {"$in": ["board-fundraising-game", "strategic-planning"]}}, {"_id": 0}).to_list(1000)
    for journey in journeys:
        meeting = journey.get("meeting") or {}
        if not meeting.get("date") or not meeting.get("time") or not meeting.get("timezone"):
            continue
        try:
            from zoneinfo import ZoneInfo
            starts = datetime.fromisoformat(meeting["date"] + "T" + meeting["time"]).replace(tzinfo=ZoneInfo(meeting["timezone"]))
            hours = (starts.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds() / 3600
        except (ValueError, KeyError):
            continue
        if not 0 < hours <= 48:
            continue
        meeting_key = digest(str(meeting))[:16]
        await queue_email(db, f"meeting-reminder:{journey['journey_id']}:{meeting_key}", journey["email"], "Prepare for Your Board Meeting",
            "Your meeting is approaching. You can review everyone's submitted ideas, open the facilitation guide, and prepare the group session now. Your meeting link remains available whenever you need it.",
            journey_id=journey["journey_id"], action_path="/v2/group/" + journey["journey_id"])


async def jobs_once(db, generation_tasks=None):
    tasks = generation_tasks if generation_tasks is not None else {}
    for key, task in list(tasks.items()):
        if task.done():
            tasks.pop(key)
    # A newly seeded response guide may race the end of an earlier generation.
    # Inspect durable preparing records so it can never be stranded by a status
    # write on the journey record.
    waiting = await db.v2_resources.find({"status": "preparing"}, {"_id": 0, "journey_id": 1}).to_list(100)
    for row in waiting:
        await db.v2_journeys.update_one({"journey_id": row["journey_id"], "state": "paid",
                                       "generation_status": {"$in": ["complete", "complete_with_errors", "failed"]}},
                                      {"$set": {"generation_status": "pending"}})
    if len(tasks) < 2:
        journeys = await db.v2_journeys.find({"state": "paid", "$or": [{"generation_status": "pending"},
            {"generation_status": "running", "generation_lease_until": {"$lte": now_iso()}}]}, {"_id": 0}).to_list(2 - len(tasks))
        for journey in journeys:
            jid = journey["journey_id"]
            claimed = await db.v2_journeys.update_one({"journey_id": jid, "generation_status": journey["generation_status"]},
                {"$set": {"generation_status": "running", "generation_lease_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}})
            if claimed.modified_count:
                tasks[jid] = asyncio.create_task(generate_journey(db, journey))
    records = await db.v2_email_outbox.find({"$or": [
        {"status": {"$in": ["pending", "failed"]}, "next_attempt_at": {"$lte": now_iso()}},
        {"status": "sending", "lease_until": {"$lte": now_iso()}}]}, {"_id": 0}).to_list(25)
    for record in records:
        await process_email(db, record["event_id"])
    return tasks


async def run_v2_jobs(db):
    tasks = {}
    last_reminder = 0
    try:
        while is_enabled():
            try:
                await jobs_once(db, tasks)
                if asyncio.get_running_loop().time() - last_reminder > 60:
                    await queue_meeting_reminders(db)
                    last_reminder = asyncio.get_running_loop().time()
            except Exception:
                # Persisted jobs are retried on the next pass; an unavailable
                # provider must never terminate unrelated original workers.
                pass
            await asyncio.sleep(2)
    finally:
        for task in tasks.values():
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks.values(), return_exceptions=True)
