"""Iteration 53 — two-stage recruitment offer (DIY $297 + Selection & Onboarding $297) backend tests."""
import os
import time
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
    tracker = {"sessions": [], "members": [], "emails": []}
    yield tracker
    for sid in tracker["sessions"]:
        db.payment_transactions.delete_many({"session_id": sid})
        db.board_recruitment_intakes.delete_many({"session_id": sid})
    for uid in tracker["members"]:
        db.members.delete_many({"user_id": uid})
        db.course_progress.delete_many({"user_id": uid})
        db.recruitment_profiles.delete_many({"user_id": uid})


def register_member(api, created, email, entitlements):
    r = api.post(f"{BASE_URL}/api/members/register", json={
        "first_name": "TEST", "last_name": "Stage", "email": email,
        "password": "TestPass123!", "confirm_password": "TestPass123!"})
    assert r.status_code == 201, r.text
    data = r.json()
    uid = data["member"]["user_id"]
    created["members"].append(uid)
    return uid, data["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------- Stripe checkouts (items 3,4,5)
class TestCheckoutSessions:
    def test_diy_297_checkout(self, api, created):
        r = api.post(f"{BASE_URL}/api/payments/diy-checkout",
                     json={"origin_url": BASE_URL, "result_token": "", "cancel_path": "/offer/recruitment"})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        created["sessions"].append(sid)
        assert r.json()["checkout_url"].startswith("https://")
        s = stripe.checkout.Session.retrieve(sid)
        assert s.amount_total == 29700
        assert s.success_url == f"{BASE_URL}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}"
        assert s.cancel_url == f"{BASE_URL}/offer/recruitment?checkout=cancelled"
        assert s.metadata["purchase_source"] == "recruitment_campaign_diy_297"
        assert s.metadata["selected_tier"] == "297"

    def test_dwy_1497_checkout(self, api, created):
        r = api.post(f"{BASE_URL}/api/payments/direct-project-checkout",
                     json={"origin_url": BASE_URL, "result_token": ""})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        created["sessions"].append(sid)
        s = stripe.checkout.Session.retrieve(sid)
        assert s.amount_total == 149700
        assert s.success_url == f"{BASE_URL}/board-recruitment-intake?session_id={{CHECKOUT_SESSION_ID}}"
        assert s.metadata["purchase_source"] == "direct_board_recruitment_project"

    def test_selection_onboarding_checkout(self, api, created):
        r = api.post(f"{BASE_URL}/api/payments/selection-onboarding-checkout",
                     json={"origin_url": BASE_URL, "result_token": ""})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        created["sessions"].append(sid)
        s = stripe.checkout.Session.retrieve(sid, expand=["line_items"])
        assert s.amount_total == 29700
        assert s.success_url == f"{BASE_URL}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}"
        assert s.cancel_url == f"{BASE_URL}/app/recruitment/selection-offer?checkout=cancelled"
        assert s.metadata["purchase_source"] == "recruitment_selection_onboarding_297"
        # distinct price from DIY 297
        price_id = s.line_items.data[0].price.id
        price = stripe.Price.retrieve(price_id, expand=["product"])
        assert price.lookup_key == "recruitment_selection_onboarding_297", price.lookup_key
        diy = api.post(f"{BASE_URL}/api/payments/diy-checkout",
                       json={"origin_url": BASE_URL, "result_token": ""})
        diy_sid = diy.json()["session_id"]
        created["sessions"].append(diy_sid)
        diy_s = stripe.checkout.Session.retrieve(diy_sid, expand=["line_items"])
        assert diy_s.line_items.data[0].price.id != price_id

    def test_selection_session_unpaid_cannot_claim(self, api, created):
        """Item 8: registering with a real but UNPAID selection session must not grant entitlement."""
        r = api.post(f"{BASE_URL}/api/payments/selection-onboarding-checkout",
                     json={"origin_url": BASE_URL, "result_token": ""})
        sid = r.json()["session_id"]
        created["sessions"].append(sid)
        email = f"TEST_unpaid_{STAMP}@example.com"
        reg = api.post(f"{BASE_URL}/api/members/register", json={
            "first_name": "TEST", "last_name": "Unpaid", "email": email,
            "password": "TestPass123!", "confirm_password": "TestPass123!", "session_id": sid})
        assert reg.status_code == 402, f"expected 402, got {reg.status_code}: {reg.text[:300]}"


# ---------------------------------------------------------------- Intake routing (item 7)
class TestIntakeRouting:
    def _seed(self, db, created, source):
        sid = f"cs_test_TEST{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc).isoformat()
        db.payment_transactions.insert_one({
            "session_id": sid, "purchase_source": source, "selected_tier": "297",
            "payment_status": "paid", "status": "completed", "amount": 29700,
            "currency": "usd", "test_mode": True, "created_at": now, "updated_at": now})
        created["sessions"].append(sid)
        return sid

    def _payload(self, sid):
        return {
            "session_id": sid, "your_name": "TEST Person", "email": f"TEST_intake_{STAMP}@example.com",
            "organization_name": "TEST Org", "mission": "Testing missions", "city": "Austin",
            "state": "TX", "board_type": "Governing"}

    def test_diy_intake_context_and_submit(self, api, db, created):
        sid = self._seed(db, created, "recruitment_campaign_diy_297")
        ctx = api.get(f"{BASE_URL}/api/board-recruitment-intake/context", params={"session_id": sid})
        assert ctx.status_code == 200, ctx.text
        body = ctx.json()
        assert body.get("eligible") is True, body
        sub = api.post(f"{BASE_URL}/api/board-recruitment-intake/submit", json=self._payload(sid))
        assert sub.status_code == 201, sub.text
        assert sub.json()["redirect_url"] == "/recruitment-start-here"

    def test_dwy_intake_submit_calendly(self, api, db, created):
        sid = self._seed(db, created, "direct_board_recruitment_project")
        sub = api.post(f"{BASE_URL}/api/board-recruitment-intake/submit", json=self._payload(sid))
        assert sub.status_code == 201, sub.text
        assert sub.json()["redirect_url"] == "https://calendly.com/boardbuilder/recruitboard"

    def test_intake_context_rejects_bogus_session(self, api):
        r = api.get(f"{BASE_URL}/api/board-recruitment-intake/context",
                    params={"session_id": "cs_test_bogus_does_not_exist"})
        assert r.status_code in (402, 404), r.status_code


# ---------------------------------------------------------------- Course gating (items 9, 10)
class TestCourseGating:
    @pytest.fixture(scope="class")
    def stage1(self, api, db, created):
        email = f"TEST_stage1_{STAMP}@example.com"
        uid, token = register_member(api, created, email, ["recruitment_self_guided"])
        db.members.update_one({"user_id": uid}, {"$set": {"entitlements": ["recruitment_self_guided"]}})
        return {"user_id": uid, "token": token, "email": email}

    # iter56: module 1 RESTORED to the customer journey -> 6 modules, positions 1-6
    def test_six_modules_with_module_one(self, api, stage1):
        r = api.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=auth(stage1["token"]))
        assert r.status_code == 200, r.text
        modules = r.json()["modules"]
        assert [m["number"] for m in modules] == [1, 2, 3, 4, 5, 6]
        assert [m.get("position") for m in modules] == [1, 2, 3, 4, 5, 6]
        assert modules[0]["title"] == "Understanding the Board Recruitment Process"
        locked = {m["number"]: m.get("locked") for m in modules}
        assert locked == {1: False, 2: False, 3: False, 4: True, 5: True, 6: True}, locked

    def test_progress_allowed_on_1_2_and_3(self, api, stage1):
        for n in (1, 2, 3):
            r = api.post(f"{BASE_URL}/api/courses/progress", headers=auth(stage1["token"]),
                         json={"product": "recruitment_self_guided", "module_number": n, "action": "completed"})
            assert r.status_code == 200, f"module {n}: {r.status_code} {r.text[:200]}"

    def test_progress_blocked_on_module_4(self, api, stage1):
        r = api.post(f"{BASE_URL}/api/courses/progress", headers=auth(stage1["token"]),
                     json={"product": "recruitment_self_guided", "module_number": 4, "action": "completed"})
        assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"

    def test_workspace_gating_stage1(self, api, stage1):
        h = auth(stage1["token"])
        assert api.get(f"{BASE_URL}/api/workspace/applications", headers=h).status_code == 403
        assert api.get(f"{BASE_URL}/api/workspace/profile", headers=h).status_code == 200
        gen = api.post(f"{BASE_URL}/api/workspace/generate", headers=h,
                       json={"product": "recruitment_self_guided", "type": "general_interview_invitation"})
        assert gen.status_code == 403, f"{gen.status_code} {gen.text[:200]}"

    def test_unlock_after_selection_entitlement(self, api, db, stage1):
        db.members.update_one({"user_id": stage1["user_id"]},
                              {"$set": {"entitlements": ["recruitment_self_guided", "recruitment_selection_onboarding"]}})
        time.sleep(0.5)
        h = auth(stage1["token"])
        r = api.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=h)
        assert r.status_code == 200
        modules = r.json()["modules"]
        assert all(m.get("locked") is False for m in modules), [(m["number"], m.get("locked")) for m in modules]
        assert api.get(f"{BASE_URL}/api/workspace/applications", headers=h).status_code == 200
        p = api.post(f"{BASE_URL}/api/courses/progress", headers=h,
                     json={"product": "recruitment_self_guided", "module_number": 4, "action": "completed"})
        assert p.status_code == 200, p.text
