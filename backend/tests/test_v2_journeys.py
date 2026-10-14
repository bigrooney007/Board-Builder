"""V2 acceptance tests using synthetic organizations and mocked providers.

Run from the repository root:
    python -m unittest discover -s backend/tests -p test_v2_journeys.py -v

The fixture never connects to MongoDB, Stripe, an AI provider or an email
provider. Payment and email transport are the only external seams replaced;
application authorization, validation, approval and persistence are exercised.
"""

import asyncio
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
from fastapi import FastAPI, HTTPException
from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from tests.v2_fixture import Database
from tests.v2_test_providers import external_import_guards, FakeStripe, FakeEmailTransport, FakeStructuredAI


TEST_ENV = {
    "NBB_V2_ENABLED": "true",
    "NBB_V2_ORIGIN": "http://testserver",
    "NBB_V2_PREVIEW_KEY": "synthetic-preview-only-key",
    "NBB_V2_SESSION_SECRET": "synthetic-session-secret-at-least-32-characters",
    "JWT_SECRET": "synthetic-original-jwt-secret-at-least-32-characters",
    "NBB_V2_NETWORK_LIVE_ENABLED": "false",
    "NBB_V2_PAYMENTS_TEST_ONLY": "true",
    "NBB_V2_EMAIL_TEST_MODE": "true",
    "NBB_V2_TEST_EMAILS": "leader@example.test,candidate@example.test,board@example.test,opted-in@example.test",
    "RESEND_API_KEY": "",
    "BOARD_APPLICANT_SENDER": "Board Builder <network@example.test>",
    "NONPROFIT_SENDER": "Board Builder <resources@example.test>",
    "STRIPE_API_KEY": "sk_test_synthetic_never_use_network",
    "STRIPE_SECRET_KEY": "sk_test_synthetic_never_use_network",
    "MONGO_URL": "",
    "EMERGENT_LLM_KEY": "",
    "OPENAI_API_KEY": "",
}


