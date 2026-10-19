"""Professional entry point and standalone paid consultations.

This collection never creates a member or grants one of the four product entitlements.
Stripe's existing signed webhook and server-side retrieval are the only payment trust sources.
"""
import asyncio
import copy
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from auth_service import authenticate_admin
from workflow_delivery import deliver_once

SOURCE = "rooney_professional_consultation_197"
CONTENT_KEY = "professional-entry-part-one"
AMOUNT = 19700
DEFAULTS = json.loads((Path(__file__).resolve().parents[1] / "frontend/src/content/professionalEntry.json").read_text())
# Reuse the project's existing booking destination without putting it in the public bundle.
DEFAULTS["consultation"]["bookingUrl"] = "https://calendly.com/boardbuilder/recruitboard"
logger = logging.getLogger(__name__)


def now():
    return datetime.now(timezone.utc).isoformat()


def origin():
    return os.environ.get("PUBLIC_ORIGIN", "https://nonprofitboardbuilder.com").rstrip("/")


def safe_url(value, *, internal=False, calendly=False):
    if not isinstance(value, str) or len(value) > 2000 or any(c.isspace() or ord(c) < 32 for c in value):
        return False
    if internal and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return True
    parsed = urlparse(value)
    return (parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
            and (not calendly or parsed.hostname == "calendly.com" or parsed.hostname.endswith(".calendly.com")))


async def content(db):
    saved = await db.site_content.find_one({"key": CONTENT_KEY}, {"_id": 0}) or {}
    result = copy.deepcopy(DEFAULTS)
    for section in result:
        result[section].update((saved.get("content") or {}).get(section) or {})
    return result


def validate_section(section, payload):
    if not isinstance(payload, dict) or set(payload) != set(DEFAULTS[section]):
        raise HTTPException(422, "The page fields are incomplete or unsupported. Reload the editor and try again.")
    for key, default in DEFAULTS[section].items():
        value = payload[key]
        if key == "products":
            if not isinstance(value, list) or len(value) != 4:
                raise HTTPException(422, "Keep the four existing services.")
            for product in value:
                if not isinstance(product, dict) or set(product) != {"eyebrow", "title", "text", "cta"} or any(not isinstance(v, str) or len(v) > 10000 for v in product.values()):
                    raise HTTPException(422, "Invalid service content.")
        elif key == "testimonialIds":
            if not isinstance(value, list) or len(value) > 8 or len(set(map(str, value))) != len(value) or any(type(v) is not int or v not in range(8) for v in value):
                raise HTTPException(422, "Choose existing testimonials without duplicates.")
        elif not isinstance(value, str) or len(value) > 40000:
            raise HTTPException(422, "Page content must be text of a supported length.")
    for key in ("portrait", "fundraisingUrl", "gameUrl", "bookingUrl"):
        if key in payload and not safe_url(payload[key], internal=key == "gameUrl", calendly=key == "bookingUrl"):
            raise HTTPException(422, "Use a secure, valid image or destination URL. Booking requires a Calendly URL.")
    return payload


class Intake(BaseModel):
    request_id: uuid.UUID
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    organization: str = Field(min_length=2, max_length=200)
    website: str = Field(default="", max_length=2000)
    role: str = Field(min_length=2, max_length=200)
    topic: str = Field(min_length=5, max_length=6000)


class Confirm(BaseModel):
    session_id: str = Field(default="", max_length=200)


class Recovery(BaseModel):
    email: EmailStr


class Notes(BaseModel):
    before: str = Field(default="", max_length=20000)
    after: str = Field(default="", max_length=20000)


class ResendRequest(BaseModel):
    request_id: uuid.UUID


def public_record(row):
    return {key: row.get(key) for key in ("consultation_id", "name", "organization", "payment_status", "booking_status", "amount", "currency", "paid_at")}


async def token_record(db, token):
    if len(token) < 40 or len(token) > 100:
        raise HTTPException(404, "This consultation link could not be found.")
    row = await db.consultations.find_one({"token_hash": hashlib.sha256(token.encode()).hexdigest()}, {"_id": 0})
    if not row:
        raise HTTPException(404, "This consultation link could not be found.")
    return row


async def send_booking_email(db, row, event_key=None, *, booked=False):
    settings = (await content(db))["consultation"]
    return await deliver_once(db, "consultation:" + row["consultation_id"], event_key or "consultation-paid",
        row["email"], settings["bookedEmailSubject" if booked else "emailSubject"],
        settings["bookedEmailBody" if booked else "emailBody"],
        origin() + "/consultation/resume/" + row["access_token"], cta_label=settings["bookingCta"])


