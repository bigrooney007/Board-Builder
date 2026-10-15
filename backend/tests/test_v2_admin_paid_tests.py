"""Real paid V2 handlers behind admin-only, per-admin isolated test storage."""
import importlib
import os
import sys
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI

from backend.tests.test_v2_journeys import TEST_ENV, funding_audience
from tests.v2_fixture import Database
from tests.v2_test_providers import external_import_guards


class V2AdminPaidTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        env = patch.dict(os.environ, TEST_ENV)
        env.start(); self.addCleanup(env.stop)
        guards = patch.dict(sys.modules, external_import_guards())
        guards.start(); self.addCleanup(guards.stop)
        from v2_core import create_indexes
        from v2_routes import create_v2_router
        from auth_service import create_access_token
        self.db = Database()
        await create_indexes(self.db)
        await self.db.users.insert_one({"user_id": "test-admin-one", "email": "owner@example.test", "role": "admin"})
        await self.db.users.insert_one({"user_id": "test-admin-two", "email": "other@example.test", "role": "admin"})
        app = FastAPI(); app.include_router(create_v2_router(self.db))
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)
        self.client.cookies.set("admin_access_token", create_access_token("test-admin-one", "owner@example.test"))
        self.other_token = create_access_token("test-admin-two", "other@example.test")
        self.provider = AsyncMock(side_effect=AssertionError("An admin test attempted live provider delivery"))
        for name in ("ai_service.generate_structured", "v2_email.send_provider"):
            replacement = patch(name, new=self.provider); replacement.start(); self.addCleanup(replacement.stop)
        stripe = patch("v2_payments.stripe_sdk", side_effect=AssertionError("An admin test attempted Stripe"))
        stripe.start(); self.addCleanup(stripe.stop)

    async def call(self, method, path, data=None, status=200):
        response = await self.client.request(method, "/api/v2" + path, json=data)
        self.assertEqual(response.status_code, status, response.text[:2000])
        return response.json()

    async def sandbox(self, method, path, data=None, status=200):
        return await self.call(method, "/admin/test-api" + path, data, status)

    async def start(self, product, setup=True):
        journey = (await self.call("POST", "/admin/test-journeys/" + product))["journey"]
        jid = journey["journey_id"]
        if setup:
            body = {"branding": {"organization_name": "Our Sample Charity", "primary_color": "#123456"}}
            if product in {"strategic-planning", "board-fundraising-game"}:
                body["meeting"] = {"date": "2030-11-30", "time": "15:00", "timezone": "Europe/London"}
            await self.sandbox("POST", f"/journeys/{jid}/setup", body)
            journey = await self.sandbox("GET", f"/journeys/{jid}")
        return journey

    async def approve(self, jid, row):
        return await self.sandbox("POST", f"/journeys/{jid}/resources/{row['resource_id']}/approve", {"expected_revision": row["revision"]})

    async def test_four_paid_routes_start_at_setup_and_use_separate_storage_without_payments(self):
        for product in ("recruit", "board-fundraising-game", "strategic-planning", "board-recommitment"):
            journey = await self.start(product, setup=False)
            jid = journey["journey_id"]
            self.assertTrue(jid.startswith("admin-test-" + product))
            self.assertFalse(journey["setup_complete"])
            self.assertEqual(journey["payment_status"], "admin_test_no_payment")
            self.assertEqual((await self.sandbox("GET", f"/journeys/{jid}/resources"))["next"], "/v2/setup/" + jid)
            self.assertEqual((await self.call("GET", "/admin/test-journeys/" + product))["journey"]["journey_id"], jid)
            await self.sandbox("POST", f"/journeys/{jid}/checkout", {}, status=403)
            await self.call("GET", f"/journeys/{jid}", status=404)
        for name in ("v2_journeys", "v2_purchases", "payment_transactions", "v2_email_outbox", "opportunities", "board_applicants"):
            self.assertEqual(await getattr(self.db, name).count_documents({}), 0)
        self.provider.assert_not_awaited()

    async def test_admin_cookie_is_required_for_every_test_api_and_each_admin_has_its_own_records(self):
        journey = await self.start("board-recommitment")
        jid, token = journey["journey_id"], journey["form_token"]
        self.client.cookies.clear()
        await self.call("GET", "/admin/test-journeys/board-recommitment", status=401)
        await self.sandbox("GET", f"/forms/{token}", status=401)
        await self.sandbox("GET", f"/journeys/{jid}/resources", status=401)
        self.client.cookies.set("admin_access_token", self.other_token)
        self.assertIsNone((await self.call("GET", "/admin/test-journeys/board-recommitment"))["journey"])
        await self.sandbox("GET", f"/journeys/{jid}/resources", status=404)
        await self.sandbox("GET", f"/forms/{token}", status=404)

    async def test_recruitment_profile_pack_launch_application_guide_and_captured_emails(self):
        journey = await self.start("recruit")
        jid = journey["journey_id"]
        rows = (await self.sandbox("GET", f"/journeys/{jid}/resources"))["resources"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "ready")
        self.assertIn("SAMPLE FOR ADMIN TESTING", rows[0]["text"])
        await self.approve(jid, rows[0])
        rows = (await self.sandbox("GET", f"/journeys/{jid}/resources"))["resources"]
        self.assertEqual(len(rows), 33)
        self.assertTrue(all(row["status"] in {"ready", "approved"} for row in rows), [(row["key"], row["status"]) for row in rows])
        for row in rows:
            await self.approve(jid, row)
        campaign = await self.sandbox("GET", f"/journeys/{jid}/campaign")
        launched = await self.sandbox("POST", f"/journeys/{jid}/campaign/launch", {"confirmed": True, "expected_revision": campaign["revision"]})
        self.assertEqual(launched["status"], "active")
        self.assertIn("/v2/admin-test/marketplace", launched["marketplace_link"])
        self.assertEqual(len((await self.sandbox("GET", "/marketplace"))["opportunities"]), 1)
        form = await self.sandbox("GET", f"/forms/{journey['form_token']}")
        answers = {question["id"]: "I can support our learning work." for question in form["questions"]}
        answers.update(location="Sample City", profession="Education adviser", why_interested="I can contribute my governance experience.")
        submitted = await self.sandbox("POST", f"/forms/{journey['form_token']}/submit", {"name": "Sample Candidate", "email": "candidate@example.test", "answers": answers, "idempotency_key": "sample-application"})
        sid = submitted["submission_id"]
        for kind in ("guide", "interview-invitation", "rejection"):
            result = await self.sandbox("POST", f"/journeys/{jid}/responses/{sid}/generate", {"kind": kind})
            saved = await self.sandbox("GET", f"/journeys/{jid}/resources/{result['resource_id']}")
            self.assertEqual(saved["status"], "ready")
        inbox = await self.call("GET", "/admin/test-journeys/recruit/inbox")
        self.assertTrue(inbox["emails"])
        self.assertTrue(all(row["status"] == "captured_not_sent" for row in inbox["emails"]))
        self.assertTrue(any("Applicant" in row["subject"] for row in inbox["emails"]))
        self.assertEqual(await self.db.opportunities.count_documents({}), 0)
        self.assertEqual(await self.db.v2_email_outbox.count_documents({}), 0)
        self.provider.assert_not_awaited()

    async def test_group_products_keep_meeting_requirement_and_invitation_tokens_in_test_context(self):
        for product in ("strategic-planning", "board-fundraising-game"):
            journey = await self.start(product, setup=False)
            jid = journey["journey_id"]
            await self.sandbox("POST", f"/journeys/{jid}/setup", {"branding": {"organization_name": "Our Sample Charity"}}, status=422)
            await self.sandbox("POST", f"/journeys/{jid}/setup", {"branding": {"organization_name": "Our Sample Charity"}, "meeting": {"date": "2030-11-30", "time": "15:00", "timezone": "Europe/London"}})
            person = await self.sandbox("POST", f"/journeys/{jid}/invitations", {"name": "Sample Board Member", "email": "board@example.test", "send": True})
            self.assertTrue(person["form_token"].startswith("admin-test-" + product))
            await self.sandbox("GET", f"/forms/{person['form_token']}")
            shared = await self.sandbox("POST", f"/journeys/{jid}/group/share", {})
            self.assertIn("/v2/meeting/admin-test-", shared["group_link"])
            await self.sandbox("GET", shared["group_link"].replace("http://testserver/v2", ""))
            inbox = await self.call("GET", "/admin/test-journeys/" + product + "/inbox")
            self.assertTrue(inbox["emails"])
            self.assertTrue(all(row["status"] == "captured_not_sent" for row in inbox["emails"]))
        self.provider.assert_not_awaited()

    async def test_recommitment_response_generates_editable_guide_and_captures_approval(self):
        from v2_form_content import RECOMMIT_ADVISORY
        journey = await self.start("board-recommitment")
        jid = journey["journey_id"]
        answers = {"recommitment": RECOMMIT_ADVISORY, "decision_reason": "I need to discuss how much time I can offer.", "contribution_interests": ["Fundraising / Resource Development"], "strengths_resources": "Education experience.", "monthly_availability": "2–4 hours", "anything_else": "Please discuss expectations with me."}
        submitted = await self.sandbox("POST", f"/forms/{journey['form_token']}/submit", {"name": "Sample Board Member", "email": "board@example.test", "answers": answers, "idempotency_key": "sample-recommitment"})
        result = await self.sandbox("POST", f"/journeys/{jid}/responses/{submitted['submission_id']}/generate", {"kind": "guide"})
        saved = await self.sandbox("GET", f"/journeys/{jid}/resources/{result['resource_id']}")
        self.assertEqual(saved["status"], "ready")
        await self.approve(jid, saved)
        inbox = await self.call("GET", "/admin/test-journeys/board-recommitment/inbox")
        self.assertTrue(any(row["resource_id"] == saved["resource_id"] for row in inbox["emails"]))
        self.provider.assert_not_awaited()

    async def test_cross_site_and_disallowed_adapter_routes_are_rejected(self):
        response = await self.client.post("/api/v2/admin/test-journeys/recruit", headers={"origin": "https://unrelated.example.test"})
        self.assertEqual(response.status_code, 403)
        for path in ("/recover", "/journeys/new/checkout", "/journeys/new/payment", "/admin/overview", "/access-link"):
            await self.sandbox("POST", path, {}, status=403)

    async def test_both_group_tests_generate_and_approve_only_their_adopted_decisions(self):
        for product in ("board-fundraising-game", "strategic-planning"):
            journey = await self.start(product)
            jid = journey["journey_id"]
            group = await self.sandbox("GET", f"/journeys/{jid}/group")
            section = group["sections"][0]["key"]
            content = funding_audience("individuals", "agreed-audience") if product == "board-fundraising-game" else "The board approved community learning as its planning priority."
            await self.sandbox("POST", f"/journeys/{jid}/decisions", {"category": section, "title": "Our adopted test decision", "content": content, "status": "adopted"})
            final = await self.sandbox("POST", f"/journeys/{jid}/final-preview", {})
            self.assertIn("Our adopted test decision", final["text"])
            await self.approve(jid, final)
            downloaded = await self.client.get(f"/api/v2/admin/test-api/journeys/{jid}/resources/{final['resource_id']}/download?format=docx")
            self.assertEqual(downloaded.status_code, 200)
            self.assertTrue(downloaded.content.startswith(b"PK"))
            inbox = await self.call("GET", "/admin/test-journeys/" + product + "/inbox")
            self.assertTrue(any(row["resource_id"] == final["resource_id"] for row in inbox["emails"]))
        self.provider.assert_not_awaited()
