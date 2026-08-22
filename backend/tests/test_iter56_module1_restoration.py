"""Iteration 56 — VERIFY restoration of recruitment Module 1 / Step 1 into the customer journey.

Scope (read-only except throwaway members / test payment rows):
 1. Fresh $297 customer journey (Mongo-simulated payment) -> intake eligible -> submit redirect
 2. Course API for a stage-1-only member: 6 modules, numbers/positions 1-6, locks {1-3:F,4-6:T}
    module 1 title + canonical video, progress 200 on 1/2/3, 403 on 4, workspace 403
 3. Second payment (entitlement grant) unlocks all 6; module 4 title; applications 200;
    selection-onboarding checkout still 29700 / recruitment_selection_onboarding_297
 4. Unpaid / DWY / grandfather spot checks
 5. Read-only other-funnel regression
"""
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
import stripe
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or backend_env["STRIPE_SECRET_KEY"]
MONGO_URL = os.environ.get("MONGO_URL") or backend_env["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME") or backend_env["DB_NAME"]

STAMP = uuid.uuid4().hex[:8]
STAGE1_EMAIL = f"TEST_iter56_stage1_{STAMP}@example.com"
MODULE1_VIDEO_ID = "MADZN-LqAvA"
SELECTION_NAME = "Selection, Interview, Reference Check & Onboarding"


@pytest.fixture(scope="session")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def created(db):
    tracker = {"sessions": [], "members": []}
    yield tracker
    for sid in tracker["sessions"]:
        db.payment_transactions.delete_many({"session_id": sid})
        db.board_recruitment_intakes.delete_many({"session_id": sid})
    for uid in tracker["members"]:
        db.members.delete_many({"user_id": uid})
        db.course_progress.delete_many({"user_id": uid})
        db.recruitment_profiles.delete_many({"user_id": uid})
        db.board_applications.delete_many({"user_id": uid})


def auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def register(api, created, email):
    r = api.post(f"{BASE_URL}/api/members/register", json={
        "first_name": "Iter56", "last_name": "Tester", "email": email,
        "password": "TestPass123!", "confirm_password": "TestPass123!"})
    assert r.status_code == 201, r.text
    data = r.json()
    created["members"].append(data["member"]["user_id"])
    return data["member"]["user_id"], data["token"]


def seed_paid_txn(db, created, source, amount, tier="297"):
    sid = f"cs_test_TESTITER56{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc).isoformat()
    db.payment_transactions.insert_one({
        "session_id": sid, "purchase_source": source, "selected_tier": tier,
        "payment_status": "paid", "status": "completed", "amount": amount,
        "currency": "usd", "test_mode": True, "created_at": now, "updated_at": now})
    created["sessions"].append(sid)
    return sid


def intake_payload(sid, email):
    return {"session_id": sid, "your_name": "Iter56 Tester", "email": email,
            "organization_name": "TEST Iter56 Org", "mission": "Testing module 1 restoration",
            "city": "Austin", "state": "TX", "board_type": "Governing"}


@pytest.fixture(scope="session")
def stage1(api, db, created):
    uid, token = register(api, created, STAGE1_EMAIL)
    db.members.update_one({"user_id": uid}, {"$set": {"entitlements": ["recruitment_self_guided"]}})
    return {"user_id": uid, "token": token, "email": STAGE1_EMAIL}


# --- 1. Fresh $297 customer journey -------------------------------------------
class TestFreshCustomerJourney:
    def test_intake_context_and_submit_redirect(self, api, db, created, stage1):
        sid = seed_paid_txn(db, created, "recruitment_campaign_diy_297", 29700)
        ctx = api.get(f"{BASE_URL}/api/board-recruitment-intake/context", params={"session_id": sid})
        assert ctx.status_code == 200, ctx.text
        assert ctx.json().get("eligible") is True, ctx.json()
        sub = api.post(f"{BASE_URL}/api/board-recruitment-intake/submit",
                       json=intake_payload(sid, stage1["email"]))
        assert sub.status_code == 201, sub.text
        assert sub.json()["redirect_url"] == "/recruitment-start-here", sub.json()


