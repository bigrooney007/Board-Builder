"""Complete Board Fix master intake: shared prefill mappings, member-mode helpers and write-back."""
from datetime import datetime, timezone

SYNTHETIC_PREFIX = "board-fix-"
BOARD_FIX_SOURCE = "board_fix_system_497"

MASTER_MAPPINGS = {
    "recruitment": {
        "organization_name": "organization_name", "website": "website", "mission": "mission",
        "present_board": "board_size", "current_board_strengths": "skills_represented",
        "board_challenges": "board_problems", "accomplish": "board_accomplish",
        "specific_wants": "recruitment_needs",
    },
    "reactivation": {
        "organization_name": "organization_name", "mission": "mission",
        "present_board": "board_size", "board_help_accomplish": "board_accomplish",
        "current_skills": "skills_represented", "missing_skills": "skills_missing",
        "original_responsibilities": "board_responsibilities",
        "actually_happening": "board_engagement", "disengage_reason": "board_problems",
        "direction_12_24": "strategic_priorities",
    },
    "activation": {
        "organization_name": "organization_name", "present_board": "board_size",
        "direction_12_24": "strategic_priorities", "organization_priorities": "organizational_goals",
        "board_skills_relationships": "skills_represented", "desired_change": "transformation_areas",
    },
}


def synthetic_session(user_id: str) -> str:
    return f"{SYNTHETIC_PREFIX}{user_id}"


async def get_master_record(db, user_id: str = "", email: str = ""):
    if user_id:
        record = await db.board_fix_intakes.find_one({"user_id": user_id}, {"_id": 0})
        if record:
            return record
    if email:
        return await db.board_fix_intakes.find_one({"lead_email": email.lower()}, {"_id": 0})
    return None


def master_prefill(pathway: str, master_data: dict) -> dict:
    return {field: str(master_data.get(source)).strip()
            for field, source in MASTER_MAPPINGS[pathway].items()
            if str(master_data.get(source, "") or "").strip()}


async def board_fix_member(request, db, pathway_entitlement: str) -> dict:
    from member_auth import authenticate_member, require_entitlement
    member = await authenticate_member(request, db)
    require_entitlement(member, {"board_fix_system", pathway_entitlement})
    return member


async def write_back_master(db, user_id: str, pathway: str, submitted: dict) -> None:
    """Fold new or changed pathway intake answers into the customer's Board Fix master record."""
    if not user_id:
        return
    record = await get_master_record(db, user_id=user_id)
    if not record:
        return
    data = record.get("data", {}) or {}
    updates = {}
    for field, source in MASTER_MAPPINGS[pathway].items():
        value = submitted.get(field, "")
        if isinstance(value, list):
            value = "; ".join(str(item) for item in value)
        value = str(value or "").strip()
        if value and value != str(data.get(source, "") or "").strip():
            updates[f"data.{source}"] = value
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.board_fix_intakes.update_one({"session_id": record["session_id"]}, {"$set": updates})
