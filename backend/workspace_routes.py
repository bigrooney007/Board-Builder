"""Phase 3 member workspace routes — $497 Self-Guided Recruitment execution platform.
All endpoints require member auth + recruitment_self_guided entitlement. Tenant isolation enforced by user_id scoping.
"""
import io
import os
import secrets
from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from pydantic import BaseModel, Field

from ai_service import GENERATION_TYPES, extract_cv_text, generate_structured
from member_auth import authenticate_member, require_entitlement
from opportunity_emails import send_opportunity_broadcast, send_signature_request
from workspace_service import (
    APPLICATION_STATUSES, BACKGROUND_STATUSES, CORE_QUESTIONS, REFERENCE_OUTCOMES,
    application_context_text, build_org_context, get_current_material, get_lead, get_profile,
    new_id, now_iso, reference_context, run_interview_guide, save_generation, slugify,
)


class ProfileUpdate(BaseModel):
    data: dict


class GenerateRequest(BaseModel):
    type: str
    application_id: Optional[str] = ""
    instructions: Optional[str] = ""


class MaterialEdit(BaseModel):
    display_text: str = Field(min_length=1)


class SetCurrent(BaseModel):
    version: int


class CustomQuestion(BaseModel):
    id: Optional[str] = ""
    label: str = Field(min_length=1)
    type: str = "textarea"


class ApplicationFormUpdate(BaseModel):
    custom_questions: List[CustomQuestion]


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    background_check: Optional[dict] = None
    interview_completed: Optional[bool] = None
    candidate_email: Optional[str] = None
    board_role: Optional[str] = None


class ReferenceRecord(BaseModel):
    reference_name: str = Field(min_length=1)
    relationship: str = ""
    email: str = ""
    phone: str = ""
    date_contacted: str = ""
    notes: str = ""
    outcome: str = "Not completed"


class SignaturePrepare(BaseModel):
    agreement_type: str
    application_id: str = Field(min_length=1)


