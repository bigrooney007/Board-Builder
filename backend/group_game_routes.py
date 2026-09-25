"""Board Fundraising Game group meeting: one host-controlled screen shared by the whole board."""
import re
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from member_auth import authenticate_member, new_uuid, require_entitlement
from game_content import GAME_SECTION_DEFAULTS

GAME_ENTITLEMENT = "board_fundraising_game"
TOTAL_ROUNDS = 4
GROUP_GAME_VERSION = "four-area-v1"

ROUND_DEFS = [
    {"round_number": 1, "section_key": "who_should_fund", "source_key": "who_should_fund",
     "title": "Who Should Fund Our Mission",
     "instruction": "Review every funding-audience idea together, including the organization's present donor, business and grantor reality. Discuss what the board agrees should move forward."},
    {"round_number": 2, "section_key": "where_to_find", "source_key": "where_to_find",
     "title": "Where We Can Consistently Find Them",
     "instruction": "Review the places, networks and channels suggested by the board. Discuss what is realistic for {organization}."},
    {"round_number": 3, "section_key": "attract_attention", "source_key": "attract_attention",
     "title": "How We Will Attract Their Attention",
     "instruction": "Review the board's attraction ideas and agree on the approaches that fit the audiences and the mission."},
    {"round_number": 4, "section_key": "fundraising_process", "source_key": "fundraising_process",
     "title": "How We Will Raise Money From Them",
     "instruction": "Review everyone's fundraising-process ideas together with the ways the organization presently raises money from its donors, business supporters and grantors. Keep the present methods that should continue and select or add stronger methods where needed."},
]

AREA_DEFS = [
    {"key": "who_should_fund", "title": "The Exact Type Of People, Businesses and Grantors Meant To Fund The Mission"},
    {"key": "where_to_find", "title": "Where To Consistently Find Them"},
    {"key": "attract_attention", "title": "How To Attract Their Attention"},
    {"key": "fundraising_process", "title": "The Exact Process To Raise Money Exponentially"},
]

AUDIENCE_BUCKETS = {"individual": "people", "business": "businesses", "grantor": "grantors"}
SECTION_ID_BY_KEY = {section["key"]: section["id"] for section in GAME_SECTION_DEFAULTS}
STAGE_LABELS = {section["key"]: {stage["key"]: stage["label"] for stage in section.get("stages", [])}
                for section in GAME_SECTION_DEFAULTS if section.get("stages")}

