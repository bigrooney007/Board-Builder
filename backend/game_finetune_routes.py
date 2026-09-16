"""AI Fine-Tuning for the guided Individual Game.
The player's free-form SECOND RESPONSE is fine-tuned once per strategic area (input-hash deduped).
One proposal is shown (Your Idea vs Fine-Tuned Version). Structured entries are extracted behind the
scenes for Group Review / strategy generation and are stored on approval, phrased per the decision."""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_service import parse_json_response

SYSTEM_MESSAGE = """You are the AI Fine-Tuning assistant for the Board Fundraising Game.
A nonprofit board member wrote a free-form answer for one strategic area. Your job:
1. Rewrite the answer into a clearer, better organized version (refined_text) that preserves EVERY idea and the writer's meaning. Make vague funder profiles specific and searchable using the organization context. Never invent audiences, places or ideas the answer does not support.
2. Extract the individual ideas as structured entries for downstream use, preserving the writer's meaning.
Plain, direct language. Return only the required JSON."""

SECTION_TASKS = {
    1: "This answer describes who should fund the mission. In refined_text, organize under PEOPLE, BUSINESSES and GRANTORS where useful. Each entry is one funder profile with audience_type set to individual, business or grantor, refined into an exact searchable ideal-funder profile.",
    2: "This answer describes where to consistently find the funders. Where an idea clearly relates to one of the approved audiences provided, set that audience on the entry. Each entry is one specific, searchable place, network, platform, directory, association or event.",
    3: "This answer describes what to offer funders to attract their attention. Where an idea clearly relates to one of the approved audiences provided, set that audience on the entry. Each entry is one concrete attraction offer. Do not invent unrelated lead magnets, campaigns or events.",
    4: "This answer describes how the organization will raise money. In refined_text, organize relevant ideas under KNOW, LIKE, TRUST, ASK, FOLLOW UP and STEWARD where useful. Each entry is one clear, actionable process statement.",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def second_response_text(response: dict) -> str:
    extras = response.get("extras") or {}
    text = str(extras.get("second_response") or "").strip()
    if text:
        return text
    return "\n".join(str(item).strip() for item in (response.get("final_response") or []) if str(item).strip())


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
        schema = {"refined_text": "string — the organized fine-tuned version of the whole answer",
                  "entries": [{"original": "string — the writer's idea in their own words",
                               "refined": "string — the fine-tuned version of that idea",
                               "audience_type": "individual | business | grantor | empty string",
                               "audience": "string — matching approved audience when clear, else empty string"}]}
        prompt = (
            f"ORGANIZATION CONTEXT:\n{json.dumps(context, indent=1)}\n\n"
            + (f"APPROVED AUDIENCES FROM AREA 1:\n{json.dumps(audiences, indent=1)}\n\n" if audiences else "")
            + f"TASK: {SECTION_TASKS[section_id]}\n\n"
            + f"THE WRITER'S ANSWER:\n{text}\n\n"
            + "Respond with ONE JSON object matching exactly this schema. Return only JSON — no markdown, no commentary:\n"
            + json.dumps(schema, indent=1)
        )
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
        model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
        chat = LlmChat(api_key=api_key, session_id=f"bfg-finetune-{uuid.uuid4()}",
                       system_message=SYSTEM_MESSAGE).with_model("anthropic", model)
        raw = await chat.send_message(UserMessage(text=prompt))
        data = parse_json_response(raw if isinstance(raw, str) else getattr(raw, "text", str(raw)))
        refined_text = str(data.get("refined_text") or "").strip()[:8000] or text
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
        text = second_response_text(response)
        current_hash = hashlib.sha256(text.encode()).hexdigest()
        fine_tuning = response.get("fine_tuning") or {}
        if fine_tuning.get("input_hash") == current_hash and fine_tuning.get("proposals") is not None:
            return state_payload(response)
        if not text:
            await db.game_section_responses.update_one(
                {"board_member_id": record["member_id"], "section_id": section_id},
                {"$set": {"fine_tuning": {"input_hash": current_hash, "proposals": [], "structured": [],
                                          "completed": True, "generated_at": now_iso()},
                          "approved_entries": [], "updated_at": now_iso()}})
            return {"proposals": [], "completed": True, "approved_entries": []}
        profile = await db.game_profiles.find_one({"user_id": record["user_id"]}, {"_id": 0}) or {}
        try:
            result = await run_finetune(record, section_id, text, profile)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="We could not refine your idea right now. Please try again.") from exc
        proposals = [{"entry_id": "main", "original": text, "refined": result["refined_text"]}]
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
        fine_tuning = response.get("fine_tuning") or {}
        proposals = fine_tuning.get("proposals") or []
        if not proposals:
            raise HTTPException(status_code=409, detail="Run fine-tuning before saving your decision")
        decision = next((entry.decision for entry in payload.entries if entry.entry_id == "main"), "")
        if decision not in {"use_ai", "keep_original"}:
            raise HTTPException(status_code=422, detail="Choose one of the two versions to continue")
        main = proposals[0]
        display_text = main["refined"] if decision == "use_ai" else main["original"]
        approved = []
        for entry in fine_tuning.get("structured") or []:
            chosen = (entry.get("refined") if decision == "use_ai" else entry.get("original")) or entry.get("refined") or entry.get("original") or ""
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
        return {"status": "approved", "approved_entries": approved}

    return router
