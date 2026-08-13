"""Iteration 30: Regression suite for the new 3-email weekly Recruitment nurture sequence.

Scope (paraphrased from user's 54-item checklist):
- Templates content, subjects & CTA URLs
- HTML render, greeting merge, unsubscribe placeholder, no unresolved tokens
- Enable gating via env
- Rotation math & failure handling (mocked broadcasts)
- Sender formatting
- Purchase-time stop (recruitment purchase sources only, idempotent, safe)
- Lead enrollment path (unchanged)
- Admin nurture/status endpoint fields
- Regression: existing pytest suites still pass; checkout endpoints unchanged
"""
import asyncio
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")

import marketing_service  # noqa: E402
from marketing_service import (  # noqa: E402
    NURTURE_TEMPLATES,
    RECRUITMENT_PURCHASE_SOURCES,
    enabled_nurture_sources,
    nurture_email_html,
    nurture_sender,
    run_weekly_nurture,
    stop_recruitment_nurture_for_purchase,
)

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://board-funnel-v2.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PASSWORD = "PC8JX97y7YjPUel9-gM5gAem"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def db():
    # Function scope so each async test binds to its own event loop
    client = AsyncIOMotorClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:120]}")
    return s


# =====================================================
# GROUP 1: TEMPLATES — exact copy, subjects, CTA URLs
# =====================================================
class TestTemplates:
    def test_recruitment_has_exactly_three_templates(self):
        assert len(NURTURE_TEMPLATES["recruitment"]) == 3

    def test_reactivation_and_fundraising_unchanged_four_each(self):
        assert len(NURTURE_TEMPLATES["reactivation"]) == 4
        assert len(NURTURE_TEMPLATES["fundraising_activation"]) == 4

    def test_email1_subject_url_and_rooney_sentence(self):
        t = NURTURE_TEMPLATES["recruitment"][0]
        assert t["subject"] == "Before You Decide How to Build Your Board"
        assert t["url"] == "/about-rooney"
        joined = " ".join(t["paragraphs"])
        assert "I made mistakes, damaged relationships, learned from the experience, rebuilt my Board, and eventually developed a process that worked." in joined

    def test_email2_subject_url_and_required_phrases(self):
        t = NURTURE_TEMPLATES["recruitment"][1]
        assert t["subject"] == "You Can Build Your Board Yourself"
        assert t["url"] == "/recruit-your-board-yourself"
        joined = " ".join(t["paragraphs"])
        assert "Board Applicant Network" in joined
        assert "use it again whenever your nonprofit needs another Board Member" in joined
        assert "$497, one time" in joined
        assert "Your investment is protected by our 100% money-back guarantee." in joined
        # Rooney support wording
        assert "reach out to me for support" in joined.lower() or "reach out to me" in joined

    def test_email3_subject_url_and_required_phrases(self):
        t = NURTURE_TEMPLATES["recruitment"][2]
        assert t["subject"] == "Want Me to Help You Build Your Board?"
        assert t["url"] == "/board-recruitment-proposal"
        joined = " ".join(t["paragraphs"])
        assert "$1,997" in joined
        assert "You remain in control of who joins your Board." in joined

    def test_no_recruitment_template_links_to_recruit_options(self):
        for t in NURTURE_TEMPLATES["recruitment"]:
            assert t["url"] != "/recruit/options"
            assert "/recruit/options" not in " ".join(t["paragraphs"])

    def test_reactivation_and_fundraising_urls_still_options_paths(self):
        for t in NURTURE_TEMPLATES["reactivation"]:
            assert t["url"] == "/reactivate/options"
        for t in NURTURE_TEMPLATES["fundraising_activation"]:
            assert t["url"] == "/activate/options"


