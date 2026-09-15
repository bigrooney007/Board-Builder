"""Board Fundraising Game Phase 8: Game Night host tools (call script, facilitation guide, checklist)."""
import copy
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from auth_service import authenticate_admin
from member_auth import authenticate_member, require_entitlement
from game_night_routes import fmt_deadline, fmt_goal, fmt_meeting_date, fmt_time
from host_tools_content import DEFAULT_HOST_TOOLS

GAME_ENTITLEMENT = "board_fundraising_game"
TOTAL_SECTIONS = 10


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChecklistToggle(BaseModel):
    item_key: str = Field(min_length=1, max_length=160)
    checked: bool


def _text(value, limit=8000):
    return str(value)[:limit] if isinstance(value, str) and value.strip() else ""


def _items(value, limit=60):
    if not isinstance(value, list):
        return []
    return [str(item)[:600] for item in value if str(item).strip()][:limit]


def _merge_blocks(defaults: list, overrides) -> list:
    overrides = overrides if isinstance(overrides, list) else []
    merged = []
    for index, block in enumerate(defaults):
        override = overrides[index] if index < len(overrides) and isinstance(overrides[index], dict) else {}
        item = dict(block)
        if "label" in block:
            item["label"] = _text(override.get("label"), 300) or block["label"]
        if "items" in block:
            item["items"] = _items(override.get("items")) or list(block["items"])
        elif "text" in block:
            item["text"] = _text(override.get("text")) or block["text"]
        merged.append(item)
    return merged


def sanitize_content(payload: dict) -> dict:
    content = copy.deepcopy(DEFAULT_HOST_TOOLS)
    call = payload.get("call_script") if isinstance(payload.get("call_script"), dict) else {}
    content["call_script"]["page_title"] = _text(call.get("page_title"), 300) or content["call_script"]["page_title"]
    content["call_script"]["intro"] = _text(call.get("intro")) or content["call_script"]["intro"]
    call_overrides = {section.get("key"): section for section in (call.get("sections") or []) if isinstance(section, dict)}
    for section in content["call_script"]["sections"]:
        override = call_overrides.get(section["key"]) or {}
        section["heading"] = _text(override.get("heading"), 300) or section["heading"]
        section["body"] = _text(override.get("body")) or section["body"]

    guide = payload.get("facilitation") if isinstance(payload.get("facilitation"), dict) else {}
    content["facilitation"]["page_title"] = _text(guide.get("page_title"), 300) or content["facilitation"]["page_title"]
    guide_overrides = {section.get("key"): section for section in (guide.get("sections") or []) if isinstance(section, dict)}
    for section in content["facilitation"]["sections"]:
        override = guide_overrides.get(section["key"]) or {}
        section["heading"] = _text(override.get("heading"), 300) or section["heading"]
        section["blocks"] = _merge_blocks(section["blocks"], override.get("blocks"))

    checklist = payload.get("checklist") if isinstance(payload.get("checklist"), dict) else {}
    content["checklist"]["page_title"] = _text(checklist.get("page_title"), 300) or content["checklist"]["page_title"]
    content["checklist"]["intro"] = _text(checklist.get("intro")) or content["checklist"]["intro"]
    group_overrides = {group.get("key"): group for group in (checklist.get("groups") or []) if isinstance(group, dict)}
    for group in content["checklist"]["groups"]:
        override = group_overrides.get(group["key"]) or {}
        group["heading"] = _text(override.get("heading"), 300) or group["heading"]
        group["items"] = _items(override.get("items")) or list(group["items"])
    return content


def substitute(value, mapping: dict):
    if isinstance(value, str):
        for token, replacement in mapping.items():
            value = value.replace(token, replacement)
        return value
    if isinstance(value, list):
        return [substitute(item, mapping) for item in value]
    if isinstance(value, dict):
        return {key: substitute(item, mapping) for key, item in value.items()}
    return value


