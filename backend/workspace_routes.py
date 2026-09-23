"""Phase 3 member workspace routes — $497 Self-Guided Recruitment execution platform.
All endpoints require member auth + recruitment_self_guided entitlement. Tenant isolation enforced by user_id scoping.
"""
import asyncio
import io
import os
import secrets
from datetime import datetime, timezone
from typing import List, Optional

import resend
from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from pydantic import BaseModel, Field

from ai_service import GENERATION_TYPES, extract_cv_text, generate_structured
from member_auth import authenticate_member, require_entitlement
from opportunity_emails import send_opportunity_broadcast, send_signature_request
from reactivation_routes import email_html as portfolio_email_html
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
    referee_id: Optional[str] = ""


class MaterialEdit(BaseModel):
    display_text: str = Field(min_length=1)


class BoardProfilesUpdate(BaseModel):
    priority_roles: List[dict] = Field(min_length=1)


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
    portfolio_role_approved: Optional[bool] = None
    portfolio_role_rationale: Optional[str] = None


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


class OnboardingLiveSectionUpdate(BaseModel):
    current_section_index: int = Field(ge=0)


def create_workspace_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/workspace")
    cv_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="opportunity_cvs")

    async def current_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {"recruitment_self_guided"})
        return member

    async def selection_member(request: Request) -> dict:
        member = await current_member(request)
        require_entitlement(member, {"recruitment_selection_onboarding"})
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
                "organization_name": lead.get("organization", ""), "mission": answers.get("mission", ""), "website": lead.get("website", ""),
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
        material = await db.generated_materials.find_one(
            {"user_id": user_id, "type": material_type, "application_id": "", "status": "Approved"}, {"_id": 0, "material_id": 1})
        if not material:
            return ""
        existing = await db.share_links.find_one({"material_id": material["material_id"]}, {"_id": 0})
        if existing:
            return existing["share_token"]
        token = secrets.token_urlsafe(24)
        await db.share_links.insert_one({"share_token": token, "material_id": material["material_id"], "user_id": user_id, "created_at": now_iso()})
        return token

    GOVERNANCE_BYLAWS_TYPES = {"formal_appointment_letter", "formal_appointment_email", "board_manual",
                               "board_member_agreement", "conflict_of_interest_agreement", "confidentiality_agreement", "onboarding_script"}
    MANUAL_REFERENCE_MATERIAL_TYPES = {"candidate_referee_request", "reference_request_email",
                                       "referee_confirmation_email", "reference_call_script", "reference_evaluation_form"}

    async def bylaws_context(user_id: str) -> str:
        intake = await db.board_reactivation_intakes.find_one(
            {"user_id": user_id}, {"_id": 0, "bylaws_text": 1}, sort=[("submitted_at", -1)])
        if not intake or not intake.get("bylaws_text"):
            return ""
        return ("\n\nORGANIZATION BYLAWS EXTRACT (verified governance context ONLY — use for factual governance information such as actual "
                "Board terminology, Board structure, officer roles, term of service, meeting/voting structure, appointment structure and "
                "conflict procedures where explicitly stated. Never invent legal conclusions, quorum rules, officer powers, removal procedures, "
                "voting thresholds, statutory requirements or term lengths. Where an intake assumption conflicts with the verified bylaws on a "
                "structural governance fact, prefer the verified governing document and avoid unsupported claims):\n"
                + intake["bylaws_text"][:10000])

    async def onboarding_conclusion_context(application: dict) -> str:
        conclusion = application.get("onboarding_conclusion") or {}
        if not conclusion.get("saved_at"):
            return ""
        safe = {key: conclusion.get(key, "") for key in [
            "board_role", "agreed_primary_contribution_area", "agreed_responsibility", "agreed_leadership",
            "how_their_experience_will_be_used", "organization_support_agreed", "immediate_next_steps"]}
        import json as _json
        return ("\n\nONBOARDING CONCLUSION / ROLE AGREEMENT (founder-recorded — AUTHORITATIVE for what was actually agreed during onboarding; "
                "never contradict or expand beyond it):\n" + _json.dumps(safe, indent=1, default=str))

    # ---------- Generation (deliberate button clicks only) ----------
    @router.post("/generate")
    async def generate(payload: GenerateRequest, request: Request):
        member = await current_member(request)
        user_id = member["user_id"]
        if payload.type in MANUAL_REFERENCE_MATERIAL_TYPES:
            raise HTTPException(status_code=410, detail="Manual reference materials have been replaced by the automated reference-check process.")
        if payload.type not in GENERATION_TYPES:
            raise HTTPException(status_code=422, detail="Unknown generation type")
        meta = GENERATION_TYPES[payload.type]
        if meta.get("module", 0) >= 4:
            require_entitlement(member, {"recruitment_selection_onboarding"})
        profile = await get_profile(db, user_id)
        if not profile.get("confirmed"):
            raise HTTPException(status_code=409, detail="Complete your Recruitment Profile before generating materials")
        lead_doc = await get_lead(db, member)
        org_name_check = (lead_doc or {}).get("organization", "") or profile.get("data", {}).get("organization_name", "")
        mission_check = profile.get("data", {}).get("mission", "")
        if not org_name_check or not mission_check:
            raise HTTPException(status_code=422, detail="Add your organization name and mission statement in your Recruitment Profile first. They are required so every recruitment material is finished and organization-specific.")
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
            if payload.type in {"formal_appointment_letter", "formal_appointment_email"}:
                if application.get("status") != "Selected" and application.get("final_outcome") != "Joined Board":
                    raise HTTPException(status_code=409, detail="Confirm this candidate's Formal Appointment first. The founder confirms the appointment — it is never automatic.")
            if payload.type in {"ninety_day_plan", "board_member_portfolio"}:
                profile_done = await db.board_profile_responses.find_one(
                    {"user_id": user_id, "$or": [{"application_id": application_id}, {"data.email": application.get("applicant_email", "")}]},
                    {"_id": 0, "response_id": 1})
                if not profile_done:
                    raise HTTPException(status_code=409, detail="This member's New Board Member Profile has not been completed yet. Complete that profile first so this resource can be tailored to the person's real skills, interests, capacity and preferred contribution.")
                if payload.type == "board_member_portfolio" and not application.get("portfolio_role_approved"):
                    raise HTTPException(status_code=409, detail="Review, edit and approve this person's Board role before generating their Board Member Portfolio.")
            if payload.type in {"board_member_portfolio", "board_member_engagement_guide", "ninety_day_plan"}:
                context += "\n\n" + application_context_text({**application, "notes": "", "references": []})
                profile_response = await db.board_profile_responses.find_one(
                    {"user_id": user_id, "$or": [{"application_id": application_id}, {"data.email": application.get("applicant_email", "")}]},
                    {"_id": 0, "data": 1})
                if profile_response:
                    import json as _json
                    context += "\n\nNEW BOARD MEMBER PROFILE FORM RESPONSE (the member's own stated strengths, interests, desired contribution, capacity, leadership interest and networks):\n" + _json.dumps(profile_response["data"], indent=1)
                if application.get("board_role"):
                    context += f"\n\nBOARD ROLE / EXPERTISE AREA THEY WERE RECRUITED FOR: {application['board_role']}"
                cv_doc = await db.opportunity_applications.find_one({"application_id": application_id}, {"_id": 0, "cv_text": 1})
                if cv_doc and cv_doc.get("cv_text"):
                    context += "\n\nCANDIDATE CV / RESUME (verified professional background; use only what is actually present):\n" + cv_doc["cv_text"][:12000]
                if payload.type in {"board_member_portfolio", "ninety_day_plan"}:
                    conclusion_context = await onboarding_conclusion_context(application)
                    if conclusion_context:
                        context += conclusion_context
                        context += "\n\nAUTHORITY NOTE: where the optional founder-recorded Onboarding Conclusion contains a specific agreement, that explicit agreement overrides earlier interests or possibilities. Where no Onboarding Conclusion exists, build from the Board Member Profile, application/CV, recruited role and verified organization context without inventing commitments."
                context += "\n\nPRIVACY: never include referee responses, background-check information, internal interview notes, private founder notes or internal evaluation material."
            else:
                context += "\n\n" + application_context_text(application)
                cv_doc = await db.opportunity_applications.find_one({"application_id": application_id}, {"_id": 0, "cv_text": 1})
                if cv_doc and cv_doc.get("cv_text"):
                    context += "\n\nCANDIDATE CV / RESUME (extracted text — use only what is actually present):\n" + cv_doc["cv_text"][:12000]
        if payload.type in GOVERNANCE_BYLAWS_TYPES:
            context += await bylaws_context(user_id)
        if payload.type == "portfolio_email":
            portfolio = await db.generated_materials.find_one(
                {"user_id": user_id, "type": "board_member_portfolio", "application_id": application_id, "status": "Approved"},
                {"_id": 0, "share_token": 1})
            if not portfolio or not portfolio.get("share_token"):
                raise HTTPException(status_code=409, detail="Approve this member's Board Member Portfolio first — the email delivers the approved Portfolio using its secure link.")
            snapshot = application.get("profile_snapshot", {}) if application else {}
            first_name = (snapshot.get("full_name", "") or "there").split(" ")[0]
            org_doc = await db.opportunities.find_one({"user_id": user_id}, {"_id": 0, "organization_name": 1}) or {}
            org_name = org_doc.get("organization_name", "") or org_name_check
            founder_name = f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()
            portfolio_url = f"{origin}/portfolio/{portfolio['share_token']}"
            structured = {
                "subject": f"Your Board Member Portfolio | {org_name}",
                "body": (f"Dear {first_name},\n\n"
                         f"Welcome to the Board of {org_name}.\n\n"
                         "Your Board Member Portfolio brings together the experience, strengths, interests and capacity you shared through the recruitment process and your Board Member Profile, together with the role the organization recruited you to help strengthen. Where we have already confirmed specific responsibilities together, those agreements are reflected as well.\n\n"
                         f"You can review your Portfolio using your secure link:\n\n{portfolio_url}\n\n"
                         "Use it as a practical starting point for how you can contribute. As your role develops through Strategic Planning and future Board decisions, your responsibilities can become even more specific.\n\n"
                         f"Warm regards,\n{founder_name}\n{org_name}"),
            }
            material = await save_generation(db, user_id, payload.type, structured, "Deterministic portfolio delivery email — no AI call used.", application_id)
            return material
        if payload.type in {"interview_invitation", "interview_invitation_message", "before_interview_rejection"} and application and application.get("board_role"):
            context += f"\n\nBOARD ROLE / EXPERTISE AREA THIS CANDIDATE APPLIED FOR: {application['board_role']}"
        if payload.type == "candidate_referee_request":
            process = await db.reference_processes.find_one(
                {"owner_user_id": user_id, "application_id": application_id}, {"_id": 0, "candidate_token": 1, "status": 1})
            if process and process.get("candidate_token") and process.get("status") not in {"Completed", "References Submitted"}:
                context += f"\n\nSECURE REFERENCE INFORMATION FORM URL FOR THIS CANDIDATE (include this exact link): {origin}/reference-form/{process['candidate_token']}"
            else:
                context += "\n\nNO SECURE REFERENCE FORM LINK EXISTS YET — ask the candidate to reply to this email with their referee details."
        if payload.type in {"reference_request_email", "reference_call_script", "reference_evaluation_form", "referee_confirmation_email"} and application_id:
            import json as _json
            process = await db.reference_processes.find_one(
                {"owner_user_id": user_id, "application_id": application_id}, {"_id": 0, "references": 1})
            referees = (process or {}).get("references", [])

            def _referee_details(record):
                return {key: record.get(key, "") for key in ["name", "position", "organization", "relationship", "email", "phone"]}

            selected = next((r for r in referees if r.get("reference_id") == (payload.referee_id or "")), None)
            if not selected and len(referees) == 1:
                selected = referees[0]
            if selected:
                context += ("\n\nTHE SELECTED REFEREE FOR THIS RESOURCE (use ONLY this referee's actual details — never mix in another referee's information):\n"
                            + _json.dumps(_referee_details(selected), indent=1, default=str))
            elif referees:
                context += ("\n\nREFEREES SUPPLIED BY THE CANDIDATE (this resource is produced for ONE referee at a time. Because a single referee has "
                            "not been indicated, address the referee as [Referee Name] and NEVER merge or mix details from different referees):\n"
                            + _json.dumps([_referee_details(r) for r in referees], indent=1, default=str))
        if payload.type == "powerhouse_board_blueprint":
            context += ("\n\nPRESENT BOARD COMPOSITION RULE: Where the supplied information shows the founder/executive director is a serving "
                        "member of the governing Board, include the founder — with their actual skills, experience and role — as part of the "
                        "confirmed present Board when assessing current composition and calculating the gap. Do not automatically count an "
                        "executive director as a Board Member if the supplied information explicitly says they are not serving on the governing Board.")
            summary_material = await get_current_material(db, user_id, "reactivation_board_summary")
            if summary_material and summary_material["current"]:
                context += ("\n\nSUMMARY OF YOUR ENTIRE BOARD (consolidated post-Reactivation picture: confirmed active Board, strengths, what "
                            "it can help carry, presently uncovered areas and unresolved status — where the underlying member records below are "
                            "also supplied, those verified records remain authoritative):\n"
                            + summary_material["current"]["display_text"][:10000])
            roster = await db.reactivation_board_members.find(
                {"user_id": user_id},
                {"_id": 0, "name": 1, "role": 1, "response": 1, "status": 1,
                 "conversation_outcome": 1, "conversation_conclusion": 1}).to_list(100)
            if roster:
                import json as _json
                final_outcomes = {"Continuing as an Active Board Member", "Transitioning to an Advisory Role",
                                  "Transitioning to Another Support Role", "Stepping Down From the Board"}

                def _roster_entry(record):
                    outcome = record.get("conversation_outcome", "")
                    resolved = bool((record.get("conversation_conclusion") or "").strip()) and outcome in final_outcomes
                    entry = {"name": record.get("name", ""), "board_role": record.get("role", ""),
                             "final_recorded_outcome": outcome or "No final outcome recorded yet",
                             "resolution": "RESOLVED" if resolved else "UNRESOLVED"}
                    if resolved and outcome == "Continuing as an Active Board Member":
                        response = record.get("response") or {}
                        entry["confirmed_member_expertise"] = {key: response.get(key, "") for key in [
                            "expertise", "expertise_other", "strengths_resources", "contribution_interests",
                            "ownership_area", "leadership_interest", "leadership_area", "monthly_availability"]}
                    return entry

                context += ("\n\nCURRENT BOARD ROSTER AFTER REACTIVATION (the saved final Reactivation outcome — not the Recommitment Form — "
                            "determines who is actually on the confirmed present Board. Count ONLY members whose final outcome is Continuing as "
                            "an Active Board Member. Never count stepped-down members. Never count Advisory members as governing Board members "
                            "(Advisory capability may be acknowledged separately but is not governing Board capability). Never count UNRESOLVED "
                            "members as confirmed active Board members):\n"
                            + _json.dumps([_roster_entry(record) for record in roster], indent=1, default=str)[:14000])
            reactivation_intake = await db.board_reactivation_intakes.find_one(
                {"user_id": user_id}, {"_id": 0, "bylaws_text": 1}, sort=[("submitted_at", -1)])
            if reactivation_intake and reactivation_intake.get("bylaws_text"):
                context += ("\n\nORGANIZATION BYLAWS EXTRACT (verified Board/governance context ONLY — use for Board structure, Board-size "
                            "parameters or officer structure where explicitly stated; never invent legal requirements or legal conclusions; "
                            "where sources conflict, use the verified information conservatively):\n"
                            + reactivation_intake["bylaws_text"][:10000])
        if payload.type in {"conditional_offer", "unconditional_offer"}:
            required_types = ["organization_overview", "board_manual", "board_member_agreement",
                              "confidentiality_agreement", "conflict_of_interest_agreement"]
            missing = []
            for doc_type in required_types:
                document = await db.generated_materials.find_one(
                    {"user_id": user_id, "type": doc_type, "application_id": "", "status": "Approved"},
                    {"_id": 0, "material_id": 1})
                if not document:
                    missing.append(GENERATION_TYPES[doc_type]["title"])
            onboarding_session = profile.get("onboarding_session") or {}
            if not onboarding_session.get("date") or not onboarding_session.get("time") or not onboarding_session.get("timezone"):
                missing.append("Onboarding date, time and timezone")
            if missing:
                raise HTTPException(
                    status_code=409,
                    detail="Prepare the onboarding session before generating the appointment email: " + ", ".join(missing),
                )
            context += (
                "\n\nONBOARDING SESSION DETAILS (include these actual details in the appointment email):\n"
                f"Date: {onboarding_session.get('date', '')}\n"
                f"Time: {onboarding_session.get('time', '')}\n"
                f"Timezone: {onboarding_session.get('timezone', '')}\n"
                f"Format: {onboarding_session.get('format', '')}\n"
                f"Meeting link: {onboarding_session.get('link', '')}\n"
                f"Location: {onboarding_session.get('location', '')}"
            )

        if payload.type == "conditional_offer":
            process = await db.reference_processes.find_one(
                {"owner_user_id": user_id, "application_id": application_id}, {"_id": 0, "status": 1})
            reference_status = (process or {}).get("status") or application.get("reference_check_status") or "Not started"
            background_status = (application.get("background_check") or {}).get("status") or "Not decided"
            context += (
                "\n\nCONDITIONAL APPOINTMENT STATUS (authoritative):"
                f"\nREFERENCE PROCESS STATUS: {reference_status}."
                f"\nBACKGROUND CHECK STATUS: {background_status}."
                "\nThe founder is choosing a CONDITIONAL appointment offer. State only the actual conditions that remain outstanding. "
                "If the reference process is not Completed, it may be stated as an outstanding condition. "
                "If a background check is explicitly required and not Completed, it may be stated as an outstanding condition. "
                "If Background Check is Not Required, do not mention it as a condition. "
                "Onboarding is a separate next stage after this appointment offer."
            )
            if application.get("board_role"):
                context += f"\nBOARD ROLE / PRIORITY EXPERTISE PROFILE FOR THIS CANDIDATE: {application['board_role']}"

        if payload.type == "unconditional_offer":
            context += (
                "\n\nUNCONDITIONAL APPOINTMENT OFFER (authoritative): "
                "The founder has chosen to offer this candidate the Board position without making reference or background-check completion a condition of the offer. "
                "Do not claim those checks were completed if they were not. Onboarding is the next stage."
            )
            if application.get("board_role"):
                context += f"\nBOARD ROLE / PRIORITY EXPERTISE PROFILE FOR THIS CANDIDATE: {application['board_role']}"

        if payload.type == "onboarding_email":
            required_types = ["organization_overview", "board_manual", "board_member_agreement",
                              "confidentiality_agreement", "conflict_of_interest_agreement"]
            missing = []
            for doc_type in required_types:
                document = await db.generated_materials.find_one(
                    {"user_id": user_id, "type": doc_type, "application_id": "", "status": "Approved"},
                    {"_id": 0, "material_id": 1})
                if not document:
                    missing.append(GENERATION_TYPES[doc_type]["title"])
            session = profile.get("onboarding_session") or {}
            if not session.get("date") or not session.get("time") or not session.get("timezone"):
                missing.append("Onboarding date, time and timezone")
            if missing:
                raise HTTPException(status_code=409, detail="Prepare and approve the onboarding items first: " + ", ".join(missing))

            links = []
            overview_token = await ensure_share_token(user_id, "organization_overview")
            manual_token = await ensure_share_token(user_id, "board_manual")
            links.append(f"Organization Overview (View): {origin}/shared/{overview_token}")
            links.append(f"Board Manual (View): {origin}/shared/{manual_token}")

            for agreement_type in ["board_member_agreement", "confidentiality_agreement", "conflict_of_interest_agreement"]:
                request_record = await db.signature_requests.find_one(
                    {"owner_user_id": user_id, "application_id": application_id, "agreement_type": agreement_type, "status": {"$ne": "Void"}},
                    {"_id": 0, "token": 1})
                if not request_record:
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
                    request_record = {"token": token}
                links.append(f"{GENERATION_TYPES[agreement_type]['title']} (Review and Sign): {origin}/sign/{request_record['token']}")

            profile_link = await db.board_profile_links.find_one(
                {"user_id": user_id, "application_id": application_id}, {"_id": 0, "token": 1})
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

            context += (
                "\n\nBOARD ONBOARDING SESSION (use these exact details):\n"
                + "\n".join(f"{key}: {value}" for key, value in session.items() if value)
                + "\n\nONBOARDING LINKS (copy every URL exactly):\n"
                + "\n".join(links)
            )
        if payload.type in {"formal_appointment_letter", "formal_appointment_email"}:
            process = await db.reference_processes.find_one(
                {"owner_user_id": user_id, "application_id": application_id}, {"_id": 0, "status": 1})
            reference_status = (process or {}).get("status") or application.get("reference_check_status") or "Not started"
            background = (application.get("background_check") or {}).get("status", "")
            context += ("\n\nFORMAL APPOINTMENT STATUS (read-only facts):"
                        "\nThe founder has confirmed this candidate's FINAL FORMAL APPOINTMENT after onboarding. The appointment is no longer conditional."
                        f"\nREFERENCE PROCESS STATUS: {reference_status}."
                        f"\nBACKGROUND CHECK STATUS: {background or 'Not recorded'}."
                        "\nThese statuses are informational only. The founder deliberately controls whether reference/background checks are used and has already made the final appointment decision. "
                        "Never describe the final appointment as subject to a check that the founder chose not to require.")
            if application.get("board_role"):
                context += f"\nBOARD ROLE / PRIORITY EXPERTISE PROFILE FOR THIS CANDIDATE: {application['board_role']}"
        if payload.type == "formal_appointment_letter":
            context += f"\n\nFORMAL APPOINTMENT LETTER DATE (backend-supplied — copy exactly into letter_date; never invent a date): {datetime.now(timezone.utc).strftime('%B %d, %Y').replace(' 0', ' ')}"
        if payload.type == "formal_appointment_email":
            links = []
            letter_material = await db.generated_materials.find_one(
                {"user_id": user_id, "type": "formal_appointment_letter", "application_id": application_id, "status": "Approved"},
                {"_id": 0, "material_id": 1})
            if letter_material:
                letter_link = await db.share_links.find_one(
                    {"material_id": letter_material["material_id"]},
                    {"_id": 0, "share_token": 1})
                if not letter_link:
                    letter_link = {"share_token": secrets.token_urlsafe(24)}
                    await db.share_links.insert_one({
                        "share_token": letter_link["share_token"],
                        "material_id": letter_material["material_id"],
                        "user_id": user_id,
                        "created_at": now_iso(),
                    })
                links.append(f"Formal Board Appointment Letter (View): {origin}/shared/{letter_link['share_token']}")
            context += (
                "\n\nFINAL APPOINTMENT EMAIL: Onboarding has already been completed. "
                "Do not ask the new Board Member to repeat onboarding, re-sign documents or redo their Board Member Profile."
            )
            if links:
                context += "\n\nFINAL APPOINTMENT LINK TO INCLUDE:\n" + "\n".join(links)
        if payload.type == "first_board_meeting_invitation":
            meeting = profile.get("first_meeting") or {}
            if meeting:
                context += "\n\nFIRST BOARD MEETING DETAILS (use these exact details; omit anything blank):\n" + "\n".join(f"{k}: {v}" for k, v in meeting.items() if v)
            joined = await db.opportunity_applications.find(
                {"owner_user_id": user_id, "final_outcome": "Joined Board"},
                {"_id": 0, "application_id": 1, "profile_snapshot": 1, "applicant_email": 1}).to_list(30)
            incomplete = 0
            for member_app in joined:
                response_doc = await db.board_profile_responses.find_one({"user_id": user_id, "application_id": member_app["application_id"]}, {"_id": 0, "submitted_at": 1})
                if not response_doc:
                    incomplete += 1
            names = ", ".join(m.get("profile_snapshot", {}).get("full_name", "") for m in joined)
            context += f"\n\nFORMALLY APPOINTED BOARD MEMBERS RECEIVING THIS INVITATION (Joined Board only — never invite conditional or merely selected candidates): {names or 'the new board members'}"
            if incomplete:
                context += ("\n\nBOARD MEMBER PROFILE STATUS: one or more recipients have NOT completed their New Board Member Profile. Do NOT name them and do NOT include any "
                            "candidate-specific secure URL in this group email. Simply include a general reminder along the lines of: 'If you have not yet completed your "
                            "Board Member Profile, please use the secure link provided in your appointment/onboarding email to complete it before the meeting.'")
            else:
                context += "\n\nBOARD MEMBER PROFILE STATUS: every recipient has completed their Board Member Profile — OMIT the profile reminder entirely."
        if payload.type == "onboarding_script":
            structured={"session_purpose":"Welcome newly appointed Board Members, clarify how the Board and founder will work together, discuss each person's strengths, and record the responsibilities actually agreed during the session.","before_you_begin":["Confirm the meeting date, time and participant list.","Open the approved Organization Overview, Board Manual and three agreements.","Prepare a place to record each member's agreed role, responsibility, support needed and immediate next step.","Tell everyone before any recording or transcription begins and obtain their consent."],"sections":[
                {"title":"Welcome And Introductions","objective":"Create connection and explain the outcome of the session.","founder_script":"Welcome, and thank you for agreeing to serve. Today we will make sure you understand our organization, the Board we are building and how we will work together. We will also discuss where each of you believes your experience and strengths can make the greatest contribution. Before we finish, we will confirm the next step for each person.","discussion_questions":["Please introduce yourself, what drew you to this mission and what you hope to contribute."],"facilitator_notes":["Let every person speak without assigning a role yet."]},
                {"title":"Why The Organization Exists And Where It Is Going","objective":"Ground the Board in verified mission, present reality and priorities.","founder_script":"I will briefly walk us through why the organization exists, who we serve, what we do today and the direction we are working toward. Please ask questions wherever greater clarity would help you lead with us.","discussion_questions":["What questions do you have about the mission, programs or present priorities?"],"facilitator_notes":["Use the approved Organization Overview. Distinguish current reality from future ambition."]},
                {"title":"The Role Of The Board","objective":"Clarify Board-level leadership and expectations.","founder_script":"Board service here means shared leadership, planning, guidance, accountability, appropriate oversight and helping the organization build the relationships and capacity required to advance the mission. Board Members are not unpaid staff, and we will define responsibilities clearly rather than assuming everyone does the same work.","discussion_questions":["What part of this Board role needs clarification?"],"facilitator_notes":["Use the approved Board Manual and Agreement. Do not invent legal requirements."]},
                {"title":"Your Strengths And Contribution","objective":"Reach an honest, mutual agreement with each member.","founder_script":"I would like us to discuss where your experience, interests and capacity connect with what the organization needs. This is a conversation, not an assignment. We will only record a responsibility after we agree on it together.","discussion_questions":["Where do you believe you can contribute most?","What responsibility are you willing to carry?","What support would help you succeed?","What immediate next step should we record?"],"facilitator_notes":["Repeat this conversation for each member and record the actual conclusion."]},
                {"title":"Documents, Fundraising And Next Steps","objective":"Confirm outstanding onboarding items and what happens after the meeting.","founder_script":"The Organization Overview explains the mission and work. The Board Manual explains how the Board functions. The Board Member, Confidentiality and Conflict of Interest Agreements record our shared expectations. We will address fundraising responsibilities later through the Board Fundraising Planning process rather than making assumptions today. After this session, I will document what we agreed and send your Board Member Portfolio and next-step information.","discussion_questions":["Is any document or immediate next step unclear?"],"facilitator_notes":["Do not read every document aloud. Confirm any outstanding signature or profile item."]}],"after_the_session":["Save an Onboarding Conclusion / Role Agreement for each member.","Generate the Board Member Portfolio only from the recorded agreement and verified organization information.","Send the confirmed first Board meeting information.","Follow up by email with any outstanding document or action."]}
        else:
            try:
                structured = await generate_structured(payload.type, context, payload.instructions or "")
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Generation failed: {str(exc)[:300]}. Your information is preserved — you can try again.") from exc
        structured = replace_link(structured, apply_url)
        material = await save_generation(db, user_id, payload.type, structured, context[:1500], application_id)
        if application_id and payload.type == "interview_invitation":
            await db.opportunity_applications.update_one(
                {"application_id": application_id, "owner_user_id": user_id},
                {"$set": {"status": "Interview Invited", "interview_invitation_generated_at": now_iso(), "updated_at": now_iso()}},
            )
        if application_id and payload.type == "interview_guide":
            await db.opportunity_applications.update_one(
                {"application_id": application_id, "owner_user_id": user_id},
                {"$set": {"interview_guide.status": "Ready", "interview_guide.material_id": material["material_id"],
                          "interview_guide.generated_at": now_iso(), "updated_at": now_iso()}},
            )
        return material

    ONBOARDING_CONCLUSION_FIELDS = ["board_role", "agreed_primary_contribution_area", "agreed_responsibility", "agreed_leadership",
                                    "how_their_experience_will_be_used", "organization_support_agreed", "immediate_next_steps", "private_notes"]

    @router.get("/applications/{application_id}/onboarding-conclusion")
    async def get_onboarding_conclusion(application_id: str, request: Request):
        member = await selection_member(request)
        application = await owned_application(member["user_id"], application_id)
        conclusion = application.get("onboarding_conclusion") or {}
        return {"board_member": application.get("profile_snapshot", {}).get("full_name", ""),
                "board_role": conclusion.get("board_role") or application.get("board_role", ""),
                "conclusion": {key: conclusion.get(key, "") for key in ONBOARDING_CONCLUSION_FIELDS},
                "saved_at": conclusion.get("saved_at", "")}

    @router.put("/applications/{application_id}/onboarding-conclusion")
    async def save_onboarding_conclusion(application_id: str, payload: dict, request: Request):
        member = await selection_member(request)
        await owned_application(member["user_id"], application_id)
        conclusion = {key: str(payload.get(key, ""))[:6000] for key in ONBOARDING_CONCLUSION_FIELDS}
        if not conclusion["agreed_responsibility"].strip() and not conclusion["agreed_primary_contribution_area"].strip():
            raise HTTPException(status_code=422, detail="Record the agreed contribution area or responsibility before saving the Onboarding Conclusion")
        conclusion["saved_at"] = now_iso()
        await db.opportunity_applications.update_one(
            {"application_id": application_id, "owner_user_id": member["user_id"]},
            {"$set": {"onboarding_conclusion": conclusion}})
        return {"status": "saved", "saved_at": conclusion["saved_at"]}

    @router.post("/materials/{material_id}/approve")
    async def approve_material(material_id: str, request: Request):
        member = await current_member(request)
        material = await db.generated_materials.find_one(
            {"material_id": material_id, "user_id": member["user_id"]}, {"_id": 0, "type": 1, "share_token": 1})
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        updates = {"status": "Approved", "approved_at": now_iso(), "updated_at": now_iso()}
        if material["type"] == "board_member_portfolio" and not material.get("share_token"):
            updates["share_token"] = secrets.token_urlsafe(24)
        await db.generated_materials.update_one(
            {"material_id": material_id, "user_id": member["user_id"]}, {"$set": updates})
        if material["type"] == "powerhouse_board_blueprint":
            await db.recruitment_preparation.update_one(
                {"user_id": member["user_id"]},
                {"$set": {"status": "queued", "stage": "campaign_assets", "updated_at": now_iso()},
                 "$setOnInsert": {"created_at": now_iso()}},
                upsert=True,
            )
            asyncio.create_task(prepare_campaign_assets(member["user_id"]))
        refreshed = await db.generated_materials.find_one({"material_id": material_id}, {"_id": 0, "share_token": 1})
        return {"status": "Approved", "share_token": (refreshed or {}).get("share_token", "")}

    # ---------- Board Member Portfolio email (My Board) ----------
    async def approved_portfolio_for(user_id: str, application_id: str) -> dict:
        material = await db.generated_materials.find_one(
            {"user_id": user_id, "type": "board_member_portfolio", "application_id": application_id}, {"_id": 0})
        if not material or material["status"] != "Approved" or not material.get("share_token"):
            raise HTTPException(status_code=409, detail="Approve this Portfolio before preparing the email.")
        return material

    async def recruitment_portfolio_email_content(member: dict, application: dict, material: dict, origin: str) -> dict:
        profile = await get_profile(db, member["user_id"])
        organization = (profile.get("data") or {}).get("organization_name", "") or "our organization"
        snapshot = application.get("profile_snapshot") or {}
        name = snapshot.get("full_name") or application.get("applicant_email", "")
        first = name.split(" ")[0] if name else "there"
        recipient = application.get("applicant_email") or application.get("candidate_email") or ""
        link = f"{origin}/portfolio/{material['share_token']}"
        founder_name = f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()
        body = (
            f"Dear {first},\n\n"
            f"Welcome to the board of {organization}, and thank you for the time you have invested in the recruitment process.\n\n"
            "To help you begin with clarity, I have put together your Board Member Portfolio.\n\n"
            f"It brings together the experience, strengths, interests and capacity you shared through your application and Board Member Profile, along with the role you were recruited to help strengthen at {organization}.\n\n"
            "Please review your Portfolio using the link below:\n\n"
            "[VIEW MY BOARD MEMBER PORTFOLIO]\n\n"
            "I am glad to have you with us, and I look forward to working together as we move forward.\n\n"
            f"{founder_name}\n{organization}")
        return {"to_name": name, "to_email": recipient, "subject": f"Your Board Member Portfolio | {organization}",
                "body": body, "button_label": "VIEW MY BOARD MEMBER PORTFOLIO",
                "portfolio_link": link, "share_token": material["share_token"]}

    @router.get("/applications/{application_id}/portfolio-email")
    async def preview_recruitment_portfolio_email(application_id: str, request: Request):
        member = await selection_member(request)
        application = await db.opportunity_applications.find_one(
            {"application_id": application_id, "owner_user_id": member["user_id"]}, {"_id": 0, "cv_text": 0})
        if not application:
            raise HTTPException(status_code=404, detail="Board member not found")
        material = await approved_portfolio_for(member["user_id"], application_id)
        return await recruitment_portfolio_email_content(member, application, material, origin_of(request))

    class RecruitmentPortfolioEmailSend(BaseModel):
        subject: str = Field(min_length=1)
        body: str = Field(min_length=1)

    @router.post("/applications/{application_id}/portfolio-email")
    async def send_recruitment_portfolio_email(application_id: str, payload: RecruitmentPortfolioEmailSend, request: Request):
        member = await selection_member(request)
        application = await db.opportunity_applications.find_one(
            {"application_id": application_id, "owner_user_id": member["user_id"]}, {"_id": 0, "cv_text": 0})
        if not application:
            raise HTTPException(status_code=404, detail="Board member not found")
        material = await approved_portfolio_for(member["user_id"], application_id)
        defaults = await recruitment_portfolio_email_content(member, application, material, origin_of(request))
        if not defaults["to_email"]:
            raise HTTPException(status_code=409, detail="We do not have an email address for this board member yet.")
        body = payload.body if "[" in payload.body else payload.body + f"\n\n[{defaults['button_label']}]"
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        message = {"from": os.environ["NONPROFIT_SENDER"], "to": [defaults["to_email"]],
                   "subject": payload.subject,
                   "html": portfolio_email_html(body, defaults["button_label"], defaults["portfolio_link"])}
        if member.get("email"):
            message["reply_to"] = [member["email"]]
        try:
            await resend.Emails.send_async(message)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc
        now = now_iso()
        await db.generated_materials.update_one(
            {"material_id": material["material_id"]},
            {"$set": {"sent_at": now, "sent_to": defaults["to_email"], "sent_version": material["current_version"], "updated_at": now}})
        return {"status": "sent", "sent_at": now}

    # ---------- External applicants, share links, board member profile form ----------
    @router.post("/applications/external", status_code=201)
    async def add_external_applicant(request: Request, name: str = Form(...), cv: UploadFile = File(...), email: str = Form(""), phone: str = Form(""), linkedin: str = Form(""), notes: str = Form("")):
        member = await selection_member(request)
        ts = now_iso()
        cv_file_id, cv_filename, cv_text = "", "", ""
        if cv is not None and cv.filename:
            extension = os.path.splitext(cv.filename)[1].lower()
            if extension not in {".pdf", ".doc", ".docx"}:
                raise HTTPException(status_code=422, detail="Upload the applicant's CV as a PDF, DOC, or DOCX file")
            content = await cv.read()
            if not content:
                raise HTTPException(status_code=422, detail="The uploaded CV file is empty")
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

    @router.post("/materials/{material_id}/design")
    async def edit_material_design(material_id: str, payload: dict, request: Request):
        member = await current_member(request)
        instruction = str(payload.get("instruction", "")).strip()
        if not instruction:
            raise HTTPException(status_code=422, detail="Describe what you want changed about the design")
        material = await db.generated_materials.find_one({"material_id": material_id, "user_id": member["user_id"]}, {"_id": 0, "material_id": 1, "design_spec": 1, "title": 1, "design_instruction_history": 1})
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        current = material.get("design_spec") or {"heading_scale": 1, "logo_position": "left", "body_font": "serif",
                                                  "spacing_scale": 1, "text_align": "left", "accent_intensity": "standard"}
        context = (f"DOCUMENT: {material.get('title', '')}\n\nCURRENT DESIGN VALUES:\n"
                   + "\n".join(f"- {key}: {value}" for key, value in current.items())
                   + f"\n\nCUSTOMER'S DESIGN INSTRUCTION:\n{instruction}")
        structured = await generate_structured("resource_design_adjustments", context)
        spec = {
            "heading_scale": min(max(float(structured.get("heading_scale", current.get("heading_scale", 1)) or 1), 0.6), 1.5),
            "logo_position": structured.get("logo_position") if structured.get("logo_position") in {"left", "right", "center"} else current.get("logo_position", "left"),
            "body_font": structured.get("body_font") if structured.get("body_font") in {"serif", "sans-serif"} else current.get("body_font", "serif"),
            "spacing_scale": min(max(float(structured.get("spacing_scale", current.get("spacing_scale", 1)) or 1), 0.6), 2),
            "text_align": structured.get("text_align") if structured.get("text_align") in {"left", "center"} else current.get("text_align", "left"),
            "accent_intensity": structured.get("accent_intensity") if structured.get("accent_intensity") in {"subtle", "standard", "strong"} else current.get("accent_intensity", "standard"),
        }
        await db.generated_materials.update_one({"material_id": material_id}, {"$set": {
            "design_spec": spec, "design_instruction_history": (material.get("design_instruction_history") or []) + [{"instruction": instruction, "applied_at": now_iso()}]}})
        return {"design_spec": spec}

    async def onboarding_live_payload(user_id: str, origin: str) -> dict:
        profile = await get_profile(db, user_id)
        live = profile.get("onboarding_live") or {}
        material = await get_current_material(db, user_id, "board_manual", "")
        current = material.get("current") if material else None
        structured = (current or {}).get("structured") or {}
        sections = [
            {"title": str(section.get("title") or "").strip(), "content": str(section.get("content") or "").strip()}
            for section in (structured.get("sections") or [])
            if str(section.get("title") or "").strip() or str(section.get("content") or "").strip()
        ]
        if not sections and current and str(current.get("display_text") or "").strip():
            sections = [{"title": "Board Member Manual", "content": str(current.get("display_text") or "").strip()}]
        index = min(max(int(live.get("current_section_index") or 0), 0), max(0, len(sections) - 1))
        token = live.get("share_token", "")
        opportunity = await db.opportunities.find_one({"user_id": user_id}, {"_id": 0, "organization_name": 1}) or {}
        organization_name = (profile.get("data") or {}).get("organization_name") or opportunity.get("organization_name", "")
        session = {
            "share_token": token,
            "viewer_url": f"{origin}/onboarding-session/{token}" if token else "",
            "status": live.get("status", "NOT STARTED"),
            "current_section_index": index,
        }
        return {
            "organization_name": organization_name,
            "session": session,
            "share_token": token,
            "viewer_url": session["viewer_url"],
            "status": session["status"],
            "current_section_index": index,
            "total_sections": len(sections),
            "sections": sections,
        }

    @router.get("/onboarding-live")
    async def get_onboarding_live(request: Request):
        member = await current_member(request)
        origin = os.environ.get("PUBLIC_ORIGIN") or request.headers.get("origin") or "https://nonprofitboardbuilder.com"
        return await onboarding_live_payload(member["user_id"], origin)

    @router.post("/onboarding-live/share")
    async def share_onboarding_live(request: Request):
        member = await current_member(request)
        profile = await get_profile(db, member["user_id"])
        live = profile.get("onboarding_live") or {}
        token = live.get("share_token") or secrets.token_urlsafe(24)
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {
                "onboarding_live.share_token": token,
                "onboarding_live.status": live.get("status") or "NOT STARTED",
                "onboarding_live.current_section_index": int(live.get("current_section_index") or 0),
                "onboarding_live.updated_at": now_iso(),
            }},
            upsert=True,
        )
        origin = os.environ.get("PUBLIC_ORIGIN") or request.headers.get("origin") or "https://nonprofitboardbuilder.com"
        return await onboarding_live_payload(member["user_id"], origin)

    @router.post("/onboarding-live/start")
    async def start_onboarding_live(request: Request):
        member = await current_member(request)
        manual = await get_current_material(db, member["user_id"], "board_manual", "")
        if not manual or manual["material"].get("status") != "Approved":
            raise HTTPException(status_code=409, detail="Approve the Board Manual before starting the live onboarding session.")
        profile = await get_profile(db, member["user_id"])
        session_details = profile.get("onboarding_session") or {}
        if not session_details.get("date") or not session_details.get("time") or not session_details.get("timezone"):
            raise HTTPException(status_code=409, detail="Save the onboarding date, time and timezone before starting the live session.")
        live = profile.get("onboarding_live") or {}
        token = live.get("share_token") or secrets.token_urlsafe(24)
        now = now_iso()
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {
                "onboarding_live.share_token": token,
                "onboarding_live.status": "IN PROGRESS",
                "onboarding_live.current_section_index": int(live.get("current_section_index") or 0),
                "onboarding_live.started_at": live.get("started_at") or now,
                "onboarding_live.updated_at": now,
            }},
            upsert=True,
        )
        origin = os.environ.get("PUBLIC_ORIGIN") or request.headers.get("origin") or "https://nonprofitboardbuilder.com"
        return await onboarding_live_payload(member["user_id"], origin)

    @router.post("/onboarding-live/progress")
    @router.put("/onboarding-live/section")
    async def set_onboarding_live_section(payload: OnboardingLiveSectionUpdate, request: Request):
        member = await current_member(request)
        origin = os.environ.get("PUBLIC_ORIGIN") or request.headers.get("origin") or "https://nonprofitboardbuilder.com"
        current = await onboarding_live_payload(member["user_id"], origin)
        if not current.get("share_token"):
            raise HTTPException(status_code=409, detail="Create the shared onboarding screen first.")
        if current["total_sections"] and payload.current_section_index >= current["total_sections"]:
            raise HTTPException(status_code=422, detail="That onboarding section does not exist.")
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {
                "onboarding_live.current_section_index": payload.current_section_index,
                "onboarding_live.status": "IN PROGRESS",
                "onboarding_live.updated_at": now_iso(),
            }},
        )
        return await onboarding_live_payload(member["user_id"], origin)

    @router.post("/onboarding-live/complete")
    async def complete_onboarding_live(request: Request):
        member = await current_member(request)
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"onboarding_live.status": "COMPLETED", "onboarding_live.completed_at": now_iso(), "onboarding_live.updated_at": now_iso()}},
        )
        origin = os.environ.get("PUBLIC_ORIGIN") or request.headers.get("origin") or "https://nonprofitboardbuilder.com"
        return await onboarding_live_payload(member["user_id"], origin)

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

    @router.get("/board-profiles")
    async def board_profiles(request: Request):
        member = await current_member(request)
        material = await get_current_material(db, member["user_id"], "powerhouse_board_blueprint")
        lead = await get_lead(db, member) or {}
        desired_raw = ((lead.get("answers") or {}).get("new_members_needed") or "").strip()
        desired_count = int(desired_raw) if desired_raw.isdigit() else None
        current = material["current"] if material else None
        return {
            "material": material["material"] if material else None,
            "priority_roles": (current.get("structured") or {}).get("priority_roles", []) if current else [],
            "desired_count": desired_count,
        }

    @router.put("/board-profiles")
    async def update_board_profiles(payload: BoardProfilesUpdate, request: Request):
        member = await current_member(request)
        lead = await get_lead(db, member) or {}
        desired_raw = ((lead.get("answers") or {}).get("new_members_needed") or "").strip()
        desired_count = int(desired_raw) if desired_raw.isdigit() else None
        roles = []
        for raw in payload.priority_roles:
            role_name = str(raw.get("role_name") or "").strip()
            why = str(raw.get("why_this_person_is_important") or "").strip()
            support = str(raw.get("how_this_person_can_support") or "").strip()
            if not role_name:
                raise HTTPException(status_code=422, detail="Every Board Member profile needs a role or profile title.")
            roles.append({
                "role_name": role_name[:180],
                "why_this_person_is_important": why[:1200],
                "how_this_person_can_support": support[:1200],
            })
        if desired_count and len(roles) != desired_count:
            raise HTTPException(
                status_code=409,
                detail=f"You told us you want to recruit {desired_count} new Board Members. Keep exactly {desired_count} profiles by editing, replacing or removing one before approval.",
            )
        material = await save_generation(
            db, member["user_id"], "powerhouse_board_blueprint",
            {"priority_roles": roles},
            "Founder-edited Board Member profiles from the six Recruitment Questions.",
        )
        return {"material": material, "priority_roles": roles, "desired_count": desired_count}

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

    # These are the four materials the customer can actually generate in the
    # Recruitment dashboard.  Do not gate launch on hidden/legacy material
    # types that have no corresponding customer control.
    CAMPAIGN_TYPES = ["board_recruitment_job_post", "recruitment_emails", "social_posts", "referral_request_email"]

    async def opportunity_readiness(user_id, opportunity):
        material_types = await db.generated_materials.distinct(
            "type",
            {
                "user_id": user_id,
                "type": {"$in": CAMPAIGN_TYPES},
                "$or": [
                    {"application_id": ""},
                    {"application_id": None},
                    {"application_id": {"$exists": False}},
                ],
            },
        )
        generated_types = {item for item in material_types if item in CAMPAIGN_TYPES}
        return {
            "application_saved": bool(opportunity.get("application_saved")),
            "materials_generated": all(item in generated_types for item in CAMPAIGN_TYPES),
            "materials_count": len(generated_types),
            "materials_total": len(CAMPAIGN_TYPES),
        }

    async def prepare_campaign_assets(user_id: str) -> None:
        """Prepare the next recruitment stage after the founder approves the board profiles."""
        try:
            member = await db.members.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0}) or {}
            if not member:
                return
            await db.recruitment_preparation.update_one(
                {"user_id": user_id},
                {"$set": {"status": "generating", "stage": "application", "updated_at": now_iso()}},
                upsert=True,
            )
            opportunity = await ensure_opportunity(user_id, member)
            if not opportunity.get("application_saved"):
                await db.opportunities.update_one(
                    {"user_id": user_id},
                    {"$set": {"custom_questions": opportunity.get("custom_questions", []),
                              "application_saved": True, "updated_at": now_iso()}},
                )
                opportunity["application_saved"] = True

            origin = os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com"
            apply_url = f"{origin}/board-opportunities/{opportunity['slug']}/apply"
            base_context = await build_org_context(db, user_id, member)
            base_context += f"\n\nBOARD APPLICATION URL (insert this exact URL wherever the application link belongs): {apply_url}"

            failures = []
            for generation_type in CAMPAIGN_TYPES:
                existing = await db.generated_materials.find_one(
                    {"user_id": user_id, "type": generation_type,
                     "$or": [{"application_id": ""}, {"application_id": None}, {"application_id": {"$exists": False}}]},
                    {"_id": 0, "material_id": 1},
                )
                if existing:
                    continue
                await db.recruitment_preparation.update_one(
                    {"user_id": user_id},
                    {"$set": {"stage": generation_type, "updated_at": now_iso()}},
                )
                try:
                    context = base_context
                    reference = await reference_context(db, generation_type)
                    if reference:
                        context += f"\n\n{reference}"
                    structured = await generate_structured(
                        generation_type,
                        context,
                        "Prepare a finished organization-specific recruitment asset from the founder-approved Board Member profiles. "
                        "Use the organization's actual mission, board needs, value proposition and application link. Do not invent facts.",
                    )
                    await save_generation(db, user_id, generation_type, structured, context[:1500])
                except Exception as exc:
                    failures.append({"type": generation_type, "error": str(exc)[:300]})

            status = "ready" if not failures else "partial"
            await db.recruitment_preparation.update_one(
                {"user_id": user_id},
                {"$set": {"status": status, "stage": "campaign_assets", "failures": failures,
                          "completed_at": now_iso(), "updated_at": now_iso()}},
                upsert=True,
            )
        except Exception as exc:
            await db.recruitment_preparation.update_one(
                {"user_id": user_id},
                {"$set": {"status": "failed", "stage": "campaign_assets",
                          "error": str(exc)[:500], "updated_at": now_iso()}},
                upsert=True,
            )

    async def prepare_onboarding_assets(user_id: str) -> None:
        """Prepare reusable organization-level onboarding drafts while recruitment is running."""
        try:
            member = await db.members.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0}) or {}
            if not member:
                return
            context = await build_org_context(db, user_id, member)
            context += await bylaws_context(user_id)
            types = ["organization_overview", "board_manual", "board_member_agreement",
                     "confidentiality_agreement", "conflict_of_interest_agreement"]
            await db.recruitment_preparation.update_one(
                {"user_id": user_id},
                {"$set": {"onboarding_status": "generating", "onboarding_stage": types[0], "updated_at": now_iso()}},
                upsert=True,
            )
            failures = []
            for generation_type in types:
                existing = await db.generated_materials.find_one(
                    {"user_id": user_id, "type": generation_type,
                     "$or": [{"application_id": ""}, {"application_id": None}, {"application_id": {"$exists": False}}]},
                    {"_id": 0, "material_id": 1},
                )
                if existing:
                    continue
                await db.recruitment_preparation.update_one(
                    {"user_id": user_id},
                    {"$set": {"onboarding_stage": generation_type, "updated_at": now_iso()}},
                )
                try:
                    reference = await reference_context(db, generation_type)
                    generation_context = context + (f"\n\n{reference}" if reference else "")
                    structured = await generate_structured(
                        generation_type,
                        generation_context,
                        "Use the standard Board onboarding framework for this resource and update it only with verified organization-specific "
                        "mission, board model, expectations and governance information. Keep the framework consistent across organizations. "
                        "Do not invent legal requirements, policies or organization facts.",
                    )
                    await save_generation(db, user_id, generation_type, structured, generation_context[:1500])
                except Exception as exc:
                    failures.append({"type": generation_type, "error": str(exc)[:300]})
            await db.recruitment_preparation.update_one(
                {"user_id": user_id},
                {"$set": {"onboarding_status": "ready" if not failures else "partial",
                          "onboarding_stage": "onboarding_assets", "onboarding_failures": failures,
                          "onboarding_completed_at": now_iso(), "updated_at": now_iso()}},
                upsert=True,
            )
        except Exception as exc:
            await db.recruitment_preparation.update_one(
                {"user_id": user_id},
                {"$set": {"onboarding_status": "failed", "onboarding_stage": "onboarding_assets",
                          "onboarding_error": str(exc)[:500], "updated_at": now_iso()}},
                upsert=True,
            )

    @router.get("/opportunity")
    async def read_opportunity(request: Request):
        member = await current_member(request)
        opportunity = await ensure_opportunity(member["user_id"], member)
        readiness = await opportunity_readiness(member["user_id"], opportunity)
        applications = await db.opportunity_applications.count_documents({"owner_user_id": member["user_id"]})
        preparation = await db.recruitment_preparation.find_one(
            {"user_id": member["user_id"]}, {"_id": 0}) or {}
        return {"opportunity": opportunity, "core_questions": CORE_QUESTIONS, "readiness": readiness,
                "applications_count": applications, "preparation": preparation}

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
        readiness = await opportunity_readiness(user_id, opportunity)
        if not (readiness["application_saved"] and readiness["materials_generated"]):
            raise HTTPException(status_code=409, detail="Generate all four recruitment campaign materials before launching your campaign")
        board_opportunity = await get_current_material(db, user_id, "board_opportunity")
        structured = (board_opportunity["current"].get("structured") or {}) if (board_opportunity and board_opportunity["current"]) else {}
        profile = await get_profile(db, user_id)
        data = profile.get("data", {})
        strategy_intake = profile.get("strategy_intake", {}) or {}
        blueprint = await get_current_material(db, user_id, "powerhouse_board_blueprint")
        role_names = ""
        if blueprint and blueprint["current"]:
            roles = (blueprint["current"].get("structured") or {}).get("priority_roles", [])
            role_names = ", ".join(role.get("role_name", "") for role in roles if role.get("role_name"))
        commitment = ", ".join(v for v in [strategy_intake.get("meeting_frequency", ""), strategy_intake.get("time_expectation", "")] if v)
        location = strategy_intake.get("meeting_location", "") or ", ".join(v for v in [data.get("city", ""), data.get("state_region", "")] if v)
        email_content = {
            "mission": data.get("mission", "") or structured.get("about_the_organization", ""),
            "candidate_needs": structured.get("who_we_are_looking_for", "") or role_names or ", ".join(data.get("desired_board_skills", [])),
            "commitment": structured.get("meeting_time_and_location", "") or commitment,
            "location": location or structured.get("meeting_time_and_location", ""),
            "deadline": strategy_intake.get("deadline_date", "") or structured.get("application_deadline", ""),
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
        await db.recruitment_preparation.update_one(
            {"user_id": user_id},
            {"$set": {"onboarding_status": "queued", "onboarding_stage": "onboarding_assets", "updated_at": now_iso()},
             "$setOnInsert": {"created_at": now_iso()}},
            upsert=True,
        )
        asyncio.create_task(prepare_onboarding_assets(user_id))
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
        member = await selection_member(request)
        query = {"owner_user_id": member["user_id"]}
        if status:
            query["status"] = status
        applications = await db.opportunity_applications.find(query, {"_id": 0, "cv_text": 0}).sort("created_at", -1).to_list(500)
        profile_rows = await db.board_profile_responses.find({"user_id": member["user_id"]}, {"_id": 0, "application_id": 1, "data.email": 1}).to_list(500)
        profile_application_ids = {row.get("application_id") for row in profile_rows if row.get("application_id")}
        profile_emails = {str((row.get("data") or {}).get("email") or "").strip().lower() for row in profile_rows if str((row.get("data") or {}).get("email") or "").strip()}
        application_ids = [application.get("application_id") for application in applications if application.get("application_id")]
        material_rows = await db.generated_materials.find(
            {"user_id": member["user_id"], "application_id": {"$in": application_ids}},
            {"_id": 0, "application_id": 1, "type": 1, "status": 1},
        ).to_list(2000)
        material_map = {}
        for row in material_rows:
            material_map.setdefault(row.get("application_id"), set()).add(row.get("type"))
        for application in applications:
            application["board_profile_completed"] = (
                application.get("application_id") in profile_application_ids
                or str(application.get("applicant_email") or "").strip().lower() in profile_emails
            )
            generated = material_map.get(application.get("application_id"), set())
            application["journey"] = {
                "interview_invitation_generated": "interview_invitation" in generated,
                "rejection_generated": "before_interview_rejection" in generated,
                "interview_guide_generated": "interview_guide" in generated,
                "conditional_offer_generated": "conditional_offer" in generated,
                "unconditional_offer_generated": "unconditional_offer" in generated,
                "portfolio_generated": "board_member_portfolio" in generated,
            }
        return {"applications": applications, "statuses": APPLICATION_STATUSES}

    @router.get("/applications/{application_id}")
    async def application_detail(application_id: str, request: Request):
        member = await selection_member(request)
        application = await owned_application(member["user_id"], application_id)
        application.pop("cv_text", None)
        materials = await db.generated_materials.find(
            {"user_id": member["user_id"], "application_id": application_id}, {"_id": 0}).to_list(100)
        return {"application": application, "materials": materials,
                "reference_outcomes": REFERENCE_OUTCOMES, "background_statuses": BACKGROUND_STATUSES}

    @router.patch("/applications/{application_id}")
    async def update_application(application_id: str, payload: ApplicationUpdate, request: Request):
        member = await selection_member(request)
        application = await owned_application(member["user_id"], application_id)
        updates = {"updated_at": now_iso()}
        if payload.status is not None:
            if payload.status not in APPLICATION_STATUSES:
                raise HTTPException(status_code=422, detail="Invalid applicant status")
            if payload.status == "Selected" and application.get("status") != "Selected":
                profile_done = await db.board_profile_responses.find_one(
                    {"user_id": member["user_id"], "$or": [{"application_id": application_id}, {"data.email": application.get("applicant_email", "")}]},
                    {"_id": 0, "response_id": 1})
                if not profile_done:
                    raise HTTPException(
                        status_code=409,
                        detail="Ask this person to complete their Board Member Profile before confirming the Final Board Appointment. Their profile gives the organization the verified information needed to tailor their role and Portfolio."
                    )
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
        if payload.portfolio_role_approved is not None:
            updates["portfolio_role_approved"] = payload.portfolio_role_approved
            if payload.portfolio_role_approved:
                updates["portfolio_role_approved_at"] = now_iso()
        if payload.portfolio_role_rationale is not None:
            updates["portfolio_role_rationale"] = payload.portfolio_role_rationale
        if payload.background_check is not None:
            check = payload.background_check
            if check.get("status") and check["status"] not in BACKGROUND_STATUSES:
                raise HTTPException(status_code=422, detail="Invalid background check status")
            updates["background_check"] = {k: check.get(k, "") for k in ["required", "requested_date", "completed_date", "status", "notes"]}
        await db.opportunity_applications.update_one({"application_id": application_id}, {"$set": updates})
        return await db.opportunity_applications.find_one({"application_id": application_id}, {"_id": 0, "cv_text": 0})

    @router.post("/applications/{application_id}/references", status_code=201)
    async def add_reference(application_id: str, payload: ReferenceRecord, request: Request):
        member = await selection_member(request)
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
        member = await selection_member(request)
        application = await owned_application(member["user_id"], application_id)
        if not application.get("cv_file_id"):
            if application.get("internal_preview") and application.get("cv_text"):
                filename = (application.get("profile_snapshot", {}).get("full_name") or "Applicant").replace(" ", "-") + "-Preview-CV.txt"
                return StreamingResponse(
                    io.BytesIO(application["cv_text"].encode("utf-8")),
                    media_type="text/plain",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'},
                )
            raise HTTPException(status_code=404, detail="No CV on this application")
        stream = await cv_bucket.open_download_stream(ObjectId(application["cv_file_id"]))
        content = await stream.read()
        return StreamingResponse(io.BytesIO(content), media_type=application.get("cv_content_type", "application/octet-stream"),
                                 headers={"Content-Disposition": f'inline; filename="{application.get("cv_filename", "cv")}"'})

    @router.post("/applications/{application_id}/interview-guide/retry")
    async def retry_guide(application_id: str, request: Request):
        member = await selection_member(request)
        await owned_application(member["user_id"], application_id)
        await run_interview_guide(db, application_id)
        application = await db.opportunity_applications.find_one({"application_id": application_id}, {"_id": 0, "cv_text": 0})
        return {"interview_guide": application.get("interview_guide", {})}

    @router.post("/applications/{application_id}/role-recommendation")
    async def recommend_board_role(application_id: str, request: Request):
        member = await selection_member(request)
        application = await owned_application(member["user_id"], application_id)
        context = await build_org_context(db, member["user_id"], member)
        context += "\n\n" + application_context_text(application)
        if application.get("board_role"):
            context += f"\n\nROLE OR EXPERTISE AREA ORIGINALLY ASSOCIATED WITH THIS CANDIDATE: {application['board_role']}"
        cv_doc = await db.opportunity_applications.find_one(
            {"application_id": application_id}, {"_id": 0, "cv_text": 1})
        if cv_doc and cv_doc.get("cv_text"):
            context += "\n\nCANDIDATE CV / RESUME:\n" + cv_doc["cv_text"][:12000]
        try:
            recommendation = await generate_structured(
                "board_role_recommendation",
                context,
                "Recommend the strongest Board role or contribution focus for this individual. Keep the recommendation practical, specific and editable by the founder.",
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail="The Board role recommendation could not be prepared yet.") from exc
        await db.opportunity_applications.update_one(
            {"application_id": application_id, "owner_user_id": member["user_id"]},
            {"$set": {
                "board_role_recommendation": recommendation,
                "portfolio_role_approved": False,
                "portfolio_role_recommended_at": now_iso(),
                "updated_at": now_iso(),
            }},
        )
        return {"recommendation": recommendation}

    # ---------- Module 6: Signatures ----------
    AGREEMENT_TYPES = {"board_member_agreement", "confidentiality_agreement", "conflict_of_interest_agreement"}

    @router.post("/signatures/prepare", status_code=201)
    async def prepare_signature(payload: SignaturePrepare, request: Request):
        member = await selection_member(request)
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
            raise HTTPException(status_code=409, detail="Generate and save the agreement in the Onboarding step before preparing it for signature")
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
        member = await selection_member(request)
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
        member = await selection_member(request)
        query = {"owner_user_id": member["user_id"]}
        if application_id:
            query["application_id"] = application_id
        records = await db.signature_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
        return {"signatures": records}

    @router.get("/signatures/{request_id}/download")
    async def download_signed(request_id: str, request: Request):
        member = await selection_member(request)
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
