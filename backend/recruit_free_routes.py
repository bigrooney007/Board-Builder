"""Public four-question Board Recruitment assessment and paid-flow handoff."""
import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ai_service import generate_structured
from member_auth import authenticate_member, new_uuid, require_entitlement


ASSESSMENT_COLLECTION_NAMES = (
    "recruitment_free_assessments",
    "recruit_free_assessments",
    "free_recruitment_assessments",
)
QUESTION_KEYS = {1: "mission", 2: "current_board", 3: "important_areas", 4: "support_needs"}
EVENTS = {
    "video_page_viewed",
    "checkout_started",
    "welcome_completed",
    "intake_completed",
    "dashboard_entered",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RecruitFreeStart(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    organization: str = Field(min_length=1, max_length=300)
    desired_count: str = Field(min_length=1, max_length=20)


class RecruitFreeAnswer(BaseModel):
    question: int = Field(ge=1, le=4)
    text: str = Field(min_length=1, max_length=12000)


class RecruitFreeEvent(BaseModel):
    event: str = Field(min_length=1, max_length=80)


def normalize_count(value: str):
    clean = str(value or "").strip().lower()
    if clean in {"not_sure", "not sure", "unsure"}:
        return None
    if not clean.isdigit() or not 1 <= int(clean) <= 50:
        raise HTTPException(status_code=422, detail="Enter a number from 1 to 50, or choose I'm not sure yet")
    return int(clean)


def public_assessment(doc: dict) -> dict:
    return {key: value for key, value in (doc or {}).items()
            if key not in {"_id", "created_at", "updated_at", "generation_error"}}


def assessment_collections(db):
    return [getattr(db, name) for name in ASSESSMENT_COLLECTION_NAMES]


async def find_assessment(db, query: dict):
    for collection in assessment_collections(db):
        doc = await collection.find_one(query, {"_id": 0}, sort=[("updated_at", -1)])
        if doc:
            return collection, doc
    return assessment_collections(db)[0], None


def lead_answers(doc: dict) -> dict:
    answers = doc.get("answers") or {}
    return {
        "mission": answers.get("mission", ""),
        "present_board": answers.get("current_board", ""),
        "important_areas": answers.get("important_areas", ""),
        "accomplish": answers.get("support_needs", ""),
        "new_members_needed": str(doc.get("desired_count") or "Not sure"),
    }


async def sync_funnel_lead(db, doc: dict) -> None:
    await db.funnel_leads.update_one(
        {"lead_id": doc["lead_id"]},
        {"$set": {
            "result_token": doc["token"],
            "offer_source": "recruitment",
            "lead_source": "recruitment_free_assessment",
            "name": doc["name"],
            "email": doc["email"],
            "organization": doc["organization"],
            "phone": "",
            "website": "",
            "city": "",
            "state_region": "",
            "country": "",
            "answers": lead_answers(doc),
            "free_assessment_result": doc.get("result"),
            "updated_at": now_iso(),
        }, "$setOnInsert": {
            "created_at": doc.get("created_at") or now_iso(),
            "owner_email_status": "Not required",
            "selected_tier": "",
        }},
        upsert=True,
    )


async def attach_free_assessment_to_member(db, lead_id: str, member: dict) -> None:
    """Carry the free result into the paid dashboard instead of making the buyer repeat it."""
    if not lead_id:
        return
    collection, assessment = await find_assessment(db, {"lead_id": lead_id})
    if not assessment:
        return
    timestamp = now_iso()
    await collection.update_one(
        {"token": assessment["token"]},
        {"$set": {"state.paid": True, "member_user_id": member["user_id"], "updated_at": timestamp}},
    )

    result = assessment.get("result") or {}
    if result and not await db.generated_materials.find_one({
        "user_id": member["user_id"], "type": "powerhouse_board_blueprint", "application_id": ""
    }, {"_id": 0, "material_id": 1}):
        from workspace_service import save_generation
        await save_generation(
            db,
            member["user_id"],
            "powerhouse_board_blueprint",
            result,
            "Four-question Board Recruitment assessment",
        )

    answers = assessment.get("answers") or {}
    role_names = [row.get("role_name", "") for row in result.get("priority_roles", []) if row.get("role_name")]
    incoming = {
        "organization_name": assessment.get("organization", ""),
        "mission": answers.get("mission", ""),
        "present_board": answers.get("current_board", ""),
        "new_members_count": str(assessment.get("desired_count") or "Not sure"),
        "current_board_strengths": answers.get("current_board", ""),
        "desired_board_skills": role_names,
        "priorities": answers.get("support_needs", ""),
        "important_areas": answers.get("important_areas", ""),
    }
    existing = await db.recruitment_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0}) or {}
    data = existing.get("data") or {}
    merged = {**incoming, **{key: value for key, value in data.items() if value not in (None, "", [])}}
    await db.recruitment_profiles.update_one(
        {"user_id": member["user_id"]},
        {"$set": {"data": merged, "confirmed": True, "recruitment_profile_confirmed": True,
                  "confirmed_at": timestamp, "updated_at": timestamp},
         "$setOnInsert": {"created_at": timestamp}},
        upsert=True,
    )


