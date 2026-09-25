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

LEGACY_FINAL_SYSTEM_MESSAGE = """You are compiling the Final Board Fundraising Strategy for a nonprofit organisation.
The board has completed Individual Games and explicitly selected the ideas it agreed with across the Group Game. A meeting transcript may also be supplied, but it is optional enrichment rather than a prerequisite.
Reconcile all supplied information into one execution-ready ORGANIZATION fundraising strategy.
Where a supplied transcript clearly changes something during the meeting, that explicit meeting decision overrides earlier drafts and ideas. When no transcript is available, the Group Game selections and Board-added agreed wording are the authoritative decisions.
Where the transcript does not change a decision, treat the ideas explicitly selected by the Lead User during the Group Game as the Board's adopted direction.
Where ideas genuinely conflict and no resolution exists in the transcript, present the unresolved difference clearly rather than silently choosing one.
The Board's explicitly selected ideas, Board-added agreed wording and explicit meeting decisions are the primary authority. Preserve their distinctive language, logic, examples and intended meaning wherever practical. Do not average multiple contributions into vague generic fundraising language simply to make the document sound polished. Organize, connect and operationalize what the Board chose while keeping the Board able to recognize its own thinking. Nonprofit Board Builder recommendations remain subordinate unless the Board explicitly selected or adopted them.
Divide the fundraising process by audience (Individuals, Businesses, Grantors) and only include audience categories the organisation actually identified. Do not invent Businesses or Grantors the board did not identify.
Board Priorities are only the ideas the Board explicitly selected with the Group Game checkboxes or added as agreed ideas during the discussion. Additional Board Ideas are valid contributed ideas that were visible but not selected. Preserve them separately, never discard them and never misrepresent them as adopted priorities.
For team roles, use the supplied team, participation choices, time commitments and responsibilities from the transcript. Assign a person only where they explicitly indicated they want to help or accepted a responsibility. Where a required responsibility has nobody available, set assigned to exactly "ROLE / CAPACITY NEEDED". Never invent commitments.
The execution timeline is DEADLINE-DRIVEN. Use the supplied funding deadline and exact days available to determine the practical execution window. Do not force a 90-day, 120-day or other standard plan when the organisation has less or more time. A 30-day deadline needs a focused 30-day sprint; a 60-day deadline needs a realistic 60-day plan; longer windows can allocate more time to building Know/Like/Trust before asks. Start by building only the minimum system required to execute, then move the identified audiences through the Board-approved fundraising process quickly enough to pursue the goal before the deadline. Follow-up and stewardship continue throughout. Businesses and grantors are worked one relationship or one funder at a time around their real decision/application timelines.
For the execution budget, preserve any amounts the Board actually discussed. Do not invent vendor prices. Separate what is REQUIRED NOW from what can wait. For every meaningful cost, identify the lowest-cost practical route supported by the context: reuse existing staff/Board capacity, existing subscriptions, free tiers, simple templates, structured spreadsheets/low-cost CRM, AI-assisted drafting or public research before recommending new paid capacity. If a price was not supplied, say "PRICE TO CONFIRM" instead of inventing an amount.
Do not invent facts, funders, organisations, relationships, commitments, amounts or deadlines. Do not invent specific entities such as named businesses, foundations, LinkedIn or Facebook groups, associations, conferences or directories — where a specific entity was not supplied, give the exact search method instead.
Inspect the organisation's present fundraising processes (Current Reality). Never discard an existing approach simply because the framework offers another: preserve what the organisation says is working, strengthen weaknesses, fill missing pieces and add better processes where needed. Where useful distinguish what they are already doing, what should be strengthened and what should be added. Do not claim something is proven to work unless the organisation indicated it produces results.
Every fundraising_process audience MUST begin with how_this_process_works — a short organisation-specific explanation (not generic boilerplate, never one copied paragraph reused across audiences).
WHERE TO FIND must be operational: do not merely name a channel. State the repeatable prospecting action the organisation or Board should take in that place, how it will identify suitable prospects and, where supported by the deadline/context, the practical rhythm for doing it.
ATTRACTION must be operational: connect the selected audience to the specific message, evidence, content, event, introduction or experience that gives that audience a reason to engage before an ask.
FUNDRAISING PROCESS must read like a sequence somebody can follow. Every meaningful step should make the next action obvious and connect Know → Like → Trust → Ask → Follow Up → Steward to the actual audience.
EXECUTION TIMELINE should use real dates or clear day/week ranges when the supplied deadline makes them safely calculable. Sequence the minimum system setup first, then prospecting/relationship actions, asks/proposals, follow-up and stewardship so work is capable of reaching decisions before the funding deadline.
Write for nonprofit leaders and board members in clear, direct, execution-ready language. Keep the finished strategy concise enough to function like a two-to-four-page operating roadmap when rendered. Remove generic explanation, repeated ideas and motivational filler. Every section should tell the organisation what to do, where to do it, who owns it or what capacity is missing, and how it connects to the fundraising goal.
The Board Fundraising Process must explain how Board Members use their own networks inside the organisation's fundraising system: identify people, businesses and grantors who match the approved funder profiles; map the relationship; make or enable the introduction; then use the organisation's approved Know → Like → Trust → Ask → Follow Up → Steward process. Do not treat Board fundraising as a separate competing strategy.
The Final Strategy is an organizational strategy, not a meeting report. Never write "X said", "Y suggested", contributor-by-contributor attribution, transcript commentary or a history of who proposed an idea. Integrate adopted thinking into the strategy itself. Individual names may appear only where the Board explicitly assigned that person an execution responsibility.
Return only the required structured JSON."""

