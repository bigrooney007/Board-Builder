import html
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

import resend
import stripe
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from member_auth import (
    authenticate_member, clear_member_cookie, create_member_token,
    hash_member_password, new_uuid, set_member_cookie, verify_member_password,
)
from course_content import BASIC_MODULES

TIER_ENTITLEMENTS = {"97": "recruitment_basic", "497": "recruitment_self_guided"}
TIER_PRODUCTS = {"97": "Recruitment Basic", "497": "Recruitment Self-Guided"}


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: str
    session_id: Optional[str] = ""


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    email: EmailStr
    password: str = Field(min_length=1)
    session_id: Optional[str] = ""


class ClaimRequest(BaseModel):
    session_id: str = Field(min_length=1)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    origin_url: str = Field(min_length=1)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8)
    confirm_password: str


async def claim_recruitment_purchase(db, member: dict, session_id: str) -> dict:
    """Server-side Stripe verification. Grants entitlement only when Stripe confirms payment."""
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    existing = await db.purchases.find_one({"session_id": session_id}, {"_id": 0})
    if existing and existing["user_id"] != member["user_id"]:
        raise HTTPException(status_code=409, detail="This purchase is already linked to a different account")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError as exc:
        raise HTTPException(status_code=400, detail="We could not verify this purchase with Stripe") from exc
    if session.payment_status != "paid":
        raise HTTPException(status_code=402, detail="This payment has not been completed yet")
    metadata = session.metadata or {}
    offer_source = metadata.get("offer_source", "")
    tier = metadata.get("selected_tier", "")
    if offer_source == "recruit_with_rooney" and tier == "997":
        entitlement = "recruitment_self_guided"
        product_name = "Recruit With Rooney"
    elif offer_source == "direct_diy_board_recruitment" and tier == "497":
        entitlement = "recruitment_self_guided"
        product_name = "Do It Yourself Board Recruitment"
    elif offer_source == "recruitment" and tier in TIER_ENTITLEMENTS:
        entitlement = TIER_ENTITLEMENTS[tier]
        product_name = TIER_PRODUCTS[tier]
    else:
        raise HTTPException(status_code=400, detail="This purchase is not a Recruitment program purchase")
    lead_id = metadata.get("lead_id", "")
    now = datetime.now(timezone.utc).isoformat()
    purchase = {
        "purchase_id": existing["purchase_id"] if existing else new_uuid(),
        "user_id": member["user_id"],
        "lead_id": lead_id,
        "stripe_customer_id": session.customer or "",
        "session_id": session_id,
        "payment_intent_id": session.payment_intent or "",
        "tier": tier,
        "product": product_name,
        "entitlement": entitlement,
        "amount": session.amount_total,
        "currency": session.currency,
        "payment_status": session.payment_status,
        "purchased_at": existing["purchased_at"] if existing else now,
        "updated_at": now,
    }
    if offer_source == "recruit_with_rooney":
        purchase.update({
            "purchase_source": "recruit_with_rooney_997", "offer": "Recruit With Rooney",
            "support_program": "recruit_with_rooney", "price_paid": 997,
        })
    elif offer_source == "direct_diy_board_recruitment":
        purchase.update({
            "purchase_source": "direct_diy_board_recruitment_497",
            "offer": "Do It Yourself Board Recruitment", "price_paid": 497,
        })
    await db.purchases.update_one({"session_id": session_id}, {"$set": purchase}, upsert=True)
    update = {"$addToSet": {"entitlements": entitlement}, "$set": {"updated_at": now}}
    if lead_id:
        update["$addToSet"] = {"entitlements": entitlement, "lead_ids": lead_id}
    if session.customer:
        update["$set"]["stripe_customer_id"] = session.customer
    await db.members.update_one({"user_id": member["user_id"]}, update)
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"status": "completed", "payment_status": "paid",
                  "stripe_payment_intent_id": session.payment_intent or "",
                  "claimed_by_user_id": member["user_id"], "updated_at": now}},
    )
    if lead_id:
        await db.funnel_leads.update_one(
            {"lead_id": lead_id}, {"$set": {"member_user_id": member["user_id"], "updated_at": now}}
        )
    try:
        from marketing_service import stop_recruitment_nurture
        await stop_recruitment_nurture(db, member["email"])
        lead = await db.funnel_leads.find_one({"lead_id": lead_id}, {"_id": 0, "email": 1}) if lead_id else None
        if lead and lead["email"].lower() != member["email"].lower():
            await stop_recruitment_nurture(db, lead["email"])
    except Exception:
        pass
    if purchase.get("purchase_source") == "recruit_with_rooney_997":
        try:
            from accountability_service import enroll_rooney_engagement
            await enroll_rooney_engagement(db, member, purchase)
        except Exception:
            pass
    return purchase


def public_member(member: dict) -> dict:
    return {
        "user_id": member["user_id"], "email": member["email"],
        "first_name": member["first_name"], "last_name": member["last_name"],
        "entitlements": member.get("entitlements", []),
    }


