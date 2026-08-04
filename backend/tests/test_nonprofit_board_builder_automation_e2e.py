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

sys.path.append(str(Path(__file__).resolve().parents[1]))

from automation_service import (
    applicant_email,
    applicant_subject,
    create_weekly_report,
    nonprofit_email,
    nonprofit_subject,
    process_no_action,
    token_hash,
)
from resend_service import send_automation_error


load_dotenv(Path("/app/frontend/.env"))
load_dotenv(Path("/app/backend/.env"))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API_URL = f"{BASE_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL", "")
DB_NAME = os.environ.get("DB_NAME", "")
OWNER_EMAIL = os.environ.get("OWNER_NOTIFICATION_EMAIL", "").strip().lower()

TEST_TAG = uuid.uuid4().hex[:8]
ASSESS_TRUE_EMAIL = f"qa.np.true.{TEST_TAG}@nonprofitboardbuilder.com"
ASSESS_FALSE_EMAIL = f"qa.np.false.{TEST_TAG}@nonprofitboardbuilder.com"
APPLICANT_EMAIL = f"qa.applicant.{TEST_TAG}@nonprofitboardbuilder.com"
NO_ACTION_NONPROFIT_EMAIL = f"qa.np.noaction.{TEST_TAG}@nonprofitboardbuilder.com"
NO_ACTION_APPLICANT_EMAIL = f"qa.app.noaction.{TEST_TAG}@nonprofitboardbuilder.com"
TEMP_SEGMENT_NAME = f"NBB TEMP TEST SEGMENT {TEST_TAG}"


def _ensure_required_env():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL missing")
    if not MONGO_URL or not DB_NAME:
        pytest.skip("MONGO_URL or DB_NAME missing")
    if not OWNER_EMAIL:
        pytest.skip("OWNER_NOTIFICATION_EMAIL missing")


@pytest.fixture(scope="session")
def mongo_db():
    _ensure_required_env()
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


@pytest.fixture(scope="session")
def resend_key():
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        pytest.skip("RESEND_API_KEY missing")
    resend.api_key = key
    return key


def run_with_async_db(async_callable):
    async def _runner():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            return await async_callable(db)
        finally:
            client.close()

    return asyncio.run(_runner())


def _assessment_payload(email: str, email_permission: bool, execution_preference: str):
    return {
        "name": "QA Nonprofit Leader",
        "email": email,
        "phone": "+1 302 555 0102",
        "organization_name": "QA Test Nonprofit",
        "website": "https://example.org",
        "mission": "Serve local families and youth.",
        "city": "Middletown",
        "state_region": "Delaware",
        "country": "United States",
        "annual_budget": "$250,000 - $499,999",
        "most_important_board_result": "More fundraising participation",
        "bylaws_board_size": "10",
        "current_board_size": "7",
        "active_board_members": "4",
        "inactive_board_members": "3",
        "present_board_condition": ["Some members are active"],
        "board_type": "Working board",
        "commitment_conversations": "Some members",
        "willing_to_allow_step_down": "Yes",
        "bylaw_clarity": "Mostly clear",
        "new_board_members_needed": "3",
        "recruitment_timeline": "Within 90 days",
        "areas_carried_alone": ["Fundraising"],
        "missing_skills_networks": "Fundraising and legal expertise",
        "expected_new_member_benefit": "Access to donor networks",
        "people_already_identified": "No",
        "benefits_of_joining": "Mission impact and leadership",
        "previous_recruitment_experience": "Limited success",
        "present_fundraising_involvement": "Yes, a few of them",
        "board_support_areas": ["Making introductions"],
        "written_fundraising_strategy": "No",
        "individual_responsibilities": "No",
        "board_participation_in_planning": "No",
        "missing_fundraising_elements": ["A clear fundraising strategy"],
        "desired_result": "Reliable donor growth",
        "support_required": "Work with me one-on-one while I execute.",
        "execution_preference": execution_preference,
        "additional_information": "",
        "confirmation_accepted": True,
        "email_permission": email_permission,
    }