# --- 2. Course API: module 1 restored -----------------------------------------
class TestCourseStructureRestored:
    def test_six_modules_positions_and_locks(self, api, stage1):
        r = api.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=auth(stage1["token"]))
        assert r.status_code == 200, r.text
        modules = r.json()["modules"]
        assert [m["number"] for m in modules] == [1, 2, 3, 4, 5, 6]
        assert [m["position"] for m in modules] == [1, 2, 3, 4, 5, 6]
        assert {m["number"]: m["locked"] for m in modules} == {
            1: False, 2: False, 3: False, 4: True, 5: True, 6: True}

    def test_module_titles_and_module1_video(self, api, stage1):
        r = api.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=auth(stage1["token"]))
        modules = {m["number"]: m for m in r.json()["modules"]}
        assert modules[1]["title"] == "Understanding the Board Recruitment Process", modules[1]["title"]
        assert modules[2]["title"] == "Identifying the People Your Board Needs", modules[2]["title"]
        assert modules[3]["title"] == "Launch Your Recruitment Campaign", modules[3]["title"]
        assert MODULE1_VIDEO_ID in modules[1].get("youtube_url", ""), modules[1].get("youtube_url")

    def test_progress_allowed_on_1_2_3(self, api, stage1):
        for n in (1, 2, 3):
            r = api.post(f"{BASE_URL}/api/courses/progress", headers=auth(stage1["token"]),
                         json={"product": "recruitment_self_guided", "module_number": n, "action": "completed"})
            assert r.status_code == 200, f"module {n}: {r.status_code} {r.text[:200]}"
        # totals reverted to 6 -> 3/6 = 50%
        body = r.json()
        assert body["modules_completed"] == 3, body
        assert body["percent_complete"] == 50, body

    def test_course_percent_reflects_six_total(self, api, stage1):
        r = api.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=auth(stage1["token"]))
        data = r.json()
        assert data["modules_completed"] == 3, data["modules_completed"]
        assert data["percent_complete"] == 50, data["percent_complete"]

    def test_progress_blocked_on_module_4(self, api, stage1):
        r = api.post(f"{BASE_URL}/api/courses/progress", headers=auth(stage1["token"]),
                     json={"product": "recruitment_self_guided", "module_number": 4, "action": "completed"})
        assert r.status_code == 403, f"{r.status_code} {r.text[:300]}"
        assert SELECTION_NAME in r.json().get("detail", ""), r.text

    def test_workspace_applications_blocked(self, api, stage1):
        assert api.get(f"{BASE_URL}/api/workspace/applications",
                       headers=auth(stage1["token"])).status_code == 403


# --- 3. Second payment entitlement unchanged ----------------------------------
class TestSecondPaymentUnlock:
    def test_selection_checkout_unchanged(self, api, created):
        r = api.post(f"{BASE_URL}/api/payments/selection-onboarding-checkout",
                     json={"origin_url": BASE_URL, "result_token": ""})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        created["sessions"].append(sid)
        s = stripe.checkout.Session.retrieve(sid)
        assert s.amount_total == 29700, s.amount_total
        assert s.metadata["purchase_source"] == "recruitment_selection_onboarding_297"

    def test_all_six_unlock_after_grant(self, api, db, stage1):
        db.members.update_one({"user_id": stage1["user_id"]},
                              {"$addToSet": {"entitlements": "recruitment_selection_onboarding"}})
        h = auth(stage1["token"])
        r = api.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=h)
        assert r.status_code == 200, r.text
        modules = {m["number"]: m for m in r.json()["modules"]}
        assert list(modules) == [1, 2, 3, 4, 5, 6]
        assert all(m["locked"] is False for m in modules.values()), \
            {n: m["locked"] for n, m in modules.items()}
        assert modules[4]["title"] == "Select and Interview Your Applicants", modules[4]["title"]
        assert modules[4]["position"] == 4, modules[4]["position"]
        assert api.get(f"{BASE_URL}/api/workspace/applications", headers=h).status_code == 200
        p = api.post(f"{BASE_URL}/api/courses/progress", headers=h,
                     json={"product": "recruitment_self_guided", "module_number": 4, "action": "completed"})
        assert p.status_code == 200, p.text


# --- 4. Unpaid / DWY / grandfather spot checks --------------------------------
class TestSpotChecks:
    def test_bogus_session_intake_blocked(self, api):
        r = api.get(f"{BASE_URL}/api/board-recruitment-intake/context",
                    params={"session_id": "cs_test_bogus_iter56"})
        assert r.status_code in (402, 403, 404), f"{r.status_code} {r.text[:200]}"

    def test_dwy_checkout_and_intake_submit(self, api, db, created):
        r = api.post(f"{BASE_URL}/api/payments/direct-project-checkout",
                     json={"origin_url": BASE_URL, "result_token": ""})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        created["sessions"].append(sid)
        s = stripe.checkout.Session.retrieve(sid)
        assert s.amount_total == 149700, s.amount_total
        assert "/board-recruitment-intake?session_id=" in s.success_url, s.success_url
        dwy_sid = seed_paid_txn(db, created, "direct_board_recruitment_project", 149700, tier="1497")
        sub = api.post(f"{BASE_URL}/api/board-recruitment-intake/submit",
                       json=intake_payload(dwy_sid, f"TEST_iter56_dwy_{STAMP}@example.com"))
        assert sub.status_code == 201, sub.text
        assert "calendly.com" in sub.json()["redirect_url"], sub.json()

    def test_grandfathered_members_intact(self, db):
        count = db.members.count_documents({"entitlements": {"$all": [
            "recruitment_self_guided", "recruitment_selection_onboarding"]}})
        assert count >= 8, count

    def test_stage1b_tester_untouched(self, db):
        doc = db.members.find_one({"email": "stage1b.tester@example.com"})
        assert doc is not None
        assert doc.get("entitlements") == ["recruitment_self_guided"], doc.get("entitlements")


# --- 5. Read-only other-funnel regression ------------------------------------
class TestOtherFunnels:
    @pytest.mark.parametrize("path", ["/reactivate", "/activate"])
    def test_pages_load(self, api, path):
        assert api.get(f"{BASE_URL}{path}").status_code == 200

    def test_reactivation_project_checkout(self, api, created):
        r = api.post(f"{BASE_URL}/api/payments/reactivation-project-checkout",
                     json={"origin_url": BASE_URL, "result_token": ""})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        created["sessions"].append(sid)
        assert stripe.checkout.Session.retrieve(sid).amount_total == 549700
