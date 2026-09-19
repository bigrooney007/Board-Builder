import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth_service import authenticate_admin
from checkout_recovery import lead_checkout_context
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
    result_token: str = ""
    cancel_path: str = ""


class DIYCheckoutRequest(BaseModel):
    origin_url: str = Field(min_length=1)
    result_token: str = ""
    cancel_path: str = ""
    product: str = ""


ALLOWED_CANCEL_PATHS = {"/offer/recruitment", "/offer/reactivation", "/offer/activation", "/offer/board-fix", "/offer/fundraising-board-builder", "/board-recruitment", "/board-fundraising-activation", "/game/start", "/", "/strategic-planning/video", "/board-recommitment/video"}


def resolve_cancel_url(payload, default_path: str) -> str:
    path = payload.cancel_path if payload.cancel_path in ALLOWED_CANCEL_PATHS else default_path
    return f"{payload.origin_url}{path}?checkout=cancelled"


_price_cache = {}


def resolve_offer_price_id(env_key: str, lookup_key: str, product_name: str, unit_amount: int) -> str:
    if _price_cache.get(lookup_key):
        return _price_cache[lookup_key]
    configured = os.environ.get(env_key, "").strip().strip('"')
    if configured:
        try:
            price = stripe.Price.retrieve(configured)
            if price.active and price.unit_amount == unit_amount and price.currency == "usd" and not price.recurring:
                _price_cache[lookup_key] = configured
                return configured
        except stripe.StripeError:
            pass
    existing = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1).data
    if existing:
        _price_cache[lookup_key] = existing[0].id
        return _price_cache[lookup_key]
    product = stripe.Product.create(
        name=product_name, tax_code="txcd_10000000",
        metadata={"managed_by": "emergent", "emergent_product_id": lookup_key},
    )
    price = stripe.Price.create(
        product=product.id, unit_amount=unit_amount, currency="usd",
        lookup_key=lookup_key, transfer_lookup_key=True,
    )
    _price_cache[lookup_key] = price.id
    return _price_cache[lookup_key]


def resolve_diy_price_id() -> str:
    return resolve_offer_price_id("STRIPE_RECRUITMENT_CAMPAIGN_DIY_297_PRICE_ID", "recruitment_campaign_diy_297", "Board Recruitment Campaign Launch — Do It Yourself", 29700)


def resolve_direct_project_price_id() -> str:
    return resolve_offer_price_id("STRIPE_DIRECT_BOARD_RECRUITMENT_1997_PRICE_ID", "direct_board_recruitment_project_1997", "Recruit My Board With Rooney", 199700)


def resolve_board_fix_price_id() -> str:
    return resolve_offer_price_id("STRIPE_BOARD_FIX_SYSTEM_497_PRICE_ID", "board_fix_system_497", "Complete Board Fix System", 49700)


def resolve_board_fix_dwm_price_id() -> str:
    return resolve_offer_price_id("STRIPE_BOARD_FIX_DWM_5997_PRICE_ID", "board_fix_dwm_5997", "Complete Board Transformation — Done With You", 599700)


def resolve_selection_onboarding_price_id() -> str:
    return resolve_offer_price_id("STRIPE_RECRUITMENT_SELECTION_ONBOARDING_297_PRICE_ID", "recruitment_selection_onboarding_297", "Selection, Interview, Reference Check & Onboarding", 29700)


def resolve_reactivation_diy_price_id() -> str:
    return resolve_offer_price_id("STRIPE_DIY_BOARD_REACTIVATION_497_PRICE_ID", "diy_board_reactivation_497", "Reactivate Your Board Yourself", 49700)


def resolve_reactivation_project_price_id() -> str:
    return resolve_offer_price_id("STRIPE_DIRECT_BOARD_REACTIVATION_5497_PRICE_ID", "direct_board_reactivation_project_5497", "Board Reactivation Project", 549700)


def resolve_activation_diy_price_id() -> str:
    return resolve_offer_price_id("STRIPE_DIY_BOARD_ACTIVATION_497_PRICE_ID", "diy_board_activation_497", "Activate Your Board Yourself", 49700)


