"""Iteration 12: Founder-only Recruitment Execution Reference Library + Module 1 Blueprint.

Covers:
- Admin access gating on /api/admin/reference-library (401 without cookie, 403 with member cookie, 200 with admin).
- Upload/list/approve/delete round-trip on a TEST .txt reference, plus 422 for invalid module.
- Retrieval gating (workspace_service.reference_context) via the backend's Mongo.
- Module 1 blueprint generation end-to-end (single Claude call, ~120s allowed).
- Privacy spot-check: blueprint must not contain 'For All The Children'.

STRICT: founder doc (reference_id 860f14a8d196abf2) must remain and END UNAPPROVED. Only ONE Claude call permitted.
"""
import asyncio
import io
import os
import secrets
import sys

import pytest
import requests
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
FOUNDER_REF_ID = "860f14a8d196abf2"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def member_session():
    """Ephemeral member with no entitlements — used to prove 401/403 gating."""
    s = requests.Session()
    email = f"TEST_refmember_{secrets.token_hex(4)}@example.com"
    password = "TestMember!12345"
    r = s.post(f"{BASE_URL}/api/members/register",
               json={"first_name": "TEST", "last_name": "Member", "email": email,
                     "password": password, "confirm_password": password}, timeout=15)
    assert r.status_code == 201, f"Member register failed: {r.status_code} {r.text[:200]}"
    yield s, email
    # cleanup
    try:
        client = MongoClient(MONGO_URL)
        client[DB_NAME].members.delete_one({"email": email})
        client.close()
    except Exception:
        pass


# ---------- Admin access gating ----------

