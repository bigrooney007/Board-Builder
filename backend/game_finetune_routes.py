"""AI refinement for the teaching-first guided Individual Game.
One exact participant answer is compared with one improved version for each strategic area."""
import json
import os
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_service import parse_json_response
from rooney_intelligence import log_refinement
from game_response_quality import (
    is_meaningful_game_response,
    original_idea_text,
    response_input_hash,
)

SYSTEM_MESSAGE = """You are an experienced nonprofit fundraising strategist applying Rooney Akpesiri's fundraising process inside the Board Fundraising Game.
A participant learned one strategic area and submitted one answer. Your job:
1. Produce strengthened_text — a clearer, more specific, actionable, practical and executable organization of the participant's own ideas. This is a reflection step, not strategy generation. Do not teach a framework or add ideas the participant did not supply.
2. Preserve the participant's meaning and every materially useful idea. If the answer is already strong, improve only clarity, structure, completeness, specificity and operational detail. Never replace a good idea with a different idea.
3. Never invent specific entities: no invented businesses, foundations, grantmakers, LinkedIn or Facebook groups, associations, conferences, directories, networks, events, funders or donor names. If the organization supplied an entity, use it. Otherwise give the exact search method instead of a name.
4. Extract the individual ideas as structured entries for downstream use, preserving the writer's meaning.
5. If the response does not contain a usable idea, do not supply one from general fundraising knowledge. Never turn blanks, confirmations such as Yes, or other non-answers into a strategy.
Plain, direct language. Do not merely make vague ideas sound professional. Return only the required JSON."""

