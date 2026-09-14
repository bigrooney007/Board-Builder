"""Board Fundraising Game: site content, pre-payment profile, claim + welcome email, situation form, dashboard."""
import html
import os
from datetime import datetime, timezone

import resend
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth_service import authenticate_admin
from member_auth import authenticate_member, require_entitlement
from member_routes import claim_recruitment_purchase

GAME_ENTITLEMENT = "board_fundraising_game"

DEFAULT_CONTENT = {
    "hero_badge": "THE BOARD FUNDRAISING GAME",
    "headline": "Bring Your Board Together to Build the Fundraising Strategy Your Organisation Needs",
    "subheadline": "The Board Fundraising Game unites your nonprofit board around one goal: creating and adopting the fundraising strategy your organization needs to raise money exponentially.",
    "goal_label": "How Much Does Your Organisation Want To Raise?",
    "goal_placeholder": "500,000",
    "cta_label": "Start Your Board Fundraising Game",
    "video_enabled": True,
    "video_heading": "See How the Board Fundraising Game Works",
    "video_text": "What board members do before Game Night, what happens during Game Night, and how your board leaves with a fundraising strategy and clear execution roles.",
    "stages_heading": "One Game. Three Stages. A Board That Fundraises.",
    "stages": [
        {"key": "before", "title": "Before Game Night", "items": [
            "Your organisation invites its board.",
            "Each board member receives a link to prepare for the Board Fundraising Game.",
            "They learn how fundraising strategy works, contribute their ideas and indicate how they want to participate in fundraising.",
        ]},
        {"key": "during", "title": "During Game Night", "items": [
            "The board comes together.",
            "They review and prioritise the ideas contributed by the board.",
            "The platform uses their collective thinking to create your organisation's fundraising strategy.",
            "The board reviews the strategy and agrees on how they will execute it.",
        ]},
        {"key": "after", "title": "After Game Night", "items": [
            "Your organisation has its fundraising strategy.",
            "Each board member receives their role in helping build the fundraising system and supporting fundraising.",
            "They also receive the materials and resources required to execute.",
        ]},
    ],
    "benefits_heading": "What Your Organisation Walks Away With",
    "benefits": [
        "Build a fundraising strategy with your entire board",
        "Teach board members how fundraising actually works",
        "Capture the knowledge, relationships and ideas already sitting around your board table",
        "Identify the best fundraising audiences and opportunities",
        "Decide how the organisation will raise money",
        "Build the fundraising system required to execute at scale",
        "Give every board member a clear role",
        "Equip board members with the tools they need to execute",
        "Turn the next board meeting into a working fundraising strategy session",
    ],
    "pricing_heading": "Unlock Your Board Fundraising Game",
    "price_display": "$497",
    "price_note": "One-time payment. One organisation. Your entire board plays.",
    "faqs_heading": "Frequently Asked Questions",
    "faqs": [
        {"q": "What exactly is the Board Fundraising Game?", "a": "It is a structured experience that brings your board together to build, adopt and prepare to execute the fundraising strategy your organisation needs to raise its fundraising goal."},
        {"q": "Is this a subscription?", "a": "No. The Board Fundraising Game is a one-time payment for your organisation."},
        {"q": "Do my board members need accounts?", "a": "No. You set up the game and your board members receive simple links to participate."},
        {"q": "How long does Game Night take?", "a": "Most boards complete Game Night inside a single board meeting. Preparation happens individually before the meeting."},
        {"q": "What happens after we play?", "a": "Your organisation leaves with its fundraising strategy, and every board member receives their execution role and the materials to act on it."},
    ],
    "testimonials_heading": "What Nonprofit Leaders Say",
}

ORG_FIELDS = ["name", "website", "org_type", "location", "mission", "who_served"]
GOAL_FIELDS = ["amount", "deadline", "purpose", "why_now"]
USER_FIELDS = ["full_name", "job_title", "email"]
SITUATION_SECTIONS = ["financial", "activities", "team", "donors", "corporate", "grantors", "technology", "materials", "reflections"]

GAME_AREAS = [
    {"key": "group_game", "name": "Start Group Game", "description": "Run Game Night with your board and prioritise the board's ideas together."},
    {"key": "working_strategy", "name": "Working Fundraising Strategy", "description": "The strategy built from your board's collective thinking."},
    {"key": "final_strategy", "name": "Final Fundraising Strategy", "description": "The strategy your board reviews, refines and adopts."},
    {"key": "portfolios", "name": "Board Portfolios", "description": "Each board member's role in executing the strategy."},
    {"key": "execution_materials", "name": "Execution Materials", "description": "The tools and resources your board needs to execute."},
]


