"""Iteration 54 — FINAL VERIFICATION of the two-stage recruitment funnel (read-only except throwaway members).

Covers: TEST A (stage-1 $297 access + stage-2 lockout), TEST B (stage-2 Stripe + unlock + entitlement purity),
TEST C ($1,497 DWY), item 4 (first $297 Stripe), item 5 (unpaid protection), item 6 (grandfathered intact),
item 8 (other-funnel regression, read-only).
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
VERIFY_A_EMAIL = f"verifyA.tester+{STAMP}@example.com"


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
        "first_name": "Verify", "last_name": "Tester", "email": email,
        "password": "TestPass123!", "confirm_password": "TestPass123!"})
    assert r.status_code == 201, r.text
    data = r.json()
    created["members"].append(data["member"]["user_id"])
    return data["member"]["user_id"], data["token"]


def seed_paid_txn(db, created, source, amount, tier="297"):
    sid = f"cs_test_TESTITER54{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc).isoformat()
    db.payment_transactions.insert_one({
        "session_id": sid, "purchase_source": source, "selected_tier": tier,
        "payment_status": "paid", "status": "completed", "amount": amount,
        "currency": "usd", "test_mode": True, "created_at": now, "updated_at": now})
    created["sessions"].append(sid)
    return sid


def intake_payload(sid, email):
    return {"session_id": sid, "your_name": "Verify Tester", "email": email,
            "organization_name": "TEST Verify Org", "mission": "Testing missions for verification",
            "city": "Austin", "state": "TX", "board_type": "Governing"}


# ================================================================ Shared stage-1 member (TEST A / B)
@pytest.fixture(scope="session")
def member_a(api, db, created):
    uid, token = register(api, created, VERIFY_A_EMAIL)
    db.members.update_one({"user_id": uid}, {"$set": {"entitlements": ["recruitment_self_guided"]}})
    return {"user_id": uid, "token": token, "email": VERIFY_A_EMAIL}


# ================================================================ Item 4: first $297 Stripe session
class TestFirstStagePayment:
    def test_diy_297_stripe_session(self, api, created):
        r = api.post(f"{BASE_URL}/api/payments/diy-checkout",
                     json={"origin_url": BASE_URL, "result_token": "", "cancel_path": "/offer/recruitment"})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        created["sessions"].append(sid)
        s = stripe.checkout.Session.retrieve(sid, expand=["line_items"])
        assert s.amount_total == 29700, s.amount_total
        assert s.success_url == f"{BASE_URL}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}"
        assert s.metadata["purchase_source"] == "recruitment_campaign_diy_297"
        pytest.diy_price_id = s.line_items.data[0].price.id


# ================================================================ TEST A
class TestAStageOneAccess:
    def test_intake_context_eligible_and_submit_redirect(self, api, db, created, member_a):
        sid = seed_paid_txn(db, created, "recruitment_campaign_diy_297", 29700)
        ctx = api.get(f"{BASE_URL}/api/board-recruitment-intake/context", params={"session_id": sid})
        assert ctx.status_code == 200, ctx.text
        assert ctx.json().get("eligible") is True, ctx.json()
        sub = api.post(f"{BASE_URL}/api/board-recruitment-intake/submit",
                       json=intake_payload(sid, member_a["email"]))
        assert sub.status_code == 201, sub.text
        assert sub.json()["redirect_url"] == "/recruitment-start-here", sub.json()

    def test_module_2_and_3_accessible_with_titles(self, api, member_a):
        r = api.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=auth(member_a["token"]))
        assert r.status_code == 200, r.text
        modules = {m["number"]: m for m in r.json()["modules"]}
        assert list(modules) == [2, 3, 4, 5, 6], list(modules)
        assert modules[2]["locked"] is False and modules[3]["locked"] is False
        assert modules[2]["position"] == 1 and modules[3]["position"] == 2
        # NOTE: actual product copy is "Identifying the People Your Board Needs"
        # (user's request paraphrased it as "Identify the Board You Need").
        assert "Identifying the People Your Board Needs" == modules[2]["title"], modules[2]["title"]
        assert "Launch Your Recruitment Campaign" in modules[3]["title"], modules[3]["title"]
        for n in (2, 3):
            p = api.post(f"{BASE_URL}/api/courses/progress", headers=auth(member_a["token"]),
                         json={"product": "recruitment_self_guided", "module_number": n, "action": "completed"})
            assert p.status_code == 200, f"module {n}: {p.status_code} {p.text[:200]}"

    def test_stage_two_locked(self, api, member_a):
        h = auth(member_a["token"])
        r = api.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=h)
        modules = {m["number"]: m for m in r.json()["modules"]}
        assert {n: modules[n]["locked"] for n in (4, 5, 6)} == {4: True, 5: True, 6: True}
        assert api.get(f"{BASE_URL}/api/workspace/applications", headers=h).status_code == 403
        p = api.post(f"{BASE_URL}/api/courses/progress", headers=h,
                     json={"product": "recruitment_self_guided", "module_number": 4, "action": "completed"})
        assert p.status_code == 403, f"{p.status_code} {p.text[:200]}"
        g = api.post(f"{BASE_URL}/api/workspace/generate", headers=h,
                     json={"product": "recruitment_self_guided", "type": "general_interview_invitation"})
        assert g.status_code == 403, f"{g.status_code} {g.text[:200]}"


# ================================================================ TEST B
class TestBSecondStage:
    def test_selection_checkout_distinct_price(self, api, created):
        r = api.post(f"{BASE_URL}/api/payments/selection-onboarding-checkout",
                     json={"origin_url": BASE_URL, "result_token": ""})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        created["sessions"].append(sid)
        s = stripe.checkout.Session.retrieve(sid, expand=["line_items"])
        assert s.amount_total == 29700, s.amount_total
        assert s.metadata["purchase_source"] == "recruitment_selection_onboarding_297"
        price_id = s.line_items.data[0].price.id
        assert price_id != getattr(pytest, "diy_price_id", None), "stage-2 price id equals stage-1 price id"

    def test_unlock_after_entitlement_grant(self, api, db, member_a):
        db.members.update_one({"user_id": member_a["user_id"]}, {"$addToSet": {
            "entitlements": "recruitment_selection_onboarding"}})
        h = auth(member_a["token"])
        r = api.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=h)
        assert r.status_code == 200
        modules = {m["number"]: m for m in r.json()["modules"]}
        assert all(m["locked"] is False for m in modules.values()), \
            {n: m["locked"] for n, m in modules.items()}
        assert "Select" in modules[4]["title"] and "Interview" in modules[4]["title"], modules[4]["title"]
        assert "Reference" in modules[5]["title"], modules[5]["title"]
        assert "Onboard" in modules[6]["title"], modules[6]["title"]
        assert api.get(f"{BASE_URL}/api/workspace/applications", headers=h).status_code == 200
        p = api.post(f"{BASE_URL}/api/courses/progress", headers=h,
                     json={"product": "recruitment_self_guided", "module_number": 4, "action": "completed"})
        assert p.status_code == 200, p.text

    def test_no_unrelated_entitlements(self, db, member_a):
        doc = db.members.find_one({"user_id": member_a["user_id"]})
        ents = sorted(doc.get("entitlements", []))
        assert ents == ["recruitment_selection_onboarding", "recruitment_self_guided"], ents


# ================================================================ TEST C
class TestCDoWithUs:
    def test_dwy_checkout_and_calendly_redirect(self, api, db, created):
        r = api.post(f"{BASE_URL}/api/payments/direct-project-checkout",
                     json={"origin_url": BASE_URL, "result_token": ""})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        created["sessions"].append(sid)
        s = stripe.checkout.Session.retrieve(sid)
        assert s.amount_total == 149700, s.amount_total
        assert s.success_url == f"{BASE_URL}/board-recruitment-intake?session_id={{CHECKOUT_SESSION_ID}}"
        assert s.metadata["purchase_source"] == "direct_board_recruitment_project"

        paid = seed_paid_txn(db, created, "direct_board_recruitment_project", 149700, tier="1497")
        ctx = api.get(f"{BASE_URL}/api/board-recruitment-intake/context", params={"session_id": paid})
        assert ctx.status_code == 200 and ctx.json().get("eligible") is True, ctx.text
        sub = api.post(f"{BASE_URL}/api/board-recruitment-intake/submit",
                       json=intake_payload(paid, f"TEST_dwy_{STAMP}@example.com"))
        assert sub.status_code == 201, sub.text
        assert sub.json()["redirect_url"] == "https://calendly.com/boardbuilder/recruitboard", sub.json()


# ================================================================ Item 5: unpaid protection
class TestUnpaidProtection:
    def test_bogus_and_missing_session_blocked(self, api):
        r = api.get(f"{BASE_URL}/api/board-recruitment-intake/context",
                    params={"session_id": "cs_test_bogus_iter54"})
        assert r.status_code in (402, 404), f"{r.status_code} {r.text[:200]}"

    def test_no_entitlement_member_403(self, api, created):
        uid, token = register(api, created, f"TEST_noent_{STAMP}@example.com")
        h = auth(token)
        assert api.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=h).status_code == 403
        assert api.get(f"{BASE_URL}/api/workspace/profile", headers=h).status_code == 403

    def test_register_with_unpaid_real_session_402(self, api, created):
        r = api.post(f"{BASE_URL}/api/payments/diy-checkout",
                     json={"origin_url": BASE_URL, "result_token": ""})
        sid = r.json()["session_id"]
        created["sessions"].append(sid)
        reg = api.post(f"{BASE_URL}/api/members/register", json={
            "first_name": "TEST", "last_name": "Unpaid", "email": f"TEST_unpaid54_{STAMP}@example.com",
            "password": "TestPass123!", "confirm_password": "TestPass123!", "session_id": sid})
        assert reg.status_code == 402, f"{reg.status_code} {reg.text[:300]}"


# ================================================================ Item 6: grandfathered members (read-only)
class TestGrandfathered:
    def test_both_entitlement_members_count(self, db):
        cur = list(db.members.find(
            {"entitlements": {"$all": ["recruitment_self_guided", "recruitment_selection_onboarding"]}},
            {"email": 1, "entitlements": 1, "purchases": 1, "_id": 0}))
        real = [m for m in cur if not m["email"].startswith("TEST_") and "verifyA.tester" not in m["email"]]
        assert len(real) >= 8, f"only {len(real)} members: {[m['email'] for m in real]}"
        spot = real[0]
        assert "recruitment_self_guided" in spot["entitlements"]
        assert "recruitment_selection_onboarding" in spot["entitlements"]


# ================================================================ Item 8: other funnels unchanged (read-only)
class TestOtherFunnelsRegression:
    @pytest.mark.parametrize("path", ["/reactivate", "/activate"])
    def test_pages_load(self, api, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=30)
        assert r.status_code == 200, r.status_code

    def test_reactivation_project_checkout(self, api, created):
        r = api.post(f"{BASE_URL}/api/payments/reactivation-project-checkout",
                     json={"origin_url": BASE_URL, "result_token": ""})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        created["sessions"].append(sid)
        s = stripe.checkout.Session.retrieve(sid)
        assert s.amount_total == 549700, s.amount_total
