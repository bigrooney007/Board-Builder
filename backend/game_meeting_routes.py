"""Board Fundraising Game: post-Group-Game meeting transcript, Final Strategy compilation and Relationship Mapping."""
import asyncio
import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from io import BytesIO

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from ai_service import parse_json_response
from member_auth import authenticate_member, new_uuid, require_entitlement
from game_content import GAME_SECTION_DEFAULTS
from group_game_routes import AREA_DEFS, area_ideas

GAME_ENTITLEMENT = "board_fundraising_game"
SECTION_ID_BY_KEY = {section["key"]: section["id"] for section in GAME_SECTION_DEFAULTS}
FUNDER_TYPES = {"Individual", "Business", "Grantor"}

FINAL_SYSTEM_MESSAGE = """You are compiling the Final Board Fundraising Strategy for a nonprofit organisation.
The board has completed Individual Games, prioritised ideas together in a Group Game and held a board meeting captured in the supplied transcript.
Reconcile all supplied information into one execution-ready fundraising strategy.
Where the board changed something during the meeting, the meeting decision overrides earlier drafts and ideas.
Where there is no meeting decision, use the prioritised and approved strategy information.
Where ideas genuinely conflict and no resolution exists in the transcript, present the unresolved difference clearly rather than silently choosing one.
Divide the fundraising process by audience (Individuals, Businesses, Grantors) and only include audience categories the organisation actually identified. Do not invent Businesses or Grantors the board did not identify.
Board Priorities are only the ideas actually ranked by the board in the Group Game. Additional Board Ideas are valid contributed ideas that were not prioritised — preserve them separately, never discard them and never misrepresent them as priorities.
For team roles, use the supplied team, participation choices, time commitments and responsibilities from the transcript. Assign a person only where they explicitly indicated they want to help or accepted a responsibility. Where a required responsibility has nobody available, set assigned to exactly "ROLE / CAPACITY NEEDED". Never invent commitments.
The execution timeline must start with building the fundraising system, then roughly 30 to 60 days of Know/Like/Trust activity for individuals, then roughly a 30-day concentrated ask campaign, with follow up and stewardship continuing. Businesses and grantors are worked one relationship or one funder at a time on their own timelines built from the organisation's actual strategy.
Do not invent facts, funders, organisations, relationships, commitments, amounts or deadlines.
Write for nonprofit leaders and board members in clear, direct, execution-ready language.
Return only the required structured JSON."""

