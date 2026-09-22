"""Phase 3 public routes: hosted board application, saved-profile apply tokens, e-signature.
No applicant accounts required. CVs stay private (GridFS only, never public URLs).
"""
import json
import logging
import os
from typing import Optional

import resend
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from pydantic import BaseModel, Field

from ai_service import extract_cv_text
from opportunity_emails import send_application_receipt
from workspace_service import CORE_QUESTIONS, get_current_material, new_id, now_iso
from opportunity_emails import send_signature_confirmations
from reactivation_routes import email_html

logger = logging.getLogger(__name__)

ALLOWED_CV_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_CV_BYTES = 8 * 1024 * 1024


class SignPayload(BaseModel):
    agreed: bool
    typed_signature: str = Field(min_length=2)
    email: str = Field(min_length=3)
    date: str = Field(min_length=4)
    signature_method: str = "typed"
    signature_image: str = ""


def public_opportunity_view(opportunity: dict, board_opportunity_display: str, structured: dict, mission: str = "", board_type: str = "") -> dict:
    org = opportunity["organization_name"]
    board_label = "Advisory Board" if "advisory" in (board_type or "").lower() else "Board of Directors"
    mission_clean = (mission or "").strip().rstrip(".")
    intro_sentences = [f"{org} is recruiting committed professionals to serve on its {board_label}."]
    if mission_clean:
        intro_sentences.append(f"Our mission is {mission_clean}.")
    intro_sentences.append("Complete the application below if you would like to be considered for this opportunity.")
    return {
        "slug": opportunity["slug"], "status": opportunity["status"],
        "organization_name": org,
        "mission": mission,
        "board_label": board_label,
        "intro_sentences": intro_sentences,
        "logo_data": opportunity.get("logo_data", ""),
        "core_questions": CORE_QUESTIONS,
        "custom_questions": opportunity.get("custom_questions", []),
    }


