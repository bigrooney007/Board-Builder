"""Iteration 60 — Complete Board Fix member-mode intake submit (session_id='') + optional bylaws upload.

Narrow bug verification only. Uses a dedicated fresh member; never touches rooney@ records.
No AI, no emails, no Stripe checkouts.
"""
import io
import os
import time

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")

WORKER = os.environ.get("PYTEST_XDIST_WORKER", "solo")
TESTER_EMAIL = f"bufintake-tester-{int(time.time())}-{WORKER}@example.com"
TESTER_PASSWORD = "BufTest123!"


@pytest.fixture(scope="session")
def mongo_db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="session")
def member(mongo_db):
    """Register a fresh member and grant board_fix_system directly in Mongo (no purchase)."""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/members/register", json={
        "first_name": "BUF", "last_name": "Tester", "email": TESTER_EMAIL,
        "password": TESTER_PASSWORD, "confirm_password": TESTER_PASSWORD,
    })
    assert response.status_code == 201, f"register failed: {response.status_code} {response.text[:400]}"
    body = response.json()
    user_id = body["member"]["user_id"]
    token = body["token"]
    assert body["member"]["entitlements"] == []
    result = mongo_db.members.update_one({"user_id": user_id}, {"$addToSet": {"entitlements": "board_fix_system"}})
    assert result.matched_count == 1
    yield {"user_id": user_id, "token": token, "session": session, "email": TESTER_EMAIL}
    # teardown: remove all data created by this dedicated tester only
    mongo_db.members.delete_one({"user_id": user_id})
    mongo_db.board_fix_intakes.delete_many({"user_id": user_id})
    mongo_db.board_fix_journeys.delete_many({"user_id": user_id})
    mongo_db.recruitment_profiles.delete_many({"user_id": user_id})
    session.close()


@pytest.fixture(scope="session")
def member_client(member):
    """Cookie-authenticated session (register set member_access_token cookie)."""
    return member["session"]


def tiny_pdf() -> bytes:
    from reportlab.pdfgen import canvas
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(80, 700, "ARTICLE I BYLAWS OF BUF INTAKE TEST ORG")
    pdf.save()
    return buffer.getvalue()


INTAKE_DATA = {
    "organization_name": "BUF Intake Test Org",
    "mission": "x",
    "website": "https://buf-intake-test.example.com",
    "board_size": "7",
    "skills_represented": "Finance, Legal",
    "board_problems": "Board is disengaged",
    "strategic_priorities": "Grow major gifts",
}


# --- The reported bug: member-mode submit with session_id='' ---
class TestMemberModeIntakeSubmit:

    def test_submit_with_empty_session_id_first_time(self, member_client, mongo_db, member):
        response = member_client.post(f"{BASE_URL}/api/board-fix-intake/submit",
                                      json={"session_id": "", "data": INTAKE_DATA})
        assert response.status_code != 422, f"REGRESSION: 422 returned — {response.text[:400]}"
        assert response.status_code == 200, f"{response.status_code} {response.text[:400]}"
        body = response.json()
        assert body["status"] == "submitted"
        assert body["redirect_url"] == "/board-fix-orientation"
        # bylaws are optional: succeeded with no bylaws upload and no bylaws field in payload
        doc = mongo_db.board_fix_intakes.find_one({"user_id": member["user_id"]})
        assert doc is not None
        assert doc["session_id"] == f"member-intake-{member['user_id']}"
        assert doc["data"]["organization_name"] == "BUF Intake Test Org"
        assert doc.get("submitted_at")
        assert "bylaws_filename" not in doc
        assert "bylaws_text" not in doc["data"]

    def test_context_reopen_returns_saved_answers(self, member_client):
        response = member_client.get(f"{BASE_URL}/api/board-fix-intake/context")
        assert response.status_code == 200, response.text[:300]
        body = response.json()
        assert body["eligible"] is True
        assert body["submitted"] is True
        assert body["data"]["organization_name"] == "BUF Intake Test Org"
        assert body["data"]["board_size"] == "7"
        assert body["lead_name"] == "BUF Tester"
        assert "bylaws_filename" in body

    def test_edit_submit_redirects_to_roadmap_and_no_duplicates(self, member_client, mongo_db, member):
        edited = {**INTAKE_DATA, "board_size": "9", "mission": "Edited mission"}
        response = member_client.post(f"{BASE_URL}/api/board-fix-intake/submit",
                                      json={"session_id": "", "data": edited})
        assert response.status_code == 200, response.text[:400]
        assert response.json()["redirect_url"] == "/board-fix-roadmap"
        assert mongo_db.board_fix_intakes.count_documents({"user_id": member["user_id"]}) == 1
        follow = member_client.get(f"{BASE_URL}/api/board-fix-intake/context")
        assert follow.json()["data"]["board_size"] == "9"
        assert follow.json()["data"]["mission"] == "Edited mission"

    def test_submit_with_bearer_token(self, member):
        response = requests.post(f"{BASE_URL}/api/board-fix-intake/submit",
                                 json={"session_id": "", "data": {**INTAKE_DATA, "board_size": "11"}},
                                 headers={"Authorization": f"Bearer {member['token']}"})
        assert response.status_code == 200, response.text[:400]
        assert response.json()["redirect_url"] == "/board-fix-roadmap"


