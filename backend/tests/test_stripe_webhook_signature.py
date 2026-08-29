"""Independent verification of Stripe webhook signature handling + idempotency (preview env only)."""
import asyncio
import hashlib
import hmac
import json
import os
import time

import pytest
import requests
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")
WEBHOOK_URL = f"{BASE_URL}/api/stripe/webhook"
SECRET = backend_env.get("STRIPE_WEBHOOK_SECRET")
MONGO_URL = backend_env.get("MONGO_URL")
DB_NAME = backend_env.get("DB_NAME")
TEST_SESSION_ID = f"cs_wh_test_idem_{os.getpid()}"


def sign(payload: str, secret: str) -> str:
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def event_body(event_type: str, session_id: str, payment_status: str = "paid") -> str:
    return json.dumps({
        "id": "evt_test_webhook_qa",
        "object": "event",
        "type": event_type,
        "data": {"object": {
            "id": session_id,
            "object": "checkout.session",
            "payment_status": payment_status,
            "payment_intent": "pi_test_qa_123",
            "status": "complete",
            "customer_details": {"email": "TEST_qa_webhook@example.com"},
        }},
    })


def post_event(body: str, secret: str):
    return requests.post(
        WEBHOOK_URL,
        data=body.encode(),
        headers={"Content-Type": "application/json", "Stripe-Signature": sign(body, secret)},
        timeout=30,
    )


def mongo_find():
    async def _run():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            docs = await client[DB_NAME].payment_transactions.find(
                {"session_id": TEST_SESSION_ID}, {"_id": 0}
            ).to_list(10)
            return docs
        finally:
            client.close()
    return asyncio.get_event_loop().run_until_complete(_run())


def mongo_write(doc=None):
    async def _run():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            coll = client[DB_NAME].payment_transactions
            await coll.delete_many({"session_id": TEST_SESSION_ID})
            if doc:
                await coll.insert_one(doc)
        finally:
            client.close()
    asyncio.get_event_loop().run_until_complete(_run())


@pytest.fixture(scope="module", autouse=True)
def env_ready():
    assert SECRET, "STRIPE_WEBHOOK_SECRET missing in /app/backend/.env"
    assert MONGO_URL and DB_NAME
    yield
    mongo_write(None)  # cleanup


# --- Signature verification ---
class TestSignature:
    def test_valid_signature_returns_200(self):
        body = event_body("checkout.session.completed", "cs_test_qa_nonexistent_sig")
        r = post_event(body, SECRET)
        assert r.status_code == 200, r.text[:300]
        assert r.json() == {"status": "ok"}

    def test_wrong_secret_returns_400(self):
        body = event_body("checkout.session.completed", "cs_test_qa_nonexistent_sig")
        r = post_event(body, "whsec_totally_wrong_secret_value_qa")
        assert r.status_code == 400, r.text[:300]
        assert r.json().get("detail") == "Invalid Stripe signature"

    def test_unsigned_post_returns_400(self):
        body = event_body("checkout.session.completed", "cs_test_qa_nonexistent_sig")
        r = requests.post(WEBHOOK_URL, data=body.encode(),
                          headers={"Content-Type": "application/json"}, timeout=30)
        assert r.status_code == 400, r.text[:300]
        assert r.json().get("detail") == "Invalid Stripe signature"

    def test_tampered_body_returns_400(self):
        body = event_body("checkout.session.completed", "cs_test_qa_nonexistent_sig")
        headers = {"Content-Type": "application/json", "Stripe-Signature": sign(body, SECRET)}
        r = requests.post(WEBHOOK_URL, data=(body + " ").encode(), headers=headers, timeout=30)
        assert r.status_code == 400, r.text[:300]


# --- Idempotency of checkout.session.completed ---
class TestIdempotency:
    def test_replay_is_idempotent(self):
        mongo_write({
            "session_id": TEST_SESSION_ID,
            "purchase_source": "board_fix_system_497",
            "payment_status": "pending",
            "status": "initiated",
            "amount": 49700,
            "currency": "usd",
            "created_at": "2026-07-01T00:00:00+00:00",
            "updated_at": "2026-07-01T00:00:00+00:00",
        })
        body = event_body("checkout.session.completed", TEST_SESSION_ID)

        r1 = post_event(body, SECRET)
        assert r1.status_code == 200, r1.text[:300]
        docs = mongo_find()
        assert len(docs) == 1
        assert docs[0]["payment_status"] == "paid"
        assert docs[0]["status"] == "completed"
        assert docs[0]["stripe_payment_intent_id"] == "pi_test_qa_123"
        first_updated = docs[0]["updated_at"]

        time.sleep(1.2)
        r2 = post_event(body, SECRET)
        assert r2.status_code == 200, r2.text[:300]
        docs2 = mongo_find()
        assert len(docs2) == 1, f"duplicate docs created: {len(docs2)}"
        assert docs2[0]["payment_status"] == "paid"
        assert docs2[0]["status"] == "completed"
        assert docs2[0]["updated_at"] == first_updated, "replay overwrote paid transaction"

    def test_expired_event_accepted(self):
        r = post_event(event_body("checkout.session.expired", TEST_SESSION_ID), SECRET)
        assert r.status_code == 200, r.text[:300]

    def test_async_payment_failed_accepted(self):
        r = post_event(event_body("checkout.session.async_payment_failed",
                                  "cs_test_qa_nonexistent_sig", "unpaid"), SECRET)
        assert r.status_code == 200, r.text[:300]


# --- Production endpoint liveness (unsigned POST should be 400, not 5xx) ---
def test_production_endpoint_alive():
    url = "https://nonprofitboardbuilder.com/api/stripe/webhook"
    try:
        r = requests.post(url, data=b'{"id":"evt_qa","type":"ping"}',
                          headers={"Content-Type": "application/json"}, timeout=30)
    except requests.RequestException as exc:
        pytest.fail(f"production endpoint unreachable: {exc}")
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:300]}"
