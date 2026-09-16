"""Board Fundraising Game Phase 9: post-game handoff — adopted strategy delivery and board post-game pages."""
import html
import os
from datetime import datetime, timezone

import resend
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth_service import authenticate_admin
from member_auth import authenticate_member, require_entitlement
from game_night_routes import fmt_deadline, fmt_goal

GAME_ENTITLEMENT = "board_fundraising_game"
TOTAL_SECTIONS = 10

DEFAULT_POSTGAME_EMAIL = {
    "subject": "Your Board Fundraising Strategy Is Ready",
    "opening": "Thank you for participating in [Organization Name]'s Board Fundraising Game.",
    "strategy_ready": "Your board's final fundraising strategy is now ready.\n\nThe strategy brings together the ideas contributed by the board, the priorities selected during the Group Game and the decisions made during your board meeting.",
    "execution_next": "Start by reviewing the final strategy.\n\nThen click See How I Am Involved to view your personal Board Fundraising Portfolio and see exactly how you agreed to help.\n\nYou will also be able to access your Execution Materials and complete your Relationship Mapping Form.",
}

PORTFOLIO_SENT_STATUSES = {"sent", "change_requested", "approved", "materials_ready"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SendSelected(BaseModel):
    member_ids: list = Field(default_factory=list)
    origin_url: str = Field(min_length=1)


class SendOne(BaseModel):
    origin_url: str = Field(min_length=1)


def create_postgame_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def game_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        return member

    async def get_profile(user_id: str) -> dict:
        return await db.game_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}

    async def adopted_strategy(user_id: str):
        return await db.game_strategies.find_one(
            {"user_id": user_id, "status": "adopted"}, {"_id": 0}, sort=[("adopted_at", -1)])

    async def email_content() -> dict:
        doc = await db.marketing_settings.find_one({"key": "game_postgame_email"}, {"_id": 0}) or {}
        stored = doc.get("content") or {}
        return {key: (str(stored.get(key)).strip()[:8000] if isinstance(stored.get(key), str) and str(stored.get(key)).strip() else value)
                for key, value in DEFAULT_POSTGAME_EMAIL.items()}

    def token_map(profile: dict, first_name: str) -> dict:
        organization = profile.get("organization") or {}
        primary = profile.get("primary_user") or {}
        return {
            "[Board Member First Name]": first_name,
            "[Organization Name]": (organization.get("name") or "").strip() or "our organization",
            "[Organisation Name]": (organization.get("name") or "").strip() or "our organization",
            "[Fundraising Goal]": fmt_goal(profile),
            "[Fundraising Deadline]": fmt_deadline(profile) or "our deadline",
            "[Primary User Full Name]": primary.get("full_name", ""),
            "[Primary User Job Title]": primary.get("job_title", ""),
            "[Organization Website]": organization.get("website", ""),
        }

    def fill(text: str, mapping: dict) -> str:
        for token, replacement in mapping.items():
            text = text.replace(token, replacement)
        return text

    def paragraphs_html(text: str) -> str:
        return "".join(f"<p style='margin:14px 0;'>{html.escape(line.strip())}</p>"
                       for line in text.split("\n") if line.strip())

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

    def game_button(link: str, label: str) -> str:
        return (f"<p style='margin:22px 0;'><a href='{html.escape(link)}' "
                f"style='background:#4f46e5;color:#ffffff;padding:13px 26px;border-radius:999px;"
                f"text-decoration:none;font-weight:bold;display:inline-block;'>{html.escape(label)}</a></p>")

    async def send_strategy_email(member: dict, record: dict, profile: dict, strategy: dict, origin: str, content: dict):
        first = record["full_name"].split(" ")[0]
        mapping = token_map(profile, first)
        body = (
            f"<p style='margin:14px 0;'>Hi {html.escape(first)},</p>"
            + paragraphs_html(fill(content["opening"], mapping))
            + paragraphs_html(fill(content["strategy_ready"], mapping))
            + game_button(f"{origin.rstrip('/')}/game/final/{record['token']}", "View Final Fundraising Strategy")
            + paragraphs_html(fill(content["execution_next"], mapping))
            + "<p style='margin:22px 0 4px;'></p>" + signature_html(profile, member)
        )
        resend.api_key = os.environ["RESEND_API_KEY"]
        await resend.Emails.send_async({
            "from": os.environ["GAME_EMAIL_SENDER"], "to": [record["email"]],
            "reply_to": member["email"], "subject": fill(content["subject"], mapping),
            "html": f"<div style='max-width:600px;margin:auto;font-family:Arial,sans-serif;color:#111;line-height:1.6;'>{body}</div>",
        })

    async def record_delivery(user_id: str, strategy_id: str, record: dict, status: str, error: str = ""):
        now = now_iso()
        existing = await db.game_strategy_deliveries.find_one(
            {"strategy_id": strategy_id, "board_member_id": record["member_id"]}, {"_id": 0})
        sets = {"status": status, "email": record["email"], "member_name": record["full_name"],
                "error": error[:600], "updated_at": now}
        if status == "sent":
            if existing and existing.get("sent_at"):
                sets["last_resend_at"] = now
            else:
                sets["sent_at"] = now
        await db.game_strategy_deliveries.update_one(
            {"strategy_id": strategy_id, "board_member_id": record["member_id"]},
            {"$set": sets, "$setOnInsert": {
                "user_id": user_id, "strategy_id": strategy_id,
                "board_member_id": record["member_id"], "created_at": now}},
            upsert=True)

    async def deliver_to(member: dict, record: dict, profile: dict, strategy: dict, origin: str, content: dict) -> bool:
        try:
            await send_strategy_email(member, record, profile, strategy, origin, content)
            await record_delivery(member["user_id"], strategy["strategy_id"], record, "sent")
            return True
        except Exception as exc:  # noqa: BLE001
            await record_delivery(member["user_id"], strategy["strategy_id"], record, "delivery_failed", str(exc))
            return False

    async def active_members(user_id: str) -> list:
        return await db.game_board_members.find(
            {"user_id": user_id, "removed": {"$ne": True}}, {"_id": 0}).sort("created_at", 1).to_list(200)

    async def group_joined_ids(user_id: str) -> set:
        session = await db.group_game_sessions.find_one(
            {"user_id": user_id, "status": {"$ne": "archived"}}, {"_id": 0, "session_id": 1}, sort=[("created_at", -1)])
        if not session:
            return set()
        rows = await db.group_game_participants.find(
            {"session_id": session["session_id"]}, {"_id": 0, "board_member_id": 1}).to_list(300)
        return {row.get("board_member_id") for row in rows}

    async def portfolio_summary(user_id: str) -> dict:
        rows = await db.board_portfolios.find(
            {"user_id": user_id}, {"_id": 0, "portfolio_id": 1, "status": 1, "version": 1, "approved_version": 1}).to_list(300)
        approved = 0
        toolkits_ready = 0
        for row in rows:
            if row.get("status") in {"approved", "materials_ready"}:
                approved += 1
            toolkit = await db.execution_toolkits.find_one(
                {"portfolio_id": row["portfolio_id"],
                 "portfolio_version": row.get("approved_version") or row.get("version", 1),
                 "status": "ready"}, {"_id": 0, "toolkit_id": 1})
            if toolkit:
                toolkits_ready += 1
        return {"total": len(rows), "approved_count": approved, "toolkit_ready_count": toolkits_ready,
                "execution_ready": any(row.get("status") == "materials_ready" for row in rows)}

    async def journey_status(user_id: str, adopted, portfolios: dict) -> str:
        if portfolios["execution_ready"]:
            return "Execution Ready"
        if portfolios["total"] > 0:
            return "Moving Into Execution"
        if adopted:
            return "Strategy Adopted"
        if await db.meeting_review_sessions.find_one({"user_id": user_id}, {"_id": 0, "review_id": 1}):
            return "Strategy Review"
        session = await db.group_game_sessions.find_one(
            {"user_id": user_id, "status": {"$in": ["in_progress", "completed"]}}, {"_id": 0, "session_id": 1})
        if session:
            return "Game Night In Progress"
        invited = await db.game_board_members.count_documents(
            {"user_id": user_id, "removed": {"$ne": True}, "invitation_status": "invited"})
        night = await db.game_nights.find_one({"user_id": user_id}, {"_id": 0, "meeting_date": 1}) or {}
        if invited > 0 and night.get("meeting_date"):
            return "Ready For Game Night"
        if invited > 0:
            return "Board Preparing"
        return "Setting Up"

    async def game_status_for(member_id: str, invitation_status: str, total: int = 0) -> str:
        done = await db.game_section_responses.count_documents(
            {"board_member_id": member_id, "completed": True})
        if done >= (total or TOTAL_SECTIONS):
            return "Game Completed"
        if done > 0:
            return "Game In Progress"
        return "Invited" if invitation_status == "invited" else "Not Invited"

    # ---------- Host overview ----------

    @router.get("/game/postgame/overview")
    async def postgame_overview(request: Request):
        member = await game_member(request)
        profile = await get_profile(member["user_id"])
        strategy = await adopted_strategy(member["user_id"])
        portfolios = await portfolio_summary(member["user_id"])
        organization = (profile.get("organization") or {}).get("name", "")
        base = {
            "organization_name": organization,
            "goal_display": fmt_goal(profile), "deadline_display": fmt_deadline(profile),
            "journey_status": await journey_status(member["user_id"], strategy, portfolios),
            "portfolios": portfolios,
        }
        if not strategy:
            return {**base, "adopted": False}
        deliveries = {row["board_member_id"]: row for row in await db.game_strategy_deliveries.find(
            {"strategy_id": strategy["strategy_id"]}, {"_id": 0}).to_list(300)}
        joined = await group_joined_ids(member["user_id"])
        recipients = []
        sent_count = 0
        for record in await active_members(member["user_id"]):
            delivery = deliveries.get(record["member_id"]) or {}
            if delivery.get("status") == "sent":
                sent_count += 1
            recipients.append({
                "member_id": record["member_id"], "full_name": record["full_name"], "email": record["email"],
                "game_status": await game_status_for(record["member_id"], record.get("invitation_status", ""), record.get("total_sections") or 0),
                "group_joined": record["member_id"] in joined,
                "delivery": {
                    "status": delivery.get("status", "not_sent"),
                    "sent_at": delivery.get("sent_at", ""),
                    "last_resend_at": delivery.get("last_resend_at", ""),
                    "error": delivery.get("error", ""),
                },
            })
        return {
            **base, "adopted": True,
            "adopted_at": strategy.get("adopted_at", ""),
            "strategy_id": strategy["strategy_id"],
            "recipients": recipients,
            "sent_count": sent_count, "total_recipients": len(recipients),
        }

    # ---------- Strategy delivery ----------

    @router.post("/game/postgame/send")
    async def send_selected(payload: SendSelected, request: Request):
        member = await game_member(request)
        strategy = await adopted_strategy(member["user_id"])
        if not strategy:
            raise HTTPException(status_code=409, detail="Adopt a fundraising strategy before sending it to your board")
        selected = {str(member_id) for member_id in payload.member_ids}
        if not selected:
            raise HTTPException(status_code=422, detail="Select at least one board member")
        profile = await get_profile(member["user_id"])
        content = await email_content()
        sent = 0
        failed = []
        for record in await active_members(member["user_id"]):
            if record["member_id"] not in selected:
                continue
            if await deliver_to(member, record, profile, strategy, payload.origin_url, content):
                sent += 1
            else:
                failed.append({"member_id": record["member_id"], "full_name": record["full_name"], "email": record["email"]})
        return {"sent": sent, "failed": failed}

    @router.post("/game/postgame/send/{member_id}")
    async def send_one(member_id: str, payload: SendOne, request: Request):
        member = await game_member(request)
        strategy = await adopted_strategy(member["user_id"])
        if not strategy:
            raise HTTPException(status_code=409, detail="Adopt a fundraising strategy before sending it to your board")
        record = await db.game_board_members.find_one(
            {"member_id": member_id, "user_id": member["user_id"], "removed": {"$ne": True}}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Board member not found")
        profile = await get_profile(member["user_id"])
        content = await email_content()
        if await deliver_to(member, record, profile, strategy, payload.origin_url, content):
            return {"status": "sent"}
        raise HTTPException(status_code=502, detail="The strategy email could not be sent. Please try again.")

    # ---------- Board member post-game page (public via Group Game link + slot) ----------

    @router.get("/game/postgame/play/{token}")
    async def postgame_play(token: str, slot: str = ""):
        session = await db.group_game_sessions.find_one(
            {"token": token, "status": {"$ne": "archived"}}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="This Group Game link is not valid")
        strategy = await adopted_strategy(session["user_id"])
        if not strategy:
            return {"adopted": False}
        profile = await get_profile(session["user_id"])
        portfolio_state = "waiting"
        portfolio_token = ""
        if slot:
            record = await db.game_board_members.find_one(
                {"token": slot, "user_id": session["user_id"], "removed": {"$ne": True}}, {"_id": 0})
            if record:
                portfolio = await db.board_portfolios.find_one(
                    {"user_id": session["user_id"], "board_member_id": record["member_id"]},
                    {"_id": 0, "status": 1, "token": 1}, sort=[("created_at", -1)])
                if portfolio and portfolio.get("status") in PORTFOLIO_SENT_STATUSES:
                    portfolio_state = "sent"
                    portfolio_token = portfolio.get("token", "")
        return {
            "adopted": True,
            "organization_name": (profile.get("organization") or {}).get("name", ""),
            "goal_display": fmt_goal(profile), "deadline_display": fmt_deadline(profile),
            "strategy_share_token": strategy.get("share_token", ""),
            "portfolio_state": portfolio_state, "portfolio_token": portfolio_token,
        }

    # ---------- Admin: post-game communication ----------

    @router.get("/admin/game/postgame-email")
    async def admin_read_postgame_email(request: Request):
        await authenticate_admin(request, db)
        return {"content": await email_content()}

    @router.put("/admin/game/postgame-email")
    async def admin_save_postgame_email(payload: dict, request: Request):
        await authenticate_admin(request, db)
        content = {key: str(payload.get(key, "")).strip()[:8000] or DEFAULT_POSTGAME_EMAIL[key]
                   for key in DEFAULT_POSTGAME_EMAIL}
        await db.marketing_settings.update_one(
            {"key": "game_postgame_email"},
            {"$set": {"content": content, "updated_at": now_iso()}}, upsert=True)
        return {"content": content}

    return router
