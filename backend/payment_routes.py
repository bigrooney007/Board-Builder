import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth_service import authenticate_admin
from funnel_models import CheckoutRequest


PRICE_ENV = {
    ("recruitment", "97"): "STRIPE_RECRUITMENT_97_PRICE_ID",
    ("recruitment", "497"): "STRIPE_RECRUITMENT_497_PRICE_ID",
    ("reactivation", "97"): "STRIPE_REACTIVATION_97_PRICE_ID",
    ("reactivation", "497"): "STRIPE_REACTIVATION_497_PRICE_ID",
    ("fundraising_activation", "97"): "STRIPE_FUNDRAISING_ACTIVATION_97_PRICE_ID",
    ("fundraising_activation", "497"): "STRIPE_FUNDRAISING_ACTIVATION_497_PRICE_ID",
}


class RooneyCheckoutRequest(BaseModel):
    origin_url: str = Field(min_length=1)
    internal_test: bool = False


class DirectProjectCheckoutRequest(BaseModel):
    origin_url: str = Field(min_length=1)


class DIYCheckoutRequest(BaseModel):
    origin_url: str = Field(min_length=1)


def create_payment_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/payments")
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    @router.get("/config")
    async def payment_config():
        return {
            "paid_programs_live": os.environ["PAID_PROGRAMS_LIVE"].lower() == "true",
            "recruitment_97_live": os.environ.get("RECRUITMENT_97_LIVE", "false").lower() == "true",
            "recruitment_497_live": os.environ.get("RECRUITMENT_497_LIVE", "false").lower() == "true",
            "recruit_with_rooney_997_live": os.environ.get("RECRUIT_WITH_ROONEY_997_LIVE", "false").lower() == "true",
            "stripe_mode": os.environ["STRIPE_MODE"],
        }

    @router.post("/checkout")
    async def create_checkout(payload: CheckoutRequest, request: Request):
        lead = await db.funnel_leads.find_one({"lead_id": payload.lead_id}, {"_id": 0})
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        if lead["offer_source"] == "recruitment":
            flag = "RECRUITMENT_97_LIVE" if payload.tier == "97" else "RECRUITMENT_497_LIVE"
            paid_live = os.environ.get(flag, "false").lower() == "true"
        else:
            paid_live = os.environ["PAID_PROGRAMS_LIVE"].lower() == "true"
        if not paid_live:
            if not payload.internal_test:
                raise HTTPException(status_code=403, detail="Program access is not open yet")
            await authenticate_admin(request, db)
        price_env = PRICE_ENV.get((lead["offer_source"], payload.tier))
        if not price_env:
            raise HTTPException(status_code=400, detail="This tier is not available for the selected offer")
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        option_path = {
            "recruitment": "/recruit/options", "reactivation": "/reactivate/options",
            "fundraising_activation": "/activate/options",
        }[lead["offer_source"]]
        if lead["offer_source"] == "recruitment":
            success_url = f"{payload.origin_url}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}"
        else:
            success_url = f"{payload.origin_url}{option_path}?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
        kwargs = {
            "line_items": [{"price": os.environ[price_env], "quantity": 1}], "mode": "payment",
            "customer_email": lead["email"],
            "success_url": success_url,
            "cancel_url": f"{payload.origin_url}{option_path}?checkout=cancelled",
            "metadata": {
                "lead_id": lead["lead_id"], "email": lead["email"], "organization": lead["organization"],
                "offer_source": lead["offer_source"], "selected_tier": payload.tier,
            },
        }
        try:
            session = stripe.checkout.Session.create(**kwargs, managed_payments={"enabled": True})
        except stripe.InvalidRequestError as exc:
            message = (getattr(exc, "user_message", "") or str(exc)).lower()
            if "managed payments" not in message and "ineligible" not in message:
                raise
            session = stripe.checkout.Session.create(
                **kwargs, automatic_tax={"enabled": True}, billing_address_collection="required",
            )
        now = datetime.now(timezone.utc).isoformat()
        transaction = {
            "session_id": session.id, "lead_id": lead["lead_id"], "offer_source": lead["offer_source"],
            "selected_tier": payload.tier, "amount": 9700 if payload.tier == "97" else 49700,
            "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": True, "created_at": now, "updated_at": now,
        }
        await db.payment_transactions.insert_one(transaction.copy())
        await db.funnel_leads.update_one(
            {"lead_id": lead["lead_id"]},
            {"$set": {"selected_tier": payload.tier, "stripe_session_id": session.id, "updated_at": now}},
        )
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/rooney-checkout")
    async def create_rooney_checkout(payload: RooneyCheckoutRequest, request: Request):
        live = os.environ.get("RECRUIT_WITH_ROONEY_997_LIVE", "false").lower() == "true"
        if not live:
            if not payload.internal_test:
                raise HTTPException(status_code=403, detail="Enrollment is not open yet")
            await authenticate_admin(request, db)
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": os.environ["STRIPE_RECRUIT_WITH_ROONEY_997_PRICE_ID"], "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{payload.origin_url}/recruit-with-rooney?checkout=cancelled",
            "metadata": {
                "offer_source": "recruit_with_rooney", "selected_tier": "997",
                "purchase_source": "recruit_with_rooney_997", "offer": "Recruit With Rooney",
                "support_program": "recruit_with_rooney",
            },
        }
        try:
            session = stripe.checkout.Session.create(**kwargs, managed_payments={"enabled": True})
        except stripe.InvalidRequestError as exc:
            message = (getattr(exc, "user_message", "") or str(exc)).lower()
            if "managed payments" not in message and "ineligible" not in message:
                raise
            session = stripe.checkout.Session.create(
                **kwargs, automatic_tax={"enabled": True}, billing_address_collection="required",
            )
        now = datetime.now(timezone.utc).isoformat()
        await db.payment_transactions.insert_one({
            "session_id": session.id, "lead_id": "", "offer_source": "recruit_with_rooney",
            "selected_tier": "997", "purchase_source": "recruit_with_rooney_997",
            "amount": 99700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/direct-project-checkout")
    async def create_direct_project_checkout(payload: DirectProjectCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": os.environ["STRIPE_DIRECT_BOARD_RECRUITMENT_PRICE_ID"], "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/board-recruitment-intake?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{payload.origin_url}/board-recruitment-proposal?checkout=cancelled",
            "metadata": {
                "offer_source": "direct_board_recruitment_project",
                "purchase_source": "direct_board_recruitment_project",
                "offer": "Board Recruitment Project",
            },
        }
        try:
            session = stripe.checkout.Session.create(**kwargs, managed_payments={"enabled": True})
        except stripe.InvalidRequestError as exc:
            message = (getattr(exc, "user_message", "") or str(exc)).lower()
            if "managed payments" not in message and "ineligible" not in message:
                raise
            session = stripe.checkout.Session.create(
                **kwargs, automatic_tax={"enabled": True}, billing_address_collection="required",
            )
        now = datetime.now(timezone.utc).isoformat()
        await db.payment_transactions.insert_one({
            "session_id": session.id, "lead_id": "", "offer_source": "direct_board_recruitment_project",
            "selected_tier": "direct_project", "purchase_source": "direct_board_recruitment_project",
            "offer": "Board Recruitment Project",
            "amount": 199850, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/diy-checkout")
    async def create_diy_checkout(payload: DIYCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": os.environ["STRIPE_DIY_BOARD_RECRUITMENT_497_PRICE_ID"], "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{payload.origin_url}/recruit-your-board-yourself?checkout=cancelled",
            "metadata": {
                "offer_source": "direct_diy_board_recruitment", "selected_tier": "497",
                "purchase_source": "direct_diy_board_recruitment_497",
                "offer": "Do It Yourself Board Recruitment",
            },
        }
        try:
            session = stripe.checkout.Session.create(**kwargs, managed_payments={"enabled": True})
        except stripe.InvalidRequestError as exc:
            message = (getattr(exc, "user_message", "") or str(exc)).lower()
            if "managed payments" not in message and "ineligible" not in message:
                raise
            session = stripe.checkout.Session.create(
                **kwargs, automatic_tax={"enabled": True}, billing_address_collection="required",
            )
        now = datetime.now(timezone.utc).isoformat()
        await db.payment_transactions.insert_one({
            "session_id": session.id, "lead_id": "", "offer_source": "direct_diy_board_recruitment",
            "selected_tier": "497", "purchase_source": "direct_diy_board_recruitment_497",
            "offer": "Do It Yourself Board Recruitment",
            "amount": 49700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.get("/status/{session_id}")
    async def payment_status(session_id: str):
        transaction = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        if transaction["payment_status"] != "paid":
            try:
                session = stripe.checkout.Session.retrieve(session_id)
                if session.payment_status == "paid" or session.status == "complete":
                    now = datetime.now(timezone.utc).isoformat()
                    await db.payment_transactions.update_one(
                        {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                        {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now}},
                    )
                    transaction.update({"status": "completed", "payment_status": "paid"})
            except stripe.StripeError:
                pass
        return {"session_id": session_id, "status": transaction["status"], "payment_status": transaction["payment_status"]}

    return router


def create_stripe_webhook_router(db) -> APIRouter:
    router = APIRouter()
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    @router.post("/api/stripe/webhook")
    async def stripe_webhook(request: Request):
        payload = await request.body()
        signature = request.headers.get("stripe-signature", "")
        try:
            event = stripe.Webhook.construct_event(payload, signature, os.environ["STRIPE_WEBHOOK_SECRET"])
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc
        item = event["data"]["object"]
        event_type = event["type"]
        now = datetime.now(timezone.utc).isoformat()
        if event_type == "checkout.session.completed":
            await db.payment_transactions.update_one(
                {"session_id": item["id"], "payment_status": {"$ne": "paid"}},
                {"$set": {"status": "completed", "payment_status": item.get("payment_status", "paid"),
                          "stripe_payment_intent_id": item.get("payment_intent", ""), "updated_at": now}},
            )
        elif event_type == "checkout.session.async_payment_succeeded":
            await db.payment_transactions.update_one(
                {"session_id": item["id"]}, {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now}}
            )
        elif event_type == "checkout.session.async_payment_failed":
            await db.payment_transactions.update_one(
                {"session_id": item["id"]}, {"$set": {"status": "failed", "payment_status": "failed", "updated_at": now}}
            )
        elif event_type == "checkout.session.expired":
            await db.payment_transactions.update_one(
                {"session_id": item["id"]}, {"$set": {"status": "expired", "payment_status": "expired", "updated_at": now}}
            )
        return {"status": "ok"}

    return router