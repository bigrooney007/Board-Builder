import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
import resend
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient


sys.path.append(str(Path("/app/backend")))


load_dotenv(Path("/app/frontend/.env"))
load_dotenv(Path("/app/backend/.env"))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API_URL = f"{BASE_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL", "")
DB_NAME = os.environ.get("DB_NAME", "")
OWNER_EMAIL = os.environ.get("OWNER_NOTIFICATION_EMAIL", "").strip().lower()


def _require_env():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL missing")
    if not MONGO_URL or not DB_NAME:
        pytest.skip("MONGO_URL or DB_NAME missing")
    if not os.environ.get("RESEND_API_KEY"):
        pytest.skip("RESEND_API_KEY missing")


@pytest.fixture(scope="session")
def tag():
    return uuid.uuid4().hex[:8]


@pytest.fixture(scope="session")
def mongo_db():
    _require_env()
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


@pytest.fixture(scope="session", autouse=True)
def configure_resend_api():
    _require_env()
    resend.api_key = os.environ["RESEND_API_KEY"]


@pytest.fixture(scope="session")
def ids(tag):
    return {
        "us_np_email": f"qa.final.us.np.{tag}@nonprofitboardbuilder.com",
        "uk_np_email": f"qa.final.uk.np.{tag}@nonprofitboardbuilder.com",
        "us_app_email": f"qa.final.us.app.{tag}@nonprofitboardbuilder.com",
        "uk_app_email": f"qa.final.uk.app.{tag}@nonprofitboardbuilder.com",
    }


def _run_async(coro_factory):
    async def _runner():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            return await coro_factory(db)
        finally:
            client.close()

    return asyncio.run(_runner())


def _assessment_payload(email: str, country: str, execution_preference: str):
    state_region = "Colorado" if country == "United States" else "Greater London"
    city = "Colorado Springs" if country == "United States" else "London"
    return {
        "name": "QA Final Nonprofit Leader",
        "email": email,
        "phone": "+1 719 555 0191",
        "organization_name": "QA Final Community Nonprofit",
        "website": "https://example.org",
        "mission": "Serve families through education and community support.",
        "city": city,
        "state_region": state_region,
        "country": country,
        "annual_budget": "$250,000–$499,999",
        "most_important_board_result": "Increase board-led fundraising participation",
        "bylaws_board_size": "10",
        "current_board_size": "7",
        "active_board_members": "4",
        "inactive_board_members": "3",
        "present_board_condition": ["Some board members have stopped attending meetings."],
        "board_type": "Working board",
        "commitment_conversations": "With some of them",
        "willing_to_allow_step_down": "Yes",
        "bylaw_clarity": "Mostly clear",
        "new_board_members_needed": "3",
        "recruitment_timeline": "Within 90 days",
        "areas_carried_alone": ["Fundraising"],
        "missing_skills_networks": "Fundraising and corporate partnership experience",
        "expected_new_member_benefit": "More donor introductions and campaign support",
        "people_already_identified": "No",
        "benefits_of_joining": "Mission impact and community leadership",
        "previous_recruitment_experience": "We tried but did not receive enough qualified applicants",
        "present_fundraising_involvement": "Yes, a few of them",
        "board_support_areas": ["Making introductions"],
        "written_fundraising_strategy": "No",
        "individual_responsibilities": "No",
        "board_participation_in_planning": "No",
        "missing_fundraising_elements": ["A clear fundraising strategy"],
        "desired_result": "Consistent fundraising leadership from the board",
        "support_required": "Work with me one-on-one while I execute.",
        "execution_preference": execution_preference,
        "additional_information": "",
        "confirmation_accepted": True,
    }


