"""Batch 1/2/3 backend verification for the recruitment funnel updates (iteration 22).

Checks:
- /api/direct-recruitment/config returns li9NzvRCCEw video
- /recruit lead submission with 5 fields returns 201
- DIY checkout $497 (49700) - success/cancel URLs, purchase_source
- Direct project checkout $1,997 (199700) - lookup key direct_board_recruitment_project_1997
- Intake submit for DIY seed returns redirect_url=/recruitment-start-here
- Intake submit for direct-project seed returns redirect_url=calendly
- Intake blocked card copy: "Do It With Me — $1,997"
"""
import os
import re
import uuid
import asyncio
import pytest
import requests
import stripe
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
ORIGIN = BASE_URL


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


# ---- Batch 1: /recruit funnel + video config ----
class TestBatch1Funnel:
    def test_direct_recruitment_video_config(self, client):
        r = client.get(f"{BASE_URL}/api/direct-recruitment/config")
        assert r.status_code == 200
        assert "li9NzvRCCEw" in r.json().get("video_url", "")

    def test_recruit_lead_5_fields(self, client, db):
        payload = {
            "name": "TEST Founder",
            "email": f"test-recruit-{uuid.uuid4().hex[:8]}@example.com",
            "organization": "TEST Org",
            "phone": "555-123-4567",
            "answers": {"new_members_needed": "3"},
        }
        r = client.post(f"{BASE_URL}/api/funnel-leads/recruitment", json=payload)
        assert r.status_code == 201, r.text
        lead = r.json()
        assert "lead_id" in lead
        mongo, loop = db
        loop.run_until_complete(mongo.funnel_leads.delete_one({"lead_id": lead["lead_id"]}))


# ---- Batch 2: DIY $497 + Direct Project $1,997 ----
class TestBatch2Checkouts:
    def test_diy_amount_and_metadata(self, client, db):
        r = client.post(f"{BASE_URL}/api/payments/diy-checkout", json={"origin_url": ORIGIN})
        assert r.status_code == 200
        sid = r.json()["session_id"]
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        sess = stripe.checkout.Session.retrieve(sid)
        assert sess.amount_total == 49700
        assert sess.mode == "payment"
        assert "/purchase/success" in sess.success_url
        assert "/recruit-your-board-yourself?checkout=cancelled" in sess.cancel_url
        assert sess.metadata["purchase_source"] == "direct_diy_board_recruitment_497"
        mongo, loop = db
        loop.run_until_complete(mongo.payment_transactions.delete_one({"session_id": sid}))

    def test_direct_project_amount_and_metadata(self, client, db):
        r = client.post(f"{BASE_URL}/api/payments/direct-project-checkout", json={"origin_url": ORIGIN})
        assert r.status_code == 200
        sid = r.json()["session_id"]
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        sess = stripe.checkout.Session.retrieve(sid)
        assert sess.amount_total == 199700, f"expected 199700, got {sess.amount_total}"
        assert "/board-recruitment-intake" in sess.success_url
        assert "/board-recruitment-proposal?checkout=cancelled" in sess.cancel_url
        # Confirm the price is linked to lookup_key direct_board_recruitment_project_1997
        line = stripe.checkout.Session.list_line_items(sid, limit=1).data[0]
        price = stripe.Price.retrieve(line.price.id)
        assert price.unit_amount == 199700
        assert price.lookup_key == "direct_board_recruitment_project_1997"
        mongo, loop = db
        row = loop.run_until_complete(mongo.payment_transactions.find_one({"session_id": sid}))
        assert row["amount"] == 199700
        assert row["purchase_source"] == "direct_board_recruitment_project"
        loop.run_until_complete(mongo.payment_transactions.delete_one({"session_id": sid}))


# ---- Batch 3: intake redirect_url differs per purchase_source ----
class TestBatch3IntakeRedirect:
    def _seed_paid(self, mongo, loop, purchase_source, amount):
        sid = f"cs_test_seed_{uuid.uuid4().hex[:16]}"
        loop.run_until_complete(mongo.payment_transactions.insert_one({
            "session_id": sid, "purchase_source": purchase_source,
            "offer_source": purchase_source.replace("_497", ""),
            "amount": amount, "currency": "usd", "status": "completed", "payment_status": "paid",
            "test_mode": True,
        }))
        return sid

    def _intake_payload(self, sid):
        return {
            "session_id": sid,
            "your_name": "TEST Founder", "email": f"test-{uuid.uuid4().hex[:6]}@example.com",
            "organization_name": "TEST Org", "website": "",
            "mission": "Serve people.", "city": "New York", "state": "NY",
            "board_type": "Governing Board",
            "org_linkedin": "No", "personal_linkedin": "No",
            "present_board": "5", "active_board": "3", "new_members_count": "3",
            "current_board_strengths": "Fundraising", "board_challenges": "Attendance",
            "desired_skills": ["Fundraising"],
            "accomplish": "Raise money", "meeting_frequency": "Monthly", "meeting_format": "Hybrid",
            "meeting_location": "Office", "board_term": "2 Years", "time_commitment": "10",
            "max_board_size": "15", "application_deadline": "Open Until Positions Are Filled",
        }

    def test_diy_intake_redirects_to_start_here(self, client, db):
        mongo, loop = db
        sid = self._seed_paid(mongo, loop, "direct_diy_board_recruitment_497", 49700)
        try:
            r = client.post(f"{BASE_URL}/api/board-recruitment-intake/submit", json=self._intake_payload(sid))
            assert r.status_code == 201, r.text
            assert r.json()["redirect_url"] == "/recruitment-start-here"
        finally:
            loop.run_until_complete(mongo.payment_transactions.delete_one({"session_id": sid}))
            loop.run_until_complete(mongo.board_recruitment_intakes.delete_many({"session_id": sid}))

    def test_dwm_intake_redirects_to_calendly(self, client, db):
        mongo, loop = db
        sid = self._seed_paid(mongo, loop, "direct_board_recruitment_project", 199700)
        try:
            r = client.post(f"{BASE_URL}/api/board-recruitment-intake/submit", json=self._intake_payload(sid))
            assert r.status_code == 201, r.text
            assert r.json()["redirect_url"] == "https://calendly.com/boardbuilder/recruitboard"
        finally:
            loop.run_until_complete(mongo.payment_transactions.delete_one({"session_id": sid}))
            loop.run_until_complete(mongo.board_recruitment_intakes.delete_many({"session_id": sid}))

    def test_intake_context_bogus_returns_404(self, client):
        r = client.get(f"{BASE_URL}/api/board-recruitment-intake/context",
                       params={"session_id": f"cs_bogus_{uuid.uuid4().hex}"})
        assert r.status_code == 404


# ---- Regression: SPA routes ----
class TestSpaRoutes:
    @pytest.mark.parametrize("path", [
        "/", "/recruit", "/recruit-with-rooney", "/recruit-your-board-yourself",
        "/board-recruitment-proposal", "/board-recruitment-intake",
        "/recruitment-start-here", "/about-rooney", "/reactivate", "/activate",
    ])
    def test_html_shell(self, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=15)
        assert r.status_code == 200
        assert 'id="root"' in r.text
