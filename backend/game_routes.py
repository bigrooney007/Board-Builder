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
    "headline": "Get Your Board Members To Raise Money and Work With You To Build Your Organization's Fundraising System",
    "subheadline": "Stop Self-Funding or Carrying Fundraising Alone. Turn Your Next Board Meeting Into A Fun Board Fundraising Activation Session.",
    "intro_heading": "Why Your Board Is Not Fundraising With You",
    "intro_paragraphs": [
        "Your board cannot fully commit to raising money and building your organization's fundraising system when they had no role in creating the strategy they are being asked to execute.",
        "If you want your board members to raise money and help build your fundraising system, bring them into the process of creating and adopting the fundraising strategy with you.",
        "The Board Fundraising Game brings everyone into the process from the beginning. It captures the knowledge, relationships and ideas already sitting around your board table and turns them into a fundraising strategy your board understands, adopts and is prepared to execute.",
    ],
    "goal_label": "How Much Does Your Organization Want To Raise?",
    "goal_placeholder": "500,000",
    "cta_label": "Start My Board Fundraising Game",
    "video_enabled": True,
    "video_label": "Watch",
    "video_heading": "See How The Board Fundraising Game Works",
    "video_text": "See how your board moves from individual thinking to collective decisions, an adopted fundraising strategy and clear fundraising roles for every board member.",
    "stages_label": "How It Works",
    "stages_heading": "One Game. One Fundraising Goal. Your Entire Board Behind It.",
    "stages": [
        {"key": "before", "number": "1", "title": "Before Game Night", "items": [
            "Each board member receives their own Individual Game invitation link before your next board meeting.",
            "They learn how fundraising works, contribute their ideas about how your organization can raise money and decide how they would like to participate in fundraising.",
            "By the time your board meets, everyone has already thought seriously about how your organization can reach its fundraising goal.",
        ]},
        {"key": "during", "number": "2", "title": "During Game Night", "items": [
            "Your board turns individual ideas into collective decisions.",
            "Everyone reviews the ideas contributed by the board and ranks the strongest opportunities they believe your organization should prioritize.",
            "The platform turns those priorities into your fundraising strategy.",
            "Your board reviews the strategy together, makes the final decisions and adopts the strategy it is prepared to execute.",
        ]},
        {"key": "after", "number": "3", "title": "After Game Night", "items": [
            "Everyone leaves knowing what happens next.",
            "Your organization leaves with an adopted fundraising strategy.",
            "Each board member receives a personal Board Fundraising Portfolio showing how they will help build your fundraising system and how they will help raise money.",
            "They also receive the scripts, templates, checklists and resources they need to execute their role.",
        ]},
    ],
    "stages_cta_label": "Launch My Board Fundraising Game",
    "outcomes_label": "Outcomes",
    "outcomes_heading": "Your Board Meeting Ends With More Than A Conversation",
    "outcomes": [
        {"key": "strategy", "heading": "1. A Clear Fundraising Strategy and Direction", "paragraphs": [
            "Your board identifies who your organization should raise money from, where to find them, how to attract them, the process to raise money from them, and the team, technology and materials required to execute.",
            "You also leave with a clear execution timeline and direction for moving from strategy into action.",
        ]},
        {"key": "knowledge", "heading": "2. A Board That Knows How To Raise Money", "paragraphs": [
            "Your board members learn how fundraising actually works while building the strategy themselves.",
            "They understand who your organization is raising money from, how those funders will be reached and what needs to happen to move them from first contact to financial support.",
            "Instead of simply telling your board members to fundraise, you give them the knowledge, strategy and tools to actually do it.",
        ]},
        {"key": "system", "heading": "3. A Fundraising System Your Organization Can Build On", "paragraphs": [
            "If your organization wants to consistently raise money from individuals, businesses and grantmakers, fundraising cannot depend entirely on you.",
            "You need a system that consistently helps your organization find potential funders, attract their attention, build relationships, ask for support, follow up and steward them.",
            "The Board Fundraising Game helps your board design that system with you so fundraising can become an organizational capability instead of one person's responsibility.",
        ]},
        {"key": "roles", "heading": "4. A Clear Role For Every Board Member", "paragraphs": [
            "Every board member chooses how they want to participate.",
            "They identify how they want to help build your fundraising system and how they want to help raise money directly.",
            "Then they receive a personal Board Fundraising Portfolio and the tools they need to execute their role.",
        ]},
        {"key": "trust", "heading": "5. A Board That Trusts Your Leadership", "paragraphs": [
            "When you lead your board through a clear process that teaches them, involves them in decisions and equips them to contribute, you give them a reason to trust your leadership.",
            "You are no longer simply asking them to do more.",
            "You are giving them the structure, direction and resources they need to show up at the level they want to show up.",
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
    "faqs_label": "Questions",
    "faqs_heading": "Frequently Asked Questions",
    "faqs": [
        {"q": "What exactly is the Board Fundraising Game?", "a": "It is a structured experience that brings your board together to build, adopt and prepare to execute the fundraising strategy your organisation needs to raise its fundraising goal."},
        {"q": "Is this a subscription?", "a": "No. The Board Fundraising Game is a one-time payment for your organisation."},
        {"q": "Do my board members need accounts?", "a": "No. You set up the game and your board members receive simple links to participate."},
        {"q": "How long does Game Night take?", "a": "Most boards complete Game Night inside a single board meeting. Preparation happens individually before the meeting."},
        {"q": "What happens after we play?", "a": "Your organisation leaves with its fundraising strategy, and every board member receives their execution role and the materials to act on it."},
    ],
    "testimonials_heading": "What Nonprofit Leaders Say",
    "closing_heading": "Ready To Stop Carrying Fundraising Alone?",
    "closing_text": "Bring your board together around one fundraising goal and build the strategy, system and board participation required to reach it.",
    "closing_cta_label": "Start My Board Fundraising Game",
}

ORG_FIELDS = ["name", "website", "org_type", "location", "mission", "who_served"]
GOAL_FIELDS = ["amount", "deadline", "purpose", "why_now"]
USER_FIELDS = ["full_name", "job_title", "email"]
SITUATION_SECTIONS = ["financial", "activities", "team", "donors", "corporate", "grantors", "technology", "materials", "reflections"]

GAME_AREAS = [
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
            member = await db.members.find_one(
                {"user_id": profile["user_id"]},
                {"_id": 0, "email": 1, "first_name": 1, "last_name": 1, "entitlements": 1, "game_test_unlock": 1}) or {}
            unlocked = GAME_ENTITLEMENT in member.get("entitlements", [])
            purchase = await db.purchases.find_one(
                {"user_id": profile["user_id"], "purchase_source": "board_fundraising_game_497"},
                {"_id": 0, "offer": 1, "price_paid": 1, "purchased_at": 1, "created_at": 1})
            test_unlock = member.get("game_test_unlock") if isinstance(member.get("game_test_unlock"), dict) else {}
            test_active = bool(test_unlock.get("active"))
            if purchase:
                access_state = "Paid — Stripe"
            elif test_active:
                access_state = "Unlocked For Testing"
            elif unlocked:
                access_state = "Unlocked"
            else:
                access_state = "Not Unlocked"
            if unlocked and profile.get("situation_completed"):
                stage = "Game Setup Complete"
            elif unlocked and test_active and not purchase:
                stage = "Testing — Setup In Progress"
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
                "access_state": access_state,
                "test_unlock": {
                    "active": test_active,
                    "unlocked_at": test_unlock.get("test_unlocked_at", ""),
                    "unlocked_by": test_unlock.get("test_unlocked_by_email", "") or test_unlock.get("test_unlocked_by", ""),
                },
                "purchase": {
                    "offer": purchase.get("offer", ""), "price_paid": purchase.get("price_paid", 0),
                    "purchased_at": purchase.get("purchased_at", "") or purchase.get("created_at", ""),
                } if purchase else None,
                "updated_at": profile.get("updated_at", ""),
            })
        return {"customers": rows}

    async def game_purchase_for(user_id: str):
        return await db.purchases.find_one(
            {"user_id": user_id, "purchase_source": "board_fundraising_game_497"}, {"_id": 0, "purchase_id": 1})

    @router.post("/admin/game/customers/{user_id}/unlock-testing")
    async def unlock_for_testing(user_id: str, request: Request):
        admin = await authenticate_admin(request, db)
        target = await db.members.find_one(
            {"user_id": user_id}, {"_id": 0, "user_id": 1, "email": 1, "entitlements": 1, "game_test_unlock": 1})
        if not target:
            raise HTTPException(status_code=404, detail="Account not found")
        if await game_purchase_for(user_id):
            raise HTTPException(status_code=409, detail="This account already has a genuine Stripe payment for the Board Fundraising Game")
        existing_unlock = target.get("game_test_unlock") if isinstance(target.get("game_test_unlock"), dict) else {}
        if existing_unlock.get("active"):
            raise HTTPException(status_code=409, detail="This account is already unlocked for testing")
        now = datetime.now(timezone.utc).isoformat()
        unlock = {
            "active": True, "payment_status": "unlocked", "payment_source": "admin_test", "test_unlock": True,
            "test_unlocked_at": now,
            "test_unlocked_by": admin.get("user_id", ""), "test_unlocked_by_email": admin.get("email", ""),
        }
        await db.members.update_one(
            {"user_id": user_id},
            {"$addToSet": {"entitlements": GAME_ENTITLEMENT},
             "$set": {"game_test_unlock": unlock, "updated_at": now}})
        return {"status": "unlocked", "unlocked_at": now, "access_source": "Admin Test"}

    @router.post("/admin/game/customers/{user_id}/revoke-testing")
    async def revoke_testing_access(user_id: str, request: Request):
        await authenticate_admin(request, db)
        target = await db.members.find_one(
            {"user_id": user_id}, {"_id": 0, "user_id": 1, "game_test_unlock": 1})
        if not target:
            raise HTTPException(status_code=404, detail="Account not found")
        unlock = target.get("game_test_unlock") if isinstance(target.get("game_test_unlock"), dict) else {}
        if not unlock.get("active"):
            raise HTTPException(status_code=409, detail="This account does not have testing access")
        now = datetime.now(timezone.utc).isoformat()
        update = {"$set": {"game_test_unlock.active": False, "game_test_unlock.revoked_at": now, "updated_at": now}}
        if not await game_purchase_for(user_id):
            update["$pull"] = {"entitlements": GAME_ENTITLEMENT}
        await db.members.update_one({"user_id": user_id}, update)
        return {"status": "revoked"}

    return router