def _applicant_payload(email: str, country: str):
    state_region = "Texas" if country == "United States" else "Greater London"
    city = "Austin" if country == "United States" else "London"
    postal_code = "73301" if country == "United States" else "SW1A 1AA"
    return {
        "first_name": "QA",
        "last_name": "FinalApplicant",
        "email": email,
        "phone": "+1 719 555 0117",
        "linkedin_url": "https://www.linkedin.com/in/qa-final-applicant",
        "country": country,
        "city": city,
        "state_region": state_region,
        "postal_code": postal_code,
        "job_title": "Director of Programs",
        "employer": "QA Final Employer",
        "professional_field": "Operations",
        "years_experience": "11–20 years",
        "skills": ["Fundraising", "Strategic planning"],
        "other_skill": "",
        "professional_summary": "Experienced operator and fundraiser.",
        "causes": ["Education and literacy"],
        "other_cause": "",
        "board_types": ["Governing board"],
        "participation_preferences": ["Hybrid"],
        "geographic_preferences": "Local and remote",
        "availability": "Within 30 days",
        "monthly_commitment": "5–8 hours",
        "previous_board_experience": "No, this would be my first board position.",
        "board_experience_details": "",
        "fundraising_activities": ["Making professional introductions"],
        "professional_relationships": "Introductions to local donors and business leaders.",
        "reason_for_joining": "Support strong nonprofits in meaningful ways.",
        "commitment_answer": "Yes",
        "understands_unpaid": "Yes",
        "profile_sharing_permission": True,
        "board_opportunity_consent": True,
        "privacy_accepted": True,
    }


# Assessment + email + nonprofit contact sync coverage
def test_us_nonprofit_assessment_saves_owner_email_and_execution_preference(mongo_db, ids):
    pref = "Walk With Us Through the Process — We want someone to guide us, work with us and support us while we execute the board transformation process."
    payload = _assessment_payload(ids["us_np_email"], "United States", pref)
    response = requests.post(f"{API_URL}/assessments", json=payload)
    assert response.status_code == 201
    body = response.json()

    doc = mongo_db.board_assessments.find_one({"assessment_number": body["assessment_number"]}, {"_id": 0})
    assert doc is not None
    assert doc["execution_preference"] == pref
    assert doc["owner_email_status"] == "Sent"
    assert doc["resend_sync_status"] == "Synced"
    assert isinstance(doc.get("resend_contact_id"), str) and doc["resend_contact_id"]

    contact = mongo_db.nonprofit_contacts.find_one({"email": ids["us_np_email"]}, {"_id": 0})
    assert contact is not None
    assert contact["latest_assessment_number"] == body["assessment_number"]
    assert isinstance(contact.get("created_at"), str) and contact["created_at"]
    assert isinstance(contact.get("latest_assessment_at"), str) and contact["latest_assessment_at"]
    assert contact["execution_preference"] == pref


def test_uk_nonprofit_assessment_skips_nonprofit_contacts_marketing_record(mongo_db, ids):
    pref = "Give Us the Instructions, Tools and Materials to Execute Ourselves — We want Nonprofit Board Builder to show us exactly what to do and provide the forms, materials and process required for us to reactivate, recruit and activate our board ourselves."
    payload = _assessment_payload(ids["uk_np_email"], "United Kingdom", pref)
    response = requests.post(f"{API_URL}/assessments", json=payload)
    assert response.status_code == 201
    body = response.json()

    doc = mongo_db.board_assessments.find_one({"assessment_number": body["assessment_number"]}, {"_id": 0})
    assert doc is not None
    assert doc["owner_email_status"] == "Sent"
    assert doc["resend_sync_status"] == "Not Applicable — United Kingdom"
    assert doc.get("resend_contact_id", "") == ""

    contact = mongo_db.nonprofit_contacts.find_one({"email": ids["uk_np_email"]}, {"_id": 0})
    assert contact is None