def create_workspace_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/workspace")
    cv_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="opportunity_cvs")

    async def current_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {"recruitment_self_guided"})
        return member

    async def owned_application(user_id: str, application_id: str) -> dict:
        application = await db.opportunity_applications.find_one(
            {"application_id": application_id, "owner_user_id": user_id}, {"_id": 0})
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        return application

    # ---------- Module 1: Recruitment Profile ----------
    @router.get("/profile")
    async def read_profile(request: Request):
        member = await current_member(request)
        profile = await get_profile(db, member["user_id"])
        lead = await get_lead(db, member)
        prefill = {}
        if lead:
            answers = lead.get("answers", {})
            prefill = {
                "organization_name": lead.get("organization", ""), "website": lead.get("website", ""),
                "city": lead.get("city", ""), "state_region": lead.get("state_region", ""),
                "country": lead.get("country", ""), "present_board": answers.get("present_board", ""),
                "active_board": answers.get("active_board", ""), "new_members_count": answers.get("new_members_needed", ""),
                "board_kind": answers.get("board_type", ""), "strengthen_areas": answers.get("strengthen_areas", []),
                "priorities": answers.get("accomplish", ""),
            }
        return {"profile": profile.get("data", {}), "confirmed": profile.get("confirmed", False),
                "confirmed_at": profile.get("confirmed_at", ""), "prefill": prefill,
                "strategy_intake": profile.get("strategy_intake", {})}

    @router.put("/profile")
    async def save_profile(payload: ProfileUpdate, request: Request):
        member = await current_member(request)
        ts = now_iso()
        existing = await get_profile(db, member["user_id"])
        data = {**existing.get("data", {}), **payload.data}
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"data": data, "updated_at": ts, "confirmed": False},
             "$setOnInsert": {"created_at": ts}}, upsert=True)
        return {"status": "saved", "confirmed": False}

    @router.put("/strategy-intake")
    async def save_strategy_intake(payload: ProfileUpdate, request: Request):
        member = await current_member(request)
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"strategy_intake": payload.data, "updated_at": now_iso()}}, upsert=True)
        return {"status": "saved"}

    @router.post("/profile/confirm")
    async def confirm_profile(request: Request):
        member = await current_member(request)
        profile = await get_profile(db, member["user_id"])
        if not profile.get("data"):
            raise HTTPException(status_code=400, detail="Complete your Recruitment Profile before confirming")
        ts = now_iso()
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"confirmed": True, "recruitment_profile_confirmed": True, "confirmed_at": ts, "updated_at": ts}})
        return {"status": "confirmed", "confirmed_at": ts}

    MODULE3_LINK_TYPES = {"board_opportunity", "linkedin_post", "social_posts", "recruitment_emails", "board_recruitment_job_post",
                          "personal_invitation_email", "personal_invitation_message", "referral_request_email", "referral_request_message",
                          "linkedin_launch_instructions"}
    ONBOARDING_DOC_TYPES = ["organization_overview", "board_manual", "board_member_agreement", "confidentiality_agreement", "conflict_of_interest_agreement"]

    def origin_of(request: Request) -> str:
        return os.environ.get("PUBLIC_ORIGIN") or request.headers.get("origin") or "https://nonprofitboardbuilder.com"

    def replace_link(value, url):
        if isinstance(value, str):
            return value.replace("[APPLICATION LINK]", url)
        if isinstance(value, list):
            return [replace_link(item, url) for item in value]
        if isinstance(value, dict):
            return {k: replace_link(v, url) for k, v in value.items()}
        return value

    async def ensure_share_token(user_id: str, material_type: str) -> str:
        material = await db.generated_materials.find_one({"user_id": user_id, "type": material_type, "application_id": ""}, {"_id": 0, "material_id": 1})
        if not material:
            return ""
        existing = await db.share_links.find_one({"material_id": material["material_id"]}, {"_id": 0})
        if existing:
            return existing["share_token"]
        token = secrets.token_urlsafe(24)
        await db.share_links.insert_one({"share_token": token, "material_id": material["material_id"], "user_id": user_id, "created_at": now_iso()})
        return token

    # ---------- Generation (deliberate button clicks only) ----------
    @router.post("/generate")
    async def generate(payload: GenerateRequest, request: Request):
        member = await current_member(request)
        user_id = member["user_id"]
        if payload.type not in GENERATION_TYPES:
            raise HTTPException(status_code=422, detail="Unknown generation type")
        meta = GENERATION_TYPES[payload.type]
        profile = await get_profile(db, user_id)
        if not profile.get("confirmed"):
            raise HTTPException(status_code=409, detail="Complete Module 1 before generating materials")
        lead_doc = await get_lead(db, member)
        org_name_check = (lead_doc or {}).get("organization", "") or profile.get("data", {}).get("organization_name", "")
        mission_check = profile.get("data", {}).get("mission", "")
        if not org_name_check or not mission_check:
            raise HTTPException(status_code=422, detail="Add your organization name and mission statement in Module 1 first. They are required so every recruitment material is finished and organization-specific.")
        context = await build_org_context(db, user_id, member)
        reference = await reference_context(db, payload.type)
        if reference:
            context = f"{context}\n\n{reference}"
        origin = origin_of(request)
        opportunity = await ensure_opportunity(user_id, member)
        apply_url = f"{origin}/board-opportunities/{opportunity['slug']}/apply"
        if payload.type in MODULE3_LINK_TYPES:
            context += f"\n\nBOARD APPLICATION URL (insert this exact URL wherever the application link belongs): {apply_url}"
        application_id = ""
        application = None
        if meta.get("per_application"):
            if not payload.application_id:
                raise HTTPException(status_code=422, detail="This material is generated for a specific applicant")
            application = await owned_application(user_id, payload.application_id)
            application_id = application["application_id"]
            if payload.type == "board_member_portfolio":
                context += "\n\n" + application_context_text({**application, "notes": "", "references": []})
                profile_response = await db.board_profile_responses.find_one(
                    {"user_id": user_id, "data.email": application.get("applicant_email", "")}, {"_id": 0, "data": 1})
                if profile_response:
                    import json as _json
                    context += "\n\nBOARD MEMBER PROFILE FORM RESPONSE:\n" + _json.dumps(profile_response["data"], indent=1)
                if application.get("board_role"):
                    context += f"\n\nBOARD ROLE THEY WERE RECRUITED FOR: {application['board_role']}"
                context += "\n\nPRIVACY: never include referee responses, internal interview notes or internal evaluation material."
            else:
                context += "\n\n" + application_context_text(application)
        if payload.type == "conditional_offer":
            missing = []
            for doc_type in ONBOARDING_DOC_TYPES:
                doc = await db.generated_materials.find_one({"user_id": user_id, "type": doc_type, "application_id": ""}, {"_id": 0, "status": 1})
                if not doc or doc.get("status") != "Approved":
                    missing.append(GENERATION_TYPES[doc_type]["title"])
            profile_form = await db.board_profile_forms.find_one({"user_id": user_id}, {"_id": 0, "share_token": 1})
            if not profile_form:
                missing.append("Board Member Profile Form")
            if missing:
                raise HTTPException(status_code=409, detail="Complete the following onboarding materials before preparing this candidate's Conditional Appointment: " + ", ".join(missing))
            links = []
            overview_token = await ensure_share_token(user_id, "organization_overview")
            manual_token = await ensure_share_token(user_id, "board_manual")
            if overview_token:
                links.append(f"Organization Overview (View): {origin}/shared/{overview_token}")
            if manual_token:
                links.append(f"Board Manual (View): {origin}/shared/{manual_token}")
            # candidate-specific signature links (idempotent per agreement + candidate)
            for agreement_type in ["board_member_agreement", "confidentiality_agreement", "conflict_of_interest_agreement"]:
                existing_request = await db.signature_requests.find_one(
                    {"owner_user_id": user_id, "application_id": application_id, "agreement_type": agreement_type, "status": {"$ne": "Void"}},
                    {"_id": 0, "token": 1, "status": 1})
                if existing_request and existing_request.get("status") == "Signed":
                    continue
                if not existing_request:
                    agreement_material = await get_current_material(db, user_id, agreement_type, "")
                    token = secrets.token_urlsafe(24)
                    await db.signature_requests.insert_one({
                        "request_id": new_id(), "token": token, "owner_user_id": user_id,
                        "application_id": application_id, "agreement_type": agreement_type,
                        "agreement_title": GENERATION_TYPES[agreement_type]["title"],
                        "material_id": agreement_material["material"]["material_id"],
                        "agreement_version": agreement_material["current"]["version"],
                        "document_snapshot": agreement_material["current"]["display_text"],
                        "organization_name": (await db.opportunities.find_one({"user_id": user_id}, {"_id": 0, "organization_name": 1}) or {}).get("organization_name", ""),
                        "board_member_name": application.get("profile_snapshot", {}).get("full_name", ""),
                        "board_member_email": application.get("applicant_email", ""),
                        "status": "Ready for Signature", "created_at": now_iso(), "updated_at": now_iso(),
                    })
                    existing_request = {"token": token}
                links.append(f"{GENERATION_TYPES[agreement_type]['title']} (Review and Sign): {origin}/sign/{existing_request['token']}")
            # candidate-specific profile form link (idempotent)
            profile_link = await db.board_profile_links.find_one({"user_id": user_id, "application_id": application_id}, {"_id": 0, "token": 1})
            if not profile_link:
                profile_link = {"token": secrets.token_urlsafe(24)}
                snapshot = application.get("profile_snapshot", {})
                await db.board_profile_links.insert_one({
                    "token": profile_link["token"], "user_id": user_id, "application_id": application_id,
                    "prefill": {"full_name": snapshot.get("full_name", ""), "email": application.get("applicant_email", ""),
                                "professional_title": snapshot.get("profession", ""), "employer": snapshot.get("employer", ""),
                                "linkedin": snapshot.get("linkedin", ""), "location": f"{snapshot.get('city', '')} {snapshot.get('state_region', '')}".strip()},
                    "status": "Created", "created_at": now_iso(),
                })
            links.append(f"Board Member Profile Form (Complete Your Profile): {origin}/board-profile/{profile_link['token']}")
            process = await db.reference_processes.find_one({"owner_user_id": user_id, "application_id": application_id}, {"_id": 0, "candidate_token": 1, "status": 1})
            if process and process.get("status") not in {"Completed", "References Submitted", "In Progress"}:
                links.append(f"Reference Information Form (Provide Your References): {origin}/reference-form/{process['candidate_token']}")
            background = (application.get("background_check") or {}).get("status", "")
            context += f"\n\nBACKGROUND CHECK STATUS FOR THIS CANDIDATE: {background or 'Not recorded'} — never state a background check is required if it is marked Not Required."
            if process:
                context += f"\nREFERENCE CHECK STATUS: {process.get('status')} — never ask for references again if they are already submitted or completed."
            session = profile.get("onboarding_session") or {}
            if session:
                context += "\n\nBOARD ONBOARDING SESSION (invite the candidate to this session using these exact details):\n" + "\n".join(f"{k}: {v}" for k, v in session.items() if v)
            if links:
                context += ("\n\nLINKS TO INCLUDE IN THE EMAIL under a clear 'Before the Onboarding Session' section (use these exact URLs on their own lines; already-signed agreements are intentionally omitted — do not ask for them again):\n" + "\n".join(links))
        try:
            structured = await generate_structured(payload.type, context, payload.instructions or "")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Generation failed: {str(exc)[:300]}. Your information is preserved — you can try again.") from exc
        structured = replace_link(structured, apply_url)
        material = await save_generation(db, user_id, payload.type, structured, context[:1500], application_id)
        return material

    @router.post("/materials/{material_id}/approve")
    async def approve_material(material_id: str, request: Request):
        member = await current_member(request)
        result = await db.generated_materials.update_one(
            {"material_id": material_id, "user_id": member["user_id"]},
            {"$set": {"status": "Approved", "approved_at": now_iso(), "updated_at": now_iso()}})
        if not result.matched_count:
            raise HTTPException(status_code=404, detail="Material not found")
        return {"status": "Approved"}

    # ---------- External applicants, share links, board member profile form ----------
    @router.post("/applications/external", status_code=201)
    async def add_external_applicant(request: Request, name: str = Form(...), cv: UploadFile = File(None), email: str = Form(""), phone: str = Form(""), linkedin: str = Form(""), notes: str = Form("")):
        member = await current_member(request)
        ts = now_iso()
        cv_file_id, cv_filename, cv_text = "", "", ""
        if cv is not None and cv.filename:
            content = await cv.read()
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="CV file is too large (10MB maximum)")
            file_id = await cv_bucket.upload_from_stream(cv.filename, content)
            cv_file_id, cv_filename = str(file_id), cv.filename
            cv_text = extract_cv_text(content, cv.filename)
        application = {
            "application_id": new_id(), "owner_user_id": member["user_id"], "opportunity_id": "",
            "applicant_email": email.strip().lower(), "source": "LinkedIn / External", "status": "New",
            "profile_snapshot": {"full_name": name.strip(), "email": email.strip().lower(), "phone": phone.strip(), "linkedin": linkedin.strip(), "profession": "", "city": "", "state_region": ""},
            "answers": {}, "notes": notes.strip(), "cv_file_id": cv_file_id, "cv_filename": cv_filename, "cv_text": cv_text,
            "interview_guide": {"status": "Pending"}, "references": [], "background_check": {"status": "Not started"},
            "created_at": ts, "updated_at": ts,
        }
        await db.opportunity_applications.insert_one(application.copy())
        return {"application_id": application["application_id"], "status": "New"}

    @router.post("/materials/{material_id}/share", status_code=201)
    async def share_material(material_id: str, request: Request):
        member = await current_member(request)
        material = await db.generated_materials.find_one({"material_id": material_id, "user_id": member["user_id"]}, {"_id": 0, "material_id": 1, "type": 1})
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        if GENERATION_TYPES.get(material["type"], {}).get("agreement"):
            raise HTTPException(status_code=422, detail="Agreements are shared through the secure signature workflow, not a public share link")
        existing = await db.share_links.find_one({"material_id": material_id}, {"_id": 0})
        if existing:
            return {"share_token": existing["share_token"]}
        token = secrets.token_urlsafe(24)
        await db.share_links.insert_one({"share_token": token, "material_id": material_id, "user_id": member["user_id"], "created_at": now_iso()})
        return {"share_token": token}

    @router.get("/board-profile-form")
    async def board_profile_form(request: Request):
        member = await current_member(request)
        record = await db.board_profile_forms.find_one({"user_id": member["user_id"]}, {"_id": 0})
        if not record:
            profile = await get_profile(db, member["user_id"])
            org = (profile.get("data", {}) or {}).get("organization_name", "") or "Your organization"
            record = {"share_token": secrets.token_urlsafe(24), "user_id": member["user_id"], "organization_name": org, "created_at": now_iso()}
            await db.board_profile_forms.insert_one(record.copy())
        responses = await db.board_profile_responses.find({"user_id": member["user_id"]}, {"_id": 0}).sort("submitted_at", -1).to_list(100)
        return {"share_token": record["share_token"], "organization_name": record["organization_name"], "responses": responses}

    # ---------- Materials library ----------
    @router.get("/materials")
    async def list_materials(request: Request, application_id: str = ""):
        member = await current_member(request)
        query = {"user_id": member["user_id"]}
        if application_id:
            query["application_id"] = application_id
        materials = await db.generated_materials.find(query, {"_id": 0, "versions.structured": 0}).sort("updated_at", -1).to_list(300)
        return {"materials": materials}

    @router.get("/materials/{material_id}")
    async def get_material(material_id: str, request: Request):
        member = await current_member(request)
        material = await db.generated_materials.find_one({"material_id": material_id, "user_id": member["user_id"]}, {"_id": 0})
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        return material

    @router.put("/materials/{material_id}")
    async def edit_material(material_id: str, payload: MaterialEdit, request: Request):
        member = await current_member(request)
        material = await db.generated_materials.find_one({"material_id": material_id, "user_id": member["user_id"]}, {"_id": 0})
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        ts = now_iso()
        version_number = max(v["version"] for v in material["versions"]) + 1
        version = {"version": version_number, "structured": None, "display_text": payload.display_text,
                   "source": "edited", "input_context_summary": "Manual edit", "created_at": ts}
        await db.generated_materials.update_one(
            {"material_id": material_id},
            {"$push": {"versions": version}, "$set": {"current_version": version_number, "updated_at": ts, "status": "Edited"}})
        return await db.generated_materials.find_one({"material_id": material_id}, {"_id": 0})

    @router.post("/materials/{material_id}/current")
    async def set_current(material_id: str, payload: SetCurrent, request: Request):
        member = await current_member(request)
        material = await db.generated_materials.find_one({"material_id": material_id, "user_id": member["user_id"]}, {"_id": 0})
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        if payload.version not in {v["version"] for v in material["versions"]}:
            raise HTTPException(status_code=422, detail="Unknown version")
        await db.generated_materials.update_one({"material_id": material_id}, {"$set": {"current_version": payload.version, "updated_at": now_iso()}})
        return {"status": "ok", "current_version": payload.version}

    # ---------- Opportunity ----------
    async def ensure_opportunity(user_id: str, member: dict) -> dict:
        opportunity = await db.opportunities.find_one({"user_id": user_id}, {"_id": 0})
        if opportunity:
            return opportunity
        lead = await get_lead(db, member)
        profile = await get_profile(db, user_id)
        org_name = (profile.get("data", {}) or {}).get("organization_name") or (lead or {}).get("organization", "Nonprofit")
        ts = now_iso()
        opportunity = {
            "opportunity_id": new_id(), "user_id": user_id, "slug": slugify(org_name),
            "organization_name": org_name, "status": "Draft", "custom_questions": [],
            "email_content": {}, "broadcast_initiated": False, "broadcast_id": "",
            "created_at": ts, "updated_at": ts,
        }
        await db.opportunities.insert_one(opportunity.copy())
        return opportunity

    def opportunity_readiness(strategy, board_opportunity, opportunity):
        return {
            "strategy_approved": bool(strategy and strategy["current"]),
            "opportunity_saved": bool(board_opportunity and board_opportunity["current"] and board_opportunity["material"].get("status") == "Approved"),
            "application_saved": bool(opportunity.get("application_saved")),
        }

    @router.get("/opportunity")
    async def read_opportunity(request: Request):
        member = await current_member(request)
        opportunity = await ensure_opportunity(member["user_id"], member)
        if not opportunity.get("application_saved"):
            await db.opportunities.update_one(
                {"user_id": member["user_id"]},
                {"$set": {"custom_questions": [], "application_saved": True, "updated_at": now_iso()}})
            opportunity = await db.opportunities.find_one({"user_id": member["user_id"]}, {"_id": 0})
        strategy = await get_current_material(db, member["user_id"], "recruitment_strategy")
        board_opportunity = await get_current_material(db, member["user_id"], "board_opportunity")
        readiness = opportunity_readiness(strategy, board_opportunity, opportunity)
        applications = await db.opportunity_applications.count_documents({"owner_user_id": member["user_id"]})
        return {"opportunity": opportunity, "core_questions": CORE_QUESTIONS, "readiness": readiness,
                "applications_count": applications}

    @router.put("/opportunity/application")
    async def save_application_form(payload: ApplicationFormUpdate, request: Request):
        member = await current_member(request)
        await ensure_opportunity(member["user_id"], member)
        questions = [{"id": q.id or new_id(), "label": q.label, "type": q.type if q.type in {"text", "textarea", "yes_no"} else "textarea"} for q in payload.custom_questions[:10]]
        await db.opportunities.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"custom_questions": questions, "application_saved": True, "updated_at": now_iso()}})
        return {"status": "saved", "custom_questions": questions}

    @router.post("/opportunity/application/generate")
    async def generate_standard_application(request: Request):
        """Creates and automatically saves the standard Board Application. No AI call, no emails sent."""
        member = await current_member(request)
        await ensure_opportunity(member["user_id"], member)
        await db.opportunities.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"custom_questions": [], "application_saved": True, "updated_at": now_iso()}})
        opportunity = await db.opportunities.find_one({"user_id": member["user_id"]}, {"_id": 0})
        return {"status": "generated", "opportunity": opportunity, "core_questions": CORE_QUESTIONS}

    @router.post("/opportunity/publish")
    async def publish_opportunity(request: Request):
        member = await current_member(request)
        user_id = member["user_id"]
        opportunity = await ensure_opportunity(user_id, member)
        if opportunity["status"] == "Published":
            raise HTTPException(status_code=409, detail="This recruitment campaign is already published")
        strategy = await get_current_material(db, user_id, "recruitment_strategy")
        board_opportunity = await get_current_material(db, user_id, "board_opportunity")
        readiness = opportunity_readiness(strategy, board_opportunity, opportunity)
        if not all(readiness.values()):
            raise HTTPException(status_code=409, detail="Approve your Recruitment Strategy, save your Board Opportunity and save your Board Application before publishing")
        structured = board_opportunity["current"].get("structured") or {}
        profile = await get_profile(db, user_id)
        data = profile.get("data", {})
        email_content = {
            "mission": data.get("mission", structured.get("about_the_organization", "")),
            "candidate_needs": structured.get("who_we_are_looking_for", "") or ", ".join(data.get("strengthen_areas", [])),
            "commitment": structured.get("meeting_time_and_location", ""),
            "location": structured.get("meeting_time_and_location", ""),
            "deadline": structured.get("application_deadline", ""),
        }
        ts = now_iso()
        # atomic guard against duplicate broadcasts
        result = await db.opportunities.update_one(
            {"user_id": user_id, "broadcast_initiated": {"$ne": True}},
            {"$set": {"status": "Published", "published_at": ts, "email_content": email_content,
                      "broadcast_initiated": True, "updated_at": ts}})
        if not result.modified_count:
            raise HTTPException(status_code=409, detail="The network announcement was already initiated for this campaign")
        opportunity = await db.opportunities.find_one({"user_id": user_id}, {"_id": 0})
        origin = os.environ.get("PUBLIC_ORIGIN") or request.headers.get("origin") or "https://nonprofitboardbuilder.com"
        broadcast_status = "Failed"
        try:
            outcome = await send_opportunity_broadcast(db, opportunity, opportunity["organization_name"], origin,
                                                       force_test=bool(member.get("review_mode")))
            await db.opportunities.update_one({"user_id": user_id}, {"$set": {
                "broadcast_id": outcome["broadcast_id"], "broadcast_mode": outcome["mode"],
                "broadcast_recipients": outcome["recipients"], "broadcast_status": "Initiated", "updated_at": now_iso()}})
            broadcast_status = "Initiated"
        except Exception as exc:
            await db.opportunities.update_one({"user_id": user_id}, {"$set": {"broadcast_status": "Failed", "broadcast_error": str(exc)[:400]}})
        opportunity = await db.opportunities.find_one({"user_id": user_id}, {"_id": 0})
        return {"status": "Published", "broadcast_status": broadcast_status, "opportunity": opportunity}

    @router.post("/opportunity/close")
    async def close_opportunity(request: Request):
        member = await current_member(request)
        result = await db.opportunities.update_one(
            {"user_id": member["user_id"], "status": "Published"},
            {"$set": {"status": "Closed", "closed_at": now_iso(), "updated_at": now_iso()}})
        if not result.modified_count:
            raise HTTPException(status_code=409, detail="No published campaign to close")
        return {"status": "Closed"}

    # ---------- Module 4: Applicant workspace ----------
    @router.get("/applications")
    async def list_applications(request: Request, status: str = ""):
        member = await current_member(request)
        query = {"owner_user_id": member["user_id"]}
        if status:
            query["status"] = status
        applications = await db.opportunity_applications.find(query, {"_id": 0, "cv_text": 0}).sort("created_at", -1).to_list(500)
        return {"applications": applications, "statuses": APPLICATION_STATUSES}

    @router.get("/applications/{application_id}")
    async def application_detail(application_id: str, request: Request):
        member = await current_member(request)
        application = await owned_application(member["user_id"], application_id)
        application.pop("cv_text", None)
        materials = await db.generated_materials.find(
            {"user_id": member["user_id"], "application_id": application_id}, {"_id": 0}).to_list(100)
        return {"application": application, "materials": materials,
                "reference_outcomes": REFERENCE_OUTCOMES, "background_statuses": BACKGROUND_STATUSES}

    @router.patch("/applications/{application_id}")
    async def update_application(application_id: str, payload: ApplicationUpdate, request: Request):
        member = await current_member(request)
        await owned_application(member["user_id"], application_id)
        updates = {"updated_at": now_iso()}
        if payload.status is not None:
            if payload.status not in APPLICATION_STATUSES:
                raise HTTPException(status_code=422, detail="Invalid applicant status")
            updates["status"] = payload.status
        if payload.notes is not None:
            updates["notes"] = payload.notes
        if payload.interview_completed is not None:
            updates["interview_completed"] = payload.interview_completed
            if payload.interview_completed:
                updates["interview_completed_at"] = now_iso()
        if payload.candidate_email is not None:
            updates["applicant_email"] = payload.candidate_email.strip().lower()
            updates["profile_snapshot.email"] = payload.candidate_email.strip().lower()
        if payload.board_role is not None:
            updates["board_role"] = payload.board_role
        if payload.background_check is not None:
            check = payload.background_check
            if check.get("status") and check["status"] not in BACKGROUND_STATUSES:
                raise HTTPException(status_code=422, detail="Invalid background check status")
            updates["background_check"] = {k: check.get(k, "") for k in ["required", "requested_date", "completed_date", "status", "notes"]}
        await db.opportunity_applications.update_one({"application_id": application_id}, {"$set": updates})
        return await db.opportunity_applications.find_one({"application_id": application_id}, {"_id": 0, "cv_text": 0})

    @router.post("/applications/{application_id}/references", status_code=201)
    async def add_reference(application_id: str, payload: ReferenceRecord, request: Request):
        member = await current_member(request)
        await owned_application(member["user_id"], application_id)
        if payload.outcome not in REFERENCE_OUTCOMES:
            raise HTTPException(status_code=422, detail="Invalid reference outcome")
        record = payload.model_dump()
        record.update({"reference_id": new_id(), "created_at": now_iso()})
        await db.opportunity_applications.update_one(
            {"application_id": application_id}, {"$push": {"references": record}, "$set": {"updated_at": now_iso()}})
        return record

    @router.get("/applications/{application_id}/cv")
    async def download_cv(application_id: str, request: Request):
        member = await current_member(request)
        application = await owned_application(member["user_id"], application_id)
        if not application.get("cv_file_id"):
            raise HTTPException(status_code=404, detail="No CV on this application")
        stream = await cv_bucket.open_download_stream(ObjectId(application["cv_file_id"]))
        content = await stream.read()
        return StreamingResponse(io.BytesIO(content), media_type=application.get("cv_content_type", "application/octet-stream"),
                                 headers={"Content-Disposition": f'attachment; filename="{application.get("cv_filename", "cv")}"'})

    @router.post("/applications/{application_id}/interview-guide/retry")
    async def retry_guide(application_id: str, request: Request):
        member = await current_member(request)
        await owned_application(member["user_id"], application_id)
        await run_interview_guide(db, application_id)
        application = await db.opportunity_applications.find_one({"application_id": application_id}, {"_id": 0, "cv_text": 0})
        return {"interview_guide": application.get("interview_guide", {})}

    # ---------- Module 6: Signatures ----------
    AGREEMENT_TYPES = {"board_member_agreement", "confidentiality_agreement", "conflict_of_interest_agreement"}

    @router.post("/signatures/prepare", status_code=201)
    async def prepare_signature(payload: SignaturePrepare, request: Request):
        member = await current_member(request)
        user_id = member["user_id"]
        if payload.agreement_type not in AGREEMENT_TYPES:
            raise HTTPException(status_code=422, detail="Unknown agreement type")
        application = await owned_application(user_id, payload.application_id)
        if application.get("status") != "Selected":
            raise HTTPException(status_code=409, detail="Agreements can only be prepared for Selected board members")
        material = await get_current_material(db, user_id, payload.agreement_type, payload.application_id)
        if not material or not material["current"]:
            material = await get_current_material(db, user_id, payload.agreement_type, "")
        if not material or not material["current"]:
            raise HTTPException(status_code=409, detail="Generate and save the agreement in Module 5 before preparing it for signature")
        ts = now_iso()
        snapshot = application.get("profile_snapshot", {})
        record = {
            "request_id": new_id(), "token": new_id() + new_id().replace("-", ""),
            "owner_user_id": user_id, "application_id": payload.application_id,
            "agreement_type": payload.agreement_type,
            "agreement_title": GENERATION_TYPES[payload.agreement_type]["title"],
            "material_id": material["material"]["material_id"],
            "agreement_version": material["current"]["version"],
            "document_snapshot": material["current"]["display_text"],
            "board_member_name": snapshot.get("full_name", ""),
            "board_member_email": snapshot.get("email", ""),
            "organization_name": (await ensure_opportunity(user_id, member))["organization_name"],
            "status": "Ready for Signature", "created_at": ts, "updated_at": ts,
        }
        await db.signature_requests.insert_one(record.copy())
        record.pop("token", None)
        return record

    @router.post("/signatures/{request_id}/send")
    async def send_signature(request_id: str, request: Request):
        member = await current_member(request)
        record = await db.signature_requests.find_one({"request_id": request_id, "owner_user_id": member["user_id"]}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Signature request not found")
        if record["status"] == "Signed":
            raise HTTPException(status_code=409, detail="This agreement has already been signed")
        origin = os.environ.get("PUBLIC_ORIGIN") or request.headers.get("origin") or "https://nonprofitboardbuilder.com"
        sign_url = f"{origin}/sign/{record['token']}"
        try:
            await send_signature_request(record["board_member_email"], record["board_member_name"],
                                         record["organization_name"], record["agreement_title"], sign_url)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"The signature email could not be sent: {str(exc)[:200]}") from exc
        await db.signature_requests.update_one({"request_id": request_id}, {"$set": {"status": "Sent", "sent_at": now_iso(), "updated_at": now_iso()}})
        return {"status": "Sent"}

    @router.get("/signatures")
    async def list_signatures(request: Request, application_id: str = ""):
        member = await current_member(request)
        query = {"owner_user_id": member["user_id"]}
        if application_id:
            query["application_id"] = application_id
        records = await db.signature_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
        return {"signatures": records}

    @router.get("/signatures/{request_id}/download")
    async def download_signed(request_id: str, request: Request):
        member = await current_member(request)
        record = await db.signature_requests.find_one({"request_id": request_id, "owner_user_id": member["user_id"]}, {"_id": 0, "token": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Signature request not found")
        signed = record.get("signed", {})
        text = record["document_snapshot"] + (
            f"\n\n---------------------------\nSIGNED ELECTRONICALLY\nName: {signed.get('typed_signature', '')}\nEmail: {signed.get('email', '')}\nDate: {signed.get('date', '')}\nSigned at: {signed.get('signed_at', '')}\nSignature request ID: {record['request_id']}"
            if signed else "\n\n(Not yet signed)")
        return StreamingResponse(io.BytesIO(text.encode("utf-8")), media_type="text/plain",
                                 headers={"Content-Disposition": f'attachment; filename="{record["agreement_type"]}-{record["request_id"][:8]}.txt"'})

    return router