ROONEY_RECOMMENDATIONS = {
    "who_should_fund": ["Prioritize people whose lived experience, values or personal story connects directly to the mission.", "Identify businesses whose customers, employees, location or social-impact priorities connect to the people the organization serves.", "Focus grant research on funders whose stated priorities, geography and eligible costs match the mission and the purpose of the fundraising goal."],
    "where_to_find": ["Map the Board's existing personal, professional, business and community networks before starting cold outreach.", "Use trusted places where each priority audience already gathers, learns or makes decisions.", "Build a repeatable prospect-research routine instead of relying on occasional searches."],
    "attract_attention": ["Create useful mission-connected content or experiences that give potential funders a reason to engage before an ask.", "Use credible impact evidence, stories and leadership visibility to build attention and trust.", "Create a clear corporate or grantor-facing value proposition for each priority audience."],
    "fundraising_process": ["Use the relationship pathway KNOW, LIKE, TRUST, ASK, FOLLOW UP and STEWARD for every priority audience.", "Define the next action and follow-up point for every prospect relationship.", "Treat stewardship as the beginning of the next gift or partnership rather than the end of the process."],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalise(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", str(text).lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def required_rank_for(idea_count: int) -> int:
    if idea_count == 0:
        return 0
    if idea_count <= 3:
        return idea_count
    if idea_count <= 7:
        return 3
    return 5


def fmt_goal(profile: dict) -> str:
    amount = (profile.get("goal") or {}).get("amount") or 0
    return f"${int(amount):,}" if amount else "its fundraising goal"


def contributor_names(names: list) -> str:
    unique = list(dict.fromkeys(names))
    if len(unique) == 1:
        return unique[0]
    return ", ".join(unique[:-1]) + " and " + unique[-1]


def dedupe_texts(items: list) -> list:
    seen = set()
    out = []
    for item in items:
        key = normalise(item)
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def strategy_item_text(item) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return " — ".join(str(item.get(key, "")).strip() for key in ("title", "explanation", "focus") if str(item.get(key, "")).strip())
    return str(item or "").strip()


def working_strategy_ideas(data: dict, section_key: str) -> list:
    if not isinstance(data, dict):
        return []
    if section_key == "who_should_fund":
        audiences = data.get("fundraising_audiences") or {}
        if any(audiences.get(key) for key in ("individuals", "businesses", "grantors")):
            ideas = []
            for key, label in (("individuals", "INDIVIDUALS"), ("businesses", "BUSINESSES"), ("grantors", "GRANTORS")):
                for item in audiences.get(key) or []:
                    text = strategy_item_text(item)
                    if text:
                        ideas.append(f"{label}: {text}")
            return ideas
        return [strategy_item_text(item) for item in ((data.get("fundraising_audiences") or {}).get("priorities") or []) if strategy_item_text(item)]
    if section_key in {"where_to_find", "attract_attention", "technology", "materials"}:
        source_key={"attract_attention":"attraction"}.get(section_key,section_key)
        return [strategy_item_text(item) for item in ((data.get(source_key) or {}).get("priorities") or []) if strategy_item_text(item)]
    if section_key == "fundraising_process":
        process=data.get("fundraising_process") or [];ideas=[]
        if isinstance(process, dict):
            audience_processes = [("", process)]
            if any(isinstance(process.get(key), dict) for key in ("individuals", "businesses", "grantors")):
                audience_processes = [(key.upper(), process.get(key) or {}) for key in ("individuals", "businesses", "grantors")]
            for audience, audience_process in audience_processes:
                for stage in ("know","like","trust","ask","follow_up","steward"):
                    for item in audience_process.get(stage) or []:
                        text=strategy_item_text(item)
                        if text:ideas.append(f"{audience + ': ' if audience else ''}{stage.replace('_',' ').upper()}: {text}")
        return ideas
    if section_key == "team":
        return [strategy_item_text(item) for item in ((data.get("fundraising_team") or {}).get("priorities") or []) if strategy_item_text(item)]
    if section_key == "budget":
        budget = data.get("execution_budget") or {}
        ideas = []
        if isinstance(budget, dict):
            for item in budget.get("required_now") or []:
                text = strategy_item_text(item)
                if text: ideas.append(f"REQUIRED NOW: {text}")
            for item in budget.get("later") or []:
                text = strategy_item_text(item)
                if text: ideas.append(f"LATER: {text}")
            summary = str(budget.get("budget_summary") or "").strip()
            if summary: ideas.append(f"BUDGET APPROACH: {summary}")
        return ideas
    if section_key == "execution":
        timeline=data.get("execution_timeline") or {};ideas=[]
        if isinstance(timeline, dict):
            for stage in ("set_up","launch","execute","review_and_improve"):
                for item in timeline.get(stage) or []:
                    text=strategy_item_text(item)
                    if text:ideas.append(f"{stage.replace('_',' ').upper()}: {text}")
        return ideas
    return []


def extract_ideas(response: dict, section_key: str) -> list:
    """Return individual idea strings from an Individual Game response document.
    V2 responses carry a deterministic flat group_game_ideas list; use it when present."""
    v2_ideas = [str(item).strip() for item in (response.get("group_game_ideas") or []) if str(item).strip()]
    if v2_ideas:
        return dedupe_texts(v2_ideas)
    ideas = []
    final = [item for item in (response.get("final_response") or []) if str(item).strip()]
    ideas.extend(final)
    for items in (response.get("guided_selections") or {}).values():
        ideas.extend(item for item in items if str(item).strip())
    for items in (response.get("additional_ideas") or {}).values():
        ideas.extend(item for item in items if str(item).strip())
    labels = STAGE_LABELS.get(section_key, {})
    for stage_key, value in (response.get("stage_responses") or {}).items():
        label = labels.get(stage_key, stage_key.replace("_", " ").upper())
        entries = value if isinstance(value, list) else [value]
        for entry in entries:
            if str(entry).strip():
                ideas.append(f"{label}: {str(entry).strip()}")
    if not final:
        ideas.extend(item for item in (response.get("first_response") or []) if str(item).strip())
    return dedupe_texts(ideas)


def area_ideas(response: dict, source_key: str, audience_type: str = "") -> list:
    """Final APPROVED fine-tuned entries feed the Group Game; deterministic fallbacks for records without fine-tuning."""
    approved = [entry for entry in (response.get("approved_entries") or [])
                if isinstance(entry, dict) and str(entry.get("text", "")).strip()]
    if approved:
        if audience_type:
            return dedupe_texts([str(entry["text"]).strip() for entry in approved if entry.get("audience_type") == audience_type])
        return dedupe_texts([str(entry["text"]).strip() for entry in approved])
    extras = response.get("extras") or {}
    if audience_type:
        bucket = AUDIENCE_BUCKETS[audience_type]
        items = [str(item).strip() for item in (extras.get(bucket) or []) if str(item).strip()]
        if items or any(extras.get(name) for name in AUDIENCE_BUCKETS.values()):
            return items
        return extract_ideas(response, source_key) if audience_type == "individual" else []
    return extract_ideas(response, source_key)


class JoinPayload(BaseModel):
    slot_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1, max_length=120)


class SubmitPayload(BaseModel):
    slot_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1, max_length=120)
    round_number: int = Field(ge=1, le=TOTAL_ROUNDS)
    rankings: list = Field(default_factory=list)


class CloseRoundPayload(BaseModel):
    round_number: int = Field(ge=1, le=TOTAL_ROUNDS)


