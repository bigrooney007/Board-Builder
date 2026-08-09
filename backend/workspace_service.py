"""Phase 3 workspace helpers: profile context, materials persistence, core application questions."""
import json
import re
import secrets
import uuid
from datetime import datetime, timezone

from ai_service import GENERATION_TYPES, structured_to_display

CORE_QUESTIONS = [
    {"id": "full_name", "label": "Full name", "type": "text", "required": True},
    {"id": "email", "label": "Email", "type": "email", "required": True},
    {"id": "phone", "label": "Phone", "type": "text", "required": True},
    {"id": "city", "label": "City", "type": "text", "required": True},
    {"id": "state_region", "label": "State/region", "type": "text", "required": True},
    {"id": "country", "label": "Country", "type": "text", "required": True},
    {"id": "profession", "label": "Current profession/job title", "type": "text", "required": True},
    {"id": "employer", "label": "Current organization/employer", "type": "text", "required": False},
    {"id": "linkedin", "label": "LinkedIn profile", "type": "text", "required": False},
    {"id": "board_experience", "label": "Previous nonprofit board experience", "type": "textarea", "required": True},
    {"id": "why_interested", "label": "Why are you interested in joining this board?", "type": "textarea", "required": True},
    {"id": "skills_experience", "label": "Which skills and professional experience would you bring?", "type": "textarea", "required": True},
    {"id": "fundraising_support", "label": "Which fundraising activities are you willing to support?", "type": "textarea", "required": True},
    {"id": "relationships", "label": "Which professional, business or community relationships could help advance the mission?", "type": "textarea", "required": True},
    {"id": "monthly_time", "label": "How much time can you commit each month?", "type": "text", "required": True},
    {"id": "attend_meetings", "label": "Are you willing to attend board meetings consistently?", "type": "yes_no", "required": True},
    {"id": "accept_responsibility", "label": "Are you willing to accept responsibility for agreed assignments?", "type": "yes_no", "required": True},
    {"id": "causes", "label": "What causes or communities are you especially passionate about?", "type": "textarea", "required": True},
]

APPLICATION_STATUSES = ["Applied", "Reviewing", "Interview", "Selected", "Not Selected", "Withdrawn"]
OPPORTUNITY_STATUSES = ["Draft", "Ready to Publish", "Published", "Closed"]
REFERENCE_OUTCOMES = ["Positive", "Mixed", "Concern", "Unable to verify", "Not completed"]
BACKGROUND_STATUSES = ["Not required", "Not started", "In progress", "Completed", "Follow-up required"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def slugify(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (text or "board").lower()).strip("-")[:50] or "board"
    return f"{base}-{secrets.token_hex(3)}"


def profile_context_text(profile_data: dict, lead: dict = None) -> str:
    parts = []
    if lead:
        parts.append("PUBLIC RECRUITMENT FORM:\n" + json.dumps({k: lead.get(k) for k in ["organization", "website", "city", "state_region", "country"]} | (lead.get("answers") or {}), indent=1, default=str))
    if profile_data:
        parts.append("CONFIRMED MODULE 1 RECRUITMENT PROFILE:\n" + json.dumps(profile_data, indent=1, default=str))
    return "\n\n".join(parts) if parts else "No profile information available."


async def get_profile(db, user_id: str) -> dict:
    return await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}


async def get_lead(db, member: dict):
    lead_ids = member.get("lead_ids", [])
    if not lead_ids:
        return None
    return await db.funnel_leads.find_one({"lead_id": {"$in": lead_ids}, "offer_source": "recruitment"}, {"_id": 0}, sort=[("created_at", -1)])


async def get_current_material(db, user_id: str, generation_type: str, application_id: str = ""):
    query = {"user_id": user_id, "type": generation_type, "application_id": application_id or ""}
    material = await db.generated_materials.find_one(query, {"_id": 0})
    if not material:
        return None
    current = next((v for v in material["versions"] if v["version"] == material["current_version"]), None)
    return {"material": material, "current": current}