def resolve_fundraising_board_builder_price_id() -> str:
    return resolve_offer_price_id("STRIPE_FUNDRAISING_BOARD_BUILDER_497_PRICE_ID", "fundraising_board_builder_497", "Fundraising Board Builder", 49700)


def resolve_fbb_recruitment_price_id() -> str:
    return resolve_offer_price_id("STRIPE_FBB_RECRUITMENT_497_PRICE_ID", "board_recruitment_497", "Board Recruitment", 49700)


def resolve_fbb_activation_price_id() -> str:
    return resolve_offer_price_id("STRIPE_FBB_ACTIVATION_497_PRICE_ID", "board_fundraising_activation_497", "Board Fundraising Activation", 49700)


def resolve_activate_with_rooney_price_id() -> str:
    return resolve_offer_price_id("STRIPE_ACTIVATE_MY_BOARD_WITH_ROONEY_2997_PRICE_ID", "activate_my_board_with_rooney_2997", "Activate My Board With Rooney", 299700)


def resolve_activation_project_price_id() -> str:
    return resolve_offer_price_id("STRIPE_DIRECT_BOARD_ACTIVATION_5497_PRICE_ID", "direct_board_activation_project_5497", "Board Fundraising Activation Project", 549700)


def resolve_complete_transformation_price_id() -> str:
    return resolve_offer_price_id("STRIPE_COMPLETE_TRANSFORMATION_1997_PRICE_ID", "complete_board_transformation_1997", "Complete Board Transformation", 199700)


def resolve_campaign_launch_price_id() -> str:
    return resolve_offer_price_id("STRIPE_RECRUITMENT_CAMPAIGN_LAUNCH_697_PRICE_ID", "recruitment_campaign_launch_697", "Recruitment Campaign Launch", 69700)


def resolve_game_price_id() -> str:
    return resolve_offer_price_id("STRIPE_BOARD_FUNDRAISING_GAME_497_PRICE_ID", "board_fundraising_game_497", "Board Fundraising Game", 49700)


DFY_CHECKOUT_OFFERS = {
    "reactivation": {
        "env_key": "STRIPE_BOARD_REACTIVATION_DFY_2997_PRICE_ID", "lookup_key": "board_reactivation_dfy_2997",
        "product_name": "Board Reactivation", "amount": 299700,
        "purchase_source": "board_reactivation_dfy", "offer": "Board Reactivation",
        "intake_path": "/board-reactivation-intake",
    },
    "recruitment": {
        "env_key": "STRIPE_BOARD_RECRUITMENT_DFY_3997_PRICE_ID", "lookup_key": "board_recruitment_dfy_3997",
        "product_name": "Board Recruitment", "amount": 399700,
        "purchase_source": "board_recruitment_dfy", "offer": "Board Recruitment",
        "intake_path": "/board-recruitment-intake",
    },
    "activation": {
        "env_key": "STRIPE_BOARD_ACTIVATION_DFY_4997_PRICE_ID", "lookup_key": "board_fundraising_activation_dfy_4997",
        "product_name": "Board Fundraising Activation", "amount": 499700,
        "purchase_source": "board_fundraising_activation_dfy", "offer": "Board Fundraising Activation",
        "intake_path": "/board-activation-intake",
    },
}


class DFYCheckoutRequest(BaseModel):
    origin_url: str = Field(min_length=1)
    result_token: str = ""
    pathway: str = Field(min_length=1)