# =====================================================
# GROUP 2: HTML RENDER
# =====================================================
class TestHtmlRender:
    ORIGIN = "https://nonprofitboardbuilder.com"

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_recruitment_render_has_greeting_merge_triple_braces(self, idx):
        html = nurture_email_html(NURTURE_TEMPLATES["recruitment"][idx], self.ORIGIN)
        # Resend broadcast merge syntax uses TRIPLE braces per official docs:
        # https://resend.com/blog/broadcast-api -> 'Hi {{{FIRST_NAME|there}}}'
        assert "Hi {{{FIRST_NAME|there}}}," in html, (
            f"Expected 3-brace Resend broadcast merge 'Hi {{{{{{FIRST_NAME|there}}}}}},' in HTML but got greeting section: "
            f"{html[html.find('Hi '):html.find('Hi ')+80] if 'Hi ' in html else 'MISSING'}"
        )

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_recruitment_render_cta_href_and_closing(self, idx):
        t = NURTURE_TEMPLATES["recruitment"][idx]
        html = nurture_email_html(t, self.ORIGIN)
        assert f"href='{self.ORIGIN}{t['url']}'" in html
        assert "Rooney Akpesiri" in html
        assert "The Nonprofit Board Builder" in html

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_recruitment_render_unsubscribe_and_postal(self, idx):
        html = nurture_email_html(NURTURE_TEMPLATES["recruitment"][idx], self.ORIGIN)
        # Resend broadcast merge syntax uses TRIPLE braces (official docs)
        assert "{{{RESEND_UNSUBSCRIBE_URL}}}" in html
        assert "Unsubscribe" in html
        # Postal address block present (env may not be set during test — accept placeholder)
        assert "Nonprofit Board Builder —" in html

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_no_test_or_placeholder_strings(self, idx):
        html = nurture_email_html(NURTURE_TEMPLATES["recruitment"][idx], self.ORIGIN).lower()
        for banned in ["sandbox", "staging", "localhost", "preview"]:
            assert banned not in html, f"Found banned substring '{banned}' in rendered HTML"
        # No unresolved plain-bracket placeholders
        assert "[first name]" not in html
        assert "[organization]" not in html

    def test_legacy_reactivation_render_has_headline_no_greeting(self):
        t = NURTURE_TEMPLATES["reactivation"][0]
        html = nurture_email_html(t, self.ORIGIN)
        assert "<h1" in html
        assert t["headline"] in html
        assert "Hi {{" not in html  # no greeting for legacy templates


# =====================================================
# GROUP 3: ENABLE GATING
# =====================================================
class TestEnableGating:
    def test_current_env_only_recruitment_enabled(self, monkeypatch):
        monkeypatch.setenv("LEAD_NURTURE_ENABLED", "false")
        monkeypatch.setenv("RECRUITMENT_LEAD_NURTURE_ENABLED", "true")
        assert enabled_nurture_sources() == {"recruitment"}

    def test_both_false_returns_empty(self, monkeypatch):
        monkeypatch.setenv("LEAD_NURTURE_ENABLED", "false")
        monkeypatch.setenv("RECRUITMENT_LEAD_NURTURE_ENABLED", "false")
        assert enabled_nurture_sources() == set()

    def test_lead_nurture_true_enables_all(self, monkeypatch):
        monkeypatch.setenv("LEAD_NURTURE_ENABLED", "true")
        monkeypatch.setenv("RECRUITMENT_LEAD_NURTURE_ENABLED", "false")
        assert enabled_nurture_sources() == {"recruitment", "reactivation", "fundraising_activation"}

    @pytest.mark.asyncio
    async def test_preview_safety_guard_test_database(self, db, monkeypatch):
        # With DB_NAME=test_database, real-send path skips ALL sources (preview guard)
        monkeypatch.setenv("DB_NAME", "test_database")
        monkeypatch.setenv("LEAD_NURTURE_ENABLED", "true")  # enable all
        # Ensure no real broadcast is ever called
        broadcast_mock = AsyncMock(return_value="bcast_dummy")
        with patch.object(marketing_service, "create_segment_broadcast", broadcast_mock):
            results = await run_weekly_nurture(db, "https://example.com", test_only=False)
        broadcast_mock.assert_not_called()
        for src in ["recruitment", "reactivation", "fundraising_activation"]:
            assert results.get(src, {}).get("skipped") is True
            assert "preview" in results[src]["reason"].lower()

    @pytest.mark.asyncio
    async def test_disabled_sources_are_skipped_and_recruitment_broadcasts(self, db, monkeypatch):
        # Simulate production: DB_NAME != test_database, only recruitment enabled
        monkeypatch.setenv("DB_NAME", "prod_like_db")
        monkeypatch.setenv("LEAD_NURTURE_ENABLED", "false")
        monkeypatch.setenv("RECRUITMENT_LEAD_NURTURE_ENABLED", "true")
        # Clear duplicate-protection rows for this week so send goes through
        from marketing_service import week_key
        wk = week_key()
        await db.nurture_sends.delete_many({"scheduled_week": wk})
        # Provide fake segments
        segments_mock = AsyncMock(return_value={"recruitment": "seg_r", "reactivation": "seg_a", "fundraising_activation": "seg_f"})
        broadcast_mock = AsyncMock(return_value="bcast_123")
        with patch.object(marketing_service, "get_nurture_segments", segments_mock), \
             patch.object(marketing_service, "create_segment_broadcast", broadcast_mock):
            results = await run_weekly_nurture(db, "https://example.com", test_only=False)
        assert results["recruitment"].get("sent") is True
        assert results["reactivation"].get("skipped") is True
        assert results["fundraising_activation"].get("skipped") is True
        assert broadcast_mock.call_count == 1  # only recruitment
        # Cleanup
        await db.nurture_sends.delete_many({"scheduled_week": wk})
        await db.nurture_rotation.delete_many({"segment": "recruitment"})