async def verify_payment(db, row, session_id=None):
    session_id = session_id or row.get("session_id")
    if not session_id or session_id != row.get("session_id"):
        raise HTTPException(403, "This payment does not belong to your consultation.")
    try:
        session = await asyncio.to_thread(stripe.checkout.Session.retrieve, session_id)
    except stripe.StripeError as exc:
        raise HTTPException(503, "Payment confirmation is temporarily unavailable. Please try again.") from exc
    metadata = session.get("metadata") or {}
    if (metadata.get("consultation_id") != row["consultation_id"] or metadata.get("offer_source") != SOURCE
            or session.get("client_reference_id") != row["consultation_id"]
            or session.get("currency") != "usd" or session.get("amount_subtotal") != AMOUNT
            or (session.get("amount_total") or 0) < AMOUNT):
        raise HTTPException(409, "The payment details could not be matched to this consultation.")
    if session.get("payment_status") == "paid":
        await db.consultations.update_one({"consultation_id": row["consultation_id"], "payment_status": {"$ne": "paid"}},
            {"$set": {"payment_status": "paid", "paid_at": now(), "updated_at": now(),
                      "amount_paid": session["amount_total"], "stripe_payment_intent": session.get("payment_intent"),
                      "stripe_customer": session.get("customer"), "checkout_status": session.get("status"),
                      "stripe_livemode": bool(session.get("livemode"))}})
        row = await db.consultations.find_one({"consultation_id": row["consultation_id"]}, {"_id": 0})
        await send_booking_email(db, row)
    elif row.get("payment_status") != "paid":
        status = "expired" if session.get("status") == "expired" else "pending"
        await db.consultations.update_one({"consultation_id": row["consultation_id"], "payment_status": {"$ne": "paid"}},
            {"$set": {"payment_status": status, "checkout_status": session.get("status"), "updated_at": now()}})
        row = {**row, "payment_status": status, "checkout_status": session.get("status")}
    return row


async def handle_stripe_event(db, event):
    """Called only after the existing webhook has verified Stripe's signature."""
    item = event["data"]["object"]
    if (item.get("metadata") or {}).get("offer_source") != SOURCE:
        return False
    row = await db.consultations.find_one({"consultation_id": (item.get("metadata") or {}).get("consultation_id")}, {"_id": 0})
    if row and row.get("session_id") != item.get("id") and item.get("id") in row.get("checkout_history", []):
        return True  # A late event for a session already confirmed expired before retry.
    if not row or row.get("session_id") != item.get("id"):
        # A webhook can beat the checkout API's database write. Ask Stripe to retry.
        raise HTTPException(503, "The consultation checkout is still being saved.")
    if event["type"] in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        await verify_payment(db, row, item["id"])
    elif event["type"] in {"checkout.session.async_payment_failed", "checkout.session.expired"}:
        await db.consultations.update_one({"consultation_id": row["consultation_id"], "payment_status": {"$ne": "paid"}},
            {"$set": {"payment_status": "failed" if event["type"].endswith("failed") else "expired", "updated_at": now()}})
    return True


async def recover_consultations(db):
    """Resume interrupted confirmations and retry failed transactional delivery."""
    rows = await db.consultations.find({"session_id": {"$exists": True}, "payment_status": {"$in": ["pending", "failed"]}}, {"_id": 0}).sort("updated_at", 1).limit(25).to_list(25)
    for row in rows:
        try:
            await verify_payment(db, row)
        except Exception:
            logger.warning("Consultation payment reconciliation will retry", exc_info=True)
    paid = await db.consultations.find({"payment_status": "paid"}, {"_id": 0}).sort("paid_at", -1).limit(100).to_list(100)
    for row in paid:
        await send_booking_email(db, row)
    failed = await db.workflow_email_deliveries.find({"user_id": {"$regex": "^consultation:"}, "status": {"$in": ["failed", "pending", "sending"]}}, {"_id": 0}).limit(100).to_list(100)
    for message in failed:
        await deliver_once(db, message["user_id"], message["event_key"], message["recipient"], message["subject"], message["text"], message["link"], cta_label=message.get("cta_label", "CHOOSE MY MEETING TIME"))


async def consultation_recovery_loop(db):
    while True:
        try:
            await recover_consultations(db)
        except Exception:
            logger.exception("Consultation recovery will retry")
        await asyncio.sleep(60)