def _applicant_payload(email: str, offers: bool):
    return {
        "first_name": "QA",
        "last_name": "Applicant",
        "email": email,
        "phone": "+1 415 555 0101",
        "linkedin_url": "https://www.linkedin.com/in/qa-board-applicant",
        "country": "United States",
        "city": "Austin",
        "state_region": "Texas",
        "postal_code": "73301",
        "job_title": "Director of Operations",
        "employer": "QA Employer Inc",
        "professional_field": "Operations",
        "years_experience": "11–20 years",
        "skills": ["Fundraising", "Operations"],
        "other_skill": "",
        "professional_summary": "Experienced professional supporting nonprofit growth.",
        "causes": ["Education and literacy"],
        "other_cause": "",
        "board_types": ["Governing board"],
        "participation_preferences": ["Hybrid"],
        "geographic_preferences": "Texas and remote",
        "availability": "Within 30 days",
        "monthly_commitment": "5–8 hours",
        "previous_board_experience": "No, this would be my first board position.",
        "board_experience_details": "",
        "fundraising_activities": ["Making professional introductions"],
        "professional_relationships": "Introductions to local leaders.",
        "reason_for_joining": "Serve mission-driven organizations.",
        "commitment_answer": "Yes",
        "understands_unpaid": "Yes",
        "profile_sharing_permission": True,
        "board_opportunity_consent": True,
        "other_offers_consent": offers,
        "privacy_accepted": True,
    }


def _value(item, key):
    return item.get(key) if isinstance(item, dict) else getattr(item, key, None)


@pytest.fixture(scope="session")
def temp_segment_id(resend_key):
    # Resend infrastructure coverage: create/reuse a dedicated owner-only test segment.
    async def _get_or_create():
        listed = await resend.Segments.list_async({"limit": 100})
        for row in _value(listed, "data") or []:
            if _value(row, "name") == TEMP_SEGMENT_NAME:
                return _value(row, "id")
        created = await resend.Segments.create_async({"name": TEMP_SEGMENT_NAME})
        return _value(created, "id")

    segment_id = asyncio.run(_get_or_create())
    assert isinstance(segment_id, str) and segment_id
    return segment_id


