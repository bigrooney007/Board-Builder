"""Board Fundraising Game Phase 2: Game Night setup, board members, invitations, reminders, individual game play."""
import html
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

import resend
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from auth_service import authenticate_admin
from member_auth import authenticate_member, new_uuid, require_entitlement
from game_content import EDITABLE_FIELDS, merged_sections
from game_content_v3 import GAME_V3
from game_response_quality import is_meaningful_game_response, response_input_hash, response_texts
from reactivation_routes import email_html

logger = logging.getLogger(__name__)

GAME_ENTITLEMENT = "board_fundraising_game"
REMINDER_HOURS = 48
TOTAL_SECTIONS = 10

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fmt_goal(profile: dict) -> str:
    amount = (profile.get("goal") or {}).get("amount") or 0
    return f"${int(amount):,}" if amount else "its fundraising goal"


def fmt_deadline(profile: dict) -> str:
    raw = (profile.get("goal") or {}).get("deadline") or ""
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%B %-d, %Y")
    except ValueError:
        return raw


def fmt_meeting_date(night: dict) -> str:
    raw = night.get("meeting_date") or ""
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%A, %B %-d, %Y")
    except ValueError:
        return raw


def fmt_time(night: dict) -> str:
    raw = night.get("start_time") or ""
    try:
        parsed = datetime.strptime(raw, "%H:%M").strftime("%-I:%M %p")
    except ValueError:
        parsed = raw
    tz = night.get("timezone") or ""
    return f"{parsed} {tz}".strip()


class GameNightUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    meeting_date: str = Field(min_length=1, max_length=20)
    funding_deadline: str = Field(min_length=1, max_length=20)
    start_time: str = Field(min_length=1, max_length=20)
    timezone_name: str = Field(min_length=1, max_length=80)
    meeting_format: str = Field(min_length=1, max_length=20)
    meeting_link: str = Field(default="", max_length=500)
    meeting_location: str = Field(default="", max_length=500)
    note: str = Field(default="", max_length=4000)


class BoardMemberCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    board_title: str = Field(default="", max_length=200)
    participant_role: str = Field(default="board_member", max_length=60)


class SendPayload(BaseModel):
    origin_url: str = Field(min_length=1)


class SectionSave(BaseModel):
    first_response: list = Field(default_factory=list)
    guided_selections: dict = Field(default_factory=dict)
    additional_ideas: dict = Field(default_factory=dict)
    stage_responses: dict = Field(default_factory=dict)
    final_response: list = Field(default_factory=list)
    preferences: list = Field(default_factory=list)
    do_not_want: list = Field(default_factory=list)
    group_game_ideas: list = Field(default_factory=list)
    extras: dict = Field(default_factory=dict)
    first_move_locked: bool = False


def clean_list(items, limit=80, max_chars=600):
    return [str(item)[:max_chars] for item in (items or [])[:limit] if str(item).strip()]


def clean_dict_of_lists(data):
    return {str(key)[:80]: clean_list(value) for key, value in (data or {}).items() if isinstance(value, list)}


