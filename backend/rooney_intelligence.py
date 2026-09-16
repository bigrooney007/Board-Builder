"""Rooney Fundraising Intelligence: structured feedback store + de-identified pattern library."""
import re
import uuid
from datetime import datetime, timezone

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def scrub(text: str) -> str:
    cleaned = EMAIL_RE.sub("[email removed]", str(text or ""))
    return PHONE_RE.sub("[phone removed]", cleaned)


async def log_refinement(db, *, user_id, board_member_id, section_id, first_response, second_response,
                         complete_idea, strengthened, decision, org_category="", mission_category=""):
    await db.rooney_intelligence_events.insert_one({
        "event_id": str(uuid.uuid4()), "event_type": "refinement",
        "product": "board_fundraising_game", "strategic_area": section_id,
        "user_id": user_id, "board_member_id": board_member_id,
        "organization_category": org_category, "mission_category": mission_category,
        "first_response": str(first_response or "")[:6000],
        "second_response": str(second_response or "")[:6000],
        "complete_user_idea": str(complete_idea or "")[:8000],
        "strengthened_version": str(strengthened or "")[:8000],
        "kept_own_idea": decision == "keep_original",
        "accepted_strengthened": decision == "use_ai",
        "created_at": now_iso(),
    })
    await db.rooney_patterns.insert_one({
        "pattern_id": str(uuid.uuid4()), "pattern_type": "refinement",
        "strategic_area": section_id,
        "organization_category": org_category, "mission_category": mission_category,
        "strengthened_pattern": scrub(strengthened)[:6000],
        "accepted": decision == "use_ai",
        "created_at": now_iso(),
    })


async def log_review_decision(db, *, user_id, item, new_status, actor=""):
    await db.rooney_intelligence_events.insert_one({
        "event_id": str(uuid.uuid4()), "event_type": "board_review_decision",
        "product": "board_fundraising_game", "user_id": user_id,
        "recommendation": str(item.get("text", ""))[:4000],
        "strategic_area": item.get("area", ""),
        "original_source": item.get("source", ""),
        "original_status": item.get("original_status", ""),
        "new_status": new_status,
        "adopted_as_priority": new_status == "priority",
        "kept_as_recommendation": new_status == "recommendation",
        "marked_not_now": new_status == "not_now",
        "acting_host": actor,
        "created_at": now_iso(),
    })


async def store_strategy_patterns(db, *, user_id, mission_category, strategy_data):
    data = strategy_data or {}
    generalized = {
        "audiences": [item.get("title", "") for group in (data.get("fundraising_audiences") or {}).values()
                      if isinstance(group, list) for item in group if isinstance(item, dict)],
        "attraction": [item.get("title", "") if isinstance(item, dict) else str(item)
                       for item in (data.get("attraction") or {}).get("priorities", [])],
        "timeline_shape": sorted((data.get("execution_timeline") or {}).keys()),
    }
    await db.rooney_patterns.insert_one({
        "pattern_id": str(uuid.uuid4()), "pattern_type": "strategy",
        "mission_category": mission_category,
        "pattern": {key: [scrub(value)[:400] for value in values] if isinstance(values, list) else values
                    for key, values in generalized.items()},
        "created_at": now_iso(),
    })


async def retrieve_patterns(db, *, strategic_area=None, mission_category="", limit=8):
    query = {}
    if strategic_area:
        query["strategic_area"] = strategic_area
    if mission_category:
        query["mission_category"] = mission_category
    rows = await db.rooney_patterns.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    if not rows and mission_category:
        rows = await db.rooney_patterns.find(
            {k: v for k, v in query.items() if k != "mission_category"}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return rows