# Applicant create/upsert + GridFS + email + Resend sync coverage
def test_us_applicant_with_resume_persists_and_sends_expected_statuses(mongo_db, ids):
    payload = _applicant_payload(ids["us_app_email"], "United States")
    files = {
        "resume": (
            "qa_final_resume.pdf",
            b"%PDF-1.4\n% QA FINAL\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF",
            "application/pdf",
        )
    }
    response = requests.post(f"{API_URL}/applicants", data={"payload": json.dumps(payload)}, files=files)
    assert response.status_code == 201
    body = response.json()
    assert body["created"] is True

    doc = mongo_db.board_applicants.find_one({"email": ids["us_app_email"]}, {"_id": 0})
    assert doc is not None
    assert isinstance(doc.get("resume_file_id"), str) and doc["resume_file_id"]
    assert doc["owner_notification_status"] == "Sent"
    assert doc["resend_segment_status"] == "Synced"
    assert doc["confirmation_email_status"] == "Sent"
    assert isinstance(doc.get("confirmation_email_id"), str) and doc["confirmation_email_id"]

    grid_doc = mongo_db["applicant_resumes.files"].find_one({"metadata.applicant_id": doc["applicant_id"]})
    assert grid_doc is not None


def test_duplicate_us_applicant_preserves_id_created_at_and_resume_without_second_confirmation(mongo_db, ids):
    before = mongo_db.board_applicants.find_one({"email": ids["us_app_email"]}, {"_id": 0})
    assert before is not None
    before_confirmation_id = before.get("confirmation_email_id", "")

    payload = _applicant_payload(ids["us_app_email"], "United States")
    payload["job_title"] = "Chief Operating Officer"
    response = requests.post(f"{API_URL}/applicants", data={"payload": json.dumps(payload)})
    assert response.status_code == 201
    body = response.json()
    assert body["created"] is False

    after = mongo_db.board_applicants.find_one({"email": ids["us_app_email"]}, {"_id": 0})
    assert after is not None
    assert after["applicant_id"] == before["applicant_id"]
    assert after["created_at"] == before["created_at"]
    assert after["updated_at"] != before["updated_at"]
    assert after["resume_file_id"] == before["resume_file_id"]
    assert after["job_title"] == "Chief Operating Officer"
    assert after["confirmation_email_status"] == "Not Sent — Existing Profile"
    assert after.get("confirmation_email_id", "") == before_confirmation_id
    assert mongo_db.board_applicants.count_documents({"email": ids["us_app_email"]}) == 1


def test_uk_applicant_saves_and_syncs_to_resend_topic_segment(mongo_db, ids):
    payload = _applicant_payload(ids["uk_app_email"], "United Kingdom")
    response = requests.post(f"{API_URL}/applicants", data={"payload": json.dumps(payload)})
    assert response.status_code == 201

    doc = mongo_db.board_applicants.find_one({"email": ids["uk_app_email"]}, {"_id": 0})
    assert doc is not None
    assert doc["owner_notification_status"] == "Sent"
    assert doc["confirmation_email_status"] == "Sent"
    assert doc["resend_segment_status"] == "Synced"
    assert isinstance(doc.get("resend_contact_id"), str) and doc["resend_contact_id"]


# Existing one-time applicant sync idempotency coverage
def test_existing_sync_run_completed_and_idempotent(mongo_db):
    from resend_service import sync_existing_applicants_once

    run = mongo_db.automation_runs.find_one({"run_key": "existing_board_applicant_resend_sync_v1"}, {"_id": 0})
    assert run is not None
    assert run["status"] == "Completed"
    assert run["processed"] == 13
    assert run["synced"] == 13
    assert run["failed"] == 0

    sample = mongo_db.board_applicants.find_one({}, {"_id": 0})
    assert sample is not None
    before = {
        "applicant_id": sample["applicant_id"],
        "created_at": sample["created_at"],
        "resume_file_id": sample.get("resume_file_id", ""),
        "confirmation_email_status": sample.get("confirmation_email_status", ""),
    }

    result = _run_async(lambda db: sync_existing_applicants_once(db))
    assert result == {"processed": 13, "synced": 13, "failed": 0}

    after = mongo_db.board_applicants.find_one({"applicant_id": before["applicant_id"]}, {"_id": 0})
    assert after is not None
    assert after["created_at"] == before["created_at"]
    assert after.get("resume_file_id", "") == before["resume_file_id"]
    assert after.get("confirmation_email_status", "") == before["confirmation_email_status"]