def create_public_opportunity_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/public")
    cv_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="opportunity_cvs")
    resume_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="applicant_resumes")

    async def published_opportunity(slug: str, allow_closed: bool = True) -> dict:
        opportunity = await db.opportunities.find_one({"slug": slug}, {"_id": 0})
        if not opportunity or opportunity["status"] in {"Draft", "Ready to Publish"}:
            raise HTTPException(status_code=404, detail="Board opportunity not found")
        if opportunity["status"] == "Closed" and not allow_closed:
            raise HTTPException(status_code=410, detail="Applications Closed")
        return opportunity

    async def opportunity_content(opportunity: dict):
        material = await db.generated_materials.find_one(
            {"user_id": opportunity["user_id"], "type": "board_opportunity", "application_id": ""}, {"_id": 0})
        if not material:
            return "", {}
        current = next((v for v in material["versions"] if v["version"] == material["current_version"]), {})
        return current.get("display_text", ""), (current.get("structured") or {})

    async def store_cv(cv: UploadFile, application_id: str) -> dict:
        extension = os.path.splitext(cv.filename or "")[1].lower()
        if extension not in ALLOWED_CV_EXTENSIONS:
            raise HTTPException(status_code=400, detail="CV must be a PDF, DOC, or DOCX file.")
        content = await cv.read(MAX_CV_BYTES + 1)
        if len(content) > MAX_CV_BYTES:
            raise HTTPException(status_code=400, detail="CV must be 8 MB or smaller.")
        file_id = await cv_bucket.upload_from_stream(cv.filename, content, metadata={"application_id": application_id})
        return {"cv_file_id": str(file_id), "cv_filename": cv.filename,
                "cv_content_type": cv.content_type or "application/octet-stream",
                "cv_text": extract_cv_text(content, cv.filename)}

    async def create_application(opportunity: dict, source: str, snapshot: dict, answers: dict,
                                 cv_data: dict, background: BackgroundTasks, applicant_id: str = "") -> dict:
        email = (snapshot.get("email") or "").lower()
        duplicate = await db.opportunity_applications.find_one(
            {"opportunity_id": opportunity["opportunity_id"], "applicant_email": email}, {"_id": 0, "application_id": 1})
        if duplicate:
            raise HTTPException(status_code=409, detail="An application from this email has already been submitted for this opportunity")
        ts = now_iso()
        application = {
            "application_id": new_id(), "opportunity_id": opportunity["opportunity_id"],
            "owner_user_id": opportunity["user_id"], "source": source, "applicant_id": applicant_id,
            "applicant_email": email, "profile_snapshot": snapshot, "answers": answers,
            "status": "Applied", "interview_guide": {"status": "Pending"},
            "notes": "", "references": [], "background_check": {"status": "Not started"},
            "created_at": ts, "updated_at": ts, **cv_data,
        }
        await db.opportunity_applications.insert_one(application.copy())
        try:
            await send_application_receipt(email, snapshot.get("full_name", "there"), opportunity["organization_name"])
            await db.opportunity_applications.update_one({"application_id": application["application_id"]}, {"$set": {"receipt_email_status": "Sent"}})
        except Exception as exc:
            await db.opportunity_applications.update_one({"application_id": application["application_id"]}, {"$set": {"receipt_email_status": "Failed", "receipt_email_error": str(exc)[:300]}})
        try:
            owner = await db.members.find_one(
                {"user_id": opportunity["user_id"]}, {"_id": 0, "email": 1, "first_name": 1, "name": 1}) or {}
            owner_email = str(owner.get("email") or "").strip().lower()
            if owner_email:
                owner_name = owner.get("first_name") or str(owner.get("name") or "").split(" ")[0] or "there"
                applicant_name = snapshot.get("full_name") or email
                origin = (os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com").rstrip("/")
                view_url = f"{origin}/app/board-recruitment?application_id={application['application_id']}#br-section-applicants"
                body = (
                    f"Hi {owner_name},\n\n"
                    f"{applicant_name} has completed your Board Member Application Form for {opportunity['organization_name']}.\n\n"
                    "Open their application to review every response and continue the recruitment process.\n\n"
                    "Nonprofit Board Builder"
                )
                resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
                result = await resend.Emails.send_async({
                    "from": os.environ["NONPROFIT_SENDER"], "to": [owner_email],
                    "subject": f"Board Application Received | {applicant_name}",
                    "html": email_html(body, f"VIEW {str(applicant_name).split(' ')[0].upper()}'S APPLICATION", view_url),
                })
                await db.opportunity_applications.update_one(
                    {"application_id": application["application_id"]},
                    {"$set": {"owner_notification_status": "Sent", "owner_notification_email_id": str(getattr(result, "id", ""))}})
        except Exception as exc:
            logger.exception("Recruitment owner notification failed for %s", application["application_id"])
            await db.opportunity_applications.update_one(
                {"application_id": application["application_id"]},
                {"$set": {"owner_notification_status": "Failed", "owner_notification_error": str(exc)[:300]}})
        application.pop("cv_text", None)
        return application

    @router.get("/board-opportunities/{slug}")
    async def view_opportunity(slug: str):
        opportunity = await published_opportunity(slug)
        display, structured = await opportunity_content(opportunity)
        profile = await db.recruitment_profiles.find_one({"user_id": opportunity["user_id"]}, {"_id": 0, "data": 1, "branding": 1})
        data = (profile or {}).get("data", {})
        lead = await db.funnel_leads.find_one({"member_user_id": opportunity["user_id"]}, {"_id": 0, "answers": 1})
        form = (lead or {}).get("answers", {})
        mission = data.get("mission") or form.get("mission") or ""
        board_type = data.get("board_kind") or form.get("board_type") or form.get("board_kind") or ""
        view = public_opportunity_view(opportunity, display, structured, mission, board_type)
        view["logo_data"] = ((profile or {}).get("branding") or {}).get("logo_data", "")
        return view

    @router.post("/board-opportunities/{slug}/apply", status_code=201)
    async def public_apply(slug: str, background: BackgroundTasks, payload: str = Form(...), cv: UploadFile = File(...)):
        opportunity = await published_opportunity(slug, allow_closed=False)
        try:
            answers = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="Invalid application payload") from exc
        missing = [q["label"] for q in CORE_QUESTIONS if q["required"] and not str(answers.get(q["id"], "")).strip()]
        if missing:
            raise HTTPException(status_code=422, detail=f"Required answers missing: {', '.join(missing)}")
        snapshot = {q["id"]: answers.get(q["id"], "") for q in CORE_QUESTIONS[:9]}
        snapshot["full_name"] = answers.get("full_name", "")
        custom_answers = {q["id"]: answers.get(q["id"], "") for q in opportunity.get("custom_questions", [])}
        core_answers = {q["id"]: answers.get(q["id"], "") for q in CORE_QUESTIONS}
        cv_data = await store_cv(cv, "pending")
        application = await create_application(opportunity, "Public Application", snapshot,
                                               {**core_answers, "custom": custom_answers}, cv_data, background)
        return {"application_id": application["application_id"], "status": "Applied",
                "message": "Your Application Has Been Submitted"}

    # ---------- Saved-profile apply tokens ----------
    def applicant_snapshot(applicant: dict) -> dict:
        return {
            "full_name": f"{applicant.get('first_name', '')} {applicant.get('last_name', '')}".strip(),
            "email": applicant.get("email", ""), "phone": applicant.get("phone", ""),
            "city": applicant.get("city", ""), "state_region": applicant.get("state_region", ""),
            "country": applicant.get("country", ""), "profession": applicant.get("job_title", ""),
            "employer": applicant.get("employer", ""), "linkedin": str(applicant.get("linkedin_url") or ""),
        }

    def applicant_answers(applicant: dict) -> dict:
        return {
            "board_experience": f"{applicant.get('previous_board_experience', '')} {applicant.get('board_experience_details', '')}".strip(),
            "why_interested": applicant.get("reason_for_joining", ""),
            "skills_experience": f"{applicant.get('professional_summary', '')} Skills: {', '.join(applicant.get('skills', []))}".strip(),
            "fundraising_support": ", ".join(applicant.get("fundraising_activities", [])),
            "relationships": applicant.get("professional_relationships", ""),
            "monthly_time": applicant.get("monthly_commitment", ""),
            "attend_meetings": applicant.get("commitment_answer", ""),
            "accept_responsibility": applicant.get("commitment_answer", ""),
            "causes": ", ".join(applicant.get("causes", [])),
        }

    async def token_context(token: str):
        record = await db.apply_tokens.find_one({"token": token}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This application link is not valid")
        opportunity = await db.opportunities.find_one({"opportunity_id": record["opportunity_id"]}, {"_id": 0})
        if not opportunity or opportunity["status"] != "Published":
            raise HTTPException(status_code=410, detail="Applications Closed")
        applicant = await db.board_applicants.find_one({"applicant_id": record["applicant_id"]}, {"_id": 0})
        return record, opportunity, applicant

    @router.get("/apply/{token}")
    async def view_apply_token(token: str):
        record, opportunity, applicant = await token_context(token)
        display, structured = await opportunity_content(opportunity)
        already = False
        if applicant:
            already = bool(await db.opportunity_applications.find_one(
                {"opportunity_id": opportunity["opportunity_id"], "applicant_email": applicant["email"]}, {"_id": 0, "application_id": 1}))
        profile = {}
        if applicant:
            profile = {
                "name": f"{applicant.get('first_name', '')} {applicant.get('last_name', '')}".strip(),
                "profession": applicant.get("job_title", ""), "employer": applicant.get("employer", ""),
                "professional_summary": applicant.get("professional_summary", ""),
                "skills": applicant.get("skills", []), "board_experience": applicant.get("previous_board_experience", ""),
                "fundraising_interests": applicant.get("fundraising_activities", []),
                "causes": applicant.get("causes", []),
                "location": f"{applicant.get('city', '')}, {applicant.get('state_region', '')}, {applicant.get('country', '')}",
                "availability": applicant.get("availability", ""),
                "cv_filename": applicant.get("resume_filename", ""),
            }
        return {"opportunity": public_opportunity_view(opportunity, display, structured),
                "profile": profile, "has_profile": bool(applicant), "already_applied": already}

    @router.post("/apply/{token}/confirm", status_code=201)
    async def confirm_saved_application(token: str, background: BackgroundTasks):
        record, opportunity, applicant = await token_context(token)
        if not applicant:
            raise HTTPException(status_code=404, detail="Saved Board Applicant profile not found")
        cv_data = {"cv_file_id": "", "cv_filename": "", "cv_content_type": "", "cv_text": ""}
        if applicant.get("resume_file_id"):
            stream = await resume_bucket.open_download_stream(ObjectId(applicant["resume_file_id"]))
            content = await stream.read()
            file_id = await cv_bucket.upload_from_stream(applicant.get("resume_filename", "cv"), content,
                                                         metadata={"snapshot_of": applicant["resume_file_id"]})
            cv_data = {"cv_file_id": str(file_id), "cv_filename": applicant.get("resume_filename", ""),
                       "cv_content_type": applicant.get("resume_content_type", "application/octet-stream"),
                       "cv_text": extract_cv_text(content, applicant.get("resume_filename", ""))}
        application = await create_application(opportunity, "Board Applicant Network", applicant_snapshot(applicant),
                                               applicant_answers(applicant), cv_data, background, applicant["applicant_id"])
        return {"application_id": application["application_id"],
                "message": "Your Application Has Been Submitted",
                "supporting": f"Your saved professional profile has been submitted to {opportunity['organization_name']} for consideration. Completing an application does not guarantee an interview or board appointment."}

    @router.post("/apply/{token}/apply-updated", status_code=201)
    async def apply_with_updates(token: str, background: BackgroundTasks, payload: str = Form(...),
                                 cv: Optional[UploadFile] = File(None)):
        record, opportunity, applicant = await token_context(token)
        if not applicant:
            raise HTTPException(status_code=404, detail="Saved Board Applicant profile not found")
        try:
            body = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="Invalid payload") from exc
        answers_input = body.get("answers", {})
        snapshot = {**applicant_snapshot(applicant), **{k: v for k, v in answers_input.items() if k in {"full_name", "email", "phone", "city", "state_region", "country", "profession", "employer", "linkedin"} and str(v).strip()}}
        answers = {**applicant_answers(applicant), **{k: v for k, v in answers_input.items() if str(v).strip()}}
        if cv and cv.filename:
            cv_data = await store_cv(cv, "pending")
        elif applicant.get("resume_file_id"):
            stream = await resume_bucket.open_download_stream(ObjectId(applicant["resume_file_id"]))
            content = await stream.read()
            file_id = await cv_bucket.upload_from_stream(applicant.get("resume_filename", "cv"), content, metadata={})
            cv_data = {"cv_file_id": str(file_id), "cv_filename": applicant.get("resume_filename", ""),
                       "cv_content_type": applicant.get("resume_content_type", ""), "cv_text": extract_cv_text(content, applicant.get("resume_filename", ""))}
        else:
            cv_data = {"cv_file_id": "", "cv_filename": "", "cv_content_type": "", "cv_text": ""}
        application = await create_application(opportunity, "Board Applicant Network", snapshot, answers,
                                               cv_data, background, applicant["applicant_id"])
        if body.get("update_profile") is True:
            profile_updates = {}
            mapping = {"phone": "phone", "city": "city", "state_region": "state_region", "profession": "job_title", "employer": "employer", "monthly_time": "monthly_commitment"}
            for source_key, target_key in mapping.items():
                if str(answers_input.get(source_key, "")).strip():
                    profile_updates[target_key] = answers_input[source_key]
            if profile_updates:
                profile_updates["updated_at"] = now_iso()
                await db.board_applicants.update_one({"applicant_id": applicant["applicant_id"]}, {"$set": profile_updates})
        return {"application_id": application["application_id"], "message": "Your Application Has Been Submitted"}

    # ---------- E-signature ----------
    @router.get("/sign/{token}")
    async def view_signature(token: str):
        record = await db.signature_requests.find_one({"token": token}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This signature link is not valid")
        branding = (await db.recruitment_profiles.find_one({"user_id": record["owner_user_id"]}, {"_id": 0, "branding": 1}) or {}).get("branding", {})
        signed = record.get("signed") or {}
        return {"agreement_title": record["agreement_title"], "organization_name": record["organization_name"],
                "board_member_name": record["board_member_name"], "document": record["document_snapshot"],
                "status": record["status"], "signed": bool(record.get("signed")),
                "agreement_version": record.get("agreement_version"),
                "logo_data": branding.get("logo_data", ""), "primary_color": branding.get("primary_color", ""),
                "signed_record": {"name": signed.get("typed_signature", ""), "date": signed.get("date", ""),
                                  "signed_at": signed.get("signed_at", ""), "method": signed.get("method", "typed"),
                                  "signature_image": signed.get("signature_image", "")} if signed else None}

    @router.post("/sign/{token}")
    async def sign_agreement(token: str, payload: SignPayload):
        record = await db.signature_requests.find_one({"token": token}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This signature link is not valid")
        if record["status"] == "Signed":
            raise HTTPException(status_code=409, detail="This agreement has already been signed")
        if not payload.agreed:
            raise HTTPException(status_code=422, detail="You must confirm that you have read and agree to the document")
        method = payload.signature_method if payload.signature_method in {"typed", "drawn", "uploaded"} else "typed"
        if method in {"drawn", "uploaded"} and not payload.signature_image.startswith("data:image"):
            raise HTTPException(status_code=422, detail="Add your signature before submitting, or switch to the typed signature option")
        if len(payload.signature_image) > 300000:
            raise HTTPException(status_code=413, detail="The drawn signature image is too large")
        ts = now_iso()
        signed = {"typed_signature": payload.typed_signature, "email": payload.email.lower(),
                  "date": payload.date, "signed_at": ts, "method": method,
                  "signature_image": payload.signature_image if method in {"drawn", "uploaded"} else ""}
        result = await db.signature_requests.update_one(
            {"token": token, "status": {"$ne": "Signed"}},
            {"$set": {"status": "Signed", "signed": signed, "updated_at": ts}})
        if not result.modified_count:
            raise HTTPException(status_code=409, detail="This agreement has already been signed")
        owner = await db.members.find_one({"user_id": record["owner_user_id"]}, {"_id": 0, "email": 1})
        try:
            await send_signature_confirmations(record["board_member_email"] or payload.email, payload.typed_signature,
                                               (owner or {}).get("email", ""), record["organization_name"], record["agreement_title"])
        except Exception:
            pass
        return {"status": "Signed", "message": "Your signature has been recorded. Both you and the organization will receive a confirmation email."}

    @router.get("/onboarding-session/{token}")
    async def public_onboarding_session(token: str):
        profile = await db.recruitment_profiles.find_one(
            {"onboarding_live.share_token": token},
            {"_id": 0, "user_id": 1, "data.organization_name": 1, "onboarding_live": 1},
        )
        if not profile:
            raise HTTPException(status_code=404, detail="This onboarding session link is not available")
        material = await get_current_material(db, profile["user_id"], "board_manual", "")
        if not material or not material.get("current"):
            raise HTTPException(status_code=404, detail="The Board Member Manual is not available for this onboarding session")
        current = material["current"]
        structured = current.get("structured") or {}
        sections = []
        for index, section in enumerate(structured.get("sections") or [], 1):
            title = str(section.get("title") or f"Onboarding Section {index}").strip()
            content = str(section.get("content") or "").strip()
            if title or content:
                sections.append({"title": title, "content": content})
        if not sections and str(current.get("display_text") or "").strip():
            sections = [{"title": "Board Member Manual", "content": str(current.get("display_text") or "").strip()}]
        live = profile.get("onboarding_live") or {}
        opportunity = await db.opportunities.find_one({"user_id": profile["user_id"]}, {"_id": 0, "organization_name": 1}) or {}
        organization_name = (profile.get("data") or {}).get("organization_name") or opportunity.get("organization_name", "")
        index = min(max(int(live.get("current_section_index") or 0), 0), max(0, len(sections) - 1))
        return {
            "organization_name": organization_name,
            "status": live.get("status", "NOT STARTED"),
            "current_section_index": index,
            "total_sections": len(sections),
            "section": sections[index] if sections else None,
        }

    return router
