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
from platform_communications import notify_homepage_lead, public_origin

GAME_ENTITLEMENT = "board_fundraising_game"

DEFAULT_CONTENT = {
    "content_version": 2,
    "hero_badge": "THE BOARD FUNDRAISING GAME",
    "headline": "GET YOUR BOARD WORKING WITH YOU TO RAISE MONEY",
    "subheadline": "Fundraising should not depend entirely on you.",
    "hero_explanation": "The Board Fundraising Game helps you and your board build the fundraising strategy your organization will use to consistently find potential funders, attract them, build relationships and raise money.",
    "agent_intro": "Your Board Fundraising Agent will guide you and your board through five practical questions:",
    "agent_questions": [
        "Who do you think can help fund your organization?",
        "Where can you find them?",
        "How can you attract them and get them interested in your organization?",
        "What should you ask them for, and how much should you ask?",
        "How do you move them from first discovering your organization to eventually funding it?",
    ],
    "agent_followup": "Then your board members will share their own ideas. You will bring everyone's thinking together, agree on the strongest fundraising strategy and decide how each person will participate.",
    "start_supporting": "It starts with you. Answer five questions about how you think your organization can reach this fundraising goal. Then invite your board to bring their ideas into the strategy.",
    "intro_heading": "Fundraising Is Not A One-Person Job",
    "intro_paragraphs": [
        "You start with one audience you believe can help fund your work and share your thinking in your own words.",
        "Your board members each do the same. The Board Fundraising Game brings those perspectives into one meeting where you decide what to pursue together.",
        "Your Board Fundraising Agent guides the process and turns the board's adopted decisions into a strategy with a clear role for each participant.",
    ],
    "goal_label": "How Much Does Your Organization Want To Raise?",
    "goal_placeholder": "500,000",
    "cta_label": "START MY BOARD FUNDRAISING GAME",
    "video_enabled": True,
    "video_label": "Watch",
    "video_heading": "See How The Board Fundraising Game Works",
    "video_text": "See exactly how you and your board move from a fundraising goal to an adopted, practical fundraising plan and clear participation choices.",
    "stages_label": "How It Works",
    "stages_heading": "From Your Ideas To A Fundraising System Built With Your Board",
    "stages": [
        {"key": "start", "number": "1", "title": "Start The Game Yourself", "items": [
            "Choose your fundraising goal and answer five practical questions about how you think your organization can raise the money.",
            "Your answers are saved exactly as you give them. Your thinking comes into the game before you ask anybody else to participate.",
        ]},
        {"key": "invite", "number": "2", "title": "Invite Your Board", "items": [
            "Upgrade and invite each board member to answer the same five questions independently and say how they would be comfortable participating.",
            "Bring the thinking, relationships and perspectives of your board into the strategy.",
        ]},
        {"key": "group", "number": "3", "title": "Play The Group Board Fundraising Game", "items": [
            "Bring everyone's proposed audiences and ideas into your board meeting.",
            "Decide which opportunities are strongest, where to find and attract funders, what to ask and how to build the relationship toward giving.",
            "Your board makes the decisions together.",
        ]},
        {"key": "execute", "number": "4", "title": "Build And Execute Your Fundraising Strategy", "items": [
            "Your Board Fundraising Agent turns the board's adopted decisions into your organization's fundraising strategy.",
            "Each member receives a clear role based on what the strategy needs and how they said they can participate, with a Board Fundraising Portfolio and execution support.",
        ]},
    ],
    "stages_cta_label": "START MY BOARD FUNDRAISING GAME",
    "outcomes_label": "Outcomes",
    "outcomes_heading": "What You And Your Board Build Together",
    "outcomes": [
        {"key": "strategy", "heading": "A Fundraising Strategy Built With Your Board", "paragraphs": [
            "Know who you are trying to raise money from, where to find them, how to attract them, what to ask for and the process for turning relationships into funding.",
        ]},
        {"key": "people", "heading": "More People Helping You Build The Fundraising System", "paragraphs": [
            "Fundraising no longer sits entirely with the Executive Director. Your board contributes ideas, relationships and execution capacity.",
        ]},
        {"key": "roles", "heading": "A Clear Role For Every Board Member", "paragraphs": [
            "Board members tell you how they can participate, help build the strategy and receive responsibilities connected to it.",
        ]},
        {"key": "system", "heading": "A Fundraising System You Can Keep Building", "paragraphs": [
            "Create a repeatable process for finding potential funders, attracting them, developing relationships, making the right ask, following up and stewarding them.",
        ]},
    ],
    "benefits_heading": "What Your Organization Walks Away With",
    "benefits": [
        "Build a fundraising strategy with your entire board",
        "Teach board members how fundraising actually works",
        "Capture the knowledge, relationships and ideas already sitting around your board table",
        "Identify the best fundraising audiences and opportunities",
        "Decide how the organization will raise money",
        "Use your present fundraising experience while adding stronger ideas from the Board",
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
    "closing_text": "Start with your fundraising goal and five questions. Your own ideas are the beginning of a strategy you and your board can build together.",
    "closing_cta_label": "START MY BOARD FUNDRAISING GAME",
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
        "saved_supporting": "You have set your fundraising goal. Answer five questions in your own words to start your Board Fundraising Game.",
        "next_heading": "Start With Your Own Fundraising Ideas",
        "next_supporting": "Identify one audience, where to find them, how to attract them, what to ask and how to build a relationship toward giving. Your board will later answer the same five questions independently.",
        "invite_cta": "Play My Board Fundraising Game",
    },
    "upgrade_page": {
        "label": "YOUR IDEAS ARE SAVED",
        "heading": "You've Shared Your Fundraising Ideas. Now Let's Bring In Your Board.",
        "supporting": "That's your perspective. Upgrade to invite your board members to answer the same questions independently, bring everyone's ideas into the group game and build the strategy together.",
        "completed_areas": [
            "Who you believe can help fund your organization",
            "Where you believe you can find them",
            "How you believe you can attract them",
            "What you think you should ask for and how much",
            "How you think you can build a relationship toward giving",
        ],
        "more_people_statement": "The more people who play the game, the more ideas you have about who to raise money from, where to find them, how to attract them and how to raise money from them.",
        "goal_label": "Your Fundraising Goal",
        "video_label": "Watch",
        "video_heading": "See What Happens After You Unlock",
        "video_text": "See exactly what happens from the moment you unlock your Board Fundraising Game to the moment your board leaves with an adopted fundraising strategy, clear roles and the tools required to execute.",
        "process_label": "What Happens Next",
        "process_heading": "What Happens After You Unlock",
        "process_supporting": "From the moment you unlock your game, the platform leads you and your board through the entire process.",
        "process_steps": [
            {"heading": "1. Continue Your Part Of The Game", "paragraphs": [
                "Your five original answers are saved. Tell us how you would be comfortable participating and review your present fundraising circumstances."]},
            {"heading": "2. Tell Us What You Already Have", "paragraphs": [
                "Tell us about your present donor base, the businesses and grantors already giving to your organization, why they support you and how you presently raise money from them.",
                "Keep the present methods that already work available for the Board's decisions."]},
            {"heading": "3. Invite Your Board Members To Play", "paragraphs": [
                "Each board member receives their own secure Individual Game link.",
                "Each board member answers the same five questions about one audience and says how they would be comfortable participating."]},
            {"heading": "4. Play Together During Your Next Board Meeting", "paragraphs": [
                "During your next board meeting, you and your board review the ideas contributed by everyone across six focused decisions: audiences and reasons, where to find them, how to attract them, what to ask them to fund and how much to ask, the fundraising process and each Board Member's role.",
                "Your board discusses the attributed ideas, compares them with your present fundraising circumstances and prioritizes the strongest direction together."]},
            {"heading": "5. Generate The Complete Fundraising Plan", "paragraphs": [
                "The platform presents the Board's own decisions as a practical plan with an executive summary, funding audiences and reasons, where to find them, how to attract them, what to ask for, the fundraising process and Board roles.",
                "Your present donors, business supporters, grantors and current fundraising methods are preserved wherever the Board chooses to continue using them."]},
            {"heading": "6. Adopt The Strategy And Start Raising Money", "paragraphs": [
                "You and your board review the final fundraising strategy, make the final decisions and adopt it as your organization's working fundraising strategy.",
                "After the meeting, every board member receives the adopted strategy, their personal Board Fundraising Portfolio and an Executive Assistant that recommends and creates the specific materials they need when they are ready to use them."]},
        ],
        "repeat_heading": "Ready To Bring Your Board Into The Process?",
        "repeat_supporting": "Unlock your Board Fundraising Game and start preparing your board to build, adopt and execute the fundraising strategy your organization needs.",
        "repeat_cta": "Invite My Board And Continue — $497",
        "intro_heading": "Stop Carrying Fundraising Alone",
        "intro_paragraphs": [
            "Your board is less likely to take ownership of fundraising when they had no role in creating the strategy they are being asked to execute.",
            "The Board Fundraising Game brings them into the process. Your board learns how fundraising works, contributes ideas, makes collective decisions, adopts the strategy and chooses how each member will participate in execution.",
        ],
        "outcomes_label": "Outcomes",
        "outcomes_heading": "What Your Organization Walks Away With",
        "outcomes": [
            {"heading": "A Clear Fundraising Strategy", "paragraphs": ["Know the audiences your board chooses, where to find and attract them, what to ask and how to build the relationships that lead to funding."]},
            {"heading": "Your Present Fundraising Strengths Preserved", "paragraphs": ["Keep the present donors, business supporters, grantors and fundraising methods the Board wants to continue using."]},
            {"heading": "More Ideas From Your Entire Board", "paragraphs": ["The more people who play the game, the more ideas you have about who to raise money from, where to find them, how to attract them and how to raise money from them."]},
            {"heading": "A Clear Role For Every Board Member", "paragraphs": ["Every Board Member chooses how they want to help raise money."]},
            {"heading": "On-Demand Execution Support", "paragraphs": ["Each Board Member's Executive Assistant recommends useful materials from the role in their approved Portfolio, creates only what they choose to use and answers questions as they execute."]},
        ],
        "features_heading": "Everything You Need To Run Your Board Fundraising Game",
        "features": [
            {"heading": "Individual Board Member Games", "description": "Every board member receives their own secure link to learn, contribute ideas and choose how they want to participate."},
            {"heading": "Group Review Game", "description": "Bring everyone's ideas together and let the board collectively prioritize the strongest fundraising opportunities."},
            {"heading": "Board-Prioritized Fundraising Strategy", "description": "Turn the board's decisions into a complete fundraising strategy."},
            {"heading": "Strategy Review and Adoption", "description": "Review the strategy together, capture board decisions and adopt the final plan."},
            {"heading": "Board Fundraising Portfolios", "description": "Give every board member a clear role in helping the organization raise money."},
            {"heading": "Personal Executive Assistants", "description": "Recommend and create the scripts, templates, checklists and resources each Board Member needs for the role they accepted."},
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
        "payment_includes": "Includes the complete Board Fundraising Game, a Clear Fundraising Strategy, Fun Filled Moment With Board Members, Board Fundraising Portfolios and a personal Executive Assistant for each Board Member.",
        "payment_cta": "Invite My Board And Continue — $497",
    },
}

ORG_FIELDS = ["name", "website", "org_type", "location", "mission", "who_served"]
GOAL_FIELDS = ["amount", "deadline", "purpose", "why_now"]
USER_FIELDS = ["full_name", "job_title", "email"]
SITUATION_SECTIONS = ["financial", "activities", "team", "donors", "corporate", "grantors", "technology", "materials", "reflections", "current_reality", "participation"]

GAME_AREAS = [
    {"key": "final_strategy", "name": "Final Fundraising Strategy", "description": "The strategy your board reviews, refines and adopts."},
    {"key": "portfolios", "name": "Board Portfolios", "description": "Each board member's role in executing the strategy."},
    {"key": "executive_assistants", "name": "Board Executive Assistants", "description": "Role-specific recommendations and on-demand materials that help each Board Member execute."},
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
    homepage_capture: bool = False


class GameBrandingUpdate(BaseModel):
    logo_data: str = Field(default="", max_length=750000)


class ClaimPayload(BaseModel):
    session_id: str = ""
    origin_url: str = ""


class SituationUpdate(BaseModel):
    sections: dict = Field(default_factory=dict)
    current_step: int = Field(default=0, ge=0, le=20)


class FreeGameAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=6000)


FREE_QUESTION_COUNT = 5


def situation_is_complete(doc: dict) -> bool:
    if not doc or not doc.get("completed") or int(doc.get("current_step") or 0) < 3:
        return False
    sections = doc.get("sections") or {}
    return bool((sections.get("current_reality") or {}).get("reviewed"))


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

    @router.get("/game/free")
    async def free_game(request: Request):
        member = await authenticate_member(request, db)
        profile = await get_profile_doc(member["user_id"])
        if not profile.get("profile_completed"):
            raise HTTPException(status_code=409, detail="Choose your fundraising goal and save your organization first")
        saved = await db.game_free_responses.find_one({"user_id": member["user_id"]}, {"_id": 0}) or {}
        answers = saved.get("answers") or {}
        first_unanswered = next((index for index in range(1, FREE_QUESTION_COUNT + 1)
                                 if not str(answers.get(str(index), "")).strip()), FREE_QUESTION_COUNT + 1)
        return {
            "answers": answers, "next_question": first_unanswered, "complete": first_unanswered > FREE_QUESTION_COUNT,
            "organization_name": (profile.get("organization") or {}).get("name", ""),
            "goal_amount": (profile.get("goal") or {}).get("amount", 0),
            "unlocked": GAME_ENTITLEMENT in member.get("entitlements", []),
        }

    @router.put("/game/free/{question_number}")
    async def save_free_game_answer(question_number: int, payload: FreeGameAnswer, request: Request):
        member = await authenticate_member(request, db)
        profile = await get_profile_doc(member["user_id"])
        if not profile.get("profile_completed"):
            raise HTTPException(status_code=409, detail="Choose your fundraising goal and save your organization first")
        if not 1 <= question_number <= FREE_QUESTION_COUNT or not payload.answer.strip():
            raise HTTPException(status_code=422, detail="Answer this question in your own words")
        saved = await db.game_free_responses.find_one({"user_id": member["user_id"]}, {"_id": 0}) or {}
        answers = saved.get("answers") or {}
        if any(not str(answers.get(str(index), "")).strip() for index in range(1, question_number)):
            raise HTTPException(status_code=409, detail="Please answer the earlier question first")
        now = datetime.now(timezone.utc).isoformat()
        # Keep the original response byte-for-byte as a string. No AI, scoring or rewriting runs here.
        await db.game_free_responses.update_one(
            {"user_id": member["user_id"]},
            {"$set": {f"answers.{question_number}": payload.answer, "updated_at": now},
             "$setOnInsert": {"user_id": member["user_id"], "created_at": now}}, upsert=True,
        )
        return {"next_question": question_number + 1, "complete": question_number == FREE_QUESTION_COUNT}

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
        if payload.homepage_capture and completed:
            try:
                root = public_origin()
                await notify_homepage_lead(
                    db,
                    pathway="board-fundraising-game",
                    source_id=member["user_id"],
                    name=primary_user.get("full_name") or member.get("first_name", ""),
                    email=member.get("email", ""),
                    organization=organization.get("name", ""),
                    continue_url=f"{root}/login?next=%2Fgame%2Fquestions",
                    details={"fundraising_goal": f"${int(goal.get('amount') or 0):,}"},
                )
            except Exception:
                pass
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
        if not doc:
            return {"sections": {}, "current_step": 0, "completed": False}
        return {**doc, "completed": situation_is_complete(doc)}

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
        situation = await db.game_situations.find_one({"user_id": member["user_id"]}, {"_id": 0}) or {}
        primary = await db.game_board_members.find_one(
            {"user_id": member["user_id"], "is_primary": True, "removed": {"$ne": True}}, {"_id": 0, "member_id": 1})
        audience_complete = bool(primary and await db.game_audience_responses.find_one(
            {"board_member_id": primary["member_id"], "completed": True}, {"_id": 0, "response_id": 1}))
        candidate = {**situation, "completed": True}
        if not audience_complete or not situation_is_complete(candidate):
            raise HTTPException(
                status_code=409,
                detail="Complete your audience game and the present donor, business and grantor review before finishing.",
            )
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
        situation = await db.game_situations.find_one({"user_id": member["user_id"]}, {"_id": 0}) or {}
        situation_completed = situation_is_complete(situation)
        primary = await db.game_board_members.find_one(
            {"user_id": member["user_id"], "is_primary": True, "removed": {"$ne": True}},
            {"_id": 0, "member_id": 1})
        individual_game_completed = False
        night = await db.game_nights.find_one(
            {"user_id": member["user_id"]},
            {"_id": 0, "meeting_date": 1, "funding_deadline": 1, "start_time": 1, "timezone": 1},
        ) or {}
        game_night_ready = bool(night.get("meeting_date") and night.get("start_time") and night.get("funding_deadline"))
        board_participant_count = await db.game_board_members.count_documents({
            "user_id": member["user_id"], "removed": {"$ne": True}, "is_primary": {"$ne": True},
        })
        if primary:
            individual_game_completed = bool(await db.game_audience_responses.find_one(
                {"board_member_id": primary["member_id"], "completed": True}, {"_id": 0, "response_id": 1}))
        return {
            "first_name": member.get("first_name", ""),
            "organization": profile.get("organization", {}),
            "goal": profile.get("goal", {}),
            "situation_completed": situation_completed,
            "individual_game_completed": individual_game_completed,
            "game_night_ready": game_night_ready,
            "game_night": night,
            "board_participant_count": board_participant_count,
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
