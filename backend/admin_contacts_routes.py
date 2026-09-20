"""Admin Contact Center: unified contacts, detail view, timeline, manual access, email history, support view."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth_service import authenticate_admin
from lifecycle_engine import upsert_template

GRANTABLE = {
    "board_fundraising_game": "Board Fundraising Game",
    "fbb_recruitment": "Board Recruitment",
    "facilitated_board_fundraising_game": "Facilitated Board Fundraising Game",
}


def iso():
    return datetime.now(timezone.utc).isoformat()


class AccessPayload(BaseModel):
    user_id: str = Field(min_length=1)
    entitlement: str = Field(min_length=1)
    action: str = Field(min_length=1)  # grant | revoke


class TemplatePayload(BaseModel):
    product: str = Field(min_length=1)  # board_fundraising_game | board_recruitment
    payment_state: str = Field(min_length=1)  # paid | unpaid
    stage: int = Field(default=0, ge=0, le=6)  # 0 = stage-agnostic fallback
    sequence: int = Field(ge=1, le=5)  # 1-4 = Day 1/3/5/7, 5 = monthly callback
    subject: str = ""
    body: str = ""
    cta_label: str = "Continue"
    cta_destination: str = ""


def create_admin_contacts_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/admin/contacts")

    async def contact_products(member):
        entitlements = set(member.get("entitlements") or [])
        products = []
        if "board_fundraising_game" in entitlements:
            products.append("Board Fundraising Game (paid/granted)")
        elif await db.game_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "user_id": 1}):
            products.append("Board Fundraising Game (lead)")
        if entitlements & {"fbb_recruitment", "recruitment_self_guided", "fundraising_board_builder"}:
            products.append("Board Recruitment")
        if "facilitated_board_fundraising_game" in entitlements:
            products.append("Facilitated Board Fundraising Game")
        return products

    @router.get("")
    async def list_contacts(request: Request):
        await authenticate_admin(request, db)
        contacts = {}
        members = await db.members.find(
            {"internal_dashboard_preview": {"$ne": True}}, {"_id": 0, "password_hash": 0}
        ).to_list(4000)
        for member in members:
            email = (member.get("email") or "").lower()
            if not email:
                continue
            profile = await db.game_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "organization": 1})
            state = await db.lifecycle_state.find_one({"email": member["email"]}, {"_id": 0}, sort=[("entered_at", -1)])
            last_email = await db.lifecycle_email_log.find_one({"email": member["email"], "status": "sent"}, {"_id": 0}, sort=[("sent_at", -1)])
            paid = bool(await db.payment_transactions.find_one({"claimed_by_user_id": member["user_id"], "payment_status": "paid"}, {"_id": 0, "session_id": 1}))
            contacts[email] = {
                "contact_id": member["user_id"], "user_id": member["user_id"],
                "name": f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
                "email": member.get("email", ""), "phone": member.get("phone", ""),
                "location": member.get("location", ""),
                "organization": (profile or {}).get("organization", {}).get("name", "") if profile else "",
                "source": "member_signup", "contact_type": "customer" if paid else "lead",
                "products": await contact_products(member),
                "paid": paid or bool(member.get("entitlements")),
                "access_status": ", ".join(member.get("entitlements") or []) or "none",
                "current_stage": (state or {}).get("stage", ""),
                "last_activity": member.get("updated_at", member.get("created_at", "")),
                "created_at": member.get("created_at", ""),
                "last_email_sent": (last_email or {}).get("sent_at", ""),
            }
        invitees = await db.game_board_members.find({"removed": {"$ne": True}}, {"_id": 0}).to_list(4000)
        for record in invitees:
            email = (record.get("email") or "").lower()
            if not email or email in contacts:
                continue
            contacts[email] = {
                "contact_id": record["member_id"], "user_id": "",
                "name": record.get("full_name", ""), "email": record.get("email", ""),
                "phone": "", "location": "", "organization": "",
                "source": "game_invitation",
                "contact_type": f"invited_{record.get('participant_role', 'board_member')}",
                "products": ["Board Fundraising Game (participant)"], "paid": False,
                "access_status": record.get("invitation_status", ""),
                "current_stage": f"{record.get('sections_completed', 0)} sections" if record.get("sections_completed") else "",
                "last_activity": record.get("updated_at", record.get("created_at", "")),
                "created_at": record.get("created_at", ""),
                "last_email_sent": record.get("invited_at", ""),
            }
        rows = sorted(contacts.values(), key=lambda row: row.get("created_at") or "", reverse=True)
        return {"contacts": rows, "total": len(rows)}

    @router.get("/detail/{user_id}")
    async def contact_detail(user_id: str, request: Request):
        admin = await authenticate_admin(request, db)
        member = await db.members.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
        if not member:
            raise HTTPException(status_code=404, detail="Contact not found")
        await db.admin_access_audit.insert_one({
            "audit_id": str(uuid.uuid4()), "admin": getattr(admin, "get", lambda *_: "")("email") if isinstance(admin, dict) else "",
            "user_id": user_id, "action": "support_view_opened", "at": iso()})
        profile = await db.game_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}
        situation = await db.game_situations.find_one({"user_id": user_id}, {"_id": 0}) or {}
        participants = await db.game_board_members.find({"user_id": user_id, "removed": {"$ne": True}}, {"_id": 0}).to_list(300)
        member_ids = [p["member_id"] for p in participants]
        responses = await db.game_section_responses.find({"board_member_id": {"$in": member_ids}}, {"_id": 0}).to_list(2000)
        game_responses = []
        names = {p["member_id"]: p.get("full_name", "") for p in participants}
        for response in responses:
            fine_tuning = response.get("fine_tuning") or {}
            proposal = (fine_tuning.get("proposals") or [{}])[0]
            game_responses.append({
                "participant": names.get(response.get("board_member_id"), ""),
                "section_id": response.get("section_id"),
                "first_response": (response.get("first_response") or [""])[0] if response.get("first_response") else "",
                "second_response": (response.get("extras") or {}).get("second_response", ""),
                "complete_user_idea": proposal.get("original", ""),
                "strengthened_version": proposal.get("refined", ""),
                "accepted_version": fine_tuning.get("decision", ""),
                "participation": response.get("extras") if response.get("section_id") == 5 else None,
            })
        strategies = await db.game_strategies.find({"user_id": user_id}, {"_id": 0, "data": 0, "section_edits": 0}).sort("generated_at", -1).to_list(50)
        review = await db.game_board_reviews.find_one({"user_id": user_id}, {"_id": 0})
        night = await db.game_nights.find_one({"user_id": user_id}, {"_id": 0})
        transcript = await db.game_meeting_transcripts.find_one({"user_id": user_id}, {"_id": 0, "text": 0})
        payments = await db.payment_transactions.find({"claimed_by_user_id": user_id}, {"_id": 0}).to_list(50)
        emails = await db.lifecycle_email_log.find({"$or": [{"user_id": user_id}, {"email": member.get("email", "")}]}, {"_id": 0}).sort("sent_at", -1).to_list(200)
        access_history = await db.admin_access_history.find({"user_id": user_id}, {"_id": 0}).sort("at", -1).to_list(100)
        portfolios = await db.board_portfolios.find({"user_id": user_id}, {"_id": 0, "member_name": 1, "status": 1, "created_at": 1}).to_list(100)
        relationships = await db.game_relationships.find({"user_id": user_id}, {"_id": 0}).to_list(300)
        group = await db.group_game_sessions.find_one({"user_id": user_id}, {"_id": 0}, sort=[("created_at", -1)])
        timeline = build_timeline(member, participants, strategies, payments, emails, night, transcript, group)
        return {
            "contact": member, "organization_profile": profile, "current_fundraising_reality": situation.get("sections", {}),
            "participants": participants, "game_responses": game_responses,
            "strategies": strategies, "board_strategy_review": review, "meeting_details": night,
            "meeting_transcript": transcript, "group_game": group,
            "portfolios": portfolios, "relationship_mapping": relationships,
            "payments": payments, "email_history": emails, "access_history": access_history,
            "timeline": timeline,
        }

    def build_timeline(member, participants, strategies, payments, emails, night, transcript, group):
        events = [{"at": member.get("created_at", ""), "event": "Account created"}]
        for payment in payments:
            if payment.get("payment_status") == "paid":
                events.append({"at": payment.get("updated_at", ""), "event": f"Payment completed — {payment.get('offer', '')}"})
        for participant in participants:
            if participant.get("invited_at"):
                events.append({"at": participant["invited_at"], "event": f"Invitation sent — {participant.get('full_name', '')}"})
            if participant.get("completed_at"):
                events.append({"at": participant["completed_at"], "event": f"Participant completed — {participant.get('full_name', '')}"})
        if night and night.get("updated_at"):
            events.append({"at": night["updated_at"], "event": "Meeting details saved"})
        if group and group.get("completed_at"):
            events.append({"at": group["completed_at"], "event": "Group Game completed"})
        if transcript and transcript.get("submitted_at"):
            events.append({"at": transcript["submitted_at"], "event": "Meeting transcript submitted"})
        for strategy in strategies:
            events.append({"at": strategy.get("generated_at", ""), "event": f"Strategy generated — {strategy.get('mode', '')} v{strategy.get('version', '')}"})
        for email in emails[:25]:
            events.append({"at": email.get("sent_at", ""), "event": f"Lifecycle email {email.get('status', '')} — {email.get('subject', '') or email.get('template_id', '')}"})
        return sorted([event for event in events if event["at"]], key=lambda event: event["at"], reverse=True)

    @router.post("/access")
    async def manage_access(payload: AccessPayload, request: Request):
        await authenticate_admin(request, db)
        if payload.entitlement not in GRANTABLE:
            raise HTTPException(status_code=422, detail="Unknown entitlement")
        member = await db.members.find_one({"user_id": payload.user_id}, {"_id": 0, "user_id": 1})
        if not member:
            raise HTTPException(status_code=404, detail="Contact not found")
        if payload.action == "grant":
            update = {"$addToSet": {"entitlements": payload.entitlement}, "$set": {"updated_at": iso()}}
        elif payload.action == "revoke":
            update = {"$pull": {"entitlements": payload.entitlement}, "$set": {"updated_at": iso()}}
        else:
            raise HTTPException(status_code=422, detail="Action must be grant or revoke")
        await db.members.update_one({"user_id": payload.user_id}, update)
        await db.admin_access_history.insert_one({
            "history_id": str(uuid.uuid4()), "user_id": payload.user_id,
            "entitlement": payload.entitlement, "action": payload.action,
            "access_status": "admin_granted" if payload.action == "grant" else "admin_revoked",
            "payment_status_unchanged": True, "at": iso()})
        return {"status": "ok"}

    @router.get("/lifecycle-templates")
    async def list_lifecycle_templates(request: Request):
        await authenticate_admin(request, db)
        templates = await db.lifecycle_templates.find({}, {"_id": 0}).sort(
            [("product", 1), ("payment_state", 1), ("stage", 1), ("sequence", 1)]).to_list(500)
        return {"templates": templates}

    @router.post("/lifecycle-templates")
    async def save_lifecycle_template(payload: TemplatePayload, request: Request):
        await authenticate_admin(request, db)
        if payload.product not in {"board_fundraising_game", "board_recruitment"}:
            raise HTTPException(status_code=422, detail="Unknown product")
        if payload.payment_state not in {"paid", "unpaid"}:
            raise HTTPException(status_code=422, detail="payment_state must be paid or unpaid")
        template = payload.model_dump()
        template["template_id"] = f"{payload.product}:{payload.payment_state}:{payload.stage}:{payload.sequence}"
        await upsert_template(db, template)
        return {"status": "ok", "template_id": template["template_id"]}

    @router.delete("/lifecycle-templates/{template_id}")
    async def delete_lifecycle_template(template_id: str, request: Request):
        await authenticate_admin(request, db)
        await db.lifecycle_templates.delete_one({"template_id": template_id})
        return {"status": "ok"}

    return router