FINAL_V2_SCHEMA = {
    "executive_summary": "string — the organisation, the fundraising goal, the deadline, what the money supports, the strategic direction the board decided on and the primary priorities",
    "fundraising_goal": {"amount": "string — exactly as supplied", "currency": "USD", "deadline": "string", "purpose": "string",
                         "summary": "string — concise explanation of what the organisation is working to accomplish"},
    "fundraising_audiences": {
        "individuals": [{"title": "Audience profile name", "explanation": "Why they match — grounded in supplied information", "focus": "What to focus on"}],
        "businesses": [{"title": "string", "explanation": "string", "focus": "string"}],
        "grantors": [{"title": "string", "explanation": "string", "focus": "string"}],
    },
    "where_to_find": {"priorities": [{"title": "Place / channel / network", "explanation": "string", "focus": "string"}], "additional_ideas": ["string"]},
    "attraction": {"priorities": [{"title": "Attraction activity", "explanation": "string", "focus": "string"}], "additional_ideas": ["string"]},
    "fundraising_process": {
        "individuals": {"know": ["string — organisation-specific"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
        "businesses": {"know": ["string"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
        "grantors": {"know": ["string"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
    },
    "team_roles": [{"role": "Role title", "assigned": "Person's name where explicitly committed, otherwise exactly 'ROLE / CAPACITY NEEDED'", "responsibility": "string"}],
    "execution_resources": {"people": ["string"], "technology": ["string"], "materials": ["string"], "resources": ["string"], "content": ["string"]},
    "execution_timeline": {
        "phase_1_build_the_system": ["string — confirm team, assign roles, set up tracking, create materials and attraction content, prepare outreach lists, complete board relationship mapping, prepare follow-up systems"],
        "phase_2_build_know_like_trust": ["string — approximately 30 to 60 days of Know/Like/Trust activity for individuals"],
        "phase_3_ask_campaign": ["string — approximately 30 days of concentrated asking where appropriate"],
        "follow_up_and_steward": ["string"],
        "business_timeline": ["string — business relationships worked one at a time, built from the actual business strategy; empty if no businesses identified"],
        "grantor_timeline": ["string — grantors worked one at a time around research, cultivation, deadlines, applications, follow-up and reporting; empty if no grantors identified"],
    },
    "board_priorities": [{"area": "Strategic area title", "items": ["string — only ideas actually ranked by the board"]}],
    "additional_board_ideas": [{"area": "Strategic area title", "items": ["string — contributed but not prioritised"]}],
    "next_step": "string — exactly: 'Your final fundraising strategy is ready. Review it with your board, send it to every participant and move into execution using the Board Portfolios, Execution Materials and Relationship Mapping.'",
}

BOARD_FUNDRAISING_PROCESS = {
    "know": [
        "The board member identifies people, businesses or grantors in their network who match the organization's ideal funding audiences.",
        "The board member makes the introduction or creates the first connection.",
    ],
    "like": [
        "The board member explains why they personally support the organization and gives the prospect an easy way to learn more about the mission.",
    ],
    "trust": [
        "The prospect receives relevant impact information, stories, results, evidence and opportunities to interact with the organization.",
        "Where appropriate, the board member brings the prospect into a conversation, event or meeting with the organization.",
    ],
    "ask": [
        "Based on the Relationship Mapping Form, determine whether the board member will make the ask, the board member and organization will make the ask together, or the board member will introduce the relationship and the organization will make the ask.",
    ],
    "follow_up": [
        "The person responsible for the relationship follows up after meetings, introductions, proposals or asks.",
        "The relationship should not be abandoned simply because someone did not give immediately.",
    ],
    "steward": [
        "Thank the funder.",
        "Show what their support made possible.",
        "Keep the board member connected to the relationship where appropriate.",
        "Continue communicating impact and future opportunities.",
    ],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TranscriptPaste(BaseModel):
    text: str = Field(min_length=1, max_length=400000)


class RelationshipEntry(BaseModel):
    funder_type: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=300)
    organization: str = Field(default="", max_length=300)
    email: str = Field(default="", max_length=300)
    phone: str = Field(default="", max_length=100)
    other_contact: str = Field(default="", max_length=600)
    how_know: str = Field(default="", max_length=2000)
    why_match: str = Field(default="", max_length=2000)
    willing_intro: bool = False
    willing_participate: bool = False
    willing_ask: bool = False
    willing_org_ask: bool = False


def extract_upload_text(filename: str, raw: bytes) -> str:
    lowered = (filename or "").lower()
    if lowered.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(raw))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if lowered.endswith(".docx"):
        import docx
        document = docx.Document(BytesIO(raw))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    if lowered.endswith(".txt"):
        return raw.decode("utf-8", errors="replace")
    raise HTTPException(status_code=422, detail="Upload a PDF, DOCX or TXT transcript file")


def create_game_meeting_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def game_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        return member

    async def get_profile(user_id: str) -> dict:
        return await db.game_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}

    async def completed_group_session(user_id: str):
        return await db.group_game_sessions.find_one(
            {"user_id": user_id, "status": "completed"}, {"_id": 0}, sort=[("completed_at", -1)])

    async def get_transcript(user_id: str):
        return await db.game_meeting_transcripts.find_one({"user_id": user_id}, {"_id": 0}, sort=[("submitted_at", -1)])

    async def latest_final(user_id: str):
        return await db.game_strategies.find_one(
            {"user_id": user_id, "mode": "final"}, {"_id": 0}, sort=[("generated_at", -1)])

    async def final_job(user_id: str):
        return await db.game_strategy_jobs.find_one({"user_id": user_id, "mode": "final"}, {"_id": 0})

    async def save_transcript(user_id: str, text: str, source: str, filename: str = ""):
        cleaned = text.strip()
        if not cleaned:
            raise HTTPException(status_code=422, detail="The transcript is empty")
        await db.game_meeting_transcripts.update_one(
            {"user_id": user_id},
            {"$set": {"text": cleaned[:400000], "source": source, "filename": filename,
                      "submitted_at": now_iso()},
             "$setOnInsert": {"transcript_id": new_uuid(), "user_id": user_id, "created_at": now_iso()}},
            upsert=True)

    # ---------- Final compile context ----------

    async def board_ideas_by_area(user_id: str) -> dict:
        members = await db.game_board_members.find(
            {"user_id": user_id, "removed": {"$ne": True}}, {"_id": 0, "member_id": 1}).to_list(200)
        member_ids = [record["member_id"] for record in members]
        collected = {}
        for definition in AREA_DEFS:
            section_id = SECTION_ID_BY_KEY.get(definition["key"])
            responses = await db.game_section_responses.find(
                {"user_id": user_id, "board_member_id": {"$in": member_ids}, "section_id": section_id}, {"_id": 0}).to_list(300)
            ideas = []
            for response in responses:
                if definition["key"] == "who_should_fund":
                    for audience_type, label in (("individual", "Individual"), ("business", "Business"), ("grantor", "Grantor")):
                        ideas.extend(f"{label}: {text}" for text in area_ideas(response, definition["key"], audience_type))
                else:
                    ideas.extend(area_ideas(response, definition["key"]))
            seen = set()
            unique = []
            for idea in ideas:
                key = " ".join(str(idea).lower().split())
                if key and key not in seen:
                    seen.add(key)
                    unique.append(str(idea).strip()[:400])
            collected[definition["key"]] = unique
        return collected

    async def participation_choices(user_id: str) -> list:
        rows = await db.game_section_responses.find(
            {"user_id": user_id, "section_id": 5, "completed": True}, {"_id": 0, "extras": 1, "board_member_id": 1}).to_list(300)
        members = {record["member_id"]: record["full_name"] for record in await db.game_board_members.find(
            {"user_id": user_id}, {"_id": 0, "member_id": 1, "full_name": 1}).to_list(300)}
        choices = []
        for row in rows:
            extras = row.get("extras") or {}
            if extras.get("build") or extras.get("raise") or extras.get("time") or extras.get("additional_idea"):
                choices.append({
                    "board_member_name": members.get(row.get("board_member_id"), ""),
                    "wants_to_help_build_and_manage_the_fundraising_system": extras.get("build", []),
                    "build_other": extras.get("build_other", ""),
                    "wants_to_help_raise_money": extras.get("raise", []),
                    "raise_other": extras.get("raise_other", ""),
                    "monthly_time_commitment": extras.get("time", ""),
                    "additional_comments": extras.get("additional_idea", ""),
                })
        return choices

    async def group_results_by_area(user_id: str) -> dict:
        session = await completed_group_session(user_id)
        if not session:
            return {}
        rows = await db.group_game_results.find(
            {"session_id": session["session_id"]}, {"_id": 0}).sort("round_number", 1).to_list(20)
        return {row["title"]: {
            "board_priorities_in_rank_order": [item["text"] for item in row["results"] if item.get("prioritised")],
            "additional_board_ideas_not_prioritised": [item["text"] for item in row["results"] if not item.get("prioritised")],
        } for row in rows}

    async def run_final_compile(user_id: str):
        try:
            profile = await get_profile(user_id)
            goal = profile.get("goal") or {}
            situation = await db.game_situations.find_one({"user_id": user_id}, {"_id": 0}) or {}
            transcript = await get_transcript(user_id) or {}
            organization = profile.get("organization") or {}
            context = {
                "organisation_profile": organization,
                "fundraising_goal": {
                    "amount": f"${int(goal.get('amount') or 0):,}" if goal.get("amount") else "",
                    "currency": "USD", "deadline": goal.get("deadline", ""),
                    "purpose": goal.get("purpose", ""), "why_it_matters_now": goal.get("why_now", ""),
                },
                "current_fundraising_reality_and_existing_team": situation.get("sections", {}),
                "approved_board_member_ideas_by_strategy_area": await board_ideas_by_area(user_id),
                "participation_choices_and_time_commitments": await participation_choices(user_id),
                "group_game_results": await group_results_by_area(user_id),
                "board_meeting_transcript": (transcript.get("text") or "")[:120000],
            }
            api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
            model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
            chat = LlmChat(api_key=api_key, session_id=f"bfg-final-compile-{uuid.uuid4()}",
                           system_message=FINAL_SYSTEM_MESSAGE).with_model("anthropic", model)
            prompt = (
                "FINAL STRATEGY CONTEXT (the only information you may use):\n"
                f"{json.dumps(context, indent=1)}\n\n"
                "Use the meeting transcript to identify final board decisions, changes to strategy, additional ideas, "
                "assignments, responsibilities, clarifications, execution decisions, timing decisions and decisions about "
                "who will make introductions or asks. Integrate those decisions into the relevant strategy sections. "
                "Do not invent decisions that are not present.\n\n"
                "Respond with ONE JSON object matching exactly this schema (descriptions explain each field). "
                "Return only JSON — no markdown, no commentary:\n"
                + json.dumps(FINAL_V2_SCHEMA, indent=1)
            )
            response = await chat.send_message(UserMessage(text=prompt))
            text = response if isinstance(response, str) else getattr(response, "text", str(response))
            data = parse_json_response(text)
            data["board_fundraising_process"] = BOARD_FUNDRAISING_PROCESS
            version = await db.game_strategies.count_documents({"user_id": user_id, "mode": "final"}) + 1
            now = now_iso()
            record = {
                "strategy_id": new_uuid(), "user_id": user_id, "mode": "final",
                "status": "adopted", "version": version, "schema_version": 2,
                "share_token": secrets.token_urlsafe(24),
                "prepared_by": f"The Board of {organization.get('name', '').strip()}".strip(),
                "data": data, "section_edits": {},
                "source": "meeting_transcript_compile",
                "generated_at": now, "created_at": now, "adopted_at": now,
                "last_edited_at": "", "last_edited_by": "", "review_completed_at": "",
            }
            await db.game_strategies.insert_one(record.copy())
            await db.game_strategy_jobs.update_one(
                {"user_id": user_id, "mode": "final"},
                {"$set": {"status": "done", "strategy_id": record["strategy_id"], "error": "", "finished_at": now_iso()}})
        except Exception:
            await db.game_strategy_jobs.update_one(
                {"user_id": user_id, "mode": "final"},
                {"$set": {"status": "failed", "error": "generation_failed", "finished_at": now_iso()}})

    # ---------- Transcript + compile ----------

    @router.post("/game/meeting/transcript")
    async def paste_transcript(payload: TranscriptPaste, request: Request):
        member = await game_member(request)
        await save_transcript(member["user_id"], payload.text, "pasted")
        return {"status": "saved"}

    @router.post("/game/meeting/transcript-upload")
    async def upload_transcript(request: Request, file: UploadFile = File(...)):
        member = await game_member(request)
        raw = await file.read()
        if len(raw) > 20 * 1024 * 1024:
            raise HTTPException(status_code=422, detail="The transcript file is too large (20 MB maximum)")
        text = extract_upload_text(file.filename or "", raw)
        await save_transcript(member["user_id"], text, "uploaded", file.filename or "")
        return {"status": "saved", "characters": len(text.strip())}

    @router.post("/game/meeting/compile-final")
    async def compile_final(request: Request):
        member = await game_member(request)
        if not await completed_group_session(member["user_id"]):
            raise HTTPException(status_code=409, detail="Complete the Group Game before compiling the final strategy")
        if not await get_transcript(member["user_id"]):
            raise HTTPException(status_code=422, detail="Paste or upload your meeting transcript first")
        job = await final_job(member["user_id"])
        if job and job.get("status") == "running":
            return {"status": "running"}
        await db.game_strategy_jobs.update_one(
            {"user_id": member["user_id"], "mode": "final"},
            {"$set": {"status": "running", "error": "", "strategy_id": "", "started_at": now_iso(), "finished_at": ""},
             "$setOnInsert": {"user_id": member["user_id"], "mode": "final"}},
            upsert=True)
        asyncio.create_task(run_final_compile(member["user_id"]))
        return {"status": "running"}

    @router.get("/game/meeting/overview")
    async def meeting_overview(request: Request):
        member = await game_member(request)
        session = await completed_group_session(member["user_id"])
        transcript = await get_transcript(member["user_id"])
        job = await final_job(member["user_id"]) or {}
        final = await latest_final(member["user_id"])
        job_status = job.get("status", "")
        if job_status == "running":
            output_state = "generating"
        elif final:
            output_state = "ready"
        elif not session:
            output_state = "locked"
        else:
            output_state = "meeting"
        return {
            "group_completed": bool(session),
            "transcript": {
                "submitted": bool(transcript),
                "source": (transcript or {}).get("source", ""),
                "filename": (transcript or {}).get("filename", ""),
                "characters": len((transcript or {}).get("text", "")),
                "submitted_at": (transcript or {}).get("submitted_at", ""),
            },
            "final": {
                "status": job_status or ("done" if final else "none"),
                "strategy_id": (final or {}).get("strategy_id", ""),
                "generated_at": (final or {}).get("generated_at", ""),
                "version": (final or {}).get("version", 0),
            },
            "outputs": {
                "final_strategy": output_state,
                "board_portfolios": output_state,
                "execution_materials": output_state,
                "relationship_mapping": output_state,
            },
        }

    # ---------- Relationship Mapping ----------

    async def member_by_token(token: str) -> dict:
        record = await db.game_board_members.find_one(
            {"token": token, "removed": {"$ne": True}}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This link is not valid")
        return record

    def entry_view(row: dict) -> dict:
        return {key: row.get(key, "") for key in (
            "relationship_id", "funder_type", "name", "organization", "email", "phone", "other_contact",
            "how_know", "why_match", "created_at")} | {
            "willing_intro": bool(row.get("willing_intro")),
            "willing_participate": bool(row.get("willing_participate")),
            "willing_ask": bool(row.get("willing_ask")),
            "willing_org_ask": bool(row.get("willing_org_ask")),
        }

    @router.get("/game/play/{token}/relationships")
    async def list_relationships(token: str):
        record = await member_by_token(token)
        profile = await get_profile(record["user_id"])
        rows = await db.game_relationships.find(
            {"board_member_id": record["member_id"]}, {"_id": 0}).sort("created_at", 1).to_list(300)
        return {
            "organization_name": (profile.get("organization") or {}).get("name", ""),
            "member_first_name": record["full_name"].split(" ")[0],
            "entries": [entry_view(row) for row in rows],
        }

    @router.post("/game/play/{token}/relationships")
    async def add_relationship(token: str, payload: RelationshipEntry):
        record = await member_by_token(token)
        if payload.funder_type not in FUNDER_TYPES:
            raise HTTPException(status_code=422, detail="Choose Individual, Business or Grantor")
        row = {
            "relationship_id": new_uuid(), "user_id": record["user_id"],
            "board_member_id": record["member_id"], "member_name": record["full_name"],
            "funder_type": payload.funder_type, "name": payload.name.strip(),
            "organization": payload.organization.strip(), "email": payload.email.strip(),
            "phone": payload.phone.strip(), "other_contact": payload.other_contact.strip(),
            "how_know": payload.how_know.strip(), "why_match": payload.why_match.strip(),
            "willing_intro": payload.willing_intro, "willing_participate": payload.willing_participate,
            "willing_ask": payload.willing_ask, "willing_org_ask": payload.willing_org_ask,
            "created_at": now_iso(),
        }
        await db.game_relationships.insert_one(row.copy())
        return {"status": "saved", "entry": entry_view(row)}

    @router.get("/game/relationships")
    async def all_relationships(request: Request):
        member = await game_member(request)
        rows = await db.game_relationships.find(
            {"user_id": member["user_id"]}, {"_id": 0}).sort("created_at", 1).to_list(1000)
        return {"entries": [{**entry_view(row), "member_name": row.get("member_name", "")} for row in rows]}

    # ---------- Board member final strategy journey ----------

    @router.get("/game/final/{token}")
    async def member_final_strategy(token: str):
        record = await member_by_token(token)
        profile = await get_profile(record["user_id"])
        strategy = await latest_final(record["user_id"])
        if not strategy:
            strategy = await db.game_strategies.find_one(
                {"user_id": record["user_id"], "status": "adopted"}, {"_id": 0}, sort=[("adopted_at", -1)])
        if not strategy:
            return {"ready": False, "organization_name": (profile.get("organization") or {}).get("name", "")}
        portfolio = await db.board_portfolios.find_one(
            {"user_id": record["user_id"], "board_member_id": record["member_id"]},
            {"_id": 0, "token": 1, "status": 1}, sort=[("created_at", -1)])
        return {
            "ready": True,
            "organization_name": (profile.get("organization") or {}).get("name", ""),
            "member_first_name": record["full_name"].split(" ")[0],
            "portfolio_token": (portfolio or {}).get("token", ""),
            "strategy": {
                "mode": strategy["mode"], "status": strategy["status"], "version": strategy["version"],
                "schema_version": strategy.get("schema_version", 1),
                "prepared_by": strategy.get("prepared_by", ""),
                "generated_at": strategy["generated_at"], "data": strategy["data"],
                "section_edits": strategy.get("section_edits", {}),
                "organization_name": (profile.get("organization") or {}).get("name", ""),
            },
        }

    return router
