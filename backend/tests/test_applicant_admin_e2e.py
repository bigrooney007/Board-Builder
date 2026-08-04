import os
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv(Path("/app/frontend/.env"))
load_dotenv(Path("/app/backend/.env"))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
MONGO_URL = os.environ.get("MONGO_URL", "")
DB_NAME = os.environ.get("DB_NAME", "")


@pytest.fixture(scope="session")
def api_url():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL missing")
    return f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def mongo_db():
    if not MONGO_URL or not DB_NAME:
        pytest.skip("MONGO_URL or DB_NAME missing")
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


@pytest.fixture
def session_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# Auth module coverage: seeded admin hash/indexes, login, cookie auth, lockout, CORS credentials.
def test_admin_seed_hash_and_indexes(mongo_db):
    user = mongo_db.users.find_one({"email": ADMIN_EMAIL, "role": "admin"})
    assert user is not None
    assert isinstance(user.get("password_hash"), str)
    assert user["password_hash"].startswith("$2b$")

    user_indexes = mongo_db.users.index_information()
    login_indexes = mongo_db.login_attempts.index_information()
    assert any(idx.get("key") == [("email", 1)] and idx.get("unique") for idx in user_indexes.values())
    assert any(idx.get("key") == [("identifier", 1)] and idx.get("unique") for idx in login_indexes.values())