def create_game_night_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def game_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        return member

    async def get_night(user_id: str) -> dict:
        return await db.game_nights.find_one({"user_id": user_id}, {"_id": 0}) or {}

    async def get_profile(user_id: str) -> dict:
        return await db.game_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}

    async def get_sections_content() -> list:
        doc = await db.marketing_settings.find_one({"key": "game_individual_content"}, {"_id": 0}) or {}
        return merged_sections(doc.get("sections") or {})

    async def merged_v3() -> dict:
        doc = await db.marketing_settings.find_one({"key": "game_v3_content"}, {"_id": 0}) or {}
        stored = doc.get("content") if isinstance(doc.get("content"), dict) else {}
        return {**GAME_V3, **{key: value for key, value in stored.items() if key in GAME_V3}}

    async def member_row(record: dict) -> dict:
        total = record.get("total_sections") or TOTAL_SECTIONS
        completed = await db.game_section_responses.count_documents(
            {"board_member_id": record["member_id"], "completed": True})
        started = completed > 0 or await db.game_section_responses.count_documents({"board_member_id": record["member_id"]}) > 0
        if completed >= total:
            game_status = "Game Completed"
        elif completed > 0:
            game_status = "Game In Progress"
        elif started:
            game_status = "Game Started"
        elif record.get("invitation_status") == "invited":
            game_status = "Invited"
        else:
            game_status = "Not Invited"
        reminder_available_at = ""
        if record.get("last_reminder_at"):
            reminder_available_at = (datetime.fromisoformat(record["last_reminder_at"]) + timedelta(hours=REMINDER_HOURS)).isoformat()
        return {
            "member_id": record["member_id"], "full_name": record["full_name"], "email": record["email"],
            "board_title": record.get("board_title", ""), "token": record["token"],
            "invitation_status": record.get("invitation_status", "not_invited"),
            "invited_at": record.get("invited_at", ""), "last_reminder_at": record.get("last_reminder_at", ""),
            "reminder_available_at": reminder_available_at,
            "sections_completed": completed, "total_sections": total,
            "game_started": started, "status": game_status,
        }

    # ---------- Game Night setup ----------

    @router.get("/game/night")
    async def read_game_night(request: Request):
        member = await game_member(request)
        profile = await get_profile(member["user_id"])
        night = await get_night(member["user_id"])
        default_name = f"{(profile.get('organization') or {}).get('name', '').strip() or 'Our'} Board Fundraising Game"
        return {"night": night, "default_name": default_name}

    @router.put("/game/night")
    async def save_game_night(payload: GameNightUpdate, request: Request):
        member = await game_member(request)
        if payload.meeting_format not in {"in_person", "online", "hybrid"}:
            raise HTTPException(status_code=422, detail="Choose a meeting format")
        try:
            meeting_date = datetime.strptime(payload.meeting_date.strip(), "%Y-%m-%d").date()
            funding_deadline = datetime.strptime(payload.funding_deadline.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=422, detail="Use a valid meeting date and funding deadline")
        if funding_deadline < meeting_date:
            raise HTTPException(status_code=422, detail="The funding deadline cannot be before the Board meeting date")
        now = now_iso()
        await db.game_nights.update_one(
            {"user_id": member["user_id"]},
            {"$set": {
                "name": payload.name.strip(), "meeting_date": payload.meeting_date.strip(),
                "funding_deadline": payload.funding_deadline.strip(),
                "start_time": payload.start_time.strip(), "timezone": payload.timezone_name.strip(),
                "meeting_format": payload.meeting_format,
                "meeting_link": payload.meeting_link.strip(), "meeting_location": payload.meeting_location.strip(),
                "note": payload.note.strip(), "status": "scheduled", "updated_at": now},
             "$setOnInsert": {"user_id": member["user_id"], "created_at": now}},
            upsert=True)
        await db.game_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"goal.deadline": payload.funding_deadline.strip(), "updated_at": now}},
            upsert=True,
        )
        return {"night": await get_night(member["user_id"])}

    # ---------- Board member management ----------

    @router.get("/game/board-members")
    async def list_board_members(request: Request):
        member = await game_member(request)
        records = await db.game_board_members.find(
            {"user_id": member["user_id"], "removed": {"$ne": True}}, {"_id": 0}).sort("created_at", 1).to_list(200)
        return {"board_members": [await member_row(record) for record in records]}

    @router.post("/game/board-members", status_code=201)
    async def add_board_member(payload: BoardMemberCreate, request: Request):
        member = await game_member(request)
        now = now_iso()
        record = {
            "member_id": new_uuid(), "user_id": member["user_id"],
            "token": secrets.token_urlsafe(24),
            "full_name": payload.full_name.strip(), "email": str(payload.email).lower(),
            "board_title": payload.board_title.strip(),
            "participant_role": payload.participant_role if payload.participant_role in
            {"board_member", "staff", "volunteer", "other_leader"} else "board_member",
            "game_version": 3, "total_sections": 5,
            "invitation_status": "not_invited", "invited_at": "", "last_reminder_at": "",
            "removed": False, "created_at": now, "updated_at": now,
        }
        await db.game_board_members.insert_one(record.copy())
        return {"board_member": await member_row(record)}

    @router.post("/game/self-play", status_code=201)
    async def self_play(request: Request):
        member = await authenticate_member(request, db)
        profile = await db.game_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0}) or {}
        if not profile.get("profile_completed"):
            raise HTTPException(status_code=409, detail="Save your Fundraising Game Profile before playing")
        existing = await db.game_board_members.find_one(
            {"user_id": member["user_id"], "is_primary": True, "removed": {"$ne": True}}, {"_id": 0})
        if existing:
            return {"token": existing["token"], "member_id": existing["member_id"]}
        primary = profile.get("primary_user") or {}
        now = now_iso()
        record = {
            "member_id": new_uuid(), "user_id": member["user_id"],
            "token": secrets.token_urlsafe(24),
            "full_name": primary.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip() or "Primary User",
            "email": member["email"], "board_title": primary.get("job_title", ""),
            "is_primary": True, "game_version": 3, "total_sections": 4,
            "invitation_status": "self", "invited_at": "", "last_reminder_at": "",
            "removed": False, "created_at": now, "updated_at": now,
        }
        await db.game_board_members.insert_one(record.copy())
        return {"token": record["token"], "member_id": record["member_id"]}

    @router.put("/game/board-members/{member_id}")
    async def edit_board_member(member_id: str, payload: BoardMemberCreate, request: Request):
        member = await game_member(request)
        result = await db.game_board_members.update_one(
            {"member_id": member_id, "user_id": member["user_id"]},
            {"$set": {"full_name": payload.full_name.strip(), "email": str(payload.email).lower(),
                      "board_title": payload.board_title.strip(), "updated_at": now_iso()}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Board member not found")
        record = await db.game_board_members.find_one({"member_id": member_id}, {"_id": 0})
        return {"board_member": await member_row(record)}

    @router.delete("/game/board-members/{member_id}")
    async def remove_board_member(member_id: str, request: Request):
        member = await game_member(request)
        result = await db.game_board_members.update_one(
            {"member_id": member_id, "user_id": member["user_id"]},
            {"$set": {"removed": True, "removed_at": now_iso()}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Board member not found")
        return {"status": "removed"}

    # ---------- Emails ----------

    def signature_html(profile: dict, member: dict) -> str:
        primary = profile.get("primary_user") or {}
        organization = profile.get("organization") or {}
        lines = [
            primary.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
            primary.get("job_title", ""),
            organization.get("name", ""),
            organization.get("website", ""),
        ]
        return "".join(f"<p style='margin:2px 0;'>{html.escape(line)}</p>" for line in lines if line and line.strip())

    def night_details_html(night: dict, primary_first: str) -> str:
        parts = [f"<p style='margin:2px 0;'><strong>Game Night</strong></p>",
                 f"<p style='margin:2px 0;'>Date: {html.escape(fmt_meeting_date(night))}</p>",
                 f"<p style='margin:2px 0;'>Time: {html.escape(fmt_time(night))}</p>"]
        fmt = night.get("meeting_format", "")
        if fmt in {"online", "hybrid"} and night.get("meeting_link"):
            parts.append(f"<p style='margin:2px 0;'>Meeting Link: <a href='{html.escape(night['meeting_link'])}'>{html.escape(night['meeting_link'])}</a></p>")
        if fmt in {"in_person", "hybrid"} and night.get("meeting_location"):
            parts.append(f"<p style='margin:2px 0;'>Location: {html.escape(night['meeting_location'])}</p>")
        if night.get("note"):
            parts.append(f"<p style='margin:10px 0 2px;'><strong>Note From {html.escape(primary_first)}:</strong></p>"
                         f"<p style='margin:2px 0;'>{html.escape(night['note'])}</p>")
        return "".join(parts)

    async def send_game_email(to_email: str, reply_to: str, subject: str, body_html: str):
        try:
            resend.api_key = os.environ["RESEND_API_KEY"]
            await resend.Emails.send_async({
                "from": os.environ["GAME_EMAIL_SENDER"], "to": [to_email],
                "reply_to": reply_to, "subject": subject,
                "html": f"<div style='max-width:600px;margin:auto;font-family:Arial,sans-serif;color:#111;line-height:1.6;'>{body_html}</div>",
            })
        except Exception as exc:
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc

    def game_button(link: str, label: str) -> str:
        return (f"<p style='margin:22px 0;'><a href='{html.escape(link)}' "
                f"style='background:#4f46e5;color:#ffffff;padding:13px 26px;border-radius:999px;"
                f"text-decoration:none;font-weight:bold;display:inline-block;'>{html.escape(label)}</a></p>")

    async def send_invitation(member: dict, record: dict, profile: dict, night: dict, origin: str):
        organization = (profile.get("organization") or {}).get("name", "your organization")
        primary = profile.get("primary_user") or {}
        primary_name = primary.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()
        primary_first = primary_name.split(" ")[0] if primary_name else ""
        first_name = record["full_name"].split(" ")[0]
        goal = fmt_goal(profile)
        deadline = fmt_deadline(profile)
        goal_line = f"Our organization is working toward a fundraising goal of {html.escape(goal)}"
        goal_line += f" by {html.escape(deadline)}." if deadline else "."
        link = f"{origin.rstrip('/')}/play/{record['token']}"
        body = (
            f"<p>Hi {html.escape(first_name)},</p>"
            f"<p>{html.escape(primary_name)} has invited you to participate in {html.escape(organization)}'s Board Fundraising Game.</p>"
            f"<p>{goal_line}</p>"
            f"<p>During our next board meeting, we will come together to build and adopt the fundraising strategy our organization will use to work toward this goal.</p>"
            f"<p><strong>Before Game Night, we need your ideas.</strong></p>"
            f"<p>You will play a short individual fundraising game that will teach you how a complete fundraising strategy is built while helping you share your own ideas about how {html.escape(organization)} can raise money.</p>"
            f"<p>You can complete the game one section at a time and return whenever you need to.</p>"
            f"{game_button(link, 'Start My Individual Game')}"
            f"{night_details_html(night, primary_first)}"
            f"<div style='margin-top:26px;'>{signature_html(profile, member)}</div>"
        )
        subject = f"You're Invited To Play The Board Fundraising Game For {organization}"
        await send_game_email(record["email"], member["email"], subject, body)

    async def send_reminder(member: dict, record: dict, profile: dict, night: dict, origin: str):
        organization = (profile.get("organization") or {}).get("name", "your organization")
        primary = profile.get("primary_user") or {}
        primary_name = primary.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()
        first_name = record["full_name"].split(" ")[0]
        link = f"{origin.rstrip('/')}/play/{record['token']}"
        signature_lines = [primary_name, primary.get("job_title", ""), (profile.get("organization") or {}).get("name", "")]
        signature = "".join(f"<p style='margin:2px 0;'>{html.escape(line)}</p>" for line in signature_lines if line and line.strip())
        body = (
            f"<p>Hi {html.escape(first_name)},</p>"
            f"<p>Game Night for {html.escape(organization)} is coming up.</p>"
            f"<p>Your ideas will help your board build the fundraising strategy your organization will use to work toward its {html.escape(fmt_goal(profile))} goal.</p>"
            f"<p>Complete your Individual Board Fundraising Game before the meeting so your ideas can be included when the board plays together.</p>"
            f"{game_button(link, 'Continue My Game')}"
            f"<p>Game Night: {html.escape(fmt_meeting_date(night))} at {html.escape(fmt_time(night))}</p>"
            f"<div style='margin-top:26px;'>{signature}</div>"
        )
        await send_game_email(record["email"], member["email"], "Your Board Fundraising Game Is Waiting", body)

    async def require_night(user_id: str) -> dict:
        night = await get_night(user_id)
        if not night.get("meeting_date") or not night.get("funding_deadline"):
            raise HTTPException(status_code=409, detail="meeting_details_required")
        return night

    @router.post("/game/board-members/{member_id}/invite")
    async def invite_board_member(member_id: str, payload: SendPayload, request: Request):
        member = await game_member(request)
        record = await db.game_board_members.find_one(
            {"member_id": member_id, "user_id": member["user_id"], "removed": {"$ne": True}}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Board member not found")
        night = await require_night(member["user_id"])
        profile = await get_profile(member["user_id"])
        await send_invitation(member, record, profile, night, payload.origin_url)
        await db.game_board_members.update_one(
            {"member_id": member_id},
            {"$set": {"invitation_status": "invited", "invited_at": now_iso(), "updated_at": now_iso()}})
        fresh = await db.game_board_members.find_one({"member_id": member_id}, {"_id": 0})
        return {"board_member": await member_row(fresh)}

    @router.post("/game/board-members/invite-all")
    async def invite_all(payload: SendPayload, request: Request):
        member = await game_member(request)
        night = await require_night(member["user_id"])
        profile = await get_profile(member["user_id"])
        records = await db.game_board_members.find(
            {"user_id": member["user_id"], "removed": {"$ne": True}, "invitation_status": {"$ne": "invited"}},
            {"_id": 0}).to_list(200)
        sent = 0
        for record in records:
            await send_invitation(member, record, profile, night, payload.origin_url)
            await db.game_board_members.update_one(
                {"member_id": record["member_id"]},
                {"$set": {"invitation_status": "invited", "invited_at": now_iso(), "updated_at": now_iso()}})
            sent += 1
        return {"sent": sent}

    def reminder_block(record: dict):
        last = record.get("last_reminder_at")
        if not last:
            return None
        available_at = datetime.fromisoformat(last) + timedelta(hours=REMINDER_HOURS)
        remaining = available_at - datetime.now(timezone.utc)
        if remaining.total_seconds() <= 0:
            return None
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}m"

    async def is_completed(member_id: str) -> bool:
        record = await db.game_board_members.find_one({"member_id": member_id}, {"_id": 0, "total_sections": 1}) or {}
        total = record.get("total_sections") or TOTAL_SECTIONS
        return await db.game_section_responses.count_documents({"board_member_id": member_id, "completed": True}) >= total

    @router.post("/game/board-members/{member_id}/remind")
    async def remind_board_member(member_id: str, payload: SendPayload, request: Request):
        member = await game_member(request)
        record = await db.game_board_members.find_one(
            {"member_id": member_id, "user_id": member["user_id"], "removed": {"$ne": True}}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Board member not found")
        if record.get("invitation_status") != "invited":
            raise HTTPException(status_code=409, detail="Send the invitation first")
        if await is_completed(member_id):
            raise HTTPException(status_code=409, detail="This board member has already completed their game")
        remaining = reminder_block(record)
        if remaining:
            raise HTTPException(status_code=429, detail=f"Reminder sent. Available again in {remaining}.")
        night = await require_night(member["user_id"])
        profile = await get_profile(member["user_id"])
        await send_reminder(member, record, profile, night, payload.origin_url)
        await db.game_board_members.update_one(
            {"member_id": member_id}, {"$set": {"last_reminder_at": now_iso(), "updated_at": now_iso()}})
        fresh = await db.game_board_members.find_one({"member_id": member_id}, {"_id": 0})
        return {"board_member": await member_row(fresh)}

    @router.post("/game/board-members/remind-all")
    async def remind_all(payload: SendPayload, request: Request):
        member = await game_member(request)
        night = await require_night(member["user_id"])
        profile = await get_profile(member["user_id"])
        records = await db.game_board_members.find(
            {"user_id": member["user_id"], "removed": {"$ne": True}, "invitation_status": "invited"},
            {"_id": 0}).to_list(200)
        sent = 0
        for record in records:
            if await is_completed(record["member_id"]) or reminder_block(record):
                continue
            await send_reminder(member, record, profile, night, payload.origin_url)
            await db.game_board_members.update_one(
                {"member_id": record["member_id"]}, {"$set": {"last_reminder_at": now_iso(), "updated_at": now_iso()}})
            sent += 1
        return {"sent": sent}

    @router.get("/game/board-members/{member_id}/responses")
    async def view_responses(member_id: str, request: Request):
        member = await game_member(request)
        record = await db.game_board_members.find_one(
            {"member_id": member_id, "user_id": member["user_id"]}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Board member not found")
        responses = await db.game_section_responses.find(
            {"board_member_id": member_id}, {"_id": 0}).sort("section_id", 1).to_list(20)
        sections = await get_sections_content()
        titles = {section["id"]: section["title"] for section in sections}
        for response in responses:
            response["section_title"] = titles.get(response["section_id"], f"Section {response['section_id']}")
        return {"board_member": await member_row(record), "responses": responses}

    # ---------- Individual game content ----------

    @router.get("/game/individual-content")
    async def individual_content():
        return {"sections": await get_sections_content()}

    @router.put("/admin/game/individual-content/{section_id}")
    async def update_individual_content(section_id: int, payload: dict, request: Request):
        await authenticate_admin(request, db)
        if section_id < 1 or section_id > TOTAL_SECTIONS:
            raise HTTPException(status_code=404, detail="Unknown section")
        sets = {}
        for field in EDITABLE_FIELDS:
            if isinstance(payload.get(field), str):
                sets[f"sections.{section_id}.{field}"] = payload[field][:8000]
        group_items = payload.get("group_items")
        if isinstance(group_items, dict):
            for group_key, items in group_items.items():
                if isinstance(items, list):
                    sets[f"sections.{section_id}.group_items.{str(group_key)[:80]}"] = [
                        {"text": str(item.get("text", ""))[:600], "hint": str(item.get("hint", ""))[:600]}
                        for item in items if isinstance(item, dict) and str(item.get("text", "")).strip()][:40]
        if not sets:
            raise HTTPException(status_code=422, detail="No editable fields provided")
        sets["updated_at"] = now_iso()
        await db.marketing_settings.update_one({"key": "game_individual_content"}, {"$set": sets}, upsert=True)
        return {"sections": await get_sections_content()}

    # ---------- Public play (secure token, no account) ----------

    async def playing_member(token: str) -> dict:
        record = await db.game_board_members.find_one({"token": token, "removed": {"$ne": True}}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This game link is not valid")
        return record

    @router.get("/game/play/{token}")
    async def play_context(token: str):
        record = await playing_member(token)
        profile = await get_profile(record["user_id"])
        night = await get_night(record["user_id"])
        situation = (await db.game_situations.find_one(
            {"user_id": record["user_id"]}, {"_id": 0}) or {}).get("sections") or {}

        def context_lines(section_key: str, fields: list) -> list:
            data = situation.get(section_key) or {}
            lines = []
            for field in fields:
                value = data.get(field)
                if isinstance(value, list):
                    lines.extend(str(v).strip() for v in value if str(v).strip())
                elif isinstance(value, str) and value.strip():
                    lines.append(value.strip())
            return lines[:15]

        responses = await db.game_section_responses.find(
            {"board_member_id": record["member_id"]},
            {"_id": 0, "section_id": 1, "completed": 1, "first_move_locked": 1}).to_list(20)
        organization = profile.get("organization") or {}
        org_member = await db.members.find_one({"user_id": record["user_id"]}, {"_id": 0, "entitlements": 1}) or {}
        return {
            "paid": GAME_ENTITLEMENT in org_member.get("entitlements", []),
            "first_name": record["full_name"].split(" ")[0],
            "organization_name": organization.get("name", ""),
            "goal_display": fmt_goal(profile),
            "deadline_display": fmt_deadline(profile),
            "game_night": {
                "date_display": fmt_meeting_date(night), "time_display": fmt_time(night),
                "meeting_format": night.get("meeting_format", ""),
                "meeting_link": night.get("meeting_link", ""), "meeting_location": night.get("meeting_location", ""),
                "note": night.get("note", ""),
            } if night else None,
            "sections": await get_sections_content(),
            "v3": await merged_v3(),
            "member": {
                "game_version": record.get("game_version") or 2,
                "is_primary": bool(record.get("is_primary")),
                "participant_role": record.get("participant_role", "board_member"),
                "total_sections": record.get("total_sections") or TOTAL_SECTIONS,
            },
            "situation_context": {
                "technology": context_lines("technology", ["tools", "tech_working"]),
                "team": context_lines("team", ["who_handles", "board_involvement"]),
                "materials": context_lines("materials", ["materials"]),
            },
            "progress": {str(response["section_id"]): {"completed": bool(response.get("completed")), "first_move_locked": bool(response.get("first_move_locked"))} for response in responses},
        }

    @router.get("/game/play/{token}/section/{section_id}")
    async def play_section(token: str, section_id: int):
        record = await playing_member(token)
        response = await db.game_section_responses.find_one(
            {"board_member_id": record["member_id"], "section_id": section_id}, {"_id": 0})
        return {"response": response or {}}

    async def save_section(record: dict, section_id: int, payload: SectionSave, complete: bool):
        if section_id < 1 or section_id > TOTAL_SECTIONS:
            raise HTTPException(status_code=404, detail="Unknown section")
        now = now_iso()
        existing = await db.game_section_responses.find_one(
            {"board_member_id": record["member_id"], "section_id": section_id}, {"_id": 0}) or {}
        sets = {
            "guided_selections": clean_dict_of_lists(payload.guided_selections),
            "additional_ideas": clean_dict_of_lists(payload.additional_ideas),
            "stage_responses": {str(key)[:80]: str(value)[:6000] if isinstance(value, str) else clean_list(value)
                                for key, value in (payload.stage_responses or {}).items()},
            "final_response": clean_list(payload.final_response, max_chars=6000),
            "preferences": [
                {"option": str(pref.get("option", ""))[:300], "note": str(pref.get("note", ""))[:2000],
                 "involvement": str(pref.get("involvement", ""))[:80]}
                for pref in (payload.preferences or [])[:40] if isinstance(pref, dict) and str(pref.get("option", "")).strip()],
            "do_not_want": clean_list(payload.do_not_want),
            "group_game_ideas": clean_list(payload.group_game_ideas),
            "extras": payload.extras if isinstance(payload.extras, dict) else {},
            "game_version": 2,
            "updated_at": now,
        }
        if not existing.get("first_move_locked"):
            sets["first_response"] = clean_list(payload.first_response, max_chars=6000)
            if payload.first_move_locked:
                sets["first_move_locked"] = True
        sets["completed"] = True if complete else bool(existing.get("completed"))
        effective = {**existing, **sets}
        if section_id <= 4 and complete and not is_meaningful_game_response(response_texts(effective)):
            raise HTTPException(
                status_code=422,
                detail="Tell us your actual idea before continuing. A short answer such as 'Yes' does not give us enough to strengthen without inventing information.",
            )
        if response_input_hash(existing) != response_input_hash(effective):
            sets["fine_tuning"] = {}
            sets["approved_entries"] = []
            sets["approved_display"] = ""
        if complete:
            if not existing.get("completed_at"):
                sets["completed_at"] = now
            if not existing.get("first_move_locked") and not payload.first_move_locked:
                sets["first_move_locked"] = True
        await db.game_section_responses.update_one(
            {"board_member_id": record["member_id"], "section_id": section_id},
            {"$set": sets, "$setOnInsert": {
                "board_member_id": record["member_id"], "user_id": record["user_id"],
                "section_id": section_id, "created_at": now}},
            upsert=True)
        completed_count = await db.game_section_responses.count_documents(
            {"board_member_id": record["member_id"], "completed": True})
        member_sets = {"updated_at": now}
        total_sections = record.get("total_sections") or TOTAL_SECTIONS
        newly_completed = completed_count >= total_sections and not record.get("completed_at")
        if completed_count >= total_sections:
            member_sets["completed_at"] = now
        await db.game_board_members.update_one({"member_id": record["member_id"]}, {"$set": member_sets})
        if newly_completed and not record.get("is_primary"):
            try:
                owner = await db.members.find_one(
                    {"user_id": record["user_id"]}, {"_id": 0, "email": 1, "first_name": 1, "name": 1}) or {}
                owner_email = str(owner.get("email") or "").strip().lower()
                if owner_email:
                    profile = await get_profile(record["user_id"])
                    owner_name = owner.get("first_name") or str(owner.get("name") or "").split(" ")[0] or "there"
                    participant_name = record.get("full_name") or record.get("email") or "A participant"
                    origin = (os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com").rstrip("/")
                    view_url = f"{origin}/game/dashboard?response={record['member_id']}#bfg-board-members-section"
                    resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
                    await resend.Emails.send_async({
                        "from": os.environ["NONPROFIT_SENDER"], "to": [owner_email],
                        "subject": f"Board Fundraising Game Response Received | {participant_name}",
                        "html": email_html(
                            f"Hi {owner_name},\n\n{participant_name} has completed their Board Fundraising Game for "
                            f"{(profile.get('organization') or {}).get('name') or 'your organization'}.\n\n"
                            "Open their response to review every idea and participation choice.\n\nNonprofit Board Builder",
                            f"VIEW {str(participant_name).split(' ')[0].upper()}'S RESPONSE", view_url),
                    })
                    await db.game_board_members.update_one(
                        {"member_id": record["member_id"]},
                        {"$set": {"owner_notification_status": "Sent", "owner_notification_sent_at": now}})
            except Exception as exc:
                logger.exception("Game owner notification failed for %s", record["member_id"])
                await db.game_board_members.update_one(
                    {"member_id": record["member_id"]},
                    {"$set": {"owner_notification_status": "Failed", "owner_notification_error": str(exc)[:300]}})
        return completed_count

    @router.put("/game/play/{token}/section/{section_id}")
    async def save_play_section(token: str, section_id: int, payload: SectionSave):
        record = await playing_member(token)
        completed_count = await save_section(record, section_id, payload, complete=False)
        return {"status": "saved", "sections_completed": completed_count}

    @router.post("/game/play/{token}/section/{section_id}/complete")
    async def complete_play_section(token: str, section_id: int, payload: SectionSave):
        record = await playing_member(token)
        completed_count = await save_section(record, section_id, payload, complete=True)
        return {"status": "completed", "sections_completed": completed_count, "total_sections": record.get("total_sections") or TOTAL_SECTIONS}

    @router.get("/admin/game/v3-content")
    async def admin_read_v3(request: Request):
        await authenticate_admin(request, db)
        return {"content": await merged_v3()}

    @router.put("/admin/game/v3-content")
    async def admin_save_v3(payload: dict, request: Request):
        await authenticate_admin(request, db)
        content = {key: value for key, value in (payload or {}).items() if key in GAME_V3}
        await db.marketing_settings.update_one(
            {"key": "game_v3_content"}, {"$set": {"content": content, "updated_at": now_iso()}}, upsert=True)
        return {"content": await merged_v3()}

    return router