def create_host_tools_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def game_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        return member

    async def merged_content() -> dict:
        doc = await db.marketing_settings.find_one({"key": "game_host_tools_content"}, {"_id": 0}) or {}
        stored = doc.get("content")
        return sanitize_content(stored) if isinstance(stored, dict) else copy.deepcopy(DEFAULT_HOST_TOOLS)

    async def get_night(user_id: str) -> dict:
        return await db.game_nights.find_one({"user_id": user_id}, {"_id": 0}) or {}

    @router.get("/game/host-tools/content")
    async def host_tools_content(request: Request, member_id: str = ""):
        member = await game_member(request)
        profile = await db.game_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0}) or {}
        night = await get_night(member["user_id"])
        organization = (profile.get("organization") or {}).get("name", "").strip() or "our organization"
        content = substitute(await merged_content(), {
            "[Organization Name]": organization,
            "[Organisation Name]": organization,
            "[Fundraising Goal]": fmt_goal(profile),
            "[Fundraising Deadline]": fmt_deadline(profile) or "our deadline",
        })
        invited = await db.game_board_members.count_documents(
            {"user_id": member["user_id"], "removed": {"$ne": True}, "invitation_status": "invited"})
        completed = 0
        records = await db.game_board_members.find(
            {"user_id": member["user_id"], "removed": {"$ne": True}}, {"_id": 0, "member_id": 1, "total_sections": 1}).to_list(200)
        for record in records:
            done = await db.game_section_responses.count_documents(
                {"board_member_id": record["member_id"], "completed": True})
            if done >= (record.get("total_sections") or TOTAL_SECTIONS):
                completed += 1
        member_first_name = ""
        if member_id:
            record = await db.game_board_members.find_one(
                {"member_id": member_id, "user_id": member["user_id"], "removed": {"$ne": True}}, {"_id": 0})
            if record:
                member_first_name = record["full_name"].split(" ")[0]
        night_display = ""
        if night.get("meeting_date"):
            night_display = f"{fmt_meeting_date(night)} at {fmt_time(night)}".strip()
        return {"content": content, "context": {
            "organization_name": organization,
            "goal_display": fmt_goal(profile),
            "deadline_display": fmt_deadline(profile),
            "night_display": night_display,
            "invited_count": invited,
            "completed_count": completed,
            "member_first_name": member_first_name,
        }}

    # ---------- Checklist state (per Game Night, old checklists preserved) ----------

    @router.get("/game/host-tools/checklist")
    async def read_checklist(request: Request):
        member = await game_member(request)
        night = await get_night(member["user_id"])
        night_key = night.get("meeting_date") or "unscheduled"
        doc = await db.game_night_checklists.find_one(
            {"user_id": member["user_id"], "night_key": night_key}, {"_id": 0}) or {}
        return {"night_key": night_key, "has_night": bool(night.get("meeting_date")), "checked": doc.get("checked") or {}}

    @router.put("/game/host-tools/checklist")
    async def toggle_checklist(payload: ChecklistToggle, request: Request):
        member = await game_member(request)
        night = await get_night(member["user_id"])
        night_key = night.get("meeting_date") or "unscheduled"
        item_key = payload.item_key.replace(".", "-").replace("$", "-")
        now = now_iso()
        await db.game_night_checklists.update_one(
            {"user_id": member["user_id"], "night_key": night_key},
            {"$set": {f"checked.{item_key}": payload.checked, "updated_at": now},
             "$setOnInsert": {"user_id": member["user_id"], "night_key": night_key, "created_at": now}},
            upsert=True)
        return {"status": "saved", "night_key": night_key}

    # ---------- Admin content management ----------

    @router.get("/admin/game/host-tools-content")
    async def admin_read_host_tools(request: Request):
        await authenticate_admin(request, db)
        return {"content": await merged_content()}

    @router.put("/admin/game/host-tools-content")
    async def admin_save_host_tools(payload: dict, request: Request):
        await authenticate_admin(request, db)
        content = sanitize_content(payload if isinstance(payload, dict) else {})
        await db.marketing_settings.update_one(
            {"key": "game_host_tools_content"},
            {"$set": {"content": content, "updated_at": now_iso()}}, upsert=True)
        return {"content": content}

    return router
