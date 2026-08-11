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


REFERENCE_RULES = (
    "FOUNDER RECRUITMENT EXECUTION REFERENCE LIBRARY — private examples of how Rooney actually executes this stage in practice.\n"
    "STRICT RULES: use ONLY the structure, methodology, patterns, questions, sections and writing approach from these examples. "
    "They may contain a past client's information — NEVER copy or expose any client name, organization name, people's names, emails, phones, addresses, "
    "board member or applicant names, CV details, confidential notes or client-specific facts into this customer's output. "
    "Never duplicate an old document with names swapped; every output must be built from the current nonprofit's own information. "
    "SOURCE PRIORITY: (1) the current customer's actual information, (2) the locked six-stage Recruitment Framework, (3) these reference patterns, (4) general writing ability. "
    "If a reference conflicts with the locked framework, the framework wins."
)


MODULE_KEYWORDS = {
    1: ["board members your organization needs", "board matrix", "board gap", "skills assessment", "identify the board", "board audit"],
    2: ["recruitment strategy", "outreach strategy", "recruitment channels"],
    3: ["board opportunity", "board application", "linkedin", "social media", "recruitment email", "job post"],
    4: ["interview"],
    5: ["reference", "background check"],
    6: ["onboard", "board manual", "agreement", "orientation", "conflict of interest", "confidentiality"],
}

GENERATION_KEYWORDS = {
    "powerhouse_board_blueprint": ["board audit", "board matrix", "board composition", "skills gap", "board at a glance", "board needs"],
    "recruitment_strategy": ["recruitment strategy", "outreach strategy", "recruitment channels", "personal network", "public board recruitment", "national database of board candidates"],
    "board_opportunity": ["board opportunity", "board recruitment post", "board position"],
    "application_questions": ["application question", "board application", "application form"],
    "linkedin_post": ["linkedin post", "linkedin"],
    "social_posts": ["social media outreach", "social media", "facebook", "instagram"],
    "recruitment_emails": ["email newsletter", "recruitment email", "email outreach"],
    "linkedin_launch_instructions": ["linkedin/boardbuild", "boardsource", "idealist", "volunteer match", "linkedin"],
    "board_recruitment_job_post": ["linkedin job post", "job post", "board recruitment job"],
    "personal_invitation_email": ["personal invitation", "invitation email", "personal network"],
    "personal_invitation_message": ["personal invitation", "invitation message", "personal network"],
    "general_interview_invitation": ["interview invitation", "invite you to interview", "schedule an interview"],
    "general_rejection_email": ["decided to move forward", "not move forward", "rejection"],
    "conditional_offer": ["conditional board position offer", "conditional offer", "pending reference"],
    "after_interview_rejection": ["after careful consideration", "decided to move forward", "rejection"],
    "onboarding_script": ["welcome & introductions", "orientation", "onboarding"],
    "interview_guide": ["interview questions", "interview guide", "candidate interview", "interview agenda"],
    "interview_invitation": ["interview invitation", "schedule an interview", "invite you to interview"],
    "after_interview_email": ["after the interview", "thank you for interviewing", "following your interview"],
    "reference_request_email": ["reference request", "reference email", "references"],
    "reference_call_script": ["reference call", "reference questions", "reference check"],
    "reference_evaluation_form": ["reference evaluation", "reference check", "reference form"],
    "onboarding_agenda": ["welcome & introductions", "onboarding agenda", "orientation agenda", "review of board documents"],
    "organization_overview": ["organizational overview", "organization overview", "about the organization"],
    "board_manual": ["board manual", "board orientation", "board responsibilities"],
    "board_member_agreement": ["board member agreement", "board agreement"],
    "confidentiality_agreement": ["confidentiality and conflict of interest agreement", "confidentiality"],
    "conflict_of_interest_agreement": ["conflict of interest policy", "conflict of interest"],
    "ninety_day_plan": ["90 day", "ninety day", "90-day", "first 90"],
    "first_board_meeting_invitation": ["first board meeting", "board meeting invitation", "meeting invitation"],
}

REFERENCE_BUDGET = 8000
MODULE_FALLBACK_BUDGET = 4000


def _align_to_paragraph(text: str, start: int, end: int):
    ps = text.rfind("\n\n", 0, start)
    start = ps + 2 if ps != -1 else 0
    pe = text.find("\n\n", end)
    end = pe if pe != -1 else len(text)
    return start, min(end, start + 3000)


def _find_windows(text: str, lowered: str, keywords) -> list:
    windows = []
    for kw in keywords:
        pos = 0
        while True:
            i = lowered.find(kw, pos)
            if i == -1:
                break
            s, e = _align_to_paragraph(text, max(0, i - 300), i + len(kw) + 1200)
            windows.append([s, e])
            pos = i + len(kw)
    return windows


def _merge_windows(windows: list) -> list:
    windows.sort(key=lambda w: w[0])
    merged = []
    for s, e in windows:
        if merged and s <= merged[-1][1] + 200:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged


def slice_reference(text: str, module: int, gen_key: str = "", budget: int = REFERENCE_BUDGET) -> str:
    lowered = text.lower()
    windows = _find_windows(text, lowered, GENERATION_KEYWORDS.get(gen_key, []))
    if not windows:
        windows = _find_windows(text, lowered, MODULE_KEYWORDS.get(module, []))
        budget = min(budget, MODULE_FALLBACK_BUDGET)
    if not windows:
        return ""
    parts, total = [], 0
    for s, e in _merge_windows(windows):
        if total >= budget:
            break
        chunk = text[s:min(e, s + (budget - total))].strip()
        if chunk:
            parts.append(chunk)
            total += len(chunk)
    return "\n\n[...]\n\n".join(parts)


async def reference_context(db, gen_key: str) -> str:
    from ai_service import GENERATION_TYPES
    module = GENERATION_TYPES.get(gen_key, {}).get("module", 0)
    docs = await db.reference_materials.find(
        {"approved": True, "$or": [{"module": {"$in": [0, module]}}, {"resource_types": gen_key}]},
        {"_id": 0, "title": 1, "content_text": 1, "resource_types": 1, "module": 1},
    ).to_list(6)
    if not docs:
        return ""
    docs.sort(key=lambda d: 0 if gen_key in (d.get("resource_types") or []) else (1 if d.get("module") == module else 2))
    remaining = REFERENCE_BUDGET
    parts = []
    for d in docs[:2]:
        if remaining <= 0:
            break
        excerpt = slice_reference(d["content_text"], module, gen_key, budget=remaining)
        if excerpt:
            parts.append(f"REFERENCE EXAMPLE — {d['title']}:\n{excerpt}")
            remaining -= len(excerpt)
    if not parts:
        return ""
    return REFERENCE_RULES + "\n\n" + "\n\n".join(parts)


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
    if profile.get("strategy_intake"):
        parts.append("MODULE 2 RECRUITMENT STRATEGY INTAKE (the founder's answers about their network and channels):\n" + json.dumps(profile["strategy_intake"], indent=1, default=str))
    blueprint = await get_current_material(db, user_id, "powerhouse_board_blueprint")
    if blueprint and blueprint["current"]:
        parts.append("APPROVED POWERHOUSE BOARD BLUEPRINT (Module 1 — the exact board member profiles to recruit):\n" + blueprint["current"]["display_text"][:12000])
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
