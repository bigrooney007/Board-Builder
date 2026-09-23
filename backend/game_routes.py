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
    "headline": "Get Your Board Members To Start Raising Money and Work With You To Build Your Organization's Fundraising System",
    "subheadline": "Play the Board Fundraising Game with your board, create your fundraising strategy, equip your board members to start raising money, and guarantee your organization's financial sustainability by building your organization's fundraising system with your board.",
    "intro_heading": "Those That Plan Together, Execute Together.",
    "intro_paragraphs": [
        "The first step to get your board to start raising money and building your organization's fundraising system with you is by creating your organization's fundraising strategy with them.",
        "I mean a clear strategy that identifies the exact type of people, businesses and grantors with the strongest reason to fund your mission, where to find them, how to attract them consistently, and the exact process to raise money from them.",
        "The Board Fundraising Game helps you create this strategy with your board, equip your board to execute the strategy individually and work with you to build the system that will drive the strategy at scale so as to raise money exponentially for your organization.",
    ],
    "goal_label": "How Much Does Your Organization Want To Raise?",
    "goal_placeholder": "500,000",
    "cta_label": "Start My Board Fundraising Game",
    "video_enabled": True,
    "video_label": "Watch",
    "video_heading": "See How The Board Fundraising Game Works",
    "video_text": "See exactly how you and your board move from a fundraising goal to an adopted fundraising strategy, clear board roles and the tools required to execute.",
    "stages_label": "How It Works",
    "stages_heading": "One Game. One Fundraising Goal. Your Entire Board Behind It.",
    "stages": [
        {"key": "before", "number": "1", "title": "Before Game Night", "items": [
            "Each board member receives their own Individual Game link before your next board meeting.",
            "They learn how fundraising works, contribute ideas for reaching your fundraising goal and choose how they want to participate.",
            "Everyone arrives at the meeting already thinking seriously about how your organization can raise the money.",
        ]},
        {"key": "during", "number": "2", "title": "During Game Night", "items": [
            "Your board turns individual ideas into collective decisions.",
            "Everyone reviews the ideas contributed by the board and prioritizes the strongest opportunities.",
            "The platform turns those priorities into your fundraising strategy.",
            "Your board reviews it, makes the final decisions and adopts the strategy together.",
        ]},
        {"key": "after", "number": "3", "title": "After Game Night", "items": [
            "Your organization leaves with an adopted fundraising strategy.",
            "Each board member receives a personal Board Fundraising Portfolio showing how they will help build the fundraising system and raise money.",
            "They also receive the scripts, templates, checklists and resources they need to execute their role.",
        ]},
    ],
    "stages_cta_label": "Launch My Board Fundraising Game",
    "outcomes_label": "Outcomes",
    "outcomes_heading": "Your Board Meeting Ends With More Than A Conversation",
    "outcomes": [
        {"key": "strategy", "heading": "1. A Clear Fundraising Strategy", "paragraphs": [
            "Know who you will raise money from, where to find them, how to attract them, how you will raise money from them, and what team, technology, materials, timeline and budget you need to execute.",
        ]},
        {"key": "knowledge", "heading": "2. A Board That Knows How To Raise Money", "paragraphs": [
            "Your board learns how fundraising works by actually helping build the strategy.",
            "Instead of simply asking board members to fundraise, you equip them to do it.",
        ]},
        {"key": "system", "heading": "3. A Fundraising System That Does Not Depend Entirely On You", "paragraphs": [
            "Build a system for consistently finding potential funders, attracting them, building relationships, asking for support, following up and stewarding them.",
            "Fundraising becomes an organizational responsibility instead of yours alone.",
        ]},
        {"key": "roles", "heading": "4. A Clear Role For Every Board Member", "paragraphs": [
            "Each board member chooses how they want to help build the fundraising system and how they want to help raise money.",
            "Then they receive their personal role and the tools required to execute it.",
        ]},
        {"key": "trust", "heading": "5. A Board That Trusts Your Leadership", "paragraphs": [
            "You are not simply asking your board to do more.",
            "You are leading them through a process that teaches them, involves them in decisions and equips them to contribute.",
        ]},
    ],
    "benefits_heading": "What Your Organization Walks Away With",
    "benefits": [
        "Build a fundraising strategy with your entire board",
        "Teach board members how fundraising actually works",
        "Capture the knowledge, relationships and ideas already sitting around your board table",
        "Identify the best fundraising audiences and opportunities",
        "Decide how the organization will raise money",
        "Build the fundraising system required to execute at scale",
        "Give every board member a clear role",
        "Equip board members with the tools they need to execute",
        "Turn the next board meeting into a working fundraising strategy session",
    ],
    "pricing_heading": "Unlock Your Board Fundraising Game",
    "price_display": "$497",
    "price_note": "One-time payment. One organization. Your entire board plays.",
    "faqs_label": "Questions",
    "faqs_heading": "Frequently Asked Questions",
    "faqs": [
        {"q": "What exactly is the Board Fundraising Game?", "a": "It is a structured experience that brings your board together to build, adopt and prepare to execute the fundraising strategy your organization needs to raise its fundraising goal."},
        {"q": "Is this a subscription?", "a": "No. The Board Fundraising Game is a one-time payment for your organization."},
        {"q": "Do my board members need accounts?", "a": "No. You set up the game and your board members receive simple links to participate."},
        {"q": "How long does Game Night take?", "a": "Most boards complete Game Night inside a single board meeting. Preparation happens individually before the meeting."},
        {"q": "What happens after we play?", "a": "Your organization leaves with its fundraising strategy, and every board member receives their execution role and the materials to act on it."},
    ],
    "testimonials_heading": "What Nonprofit Leaders Say",
    "closing_heading": "Ready To Stop Carrying Fundraising Alone?",
    "closing_text": "Bring your board together around one fundraising goal and leave with the strategy, board roles and fundraising system required to pursue it together.",
    "closing_cta_label": "Start My Board Fundraising Game",
    "footer_recruit_label": "Recruit Board Members With Fundraising Experience",
    "footer_recruit_url": "/recruit",
    "profile_flow": {
        "heading": "Create Your Board Fundraising Game",
        "supporting": "Tell us about your organization and the fundraising goal you want to bring your board together to achieve.",
        "step1_heading": "Tell Us About Your Organization",
        "step2_heading": "What Are You Bringing Your Board Together To Achieve?",
        "step3_heading": "Who Is Leading The Board Fundraising Game?",
        "review_heading": "Review Your Fundraising Game",
        "review_supporting": "Make sure everything is correct before saving your Fundraising Game Profile.",
        "save_button": "Save My Fundraising Game Profile",
        "saved_heading": "Your Board Fundraising Game Is Ready",
        "saved_supporting": "You have set your fundraising goal. Now play the game yourself and create the fundraising strategy your organization will use to reach it.",
        "next_heading": "Play The Game And Create Your Fundraising Strategy",
        "next_supporting": "Answer eight guided questions across four strategic areas. By the end, you will have created the thinking behind your organization's fundraising strategy.",
        "invite_cta": "Play My Board Fundraising Game",
    },
    "upgrade_page": {
        "label": "YOUR FUNDRAISING STRATEGY IS READY",
        "heading": "Bring Your Board Into The Game",
        "supporting": "You have completed your game and created the thinking your fundraising strategy will be built around. Unlock the full Board Fundraising Game to see your strategy, invite your board members and bring everyone's ideas together during your next board meeting.",
        "completed_areas": [
            "The exact type of people, businesses and grantors meant to fund your mission or with the greatest reason to fund your organization",
            "Where to consistently find potential funders",
            "How to attract their attention",
            "The exact process to raise money exponentially for your organization",
        ],
        "more_people_statement": "The more the people that play the game, the more ideas you have on how to raise money and the more support you have when raising money and building the system that drives the strategy.",
        "goal_label": "Your Fundraising Goal",
        "video_label": "Watch",
        "video_heading": "See What Happens After You Unlock",
        "video_text": "See exactly what happens from the moment you unlock your Board Fundraising Game to the moment your board leaves with an adopted fundraising strategy, clear roles and the tools required to execute.",
        "process_label": "What Happens Next",
        "process_heading": "What Happens After You Unlock",
        "process_supporting": "From the moment you unlock your game, the platform leads you and your board through the entire process.",
        "process_steps": [
            {"heading": "1. See The Fundraising Strategy You Just Created", "paragraphs": [
                "Your answers are turned into your fundraising strategy around the goal your organization wants to reach.",
                "You can now see the exact type of people, businesses and grantors meant to fund your mission, where to consistently find them, how to attract their attention and the exact process to raise money exponentially for your organization."]},
            {"heading": "2. Tell Us What You Already Have", "paragraphs": [
                "To build the complete fundraising system around your strategy, tell us about your present donor base, the businesses and grantors already giving to your organization, your fundraising team and the resources you already use.",
                "You will also tell us how you want to be involved in building and managing the fundraising system and how you want to be involved in raising money."]},
            {"heading": "3. Invite Your Board Members To Play", "paragraphs": [
                "Each board member receives their own secure Individual Game link.",
                "They answer the same eight guided questions you answered, learn how fundraising works while playing the game, contribute their ideas and tell us how they want to be involved in building and managing the fundraising system and raising money."]},
            {"heading": "4. Play Together During Your Next Board Meeting", "paragraphs": [
                "During your next board meeting, you and your board review the ideas contributed by everyone across the four areas that drive your fundraising strategy.",
                "Your board prioritizes the strongest ideas together. Because the Group Game is now focused on only four areas, the game itself can be completed in about 10 minutes."]},
            {"heading": "5. Build The Complete Fundraising System Around The Strategy", "paragraphs": [
                "The platform uses your fundraising strategy, your organization's present reality, your fundraising goal, your deadline and your board's decisions to identify the people, technology, materials, resources and execution plan needed to execute the strategy.",
                "Your board does not have to manually design every part of the fundraising system. The system is built around the strategy your board has already agreed on."]},
            {"heading": "6. Adopt The Strategy And Start Executing", "paragraphs": [
                "You and your board review the final fundraising strategy, make the final decisions and adopt it as your organization's working fundraising strategy.",
                "After the meeting, every board member receives the adopted strategy, their personal Board Fundraising Portfolio and the personalized scripts, templates, checklists and execution materials they need to perform the role they agreed to play."]},
        ],
        "repeat_heading": "Ready To Bring Your Board Into The Process?",
        "repeat_supporting": "Unlock your Board Fundraising Game and start preparing your board to build, adopt and execute the fundraising strategy your organization needs.",
        "repeat_cta": "Unlock My Fundraising Strategy + Board Fundraising Game — $497",
        "intro_heading": "Stop Carrying Fundraising Alone",
        "intro_paragraphs": [
            "Your board is less likely to take ownership of fundraising when they had no role in creating the strategy they are being asked to execute.",
            "The Board Fundraising Game brings them into the process. Your board learns how fundraising works, contributes ideas, makes collective decisions, adopts the strategy and chooses how each member will participate in execution.",
        ],
        "outcomes_label": "Outcomes",
        "outcomes_heading": "What Your Organization Walks Away With",
        "outcomes": [
            {"heading": "A Clear Fundraising Strategy", "paragraphs": ["Know the exact type of people, businesses and grantors meant to fund your mission, where to find them, how to attract them and the exact process to raise money exponentially for your organization."]},
            {"heading": "A Fundraising System Built Around The Strategy", "paragraphs": ["Know the people, technology, materials, resources, timeline and execution structure needed to put the strategy to work."]},
            {"heading": "More Ideas From Your Entire Board", "paragraphs": ["The more the people that play the game, the more ideas you have on how to raise money and the more support you have when raising money and building the system that drives the strategy."]},
            {"heading": "A Clear Role For Every Board Member", "paragraphs": ["Every board member chooses how they want to help build and manage the fundraising system and how they want to help raise money."]},
            {"heading": "The Tools To Execute", "paragraphs": ["Board members receive their Board Fundraising Portfolio and personalized scripts, templates, checklists and execution materials based on the role they agreed to perform."]},
        ],
        "features_heading": "Everything You Need To Run Your Board Fundraising Game",
        "features": [
            {"heading": "Individual Board Member Games", "description": "Every board member receives their own secure link to learn, contribute ideas and choose how they want to participate."},
            {"heading": "Group Review Game", "description": "Bring everyone's ideas together and let the board collectively prioritize the strongest fundraising opportunities."},
            {"heading": "Board-Prioritized Fundraising Strategy", "description": "Turn the board's decisions into a complete fundraising strategy."},
            {"heading": "Strategy Review and Adoption", "description": "Review the strategy together, capture board decisions and adopt the final plan."},
            {"heading": "Board Fundraising Portfolios", "description": "Give every board member a clear role in building the fundraising system and raising money."},
            {"heading": "Personalized Execution Toolkits", "description": "Equip board members with the scripts, templates, checklists and resources required to perform their role."},
            {"heading": "Game Night Host Tools", "description": "Use your call script, facilitation guide and preparation checklist to confidently lead the process."},
        ],
        "steps_heading": "What Happens After You Unlock?",
        "steps": [
            {"heading": "Complete Your Game Setup", "description": "Watch the short tutorial and tell us about your organization's current fundraising situation."},
            {"heading": "Set Game Night", "description": "Choose your board meeting date and add the board members who will participate."},
            {"heading": "Invite Your Board", "description": "Every board member receives their own secure Individual Game link."},
            {"heading": "Bring Everyone Together", "description": "Run the Board Fundraising Game during your board meeting and leave with the strategy, board roles and tools required to execute."},
        ],
        "payment_heading": "Unlock Your Board Fundraising Game",
        "payment_price": "$497",
        "payment_onetime": "One-time payment",
        "payment_org_line": "One organization. Your entire board participates.",
        "payment_subscription_line": "No subscription.",
        "payment_includes": "Includes the complete Board Fundraising Game, a Clear Fundraising Strategy, Fun Filled Moment With Board Members, Board Fundraising Portfolios and personalized Execution Toolkits for each Board Member.",
        "payment_cta": "Unlock My Fundraising Strategy + Board Fundraising Game — $497",
    },
}