LEGACY_FINAL_V2_SCHEMA = {
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
        "individuals": {"how_this_process_works": "string — organization-specific explanation of which individuals this process is for, why they care, how it moves them from discovery to financial support and why it fits — generated from the actual audiences, attraction strategy and current reality; never generic boilerplate", "know": ["string — organisation-specific"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
        "businesses": {"how_this_process_works": "string — which businesses, why they align, which decision makers matter, how the organization gets in front of them and how it moves toward support", "know": ["string"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
        "grantors": {"how_this_process_works": "string — what type of grantors, why they align, how to identify them, how relationships and deadlines are handled and why the process fits", "know": ["string"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
    },
    "team_roles": [{"role": "Role title", "assigned": "Person's name where explicitly committed, otherwise exactly 'ROLE / CAPACITY NEEDED'", "responsibility": "string"}],
    "execution_resources": {"people": ["string"], "technology": ["string"], "materials": ["string"], "resources": ["string"], "content": ["string"]},
    "execution_budget": {
        "required_now": [{"item": "string", "why_needed": "string", "lowest_cost_approach": "string", "cost": "exact Board-supplied amount or exactly 'PRICE TO CONFIRM'"}],
        "later_or_optional": [{"item": "string", "why_later": "string", "lowest_cost_approach": "string", "cost": "exact Board-supplied amount or exactly 'PRICE TO CONFIRM'"}],
        "cost_reduction_options": ["string — concrete ways to execute with existing capacity, current subscriptions, free tiers, templates, AI-assisted drafting or public research"],
        "budget_summary": "string — the smallest realistic launch-budget logic supported by the Board's decisions; do not invent a total",
    },
    "execution_timeline": {
        "phase_1_build_the_system": ["string — deadline-driven actions to confirm owners, set up only the required tracking, create essential materials/content, prepare prospect lists and complete Board relationship mapping"],
        "phase_2_build_know_like_trust": ["string — deadline-driven Know/Like/Trust actions sized to the actual days available; do not assume 30–60 days when the deadline is shorter"],
        "phase_3_ask_campaign": ["string — deadline-driven asking/proposal actions timed so realistic prospects can decide before the funding deadline"],
        "follow_up_and_steward": ["string"],
        "business_timeline": ["string — business relationships worked one at a time, built from the actual business strategy; empty if no businesses identified"],
        "grantor_timeline": ["string — grantors worked one at a time around research, cultivation, deadlines, applications, follow-up and reporting; empty if no grantors identified"],
    },
    "board_priorities": [{"area": "Strategic area title", "items": ["string — only ideas explicitly selected or added as agreed by the Board during the Group Game"]}],
    "additional_board_ideas": [{"area": "Strategic area title", "items": ["string — contributed ideas shown to the Board but not explicitly adopted"]}],
    "next_step": "string — exactly: 'Your final fundraising strategy is ready. Review it with your board, send it to every participant and move into execution using the Board Portfolios, Execution Materials and Relationship Mapping.'",
}

FINAL_SYSTEM_MESSAGE = """You are compiling the Final Board Fundraising Strategy for a nonprofit organisation.
The Board has completed its Individual Games and explicitly selected its ideas during the six-round Group Game.
Create a proper fundraising plan, not meeting minutes. It must contain an executive summary with the exact goal, purpose and deadline; who the organisation will raise money from across individuals, businesses and grantors and why; where to find them; how to attract them and build credibility; what to ask each audience to fund and how much to ask; the step-by-step fundraising process; and the agreed role of every participating Board Member.
Use the Board's selected ideas and explicit transcript decisions as the sole authority. Preserve their distinctive language, intent and logic. Your job is to present their ideas clearly and make them practical and actionable only where their own context supports the detail. Do not replace their ideas with your own.
Use the lead user's present donors, business supporters, grantors and current fundraising methods as valid options where the Board selected or retained them.
Do not write "the Board discussed", "a participant said", names of contributors outside agreed roles, or any meeting-history language.
Do not add generic advice or invent funders, organisations, relationships, commitments, actions, amounts or results. Leave unsupported parts empty.
Write proper explanatory paragraphs in Rooney Akpesiri's clear, direct and practical style.
Return only the required structured JSON."""

FINAL_V2_SCHEMA = {
    "executive_summary": "Two or three proper paragraphs explaining the exact fundraising amount, purpose, deadline and agreed strategic approach without describing the meeting",
    "fundraising_audiences": {
        "individuals": [{"title": "Audience profile", "explanation": "Why they have a reason to give", "focus": "What the organisation will focus on"}],
        "businesses": [{"title": "Business audience profile", "explanation": "Why they have a reason to support", "focus": "What the organisation will focus on"}],
        "grantors": [{"title": "Grantor profile", "explanation": "Why the mission and funding focus align", "focus": "What the organisation will focus on"}],
    },
    "where_to_find": {"priorities": [{"title": "Place / channel / network", "explanation": "How it connects to the chosen audience", "focus": "How the organisation will use it consistently"}], "additional_ideas": ["string"]},
    "attraction": {"priorities": [{"title": "Attraction idea", "explanation": "Why it matters to the chosen audience", "focus": "How the organisation will use it"}], "additional_ideas": ["string"]},
    "funding_ask": {
        "individuals": [{"title": "What to fund", "explanation": "Exact amount or range agreed", "focus": "How the ask connects to the goal"}],
        "businesses": [{"title": "What to sponsor or fund", "explanation": "Exact amount or range agreed", "focus": "How the ask connects to the goal"}],
        "grantors": [{"title": "What to fund", "explanation": "Exact amount or range agreed", "focus": "How the request connects to the goal"}],
    },
    "fundraising_process": {
        "individuals": {"how_this_process_works": "string", "know": ["string"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
        "businesses": {"how_this_process_works": "string", "know": ["string"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
        "grantors": {"how_this_process_works": "string", "know": ["string"], "like": ["string"], "trust": ["string"], "ask": ["string"], "follow_up": ["string"], "steward": ["string"]},
    },
    "board_roles": [{"name": "Board Member's real name", "role": "Agreed role", "responsibility": "Specific agreed action and timing from the Group Game or transcript"}],
}

CORE_STRATEGY_KEYS = ["executive_summary", "fundraising_audiences", "where_to_find", "attraction", "funding_ask", "fundraising_process", "board_roles"]

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
            {"user_id": user_id, "removed": {"$ne": True}}, {"_id": 0, "member_id": 1, "full_name": 1}).to_list(200)
        names = {record["member_id"]: record.get("full_name") or "Board Member" for record in members}
        rows = await db.game_audience_responses.find(
            {"user_id": user_id, "board_member_id": {"$in": list(names)}, "completed": True}, {"_id": 0}).to_list(300)
        collected = {definition["key"]: [] for definition in AREA_DEFS}
        field_map = {"funding_audiences": "audience", "where_to_find": "where", "attraction": "attraction",
                     "funding_ask": "funding_ask", "fundraising_process": "process"}
        labels = {"individuals": "Individuals", "businesses": "Businesses", "grantors": "Grantors"}
        for row in rows:
            for audience_key, answer in (row.get("audiences") or {}).items():
                if audience_key not in labels or (audience_key != "individuals" and not answer.get("enabled")):
                    continue
                for area_key, field in field_map.items():
                    value = str(answer.get(field) or "").strip()
                    if value:
                        reason = str(answer.get("reason") or "").strip()
                        collected[area_key].append(f"{labels[audience_key]}: {value}" + (f" | Why: {reason}" if area_key == "funding_audiences" and reason else ""))
            if row.get("involvement"):
                collected["board_roles"].append(f"{names.get(row['board_member_id'], 'Board Member')}: {row['involvement']}")
        return collected

    async def participation_choices(user_id: str) -> list:
        members = {record["member_id"]: record["full_name"] for record in await db.game_board_members.find(
            {"user_id": user_id}, {"_id": 0, "member_id": 1, "full_name": 1}).to_list(300)}
        choices = []
        rows = await db.game_audience_responses.find(
            {"user_id": user_id, "completed": True}, {"_id": 0, "board_member_id": 1, "involvement": 1}).to_list(300)
        for row in rows:
            if row.get("involvement"):
                choices.append({"board_member_name": members.get(row.get("board_member_id"), ""),
                                "preferred_involvement": row["involvement"]})
        return choices

    async def group_results_by_area(user_id: str) -> dict:
        session = await completed_group_session(user_id)
        if not session:
            return {}
        rows = await db.group_game_results.find(
            {"session_id": session["session_id"]}, {"_id": 0}).sort("round_number", 1).to_list(20)
        output={}
        for row in rows:
            selected=sorted([item for item in row.get("results",[]) if item.get("prioritised")],key=lambda item:(item.get("rank") or 999,item.get("order") or 999))
            additional=sorted([item for item in row.get("results",[]) if not item.get("prioritised")],key=lambda item:item.get("order") or 999)
            output[row["title"]]={"board_agreed_ideas":[item["text"] for item in selected],
                                  "additional_board_ideas_not_adopted":[item["text"] for item in additional]}
        return output

    async def review_decisions_context(user_id: str) -> dict:
        review = await db.game_board_reviews.find_one({"user_id": user_id}, {"_id": 0}) or {}
        items = review.get("items", [])
        return {
            "note": ("These are explicit board decisions made during the Board Strategy Review. Honour them. "
                     "Adopted Rooney recommendations must move into the relevant main strategy sections and Board Priorities, "
                     "keeping their origin behind the scenes. A later explicit meeting-transcript decision may supersede these; "
                     "if a conflict is ambiguous, flag it rather than silently choosing."),
            "board_priorities": [{"area": i["area"], "text": i["text"], "source": i["source"]}
                                 for i in items if i["status"] == "priority"],
            "additional_board_ideas": [{"area": i["area"], "text": i["text"], "source": i["source"]}
                                       for i in items if i["status"] == "additional"],
            "rooney_recommendations_not_adopted": [{"area": i["area"], "text": i["text"]}
                                                   for i in items if i["status"] == "recommendation"],
            "marked_not_now": [{"area": i["area"], "text": i["text"]} for i in items if i["status"] == "not_now"],
        }

    async def run_final_compile(user_id: str):
        try:
            profile = await get_profile(user_id)
            goal = profile.get("goal") or {}
            situation = await db.game_situations.find_one({"user_id": user_id}, {"_id": 0}) or {}
            transcript = await get_transcript(user_id) or {}
            organization = profile.get("organization") or {}
            current_reality = (situation.get("sections") or {}).get("current_reality") or {}
            current_funder_keys = {
                "current_individual_donor_profile", "current_individual_donor_where", "current_individual_donor_attraction", "current_individual_donor_support", "current_individual_donor_process",
                "current_business_profile", "current_business_where", "current_business_attraction", "current_business_support", "current_business_process",
                "current_grantor_profile", "current_grantor_where", "current_grantor_attraction", "current_grantor_support", "current_grantor_process",
                "current_individual_donors", "current_businesses", "current_grantors",
                "individual_fundraising_process", "business_fundraising_process", "grant_fundraising_process",
            }
            context = {
                "organisation_profile": organization,
                "fundraising_goal": {
                    "amount": f"${int(goal.get('amount') or 0):,}" if goal.get("amount") else "",
                    "currency": "USD", "deadline": goal.get("deadline", ""),
                    "purpose": goal.get("purpose", ""), "why_it_matters_now": goal.get("why_now", ""),
                },
                "current_funder_context": {key: value for key, value in current_reality.items() if key in current_funder_keys},
                "approved_board_member_ideas_by_strategy_area": await board_ideas_by_area(user_id),
                "participation_choices_and_time_commitments": await participation_choices(user_id),
                "group_game_results": await group_results_by_area(user_id),
                "board_strategy_review_decisions": await review_decisions_context(user_id),
                "board_meeting_transcript": (transcript.get("text") or "")[:120000],
            }
            api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
            model = os.environ.get("FUNDRAISING_STRATEGY_MODEL", "claude-haiku-4-5-20251001")
            chat = LlmChat(api_key=api_key, session_id=f"bfg-final-compile-{uuid.uuid4()}",
                           system_message=FINAL_SYSTEM_MESSAGE).with_model("anthropic", model)
            prompt = (
                "FINAL STRATEGY CONTEXT (the only information you may use):\n"
                f"{json.dumps(context, indent=1)}\n\n"
                "Treat the Group Game checkbox selections and Board-added agreed ideas as explicit Board decisions and preserve their wording and logic as closely as practical. Use the full meeting transcript to identify clarifications, final decisions and agreed Board Member roles across all six decisions. "
                "Do not invent decisions that are not present.\n\n"
                "Respond with ONE JSON object matching exactly this schema (descriptions explain each field). "
                "Return only JSON — no markdown, no commentary:\n"
                + json.dumps(FINAL_V2_SCHEMA, indent=1)
            )
            response = await chat.send_message(UserMessage(text=prompt))
            text = response if isinstance(response, str) else getattr(response, "text", str(response))
            generated = parse_json_response(text)
            data = {key: generated.get(key, {}) for key in CORE_STRATEGY_KEYS}
            version = await db.game_strategies.count_documents({"user_id": user_id, "mode": "final"}) + 1
            now = now_iso()
            record = {
                "strategy_id": new_uuid(), "user_id": user_id, "mode": "final",
                "status": "final_draft", "version": version, "schema_version": 4,
                "share_token": secrets.token_urlsafe(24),
                "prepared_by": f"The Board of {organization.get('name', '').strip()}".strip(),
                "data": data, "section_edits": {},
                "source": "group_game_final_compile",
                "generated_at": now, "created_at": now,
                "last_edited_at": "", "last_edited_by": "", "review_completed_at": "",
            }
            await db.game_strategies.insert_one(record.copy())
            session = await completed_group_session(user_id)
            existing_review = await db.meeting_review_sessions.find_one(
                {"user_id": user_id, "group_session_id": (session or {}).get("session_id", "")}, {"_id": 0}) or {}
            review_id = existing_review.get("review_id") or new_uuid()
            await db.meeting_review_sessions.update_one(
                {"review_id": review_id},
                {"$set": {"user_id": user_id, "group_session_id": (session or {}).get("session_id", ""),
                          "strategy_id": record["strategy_id"], "final_strategy_id": record["strategy_id"],
                          "status": "final_strategy_created", "final_review_status": "response",
                          "final_strategy_created_at": now, "updated_at": now},
                 "$setOnInsert": {"started_at": now, "created_at": now}}, upsert=True)
            try:
                from rooney_intelligence import store_strategy_patterns
                await store_strategy_patterns(db, user_id=user_id,
                                              mission_category=str(organization.get("mission", ""))[:160],
                                              strategy_data=data)
            except Exception:
                pass
            await db.game_strategy_jobs.update_one(
                {"user_id": user_id, "mode": "final"},
                {"$set": {"status": "done", "strategy_id": record["strategy_id"], "error": "", "finished_at": now_iso()}})
        except Exception:
            await db.game_strategy_jobs.update_one(
                {"user_id": user_id, "mode": "final"},
                {"$set": {"status": "failed", "error": "generation_failed", "finished_at": now_iso()}})

    # ---------- Board Strategy Review (post-Group-Game, before transcript) ----------

    async def seed_review(user_id: str):
        session = await completed_group_session(user_id)
        if not session:
            raise HTTPException(status_code=409, detail="Complete the Group Game first")
        review = await db.game_board_reviews.find_one({"user_id": user_id}, {"_id": 0})
        if review:
            return review
        rows = await db.group_game_results.find({"session_id": session["session_id"]}, {"_id": 0}).sort("round_number", 1).to_list(20)
        items = []
        for row in rows:
            for result in row.get("results", []):
                prioritised = bool(result.get("prioritised")) and result.get("selection_count", 0) > 0
                status = "priority" if prioritised else "additional"
                items.append({
                    "item_id": new_uuid(), "area": row.get("title", ""), "text": result.get("text", ""),
                    "source": "board_priority" if prioritised else "additional_idea",
                    "original_status": status, "status": status,
                    "decided_at": "", "decided_by": "",
                })
        review = {"user_id": user_id, "items": items, "recommendations_generated": False,
                  "completed": False, "created_at": now_iso(), "updated_at": now_iso()}
        await db.game_board_reviews.insert_one(dict(review))
        return review

    @router.get("/game/review")
    async def get_board_review(request: Request):
        member = await game_member(request)
        review = await seed_review(member["user_id"])
        review.pop("_id", None)
        return review

    @router.post("/game/review/recommendations")
    async def generate_recommendations(request: Request):
        member = await game_member(request)
        review = await seed_review(member["user_id"])
        if review.get("recommendations_generated"):
            return {"status": "already_generated"}
        profile = await get_profile(member["user_id"])
        situation = await db.game_situations.find_one({"user_id": member["user_id"]}, {"_id": 0}) or {}
        context = {
            "organisation_profile": profile.get("organization") or {},
            "fundraising_goal": profile.get("goal") or {},
            "current_fundraising_reality": situation.get("sections", {}),
            "board_ideas_by_area": await board_ideas_by_area(member["user_id"]),
            "participation_choices": await participation_choices(member["user_id"]),
            "group_game_results": await group_results_by_area(member["user_id"]),
        }
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
        chat = LlmChat(api_key=api_key, session_id=f"bfg-review-recs-{uuid.uuid4()}",
                       system_message=(
                           "You are Rooney Akpesiri's fundraising process applied by an experienced nonprofit fundraising strategist. "
                           "Recommend practical, specific, executable ideas this organisation should consider that are currently missing or underdeveloped. "
                           "Every recommendation must state exactly who, exactly where, exactly what to create or do, exactly how to find them, what process should run and the next step. "
                           "Never return vague ideas like build relationships, reach businesses, create awareness, use LinkedIn, apply for grants or create content. "
                           "Never invent named businesses, foundations, groups, associations, events or funders — give the exact search method instead. Return only JSON.")
                       ).with_model("anthropic", os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"))
        prompt = (f"CONTEXT:\n{json.dumps(context, indent=1)}\n\n"
                  "Return ONE JSON object: {\"recommendations\": [{\"area\": \"strategic area title\", \"text\": \"one complete actionable recommendation\"}]} "
                  "with 4 to 10 recommendations. Only JSON.")
        response = await chat.send_message(UserMessage(text=prompt))
        data = parse_json_response(response if isinstance(response, str) else getattr(response, "text", str(response)))
        new_items = [{
            "item_id": new_uuid(), "area": str(item.get("area", ""))[:200], "text": str(item.get("text", ""))[:3000],
            "source": "ROONEY_PROCESS_RECOMMENDATION", "original_status": "recommendation",
            "status": "recommendation", "decided_at": "", "decided_by": "",
        } for item in (data.get("recommendations") or []) if str(item.get("text", "")).strip()]
        await db.game_board_reviews.update_one(
            {"user_id": member["user_id"]},
            {"$push": {"items": {"$each": new_items}},
             "$set": {"recommendations_generated": True, "updated_at": now_iso()}})
        return {"status": "generated", "count": len(new_items)}

    @router.post("/game/review/decision")
    async def review_decision(payload: dict, request: Request):
        member = await game_member(request)
        item_id = str(payload.get("item_id", ""))
        status = str(payload.get("status", ""))
        if status not in {"priority", "additional", "recommendation", "not_now"}:
            raise HTTPException(status_code=422, detail="Unknown decision")
        review = await db.game_board_reviews.find_one({"user_id": member["user_id"]}, {"_id": 0})
        item = next((i for i in (review or {}).get("items", []) if i["item_id"] == item_id), None)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        actor = f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()
        await db.game_board_reviews.update_one(
            {"user_id": member["user_id"], "items.item_id": item_id},
            {"$set": {"items.$.status": status, "items.$.decided_at": now_iso(),
                      "items.$.decided_by": actor, "updated_at": now_iso()}})
        from rooney_intelligence import log_review_decision
        await log_review_decision(db, user_id=member["user_id"], item=item, new_status=status, actor=actor)
        return {"status": "saved"}

    @router.post("/game/review/complete")
    async def complete_board_review(request: Request):
        member = await game_member(request)
        await db.game_board_reviews.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"completed": True, "completed_at": now_iso(), "updated_at": now_iso()}})
        return {"status": "completed"}

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

    @router.post("/game/meeting/recording/chunk")
    async def save_recording_chunk(payload: TranscriptPaste, request: Request):
        member=await game_member(request);text=str(payload.text).strip()
        if not text:raise HTTPException(status_code=422,detail="The transcript chunk is empty")
        await db.game_meeting_live_recordings.update_one(
            {"user_id":member["user_id"]},
            {"$push":{"chunks":{"text":text[:12000],"captured_at":now_iso()}},"$set":{"status":"recording","updated_at":now_iso()},
             "$setOnInsert":{"recording_id":new_uuid(),"user_id":member["user_id"],"created_at":now_iso()}},upsert=True)
        return {"status":"saved"}

    @router.post("/game/meeting/recording/finish")
    async def finish_live_recording(request: Request):
        member=await game_member(request);record=await db.game_meeting_live_recordings.find_one({"user_id":member["user_id"]},{"_id":0}) or {}
        chunks=[str(item.get("text","")).strip() for item in (record.get("chunks") or []) if str(item.get("text","")).strip()]
        text=" ".join(chunks).strip()
        if not text:raise HTTPException(status_code=422,detail="No live transcript was captured. Paste or upload the meeting transcript instead.")
        await save_transcript(member["user_id"],text,"live_recording")
        await db.game_meeting_live_recordings.update_one({"user_id":member["user_id"]},{"$set":{"status":"finished","finished_at":now_iso(),"updated_at":now_iso()}})
        return {"status":"saved","characters":len(text)}

    @router.post("/game/meeting/compile-final")
    async def compile_final(request: Request):
        member = await game_member(request)
        if not await completed_group_session(member["user_id"]):
            raise HTTPException(status_code=409, detail="Complete the Group Game before compiling the final strategy")
        job = await final_job(member["user_id"])
        if job and job.get("status") == "running" and not generation_job_stale(job):
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
        if generation_job_stale(job):
            await db.game_strategy_jobs.update_one(
                {"user_id": member["user_id"], "mode": "final", "status": "running"},
                {"$set": {"status": "failed", "error": "generation_timed_out", "finished_at": now_iso()}})
            job_status = "failed"
        if job_status == "running":
            output_state = "generating"
        elif final:
            output_state = "ready"
        elif job_status == "failed":
            output_state = "failed"
        elif not session:
            output_state = "locked"
        else:
            output_state = "preparing"
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

    @router.get("/game/relationships/export.csv")
    async def export_relationships(request: Request):
        import csv
        import io
        from fastapi.responses import Response as HttpResponse
        member=await game_member(request);rows=await db.game_relationships.find({"user_id":member["user_id"]},{"_id":0}).sort("created_at",1).to_list(5000);stream=io.StringIO();fields=["funder_type","name","organization","email","phone","other_contact","member_name","how_know","why_match","willing_intro","willing_participate","willing_ask","willing_org_ask"];writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in rows:writer.writerow({key:row.get(key,"") for key in fields})
        return HttpResponse(content=stream.getvalue(),media_type="text/csv",headers={"Content-Disposition":'attachment; filename="board-relationship-map.csv"'})

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
            "participant_role": record.get("participant_role", "board_member"),
            "strategy": {
                "mode": strategy["mode"], "status": strategy["status"], "version": strategy["version"],
                "schema_version": strategy.get("schema_version", 1),
                "prepared_by": strategy.get("prepared_by", ""),
                "generated_at": strategy["generated_at"], "data": strategy["data"],
                "section_edits": strategy.get("section_edits", {}),
                "organization_name": (profile.get("organization") or {}).get("name", ""),
            },
        }

    @router.get("/game/final/{token}/download")
    async def member_final_download(token: str):
        from fastapi.responses import Response as HttpResponse
        from strategy_pdf import build_strategy_pdf
        record = await member_by_token(token)
        profile = await get_profile(record["user_id"])
        strategy = await latest_final(record["user_id"]) or await db.game_strategies.find_one(
            {"user_id": record["user_id"], "status": "adopted"}, {"_id": 0}, sort=[("adopted_at", -1)])
        if not strategy:
            raise HTTPException(status_code=404, detail="No final strategy available yet")
        org_name = (profile.get("organization") or {}).get("name", "")
        pdf = build_strategy_pdf(strategy, org_name)
        return HttpResponse(content=pdf, media_type="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="final-fundraising-strategy-v{strategy["version"]}.pdf"'})

    return router