async def save_generation(db, user_id: str, generation_type: str, structured: dict, context_summary: str, application_id: str = "") -> dict:
    meta = GENERATION_TYPES[generation_type]
    display = structured_to_display(generation_type, structured)
    query = {"user_id": user_id, "type": generation_type, "application_id": application_id or ""}
    existing = await db.generated_materials.find_one(query, {"_id": 0})
    ts = now_iso()
    version_number = (max((v["version"] for v in existing["versions"]), default=0) + 1) if existing else 1
    version = {"version": version_number, "structured": structured, "display_text": display,
               "source": "generated", "input_context_summary": context_summary[:2000], "created_at": ts}
    if existing:
        await db.generated_materials.update_one(query, {"$push": {"versions": version}, "$set": {"current_version": version_number, "updated_at": ts, "status": "Generated"}})
    else:
        await db.generated_materials.insert_one({
            "material_id": new_id(), "user_id": user_id, "type": generation_type,
            "application_id": application_id or "", "module": meta["module"], "title": meta["title"],
            "versions": [version], "current_version": 1, "status": "Generated",
            "created_at": ts, "updated_at": ts,
        })
    return await db.generated_materials.find_one(query, {"_id": 0})


def application_context_text(application: dict, include_cv: bool = True) -> str:
    answers = application.get("answers", {})
    snapshot = application.get("profile_snapshot", {})
    parts = ["APPLICANT APPLICATION:\n" + json.dumps({**snapshot, **answers}, indent=1, default=str)]
    if include_cv and application.get("cv_text"):
        parts.append("APPLICANT CV (extracted text):\n" + application["cv_text"][:15000])
    return "\n\n".join(parts)


async def build_org_context(db, user_id: str, member: dict) -> str:
    """Standard organization context: public form + confirmed profile + approved strategy + opportunity."""
    profile = await get_profile(db, user_id)
    lead = await get_lead(db, member)
    parts = [profile_context_text(profile.get("data", {}), lead)]
    strategy = await get_current_material(db, user_id, "recruitment_strategy")
    if strategy and strategy["current"]:
        parts.append("APPROVED RECRUITMENT STRATEGY:\n" + strategy["current"]["display_text"][:12000])
    opportunity_material = await get_current_material(db, user_id, "board_opportunity")
    if opportunity_material and opportunity_material["current"]:
        parts.append("BOARD OPPORTUNITY:\n" + opportunity_material["current"]["display_text"][:8000])
    return "\n\n".join(parts)


async def run_interview_guide(db, application_id: str) -> None:
    """One automatic generation attempt. Application always remains intact on failure."""
    import os
    from ai_service import generate_structured
    application = await db.opportunity_applications.find_one({"application_id": application_id}, {"_id": 0})
    if not application:
        return
    if os.environ.get("AUTO_INTERVIEW_GUIDE", "true").lower() != "true":
        await db.opportunity_applications.update_one({"application_id": application_id}, {"$set": {"interview_guide": {"status": "Disabled"}}})
        return
    await db.opportunity_applications.update_one({"application_id": application_id}, {"$set": {"interview_guide.status": "Generating"}})
    try:
        owner_id = application["owner_user_id"]
        member = await db.members.find_one({"user_id": owner_id}, {"_id": 0}) or {}
        context = await build_org_context(db, owner_id, member) + "\n\n" + application_context_text(application)
        structured = await generate_structured("interview_guide", context)
        material = await save_generation(db, owner_id, "interview_guide", structured, "Automatic interview guide", application_id)
        await db.opportunity_applications.update_one(
            {"application_id": application_id},
            {"$set": {"interview_guide": {"status": "Ready", "material_id": material["material_id"], "generated_at": now_iso()}}},
        )
    except Exception as exc:
        await db.opportunity_applications.update_one(
            {"application_id": application_id},
            {"$set": {"interview_guide": {"status": "Failed", "error": str(exc)[:400], "failed_at": now_iso()}}},
        )