ORG_FIELDS = ["name", "website", "org_type", "location", "mission", "who_served"]
GOAL_FIELDS = ["amount", "deadline", "purpose", "why_now"]
USER_FIELDS = ["full_name", "job_title", "email"]
SITUATION_SECTIONS = ["financial", "activities", "team", "donors", "corporate", "grantors", "technology", "materials", "reflections", "current_reality", "participation"]

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


class GameBrandingUpdate(BaseModel):
    logo_data: str = Field(default="", max_length=750000)


class ClaimPayload(BaseModel):
    session_id: str = ""
    origin_url: str = ""


class SituationUpdate(BaseModel):
    sections: dict = Field(default_factory=dict)
    current_step: int = Field(default=0, ge=0, le=20)


def create_game_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def get_content() -> dict:
        # Public Game homepage content has one source of truth: the versioned
        # DEFAULT_CONTENT in this file. Database-stored homepage overrides made
        # deployments non-deterministic, so they are intentionally not applied.
        return DEFAULT_CONTENT

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
        raise HTTPException(
            status_code=409,
            detail="Board Fundraising Game public-page content is version-controlled in source and cannot be overridden from the database.",
        )

    @router.get("/game/profile")
    async def game_profile(request: Request):
        member = await authenticate_member(request, db)
        profile = await get_profile_doc(member["user_id"])
        return {
            "profile": profile,
            "unlocked": GAME_ENTITLEMENT in member.get("entitlements", []),
            "member": {"first_name": member.get("first_name", ""), "last_name": member.get("last_name", ""), "email": member.get("email", "")},
        }

    @router.get("/game/branding")
    async def game_branding(request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        profile = await get_profile_doc(member["user_id"])
        return {"branding": profile.get("branding") or {}}

    @router.put("/game/branding")
    async def save_game_branding(payload: GameBrandingUpdate, request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        logo = payload.logo_data.strip()
        if logo and not logo.startswith("data:image/"):
            raise HTTPException(status_code=422, detail="Choose a valid image file for your organization logo.")
        if len(logo) > 750000:
            raise HTTPException(status_code=413, detail="Logo is too large. Use an image under 500KB.")
        await db.game_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"branding.logo_data": logo, "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        return {"branding": {"logo_data": logo}}

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
            access_block = (f"<p><strong>Account email:</strong> {html.escape(member['email'])}</p>"
                            f"<p><a href='{origin}/login?next=%2Fgame%2Fdashboard'>Log in to your Board Fundraising Game</a></p>"
                            f"<p>If you forget your password, use <a href='{origin}/forgot-password'>Forgot Password</a>.</p>"
                            f"<p>Save this email so you can return to your work later.</p>") if origin else ""
            try:
                resend.api_key = os.environ["RESEND_API_KEY"]
                await resend.Emails.send_async({
                    "from": os.environ["NONPROFIT_SENDER"], "to": [member["email"]],
                    "subject": "Welcome to Your Board Fundraising Game",
                    "html": f"<div style='max-width:560px;margin:auto;font-family:Arial,sans-serif;color:#000;'>"
                            f"<h2>Welcome to Your Board Fundraising Game</h2>"
                            f"<p>Hello {html.escape(member.get('first_name', ''))},</p>"
                            f"<p>Your Board Fundraising Game is unlocked. Your tutorial video explains how to use the platform, prepare your board and run the game.</p>"
                            f"{video_block}{dashboard_link}{access_block}"
                            f"<p>Next step: play your Board Fundraising Game. When you finish, continue into your dashboard.</p></div>",
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
        primary = await db.game_board_members.find_one(
            {"user_id": member["user_id"], "is_primary": True, "removed": {"$ne": True}},
            {"_id": 0, "member_id": 1})
        individual_game_completed = False
        night = await db.game_nights.find_one(
            {"user_id": member["user_id"]},
            {"_id": 0, "meeting_date": 1, "funding_deadline": 1, "start_time": 1, "timezone": 1},
        ) or {}
        game_night_ready = bool(night.get("meeting_date") and night.get("funding_deadline") and night.get("start_time") and night.get("timezone"))
        if primary:
            rows = await db.game_section_responses.find(
                {"board_member_id": primary["member_id"], "section_id": {"$in": [1, 2, 3, 4]}},
                {"_id": 0, "section_id": 1, "fine_tuning.completed": 1}).to_list(10)
            completed_sections = {
                row.get("section_id") for row in rows
                if (row.get("fine_tuning") or {}).get("completed")
            }
            individual_game_completed = all(section_id in completed_sections for section_id in [1, 2, 3, 4])
        return {
            "first_name": member.get("first_name", ""),
            "organization": profile.get("organization", {}),
            "goal": profile.get("goal", {}),
            "situation_completed": situation_completed,
            "individual_game_completed": individual_game_completed,
            "game_night_ready": game_night_ready,
            "game_night": night,
            "status": "set_up_board" if situation_completed and individual_game_completed else "complete_setup",
            "areas": [{**area, "locked": True} for area in GAME_AREAS],
        }

    @router.get("/admin/game/customers")
    async def game_customers(request: Request):
        await authenticate_admin(request, db)
        rows = []
        profiles = await db.game_profiles.find(
            {"internal_preview": {"$ne": True}}, {"_id": 0}
        ).sort("updated_at", -1).to_list(300)
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
