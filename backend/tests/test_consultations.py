"""Standalone consultation payments, authorization, persistence and transactional delivery.

HTTP acceptance tests use disposable Mongo and replace only Stripe/Resend transport.
They cannot charge a customer or send email outside this process.
"""
import copy
import hashlib
import hmac
import json
import os
import sys
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))
import consultation_routes as consultations


class ConsultationConfiguration(unittest.TestCase):
    def test_only_four_services_and_separate_fixed_price(self):
        self.assertEqual(consultations.AMOUNT, 19700)
        self.assertEqual(len(consultations.DEFAULTS["home"]["products"]), 4)
        self.assertNotIn(consultations.SOURCE, {"board_fundraising_game_1497", "recruitment_self_guided", "strategic_planning_497", "reactivation_self_guided"})
        self.assertNotIn("free consultation", json.dumps(consultations.DEFAULTS).lower())

    def test_admin_cannot_change_price_or_supply_unsafe_booking_destination(self):
        from fastapi import HTTPException
        settings = copy.deepcopy(consultations.DEFAULTS["consultation"])
        for url in ("javascript:alert(1)", "https://evil.example/booking", "https://calendly.com.evil.example/book", "https://owner:password@calendly.com/book"):
            with self.assertRaises(HTTPException):
                consultations.validate_section("consultation", {**settings, "bookingUrl": url})
        with self.assertRaises(HTTPException):
            consultations.validate_section("consultation", {**settings, "amount": 1})
        self.assertEqual(consultations.validate_section("consultation", settings), settings)

    def test_existing_testimonials_only_and_explicit_order(self):
        from fastapi import HTTPException
        personal = copy.deepcopy(consultations.DEFAULTS["personal"])
        personal["testimonialIds"] = [7, 0, 4]
        self.assertEqual(consultations.validate_section("personal", personal)["testimonialIds"], [7, 0, 4])
        for value in ([0, 0], [100], [True], "0"):
            with self.assertRaises(HTTPException):
                consultations.validate_section("personal", {**personal, "testimonialIds": value})


