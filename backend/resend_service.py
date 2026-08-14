import html
import os
from datetime import datetime, timezone
from typing import Any, Dict

import resend


SEGMENTS = {
    "nonprofit_leaders": "Nonprofit Board Builder — Nonprofit Leaders",
    "board_applicants": "Nonprofit Board Builder — Board Applicants",
}

TOPICS = {
    "board_building": (
        "Board Building Opportunities for Nonprofits",
        "Weekly board-building sales emails, recruitment information, board reactivation and fundraising activation strategies, services and relevant offers.",
    ),
    "board_opportunities": (
        "Nonprofit Board Opportunities",
        "Genuine board opportunities, invitations to apply and information directly connected to an active board opportunity or introduction.",
    ),
}

CONTACT_PROPERTIES = [
    "contact_type", "phone_number", "country", "city", "state_region",
    "job_title", "employer", "professional_field", "skills", "causes",
    "board_types", "geographic_preferences", "participation_preferences",
    "availability", "fundraising_strengths", "organization_name", "submission_id",
    "present_board_size", "active_board_members", "inactive_board_members",
    "recruitment_need", "fundraising_need", "execution_preference",
    "first_submission_at", "latest_submission_at",
]


def configure_resend() -> None:
    resend.api_key = os.environ["RESEND_API_KEY"]


def value(item: Any, key: str) -> Any:
    return item.get(key) if isinstance(item, dict) else getattr(item, key, None)


async def provision_resend_resources() -> Dict[str, str]:
    configure_resend()
    result: Dict[str, str] = {}
    segments = await resend.Segments.list_async({"limit": 100})
    segment_map = {value(item, "name"): value(item, "id") for item in value(segments, "data") or []}
    for key, name in SEGMENTS.items():
        segment_id = segment_map.get(name)
        if not segment_id:
            segment_id = value(await resend.Segments.create_async({"name": name}), "id")
        result[f"segment_{key}"] = segment_id

    topics = await resend.Topics.list_async({"limit": 100})
    topic_map = {value(item, "name"): value(item, "id") for item in value(topics, "data") or []}
    for key, (name, description) in TOPICS.items():
        topic_id = topic_map.get(name)
        if not topic_id:
            topic_id = value(await resend.Topics.create_async({
                "name": name, "description": description, "default_subscription": "opt_out",
            }), "id")
        result[f"topic_{key}"] = topic_id

    properties = await resend.ContactProperties.list_async({"limit": 100})
    existing = {value(item, "key") for item in value(properties, "data") or []}
    for key in CONTACT_PROPERTIES:
        if key not in existing:
            await resend.ContactProperties.create_async({"key": key, "type": "string", "fallback_value": ""})
    return result


def clean_properties(properties: Dict[str, Any]) -> Dict[str, str]:
    cleaned = {}
    for key in CONTACT_PROPERTIES:
        item = properties.get(key, "")
        if isinstance(item, list):
            item = " | ".join(item)
        cleaned[key] = str(item or "")[:500]
    return cleaned


async def upsert_contact(
    *, email: str, first_name: str, last_name: str, properties: Dict[str, Any],
    segment_id: str, topic_id: str,
) -> str:
    configure_resend()
    params = {
        "email": email, "first_name": first_name, "last_name": last_name,
        "unsubscribed": False, "properties": clean_properties(properties),
    }
    try:
        contact = await resend.Contacts.get_async(email=email)
        contact_id = value(contact, "id")
        response = await resend.Contacts.update_async(params)
        contact_id = value(response, "id") or contact_id
    except Exception:
        response = await resend.Contacts.create_async(params)
        contact_id = value(response, "id")
    await resend.ContactSegments.add_async({"segment_id": segment_id, "email": email})
    await resend.ContactsTopics.update_async({
        "email": email, "topics": [{"id": topic_id, "subscription": "opt_in"}],
    })
    return contact_id


async def sync_nonprofit_leader(contact: Dict[str, Any]) -> str:
    parts = contact["name"].strip().split(" ", 1)
    return await upsert_contact(
        email=contact["email"], first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "",
        properties={
            "contact_type": "Nonprofit Leader", "phone_number": contact["phone"],
            "country": contact["country"], "city": contact["city"],
            "state_region": contact["state_region"], "organization_name": contact["organization_name"],
            "submission_id": contact["latest_assessment_number"],
            "present_board_size": contact["present_board_size"],
            "active_board_members": contact["active_board_members"],
            "inactive_board_members": contact["inactive_board_members"],
            "recruitment_need": contact["recruitment_need"],
            "fundraising_need": contact["fundraising_need"],
            "execution_preference": contact["execution_preference"],
            "first_submission_at": contact["created_at"],
            "latest_submission_at": contact["latest_assessment_at"],
        },
        segment_id=os.environ["RESEND_NONPROFIT_LEADERS_SEGMENT_ID"],
        topic_id=os.environ["RESEND_BOARD_BUILDING_TOPIC_ID"],
    )


