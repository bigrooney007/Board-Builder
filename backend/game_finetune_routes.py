"""Board Fundraising Game V3: AI Fine-Tuning of strategic ideas (paid organizations only).
One efficient AI call per strategic answer; the participant approves, keeps or edits every idea."""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_service import parse_json_response

GAME_ENTITLEMENT = "board_fundraising_game"

SYSTEM_MESSAGE = """You are the AI Fine-Tuning assistant for the Board Fundraising Game.
Nonprofit board members contribute raw fundraising ideas. Your job is to fine-tune each idea into a specific, searchable, actionable version WITHOUT changing the participant's intent.
For funder audiences, turn broad descriptions into precise ideal-funder profiles someone could actually search for and find. Example: "Parents" becomes "Parents of children with autism in Greater Pittsburgh with the financial capacity to give".
Use the organization's mission, the people it serves and its location to make each idea specific. Never invent facts the idea and the organization context do not support.
Return exactly one fine-tuned entry per input idea, in the same order, echoing the original idea unchanged.
Keep each fine-tuned version to one or two sentences of plain, direct language. Return only the required JSON."""

SECTION_TASKS = {
    1: "Each input is a type of person, business or grantor meant to fund this mission. Fine-tune each one into an exact, searchable ideal-funder profile. Keep the supplied audience_type exactly as given (individual, business or grantor).",
    2: "Each input is a place or channel where a specific audience can be consistently found. Fine-tune each one into a specific, searchable place, network, platform, directory, association or event. Keep the supplied audience pairing exactly as given.",
    3: "Each input is something the organization can offer to attract a specific audience's attention. Fine-tune each one into a concrete, executable attraction offer. Keep the supplied audience pairing exactly as given.",
    4: "Each input describes part of how the organization will raise money. Fine-tune each one into a clear, actionable process statement aligned with KNOW, LIKE, TRUST, ASK, FOLLOW UP and STEWARD.",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def section_inputs(section_id: int, response: dict) -> list:
    extras = response.get("extras") or {}
    if section_id == 1:
        return [{"idea": str(item).strip(), "audience_type": audience_type}
                for audience_type, bucket in (("individual", "people"), ("business", "businesses"), ("grantor", "grantors"))
                for item in (extras.get(bucket) or []) if str(item).strip()]
    if section_id == 2:
        return [{"idea": str(item).strip(), "audience": str(audience)}
                for audience, items in (extras.get("places") or {}).items()
                for item in (items or []) if str(item).strip()]
    if section_id == 3:
        return [{"idea": str(item).strip(), "audience": str(audience)}
                for audience, items in (extras.get("ideas") or {}).items()
                for item in (items or []) if str(item).strip()]
    return [{"idea": str(item).strip()} for item in (response.get("final_response") or []) if str(item).strip()]


def inputs_hash(items: list) -> str:
    return hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()


class DecisionEntry(BaseModel):
    entry_id: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    text: str = Field(default="", max_length=4000)


class DecisionsPayload(BaseModel):
    entries: list[DecisionEntry] = Field(default_factory=list)


def create_finetune_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def playing_member(token: str) -> dict:
        record = await db.game_board_members.find_one({"token": token, "removed": {"$ne": True}}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This game link is not valid")
        org_member = await db.members.find_one({"user_id": record["user_id"]}, {"_id": 0, "entitlements": 1}) or {}
        if GAME_ENTITLEMENT not in org_member.get("entitlements", []):
            raise HTTPException(status_code=402, detail="AI fine-tuning unlocks after your organization's game is unlocked")
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

    async def run_finetune(record: dict, section_id: int, items: list, profile: dict) -> list:
        organization = profile.get("organization") or {}
        goal = profile.get("goal") or {}
        context = {
            "organization_name": organization.get("name", ""),
            "mission": organization.get("mission", ""),
            "who_the_organization_serves": organization.get("who_served", ""),
            "location": organization.get("location", ""),
            "fundraising_goal": f"${int(goal.get('amount') or 0):,}" if goal.get("amount") else "",
        }
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
        model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
        chat = LlmChat(api_key=api_key, session_id=f"bfg-finetune-{uuid.uuid4()}",
                       system_message=SYSTEM_MESSAGE).with_model("anthropic", model)
        schema = {"entries": [{"original": "string — the input idea echoed exactly", "refined": "string — the fine-tuned version",
                               "audience_type": "individual | business | grantor — only for funder-audience ideas, echo the supplied value",
                               "audience": "string — echo the supplied audience pairing when given, else empty string"}]}
        prompt = (
            f"ORGANIZATION CONTEXT:\n{json.dumps(context, indent=1)}\n\n"
            f"TASK: {SECTION_TASKS[section_id]}\n\n"
            f"INPUT IDEAS (fine-tune every one, same order):\n{json.dumps(items, indent=1)}\n\n"
            "Respond with ONE JSON object matching exactly this schema. Return only JSON — no markdown, no commentary:\n"
            + json.dumps(schema, indent=1)
        )
        raw = await chat.send_message(UserMessage(text=prompt))
        text = raw if isinstance(raw, str) else getattr(raw, "text", str(raw))
        data = parse_json_response(text)
        entries = data.get("entries") if isinstance(data.get("entries"), list) else []
        proposals = []
        for index, item in enumerate(items):
            match = entries[index] if index < len(entries) and isinstance(entries[index], dict) else {}
            proposals.append({
                "entry_id": f"e{index}",
                "original": item["idea"],
                "refined": str(match.get("refined") or item["idea"]).strip()[:2000],
                "audience_type": item.get("audience_type", "") or str(match.get("audience_type", ""))[:20],
                "audience": item.get("audience", ""),
            })
        return proposals

    @router.post("/game/play/{token}/fine-tune/{section_id}")
    async def fine_tune_section(token: str, section_id: int):
        record = await playing_member(token)
        response = await get_response(record, section_id)
        items = section_inputs(section_id, response)
        current_hash = inputs_hash(items)
        fine_tuning = response.get("fine_tuning") or {}
        if fine_tuning.get("input_hash") == current_hash and fine_tuning.get("proposals") is not None:
            return state_payload(response)
        if not items:
            await db.game_section_responses.update_one(
                {"board_member_id": record["member_id"], "section_id": section_id},
                {"$set": {"fine_tuning": {"input_hash": current_hash, "proposals": [], "completed": True,
                                          "generated_at": now_iso()},
                          "approved_entries": [], "updated_at": now_iso()}})
            return {"proposals": [], "completed": True, "approved_entries": []}
        profile = await db.game_profiles.find_one({"user_id": record["user_id"]}, {"_id": 0}) or {}
        try:
            proposals = await run_finetune(record, section_id, items, profile)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="We could not fine-tune your ideas right now. Please try again.") from exc
        await db.game_section_responses.update_one(
            {"board_member_id": record["member_id"], "section_id": section_id},
            {"$set": {"fine_tuning": {"input_hash": current_hash, "proposals": proposals, "completed": False,
                                      "generated_at": now_iso()},
                      "updated_at": now_iso()}})
        return {"proposals": proposals, "completed": False, "approved_entries": response.get("approved_entries", [])}

    @router.post("/game/play/{token}/fine-tune/{section_id}/decisions")
    async def save_decisions(token: str, section_id: int, payload: DecisionsPayload):
        record = await playing_member(token)
        response = await get_response(record, section_id)
        fine_tuning = response.get("fine_tuning") or {}
        proposals = {item["entry_id"]: item for item in fine_tuning.get("proposals", [])}
        if not proposals:
            raise HTTPException(status_code=409, detail="Run fine-tuning before saving your decisions")
        decisions = {entry.entry_id: entry for entry in payload.entries}
        approved = []
        for entry_id, proposal in proposals.items():
            decision = decisions.get(entry_id)
            if not decision or decision.decision not in {"use_ai", "keep_original", "edited"}:
                raise HTTPException(status_code=422, detail="Choose an option for every idea before saving")
            if decision.decision == "use_ai":
                chosen = proposal["refined"]
            elif decision.decision == "keep_original":
                chosen = proposal["original"]
            else:
                chosen = decision.text.strip()
                if not chosen:
                    raise HTTPException(status_code=422, detail="An edited idea cannot be empty")
            stored = chosen
            if section_id in (2, 3) and proposal.get("audience"):
                stored = f"{proposal['audience']} — {chosen}"
            approved.append({
                "entry_id": entry_id, "text": stored[:2400], "chosen_text": chosen[:2000],
                "original": proposal["original"], "refined": proposal["refined"],
                "decision": decision.decision,
                "audience_type": proposal.get("audience_type", ""),
                "audience": proposal.get("audience", ""),
            })
        now = now_iso()
        await db.game_section_responses.update_one(
            {"board_member_id": record["member_id"], "section_id": section_id},
            {"$set": {"approved_entries": approved, "fine_tuning.completed": True,
                      "fine_tuning.completed_at": now, "updated_at": now}})
        return {"status": "approved", "approved_entries": approved}

    return router
