"""Consolidated Board Reactivation / Engagement Plan (shared-safe) — reuses existing engines."""
import asyncio
import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone

import resend
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ai_service import generate_structured
from board_fix_master import get_master_record
from member_auth import authenticate_member, require_entitlement
from reactivation_routes import build_portfolio_pdf, email_html, origin_of

logger = logging.getLogger(__name__)

OUTCOME_ACTIVE = "Continuing as an Active Board Member"
OUTCOME_ADVISORY = "Transitioning to an Advisory Role"
FINAL_OUTCOMES = {OUTCOME_ACTIVE, OUTCOME_ADVISORY, "Transitioning to Another Support Role", "Stepping Down From the Board"}
UNRESOLVED_WARNING = "Some Board Member outcomes are still unresolved. Complete the remaining Reactivation conversations before finalizing your Board Engagement Plan."


def is_resolved(record: dict) -> bool:
    return bool((record.get("conversation_conclusion") or "").strip()) and record.get("conversation_outcome") in FINAL_OUTCOMES


class TextPayload(BaseModel):
    text: str = Field(min_length=1)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def plan_text(structured: dict, organization: str) -> str:
    def block(title, value):
        if isinstance(value, list):
            return [title] + [f"- {item}" for item in value] + [""] if value else []
        return [title, str(value), ""] if value else []
    title = structured.get("document_title") or "Board Reactivation & Engagement Plan"
    lines = [str(title).upper()]
    if organization and organization.lower() not in str(title).lower():
        lines.append(organization)
    lines.append("")
    lines += block("PURPOSE", structured.get("purpose", ""))
    lines += block("OUR BOARD MOVING FORWARD", structured.get("our_board_moving_forward", ""))
    lines += block("HOW WE WILL WORK TOGETHER", structured.get("how_we_will_work_together", []))
    members = structured.get("board_member_engagement", []) or []
    if members:
        lines.append("OUR BOARD MEMBER ENGAGEMENT")
        for entry in members:
            lines.append("")
            lines.append(entry.get("member_name", ""))
            if entry.get("board_role"):
                lines.append(f"Board Role: {entry['board_role']}")
            if entry.get("what_they_bring"):
                lines.append(f"What They Bring: {entry['what_they_bring']}")
            if entry.get("how_they_will_contribute"):
                lines.append(f"How They Will Contribute: {entry['how_they_will_contribute']}")
            if entry.get("agreed_responsibility"):
                lines.append(f"Agreed Responsibility: {entry['agreed_responsibility']}")
            if entry.get("agreed_leadership"):
                lines.append(f"Agreed Leadership: {entry['agreed_leadership']}")
            if entry.get("organization_support"):
                lines.append(f"Organization Support: {entry['organization_support']}")
        lines.append("")
    lines += block("OUR COLLECTIVE BOARD STRENGTHS", structured.get("collective_board_strengths", []))
    lines += block("HOW OUR STRENGTHS WORK TOGETHER", structured.get("how_our_strengths_work_together", ""))
    lines += block("OUR SHARED BOARD COMMITMENTS", structured.get("shared_board_commitments", []))
    lines += block("HOW THE ORGANIZATION WILL SUPPORT THE BOARD", structured.get("organization_commitments_to_the_board", []))
    advisory = structured.get("advisory_support", []) or []
    if advisory:
        lines.append("ADVISORY SUPPORT")
        for entry in advisory:
            line = f"- {entry.get('name', '')}"
            if entry.get("agreed_support"):
                line += f" — {entry['agreed_support']}"
            lines.append(line)
        lines.append("")
    lines += block("IMMEDIATE NEXT STEPS", structured.get("immediate_next_steps", []))
    lines += block("MOVING FORWARD TOGETHER", structured.get("moving_forward_together", ""))
    return "\n".join(lines).strip()


