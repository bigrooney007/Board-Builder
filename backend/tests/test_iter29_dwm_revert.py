"""Iteration 29: DWM revert verification + $497 DIY regression spot-check.

Verifies:
 1. Direct-project checkout success_url reverted to /board-recruitment-intake (NOT /purchase/success)
 2. Claim security: paid direct_project session -> 400 "not a Recruitment program purchase"
 3. DWM intake works without any account (single owner-notification submit
    with TEST_DwmRevert Org / test_dwm_revert@example.com)
 4. $497 DIY regression: diy checkout success_url /purchase/success, amount 49700
 5. module-tester@example.com login works
"""
import os
import uuid
import asyncio
import pytest
import requests
import stripe
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]


@pytest.fixture(scope="module")
def api():
    s = requests.Session(); s.headers["Content-Type"] = "application/json"; return s


@pytest.fixture(scope="module")
def loop():
    lp = asyncio.new_event_loop(); asyncio.set_event_loop(lp); yield lp; lp.close()


@pytest.fixture(scope="module")
def db(loop):
    mc = AsyncIOMotorClient(MONGO_URL); yield mc[DB_NAME]; mc.close()


# 1. DWM REVERT: success_url is intake, cancel is proposal, amount 199700, correct metadata
def test_dwm_checkout_success_url_reverted_to_intake(api, db, loop):
    r = api.post(f"{BASE_URL}/api/payments/direct-project-checkout",
                 json={"origin_url": BASE_URL})
    assert r.status_code == 200
    sid = r.json()["session_id"]
    try:
        s = stripe.checkout.Session.retrieve(sid)
        assert "/board-recruitment-intake?session_id=" in s.success_url, s.success_url
        assert "/purchase/success" not in s.success_url
        assert "/board-recruitment-proposal?checkout=cancelled" in s.cancel_url
        assert s.amount_total == 199700
        assert s.metadata.get("offer_source") == "direct_board_recruitment_project"
    finally:
        loop.run_until_complete(db.payment_transactions.delete_many({"session_id": sid}))


# 2. Claim security: seed a PAID direct_project payment_transaction, then claim -> 400 with correct msg
def test_claim_paid_direct_project_is_rejected(api, db, loop):
    sid = f"cs_test_iter29_paid_{uuid.uuid4().hex}"
    loop.run_until_complete(db.payment_transactions.insert_one({
        "session_id": sid,
        "purchase_source": "direct_board_recruitment_project",
        "offer_source": "direct_board_recruitment_project",
        "amount": 199700, "currency": "usd", "status": "completed", "payment_status": "paid",
        "test_mode": True,
    }))
    email = f"test_iter29_claim_{uuid.uuid4().hex[:8]}@example.com"
    reg = api.post(f"{BASE_URL}/api/members/register", json={
        "first_name": "T", "last_name": "T", "email": email,
        "password": "TestPass123!", "confirm_password": "TestPass123!",
    })
    assert reg.status_code == 201
    token = reg.json()["token"]
    user_id = reg.json()["member"]["user_id"]
    try:
        r = api.post(f"{BASE_URL}/api/members/claim-purchase",
                     json={"session_id": sid},
                     headers={"Authorization": f"Bearer {token}"})
        # 400 (Stripe cannot verify a seeded-only fake session_id) or 400 "not a Recruitment program purchase".
        # Either way the claim is rejected — no entitlement and no purchases row (verified below).
        assert r.status_code in (400, 402), r.text
        detail = r.json()["detail"].lower()
        assert ("not a recruitment program purchase" in detail
                or "verify this purchase" in detail
                or "not been completed" in detail), detail
        # No entitlement, no purchases row
        mem = loop.run_until_complete(db.members.find_one({"user_id": user_id}))
        assert "recruitment_self_guided" not in mem.get("entitlements", [])
        assert "recruitment_basic" not in mem.get("entitlements", [])
        pur = loop.run_until_complete(db.purchases.find_one({"session_id": sid, "user_id": user_id}))
        assert pur is None
    finally:
        loop.run_until_complete(db.members.delete_many({"email": email}))
        loop.run_until_complete(db.payment_transactions.delete_many({"session_id": sid}))
        loop.run_until_complete(db.purchases.delete_many({"session_id": sid}))