async def ensure_consultation_indexes(db):
    await db.consultations.create_index("consultation_id", unique=True)
    await db.consultations.create_index("request_id", unique=True)
    await db.consultations.create_index("token_hash", unique=True)
    await db.consultations.create_index("session_id", unique=True, sparse=True)
    await db.consultations.create_index("email")
    await db.consultation_throttles.create_index("expires_at", expireAfterSeconds=0)


async def no_cache(response: Response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"


def create_consultation_router(db):
    router = APIRouter(prefix="/api", dependencies=[Depends(no_cache)])

    async def throttle(key, maximum, seconds):
        window = int(time.time()) // seconds
        key = hashlib.sha256(f"{key}:{window}".encode()).hexdigest()
        await db.consultation_throttles.update_one({"_id": key}, {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": datetime.now(timezone.utc) + timedelta(seconds=seconds * 2)}}, upsert=True)
        row = await db.consultation_throttles.find_one({"_id": key})
        if row["count"] > maximum:
            raise HTTPException(429, "Please wait a few minutes before trying again.")

    @router.get("/professional/content")
    async def public_content():
        all_content = await content(db)
        # Calendly is released only through the payment-checked booking endpoint.
        all_content["consultation"].pop("bookingUrl", None)
        all_content["consultation"].pop("emailSubject", None)
        all_content["consultation"].pop("emailBody", None)
        return {"content": all_content, "amount": AMOUNT, "currency": "usd"}

    @router.get("/admin/professional/content")
    async def admin_content(request: Request):
        await authenticate_admin(request, db)
        return {"content": await content(db), "amount": AMOUNT, "currency": "usd",
                "integrations": {"stripe_configured": bool(os.environ.get("STRIPE_SECRET_KEY")),
                    "stripe_mode": "live" if os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_live_") else "test",
                    "stripe_webhook_configured": bool(os.environ.get("STRIPE_WEBHOOK_SECRET")),
                    "email_configured": bool(os.environ.get("RESEND_API_KEY") and os.environ.get("NONPROFIT_SENDER")),
                    "calendly_webhook_configured": bool(os.environ.get("CALENDLY_WEBHOOK_SIGNING_KEY"))}}

    @router.put("/admin/professional/content/{section}")
    async def save_content(section: str, payload: dict, request: Request):
        actor = await authenticate_admin(request, db)
        if section not in DEFAULTS:
            raise HTTPException(404, "Unknown content section.")
        validate_section(section, payload)
        await db.site_content.update_one({"key": CONTENT_KEY}, {"$set": {f"content.{section}": payload, "updated_at": now(), "updated_by": actor["user_id"]}}, upsert=True)
        return {"content": (await content(db))[section]}

    @router.post("/consultations/intake")
    async def intake(payload: Intake, request: Request):
        await throttle("intake:" + (request.client.host if request.client else "unknown"), 30, 600)
        values = {key: value.strip() if isinstance(value, str) else value for key, value in payload.model_dump(mode="json").items()}
        if any(not values[key] for key in ("name", "organization", "role", "topic")):
            raise HTTPException(422, "Please complete your consultation details.")
        if values["website"]:
            parsed = urlparse(values["website"] if "://" in values["website"] else "https://" + values["website"])
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
                raise HTTPException(422, "Please provide a valid organization website.")
        values["email"] = values["email"].lower()
        token = secrets.token_urlsafe(32)
        row = {**values, "consultation_id": str(uuid.uuid4()), "access_token": token, "token_hash": hashlib.sha256(token.encode()).hexdigest(),
               "product": SOURCE, "amount": AMOUNT, "currency": "usd", "payment_status": "pending", "booking_status": "not_booked", "created_at": now(), "updated_at": now(), "checkout_attempt": 0}
        await db.consultations.update_one({"request_id": values["request_id"]}, {"$setOnInsert": row}, upsert=True)
        saved = await db.consultations.find_one({"request_id": values["request_id"]}, {"_id": 0})
        if any(saved.get(key) != values[key] for key in ("name", "email", "organization", "website", "role", "topic")):
            raise HTTPException(409, "This form was already saved with different details. Start a new consultation request.")
        return {"token": saved["access_token"], "consultation": public_record(saved)}

    @router.post("/consultations/recover")
    async def recover(payload: Recovery, request: Request):
        await throttle("recover-ip:" + (request.client.host if request.client else "unknown"), 10, 600)
        await throttle("recover-email:" + str(payload.email).lower(), 3, 600)
        rows = await db.consultations.find({"email": str(payload.email).lower(), "payment_status": "paid"}, {"_id": 0}).sort("paid_at", -1).limit(10).to_list(10)
        for row in rows:
            await send_booking_email(db, row, "consultation-recovery:" + str(int(time.time()) // 600))
        return {"status": "accepted"}

    @router.post("/consultations/{token}/checkout")
    async def checkout(token: str):
        row = await token_record(db, token)
        if row["payment_status"] == "paid":
            return {"resume_url": "/consultation/resume/" + token}
        if row.get("session_id"):
            row = await verify_payment(db, row)
            if row["payment_status"] == "paid":
                return {"resume_url": "/consultation/resume/" + token}
            if row.get("checkout_status") == "open" and row.get("checkout_url"):
                return {"checkout_url": row["checkout_url"]}
            if row.get("checkout_status") != "expired":
                raise HTTPException(409, "Your payment is processing. Please check its status before starting another payment.")
        claim = await db.consultations.update_one({"consultation_id": row["consultation_id"], "$or": [{"checkout_lock": {"$exists": False}}, {"checkout_lock": {"$lt": time.time() - 120}}]}, {"$set": {"checkout_lock": time.time()}})
        if not claim.modified_count:
            raise HTTPException(409, "Your checkout is opening. Please try again in a moment.")
        attempt = row.get("checkout_attempt", 0) + 1
        try:
            from payment_routes import resolve_offer_price_id
            stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
            price_id = await asyncio.to_thread(resolve_offer_price_id, "STRIPE_ROONEY_CONSULTATION_197_PRICE_ID", SOURCE, "Professional Consultation with Rooney Akpesiri", AMOUNT)
            kwargs = {"line_items": [{"price": price_id, "quantity": 1}], "mode": "payment", "customer_email": row["email"],
                "client_reference_id": row["consultation_id"],
                "metadata": {"offer_source": SOURCE, "consultation_id": row["consultation_id"]},
                "success_url": origin() + "/consultation/confirmed?token=" + token + "&session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": origin() + "/consultation/resume/" + token + "?checkout=cancelled",
                "idempotency_key": f"consultation:{row['consultation_id']}:{attempt}"}
            # Reuse the existing account's managed-payments capability and fallback.
            try:
                session = await asyncio.to_thread(stripe.checkout.Session.create, **kwargs, managed_payments={"enabled": True})
            except stripe.InvalidRequestError as exc:
                if "managed payments" not in str(exc).lower() and "ineligible" not in str(exc).lower():
                    raise
                session = await asyncio.to_thread(stripe.checkout.Session.create, **{**kwargs, "idempotency_key": kwargs["idempotency_key"] + ":standard"}, automatic_tax={"enabled": True}, billing_address_collection="required")
            await db.consultations.update_one({"consultation_id": row["consultation_id"]}, {"$set": {"session_id": session.id, "checkout_url": session.url, "checkout_attempt": attempt, "checkout_status": "open", "payment_status": "pending", "updated_at": now()}, "$addToSet": {"checkout_history": session.id}, "$unset": {"checkout_lock": ""}})
            return {"checkout_url": session.url}
        except (stripe.StripeError, KeyError) as exc:
            await db.consultations.update_one({"consultation_id": row["consultation_id"]}, {"$unset": {"checkout_lock": ""}})
            raise HTTPException(503, "Secure payment could not open. Please try again shortly.") from exc

    @router.get("/consultations/{token}")
    async def status(token: str):
        return public_record(await token_record(db, token))

    @router.post("/consultations/{token}/confirm")
    async def confirm(token: str, payload: Confirm):
        row = await token_record(db, token)
        if row.get("session_id"):
            row = await verify_payment(db, row, payload.session_id or None)
        elif payload.session_id:
            raise HTTPException(403, "This payment does not belong to your consultation.")
        return public_record(row)

    @router.get("/consultations/{token}/book")
    async def book(token: str):
        row = await token_record(db, token)
        if row["payment_status"] != "paid":
            raise HTTPException(402, "Please complete payment before choosing a meeting time.")
        url = (await content(db))["consultation"]["bookingUrl"]
        if not safe_url(url, calendly=True):
            raise HTTPException(503, "Your payment is saved. Please contact us for help choosing your meeting time.")
        parsed = urlparse(url)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        params.update({"name": row["name"], "email": row["email"], "utm_content": row["consultation_id"]})
        await db.consultations.update_one({"consultation_id": row["consultation_id"], "booking_status": "not_booked"}, {"$set": {"booking_status": "link_opened", "booking_opened_at": now(), "updated_at": now()}})
        return RedirectResponse(urlunparse(parsed._replace(query=urlencode(params))), status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})

    @router.get("/admin/consultations")
    async def admin_list(request: Request, skip: int = 0):
        await authenticate_admin(request, db)
        skip = max(0, min(skip, 1000000))
        rows = await db.consultations.find({}, {"_id": 0, "access_token": 0, "token_hash": 0, "checkout_url": 0}).sort("created_at", -1).skip(skip).limit(50).to_list(50)
        return {"records": rows, "total": await db.consultations.count_documents({})}

    @router.get("/admin/consultations/{consultation_id}")
    async def admin_record(consultation_id: str, request: Request):
        await authenticate_admin(request, db)
        row = await db.consultations.find_one({"consultation_id": consultation_id}, {"_id": 0, "access_token": 0, "token_hash": 0, "checkout_url": 0})
        if not row:
            raise HTTPException(404, "Consultation not found.")
        row["deliveries"] = await db.workflow_email_deliveries.find({"user_id": "consultation:" + consultation_id}, {"_id": 0, "link": 0}).to_list(100)
        return row

    @router.put("/admin/consultations/{consultation_id}/notes")
    async def save_notes(consultation_id: str, payload: Notes, request: Request):
        actor = await authenticate_admin(request, db)
        changed = await db.consultations.update_one({"consultation_id": consultation_id}, {"$set": {"private_notes": payload.model_dump(), "notes_updated_by": actor["user_id"], "notes_updated_at": now()}})
        if not changed.matched_count:
            raise HTTPException(404, "Consultation not found.")
        return {"status": "saved"}

    @router.post("/admin/consultations/{consultation_id}/resend")
    async def resend(consultation_id: str, payload: ResendRequest, request: Request):
        await authenticate_admin(request, db)
        row = await db.consultations.find_one({"consultation_id": consultation_id}, {"_id": 0})
        if not row or row["payment_status"] != "paid":
            raise HTTPException(409, "Only paid consultations have a booking link.")
        return await send_booking_email(db, row, "consultation-resend:" + str(payload.request_id))

    @router.post("/consultations/calendly-webhook")
    async def calendly_webhook(request: Request):
        secret = os.environ.get("CALENDLY_WEBHOOK_SIGNING_KEY", "")
        if not secret:
            raise HTTPException(503, "Calendly booking confirmations are not configured.")
        raw = await request.body()
        signature = request.headers.get("Calendly-Webhook-Signature", "")
        try:
            parts = dict(pair.strip().split("=", 1) for pair in signature.split(","))
            stamp = parts["t"]
            expected = hmac.new(secret.encode(), stamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
            if abs(time.time() - int(stamp)) > 300 or not hmac.compare_digest(parts["v1"], expected):
                raise ValueError()
            event = json.loads(raw)
        except (KeyError, ValueError, TypeError):
            raise HTTPException(400, "Invalid Calendly signature.")
        data = event.get("payload") or {}
        consultation_id = (data.get("tracking") or {}).get("utm_content")
        if not consultation_id or event.get("event") not in {"invitee.created", "invitee.canceled"}:
            return {"status": "ignored"}
        row = await db.consultations.find_one({"consultation_id": consultation_id, "payment_status": "paid", "email": str(data.get("email", "")).lower()}, {"_id": 0})
        if not row:
            return {"status": "ignored"}
        timestamp = event.get("created_at") or data.get("updated_at") or data.get("created_at")
        if not timestamp:
            raise HTTPException(422, "A booking event timestamp is required.")
        booking_status = "booked" if event["event"] == "invitee.created" else "cancelled"
        result = await db.consultations.update_one({"consultation_id": consultation_id, "$or": [{"booking_event_at": {"$exists": False}}, {"booking_event_at": {"$lt": timestamp}}]},
            {"$set": {"booking_status": booking_status, "booking_event_at": timestamp, "calendly_invitee": data.get("uri"), "calendly_event": data.get("event"), "meeting": data.get("scheduled_event") or {}, "updated_at": now()}})
        if result.modified_count and booking_status == "booked":
            await send_booking_email(db, row, "consultation-booked:" + str(data.get("uri") or timestamp), booked=True)
        return {"status": "ok"}

    return router
