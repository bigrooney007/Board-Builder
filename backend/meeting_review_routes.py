"""Board Fundraising Game Phase 5: Meeting Review, Transcript, Meeting Decisions, Final Strategy and Adoption.
Two deliberate AI calls only (Analyse Meeting Discussion, Generate Final Strategy). Polling-based screen sync."""
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
from strategy_routes import OUTPUT_SCHEMA, EDITABLE_SECTION_KEYS

GAME_ENTITLEMENT = "board_fundraising_game"

STRATEGY_SECTIONS = [
    ("fundraising_audiences", "Who We Will Raise Money From"),
    ("where_to_find", "Where We Will Find Them"),
    ("attraction", "How We Will Attract Their Attention"),
    ("fundraising_process", "How We Will Raise Money From Them"),
]
SECTION_KEYS = [key for key, _ in STRATEGY_SECTIONS]
SECTION_TITLES = dict(STRATEGY_SECTIONS)
TOTAL_SECTIONS = len(STRATEGY_SECTIONS)

FEEDBACK_TYPES = {"approve", "suggest_change", "needs_discussion"}
TRANSCRIPT_SOURCES = {"live_transcript", "manual_notes", "pasted_transcript"}

ANALYSIS_SYSTEM_MESSAGE = """You are analysing a nonprofit board's discussion while it reviews its fundraising strategy.
Your job is to identify the decisions the board appears to have made during the meeting.
Use the Board-Prioritised Draft, board member feedback, meeting transcript, meeting notes and manual edits as context.
Do not generate a new fundraising strategy.
Do not invent decisions.
Do not assume that an idea mentioned during discussion was accepted unless the discussion reasonably indicates agreement, approval, a decision or a clear direction.
Distinguish between confirmed decisions, suggested changes, unresolved discussion and execution commitments.
If the transcript is ambiguous, mark the matter as unresolved rather than guessing.
Preserve the meaning of the board's discussion.
Return only structured JSON."""

ANALYSIS_OUTPUT_SCHEMA = {
    "sections": [{
        "section_id": "string — one of the supplied strategy section keys",
        "section_title": "string",
        "decision_summary": "string — concise summary of what the board decided or discussed for this section; empty string if nothing",
        "proposed_changes": [{
            "action": "add|update|remove|reorder|keep",
            "target": "string — what part of the section the change applies to",
            "current_content": "string",
            "proposed_content": "string",
            "reason": "string — the reason extracted from the discussion",
        }],
        "unresolved_items": ["string"],
    }],
    "execution_commitments": [{
        "board_member_name": "string",
        "commitment_type": "system_building|direct_fundraising|other",
        "commitment": "string",
        "deadline": "string — empty if none identified",
        "context": "string",
    }],
    "general_unresolved_items": ["string"],
}

FINAL_SYSTEM_MESSAGE = """You are creating the Final Fundraising Strategy for a nonprofit organisation after its board has reviewed a Board-Prioritised Draft.
The organisation has already completed fundraising planning, individual board input, collective prioritisation and a board strategy review meeting.
Your job is to update the Board-Prioritised Draft using only the meeting decisions that were explicitly accepted by the organisation user.
Preserve Board Priorities unless an accepted meeting decision changes them.
Preserve Additional Board Ideas unless an accepted meeting decision moves, removes or modifies them.
Do not invent new decisions.
Do not invent donors, businesses, grantmakers, relationships, board commitments, amounts, deadlines or organisational information.
Do not include rejected proposed changes.
Do not convert unresolved discussion into a decision.
Keep the same structured fundraising strategy format as the Board-Prioritised Draft.
Write clearly, directly and professionally.
Return only the required structured JSON."""

FINAL_OUTPUT_SCHEMA = OUTPUT_SCHEMA


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def section_content(strategy: dict, key: str):
    edits = strategy.get("section_edits") or {}
    if edits.get(key):
        return edits[key]
    return (strategy.get("data") or {}).get(key)


class StartPayload(BaseModel):
    strategy_id: str = Field(min_length=1)


class SectionPayload(BaseModel):
    index: int = Field(ge=0, le=TOTAL_SECTIONS - 1)


class EditSectionPayload(BaseModel):
    section_key: str = Field(min_length=1)
    text: str = Field(default="", max_length=40000)


class TranscriptPayload(BaseModel):
    section_key: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=60000)
    source: str = Field(default="live_transcript")


class TranscriptEditPayload(BaseModel):
    text: str = Field(default="", max_length=60000)


class DecisionPayload(BaseModel):
    status: str = Field(min_length=1)
    edited_content: str = Field(default="", max_length=20000)
    resolution_text: str = Field(default="", max_length=20000)


