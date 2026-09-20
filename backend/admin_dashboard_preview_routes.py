"""Admin-only launchers for the four real customer product dashboards."""
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from auth_service import authenticate_admin
from member_auth import create_member_token, set_member_cookie


PRODUCTS = {
    "recruitment": {
        "entitlements": ["recruitment_self_guided", "recruitment_selection_onboarding"],
        "dashboard_path": "/app/board-recruitment",
    },
    "board-fundraising-game": {
        "entitlements": ["board_fundraising_game"],
        "dashboard_path": "/game/dashboard",
    },
    "strategic-planning": {
        "entitlements": [],
        "dashboard_path": "/strategic-planning/dashboard",
        "purchase_source": "strategic_planning_497",
    },
    "board-recommitment": {
        "entitlements": ["reactivation_self_guided"],
        "dashboard_path": "/board-recommitment/dashboard",
        "purchase_source": "board_recommitment_497",
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_admin_dashboard_preview_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/admin/dashboard-preview")

    async def preview_member(admin: dict) -> dict:
        fingerprint = hashlib.sha256(admin["user_id"].encode("utf-8")).hexdigest()[:16]
        user_id = f"admin-dashboard-preview-{fingerprint}"
        email = f"dashboard-preview-{fingerprint}@nonprofitboardbuilder.internal"
        now = now_iso()
        await db.members.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "email": email,
                    "first_name": "Rooney",
                    "last_name": "Admin Preview",
                    "internal_admin_entitlement": True,
                    "internal_dashboard_preview": True,
                    "review_mode": True,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "password_hash": "",
                    "lead_ids": [],
                    "stripe_customer_id": "",
                    "entitlements": [],
                    "created_at": now,
                },
            },
            upsert=True,
        )
        return await db.members.find_one({"user_id": user_id}, {"_id": 0})

    async def seed_guided_product(member: dict, product: str, config: dict) -> str:
        now = now_iso()
        session_id = f"admin_preview_{product.replace('-', '_')}_{member['user_id'][-16:]}"
        lead_token = f"admin-preview-{product}-{member['user_id'][-16:]}"
        await db.guided_product_leads.update_one(
            {"token": lead_token},
            {"$set": {
                "token": lead_token, "product": product, "name": "Rooney Akpesiri",
                "email": member["email"], "organization": "Nonprofit Board Builder Preview Organization",
                "board_count": 5, "internal_preview": True, "followup_status": "converted", "updated_at": now,
            }, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "session_id": session_id, "status": "completed", "payment_status": "paid",
                "offer_source": "internal_admin_preview", "purchase_source": config["purchase_source"],
                "guided_lead_token": lead_token, "lead_email": member["email"],
                "claimed_by_user_id": member["user_id"], "amount": 0,
                "internal_preview": True, "updated_at": now,
            }, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        answers = {
            "mission": "Build the boards and systems nonprofit organizations need to grow and raise money.",
            "goals": "Strengthen the board, clarify direction, and build sustainable organizational systems.",
        }
        if product == "strategic-planning":
            answers.update({
                "objectives": "Create clear priorities, ownership, and measurable execution plans.",
                "programs": "Board Recruitment\nBoard Fundraising Game\nStrategic Planning\nBoard Recommitment",
                "team_building": "Build leadership capacity around each strategic priority.",
                "operations": "Strengthen repeatable processes and accountability.",
                "marketing": "Build consistent visibility with nonprofit leaders.",
                "partnerships": "Develop mission-aligned nonprofit and funding partnerships.",
                "fundraising": "Build a clear fundraising strategy and supporting system.",
                "technology": "Use the platform to coordinate planning and execution.",
                "budget": "Build a costed plan for full execution.",
                "priorities": "Board capacity, fundraising sustainability, and delegated leadership.",
                "action_planning": "Assign owners, timelines, resources, and review points.",
                "next_meeting": "Next scheduled board meeting",
            })
        await db.guided_product_intakes.update_one(
            {"session_id": session_id},
            {"$set": {"session_id": session_id, "product": product, "answers": answers,
                      "internal_preview": True, "updated_at": now},
             "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        if product == "strategic-planning":
            project_id = f"admin-preview-{member['user_id'][-16:]}"
            await db.sp_projects.update_one(
                {"guided_session_id": session_id},
                {"$set": {
                    "organization_name": "Nonprofit Board Builder Preview Organization",
                    "founder_name": "Rooney Akpesiri", "founder_email": member["email"],
                    "founder_title": "Founder", "mission": answers["mission"],
                    "status": "Active", "internal_preview": True,
                }, "$setOnInsert": {
                    "project_id": project_id,
                    "guided_session_id": session_id,
                    "generic_form_token": f"admin-preview-form-{member['user_id'][-16:]}",
                    "created_at": now,
                }},
                upsert=True,
            )
            project = await db.sp_projects.find_one(
                {"guided_session_id": session_id}, {"_id": 0, "project_id": 1}
            )
            project_id = project["project_id"]
            await db.sp_participants.update_one(
                {"project_id": project_id, "email": member["email"]},
                {"$set": {
                    "name": "Rooney Akpesiri", "role": "Lead User", "status": "INVITED",
                    "internal_preview": True,
                }, "$setOnInsert": {
                    "participant_id": f"admin-preview-lead-{member['user_id'][-16:]}",
                    "project_id": project_id, "email": member["email"],
                    "form_token": f"admin-preview-lead-form-{member['user_id'][-16:]}",
                    "review_status": "NOT SENT",
                    "review_token": f"admin-preview-review-{member['user_id'][-16:]}",
                    "created_at": now,
                }},
                upsert=True,
            )
        elif product == "board-recommitment":
            await db.board_reactivation_intakes.update_one(
                {"guided_session_id": session_id},
                {"$set": {
                    "user_id": member["user_id"],
                    "organization_name": "Nonprofit Board Builder Preview Organization",
                    "founder_title": "Founder", "mission": answers["mission"],
                    "organization_goals": answers["goals"], "guided_session_id": session_id,
                    "guided_answers": answers, "internal_preview": True, "submitted_at": now,
                }},
                upsert=True,
            )
        return session_id

    @router.post("/{product}")
    async def launch_dashboard_preview(product: str, request: Request, response: Response):
        admin = await authenticate_admin(request, db)
        config = PRODUCTS.get(product)
        if not config:
            raise HTTPException(status_code=404, detail="Unknown product dashboard")
        member = await preview_member(admin)
        if config["entitlements"]:
            await db.members.update_one(
                {"user_id": member["user_id"]},
                {"$addToSet": {"entitlements": {"$each": config["entitlements"]}},
                 "$set": {"updated_at": now_iso()}},
            )
            member = await db.members.find_one({"user_id": member["user_id"]}, {"_id": 0})

        dashboard_url = config["dashboard_path"]
        if product == "board-fundraising-game":
            now = now_iso()
            await db.game_profiles.update_one(
                {"user_id": member["user_id"]},
                {"$set": {
                    "organization": {"name": "Nonprofit Board Builder Preview Organization"},
                    "goal": {"amount": "500000", "purpose": "Build sustainable nonprofit growth"},
                    "primary_user": {"full_name": "Rooney Akpesiri", "email": member["email"]},
                    "profile_completed": True, "situation_completed": True,
                    "internal_preview": True, "updated_at": now,
                }, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            await db.game_situations.update_one(
                {"user_id": member["user_id"]},
                {"$set": {"completed": True, "internal_preview": True, "updated_at": now},
                 "$setOnInsert": {"sections": {}, "current_step": 0, "created_at": now}},
                upsert=True,
            )
        elif product in {"strategic-planning", "board-recommitment"}:
            session_id = await seed_guided_product(member, product, config)
            dashboard_url = f"{dashboard_url}?session_id={session_id}"

        set_member_cookie(response, create_member_token(member["user_id"], member["email"]))
        return {"dashboard_url": dashboard_url, "product": product}

    return router