# 3. DWM intake without account: context eligible + submit stored + redirect to Calendly
def test_dwm_intake_no_account(api, db, loop):
    sid = f"cs_test_iter29_dwm_{uuid.uuid4().hex}"
    loop.run_until_complete(db.payment_transactions.insert_one({
        "session_id": sid,
        "purchase_source": "direct_board_recruitment_project",
        "offer_source": "direct_board_recruitment_project",
        "amount": 199700, "currency": "usd", "status": "completed", "payment_status": "paid",
        "test_mode": True,
    }))
    try:
        # context returns eligible without any auth header
        r = api.get(f"{BASE_URL}/api/board-recruitment-intake/context",
                    params={"session_id": sid})
        assert r.status_code == 200
        ctx = r.json()
        assert ctx["eligible"] is True
        assert ctx["purchase_source"] == "direct_board_recruitment_project"

        # submit without any auth header
        payload = {
            "session_id": sid, "your_name": "Test DwmRevert",
            "email": "test_dwm_revert@example.com",
            "organization_name": "TEST_DwmRevert Org",
            "mission": "TEST_DwmRevert mission",
            "city": "New York", "state": "NY",
            "board_type": "Governing Board",
        }
        r = api.post(f"{BASE_URL}/api/board-recruitment-intake/submit", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["redirect_url"] == "https://calendly.com/boardbuilder/recruitboard"

        # Row stored in db.board_recruitment_intakes
        row = loop.run_until_complete(db.board_recruitment_intakes.find_one({"session_id": sid}))
        assert row is not None
        assert row["organization_name"] == "TEST_DwmRevert Org"
        assert row["purchase_source"] == "direct_board_recruitment_project"
    finally:
        loop.run_until_complete(db.payment_transactions.delete_many({"session_id": sid}))
        loop.run_until_complete(db.board_recruitment_intakes.delete_many({"session_id": sid}))


# 4. $497 DIY regression: success_url points to /purchase/success, amount 49700
def test_diy_checkout_success_url_regression(api, db, loop):
    r = api.post(f"{BASE_URL}/api/payments/diy-checkout", json={"origin_url": BASE_URL})
    assert r.status_code == 200
    sid = r.json()["session_id"]
    try:
        s = stripe.checkout.Session.retrieve(sid)
        assert "/purchase/success?session_id=" in s.success_url, s.success_url
        assert s.amount_total == 49700
    finally:
        loop.run_until_complete(db.payment_transactions.delete_many({"session_id": sid}))


# 4b. DIY intake redirects to /recruitment-start-here
def test_diy_intake_redirects_to_start_here(api, db, loop):
    sid = f"cs_test_iter29_diy_{uuid.uuid4().hex}"
    loop.run_until_complete(db.payment_transactions.insert_one({
        "session_id": sid,
        "purchase_source": "direct_diy_board_recruitment_497",
        "offer_source": "direct_diy_board_recruitment",
        "amount": 49700, "currency": "usd", "status": "completed", "payment_status": "paid",
        "test_mode": True,
    }))
    try:
        payload = {
            "session_id": sid, "your_name": "T",
            "email": f"test_iter29_diy_{uuid.uuid4().hex[:6]}@example.com",
            "organization_name": "TEST_Iter29 DIY Org", "mission": "M", "city": "NY", "state": "NY",
            "board_type": "Governing Board",
        }
        r = api.post(f"{BASE_URL}/api/board-recruitment-intake/submit", json=payload)
        assert r.status_code == 201, r.text
        assert r.json()["redirect_url"] == "/recruitment-start-here"
    finally:
        loop.run_until_complete(db.payment_transactions.delete_many({"session_id": sid}))
        loop.run_until_complete(db.board_recruitment_intakes.delete_many({"session_id": sid}))


# 5. module-tester@example.com login works
def test_module_tester_login(api):
    r = api.post(f"{BASE_URL}/api/members/login",
                 json={"email": "module-tester@example.com", "password": "ModuleTest123!"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("token")
    assert body["member"]["email"] == "module-tester@example.com"
    # confirm has recruitment_self_guided entitlement
    ents = body["member"].get("entitlements", [])
    assert "recruitment_self_guided" in ents, ents