def clean_section(data: dict, fields: list) -> dict:
    out = {}
    for key in fields:
        if key in (data or {}):
            value = data[key]
            if key == "amount":
                try:
                    out[key] = max(0, int(float(str(value).replace(",", "").replace("$", "") or 0)))
                except (TypeError, ValueError):
                    out[key] = 0
            else:
                out[key] = str(value or "").strip()[:4000]
    return out


class ProfileUpdate(BaseModel):
    organization: dict = Field(default_factory=dict)
    goal: dict = Field(default_factory=dict)
    primary_user: dict = Field(default_factory=dict)


class ClaimPayload(BaseModel):
    session_id: str = ""
    origin_url: str = ""


class SituationUpdate(BaseModel):
    sections: dict = Field(default_factory=dict)
    current_step: int = Field(default=0, ge=0, le=20)


def create_game_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def get_content() -> dict:
        doc = await db.marketing_settings.find_one({"key": "game_site_content"}, {"_id": 0}) or {}
        stored = doc.get("content") or {}
        return {**DEFAULT_CONTENT, **{k: v for k, v in stored.items() if k in DEFAULT_CONTENT}}

    async def get_profile_doc(user_id: str) -> dict:
        return await db.game_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}

    async def welcome_video_url() -> str:
        doc = await db.marketing_settings.find_one({"key": "flow_videos"}, {"_id": 0}) or {}
        return (doc.get("videos") or {}).get("game_welcome", "")

    @router.get("/game/content")
    async def game_content():
        return {"content": await get_content()}

    @router.put("/admin/game/content")
    async def update_game_content(payload: dict, request: Request):
        await authenticate_admin(request, db)
        clean = {k: payload[k] for k in payload if k in DEFAULT_CONTENT}
        if not clean:
            raise HTTPException(status_code=422, detail="No recognised content fields provided")
        sets = {f"content.{k}": v for k, v in clean.items()}
        sets["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.marketing_settings.update_one({"key": "game_site_content"}, {"$set": sets}, upsert=True)
        return {"content": await get_content()}

    @router.get("/game/profile")
    async def game_profile(request: Request):
        member = await authenticate_member(request, db)
        profile = await get_profile_doc(member["user_id"])
        return {
            "profile": profile,
            "unlocked": GAME_ENTITLEMENT in member.get("entitlements", []),
            "member": {"first_name": member.get("first_name", ""), "last_name": member.get("last_name", ""), "email": member.get("email", "")},
        }

    @router.put("/game/profile")
    async def save_game_profile(payload: ProfileUpdate, request: Request):
        member = await authenticate_member(request, db)
        existing = await get_profile_doc(member["user_id"])
        now = datetime.now(timezone.utc).isoformat()
        organization = {**existing.get("organization", {}), **clean_section(payload.organization, ORG_FIELDS)}
        goal = {**existing.get("goal", {}), **clean_section(payload.goal, GOAL_FIELDS)}
        primary_user = {**existing.get("primary_user", {}), **clean_section(payload.primary_user, USER_FIELDS)}
        if not primary_user.get("email"):
            primary_user["email"] = member.get("email", "")
        completed = bool(organization.get("name") and goal.get("amount") and goal.get("purpose") and primary_user.get("full_name"))
        await db.game_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"organization": organization, "goal": goal, "primary_user": primary_user,
                      "profile_completed": completed, "updated_at": now},
             "$setOnInsert": {"user_id": member["user_id"], "created_at": now}},
            upsert=True)
        return {"profile": await get_profile_doc(member["user_id"])}

    @router.post("/game/claim")
    async def game_claim(payload: ClaimPayload, request: Request):
        member = await authenticate_member(request, db)
        if payload.session_id:
            await claim_recruitment_purchase(db, member, payload.session_id)
        fresh = await db.members.find_one({"user_id": member["user_id"]}, {"_id": 0, "password_hash": 0}) or member
        if GAME_ENTITLEMENT not in fresh.get("entitlements", []):
            raise HTTPException(status_code=402, detail="We could not confirm your Board Fundraising Game purchase yet")
        profile = await get_profile_doc(member["user_id"])
        if not profile.get("welcome_email_sent"):
            video_url = await welcome_video_url()
            origin = html.escape((payload.origin_url or "").rstrip("/"))
            video_block = f"<p><a href='{html.escape(video_url)}'>Watch your tutorial video</a></p>" if video_url else ""
            dashboard_link = f"<p>You can return to your game anytime at <a href='{origin}/game/dashboard'>{origin}/game/dashboard</a>.</p>" if origin else ""
            try:
                resend.api_key = os.environ["RESEND_API_KEY"]
                await resend.Emails.send_async({
                    "from": os.environ["NONPROFIT_SENDER"], "to": [member["email"]],
                    "subject": "Welcome to Your Board Fundraising Game",
                    "html": f"<div style='max-width:560px;margin:auto;font-family:Arial,sans-serif;color:#000;'>"
                            f"<h2>Welcome to Your Board Fundraising Game</h2>"
                            f"<p>Hello {html.escape(member.get('first_name', ''))},</p>"
                            f"<p>Your Board Fundraising Game is unlocked. Your tutorial video explains how to use the platform, prepare your board and run the game.</p>"
                            f"{video_block}{dashboard_link}"
                            f"<p>Next step: complete your game setup so we understand your organisation's current fundraising situation.</p></div>",
                })
                await db.game_profiles.update_one(
                    {"user_id": member["user_id"]},
                    {"$set": {"welcome_email_sent": True, "welcome_email_sent_at": datetime.now(timezone.utc).isoformat()},
                     "$setOnInsert": {"user_id": member["user_id"], "created_at": datetime.now(timezone.utc).isoformat()}},
                    upsert=True)
            except Exception:
                pass
        return {"unlocked": True, "situation_completed": bool(profile.get("situation_completed"))}

    @router.get("/game/situation")
    async def game_situation(request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        doc = await db.game_situations.find_one({"user_id": member["user_id"]}, {"_id": 0})
        return doc or {"sections": {}, "current_step": 0, "completed": False}

    @router.put("/game/situation")
    async def save_game_situation(payload: SituationUpdate, request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        now = datetime.now(timezone.utc).isoformat()
        sets = {"current_step": payload.current_step, "updated_at": now}
        for key, value in (payload.sections or {}).items():
            if key in SITUATION_SECTIONS and isinstance(value, dict):
                clean = {}
                for field, raw in value.items():
                    field = str(field)[:80]
                    if isinstance(raw, list):
                        clean[field] = [str(item)[:300] for item in raw[:40]]
                    else:
                        clean[field] = str(raw or "")[:6000]
                sets[f"sections.{key}"] = clean
        await db.game_situations.update_one(
            {"user_id": member["user_id"]},
            {"$set": sets, "$setOnInsert": {"user_id": member["user_id"], "completed": False, "created_at": now}},
            upsert=True)
        return {"status": "saved"}

    @router.post("/game/situation/complete")
    async def complete_game_situation(request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        now = datetime.now(timezone.utc).isoformat()
        await db.game_situations.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"completed": True, "completed_at": now, "updated_at": now},
             "$setOnInsert": {"user_id": member["user_id"], "created_at": now}},
            upsert=True)
        await db.game_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"situation_completed": True, "updated_at": now},
             "$setOnInsert": {"user_id": member["user_id"], "created_at": now}},
            upsert=True)
        return {"status": "complete"}

    @router.get("/game/dashboard")
    async def game_dashboard(request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        profile = await get_profile_doc(member["user_id"])
        situation_completed = bool(profile.get("situation_completed"))
        return {
            "first_name": member.get("first_name", ""),
            "organization": profile.get("organization", {}),
            "goal": profile.get("goal", {}),
            "situation_completed": situation_completed,
            "status": "set_up_board" if situation_completed else "complete_setup",
            "areas": [{**area, "locked": True} for area in GAME_AREAS],
        }

    @router.get("/admin/game/customers")
    async def game_customers(request: Request):
        await authenticate_admin(request, db)
        rows = []
        profiles = await db.game_profiles.find({}, {"_id": 0}).sort("updated_at", -1).to_list(300)
        for profile in profiles:
            member = await db.members.find_one({"user_id": profile["user_id"]}, {"_id": 0, "email": 1, "first_name": 1, "last_name": 1, "entitlements": 1}) or {}
            unlocked = GAME_ENTITLEMENT in member.get("entitlements", [])
            if unlocked and profile.get("situation_completed"):
                stage = "Game Setup Complete"
            elif unlocked:
                stage = "Paid — Setup In Progress"
            elif profile.get("profile_completed"):
                stage = "Profile Complete — Awaiting Payment"
            else:
                stage = "Profile Started"
            rows.append({
                "user_id": profile["user_id"], "stage": stage,
                "name": f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
                "email": member.get("email", ""),
                "organization": profile.get("organization", {}).get("name", ""),
                "goal_amount": profile.get("goal", {}).get("amount", 0),
                "goal_deadline": profile.get("goal", {}).get("deadline", ""),
                "unlocked": unlocked,
                "updated_at": profile.get("updated_at", ""),
            })
        return {"customers": rows}

    return router