# =====================================================
# GROUP 4: ROTATION 1→2→3→1→2 and failure handling
# =====================================================
class TestRotation:
    @pytest.mark.asyncio
    async def test_rotation_cycle_and_failure(self, db, monkeypatch):
        monkeypatch.setenv("DB_NAME", "prod_like_db")
        monkeypatch.setenv("LEAD_NURTURE_ENABLED", "false")
        monkeypatch.setenv("RECRUITMENT_LEAD_NURTURE_ENABLED", "true")

        segments_mock = AsyncMock(return_value={"recruitment": "seg_r", "reactivation": "seg_a", "fundraising_activation": "seg_f"})
        broadcast_mock = AsyncMock(return_value="bcast_ok")

        # reset rotation
        await db.nurture_rotation.delete_many({"segment": "recruitment"})
        await db.nurture_sends.delete_many({"segment": "recruitment"})

        sent_templates = []
        for week_num in range(1, 6):
            fake_week = f"2099-W{week_num:02d}"
            monkeypatch.setattr(marketing_service, "week_key", lambda w=fake_week: w)
            # Patch the internal now_tz-derived week: run_weekly_nurture calls now_tz(...).strftime
            # Instead we fake by clearing rows and letting real code compute week. Since we can't
            # easily override the ISO week, we just use unique keys via patching the module attr.
            with patch("marketing_service.now_tz") as ntz, \
                 patch.object(marketing_service, "get_nurture_segments", segments_mock), \
                 patch.object(marketing_service, "create_segment_broadcast", broadcast_mock):
                fake_dt = MagicMock()
                fake_dt.strftime.side_effect = lambda fmt: fake_week if fmt == "%G-W%V" else "2099-01-01T00:00:00"
                fake_dt.isoformat.return_value = "2099-01-01T00:00:00"
                ntz.return_value = fake_dt
                results = await run_weekly_nurture(db, "https://example.com", test_only=False)
            sent_templates.append(results["recruitment"].get("template"))

        assert sent_templates == [1, 2, 3, 1, 2], f"Rotation misaligned: {sent_templates}"

        # Failure path — broadcast raises, rotation must NOT advance
        rot_before = (await db.nurture_rotation.find_one({"segment": "recruitment"}))["last_sent"]
        assert rot_before == 2  # After [1,2,3,1,2] cycle
        fail_week = "2099-W99"
        alert_mock = AsyncMock()
        failing_broadcast = AsyncMock(side_effect=RuntimeError("boom"))
        with patch("marketing_service.now_tz") as ntz, \
             patch.object(marketing_service, "get_nurture_segments", segments_mock), \
             patch.object(marketing_service, "create_segment_broadcast", failing_broadcast), \
             patch.object(marketing_service, "send_owner_alert", alert_mock):
            fake_dt = MagicMock()
            fake_dt.strftime.side_effect = lambda fmt: fail_week if fmt == "%G-W%V" else "2099-01-01T00:00:00"
            fake_dt.isoformat.return_value = "2099-01-01T00:00:00"
            ntz.return_value = fake_dt
            results = await run_weekly_nurture(db, "https://example.com", test_only=False)

        assert results["recruitment"].get("sent") is False
        assert "boom" in results["recruitment"]["error"]
        rot_after = (await db.nurture_rotation.find_one({"segment": "recruitment"}))["last_sent"]
        assert rot_after == rot_before, "Failed send must not advance rotation"
        alert_mock.assert_awaited()  # owner alerted
        send_row = await db.nurture_sends.find_one({"segment": "recruitment", "scheduled_week": fail_week})
        assert send_row["status"] == "Failed"

        # Duplicate same-week protection
        with patch("marketing_service.now_tz") as ntz, \
             patch.object(marketing_service, "get_nurture_segments", segments_mock), \
             patch.object(marketing_service, "create_segment_broadcast", broadcast_mock):
            fake_dt = MagicMock()
            fake_dt.strftime.side_effect = lambda fmt: fail_week if fmt == "%G-W%V" else "2099-01-01T00:00:00"
            fake_dt.isoformat.return_value = "2099-01-01T00:00:00"
            ntz.return_value = fake_dt
            dup = await run_weekly_nurture(db, "https://example.com", test_only=False)
        assert dup["recruitment"].get("skipped") is True
        assert "already sent" in dup["recruitment"]["reason"].lower()

        # Legacy safety: last_sent=4 → (4%3)+1 = 2
        await db.nurture_rotation.update_one({"segment": "recruitment"}, {"$set": {"last_sent": 4}})
        legacy_week = "2099-W98"
        with patch("marketing_service.now_tz") as ntz, \
             patch.object(marketing_service, "get_nurture_segments", segments_mock), \
             patch.object(marketing_service, "create_segment_broadcast", broadcast_mock):
            fake_dt = MagicMock()
            fake_dt.strftime.side_effect = lambda fmt: legacy_week if fmt == "%G-W%V" else "2099-01-01T00:00:00"
            fake_dt.isoformat.return_value = "2099-01-01T00:00:00"
            ntz.return_value = fake_dt
            legacy = await run_weekly_nurture(db, "https://example.com", test_only=False)
        assert legacy["recruitment"].get("template") == 2

        # Cleanup
        await db.nurture_sends.delete_many({"segment": "recruitment"})
        await db.nurture_rotation.delete_many({"segment": "recruitment"})


