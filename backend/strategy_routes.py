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
from pydantic import BaseModel, Field

from ai_service import parse_json_response
from member_auth import authenticate_member, new_uuid, require_entitlement
from game_content import GAME_SECTION_DEFAULTS
from group_game_routes import ROUND_DEFS, extract_ideas

GAME_ENTITLEMENT = "board_fundraising_game"
MODES = {"working": "working", "board_prioritized": "board_prioritized_draft"}

STRATEGY_SYSTEM_MESSAGE = """You are the Fundraising Strategy Engine for the Board Fundraising Game.
Your job is to turn structured organisation information and board fundraising ideas into a practical fundraising strategy that the organisation can actually use.
The strategy must be grounded in the organisation's fundraising goal, mission, current fundraising situation and the ideas contributed by its board.
When strategy_mode is board_prioritized, Board Priorities represent the strongest collective direction chosen during the Group Review Game. Build the main strategy around those priorities. Additional Board Ideas must remain secondary and must be preserved separately rather than discarded.
When strategy_mode is working, create the best working strategy possible from all information currently available. Do not describe any idea as board-approved, board-prioritised or adopted unless the supplied data explicitly establishes that status.
Do not invent facts, funders, organisations, relationships, commitments, results or financial information.
Where strategic information is missing, you may provide a concise recommendation, but clearly identify it as a recommendation rather than something supplied by the organisation or board.
Write for nonprofit leaders and board members. Use clear, direct, execution-ready language.
Return only the required structured strategy output."""

GENERATION_RULES = """RULES:
- Use the organisation's actual information. Use the fundraising goal exactly as provided — never change the amount.
- Use the board's submitted ideas. Give Board Priorities greater weight in board_prioritized mode. Preserve Additional Board Ideas separately.
- Turn raw ideas into clear strategic language. Connect related board ideas where useful. Produce practical actions.
- Keep the writing direct and professional. Avoid fundraising jargon where plain language works. Avoid generic filler. Avoid repeating the same idea across multiple sections unnecessarily.
- Never invent donor names, company names, grantmaker names, existing relationships, board commitments, or amounts other than the fundraising goal supplied.
- Never claim the organisation currently has a system, material, person or relationship unless the supplied data says so.
- Where board information is missing for a section and a recommendation is genuinely useful, provide it with "source": "recommendation" (or prefix plain-string items with "Recommended Action: "). If there is truly not enough information, return an empty array for that part — do not fabricate content.
- Do not expose individual board member names inside the strategy. It is a collective organisational document.
- In working mode do not label any idea as a board priority; in board_prioritized mode keep priorities and additional ideas clearly separate."""

