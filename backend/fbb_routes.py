"""Fundraising Board Builder: flow video management + admin customer journey visibility."""
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth_service import authenticate_admin

FBB_PURCHASE_SOURCE = "fundraising_board_builder_497"

FLOW_VIDEO_DEFS = [
    {"key": "three_mistakes", "name": "Three Mistakes Video Page", "default_url": "https://www.youtube.com/watch?v=KDCnKeJoPRc"},
    {"key": "post_payment_welcome", "name": "Post-Payment Welcome Page", "default_url": ""},
    {"key": "fundraising_activation", "name": "Board Fundraising Activation Page", "default_url": "https://www.youtube.com/watch?v=Aw751ZtIIks"},
    {"key": "board_recruitment", "name": "Board Recruitment Page", "default_url": "https://www.youtube.com/watch?v=4aLqppruUvs"},
]
FLOW_VIDEO_KEYS = {item["key"] for item in FLOW_VIDEO_DEFS}

YOUTUBE_PATTERNS = [
    re.compile(r"[?&]v=([A-Za-z0-9_-]{11})"),
    re.compile(r"youtu\.be/([A-Za-z0-9_-]{11})"),
    re.compile(r"/embed/([A-Za-z0-9_-]{11})"),
    re.compile(r"/shorts/([A-Za-z0-9_-]{11})"),
]


def youtube_id(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    for pattern in YOUTUBE_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url
    return ""


class FlowVideoUpdate(BaseModel):
    url: str = Field(max_length=500)


def create_fbb_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def video_list() -> list:
        doc = await db.marketing_settings.find_one({"key": "flow_videos"}, {"_id": 0}) or {}
        stored = doc.get("videos", {})
        return [{"key": item["key"], "name": item["name"],
                 "url": stored.get(item["key"], item["default_url"]),
                 "youtube_id": youtube_id(stored.get(item["key"], item["default_url"]))}
                for item in FLOW_VIDEO_DEFS]

    @router.get("/flow-videos")
    async def flow_videos():
        return {"videos": await video_list()}

    @router.get("/admin/flow-videos")
    async def admin_flow_videos(request: Request):
        await authenticate_admin(request, db)
        return {"videos": await video_list()}

    @router.put("/admin/flow-videos/{key}")
    async def update_flow_video(key: str, payload: FlowVideoUpdate, request: Request):
        await authenticate_admin(request, db)
        if key not in FLOW_VIDEO_KEYS:
            raise HTTPException(status_code=404, detail="Unknown flow video")
        url = payload.url.strip()
        if url and not youtube_id(url):
            raise HTTPException(status_code=422, detail="Paste a valid YouTube link (or the 11-character video ID)")
        await db.marketing_settings.update_one(
            {"key": "flow_videos"},
            {"$set": {f"videos.{key}": url, "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
        return {"videos": await video_list()}

    @router.get("/admin/fbb/customers")
    async def fbb_customers(request: Request):
        await authenticate_admin(request, db)
        rows = []
        paid_emails = set()
        txns = await db.payment_transactions.find(
            {"purchase_source": FBB_PURCHASE_SOURCE},
            {"_id": 0, "session_id": 1, "payment_status": 1, "lead_name": 1, "lead_email": 1,
             "claimed_by_user_id": 1, "created_at": 1},
        ).sort("created_at", -1).to_list(300)
        for txn in txns:
            session_id = txn["session_id"]
            intake = await db.board_fix_intakes.find_one(
                {"session_id": session_id}, {"_id": 0, "submitted_at": 1, "user_id": 1, "data.organization_name": 1})
            user_id = txn.get("claimed_by_user_id") or (intake or {}).get("user_id", "")
            member = None
            if user_id:
                member = await db.members.find_one({"user_id": user_id}, {"_id": 0, "email": 1, "first_name": 1, "last_name": 1})
            activation = {"planning_responses": 0, "strategy_status": ""}
            recruitment = {"applicants": 0}
            if user_id:
                activation["planning_responses"] = await db.activation_participants.count_documents({"user_id": user_id, "status": "COMPLETED"})
                strategy = await db.activation_strategies.find_one({"user_id": user_id}, {"_id": 0, "status": 1}) or {}
                activation["strategy_status"] = strategy.get("status", "")
                recruitment["applicants"] = await db.opportunity_applications.count_documents({"owner_user_id": user_id})
            paid = txn.get("payment_status") == "paid"
            if member:
                stage = "Account Created"
            elif intake and intake.get("submitted_at"):
                stage = "Intake Completed"
            elif paid:
                stage = "Paid — Awaiting Intake"
            else:
                stage = "Checkout Started"
            email = (member or {}).get("email") or txn.get("lead_email", "")
            if email:
                paid_emails.add(email.lower())
            name = f"{member['first_name']} {member['last_name']}".strip() if member else txn.get("lead_name", "")
            rows.append({
                "type": "customer", "stage": stage, "session_id": session_id,
                "name": name, "email": email,
                "organization": ((intake or {}).get("data") or {}).get("organization_name", ""),
                "paid": paid, "created_at": txn.get("created_at", ""),
                "intake_submitted": bool(intake and intake.get("submitted_at")),
                "account_created": bool(member), "user_id": user_id,
                "activation": activation, "recruitment": recruitment,
            })
        leads = await db.funnel_leads.find(
            {"offer_source": "board_fix", "lead_source": "homepage_lead_magnet"},
            {"_id": 0, "name": 1, "email": 1, "created_at": 1, "lead_magnet_email_status": 1},
        ).sort("created_at", -1).to_list(200)
        lead_rows = [
            {"type": "lead", "stage": "Lead Captured — Video Link Sent", "name": lead.get("name", ""),
             "email": lead.get("email", ""), "organization": "", "paid": False,
             "created_at": lead.get("created_at", ""), "video_email_status": lead.get("lead_magnet_email_status", "")}
            for lead in leads if (lead.get("email") or "").lower() not in paid_emails
        ]
        return {"customers": rows, "leads": lead_rows}

    return router
