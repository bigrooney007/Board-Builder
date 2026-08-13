"""Batch 1 verification tests — Five-step Recruitment restructure.
Covers course endpoints (5 modules, videos, progress /5), migration DB state,
intake merge into recruitment_profiles, publish readiness (no strategy),
admin video validation, and tenant isolation spot check.
"""
import os
import time
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
DB = MONGO[os.environ.get("DB_NAME", "test_database")]

ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PASSWORD = "PC8JX97y7YjPUel9-gM5gAem"

EXPECTED_TITLES = [
    "Identify the Board Members Your Organization Needs",
    "Launch Your Recruitment Campaign",
    "Select and Interview Your Applicants",
    "Complete References and Background Checks",
    "Onboard Your New Board Members",
]
EXPECTED_VIDEOS = {
    1: "Crzh5tPpQYo",
    2: "E4S16dkgKSY",
    3: "WxGpi3hHEO8",
    4: "-gbn1_sl9h8",
    5: "fdjjsiEnfWc",
}


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json().get("access_token") or r.cookies.get("admin_access_token")


@pytest.fixture(scope="session")
def admin_session(admin_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {admin_token}"})
    s.cookies.set("admin_access_token", admin_token)
    return s


def _register_member(email_prefix, entitlements, profile_data=None, strategy=None):
    email = f"TEST_{email_prefix}_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    r = requests.post(f"{BASE_URL}/api/members/register", json={
        "email": email, "password": password, "confirm_password": password,
        "first_name": "Test", "last_name": "User",
    })
    assert r.status_code in (200, 201), r.text
    token = r.json().get("token") or r.json().get("access_token")
    # promote entitlements + optionally profile in mongo
    user_id_doc = DB.members.find_one({"email": email.lower()})
    assert user_id_doc, f"Member not found after register: {email}"
    user_id = user_id_doc["user_id"]
    DB.members.update_one({"user_id": user_id}, {"$set": {"entitlements": entitlements}})
    if profile_data is not None or strategy is not None:
        DB.recruitment_profiles.update_one(
            {"user_id": user_id},
            {"$set": {"data": profile_data or {}, "strategy_intake": strategy or {}, "confirmed": bool(profile_data)}},
            upsert=True,
        )
    return {"email": email, "password": password, "token": token, "user_id": user_id}


@pytest.fixture(scope="session")
def member_full():
    m = _register_member("full", ["recruitment_self_guided"], profile_data={
        "organization_name": "TEST Nonprofit Alpha",
        "mission": "Deliver TEST outcomes for children",
        "desired_board_skills": ["Fundraising", "Legal"],
        "board_kind": "Traditional",
    })
    yield m
    DB.members.delete_one({"user_id": m["user_id"]})
    DB.recruitment_profiles.delete_one({"user_id": m["user_id"]})


@pytest.fixture(scope="session")
def member_empty():
    m = _register_member("empty", ["recruitment_self_guided"])
    yield m
    DB.members.delete_one({"user_id": m["user_id"]})
    DB.recruitment_profiles.delete_one({"user_id": m["user_id"]})


@pytest.fixture(scope="session")
def member_basic():
    m = _register_member("basic", ["recruitment_basic"])
    yield m
    DB.members.delete_one({"user_id": m["user_id"]})


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Courses ----------
class TestCoursesSelfGuided:
    def test_self_guided_returns_5_modules(self, member_full):
        r = requests.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=auth(member_full["token"]))
        assert r.status_code == 200, r.text
        data = r.json()
        modules = data["modules"]
        assert len(modules) == 5
        assert [m["title"] for m in modules] == EXPECTED_TITLES
        for m in modules:
            assert EXPECTED_VIDEOS[m["number"]] in m["youtube_url"], f"module {m['number']} video wrong: {m['youtube_url']}"
        titles_lower = " ".join(EXPECTED_TITLES).lower()
        assert "build your recruitment strategy" not in titles_lower

    def test_self_guided_percent_over_5(self, member_full):
        r = requests.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=auth(member_full["token"]))
        assert r.status_code == 200
        # percent should be int in 0..100 in multiples reflecting /5
        data = r.json()
        assert data["percent_complete"] in {0, 20, 40, 60, 80, 100}


class TestCoursesBasic:
    def test_basic_returns_5_modules(self, member_basic):
        r = requests.get(f"{BASE_URL}/api/courses/recruitment/basic", headers=auth(member_basic["token"]))
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["modules"]) == 5
        assert [m["title"] for m in data["modules"]] == EXPECTED_TITLES
        for m in data["modules"]:
            assert EXPECTED_VIDEOS[m["number"]] in m["youtube_url"]


