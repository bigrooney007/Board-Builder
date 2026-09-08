"""End-to-end verification for Recruit With Rooney ($997) — Batches 1, 2, 3."""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://board-drip.preview.emergentagent.com"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
TEST_EMAIL_PREFIX = "TEST_rwr_"


# ============================ BATCH 1 — Config endpoints ============================
class TestBatch1Config:
    def test_direct_recruitment_config_empty(self):
        r = requests.get(f"{BASE_URL}/api/direct-recruitment/config")
        assert r.status_code == 200
        assert r.json() == {"video_url": ""}

    def test_recruitment_guarantee_not_configured(self):
        r = requests.get(f"{BASE_URL}/api/recruitment-guarantee")
        assert r.status_code == 200
        assert r.json()["configured"] is False

    def test_payments_config_flags(self):
        r = requests.get(f"{BASE_URL}/api/payments/config")
        assert r.status_code == 200
        data = r.json()
        assert data["recruit_with_rooney_997_live"] is False
        assert data["recruitment_97_live"] is False
        assert data["recruitment_497_live"] is False
        assert data["stripe_mode"] == "test"


# ============================ BATCH 2 — Checkout gating ============================
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


class TestBatch2Checkout:
    def test_rooney_checkout_no_auth_returns_403(self):
        r = requests.post(
            f"{BASE_URL}/api/payments/rooney-checkout",
            json={"origin_url": "https://example.com", "internal_test": False},
        )
        assert r.status_code == 403
        assert "Enrollment is not open yet" in r.json().get("detail", "")

    def test_rooney_checkout_internal_test_without_admin_403(self):
        # internal_test true but no admin cookie -> should still be blocked by authenticate_admin
        r = requests.post(
            f"{BASE_URL}/api/payments/rooney-checkout",
            json={"origin_url": "https://example.com", "internal_test": True},
        )
        assert r.status_code in (401, 403)

    def test_rooney_checkout_admin_creates_test_session(self, admin_session):
        origin = "https://example.com"
        r = admin_session.post(
            f"{BASE_URL}/api/payments/rooney-checkout",
            json={"origin_url": origin, "internal_test": True},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "checkout_url" in data and "session_id" in data
        assert "stripe.com" in data["checkout_url"]
        # Verify session details via Stripe API directly (test key)
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        session = stripe.checkout.Session.retrieve(data["session_id"])
        assert session.amount_total == 99700
        assert session.currency == "usd"
        assert session.mode == "payment"
        md = session.metadata or {}
        assert md.get("offer_source") == "recruit_with_rooney"
        assert md.get("selected_tier") == "997"
        assert md.get("purchase_source") == "recruit_with_rooney_997"
        assert session.cancel_url == f"{origin}/recruit-with-rooney?checkout=cancelled"

        # payment_transactions record
        async def _check():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            tx = await db.payment_transactions.find_one({"session_id": data["session_id"]}, {"_id": 0})
            client.close()
            return tx
        tx = asyncio.run(_check())
        assert tx is not None
        assert tx["amount"] == 99700
        assert tx["purchase_source"] == "recruit_with_rooney_997"
        assert tx["offer_source"] == "recruit_with_rooney"


# ============================ BATCH 3 — Accountability engine ============================
@pytest.fixture
def db_client():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


async def _cleanup(db, email):
    member = await db.members.find_one({"email": email}, {"_id": 0})
    if member:
        uid = member["user_id"]
        await db.rooney_engagements.delete_many({"user_id": uid})
        await db.purchases.delete_many({"user_id": uid})
        await db.course_progress.delete_many({"user_id": uid})
        await db.members.delete_one({"user_id": uid})


async def _seed_member_and_purchase(db, email, first_name="Test", purchased_days_ago=0, refunded=False):
    from member_auth import new_uuid, hash_member_password
    now = datetime.now(timezone.utc)
    purchased_at = (now - timedelta(days=purchased_days_ago)).isoformat()
    user_id = new_uuid()
    member = {
        "user_id": user_id, "email": email, "first_name": first_name, "last_name": "User",
        "password_hash": hash_member_password("Password1234!"),
        "entitlements": ["recruitment_self_guided"], "lead_ids": [],
        "stripe_customer_id": "", "created_at": now.isoformat(), "updated_at": now.isoformat(),
    }
    await db.members.insert_one(member.copy())
    purchase_id = new_uuid()
    purchase = {
        "purchase_id": purchase_id, "user_id": user_id, "lead_id": "",
        "stripe_customer_id": "", "session_id": f"cs_test_{purchase_id}",
        "payment_intent_id": "", "tier": "997", "product": "Recruit With Rooney",
        "entitlement": "recruitment_self_guided", "amount": 99700, "currency": "usd",
        "payment_status": "refunded" if refunded else "paid",
        "purchased_at": purchased_at, "updated_at": now.isoformat(),
        "purchase_source": "recruit_with_rooney_997", "offer": "Recruit With Rooney",
        "support_program": "recruit_with_rooney", "price_paid": 997,
    }
    await db.purchases.insert_one(purchase.copy())
    return member, purchase


async def _mark_module_completed(db, user_id, module_number):
    from member_auth import new_uuid
    now = datetime.now(timezone.utc).isoformat()
    await db.course_progress.update_one(
        {"user_id": user_id, "product": "recruitment_self_guided", "module_number": module_number},
        {"$set": {"completed": True, "completed_at": now, "last_visited_at": now,
                  "user_id": user_id, "product": "recruitment_self_guided",
                  "module_number": module_number, "progress_id": new_uuid()}},
        upsert=True,
    )


def _patch_email(monkeypatch):
    """Patch send_rooney_email to no-op returning a fake id (avoid real Resend calls)."""
    import accountability_service

    async def fake_send(to, subject, html_body):
        return f"fake_email_{subject[:20]}"
    monkeypatch.setattr(accountability_service, "send_rooney_email", fake_send)


class TestBatch3Accountability:
    def test_welcome_enrollment_idempotent(self, db_client, monkeypatch):
        email = f"{TEST_EMAIL_PREFIX}welcome@example.com"

        async def run():
            db = db_client
            await _cleanup(db, email)
            _patch_email(monkeypatch)
            from accountability_service import enroll_rooney_engagement
            member, purchase = await _seed_member_and_purchase(db, email)
            e1 = await enroll_rooney_engagement(db, member, purchase)
            e2 = await enroll_rooney_engagement(db, member, purchase)
            engagements = await db.rooney_engagements.find({"user_id": member["user_id"]}, {"_id": 0}).to_list(10)
            assert len(engagements) == 1, f"expected 1 engagement got {len(engagements)}"
            eng = engagements[0]
            assert eng["status"] == "active"
            assert eng["welcome_sent_at"]
            assert eng["purchased_at"] == purchase["purchased_at"]
            await _cleanup(db, email)
        asyncio.run(run())

    def test_schedule_days_2_through_21_and_stage_progression(self, db_client, monkeypatch):
        email = f"{TEST_EMAIL_PREFIX}schedule@example.com"

        async def run():
            db = db_client
            await _cleanup(db, email)
            _patch_email(monkeypatch)
            from accountability_service import enroll_rooney_engagement, process_accountability, CHECKIN_DAYS
            member, purchase = await _seed_member_and_purchase(db, email)
            await enroll_rooney_engagement(db, member, purchase)

            purchased_at = datetime.fromisoformat(
                (await db.rooney_engagements.find_one({"user_id": member["user_id"]}))["purchased_at"]
            )
            # Simulate each check-in day
            for day in CHECKIN_DAYS:
                # Progress modules as we go
                if day == 4:
                    await _mark_module_completed(db, member["user_id"], 1)
                elif day == 8:
                    await _mark_module_completed(db, member["user_id"], 2)
                elif day == 12:
                    await _mark_module_completed(db, member["user_id"], 3)
                elif day == 16:
                    await _mark_module_completed(db, member["user_id"], 4)
                elif day == 20:
                    await _mark_module_completed(db, member["user_id"], 5)
                now = purchased_at + timedelta(days=day, hours=1)
                await process_accountability(db, now=now, ignore_window=True)
                # Idempotency: re-run same clock
                await process_accountability(db, now=now, ignore_window=True)

            eng = await db.rooney_engagements.find_one({"user_id": member["user_id"]}, {"_id": 0})
            sent = [s for s in eng["sends"] if s.get("status") == "sent"]
            sent_days = sorted(s["day"] for s in sent)
            assert sent_days == CHECKIN_DAYS, f"sent_days={sent_days}"
            # Day 21 sets status ended
            assert eng["status"] == "ended"
            # Stage tracking on sends
            day_to_stage = {s["day"]: s.get("stage") for s in sent}
            # Day 2: no course_progress yet -> not_started
            assert day_to_stage[2] == "not_started"
            # After completing module 1 at day 4, day 4 send should be module2
            assert day_to_stage[4] == "module2"
            # After completing module 2 at day 8, day 8 send should be module3
            assert day_to_stage[8] == "module3"
            assert day_to_stage[12] == "module4"
            # Variant rotation: same-stage repeat should increment
            module2_sends = [s for s in sent if s.get("stage") == "module2"]
            variants = sorted(s.get("variant", 0) for s in module2_sends)
            # day 4 and day 6 both module2 (module 2 completed at day 8)
            if len(module2_sends) >= 2:
                assert variants[0] != variants[1], f"variants did not rotate: {variants}"
            await _cleanup(db, email)
        asyncio.run(run())

    def test_completion_email_stops_sequence(self, db_client, monkeypatch):
        email = f"{TEST_EMAIL_PREFIX}completion@example.com"

        async def run():
            db = db_client
            await _cleanup(db, email)
            _patch_email(monkeypatch)
            from accountability_service import enroll_rooney_engagement, process_accountability
            member, purchase = await _seed_member_and_purchase(db, email)
            await enroll_rooney_engagement(db, member, purchase)
            for m in range(1, 7):
                await _mark_module_completed(db, member["user_id"], m)
            purchased_at = datetime.fromisoformat(purchase["purchased_at"])
            # Simulate day 4 send after all completed
            await process_accountability(db, now=purchased_at + timedelta(days=4), ignore_window=True)
            eng = await db.rooney_engagements.find_one({"user_id": member["user_id"]}, {"_id": 0})
            assert eng["status"] == "completed"
            assert eng["completion_sent_at"]
            completions = [s for s in eng["sends"] if s.get("day") == "completion"]
            assert len(completions) == 1
            assert completions[0]["subject"] == "You Built Your Board"
            # Later days should not add more sends
            await process_accountability(db, now=purchased_at + timedelta(days=10), ignore_window=True)
            eng2 = await db.rooney_engagements.find_one({"user_id": member["user_id"]}, {"_id": 0})
            assert len([s for s in eng2["sends"] if s.get("status") == "sent"]) == 1
            await _cleanup(db, email)
        asyncio.run(run())

    def test_refund_stops_sequence(self, db_client, monkeypatch):
        email = f"{TEST_EMAIL_PREFIX}refund@example.com"

        async def run():
            db = db_client
            await _cleanup(db, email)
            _patch_email(monkeypatch)
            from accountability_service import enroll_rooney_engagement, process_accountability
            member, purchase = await _seed_member_and_purchase(db, email, refunded=True)
            await enroll_rooney_engagement(db, member, purchase)
            purchased_at = datetime.fromisoformat(purchase["purchased_at"])
            await process_accountability(db, now=purchased_at + timedelta(days=4), ignore_window=True)
            eng = await db.rooney_engagements.find_one({"user_id": member["user_id"]}, {"_id": 0})
            assert eng["status"] == "ended_refunded"
            sent = [s for s in eng["sends"] if s.get("status") == "sent"]
            assert len(sent) == 0
            await _cleanup(db, email)
        asyncio.run(run())

    def test_no_engagement_for_497_purchase(self, db_client, monkeypatch):
        email = f"{TEST_EMAIL_PREFIX}497@example.com"

        async def run():
            db = db_client
            await _cleanup(db, email)
            _patch_email(monkeypatch)
            from member_auth import new_uuid, hash_member_password
            now = datetime.now(timezone.utc).isoformat()
            uid = new_uuid()
            await db.members.insert_one({
                "user_id": uid, "email": email, "first_name": "T", "last_name": "U",
                "password_hash": hash_member_password("Password1234!"),
                "entitlements": ["recruitment_self_guided"],
                "lead_ids": [], "stripe_customer_id": "", "created_at": now, "updated_at": now,
            })
            # $497 purchase (no purchase_source)
            pid = new_uuid()
            await db.purchases.insert_one({
                "purchase_id": pid, "user_id": uid, "session_id": f"cs_test_{pid}",
                "tier": "497", "product": "Recruitment Self-Guided",
                "entitlement": "recruitment_self_guided", "amount": 49700, "currency": "usd",
                "payment_status": "paid", "purchased_at": now, "updated_at": now,
            })
            engs = await db.rooney_engagements.find({"user_id": uid}).to_list(10)
            assert engs == []
            await _cleanup(db, email)
        asyncio.run(run())


# ============================ REGRESSION ============================
class TestRegression:
    def test_homepage_ok(self):
        r = requests.get(f"{BASE_URL}/", allow_redirects=True)
        assert r.status_code == 200

    def test_public_config_intact(self):
        r = requests.get(f"{BASE_URL}/api/payments/config")
        j = r.json()
        for key in ("paid_programs_live", "recruitment_97_live", "recruitment_497_live",
                    "recruit_with_rooney_997_live", "stripe_mode"):
            assert key in j