def request(method="GET", cookies=None, headers=None):
    raw = [(str(k).lower().encode(), str(v).encode()) for k, v in (headers or {}).items()]
    if cookies:
        raw.append((b"cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()).encode()))
    return Request({"type": "http", "method": method, "headers": raw, "path": "/api/v2/test"})


class V2AccessSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.environment = patch.dict(os.environ, TEST_ENV, clear=False)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.core = importlib.import_module("v2_core")
        self.db = Database()
        await self.core.create_indexes(self.db)
        self.journeys = []
        for index in range(2):
            journey = {
                "journey_id": f"synthetic-organization-{index}", "form_token": f"synthetic-form-{index}",
                "product": "recruit", "state": "paid", "email": f"leader{index}@example.test",
                "organization": f"Synthetic nonprofit {index}", "draft_digest": self.core.digest(f"draft-{index}"),
            }
            await self.db.v2_journeys.insert_one(journey)
            self.journeys.append(journey)

    def owner_request(self, index=0, method="GET", headers=None):
        journey = self.journeys[index]
        token = self.core.session_token("owner", journey_id=journey["journey_id"], email=journey["email"])
        return request(method, {"nbb_v2_owner_" + journey["journey_id"]: token}, headers)

    async def test_owner_capability_is_scoped_to_one_organization(self):
        own = await self.core.require_owner(self.owner_request(), self.db, self.journeys[0]["journey_id"])
        self.assertEqual(own["organization"], "Synthetic nonprofit 0")
        with self.assertRaises(HTTPException) as rejected:
            await self.core.require_owner(self.owner_request(), self.db, self.journeys[1]["journey_id"])
        self.assertEqual(rejected.exception.status_code, 401)

    async def test_preview_cookie_does_not_grant_private_owner_access(self):
        preview = self.core.session_token("preview")
        req = request(cookies={"nbb_v2_preview": preview})
        self.assertTrue(await self.core.preview_access(req, self.db))
        with self.assertRaises(HTTPException) as rejected:
            await self.core.require_owner(req, self.db, self.journeys[0]["journey_id"])
        self.assertEqual(rejected.exception.status_code, 401)

    async def test_free_intake_draft_token_cannot_read_paid_responses(self):
        req = request(headers={"X-V2-Draft": "draft-0"})
        allowed = await self.core.require_owner(req, self.db, self.journeys[0]["journey_id"], paid=False)
        self.assertEqual(allowed["journey_id"], self.journeys[0]["journey_id"])
        with self.assertRaises(HTTPException) as rejected:
            await self.core.require_owner(req, self.db, self.journeys[0]["journey_id"], paid=True)
        self.assertEqual(rejected.exception.status_code, 401)

    async def test_expired_tampered_and_wrong_kind_tokens_are_rejected(self):
        expired = jwt.encode({"iss": "nbb-v2", "aud": "nbb-v2", "kind": "owner", "journey_id": "synthetic-organization-0", "email": "leader0@example.test", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}, TEST_ENV["NBB_V2_SESSION_SECRET"], algorithm="HS256")
        valid = self.core.session_token("owner", journey_id="synthetic-organization-0", email="leader0@example.test")
        for token in (expired, valid[:-10] + "tampered00", self.core.session_token("preview")):
            with self.subTest(token=token[-12:]):
                with self.assertRaises(HTTPException) as rejected:
                    await self.core.require_owner(request(cookies={"nbb_v2_owner_synthetic-organization-0": token}), self.db, "synthetic-organization-0")
                self.assertEqual(rejected.exception.status_code, 401)

    async def test_cross_site_mutation_is_rejected(self):
        with self.assertRaises(HTTPException) as rejected:
            await self.core.require_owner(self.owner_request(method="POST", headers={"origin": "https://unrelated.example.test"}), self.db, "synthetic-organization-0")
        self.assertEqual(rejected.exception.status_code, 403)

    async def test_unpaid_product_is_not_unlocked_by_valid_owner_cookie(self):
        await self.db.v2_journeys.update_one({"journey_id": "synthetic-organization-0"}, {"$set": {"state": "free"}})
        with self.assertRaises(HTTPException) as rejected:
            await self.core.require_owner(self.owner_request(), self.db, "synthetic-organization-0")
        self.assertEqual(rejected.exception.status_code, 403)

    async def test_mutation_lease_blocks_parallel_saves_and_releases_on_error(self):
        async with self.core.journey_lock(self.db, "synthetic-organization-0"):
            with self.assertRaises(HTTPException) as conflict:
                async with self.core.journey_lock(self.db, "synthetic-organization-0"):
                    self.fail("A concurrent mutation was allowed")
            self.assertEqual(conflict.exception.status_code, 409)
        with self.assertRaises(RuntimeError):
            async with self.core.journey_lock(self.db, "synthetic-organization-0"):
                raise RuntimeError("synthetic generation failure")
        async with self.core.journey_lock(self.db, "synthetic-organization-0"):
            pass
        journey = await self.db.v2_journeys.find_one({"journey_id": "synthetic-organization-0"})
        self.assertNotIn("mutation_lease", journey)

    async def test_owner_email_links_are_random_expiring_and_hashed_at_rest(self):
        url = await self.core.issue_owner_link(self.db, "synthetic-organization-0", "/v2/resources/synthetic-organization-0")
        token = parse_qs(urlparse(url).query)["access"][0]
        record = await self.db.v2_access_links.find_one({"token_digest": self.core.digest(token)})
        self.assertGreater(len(token), 32)
        self.assertNotIn(token, str(record))
        self.assertGreater(record["expires_at"], self.core.now_iso())
        self.assertEqual(record["journey_id"], "synthetic-organization-0")

    async def test_email_links_cannot_redirect_to_external_or_old_workflows(self):
        bad_paths = ["https://evil.example.test/", "//evil.example.test/v2/resources", "/app/board-recruitment", "/v2/../app", "/v2/%2e%2e/app", "/v2/\\evil", "/v2/resources\nLocation: https://evil.example.test"]
        for path in bad_paths:
            with self.subTest(path=path):
                with self.assertRaises(HTTPException):
                    self.core.internal_path(path)

    async def test_disabled_preview_fails_closed(self):
        with patch.dict(os.environ, {"NBB_V2_ENABLED": "false"}):
            with self.assertRaises(HTTPException) as unavailable:
                await self.core.require_owner(self.owner_request(), self.db, "synthetic-organization-0")
        self.assertEqual(unavailable.exception.status_code, 404)

    async def test_deployment_defaults_allow_entry_but_not_private_records(self):
        with patch.dict(os.environ):
            os.environ.pop("NBB_V2_ENABLED", None)
            os.environ.pop("NBB_V2_PREVIEW_KEY", None)
            self.assertTrue(self.core.is_enabled())
            self.assertTrue(await self.core.preview_access(request(), self.db))
            with self.assertRaises(HTTPException) as denied:
                await self.core.require_owner(request(), self.db, "synthetic-organization-0")
            self.assertEqual(denied.exception.status_code, 401)

    async def test_optional_preview_key_still_restricts_entry(self):
        with self.assertRaises(HTTPException) as denied:
            await self.core.preview_access(request(), self.db)
        self.assertEqual(denied.exception.status_code, 403)

    async def test_origin_reuses_existing_site_configuration(self):
        with patch.dict(os.environ):
            os.environ.pop("NBB_V2_ORIGIN", None)
            os.environ["PUBLIC_ORIGIN"] = "https://board.example.test/"
            self.assertEqual(self.core.origin(), "https://board.example.test")
            self.core.csrf_guard(request(method="POST", headers={"origin": "https://board.example.test"}))
            os.environ.pop("PUBLIC_ORIGIN")
            self.assertEqual(self.core.origin(), "https://nonprofitboardbuilder.com")
            os.environ["NBB_V2_ORIGIN"] = "https://explicit.example.test"
            self.assertEqual(self.core.origin(), "https://explicit.example.test")


def intake_answers(product):
    from v2_form_content import INTAKE_FIELDS
    answers = {key: "Our synthetic nonprofit provides literacy support and welcomes practical board guidance." for key in INTAKE_FIELDS[product]}
    if product == "strategic-planning":
        answers["program_details"] = [{"name": "Literacy support", "description": "Weekly reading groups.", "present_work": "Volunteer-led sessions."}]
        answers["budget"] = "The board has not approved a budget figure yet."
    if product == "board-recommitment":
        answers["need_by"] = "2026-11-30"
    return answers


def funding_audience(category, ident, funder=None, approach="Introduce our verified literacy work."):
    return {
        "audience_id": ident, "category": category, "funder": funder or f"Synthetic {category} audience {ident}",
        "why": "Their stated interests align with literacy support.", "where": "Our existing community connections.",
        "attract": approach, "relationship": "Invite a conversation before requesting support.",
        "ask": "Support the literacy sessions.", "amount": "We are unsure. We need to agree a suitable amount.",
    }


class V2CompleteAPIJourneys(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.environment = patch.dict(os.environ, TEST_ENV, clear=False)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.guards = patch.dict(sys.modules, external_import_guards())
        self.guards.start()
        self.addCleanup(self.guards.stop)
        self.core = importlib.import_module("v2_core")
        self.forms = importlib.import_module("v2_forms")
        self.resources = importlib.import_module("v2_resources")
        self.payments = importlib.import_module("v2_payments")
        self.emails = importlib.import_module("v2_email")
        self.routes = importlib.import_module("v2_routes")
        self.db = Database()
        await self.core.create_indexes(self.db)
        self.stripe = FakeStripe()
        self.transport = FakeEmailTransport()
        self.ai = FakeStructuredAI()
        self.patches = [patch("v2_payments.stripe_sdk", return_value=self.stripe),
                        patch("ai_service.generate_structured", new=self.ai),
                        patch("v2_email.send_provider", new=self.transport)]
        for provider_patch in self.patches:
            provider_patch.start()
            self.addCleanup(provider_patch.stop)
        app = FastAPI()
        self.core.install_v2_response_headers(app)
        app.include_router(self.routes.create_v2_router(self.db))
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)
        self.app = app
        await self.ok("POST", "/preview-access", {"key": TEST_ENV["NBB_V2_PREVIEW_KEY"]})
        await self.db.members.insert_one({"user_id": "original-member", "email": "original@example.test", "entitlements": ["recruitment_self_guided"]})
        await self.db.purchases.insert_one({"purchase_id": "historical-purchase", "amount": 49700, "email": "original@example.test"})
        self.original_members = await self.db.members.find({}).to_list(None)
        self.original_purchases = await self.db.purchases.find({}).to_list(None)

    async def ok(self, method, path, body=None, expected=200, client=None, **options):
        response = await (client or self.client).request(method, "/api/v2" + path, json=body, **options)
        self.assertEqual(response.status_code, expected, f"{method} {path}: {response.text[:1500]}")
        return response.json()

    async def make_journey(self, product, paid=True, email="leader@example.test", organization="Synthetic Education Trust"):
        draft = await self.ok("POST", "/journeys", {"product": product, "name": "Synthetic Leader", "email": email,
                                                     "organization": organization, "desired_count": 2, "board_count": 5, "goal_amount": 25000})
        jid = draft["journey_id"]
        self.client.headers["X-V2-Draft"] = draft["draft_token"]
        saved = await self.ok("PUT", f"/journeys/{jid}/answers", {"answers": intake_answers(product)})
        self.assertTrue(saved["complete"])
        await self.ok("PUT", f"/journeys/{jid}/branding", {"branding": {"organization_name": organization, "primary_color": "#123456", "secondary_color": "#654321", "logo_data": ""}})
        if paid:
            checkout = await self.ok("POST", f"/journeys/{jid}/checkout", {})
            self.stripe.pay(checkout["session_id"])
            confirmed = await self.ok("GET", f"/journeys/{jid}/payment?session_id={checkout['session_id']}")
            self.assertEqual(confirmed["state"], "paid")
            journey = await self.core.find_journey(self.db, jid)
            await self.resources.generate_pending_resources(self.db, journey)
        return await self.core.find_journey(self.db, jid)

    async def resource_by_key(self, journey, key):
        rows = (await self.ok("GET", f"/journeys/{journey['journey_id']}/resources"))["resources"]
        return next(row for row in rows if row["key"] == key)

    async def approve(self, journey, resource):
        return await self.ok("POST", f"/journeys/{journey['journey_id']}/resources/{resource['resource_id']}/approve", {"expected_revision": resource["revision"]})

    async def submit(self, journey, answers, name="Synthetic Board Member", email="board@example.test", token=None, key="synthetic-response-1"):
        return await self.ok("POST", f"/forms/{token or journey['form_token']}/submit",
                             {"name": name, "email": email, "answers": answers, "idempotency_key": key})

    async def flush_emails(self):
        rows = await self.db.v2_email_outbox.find({}).to_list(None)
        for event in rows:
            await self.emails.process_email(self.db, event["event_id"], transport=self.transport)

    async def launch(self, journey):
        for key in ("board_opportunity", "application_questions", "board_recruitment_job_post", "linkedin_post"):
            await self.approve(journey, await self.resource_by_key(journey, key))
        preview = await self.ok("GET", f"/journeys/{journey['journey_id']}/campaign")
        return await self.ok("POST", f"/journeys/{journey['journey_id']}/campaign/launch", {"confirmed": True, "expected_revision": preview["revision"]})

    async def test_normal_deployment_allows_four_free_journeys_without_preview_login(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver") as visitor:
            with patch.dict(os.environ):
                os.environ.pop("NBB_V2_ENABLED", None)
                os.environ.pop("NBB_V2_PREVIEW_KEY", None)
                access = await self.ok("GET", "/access", client=visitor)
                self.assertTrue(access["allowed"])
                catalog = await self.ok("GET", "/catalog", client=visitor)
                self.assertEqual(len(catalog["products"]), 4)
                self.assertTrue(all(product["amount"] == 19700 for product in catalog["products"]))
                for product in self.core.PRODUCTS:
                    draft = await self.ok("POST", "/journeys", {"product": product, "name": "Synthetic Visitor", "email": "leader@example.test", "organization": "Synthetic Education Trust", "desired_count": 2, "board_count": 5, "goal_amount": 25000}, client=visitor)
                    saved = await self.ok("PUT", f"/journeys/{draft['journey_id']}/answers", {"answers": intake_answers(product)}, client=visitor, headers={"X-V2-Draft": draft["draft_token"]})
                    self.assertTrue(saved["complete"])
                    private = await visitor.get(f"/api/v2/journeys/{draft['journey_id']}/resources")
                    self.assertEqual(private.status_code, 401)
                self.assertEqual(await self.db.v2_purchases.count_documents({}), 0)

    async def test_deployment_defaults_use_existing_payment_and_transactional_email_services(self):
        with patch.dict(os.environ):
            os.environ.pop("NBB_V2_PAYMENTS_TEST_ONLY", None)
            os.environ.pop("NBB_V2_STRIPE_SECRET_KEY", None)
            os.environ.pop("NBB_V2_EMAIL_TEST_MODE", None)
            os.environ.pop("NBB_V2_TEST_EMAILS", None)
            os.environ["STRIPE_SECRET_KEY"] = "sk_live_synthetic_never_use_network"
            self.assertEqual(self.payments.stripe_key(), os.environ["STRIPE_SECRET_KEY"])
            journey = await self.make_journey("board-recommitment", paid=False)
            checkout = await self.ok("POST", f"/journeys/{journey['journey_id']}/checkout", {})
            self.stripe.pay(checkout["session_id"])
            self.stripe.sessions[checkout["session_id"]]["livemode"] = True
            await self.ok("GET", f"/journeys/{journey['journey_id']}/payment?session_id={checkout['session_id']}")
            welcome = await self.db.v2_email_outbox.find_one({"event_key": "welcome:" + journey["journey_id"]})
            delivered = await self.emails.process_email(self.db, welcome["event_id"])
            self.assertEqual(delivered["status"], "sent")
            self.assertEqual(await self.db.v2_purchases.count_documents({}), 1)
            self.assertEqual(await self.db.members.find({}).to_list(None), self.original_members)
            self.assertEqual(await self.db.purchases.find({}).to_list(None), self.original_purchases)

    async def test_four_197_checkout_flows_create_separate_entitlements_preserving_history(self):
        journeys = []
        for product in self.core.PRODUCTS:
            journey = await self.make_journey(product)
            journeys.append(journey)
            self.assertEqual(journey["product"], product)
            self.assertEqual(journey["activation_status"], "complete")
            resources = await self.db.v2_resources.count_documents({"journey_id": journey["journey_id"]})
            self.assertGreater(resources, 0)
        self.assertEqual(await self.db.v2_purchases.count_documents({}), 4)
        self.assertEqual(len(self.stripe.calls), 4)
        for call in self.stripe.calls:
            self.assertEqual(call["line_items"][0]["price_data"]["unit_amount"], 19700)
            self.assertEqual(call["metadata"]["journey_version"], "v2")
            self.assertTrue(call["metadata"]["purchase_source"].endswith("_197"))
        self.assertEqual(await self.db.members.find({}).to_list(None), self.original_members)
        self.assertEqual(await self.db.purchases.find({}).to_list(None), self.original_purchases)

    async def test_automatic_generation_worker_finishes_paid_pack_without_manual_request(self):
        journey = await self.make_journey("recruit")
        rows = await self.db.v2_resources.find({"journey_id": journey["journey_id"]}).to_list(None)
        self.assertEqual(len(rows), 39)
        # Replay the durable generation job as the startup worker does. The
        # test helper has already produced these resources, so explicitly mark
        # one generated row pending to exercise asynchronous recovery as well.
        await self.db.v2_resources.update_one({"journey_id": journey["journey_id"], "key": "linkedin_post"},
                                            {"$set": {"status": "preparing", "text": ""}})
        await self.db.v2_journeys.update_one({"journey_id": journey["journey_id"]}, {"$set": {"generation_status": "pending"}})
        tasks = await self.emails.jobs_once(self.db)
        self.assertIn(journey["journey_id"], tasks)
        await asyncio.gather(*tasks.values())
        restored = await self.db.v2_resources.find_one({"journey_id": journey["journey_id"], "key": "linkedin_post"})
        self.assertEqual(restored["status"], "ready")
        self.assertIn(journey["organization"], restored["text"])

    async def test_network_permission_is_rechecked_and_notifications_are_public_scoped(self):
        journey = await self.make_journey("recruit")
        await self.db.board_applicants.insert_one({"applicant_id": "network-test", "email": "opted-in@example.test",
            "board_opportunity_consent": True, "status": "Active", "resend_contact_id": "synthetic-contact"})
        await self.db.board_applicants.insert_one({"applicant_id": "network-no-consent", "email": "board@example.test",
            "board_opportunity_consent": False, "status": "Active", "resend_contact_id": "synthetic-other-contact"})
        await self.launch(journey)
        events = await self.db.v2_email_outbox.find({"purpose": "board-opportunity"}).to_list(None)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["to"], "opted-in@example.test")
        self.assertIn("/v2/forms/", event["payload"]["html"])
        self.assertNotIn("access=", event["payload"]["html"])
        self.assertIn("List-Unsubscribe", event["payload"]["headers"])
        await self.db.board_applicants.update_one({"applicant_id": "network-test"}, {"$set": {"board_opportunity_consent": False}})
        count = len(self.transport.calls)
        result = await self.emails.process_email(self.db, event["event_id"], transport=self.transport)
        self.assertEqual(result["status"], "suppressed")
        self.assertEqual(len(self.transport.calls), count)

    async def test_api_errors_and_private_responses_are_noindex_and_not_cached(self):
        response = await self.client.get("/api/v2/journeys/missing/resources")
        self.assertIn(response.status_code, {401, 404})
        self.assertIn("noindex", response.headers["X-Robots-Tag"])
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    async def test_checkout_double_click_and_payment_replay_are_idempotent(self):
        journey = await self.make_journey("strategic-planning", paid=False)
        path = f"/journeys/{journey['journey_id']}/checkout"
        first = await self.ok("POST", path, {})
        second = await self.ok("POST", path, {})
        self.assertEqual(first, second)
        self.assertEqual(len(self.stripe.calls), 1)
        self.stripe.pay(first["session_id"])
        for _ in range(2):
            await self.ok("GET", f"/journeys/{journey['journey_id']}/payment?session_id={first['session_id']}")
        self.assertEqual(await self.db.v2_purchases.count_documents({}), 1)
        self.assertEqual(await self.db.v2_email_outbox.count_documents({"event_key": "welcome:" + journey["journey_id"]}), 1)
        self.assertEqual(await self.db.v2_invitations.count_documents({"journey_id": journey["journey_id"], "role": "Leader"}), 1)

    async def test_unpaid_checkout_has_no_private_resources_or_purchase(self):
        journey = await self.make_journey("board-recommitment", paid=False)
        checkout = await self.ok("POST", f"/journeys/{journey['journey_id']}/checkout", {})
        result = await self.ok("GET", f"/journeys/{journey['journey_id']}/payment?session_id={checkout['session_id']}")
        self.assertEqual(result["payment_status"], "unpaid")
        self.assertEqual(await self.db.v2_purchases.count_documents({}), 0)
        response = await self.client.get(f"/api/v2/journeys/{journey['journey_id']}/resources")
        self.assertIn(response.status_code, (401, 403))

    async def test_payment_cannot_unlock_another_journey_and_rejects_mismatched_amount(self):
        first = await self.make_journey("strategic-planning", paid=False)
        checkout = await self.ok("POST", f"/journeys/{first['journey_id']}/checkout", {})
        second = await self.make_journey("board-recommitment", paid=False)
        denied = await self.client.get(f"/api/v2/journeys/{second['journey_id']}/payment?session_id={checkout['session_id']}")
        self.assertEqual(denied.status_code, 404)
        self.stripe.pay(checkout["session_id"])
        self.stripe.sessions[checkout["session_id"]]["amount_total"] = 197
        self.client.headers["X-V2-Draft"] = (await self.db.v2_journeys.find_one({"journey_id": second["journey_id"]})).get("unused", "")
        # Verification validates the payment before fulfillment, even when called
        # from a signed webhook rather than a browser draft session.
        transaction = await self.db.payment_transactions.find_one({"session_id": checkout["session_id"]})
        with self.assertRaises(HTTPException) as mismatch:
            await self.payments.record_verified_payment(self.db, transaction, self.stripe.retrieve(checkout["session_id"]))
        self.assertEqual(mismatch.exception.status_code, 403)
        self.assertEqual(await self.db.v2_purchases.count_documents({}), 0)

    async def test_live_payment_cannot_activate_test_preview(self):
        journey = await self.make_journey("board-recommitment", paid=False)
        checkout = await self.ok("POST", f"/journeys/{journey['journey_id']}/checkout", {})
        self.stripe.pay(checkout["session_id"])
        self.stripe.sessions[checkout["session_id"]]["livemode"] = True
        rejected = await self.client.get(f"/api/v2/journeys/{journey['journey_id']}/payment?session_id={checkout['session_id']}")
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(await self.db.v2_purchases.count_documents({}), 0)

    async def test_resource_approval_emails_exact_immutable_branded_editable_versions_once(self):
        journey = await self.make_journey("recruit")
        resource = await self.resource_by_key(journey, "board_expectations")
        original_text = "Synthetic Education Trust\n\nThese are the exact expectations our board approved."
        resource = await self.ok("PUT", f"/journeys/{journey['journey_id']}/resources/{resource['resource_id']}",
                                 {"expected_revision": resource["revision"], "text": original_text})
        await self.approve(journey, resource)
        await self.approve(journey, resource)
        stored = await self.db.v2_resources.find_one({"resource_id": resource["resource_id"]})
        snapshot = deepcopy(stored["approved_versions"][0])
        self.assertEqual(len(stored["approved_versions"]), 1)
        self.assertEqual(snapshot["text"], original_text)
        self.assertEqual(snapshot["branding"]["primary_color"], "#123456")
        event = await self.db.v2_email_outbox.find_one({"event_key": f"resource-approved:{resource['resource_id']}:{resource['revision']}"})
        self.assertEqual(event["to"], journey["email"])
        self.assertEqual(len(event["payload"]["attachments"]), 3)
        for fmt, signature in (("pdf", b"%PDF"), ("docx", b"PK"), ("txt", original_text.encode())):
            download = await self.client.get(f"/api/v2/journeys/{journey['journey_id']}/resources/{resource['resource_id']}/download?format={fmt}")
            self.assertEqual(download.status_code, 200)
            self.assertTrue(download.content.startswith(signature))
            self.assertEqual(download.content, base64.b64decode(snapshot["artifacts"][fmt]["content"]))
        revised = await self.ok("PUT", f"/journeys/{journey['journey_id']}/resources/{resource['resource_id']}",
                                {"expected_revision": resource["revision"], "text": original_text + "\n\nA revised expectation."})
        self.assertIsNone(revised["approved_revision"])
        await self.approve(journey, revised)
        after = await self.db.v2_resources.find_one({"resource_id": resource["resource_id"]})
        self.assertEqual(after["approved_versions"][0], snapshot)
        self.assertEqual(len(after["approved_versions"]), 2)
        self.assertEqual(await self.db.v2_email_outbox.count_documents({"resource_id": resource["resource_id"]}), 2)

    async def test_failed_email_retries_same_exact_payload_and_provider_key_without_duplicates(self):
        journey = await self.make_journey("board-recommitment")
        resource = await self.resource_by_key(journey, "participant_form")
        await self.approve(journey, resource)
        event = await self.db.v2_email_outbox.find_one({"resource_id": resource["resource_id"]})
        saved_payload = deepcopy(event["payload"])
        self.transport.fail_next = 1
        failed = await self.emails.process_email(self.db, event["event_id"], self.transport)
        self.assertEqual(failed["status"], "failed")
        await self.emails.retry_email(self.db, event["event_id"], journey["journey_id"])
        sent = await self.emails.process_email(self.db, event["event_id"], self.transport)
        self.assertEqual(sent["status"], "sent")
        await self.emails.process_email(self.db, event["event_id"], self.transport)
        self.assertEqual(len(self.transport.calls), 2)
        self.assertEqual(self.transport.calls[0], self.transport.calls[1])
        self.assertEqual(sent["payload"], saved_payload)
        self.assertEqual(len(self.transport.deliveries), 1)

    async def test_preview_email_safeguard_blocks_contacts_outside_test_allowlist(self):
        journey = await self.make_journey("board-recommitment", email="unlisted@example.test")
        event = await self.db.v2_email_outbox.find_one({"event_key": "welcome:" + journey["journey_id"]})
        blocked = await self.emails.process_email(self.db, event["event_id"], self.transport)
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(self.transport.calls, [])

    async def test_recruitment_complete_pack_confirmed_campaign_application_cv_and_actions(self):
        journey = await self.make_journey("recruit")
        rows = (await self.ok("GET", f"/journeys/{journey['journey_id']}/resources"))["resources"]
        from v2_resource_content import RECRUITMENT_INVENTORY
        self.assertEqual({row["key"] for row in rows}, {item[0] for item in RECRUITMENT_INVENTORY})
        self.assertTrue(all(row["status"] == "ready" for row in rows), [r for r in rows if r["status"] != "ready"])
        self.assertFalse(any("background" in row["key"] or "background check" in row["text"].lower() for row in rows))
        before_launch = await self.client.post(f"/api/v2/forms/{journey['form_token']}/submit", json={"name": "Candidate Avery", "email": "candidate@example.test", "answers": {"location": "Synthetic City", "profession": "Education adviser", "why_interested": "Literacy and board governance"}, "idempotency_key": "application-1"})
        self.assertEqual(before_launch.status_code, 410)
        preview = await self.ok("GET", f"/journeys/{journey['journey_id']}/campaign")
        missing_approval = await self.client.post(f"/api/v2/journeys/{journey['journey_id']}/campaign/launch", json={"confirmed": True, "expected_revision": preview["revision"]})
        self.assertEqual(missing_approval.status_code, 409)
        await self.launch(journey)
        opportunity = (await self.ok("GET", "/marketplace"))["opportunities"]
        self.assertTrue(any(item.get("organization_name") == journey["organization"] for item in opportunity))
        form = await self.ok("GET", f"/forms/{journey['form_token']}")
        self.assertEqual(form["branding"]["primary_color"], "#123456")
        answers = {question["id"]: "I can support the board's literacy work." for question in form["questions"]}
        answers.update({"location": "Synthetic City", "profession": "Education adviser", "why_interested": "Literacy and board governance"})
        payload = {"name": "Candidate Avery", "email": "candidate@example.test", "answers": answers, "idempotency_key": "application-1"}
        cv = b"Candidate Avery\nSynthetic CV: education governance experience and literacy support."
        submission = await self.client.post(f"/api/v2/forms/{journey['form_token']}/submit",
            files={"cv": ("CV.txt", cv, "text/plain")}, data={"payload": json.dumps(payload)})
        self.assertEqual(submission.status_code, 200, submission.text)
        sid = submission.json()["submission_id"]
        again = await self.submit(journey, answers, "Candidate Avery", "candidate@example.test", key="application-1")
        self.assertEqual(sid, again["submission_id"])
        self.assertEqual(await self.db.v2_submissions.count_documents({"journey_id": journey["journey_id"]}), 1)
        self.assertEqual(await self.db.v2_email_outbox.count_documents({"event_key": f"submission:{sid}:leader"}), 1)
        notice = await self.db.v2_email_outbox.find_one({"event_key": f"submission:{sid}:leader"})
        self.assertNotIn("Literacy and board governance", notice["payload"]["html"])
        response = await self.ok("GET", f"/journeys/{journey['journey_id']}/responses/{sid}")
        self.assertEqual(response["name"], "Candidate Avery")
        self.assertEqual(response["cv"]["filename"], "CV.txt")
        downloaded = await self.client.get(f"/api/v2/journeys/{journey['journey_id']}/responses/{sid}/cv")
        self.assertEqual(downloaded.content, cv)
        for kind in ("guide", "interview-invitation", "rejection"):
            generated = await self.ok("POST", f"/journeys/{journey['journey_id']}/responses/{sid}/generate", {"kind": kind})
            await self.resources.generate_pending_resources(self.db, await self.core.find_journey(self.db, journey["journey_id"]))
            generated = await self.ok("GET", f"/journeys/{journey['journey_id']}/resources/{generated['resource_id']}")
            self.assertEqual(generated["status"], "ready")
            self.assertIn("Candidate Avery", generated["text"])
            await self.approve(journey, generated)
            if kind != "guide":
                await self.ok("POST", f"/journeys/{journey['journey_id']}/resources/{generated['resource_id']}/send", {"recipient": "applicant"})
        guide_call = next(call for call in self.ai.calls if call[0] == "interview_guide")
        guide_context, _ = json.JSONDecoder().raw_decode(guide_call[1].split("VERIFIED V2 CONTEXT:\n", 1)[1])
        self.assertEqual(guide_context["cv_text"], cv.decode())
        self.assertIn("Literacy and board governance", guide_call[1])
        await self.flush_emails()
        self.assertTrue(any(payload["to"] == ["candidate@example.test"] for payload, _ in self.transport.calls))
        paused = await self.ok("POST", f"/journeys/{journey['journey_id']}/campaign/status", {"status": "paused"})
        self.assertEqual(paused["status"], "paused")
        stopped = await self.client.post(f"/api/v2/forms/{journey['form_token']}/submit", json={**payload, "idempotency_key": "after-pause"})
        self.assertEqual(stopped.status_code, 410)
        self.assertEqual((await self.ok("GET", f"/journeys/{journey['journey_id']}/responses/{sid}"))["name"], "Candidate Avery")

    async def test_repeatable_audiences_progress_private_drafts_and_skipped_categories(self):
        journey = await self.make_journey("board-fundraising-game")
        rows = [funding_audience(category, f"{category}-{i}") for category in ("individuals", "businesses", "grantmakers") for i in (1, 2)]
        answers = {"audiences": rows, "participation": "I am willing to introduce education contacts after agreement."}
        first = await self.ok("PUT", f"/forms/{journey['form_token']}/draft", {"answers": answers})
        second = await self.ok("PUT", f"/forms/{journey['form_token']}/draft", {"answers": {"audiences": [], "participation": "I am unsure about my available time."}})
        self.assertNotEqual(first["draft_token"], second["draft_token"])
        anonymous = await self.ok("GET", f"/forms/{journey['form_token']}")
        self.assertNotIn("answers", anonymous)
        recovered = await self.ok("GET", f"/forms/{journey['form_token']}?draft_token={first['draft_token']}")
        self.assertEqual(recovered["answers"], answers)
        result = await self.ok("POST", f"/forms/{journey['form_token']}/submit", {"name": "Synthetic Board Member", "email": "board@example.test", "answers": answers, "draft_token": first["draft_token"]})
        empty = await self.ok("POST", f"/forms/{journey['form_token']}/submit", {"name": "Synthetic Volunteer", "email": "board@example.test", "answers": {"audiences": [], "participation": "I am unsure about my available time."}, "draft_token": second["draft_token"]})
        self.assertNotEqual(result["submission_id"], empty["submission_id"])
        response = await self.ok("GET", f"/journeys/{journey['journey_id']}/responses/{result['submission_id']}")
        self.assertEqual(len(response["answers"]["audiences"]), 6)
        self.assertEqual(len(self.ai.calls), 0, "Participant fundraising ideas must not trigger AI audience recommendations")
        bad = await self.client.post(f"/api/v2/forms/{journey['form_token']}/submit", json={"name": "Synthetic incomplete", "email": "board@example.test", "answers": {"audiences": [{"category": "individuals", "funder": "Local teachers"}], "participation": "I can help."}, "idempotency_key": "incomplete"})
        self.assertEqual(bad.status_code, 422)

    async def test_fundraising_group_preserves_overlaps_adopts_only_agreed_ideas_and_consent(self):
        journey = await self.make_journey("board-fundraising-game")
        first = funding_audience("businesses", "business-1", "Local business owners", "Arrange personal introductions.")
        second = funding_audience("businesses", "business-2", "Local business owners", "Invite them to observe our work.")
        reject = funding_audience("individuals", "individual-1", "UNAPPROVED AUDIENCE TO EXCLUDE")
        await self.submit(journey, {"audiences": [first, reject], "participation": "I am willing to make introductions."}, key="member-one")
        await self.submit(journey, {"audiences": [second], "participation": "I can help host an agreed visit."}, name="Synthetic second member", key="member-two")
        await self.ok("PUT", f"/journeys/{journey['journey_id']}/meeting", {"date": "2030-01-20", "time": "10:30", "timezone": "Europe/London"})
        group = await self.ok("GET", f"/journeys/{journey['journey_id']}/group")
        business = next(section for section in group["sections"] if section["key"] == "businesses")
        self.assertEqual(len(business["ideas"]), 2)
        self.assertEqual(len(business["overlap_groups"][0]["source_ids"]), 2)
        self.assertEqual({idea["content"]["attract"] for idea in business["ideas"]}, {first["attract"], second["attract"]})
        combined = {**first, "attract": first["attract"] + " " + second["attract"]}
        adopted = await self.ok("POST", f"/journeys/{journey['journey_id']}/decisions", {"category": "businesses", "title": "Local business owners", "content": combined, "source_ids": [idea["source_id"] for idea in business["ideas"]], "status": "adopted"})
        individual = next(section for section in group["sections"] if section["key"] == "individuals")["ideas"][0]
        await self.ok("POST", f"/journeys/{journey['journey_id']}/decisions", {"category": "individuals", "title": reject["funder"], "content": reject, "source_ids": [individual["source_id"]], "status": "rejected"})
        participant = group["participants"][0]
        declined = await self.client.post(f"/api/v2/journeys/{journey['journey_id']}/commitments", json={"participant_id": participant["participant_id"], "responsibility": "Make introductions.", "audience_ids": [adopted["decision_id"]], "consent_confirmed": False})
        self.assertEqual(declined.status_code, 422)
        await self.ok("POST", f"/journeys/{journey['journey_id']}/commitments", {"participant_id": participant["participant_id"], "responsibility": "Make the agreed introductions.", "audience_ids": [adopted["decision_id"]], "consent_confirmed": True})
        preview = await self.ok("POST", f"/journeys/{journey['journey_id']}/final-preview", {})
        self.assertIn(first["attract"], preview["text"])
        self.assertIn(second["attract"], preview["text"])
        self.assertIn("Make the agreed introductions.", preview["text"])
        self.assertNotIn(reject["funder"], preview["text"])
        await self.approve(journey, preview)
        approved = await self.db.v2_email_outbox.find_one({"resource_id": preview["resource_id"]})
        self.assertEqual(approved["to"], journey["email"])
        await self.flush_emails()
        self.assertEqual((await self.db.v2_email_outbox.find_one({"event_id": approved["event_id"]}))["status"], "sent")

    async def test_strategic_board_questionnaire_mission_and_only_adopted_plan_delivery(self):
        journey = await self.make_journey("strategic-planning")
        invite = await self.ok("POST", f"/journeys/{journey['journey_id']}/invitations", {"name": "Synthetic Board Member", "email": "board@example.test", "role": "Board Member", "send": True})
        context = await self.ok("GET", f"/forms/{invite['form_token']}")
        self.assertEqual(context["branding"]["primary_color"], "#123456")
        answers = {question["id"]: f"UNADOPTED {question['id']} proposal." for question in context["questions"]}
        await self.submit(journey, answers, token=invite["form_token"])
        group = await self.ok("GET", f"/journeys/{journey['journey_id']}/group")
        mission = next(section for section in group["sections"] if section["title"] == "Mission")
        goals = next(section for section in group["sections"] if section["title"] == "Goals")
        await self.ok("POST", f"/journeys/{journey['journey_id']}/decisions", {"category": mission["key"], "title": "Our existing mission", "keep_existing_mission": True, "status": "adopted"})
        agreed = "The board approved expanding the existing literacy sessions within verified available resources."
        await self.ok("POST", f"/journeys/{journey['journey_id']}/decisions", {"category": goals["key"], "title": "Approved literacy goal", "content": agreed, "source_ids": [goals["ideas"][0]["source_id"]], "status": "adopted"})
        preview = await self.ok("POST", f"/journeys/{journey['journey_id']}/final-preview", {})
        self.assertIn(journey["answers"]["mission"], preview["text"])
        self.assertIn(agreed, preview["text"])
        self.assertNotIn("UNADOPTED", preview["text"])
        self.assertNotIn("$", preview["text"], "No budget figures were supplied or adopted")
        await self.approve(journey, preview)
        downloaded = await self.client.get(f"/api/v2/journeys/{journey['journey_id']}/resources/{preview['resource_id']}/download?format=docx")
        self.assertTrue(downloaded.content.startswith(b"PK"))
        event = await self.db.v2_email_outbox.find_one({"resource_id": preview["resource_id"]})
        self.assertIn("access=", event["payload"]["html"])
        self.assertEqual(event["to"], journey["email"])

    async def test_group_decision_change_invalidates_stale_final_approval(self):
        journey = await self.make_journey("strategic-planning")
        group = await self.ok("GET", f"/journeys/{journey['journey_id']}/group")
        category = group["sections"][0]["key"]
        decision = await self.ok("POST", f"/journeys/{journey['journey_id']}/decisions", {"category": category, "title": "Agreed mission", "content": "The approved mission.", "status": "adopted"})
        preview = await self.ok("POST", f"/journeys/{journey['journey_id']}/final-preview", {})
        await self.ok("POST", f"/journeys/{journey['journey_id']}/decisions", {**decision, "content": "The revised approved mission."})
        stale = await self.client.post(f"/api/v2/journeys/{journey['journey_id']}/resources/{preview['resource_id']}/approve", json={"expected_revision": preview["revision"]})
        self.assertEqual(stale.status_code, 409)
        renewed = await self.ok("POST", f"/journeys/{journey['journey_id']}/final-preview", {})
        self.assertIn("The revised approved mission.", renewed["text"])
        await self.approve(journey, renewed)

    async def test_shared_meeting_is_read_only_and_excludes_private_contacts(self):
        journey = await self.make_journey("strategic-planning")
        shared = await self.ok("POST", f"/journeys/{journey['journey_id']}/group/share", {})
        token = shared["group_link"].rsplit("/", 1)[-1]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver") as visitor:
            data = await self.ok("GET", f"/meeting/{token}", client=visitor)
            self.assertTrue(data["read_only"])
            self.assertNotIn(journey["email"], json.dumps(data))
            self.assertNotIn("form_token", json.dumps(data))
            denied = await visitor.post(f"/api/v2/journeys/{journey['journey_id']}/decisions", json={"category": data["sections"][0]["key"], "content": "Unauthorized", "status": "adopted"})
            self.assertEqual(denied.status_code, 401)

    async def test_recommitment_templates_response_source_and_approved_conversation_email(self):
        from v2_form_content import RECOMMIT_ADVISORY
        journey = await self.make_journey("board-recommitment")
        rows = (await self.ok("GET", f"/journeys/{journey['journey_id']}/resources"))["resources"]
        for key in ("recommitment_invitation", "recommitment_followup_1", "recommitment_followup_2"):
            template = next(row for row in rows if row["key"] == key)
            self.assertIn(journey["form_token"], template["text"])
        external = await self.ok("POST", f"/journeys/{journey['journey_id']}/invitations", {"name": "Synthetic Board Member", "email": "board@example.test", "send": False})
        self.assertEqual(external["delivery_status"], "not_sent")
        self.assertEqual(await self.db.v2_email_outbox.count_documents({"event_key": f"invitation:{external['invitation_id']}"}), 0)
        answers = {"recommitment": RECOMMIT_ADVISORY, "decision_reason": "I am unsure I can attend regular meetings.", "contribution_interests": ["Fundraising / Resource Development"], "strengths_resources": "Education contacts.", "monthly_availability": "2–4 hours", "anything_else": "Please discuss expectations with me."}
        submitted = await self.submit(journey, answers, token=external["form_token"])
        sid = submitted["submission_id"]
        before = await self.db.v2_submissions.find_one({"submission_id": sid})
        generated = await self.ok("POST", f"/journeys/{journey['journey_id']}/responses/{sid}/generate", {"kind": "guide"})
        await self.resources.generate_pending_resources(self.db, await self.core.find_journey(self.db, journey["journey_id"]))
        generated = await self.ok("GET", f"/journeys/{journey['journey_id']}/resources/{generated['resource_id']}")
        self.assertIn(answers["decision_reason"], generated["text"])
        self.assertIn(RECOMMIT_ADVISORY, generated["text"])
        self.assertNotIn("recommitted", before)
        edited = await self.ok("PUT", f"/journeys/{journey['journey_id']}/resources/{generated['resource_id']}", {"expected_revision": generated["revision"], "text": generated["text"] + "\n\nAsk what meeting frequency would be realistic."})
        await self.approve(journey, edited)
        self.assertEqual(await self.db.v2_submissions.find_one({"submission_id": sid}), before)
        event = await self.db.v2_email_outbox.find_one({"resource_id": generated["resource_id"]})
        self.assertEqual(event["to"], journey["email"])
        self.assertEqual(base64.b64decode(event["payload"]["attachments"][2]["content"]).decode(), edited["text"])

    async def test_other_organization_cannot_read_submission_resource_or_cv(self):
        first = await self.make_journey("board-recommitment")
        second = await self.make_journey("board-recommitment", organization="Another Synthetic Organization")
        resource = await self.resource_by_key(first, "participant_form")
        denied = await self.client.get(f"/api/v2/journeys/{second['journey_id']}/resources/{resource['resource_id']}")
        self.assertEqual(denied.status_code, 404)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver") as outsider:
            for path in (f"/journeys/{first['journey_id']}/resources", f"/journeys/{first['journey_id']}/responses"):
                response = await outsider.get("/api/v2" + path)
                self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main(verbosity=2)
