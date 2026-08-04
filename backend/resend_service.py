import html
import os
from typing import Any, Dict, Iterable

import resend


SEGMENTS = {
    "board_applicants": "Board Applicants",
    "nonprofit_leaders": "Nonprofit Leaders",
}

TOPICS = {
    "board_opportunities": (
        "Board Opportunities",
        "Nonprofit board positions and board-service opportunities.",
    ),
    "applicant_resources": (
        "Board Applicant Resources and Offers",
        "Training, resources and professional offers for board applicants.",
    ),
    "nonprofit_offers": (
        "Nonprofit Board-Building Offers",
        "Board recruitment, reactivation, fundraising activation, resources and offers for nonprofit leaders.",
    ),
}

CONTACT_PROPERTIES = [
    "contact_type", "country", "city", "state_region", "job_title",
    "professional_field", "causes", "board_types", "fundraising_strengths",
    "organization_name", "submission_id",
]


def configure_resend() -> None:
    resend.api_key = os.environ["RESEND_API_KEY"]


def _value(item: Any, key: str) -> Any:
    return item.get(key) if isinstance(item, dict) else getattr(item, key, None)


async def provision_resend_resources() -> Dict[str, str]:
    configure_resend()
    result: Dict[str, str] = {}

    segment_response = await resend.Segments.list_async({"limit": 100})
    existing_segments = {_value(item, "name"): _value(item, "id") for item in _value(segment_response, "data") or []}
    for env_key, name in SEGMENTS.items():
        segment_id = existing_segments.get(name)
        if not segment_id:
            created = await resend.Segments.create_async({"name": name})
            segment_id = _value(created, "id")
        result[f"segment_{env_key}"] = segment_id

    topic_response = await resend.Topics.list_async({"limit": 100})
    existing_topics = {_value(item, "name"): _value(item, "id") for item in _value(topic_response, "data") or []}
    for env_key, (name, description) in TOPICS.items():
        topic_id = existing_topics.get(name)
        if not topic_id:
            created = await resend.Topics.create_async({
                "name": name,
                "description": description,
                "default_subscription": "opt_out",
            })
            topic_id = _value(created, "id")
        result[f"topic_{env_key}"] = topic_id

    property_response = await resend.ContactProperties.list_async({"limit": 100})
    existing_properties = {_value(item, "key") for item in _value(property_response, "data") or []}
    for key in CONTACT_PROPERTIES:
        if key not in existing_properties:
            await resend.ContactProperties.create_async({"key": key, "type": "string", "fallback_value": ""})
    return result


def _clean_properties(properties: Dict[str, Any]) -> Dict[str, str]:
    cleaned = {}
    for key in CONTACT_PROPERTIES:
        value = properties.get(key, "")
        if isinstance(value, list):
            value = " | ".join(value)
        cleaned[key] = str(value or "")[:500]
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
        "properties": _clean_properties(properties),
    }
    try:
        contact = await resend.Contacts.get_async(email=email)
        contact_id = _value(contact, "id")
        response = await resend.Contacts.update_async(params)
        contact_id = _value(response, "id") or contact_id
    except Exception:
        response = await resend.Contacts.create_async(params)
        contact_id = _value(response, "id")

    await resend.ContactSegments.add_async({"segment_id": segment_id, "email": email})
    updates = list(topic_updates)
    if updates:
        await resend.ContactsTopics.update_async({"email": email, "topics": updates})
    return contact_id


async def sync_board_applicant(profile: Dict[str, Any]) -> str:
    topics = [
        {"id": os.environ["RESEND_TOPIC_BOARD_OPPORTUNITIES_ID"], "subscription": "opt_in"},
        {
            "id": os.environ["RESEND_TOPIC_APPLICANT_RESOURCES_ID"],
            "subscription": "opt_in" if profile.get("other_offers_consent") else "opt_out",
        },
    ]
    return await upsert_contact(
        email=profile["email"],
        first_name=profile["first_name"],
        last_name=profile["last_name"],
        properties={
            "contact_type": "Board Applicant",
            "country": profile["country"],
            "city": profile["city"],
            "state_region": profile["state_region"],
            "job_title": profile["job_title"],
            "professional_field": profile["professional_field"],
            "causes": profile["causes"],
            "board_types": profile["board_types"],
            "fundraising_strengths": profile["fundraising_activities"],
            "submission_id": profile["applicant_id"],
        },
        segment_id=os.environ["RESEND_SEGMENT_BOARD_APPLICANTS_ID"],
        topic_updates=topics,
    )


async def sync_nonprofit_leader(assessment: Dict[str, Any]) -> str:
    name_parts = assessment["name"].strip().split(" ", 1)
    return await upsert_contact(
        email=assessment["email"],
        first_name=name_parts[0],
        last_name=name_parts[1] if len(name_parts) > 1 else "",
        properties={
            "contact_type": "Nonprofit Leader",
            "country": assessment["country"],
            "city": assessment["city"],
            "state_region": assessment["state_region"],
            "organization_name": assessment["organization_name"],
            "submission_id": assessment["assessment_number"],
        },
        segment_id=os.environ["RESEND_SEGMENT_NONPROFIT_LEADERS_ID"],
        topic_updates=[{"id": os.environ["RESEND_TOPIC_NONPROFIT_OFFERS_ID"], "subscription": "opt_in"}],
    )


def _list_text(values: Iterable[str]) -> str:
    return ", ".join(values) if values else "Not provided"


async def send_applicant_confirmation(profile: Dict[str, Any]) -> str:
    configure_resend()
    safe = lambda value: html.escape(str(value or "Not provided"))
    content = f"""
    <div style="font-family:Arial,sans-serif;color:#17221c;line-height:1.65;max-width:680px;margin:auto;">
      <h1 style="color:#083d2a;">Welcome to the Nonprofit Board Builder Applicant Network</h1>
      <p>Hi {safe(profile['first_name'])},</p>
      <p>Your professional profile and board preferences have been saved.</p>
      <p>We will email you whenever we have a nonprofit board opportunity that matches your experience, interests, preferred causes, location and availability.</p>
      <h2 style="color:#087e5b;font-size:20px;">Your Applicant Details</h2>
      <p><strong>Applicant ID:</strong> {safe(profile['applicant_id'])}<br>
      <strong>Country:</strong> {safe(profile['country'])}<br>
      <strong>City:</strong> {safe(profile['city'])}<br>
      <strong>Professional field:</strong> {safe(profile['professional_field'])}<br>
      <strong>Preferred causes:</strong> {safe(_list_text(profile['causes']))}<br>
      <strong>Preferred board types:</strong> {safe(_list_text(profile['board_types']))}<br>
      <strong>Availability:</strong> {safe(profile['availability'])}</p>
      <h2 style="color:#087e5b;font-size:20px;">Important</h2>
      <p>Please save:<br><strong>boardapplicants@nonprofitboardbuilder.com</strong><br>to your contacts, favourites or safe-sender list so our board-opportunity emails do not go into spam.</p>
      <p>You can unsubscribe from future board-opportunity emails at any time.</p>
      <p>—<br><strong>Nonprofit Board Builder</strong><br>Helping nonprofits build powerhouse fundraising boards.</p>
      <p style="color:#68766d;font-size:12px;">{safe(os.environ['POSTAL_ADDRESS'])}</p>
    </div>
    """
    response = await resend.Emails.send_async({
        "from": os.environ["BOARD_APPLICANT_SENDER"],
        "to": [profile["email"]],
        "subject": "Your Board Applicant Profile Has Been Saved",
        "html": content,
    })
    return _value(response, "id")