def create_member_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/members")

    @router.post("/register", status_code=201)
    async def register(payload: RegisterRequest, response: Response):
        if payload.password != payload.confirm_password:
            raise HTTPException(status_code=422, detail="Passwords do not match")
        email = str(payload.email).lower()
        if await db.members.find_one({"email": email}):
            raise HTTPException(status_code=409, detail="An account with this email already exists. Please log in instead.")
        now = datetime.now(timezone.utc).isoformat()
        member = {
            "user_id": new_uuid(), "email": email,
            "first_name": payload.first_name, "last_name": payload.last_name,
            "password_hash": hash_member_password(payload.password),
            "entitlements": [], "lead_ids": [], "stripe_customer_id": "",
            "created_at": now, "updated_at": now,
        }
        await db.members.insert_one(member.copy())
        purchase = None
        if payload.session_id:
            purchase = await claim_recruitment_purchase(db, member, payload.session_id)
        fresh = await db.members.find_one({"user_id": member["user_id"]}, {"_id": 0, "password_hash": 0})
        token = create_member_token(member["user_id"], email)
        set_member_cookie(response, token)
        return {"member": public_member(fresh), "token": token,
                "claimed": purchase["entitlement"] if purchase else "",
                "claimed_source": purchase.get("purchase_source", "") if purchase else ""}

    @router.post("/login")
    async def login(payload: LoginRequest, response: Response):
        email = str(payload.email).lower()
        member = await db.members.find_one({"email": email})
        if not member or not verify_member_password(payload.password, member["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        purchase = None
        if payload.session_id:
            purchase = await claim_recruitment_purchase(db, member, payload.session_id)
        fresh = await db.members.find_one({"user_id": member["user_id"]}, {"_id": 0, "password_hash": 0})
        token = create_member_token(member["user_id"], email)
        set_member_cookie(response, token)
        return {"member": public_member(fresh), "token": token,
                "claimed": purchase["entitlement"] if purchase else "",
                "claimed_source": purchase.get("purchase_source", "") if purchase else ""}

    @router.post("/logout")
    async def logout(response: Response):
        clear_member_cookie(response)
        return {"status": "logged_out"}

    @router.get("/me")
    async def me(request: Request):
        member = await authenticate_member(request, db)
        return {"member": public_member(member)}

    @router.post("/claim-purchase")
    async def claim(payload: ClaimRequest, request: Request):
        member = await authenticate_member(request, db)
        purchase = await claim_recruitment_purchase(db, member, payload.session_id)
        fresh = await db.members.find_one({"user_id": member["user_id"]}, {"_id": 0, "password_hash": 0})
        return {"member": public_member(fresh), "claimed": purchase["entitlement"],
                "claimed_source": purchase.get("purchase_source", "")}

    @router.get("/dashboard")
    async def dashboard(request: Request):
        member = await authenticate_member(request, db)
        entitlements = member.get("entitlements", [])
        products = []
        for entitlement, name, route in [
            ("recruitment_basic", "Board Recruitment — Basic", "/app/recruitment/basic"),
            ("recruitment_self_guided", "Board Recruitment — Self-Guided System", "/app/recruitment/self-guided"),
        ]:
            if entitlement not in entitlements:
                continue
            records = await db.course_progress.find(
                {"user_id": member["user_id"], "product": entitlement}, {"_id": 0}
            ).to_list(50)
            completed = sum(1 for record in records if record.get("completed"))
            last_visit = max(records, key=lambda record: record.get("last_visited_at", ""), default=None)
            last_module = None
            if last_visit:
                number = last_visit["module_number"]
                title = next((module["title"] for module in BASIC_MODULES if module["number"] == number), "")
                last_module = {"number": number, "title": title}
            products.append({
                "entitlement": entitlement, "name": name, "route": route,
                "modules_total": 6, "modules_completed": completed,
                "percent_complete": round(completed / 6 * 100),
                "last_module": last_module,
            })
        return {"member": public_member(member), "products": products}

    @router.post("/forgot-password")
    async def forgot_password(payload: ForgotPasswordRequest):
        parsed = urlparse(payload.origin_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid application origin")
        email = str(payload.email).lower()
        member = await db.members.find_one({"email": email})
        generic = {"status": "ok", "message": "If an account exists for this email, a reset link has been sent."}
        if not member:
            return generic
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        await db.password_resets.insert_one({
            "token": token, "user_id": member["user_id"], "email": email,
            "expires_at": (now + timedelta(hours=2)).isoformat(),
            "used": False, "created_at": now.isoformat(),
        })
        reset_link = f"{payload.origin_url.rstrip('/')}/reset-password/{token}"
        try:
            resend.api_key = os.environ["RESEND_API_KEY"]
            await resend.Emails.send_async({
                "from": os.environ["NONPROFIT_SENDER"], "to": [email],
                "subject": "Reset Your Board Builder Password",
                "html": f"<div style='max-width:560px;margin:auto;font-family:Arial,sans-serif;color:#000;'><h2>Reset Your Board Builder Password</h2><p>Hello {html.escape(member['first_name'])},</p><p>We received a request to reset your Nonprofit Board Builder password. Click the link below to choose a new password. This link expires in 2 hours.</p><p><a href='{reset_link}'>Reset my password</a></p><p>If you did not request this, you can safely ignore this email.</p></div>",
            })
        except Exception:
            pass
        return generic

    @router.post("/reset-password")
    async def reset_password(payload: ResetPasswordRequest):
        if payload.password != payload.confirm_password:
            raise HTTPException(status_code=422, detail="Passwords do not match")
        record = await db.password_resets.find_one({"token": payload.token}, {"_id": 0})
        if not record or record.get("used"):
            raise HTTPException(status_code=400, detail="This reset link is invalid or has already been used")
        if record["expires_at"] < datetime.now(timezone.utc).isoformat():
            raise HTTPException(status_code=400, detail="This reset link has expired. Please request a new one.")
        now = datetime.now(timezone.utc).isoformat()
        await db.members.update_one(
            {"user_id": record["user_id"]},
            {"$set": {"password_hash": hash_member_password(payload.password), "updated_at": now}},
        )
        await db.password_resets.update_one({"token": payload.token}, {"$set": {"used": True, "used_at": now}})
        return {"status": "ok", "message": "Your password has been reset. You can now log in."}

    return router