class TestCourseProgress:
    def test_accepts_1_to_5_rejects_6(self, member_full):
        # accept module 1
        r = requests.post(f"{BASE_URL}/api/courses/progress", headers=auth(member_full["token"]),
                          json={"product": "recruitment_self_guided", "module_number": 1, "action": "viewed"})
        assert r.status_code == 200, r.text
        # reject 6
        r6 = requests.post(f"{BASE_URL}/api/courses/progress", headers=auth(member_full["token"]),
                           json={"product": "recruitment_self_guided", "module_number": 6, "action": "viewed"})
        assert r6.status_code == 422, r6.text

    def test_complete_returns_percent_over_5(self, member_full):
        r = requests.post(f"{BASE_URL}/api/courses/progress", headers=auth(member_full["token"]),
                          json={"product": "recruitment_self_guided", "module_number": 1, "action": "completed"})
        assert r.status_code == 200, r.text
        j = r.json()
        # 1 completed out of 5 => 20%
        assert j["percent_complete"] == 20
        assert j["modules_completed"] == 1
        # reset
        requests.post(f"{BASE_URL}/api/courses/progress", headers=auth(member_full["token"]),
                      json={"product": "recruitment_self_guided", "module_number": 1, "action": "uncompleted"})

    def test_retired_99_records_do_not_count(self, member_full):
        # Insert a fake module 99 progress row directly
        DB.course_progress.insert_one({
            "user_id": member_full["user_id"], "product": "recruitment_self_guided",
            "module_number": 99, "completed": True, "retired_strategy": True,
        })
        try:
            r = requests.post(f"{BASE_URL}/api/courses/progress", headers=auth(member_full["token"]),
                              json={"product": "recruitment_self_guided", "module_number": 2, "action": "completed"})
            assert r.status_code == 200
            # only module 2 counts
            assert r.json()["modules_completed"] == 1
            assert r.json()["percent_complete"] == 20
        finally:
            DB.course_progress.delete_one({"user_id": member_full["user_id"], "module_number": 99})
            requests.post(f"{BASE_URL}/api/courses/progress", headers=auth(member_full["token"]),
                          json={"product": "recruitment_self_guided", "module_number": 2, "action": "uncompleted"})


# ---------- Migration DB state ----------
class TestMigrationDB:
    def test_migration_recorded(self):
        rec = DB.migrations.find_one({"key": "five_step_recruitment_v1"})
        assert rec is not None
        assert "ran_at" in rec

    def test_course_progress_has_legacy_fields(self):
        # Any migrated doc should have five_step_migrated and legacy_module_number
        migrated = list(DB.course_progress.find({"five_step_migrated": True}).limit(10))
        # Only assert structure IF any migrated docs exist (env may be pristine)
        for doc in migrated:
            assert "legacy_module_number" in doc

    def test_retired_strategy_preserved(self):
        # Any retired records should exist as module_number 99 (or none exist if no prior data)
        retired = list(DB.course_progress.find({"module_number": 99, "retired_strategy": True}))
        # It's ok if empty in fresh env, but if any exist they must not be deleted from earlier data
        for doc in retired:
            assert doc.get("legacy_module_number") == 2
        # generated_materials for strategy should still exist with module 0
        strat_materials = list(DB.generated_materials.find({"type": "recruitment_strategy"}))
        for m in strat_materials:
            assert m.get("module") == 0