def test_auth_me_requires_auth(api_url, session_client):
    response = session_client.get(f"{api_url}/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_admin_login_sets_httponly_cookie_and_me_works(api_url, session_client):
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        pytest.skip("Admin credentials missing in env")
    login = session_client.post(f"{api_url}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert login.status_code == 200
    set_cookie = login.headers.get("set-cookie", "")
    assert "admin_access_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=None" in set_cookie

    me = session_client.get(f"{api_url}/auth/me")
    assert me.status_code == 200
    me_data = me.json()
    assert me_data["email"] == ADMIN_EMAIL
    assert me_data["role"] == "admin"


def test_admin_endpoints_block_unauthenticated(api_url, session_client):
    response = session_client.get(f"{api_url}/admin/applicants")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_auth_lockout_after_five_invalid_attempts(api_url, session_client):
    lock_email = f"lockout-{uuid.uuid4().hex[:8]}@nonprofitboardbuilder.com"
    for _ in range(5):
        bad = session_client.post(f"{api_url}/auth/login", json={"email": lock_email, "password": "bad-pass"})
        assert bad.status_code == 401
    sixth = session_client.post(f"{api_url}/auth/login", json={"email": lock_email, "password": "bad-pass"})
    assert sixth.status_code == 429
    assert "Too many login attempts" in sixth.json().get("detail", "")


def test_cors_preflight_allows_credentials(api_url):
    origin = BASE_URL
    response = requests.options(
        f"{api_url}/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert response.headers.get("access-control-allow-origin") == origin


def _applicant_payload(email, country="United States", state_region="Texas", suffix="A"):
    return {
        "first_name": "TEST",
        "last_name": f"Applicant{suffix}",
        "email": email,
        "phone": "+1 415 555 0101",
        "linkedin_url": "https://www.linkedin.com/in/test-applicant-profile",
        "country": country,
        "city": "Austin",
        "state_region": state_region,
        "postal_code": "73301",
        "job_title": "Director of Operations",
        "employer": "TEST Employer Inc",
        "professional_field": "Operations",
        "years_experience": "11–20 years",
        "skills": ["Fundraising", "Operations"],
        "other_skill": "",
        "professional_summary": "Experienced operator supporting nonprofit growth.",
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
        "professional_relationships": "Introductions to local business leaders.",
        "reason_for_joining": "Serve mission-driven organizations.",
        "commitment_answer": "Yes",
        "understands_unpaid": "Yes",
        "profile_sharing_permission": True,
        "board_opportunity_consent": True,
        "other_offers_consent": True,
        "privacy_accepted": True,
    }


@pytest.fixture(scope="session")
def e2e_ids():
    tag = uuid.uuid4().hex[:8]
    return {
        "us_email": f"qa+join-us-{tag}@nonprofitboardbuilder.com",
        "uk_email": f"qa+join-uk-{tag}@nonprofitboardbuilder.com",
        "np_yes_email": f"qa+np-yes-{tag}@nonprofitboardbuilder.com",
        "np_no_email": f"qa+np-no-{tag}@nonprofitboardbuilder.com",
    }


# Applicant module coverage: create, upsert, metadata persistence, resume handling, country rules.
def test_create_us_applicant_and_verify_persistence(api_url, mongo_db, e2e_ids):
    payload = _applicant_payload(e2e_ids["us_email"], suffix="US")
    response = requests.post(f"{api_url}/applicants", data={"payload": __import__("json").dumps(payload)})
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == e2e_ids["us_email"]
    assert data["country"] == "United States"
    assert data["created"] is True
    assert isinstance(data["applicant_id"], str) and data["applicant_id"].startswith("NBB-A-")

    doc = mongo_db.board_applicants.find_one({"email": e2e_ids["us_email"]}, {"_id": 0})
    assert doc is not None
    assert doc["applicant_id"] == data["applicant_id"]
    assert doc["source_page"] == "/join-a-board"
    assert doc["status"] == "New Applicant"
    assert isinstance(doc.get("created_at"), str)
    assert isinstance(doc.get("updated_at"), str)
    assert isinstance(doc.get("consent_at"), str)
    assert "_id" not in doc


def test_upsert_same_email_preserves_created_at_and_id(api_url, mongo_db, e2e_ids):
    existing = mongo_db.board_applicants.find_one({"email": e2e_ids["us_email"]}, {"_id": 0})
    assert existing is not None
    payload = _applicant_payload(e2e_ids["us_email"], suffix="US2")
    payload["job_title"] = "Chief Operating Officer"
    response = requests.post(f"{api_url}/applicants", data={"payload": __import__("json").dumps(payload)})
    assert response.status_code == 201
    data = response.json()
    assert data["created"] is False
    assert data["applicant_id"] == existing["applicant_id"]

    updated = mongo_db.board_applicants.find_one({"email": e2e_ids["us_email"]}, {"_id": 0})
    assert updated["applicant_id"] == existing["applicant_id"]
    assert updated["created_at"] == existing["created_at"]
    assert updated["updated_at"] != existing["updated_at"]
    assert updated["job_title"] == "Chief Operating Officer"
    assert mongo_db.board_applicants.count_documents({"email": e2e_ids["us_email"]}) == 1


def test_resume_persisted_in_gridfs_and_downloadable(api_url, mongo_db):
    email = f"qa+resume-{uuid.uuid4().hex[:8]}@nonprofitboardbuilder.com"
    payload = _applicant_payload(email, suffix="RESUME")
    files = {
        "resume": (
            "qa_resume.pdf",
            b"%PDF-1.4\n% test resume\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF",
            "application/pdf",
        )
    }
    response = requests.post(f"{api_url}/applicants", data={"payload": __import__("json").dumps(payload)}, files=files)
    assert response.status_code == 201
    applicant_id = response.json()["applicant_id"]

    doc = mongo_db.board_applicants.find_one({"email": email}, {"_id": 0})
    assert doc is not None
    assert isinstance(doc.get("resume_file_id"), str) and doc["resume_file_id"]
    assert doc.get("resume_filename") == "qa_resume.pdf"
    assert doc.get("resume_content_type") == "application/pdf"
    assert mongo_db["applicant_resumes.files"].count_documents({"metadata.applicant_id": applicant_id}) >= 1

    admin = _admin_session(api_url)
    resume_response = admin.get(f"{api_url}/admin/applicants/{applicant_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.headers.get("content-type", "").startswith("application/pdf")
    assert len(resume_response.content) > 20


def test_create_uk_applicant(api_url, mongo_db, e2e_ids):
    payload = _applicant_payload(
        e2e_ids["uk_email"],
        country="United Kingdom",
        state_region="Greater London",
        suffix="UK",
    )
    payload["city"] = "London"
    payload["postal_code"] = "SW1A 1AA"
    response = requests.post(f"{api_url}/applicants", data={"payload": __import__("json").dumps(payload)})
    assert response.status_code == 201
    data = response.json()
    assert data["country"] == "United Kingdom"

    doc = mongo_db.board_applicants.find_one({"email": e2e_ids["uk_email"]}, {"_id": 0})
    assert doc is not None
    assert doc["state_region"] == "Greater London"


def test_block_outside_country(api_url, mongo_db):
    email = f"qa+join-ca-{uuid.uuid4().hex[:8]}@nonprofitboardbuilder.com"
    payload = _applicant_payload(email, country="Canada", state_region="Ontario", suffix="CA")
    response = requests.post(f"{api_url}/applicants", data={"payload": __import__("json").dumps(payload)})
    assert response.status_code == 422
    assert "United States and United Kingdom" in str(response.json())

    doc = mongo_db.board_applicants.find_one({"email": email})
    assert doc is None


# Assessment module coverage: optional nonprofit marketing consent sync fields and admin contacts view.
def _assessment_payload(email, marketing_consent):
    return {
        "name": "TEST Nonprofit Leader",
        "email": email,
        "phone": "+1 302 555 0102",
        "organization_name": "TEST Community Impact Org",
        "website": "https://example.org",
        "mission": "Improve local outcomes.",
        "city": "Middletown",
        "state_region": "Delaware",
        "country": "United States",
        "annual_budget": "$250,000 - $499,999",
        "most_important_board_result": "More active fundraising board",
        "bylaws_board_size": "8",
        "current_board_size": "6",
        "active_board_members": "4",
        "inactive_board_members": "2",
        "present_board_condition": ["Some members are active"],
        "board_type": "Working board",
        "commitment_conversations": "Some members",
        "willing_to_allow_step_down": "Yes",
        "bylaw_clarity": "Mostly clear",
        "new_board_members_needed": "3",
        "recruitment_timeline": "Within 90 days",
        "areas_carried_alone": ["Fundraising"],
        "missing_skills_networks": "Fundraising and legal",
        "expected_new_member_benefit": "Donor connections",
        "people_already_identified": "No",
        "benefits_of_joining": "Community impact",
        "previous_recruitment_experience": "Limited success",
        "present_fundraising_involvement": "Yes, a few of them",
        "board_support_areas": ["Making introductions"],
        "written_fundraising_strategy": "No",
        "individual_responsibilities": "No",
        "board_participation_in_planning": "No",
        "missing_fundraising_elements": ["A clear fundraising strategy"],
        "desired_result": "Reliable donor pipeline",
        "support_required": "Work with me one-on-one while I execute.",
        "additional_information": "",
        "confirmation_accepted": True,
        "marketing_consent": marketing_consent,
    }


def _admin_session(api_url):
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        pytest.skip("Admin credentials missing in env")
    session = requests.Session()
    login = session.post(f"{api_url}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert login.status_code == 200
    return session


def test_assessment_with_marketing_consent_sync_fields(api_url, mongo_db, e2e_ids):
    payload = _assessment_payload(e2e_ids["np_yes_email"], True)
    response = requests.post(f"{api_url}/assessments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["submitted_email"] == e2e_ids["np_yes_email"]

    doc = mongo_db.board_assessments.find_one({"email": e2e_ids["np_yes_email"]}, sort=[("_id", -1)])
    assert doc is not None
    assert doc["marketing_consent"] is True
    assert isinstance(doc.get("marketing_consent_at"), str) and doc.get("marketing_consent_at")
    assert doc.get("marketing_resend_status") in {"Synced", "Failed", "Pending"}

    admin = _admin_session(api_url)
    contacts = admin.get(f"{api_url}/admin/nonprofit-contacts")
    assert contacts.status_code == 200
    rows = contacts.json()
    assert any(item.get("email") == e2e_ids["np_yes_email"] for item in rows)


def test_assessment_without_marketing_consent_not_requested(api_url, mongo_db, e2e_ids):
    payload = _assessment_payload(e2e_ids["np_no_email"], False)
    response = requests.post(f"{api_url}/assessments", json=payload)
    assert response.status_code == 201

    doc = mongo_db.board_assessments.find_one({"email": e2e_ids["np_no_email"]}, sort=[("_id", -1)])
    assert doc is not None
    assert doc["marketing_consent"] is False
    assert doc.get("marketing_resend_status") == "Not Requested"

    admin = _admin_session(api_url)
    contacts = admin.get(f"{api_url}/admin/nonprofit-contacts")
    assert contacts.status_code == 200
    rows = contacts.json()
    assert not any(item.get("email") == e2e_ids["np_no_email"] for item in rows)
