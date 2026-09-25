"""Board Fundraising Game Phase 4: Fundraising Strategy Engine (working + board-prioritised drafts).
One engine, deliberate single AI calls, versioned structured strategies, secure share links."""
import asyncio
import json
import os
import secrets
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ai_service import parse_json_response
from member_auth import authenticate_member, new_uuid, require_entitlement
from game_content import GAME_SECTION_DEFAULTS
from group_game_routes import AREA_DEFS, ROUND_DEFS, area_ideas
from strategy_pdf import build_strategy_pdf

GAME_ENTITLEMENT = "board_fundraising_game"
MODES = {"working": "working", "board_prioritized": "board_prioritized_draft"}

STRATEGY_SYSTEM_MESSAGE = """You are the Fundraising Strategy Engine for the Board Fundraising Game.
You think like an experienced nonprofit fundraising strategist using Rooney Akpesiri's fundraising process. Everything you produce must be exact, specific, actionable, practical, realistic and executable for this organization — ask internally: WHO exactly? WHERE exactly? WHY this audience? HOW exactly? What does the person responsible do next? What process needs to run consistently?
Never invent specific entities (businesses, foundations, grantmakers, LinkedIn or Facebook groups, associations, conferences, directories, networks, events, funders or donor names): use entities the organization supplied, otherwise give the exact search method.
Inspect the organization's current fundraising reality and existing processes. Preserve what the organization says is working and present it clearly. Do not fill missing pieces with your own recommendations. Never claim something is proven to work unless the organization indicated it produces results.
Where fundraising_process is produced, begin it with a how_this_process_works explanation: a short organization-specific description of who the process is for, why they have a reason to care, how it moves them toward financial support and why it fits — never generic boilerplate.
Your job is to turn structured organisation information and board fundraising ideas into a practical fundraising strategy that the organisation can actually use.
The strategy must be grounded in the organisation's fundraising goal, mission, current fundraising situation and the ideas contributed by its board.
When strategy_mode is board_prioritized, Board Priorities represent the strongest collective direction chosen during the Group Review Game. Build the main strategy around those priorities. Additional Board Ideas must remain secondary and must be preserved separately rather than discarded.
When strategy_mode is working, create the best working strategy possible from all information currently available. Do not describe any idea as board-approved, board-prioritised or adopted unless the supplied data explicitly establishes that status.
Do not invent facts, funders, organisations, relationships, commitments, results, financial information, tactics or recommendations.
You are an editor and strategist presenting the Board's own decisions. Preserve the substance and intent of every adopted idea. You may combine repetition, correct grammar, explain the connection between supplied ideas, and turn vague wording into practical action only when the supplied context supports the detail. Never replace a Board idea with your own.
The finished strategy is a proper plan, not meeting minutes. It contains: an executive summary stating the fundraising amount, purpose and deadline; who the organisation will raise money from across individuals, businesses and grantors and why each audience will support; where to find them; how to attract them and build credibility; what to ask each audience to fund and how much to ask; the step-by-step process for raising money from them; and the agreed role of every participating Board Member.
Write in Rooney Akpesiri's clear, direct, practical and explanatory style. Use complete paragraphs where explanation is needed and specific actions where execution is required.
Return only the required structured strategy output."""

GENERATION_RULES = """RULES:
- Use the organisation's actual information. Use the fundraising goal exactly as provided — never change the amount.
- Use the board's submitted ideas. Give Board Priorities greater weight in board_prioritized mode. Preserve Additional Board Ideas separately.
- Turn raw ideas into clear strategic language. Connect related board ideas where useful. Produce practical actions.
- Keep the writing direct and professional. Avoid fundraising jargon where plain language works. Avoid generic filler. Avoid repeating the same idea across multiple sections unnecessarily.
- Never invent donor names, company names, grantmaker names, existing relationships, board commitments, or amounts other than the fundraising goal supplied.
- Never claim the organisation currently has a system, material, person or relationship unless the supplied data says so.
- If information is missing, leave that part empty. Do not add a generic recommendation.
- Board Member names may appear only in board_roles, using the responsibilities they agreed to during the Group Game.
- In working mode do not label any idea as a board priority; in board_prioritized mode keep priorities and additional ideas clearly separate."""