class TestReferenceLibraryAccess:
    def test_list_without_cookie_401(self):
        r = requests.get(f"{BASE_URL}/api/admin/reference-library", timeout=15)
        assert r.status_code == 401

    def test_post_without_cookie_401(self):
        r = requests.post(f"{BASE_URL}/api/admin/reference-library",
                          files={"file": ("x.txt", b"hello", "text/plain")},
                          data={"title": "x", "module": "0"}, timeout=15)
        assert r.status_code == 401

    def test_patch_without_cookie_401(self):
        r = requests.patch(f"{BASE_URL}/api/admin/reference-library/{FOUNDER_REF_ID}",
                           json={"approved": True}, timeout=15)
        assert r.status_code == 401

    def test_delete_without_cookie_401(self):
        r = requests.delete(f"{BASE_URL}/api/admin/reference-library/{FOUNDER_REF_ID}", timeout=15)
        assert r.status_code == 401

    def test_list_with_member_cookie_forbidden(self, member_session):
        s, _ = member_session
        r = s.get(f"{BASE_URL}/api/admin/reference-library", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403 with member cookie, got {r.status_code}"

    def test_post_with_member_cookie_forbidden(self, member_session):
        s, _ = member_session
        r = s.post(f"{BASE_URL}/api/admin/reference-library",
                   files={"file": ("x.txt", b"hello", "text/plain")},
                   data={"title": "x", "module": "0"}, timeout=15)
        assert r.status_code in (401, 403)

    def test_list_with_admin_cookie_ok(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/reference-library", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "references" in data and "module_labels" in data
        # Founder doc must be present
        refs = data["references"]
        founder = next((x for x in refs if x["reference_id"] == FOUNDER_REF_ID), None)
        assert founder is not None, "Founder reference doc missing"
        assert founder["module"] == 0
        assert founder["approved"] is False, "Founder doc must start unapproved"
        assert "For All The Children" in founder["title"]


# ---------- Upload/approve/delete round-trip ----------

class TestReferenceRoundTrip:
    reference_id = None

    def test_upload_test_txt(self, admin_session):
        content = ("TEST reference for iteration 12. Discusses recruitment application, "
                   "board opportunity, linkedin post, and application questions.").encode()
        r = admin_session.post(f"{BASE_URL}/api/admin/reference-library",
                               files={"file": ("test_ref.txt", content, "text/plain")},
                               data={"title": "TEST reference", "module": "3", "resource_types": ""},
                               timeout=20)
        assert r.status_code == 201, r.text[:300]
        ref = r.json()["reference"]
        assert ref["title"] == "TEST reference"
        assert ref["module"] == 3
        assert ref["approved"] is False
        TestReferenceRoundTrip.reference_id = ref["reference_id"]

    def test_listed_unapproved(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/reference-library", timeout=15)
        assert r.status_code == 200
        found = next((x for x in r.json()["references"]
                      if x["reference_id"] == TestReferenceRoundTrip.reference_id), None)
        assert found is not None
        assert found["approved"] is False
        assert found["module"] == 3

    def test_patch_module_9_returns_422(self, admin_session):
        r = admin_session.patch(
            f"{BASE_URL}/api/admin/reference-library/{TestReferenceRoundTrip.reference_id}",
            json={"module": 9}, timeout=15)
        assert r.status_code == 422

    def test_approve_then_delete(self, admin_session):
        rid = TestReferenceRoundTrip.reference_id
        r = admin_session.patch(f"{BASE_URL}/api/admin/reference-library/{rid}",
                                json={"approved": True}, timeout=15)
        assert r.status_code == 200
        assert r.json()["reference"]["approved"] is True

        r = admin_session.delete(f"{BASE_URL}/api/admin/reference-library/{rid}", timeout=15)
        assert r.status_code == 200
        # verify 404 after delete
        r = admin_session.get(f"{BASE_URL}/api/admin/reference-library/{rid}", timeout=15)
        assert r.status_code == 404


# ---------- Retrieval gating (reference_context) ----------

class TestReferenceRetrievalGating:
    def test_unapproved_returns_empty(self, db):
        # Ensure founder doc is unapproved (starting state)
        db.reference_materials.update_one(
            {"reference_id": FOUNDER_REF_ID}, {"$set": {"approved": False}})
        # Also make sure no stray approved references exist
        approved_count = db.reference_materials.count_documents({"approved": True})
        assert approved_count == 0, f"Unexpected approved references: {approved_count}"

        from workspace_service import reference_context
        from motor.motor_asyncio import AsyncIOMotorClient

        async def _run():
            mc = AsyncIOMotorClient(MONGO_URL)
            try:
                text = await reference_context(mc[DB_NAME], "board_opportunity")
            finally:
                mc.close()
            return text

        text = asyncio.get_event_loop().run_until_complete(_run())
        assert text == "", f"Expected empty string with no approved refs, got: {text[:200]}"

    def test_approved_returns_rules_and_content(self, db):
        db.reference_materials.update_one(
            {"reference_id": FOUNDER_REF_ID}, {"$set": {"approved": True}})

        from workspace_service import reference_context
        from motor.motor_asyncio import AsyncIOMotorClient

        async def _run():
            mc = AsyncIOMotorClient(MONGO_URL)
            try:
                return await reference_context(mc[DB_NAME], "board_opportunity")
            finally:
                mc.close()

        text = asyncio.get_event_loop().run_until_complete(_run())
        assert "FOUNDER RECRUITMENT EXECUTION REFERENCE LIBRARY" in text
        assert "NEVER copy" in text

    def test_revoke_founder_end_state(self, db):
        """MANDATORY end-state: founder doc must be approved=false."""
        db.reference_materials.update_one(
            {"reference_id": FOUNDER_REF_ID}, {"$set": {"approved": False}})
        doc = db.reference_materials.find_one({"reference_id": FOUNDER_REF_ID})
        assert doc["approved"] is False


# ---------- Module 1 Blueprint Generation (single Claude call) ----------

class TestModule1Blueprint:
    material_id_created = None
    blueprint_display = None

    def test_generate_blueprint(self, admin_session, db):
        user_id = "owner-review-admin"
        # minimal profile data
        profile_payload = {
            "data": {
                "organization_name": "TEST_Aurora Children Foundation",
                "website": "https://aurora.test",
                "city": "Denver", "state_region": "Colorado", "country": "United States",
                "mission": "Support at-risk youth through education and mentorship.",
                "present_board": "5 members: founder, treasurer (CPA), secretary (teacher), 2 general.",
                "active_board": "Yes, meets monthly.",
                "priorities": "Grow annual fundraising, expand mentorship program, add corporate partnerships.",
                "new_members_count": "3",
                "board_kind": "Governing",
                "strengthen_areas": ["Fundraising", "Corporate partnerships", "Marketing"],
                "biggest_weaknesses": "Limited corporate connections, no fundraising specialist, minimal marketing.",
                "biggest_strengths": "Committed founder, strong program delivery, good community reputation.",
                "goals": "Add three board members with corporate fundraising, marketing, and finance expertise.",
            }
        }
        r = admin_session.put(f"{BASE_URL}/api/workspace/profile", json=profile_payload, timeout=20)
        assert r.status_code == 200, r.text[:300]

        r = admin_session.post(f"{BASE_URL}/api/workspace/profile/confirm", timeout=20)
        assert r.status_code == 200, r.text[:300]

        # single Claude call — allow up to 150s
        r = admin_session.post(f"{BASE_URL}/api/workspace/generate",
                               json={"type": "powerhouse_board_blueprint"}, timeout=180)
        assert r.status_code == 200, f"Blueprint generation failed: {r.status_code} {r.text[:400]}"
        material = r.json()
        TestModule1Blueprint.material_id_created = material.get("material_id")
        assert material.get("type") == "powerhouse_board_blueprint"
        versions = material.get("versions", [])
        assert len(versions) >= 1
        current = next(v for v in versions if v["version"] == material["current_version"])
        structured = current["structured"]
        assert isinstance(structured, dict)
        # required top-level fields per schema
        for key in ("present_board_brings", "what_is_missing",
                    "powerhouse_board_description", "candidate_profiles"):
            assert key in structured, f"missing {key} in blueprint"
        assert isinstance(structured["candidate_profiles"], list)
        assert len(structured["candidate_profiles"]) >= 1
        first = structured["candidate_profiles"][0]
        for k in ("skills_and_experience", "valuable_relationships_networks",
                  "fundraising_contribution", "board_gap_this_person_fills"):
            assert k in first, f"missing {k} in first candidate profile"
        TestModule1Blueprint.blueprint_display = current["display_text"]

    def test_privacy_spot_check(self):
        assert TestModule1Blueprint.blueprint_display is not None, "blueprint not generated"
        text = TestModule1Blueprint.blueprint_display
        assert "For All The Children" not in text, \
            "Privacy leak: reference client name appeared in generated blueprint"

    def test_cleanup_test_data(self, db):
        # remove the TEST material and profile so we don't leave state around
        db.generated_materials.delete_many(
            {"user_id": "owner-review-admin", "type": "powerhouse_board_blueprint"})
        db.recruitment_profiles.delete_many({"user_id": "owner-review-admin"})
        # confirm founder doc is unapproved (final safety)
        doc = db.reference_materials.find_one({"reference_id": FOUNDER_REF_ID})
        assert doc["approved"] is False
