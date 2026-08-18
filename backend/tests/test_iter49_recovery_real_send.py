"""Iteration 49: REAL end-to-end Checkout Recovery send test.

Proves the recovery pipeline with a REAL Stripe test session + ACTUAL Resend
send to the safe delivered@resend.dev inbox, behind CHECKOUT_RECOVERY_ENABLED=false
(function invoked directly; env flag never flipped).
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
import requests
import stripe
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")
from checkout_recovery import (  # noqa: E402
    build_recovery_html,
    process_abandoned_checkouts,
    recovery_enabled,
)
from content_templates import checkout_recovery_email  # noqa: E402

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
ORIGIN = BASE_URL
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

QA_EMAIL = "delivered@resend.dev"
QA_LEAD_PREFIX = "qa-recovery-iter49-"
QA_TXN_PREFIX = "cs_test_qa_recovery_iter49_"  # for our own synthetic txns; real txns will have real session ids we also track

ALL_MATCH_ANSWERS = {
    "present_board": 6, "active_board": 2, "need_recruit": "Yes",
    "reactivate_inactive": "Yes — some of them",
    "board_fundraising_now": "Very little", "want_fundraising": "Yes",
}


# module-level state passed between tests
_state: dict = {}


def _submit_bt_assessment(email: str) -> dict:
    payload = {
        "name": "QA Recovery Iter49",
        "email": email,
        "phone": "555-0149",
        "organization": "QA Recovery Iter49 Org",
        "city": "Testville",
        "state_region": "QA",
        "country": "USA",
        "answers": ALL_MATCH_ANSWERS,
    }
    r = requests.post(f"{API}/funnel-leads/board_transformation", json=payload, timeout=30)
    assert r.status_code == 201, f"submit failed {r.status_code}: {r.text[:300]}"
    return r.json()


async def _mongo():
    client = AsyncIOMotorClient(MONGO_URL)
    return client, client[DB_NAME]


# ---------- FLAG SAFETY (must remain false) ----------
def test_recovery_enabled_flag_is_false():
    assert recovery_enabled() is False, "CHECKOUT_RECOVERY_ENABLED must remain false"


# ---------- 1. REAL Stripe session + REAL Resend send ----------
def test_real_stripe_session_created_and_backdated():
    lead = _submit_bt_assessment(f"{QA_LEAD_PREFIX}real@example.com")
    _state["lead_id"] = lead["lead_id"]
    _state["result_token"] = lead["result_token"]

    # BUT the recovery email needs lead_email == QA_EMAIL (delivered@resend.dev).
    # The lead was submitted with the qa- prefixed email; we override the lead_email on the txn
    # by directly mongo-updating after checkout creation.
    r = requests.post(
        f"{API}/payments/diy-checkout",
        json={"origin_url": ORIGIN, "result_token": lead["result_token"]},
        timeout=45,
    )
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    session_id = body["session_id"]
    assert session_id.startswith("cs_test_"), session_id
    _state["real_session_id"] = session_id

    # Force lead_email to delivered@resend.dev on the txn and backdate created_at.
    async def _prep():
        client, db = await _mongo()
        old_iso = (datetime.now(timezone.utc) - timedelta(minutes=75)).isoformat()
        res = await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"lead_email": QA_EMAIL, "lead_name": "QA Recovery Iter49",
                      "created_at": old_iso}},
        )
        assert res.matched_count == 1
        doc = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        client.close()
        return doc
    doc = asyncio.run(_prep())
    assert doc["origin_url"] == ORIGIN
    assert doc["offer_source"] == "direct_diy_board_recruitment"
    assert doc["payment_status"] == "pending"


def test_stripe_recheck_returns_unpaid_open_for_real_session():
    # Ensure the Stripe API can retrieve the real session (recovery code path executes normally).
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    session = stripe.checkout.Session.retrieve(_state["real_session_id"])
    assert session.payment_status != "paid"
    assert session.status != "complete"


@pytest.mark.asyncio
async def test_process_abandoned_checkouts_sends_real_email():
    client, db = await _mongo()
    try:
        sent = await process_abandoned_checkouts(db)
        doc = await db.payment_transactions.find_one(
            {"session_id": _state["real_session_id"]}, {"_id": 0}
        )
        assert doc is not None
        status = doc.get("recovery_email_status")
        # PRIMARY assertion — the whole point of iter 49
        if status != "sent":
            pytest.fail(
                f"Recovery email did NOT send. status={status!r} "
                f"error={doc.get('recovery_email_error')!r}"
            )
        assert doc.get("recovery_email_id"), "recovery_email_id empty despite 'sent'"
        assert doc.get("recovery_email_at"), "recovery_email_at not set"
        _state["recovery_email_id"] = doc["recovery_email_id"]
        _state["recovery_email_at"] = doc["recovery_email_at"]
        assert sent >= 1
    finally:
        client.close()


# ---------- 2. EMAIL CONTENT CORRECTNESS ----------
def test_email_content_and_html_build():
    # Build the same message the pipeline built for the real send.
    first_name = "QA"
    offer_name = "Recruit New Board Members"
    offer_path = "/offer/recruitment"
    offer_link = f"{ORIGIN}{offer_path}"
    msg = checkout_recovery_email(first_name, "QA Recovery Iter49 Org", offer_name, offer_link)

    assert msg["subject"] == "You started building your board — your next step is ready"
    assert msg["body"].startswith(f"Hi {first_name},")
    assert offer_name in msg["body"]
    assert offer_link in msg["body"]
    assert "Rooney Akpesiri" in msg["body"]

    html_out = build_recovery_html(msg["body"], offer_link)
    # Anchor rendered
    expected_anchor_open = f'<a href="{offer_link}"'
    assert expected_anchor_open in html_out, html_out[:500]
    assert f'>{offer_link}</a>' in html_out
    # Link host equals origin_url host (not blank / not just a path)
    from urllib.parse import urlparse
    assert urlparse(offer_link).netloc == urlparse(ORIGIN).netloc
    assert urlparse(offer_link).netloc != ""


# ---------- 3. SINGLE-SEND GUARANTEE (idempotent + dedupe) ----------
@pytest.mark.asyncio
async def test_second_run_does_not_resend_same_txn():
    client, db = await _mongo()
    try:
        before = await db.payment_transactions.find_one(
            {"session_id": _state["real_session_id"]}, {"_id": 0}
        )
        assert before.get("recovery_email_status") == "sent"
        before_id = before["recovery_email_id"]
        before_at = before["recovery_email_at"]

        sent = await process_abandoned_checkouts(db)
        # No new sends for this txn
        after = await db.payment_transactions.find_one(
            {"session_id": _state["real_session_id"]}, {"_id": 0}
        )
        assert after["recovery_email_id"] == before_id, "email id should not change"
        assert after["recovery_email_at"] == before_at, "email timestamp should not change"
        # (sent may include unrelated txns — we don't assert 0 globally; just this txn didn't resend)
    finally:
        client.close()


@pytest.mark.asyncio
async def test_second_pending_same_email_becomes_skipped():
    client, db = await _mongo()
    try:
        old_iso = (datetime.now(timezone.utc) - timedelta(minutes=75)).isoformat()
        second_id = f"{QA_TXN_PREFIX}2nd_pending"
        await db.payment_transactions.delete_one({"session_id": second_id})
        await db.payment_transactions.insert_one({
            "session_id": second_id, "lead_email": QA_EMAIL,
            "lead_name": "QA Recovery Iter49", "lead_organization": "QA",
            "offer_source": "direct_diy_board_reactivation", "payment_status": "pending",
            "status": "initiated", "created_at": old_iso, "updated_at": old_iso,
            "origin_url": ORIGIN, "amount": 49700, "currency": "usd",
        })
        await process_abandoned_checkouts(db)
        doc = await db.payment_transactions.find_one({"session_id": second_id}, {"_id": 0})
        # Real Stripe retrieve for a fake session id will fail → warning path continues
        # dedupe check finds an already-sent txn for same email → 'skipped'
        assert doc.get("recovery_email_status") == "skipped", (
            f"expected 'skipped', got {doc.get('recovery_email_status')!r} "
            f"error={doc.get('recovery_email_error')!r}"
        )
    finally:
        client.close()


# ---------- 4. PAID CUSTOMER GUARD ----------
@pytest.mark.asyncio
async def test_paid_customer_pending_becomes_skipped():
    client, db = await _mongo()
    try:
        old_iso = (datetime.now(timezone.utc) - timedelta(minutes=75)).isoformat()
        paid_email = f"{QA_LEAD_PREFIX}paid@resend-test.local"
        paid_id = f"{QA_TXN_PREFIX}paidguard_paid"
        pending_id = f"{QA_TXN_PREFIX}paidguard_pending"
        await db.payment_transactions.delete_many({"session_id": {"$in": [paid_id, pending_id]}})
        await db.payment_transactions.insert_many([
            {"session_id": paid_id, "lead_email": paid_email,
             "payment_status": "paid", "status": "completed",
             "offer_source": "direct_diy_board_activation",
             "created_at": old_iso, "updated_at": old_iso},
            {"session_id": pending_id, "lead_email": paid_email,
             "lead_name": "QA Paid Iter49", "offer_source": "direct_diy_board_activation",
             "payment_status": "pending", "status": "initiated",
             "created_at": old_iso, "updated_at": old_iso, "origin_url": ORIGIN,
             "amount": 49700, "currency": "usd"},
        ])
        await process_abandoned_checkouts(db)
        pending = await db.payment_transactions.find_one({"session_id": pending_id}, {"_id": 0})
        assert pending.get("recovery_email_status") == "skipped", pending.get("recovery_email_status")
    finally:
        client.close()


# ---------- 5. LIVE BACKGROUND LOOP DID NOT TOUCH NON-QA DATA ----------
@pytest.mark.asyncio
async def test_no_stray_recovery_emails_on_real_prod_data():
    client, db = await _mongo()
    try:
        # Any txn that has a recovery_email_status and does NOT belong to qa/test prefixes = LEAK.
        cursor = db.payment_transactions.find(
            {
                "recovery_email_status": {"$exists": True},
                "session_id": {"$not": {"$regex": "^(cs_test_qa_recovery_|cs_test_)"}},
                "lead_email": {"$not": {"$regex": "^qa-recovery-"}},
            },
            {"_id": 0, "session_id": 1, "lead_email": 1, "recovery_email_status": 1},
        )
        leaks = [d async for d in cursor]
        # Exclude the delivered@resend.dev test address explicitly (created by this test)
        leaks = [d for d in leaks if d.get("lead_email") != QA_EMAIL]
        assert leaks == [], f"stray recovery emails found: {leaks[:5]}"
    finally:
        client.close()


def test_env_flag_still_false_after_all_tests():
    with open("/app/backend/.env", "r") as f:
        content = f.read()
    assert "CHECKOUT_RECOVERY_ENABLED=false" in content
    assert "CHECKOUT_RECOVERY_ENABLED=true" not in content
    assert recovery_enabled() is False


# ---------- CLEANUP ----------
def teardown_module(module):
    async def _clean():
        client, db = await _mongo()
        # Expire the real Stripe test session so no lingering open session
        try:
            sid = _state.get("real_session_id")
            if sid:
                stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
                try:
                    await asyncio.to_thread(stripe.checkout.Session.expire, sid)
                except Exception:
                    pass
                await db.payment_transactions.delete_many({"session_id": sid})
        except Exception:
            pass
        await db.funnel_leads.delete_many({"email": {"$regex": f"^{QA_LEAD_PREFIX}"}})
        await db.payment_transactions.delete_many({"lead_email": {"$regex": f"^{QA_LEAD_PREFIX}"}})
        await db.payment_transactions.delete_many({"lead_email": QA_EMAIL})
        await db.payment_transactions.delete_many({"session_id": {"$regex": f"^{QA_TXN_PREFIX}"}})
        client.close()
    asyncio.run(_clean())