class CommitmentPayload(BaseModel):
    review_status: str = Field(min_length=1)
    edited_commitment: str = Field(default="", max_length=20000)


class FinalReviewPayload(BaseModel):
    action: str = Field(min_length=1)
    index: int = Field(default=0, ge=0, le=TOTAL_SECTIONS - 1)


class AdoptPayload(BaseModel):
    confirmed: bool = False


class PlayerFeedbackPayload(BaseModel):
    slot_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1, max_length=120)
    section_key: str = Field(min_length=1)
    response_type: str = Field(min_length=1)
    comment: str = Field(default="", max_length=8000)


class PlayerFinalPayload(BaseModel):
    slot_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1, max_length=120)
    approval_status: str = Field(min_length=1)
    change_request: str = Field(default="", max_length=8000)


def create_meeting_review_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def game_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        return member

    async def get_profile(user_id: str) -> dict:
        return await db.game_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}

    async def active_review(user_id: str) -> dict:
        return await db.meeting_review_sessions.find_one(
            {"user_id": user_id}, {"_id": 0}, sort=[("started_at", -1)])

    async def require_review(user_id: str) -> dict:
        review = await active_review(user_id)
        if not review:
            raise HTTPException(status_code=404, detail="No Board Strategy Review session yet")
        return review

    async def get_strategy(user_id: str, strategy_id: str) -> dict:
        strategy = await db.game_strategies.find_one(
            {"strategy_id": strategy_id, "user_id": user_id}, {"_id": 0})
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return strategy

    async def section_feedback(review_id: str, section_key: str) -> list:
        return await db.meeting_section_feedback.find(
            {"review_id": review_id, "section_key": section_key}, {"_id": 0}).to_list(300)

    async def review_counts(review_id: str) -> dict:
        feedback_count = await db.meeting_section_feedback.count_documents({"review_id": review_id})
        transcript_available = await db.meeting_transcript_segments.count_documents(
            {"review_id": review_id, "source": {"$in": ["live_transcript", "pasted_transcript"]}}) > 0
        notes_available = await db.meeting_transcript_segments.count_documents(
            {"review_id": review_id, "source": "manual_notes"}) > 0
        manual_edit_count = await db.meeting_section_edit_history.count_documents({"review_id": review_id})
        return {"feedback_count": feedback_count, "transcript_available": transcript_available,
                "notes_available": notes_available, "manual_edit_count": manual_edit_count}

    # ---------- Host: session ----------

    @router.post("/game/meeting-review/start")
    async def start_review(payload: StartPayload, request: Request):
        member = await game_member(request)
        strategy = await get_strategy(member["user_id"], payload.strategy_id)
        if strategy.get("mode") != "board_prioritized":
            raise HTTPException(status_code=409, detail="Board Strategy Review starts from a Board-Prioritised Draft")
        existing = await db.meeting_review_sessions.find_one(
            {"user_id": member["user_id"], "strategy_id": payload.strategy_id, "status": {"$ne": "adopted"}},
            {"_id": 0}, sort=[("started_at", -1)])
        if existing:
            return {"review": existing}
        record = {
            "review_id": new_uuid(), "user_id": member["user_id"],
            "group_session_id": strategy.get("group_session_id", ""),
            "strategy_id": payload.strategy_id,
            "status": "reviewing", "current_section_index": 0,
            "final_strategy_id": "", "final_review_status": "", "final_section_index": 0,
            "transcript_consent": False,
            "analysis_status": "", "analysis_sections": [],
            "final_generation_status": "",
            "started_at": now_iso(), "review_completed_at": "", "decisions_processed_at": "",
            "final_strategy_created_at": "", "adopted_at": "", "updated_at": now_iso(),
        }
        await db.meeting_review_sessions.insert_one(record.copy())
        return {"review": record}

    @router.get("/game/meeting-review/state")
    async def review_state(request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        profile = await get_profile(member["user_id"])
        goal = profile.get("goal") or {}
        index = review.get("current_section_index", 0)
        key = SECTION_KEYS[index]
        feedback = await section_feedback(review["review_id"], key)
        joined = await db.group_game_participants.count_documents({"session_id": review["group_session_id"]})
        counts = await review_counts(review["review_id"])
        return {
            "review": review,
            "organization_name": (profile.get("organization") or {}).get("name", ""),
            "goal_display": f"${int(goal.get('amount') or 0):,}" if goal.get("amount") else "",
            "goal_deadline": goal.get("deadline", ""),
            "total_sections": TOTAL_SECTIONS,
            "current_section": {"index": index, "key": key, "title": SECTION_TITLES[key]},
            "section_feedback": {
                "approve": len([f for f in feedback if f["response_type"] == "approve"]),
                "suggest_change": len([f for f in feedback if f["response_type"] == "suggest_change"]),
                "needs_discussion": len([f for f in feedback if f["response_type"] == "needs_discussion"]),
                "comments": [{"name": f["name"], "response_type": f["response_type"], "comment": f.get("comment", "")}
                             for f in feedback if f.get("comment")],
            },
            "joined_count": joined,
            **counts,
        }

    @router.post("/game/meeting-review/section")
    async def set_section(payload: SectionPayload, request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        if review["status"] != "reviewing":
            raise HTTPException(status_code=409, detail="The strategy review is not in progress")
        await db.meeting_review_sessions.update_one(
            {"review_id": review["review_id"]},
            {"$set": {"current_section_index": payload.index, "updated_at": now_iso()}})
        return {"status": "moved", "index": payload.index}

    @router.put("/game/meeting-review/edit-section")
    async def edit_section(payload: EditSectionPayload, request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        if payload.section_key not in EDITABLE_SECTION_KEYS:
            raise HTTPException(status_code=422, detail="Unknown strategy section")
        strategy = await get_strategy(member["user_id"], review["strategy_id"])
        previous = section_content(strategy, payload.section_key)
        await db.meeting_section_edit_history.insert_one({
            "edit_id": new_uuid(), "review_id": review["review_id"],
            "section_key": payload.section_key,
            "previous_content": previous if isinstance(previous, str) else json.dumps(previous or {}),
            "updated_content": payload.text, "edited_at": now_iso(), "user_id": member["user_id"],
        })
        await db.game_strategies.update_one(
            {"strategy_id": review["strategy_id"], "user_id": member["user_id"]},
            {"$set": {f"section_edits.{payload.section_key}": payload.text,
                      "last_edited_at": now_iso(), "last_edited_by": member["user_id"]}})
        return {"status": "saved"}

    @router.post("/game/meeting-review/finish-review")
    async def finish_review(request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        if review["status"] == "reviewing":
            await db.meeting_review_sessions.update_one(
                {"review_id": review["review_id"]},
                {"$set": {"status": "review_complete", "review_completed_at": now_iso(), "updated_at": now_iso()}})
        counts = await review_counts(review["review_id"])
        return {"status": "review_complete", **counts}

    # ---------- Host: transcript ----------

    @router.post("/game/meeting-review/consent")
    async def transcript_consent(request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        await db.meeting_review_sessions.update_one(
            {"review_id": review["review_id"]},
            {"$set": {"transcript_consent": True, "updated_at": now_iso()}})
        return {"status": "confirmed"}

    @router.post("/game/meeting-review/transcript")
    async def add_transcript(payload: TranscriptPayload, request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        if payload.section_key not in SECTION_KEYS:
            raise HTTPException(status_code=422, detail="Unknown strategy section")
        source = payload.source if payload.source in TRANSCRIPT_SOURCES else "manual_notes"
        record = {
            "segment_id": new_uuid(), "review_id": review["review_id"],
            "section_key": payload.section_key, "text": payload.text.strip(),
            "source": source, "created_at": now_iso(), "updated_at": now_iso(),
        }
        await db.meeting_transcript_segments.insert_one(record.copy())
        return {"status": "saved", "segment_id": record["segment_id"]}

    @router.get("/game/meeting-review/transcript")
    async def get_transcript(request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        rows = await db.meeting_transcript_segments.find(
            {"review_id": review["review_id"]}, {"_id": 0}).sort("created_at", 1).to_list(2000)
        sections = []
        for key, title in STRATEGY_SECTIONS:
            segments = [row for row in rows if row["section_key"] == key]
            if segments:
                sections.append({"section_key": key, "title": title, "segments": segments})
        return {"sections": sections, "segment_count": len(rows)}

    @router.put("/game/meeting-review/transcript/{segment_id}")
    async def edit_transcript(segment_id: str, payload: TranscriptEditPayload, request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        result = await db.meeting_transcript_segments.update_one(
            {"segment_id": segment_id, "review_id": review["review_id"]},
            {"$set": {"text": payload.text, "updated_at": now_iso()}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Transcript segment not found")
        return {"status": "saved"}

    # ---------- Host: meeting analysis (AI ACTION 1) ----------

    async def assemble_analysis_context(user_id: str, review: dict) -> dict:
        profile = await get_profile(user_id)
        goal = profile.get("goal") or {}
        strategy = await get_strategy(user_id, review["strategy_id"])
        draft = {key: {"title": SECTION_TITLES[key], "content": section_content(strategy, key)} for key in SECTION_KEYS}
        edits = await db.meeting_section_edit_history.find(
            {"review_id": review["review_id"]}, {"_id": 0, "section_key": 1, "updated_content": 1, "edited_at": 1}).to_list(200)
        feedback = await db.meeting_section_feedback.find(
            {"review_id": review["review_id"]}, {"_id": 0, "section_key": 1, "name": 1, "response_type": 1, "comment": 1}).to_list(1000)
        segments = await db.meeting_transcript_segments.find(
            {"review_id": review["review_id"]}, {"_id": 0, "section_key": 1, "text": 1, "source": 1}).sort("created_at", 1).to_list(2000)
        transcript, notes = {}, {}
        for row in segments:
            bucket = notes if row["source"] == "manual_notes" else transcript
            bucket.setdefault(row["section_key"], []).append(row["text"])
        return {
            "organisation_profile": profile.get("organization") or {},
            "fundraising_goal": {
                "amount": f"${int(goal.get('amount') or 0):,}" if goal.get("amount") else "",
                "deadline": goal.get("deadline", ""), "purpose": goal.get("purpose", ""),
            },
            "strategy_section_keys": SECTION_KEYS,
            "board_prioritised_draft": draft,
            "manual_strategy_changes_made_during_review": edits,
            "board_member_section_feedback": {
                "approvals": [{"section": f["section_key"], "board_member": f["name"]} for f in feedback if f["response_type"] == "approve"],
                "suggested_changes": [{"section": f["section_key"], "board_member": f["name"], "suggestion": f.get("comment", "")} for f in feedback if f["response_type"] == "suggest_change"],
                "discussion_comments": [{"section": f["section_key"], "board_member": f["name"], "comment": f.get("comment", "")} for f in feedback if f["response_type"] == "needs_discussion"],
            },
            "meeting_transcript_by_section": transcript,
            "manual_meeting_notes_by_section": notes,
        }

    async def match_board_member(user_id: str, name: str) -> str:
        if not name:
            return ""
        members = await db.game_board_members.find(
            {"user_id": user_id, "removed": {"$ne": True}}, {"_id": 0, "member_id": 1, "full_name": 1}).to_list(200)
        lowered = name.strip().lower()
        for record in members:
            full = record["full_name"].strip().lower()
            if lowered == full or lowered == full.split(" ")[0]:
                return record["member_id"]
        for record in members:
            if lowered in record["full_name"].strip().lower():
                return record["member_id"]
        return ""

    async def run_analysis(user_id: str, review: dict):
        try:
            context = await assemble_analysis_context(user_id, review)
            api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
            model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
            chat = LlmChat(api_key=api_key, session_id=f"bfg-meeting-{uuid.uuid4()}",
                           system_message=ANALYSIS_SYSTEM_MESSAGE).with_model("anthropic", model)
            prompt = (
                "MEETING REVIEW CONTEXT (the only information you may use):\n"
                f"{json.dumps(context, indent=1)}\n\n"
                "Use the supplied strategy section keys as section_id values. "
                "Respond with ONE JSON object matching exactly this schema. Return only JSON — no markdown, no commentary:\n"
                + json.dumps(ANALYSIS_OUTPUT_SCHEMA, indent=1)
            )
            response = await chat.send_message(UserMessage(text=prompt))
            text = response if isinstance(response, str) else getattr(response, "text", str(response))
            data = parse_json_response(text)
            await db.meeting_decisions.delete_many({"review_id": review["review_id"]})
            await db.meeting_execution_commitments.delete_many({"review_id": review["review_id"]})
            summaries = []
            for section in data.get("sections") or []:
                key = section.get("section_id", "")
                if key not in SECTION_KEYS:
                    continue
                summaries.append({"section_key": key, "section_title": SECTION_TITLES[key],
                                  "decision_summary": str(section.get("decision_summary", ""))})
                for change in section.get("proposed_changes") or []:
                    await db.meeting_decisions.insert_one({
                        "decision_id": new_uuid(), "review_id": review["review_id"], "kind": "change",
                        "section_key": key, "section_title": SECTION_TITLES[key],
                        "decision_summary": str(section.get("decision_summary", "")),
                        "action": str(change.get("action", "update")), "target": str(change.get("target", "")),
                        "current_content": str(change.get("current_content", "")),
                        "proposed_content": str(change.get("proposed_content", "")),
                        "edited_content": "", "reason": str(change.get("reason", "")),
                        "resolution_text": "", "status": "proposed",
                        "created_at": now_iso(), "updated_at": now_iso(),
                    })
                for item in section.get("unresolved_items") or []:
                    await db.meeting_decisions.insert_one({
                        "decision_id": new_uuid(), "review_id": review["review_id"], "kind": "unresolved",
                        "section_key": key, "section_title": SECTION_TITLES[key],
                        "decision_summary": "", "action": "", "target": "",
                        "current_content": "", "proposed_content": str(item),
                        "edited_content": "", "reason": "", "resolution_text": "", "status": "unresolved",
                        "created_at": now_iso(), "updated_at": now_iso(),
                    })
            for item in data.get("general_unresolved_items") or []:
                await db.meeting_decisions.insert_one({
                    "decision_id": new_uuid(), "review_id": review["review_id"], "kind": "unresolved",
                    "section_key": "general", "section_title": "General Discussion",
                    "decision_summary": "", "action": "", "target": "",
                    "current_content": "", "proposed_content": str(item),
                    "edited_content": "", "reason": "", "resolution_text": "", "status": "unresolved",
                    "created_at": now_iso(), "updated_at": now_iso(),
                })
            for commitment in data.get("execution_commitments") or []:
                name = str(commitment.get("board_member_name", ""))
                await db.meeting_execution_commitments.insert_one({
                    "commitment_id": new_uuid(), "review_id": review["review_id"],
                    "board_member_id": await match_board_member(user_id, name),
                    "board_member_name": name,
                    "commitment_type": str(commitment.get("commitment_type", "other")),
                    "commitment": str(commitment.get("commitment", "")),
                    "deadline": str(commitment.get("deadline", "")),
                    "context": str(commitment.get("context", "")),
                    "review_status": "keep", "edited_commitment": "",
                    "created_at": now_iso(), "updated_at": now_iso(),
                })
            await db.meeting_review_sessions.update_one(
                {"review_id": review["review_id"]},
                {"$set": {"analysis_status": "done", "analysis_sections": summaries,
                          "status": "decisions_processed", "decisions_processed_at": now_iso(), "updated_at": now_iso()}})
        except Exception:
            await db.meeting_review_sessions.update_one(
                {"review_id": review["review_id"]},
                {"$set": {"analysis_status": "failed", "updated_at": now_iso()}})

    @router.post("/game/meeting-review/analyse")
    async def analyse_meeting(request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        if review.get("analysis_status") == "running":
            return {"status": "running"}
        result = await db.meeting_review_sessions.update_one(
            {"review_id": review["review_id"], "analysis_status": {"$ne": "running"}},
            {"$set": {"analysis_status": "running", "updated_at": now_iso()}})
        if result.modified_count == 0:
            return {"status": "running"}
        asyncio.create_task(run_analysis(member["user_id"], review))
        return {"status": "running"}

    @router.get("/game/meeting-review/analysis-status")
    async def analysis_status(request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        return {"status": review.get("analysis_status", "")}

    # ---------- Host: decisions review ----------

    @router.get("/game/meeting-review/decisions")
    async def get_decisions(request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        rows = await db.meeting_decisions.find(
            {"review_id": review["review_id"]}, {"_id": 0}).sort("created_at", 1).to_list(1000)
        commitments = await db.meeting_execution_commitments.find(
            {"review_id": review["review_id"]}, {"_id": 0}).sort("created_at", 1).to_list(500)
        sections = []
        for key, title in [*STRATEGY_SECTIONS, ("general", "General Discussion")]:
            changes = [row for row in rows if row["section_key"] == key and row["kind"] == "change"]
            unresolved = [row for row in rows if row["section_key"] == key and row["kind"] == "unresolved"]
            if changes or unresolved:
                summary = next((s["decision_summary"] for s in review.get("analysis_sections", []) if s["section_key"] == key), "")
                sections.append({"section_key": key, "section_title": title,
                                 "decision_summary": summary, "changes": changes, "unresolved": unresolved})
        return {"sections": sections, "commitments": commitments}

    @router.put("/game/meeting-review/decision/{decision_id}")
    async def update_decision(decision_id: str, payload: DecisionPayload, request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        decision = await db.meeting_decisions.find_one(
            {"decision_id": decision_id, "review_id": review["review_id"]}, {"_id": 0})
        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")
        updates = {"updated_at": now_iso()}
        if decision["kind"] == "change":
            if payload.status not in {"accepted", "rejected", "proposed"}:
                raise HTTPException(status_code=422, detail="Invalid decision status")
            updates["status"] = payload.status
            if payload.status == "accepted" and payload.edited_content:
                updates["edited_content"] = payload.edited_content
        else:
            if payload.status not in {"manually_resolved", "unresolved"}:
                raise HTTPException(status_code=422, detail="Invalid decision status")
            updates["status"] = payload.status
            updates["resolution_text"] = payload.resolution_text if payload.status == "manually_resolved" else ""
        await db.meeting_decisions.update_one({"decision_id": decision_id}, {"$set": updates})
        return {"status": "saved"}

    @router.put("/game/meeting-review/commitment/{commitment_id}")
    async def update_commitment(commitment_id: str, payload: CommitmentPayload, request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        if payload.review_status not in {"keep", "removed", "edited"}:
            raise HTTPException(status_code=422, detail="Invalid commitment status")
        result = await db.meeting_execution_commitments.update_one(
            {"commitment_id": commitment_id, "review_id": review["review_id"]},
            {"$set": {"review_status": payload.review_status,
                      "edited_commitment": payload.edited_commitment if payload.review_status == "edited" else "",
                      "updated_at": now_iso()}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Commitment not found")
        return {"status": "saved"}

    # ---------- Host: final strategy generation (AI ACTION 2) ----------

    async def run_final_generation(user_id: str, review: dict):
        try:
            profile = await get_profile(user_id)
            goal = profile.get("goal") or {}
            strategy = await get_strategy(user_id, review["strategy_id"])
            draft = {key: {"title": SECTION_TITLES[key], "content": section_content(strategy, key)} for key in SECTION_KEYS}
            accepted = await db.meeting_decisions.find(
                {"review_id": review["review_id"], "kind": "change", "status": "accepted"}, {"_id": 0}).to_list(500)
            resolved = await db.meeting_decisions.find(
                {"review_id": review["review_id"], "kind": "unresolved", "status": "manually_resolved"}, {"_id": 0}).to_list(500)
            context = {
                "organisation_profile": profile.get("organization") or {},
                "fundraising_goal": {
                    "amount": f"${int(goal.get('amount') or 0):,}" if goal.get("amount") else "",
                    "currency": "USD", "deadline": goal.get("deadline", ""), "purpose": goal.get("purpose", ""),
                },
                "board_prioritised_draft_being_updated": draft,
                "accepted_meeting_decisions": [{
                    "section": row["section_key"], "action": row["action"], "target": row["target"],
                    "current_content": row["current_content"],
                    "final_content": row["edited_content"] or row["proposed_content"],
                    "reason": row["reason"],
                } for row in accepted],
                "manually_resolved_meeting_items": [{
                    "section": row["section_key"], "item": row["proposed_content"], "decision": row["resolution_text"],
                } for row in resolved],
            }
            api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
            model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
            chat = LlmChat(api_key=api_key, session_id=f"bfg-final-{uuid.uuid4()}",
                           system_message=FINAL_SYSTEM_MESSAGE).with_model("anthropic", model)
            prompt = (
                "FINAL STRATEGY CONTEXT (the only information you may use):\n"
                f"{json.dumps(context, indent=1)}\n\n"
                "Update the Board-Prioritised Draft using only the accepted meeting decisions and manually resolved items. "
                "Where a draft section contains host-edited plain text, convert it into the required structured format while preserving its meaning. "
                "Respond with ONE JSON object matching exactly this schema (descriptions explain each field). "
                "Return only JSON — no markdown, no commentary:\n"
                + json.dumps(FINAL_OUTPUT_SCHEMA, indent=1)
            )
            response = await chat.send_message(UserMessage(text=prompt))
            text = response if isinstance(response, str) else getattr(response, "text", str(response))
            generated = parse_json_response(text)
            data = {key: generated.get(key, {}) for key in EDITABLE_SECTION_KEYS}
            version = await db.game_strategies.count_documents({"user_id": user_id, "mode": "final"}) + 1
            record = {
                "strategy_id": new_uuid(), "user_id": user_id, "mode": "final",
                "status": "final_draft", "version": version, "schema_version": 3,
                "share_token": secrets.token_urlsafe(24),
                "data": data, "section_edits": {},
                "group_session_id": review.get("group_session_id", ""),
                "meeting_review_id": review["review_id"],
                "source_strategy_id": review["strategy_id"],
                "generated_at": now_iso(), "created_at": now_iso(),
                "last_edited_at": "", "last_edited_by": "", "review_completed_at": "",
            }
            await db.game_strategies.insert_one(record.copy())
            await db.meeting_review_sessions.update_one(
                {"review_id": review["review_id"]},
                {"$set": {"final_generation_status": "done", "final_strategy_id": record["strategy_id"],
                          "status": "final_strategy_created", "final_strategy_created_at": now_iso(),
                          "final_review_status": "", "final_section_index": 0, "updated_at": now_iso()}})
        except Exception:
            await db.meeting_review_sessions.update_one(
                {"review_id": review["review_id"]},
                {"$set": {"final_generation_status": "failed", "updated_at": now_iso()}})

    @router.post("/game/meeting-review/generate-final")
    async def generate_final(request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        if review["status"] not in {"decisions_processed", "final_strategy_created"}:
            raise HTTPException(status_code=409, detail="Review the meeting decisions before generating the final strategy")
        if review.get("final_generation_status") == "running":
            return {"status": "running"}
        result = await db.meeting_review_sessions.update_one(
            {"review_id": review["review_id"], "final_generation_status": {"$ne": "running"}},
            {"$set": {"final_generation_status": "running", "updated_at": now_iso()}})
        if result.modified_count == 0:
            return {"status": "running"}
        asyncio.create_task(run_final_generation(member["user_id"], review))
        return {"status": "running"}

    @router.get("/game/meeting-review/final-status")
    async def final_status(request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        return {"status": review.get("final_generation_status", ""),
                "final_strategy_id": review.get("final_strategy_id", "")}

    # ---------- Host: final review + adoption ----------

    @router.post("/game/meeting-review/final-review")
    async def final_review(payload: FinalReviewPayload, request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        if review["status"] != "final_strategy_created":
            raise HTTPException(status_code=409, detail="No final strategy to review yet")
        if payload.action == "start":
            updates = {"final_review_status": "reviewing", "final_section_index": 0}
        elif payload.action == "section":
            updates = {"final_section_index": payload.index}
        elif payload.action == "finish":
            updates = {"final_review_status": "response"}
        else:
            raise HTTPException(status_code=422, detail="Unknown final review action")
        await db.meeting_review_sessions.update_one(
            {"review_id": review["review_id"]}, {"$set": {**updates, "updated_at": now_iso()}})
        return {"status": "saved"}

    @router.get("/game/meeting-review/approvals")
    async def get_approvals(request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        rows = await db.final_board_approvals.find(
            {"strategy_id": review.get("final_strategy_id", "")}, {"_id": 0}).sort("submitted_at", 1).to_list(300)
        joined = await db.group_game_participants.find(
            {"session_id": review["group_session_id"]}, {"_id": 0, "board_member_id": 1, "name": 1}).to_list(300)
        by_member = {row["board_member_id"]: row for row in rows}
        members = [{
            "name": participant["name"],
            "approval_status": by_member.get(participant["board_member_id"], {}).get("approval_status", ""),
            "change_request": by_member.get(participant["board_member_id"], {}).get("change_request", ""),
        } for participant in joined]
        approved = len([m for m in members if m["approval_status"] == "approved"])
        return {"members": members, "approved_count": approved, "participant_count": len(members)}

    @router.post("/game/meeting-review/adopt")
    async def adopt_strategy(payload: AdoptPayload, request: Request):
        member = await game_member(request)
        review = await require_review(member["user_id"])
        if not payload.confirmed:
            raise HTTPException(status_code=422, detail="Confirm the adoption checkbox to continue")
        if review["status"] != "final_strategy_created" or not review.get("final_strategy_id"):
            raise HTTPException(status_code=409, detail="There is no final strategy ready for adoption")
        strategy = await get_strategy(member["user_id"], review["final_strategy_id"])
        if strategy.get("status") == "adopted":
            return {"status": "adopted"}
        approvals = await db.final_board_approvals.find(
            {"strategy_id": review["final_strategy_id"]}, {"_id": 0}).to_list(300)
        adopted_at = now_iso()
        await db.game_strategies.update_one(
            {"strategy_id": review["final_strategy_id"], "user_id": member["user_id"]},
            {"$set": {"status": "adopted", "adopted_at": adopted_at, "adopted_by": member["user_id"],
                      "adoption_approval_snapshot": approvals,
                      "meeting_review_id": review["review_id"],
                      "group_session_id": review.get("group_session_id", ""),
                      "source_strategy_id": review["strategy_id"]}})
        await db.meeting_review_sessions.update_one(
            {"review_id": review["review_id"]},
            {"$set": {"status": "adopted", "adopted_at": adopted_at, "updated_at": now_iso()}})
        return {"status": "adopted", "adopted_at": adopted_at}

    # ---------- Board members (shared Group Game link, no account) ----------

    async def session_by_token(token: str) -> dict:
        session = await db.group_game_sessions.find_one(
            {"token": token, "status": {"$ne": "archived"}}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="This Group Game link is not valid")
        return session

    async def player_identity(session: dict, slot: str, device: str) -> dict:
        return await db.group_game_participants.find_one(
            {"session_id": session["session_id"], "slot_id": slot, "device_id": device}, {"_id": 0})

    @router.get("/game/group/play/{token}/review-state")
    async def player_review_state(token: str, slot: str = "", device: str = ""):
        session = await session_by_token(token)
        review = await db.meeting_review_sessions.find_one(
            {"user_id": session["user_id"], "group_session_id": session["session_id"]},
            {"_id": 0}, sort=[("started_at", -1)])
        if not review:
            return {"exists": False}
        profile = await get_profile(session["user_id"])
        me = await player_identity(session, slot, device)
        payload = {
            "exists": True, "status": review["status"],
            "organization_name": (profile.get("organization") or {}).get("name", ""),
            "total_sections": TOTAL_SECTIONS,
        }
        if review["status"] == "reviewing":
            index = review.get("current_section_index", 0)
            key = SECTION_KEYS[index]
            strategy = await get_strategy(session["user_id"], review["strategy_id"])
            my_feedback = None
            if me:
                my_feedback = await db.meeting_section_feedback.find_one(
                    {"review_id": review["review_id"], "section_key": key,
                     "board_member_id": me["board_member_id"]},
                    {"_id": 0, "response_type": 1, "comment": 1})
            payload["section"] = {
                "index": index, "key": key, "title": SECTION_TITLES[key], "mode": strategy.get("mode", ""),
                "data": (strategy.get("data") or {}).get(key),
                "edit": (strategy.get("section_edits") or {}).get(key, ""),
            }
            payload["my_feedback"] = my_feedback
        elif review["status"] == "final_strategy_created":
            payload["final_review_status"] = review.get("final_review_status", "")
            if review.get("final_review_status") == "reviewing" and review.get("final_strategy_id"):
                index = review.get("final_section_index", 0)
                key = SECTION_KEYS[index]
                final = await get_strategy(session["user_id"], review["final_strategy_id"])
                payload["section"] = {
                    "index": index, "key": key, "title": SECTION_TITLES[key], "mode": final.get("mode", ""),
                    "data": (final.get("data") or {}).get(key),
                    "edit": (final.get("section_edits") or {}).get(key, ""),
                }
            if me and review.get("final_strategy_id"):
                mine = await db.final_board_approvals.find_one(
                    {"strategy_id": review["final_strategy_id"], "board_member_id": me["board_member_id"]},
                    {"_id": 0, "approval_status": 1, "change_request": 1})
                payload["my_final_response"] = mine
        elif review["status"] == "adopted":
            payload["adopted_at"] = review.get("adopted_at", "")
        return payload

    @router.post("/game/group/play/{token}/review-feedback")
    async def player_feedback(token: str, payload: PlayerFeedbackPayload):
        session = await session_by_token(token)
        review = await db.meeting_review_sessions.find_one(
            {"user_id": session["user_id"], "group_session_id": session["session_id"]},
            {"_id": 0}, sort=[("started_at", -1)])
        if not review or review["status"] != "reviewing":
            raise HTTPException(status_code=409, detail="The strategy review is not open right now")
        current_key = SECTION_KEYS[review.get("current_section_index", 0)]
        if payload.section_key != current_key:
            raise HTTPException(status_code=409, detail="The board has moved to another section")
        if payload.response_type not in FEEDBACK_TYPES:
            raise HTTPException(status_code=422, detail="Unknown response type")
        me = await player_identity(session, payload.slot_id, payload.device_id)
        if not me:
            raise HTTPException(status_code=403, detail="Join the game before responding")
        comment = payload.comment.strip() if payload.response_type != "approve" else ""
        await db.meeting_section_feedback.update_one(
            {"review_id": review["review_id"], "section_key": payload.section_key,
             "board_member_id": me["board_member_id"]},
            {"$set": {"response_type": payload.response_type, "comment": comment,
                      "name": me["name"], "updated_at": now_iso()},
             "$setOnInsert": {"feedback_id": new_uuid(), "review_id": review["review_id"],
                              "section_key": payload.section_key,
                              "board_member_id": me["board_member_id"], "created_at": now_iso()}},
            upsert=True)
        return {"status": "saved"}

    @router.post("/game/group/play/{token}/final-response")
    async def player_final_response(token: str, payload: PlayerFinalPayload):
        session = await session_by_token(token)
        review = await db.meeting_review_sessions.find_one(
            {"user_id": session["user_id"], "group_session_id": session["session_id"]},
            {"_id": 0}, sort=[("started_at", -1)])
        if not review or review["status"] != "final_strategy_created" or not review.get("final_strategy_id"):
            raise HTTPException(status_code=409, detail="The final strategy review is not open right now")
        if payload.approval_status not in {"approved", "change_requested"}:
            raise HTTPException(status_code=422, detail="Unknown response")
        me = await player_identity(session, payload.slot_id, payload.device_id)
        if not me:
            raise HTTPException(status_code=403, detail="Join the game before responding")
        await db.final_board_approvals.update_one(
            {"strategy_id": review["final_strategy_id"], "board_member_id": me["board_member_id"]},
            {"$set": {"approval_status": payload.approval_status,
                      "change_request": payload.change_request.strip() if payload.approval_status == "change_requested" else "",
                      "name": me["name"], "review_id": review["review_id"], "submitted_at": now_iso()},
             "$setOnInsert": {"approval_id": new_uuid(), "strategy_id": review["final_strategy_id"],
                              "board_member_id": me["board_member_id"]}},
            upsert=True)
        return {"status": "saved"}

    return router