async def sync_board_applicant(profile: Dict[str, Any]) -> str:
    return await upsert_contact(
        email=profile["email"], first_name=profile["first_name"], last_name=profile["last_name"],
        properties={
            "contact_type": "Board Applicant", "phone_number": profile["phone"],
            "country": profile["country"], "city": profile["city"],
            "state_region": profile["state_region"], "job_title": profile["job_title"],
            "employer": profile.get("employer", ""), "professional_field": profile["professional_field"],
            "skills": profile["skills"], "causes": profile["causes"],
            "board_types": profile["board_types"],
            "geographic_preferences": profile["geographic_preferences"],
            "participation_preferences": profile["participation_preferences"],
            "availability": profile["availability"],
            "fundraising_strengths": profile["fundraising_activities"],
            "submission_id": profile["applicant_id"],
            "first_submission_at": profile["created_at"],
            "latest_submission_at": profile["updated_at"],
        },
        segment_id=os.environ["RESEND_BOARD_APPLICANTS_SEGMENT_ID"],
        topic_id=os.environ["RESEND_BOARD_OPPORTUNITIES_TOPIC_ID"],
    )


async def sync_existing_applicants_once(db) -> Dict[str, int]:
    run_key = "existing_board_applicant_resend_sync_v1"
    existing_run = await db.automation_runs.find_one({"run_key": run_key}, {"_id": 0})
    if existing_run and existing_run.get("status") == "Completed":
        return {"processed": existing_run["processed"], "synced": existing_run["synced"], "failed": existing_run["failed"]}
    applicants = await db.board_applicants.find({}, {"_id": 0}).to_list(100000)
    processed = synced = failed = 0
    for applicant in applicants:
        processed += 1
        try:
            contact_id = await sync_board_applicant(applicant)
            await db.board_applicants.update_one(
                {"email": applicant["email"]},
                {"$set": {"resend_contact_id": contact_id, "resend_segment_status": "Synced", "resend_sync_error": ""}},
            )
            synced += 1
        except Exception as exc:
            failed += 1
            await db.board_applicants.update_one(
                {"email": applicant["email"]},
                {"$set": {"resend_segment_status": "Failed", "resend_sync_error": str(exc)[:500]}},
            )
            await send_automation_error(
                db, failure_key=f"existing-applicant-sync:{applicant['applicant_id']}",
                process="Existing board applicant one-time Resend sync",
                contact_email=applicant["email"], error=str(exc), submission_saved=True,
                owner_notification_sent=False,
                corrective_action="Review the applicant contact and Resend API access, then update this contact manually in the Board Applicants Segment.",
            )
    await db.automation_runs.update_one(
        {"run_key": run_key},
        {"$set": {"run_key": run_key, "status": "Completed", "processed": processed,
                  "synced": synced, "failed": failed, "completed_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"processed": processed, "synced": synced, "failed": failed}


async def create_segment_broadcast(
    *, segment_id: str, sender: str, subject: str, html_content: str, name: str, send: bool = True,
) -> str:
    configure_resend()
    response = await resend.Broadcasts.create_async({
        "segment_id": segment_id, "from": sender, "subject": subject,
        "html": html_content, "name": name, "send": send,
    })
    return value(response, "id")


async def send_automation_error(
    db, *, failure_key: str, process: str, contact_email: str, error: str,
    submission_saved: bool, owner_notification_sent: bool, corrective_action: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    result = await db.automation_errors.update_one(
        {"failure_key": failure_key},
        {"$setOnInsert": {
            "failure_key": failure_key, "process": process, "contact_email": contact_email,
            "date_time": now, "error": error[:1000], "submission_saved": submission_saved,
            "owner_notification_sent": owner_notification_sent,
            "corrective_action": corrective_action, "notification_status": "Pending",
        }},
        upsert=True,
    )
    if not result.upserted_id:
        return
    safe = lambda item: html.escape(str(item or "Not applicable"))
    body = f"""
    <div style="max-width:600px;margin:auto;background:#ffffff;color:#000000;font-family:Arial,sans-serif;font-size:18px;line-height:1.55;padding:28px;">
      <h1 style="font-size:29px;color:#000000;">Nonprofit Board Builder Automation Error</h1>
      <p><strong>Process affected:</strong> {safe(process)}<br><strong>Applicant or nonprofit email:</strong> {safe(contact_email)}<br>
      <strong>Date and time:</strong> {safe(now)}<br><strong>Error:</strong> {safe(error)}<br>
      <strong>Form submission saved:</strong> {"Yes" if submission_saved else "No"}<br>
      <strong>Owner notification sent:</strong> {"Yes" if owner_notification_sent else "No"}</p>
      <p><strong>Corrective action required:</strong> {safe(corrective_action)}</p>
    </div>"""
    configure_resend()
    try:
        email_response = await resend.Emails.send_async({
            "from": os.environ["NONPROFIT_SENDER"], "to": [os.environ["OWNER_NOTIFICATION_EMAIL"]],
            "subject": "Nonprofit Board Builder Automation Error", "html": body,
        })
        await db.automation_errors.update_one(
            {"failure_key": failure_key},
            {"$set": {"notification_status": "Sent", "notification_email_id": value(email_response, "id")}},
        )
    except Exception as exc:
        await db.automation_errors.update_one(
            {"failure_key": failure_key},
            {"$set": {"notification_status": "Failed", "notification_error": str(exc)[:500]}},
        )


async def send_applicant_confirmation(profile: Dict[str, Any]) -> str:
    configure_resend()
    first_name = html.escape(profile["first_name"])
    body = f"""
    <div style="max-width:600px;margin:auto;background:#ffffff;color:#000000;font-family:Arial,sans-serif;font-size:18px;line-height:1.55;padding:28px;">
      <h1 style="margin:0 0 22px;color:#000000;font-size:29px;">Your Board Applicant Profile Has Been Saved</h1>
      <p>Hi {first_name},</p>
      <p>Thank you for joining the Nonprofit Board Builder Applicant Network.</p>
      <p>We have saved your professional background, skills, causes, location and board preferences.</p>
      <p>We will contact you when we have a genuine nonprofit board opportunity that may align with your profile.</p>
      <p>Please save boardapplicants@nonprofitboardbuilder.com to your contacts so you do not miss an opportunity.</p>
      <p>Completing a profile does not guarantee placement or an introduction.</p>
      <p><strong>Nonprofit Board Builder — Board Opportunities</strong></p>
      <p>{os.environ['POSTAL_ADDRESS']}<br><a style="color:#000000;" href="{{{{{{RESEND_UNSUBSCRIBE_URL}}}}}}">Unsubscribe</a></p>
    </div>"""
    response = await resend.Emails.send_async({
        "from": os.environ["BOARD_APPLICANT_SENDER"], "to": [profile["email"]],
        "subject": "Your Board Applicant Profile Has Been Saved", "html": body,
    })
    return value(response, "id")


async def send_owner_applicant_profile(profile: Dict[str, Any]) -> str:
    configure_resend()
    excluded = {"resume_file_id", "resend_sync_error", "confirmation_email_error", "owner_notification_error"}
    rows = []
    for key, item in profile.items():
        if key in excluded:
            continue
        label = key.replace("_", " ").title()
        display = ", ".join(item) if isinstance(item, list) else item
        rows.append(f"<tr><td style='padding:8px;border-bottom:1px solid #dddddd;font-weight:bold;vertical-align:top;'>{html.escape(label)}</td><td style='padding:8px;border-bottom:1px solid #dddddd;'>{html.escape(str(display or 'Not provided'))}</td></tr>")
    body = f"""
    <div style="max-width:760px;margin:auto;background:#ffffff;color:#000000;font-family:Arial,sans-serif;font-size:16px;line-height:1.5;padding:28px;">
      <h1 style="font-size:28px;color:#000000;">Board Applicant Profile — {html.escape(profile['first_name'])} {html.escape(profile['last_name'])}</h1>
      <table style="width:100%;border-collapse:collapse;">{''.join(rows)}</table>
    </div>"""
    response = await resend.Emails.send_async({
        "from": os.environ["BOARD_APPLICANT_SENDER"], "to": [os.environ["OWNER_NOTIFICATION_EMAIL"]],
        "subject": f"New Board Applicant — {profile['first_name']} {profile['last_name']}", "html": body,
    })
    return value(response, "id")