# --- Optional bylaws upload endpoint ---
class TestBylawsUpload:

    def test_upload_pdf_success(self, member_client):
        response = member_client.post(f"{BASE_URL}/api/board-fix-intake/bylaws",
                                      data={"session_id": ""},
                                      files={"file": ("TEST_bylaws.pdf", tiny_pdf(), "application/pdf")})
        assert response.status_code == 201, f"{response.status_code} {response.text[:400]}"
        body = response.json()
        assert body["status"] == "uploaded"
        assert body["filename"] == "TEST_bylaws.pdf"

    def test_context_and_mongo_reflect_bylaws(self, member_client, mongo_db, member):
        context = member_client.get(f"{BASE_URL}/api/board-fix-intake/context").json()
        assert context["bylaws_filename"] == "TEST_bylaws.pdf"
        doc = mongo_db.board_fix_intakes.find_one({"user_id": member["user_id"]})
        assert doc["bylaws_filename"] == "TEST_bylaws.pdf"
        assert doc.get("bylaws_uploaded_at")
        assert "bylaws_text" in doc["data"]
        assert "BYLAWS" in doc["data"]["bylaws_text"].upper()

    def test_upload_txt_rejected(self, member_client):
        response = member_client.post(f"{BASE_URL}/api/board-fix-intake/bylaws",
                                      data={"session_id": ""},
                                      files={"file": ("TEST_bylaws.txt", b"not allowed", "text/plain")})
        assert response.status_code == 400, f"{response.status_code} {response.text[:300]}"
        assert "PDF" in response.json()["detail"]

    def test_upload_without_auth_unauthorized(self):
        response = requests.post(f"{BASE_URL}/api/board-fix-intake/bylaws",
                                 data={"session_id": ""},
                                 files={"file": ("TEST_bylaws.pdf", tiny_pdf(), "application/pdf")})
        assert response.status_code == 401, f"{response.status_code} {response.text[:300]}"


# --- Security gates ---
class TestSecurityGates:

    def test_submit_no_auth_401(self):
        response = requests.post(f"{BASE_URL}/api/board-fix-intake/submit",
                                 json={"session_id": "", "data": INTAKE_DATA})
        assert response.status_code == 401, f"{response.status_code} {response.text[:300]}"

    def test_submit_member_without_entitlement_403(self):
        session = requests.Session()
        login = session.post(f"{BASE_URL}/api/members/login", json={
            "email": "module-tester@example.com", "password": "ModuleTest123!"})
        assert login.status_code == 200, f"login failed: {login.status_code} {login.text[:300]}"
        assert "board_fix_system" not in login.json()["member"]["entitlements"]
        response = session.post(f"{BASE_URL}/api/board-fix-intake/submit",
                                json={"session_id": "", "data": INTAKE_DATA})
        assert response.status_code == 403, f"{response.status_code} {response.text[:300]}"
        session.close()

    def test_submit_bogus_session_id_403(self, member_client):
        response = member_client.post(f"{BASE_URL}/api/board-fix-intake/submit",
                                      json={"session_id": "cs_test_bogus123", "data": INTAKE_DATA})
        assert response.status_code == 403, f"{response.status_code} {response.text[:300]}"

    def test_context_bogus_session_id_not_eligible(self):
        response = requests.get(f"{BASE_URL}/api/board-fix-intake/context",
                                params={"session_id": "cs_test_bogus123"})
        assert response.status_code == 200, f"{response.status_code} {response.text[:300]}"
        assert response.json() == {"eligible": False}

    def test_bylaws_bogus_session_id_403(self, member_client):
        response = member_client.post(f"{BASE_URL}/api/board-fix-intake/bylaws",
                                      data={"session_id": "cs_test_bogus123"},
                                      files={"file": ("TEST_bylaws.pdf", tiny_pdf(), "application/pdf")})
        assert response.status_code == 403, f"{response.status_code} {response.text[:300]}"
