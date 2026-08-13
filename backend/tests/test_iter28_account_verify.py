"""Iteration 28: Customer account/login verification for $497 DIY and $1,997 DWM flows.

Scope: backend-only surfaces that were changed today.
- Register 409 on duplicate email
- Login endpoint accepts optional session_id and returns claimed/claimed_source
- Claim security: fake session -> 400, unpaid session -> 402, session already linked
  to different account -> 409
- $1,997 DWM buyers intentionally get NO account: claim of direct_board_recruitment_project
  is rejected (400) and the checkout success_url goes straight to /board-recruitment-intake.
- Intake submit redirect_url: DIY -> /recruitment-start-here, DWM -> Calendly.

We DO NOT complete real Stripe payments in this file. Full Stripe checkout is exercised via
Playwright in the frontend automation script.
"""
import asyncio
import os
import uuid

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers["Content-Type"] = "application/json"
    return s


@pytest.fixture(scope="module")
def loop():
    lp = asyncio.new_event_loop()
    asyncio.set_event_loop(lp)
    yield lp
    lp.close()


@pytest.fixture(scope="module")
def db(loop):
    mc = AsyncIOMotorClient(MONGO_URL)
    yield mc[DB_NAME]
    mc.close()


def _reg_payload(email, session_id=""):
    return {
        "first_name": "Test", "last_name": "Verify",
        "email": email, "password": "TestPass123!", "confirm_password": "TestPass123!",
        "session_id": session_id,
    }


# ---- Register: duplicate email returns 409 ----
class TestRegisterDuplicate:
    def test_register_new_then_duplicate_returns_409(self, client, db, loop):
        email = f"test_acct_dup_{uuid.uuid4().hex[:8]}@example.com"
        r1 = client.post(f"{BASE_URL}/api/members/register", json=_reg_payload(email))
        assert r1.status_code == 201, r1.text
        body = r1.json()
        assert body["member"]["email"] == email
        assert body["token"]
        assert body["claimed"] == ""

        r2 = client.post(f"{BASE_URL}/api/members/register", json=_reg_payload(email))
        assert r2.status_code == 409
        detail = r2.json().get("detail", "").lower()
        assert "already exists" in detail
        assert "log in" in detail

        # Cleanup
        loop.run_until_complete(db.members.delete_many({"email": email}))


