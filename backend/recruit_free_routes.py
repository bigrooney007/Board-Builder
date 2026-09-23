"""Board Recruitment entry capture and the six-question paid dashboard intelligence handoff."""
import asyncio
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
QUESTION_KEYS = {
    1: "mission",
    2: "current_board",
    3: "desired_board_members",
    4: "support_needs",
    5: "board_type",
    6: "why_join",
}
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
    question: int = Field(ge=1, le=6)
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
        "desired_board_members": answers.get("desired_board_members", ""),
        "strengthen_areas": answers.get("support_needs", ""),
        "accomplish": answers.get("support_needs", ""),
        "board_type": answers.get("board_type", ""),
        "why_join": answers.get("why_join", ""),
        "new_members_needed": str(doc.get("desired_count") or "Not sure"),
    }


async def sync_funnel_lead(db, doc: dict) -> None:
    existing = await db.funnel_leads.find_one({"lead_id": doc["lead_id"]}, {"_id": 0}) or {}
    await db.funnel_leads.update_one(
        {"lead_id": doc["lead_id"]},
        {"$set": {
            "result_token": doc["token"],
            "offer_source": "recruitment",
            "lead_source": "recruitment_free_assessment",
            "name": doc["name"],
            "email": doc["email"],
            "organization": doc["organization"],
            "phone": existing.get("phone", ""),
            "website": existing.get("website", ""),
            "city": existing.get("city", ""),
            "state_region": existing.get("state_region", ""),
            "country": existing.get("country", ""),
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
    if result:
        from workspace_service import save_generation
        existing_material = await db.generated_materials.find_one(
            {"user_id": member["user_id"], "type": "powerhouse_board_blueprint", "application_id": ""},
            {"_id": 0, "versions": 1, "current_version": 1},
        )
        current_structured = None
        if existing_material:
            current_structured = next(
                (version.get("structured") for version in existing_material.get("versions", [])
                 if version.get("version") == existing_material.get("current_version")),
                None,
            )
        if json.dumps(current_structured, sort_keys=True, default=str) != json.dumps(result, sort_keys=True, default=str):
            await save_generation(
                db,
                member["user_id"],
                "powerhouse_board_blueprint",
                result,
                "Six-question Board Recruitment assessment",
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
        "desired_board_members_founder_view": answers.get("desired_board_members", ""),
        "board_kind": answers.get("board_type", ""),
        "why_join_board": answers.get("why_join", ""),
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
            "desired_count": normalize_count(str((lead.get("answers") or {}).get("new_members_needed") or "not_sure")),
            "answers": {}, "state": {"paid": True, "result_generated": False, "generation_status": "not_started"},
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
                "question_5_completed": False,
                "question_6_completed": False,
                "result_generated": False,
                "generation_status": "not_started",
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

    async def generate_result_for_doc(collection, doc: dict, member: dict) -> dict:
        if doc.get("result"):
            await attach_free_assessment_to_member(db, doc["lead_id"], member)
            return doc["result"]
        answers = doc.get("answers") or {}
        missing = [key for key in QUESTION_KEYS.values() if not str(answers.get(key) or "").strip()]
        if missing:
            raise HTTPException(status_code=409, detail="Answer all six recruitment questions before generating your result")

        exact_count = doc.get("desired_count")
        context = {
            "organization_name": doc["organization"],
            "mission": answers["mission"],
            "confirmed_present_board": answers["current_board"],
            "founder_view_of_board_members_needed": answers["desired_board_members"],
            "areas_needing_board_support": answers["support_needs"],
            "desired_board_model": answers["board_type"],
            "why_someone_should_join_this_board": answers["why_join"],
            "new_members_count": exact_count if exact_count else "Not sure",
        }
        instructions = (
            "Act as a nonprofit board-building strategist. Use every supplied answer together rather than treating each answer independently. "
            "Begin with the mission and desired board model, then assess what the present board already contributes, what the founder believes is missing, "
            "the areas where the organization needs support, and the value proposition for joining. Recommend a balanced team, not a list of generic job titles. "
            "Professional or fiduciary capability can matter, including fundraising, partnerships, marketing, finance/accounting, legal, technology, operations, "
            "community credibility, lived experience or other expertise when the organization's actual context supports it. Do not duplicate capability already "
            "covered by the present board unless the supplied information shows additional capacity is genuinely required. "
            + (f"Return EXACTLY {exact_count} priority_roles because the founder said they want to recruit {exact_count} new board members. " if exact_count else
               "Return the smallest practical set of priority_roles needed to strengthen this board. ")
            + "Each priority role must have a clear role_name. Keep customer-facing rationale concise: one or two sentences total across "
              "why_this_person_is_important and how_this_person_can_support. The recommendations must be specific to this organization."
        )

        await collection.update_one(
            {"token": doc["token"]},
            {"$set": {"state.generation_status": "generating", "updated_at": now_iso()},
             "$unset": {"generation_error": ""}},
        )
        try:
            generated = await generate_structured(
                "powerhouse_board_blueprint",
                json.dumps(context, indent=2),
                instructions,
            )
            roles = generated.get("priority_roles") if isinstance(generated, dict) else None
            if not isinstance(roles, list) or not roles:
                raise RuntimeError("No priority board roles were returned")
            if exact_count and len(roles) != int(exact_count):
                correction = (
                    f"The previous result returned {len(roles)} priority roles. The founder explicitly requested {exact_count} new board members. "
                    f"Return exactly {exact_count} distinct priority_roles. Preserve the strongest organization-specific reasoning and create a balanced team."
                )
                generated = await generate_structured(
                    "powerhouse_board_blueprint",
                    json.dumps(context, indent=2),
                    instructions + "\n\nCORRECTION REQUIRED: " + correction,
                )
                roles = generated.get("priority_roles") if isinstance(generated, dict) else None
                if not isinstance(roles, list) or len(roles) < int(exact_count):
                    raise RuntimeError(f"Could not produce the requested {exact_count} board profiles")
                if len(roles) > int(exact_count):
                    generated["priority_roles"] = roles[:int(exact_count)]

            timestamp = now_iso()
            await collection.update_one(
                {"token": doc["token"]},
                {"$set": {"result": generated, "state.result_generated": True,
                          "state.generation_status": "ready", "result_generated_at": timestamp,
                          "updated_at": timestamp},
                 "$unset": {"generation_error": ""}},
            )
            doc["result"] = generated
            await sync_funnel_lead(db, doc)
            await attach_free_assessment_to_member(db, doc["lead_id"], member)
            return generated
        except HTTPException:
            raise
        except Exception as exc:
            await collection.update_one(
                {"token": doc["token"]},
                {"$set": {"state.generation_status": "failed", "generation_error": str(exc)[:500],
                          "updated_at": now_iso()}},
            )
            raise HTTPException(status_code=503, detail="We could not prepare your board recommendations yet. Please try again.") from exc

    async def background_generate_result(token: str, user_id: str) -> None:
        try:
            collection, fresh = await find_assessment(db, {"token": token})
            if not fresh or fresh.get("result"):
                return
            member = await db.members.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0}) or {}
            if not member:
                return
            await generate_result_for_doc(collection, fresh, member)
        except Exception:
            # The dashboard exposes generation_status and allows a deliberate retry.
            return

    @router.put("/{token}/answer")
    async def answer(token: str, payload: RecruitFreeAnswer, request: Request):
        collection, doc = await find_assessment(db, {"token": token})
        if not doc:
            raise HTTPException(status_code=404, detail="Assessment not found")
        member = await authenticate_member(request, db)
        if doc.get("member_user_id") != member.get("user_id") or not doc.get("state", {}).get("paid"):
            raise HTTPException(status_code=403, detail="Complete your Board Recruitment purchase before answering these questions")
        key = QUESTION_KEYS[payload.question]
        text_value = payload.text.strip()
        if str((doc.get("answers") or {}).get(key) or "").strip() == text_value:
            return {"status": "saved", "question": payload.question, "generation_queued": False}

        opportunity = await db.opportunities.find_one(
            {"user_id": member["user_id"]}, {"_id": 0, "status": 1})
        if opportunity and opportunity.get("status") in {"Published", "Closed"}:
            raise HTTPException(
                status_code=409,
                detail="Your Recruitment campaign has already been launched. The six foundational Recruitment Questions are locked so the live campaign, applicant records and approved Board profiles stay consistent.",
            )

        timestamp = now_iso()
        await db.generated_materials.update_many(
            {"user_id": member["user_id"], "type": {"$in": [
                "powerhouse_board_blueprint", "board_recruitment_job_post",
                "recruitment_emails", "social_posts", "referral_request_email",
            ]}},
            {"$set": {"status": "Needs Review", "updated_at": timestamp}},
        )
        await db.recruitment_preparation.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"status": "stale", "stage": "six_questions_changed", "updated_at": timestamp}},
            upsert=True,
        )
        await collection.update_one(
            {"token": token},
            {"$set": {f"answers.{key}": text_value, f"state.question_{payload.question}_completed": True,
                      "state.generation_status": "not_started", "result": None,
                      "state.result_generated": False, "updated_at": timestamp}},
        )
        doc.setdefault("answers", {})[key] = text_value
        doc["result"] = None
        await sync_funnel_lead(db, doc)

        complete = all(str(doc["answers"].get(answer_key) or "").strip() for answer_key in QUESTION_KEYS.values())
        if complete:
            await collection.update_one(
                {"token": token},
                {"$set": {"state.generation_status": "queued", "updated_at": now_iso()}},
            )
            asyncio.create_task(background_generate_result(token, member["user_id"]))
        return {"status": "saved", "question": payload.question, "generation_queued": complete}

    @router.post("/{token}/result")
    async def result(token: str, request: Request):
        collection, doc = await find_assessment(db, {"token": token})
        if not doc:
            raise HTTPException(status_code=404, detail="Assessment not found")
        member = await authenticate_member(request, db)
        if doc.get("member_user_id") != member.get("user_id") or not doc.get("state", {}).get("paid"):
            raise HTTPException(status_code=403, detail="Complete your Board Recruitment purchase before generating your result")
        return {"result": await generate_result_for_doc(collection, doc, member)}

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
