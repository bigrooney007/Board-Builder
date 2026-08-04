import html
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

import resend


SEGMENTS = {
    "nonprofit_leaders": "Nonprofit Board Builder — Nonprofit Leaders",
    "board_applicants": "Nonprofit Board Builder — Board Applicants",
    "nonprofit_no_action": "Nonprofit Board Builder — Nonprofit Weekly No Action",
    "applicant_no_action": "Nonprofit Board Builder — Applicant Weekly No Action",
}

TOPICS = {
    "nonprofit_updates": (
        "Board Building Updates for Nonprofits",
        "Weekly board applicant reports, board recruitment and reactivation strategies, fundraising activation, services and relevant offers.",
    ),
    "applicant_updates": (
        "Board Opportunities and Applicant Updates",
        "Nonprofit board opportunities, weekly applicant network reports and information directly connected to joining and serving on boards.",
    ),
    "applicant_resources": (
        "Board Applicant Resources and Offers",
        "Training, resources, events and professional offers for board applicants who explicitly request them.",
    ),
}

CONTACT_PROPERTIES = [
    "contact_type", "country", "city", "state_region", "job_title",
    "professional_field", "causes", "board_types", "fundraising_strengths",
    "organization_name", "submission_id", "first_submission_at",
    "latest_submission_at", "nonprofit_action_url", "applicant_action_url",
]


def configure_resend() -> None:
    resend.api_key = os.environ["RESEND_API_KEY"]


def value(item: Any, key: str) -> Any:
    return item.get(key) if isinstance(item, dict) else getattr(item, key, None)


async def provision_resend_resources() -> Dict[str, str]:
    configure_resend()
    result: Dict[str, str] = {}
    segment_response = await resend.Segments.list_async({"limit": 100})
    existing_segments = {value(item, "name"): value(item, "id") for item in value(segment_response, "data") or []}
    for env_key, name in SEGMENTS.items():
        segment_id = existing_segments.get(name)
        if not segment_id:
            segment_id = value(await resend.Segments.create_async({"name": name}), "id")
        result[f"segment_{env_key}"] = segment_id

    topic_response = await resend.Topics.list_async({"limit": 100})
    existing_topics = {value(item, "name"): value(item, "id") for item in value(topic_response, "data") or []}
    for env_key, (name, description) in TOPICS.items():
        topic_id = existing_topics.get(name)
        if not topic_id:
            topic_id = value(await resend.Topics.create_async({
                "name": name,
                "description": description,
                "default_subscription": "opt_out",
            }), "id")
        result[f"topic_{env_key}"] = topic_id

    property_response = await resend.ContactProperties.list_async({"limit": 100})
    existing_properties = {value(item, "key") for item in value(property_response, "data") or []}
    for key in CONTACT_PROPERTIES:
        if key not in existing_properties:
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
    segment_id: str, topic_updates: Iterable[Dict[str, str]],
) -> str:
    configure_resend()
    params = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "unsubscribed": False,
        "properties": clean_properties(properties),
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
    updates = list(topic_updates)
    if updates:
        await resend.ContactsTopics.update_async({"email": email, "topics": updates})
    return contact_id


async def update_contact_properties(email: str, properties: Dict[str, Any]) -> str:
    configure_resend()
    contact = await resend.Contacts.get_async(email=email)
    existing = value(contact, "properties") or {}
    response = await resend.Contacts.update_async({
        "email": email,
        "properties": clean_properties({**existing, **properties}),
    })
    return value(response, "id") or value(contact, "id")


async def sync_board_applicant(profile: Dict[str, Any]) -> str:
    topics = [
        {"id": os.environ["RESEND_TOPIC_APPLICANT_UPDATES_ID"], "subscription": "opt_in"},
        {
            "id": os.environ["RESEND_TOPIC_APPLICANT_RESOURCES_ID"],
            "subscription": "opt_in" if profile.get("other_offers_consent") else "opt_out",
        },
    ]
    return await upsert_contact(
        email=profile["email"], first_name=profile["first_name"], last_name=profile["last_name"],
        properties={
            "contact_type": "Board Applicant", "country": profile["country"],
            "city": profile["city"], "state_region": profile["state_region"],
            "job_title": profile["job_title"], "professional_field": profile["professional_field"],
            "causes": profile["causes"], "board_types": profile["board_types"],
            "fundraising_strengths": profile["fundraising_activities"],
            "submission_id": profile["applicant_id"], "first_submission_at": profile["created_at"],
            "latest_submission_at": profile["updated_at"],
        },
        segment_id=os.environ["RESEND_SEGMENT_BOARD_APPLICANTS_ID"], topic_updates=topics,
    )


async def sync_nonprofit_leader(contact: Dict[str, Any]) -> str:
    name_parts = contact["name"].strip().split(" ", 1)
    return await upsert_contact(
        email=contact["email"], first_name=name_parts[0],
        last_name=name_parts[1] if len(name_parts) > 1 else "",
        properties={
            "contact_type": "Nonprofit Leader", "country": contact["country"],
            "city": contact["city"], "state_region": contact["state_region"],
            "organization_name": contact["organization_name"],
            "submission_id": contact["latest_assessment_number"],
            "first_submission_at": contact["created_at"],
            "latest_submission_at": contact["latest_assessment_at"],
        },
        segment_id=os.environ["RESEND_SEGMENT_NONPROFIT_LEADERS_ID"],
        topic_updates=[{"id": os.environ["RESEND_TOPIC_NONPROFIT_UPDATES_ID"], "subscription": "opt_in"}],
    )


