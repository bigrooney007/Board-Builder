import html
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List

import resend
import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from board_fix_master import BOARD_FIX_SOURCE, board_fix_member, get_master_record, master_prefill, synthetic_session, write_back_master

logger = logging.getLogger(__name__)

CALENDLY_URL = "https://calendly.com/boardbuilder/recruitboard"
DIY_START_ROUTE = "/recruitment-start-here"
BOARD_FIX_COURSE_ROUTE = "/app/recruitment/self-guided"
QUALIFYING_SOURCES = {"direct_diy_board_recruitment_497", "recruitment_campaign_diy_297", "direct_board_recruitment_project",
                      "board_recruitment_dfy", "recruitment_campaign_launch_697"}
DIY_SOURCES = {"direct_diy_board_recruitment_497", "recruitment_campaign_diy_297"}
OFFER_LABELS = {
    "direct_diy_board_recruitment_497": "Launch It Yourself — $497",
    "recruitment_campaign_diy_297": "Launch It Yourself — $297",
    "direct_board_recruitment_project": "Do It With Us — $1,497",
    "board_recruitment_dfy": "Board Recruitment — Done For You — $997",
    "recruitment_campaign_launch_697": "Recruitment Campaign Launch — $697",
    BOARD_FIX_SOURCE: "Complete Board Fix System — $497",
}


class IntakeSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")
    session_id: str = ""
    your_name: str = Field(min_length=1)
    email: EmailStr
    organization_name: str = Field(min_length=1)
    website: str = ""
    mission: str = Field(min_length=1)
    city: str = Field(min_length=1)
    state: str = ""
    board_type: str = Field(min_length=1)
    org_linkedin: str = ""
    org_linkedin_url: str = ""
    personal_linkedin: str = ""
    personal_linkedin_url: str = ""
    present_board: str = ""
    active_board: str = ""
    new_members_count: str = ""
    current_board_strengths: str = ""
    board_challenges: str = ""
    desired_skills: List[str] = []
    desired_skills_other: str = ""
    accomplish: str = ""
    specific_wants: str = ""
    meeting_frequency: str = ""
    meeting_frequency_other: str = ""
    meeting_format: str = ""
    meeting_location: str = ""
    virtual_meeting_info: str = ""
    board_term: str = ""
    board_term_other: str = ""
    time_commitment: str = ""
    max_board_size: str = ""
    max_board_size_unknown: bool = False
    application_deadline: str = ""
    deadline_date: str = ""
    anything_else: str = ""
    logo_data: str = ""
    primary_color: str = ""
    secondary_color: str = ""


