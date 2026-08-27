import html
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List

import resend
import stripe
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ai_service import extract_cv_text
from board_fix_master import BOARD_FIX_SOURCE, SYNTHETIC_PREFIX, board_fix_member, get_master_record, master_prefill, synthetic_session, write_back_master

logger = logging.getLogger(__name__)

CALENDLY_URL = "https://calendly.com/boardbuilder/recruitboard"
DIY_START_ROUTE = "/reactivation-start-here"
BOARD_FIX_COURSE_ROUTE = "/app/reactivation/self-guided"
QUALIFYING_SOURCES = {"direct_diy_board_reactivation_497", "direct_board_reactivation_project"}
OFFER_LABELS = {
    "direct_diy_board_reactivation_497": "Reactivation — Do It Yourself — $497",
    "direct_board_reactivation_project": "Reactivation — Do It With Me — $1,997",
    BOARD_FIX_SOURCE: "Complete Board Fix System — $497",
}


class ReactivationIntakeSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")
    session_id: str = ""
    your_name: str = Field(min_length=1)
    email: EmailStr
    has_bylaws: str = ""
    resignation_process: str = ""
    organization_name: str = Field(min_length=1)
    mission: str = Field(min_length=1)
    direction_12_24: str = Field(min_length=1)
    board_help_accomplish: str = Field(min_length=1)
    active_board_vision: str = Field(min_length=1)
    present_board: str = Field(min_length=1)
    active_board: str = Field(min_length=1)
    disengaged_board: str = Field(min_length=1)
    current_skills: str = Field(min_length=1)
    missing_skills: str = Field(min_length=1)
    recruited_how: List[str] = Field(min_length=1)
    original_responsibilities: str = Field(min_length=1)
    roles_defined: str = Field(min_length=1)
    roles_description: str = ""
    expected_contribution: str = Field(min_length=1)
    actually_happening: str = Field(min_length=1)
    strategic_plan: str = Field(min_length=1)
    board_participated_planning: str = Field(min_length=1)
    planning_involvement: str = ""
    disengage_reason: str = Field(min_length=1)
    disengage_when: str = Field(min_length=1)
    disengagement_signs: List[str] = Field(min_length=1)
    disengagement_signs_other: str = ""
    reactivation_attempts: str = Field(min_length=1)
    attempts_outcome: str = Field(min_length=1)
    meeting_frequency: str = Field(min_length=1)
    typical_meeting: str = Field(min_length=1)
    clear_responsibilities_after_meetings: str = Field(min_length=1)
    transition_options: List[str] = Field(min_length=1)
    anything_else: str = ""


