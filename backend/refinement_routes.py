"""Recruitment refinement routes: reference-check automation, applicant emails, admin CSV import,
owner review progress, branding settings."""
import csv
import io
import logging
import os
import re
import secrets

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

import resend
from auth_service import authenticate_admin
from ai_service import GENERATION_TYPES, generate_structured
from member_auth import authenticate_member, require_entitlement
from opportunity_emails import _send, _wrap
from workspace_service import get_current_material, new_id, now_iso

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

REFEREE_QUESTIONS = [
    ("capacity", "In what capacity have you known or worked with {candidate}, and approximately how long have you known them?"),
    ("reliability", "Based on your experience working with {candidate}, how would you describe their professionalism, reliability and ability to follow through on responsibilities they accept?"),
    ("strengths", "What strengths have you observed in {candidate} when working with other people, providing leadership, solving problems or contributing to shared goals?"),
    ("teamwork", "Is there anything relevant to {candidate}'s professional conduct, reliability or ability to carry a position of responsibility that you believe we should understand as we consider their Board application?"),
]
RECOMMEND_QUESTION = "Based on your direct experience with {candidate}, would you be comfortable recommending them for a position of responsibility such as nonprofit Board service with {org}? Please briefly explain your answer."
REFEREE_IDENTITY_FIELDS = ["name", "position", "organization", "relationship", "duration"]
RECOMMEND_OPTIONS = ["Yes", "No", "I would need more information to say"]

SENDABLE_TYPES = {"after_interview_thank_you", "before_interview_rejection", "conditional_offer", "unconditional_offer", "onboarding_email", "formal_appointment_email", "portfolio_email", "after_interview_rejection", "general_rejection_email", "interview_invitation"}


class SendCandidateForm(BaseModel):
    application_id: str = Field(min_length=1)
    candidate_email: str = ""
    subject: str = ""
    body: str = ""


class StartReference(BaseModel):
    application_id: str = Field(min_length=1)
    candidate_email: str = ""


class SendMaterial(BaseModel):
    type: str
    application_id: str = Field(min_length=1)
    resend: bool = False


class OnboardingSession(BaseModel):
    date: str = ""
    time: str = ""
    timezone: str = ""
    format: str = ""
    link: str = ""
    location: str = ""
    prepare: str = ""
    status: str = "Scheduled"


class FirstMeetingDetails(BaseModel):
    date: str = ""
    time: str = ""
    timezone: str = ""
    format: str = ""
    link: str = ""
    location: str = ""
    meeting_id: str = ""
    passcode: str = ""
    chat_link: str = ""
    instructions: str = ""


class FirstMeetingSend(BaseModel):
    application_ids: list = Field(min_length=1)
    resend: bool = False


class Branding(BaseModel):
    logo_data: str = ""
    primary_color: str = ""
    secondary_color: str = ""


class ReviewProgress(BaseModel):
    route: str = Field(min_length=1)
    label: str = ""