OUTPUT_SCHEMA = {
    "executive_summary": "Two or three proper paragraphs explaining the exact fundraising amount, purpose, deadline and the Board's agreed approach without describing the meeting.",
    "fundraising_audiences": {
        "individuals": [{"title": "Audience profile", "explanation": "Why they have a reason to give", "focus": "What the organisation should focus on"}],
        "businesses": [{"title": "Business audience profile", "explanation": "Why they have a reason to support", "focus": "What the organisation should focus on"}],
        "grantors": [{"title": "Grantor profile", "explanation": "Why the mission and funding focus align", "focus": "What the organisation should focus on"}],
    },
    "where_to_find": {"priorities": [{"title": "Audience and place, channel or network", "explanation": "Where that audience can be found", "focus": "The practical repeatable way the organisation will reach that place"}], "additional_ideas": []},
    "attraction": {"priorities": [{"title": "Audience and attraction approach", "explanation": "The value, experience, content or credibility that will matter to them", "focus": "The practical action the organisation will take"}], "additional_ideas": []},
    "funding_ask": {
        "individuals": [{"title": "Funding purpose", "explanation": "The amount or range the Board agreed to ask", "focus": "How the ask connects to the goal"}],
        "businesses": [{"title": "Sponsorship or funding purpose", "explanation": "The amount or range the Board agreed to ask", "focus": "How the ask connects to the goal"}],
        "grantors": [{"title": "Grant funding purpose", "explanation": "The amount or range the Board agreed to request", "focus": "How the request connects to the goal"}],
    },
    "fundraising_process": {
        "individuals": {"how_this_process_works": "string", "know": ["string"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
        "businesses": {"how_this_process_works": "string", "know": ["string"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
        "grantors": {"how_this_process_works": "string", "know": ["string"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
    },
    "board_roles": [{"name": "Board Member's real name", "role": "Agreed fundraising role", "responsibility": "Specific agreed action and timing, using only the discussion and transcript"}],
}

SECTION_ID_BY_KEY = {section["key"]: section["id"] for section in GAME_SECTION_DEFAULTS}
CORE_STRATEGY_KEYS = ["executive_summary", "fundraising_audiences", "where_to_find", "attraction", "funding_ask", "fundraising_process", "board_roles"]
EDITABLE_SECTION_KEYS = CORE_STRATEGY_KEYS


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generation_job_stale(job: dict, minutes: int = 10) -> bool:
    if not job or job.get("status") != "running" or not job.get("started_at"):
        return False
    try:
        started = datetime.fromisoformat(str(job["started_at"]).replace("Z", "+00:00"))
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - started).total_seconds() > minutes * 60
    except (TypeError, ValueError):
        return False


class GeneratePayload(BaseModel):
    mode: str = Field(min_length=1)


class OverridePayload(BaseModel):
    areas: dict = Field(default_factory=dict)


class SectionEditPayload(BaseModel):
    section_key: str = Field(min_length=1)
    text: str = Field(default="", max_length=40000)


def create_strategy_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def game_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        return member

    async def get_profile(user_id: str) -> dict:
        return await db.game_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}

    async def completed_group_session(user_id: str) -> dict:
        return await db.group_game_sessions.find_one(
            {"user_id": user_id, "status": "completed"}, {"_id": 0}, sort=[("completed_at", -1)]) or {}

    async def effective_priorities(session_id: str) -> dict:
        """Original group results with strategy overrides applied. Never mutates voting history."""
        override_doc = await db.group_game_overrides.find_one({"session_id": session_id}, {"_id": 0}) or {}
        override_areas = override_doc.get("areas") or {}
        results = await db.group_game_results.find({"session_id": session_id}, {"_id": 0}).sort("round_number", 1).to_list(20)
        areas = {}
        for row in results:
            items = {item["idea_id"]: item for item in row["results"]}
            original_priorities = [item for item in row["results"] if item["prioritised"]]
            original_additional = [item for item in row["results"] if not item["prioritised"]]
            override = override_areas.get(row["section_key"])
            if override:
                priorities = [items[idea_id] for idea_id in override.get("priorities", []) if idea_id in items]
                chosen = {item["idea_id"] for item in priorities}
                additional = [item for item in row["results"] if item["idea_id"] not in chosen]
            else:
                priorities, additional = original_priorities, original_additional
            areas[row["section_key"]] = {
                "section_key": row["section_key"], "round_number": row["round_number"], "title": row["title"],
                "priorities": priorities, "additional": additional,
                "original_priorities": original_priorities, "original_additional": original_additional,
                "overridden": bool(override),
            }
        return areas

    async def board_ideas_by_area(user_id: str) -> dict:
        members = await db.game_board_members.find(
            {"user_id": user_id, "removed": {"$ne": True}}, {"_id": 0, "member_id": 1, "full_name": 1}).to_list(200)
        names = {record["member_id"]: record.get("full_name") or "Board Member" for record in members}
        responses = await db.game_audience_responses.find(
            {"user_id": user_id, "board_member_id": {"$in": list(names)}, "completed": True}, {"_id": 0}).to_list(300)
        collected = {definition["key"]: [] for definition in AREA_DEFS}
        field_map = {"funding_audiences": "audience", "where_to_find": "where", "attraction": "attraction",
                     "funding_ask": "funding_ask", "fundraising_process": "process"}
        labels = {"individuals": "Individuals", "businesses": "Businesses", "grantors": "Grantors"}
        for response in responses:
            for audience_key, answer in (response.get("audiences") or {}).items():
                if audience_key not in labels or (audience_key != "individuals" and not answer.get("enabled")):
                    continue
                for area_key, field in field_map.items():
                    value = str(answer.get(field) or "").strip()
                    if value:
                        reason = str(answer.get("reason") or "").strip()
                        suffix = f" | Why: {reason}" if area_key == "funding_audiences" and reason else ""
                        collected[area_key].append(f"{labels[audience_key]}: {value}{suffix}")
            if response.get("involvement"):
                collected["board_roles"].append(f"{names.get(response['board_member_id'], 'Board Member')}: {response['involvement']}")
        return collected

    async def participation_choices(user_id: str) -> list:
        members = await db.game_board_members.find(
            {"user_id": user_id, "removed": {"$ne": True}}, {"_id": 0, "member_id": 1, "full_name": 1}).to_list(200)
        choices = []
        for record in members:
            response = await db.game_audience_responses.find_one(
                {"board_member_id": record["member_id"], "completed": True}, {"_id": 0, "involvement": 1}) or {}
            if response.get("involvement"):
                choices.append({"name": record.get("full_name") or "Board Member",
                                "preferred_involvement": response["involvement"]})
        return choices

    async def assemble_context(user_id: str, mode: str) -> tuple:
        profile = await get_profile(user_id)
        situation = await db.game_situations.find_one({"user_id": user_id}, {"_id": 0}) or {}
        organization = profile.get("organization") or {}
        goal = profile.get("goal") or {}
        board_ideas = await board_ideas_by_area(user_id)
        current_reality = (situation.get("sections") or {}).get("current_reality") or {}
        current_funder_keys = {
            "current_individual_donor_profile", "current_individual_donor_where", "current_individual_donor_attraction", "current_individual_donor_support", "current_individual_donor_process",
            "current_business_profile", "current_business_where", "current_business_attraction", "current_business_support", "current_business_process",
            "current_grantor_profile", "current_grantor_where", "current_grantor_attraction", "current_grantor_support", "current_grantor_process",
            "current_individual_donors", "current_businesses", "current_grantors",
            "individual_fundraising_process", "business_fundraising_process", "grant_fundraising_process",
        }
        context = {
            "strategy_mode": mode,
            "organisation_profile": organization,
            "fundraising_goal": {
                "amount": f"${int(goal.get('amount') or 0):,}" if goal.get("amount") else "",
                "currency": "USD", "deadline": goal.get("deadline", ""),
                "purpose": goal.get("purpose", ""), "why_it_matters_now": goal.get("why_now", ""),
            },
            "current_funder_context": {key: value for key, value in current_reality.items() if key in current_funder_keys},
            "board_member_submitted_ideas_by_strategy_area": board_ideas,
            "participation_choices_of_people_playing_the_game": await participation_choices(user_id),
        }
        group_session_id = ""
        if mode == "board_prioritized":
            session = await completed_group_session(user_id)
            if not session:
                raise HTTPException(status_code=409, detail="Complete the Group Review Game before generating a Board-Prioritised Strategy")
            group_session_id = session["session_id"]
            areas = await effective_priorities(group_session_id)
            context["group_review_game_results"] = {
                key: {
                    "board_priorities_in_rank_order": [item["text"] for item in area["priorities"]],
                    "additional_board_ideas": [item["text"] for item in area["additional"]],
                } for key, area in areas.items()
            }
        return context, group_session_id

    async def run_generation(user_id: str, mode: str, requested_by: str):
        try:
            context, group_session_id = await assemble_context(user_id, mode)
            api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
            model = os.environ.get("FUNDRAISING_STRATEGY_MODEL", "claude-haiku-4-5-20251001")
            chat = LlmChat(api_key=api_key, session_id=f"bfg-strategy-{uuid.uuid4()}",
                           system_message=STRATEGY_SYSTEM_MESSAGE).with_model("anthropic", model)
            prompt = (
                f"strategy_mode: {mode}\n\n"
                f"STRUCTURED ORGANISATION INFORMATION (the only information you may use):\n{json.dumps(context, indent=1)}\n\n"
                f"{GENERATION_RULES}\n\n"
                "Respond with ONE JSON object matching exactly this schema (descriptions explain each field). "
                "Return only JSON — no markdown, no commentary:\n"
                + json.dumps(OUTPUT_SCHEMA, indent=1)
            )
            response = await chat.send_message(UserMessage(text=prompt))
            text = response if isinstance(response, str) else getattr(response, "text", str(response))
            generated = parse_json_response(text)
            data = {key: generated.get(key, {}) for key in CORE_STRATEGY_KEYS}
            version = await db.game_strategies.count_documents({"user_id": user_id, "mode": mode}) + 1
            member_doc = await db.members.find_one({"user_id": user_id}, {"_id": 0, "first_name": 1, "last_name": 1}) or {}
            prepared_by = f"{member_doc.get('first_name', '')} {member_doc.get('last_name', '')}".strip()
            strategy = {
                "strategy_id": new_uuid(), "user_id": user_id, "mode": mode,
                "status": MODES[mode], "version": version, "schema_version": 4,
                "prepared_by": prepared_by,
                "share_token": secrets.token_urlsafe(24),
                "data": data, "section_edits": {},
                "group_session_id": group_session_id,
                "source_snapshot": {
                    "board_ideas_counts": {key: len(value) for key, value in (context.get("board_member_submitted_ideas_by_strategy_area") or {}).items()},
                    "used_group_results": mode == "board_prioritized",
                },
                "generated_at": now_iso(), "created_at": now_iso(),
                "last_edited_at": "", "last_edited_by": "", "review_completed_at": "",
            }
            await db.game_strategies.insert_one(strategy.copy())
            await db.game_strategy_jobs.update_one(
                {"user_id": user_id, "mode": mode},
                {"$set": {"status": "done", "strategy_id": strategy["strategy_id"], "error": "", "finished_at": now_iso()}})
        except Exception:
            await db.game_strategy_jobs.update_one(
                {"user_id": user_id, "mode": mode},
                {"$set": {"status": "failed", "error": "generation_failed", "finished_at": now_iso()}})

    # ---------- Priority review (board_prioritized pre-generation) ----------

    @router.get("/game/strategy/priority-review")
    async def priority_review(request: Request):
        member = await game_member(request)
        session = await completed_group_session(member["user_id"])
        if not session:
            raise HTTPException(status_code=409, detail="Complete the Group Review Game first")
        areas = await effective_priorities(session["session_id"])
        ordered = [areas[definition["section_key"]] for definition in ROUND_DEFS if definition["section_key"] in areas]
        return {"session_id": session["session_id"], "areas": [{
            "section_key": area["section_key"], "title": area["title"], "overridden": area["overridden"],
            "priorities": [{"idea_id": item["idea_id"], "text": item["text"],
                            "originally_prioritised": any(orig["idea_id"] == item["idea_id"] for orig in area["original_priorities"])}
                           for item in area["priorities"]],
            "additional": [{"idea_id": item["idea_id"], "text": item["text"],
                            "originally_prioritised": any(orig["idea_id"] == item["idea_id"] for orig in area["original_priorities"])}
                           for item in area["additional"]],
        } for area in ordered]}

    @router.put("/game/strategy/priority-review")
    async def save_priority_review(payload: OverridePayload, request: Request):
        member = await game_member(request)
        session = await completed_group_session(member["user_id"])
        if not session:
            raise HTTPException(status_code=409, detail="Complete the Group Review Game first")
        clean = {}
        valid_keys = {definition["section_key"] for definition in ROUND_DEFS}
        for key, value in (payload.areas or {}).items():
            if key in valid_keys and isinstance(value, dict):
                clean[key] = {
                    "priorities": [str(idea_id) for idea_id in value.get("priorities", [])][:100],
                    "additional": [str(idea_id) for idea_id in value.get("additional", [])][:200],
                }
        await db.group_game_overrides.update_one(
            {"session_id": session["session_id"]},
            {"$set": {"areas": clean, "updated_at": now_iso(), "updated_by": member["user_id"]},
             "$setOnInsert": {"session_id": session["session_id"], "user_id": member["user_id"], "created_at": now_iso()}},
            upsert=True)
        return {"status": "saved"}

    # ---------- Generation ----------

    @router.post("/game/strategy/generate")
    async def generate_strategy(payload: GeneratePayload, request: Request):
        member = await game_member(request)
        if payload.mode not in MODES:
            raise HTTPException(status_code=422, detail="Unknown strategy mode")
        job = await db.game_strategy_jobs.find_one({"user_id": member["user_id"], "mode": payload.mode}, {"_id": 0})
        if job and job.get("status") == "running" and not generation_job_stale(job):
            return {"status": "running"}
        if payload.mode == "board_prioritized":
            session = await completed_group_session(member["user_id"])
            if not session:
                raise HTTPException(status_code=409, detail="Complete the Group Review Game before generating a Board-Prioritised Strategy")
        await db.game_strategy_jobs.update_one(
            {"user_id": member["user_id"], "mode": payload.mode},
            {"$set": {"status": "running", "error": "", "strategy_id": "", "started_at": now_iso(), "finished_at": ""},
             "$setOnInsert": {"user_id": member["user_id"], "mode": payload.mode}},
            upsert=True)
        asyncio.create_task(run_generation(member["user_id"], payload.mode, member["user_id"]))
        return {"status": "running"}

    @router.get("/game/strategy/status")
    async def generation_status(request: Request, mode: str = "working"):
        member = await game_member(request)
        job = await db.game_strategy_jobs.find_one({"user_id": member["user_id"], "mode": mode}, {"_id": 0})
        if not job:
            return {"status": "idle"}
        if generation_job_stale(job):
            await db.game_strategy_jobs.update_one(
                {"user_id": member["user_id"], "mode": mode, "status": "running"},
                {"$set": {"status": "failed", "error": "generation_timed_out", "finished_at": now_iso()}})
            return {"status": "failed", "strategy_id": "", "error": "generation_timed_out"}
        return {"status": job.get("status", "idle"), "strategy_id": job.get("strategy_id", ""), "error": job.get("error", "")}

    @router.get("/game/strategies")
    async def list_strategies(request: Request):
        member = await game_member(request)
        rows = await db.game_strategies.find(
            {"user_id": member["user_id"]},
            {"_id": 0, "strategy_id": 1, "mode": 1, "status": 1, "version": 1, "generated_at": 1, "share_token": 1, "adopted_at": 1}
        ).sort("generated_at", -1).to_list(100)
        return {"strategies": rows}

    @router.get("/game/strategy/view/{strategy_id}")
    async def get_strategy(strategy_id: str, request: Request):
        member = await game_member(request)
        strategy = await db.game_strategies.find_one(
            {"strategy_id": strategy_id, "user_id": member["user_id"]}, {"_id": 0})
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        profile = await get_profile(member["user_id"])
        strategy["organization_name"] = (profile.get("organization") or {}).get("name", "")
        return {"strategy": strategy}

    @router.get("/game/strategy/view/{strategy_id}/download")
    async def download_strategy(strategy_id: str, request: Request):
        member = await game_member(request)
        strategy = await db.game_strategies.find_one(
            {"strategy_id": strategy_id, "user_id": member["user_id"]}, {"_id": 0})
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        profile = await get_profile(member["user_id"])
        org_name = (profile.get("organization") or {}).get("name", "")
        pdf = build_strategy_pdf(strategy, org_name)
        return Response(content=pdf, media_type="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="fundraising-strategy-v{strategy["version"]}.pdf"'})

    @router.put("/game/strategy/view/{strategy_id}/section")
    async def edit_strategy_section(strategy_id: str, payload: SectionEditPayload, request: Request):
        member = await game_member(request)
        if payload.section_key not in EDITABLE_SECTION_KEYS:
            raise HTTPException(status_code=422, detail="Unknown strategy section")
        existing = await db.game_strategies.find_one(
            {"strategy_id": strategy_id, "user_id": member["user_id"]}, {"_id": 0, "status": 1})
        if existing and existing.get("status") == "adopted":
            raise HTTPException(status_code=409, detail="An adopted strategy is read-only")
        result = await db.game_strategies.update_one(
            {"strategy_id": strategy_id, "user_id": member["user_id"]},
            {"$set": {f"section_edits.{payload.section_key}": payload.text,
                      "last_edited_at": now_iso(), "last_edited_by": member["user_id"]}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return {"status": "saved"}

    @router.post("/game/strategy/view/{strategy_id}/finish-review")
    async def finish_strategy_review(strategy_id: str, request: Request):
        member = await game_member(request)
        result = await db.game_strategies.update_one(
            {"strategy_id": strategy_id, "user_id": member["user_id"]},
            {"$set": {"review_completed_at": now_iso()}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return {"status": "review_complete"}

    # ---------- Public read-only share ----------

    @router.get("/strategy/shared/{share_token}")
    async def shared_strategy(share_token: str):
        strategy = await db.game_strategies.find_one({"share_token": share_token}, {"_id": 0})
        if not strategy:
            raise HTTPException(status_code=404, detail="This strategy link is not valid")
        profile = await get_profile(strategy["user_id"])
        return {"strategy": {
            "mode": strategy["mode"], "status": strategy["status"], "version": strategy["version"],
            "generated_at": strategy["generated_at"], "data": strategy["data"],
            "section_edits": strategy.get("section_edits", {}),
            "organization_name": (profile.get("organization") or {}).get("name", ""),
        }}

    return router