class HostDecisionPayload(BaseModel):
    round_number: int = Field(ge=1, le=TOTAL_ROUNDS)
    selected_idea_ids: list = Field(default_factory=list)
    additional_agreed_ideas: list = Field(default_factory=list)


def create_group_game_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def game_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        return member

    async def get_profile(user_id: str) -> dict:
        return await db.game_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}

    async def active_session(user_id: str) -> dict:
        return await db.group_game_sessions.find_one(
            {"user_id": user_id, "status": {"$ne": "archived"}}, {"_id": 0}, sort=[("created_at", -1)])

    async def board_members(user_id: str) -> list:
        return await db.game_board_members.find(
            {"user_id": user_id, "removed": {"$ne": True}}, {"_id": 0}).sort("created_at", 1).to_list(200)

    async def build_rounds_and_ideas(session_id: str, user_id: str, organization: str):
        await db.group_game_rounds.delete_many({"session_id": session_id})
        await db.group_game_ideas.delete_many({"session_id": session_id})
        await db.group_game_rankings.delete_many({"session_id": session_id})
        await db.group_game_results.delete_many({"session_id": session_id})
        await db.group_game_host_decisions.delete_many({"session_id": session_id})
        members = await board_members(user_id)
        member_names = {record["member_id"]: record["full_name"].split(" ")[0] for record in members}
        member_ids = list(member_names.keys())
        situation = await db.game_situations.find_one({"user_id": user_id}, {"_id": 0}) or {}
        situation_sections = situation.get("sections") or {}
        working = await db.game_strategies.find_one({"user_id":user_id,"mode":"working"},{"_id":0},sort=[("generated_at",-1)]) or {}
        working_data=working.get("data") or {}
        for definition in ROUND_DEFS:
            section_id = SECTION_ID_BY_KEY.get(definition.get("source_key", ""))
            responses = []
            if section_id:
                responses = await db.game_section_responses.find(
                    {"user_id": user_id, "board_member_id": {"$in": member_ids}, "section_id": section_id},
                    {"_id": 0}).to_list(300)
            pool = {}
            order = 0
            for response in responses:
                name = member_names.get(response["board_member_id"], "Board Member")
                for raw in area_ideas(response, definition.get("source_key", ""), definition.get("audience_type", "")):
                    text = str(raw).strip()[:400]
                    key = normalise(text)
                    if not key:
                        continue
                    if key not in pool:
                        pool[key] = {"idea_id": new_uuid(), "session_id": session_id,
                                     "round_number": definition["round_number"],
                                     "section_key": definition["section_key"],
                                     "text": text, "normalized": key,
                                     "contributor_names": [], "contributor_ids": [], "order": order}
                        order += 1
                    if response["board_member_id"] not in pool[key]["contributor_ids"]:
                        pool[key]["contributor_ids"].append(response["board_member_id"])
                        pool[key]["contributor_names"].append(name)
            v3_reality = situation_sections.get("current_reality") or {}

            def add_reality(value, label="Organization reality"):
                nonlocal order
                if str(value or "").strip():
                    text = str(value).strip()[:800]
                    key = normalise(text)
                    if key and key not in pool:
                        pool[key] = {"idea_id": new_uuid(), "session_id": session_id,
                                     "round_number": definition["round_number"], "section_key": definition["section_key"],
                                     "text": text, "normalized": key, "contributor_names": [label],
                                     "contributor_ids": [], "order": order}
                        order += 1

            if definition["section_key"] == "who_should_fund":
                present_funders = [
                    ("Organization's present individual donors", "PRESENT INDIVIDUAL DONORS", ["current_individual_donor_profile", "current_individual_donor_motivation"], "current_individual_donors"),
                    ("Organization's present business supporters", "PRESENT CORPORATE SPONSORS / BUSINESS PARTNERS", ["current_business_profile", "current_business_support"], "current_businesses"),
                    ("Organization's present grantors", "PRESENT GRANTORS", ["current_grantor_profile", "current_grantor_support"], "current_grantors"),
                ]
                for label, heading, fields, legacy_key in present_funders:
                    parts = [str(v3_reality.get(field) or "").strip() for field in fields if str(v3_reality.get(field) or "").strip()]
                    if not parts and str(v3_reality.get(legacy_key) or "").strip():
                        parts = [str(v3_reality.get(legacy_key)).strip()]
                    if parts:
                        add_reality(f"{heading}: " + " | ".join(parts), label)
            elif definition["section_key"] == "fundraising_process":
                present_processes = [
                    ("Organization's present individual-donor method", "PRESENT INDIVIDUAL DONOR METHOD", "current_individual_donor_process", "individual_fundraising_process", "current_individual_donors"),
                    ("Organization's present business-support method", "PRESENT BUSINESS / SPONSOR METHOD", "current_business_process", "business_fundraising_process", "current_businesses"),
                    ("Organization's present grant-fundraising method", "PRESENT GRANTOR METHOD", "current_grantor_process", "grant_fundraising_process", "current_grantors"),
                ]
                for label, heading, field, old_field, legacy_key in present_processes:
                    value = v3_reality.get(field) or v3_reality.get(old_field) or v3_reality.get(legacy_key) or ""
                    if str(value).strip():
                        add_reality(f"{heading}: {str(value).strip()}", label)
            for recommendation in working_strategy_ideas(working_data,definition["section_key"]):
                key=normalise(recommendation)
                if key not in pool:
                    pool[key]={"idea_id":new_uuid(),"session_id":session_id,"round_number":definition["round_number"],"section_key":definition["section_key"],
                        "text":recommendation[:800],"normalized":key,"contributor_names":["Nonprofit Board Builder recommendation based on your working strategy"],"contributor_ids":[],"order":order};order+=1
            recommendations = ROONEY_RECOMMENDATIONS.get(definition["section_key"], [])
            for recommendation in recommendations:
                key=normalise(recommendation)
                if key not in pool:
                    pool[key]={"idea_id":new_uuid(),"session_id":session_id,"round_number":definition["round_number"],"section_key":definition["section_key"],"text":recommendation,"normalized":key,"contributor_names":["Nonprofit Board Builder recommendation"],"contributor_ids":[],"order":order};order+=1
            ideas = sorted(pool.values(), key=lambda item: item["order"])
            if ideas:
                await db.group_game_ideas.insert_many([idea.copy() for idea in ideas])
            await db.group_game_rounds.insert_one({
                "round_id": new_uuid(), "session_id": session_id,
                "round_number": definition["round_number"], "section_key": definition["section_key"],
                "title": definition["title"],
                "instruction": definition["instruction"].replace("{organization}", organization),
                "status": "waiting", "required_rank": 0,
                "idea_count": len(ideas), "started_at": "", "closed_at": "", "created_at": now_iso(),
            })

    async def session_rounds(session_id: str) -> list:
        return await db.group_game_rounds.find({"session_id": session_id}, {"_id": 0}).sort("round_number", 1).to_list(20)

    def dedupe_idea_docs(ideas: list) -> tuple:
        """One canonical idea per normalized text. Returns (ordered unique idea docs, alias map idea_id -> canonical idea_id)."""
        canonical = {}
        alias = {}
        ordered = []
        for idea in ideas:
            key = idea.get("normalized") or normalise(idea["text"])
            if key in canonical:
                canon = canonical[key]
                alias[idea["idea_id"]] = canon["idea_id"]
                for name in idea.get("contributor_names", []):
                    if name not in canon["contributor_names"]:
                        canon["contributor_names"].append(name)
                continue
            entry = {**idea, "contributor_names": list(idea.get("contributor_names", []))}
            canonical[key] = entry
            alias[idea["idea_id"]] = idea["idea_id"]
            ordered.append(entry)
        return ordered, alias

    async def round_ideas(session_id: str, round_number: int) -> list:
        ideas = await db.group_game_ideas.find(
            {"session_id": session_id, "round_number": round_number}, {"_id": 0}).sort("order", 1).to_list(400)
        unique, _ = dedupe_idea_docs(ideas)
        return [{"idea_id": idea["idea_id"], "text": idea["text"],
                 "suggested_by": contributor_names(idea["contributor_names"])} for idea in unique]

    async def participants(session_id: str) -> list:
        return await db.group_game_participants.find({"session_id": session_id}, {"_id": 0}).to_list(300)

    async def submitted_slots(session_id: str, round_number: int) -> set:
        rows = await db.group_game_rankings.find(
            {"session_id": session_id, "round_number": round_number}, {"_id": 0, "slot_id": 1}).to_list(300)
        return {row["slot_id"] for row in rows}

    async def round_results(session_id: str, round_number: int) -> dict:
        return await db.group_game_results.find_one(
            {"session_id": session_id, "round_number": round_number}, {"_id": 0}) or {}

    async def host_decision(session_id: str, round_number: int) -> dict:
        return await db.group_game_host_decisions.find_one(
            {"session_id":session_id,"round_number":round_number},{"_id":0}) or {}

    # ---------- Host endpoints ----------

    @router.get("/game/group/overview")
    async def group_overview(request: Request):
        member = await game_member(request)
        profile = await get_profile(member["user_id"])
        night = await db.game_nights.find_one({"user_id": member["user_id"]}, {"_id": 0}) or {}
        members = await board_members(member["user_id"])
        completed = 0
        in_progress = 0
        ideas_ready = 0
        strategy_ids = list({SECTION_ID_BY_KEY[definition["source_key"]] for definition in ROUND_DEFS if definition.get("source_key")})
        for record in members:
            done = await db.game_section_responses.count_documents(
                {"board_member_id": record["member_id"], "completed": True})
            if done >= (record.get("total_sections") or 10):
                completed += 1
            elif done > 0:
                in_progress += 1
            ideas_ready += await db.game_section_responses.count_documents(
                {"board_member_id": record["member_id"], "section_id": {"$in": strategy_ids}, "completed": True})
        session = await active_session(member["user_id"])
        session_summary = None
        if session:
            joined = await participants(session["session_id"])
            session_summary = {
                "session_id": session["session_id"], "token": session["token"], "status": session["status"],
                "current_round": session.get("current_round", 0),
                "participants_joined": len(joined), "completed_at": session.get("completed_at", ""),
            }
        return {
            "goal_display": fmt_goal(profile),
            "funding_deadline": night.get("funding_deadline") or (profile.get("goal") or {}).get("deadline", ""),
            "game_night_date": night.get("meeting_date", ""),
            "board_member_count": len(members),
            "individual_completed": completed,
            "individual_in_progress": in_progress,
            "responses_ready": ideas_ready,
            "session": session_summary,
        }

    @router.post("/game/group/prepare")
    async def prepare_group_game(request: Request):
        member = await game_member(request)
        profile = await get_profile(member["user_id"])
        organization = (profile.get("organization") or {}).get("name", "your organization")
        session = await active_session(member["user_id"])
        if session and session.get("game_version") != GROUP_GAME_VERSION:
            await db.group_game_sessions.update_one(
                {"session_id": session["session_id"]},
                {"$set": {"status": "archived", "updated_at": now_iso()}},
            )
            session = None
        if session and session["status"] == "in_progress":
            return {"session": session}
        if session and session["status"] in {"prepared", "waiting"}:
            await build_rounds_and_ideas(session["session_id"], member["user_id"], organization)
            await db.group_game_sessions.update_one(
                {"session_id": session["session_id"]}, {"$set": {"updated_at": now_iso()}})
            return {"session": await active_session(member["user_id"])}
        if session and session["status"] == "completed":
            await db.group_game_sessions.update_one(
                {"session_id": session["session_id"]}, {"$set": {"status": "archived", "updated_at": now_iso()}})
        session_id = new_uuid()
        record = {
            "session_id": session_id, "user_id": member["user_id"],
            "token": secrets.token_urlsafe(24), "status": "waiting", "current_round": 0,
            "game_version": GROUP_GAME_VERSION,
            "created_at": now_iso(), "started_at": "", "completed_at": "", "updated_at": now_iso(),
        }
        await db.group_game_sessions.insert_one(record.copy())
        await build_rounds_and_ideas(session_id, member["user_id"], organization)
        return {"session": record}

    @router.get("/game/group/session")
    async def host_session_state(request: Request):
        member = await game_member(request)
        session = await active_session(member["user_id"])
        if not session:
            raise HTTPException(status_code=404, detail="No Group Game session yet")
        members = await board_members(member["user_id"])
        joined = {row["board_member_id"]: row for row in await participants(session["session_id"])}
        rounds = await session_rounds(session["session_id"])
        current_number = session.get("current_round", 0)
        current = next((item for item in rounds if item["round_number"] == current_number), None)
        player_status = []
        for record in members:
            row = joined.get(record["member_id"])
            player_status.append({
                "name": record["full_name"].split(" ")[0],
                "joined": bool(row),
                "submitted": False,
            })
        closed_rounds = []
        for item in rounds:
            if item["status"] == "closed":
                closed_rounds.append({
                    "round_number": item["round_number"], "title": item["title"],
                    "results": (await round_results(session["session_id"], item["round_number"])).get("results", []),
                })
        return {
            "session": {"token": session["token"], "status": session["status"], "current_round": current_number},
            "players": player_status,
            "joined_count": len(joined),
            "board_member_count": len(members),
            "current_round": None if not current else {
                "round_number": current["round_number"], "title": current["title"],
                "instruction": current["instruction"], "status": current["status"],
                "required_rank": current["required_rank"], "idea_count": current["idea_count"],
                "ideas": await round_ideas(session["session_id"], current["round_number"]),
                "submitted_count": 0,
                "selected_idea_ids":(await host_decision(session["session_id"],current["round_number"])).get("selected_idea_ids",[]),
                "additional_agreed_ideas":(await host_decision(session["session_id"],current["round_number"])).get("additional_agreed_ideas",[]),
                "results": (await round_results(session["session_id"], current["round_number"])).get("results", []) if current["status"] == "closed" else [],
            },
            "closed_rounds": closed_rounds,
            "total_rounds": TOTAL_ROUNDS,
        }

    @router.post("/game/group/start")
    async def start_group_game(request: Request):
        member = await game_member(request)
        session = await active_session(member["user_id"])
        if not session or session["status"] not in {"waiting", "prepared"}:
            raise HTTPException(status_code=409, detail="The Group Game is not ready to start")
        await db.group_game_sessions.update_one(
            {"session_id": session["session_id"]},
            {"$set": {"status": "in_progress", "current_round": 1, "started_at": now_iso(), "updated_at": now_iso()}})
        await db.group_game_rounds.update_one(
            {"session_id": session["session_id"], "round_number": 1},
            {"$set": {"status": "open", "started_at": now_iso()}})
        return {"status": "started"}

    async def compute_results(session_id: str, round_doc: dict):
        ideas = await db.group_game_ideas.find(
            {"session_id": session_id, "round_number": round_doc["round_number"]}, {"_id": 0}).sort("order", 1).to_list(400)
        unique,_=dedupe_idea_docs(ideas);decision=await host_decision(session_id,round_doc["round_number"])
        if decision:
            selected=[str(x) for x in decision.get("selected_idea_ids") or []];selected_order={idea_id:index for index,idea_id in enumerate(selected)}
            results=[]
            for idea in unique:
                chosen=idea["idea_id"] in selected
                results.append({"idea_id":idea["idea_id"],"text":idea["text"],"suggested_by":contributor_names(idea["contributor_names"]),
                    "total_score":1 if chosen else 0,"first_place_count":1 if chosen and selected_order.get(idea["idea_id"])==0 else 0,
                    "selection_count":1 if chosen else 0,"order":idea["order"],"rank":selected_order.get(idea["idea_id"],999)+1 if chosen else 0,
                    "prioritised":chosen,"additional":not chosen,"decision_source":"board_checkbox"})
            for index,text_value in enumerate(decision.get("additional_agreed_ideas") or []):
                text_value=str(text_value).strip()
                if text_value:
                    results.append({"idea_id":f"discussion-{new_uuid()}","text":text_value[:1200],"suggested_by":"Board discussion",
                        "total_score":1,"first_place_count":0,"selection_count":1,"order":len(unique)+index,"rank":len(selected)+index+1,
                        "prioritised":True,"additional":False,"decision_source":"board_discussion"})
        else:
            rankings = await db.group_game_rankings.find(
                {"session_id": session_id, "round_number": round_doc["round_number"]}, {"_id": 0}).to_list(300)
            alias={idea["idea_id"]:idea["idea_id"] for idea in unique};stats={idea["idea_id"]:{"idea_id":idea["idea_id"],"text":idea["text"],
                "suggested_by":contributor_names(idea["contributor_names"]),"total_score":0,"first_place_count":0,"selection_count":0,"order":idea["order"]} for idea in unique}
            for row in rankings:
                for entry in row.get("rankings",[]):
                    stat=stats.get(alias.get(entry.get("idea_id"),entry.get("idea_id")))
                    if not stat:continue
                    stat["total_score"]+=entry.get("points",0);stat["selection_count"]+=1
                    if entry.get("position")==1:stat["first_place_count"]+=1
            ordered=sorted(stats.values(),key=lambda item:(-item["total_score"],-item["first_place_count"],-item["selection_count"],item["order"]))
            results=[{**stat,"rank":index+1 if stat.get("selection_count") else 0,"prioritised":bool(stat.get("selection_count")),"additional":not bool(stat.get("selection_count"))} for index,stat in enumerate(ordered)]
        await db.group_game_results.update_one(
            {"session_id":session_id,"round_number":round_doc["round_number"]},
            {"$set":{"session_id":session_id,"round_number":round_doc["round_number"],"round_id":round_doc["round_id"],
                     "section_key":round_doc["section_key"],"title":round_doc["title"],"results":results,"computed_at":now_iso()}},upsert=True)

    @router.post("/game/group/decision")
    async def save_host_decision(payload: HostDecisionPayload, request: Request):
        member=await game_member(request);session=await active_session(member["user_id"])
        if not session or session["status"]!="in_progress" or session.get("current_round")!=payload.round_number:
            raise HTTPException(status_code=409,detail="This review screen is no longer open")
        round_doc=await db.group_game_rounds.find_one({"session_id":session["session_id"],"round_number":payload.round_number},{"_id":0})
        if not round_doc or round_doc.get("status")!="open":raise HTTPException(status_code=409,detail="This review screen is not open")
        valid_rows=await db.group_game_ideas.find({"session_id":session["session_id"],"round_number":payload.round_number},{"_id":0,"idea_id":1}).to_list(500);valid={row["idea_id"] for row in valid_rows};selected=[]
        for idea_id in payload.selected_idea_ids:
            idea_id=str(idea_id)
            if idea_id in valid and idea_id not in selected:selected.append(idea_id)
        additions=[];seen=set()
        for item in payload.additional_agreed_ideas:
            clean=str(item).strip()[:1200];key=normalise(clean)
            if clean and key not in seen:seen.add(key);additions.append(clean)
        await db.group_game_host_decisions.update_one(
            {"session_id":session["session_id"],"round_number":payload.round_number},
            {"$set":{"session_id":session["session_id"],"round_number":payload.round_number,"selected_idea_ids":selected,
                     "additional_agreed_ideas":additions,"updated_at":now_iso()},"$setOnInsert":{"created_at":now_iso()}},upsert=True)
        return {"status":"saved","selected_idea_ids":selected,"additional_agreed_ideas":additions}


    @router.post("/game/group/close-round")
    async def close_round(payload: CloseRoundPayload, request: Request):
        member = await game_member(request)
        session = await active_session(member["user_id"])
        if not session or session["status"] != "in_progress":
            raise HTTPException(status_code=409, detail="The Group Game is not in progress")
        round_doc = await db.group_game_rounds.find_one(
            {"session_id": session["session_id"], "round_number": payload.round_number}, {"_id": 0})
        if not round_doc or round_doc["status"] != "open":
            raise HTTPException(status_code=409, detail="This round is not open")
        decision=await host_decision(session["session_id"],payload.round_number)
        if not decision or (not decision.get("selected_idea_ids") and not decision.get("additional_agreed_ideas")):
            raise HTTPException(status_code=422, detail="Select at least one idea the Board agrees with, or add the Board's agreed idea from the discussion")
        await compute_results(session["session_id"], round_doc)
        await db.group_game_rounds.update_one(
            {"session_id": session["session_id"], "round_number": payload.round_number},
            {"$set": {"status": "closed", "closed_at": now_iso()}})
        return {"status": "closed"}

    @router.post("/game/group/next-round")
    async def next_round(request: Request):
        member = await game_member(request)
        session = await active_session(member["user_id"])
        if not session or session["status"] != "in_progress":
            raise HTTPException(status_code=409, detail="The Group Game is not in progress")
        current = session.get("current_round", 0)
        current_doc = await db.group_game_rounds.find_one(
            {"session_id": session["session_id"], "round_number": current}, {"_id": 0})
        if current_doc and current_doc["status"] != "closed":
            raise HTTPException(status_code=409, detail="Complete the discussion on the current screen first")
        if current >= TOTAL_ROUNDS:
            await db.group_game_sessions.update_one(
                {"session_id": session["session_id"]},
                {"$set": {"status": "completed", "completed_at": now_iso(), "updated_at": now_iso()}})
            return {"status": "completed"}
        upcoming = current + 1
        await db.group_game_sessions.update_one(
            {"session_id": session["session_id"]},
            {"$set": {"current_round": upcoming, "updated_at": now_iso()}})
        await db.group_game_rounds.update_one(
            {"session_id": session["session_id"], "round_number": upcoming},
            {"$set": {"status": "open", "started_at": now_iso()}})
        return {"status": "opened", "round_number": upcoming}

    @router.get("/game/group/results")
    async def group_results(request: Request):
        member = await game_member(request)
        session = await db.group_game_sessions.find_one(
            {"user_id": member["user_id"], "status": {"$in": ["completed", "in_progress"]}},
            {"_id": 0}, sort=[("created_at", -1)])
        if not session:
            raise HTTPException(status_code=404, detail="No Group Game results yet")
        joined = await participants(session["session_id"])
        rows = await db.group_game_results.find(
            {"session_id": session["session_id"]}, {"_id": 0}).sort("round_number", 1).to_list(20)
        areas = [{
            "round_number": row["round_number"], "title": row["title"], "section_key": row["section_key"],
            "priorities": [item for item in row["results"] if item["prioritised"]],
            "additional": [item for item in row["results"] if not item["prioritised"]],
        } for row in rows]
        return {
            "status": session["status"], "completed_at": session.get("completed_at", ""),
            "rounds_completed": len(rows), "total_rounds": TOTAL_ROUNDS,
            "participants": len(joined), "areas": areas,
        }

    # ---------- Player (shared secure link, no account) ----------

    async def session_by_token(token: str) -> dict:
        session = await db.group_game_sessions.find_one(
            {"token": token, "status": {"$ne": "archived"}}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="This Group Game link is not valid")
        return session

    @router.get("/game/group/play/{token}")
    async def group_entry(token: str):
        session = await session_by_token(token)
        profile = await get_profile(session["user_id"])
        member = await db.members.find_one({"user_id": session["user_id"]}, {"_id": 0, "first_name": 1}) or {}
        members = await board_members(session["user_id"])
        joined = {row["board_member_id"]: row for row in await participants(session["session_id"])}
        return {
            "organization_name": (profile.get("organization") or {}).get("name", ""),
            "goal_display": fmt_goal(profile),
            "host_first_name": member.get("first_name", ""),
            "status": session["status"],
            "players": [{
                "slot_id": record["token"], "name": record["full_name"].split(" ")[0],
                "joined": record["member_id"] in joined,
            } for record in members],
        }

    async def slot_board_member(session: dict, slot_id: str) -> dict:
        record = await db.game_board_members.find_one(
            {"user_id": session["user_id"], "token": slot_id, "removed": {"$ne": True}}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Player not found for this Game Night")
        return record

    @router.post("/game/group/play/{token}/join")
    async def group_join(token: str, payload: JoinPayload):
        session = await session_by_token(token)
        record = await slot_board_member(session, payload.slot_id)
        existing = await db.group_game_participants.find_one(
            {"session_id": session["session_id"], "board_member_id": record["member_id"]}, {"_id": 0})
        if existing and existing.get("device_id") != payload.device_id:
            raise HTTPException(status_code=409, detail="Already Joined")
        if not existing:
            await db.group_game_participants.insert_one({
                "participant_id": new_uuid(), "session_id": session["session_id"],
                "board_member_id": record["member_id"], "slot_id": payload.slot_id,
                "name": record["full_name"].split(" ")[0], "device_id": payload.device_id,
                "joined_at": now_iso(), "last_active_at": now_iso(),
            })
        else:
            await db.group_game_participants.update_one(
                {"session_id": session["session_id"], "board_member_id": record["member_id"]},
                {"$set": {"last_active_at": now_iso()}})
        return {"status": "joined", "name": record["full_name"].split(" ")[0]}

    @router.get("/game/group/play/{token}/state")
    async def group_state(token: str, slot: str = "", device: str = ""):
        session = await session_by_token(token)
        profile = await get_profile(session["user_id"])
        member = await db.members.find_one({"user_id": session["user_id"]}, {"_id": 0, "first_name": 1}) or {}
        joined = await participants(session["session_id"])
        me = next((row for row in joined if row["slot_id"] == slot and row.get("device_id") == device), None)
        if me:
            await db.group_game_participants.update_one(
                {"participant_id": me["participant_id"]}, {"$set": {"last_active_at": now_iso()}})
        current_number = session.get("current_round", 0)
        current = await db.group_game_rounds.find_one(
            {"session_id": session["session_id"], "round_number": current_number}, {"_id": 0}) if current_number else None
        my_submitted = False
        if me and current:
            my_submitted = bool(await db.group_game_rankings.find_one(
                {"session_id": session["session_id"], "round_number": current_number, "slot_id": slot}, {"_id": 0, "slot_id": 1}))
        return {
            "status": session["status"],
            "organization_name": (profile.get("organization") or {}).get("name", ""),
            "goal_display": fmt_goal(profile),
            "host_first_name": member.get("first_name", ""),
            "joined": bool(me),
            "joined_count": len(joined),
            "total_rounds": TOTAL_ROUNDS,
            "current_round": None if not current else {
                "round_number": current["round_number"], "title": current["title"],
                "instruction": current["instruction"], "status": current["status"],
                "required_rank": current["required_rank"],
                "ideas": await round_ideas(session["session_id"], current_number) if current["status"] in {"open", "closed"} else [],
                "selected_idea_ids":(await host_decision(session["session_id"],current_number)).get("selected_idea_ids",[]),
                "additional_agreed_ideas":(await host_decision(session["session_id"],current_number)).get("additional_agreed_ideas",[]),
                "submitted_count": 0,
                "my_submitted": False,
                "results": (await round_results(session["session_id"], current_number)).get("results", []) if current["status"] == "closed" else [],
            },
        }

    @router.post("/game/group/play/{token}/submit")
    async def group_submit(token: str, payload: SubmitPayload):
        session = await session_by_token(token)
        if session["status"] != "in_progress" or session.get("current_round") != payload.round_number:
            raise HTTPException(status_code=409, detail="This round is no longer open")
        me = await db.group_game_participants.find_one(
            {"session_id": session["session_id"], "slot_id": payload.slot_id, "device_id": payload.device_id}, {"_id": 0})
        if not me:
            raise HTTPException(status_code=403, detail="Join the game before submitting a ranking")
        round_doc = await db.group_game_rounds.find_one(
            {"session_id": session["session_id"], "round_number": payload.round_number}, {"_id": 0})
        if not round_doc or round_doc["status"] != "open":
            raise HTTPException(status_code=409, detail="Voting for this round is closed")
        existing = await db.group_game_rankings.find_one(
            {"session_id": session["session_id"], "round_number": payload.round_number, "slot_id": payload.slot_id}, {"_id": 0, "slot_id": 1})
        if existing:
            raise HTTPException(status_code=409, detail="Your ranking for this round is already submitted")
        required = round_doc["required_rank"]
        idea_ids = [str(idea_id) for idea_id in payload.rankings]
        if len(idea_ids) != required or len(set(idea_ids)) != required:
            raise HTTPException(status_code=422, detail=f"Rank exactly {required} ideas")
        valid = await db.group_game_ideas.count_documents(
            {"session_id": session["session_id"], "round_number": payload.round_number, "idea_id": {"$in": idea_ids}})
        if valid != required:
            raise HTTPException(status_code=422, detail="One or more ranked ideas are not part of this round")
        entries = [{"idea_id": idea_id, "position": index + 1, "points": required - index}
                   for index, idea_id in enumerate(idea_ids)]
        await db.group_game_rankings.insert_one({
            "session_id": session["session_id"], "round_id": round_doc["round_id"],
            "round_number": payload.round_number, "participant_id": me["participant_id"],
            "slot_id": payload.slot_id, "rankings": entries, "submitted_at": now_iso(),
        })
        return {"status": "submitted"}

    return router