def create_recruit_free_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/recruit/free")
    primary = assessment_collections(db)[0]

    async def member_assessment(member: dict):
        collection, doc = await find_assessment(db, {"member_user_id": member["user_id"]})
        if doc:
            return collection, doc
        query = {"lead_id": {"$in": member.get("lead_ids", [])}} if member.get("lead_ids") else {"email": member["email"]}
        collection, doc = await find_assessment(db, query)
        if doc:
            await collection.update_one(
                {"token": doc["token"]},
                {"$set": {"member_user_id": member["user_id"], "state.paid": True, "updated_at": now_iso()}},
            )
            doc["member_user_id"] = member["user_id"]
            doc.setdefault("state", {})["paid"] = True
            return collection, doc
        lead = await db.funnel_leads.find_one(
            {"$or": [{"lead_id": {"$in": member.get("lead_ids", [])}}, {"email": member["email"]}]}, {"_id": 0}
        ) or {}
        timestamp = now_iso()
        doc = {
            "token": secrets.token_urlsafe(32), "lead_id": lead.get("lead_id") or new_uuid(),
            "name": lead.get("name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
            "email": member["email"], "organization": lead.get("organization") or "Your Organization",
            "desired_count": None, "answers": {}, "state": {"paid": True, "result_generated": False},
            "result": None, "member_user_id": member["user_id"], "created_at": timestamp, "updated_at": timestamp,
        }
        await primary.insert_one(doc.copy())
        await sync_funnel_lead(db, doc)
        return primary, doc

    @router.get("/member-assessment/current")
    async def current_member_assessment(request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {"fundraising_board_builder", "fbb_recruitment", "recruitment_self_guided"})
        _, doc = await member_assessment(member)
        return public_assessment(doc)

    @router.post("/start", status_code=201)
    async def start(payload: RecruitFreeStart):
        email = str(payload.email).lower()
        desired_count = normalize_count(payload.desired_count)
        collection, existing = await find_assessment(db, {"email": email, "state.paid": {"$ne": True}})
        if existing:
            updates = {
                "name": payload.name.strip(),
                "organization": payload.organization.strip(),
                "updated_at": now_iso(),
            }
            # Do not invalidate an already generated result merely because the entry form was reopened.
            if not existing.get("result"):
                updates["desired_count"] = desired_count
            await collection.update_one({"token": existing["token"]}, {"$set": updates})
            existing.update(updates)
            await sync_funnel_lead(db, existing)
            return public_assessment(existing)

        timestamp = now_iso()
        doc = {
            "token": secrets.token_urlsafe(32),
            "lead_id": new_uuid(),
            "name": payload.name.strip(),
            "email": email,
            "organization": payload.organization.strip(),
            "desired_count": desired_count,
            "answers": {},
            "state": {
                "lead_created": True,
                "question_1_completed": False,
                "question_2_completed": False,
                "question_3_completed": False,
                "question_4_completed": False,
                "result_generated": False,
                "video_page_viewed": False,
                "checkout_started": False,
                "paid": False,
                "welcome_completed": False,
                "intake_completed": False,
                "dashboard_entered": False,
            },
            "result": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        await primary.insert_one(doc.copy())
        await sync_funnel_lead(db, doc)
        return public_assessment(doc)

    @router.get("/{token}")
    async def read(token: str):
        _, doc = await find_assessment(db, {"token": token})
        if not doc:
            raise HTTPException(status_code=404, detail="Assessment not found")
        return public_assessment(doc)

    @router.put("/{token}/answer")
    async def answer(token: str, payload: RecruitFreeAnswer, request: Request):
        collection, doc = await find_assessment(db, {"token": token})
        if not doc:
            raise HTTPException(status_code=404, detail="Assessment not found")
        member = await authenticate_member(request, db)
        if doc.get("member_user_id") != member.get("user_id") or not doc.get("state", {}).get("paid"):
            raise HTTPException(status_code=403, detail="Complete your Board Recruitment purchase before answering these questions")
        key = QUESTION_KEYS[payload.question]
        text = payload.text.strip()
        timestamp = now_iso()
        await collection.update_one(
            {"token": token},
            {"$set": {f"answers.{key}": text, f"state.question_{payload.question}_completed": True,
                      "result": None, "state.result_generated": False, "updated_at": timestamp}},
        )
        doc.setdefault("answers", {})[key] = text
        doc["result"] = None
        await sync_funnel_lead(db, doc)
        return {"status": "saved", "question": payload.question}

    @router.post("/{token}/result")
    async def result(token: str, request: Request):
        collection, doc = await find_assessment(db, {"token": token})
        if not doc:
            raise HTTPException(status_code=404, detail="Assessment not found")
        member = await authenticate_member(request, db)
        if doc.get("member_user_id") != member.get("user_id") or not doc.get("state", {}).get("paid"):
            raise HTTPException(status_code=403, detail="Complete your Board Recruitment purchase before generating your result")
        if doc.get("result"):
            return {"result": doc["result"]}
        answers = doc.get("answers") or {}
        missing = [key for key in QUESTION_KEYS.values() if not str(answers.get(key) or "").strip()]
        if missing:
            raise HTTPException(status_code=409, detail="Answer all four questions before generating your result")
        context = {
            "organization_name": doc["organization"],
            "mission": answers["mission"],
            "confirmed_present_board": answers["current_board"],
            "organization_success_areas": answers["important_areas"],
            "current_board_support_needs": answers["support_needs"],
            "new_members_count": doc.get("desired_count") if doc.get("desired_count") else "Not sure",
        }
        instructions = (
            "Use this concise four-question assessment as the complete verified context. Produce practical, "
            "organization-specific board profiles. If an exact new_members_count is supplied, return exactly that many "
            "priority_roles. Treat confirmed_present_board as the authoritative description of the present board. "
            "Keep the customer-facing recommendation concise: each priority role needs a clear role_name and only one or two "
            "sentences across why_this_person_is_important/how_this_person_can_support explaining how that board member will help "
            "this specific organization. Do not pad the result with generic explanations."
        )
        try:
            generated = await generate_structured(
                "powerhouse_board_blueprint",
                json.dumps(context, indent=2),
                instructions,
            )
        except Exception as exc:
            await collection.update_one(
                {"token": token},
                {"$set": {"generation_error": str(exc)[:500], "updated_at": now_iso()}},
            )
            raise HTTPException(status_code=503, detail="We could not prepare your result yet. Please try again.") from exc
        if not isinstance(generated.get("priority_roles"), list) or not generated["priority_roles"]:
            raise HTTPException(status_code=503, detail="We could not prepare your result yet. Please try again.")
        timestamp = now_iso()
        await collection.update_one(
            {"token": token},
            {"$set": {"result": generated, "state.result_generated": True,
                      "result_generated_at": timestamp, "updated_at": timestamp},
             "$unset": {"generation_error": ""}},
        )
        doc["result"] = generated
        await sync_funnel_lead(db, doc)
        await attach_free_assessment_to_member(db, doc["lead_id"], member)
        return {"result": generated}

    @router.post("/{token}/event")
    async def event(token: str, payload: RecruitFreeEvent):
        if payload.event not in EVENTS:
            raise HTTPException(status_code=422, detail="Unknown assessment event")
        collection, doc = await find_assessment(db, {"token": token})
        if not doc:
            raise HTTPException(status_code=404, detail="Assessment not found")
        await collection.update_one(
            {"token": token},
            {"$set": {f"state.{payload.event}": True, f"events.{payload.event}": now_iso(), "updated_at": now_iso()}},
        )
        return {"status": "recorded"}

    @router.post("/member-event/{event_name}")
    async def member_event(event_name: str, request: Request):
        if event_name not in EVENTS:
            raise HTTPException(status_code=422, detail="Unknown assessment event")
        member = await authenticate_member(request, db)
        query = {"lead_id": {"$in": member.get("lead_ids", [])}} if member.get("lead_ids") else {"email": member["email"]}
        collection, doc = await find_assessment(db, query)
        if not doc:
            return {"status": "not_found"}
        await collection.update_one(
            {"token": doc["token"]},
            {"$set": {f"state.{event_name}": True, f"events.{event_name}": now_iso(), "updated_at": now_iso()}},
        )
        return {"status": "recorded"}

    return router