def create_reactivation_intake_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/board-reactivation-intake")
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
            existing = await db.board_reactivation_intakes.find_one({"session_id": session_id}, {"_id": 0, "submitted_at": 1})
        else:
            member = await board_fix_member(request, db, "reactivation_self_guided")
            user_id = member["user_id"]
            purchase_source = BOARD_FIX_SOURCE
            existing = await db.board_reactivation_intakes.find_one(
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
                "mission": data.get("mission", ""),
                "present_board": data.get("present_board", ""),
                "active_board": data.get("active_board", ""),
            }
            organization_prefill = {key: value for key, value in known.items() if value not in ("", [], None)}
            master = await get_master_record(db, user_id=user_id, email=prefill["email"])
            for key, value in master_prefill("reactivation", (master or {}).get("data", {})).items():
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

    async def notify_owner(payload: ReactivationIntakeSubmission, purchase_source: str, now: str):
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        offer_label = OFFER_LABELS.get(purchase_source, purchase_source)
        rows = [
            ("Offer Purchased", offer_label),
            ("Name", payload.your_name), ("Email", str(payload.email)),
            ("Organization", payload.organization_name), ("Mission", payload.mission),
            ("12-24 Month Direction", payload.direction_12_24),
            ("What the Board Must Help Accomplish", payload.board_help_accomplish),
            ("What an Active Board Would Look Like", payload.active_board_vision),
            ("Current Board Members", payload.present_board),
            ("Actively Participating", payload.active_board),
            ("Disengaged / Inactive", payload.disengaged_board),
            ("Current Board Skills", payload.current_skills),
            ("Missing Skills / Relationships", payload.missing_skills),
            ("How Members Were Recruited", ", ".join(payload.recruited_how)),
            ("Original Responsibility Expectations", payload.original_responsibilities),
            ("Roles Clearly Defined", payload.roles_defined),
            ("How Responsibilities Are Assigned", payload.roles_description or "Not provided"),
            ("Expected Contribution", payload.expected_contribution),
            ("What Is Actually Happening", payload.actually_happening),
            ("Strategic Plan", payload.strategic_plan),
            ("Board Participated in Planning", payload.board_participated_planning),
            ("Planning Involvement", payload.planning_involvement or "Not provided"),
            ("Why the Board Disengaged", payload.disengage_reason),
            ("When Disengagement Started", payload.disengage_when),
            ("What Disengagement Looks Like", ", ".join(payload.disengagement_signs) + (f". Other: {payload.disengagement_signs_other}" if payload.disengagement_signs_other else "")),
            ("Previous Reactivation Attempts", payload.reactivation_attempts),
            ("What Happened", payload.attempts_outcome),
            ("Meeting Frequency", payload.meeting_frequency),
            ("Typical Board Meeting", payload.typical_meeting),
            ("Clear Responsibilities After Meetings", payload.clear_responsibilities_after_meetings),
            ("Transition Options Considered", ", ".join(payload.transition_options)),
            ("Anything Else", payload.anything_else or "Not provided"),
            ("Submitted", now),
        ]
        table = "".join(f"<tr><td style='padding:9px;border-bottom:1px solid #dddddd;font-weight:bold;vertical-align:top;'>{html.escape(str(label))}</td><td style='padding:9px;border-bottom:1px solid #dddddd;'>{html.escape(str(value))}</td></tr>" for label, value in rows)
        if purchase_source == BOARD_FIX_SOURCE:
            next_step = "is continuing on their Complete Board Fix roadmap into Board Reactivation."
        elif purchase_source == "direct_diy_board_reactivation_497":
            next_step = "is starting immediately with the self-guided Reactivation system."
        else:
            next_step = "is being sent to your Calendly."
        await resend.Emails.send_async({
            "from": os.environ["NONPROFIT_SENDER"], "to": [os.environ["OWNER_NOTIFICATION_EMAIL"]],
            "subject": f"Board Reactivation Intake Submitted — {payload.organization_name} ({offer_label})",
            "html": f"<div style='max-width:760px;margin:auto;font-family:Arial,sans-serif;color:#000;'><h1>Board Reactivation Intake Submitted</h1><p>A paying customer just completed the Board Reactivation intake and {next_step}</p><table style='width:100%;border-collapse:collapse;'>{table}</table></div>",
        })

    @router.post("/submit", status_code=201)
    async def submit_intake(request: Request, payload: ReactivationIntakeSubmission):
        now = datetime.now(timezone.utc).isoformat()
        if payload.session_id:
            transaction = await verified_transaction(payload.session_id)
            user_id = await linked_user_id(payload.session_id, transaction)
            purchase_source = transaction["purchase_source"]
            storage_session = payload.session_id
            redirect_url = DIY_START_ROUTE if purchase_source == "direct_diy_board_reactivation_497" else CALENDLY_URL
        else:
            member = await board_fix_member(request, db, "reactivation_self_guided")
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
        result = await db.board_reactivation_intakes.update_one(
            {"session_id": storage_session},
            {"$set": record, "$setOnInsert": {"intake_id": str(uuid.uuid4()), "submitted_at": now}},
            upsert=True,
        )
        if user_id:
            await write_back_master(db, user_id, "reactivation", record)
        if result.upserted_id is not None:
            try:
                await notify_owner(payload, purchase_source, now)
            except Exception:
                logger.exception("Owner reactivation intake notification failed for session %s", storage_session)
        return {"status": "submitted", "redirect_url": redirect_url, "session_key": storage_session}

    @router.post("/bylaws", status_code=201)
    async def upload_bylaws(request: Request, session_id: str = Form(...), file: UploadFile = File(...)):
        if session_id.startswith(SYNTHETIC_PREFIX):
            member = await board_fix_member(request, db, "reactivation_self_guided")
            if session_id != synthetic_session(member["user_id"]):
                raise HTTPException(status_code=403, detail="This upload does not belong to your account")
        else:
            await verified_transaction(session_id)
        intake = await db.board_reactivation_intakes.find_one({"session_id": session_id}, {"_id": 0, "intake_id": 1})
        if not intake:
            raise HTTPException(status_code=404, detail="Submit the intake form before uploading your bylaws")
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Bylaws file is too large (10MB maximum)")
        text = extract_cv_text(content, file.filename or "bylaws")
        await db.board_reactivation_intakes.update_one(
            {"session_id": session_id},
            {"$set": {"has_bylaws": "Yes", "bylaws_filename": file.filename or "", "bylaws_text": text[:120000],
                      "bylaws_uploaded_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "uploaded", "filename": file.filename or ""}

    return router