OUTPUT_SCHEMA = {
    "executive_summary": "string — concise: the organisation, the fundraising goal, the deadline, what the money will support, the overall fundraising direction and the primary fundraising priorities",
    "fundraising_goal": {"amount": "string — exactly as supplied", "currency": "string", "deadline": "string", "purpose": "string",
                         "summary": "string — concise explanation of what the organisation is working to accomplish"},
    "fundraising_audiences": {"priorities": [{"title": "Audience Name", "explanation": "Why They Are A Good Fit — grounded in supplied information", "focus": "What We Should Focus On — concise strategic direction", "source": "board_priority | board_idea | recommendation"}], "additional_ideas": ["string"]},
    "where_to_find": {"priorities": [{"title": "Place / channel / network", "explanation": "How it connects the chosen audiences to the organisation — practical", "focus": "string", "source": "string"}], "additional_ideas": ["string — Additional Places And Channels To Consider"]},
    "attraction": {"priorities": [{"title": "Attraction activity", "explanation": "How it creates visibility, relevance and interest", "focus": "string", "source": "string"}], "additional_ideas": ["string — Additional Ideas To Consider"]},
    "fundraising_process": {"know": ["string"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
    "technology": {"priorities": [{"title": "Technology category (specific products only if the organisation or board named them)", "explanation": "What it is needed for", "focus": "How it supports execution", "source": "string"}], "additional_ideas": ["string"]},
    "fundraising_team": {"priorities": [{"title": "Role", "explanation": "Primary Responsibility", "focus": "Why This Role Matters", "source": "string"}], "additional_ideas": ["string — Additional Roles To Consider"]},
    "materials": {"priorities": [{"title": "Material", "explanation": "What It Will Be Used For", "focus": "Who It Supports", "source": "string"}], "additional_ideas": ["string — Additional Materials To Consider"]},
    "execution_timeline": {"set_up": ["string — use relative periods such as Weeks 1-2 / Month 2 unless exact dates are safely calculable from the deadline"], "launch": ["string"], "execute": ["string"], "review_and_improve": ["string"]},
    "additional_board_ideas": {"fundraising_audiences": ["string"], "where_to_find": ["string"], "attraction": ["string"], "fundraising_process": ["string"], "technology": ["string"], "fundraising_team": ["string"], "materials": ["string"], "execution_timeline": ["string"]},
    "next_step": "string — for working mode use exactly: 'This is a working strategy created from the information currently available. Continue collecting board input and update the strategy as your fundraising planning develops.' For board_prioritized mode use exactly: 'Your board has prioritised the ideas behind this strategy. The next step is to review the strategy together, make any final changes and adopt it as your organisation's working fundraising plan.'",
}

SECTION_ID_BY_KEY = {section["key"]: section["id"] for section in GAME_SECTION_DEFAULTS}
EDITABLE_SECTION_KEYS = ["executive_summary", "fundraising_goal", "fundraising_audiences", "where_to_find", "attraction",
                         "fundraising_process", "technology", "fundraising_team", "materials", "execution_timeline",
                         "additional_board_ideas", "next_step"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            {"user_id": user_id, "removed": {"$ne": True}}, {"_id": 0, "member_id": 1}).to_list(200)
        member_ids = [record["member_id"] for record in members]
        collected = {}
        for definition in ROUND_DEFS:
            section_id = SECTION_ID_BY_KEY.get(definition["section_key"])
            responses = await db.game_section_responses.find(
                {"user_id": user_id, "board_member_id": {"$in": member_ids}, "section_id": section_id}, {"_id": 0}).to_list(300)
            ideas = []
            for response in responses:
                ideas.extend(extract_ideas(response, definition["section_key"]))
            seen = set()
            unique = []
            for idea in ideas:
                key = " ".join(str(idea).lower().split())
                if key and key not in seen:
                    seen.add(key)
                    unique.append(str(idea).strip()[:400])
            collected[definition["section_key"]] = unique
        return collected

    async def assemble_context(user_id: str, mode: str) -> tuple:
        profile = await get_profile(user_id)
        situation = await db.game_situations.find_one({"user_id": user_id}, {"_id": 0}) or {}
        organization = profile.get("organization") or {}
        goal = profile.get("goal") or {}
        board_ideas = await board_ideas_by_area(user_id)
        context = {
            "strategy_mode": mode,
            "organisation_profile": organization,
            "fundraising_goal": {
                "amount": f"${int(goal.get('amount') or 0):,}" if goal.get("amount") else "",
                "currency": "USD", "deadline": goal.get("deadline", ""),
                "purpose": goal.get("purpose", ""), "why_it_matters_now": goal.get("why_now", ""),
            },
            "current_fundraising_situation": situation.get("sections", {}),
            "board_member_submitted_ideas_by_strategy_area": board_ideas,
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
            model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
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
            data = parse_json_response(text)
            for key in EDITABLE_SECTION_KEYS:
                data.setdefault(key, {} if key not in {"executive_summary", "next_step"} else "")
            version = await db.game_strategies.count_documents({"user_id": user_id, "mode": mode}) + 1
            strategy = {
                "strategy_id": new_uuid(), "user_id": user_id, "mode": mode,
                "status": MODES[mode], "version": version,
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
        if job and job.get("status") == "running":
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
        return {"status": job.get("status", "idle"), "strategy_id": job.get("strategy_id", "")}

    @router.get("/game/strategies")
    async def list_strategies(request: Request):
        member = await game_member(request)
        rows = await db.game_strategies.find(
            {"user_id": member["user_id"]},
            {"_id": 0, "strategy_id": 1, "mode": 1, "status": 1, "version": 1, "generated_at": 1, "share_token": 1}
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

    @router.put("/game/strategy/view/{strategy_id}/section")
    async def edit_strategy_section(strategy_id: str, payload: SectionEditPayload, request: Request):
        member = await game_member(request)
        if payload.section_key not in EDITABLE_SECTION_KEYS:
            raise HTTPException(status_code=422, detail="Unknown strategy section")
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