SECTION_TASKS = {
    1: "This answer describes who the participant thinks should fund the mission and why. ONLY strengthen and organize the audiences they supplied. Do not add new audiences. In strengthened_text use short listicles under INDIVIDUALS, BUSINESSES and GRANTORS, but only include a category when the participant actually supplied an idea for it. Each bullet must contain: a short findable/actionable audience profile name, then one concise sentence explaining the participant's reason that audience is likely to care or give. Do not write essays, prospecting instructions, decision-maker instructions, directories, search methods or fundraising strategy. Preserve the participant's thinking; make it specific enough to act on. Each structured entry is one supplied audience with audience_type individual, business or grantor.",
    2: "This answer describes where to consistently find the funders. Transform vague answers (LinkedIn, Google, events, networking, Facebook, community organizations) into executable prospecting instructions: for LinkedIn specify the type of person, relevant job titles, industry, geography, employer type and the search/filter method; for associations identify the type of association and how it relates to the audience; for directories the type of directory; for chambers what type of businesses to identify; for events the type of event and why the audience attends; for communities the type of community. If a specific verified group was supplied, use it; otherwise give the search process. Where an idea clearly relates to one of the approved audiences provided, set that audience on the entry. Each entry is one exact, executable prospecting instruction.",
    3: "This answer describes what to offer funders to attract their attention. Turn vague recommendations (create content, educate them, tell stories, host an event, build awareness, engage them) into actual activities identifying: what is being created or offered, who it is for, what issue it addresses, why that audience would care, where it will be distributed or delivered, and the next step after engagement. Use only mechanisms that make sense for this organization and audience. Where an idea clearly relates to one of the approved audiences provided, set that audience on the entry. Each entry is one concrete attraction activity.",
    4: "This answer describes the participant's own ideas for how the organization should raise money. ONLY organize and clarify the ideas they supplied so they are practical and executable. Do not introduce, map to, evaluate against or mention KNOW, LIKE, TRUST, ASK, FOLLOW UP or STEWARD. Do not tell them what stages are missing. Do not replace their process with our framework. Keep their own sequence and meaning, turning scrambled thoughts into a short practical set of actions. The complete strategy will apply the organization's framework later.",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionEntry(BaseModel):
    entry_id: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    text: str = Field(default="", max_length=6000)


class DecisionsPayload(BaseModel):
    entries: list[DecisionEntry] = Field(default_factory=list)


def create_finetune_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def playing_member(token: str) -> dict:
        record = await db.game_board_members.find_one({"token": token, "removed": {"$ne": True}}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This game link is not valid")
        return record

    async def get_response(record: dict, section_id: int) -> dict:
        if section_id < 1 or section_id > 4:
            raise HTTPException(status_code=404, detail="Unknown strategic area")
        response = await db.game_section_responses.find_one(
            {"board_member_id": record["member_id"], "section_id": section_id}, {"_id": 0})
        if not response:
            raise HTTPException(status_code=409, detail="Complete this strategic area before fine-tuning")
        return response

    def state_payload(response: dict) -> dict:
        fine_tuning = response.get("fine_tuning") or {}
        return {
            "proposals": fine_tuning.get("proposals", []),
            "completed": bool(fine_tuning.get("completed")),
            "approved_entries": response.get("approved_entries", []),
        }

    async def run_finetune(record: dict, section_id: int, text: str, profile: dict) -> dict:
        organization = profile.get("organization") or {}
        context = {
            "organization_name": organization.get("name", ""),
            "mission": organization.get("mission", ""),
            "who_the_organization_serves": organization.get("who_served", ""),
            "location": organization.get("location", ""),
        }
        audiences = []
        if section_id in (2, 3):
            area1 = await db.game_section_responses.find_one(
                {"board_member_id": record["member_id"], "section_id": 1},
                {"_id": 0, "approved_entries": 1}) or {}
            audiences = [entry.get("text", "") for entry in (area1.get("approved_entries") or []) if entry.get("text")]
        schema = {"strengthened_text": "string — the strengthened, exact, actionable and executable version",
                  "entries": [{"original": "string — the writer's idea in their own words",
                               "refined": "string — the strengthened actionable version of that idea",
                               "audience_type": "individual | business | grantor | empty string",
                               "audience": "string — matching approved audience when clear, else empty string"}]}
        prompt = (
            f"ORGANIZATION CONTEXT:\n{json.dumps(context, indent=1)}\n\n"
            + (f"APPROVED AUDIENCES FROM AREA 1:\n{json.dumps(audiences, indent=1)}\n\n" if audiences else "")
            + f"TASK: {SECTION_TASKS[section_id]}\n\n"
            + f"THE WRITER'S EXACT ANSWER (after teaching):\n{text}\n\n"
            + "Respond with ONE JSON object matching exactly this schema. Return only JSON — no markdown, no commentary:\n"
            + json.dumps(schema, indent=1)
        )
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
        model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
        chat = LlmChat(api_key=api_key, session_id=f"bfg-finetune-{uuid.uuid4()}",
                       system_message=SYSTEM_MESSAGE).with_model("anthropic", model)
        raw = await chat.send_message(UserMessage(text=prompt))
        data = parse_json_response(raw if isinstance(raw, str) else getattr(raw, "text", str(raw)))
        refined_text = str(data.get("strengthened_text") or data.get("refined_text") or "").strip()[:8000] or text
        entries = []
        for index, item in enumerate(data.get("entries") or []):
            if not isinstance(item, dict):
                continue
            entries.append({
                "entry_id": f"e{index}",
                "original": str(item.get("original") or "").strip()[:2000],
                "refined": str(item.get("refined") or "").strip()[:2000],
                "audience_type": str(item.get("audience_type") or "").strip()[:20],
                "audience": str(item.get("audience") or "").strip()[:400],
            })
        entries = [entry for entry in entries if entry["refined"] or entry["original"]]
        return {"refined_text": refined_text, "entries": entries}

    @router.post("/game/play/{token}/fine-tune/{section_id}")
    async def fine_tune_section(token: str, section_id: int):
        record = await playing_member(token)
        response = await get_response(record, section_id)
        text = original_idea_text(response)
        current_hash = response_input_hash(response)
        if not is_meaningful_game_response(text):
            raise HTTPException(
                status_code=422,
                detail="Tell us your actual idea before continuing. We will not invent a fundraising strategy from a blank answer or a response such as 'Yes'.",
            )
        fine_tuning = response.get("fine_tuning") or {}
        if fine_tuning.get("input_hash") == current_hash and fine_tuning.get("proposals") is not None:
            return state_payload(response)
        profile = await db.game_profiles.find_one({"user_id": record["user_id"]}, {"_id": 0}) or {}
        try:
            result = await run_finetune(record, section_id, text, profile)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="We could not refine your idea right now. Please try again.") from exc
        proposals = [{"entry_id": "main", "original": text, "refined": result["refined_text"],
                      "original_is_verbatim": True}]
        await db.game_section_responses.update_one(
            {"board_member_id": record["member_id"], "section_id": section_id},
            {"$set": {"fine_tuning": {"input_hash": current_hash, "proposals": proposals,
                                      "structured": result["entries"], "completed": False,
                                      "generated_at": now_iso()},
                      "updated_at": now_iso()}})
        return {"proposals": proposals, "completed": False, "approved_entries": []}

    @router.post("/game/play/{token}/fine-tune/{section_id}/decisions")
    async def save_decisions(token: str, section_id: int, payload: DecisionsPayload):
        record = await playing_member(token)
        response = await get_response(record, section_id)
        current_hash = response_input_hash(response)
        fine_tuning = response.get("fine_tuning") or {}
        proposals = fine_tuning.get("proposals") or []
        if not proposals:
            raise HTTPException(status_code=409, detail="Run fine-tuning before saving your decision")
        if fine_tuning.get("input_hash") != current_hash:
            raise HTTPException(status_code=409, detail="Your answer changed. Review the newly improved version before choosing.")
        decision = next((entry.decision for entry in payload.entries if entry.entry_id == "main"), "")
        if decision not in {"use_ai", "keep_original"}:
            raise HTTPException(status_code=422, detail="Choose one of the two versions to continue")
        main = proposals[0]
        exact_original = original_idea_text(response)
        if not is_meaningful_game_response(exact_original):
            raise HTTPException(status_code=422, detail="Edit your answer and share an actual idea before continuing.")
        if not main.get("original_is_verbatim") or main.get("original") != exact_original:
            raise HTTPException(status_code=409, detail="Your original answer needs to be refreshed before you choose.")
        display_text = main["refined"] if decision == "use_ai" else main["original"]
        approved = []
        for entry in ((fine_tuning.get("structured") or []) if decision == "use_ai" else []):
            chosen = entry.get("refined") or entry.get("original") or ""
            if not chosen.strip():
                continue
            stored = chosen.strip()
            if section_id in (2, 3) and entry.get("audience"):
                stored = f"{entry['audience']} — {stored}"
            approved.append({
                "entry_id": entry.get("entry_id", ""), "text": stored[:2400], "chosen_text": chosen.strip()[:2000],
                "original": entry.get("original", ""), "refined": entry.get("refined", ""),
                "decision": decision, "audience_type": entry.get("audience_type", ""),
                "audience": entry.get("audience", ""),
            })
        if not approved:
            approved = [{"entry_id": "main", "text": display_text[:2400], "chosen_text": display_text[:2000],
                         "original": main["original"], "refined": main["refined"], "decision": decision,
                         "audience_type": "", "audience": ""}]
        now = now_iso()
        await db.game_section_responses.update_one(
            {"board_member_id": record["member_id"], "section_id": section_id},
            {"$set": {"approved_entries": approved, "approved_display": display_text[:8000],
                      "fine_tuning.completed": True, "fine_tuning.decision": decision,
                      "fine_tuning.completed_at": now, "updated_at": now}})
        try:
            profile = await db.game_profiles.find_one({"user_id": record["user_id"]}, {"_id": 0, "organization": 1}) or {}
            await log_refinement(
                db, user_id=record["user_id"], board_member_id=record["member_id"], section_id=section_id,
                first_response="", second_response=exact_original,
                complete_idea=main["original"], strengthened=main["refined"], decision=decision,
                org_category=(profile.get("organization") or {}).get("org_type", ""),
                mission_category=str((profile.get("organization") or {}).get("mission", ""))[:160])
        except Exception:
            pass
        return {"status": "approved", "approved_entries": approved}

    return router
