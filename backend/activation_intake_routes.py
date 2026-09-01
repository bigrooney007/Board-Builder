import html
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List

import resend
import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from board_fix_master import BOARD_FIX_SOURCE, board_fix_member, get_master_record, master_prefill, synthetic_session, write_back_master

logger = logging.getLogger(__name__)

CALENDLY_URL = "https://calendly.com/boardbuilder/recruitboard"
DIY_START_ROUTE = "/activation-start-here"
BOARD_FIX_COURSE_ROUTE = "/app/activation/self-guided"
QUALIFYING_SOURCES = {"direct_diy_board_activation_497", "direct_board_activation_project_2497", "board_fundraising_activation_dfy"}
OFFER_LABELS = {
    "direct_diy_board_activation_497": "Fundraising Activation — Do It Yourself — $497",
    "direct_board_activation_project_2497": "Fundraising Activation — Do It With Rooney — $2,497",
    "board_fundraising_activation_dfy": "Board Fundraising Activation — Done For You — $997",
    BOARD_FIX_SOURCE: "Complete Board Fix System — $497",
}

INVOLVEMENT_OPTIONS = {
    "Most Board Members actively participate", "Some Board Members participate",
    "Very little Board participation", "No meaningful Board fundraising participation", "Not Sure",
}
STATUS_YPN = {"Yes", "Partially", "No"}
STATUS_YPNN = {"Yes", "Partially", "No", "Not Sure"}


class ActivationIntakeSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")
    session_id: str = ""
    your_name: str = Field(min_length=1)
    email: EmailStr
    organization_name: str = Field(min_length=1)
    fundraising_goal: str = Field(min_length=1)
    amount_needed: str = Field(min_length=1)
    money_accomplish: str = Field(min_length=1)
    current_methods: List[str] = Field(min_length=1)
    current_methods_other: str = ""
    written_strategy: str = Field(min_length=1)
    fundraising_calendar: str = Field(min_length=1)
    fundraising_carriers: List[str] = Field(min_length=1)
    fundraising_carriers_detail: str = ""
    present_board: str = Field(min_length=1)
    active_board: str = Field(min_length=1)
    board_fundraising_involvement: str = Field(min_length=1)
    board_fundraising_activities: List[str] = Field(min_length=1)
    board_fundraising_activities_other: str = ""
    perceived_barriers: str = Field(min_length=1)
    board_skills_relationships: str = Field(min_length=1)
    direction_12_24: str = Field(min_length=1)
    organization_priorities: str = Field(min_length=1)
    previous_fundraising_planning: str = Field(min_length=1)
    broader_strategic_planning: str = Field(min_length=1)
    desired_change: str = Field(min_length=1)
    success_definition: str = Field(min_length=1)
    anything_else: str = ""
    money_needed_by: str = ""
    present_donors: str = ""
    present_business_sponsors: str = ""
    present_corporate_relationships: str = ""
    present_grantors: str = ""
    other_funding_relationships: str = ""
    individuals_type: str = ""
    individuals_approach: str = ""
    businesses_type: str = ""
    businesses_approach: str = ""
    grantors_type: str = ""
    grantors_approach: str = ""

    @field_validator("written_strategy")
    @classmethod
    def valid_written_strategy(cls, value: str) -> str:
        if value not in STATUS_YPN:
            raise ValueError("Written strategy answer must be Yes, Partially or No")
        return value

    @field_validator("fundraising_calendar", "previous_fundraising_planning", "broader_strategic_planning")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in STATUS_YPNN:
            raise ValueError("Answer must be Yes, Partially, No or Not Sure")
        return value

    @field_validator("board_fundraising_involvement")
    @classmethod
    def valid_involvement(cls, value: str) -> str:
        if value not in INVOLVEMENT_OPTIONS:
            raise ValueError("Unknown board fundraising involvement answer")
        return value


def validate_board_counts(present: str, active: str) -> None:
    try:
        total = int(present)
        active_count = int(active)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Board counts must be whole numbers") from exc
    if total < 0 or active_count < 0 or active_count > total:
        raise HTTPException(status_code=422, detail="Active Board Members cannot exceed total Board Members")