@unittest.skipUnless(os.environ.get("RECOVERY_ACCEPTANCE") == "1", "Requires disposable local Mongo acceptance configuration")
class ConsultationHTTP(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import httpx
        from fastapi import FastAPI
        from motor.motor_asyncio import AsyncIOMotorClient
        from auth_service import create_access_token
        from payment_routes import create_stripe_webhook_router
        assert os.environ["MONGO_URL"].startswith("mongodb://127.0.0.1:")
        self.mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
        self.db = self.mongo.nbb_part_one_consultation_tests
        for name in await self.db.list_collection_names():
            await self.db[name].delete_many({})
        await consultations.ensure_consultation_indexes(self.db)
        await self.db.users.insert_one({"user_id": "consultation-admin", "email": "admin@example.test", "role": "admin"})
        app = FastAPI()
        app.include_router(consultations.create_consultation_router(self.db))
        app.include_router(create_stripe_webhook_router(self.db))
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.headers = {"Authorization": "Bearer " + create_access_token("consultation-admin", "admin@example.test")}
        self.sessions = {}
        self.created = []

        def create(**kwargs):
            self.created.append(kwargs)
            sid = "cs_test_consultation_" + str(len(self.created))
            self.sessions[sid] = {"id": sid, "metadata": kwargs["metadata"], "client_reference_id": kwargs["client_reference_id"], "currency": "usd", "amount_subtotal": 19700, "amount_total": 19700, "payment_status": "unpaid", "status": "open", "payment_intent": "pi_test_consultation", "livemode": False}
            return SimpleNamespace(id=sid, url="https://checkout.stripe.com/c/pay/" + sid)

        self.email = AsyncMock(return_value={"id": "fake-provider-consultation"})
        self.price = patch("payment_routes.resolve_offer_price_id", return_value="price_consultation_197").start()
        patch("stripe.checkout.Session.create", side_effect=create).start()
        patch("stripe.checkout.Session.retrieve", side_effect=lambda sid: self.sessions[sid]).start()
        patch("resend.Emails.send_async", self.email).start()
        self.environ = patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_consultation_unit_test", "CALENDLY_WEBHOOK_SIGNING_KEY": "calendly_unit_test", "PUBLIC_ORIGIN": "https://nonprofitboardbuilder.com", "NONPROFIT_SENDER": "sender@example.test", "RESEND_API_KEY": "isolated-provider-disabled"})
        self.environ.start()

    async def asyncTearDown(self):
        patch.stopall()
        await self.client.aclose()
        self.mongo.close()

    async def intake(self, **changes):
        payload = {"request_id": str(uuid.uuid4()), "name": "Sample Leader", "email": "leader@example.org", "organization": "Sample Nonprofit", "website": "https://example.org", "role": "Executive Director", "topic": "Our board needs a clearer direction.", **changes}
        response = await self.client.post("/api/consultations/intake", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json(), payload

    async def checkout(self, paid=False):
        data, _ = await self.intake()
        token = data["token"]
        response = await self.client.post(f"/api/consultations/{token}/checkout")
        self.assertEqual(response.status_code, 200, response.text)
        row = await self.db.consultations.find_one({"access_token": token})
        if paid:
            self.sessions[row["session_id"]]["payment_status"] = "paid"
            self.sessions[row["session_id"]]["status"] = "complete"
        return token, row

    async def confirm(self, token, session=None):
        return await self.client.post(f"/api/consultations/{token}/confirm", json={"session_id": session or ""})

    def stripe_event(self, row, kind="checkout.session.completed"):
        return {"id": "evt_consultation_1", "type": kind, "data": {"object": self.sessions[row["session_id"]]}}

    async def webhook(self, row, kind="checkout.session.completed", valid=True):
        raw = json.dumps(self.stripe_event(row, kind)).encode()
        timestamp = str(int(time.time()))
        signature = hmac.new(b"whsec_consultation_unit_test", timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest() if valid else "invalid"
        return await self.client.post("/api/stripe/webhook", content=raw, headers={"Stripe-Signature": f"t={timestamp},v1={signature}"})

    async def test_short_intake_persists_and_duplicate_submission_reuses_record(self):
        data, payload = await self.intake()
        again = await self.client.post("/api/consultations/intake", json=payload)
        self.assertEqual(again.json()["token"], data["token"])
        self.assertEqual(await self.db.consultations.count_documents({}), 1)
        self.assertEqual(await self.db.members.count_documents({}), 0)
        changed = await self.client.post("/api/consultations/intake", json={**payload, "email": "someone-else@example.org"})
        self.assertEqual(changed.status_code, 409)

    async def test_checkout_is_separate_197_and_duplicate_click_does_not_charge_twice(self):
        token, row = await self.checkout()
        self.price.assert_called_once_with("STRIPE_ROONEY_CONSULTATION_197_PRICE_ID", consultations.SOURCE, "Professional Consultation with Rooney Akpesiri", 19700)
        self.assertEqual(self.created[0]["metadata"]["offer_source"], consultations.SOURCE)
        self.assertEqual(self.created[0]["customer_email"], "leader@example.org")
        self.assertEqual(self.created[0]["line_items"], [{"price": "price_consultation_197", "quantity": 1}])
        self.assertTrue(self.created[0]["success_url"].startswith("https://nonprofitboardbuilder.com/consultation/confirmed"))
        again = await self.client.post(f"/api/consultations/{token}/checkout")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(len(self.created), 1)
        self.assertEqual(await self.db.payment_transactions.count_documents({}), 0)

    async def test_unpaid_manual_success_and_foreign_tokens_never_unlock_booking(self):
        token, row = await self.checkout()
        response = await self.confirm(token, row["session_id"])
        self.assertEqual(response.json()["payment_status"], "pending")
        denied = await self.client.get(f"/api/consultations/{token}/book")
        self.assertEqual(denied.status_code, 402)
        self.assertNotIn("calendly", response.text)
        self.assertEqual((await self.confirm(token, "cs_another_person")).status_code, 403)
        self.assertEqual((await self.client.get("/api/consultations/" + "x" * 43)).status_code, 404)
        self.email.assert_not_called()

    async def test_wrong_amount_currency_or_product_cannot_grant_access(self):
        token, row = await self.checkout(paid=True)
        original = copy.deepcopy(self.sessions[row["session_id"]])
        for changes in ({"amount_subtotal": 1}, {"amount_total": 19699}, {"currency": "eur"}, {"client_reference_id": "other"}, {"metadata": {"offer_source": "board_fundraising_game_1497", "consultation_id": row["consultation_id"]}}):
            self.sessions[row["session_id"]] = {**original, **changes}
            response = await self.confirm(token)
            self.assertEqual(response.status_code, 409, response.text)
            self.assertNotEqual((await self.db.consultations.find_one({"access_token": token}))["payment_status"], "paid")
        self.email.assert_not_called()

    async def test_signed_webhook_and_success_confirmation_dedupe_email_and_keep_entitlement(self):
        token, row = await self.checkout(paid=True)
        self.assertEqual((await self.webhook(row)).status_code, 200)
        self.assertEqual((await self.webhook(row)).status_code, 200)
        self.assertEqual((await self.confirm(token)).json()["payment_status"], "paid")
        self.email.assert_awaited_once()
        session = self.sessions[row["session_id"]]
        await self.webhook(row, "checkout.session.expired")
        self.assertEqual((await self.db.consultations.find_one({"access_token": token}))["payment_status"], "paid")
        paid = await self.client.post(f"/api/consultations/{token}/checkout")
        self.assertEqual(paid.json()["resume_url"], "/consultation/resume/" + token)
        self.assertEqual(len(self.created), 1)
        self.assertEqual(await self.db.members.count_documents({}), 0)

    async def test_invalid_stripe_signature_cannot_confirm_payment(self):
        token, row = await self.checkout(paid=True)
        self.assertEqual((await self.webhook(row, valid=False)).status_code, 400)
        self.assertEqual((await self.db.consultations.find_one({"access_token": token}))["payment_status"], "pending")

    async def test_verified_paid_entitlement_survives_stripe_outage_when_resuming(self):
        import stripe
        token, row = await self.checkout(paid=True)
        await self.confirm(token)
        with patch("stripe.checkout.Session.retrieve", side_effect=stripe.APIConnectionError("Simulated provider outage")):
            self.assertEqual((await self.confirm(token)).json()["payment_status"], "paid")
            self.assertEqual((await self.client.get(f"/api/consultations/{token}/book")).status_code, 303)
            self.assertEqual((await self.confirm(token, "cs_someone_else")).status_code, 403)
        self.email.assert_awaited_once()

    async def test_failed_and_expired_sessions_never_grant_paid_access_and_expiry_can_retry(self):
        token, row = await self.checkout()
        await self.webhook(row, "checkout.session.async_payment_failed")
        self.assertEqual((await self.client.get(f"/api/consultations/{token}/book")).status_code, 402)
        self.sessions[row["session_id"]]["status"] = "expired"
        await self.webhook(row, "checkout.session.expired")
        self.assertEqual((await self.client.post(f"/api/consultations/{token}/checkout")).status_code, 200)
        self.assertEqual(len(self.created), 2)
        self.assertNotEqual(self.created[0]["idempotency_key"], self.created[1]["idempotency_key"])
        self.email.assert_not_called()

    async def test_booking_redirect_prefills_only_contact_and_opaque_id_without_private_details(self):
        from urllib.parse import urlparse, parse_qs
        token, row = await self.checkout(paid=True)
        await self.confirm(token)
        response = await self.client.get(f"/api/consultations/{token}/book", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        destination = response.headers["location"]
        self.assertEqual(urlparse(destination).hostname, "calendly.com")
        self.assertEqual(set(parse_qs(urlparse(destination).query)), {"name", "email", "utm_content"})
        for private in (token, row["session_id"], "pi_test_consultation", "Our board needs"):
            self.assertNotIn(private, destination)
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")
        self.assertEqual((await self.db.consultations.find_one({"access_token": token}))["booking_status"], "link_opened")

    async def test_paid_customer_can_recover_without_enumeration_or_second_charge(self):
        token, row = await self.checkout(paid=True)
        await self.confirm(token)
        responses = []
        for email in ("leader@example.org", "unknown@example.org"):
            responses.append(await self.client.post("/api/consultations/recover", json={"email": email}))
        self.assertEqual(responses[0].json(), responses[1].json())
        self.assertEqual(self.email.await_count, 2)
        self.assertEqual(len(self.created), 1)
        self.assertIn("/consultation/resume/" + token, self.email.call_args.args[0]["html"])

    async def test_failed_confirmation_email_is_saved_and_safely_retried(self):
        token, row = await self.checkout(paid=True)
        self.email.side_effect = RuntimeError("Temporary simulated provider outage")
        self.assertEqual((await self.confirm(token)).json()["payment_status"], "paid")
        delivery = await self.db.workflow_email_deliveries.find_one({})
        self.assertEqual(delivery["status"], "failed")
        self.email.side_effect = None
        await consultations.recover_consultations(self.db)
        await consultations.recover_consultations(self.db)
        self.assertEqual(self.email.await_count, 2)
        self.assertEqual((await self.db.workflow_email_deliveries.find_one({}))["status"], "sent")
        self.assertEqual(self.email.call_args_list[0].args[1], self.email.call_args_list[1].args[1])

    async def test_admin_content_all_sections_persists_independently_and_public_hides_booking_url(self):
        for section in consultations.DEFAULTS:
            payload = copy.deepcopy(consultations.DEFAULTS[section])
            key = {"home": "heroHeadline", "personal": "headline", "consultation": "confirmationMessage"}[section]
            payload[key] = "My exact words " + section + "\n\n## My heading\n\n**Emphasis** and [my link](https://example.org)."
            result = await self.client.put("/api/admin/professional/content/" + section, headers=self.headers, json=payload)
            self.assertEqual(result.status_code, 200, result.text)
            saved = (await self.db.site_content.find_one({"key": consultations.CONTENT_KEY}))["content"][section]
            self.assertEqual(saved[key], payload[key])
        public = await self.client.get("/api/professional/content")
        self.assertNotIn("bookingUrl", public.json()["content"]["consultation"])
        self.assertNotIn("calendly.com", public.text)
        self.assertTrue(public.json()["content"]["personal"]["headline"].startswith("My exact words personal"))

    async def test_admin_auth_separate_records_notes_resend_and_public_privacy(self):
        token, row = await self.checkout(paid=True)
        await self.confirm(token)
        consultation_id = row["consultation_id"]
        self.assertEqual((await self.client.get("/api/admin/consultations")).status_code, 401)
        self.assertEqual((await self.client.put("/api/admin/professional/content/home", json=consultations.DEFAULTS["home"])).status_code, 401)
        notes = {"before": "Private context", "after": "Private follow-up"}
        self.assertEqual((await self.client.put(f"/api/admin/consultations/{consultation_id}/notes", headers=self.headers, json=notes)).status_code, 200)
        record = (await self.client.get(f"/api/admin/consultations/{consultation_id}", headers=self.headers)).json()
        self.assertEqual(record["private_notes"], notes)
        self.assertNotIn("access_token", record)
        self.assertNotIn("token_hash", record)
        public = await self.client.get(f"/api/consultations/{token}")
        self.assertNotIn("Private", public.text)
        self.assertNotIn("session_id", public.text)
        resend = {"request_id": str(uuid.uuid4())}
        for _ in range(2):
            response = await self.client.post(f"/api/admin/consultations/{consultation_id}/resend", headers=self.headers, json=resend)
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.email.await_count, 2)
        self.assertEqual((await self.client.get("/api/admin/consultations", headers=self.headers)).json()["total"], 1)

    async def test_signed_calendly_confirmations_set_actual_booking_and_reject_invalid_replays(self):
        token, row = await self.checkout(paid=True)
        await self.confirm(token)
        event = {"event": "invitee.created", "created_at": "2026-10-19T12:00:00Z", "payload": {"tracking": {"utm_content": row["consultation_id"]}, "email": row["email"], "uri": "https://api.calendly.com/scheduled_events/event/invitees/person", "event": "https://api.calendly.com/scheduled_events/event", "scheduled_event": {"start_time": "2026-10-21T12:00:00Z"}}}
        async def send(valid=True):
            raw = json.dumps(event).encode(); timestamp = str(int(time.time()))
            digest = hmac.new(b"calendly_unit_test", timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest() if valid else "invalid"
            return await self.client.post("/api/consultations/calendly-webhook", content=raw, headers={"Calendly-Webhook-Signature": f"t={timestamp},v1={digest}"})
        self.assertEqual((await send(False)).status_code, 400)
        self.assertEqual((await send()).status_code, 200)
        self.assertEqual((await send()).status_code, 200)
        self.assertEqual((await self.db.consultations.find_one({"access_token": token}))["booking_status"], "booked")
        self.assertEqual(self.email.await_count, 2)
        event.update(event="invitee.canceled", created_at="2026-10-19T13:00:00Z")
        await send()
        event.update(event="invitee.created", created_at="2026-10-19T12:00:00Z")
        await send()
        self.assertEqual((await self.db.consultations.find_one({"access_token": token}))["booking_status"], "cancelled")

    async def test_unknown_email_recovery_is_throttled(self):
        for _ in range(3):
            self.assertEqual((await self.client.post("/api/consultations/recover", json={"email": "unknown@example.org"})).status_code, 200)
        self.assertEqual((await self.client.post("/api/consultations/recover", json={"email": "unknown@example.org"})).status_code, 429)
        self.email.assert_not_called()