def create_refinement_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

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

    def origin_of(request: Request) -> str:
        return os.environ.get("PUBLIC_ORIGIN") or request.headers.get("origin") or "https://nonprofitboardbuilder.com"

    async def org_name_of(user_id: str) -> str:
        opportunity = await db.opportunities.find_one({"user_id": user_id}, {"_id": 0, "organization_name": 1})
        return (opportunity or {}).get("organization_name", "the organization")

    async def notify_owner(user_id: str, subject: str, body_html: str, title: str):
        owner = await db.members.find_one({"user_id": user_id}, {"_id": 0, "email": 1})
        if owner and owner.get("email"):
            try:
                await _send("NONPROFIT_SENDER", owner["email"], subject, _wrap(title, body_html))
            except Exception:
                logger.exception("Owner notification failed")

    # ---------- Reference process ----------
    @router.post("/workspace/reference-process", status_code=201)
    async def start_reference_process(payload: StartReference, request: Request):
        member = await selection_member(request)
        application = await owned_application(member["user_id"], payload.application_id)
        existing = await db.reference_processes.find_one(
            {"owner_user_id": member["user_id"], "application_id": payload.application_id}, {"_id": 0})
        if existing:
            return existing

        email = (payload.candidate_email or application.get("applicant_email") or "").strip().lower()
        extracted_email = ""
        if not email and application.get("cv_text"):
            match = EMAIL_RE.search(application["cv_text"])
            extracted_email = match.group(0).lower() if match else ""

        extracted_references = []
        cv_text = (application.get("cv_text") or "").strip()
        if cv_text:
            try:
                extracted = await generate_structured(
                    "cv_reference_extraction",
                    "CANDIDATE CV / RESUME:\n" + cv_text[:16000],
                    "Extract only people explicitly identified as professional references/referees. Never infer a referee from employment history.",
                )
                for item in (extracted.get("references") or [])[:2]:
                    name = str(item.get("name") or "").strip()
                    if not name:
                        continue
                    referee_email = str(item.get("email") or "").strip().lower()
                    extracted_references.append({
                        "reference_id": new_id(),
                        "referee_token": secrets.token_urlsafe(24),
                        "name": name[:200],
                        "position": str(item.get("position") or "")[:200],
                        "organization": str(item.get("organization") or "")[:200],
                        "relationship": str(item.get("relationship") or "")[:300],
                        "duration": str(item.get("duration") or "")[:200],
                        "email": referee_email if EMAIL_RE.fullmatch(referee_email or "") else "",
                        "phone": str(item.get("phone") or "")[:50],
                        "status": "Ready to Contact" if EMAIL_RE.fullmatch(referee_email or "") else "Needs Contact Details",
                        "response": None,
                        "source": "CV",
                    })
            except Exception:
                logger.exception("CV reference extraction failed for %s", payload.application_id)

        process_status = "References Found in CV" if extracted_references else "Not Started"
        process = {
            "process_id": new_id(),
            "owner_user_id": member["user_id"],
            "application_id": payload.application_id,
            "candidate_name": application.get("profile_snapshot", {}).get("full_name", ""),
            "candidate_email": email,
            "extracted_email": extracted_email,
            "candidate_token": secrets.token_urlsafe(24),
            "status": process_status,
            "references": extracted_references,
            "reference_source": "cv" if extracted_references else "",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        await db.reference_processes.insert_one(process.copy())
        await db.opportunity_applications.update_one(
            {"application_id": payload.application_id},
            {"$set": {"reference_check_status": process_status, "updated_at": now_iso()}},
        )
        return process

    @router.get("/workspace/reference-process/{application_id}")
    async def get_reference_process(application_id: str, request: Request):
        member = await selection_member(request)
        process = await db.reference_processes.find_one(
            {"owner_user_id": member["user_id"], "application_id": application_id}, {"_id": 0})
        return {"process": process}

    @router.post("/workspace/reference-process/{application_id}/send")
    async def send_candidate_form(application_id: str, payload: SendCandidateForm, request: Request):
        member = await selection_member(request)
        process = await db.reference_processes.find_one(
            {"owner_user_id": member["user_id"], "application_id": application_id}, {"_id": 0})
        if not process:
            raise HTTPException(status_code=404, detail="Start the reference check first")
        email = (payload.candidate_email or process.get("candidate_email") or "").strip().lower()
        if not EMAIL_RE.fullmatch(email or ""):
            raise HTTPException(status_code=422, detail="Confirm or enter a valid candidate email address before sending")
        opportunity = await db.opportunities.find_one({"user_id": member["user_id"]}, {"_id": 0, "organization_name": 1})
        org = (opportunity or {}).get("organization_name", "the organization")
        url = f"{origin_of(request)}/reference-form/{process['candidate_token']}"
        subject = payload.subject.strip() or f"Reference Information Needed | {org} Board Application"
        if payload.body.strip():
            import html as _html
            paragraphs = "".join(f"<p>{_html.escape(line)}</p>" if line.strip() else "<br/>" for line in payload.body.split("\n"))
            body = paragraphs + f"<p><a href='{url}' style='display:inline-block;background:#087e5b;color:#fff;padding:13px 22px;border-radius:6px;text-decoration:none;font-weight:bold;'>Provide My References</a></p>"
        else:
            body = (f"<p>Dear {process.get('candidate_name') or 'there'},</p>"
                    f"<p>Thank you for continuing through the board recruitment process with {org}. As part of completing our reference process, please provide two professional references using the secure form below.</p>"
                    f"<p><a href='{url}' style='display:inline-block;background:#087e5b;color:#fff;padding:13px 22px;border-radius:6px;text-decoration:none;font-weight:bold;'>Provide My References</a></p>"
                    f"<p>Once your references are submitted, {org} will contact each reference directly.</p>"
                    f"<p>Thank you for your continued interest in serving with us.</p>")
        try:
            await _send("BOARD_APPLICANT_SENDER", email, subject, _wrap("Reference Information Requested", body))
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"The email could not be sent: {str(exc)[:200]}") from exc
        await db.reference_processes.update_one({"process_id": process["process_id"]},
            {"$set": {"candidate_email": email, "status": "Waiting for Candidate", "candidate_sent_at": now_iso(),
                      "candidate_sent_to": email, "updated_at": now_iso()}})
        await db.opportunity_applications.update_one(
            {"application_id": application_id},
            {"$set": {"applicant_email": email, "profile_snapshot.email": email,
                      "reference_check_status": "Waiting for Candidate", "updated_at": now_iso()}})
        return {"status": "Waiting for Candidate", "sent_to": email}

    @router.post("/workspace/reference-process/{application_id}/resend-referee/{reference_id}")
    async def resend_referee(application_id: str, reference_id: str, request: Request):
        member = await selection_member(request)
        process = await db.reference_processes.find_one(
            {"owner_user_id": member["user_id"], "application_id": application_id}, {"_id": 0})
        if not process:
            raise HTTPException(status_code=404, detail="Reference process not found")
        reference = next((r for r in process["references"] if r["reference_id"] == reference_id), None)
        if not reference:
            raise HTTPException(status_code=404, detail="Reference not found")
        await email_referee(request, process, reference)
        return {"status": "Sent"}

    async def email_referee(request: Request, process: dict, reference: dict):
        referee_email = str(reference.get("email") or "").strip().lower()
        if not EMAIL_RE.fullmatch(referee_email or ""):
            raise HTTPException(status_code=422, detail="This referee does not have a valid email address yet. Ask the applicant to confirm or complete their reference details first.")
        org = await org_name_of(process["owner_user_id"])
        candidate = process.get("candidate_name") or "A candidate"
        url = f"{origin_of(request)}/referee-form/{reference['referee_token']}"
        first_name = (reference.get("name") or "").split(" ")[0] or "there"
        body = (f"<p>Dear {first_name},</p>"
                f"<p>{candidate} has listed you as a professional reference as part of their application to serve on the Board of {org}.</p>"
                f"<p>{org} is completing its board recruitment process and would appreciate your perspective based on your experience with {candidate}. The questionnaire contains five short questions.</p>"
                f"<p><a href='{url}' style='display:inline-block;background:#087e5b;color:#fff;padding:13px 22px;border-radius:6px;text-decoration:none;font-weight:bold;'>Provide Reference</a></p>"
                f"<p>Your response will be shared with the organization reviewing the candidate.</p>"
                f"<p>Thank you for your time.</p>")
        await _send("BOARD_APPLICANT_SENDER", referee_email, f"Reference Request | {candidate} — {org} Board Application", _wrap("Reference Request", body))
        await db.reference_processes.update_one(
            {"process_id": process["process_id"], "references.reference_id": reference["reference_id"]},
            {"$set": {"references.$.status": "Sent", "references.$.sent_at": now_iso(), "updated_at": now_iso()}})
        current = await db.reference_processes.find_one({"process_id": process["process_id"]}, {"_id": 0, "status": 1})
        if current and current["status"] not in {"Completed"}:
            await db.reference_processes.update_one({"process_id": process["process_id"]}, {"$set": {"status": "In Progress"}})
            await db.opportunity_applications.update_one({"application_id": process["application_id"]},
                {"$set": {"reference_check_status": "In Progress"}})

    # ---------- Public candidate + referee forms ----------
    @router.get("/public/reference-form/{token}")
    async def view_candidate_form(token: str):
        process = await db.reference_processes.find_one({"candidate_token": token}, {"_id": 0, "candidate_name": 1, "status": 1, "references": 1})
        if not process:
            raise HTTPException(status_code=404, detail="This form is not available")
        return {"candidate_name": process["candidate_name"], "submitted": bool(process.get("references"))}

    @router.post("/public/reference-form/{token}", status_code=201)
    async def submit_candidate_form(token: str, payload: dict, request: Request):
        process = await db.reference_processes.find_one({"candidate_token": token}, {"_id": 0})
        if not process:
            raise HTTPException(status_code=404, detail="This form is not available")
        existing_references = process.get("references") or []
        contacted = any(item.get("status") in {"Sent", "Completed"} for item in existing_references)
        if existing_references and process.get("reference_source") != "cv":
            raise HTTPException(status_code=409, detail="References have already been provided")
        if existing_references and process.get("reference_source") == "cv" and contacted:
            raise HTTPException(status_code=409, detail="Reference confirmation is already in progress. Contact the organization if reference details need to change.")
        if not payload.get("permission_confirmed"):
            raise HTTPException(status_code=422, detail="Please confirm you have permission to share the referees' contact information")
        references = []
        for entry in (payload.get("references") or [])[:2]:
            email = str(entry.get("email", "")).strip().lower()
            if not str(entry.get("name", "")).strip() or not EMAIL_RE.fullmatch(email or ""):
                raise HTTPException(status_code=422, detail="Each reference needs a full name and a valid email address")
            references.append({
                "reference_id": new_id(), "referee_token": secrets.token_urlsafe(24),
                "name": str(entry.get("name", ""))[:200], "position": str(entry.get("position", ""))[:200],
                "organization": str(entry.get("organization", ""))[:200], "relationship": str(entry.get("relationship", ""))[:300],
                "email": email, "phone": str(entry.get("phone", ""))[:50], "duration": str(entry.get("duration", ""))[:200],
                "status": "Ready to Contact", "response": None,
            })
        if len(references) != 2:
            raise HTTPException(status_code=422, detail="Please provide two references")
        await db.reference_processes.update_one({"candidate_token": token},
            {"$set": {"references": references, "reference_source": "candidate", "status": "References Submitted", "references_submitted_at": now_iso(), "updated_at": now_iso()}})
        await db.opportunity_applications.update_one({"application_id": process["application_id"]},
            {"$set": {"reference_check_status": "References Submitted"}})
        candidate = process.get("candidate_name") or "Your candidate"
        review_url = f"{origin_of(request)}/app/board-recruitment#br-section-references"
        await notify_owner(process["owner_user_id"], f"References Submitted | {candidate}",
                           f"<p><strong>{candidate}</strong> has submitted their reference information.</p>"
                           f"<p>Review who they listed, then email each reference for confirmation when you are ready — nothing is sent to the references until you choose to contact them.</p>"
                           f"<p><a href='{review_url}' style='display:inline-block;background:#087e5b;color:#fff;padding:13px 22px;border-radius:6px;text-decoration:none;font-weight:bold;'>Review References</a></p>",
                           "References Submitted")
        return {"status": "submitted", "message": "Thank you. Your references have been recorded and shared with the organization."}

    @router.get("/public/referee-form/{token}")
    async def view_referee_form(token: str):
        process = await db.reference_processes.find_one({"references.referee_token": token}, {"_id": 0, "candidate_name": 1, "references": 1, "owner_user_id": 1})
        if not process:
            raise HTTPException(status_code=404, detail="This form is not available")
        reference = next(r for r in process["references"] if r["referee_token"] == token)
        org = await org_name_of(process["owner_user_id"])
        candidate = process["candidate_name"]
        return {"candidate_name": candidate, "referee_name": reference["name"], "organization_name": org,
                "completed": reference["status"] == "Completed",
                "identity": {field: reference.get(field, "") for field in REFEREE_IDENTITY_FIELDS},
                "questions": [{"id": qid, "label": label.format(candidate=candidate, org=org)} for qid, label in REFEREE_QUESTIONS],
                "recommend_question": RECOMMEND_QUESTION.format(candidate=candidate, org=org),
                "recommend_options": RECOMMEND_OPTIONS}

    @router.post("/public/referee-form/{token}", status_code=201)
    async def submit_referee_form(token: str, payload: dict, request: Request):
        process = await db.reference_processes.find_one({"references.referee_token": token}, {"_id": 0})
        if not process:
            raise HTTPException(status_code=404, detail="This form is not available")
        reference = next(r for r in process["references"] if r["referee_token"] == token)
        if reference["status"] == "Completed":
            raise HTTPException(status_code=409, detail="This reference has already been completed")
        missing = [label for qid, label in REFEREE_QUESTIONS if not str(payload.get(qid, "")).strip()]
        if missing:
            raise HTTPException(status_code=422, detail="Please answer every question.")
        if payload.get("recommend") not in RECOMMEND_OPTIONS:
            raise HTTPException(status_code=422, detail="Please choose Yes, No, or I would need more information to say")
        explanation = str(payload.get("explanation", "") or payload.get("comments", "")).strip()
        if not explanation:
            raise HTTPException(status_code=422, detail="Please explain your response to the final question")
        if not payload.get("declaration_confirmed"):
            raise HTTPException(status_code=422, detail="Please confirm that the information you provided reflects your own experience and knowledge of the candidate")
        response = {qid: str(payload.get(qid, ""))[:4000] for qid, _ in REFEREE_QUESTIONS}
        response["recommend"] = payload["recommend"]
        response["explanation"] = explanation[:4000]
        identity = {field: str(payload.get(f"identity_{field}", reference.get(field, "")))[:300] for field in REFEREE_IDENTITY_FIELDS}
        await db.reference_processes.update_one(
            {"process_id": process["process_id"], "references.referee_token": token},
            {"$set": {"references.$.status": "Completed", "references.$.response": response,
                      **{f"references.$.{field}": value for field, value in identity.items()},
                      "references.$.completed_at": now_iso(), "updated_at": now_iso()}})
        remaining = [r for r in process["references"] if r["referee_token"] != token and r["status"] != "Completed"]
        if not remaining:
            await db.reference_processes.update_one({"process_id": process["process_id"]}, {"$set": {"status": "Completed"}})
            await db.opportunity_applications.update_one({"application_id": process["application_id"]},
                {"$set": {"reference_check_status": "Completed"}})
        candidate = process.get("candidate_name") or "your candidate"
        review_url = f"{origin_of(request)}/app/board-recruitment#br-section-references"
        await notify_owner(process["owner_user_id"], f"Reference Received | {candidate}",
                           f"<p>A reference response has been received for <strong>{candidate}</strong> from <strong>{identity.get('name') or reference['name']}</strong>.</p>"
                           f"<p><a href='{review_url}' style='display:inline-block;background:#087e5b;color:#fff;padding:13px 22px;border-radius:6px;text-decoration:none;font-weight:bold;'>Review Reference</a></p>",
                           "Reference Received")
        return {"status": "submitted", "message": "Thank you. Your reference has been submitted."}

    # ---------- Send generated applicant emails ----------
    @router.post("/workspace/send-material")
    async def send_material_email(payload: SendMaterial, request: Request):
        member = await current_member(request)
        if payload.type not in SENDABLE_TYPES:
            raise HTTPException(status_code=422, detail="This material cannot be emailed")
        application = await owned_application(member["user_id"], payload.application_id)
        email = (application.get("applicant_email") or "").strip().lower()
        if not EMAIL_RE.fullmatch(email or ""):
            raise HTTPException(status_code=422, detail="Add the applicant's email address before sending")
        material = await get_current_material(db, member["user_id"], payload.type, payload.application_id)
        if not material or not material["current"]:
            raise HTTPException(status_code=409, detail="Generate and save this email first")
        already = (application.get("emails_sent") or {}).get(payload.type)
        if already and not payload.resend:
            raise HTTPException(status_code=409, detail=f"This email was already sent on {already}. Use Send Updated to deliberately send again.")
        structured = material["current"].get("structured") or {}
        subject = structured.get("subject") or GENERATION_TYPES[payload.type]["title"]
        body_text = structured.get("body") or material["current"]["display_text"]
        if payload.type == "portfolio_email":
            portfolio = await get_current_material(db, member["user_id"], "board_member_portfolio", payload.application_id)
            if portfolio and portfolio["current"]:
                body_text += "\n\n----------------------------\n" + portfolio["current"]["display_text"]
        import html as _html
        def email_line(line: str) -> str:
            escaped = _html.escape(line)
            linked = re.sub(r"(https?://[^\s]+)", r'<a href="\1">\1</a>', escaped)
            return f"<p>{linked}</p>" if line.strip() else "<br/>"
        html_body = "".join(email_line(line) for line in body_text.split("\n"))
        try:
            await _send("NONPROFIT_SENDER", email, subject, _wrap(subject, html_body))
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"The email could not be sent: {str(exc)[:200]}") from exc
        updates = {f"emails_sent.{payload.type}": now_iso(), "updated_at": now_iso()}
        if payload.type == "interview_invitation" and application.get("status") in {"Applied", "Reviewing", "New"}:
            updates["status"] = "Interview Invited"
        if payload.type == "before_interview_rejection":
            updates["status"] = "Not Moving to Interview"
        if payload.type == "conditional_offer" and application.get("status") not in {"Selected"}:
            updates["status"] = "Conditional Appointment"
            updates["appointment_offer_type"] = "Conditional"
        if payload.type == "unconditional_offer":
            updates["appointment_offer_type"] = "Unconditional"
            updates["appointment_offer_sent_at"] = now_iso()
        if payload.type == "onboarding_email":
            updates["onboarding_email_sent_at"] = now_iso()
        if payload.type == "formal_appointment_email":
            updates["status"] = "Selected"
            updates["final_outcome"] = "Joined Board"
            updates["formal_appointment_date"] = now_iso()
        await db.opportunity_applications.update_one(
            {"application_id": payload.application_id}, {"$set": updates})
        return {"status": "Sent", "to": email}

    # ---------- Onboarding session ----------
    @router.get("/workspace/onboarding-session")
    async def get_onboarding_session(request: Request):
        member = await selection_member(request)
        profile = await db.recruitment_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "onboarding_session": 1})
        return {"session": (profile or {}).get("onboarding_session", {})}

    @router.put("/workspace/onboarding-session")
    async def save_onboarding_session(payload: OnboardingSession, request: Request):
        member = await selection_member(request)
        session = payload.model_dump()
        if session.get("status") == "Completed":
            session["completed_at"] = now_iso()
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"onboarding_session": session, "updated_at": now_iso()}}, upsert=True)
        return {"status": "saved", "session": session}

    # ---------- Live onboarding facilitation ----------
    async def onboarding_manual(user_id: str) -> dict:
        material = await get_current_material(db, user_id, "board_manual", "")
        if not material or not material.get("current"):
            raise HTTPException(status_code=409, detail="Generate the Board Member Manual before starting the live onboarding session")
        if material["material"].get("status") != "Approved":
            raise HTTPException(status_code=409, detail="Approve the Board Member Manual before starting the live onboarding session")
        current = material["current"]
        structured = current.get("structured") or {}
        sections = []
        for index, section in enumerate(structured.get("sections") or [], 1):
            title = str(section.get("title") or f"Onboarding Section {index}").strip()
            content = str(section.get("content") or "").strip()
            if title or content:
                sections.append({"index": index - 1, "title": title, "content": content})
        if not sections and str(current.get("display_text") or "").strip():
            sections = [{"index": 0, "title": "Board Member Manual", "content": str(current.get("display_text") or "").strip()}]
        if not sections:
            raise HTTPException(status_code=409, detail="The approved Board Member Manual does not contain onboarding content yet")
        return {"sections": sections, "material_id": material["material"].get("material_id", "")}

    @router.get("/workspace/onboarding-live")
    async def get_live_onboarding(request: Request):
        member = await selection_member(request)
        manual = await onboarding_manual(member["user_id"])
        profile = await db.recruitment_profiles.find_one(
            {"user_id": member["user_id"]}, {"_id": 0, "data.organization_name": 1, "onboarding_live": 1}
        ) or {}
        session = profile.get("onboarding_live") or {}
        return {
            "organization_name": (profile.get("data") or {}).get("organization_name", ""),
            "session": session,
            "sections": manual["sections"],
            "manual_material_id": manual["material_id"],
        }

    @router.post("/workspace/onboarding-live/share")
    async def create_live_onboarding_share(request: Request):
        member = await selection_member(request)
        manual = await onboarding_manual(member["user_id"])
        profile = await db.recruitment_profiles.find_one(
            {"user_id": member["user_id"]}, {"_id": 0, "onboarding_live": 1}
        ) or {}
        existing = profile.get("onboarding_live") or {}
        token = existing.get("share_token") or secrets.token_urlsafe(32)
        session = {
            **existing,
            "share_token": token,
            "manual_material_id": manual["material_id"],
            "current_section_index": int(existing.get("current_section_index") or 0),
            "status": existing.get("status") if existing.get("status") in {"IN PROGRESS", "COMPLETED"} else "NOT STARTED",
            "updated_at": now_iso(),
        }
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"onboarding_live": session, "updated_at": now_iso()}},
            upsert=True,
        )
        return {"share_token": token, "status": session["status"]}

    @router.post("/workspace/onboarding-live/start")
    async def start_live_onboarding(request: Request):
        member = await selection_member(request)
        manual = await onboarding_manual(member["user_id"])
        profile = await db.recruitment_profiles.find_one(
            {"user_id": member["user_id"]}, {"_id": 0, "onboarding_live": 1}
        ) or {}
        existing = profile.get("onboarding_live") or {}
        if not existing.get("share_token"):
            raise HTTPException(status_code=409, detail="Create the shared onboarding screen link first")
        session = {
            **existing,
            "manual_material_id": manual["material_id"],
            "status": "IN PROGRESS",
            "current_section_index": min(int(existing.get("current_section_index") or 0), max(0, len(manual["sections"]) - 1)),
            "started_at": existing.get("started_at") or now_iso(),
            "updated_at": now_iso(),
        }
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"onboarding_live": session, "updated_at": now_iso()}},
            upsert=True,
        )
        return {"status": "IN PROGRESS"}

    @router.post("/workspace/onboarding-live/progress")
    async def update_live_onboarding_progress(request: Request):
        member = await selection_member(request)
        manual = await onboarding_manual(member["user_id"])
        body = await request.json()
        index = max(0, min(int(body.get("current_section_index", 0)), len(manual["sections"]) - 1))
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {
                "onboarding_live.current_section_index": index,
                "onboarding_live.status": "IN PROGRESS",
                "onboarding_live.updated_at": now_iso(),
                "updated_at": now_iso(),
            }},
            upsert=True,
        )
        return {"current_section_index": index}

    @router.post("/workspace/onboarding-live/complete")
    async def complete_live_onboarding(request: Request):
        member = await selection_member(request)
        # Deliberately does not change appointment status or onboarding-conclusion readiness.
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {
                "onboarding_live.status": "COMPLETED",
                "onboarding_live.completed_at": now_iso(),
                "onboarding_live.updated_at": now_iso(),
                "updated_at": now_iso(),
            }},
            upsert=True,
        )
        return {"status": "COMPLETED"}

    # ---------- First board meeting invitation send ----------
    @router.put("/workspace/first-meeting")
    async def save_first_meeting(payload: FirstMeetingDetails, request: Request):
        member = await selection_member(request)
        if not payload.date.strip() or not payload.time.strip() or not payload.timezone.strip():
            raise HTTPException(status_code=422, detail="Meeting date, time and timezone are required")
        await db.recruitment_profiles.update_one({"user_id": member["user_id"]},
            {"$set": {"first_meeting": payload.model_dump(), "updated_at": now_iso()}}, upsert=True)
        return {"status": "saved"}

    @router.get("/workspace/first-meeting")
    async def get_first_meeting(request: Request):
        member = await selection_member(request)
        profile = await db.recruitment_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "first_meeting": 1})
        return {"first_meeting": (profile or {}).get("first_meeting", {})}

    @router.post("/workspace/send-first-meeting")
    async def send_first_meeting(payload: FirstMeetingSend, request: Request):
        member = await selection_member(request)
        material = await get_current_material(db, member["user_id"], "first_board_meeting_invitation", "")
        if not material or not material["current"]:
            raise HTTPException(status_code=409, detail="Generate and save the First Board Meeting Invitation first")
        profile = await db.recruitment_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "first_meeting_sent": 1})
        if (profile or {}).get("first_meeting_sent") and not payload.resend:
            raise HTTPException(status_code=409, detail=f"The invitation was already sent on {profile['first_meeting_sent']['sent_at']}. Use Send Updated Meeting Information to deliberately send again.")
        structured = material["current"].get("structured") or {}
        subject = structured.get("subject") or "Your First Board Meeting"
        body_text = structured.get("body") or material["current"]["display_text"]
        import html as _html
        html_body = "".join(f"<p>{_html.escape(line)}</p>" if line.strip() else "<br/>" for line in body_text.split("\n"))
        sent, failures = [], []
        for application_id in payload.application_ids[:30]:
            application = await db.opportunity_applications.find_one(
                {"application_id": application_id, "owner_user_id": member["user_id"], "final_outcome": "Joined Board"}, {"_id": 0})
            if not application:
                failures.append(application_id)
                continue
            email = (application.get("applicant_email") or "").strip().lower()
            if not EMAIL_RE.fullmatch(email or ""):
                failures.append(application.get("profile_snapshot", {}).get("full_name", application_id))
                continue
            try:
                await _send("NONPROFIT_SENDER", email, subject, _wrap(subject, html_body))
                sent.append(email)
                await db.opportunity_applications.update_one({"application_id": application_id},
                    {"$set": {"emails_sent.first_board_meeting_invitation": now_iso()}})
            except Exception:
                failures.append(email)
        await db.recruitment_profiles.update_one({"user_id": member["user_id"]},
            {"$set": {"first_meeting_sent": {"sent_at": now_iso(), "recipients": sent}}}, upsert=True)
        return {"status": "Sent", "sent": sent, "failures": failures}

    # ---------- Branding ----------
    @router.put("/workspace/branding")
    async def save_branding(payload: Branding, request: Request):
        member = await current_member(request)
        if payload.logo_data and len(payload.logo_data) > 700000:
            raise HTTPException(status_code=413, detail="Logo image is too large (500KB maximum)")
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"branding": payload.model_dump(), "updated_at": now_iso()}}, upsert=True)
        return {"status": "saved"}

    @router.get("/workspace/branding")
    async def get_branding(request: Request):
        member = await current_member(request)
        profile = await db.recruitment_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "branding": 1})
        return {"branding": (profile or {}).get("branding", {})}

    # ---------- Admin CSV import into existing Board Applicant Network ----------
    @router.post("/admin/applicants-import")
    async def import_applicants(request: Request, file: UploadFile = File(...), confirmed: str = "false", commit: str = "true"):
        await authenticate_admin(request, db)
        if confirmed.lower() != "true":
            raise HTTPException(status_code=422, detail="Confirm you have permission to contact these people before importing")
        commit_flag = commit.lower() == "true"
        content = (await file.read()).decode("utf-8-sig", errors="ignore")
        reader = csv.DictReader(io.StringIO(content))
        mapping = {"email": ["email", "subscriber", "email address"], "first_name": ["first name", "firstname", "first"],
                   "last_name": ["last name", "lastname", "last"], "phone": ["phone", "phone number"],
                   "city": ["city"], "state_region": ["state", "state/region", "region"], "country": ["country"],
                   "linkedin_url": ["linkedin", "linkedin url"], "job_title": ["professional title", "job title", "title"],
                   "employer": ["employer", "organization", "company"], "location": ["location"], "source": ["source"]}
        headers = {h.lower().strip(): h for h in (reader.fieldnames or [])}
        def col(field):
            for candidate in mapping[field]:
                if candidate in headers:
                    return headers[candidate]
            return None
        email_col = col("email")
        if not email_col:
            raise HTTPException(status_code=422, detail="The CSV must contain an Email (or Subscriber) column")
        summary = {"imported": 0, "updated": 0, "skipped_duplicate": 0, "skipped_invalid_email": 0, "skipped_unsubscribed": 0, "failed": 0, "resend_synced": 0}
        sample = []
        seen = set()
        for row in reader:
            email = str(row.get(email_col, "")).strip().lower()
            if not EMAIL_RE.fullmatch(email or ""):
                summary["skipped_invalid_email"] += 1
                continue
            if email in seen:
                summary["skipped_duplicate"] += 1
                continue
            seen.add(email)
            existing = await db.board_applicants.find_one({"email": email}, {"_id": 0})
            if existing and existing.get("status") in {"Withdrawn", "Unsubscribed"}:
                summary["skipped_unsubscribed"] += 1
                continue
            if not commit_flag:
                if len(sample) < 5:
                    sample.append(email)
                if existing:
                    summary["updated"] += 1
                else:
                    summary["imported"] += 1
                continue
            values = {}
            for field in ["first_name", "last_name", "phone", "city", "state_region", "country", "linkedin_url", "job_title", "employer", "source"]:
                header = col(field)
                if header and str(row.get(header, "")).strip():
                    values[field] = str(row[header]).strip()[:300]
            location_header = col("location")
            if location_header and str(row.get(location_header, "")).strip() and not values.get("city"):
                values["city"] = str(row[location_header]).strip()[:300]
            try:
                if existing:
                    updates = {k: v for k, v in values.items() if v and not existing.get(k)}
                    if updates:
                        updates["updated_at"] = now_iso()
                        await db.board_applicants.update_one({"email": email}, {"$set": updates})
                        summary["updated"] += 1
                    else:
                        summary["skipped_duplicate"] += 1
                    record = {**existing, **updates} if updates else existing
                else:
                    ts = now_iso()
                    record = {
                        "applicant_id": new_id(), "email": email,
                        "first_name": values.get("first_name", ""), "last_name": values.get("last_name", ""),
                        "phone": values.get("phone", ""), "city": values.get("city", ""),
                        "state_region": values.get("state_region", ""), "country": values.get("country", ""),
                        "job_title": values.get("job_title", ""), "employer": values.get("employer", ""),
                        "professional_field": "", "skills": [], "causes": [], "board_types": [],
                        "geographic_preferences": [], "participation_preferences": [], "availability": "",
                        "fundraising_activities": [], "linkedin_url": values.get("linkedin_url", ""),
                        "status": "Active", "source": values.get("source", "Admin CSV Import"),
                        "board_opportunity_consent": True, "resend_contact_id": "",
                        "resend_segment_status": "Pending", "created_at": ts, "updated_at": ts,
                    }
                    await db.board_applicants.insert_one(record.copy())
                    summary["imported"] += 1
                # gentle Resend sync: never flips unsubscribed back on
                try:
                    resend.api_key = os.environ["RESEND_API_KEY"]
                    contact_id = ""
                    unsubscribed = False
                    try:
                        contact = await resend.Contacts.get_async(email=email)
                        contact_id = contact.get("id") if isinstance(contact, dict) else getattr(contact, "id", "")
                        unsubscribed = bool(contact.get("unsubscribed") if isinstance(contact, dict) else getattr(contact, "unsubscribed", False))
                    except Exception:
                        created = await resend.Contacts.create_async({"email": email, "first_name": record.get("first_name", ""), "last_name": record.get("last_name", "")})
                        contact_id = created.get("id") if isinstance(created, dict) else getattr(created, "id", "")
                    if unsubscribed:
                        summary["skipped_unsubscribed"] += 1
                    else:
                        await resend.ContactSegments.add_async({"segment_id": os.environ["RESEND_BOARD_APPLICANTS_SEGMENT_ID"], "email": email})
                        await db.board_applicants.update_one({"email": email}, {"$set": {"resend_contact_id": contact_id, "resend_segment_status": "Synced"}})
                        summary["resend_synced"] += 1
                except Exception:
                    await db.board_applicants.update_one({"email": email}, {"$set": {"resend_segment_status": "Failed"}})
            except Exception:
                summary["failed"] += 1
        return {"summary": summary, "preview": not commit_flag, "sample": sample}

    # ---------- Strategy PDF + Module 5 decision ----------
    @router.get("/workspace/strategy-pdf")
    async def strategy_pdf(request: Request):
        from fastapi.responses import Response
        from ai_service import STRATEGY_TIMELINE_TEXT, STRATEGY_ROADMAP_TEXT, STRATEGY_NEXT_STEP_TEXT
        from document_renderer import render_document_pdf, material_created_by
        member = await current_member(request)
        material = await db.generated_materials.find_one({"user_id": member["user_id"], "type": "recruitment_strategy", "application_id": ""}, {"_id": 0})
        if not material:
            raise HTTPException(status_code=404, detail="Generate your Recruitment Strategy first")
        structured = next((v.get("structured") for v in reversed(material["versions"]) if v.get("structured")), {}) or {}
        profile = await db.recruitment_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "branding": 1})
        branding = (profile or {}).get("branding", {})
        created_by = await material_created_by(db, member["user_id"])
        parts = []
        if structured.get("executive_summary"):
            parts += ["EXECUTIVE SUMMARY", structured["executive_summary"], ""]
        parts.append("1. BOARD MEMBERS WE ARE RECRUITING")
        for role in structured.get("roles", [])[:5]:
            parts.append(f"- {role.get('role_name', '')} — {role.get('person_sought', '')}")
        parts += ["", "2. RECRUITMENT CHANNELS"]
        for entry in structured.get("channels", []):
            parts += [str(entry.get("channel", "")).upper(), entry.get("approach", ""), ""]
        parts.append("3. SELECTION CRITERIA")
        for criterion in structured.get("selection_criteria", []):
            parts.append(f"- {criterion}")
        for block, block_title in [(STRATEGY_TIMELINE_TEXT, "4. RECRUITMENT TIMELINE"), (STRATEGY_ROADMAP_TEXT, "5. YOUR RECRUITMENT EXECUTION ROADMAP"), (STRATEGY_NEXT_STEP_TEXT, "YOUR NEXT STEP")]:
            parts += ["", block_title]
            for paragraph in block.split("\n\n")[1:]:
                if paragraph.strip():
                    parts += [paragraph, ""]
        pdf = render_document_pdf(title="Board Recruitment Strategy", org_name=created_by["organization"],
                                  body_text="\n".join(parts), branding=branding, created_by=created_by)
        return Response(content=pdf, media_type="application/pdf",
                        headers={"Content-Disposition": 'attachment; filename="Board Recruitment Strategy.pdf"'})

    @router.get("/workspace/material-pdf/{material_id}")
    async def material_pdf(material_id: str, request: Request):
        from fastapi.responses import Response
        from document_renderer import render_document_pdf, material_created_by
        member = await current_member(request)
        material = await db.generated_materials.find_one({"material_id": material_id, "user_id": member["user_id"]}, {"_id": 0})
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        current = next((v for v in material["versions"] if v["version"] == material["current_version"]), None)
        text = (current or {}).get("display_text", "")
        profile = await db.recruitment_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "branding": 1})
        branding = (profile or {}).get("branding", {})
        created_by = await material_created_by(db, member["user_id"])
        title = material["title"]
        prepared_for = ""
        if material.get("application_id"):
            application = await db.opportunity_applications.find_one({"application_id": material["application_id"]}, {"_id": 0, "profile_snapshot": 1})
            prepared_for = ((application or {}).get("profile_snapshot") or {}).get("full_name", "")
            if not prepared_for:
                record = await db.reactivation_board_members.find_one({"member_record_id": material["application_id"]}, {"_id": 0, "name": 1})
                prepared_for = (record or {}).get("name", "")
        lines = [line.rstrip() for line in text.split("\n")]
        if lines and lines[0].strip().upper() == title.upper():
            text = "\n".join(lines[1:])
        pdf = render_document_pdf(title=title, org_name=created_by["organization"], body_text=text,
                                  branding=branding, created_by=created_by, prepared_for=prepared_for)
        return Response(content=pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{title}.pdf"'})

    @router.post("/workspace/applications/{application_id}/decision")
    async def candidate_decision(application_id: str, payload: dict, request: Request):
        """Move Forward / Do Not Move Forward. Never sends emails; prepares candidate-specific links idempotently."""
        member = await selection_member(request)
        user_id = member["user_id"]
        application = await owned_application(user_id, application_id)
        decision = payload.get("decision")
        if decision not in {"move_forward", "do_not_move_forward"}:
            raise HTTPException(status_code=422, detail="Decision must be move_forward or do_not_move_forward")
        if decision == "do_not_move_forward":
            await db.opportunity_applications.update_one({"application_id": application_id},
                {"$set": {"status": "Not Moving Forward", "updated_at": now_iso()}})
            return {"status": "Not Moving Forward"}
        await db.opportunity_applications.update_one({"application_id": application_id},
            {"$set": {"status": "Moving Forward", "updated_at": now_iso()}})
        prepared = {}
        existing_process = await db.reference_processes.find_one({"owner_user_id": user_id, "application_id": application_id}, {"_id": 0, "status": 1})
        if not existing_process:
            email = (application.get("applicant_email") or "").strip().lower()
            extracted = ""
            if not email and application.get("cv_text"):
                match = EMAIL_RE.search(application["cv_text"])
                extracted = match.group(0).lower() if match else ""
            await db.reference_processes.insert_one({
                "process_id": new_id(), "owner_user_id": user_id, "application_id": application_id,
                "candidate_name": application.get("profile_snapshot", {}).get("full_name", ""),
                "candidate_email": email, "extracted_email": extracted,
                "candidate_token": secrets.token_urlsafe(24), "status": "Not Started",
                "references": [], "created_at": now_iso(), "updated_at": now_iso()})
        prepared["reference_form"] = "Ready"
        return {"status": "Moving Forward", "prepared": prepared}

    # ---------- Owner review progress ----------
    @router.get("/workspace/board-profile-link/{application_id}")
    async def get_profile_link_status(application_id: str, request: Request):
        member = await selection_member(request)
        link = await db.board_profile_links.find_one({"user_id": member["user_id"], "application_id": application_id}, {"_id": 0, "status": 1, "token": 1})
        response = None
        if link:
            response = await db.board_profile_responses.find_one({"user_id": member["user_id"], "application_id": application_id}, {"_id": 0, "data": 1, "submitted_at": 1})
        return {"link": link, "response": response}

    @router.get("/review-mode/progress")
    async def get_review_progress(request: Request):
        if os.environ.get("OWNER_RECRUITMENT_REVIEW_MODE", "false").lower() != "true":
            return {"progress": None}
        try:
            admin = await authenticate_admin(request, db)
        except HTTPException:
            return {"progress": None}
        record = await db.admin_review_progress.find_one({"admin_email": admin["email"]}, {"_id": 0})
        return {"progress": record}

    @router.post("/review-mode/progress")
    async def save_review_progress(payload: ReviewProgress, request: Request):
        if os.environ.get("OWNER_RECRUITMENT_REVIEW_MODE", "false").lower() != "true":
            raise HTTPException(status_code=404, detail="Owner review mode is not active")
        admin = await authenticate_admin(request, db)
        await db.admin_review_progress.update_one(
            {"admin_email": admin["email"]},
            {"$set": {"admin_email": admin["email"], "last_route": payload.route[:300], "last_label": payload.label[:200], "updated_at": now_iso()}}, upsert=True)
        return {"status": "saved"}

    @router.delete("/review-mode/progress")
    async def reset_review_progress(request: Request):
        admin = await authenticate_admin(request, db)
        await db.admin_review_progress.delete_one({"admin_email": admin["email"]})
        return {"status": "reset"}

    return router
