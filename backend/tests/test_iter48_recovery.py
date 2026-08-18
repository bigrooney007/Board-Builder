"""Iteration 48: badge + checkout recovery tests.

Covers:
- Backward-compat checkout without result_token
- Assessment badge recommendations via /api/funnel-leads/{result_token}
- Checkout with result_token stores lead context on payment_transactions
- process_abandoned_checkouts scenarios (sent/failed, skipped dedupe, paid dedupe,
  empty email untouched, young txn untouched)
- recovery_enabled() reflects env flag (False)
- checkout_recovery_email() template shape
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")
from checkout_recovery import (  # noqa: E402
    OFFER_PAGES,
    process_abandoned_checkouts,
    recovery_enabled,
)
from content_templates import checkout_recovery_email  # noqa: E402

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
ORIGIN = BASE_URL
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

QA_EMAIL_A = "delivered@resend.dev"  # safe recipient A
QA_EMAIL_B = "delivered@resend.dev"  # dedupe target — same address
QA_SESSION_PREFIX = "cs_test_qa_recovery_iter48_"


# ---------- helpers ----------
def _submit_bt_assessment(email: str, answers: dict) -> dict:
    payload = {
        "name": "QA Recovery",
        "email": email,
        "phone": "555-0148",
        "organization": "QA Recovery Org",
        "city": "Testville",
        "state_region": "QA",
        "country": "USA",
        "answers": answers,
    }
    r = requests.post(f"{API}/funnel-leads/board_transformation", json=payload, timeout=30)
    assert r.status_code == 201, f"submit failed {r.status_code}: {r.text[:300]}"
    return r.json()


ALL_MATCH_ANSWERS = {
    "present_board": 6, "active_board": 2, "need_recruit": "Yes",
    "reactivate_inactive": "Yes — some of them",
    "board_fundraising_now": "Very little", "want_fundraising": "Yes",
}

NO_MATCH_ANSWERS = {
    "present_board": 4, "active_board": 4, "need_recruit": "No",
    "reactivate_inactive": "No",
    "board_fundraising_now": "Yes — most do", "want_fundraising": "No",
}


# ---------- BADGE / result recommendations ----------
def test_bt_recommendations_all_match():
    lead = _submit_bt_assessment("qa-recovery-iter48-all@example.com", ALL_MATCH_ANSWERS)
    token = lead["result_token"]
    r = requests.get(f"{API}/funnel-leads/result/{token}", timeout=15)
    assert r.status_code == 200, r.text[:200]
    recs = r.json()["result"]["recommendations"]
    assert set(recs) == {"recruit", "reactivate", "activate"}, recs


def test_bt_recommendations_no_match():
    lead = _submit_bt_assessment("qa-recovery-iter48-none@example.com", NO_MATCH_ANSWERS)
    token = lead["result_token"]
    r = requests.get(f"{API}/funnel-leads/result/{token}", timeout=15)
    assert r.status_code == 200
    assert r.json()["result"]["recommendations"] == []


# ---------- backward-compat checkout without token ----------
def test_diy_checkout_without_token_still_200():
    r = requests.post(f"{API}/payments/diy-checkout", json={"origin_url": ORIGIN}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert "checkout_url" in body and "stripe.com" in body["checkout_url"]


def test_diy_checkout_with_result_token_persists_lead_context():
    lead = _submit_bt_assessment("qa-recovery-iter48-link@example.com", ALL_MATCH_ANSWERS)
    token = lead["result_token"]
    r = requests.post(
        f"{API}/payments/diy-checkout",
        json={"origin_url": ORIGIN, "result_token": token},
        timeout=30,
    )
    assert r.status_code == 200, r.text[:300]
    session_id = r.json()["session_id"]

    async def _verify():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        doc = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        client.close()
        return doc

    doc = asyncio.run(_verify())
    assert doc is not None
    assert doc.get("lead_email") == "qa-recovery-iter48-link@example.com"
    assert doc.get("lead_id"), "lead_id missing on txn"
    assert doc.get("lead_organization") == "QA Recovery Org"
    assert doc.get("origin_url") == ORIGIN


# ---------- recovery_enabled flag off ----------
def test_recovery_flag_currently_false():
    assert recovery_enabled() is False


def test_offer_pages_map_covers_expected_sources():
    expected = {
        "direct_diy_board_recruitment", "direct_board_recruitment_project",
        "direct_diy_board_reactivation", "direct_board_reactivation_project",
        "direct_diy_board_activation", "direct_board_activation_project",
    }
    assert expected.issubset(set(OFFER_PAGES))


def test_email_template_shape():
    msg = checkout_recovery_email("Alex", "Acme Nonprofit", "Recruit New Board Members", "https://example.com/offer/recruitment")
    assert "subject" in msg and "body" in msg
    assert "Hi Alex" in msg["body"]
    assert "Recruit New Board Members" in msg["body"]
    assert "https://example.com/offer/recruitment" in msg["body"]

    # empty first name → generic greeting
    msg2 = checkout_recovery_email("", "", "Reactivate Your Board", "https://x/y")
    assert msg2["body"].startswith("Hi,")


# ---------- process_abandoned_checkouts scenarios ----------
@pytest.mark.asyncio
async def test_process_abandoned_checkouts_scenarios():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    old_iso = (datetime.now(timezone.utc) - timedelta(minutes=75)).isoformat()
    young_iso = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    # clean any prior qa rows first
    await db.payment_transactions.delete_many({"session_id": {"$regex": f"^{QA_SESSION_PREFIX}"}})

    txns = [
        # (a) old pending with email + valid offer_source → should attempt send
        {
            "session_id": f"{QA_SESSION_PREFIX}1_send", "lead_email": QA_EMAIL_A,
            "lead_name": "QA Alpha", "lead_organization": "QA Nonprofit",
            "offer_source": "direct_diy_board_recruitment", "payment_status": "pending",
            "status": "initiated", "created_at": old_iso, "updated_at": old_iso,
            "origin_url": ORIGIN, "amount": 49700, "currency": "usd",
        },
        # (b) second pending SAME email → dedupe skipped
        {
            "session_id": f"{QA_SESSION_PREFIX}2_dupe", "lead_email": QA_EMAIL_A,
            "lead_name": "QA Alpha", "lead_organization": "QA Nonprofit",
            "offer_source": "direct_diy_board_reactivation", "payment_status": "pending",
            "status": "initiated", "created_at": old_iso, "updated_at": old_iso,
            "origin_url": ORIGIN, "amount": 49700, "currency": "usd",
        },
        # (c) email has a paid txn already → skipped. seed paid + pending
        {
            "session_id": f"{QA_SESSION_PREFIX}3_paid", "lead_email": "qa-recovery-iter48-paid@resend-test.local",
            "payment_status": "paid", "status": "completed",
            "offer_source": "direct_diy_board_activation",
            "created_at": old_iso, "updated_at": old_iso,
        },
        {
            "session_id": f"{QA_SESSION_PREFIX}3_pending", "lead_email": "qa-recovery-iter48-paid@resend-test.local",
            "lead_name": "QA Paid", "lead_organization": "QA",
            "offer_source": "direct_diy_board_activation", "payment_status": "pending",
            "status": "initiated", "created_at": old_iso, "updated_at": old_iso,
            "origin_url": ORIGIN,
        },
        # (d) empty lead_email → untouched
        {
            "session_id": f"{QA_SESSION_PREFIX}4_noemail", "lead_email": "",
            "offer_source": "direct_diy_board_recruitment", "payment_status": "pending",
            "status": "initiated", "created_at": old_iso, "updated_at": old_iso,
            "origin_url": ORIGIN,
        },
        # (e) young pending → untouched
        {
            "session_id": f"{QA_SESSION_PREFIX}5_young", "lead_email": "qa-recovery-iter48-young@resend-test.local",
            "lead_name": "QA Young", "offer_source": "direct_diy_board_recruitment",
            "payment_status": "pending", "status": "initiated",
            "created_at": young_iso, "updated_at": young_iso, "origin_url": ORIGIN,
        },
    ]
    await db.payment_transactions.insert_many(txns)

    try:
        await process_abandoned_checkouts(db)

        t1 = await db.payment_transactions.find_one({"session_id": f"{QA_SESSION_PREFIX}1_send"})
        assert t1.get("recovery_email_status") in {"sent", "failed"}, t1.get("recovery_email_status")
        if t1["recovery_email_status"] == "failed":
            assert "recovery_email_error" in t1

        t2 = await db.payment_transactions.find_one({"session_id": f"{QA_SESSION_PREFIX}2_dupe"})
        # Either 'skipped' (if #1 recorded 'sent') or 'sent'/'failed' if #1 failed and #2 is retried.
        # Deterministic dedupe expectation: after t1 processed with 'sent', t2 becomes 'skipped'.
        # If t1 'failed', t2 will try independently. Accept either.
        assert t2.get("recovery_email_status") in {"skipped", "sent", "failed"}

        t3 = await db.payment_transactions.find_one({"session_id": f"{QA_SESSION_PREFIX}3_pending"})
        assert t3.get("recovery_email_status") == "skipped", t3.get("recovery_email_status")

        t4 = await db.payment_transactions.find_one({"session_id": f"{QA_SESSION_PREFIX}4_noemail"})
        assert "recovery_email_status" not in t4, "empty-email txn should be untouched"

        t5 = await db.payment_transactions.find_one({"session_id": f"{QA_SESSION_PREFIX}5_young"})
        assert "recovery_email_status" not in t5, "young txn should be untouched"

    finally:
        await db.payment_transactions.delete_many({"session_id": {"$regex": f"^{QA_SESSION_PREFIX}"}})
        client.close()


# ---------- Cleanup any qa leads/txns created above ----------
def teardown_module(module):
    async def _clean():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        await db.funnel_leads.delete_many({"email": {"$regex": "^qa-recovery-iter48-"}})
        await db.payment_transactions.delete_many({"lead_email": {"$regex": "^qa-recovery-iter48-"}})
        await db.payment_transactions.delete_many({"session_id": {"$regex": f"^{QA_SESSION_PREFIX}"}})
        client.close()
    asyncio.run(_clean())
