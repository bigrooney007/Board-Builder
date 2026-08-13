"""Batch 1/2/3: About Rooney, DIY $497, Board Recruitment Proposal, Intake gating/submit.

Covers backend surfaces only (does NOT complete a real Stripe checkout).
Public URL from REACT_APP_BACKEND_URL. Uses stripe test-mode key already
configured in backend .env. Cleans up any test rows it creates.
"""
import os
import uuid
import time
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
ORIGIN = BASE_URL  # used as origin_url


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers["Content-Type"] = "application/json"
    return s


@pytest.fixture(scope="module")
def db():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    mc = AsyncIOMotorClient(MONGO_URL)
    yield mc[DB_NAME], loop
    mc.close()
    loop.close()


# ---- Batch 3: DIY checkout endpoint ----
class TestDIYCheckout:
    def test_diy_checkout_creates_stripe_session(self, client, db):
        r = client.post(f"{BASE_URL}/api/payments/diy-checkout", json={"origin_url": ORIGIN})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["session_id"].startswith("cs_")
        assert "checkout.stripe.com" in data["checkout_url"]

        # Verify DB row
        mongo, loop = db
        row = loop.run_until_complete(mongo.payment_transactions.find_one({"session_id": data["session_id"]}))
        assert row is not None
        assert row["amount"] == 49700
        assert row["currency"] == "usd"
        assert row["purchase_source"] == "direct_diy_board_recruitment_497"
        assert row["offer_source"] == "direct_diy_board_recruitment"
        assert row["payment_status"] == "pending"

        # Retrieve session to confirm success/cancel URLs
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        session = stripe.checkout.Session.retrieve(data["session_id"])
        assert session.amount_total == 49700
        assert session.currency == "usd"
        assert session.mode == "payment"
        assert "/purchase/success" in session.success_url
        assert "/recruit-your-board-yourself?checkout=cancelled" in session.cancel_url
        assert session.metadata["purchase_source"] == "direct_diy_board_recruitment_497"
        assert session.metadata["offer_source"] == "direct_diy_board_recruitment"
        assert session.metadata["selected_tier"] == "497"
        loop.run_until_complete(mongo.payment_transactions.delete_one({"session_id": data["session_id"]}))

    def test_diy_checkout_invalid_origin(self, client):
        r = client.post(f"{BASE_URL}/api/payments/diy-checkout", json={"origin_url": "not-a-url"})
        assert r.status_code == 400


# ---- Direct-project checkout success_url points straight to the intake form (no account) ----
class TestDirectProjectCheckout:
    def test_direct_project_success_url_is_intake(self, client, db):
        r = client.post(f"{BASE_URL}/api/payments/direct-project-checkout", json={"origin_url": ORIGIN})
        assert r.status_code == 200, r.text
        data = r.json()
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        session = stripe.checkout.Session.retrieve(data["session_id"])
        assert "/board-recruitment-intake" in session.success_url
        assert "session_id={CHECKOUT_SESSION_ID}" in session.success_url
        assert "/board-recruitment-proposal?checkout=cancelled" in session.cancel_url
        assert session.amount_total == 199700
        mongo, loop = db
        loop.run_until_complete(mongo.payment_transactions.delete_one({"session_id": data["session_id"]}))


# ---- Intake gating ----
class TestIntakeGating:
    def test_intake_context_404_for_bogus_session(self, client):
        r = client.get(f"{BASE_URL}/api/board-recruitment-intake/context",
                       params={"session_id": f"cs_bogus_{uuid.uuid4().hex}"})
        assert r.status_code == 404

    def test_intake_context_402_for_pending_diy_session(self, client, db):
        # Create a DIY checkout (unpaid)
        r = client.post(f"{BASE_URL}/api/payments/diy-checkout", json={"origin_url": ORIGIN})
        sid = r.json()["session_id"]
        r2 = client.get(f"{BASE_URL}/api/board-recruitment-intake/context", params={"session_id": sid})
        assert r2.status_code == 402, r2.text
        mongo, loop = db
        loop.run_until_complete(mongo.payment_transactions.delete_one({"session_id": sid}))

    def test_intake_submit_rejected_for_bogus_session(self, client):
        payload = {
            "session_id": f"cs_bogus_{uuid.uuid4().hex}",
            "your_name": "Test", "email": "test@example.com",
            "organization_name": "Org", "mission": "M", "city": "NY", "state": "NY",
            "board_type": "Governing Board",
        }
        r = client.post(f"{BASE_URL}/api/board-recruitment-intake/submit", json=payload)
        assert r.status_code == 404


