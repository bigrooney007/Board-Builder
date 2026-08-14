"""Consolidated Board Reactivation / Engagement Plan (shared-safe) — reuses existing engines."""
import asyncio
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone

import resend
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ai_service import generate_structured
from member_auth import authenticate_member, require_entitlement
from reactivation_routes import build_portfolio_pdf, email_html, origin_of

logger = logging.getLogger(__name__)


class TextPayload(BaseModel):
    text: str = Field(min_length=1)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def plan_text(structured: dict, organization: str) -> str:
    lines = ["BOARD REACTIVATION / ENGAGEMENT PLAN", organization, ""]
    for section in structured.get("sections", []):
        lines.extend([str(section.get("heading", "")).upper(), str(section.get("content", "")), ""])
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
        completed = await db.reactivation_board_members.count_documents({"user_id": member["user_id"], "status": "COMPLETED"})
        return {"status": plan.get("status", "NONE"), "display_text": plan.get("display_text", ""),
                "generation_error": plan.get("generation_error", ""), "share_token": plan.get("share_token", ""),
                "responses_available": completed}

    @router.post("/reactivation/engagement-plan/generate")
    async def generate_plan(request: Request):
        member = await member_of(request)
        user_id = member["user_id"]
        records = await db.reactivation_board_members.find({"user_id": user_id, "status": "COMPLETED"}, {"_id": 0}).to_list(300)
        participating = [r for r in records if r.get("conversation_outcome") != "Stepping Down From the Board"]
        if not participating:
            raise HTTPException(status_code=409, detail="No completed Board Member recommitment responses are available yet")
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
        shared = "\n\n".join(
            f"BOARD MEMBER (self-shared recommitment response): {r.get('name', '')} (role: {r.get('role', '')})\n"
            + "\n".join(f"  {k}: {', '.join(v) if isinstance(v, list) else v}" for k, v in (r.get("response") or {}).items() if v)
            for r in participating)
        context = (f"ORGANIZATION: {context_info['organization']}\nMISSION: {context_info['mission']}\n"
                   f"FOUNDER: {context_info['founder_name']}\n\nPARTICIPATING BOARD MEMBERS' OWN SHARED RESPONSES ONLY:\n\n{shared}")

        async def run_generation():
            try:
                structured = await generate_structured("reactivation_engagement_plan", context)
                await db.reactivation_engagement_plans.update_one({"user_id": user_id}, {"$set": {
                    "status": "Draft", "structured": structured,
                    "display_text": plan_text(structured, context_info["organization"]),
                    "members_included": [r["member_record_id"] for r in participating if r.get("member_record_id")],
                    "updated_at": now_iso()}})
            except Exception as exc:
                logger.error("Engagement plan generation failed for %s: %s", user_id, exc)
                await db.reactivation_engagement_plans.update_one({"user_id": user_id}, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300], "updated_at": now_iso()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating"}

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