def create_activation_intake_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/board-activation-intake")
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    async def verified_transaction(session_id: str) -> dict:
        transaction = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if not transaction or transaction.get("purchase_source") not in QUALIFYING_SOURCES:
            raise HTTPException(status_code=404, detail="No qualifying purchase was found for this form")
        if transaction["payment_status"] != "paid":
            try:
                session = stripe.checkout.Session.retrieve(session_id)
            except stripe.StripeError as exc:
                raise HTTPException(status_code=402, detail="This payment has not been completed yet") from exc
            if session.payment_status == "paid" or session.status == "complete":
                now = datetime.now(timezone.utc).isoformat()
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now}},
                )
                transaction["payment_status"] = "paid"
            else:
                raise HTTPException(status_code=402, detail="This payment has not been completed yet")
        return transaction

    async def linked_user_id(session_id: str, transaction: dict) -> str:
        purchase = await db.purchases.find_one({"session_id": session_id}, {"_id": 0, "user_id": 1})
        if purchase:
            return purchase["user_id"]
        return transaction.get("claimed_by_user_id", "") or ""

    @router.get("/context")
    async def intake_context(request: Request, session_id: str = ""):
        if session_id:
            transaction = await verified_transaction(session_id)
            user_id = await linked_user_id(session_id, transaction)
            purchase_source = transaction["purchase_source"]
            existing = await db.board_activation_intakes.find_one({"session_id": session_id}, {"_id": 0, "submitted_at": 1})
        else:
            member = await board_fix_member(request, db, "activation_self_guided")
            user_id = member["user_id"]
            purchase_source = BOARD_FIX_SOURCE
            existing = await db.board_activation_intakes.find_one(
                {"$or": [{"session_id": synthetic_session(user_id)}, {"user_id": user_id}]}, {"_id": 0, "submitted_at": 1})
        prefill = {"name": "", "email": ""}
        organization_prefill = {}
        if user_id:
            member = await db.members.find_one({"user_id": user_id}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1})
            if member:
                prefill = {"name": f"{member['first_name']} {member['last_name']}".strip(), "email": member["email"]}
            profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data": 1}) or {}
            data = profile.get("data", {}) or {}
            known = {
                "organization_name": data.get("organization_name", ""),
                "present_board": str(data.get("present_board", "") or ""),
                "active_board": str(data.get("active_board", "") or ""),
            }
            organization_prefill = {key: value for key, value in known.items() if value not in ("", [], None)}
            master = await get_master_record(db, user_id=user_id, email=prefill["email"])
            for key, value in master_prefill("activation", (master or {}).get("data", {})).items():
                organization_prefill.setdefault(key, value)
        if not prefill["email"] and session_id:
            try:
                session = stripe.checkout.Session.retrieve(session_id)
                details = getattr(session, "customer_details", None)
                if details:
                    prefill = {"name": details.get("name") or "", "email": details.get("email") or ""}
            except stripe.StripeError:
                pass
        return {"eligible": True, "purchase_source": purchase_source,
                "submitted": bool(existing), "prefill": prefill,
                "organization_prefill": organization_prefill, "calendly_url": CALENDLY_URL}

    async def notify_owner(payload: ActivationIntakeSubmission, purchase_source: str, now: str):
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        offer_label = OFFER_LABELS.get(purchase_source, purchase_source)
        rows = [
            ("Offer Purchased", offer_label),
            ("Name", payload.your_name), ("Email", str(payload.email)),
            ("Organization", payload.organization_name),
            ("12-Month Fundraising Goal", payload.fundraising_goal),
            ("Amount Needed (12 Months)", payload.amount_needed),
            ("What the Money Will Accomplish", payload.money_accomplish),
            ("Current Fundraising Methods", ", ".join(payload.current_methods) + (f". Other: {payload.current_methods_other}" if payload.current_methods_other else "")),
            ("Written Fundraising Strategy", payload.written_strategy),
            ("Fundraising Calendar / Execution Plan", payload.fundraising_calendar),
            ("Who Carries Fundraising", ", ".join(payload.fundraising_carriers) + (f". Detail: {payload.fundraising_carriers_detail}" if payload.fundraising_carriers_detail else "")),
            ("Total Board Members", payload.present_board),
            ("Active Board Members", payload.active_board),
            ("Board Fundraising Involvement", payload.board_fundraising_involvement),
            ("Current Board Fundraising Activities", ", ".join(payload.board_fundraising_activities) + (f". Other: {payload.board_fundraising_activities_other}" if payload.board_fundraising_activities_other else "")),
            ("Perceived Barriers", payload.perceived_barriers),
            ("Board Skills / Relationships", payload.board_skills_relationships),
            ("12-24 Month Direction", payload.direction_12_24),
            ("Organization Priorities", payload.organization_priorities),
            ("Previous Board Fundraising Planning", payload.previous_fundraising_planning),
            ("Broader Strategic Planning", payload.broader_strategic_planning),
            ("Desired Change", payload.desired_change),
            ("Successful Fundraising Board Definition", payload.success_definition),
            ("Anything Else", payload.anything_else or "Not provided"),
            ("Submitted", now),
        ]
        table = "".join(f"<tr><td style='padding:9px;border-bottom:1px solid #dddddd;font-weight:bold;vertical-align:top;'>{html.escape(str(label))}</td><td style='padding:9px;border-bottom:1px solid #dddddd;'>{html.escape(str(value))}</td></tr>" for label, value in rows)
        if purchase_source == BOARD_FIX_SOURCE:
            next_step = "is continuing on their Complete Board Fix roadmap into Board Fundraising Activation."
        elif purchase_source == "direct_diy_board_activation_497":
            next_step = "is starting immediately with the self-guided Fundraising Activation system."
        else:
            next_step = "is being sent to your Calendly."
        await resend.Emails.send_async({
            "from": os.environ["NONPROFIT_SENDER"], "to": [os.environ["OWNER_NOTIFICATION_EMAIL"]],
            "subject": f"Board Activation Intake Submitted — {payload.organization_name} ({offer_label})",
            "html": f"<div style='max-width:760px;margin:auto;font-family:Arial,sans-serif;color:#000;'><h1>Board Fundraising Activation Intake Submitted</h1><p>A paying customer just completed the Board Fundraising Activation intake and {next_step}</p><table style='width:100%;border-collapse:collapse;'>{table}</table></div>",
        })

    @router.post("/submit", status_code=201)
    async def submit_intake(request: Request, payload: ActivationIntakeSubmission):
        validate_board_counts(payload.present_board, payload.active_board)
        now = datetime.now(timezone.utc).isoformat()
        if payload.session_id:
            transaction = await verified_transaction(payload.session_id)
            user_id = await linked_user_id(payload.session_id, transaction)
            purchase_source = transaction["purchase_source"]
            storage_session = payload.session_id
            redirect_url = DIY_START_ROUTE if purchase_source == "direct_diy_board_activation_497" else CALENDLY_URL
        else:
            member = await board_fix_member(request, db, "activation_self_guided")
            user_id = member["user_id"]
            purchase_source = BOARD_FIX_SOURCE
            storage_session = synthetic_session(user_id)
            redirect_url = BOARD_FIX_COURSE_ROUTE
        record = payload.model_dump()
        record.update({
            "session_id": storage_session,
            "email": str(payload.email).lower(), "purchase_source": purchase_source,
            "user_id": user_id, "updated_at": now,
        })
        result = await db.board_activation_intakes.update_one(
            {"session_id": storage_session},
            {"$set": record, "$setOnInsert": {"intake_id": str(uuid.uuid4()), "submitted_at": now}},
            upsert=True,
        )
        if user_id:
            await write_back_master(db, user_id, "activation", record)
        if result.upserted_id is not None:
            try:
                await notify_owner(payload, purchase_source, now)
            except Exception:
                logger.exception("Owner activation intake notification failed for session %s", storage_session)
        return {"status": "submitted", "redirect_url": redirect_url, "session_key": storage_session}

    return router