async def add_to_segment(email: str, segment_id: str) -> None:
    configure_resend()
    await resend.ContactSegments.add_async({"segment_id": segment_id, "email": email})


async def remove_from_segment(email: str, segment_id: str) -> None:
    configure_resend()
    try:
        await resend.ContactSegments.remove_async({"segment_id": segment_id, "email": email})
    except Exception:
        pass


async def create_segment_broadcast(
    *, segment_id: str, sender: str, subject: str, html_content: str, name: str,
    send: bool = True,
) -> str:
    configure_resend()
    response = await resend.Broadcasts.create_async({
        "segment_id": segment_id,
        "from": sender,
        "subject": subject,
        "html": html_content,
        "name": name,
        "send": send,
    })
    return value(response, "id")


async def send_automation_error(
    db, *, failure_key: str, automation: str, contact_or_report_type: str,
    error: str, submission_saved: bool, email_sent: bool, corrective_action: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    inserted = await db.automation_errors.update_one(
        {"failure_key": failure_key},
        {"$setOnInsert": {
            "failure_key": failure_key, "automation": automation,
            "contact_or_report_type": contact_or_report_type, "date_time": now,
            "error": error[:1000], "submission_saved": submission_saved,
            "email_sent": email_sent, "corrective_action": corrective_action,
            "notification_status": "Pending",
        }},
        upsert=True,
    )
    if not inserted.upserted_id:
        return
    safe = lambda item: html.escape(str(item))
    body = f"""
    <div style="font-family:Arial,sans-serif;line-height:1.6;color:#17221c;max-width:700px;margin:auto;">
      <h1 style="color:#8b1f1f;">Nonprofit Board Builder Automation Error</h1>
      <p><strong>Automation affected:</strong> {safe(automation)}<br>
      <strong>Contact or report type:</strong> {safe(contact_or_report_type)}<br>
      <strong>Date and time:</strong> {safe(now)}<br>
      <strong>Error:</strong> {safe(error)}<br>
      <strong>Underlying form submission saved:</strong> {"Yes" if submission_saved else "No"}<br>
      <strong>Email sent:</strong> {"Yes" if email_sent else "No"}</p>
      <p><strong>Corrective action required:</strong> {safe(corrective_action)}</p>
    </div>"""
    configure_resend()
    try:
        response = await resend.Emails.send_async({
            "from": os.environ["NONPROFIT_SENDER"],
            "to": [os.environ["OWNER_NOTIFICATION_EMAIL"]],
            "subject": "Nonprofit Board Builder Automation Error — Action Required",
            "html": body,
        })
        await db.automation_errors.update_one(
            {"failure_key": failure_key},
            {"$set": {"notification_status": "Sent", "notification_email_id": value(response, "id")}},
        )
    except Exception as exc:
        await db.automation_errors.update_one(
            {"failure_key": failure_key},
            {"$set": {"notification_status": "Failed", "notification_error": str(exc)[:500]}},
        )


def list_text(values: Iterable[str]) -> str:
    return ", ".join(values) if values else "Not provided"


async def send_applicant_confirmation(profile: Dict[str, Any]) -> str:
    configure_resend()
    safe = lambda item: html.escape(str(item or "Not provided"))
    content = f"""
    <div style="font-family:Arial,sans-serif;color:#17221c;line-height:1.65;max-width:680px;margin:auto;">
      <h1 style="color:#083d2a;">Welcome to the Nonprofit Board Builder Applicant Network</h1>
      <p>Hi {safe(profile['first_name'])},</p><p>Your professional profile and board preferences have been saved.</p>
      <p>We will email you whenever we have a nonprofit board opportunity that matches your experience, interests, preferred causes, location and availability.</p>
      <h2 style="color:#087e5b;font-size:20px;">Your Applicant Details</h2>
      <p><strong>Applicant ID:</strong> {safe(profile['applicant_id'])}<br><strong>Country:</strong> {safe(profile['country'])}<br>
      <strong>City:</strong> {safe(profile['city'])}<br><strong>Professional field:</strong> {safe(profile['professional_field'])}<br>
      <strong>Preferred causes:</strong> {safe(list_text(profile['causes']))}<br><strong>Preferred board types:</strong> {safe(list_text(profile['board_types']))}<br>
      <strong>Availability:</strong> {safe(profile['availability'])}</p>
      <h2 style="color:#087e5b;font-size:20px;">Important</h2>
      <p>Please save:<br><strong>boardapplicants@nonprofitboardbuilder.com</strong><br>to your contacts, favourites or safe-sender list so our board-opportunity emails do not go into spam.</p>
      <p>You can unsubscribe from future board-opportunity emails at any time.</p>
      <p>—<br><strong>Nonprofit Board Builder</strong><br>Helping nonprofits build powerhouse fundraising boards.</p>
      <p style="color:#68766d;font-size:12px;">{safe(os.environ['POSTAL_ADDRESS'])}</p>
    </div>"""
    response = await resend.Emails.send_async({
        "from": os.environ["BOARD_APPLICANT_SENDER"], "to": [profile["email"]],
        "subject": "Your Board Applicant Profile Has Been Saved", "html": content,
    })
    return value(response, "id")