# Resend resource and config coverage
def test_final_segments_topics_and_env_ids_and_obsolete_absent():
    async def _verify():
        segments = await resend.Segments.list_async({"limit": 100})
        topics = await resend.Topics.list_async({"limit": 100})
        seg_rows = getattr(segments, "data", None) or segments.get("data", [])
        topic_rows = getattr(topics, "data", None) or topics.get("data", [])
        seg_by_id = {getattr(r, "id", None) or r.get("id"): getattr(r, "name", None) or r.get("name") for r in seg_rows}
        topic_by_id = {getattr(r, "id", None) or r.get("id"): getattr(r, "name", None) or r.get("name") for r in topic_rows}
        segment_names = [getattr(r, "name", None) or r.get("name") for r in seg_rows]

        assert seg_by_id.get(os.environ["RESEND_NONPROFIT_LEADERS_SEGMENT_ID"]) == "Nonprofit Board Builder — Nonprofit Leaders"
        assert seg_by_id.get(os.environ["RESEND_BOARD_APPLICANTS_SEGMENT_ID"]) == "Nonprofit Board Builder — Board Applicants"
        assert topic_by_id.get(os.environ["RESEND_BOARD_BUILDING_TOPIC_ID"]) == "Board Building Opportunities for Nonprofits"
        assert topic_by_id.get(os.environ["RESEND_BOARD_OPPORTUNITIES_TOPIC_ID"]) == "Nonprofit Board Opportunities"

        assert "Nonprofit Board Builder — Nonprofit Weekly No Action" not in segment_names
        assert "Nonprofit Board Builder — Applicant Weekly No Action" not in segment_names

    asyncio.run(_verify())