def create_payment_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/payments")
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    @router.get("/flow-status/{session_id}")
    async def flow_status(session_id: str, flow: str):
        contracts = {
            "recruitment": {"offer_sources": {"recruitment"}, "purchase_sources": {"recruitment_497", "recruitment_self_guided_497"}},
            "board-fundraising-game": {"offer_sources": {"board_fundraising_game"}, "purchase_sources": {"board_fundraising_game_497"}},
            "strategic-planning": {"offer_sources": {"strategic_planning"}, "purchase_sources": {"strategic_planning_497"}},
            "board-recommitment": {"offer_sources": {"board_recommitment"}, "purchase_sources": {"board_recommitment_497"}},
        }
        contract = contracts.get(flow)
        if not contract:
            raise HTTPException(status_code=400, detail="Unknown product flow")
        tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if not tx:
            raise HTTPException(status_code=404, detail="Payment session not found")
        if tx.get("payment_status") != "paid":
            try:
                stripe_session = stripe.checkout.Session.retrieve(session_id)
                if stripe_session.payment_status == "paid":
                    now = datetime.now(timezone.utc).isoformat()
                    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now}})
                    tx["status"] = "completed"; tx["payment_status"] = "paid"
            except stripe.StripeError:
                pass
        source_ok = tx.get("offer_source", "") in contract["offer_sources"] or tx.get("purchase_source", "") in contract["purchase_sources"]
        if not source_ok:
            raise HTTPException(status_code=409, detail="This payment belongs to a different product flow")
        return {"flow": flow, "payment_status": tx.get("payment_status", "pending"), "valid_flow": True}

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
            # The four-question recruitment journey is the live $497 sales flow.
            paid_live = payload.tier == "497" or os.environ.get("RECRUITMENT_97_LIVE", "false").lower() == "true"
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
        if lead.get("lead_source") == "recruitment_free_assessment":
            option_path = "/recruit/walkthrough"
        if lead["offer_source"] == "recruitment":
            success_url = f"{payload.origin_url}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}"
        else:
            success_url = f"{payload.origin_url}{option_path}?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
        if lead["offer_source"] == "recruitment" and payload.tier == "497":
            price_id = resolve_offer_price_id(
                price_env, "recruitment_self_guided_497", "Recruitment Self-Guided", 49700)
        else:
            price_id = os.environ[price_env]
        kwargs = {
            "line_items": [{"price": price_id, "quantity": 1}], "mode": "payment",
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
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live", "created_at": now, "updated_at": now,
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
            "line_items": [{"price": resolve_direct_project_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/board-recruitment-intake?session_id={{CHECKOUT_SESSION_ID}}&dfy=1",
            "cancel_url": resolve_cancel_url(payload, "/board-recruitment"),
            "metadata": {
                "offer_source": "direct_board_recruitment_project",
                "purchase_source": "direct_board_recruitment_project",
                "offer": "Recruit My Board With Rooney",
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
            "session_id": session.id, **(await lead_checkout_context(db, payload.result_token)), "origin_url": payload.origin_url, "offer_source": "direct_board_recruitment_project",
            "selected_tier": "direct_project", "purchase_source": "direct_board_recruitment_project",
            "offer": "Recruit My Board With Rooney",
            "amount": 199700, "currency": "usd", "status": "initiated", "payment_status": "pending",
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
            "line_items": [{"price": resolve_diy_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": resolve_cancel_url(payload, "/recruit-your-board-yourself"),
            "metadata": {
                "offer_source": "direct_diy_board_recruitment", "selected_tier": "297",
                "purchase_source": "recruitment_campaign_diy_297",
                "offer": "Board Recruitment Campaign Launch — Do It Yourself",
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
            "session_id": session.id, **(await lead_checkout_context(db, payload.result_token)), "origin_url": payload.origin_url, "offer_source": "direct_diy_board_recruitment",
            "selected_tier": "297", "purchase_source": "recruitment_campaign_diy_297",
            "offer": "Board Recruitment Campaign Launch — Do It Yourself",
            "amount": 29700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/board-fix-checkout")
    async def create_board_fix_checkout(payload: DIYCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": resolve_board_fix_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": resolve_cancel_url(payload, "/offer/board-fix"),
            "metadata": {
                "offer_source": "board_fix_system", "selected_tier": "497",
                "purchase_source": "board_fix_system_497",
                "offer": "Complete Board Fix System",
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
            "session_id": session.id, **(await lead_checkout_context(db, payload.result_token)), "origin_url": payload.origin_url, "offer_source": "board_fix_system",
            "selected_tier": "497", "purchase_source": "board_fix_system_497",
            "offer": "Complete Board Fix System",
            "amount": 49700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/board-fix-dwm-checkout")
    async def create_board_fix_dwm_checkout(payload: DIYCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": resolve_board_fix_dwm_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": resolve_cancel_url(payload, "/offer/board-fix"),
            "metadata": {
                "offer_source": "board_fix_system", "selected_tier": "dwm_5997",
                "purchase_source": "board_fix_dwm_5497",
                "offer": "Complete Board Fix — Do It With Me",
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
            "session_id": session.id, **(await lead_checkout_context(db, payload.result_token)), "origin_url": payload.origin_url, "offer_source": "board_fix_system",
            "selected_tier": "dwm_5997", "purchase_source": "board_fix_dwm_5497",
            "offer": "Complete Board Fix — Do It With Me",
            "amount": 599700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/selection-onboarding-checkout")
    async def create_selection_onboarding_checkout(payload: DIYCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": resolve_selection_onboarding_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{payload.origin_url}/app/recruitment/selection-offer?checkout=cancelled",
            "metadata": {
                "offer_source": "recruitment_selection_onboarding", "selected_tier": "297",
                "purchase_source": "recruitment_selection_onboarding_297",
                "offer": "Selection, Interview, Reference Check & Onboarding",
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
            "session_id": session.id, "origin_url": payload.origin_url, "offer_source": "recruitment_selection_onboarding",
            "selected_tier": "297", "purchase_source": "recruitment_selection_onboarding_297",
            "offer": "Selection, Interview, Reference Check & Onboarding",
            "amount": 29700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/reactivation-diy-checkout")
    async def create_reactivation_diy_checkout(payload: DIYCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": resolve_reactivation_diy_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": resolve_cancel_url(payload, "/reactivate-your-board-yourself"),
            "metadata": {
                "offer_source": "direct_diy_board_reactivation", "selected_tier": "497",
                "purchase_source": "direct_diy_board_reactivation_497",
                "offer": "Do It Yourself Board Reactivation",
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
            "session_id": session.id, **(await lead_checkout_context(db, payload.result_token)), "origin_url": payload.origin_url, "offer_source": "direct_diy_board_reactivation",
            "selected_tier": "497", "purchase_source": "direct_diy_board_reactivation_497",
            "offer": "Do It Yourself Board Reactivation",
            "amount": 49700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/reactivation-project-checkout")
    async def create_reactivation_project_checkout(payload: DirectProjectCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": resolve_reactivation_project_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/board-reactivation-intake?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": resolve_cancel_url(payload, "/board-reactivation-proposal"),
            "metadata": {
                "offer_source": "direct_board_reactivation_project",
                "purchase_source": "direct_board_reactivation_project",
                "offer": "Board Reactivation Project",
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
            "session_id": session.id, **(await lead_checkout_context(db, payload.result_token)), "origin_url": payload.origin_url, "offer_source": "direct_board_reactivation_project",
            "selected_tier": "direct_project", "purchase_source": "direct_board_reactivation_project",
            "offer": "Board Reactivation Project",
            "amount": 549700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    FBB_PRODUCTS = {
        "recruitment": {
            "price": resolve_fbb_recruitment_price_id, "offer_source": "fbb_recruitment",
            "purchase_source": "board_recruitment_497", "offer": "Board Recruitment",
            "cancel_default": "/board-recruitment",
        },
        "activation": {
            "price": resolve_fbb_activation_price_id, "offer_source": "fbb_activation",
            "purchase_source": "board_fundraising_activation_497", "offer": "Board Fundraising Activation",
            "cancel_default": "/board-fundraising-activation",
        },
    }

    @router.post("/fundraising-board-builder-checkout")
    async def create_fundraising_board_builder_checkout(payload: DIYCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        spec = FBB_PRODUCTS.get(payload.product, {
            "price": resolve_fundraising_board_builder_price_id, "offer_source": "fundraising_board_builder",
            "purchase_source": "fundraising_board_builder_497", "offer": "Fundraising Board Builder",
            "cancel_default": "/offer/fundraising-board-builder",
        })
        kwargs = {
            "line_items": [{"price": spec["price"](), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/welcome?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": resolve_cancel_url(payload, spec["cancel_default"]),
            "metadata": {
                "offer_source": spec["offer_source"], "selected_tier": "497",
                "purchase_source": spec["purchase_source"],
                "offer": spec["offer"],
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
            "session_id": session.id, **(await lead_checkout_context(db, payload.result_token)), "origin_url": payload.origin_url, "offer_source": spec["offer_source"],
            "selected_tier": "497", "purchase_source": spec["purchase_source"],
            "offer": spec["offer"],
            "amount": 49700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/guided-checkout")
    async def create_guided_checkout(payload: DIYCheckoutRequest):
        product = payload.product
        config = {
            "strategic-planning": ("Strategic Planning With Your Board", "strategic_planning_497", "/strategic-planning"),
            "board-recommitment": ("Board Recommitment", "board_recommitment_497", "/board-recommitment"),
        }.get(product)
        if not config:
            raise HTTPException(status_code=400, detail="Unknown guided product")
        product_name, purchase_source, base_path = config
        lead = await db.guided_product_leads.find_one({"token": payload.result_token}, {"_id": 0})
        if not lead or lead.get("product") != product:
            raise HTTPException(status_code=409, detail="This journey token belongs to a different product flow")
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price_data": {"currency": "usd", "unit_amount": 49700, "product_data": {"name": product_name}}, "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}{base_path}/payment-confirmed?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{payload.origin_url}{base_path}/video?token={payload.result_token}&checkout=cancelled",
            "metadata": {"offer_source": product.replace("-", "_"), "selected_tier": "497", "purchase_source": purchase_source, "offer": product_name, "guided_lead_token": payload.result_token},
        }
        try:
            session = stripe.checkout.Session.create(**kwargs, managed_payments={"enabled": True})
        except stripe.InvalidRequestError as exc:
            message = (getattr(exc, "user_message", "") or str(exc)).lower()
            if "managed payments" not in message and "ineligible" not in message:
                raise
            session = stripe.checkout.Session.create(**kwargs, automatic_tax={"enabled": True}, billing_address_collection="required")
        now = datetime.now(timezone.utc).isoformat()
        await db.payment_transactions.insert_one({
            "session_id": session.id, "origin_url": payload.origin_url, "offer_source": product.replace("-", "_"),
            "selected_tier": "497", "purchase_source": purchase_source, "offer": product_name, "guided_lead_token": payload.result_token,
            "amount": 49700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live", "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/game-checkout")
    async def create_game_checkout(payload: DIYCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": resolve_game_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/game/welcome?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": resolve_cancel_url(payload, "/game/start"),
            "metadata": {
                "offer_source": "board_fundraising_game", "selected_tier": "497",
                "purchase_source": "board_fundraising_game_497",
                "offer": "Board Fundraising Game",
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
            "session_id": session.id, "origin_url": payload.origin_url, "offer_source": "board_fundraising_game",
            "selected_tier": "497", "purchase_source": "board_fundraising_game_497",
            "offer": "Board Fundraising Game",
            "amount": 49700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/facilitated-game-checkout")
    async def create_facilitated_game_checkout(payload: DIYCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price_data": {
                "currency": "usd", "unit_amount": 349700,
                "product_data": {"name": "Facilitated Board Fundraising Game"}}, "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/board-activation-intake?facilitated=1&session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": resolve_cancel_url(payload, "/organize-board-fundraising-game"),
            "metadata": {
                "offer_source": "facilitated_board_fundraising_game", "selected_tier": "3497",
                "purchase_source": "facilitated_board_fundraising_game_3497",
                "offer": "Facilitated Board Fundraising Game",
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
            "session_id": session.id, "origin_url": payload.origin_url, "offer_source": "facilitated_board_fundraising_game",
            "selected_tier": "3497", "purchase_source": "facilitated_board_fundraising_game_3497",
            "offer": "Facilitated Board Fundraising Game",
            "amount": 349700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/activation-diy-checkout")
    async def create_activation_diy_checkout(payload: DIYCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": resolve_activation_diy_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": resolve_cancel_url(payload, "/activate-your-board-yourself"),
            "metadata": {
                "offer_source": "direct_diy_board_activation", "selected_tier": "497",
                "purchase_source": "direct_diy_board_activation_497",
                "offer": "Do It Yourself Board Fundraising Activation",
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
            "session_id": session.id, **(await lead_checkout_context(db, payload.result_token)), "origin_url": payload.origin_url, "offer_source": "direct_diy_board_activation",
            "selected_tier": "497", "purchase_source": "direct_diy_board_activation_497",
            "offer": "Do It Yourself Board Fundraising Activation",
            "amount": 49700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/activation-project-checkout")
    async def create_activation_project_checkout(payload: DirectProjectCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": resolve_activation_project_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/board-activation-intake?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": resolve_cancel_url(payload, "/board-activation-proposal"),
            "metadata": {
                "offer_source": "direct_board_activation_project",
                "purchase_source": "direct_board_activation_project_2497",
                "offer": "Board Fundraising Activation Project",
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
            "session_id": session.id, **(await lead_checkout_context(db, payload.result_token)), "origin_url": payload.origin_url, "offer_source": "direct_board_activation_project",
            "selected_tier": "direct_project", "purchase_source": "direct_board_activation_project_2497",
            "offer": "Board Fundraising Activation Project",
            "amount": 549700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/activate-rooney-checkout")
    async def create_activate_rooney_checkout(payload: DIYCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": resolve_activate_with_rooney_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": resolve_cancel_url(payload, "/board-fundraising-activation"),
            "metadata": {
                "offer_source": "activate_my_board_with_rooney_2997",
                "purchase_source": "activate_my_board_with_rooney_2997",
                "offer": "Activate My Board With Rooney",
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
            "session_id": session.id, **(await lead_checkout_context(db, payload.result_token)), "origin_url": payload.origin_url,
            "offer_source": "activate_my_board_with_rooney_2997",
            "selected_tier": "direct_project", "purchase_source": "activate_my_board_with_rooney_2997",
            "offer": "Activate My Board With Rooney",
            "amount": 299700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/dfy-checkout")
    async def create_dfy_checkout(payload: DFYCheckoutRequest):
        meta = DFY_CHECKOUT_OFFERS.get(payload.pathway)
        if not meta:
            raise HTTPException(status_code=400, detail="Unknown engagement")
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": resolve_offer_price_id(meta["env_key"], meta["lookup_key"], meta["product_name"], meta["amount"]), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}{meta['intake_path']}?session_id={{CHECKOUT_SESSION_ID}}&dfy=1",
            "cancel_url": f"{payload.origin_url}/offer/board-fix?checkout=cancelled",
            "metadata": {
                "offer_source": meta["purchase_source"],
                "purchase_source": meta["purchase_source"],
                "offer": meta["offer"],
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
        lead_context = await lead_checkout_context(db, payload.result_token)
        lead = await db.funnel_leads.find_one({"result_token": payload.result_token}, {"_id": 0, "diagnostic_answers": 1, "recommended_pathway": 1}) if payload.result_token else None
        await db.payment_transactions.insert_one({
            "session_id": session.id, **lead_context, "origin_url": payload.origin_url,
            "offer_source": meta["purchase_source"],
            "selected_tier": "dfy_997", "purchase_source": meta["purchase_source"],
            "offer": meta["offer"],
            "diagnostic_answers": (lead or {}).get("diagnostic_answers", {}),
            "recommended_pathway": (lead or {}).get("recommended_pathway", ""),
            "amount": meta["amount"], "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/campaign-launch-checkout")
    async def create_campaign_launch_checkout(payload: DIYCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": resolve_campaign_launch_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/board-recruitment-intake?session_id={{CHECKOUT_SESSION_ID}}&dfy=1",
            "cancel_url": f"{payload.origin_url}/offer/recruitment?checkout=cancelled",
            "metadata": {
                "offer_source": "recruitment_campaign_launch", "selected_tier": "697",
                "purchase_source": "recruitment_campaign_launch_697",
                "offer": "Recruitment Campaign Launch",
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
            "session_id": session.id, **(await lead_checkout_context(db, payload.result_token)), "origin_url": payload.origin_url,
            "offer_source": "recruitment_campaign_launch",
            "selected_tier": "697", "purchase_source": "recruitment_campaign_launch_697",
            "offer": "Recruitment Campaign Launch",
            "amount": 69700, "currency": "usd", "status": "initiated", "payment_status": "pending",
            "test_mode": os.environ.get("STRIPE_MODE", "test") != "live",
            "created_at": now, "updated_at": now,
        })
        return {"checkout_url": session.url, "session_id": session.id}

    @router.post("/complete-transformation-checkout")
    async def create_complete_transformation_checkout(payload: DIYCheckoutRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        kwargs = {
            "line_items": [{"price": resolve_complete_transformation_price_id(), "quantity": 1}],
            "mode": "payment",
            "success_url": f"{payload.origin_url}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": resolve_cancel_url(payload, "/offer/board-fix"),
            "metadata": {
                "offer_source": "board_fix_system", "selected_tier": "complete_1997",
                "purchase_source": "complete_board_transformation_1997",
                "offer": "Complete Board Transformation",
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
        lead = await db.funnel_leads.find_one({"result_token": payload.result_token}, {"_id": 0, "diagnostic_answers": 1, "recommended_pathway": 1}) if payload.result_token else None
        await db.payment_transactions.insert_one({
            "session_id": session.id, **(await lead_checkout_context(db, payload.result_token)), "origin_url": payload.origin_url, "offer_source": "board_fix_system",
            "selected_tier": "complete_1997", "purchase_source": "complete_board_transformation_1997",
            "offer": "Complete Board Transformation",
            "diagnostic_answers": (lead or {}).get("diagnostic_answers", {}),
            "recommended_pathway": (lead or {}).get("recommended_pathway", ""),
            "amount": 199700, "currency": "usd", "status": "initiated", "payment_status": "pending",
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
                    try:
                        from marketing_service import stop_recruitment_nurture_for_purchase
                        buyer_email = (session.customer_details.email if session.customer_details else "") or ""
                        await stop_recruitment_nurture_for_purchase(db, transaction, buyer_email)
                    except Exception:
                        pass
            except stripe.StripeError:
                pass
        return {"session_id": session_id, "status": transaction["status"], "payment_status": transaction["payment_status"]}

    return router


def create_stripe_webhook_router(db) -> APIRouter:
    router = APIRouter()
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    async def _stop_nurture_after_paid(item: dict) -> None:
        try:
            from marketing_service import stop_recruitment_nurture_for_purchase
            transaction = await db.payment_transactions.find_one({"session_id": item["id"]}, {"_id": 0})
            buyer_email = ((item.get("customer_details") or {}).get("email") or "")
            await stop_recruitment_nurture_for_purchase(db, transaction, buyer_email)
        except Exception:
            pass

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
            if item.get("payment_status", "paid") == "paid":
                await _stop_nurture_after_paid(item)
        elif event_type == "checkout.session.async_payment_succeeded":
            await db.payment_transactions.update_one(
                {"session_id": item["id"]}, {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now}}
            )
            await _stop_nurture_after_paid(item)
        elif event_type == "checkout.session.async_payment_failed":
            await db.payment_transactions.update_one(
                {"session_id": item["id"], "payment_status": {"$ne": "paid"}},
                {"$set": {"status": "failed", "payment_status": "failed", "updated_at": now}}
            )
        elif event_type == "checkout.session.expired":
            await db.payment_transactions.update_one(
                {"session_id": item["id"], "payment_status": {"$ne": "paid"}},
                {"$set": {"status": "expired", "payment_status": "expired", "updated_at": now}}
            )
        return {"status": "ok"}

    return router