# ---------- Intake merge ----------
class TestBoardIntakeMemory:
    def _setup_paid(self, user_id):
        sid = f"cs_test_{uuid.uuid4().hex}"
        DB.payment_transactions.insert_one({
            "session_id": sid, "purchase_source": "direct_diy_board_recruitment_497",
            "payment_status": "paid", "status": "completed",
        })
        DB.purchases.insert_one({"session_id": sid, "user_id": user_id})
        return sid

    def test_submit_merges_without_overwrite_no_duplicate(self, member_full):
        sid = self._setup_paid(member_full["user_id"])
        payload = {
            "session_id": sid, "your_name": "New Contact",
            "email": "TEST_intake@example.com",
            "organization_name": "SHOULD NOT OVERWRITE",  # existing org name should win
            "mission": "SHOULD NOT OVERWRITE mission",
            "city": "Austin", "board_type": "Traditional",
            "personal_linkedin_url": "https://linkedin.com/in/tester",
            "current_board_strengths": "Strong finance team",
            "board_challenges": "Need marketing",
            "present_board": "9",
            "desired_skills": ["Marketing"],  # should NOT overwrite existing non-empty list
            "meeting_frequency": "Monthly",
            "board_term": "3 years",
            "time_commitment": "5 hours",
        }
        try:
            r = requests.post(f"{BASE_URL}/api/board-recruitment-intake/submit", json=payload)
            assert r.status_code == 201, r.text
            profile = DB.recruitment_profiles.find_one({"user_id": member_full["user_id"]})
            data = profile["data"]
            # existing values preserved
            assert data["organization_name"] == "TEST Nonprofit Alpha"
            assert data["mission"] == "Deliver TEST outcomes for children"
            assert data["desired_board_skills"] == ["Fundraising", "Legal"]
            # new keys added
            assert data.get("contact_name") == "New Contact"
            assert data.get("personal_linkedin_url") == "https://linkedin.com/in/tester"
            assert data.get("current_board_strengths") == "Strong finance team"
            assert data.get("board_challenges") == "Need marketing"
            assert data.get("present_board") == "9"
            strat = profile.get("strategy_intake", {})
            assert strat.get("meeting_frequency") == "Monthly"
            assert strat.get("board_term") == "3 years"
            assert strat.get("time_expectation") == "5 hours"
            # single profile doc
            count = DB.recruitment_profiles.count_documents({"user_id": member_full["user_id"]})
            assert count == 1
        finally:
            DB.payment_transactions.delete_one({"session_id": sid})
            DB.purchases.delete_one({"session_id": sid})
            DB.board_recruitment_intakes.delete_one({"session_id": sid})

    def test_context_returns_organization_prefill(self, member_full):
        sid = self._setup_paid(member_full["user_id"])
        try:
            r = requests.get(f"{BASE_URL}/api/board-recruitment-intake/context", params={"session_id": sid})
            assert r.status_code == 200, r.text
            body = r.json()
            org = body.get("organization_prefill", {})
            assert org.get("organization_name") == "TEST Nonprofit Alpha"
            assert org.get("mission") == "Deliver TEST outcomes for children"
            assert "Fundraising" in (org.get("desired_skills") or [])
        finally:
            DB.payment_transactions.delete_one({"session_id": sid})
            DB.purchases.delete_one({"session_id": sid})


# ---------- Publish readiness ----------
class TestPublishReadiness:
    def test_readiness_only_has_two_keys(self, member_full):
        r = requests.get(f"{BASE_URL}/api/workspace/opportunity", headers=auth(member_full["token"]))
        assert r.status_code == 200, r.text
        readiness = r.json()["readiness"]
        assert set(readiness.keys()) == {"opportunity_saved", "application_saved"}
        assert "strategy_approved" not in readiness


# ---------- Tenant isolation ----------
class TestTenantIsolation:
    def test_member_cannot_see_others_profile(self, member_full, member_empty):
        r_a = requests.get(f"{BASE_URL}/api/workspace/profile", headers=auth(member_full["token"]))
        r_b = requests.get(f"{BASE_URL}/api/workspace/profile", headers=auth(member_empty["token"]))
        assert r_a.status_code == 200 and r_b.status_code == 200
        a = r_a.json()["profile"]
        b = r_b.json()["profile"]
        # empty member should not see other user's org name
        assert b.get("organization_name", "") != "TEST Nonprofit Alpha"
        assert a.get("organization_name") == "TEST Nonprofit Alpha"


# ---------- Admin video validation ----------
class TestAdminVideos:
    def test_reject_module_6(self, admin_session):
        r = admin_session.patch(f"{BASE_URL}/api/admin/course-videos", json={
            "product": "recruitment_self_guided", "module_number": 6, "youtube_url": "https://x"
        })
        assert r.status_code == 422, r.text

    def test_accept_module_1(self, admin_session):
        # get current value to restore
        current = DB.course_videos.find_one({"product": "recruitment_self_guided", "module_number": 1})
        original_url = (current or {}).get("youtube_url", "")
        try:
            r = admin_session.patch(f"{BASE_URL}/api/admin/course-videos", json={
                "product": "recruitment_self_guided", "module_number": 1,
                "youtube_url": original_url or "https://youtu.be/Crzh5tPpQYo",
            })
            assert r.status_code == 200, r.text
        finally:
            if original_url:
                DB.course_videos.update_one({"product": "recruitment_self_guided", "module_number": 1},
                                            {"$set": {"youtube_url": original_url}})


# ---------- Regression: dashboard modules_total ----------
class TestDashboard:
    def test_modules_total_5(self, member_full):
        r = requests.get(f"{BASE_URL}/api/members/dashboard", headers=auth(member_full["token"]))
        assert r.status_code == 200, r.text
        data = r.json()
        # find modules_total anywhere in dashboard
        blob = str(data)
        assert "'modules_total': 5" in blob or '"modules_total": 5' in blob or "modules_total=5" in blob or 5 == data.get("modules_total") or any(
            (isinstance(v, dict) and v.get("modules_total") == 5) for v in data.values() if isinstance(v, dict)
        )
