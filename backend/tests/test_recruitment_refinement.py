"""Recruitment platform refinement verification (Iteration 11).

Covers:
- Owner Review Mode: admin cookie satisfies /api/members/me and workspace endpoints.
- Strategy intake persistence (Module 2).
- External applicant creation (Module 4).
- Board profile form + public submission (Module 6).
- Material share links: non-agreement -> token; agreement -> 422.
- Security regressions: 401 without cookie, 404 for bad tokens.
"""

import io
import os
import time
import uuid

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


# --- Fixtures ---------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def cleanup(db):
    created_apps = []
    created_responses = []
    created_materials = []
    yield {"apps": created_apps, "responses": created_responses, "materials": created_materials}
    if created_apps:
        db.opportunity_applications.delete_many({"application_id": {"$in": created_apps}})
    if created_responses:
        db.board_profile_responses.delete_many({"response_id": {"$in": created_responses}})
    if created_materials:
        db.generated_materials.delete_many({"material_id": {"$in": created_materials}})
        db.share_links.delete_many({"material_id": {"$in": created_materials}})


# --- Owner Review Mode ------------------------------------------------------

class TestOwnerReviewAuth:
    def test_members_me_with_only_admin_cookie(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/members/me", timeout=15)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        member = data.get("member", data)
        assert member.get("user_id") == "owner-review-admin"
        assert "recruitment_self_guided" in member.get("entitlements", [])

    def test_members_me_without_any_cookie_401(self):
        r = requests.get(f"{BASE_URL}/api/members/me", timeout=15)
        assert r.status_code == 401

    def test_workspace_profile_without_cookie_401(self):
        r = requests.get(f"{BASE_URL}/api/workspace/profile", timeout=15)
        assert r.status_code == 401

    def test_workspace_profile_with_admin_cookie_200(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/workspace/profile", timeout=15)
        assert r.status_code == 200
        assert "profile" in r.json()


# --- Module 2: Strategy intake persistence ----------------------------------

class TestStrategyIntake:
    def test_put_and_get_strategy_intake(self, admin_session):
        payload = {"data": {"know_people": "yes", "know_people_details": "TEST_intake_details",
                            "reach_channels": ["email", "linkedin"], "recruit_outside": "yes",
                            "public_channels": ["linkedin", "facebook"]}}
        r = admin_session.put(f"{BASE_URL}/api/workspace/strategy-intake", json=payload, timeout=15)
        assert r.status_code == 200, r.text[:200]
        assert r.json().get("status") == "saved"

        r2 = admin_session.get(f"{BASE_URL}/api/workspace/profile", timeout=15)
        assert r2.status_code == 200
        intake = r2.json().get("strategy_intake", {})
        assert intake.get("know_people") == "yes"
        assert intake.get("know_people_details") == "TEST_intake_details"
        assert "linkedin" in intake.get("reach_channels", [])


# --- Module 4: External applicant -------------------------------------------

class TestExternalApplicant:
    def test_post_external_applicant_with_cv(self, admin_session, cleanup):
        email = f"TEST_ext_{uuid.uuid4().hex[:8]}@example.com"
        files = {"cv": ("resume.txt", io.BytesIO(b"TEST resume content for external applicant"), "text/plain")}
        data = {"name": "TEST External Candidate", "email": email, "phone": "555-0100",
                "linkedin": "https://linkedin.com/in/testext", "notes": "TEST notes"}
        r = admin_session.post(f"{BASE_URL}/api/workspace/applications/external", data=data, files=files, timeout=20)
        assert r.status_code == 201, r.text[:300]
        app_id = r.json()["application_id"]
        cleanup["apps"].append(app_id)

        # Verify persistence via list
        r2 = admin_session.get(f"{BASE_URL}/api/workspace/applications", timeout=15)
        assert r2.status_code == 200
        apps = r2.json().get("applications", [])
        matched = next((a for a in apps if a.get("application_id") == app_id), None)
        assert matched is not None, "External applicant not returned in listing"
        assert matched.get("source") == "External / LinkedIn"
        snap = matched.get("profile_snapshot", {})
        assert snap.get("email") == email.lower()
        assert snap.get("full_name") == "TEST External Candidate"


# --- Module 6: Board profile form -------------------------------------------

class TestBoardProfileForm:
    def test_owner_gets_token_and_public_flow(self, admin_session, cleanup, db):
        r = admin_session.get(f"{BASE_URL}/api/workspace/board-profile-form", timeout=15)
        assert r.status_code == 200
        body = r.json()
        token = body["share_token"]
        assert token and len(token) > 8

        meta = requests.get(f"{BASE_URL}/api/board-profile/{token}", timeout=15)
        assert meta.status_code == 200
        assert "organization_name" in meta.json()

        submit = requests.post(f"{BASE_URL}/api/board-profile/{token}",
                               json={"full_name": "TEST_Board Prospect", "email": "TEST_prospect@example.com",
                                     "skills": "governance,fundraising"}, timeout=15)
        assert submit.status_code == 201

        # Verify appears in owner panel
        r2 = admin_session.get(f"{BASE_URL}/api/workspace/board-profile-form", timeout=15)
        responses = r2.json().get("responses", [])
        assert any(resp["data"].get("email") == "TEST_prospect@example.com" for resp in responses)

        # Track for cleanup
        rec = db.board_profile_responses.find_one({"data.email": "TEST_prospect@example.com"})
        if rec:
            cleanup["responses"].append(rec["response_id"])

    def test_bad_token_404(self):
        r = requests.get(f"{BASE_URL}/api/board-profile/BADTOKEN_xyz", timeout=15)
        assert r.status_code == 404


# --- Share links ------------------------------------------------------------

class TestShareLinks:
    def test_share_non_agreement_and_agreement(self, admin_session, cleanup, db):
        # Seed a non-agreement material directly in Mongo (skip Claude generation).
        non_agreement_id = f"TEST_mat_{uuid.uuid4().hex[:8]}"
        db.generated_materials.insert_one({
            "material_id": non_agreement_id, "user_id": "owner-review-admin",
            "type": "board_opportunity", "title": "Board Opportunity",
            "current_version": 1,
            "versions": [{"version": 1, "structured": {}, "display_text": "TEST shareable content",
                          "created_at": "2026-01-01T00:00:00+00:00"}],
            "application_id": "", "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        })
        cleanup["materials"].append(non_agreement_id)

        r = admin_session.post(f"{BASE_URL}/api/workspace/materials/{non_agreement_id}/share", timeout=15)
        assert r.status_code == 201, r.text[:200]
        token = r.json()["share_token"]

        pub = requests.get(f"{BASE_URL}/api/shared/{token}", timeout=15)
        assert pub.status_code == 200
        assert "TEST shareable content" in pub.json().get("display_text", "")

        # Seed an agreement material
        agreement_id = f"TEST_agr_{uuid.uuid4().hex[:8]}"
        db.generated_materials.insert_one({
            "material_id": agreement_id, "user_id": "owner-review-admin",
            "type": "board_member_agreement", "title": "Board Member Agreement",
            "current_version": 1,
            "versions": [{"version": 1, "structured": {}, "display_text": "TEST agreement",
                          "created_at": "2026-01-01T00:00:00+00:00"}],
            "application_id": "TEST", "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        })
        cleanup["materials"].append(agreement_id)
        r2 = admin_session.post(f"{BASE_URL}/api/workspace/materials/{agreement_id}/share", timeout=15)
        assert r2.status_code == 422

    def test_shared_bad_token_404(self):
        r = requests.get(f"{BASE_URL}/api/shared/BADTOKEN_xyz", timeout=15)
        assert r.status_code == 404


# --- Entitlement regression -------------------------------------------------

class TestEntitlementRegression:
    def test_member_without_self_guided_cannot_access_course(self, db):
        # Create ephemeral member without recruitment_self_guided
        email = f"TEST_noent_{uuid.uuid4().hex[:6]}@example.com"
        reg = requests.post(f"{BASE_URL}/api/members/register",
                            json={"email": email, "password": os.environ["TEST_ACCOUNT_PASSWORD"],
                                  "confirm_password": os.environ["TEST_ACCOUNT_PASSWORD"],
                                  "first_name": "TEST", "last_name": "NoEnt"}, timeout=15)
        if reg.status_code not in (200, 201):
            pytest.skip(f"register unavailable: {reg.status_code}")
        body = reg.json()
        token = body.get("token") or body.get("access_token")
        assert token, f"no member token returned: {body}"
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=headers, timeout=15)
        assert r.status_code == 403
        # Cleanup
        db.members.delete_many({"email": email})
