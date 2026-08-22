"""Iteration 52 — Canonical recruitment funnel: /recruit -> /offer/recruitment -> Stripe -> intake.

Covers:
- POST /api/funnel-leads/recruitment (lead capture used by /recruit form)
- POST /api/payments/diy-checkout ($497) + cancel_path allow-list
- POST /api/payments/direct-project-checkout ($2,497) + cancel_path allow-list
- GET /api/board-recruitment-intake/context gating (bogus / missing session)
- POST /api/board-recruitment-intake/submit redirect routing (DIY vs DWY)
- Regression: reactivation-project-checkout default cancel_url fallback
"""
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
import stripe
from dotenv import dotenv_values
from pymongo import MongoClient

BACKEND_ENV = dotenv_values("/app/backend/.env")
FRONTEND_ENV = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or FRONTEND_ENV.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL") or BACKEND_ENV.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or BACKEND_ENV.get("DB_NAME")
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or BACKEND_ENV.get("STRIPE_SECRET_KEY")


@pytest.fixture(scope="module")
def client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def db():
    mongo = MongoClient(MONGO_URL)
    yield mongo[DB_NAME]
    mongo.close()


@pytest.fixture(scope="module")
def tracked(db):
    """Track inserted docs for cleanup."""
    sessions = []
    yield sessions
    for sid in sessions:
        db.payment_transactions.delete_many({"session_id": sid})
        db.board_recruitment_intakes.delete_many({"session_id": sid})