def create_board_intake_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/board-recruitment-intake")
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
            existing = await db.board_recruitment_intakes.find_one({"session_id": session_id}, {"_id": 0, "submitted_at": 1})
        else:
            member = await board_fix_member(request, db, "recruitment_self_guided")
            user_id = member["user_id"]
            purchase_source = BOARD_FIX_SOURCE
            existing = await db.board_recruitment_intakes.find_one(
                {"$or": [{"session_id": synthetic_session(user_id)}, {"user_id": user_id}]}, {"_id": 0, "submitted_at": 1})
        prefill = {"name": "", "email": ""}
        organization_prefill = {}
        if user_id:
            member = await db.members.find_one({"user_id": user_id}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1})
            if member:
                prefill = {"name": f"{member['first_name']} {member['last_name']}".strip(), "email": member["email"]}
            profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data": 1, "strategy_intake": 1}) or {}
            data = profile.get("data", {}) or {}
            strategy = profile.get("strategy_intake", {}) or {}
            known = {
                "organization_name": data.get("organization_name", ""), "website": data.get("website", ""),
                "mission": data.get("mission", ""), "city": data.get("city", ""), "state": data.get("state_region", ""),
                "board_type": data.get("board_kind", ""), "present_board": data.get("present_board", ""),
                "active_board": data.get("active_board", ""), "new_members_count": data.get("new_members_count", ""),
                "desired_skills": data.get("desired_board_skills", []) or [],
                "accomplish": data.get("priorities", ""),
                "current_board_strengths": data.get("current_board_strengths", ""),
                "board_challenges": data.get("board_challenges", ""),
                "meeting_frequency": strategy.get("meeting_frequency", ""), "meeting_format": strategy.get("meeting_format", ""),
                "meeting_location": strategy.get("meeting_location", ""), "board_term": strategy.get("board_term", ""),
                "time_commitment": strategy.get("time_expectation", ""), "max_board_size": strategy.get("max_board_size", ""),
            }
            organization_prefill = {key: value for key, value in known.items() if value not in ("", [], None)}
            master = await get_master_record(db, user_id=user_id, email=prefill["email"])
            for key, value in master_prefill("recruitment", (master or {}).get("data", {})).items():
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

    async def merge_into_recruitment_profile(user_id: str, payload: IntakeSubmission, now: str):
        existing = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data": 1, "strategy_intake": 1, "branding": 1}) or {}
        data = existing.get("data", {}) or {}
        intake_data = {
            "organization_name": payload.organization_name, "website": payload.website, "mission": payload.mission,
            "city": payload.city, "state_region": payload.state, "board_kind": payload.board_type,
            "present_board": payload.present_board, "active_board": payload.active_board,
            "new_members_count": payload.new_members_count,
            "desired_board_skills": payload.desired_skills, "desired_board_skills_other": payload.desired_skills_other,
            "priorities": payload.accomplish,
            "contact_name": payload.your_name, "contact_email": str(payload.email).lower(),
            "org_linkedin": payload.org_linkedin, "org_linkedin_url": payload.org_linkedin_url,
            "personal_linkedin": payload.personal_linkedin, "personal_linkedin_url": payload.personal_linkedin_url,
            "current_board_strengths": payload.current_board_strengths,
            "board_challenges": payload.board_challenges,
            "specific_wants": payload.specific_wants,
            "anything_else": payload.anything_else,
        }
        merged = {**data}
        for key, value in intake_data.items():
            if value not in ("", [], None) and not merged.get(key):
                merged[key] = value
        strategy = existing.get("strategy_intake", {}) or {}
        intake_strategy = {
            "meeting_frequency": payload.meeting_frequency, "meeting_frequency_other": payload.meeting_frequency_other,
            "meeting_format": payload.meeting_format, "meeting_location": payload.meeting_location,
            "virtual_meeting_info": payload.virtual_meeting_info,
            "board_term": payload.board_term, "board_term_other": payload.board_term_other,
            "time_expectation": payload.time_commitment, "max_board_size": payload.max_board_size,
            "max_board_size_unknown": payload.max_board_size_unknown,
            "application_deadline": payload.application_deadline, "deadline_date": payload.deadline_date,
        }
        merged_strategy = {**strategy}
        for key, value in intake_strategy.items():
            if value not in ("", None) and not merged_strategy.get(key):
                merged_strategy[key] = value
        sets = {"data": merged, "strategy_intake": merged_strategy, "updated_at": now}
        existing_branding = existing.get("branding", {}) or {}
        branding_updates = {key: value for key, value in {
            "logo_data": payload.logo_data, "primary_color": payload.primary_color,
            "secondary_color": payload.secondary_color}.items() if value and not existing_branding.get(key)}
        if branding_updates:
            sets["branding"] = {**existing_branding, **branding_updates}
        await db.recruitment_profiles.update_one(
            {"user_id": user_id},
            {"$set": sets,
             "$setOnInsert": {"created_at": now}},
            upsert=True,
        )

    async def notify_owner(payload: IntakeSubmission, purchase_source: str, now: str):
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        offer_label = OFFER_LABELS.get(purchase_source, purchase_source)
        rows = [
            ("Offer Purchased", offer_label),
            ("Name", payload.your_name), ("Email", str(payload.email)),
            ("Organization", payload.organization_name), ("Website", payload.website or "Not provided"),
            ("Mission", payload.mission), ("Location", f"{payload.city}, {payload.state}".strip(", ")),
            ("Board Type", payload.board_type),
            ("Organization LinkedIn", f"{payload.org_linkedin}{' — ' + payload.org_linkedin_url if payload.org_linkedin_url else ''}"),
            ("Personal LinkedIn", f"{payload.personal_linkedin}{' — ' + payload.personal_linkedin_url if payload.personal_linkedin_url else ''}"),
            ("Current Board Members", payload.present_board), ("Actively Participating", payload.active_board),
            ("New Members Wanted", payload.new_members_count),
            ("Current Board Strengths", payload.current_board_strengths),
            ("Biggest Board Challenges", payload.board_challenges),
            ("Skills to Add", ", ".join(payload.desired_skills) + (f". Other: {payload.desired_skills_other}" if payload.desired_skills_other else "")),
            ("What New Members Should Help Accomplish", payload.accomplish),
            ("Specific Wants", payload.specific_wants or "Not provided"),
            ("Meeting Frequency", payload.meeting_frequency_other or payload.meeting_frequency),
            ("Meeting Format", payload.meeting_format), ("Meeting Location", payload.meeting_location or "Not provided"),
            ("Board Member Term", payload.board_term_other or payload.board_term),
            ("Monthly Time Commitment", payload.time_commitment or "Not provided"),
            ("Maximum Board Size", payload.max_board_size or "Not Specified / I Don't Know"),
            ("Application Deadline", payload.deadline_date or payload.application_deadline),
            ("Anything Else", payload.anything_else or "Not provided"),
            ("Submitted", now),
        ]
        table = "".join(f"<tr><td style='padding:9px;border-bottom:1px solid #dddddd;font-weight:bold;vertical-align:top;'>{html.escape(str(label))}</td><td style='padding:9px;border-bottom:1px solid #dddddd;'>{html.escape(str(value))}</td></tr>" for label, value in rows)
        if purchase_source == BOARD_FIX_SOURCE:
            next_step = "is continuing on their Complete Board Fix roadmap into Board Recruitment."
        elif purchase_source in DIY_SOURCES:
            next_step = "is starting immediately with the self-guided Recruitment system."
        else:
            next_step = "is being sent to your Calendly."
        await resend.Emails.send_async({
            "from": os.environ["NONPROFIT_SENDER"], "to": [os.environ["OWNER_NOTIFICATION_EMAIL"]],
            "subject": f"Board Recruitment Intake Submitted — {payload.organization_name} ({offer_label})",
            "html": f"<div style='max-width:760px;margin:auto;font-family:Arial,sans-serif;color:#000;'><h1>Board Recruitment Intake Submitted</h1><p>A paying customer just completed the Tell Me About Your Organization and Board form and {next_step}</p><table style='width:100%;border-collapse:collapse;'>{table}</table></div>",
        })

    @router.post("/submit", status_code=201)
    async def submit_intake(request: Request, payload: IntakeSubmission):
        now = datetime.now(timezone.utc).isoformat()
        if payload.session_id:
            transaction = await verified_transaction(payload.session_id)
            user_id = await linked_user_id(payload.session_id, transaction)
            purchase_source = transaction["purchase_source"]
            storage_session = payload.session_id
            redirect_url = DIY_START_ROUTE if purchase_source in DIY_SOURCES else CALENDLY_URL
        else:
            member = await board_fix_member(request, db, "recruitment_self_guided")
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
        result = await db.board_recruitment_intakes.update_one(
            {"session_id": storage_session},
            {"$set": record, "$setOnInsert": {"intake_id": str(uuid.uuid4()), "submitted_at": now}},
            upsert=True,
        )
        if user_id:
            await merge_into_recruitment_profile(user_id, payload, now)
            await write_back_master(db, user_id, "recruitment", record)
        if result.upserted_id is not None:
            try:
                await notify_owner(payload, purchase_source, now)
                logger.info("Owner intake notification sent for session %s", storage_session)
            except Exception:
                logger.exception("Owner intake notification failed for session %s", storage_session)
        return {"status": "submitted", "redirect_url": redirect_url, "session_key": storage_session}

    return router