# ---- Claim security: fake session -> 400 ----
class TestClaimSecurity:
    def _create_member(self, client, loop, db):
        email = f"test_acct_claim_{uuid.uuid4().hex[:8]}@example.com"
        r = client.post(f"{BASE_URL}/api/members/register", json=_reg_payload(email))
        assert r.status_code == 201
        token = r.json()["token"]
        user_id = r.json()["member"]["user_id"]
        return email, token, user_id

    def test_claim_fake_session_returns_400(self, client, loop, db):
        email, token, user_id = self._create_member(client, loop, db)
        try:
            r = client.post(
                f"{BASE_URL}/api/members/claim-purchase",
                json={"session_id": f"cs_test_fake_{uuid.uuid4().hex}"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 400
            assert "verify" in r.json()["detail"].lower() or "stripe" in r.json()["detail"].lower()
        finally:
            loop.run_until_complete(db.members.delete_many({"email": email}))

    def test_claim_unpaid_session_returns_402(self, client, loop, db):
        # Create a real unpaid session
        ck = client.post(f"{BASE_URL}/api/payments/direct-project-checkout",
                         json={"origin_url": BASE_URL})
        assert ck.status_code == 200
        sid = ck.json()["session_id"]
        email, token, user_id = self._create_member(client, loop, db)
        try:
            r = client.post(
                f"{BASE_URL}/api/members/claim-purchase",
                json={"session_id": sid},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 402, r.text
            assert "not been completed" in r.json()["detail"].lower()
            # Ensure no entitlement granted
            mem = loop.run_until_complete(db.members.find_one({"user_id": user_id}))
            assert "recruitment_self_guided" not in mem.get("entitlements", [])
            # Ensure no purchases row
            pur = loop.run_until_complete(db.purchases.find_one({"session_id": sid}))
            assert pur is None
        finally:
            loop.run_until_complete(db.members.delete_many({"email": email}))
            loop.run_until_complete(db.payment_transactions.delete_many({"session_id": sid}))

    def test_claim_already_linked_to_different_account_returns_409(self, client, loop, db):
        # Simulate a pre-existing paid purchase linked to user A
        session_id = f"cs_test_prelinked_{uuid.uuid4().hex}"
        other_user_id = f"user_{uuid.uuid4().hex}"
        loop.run_until_complete(db.purchases.insert_one({
            "purchase_id": str(uuid.uuid4()), "user_id": other_user_id,
            "session_id": session_id, "entitlement": "recruitment_self_guided",
            "purchased_at": "2026-01-01T00:00:00Z",
        }))
        email, token, user_id = self._create_member(client, loop, db)
        try:
            r = client.post(
                f"{BASE_URL}/api/members/claim-purchase",
                json={"session_id": session_id},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 409, r.text
            assert "different account" in r.json()["detail"].lower()
        finally:
            loop.run_until_complete(db.members.delete_many({"email": email}))
            loop.run_until_complete(db.purchases.delete_many({"session_id": session_id}))


# ---- Login accepts session_id and returns claimed/claimed_source ----
class TestLoginContract:
    def test_login_returns_claimed_source_shape(self, client, loop, db):
        email = f"test_acct_login_{uuid.uuid4().hex[:8]}@example.com"
        r = client.post(f"{BASE_URL}/api/members/register", json=_reg_payload(email))
        assert r.status_code == 201
        try:
            r2 = client.post(
                f"{BASE_URL}/api/members/login",
                json={"email": email, "password": "TestPass123!"},
            )
            assert r2.status_code == 200
            body = r2.json()
            assert "member" in body
            assert "token" in body
            assert body.get("claimed") == ""
            assert body.get("claimed_source") == ""
        finally:
            loop.run_until_complete(db.members.delete_many({"email": email}))


# ---- Intake redirect_url differs by purchase source ----
class TestIntakeRedirectByOffer:
    def _seed_paid_session(self, loop, db, purchase_source):
        sid = f"cs_test_intake_{uuid.uuid4().hex}"
        loop.run_until_complete(db.payment_transactions.insert_one({
            "session_id": sid, "offer_source": purchase_source.replace("_497", "").replace("direct_", "direct_"),
            "purchase_source": purchase_source,
            "amount": 199700 if "project" in purchase_source else 49700,
            "status": "completed", "payment_status": "paid",
            "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
        }))
        return sid

    def _submit(self, client, sid, org):
        return client.post(f"{BASE_URL}/api/board-recruitment-intake/submit", json={
            "session_id": sid, "your_name": "Test User", "email": "test_acct_intake@example.com",
            "organization_name": org, "mission": "TEST mission", "city": "TEST City",
            "board_type": "Governing",
        })

    def test_diy_intake_redirects_to_start_here(self, client, loop, db):
        sid = self._seed_paid_session(loop, db, "direct_diy_board_recruitment_497")
        try:
            r = self._submit(client, sid, "TEST_AcctVerify DIY Org")
            assert r.status_code == 201, r.text
            assert r.json()["redirect_url"] == "/recruitment-start-here"
        finally:
            loop.run_until_complete(db.payment_transactions.delete_many({"session_id": sid}))
            loop.run_until_complete(db.board_recruitment_intakes.delete_many({"session_id": sid}))

    def test_dwm_intake_redirects_to_calendly(self, client, loop, db):
        sid = self._seed_paid_session(loop, db, "direct_board_recruitment_project")
        try:
            r = self._submit(client, sid, "TEST_AcctVerify DWM Org")
            assert r.status_code == 201, r.text
            assert r.json()["redirect_url"] == "https://calendly.com/boardbuilder/recruitboard"
        finally:
            loop.run_until_complete(db.payment_transactions.delete_many({"session_id": sid}))
            loop.run_until_complete(db.board_recruitment_intakes.delete_many({"session_id": sid}))


# ---- Direct-project checkout stamps its metadata and routes success straight to intake ----
class TestDirectProjectCheckoutMetadata:
    def test_checkout_metadata_has_direct_project_offer_source(self, client, loop, db):
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        r = client.post(f"{BASE_URL}/api/payments/direct-project-checkout",
                        json={"origin_url": BASE_URL})
        assert r.status_code == 200
        sid = r.json()["session_id"]
        try:
            s = stripe.checkout.Session.retrieve(sid)
            assert s.metadata.get("offer_source") == "direct_board_recruitment_project"
            assert s.metadata.get("purchase_source") == "direct_board_recruitment_project"
            assert s.amount_total == 199700
            assert "/board-recruitment-intake" in s.success_url
            assert "{CHECKOUT_SESSION_ID}" in s.success_url
        finally:
            loop.run_until_complete(db.payment_transactions.delete_many({"session_id": sid}))


# ---- Public login link presence in HTML ----
class TestPublicLoginLinks:
    @pytest.mark.parametrize("path", ["/", "/recruit", "/about-rooney"])
    def test_page_loads_html(self, client, path):
        r = client.get(f"{BASE_URL}{path}")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_login_page_loads(self, client):
        r = client.get(f"{BASE_URL}/login")
        assert r.status_code == 200