def seed_paid_transaction(db, tracked, purchase_source):
    session_id = f"cs_test_TEST_{uuid.uuid4().hex[:20]}"
    tracked.append(session_id)
    db.payment_transactions.insert_one({
        "session_id": session_id,
        "purchase_source": purchase_source,
        "payment_status": "paid",
        "status": "completed",
        "amount": 497.0 if "diy" in purchase_source else 2497.0,
        "currency": "usd",
        "email": "TEST_iter52@example.com",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return session_id


def intake_payload(session_id):
    return {
        "session_id": session_id,
        "your_name": "TEST Iter52",
        "email": "TEST_iter52@example.com",
        "organization_name": "TEST Iter52 Nonprofit",
        "mission": "Testing the canonical recruitment funnel end to end.",
        "city": "Austin",
        "state": "TX",
        "board_type": "Governing board",
    }


# ---------------- Funnel lead capture ----------------
class TestFunnelLead:
    def test_recruitment_lead_created(self, client):
        payload = {
            "name": "TEST Iter52 Lead",
            "email": f"TEST_iter52_{uuid.uuid4().hex[:8]}@example.com",
            "phone": "5125550123",
            "organization": "TEST Iter52 Org",
            "website": "",
            "city": "",
            "state_region": "",
            "country": "",
            "answers": {"new_members_needed": "3"},
        }
        response = client.post(f"{API}/funnel-leads/recruitment", json=payload)
        assert response.status_code in (200, 201), response.text
        data = response.json()
        assert data.get("lead_id")
        assert data.get("result_token")


# ---------------- Stripe checkout sessions ----------------
class TestCheckout:
    def test_diy_checkout_497_with_cancel_path(self, client):
        response = client.post(f"{API}/payments/diy-checkout", json={
            "origin_url": BASE_URL, "result_token": "", "cancel_path": "/offer/recruitment"})
        assert response.status_code == 200, response.text
        url = response.json().get("checkout_url")
        assert url and url.startswith("https://")
        session_id = response.json().get("session_id") or url.split("/pay/")[-1].split("#")[0]
        session = stripe.checkout.Session.retrieve(session_id)
        assert session.amount_total == 49700
        assert session.currency == "usd"
        assert session.success_url.endswith("/purchase/success?session_id={CHECKOUT_SESSION_ID}")
        assert session.cancel_url == f"{BASE_URL}/offer/recruitment?checkout=cancelled"

    def test_dwy_checkout_2497_with_cancel_path(self, client):
        response = client.post(f"{API}/payments/direct-project-checkout", json={
            "origin_url": BASE_URL, "result_token": "", "cancel_path": "/offer/recruitment"})
        assert response.status_code == 200, response.text
        url = response.json().get("checkout_url")
        session_id = response.json().get("session_id") or url.split("/pay/")[-1].split("#")[0]
        session = stripe.checkout.Session.retrieve(session_id)
        assert session.amount_total == 249700
        assert session.currency == "usd"
        assert session.success_url.endswith("/board-recruitment-intake?session_id={CHECKOUT_SESSION_ID}")
        assert session.cancel_url == f"{BASE_URL}/offer/recruitment?checkout=cancelled"

    def test_diy_checkout_rejects_unknown_cancel_path(self, client):
        """Unknown cancel_path must fall back to the default, not be echoed back."""
        response = client.post(f"{API}/payments/diy-checkout", json={
            "origin_url": BASE_URL, "cancel_path": "https://evil.example.com/steal"})
        assert response.status_code == 200, response.text
        url = response.json()["checkout_url"]
        session_id = response.json().get("session_id") or url.split("/pay/")[-1].split("#")[0]
        session = stripe.checkout.Session.retrieve(session_id)
        assert "evil.example.com" not in session.cancel_url
        assert session.cancel_url == f"{BASE_URL}/recruit-your-board-yourself?checkout=cancelled"

    def test_reactivation_project_checkout_default_cancel(self, client):
        response = client.post(f"{API}/payments/reactivation-project-checkout", json={"origin_url": BASE_URL})
        assert response.status_code == 200, response.text
        url = response.json()["checkout_url"]
        session_id = response.json().get("session_id") or url.split("/pay/")[-1].split("#")[0]
        session = stripe.checkout.Session.retrieve(session_id)
        assert session.cancel_url == f"{BASE_URL}/board-reactivation-proposal?checkout=cancelled"


# ---------------- Intake gating ----------------
class TestIntakeGating:
    def test_context_requires_session_id(self, client):
        response = client.get(f"{API}/board-recruitment-intake/context")
        assert response.status_code == 422

    def test_context_bogus_session_id(self, client):
        response = client.get(f"{API}/board-recruitment-intake/context", params={"session_id": "cs_test_bogus_iter52"})
        assert response.status_code == 404
        assert "qualifying purchase" in response.json()["detail"]

    def test_submit_bogus_session_id(self, client):
        response = client.post(f"{API}/board-recruitment-intake/submit", json=intake_payload("cs_test_bogus_iter52"))
        assert response.status_code == 404

    def test_unpaid_transaction_blocked(self, client, db, tracked):
        session_id = f"cs_test_TEST_{uuid.uuid4().hex[:20]}"
        tracked.append(session_id)
        db.payment_transactions.insert_one({
            "session_id": session_id, "purchase_source": "direct_diy_board_recruitment_497",
            "payment_status": "initiated", "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()})
        response = client.get(f"{API}/board-recruitment-intake/context", params={"session_id": session_id})
        assert response.status_code == 402, response.text


# ---------------- DWY post-payment path ----------------
class TestDwyPath:
    def test_context_and_submit_redirects_to_calendly(self, client, db, tracked):
        session_id = seed_paid_transaction(db, tracked, "direct_board_recruitment_project")

        context = client.get(f"{API}/board-recruitment-intake/context", params={"session_id": session_id})
        assert context.status_code == 200, context.text
        ctx = context.json()
        assert ctx["eligible"] is True
        assert ctx["purchase_source"] == "direct_board_recruitment_project"
        assert ctx["submitted"] is False
        assert ctx["calendly_url"] == "https://calendly.com/boardbuilder/recruitboard"

        submit = client.post(f"{API}/board-recruitment-intake/submit", json=intake_payload(session_id))
        assert submit.status_code == 201, submit.text
        assert submit.json()["redirect_url"] == "https://calendly.com/boardbuilder/recruitboard"

        # persistence: context now reports submitted
        after = client.get(f"{API}/board-recruitment-intake/context", params={"session_id": session_id})
        assert after.status_code == 200
        assert after.json()["submitted"] is True
        stored = db.board_recruitment_intakes.find_one({"session_id": session_id})
        assert stored is not None
        assert stored["organization_name"] == "TEST Iter52 Nonprofit"


# ---------------- DIY post-payment path ----------------
class TestDiyPath:
    def test_context_and_submit_redirects_to_start_here(self, client, db, tracked):
        session_id = seed_paid_transaction(db, tracked, "direct_diy_board_recruitment_497")

        context = client.get(f"{API}/board-recruitment-intake/context", params={"session_id": session_id})
        assert context.status_code == 200, context.text
        assert context.json()["purchase_source"] == "direct_diy_board_recruitment_497"

        submit = client.post(f"{API}/board-recruitment-intake/submit", json=intake_payload(session_id))
        assert submit.status_code == 201, submit.text
        assert submit.json()["redirect_url"] == "/recruitment-start-here"

    def test_submit_validation_rejects_missing_fields(self, client, db, tracked):
        session_id = seed_paid_transaction(db, tracked, "direct_diy_board_recruitment_497")
        response = client.post(f"{API}/board-recruitment-intake/submit", json={"session_id": session_id})
        assert response.status_code == 422