def test_weekly_sales_broadcast_owner_only_segment_idempotent_and_content_rules(mongo_db, tag):
    from automation_service import SALES_EMAILS, sales_email_html, send_weekly_nonprofit_sales_email

    temp_name = f"NBB TEMP TEST SEGMENT FINAL {tag}"

    async def _setup_and_send(db):
        segments = await resend.Segments.list_async({"limit": 100})
        rows = getattr(segments, "data", None) or segments.get("data", [])
        temp_id = ""
        for row in rows:
            row_name = getattr(row, "name", None) or row.get("name")
            if row_name == temp_name:
                temp_id = getattr(row, "id", None) or row.get("id")
                break
        if not temp_id:
            created = await resend.Segments.create_async({"name": temp_name})
            temp_id = getattr(created, "id", None) or created.get("id")

        try:
            await resend.Contacts.get_async(email=OWNER_EMAIL)
        except Exception:
            await resend.Contacts.create_async(
                {"email": OWNER_EMAIL, "first_name": "Rooney", "last_name": "Owner", "unsubscribed": False, "properties": {}}
            )
        await resend.ContactSegments.add_async({"segment_id": temp_id, "email": OWNER_EMAIL})

        reference = datetime.now(timezone.utc) + timedelta(weeks=60)
        first = await send_weekly_nonprofit_sales_email(db, reference=reference, segment_override=temp_id, send=True)
        second = await send_weekly_nonprofit_sales_email(db, reference=reference, segment_override=temp_id, send=True)

        number = ((reference.isocalendar().week - 1) % 4) + 1
        html = sales_email_html(SALES_EMAILS[number])
        return temp_id, first, second, html

    temp_segment_id, first, second, generated_html = _run_async(_setup_and_send)

    assert temp_segment_id != os.environ["RESEND_NONPROFIT_LEADERS_SEGMENT_ID"]
    assert first["resend_broadcast_id"] == second["resend_broadcast_id"]
    assert first["audience"] == "Nonprofit Board Builder — Nonprofit Leaders"
    assert first["send_status"] == "Sent"
    assert isinstance(first.get("send_date_time"), str) and first["send_date_time"]
    assert isinstance(first.get("resend_broadcast_id"), str) and first["resend_broadcast_id"]

    persisted = mongo_db.weekly_sales_emails.find_one(
        {
            "audience": first["audience"],
            "campaign_theme": first["campaign_theme"],
            "scheduled_week": first["scheduled_week"],
        },
        {"_id": 0},
    )
    assert persisted is not None
    assert persisted["resend_broadcast_id"] == first["resend_broadcast_id"]

    broadcast = asyncio.run(resend.Broadcasts.get_async(first["resend_broadcast_id"]))
    sent_from = getattr(broadcast, "from", None) or broadcast.get("from")
    sent_html = getattr(broadcast, "html", None) or broadcast.get("html")
    sent_subject = getattr(broadcast, "subject", None) or broadcast.get("subject")

    assert sent_from == os.environ["NONPROFIT_SENDER"]
    assert isinstance(sent_subject, str) and sent_subject
    assert isinstance(sent_html, str) and sent_html

    for html_block in (generated_html, sent_html):
        lowered = html_block.lower()
        assert "max-width:600px" in html_block
        assert "background:#ffffff" in lowered or "background: #ffffff" in lowered
        assert "color:#000000" in lowered
        assert "font-size:18px" in lowered
        assert "font-size:29px" in lowered
        assert "font-size:22px" in lowered
        assert "i am ready — your full name — organization name" in lowered
        assert "+1 719-428-5598" in html_block
        assert "{{{resend_unsubscribe_url}}}" in lowered
        assert "href=\"{{{resend_unsubscribe_url}}}\"" in lowered

        assert "report" not in lowered
        assert "applicant" not in lowered
        assert "network" not in lowered
        assert "platform" not in lowered
        assert "signup" not in lowered
        assert "statistic" not in lowered
        assert "sms" not in lowered
        assert "emergent" not in lowered
        assert "preview" not in lowered
        assert "tracked" not in lowered
        assert "{{{resend_preferences_url}}}" not in lowered


def test_scheduler_and_nonprofit_only_config_and_no_tracked_routes_in_code():
    assert os.environ.get("NONPROFIT_WEEKLY_EMAIL_ENABLED", "").lower() == "false"
    assert os.environ.get("NONPROFIT_WEEKLY_EMAIL_DAY") == "Wednesday"
    assert os.environ.get("NONPROFIT_WEEKLY_EMAIL_TIME") == "10:00"
    assert os.environ.get("NONPROFIT_WEEKLY_EMAIL_TIMEZONE") == "America/New_York"

    applicant_related_weekly = [
        key for key in os.environ.keys() if "APPLICANT_WEEKLY" in key or "MONTHLY" in key
    ]
    assert applicant_related_weekly == []

    routes_file = Path("/app/backend/applicant_routes.py").read_text(encoding="utf-8")
    assert "tracked-actions" not in routes_file
    assert "no-action" not in routes_file


def test_privacy_policy_contains_required_commitments():
    page = Path("/app/frontend/src/pages/LegalPage.jsx").read_text(encoding="utf-8")
    required_phrases = [
        "United States nonprofit contacts may receive weekly board-building emails.",
        "United States and United Kingdom applicants may receive genuine board-opportunity emails",
        "Board applicants do not receive automatic weekly or monthly emails.",
        "Profiles may be shared with nonprofit organizations only for legitimate board-opportunity consideration",
        "Resend processes email contact details",
        "unsubscribe",
        "request correction or deletion",
        "not sold",
    ]
    for phrase in required_phrases:
        assert phrase in page