# =====================================================
# GROUP 5: SENDER
# =====================================================
class TestSender:
    def test_recruitment_sender_format(self, monkeypatch):
        monkeypatch.setenv("NONPROFIT_SENDER", "Nonprofit Board Builder <nonprofits@nonprofitboardbuilder.com>")
        assert nurture_sender("recruitment") == "Rooney Akpesiri | The Nonprofit Board Builder <nonprofits@nonprofitboardbuilder.com>"

    def test_other_sources_keep_nonprofit_sender(self, monkeypatch):
        monkeypatch.setenv("NONPROFIT_SENDER", "Nonprofit Board Builder <nonprofits@nonprofitboardbuilder.com>")
        assert nurture_sender("reactivation") == "Nonprofit Board Builder <nonprofits@nonprofitboardbuilder.com>"
        assert nurture_sender("fundraising_activation") == "Nonprofit Board Builder <nonprofits@nonprofitboardbuilder.com>"


# =====================================================
# GROUP 6: PURCHASE STOP
# =====================================================
class TestPurchaseStop:
    @pytest.mark.asyncio
    async def test_recruitment_purchase_sources_constant(self):
        assert RECRUITMENT_PURCHASE_SOURCES == {"direct_diy_board_recruitment_497", "direct_board_recruitment_project"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize("source", ["direct_diy_board_recruitment_497", "direct_board_recruitment_project"])
    async def test_stop_fires_for_recruitment_sources(self, db, source):
        email_buyer = f"test_stop_buyer_{uuid.uuid4().hex[:8]}@example.com"
        email_tx = f"test_stop_tx_{uuid.uuid4().hex[:8]}@example.com"
        # seed both contacts as leads
        await db.nurture_contacts.insert_one({"email": email_buyer, "nurture_status": "lead"})
        await db.nurture_contacts.insert_one({"email": email_tx, "nurture_status": "lead"})
        remove_mock = AsyncMock()
        with patch("resend.ContactSegments.remove_async", remove_mock), \
             patch.object(marketing_service, "get_nurture_segments", AsyncMock(return_value={"recruitment": "seg_r", "reactivation": "s2", "fundraising_activation": "s3"})):
            await stop_recruitment_nurture_for_purchase(db, {"purchase_source": source, "customer_email": email_tx}, email_buyer)
        for e in [email_buyer, email_tx]:
            row = await db.nurture_contacts.find_one({"email": e})
            assert row["nurture_status"] == "customer"
        # remove_async attempted for both emails
        assert remove_mock.await_count >= 2
        # Cleanup
        await db.nurture_contacts.delete_many({"email": {"$in": [email_buyer, email_tx]}})

    @pytest.mark.asyncio
    async def test_stop_ignores_non_recruitment_source(self, db):
        email = f"test_stop_noop_{uuid.uuid4().hex[:8]}@example.com"
        await db.nurture_contacts.insert_one({"email": email, "nurture_status": "lead"})
        with patch.object(marketing_service, "get_nurture_segments", AsyncMock(return_value={"recruitment": "seg_r"})):
            await stop_recruitment_nurture_for_purchase(
                db, {"purchase_source": "recruit_with_rooney_997", "customer_email": email}, email
            )
        row = await db.nurture_contacts.find_one({"email": email})
        assert row["nurture_status"] == "lead", "Non-recruitment source must not flip contact"
        await db.nurture_contacts.delete_one({"email": email})

    @pytest.mark.asyncio
    async def test_stop_safe_with_none_and_empty(self, db):
        # Must not raise
        await stop_recruitment_nurture_for_purchase(db, None, "")
        await stop_recruitment_nurture_for_purchase(db, {}, "")
        await stop_recruitment_nurture_for_purchase(db, {"purchase_source": "direct_diy_board_recruitment_497"}, "")

    @pytest.mark.asyncio
    async def test_stop_idempotent_and_resend_failure_never_propagates(self, db):
        email = f"test_stop_idem_{uuid.uuid4().hex[:8]}@example.com"
        await db.nurture_contacts.insert_one({"email": email, "nurture_status": "lead"})
        failing_remove = AsyncMock(side_effect=RuntimeError("resend down"))
        with patch("resend.ContactSegments.remove_async", failing_remove), \
             patch.object(marketing_service, "get_nurture_segments", AsyncMock(return_value={"recruitment": "seg_r"})):
            for _ in range(3):
                await stop_recruitment_nurture_for_purchase(
                    db, {"purchase_source": "direct_diy_board_recruitment_497", "customer_email": email}, email
                )
        row = await db.nurture_contacts.find_one({"email": email})
        assert row["nurture_status"] == "customer"
        await db.nurture_contacts.delete_one({"email": email})

    def test_payment_status_endpoint_calls_stop(self):
        # Source inspection: payment_routes payment_status calls stop_recruitment_nurture_for_purchase
        # when transitioning to paid. Verify by static code check.
        src = open("/app/backend/payment_routes.py").read()
        assert "stop_recruitment_nurture_for_purchase" in src
        assert "session.customer_details" in src

    def test_webhook_only_stops_on_paid(self):
        src = open("/app/backend/payment_routes.py").read()
        # Confirm failed/expired branches do NOT call the stop helper
        # Find each branch and ensure _stop_nurture_after_paid appears only inside completed/async_payment_succeeded
        assert 'async_payment_failed' in src
        assert 'async_payment_succeeded' in src
        # Simple check: within the failed/expired blocks, the helper is not called
        for marker in ["async_payment_failed", "checkout.session.expired"]:
            idx = src.index(marker)
            snippet = src[idx: idx + 400]
            assert "_stop_nurture_after_paid" not in snippet


# =====================================================
# GROUP 7: LEAD ENROLLMENT (live sync — mocked resend)
# =====================================================
class TestLeadEnrollment:
    @pytest.mark.asyncio
    async def test_recruitment_lead_creates_nurture_contact_and_stop_flips(self, db, monkeypatch):
        email = f"test_nurture_lead_{uuid.uuid4().hex[:8]}@example.com"
        # Directly call sync_lead_nurture to avoid live Resend contact creation
        with patch.object(marketing_service, "get_nurture_segments", AsyncMock(return_value={"recruitment": "seg_r", "reactivation": "s2", "fundraising_activation": "s3"})), \
             patch("marketing_service.upsert_contact", AsyncMock(return_value="contact_abc")), \
             patch("resend.ContactSegments.remove_async", AsyncMock()):
            await marketing_service.sync_lead_nurture(db, {
                "email": email, "offer_source": "recruitment",
                "name": "Test User", "organization": "Test Org",
            })
        row = await db.nurture_contacts.find_one({"email": email})
        assert row is not None
        assert row["nurture_status"] == "lead"
        assert row["active_offer_source"] == "recruitment"

        # Now stop flips the same row to customer
        with patch.object(marketing_service, "get_nurture_segments", AsyncMock(return_value={"recruitment": "seg_r"})), \
             patch("resend.ContactSegments.remove_async", AsyncMock()):
            await stop_recruitment_nurture_for_purchase(
                db, {"purchase_source": "direct_diy_board_recruitment_497", "customer_email": email}, email
            )
        row2 = await db.nurture_contacts.find_one({"email": email})
        assert row2["nurture_status"] == "customer"
        # Cleanup
        await db.nurture_contacts.delete_one({"email": email})


# =====================================================
# GROUP 8: ADMIN STATUS ENDPOINT
# =====================================================
class TestAdminStatus:
    def test_admin_nurture_status_includes_recruitment_flag(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/nurture/status", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "recruitment_lead_nurture_enabled" in data
        assert data["recruitment_lead_nurture_enabled"] == "true"
        assert data["lead_nurture_enabled"] == "false"


# =====================================================
# GROUP 9: REGRESSION — checkout endpoints & untouched files
# =====================================================
class TestRegression:
    def test_diy_checkout_still_returns_session(self):
        r = requests.post(
            f"{BASE_URL}/api/payments/diy-checkout",
            json={"origin_url": BASE_URL},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "checkout_url" in data and "session_id" in data
        assert data["checkout_url"].startswith("https://")

    def test_direct_project_checkout_still_returns_session(self):
        r = requests.post(
            f"{BASE_URL}/api/payments/direct-project-checkout",
            json={"origin_url": BASE_URL},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "checkout_url" in data
        assert "session_id" in data

    @pytest.mark.asyncio
    async def test_diy_transaction_amount_and_success_url(self, db):
        # Create a fresh DIY checkout via endpoint, then inspect the DB record + Stripe session
        r = requests.post(f"{BASE_URL}/api/payments/diy-checkout", json={"origin_url": BASE_URL}, timeout=20)
        assert r.status_code == 200
        session_id = r.json()["session_id"]
        tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        assert tx["amount"] == 49700
        assert tx["purchase_source"] == "direct_diy_board_recruitment_497"
        # verify success URL
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        sess = stripe.checkout.Session.retrieve(session_id)
        assert "/purchase/success" in sess.success_url

    @pytest.mark.asyncio
    async def test_direct_project_transaction_amount_and_success_url(self, db):
        r = requests.post(f"{BASE_URL}/api/payments/direct-project-checkout", json={"origin_url": BASE_URL}, timeout=20)
        assert r.status_code == 200
        session_id = r.json()["session_id"]
        tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        assert tx["amount"] == 199700
        assert tx["purchase_source"] == "direct_board_recruitment_project"
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        sess = stripe.checkout.Session.retrieve(session_id)
        assert "/board-recruitment-intake" in sess.success_url