# ---- Intake happy-path (mock a paid transaction directly in DB) ----
class TestIntakeSubmitHappyPath:
    def _seed_paid(self, mongo, loop, purchase_source):
        sid = f"cs_test_seed_{uuid.uuid4().hex[:16]}"
        loop.run_until_complete(mongo.payment_transactions.insert_one({
            "session_id": sid, "purchase_source": purchase_source,
            "offer_source": purchase_source.replace("_497", "").replace("_project", "_project"),
            "amount": 49700 if "diy" in purchase_source else 199700,
            "currency": "usd", "status": "completed", "payment_status": "paid",
            "test_mode": True,
        }))
        return sid

    def test_intake_submit_and_upsert(self, client, db):
        mongo, loop = db
        sid = self._seed_paid(mongo, loop, "direct_board_recruitment_project")
        try:
            # context
            r = client.get(f"{BASE_URL}/api/board-recruitment-intake/context", params={"session_id": sid})
            assert r.status_code == 200, r.text
            ctx = r.json()
            assert ctx["eligible"] is True
            assert ctx["purchase_source"] == "direct_board_recruitment_project"
            assert ctx["calendly_url"] == "https://calendly.com/boardbuilder/recruitboard"
            assert ctx["submitted"] is False

            payload = {
                "session_id": sid,
                "your_name": "Test Founder", "email": f"test-{uuid.uuid4().hex[:6]}@example.com",
                "organization_name": "TEST Org", "website": "https://example.org",
                "mission": "Serve people.", "city": "New York", "state": "NY",
                "board_type": "Governing Board",
                "org_linkedin": "Yes", "org_linkedin_url": "https://linkedin.com/company/x",
                "personal_linkedin": "No", "personal_linkedin_url": "",
                "present_board": "5", "active_board": "3", "new_members_count": "3",
                "current_board_strengths": "Fundraising", "board_challenges": "Attendance",
                "desired_skills": ["Fundraising", "Legal"], "desired_skills_other": "",
                "accomplish": "Raise more money", "specific_wants": "",
                "meeting_frequency": "Monthly", "meeting_format": "Hybrid",
                "meeting_location": "NYC Office", "virtual_meeting_info": "Zoom",
                "board_term": "2 Years", "time_commitment": "10 hrs",
                "max_board_size": "15", "max_board_size_unknown": False,
                "application_deadline": "Open Until Positions Are Filled", "deadline_date": "",
                "anything_else": "",
            }
            r = client.post(f"{BASE_URL}/api/board-recruitment-intake/submit", json=payload)
            assert r.status_code == 201, r.text
            body = r.json()
            assert body["status"] == "submitted"
            assert body["redirect_url"] == "https://calendly.com/boardbuilder/recruitboard"

            row = loop.run_until_complete(mongo.board_recruitment_intakes.find_one({"session_id": sid}))
            assert row is not None
            assert row["organization_name"] == "TEST Org"
            assert row["purchase_source"] == "direct_board_recruitment_project"
            assert row["org_linkedin_url"] == "https://linkedin.com/company/x"

            # Resubmit must upsert (no duplicate)
            r = client.post(f"{BASE_URL}/api/board-recruitment-intake/submit", json=payload)
            assert r.status_code == 201
            count = loop.run_until_complete(mongo.board_recruitment_intakes.count_documents({"session_id": sid}))
            assert count == 1

            # context now reports submitted=True
            r = client.get(f"{BASE_URL}/api/board-recruitment-intake/context", params={"session_id": sid})
            assert r.json()["submitted"] is True
        finally:
            loop.run_until_complete(mongo.payment_transactions.delete_one({"session_id": sid}))
            loop.run_until_complete(mongo.board_recruitment_intakes.delete_many({"session_id": sid}))


# ---- Regression: public SPA routes load ----
class TestRoutes:
    @pytest.mark.parametrize("path", [
        "/", "/about-rooney", "/recruit-your-board-yourself",
        "/board-recruitment-proposal", "/board-recruitment-intake",
        "/recruit-with-rooney", "/recruit", "/reactivate", "/activate", "/join-a-board",
    ])
    def test_route_returns_html(self, client, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=15)
        assert r.status_code == 200, f"{path} returned {r.status_code}"
        assert "<div id=\"root\"" in r.text or "<div id='root'" in r.text