def test_assessment_with_email_permission_true_and_owner_email_sent(mongo_db):
    # Assessment module coverage: required execution_preference + consented nonprofit contact sync.
    payload = _assessment_payload(
        ASSESS_TRUE_EMAIL,
        True,
        "Walk With Us Through the Process — We want someone to guide us, work with us and support us while we execute the board transformation process.",
    )
    response = requests.post(f"{API_URL}/assessments", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["submitted_email"] == ASSESS_TRUE_EMAIL
    assert body["email_sent"] is True

    assessment = mongo_db.board_assessments.find_one({"assessment_number": body["assessment_number"]}, {"_id": 0})
    assert assessment is not None
    assert assessment["execution_preference"] == payload["execution_preference"]
    assert assessment["email_permission"] is True
    assert isinstance(assessment.get("email_permission_at"), str) and assessment["email_permission_at"]
    assert assessment.get("email_permission_source") == "/"
    assert assessment.get("owner_email_status") == "Sent"
    assert assessment.get("resend_sync_status") == "Synced"
    assert isinstance(assessment.get("resend_contact_id"), str) and assessment["resend_contact_id"]

    contact = mongo_db.nonprofit_contacts.find_one({"email": ASSESS_TRUE_EMAIL}, {"_id": 0})
    assert contact is not None
    assert contact["email_permission"] is True
    assert contact["latest_assessment_number"] == body["assessment_number"]
    assert isinstance(contact.get("created_at"), str) and contact["created_at"]
    assert isinstance(contact.get("latest_assessment_at"), str) and contact["latest_assessment_at"]
    assert contact.get("resend_sync_status") == "Synced"


def test_assessment_without_permission_not_requested_and_no_contact(mongo_db):
    # Assessment negative-consent coverage: save/email owner but never marketing sync.
    payload = _assessment_payload(
        ASSESS_FALSE_EMAIL,
        False,
        "Give Us the Instructions, Tools and Materials to Execute Ourselves — We want Nonprofit Board Builder to show us exactly what to do and provide the forms, materials and process we need to reactivate, recruit and activate our board ourselves.",
    )
    response = requests.post(f"{API_URL}/assessments", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["submitted_email"] == ASSESS_FALSE_EMAIL
    assert body["email_sent"] is True

    assessment = mongo_db.board_assessments.find_one({"assessment_number": body["assessment_number"]}, {"_id": 0})
    assert assessment is not None
    assert assessment["email_permission"] is False
    assert assessment.get("resend_sync_status") == "Not Requested"
    assert assessment.get("owner_email_status") == "Sent"

    contact = mongo_db.nonprofit_contacts.find_one({"email": ASSESS_FALSE_EMAIL}, {"_id": 0})
    assert contact is None


def test_applicant_create_and_confirmation_and_resend_sync(mongo_db):
    # Applicant module coverage: required board-opportunity consent + optional resources consent separation.
    payload = _applicant_payload(APPLICANT_EMAIL, offers=True)
    response = requests.post(f"{API_URL}/applicants", data={"payload": json.dumps(payload)})
    assert response.status_code == 201
    body = response.json()
    assert body["created"] is True
    assert body["email"] == APPLICANT_EMAIL

    doc = mongo_db.board_applicants.find_one({"email": APPLICANT_EMAIL}, {"_id": 0})
    assert doc is not None
    assert doc["board_opportunity_consent"] is True
    assert doc["other_offers_consent"] is True
    assert isinstance(doc.get("consent_at"), str) and doc["consent_at"]
    assert doc.get("source_page") == "/join-a-board"
    assert doc.get("resend_segment_status") == "Synced"
    assert doc.get("confirmation_email_status") == "Sent"
    assert isinstance(doc.get("resend_contact_id"), str) and doc["resend_contact_id"]


def test_applicant_duplicate_email_updates_without_duplicate_record(mongo_db):
    # Applicant upsert coverage: preserve applicant_id/created_at and update profile fields.
    before = mongo_db.board_applicants.find_one({"email": APPLICANT_EMAIL}, {"_id": 0})
    assert before is not None

    payload = _applicant_payload(APPLICANT_EMAIL, offers=False)
    payload["job_title"] = "Chief Operating Officer"
    response = requests.post(f"{API_URL}/applicants", data={"payload": json.dumps(payload)})
    assert response.status_code == 201
    body = response.json()
    assert body["created"] is False
    assert body["applicant_id"] == before["applicant_id"]

    after = mongo_db.board_applicants.find_one({"email": APPLICANT_EMAIL}, {"_id": 0})
    assert after is not None
    assert after["applicant_id"] == before["applicant_id"]
    assert after["created_at"] == before["created_at"]
    assert after["updated_at"] != before["updated_at"]
    assert after["job_title"] == "Chief Operating Officer"
    assert after["other_offers_consent"] is False
    assert mongo_db.board_applicants.count_documents({"email": APPLICANT_EMAIL}) == 1


def test_resend_segments_topics_and_env_ids_match(resend_key):
    # Resend resource coverage: exact production segment/topic names + env-id consistency.
    async def _verify():
        segments = await resend.Segments.list_async({"limit": 100})
        topics = await resend.Topics.list_async({"limit": 100})
        seg_by_id = {_value(row, "id"): _value(row, "name") for row in (_value(segments, "data") or [])}
        top_by_id = {_value(row, "id"): _value(row, "name") for row in (_value(topics, "data") or [])}

        assert seg_by_id.get(os.environ["RESEND_SEGMENT_NONPROFIT_LEADERS_ID"]) == "Nonprofit Board Builder — Nonprofit Leaders"
        assert seg_by_id.get(os.environ["RESEND_SEGMENT_BOARD_APPLICANTS_ID"]) == "Nonprofit Board Builder — Board Applicants"
        assert seg_by_id.get(os.environ["RESEND_SEGMENT_NONPROFIT_NO_ACTION_ID"]) == "Nonprofit Board Builder — Nonprofit Weekly No Action"
        assert seg_by_id.get(os.environ["RESEND_SEGMENT_APPLICANT_NO_ACTION_ID"]) == "Nonprofit Board Builder — Applicant Weekly No Action"

        assert top_by_id.get(os.environ["RESEND_TOPIC_NONPROFIT_UPDATES_ID"]) == "Board Building Updates for Nonprofits"
        assert top_by_id.get(os.environ["RESEND_TOPIC_APPLICANT_UPDATES_ID"]) == "Board Opportunities and Applicant Updates"
        assert top_by_id.get(os.environ["RESEND_TOPIC_APPLICANT_RESOURCES_ID"]) == "Board Applicant Resources and Offers"

    asyncio.run(_verify())
    assert os.environ.get("NONPROFIT_WEEKLY_REPORT_ENABLED", "").lower() == "false"
    assert os.environ.get("APPLICANT_WEEKLY_REPORT_ENABLED", "").lower() == "false"


def test_temp_test_segment_owner_only_setup(resend_key, temp_segment_id):
    # Broadcast safety coverage: ensure tests target dedicated owner-only segment, never live segments.
    async def _upsert_owner_and_add_to_segment():
        try:
            await resend.Contacts.get_async(email=OWNER_EMAIL)
        except Exception:
            await resend.Contacts.create_async(
                {"email": OWNER_EMAIL, "first_name": "Rooney", "last_name": "Owner", "unsubscribed": False, "properties": {}}
            )
        await resend.ContactSegments.add_async({"segment_id": temp_segment_id, "email": OWNER_EMAIL})

    asyncio.run(_upsert_owner_and_add_to_segment())
    assert temp_segment_id not in {
        os.environ["RESEND_SEGMENT_NONPROFIT_LEADERS_ID"],
        os.environ["RESEND_SEGMENT_BOARD_APPLICANTS_ID"],
    }


def test_nonprofit_weekly_report_broadcast_idempotent_and_tracked_action(mongo_db, temp_segment_id):
    # Nonprofit weekly automation coverage: aggregate report creation, dedupe, tracked link click status.
    import automation_service

    token = f"np-token-{TEST_TAG}-abcdefghijklmnopqrstuvwxyz"
    original_secure_token = automation_service.secure_token
    automation_service.secure_token = lambda: token
    reference = datetime.now(timezone.utc) + timedelta(days=int(TEST_TAG[:2], 16) + 120)
    recipients = [{"email": OWNER_EMAIL, "name": "Rooney Owner", "organization_name": "NBB", "resend_contact_id": ""}]
    try:
        async def _create_reports(db):
            first_local = await create_weekly_report(
                db,
                "nonprofit",
                reference=reference,
                segment_override=temp_segment_id,
                recipients_override=recipients,
                send=True,
            )
            second_local = await create_weekly_report(
                db,
                "nonprofit",
                reference=reference,
                segment_override=temp_segment_id,
                recipients_override=recipients,
                send=True,
            )
            return first_local, second_local

        first, second = run_with_async_db(_create_reports)
    finally:
        automation_service.secure_token = original_secure_token

    assert first["report_id"] == second["report_id"]
    assert first.get("resend_broadcast_id") == second.get("resend_broadcast_id")
    assert first.get("send_status") == "Sent"
    assert isinstance(first.get("resend_broadcast_id"), str) and first["resend_broadcast_id"]

    start = datetime.fromisoformat(first["reporting_period_start"])
    end = datetime.fromisoformat(first["reporting_period_end"])
    recent_count = mongo_db.board_applicants.count_documents({"created_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}})
    assert first["new_applicant_count"] == recent_count

    body = nonprofit_email({
        "new_applicant_count": first["new_applicant_count"],
        "fundraising_applicant_count": first["fundraising_applicant_count"],
        "immediately_available_applicant_count": first["immediately_available_applicant_count"],
        "total_active_applicant_count": first["total_active_applicant_count"],
    })
    assert nonprofit_subject(first["fundraising_applicant_count"])
    assert "{{{RESEND_UNSUBSCRIBE_URL}}}" in body
    assert "{{{RESEND_PREFERENCES_URL}}}" in body
    assert "{{{nonprofit_action_url}}}" in body

    tracked = requests.post(
        f"{API_URL}/tracked-actions/board-transformation-ready",
        json={"token": token},
    )
    assert tracked.status_code == 200
    tracked_data = tracked.json()
    assert tracked_data["phone"] == "+17194285598"
    assert tracked_data["status"] == "Ready for Board Transformation"
    assert tracked_data["message"] == "I am ready — Rooney Owner — NBB"

    recipient = mongo_db.weekly_report_recipients.find_one(
        {"report_id": first["report_id"], "email": OWNER_EMAIL}, {"_id": 0}
    )
    assert recipient is not None
    assert recipient["action_clicked"] is True
    assert recipient["no_action_status"] == "Removed"


def test_nonprofit_no_action_adds_only_unclicked_over_72h(mongo_db, temp_segment_id):
    # Nonprofit no-action coverage: add only unclicked contacts to nonprofit no-action segment.
    report = mongo_db.weekly_reports.find_one({"report_type": "nonprofit"}, sort=[("created_at", -1)], projection={"_id": 0})
    assert report is not None

    resend.api_key = os.environ["RESEND_API_KEY"]

    async def _prepare_contact():
        try:
            await resend.Contacts.get_async(email=NO_ACTION_NONPROFIT_EMAIL)
        except Exception:
            await resend.Contacts.create_async(
                {
                    "email": NO_ACTION_NONPROFIT_EMAIL,
                    "first_name": "No",
                    "last_name": "Action",
                    "unsubscribed": False,
                    "properties": {},
                }
            )
        await resend.ContactSegments.add_async({"segment_id": temp_segment_id, "email": NO_ACTION_NONPROFIT_EMAIL})

    asyncio.run(_prepare_contact())

    mongo_db.weekly_report_recipients.update_one(
        {"report_id": report["report_id"], "email": NO_ACTION_NONPROFIT_EMAIL, "report_type": "nonprofit"},
        {
            "$set": {
                "report_id": report["report_id"],
                "report_type": "nonprofit",
                "email": NO_ACTION_NONPROFIT_EMAIL,
                "resend_contact_id": "",
                "full_name": "No Action Contact",
                "organization_name": "QA Nonprofit",
                "token_hash": token_hash(f"np-noaction-{TEST_TAG}"),
                "eligible_at": datetime.now(timezone.utc).isoformat(),
                "action_clicked": False,
                "no_action_status": "Waiting",
            }
        },
        upsert=True,
    )
    mongo_db.weekly_reports.update_one(
        {"report_id": report["report_id"]},
        {
            "$set": {
                "sent_at": (datetime.now(timezone.utc) - timedelta(hours=73)).isoformat(),
                "send_status": "Sent",
                "no_action_processing_status": "Waiting",
            }
        },
    )

    async def _process(db):
        return await process_no_action(db, reference=datetime.now(timezone.utc))

    processed = run_with_async_db(_process)
    assert processed >= 1

    updated_recipient = mongo_db.weekly_report_recipients.find_one(
        {"report_id": report["report_id"], "email": NO_ACTION_NONPROFIT_EMAIL}, {"_id": 0}
    )
    assert updated_recipient is not None
    assert updated_recipient["no_action_status"] == "Added"


def test_applicant_weekly_report_broadcast_idempotent_and_tracked_action(mongo_db, temp_segment_id):
    # Applicant weekly automation coverage: aggregate report creation, dedupe, tracked link click status.
    import automation_service

    token = f"app-token-{TEST_TAG}-abcdefghijklmnopqrstuvwxyz"
    original_secure_token = automation_service.secure_token
    automation_service.secure_token = lambda: token
    reference = datetime.now(timezone.utc) + timedelta(days=int(TEST_TAG[:2], 16) + 121)
    recipients = [{"email": OWNER_EMAIL, "first_name": "Rooney", "last_name": "Owner", "resend_contact_id": ""}]
    try:
        async def _create_reports(db):
            first_local = await create_weekly_report(
                db,
                "applicant",
                reference=reference,
                segment_override=temp_segment_id,
                recipients_override=recipients,
                send=True,
            )
            second_local = await create_weekly_report(
                db,
                "applicant",
                reference=reference,
                segment_override=temp_segment_id,
                recipients_override=recipients,
                send=True,
            )
            return first_local, second_local

        first, second = run_with_async_db(_create_reports)
    finally:
        automation_service.secure_token = original_secure_token

    assert first["report_id"] == second["report_id"]
    assert first.get("resend_broadcast_id") == second.get("resend_broadcast_id")
    assert first.get("send_status") == "Sent"
    assert isinstance(first.get("resend_broadcast_id"), str) and first["resend_broadcast_id"]

    start = datetime.fromisoformat(first["reporting_period_start"])
    end = datetime.fromisoformat(first["reporting_period_end"])
    assessment_count = mongo_db.board_assessments.count_documents({"submitted_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}})
    assert first["new_board_assessment_count"] == assessment_count

    body = applicant_email({
        "new_board_assessment_count": first["new_board_assessment_count"],
        "recruiting_nonprofit_count": first["recruiting_nonprofit_count"],
        "requested_board_member_count": first["requested_board_member_count"],
        "fundraising_need_count": first["fundraising_need_count"],
    })
    assert applicant_subject(first["recruiting_nonprofit_count"])
    assert "{{{RESEND_UNSUBSCRIBE_URL}}}" in body
    assert "{{{RESEND_PREFERENCES_URL}}}" in body
    assert "{{{applicant_action_url}}}" in body

    tracked = requests.post(
        f"{API_URL}/tracked-actions/available-to-serve",
        json={"token": token},
    )
    assert tracked.status_code == 200
    tracked_data = tracked.json()
    assert tracked_data["phone"] == "+17194285598"
    assert tracked_data["status"] == "Available to Serve"
    assert tracked_data["message"] == "Available to Serve — Rooney Owner"

    recipient = mongo_db.weekly_report_recipients.find_one(
        {"report_id": first["report_id"], "email": OWNER_EMAIL}, {"_id": 0}
    )
    assert recipient is not None
    assert recipient["action_clicked"] is True
    assert recipient["no_action_status"] == "Removed"


def test_applicant_no_action_adds_only_unclicked_over_72h(mongo_db, temp_segment_id):
    # Applicant no-action coverage: add only unclicked contacts to applicant no-action segment.
    report = mongo_db.weekly_reports.find_one({"report_type": "applicant"}, sort=[("created_at", -1)], projection={"_id": 0})
    assert report is not None

    resend.api_key = os.environ["RESEND_API_KEY"]

    async def _prepare_contact():
        try:
            await resend.Contacts.get_async(email=NO_ACTION_APPLICANT_EMAIL)
        except Exception:
            await resend.Contacts.create_async(
                {
                    "email": NO_ACTION_APPLICANT_EMAIL,
                    "first_name": "No",
                    "last_name": "Action",
                    "unsubscribed": False,
                    "properties": {},
                }
            )
        await resend.ContactSegments.add_async({"segment_id": temp_segment_id, "email": NO_ACTION_APPLICANT_EMAIL})

    asyncio.run(_prepare_contact())

    mongo_db.weekly_report_recipients.update_one(
        {"report_id": report["report_id"], "email": NO_ACTION_APPLICANT_EMAIL, "report_type": "applicant"},
        {
            "$set": {
                "report_id": report["report_id"],
                "report_type": "applicant",
                "email": NO_ACTION_APPLICANT_EMAIL,
                "resend_contact_id": "",
                "full_name": "No Action Applicant",
                "organization_name": "",
                "token_hash": token_hash(f"app-noaction-{TEST_TAG}"),
                "eligible_at": datetime.now(timezone.utc).isoformat(),
                "action_clicked": False,
                "no_action_status": "Waiting",
            }
        },
        upsert=True,
    )
    mongo_db.weekly_reports.update_one(
        {"report_id": report["report_id"]},
        {
            "$set": {
                "sent_at": (datetime.now(timezone.utc) - timedelta(hours=73)).isoformat(),
                "send_status": "Sent",
                "no_action_processing_status": "Waiting",
            }
        },
    )

    async def _process(db):
        return await process_no_action(db, reference=datetime.now(timezone.utc))

    processed = run_with_async_db(_process)
    assert processed >= 1

    updated_recipient = mongo_db.weekly_report_recipients.find_one(
        {"report_id": report["report_id"], "email": NO_ACTION_APPLICANT_EMAIL}, {"_id": 0}
    )
    assert updated_recipient is not None
    assert updated_recipient["no_action_status"] == "Added"


def test_weekly_report_shape_failure_dedupe_and_privacy_page_content(mongo_db):
    # Metadata/privacy coverage: unique report shape, deduped automation errors, and privacy-policy assertions.
    nonprofit_report = mongo_db.weekly_reports.find_one({"report_type": "nonprofit"}, sort=[("created_at", -1)], projection={"_id": 0})
    applicant_report = mongo_db.weekly_reports.find_one({"report_type": "applicant"}, sort=[("created_at", -1)], projection={"_id": 0})
    assert nonprofit_report is not None and applicant_report is not None

    required_fields = {
        "report_id", "report_type", "period_start_key", "reporting_period_start", "reporting_period_end",
        "resend_broadcast_id", "send_status", "sent_at", "no_action_processing_status", "created_at",
    }
    for report in (nonprofit_report, applicant_report):
        assert required_fields.issubset(report.keys())
        assert report["report_type"] in {"nonprofit", "applicant"}
        assert isinstance(report["period_start_key"], str) and report["period_start_key"]

    assert mongo_db.weekly_reports.count_documents({
        "report_type": nonprofit_report["report_type"],
        "period_start_key": nonprofit_report["period_start_key"],
    }) == 1

    # Deliberately trigger dedupe path with same failure_key twice.
    async def _dedupe(db):
        await send_automation_error(
            db,
            failure_key=f"qa-dedupe-{TEST_TAG}",
            automation="QA Dedupe",
            contact_or_report_type="qa",
            error="first",
            submission_saved=True,
            email_sent=False,
            corrective_action="none",
        )
        await send_automation_error(
            db,
            failure_key=f"qa-dedupe-{TEST_TAG}",
            automation="QA Dedupe",
            contact_or_report_type="qa",
            error="second",
            submission_saved=True,
            email_sent=False,
            corrective_action="none",
        )

    run_with_async_db(_dedupe)
    assert mongo_db.automation_errors.count_documents({"failure_key": f"qa-dedupe-{TEST_TAG}"}) == 1

    page = Path("/app/frontend/src/pages/LegalPage.jsx").read_text(encoding="utf-8")
    assert "Information We Collect" in page
    assert "exact consent timestamps" in page
    assert "Weekly Email Reports" in page
    assert "Aggregate Reporting" in page
    assert "tracked" in page.lower()
    assert "unsubscribe" in page.lower()
    assert "Resend" in page
    assert "not sold" in page