def create_reactivation_plan_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def member_of(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {"reactivation_self_guided"})
        return member

    async def org_context(user_id: str) -> dict:
        intake = await db.board_reactivation_intakes.find_one({"user_id": user_id}, {"_id": 0}, sort=[("submitted_at", -1)]) or {}
        member = await db.members.find_one({"user_id": user_id}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1, "organization_name": 1}) or {}
        return {"organization": intake.get("organization_name", "") or member.get("organization_name", "") or "your organization",
                "founder_name": f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
                "founder_email": member.get("email", ""), "founder_title": intake.get("founder_title", ""),
                "mission": intake.get("mission", "")}

    async def current_plan(user_id: str) -> dict:
        return await db.reactivation_engagement_plans.find_one({"user_id": user_id}, {"_id": 0}) or {}

    @router.get("/reactivation/engagement-plan")
    async def get_plan(request: Request):
        member = await member_of(request)
        plan = await current_plan(member["user_id"])
        records = await db.reactivation_board_members.find(
            {"user_id": member["user_id"]}, {"_id": 0, "status": 1, "conversation_conclusion": 1, "conversation_outcome": 1}).to_list(300)
        confirmed = sum(1 for r in records if is_resolved(r) and r.get("conversation_outcome") == OUTCOME_ACTIVE)
        unresolved = sum(1 for r in records if not is_resolved(r))
        return {"status": plan.get("status", "NONE"), "display_text": plan.get("display_text", ""),
                "generation_error": plan.get("generation_error", ""), "share_token": plan.get("share_token", ""),
                "responses_available": confirmed, "confirmed_active": confirmed, "unresolved": unresolved,
                "unresolved_warning": UNRESOLVED_WARNING if unresolved else ""}

    @router.post("/reactivation/engagement-plan/generate")
    async def generate_plan(request: Request):
        member = await member_of(request)
        user_id = member["user_id"]
        records = await db.reactivation_board_members.find({"user_id": user_id}, {"_id": 0}).to_list(300)
        confirmed = [r for r in records if is_resolved(r) and r.get("conversation_outcome") == OUTCOME_ACTIVE]
        advisory = [r for r in records if is_resolved(r) and r.get("conversation_outcome") == OUTCOME_ADVISORY]
        unresolved = [r for r in records if not is_resolved(r)]
        if not confirmed:
            raise HTTPException(status_code=409, detail="No Board Members have a confirmed recommitment yet. Complete each Reactivation conversation and record the Conversation Conclusion and final outcome first.")
        plan = await current_plan(user_id)
        if plan.get("status") == "Generating":
            return {"status": "Generating"}
        context_info = await org_context(user_id)
        now = now_iso()
        await db.reactivation_engagement_plans.update_one(
            {"user_id": user_id},
            {"$set": {"status": "Generating", "generation_error": "", "updated_at": now},
             "$setOnInsert": {"plan_id": str(uuid.uuid4()), "user_id": user_id, "created_at": now}},
            upsert=True)
        intake = await db.board_reactivation_intakes.find_one({"user_id": user_id}, {"_id": 0}, sort=[("submitted_at", -1)]) or {}
        org_keys = ["organization_name", "mission", "direction_12_24", "board_help_accomplish",
                    "active_board_vision", "expected_contribution"]
        context = ("VERIFIED ORGANIZATION CONTEXT:\n" + json.dumps({key: intake.get(key, "") for key in org_keys}, indent=1, default=str)
                   + f"\nFOUNDER: {context_info['founder_name']}"
                   + (f" ({context_info['founder_title']})" if context_info.get("founder_title") else ""))
        master = await get_master_record(db, user_id=user_id)
        if master and master.get("data"):
            context += ("\n\nCOMPLETE BOARD FIX MASTER INTAKE (the founder's own description of the organization, its board, goals and priorities):\n"
                        + json.dumps(master["data"], indent=1, default=str)[:6000])
        if intake.get("bylaws_text"):
            context += "\n\nORGANIZATION BYLAWS EXTRACT (verified Board/governance context ONLY — never invent requirements):\n" + intake["bylaws_text"][:8000]
        context += ("\n\nCONFIRMED CONTINUING ACTIVE BOARD MEMBERS — only these people appear in the main engagement plan. "
                    "For each, the saved Conversation Conclusion is AUTHORITATIVE for what was agreed; it may contain private detail, "
                    "so extract ONLY the outward-facing agreement appropriate for a Board-facing document. "
                    "Original form responses are supporting background only; monthly capacity is for internal calibration and must not be published unless it was clearly agreed as a Board-facing commitment:\n\n")
        for record in confirmed:
            response = record.get("response") or {}
            context += json.dumps({
                "name": record["name"], "current_board_role": record.get("role", ""),
                "final_recorded_outcome": record.get("conversation_outcome", ""),
                "conversation_conclusion_authoritative": (record.get("conversation_conclusion") or "")[:2500],
                "original_form_background_only": {key: response.get(key, "") for key in [
                    "why_joined", "expertise", "expertise_other", "contribution_interests", "ownership_area",
                    "leadership_interest", "leadership_area", "strengths_resources", "monthly_availability"]},
            }, indent=1, default=str)[:6000] + "\n\n"
        if advisory:
            context += "CONFIRMED ADVISORY TRANSITIONS (may appear ONLY under Advisory Support, and only the agreed continuing support):\n\n"
            for record in advisory:
                context += json.dumps({
                    "name": record["name"],
                    "conversation_conclusion_authoritative": (record.get("conversation_conclusion") or "")[:1500],
                }, indent=1, default=str) + "\n\n"
        if unresolved:
            context += (f"\nNOTE: {len(unresolved)} current Board Member(s) still have unresolved Reactivation outcomes. "
                        "They are NOT part of this plan — do not mention them, do not treat them as continuing and do not treat them as departed.")

        async def run_generation():
            try:
                structured = await generate_structured("reactivation_engagement_plan", context)
                await db.reactivation_engagement_plans.update_one({"user_id": user_id}, {"$set": {
                    "status": "Draft", "structured": structured,
                    "display_text": plan_text(structured, context_info["organization"]),
                    "members_included": [r["member_record_id"] for r in confirmed if r.get("member_record_id")],
                    "updated_at": now_iso()}})
            except Exception as exc:
                logger.error("Engagement plan generation failed for %s: %s", user_id, exc)
                await db.reactivation_engagement_plans.update_one({"user_id": user_id}, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300], "updated_at": now_iso()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating", "unresolved_warning": UNRESOLVED_WARNING if unresolved else ""}

    @router.put("/reactivation/engagement-plan")
    async def edit_plan(payload: TextPayload, request: Request):
        member = await member_of(request)
        plan = await current_plan(member["user_id"])
        if not plan.get("display_text"):
            raise HTTPException(status_code=409, detail="Generate the Board Reactivation / Engagement Plan first")
        await db.reactivation_engagement_plans.update_one({"user_id": member["user_id"]}, {"$set": {
            "display_text": payload.text, "status": "Draft", "updated_at": now_iso()}})
        return {"status": "Draft"}

    @router.post("/reactivation/engagement-plan/approve")
    async def approve_plan(request: Request):
        member = await member_of(request)
        plan = await current_plan(member["user_id"])
        if plan.get("status") not in {"Draft", "Approved"} or not plan.get("display_text"):
            raise HTTPException(status_code=409, detail="There is no draft plan ready to approve")
        token = plan.get("share_token") or secrets.token_urlsafe(32)
        await db.reactivation_engagement_plans.update_one({"user_id": member["user_id"]}, {"$set": {
            "status": "Approved", "share_token": token, "approved_at": now_iso()}})
        return {"status": "Approved", "share_token": token}

    @router.get("/reactivation/engagement-plan/pdf")
    async def plan_pdf(request: Request):
        member = await member_of(request)
        plan = await current_plan(member["user_id"])
        if not plan.get("display_text"):
            raise HTTPException(status_code=404, detail="The plan has not been generated yet")
        context_info = await org_context(member["user_id"])
        return build_portfolio_pdf("BOARD REACTIVATION / ENGAGEMENT PLAN", context_info["organization"],
                                   {"organization_name": context_info["organization"], "issued_by": context_info["founder_name"]},
                                   plan["display_text"])

    def member_email(context_info: dict, name: str, link: str) -> dict:
        first = (name or "").split(" ")[0]
        signature = context_info["founder_name"] + (f"\n{context_info['founder_title']}" if context_info.get("founder_title") else "") + f"\n{context_info['organization']}"
        body = (f"Dear {first},\n\n"
                f"Thank you for completing your Board Member Profile & Recommitment Form for {context_info['organization']}.\n\n"
                "I have brought together what our participating Board Members shared into one Board Reactivation / Engagement Plan — how we are willing to serve, the skills and expertise around our table, the commitments we are carrying, and how we move forward together.\n\n"
                "[VIEW OUR BOARD ENGAGEMENT PLAN]\n\n"
                f"Thank you for standing with the mission.\n\n{signature}")
        return {"subject": f"Our Board Reactivation / Engagement Plan | {context_info['organization']}",
                "body": body, "button_label": "VIEW OUR BOARD ENGAGEMENT PLAN", "form_link": link}

    @router.get("/reactivation/engagement-plan/members/{member_record_id}/email-preview")
    async def email_preview(member_record_id: str, request: Request):
        member = await member_of(request)
        plan = await current_plan(member["user_id"])
        if plan.get("status") != "Approved":
            raise HTTPException(status_code=409, detail="Approve the plan before preparing the email")
        record = await db.reactivation_board_members.find_one(
            {"user_id": member["user_id"], "member_record_id": member_record_id}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Board Member not found")
        context_info = await org_context(member["user_id"])
        email = member_email(context_info, record.get("name", ""), f"{origin_of(request)}/board-plan/{plan['share_token']}")
        return {"to_name": record.get("name", ""), "to_email": record.get("email", ""), **email}

    @router.post("/reactivation/engagement-plan/members/{member_record_id}/send")
    async def send_plan(member_record_id: str, request: Request):
        member = await member_of(request)
        plan = await current_plan(member["user_id"])
        if plan.get("status") != "Approved":
            raise HTTPException(status_code=409, detail="Approve the plan before sending it")
        record = await db.reactivation_board_members.find_one(
            {"user_id": member["user_id"], "member_record_id": member_record_id}, {"_id": 0})
        if not record or not record.get("email"):
            raise HTTPException(status_code=404, detail="Board Member not found")
        context_info = await org_context(member["user_id"])
        email = member_email(context_info, record.get("name", ""), f"{origin_of(request)}/board-plan/{plan['share_token']}")
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        message = {"from": os.environ["NONPROFIT_SENDER"], "to": [record["email"]],
                   "subject": email["subject"], "html": email_html(email["body"], email["button_label"], email["form_link"])}
        if context_info.get("founder_email"):
            message["reply_to"] = [context_info["founder_email"]]
        try:
            await resend.Emails.send_async(message)
        except Exception as exc:
            logger.exception("Engagement plan send failed for %s", member_record_id)
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc
        now = now_iso()
        await db.reactivation_engagement_plans.update_one({"user_id": member["user_id"]}, {"$push": {
            "sends": {"member_record_id": member_record_id, "to_email": record["email"], "sent_at": now}}})
        return {"status": "sent", "sent_at": now}

    @router.get("/board-plan/{token}")
    async def public_plan(token: str):
        plan = await db.reactivation_engagement_plans.find_one({"share_token": token, "status": "Approved"}, {"_id": 0})
        if not plan:
            raise HTTPException(status_code=404, detail="This link is not valid")
        context_info = await org_context(plan["user_id"])
        return {"title": "Board Reactivation / Engagement Plan", "organization_name": context_info["organization"],
                "display_text": plan["display_text"], "issued_by": context_info["founder_name"]}

    return router
