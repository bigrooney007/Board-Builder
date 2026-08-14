"""Recruitment refinement routes: reference-check automation, applicant emails, admin CSV import,
owner review progress, branding settings."""
import csv
import io
import logging
import os
import re
import secrets
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

import resend
from auth_service import authenticate_admin
from ai_service import GENERATION_TYPES
from member_auth import authenticate_member, require_entitlement
from opportunity_emails import _send, _wrap
from workspace_service import get_current_material, new_id, now_iso

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

REFEREE_QUESTIONS = [
    ("capacity", "In what capacity do you know {candidate}, and approximately how long have you known or worked with them?"),
    ("reliability", "Based on your experience with {candidate}, how would you describe their reliability, professionalism and ability to follow through on responsibilities?"),
    ("strengths", "What strengths, skills or qualities have you observed that you believe could help {candidate} contribute effectively as a nonprofit board member?"),
    ("teamwork", "How have you seen {candidate} work with other people, handle responsibility or contribute to a team or organization?"),
]
RECOMMEND_QUESTION = "Based on your experience, would you feel comfortable recommending {candidate} for board service with {org}? Please explain your response."
REFEREE_IDENTITY_FIELDS = ["name", "position", "organization", "relationship", "duration"]
RECOMMEND_OPTIONS = ["Yes", "No", "I would need more information to say"]

SENDABLE_TYPES = {"after_interview_thank_you", "before_interview_rejection", "conditional_offer", "formal_appointment_email", "portfolio_email", "after_interview_rejection", "general_rejection_email", "interview_invitation"}


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
        member = await current_member(request)
        application = await owned_application(member["user_id"], payload.application_id)
        existing = await db.reference_processes.find_one(
            {"owner_user_id": member["user_id"], "application_id": payload.application_id}, {"_id": 0})
        if existing:
            return existing
        email = (payload.candidate_email or application.get("applicant_email") or "").strip().lower()
        extracted = ""
        if not email and application.get("cv_text"):
            match = EMAIL_RE.search(application["cv_text"])
            extracted = match.group(0).lower() if match else ""
        process = {
            "process_id": new_id(), "owner_user_id": member["user_id"], "application_id": payload.application_id,
            "candidate_name": application.get("profile_snapshot", {}).get("full_name", ""),
            "candidate_email": email, "extracted_email": extracted,
            "candidate_token": secrets.token_urlsafe(24), "status": "Not Started",
            "references": [], "created_at": now_iso(), "updated_at": now_iso(),
        }
        await db.reference_processes.insert_one(process.copy())
        return process

    @router.get("/workspace/reference-process/{application_id}")
    async def get_reference_process(application_id: str, request: Request):
        member = await current_member(request)
        process = await db.reference_processes.find_one(
            {"owner_user_id": member["user_id"], "application_id": application_id}, {"_id": 0})
        return {"process": process}

    @router.post("/workspace/reference-process/{application_id}/send")
    async def send_candidate_form(application_id: str, payload: SendCandidateForm, request: Request):
        member = await current_member(request)
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
        member = await current_member(request)
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
        await _send("BOARD_APPLICANT_SENDER", reference["email"], f"Reference Request | {candidate} — {org} Board Application", _wrap("Reference Request", body))
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
        if process.get("references"):
            raise HTTPException(status_code=409, detail="References have already been provided")
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
            {"$set": {"references": references, "status": "References Submitted", "references_submitted_at": now_iso(), "updated_at": now_iso()}})
        await db.opportunity_applications.update_one({"application_id": process["application_id"]},
            {"$set": {"reference_check_status": "References Submitted"}})
        candidate = process.get("candidate_name") or "Your candidate"
        review_url = f"{origin_of(request)}/app/recruitment/self-guided/module/5"
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
        review_url = f"{origin_of(request)}/app/recruitment/self-guided/module/5"
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
        html_body = "".join(f"<p>{_html.escape(line)}</p>" if line.strip() else "<br/>" for line in body_text.split("\n"))
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
        member = await current_member(request)
        profile = await db.recruitment_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "onboarding_session": 1})
        return {"session": (profile or {}).get("onboarding_session", {})}

    @router.put("/workspace/onboarding-session")
    async def save_onboarding_session(payload: OnboardingSession, request: Request):
        member = await current_member(request)
        session = payload.model_dump()
        if session.get("status") == "Completed":
            session["completed_at"] = now_iso()
        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"onboarding_session": session, "updated_at": now_iso()}}, upsert=True)
        return {"status": "saved", "session": session}

    # ---------- First board meeting invitation send ----------
    @router.put("/workspace/first-meeting")
    async def save_first_meeting(payload: FirstMeetingDetails, request: Request):
        member = await current_member(request)
        if not payload.date.strip() or not payload.time.strip() or not payload.timezone.strip():
            raise HTTPException(status_code=422, detail="Meeting date, time and timezone are required")
        await db.recruitment_profiles.update_one({"user_id": member["user_id"]},
            {"$set": {"first_meeting": payload.model_dump(), "updated_at": now_iso()}}, upsert=True)
        return {"status": "saved"}

    @router.get("/workspace/first-meeting")
    async def get_first_meeting(request: Request):
        member = await current_member(request)
        profile = await db.recruitment_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "first_meeting": 1})
        return {"first_meeting": (profile or {}).get("first_meeting", {})}

    @router.post("/workspace/send-first-meeting")
    async def send_first_meeting(payload: FirstMeetingSend, request: Request):
        member = await current_member(request)
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
                {"application_id": application_id, "owner_user_id": member["user_id"], "status": "Selected"}, {"_id": 0})
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
        from io import BytesIO
        import base64 as b64
        from fastapi.responses import Response
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, KeepTogether, Image
        from ai_service import STRATEGY_TIMELINE_TEXT, STRATEGY_ROADMAP_TEXT, STRATEGY_NEXT_STEP_TEXT
        member = await current_member(request)
        material = await db.generated_materials.find_one({"user_id": member["user_id"], "type": "recruitment_strategy", "application_id": ""}, {"_id": 0})
        if not material:
            raise HTTPException(status_code=404, detail="Generate your Recruitment Strategy first")
        structured = next((v.get("structured") for v in reversed(material["versions"]) if v.get("structured")), {}) or {}
        profile = await db.recruitment_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "branding": 1, "data": 1})
        branding = (profile or {}).get("branding", {})
        opportunity = await db.opportunities.find_one({"user_id": member["user_id"]}, {"_id": 0, "organization_name": 1})
        org = (opportunity or {}).get("organization_name") or (profile or {}).get("data", {}).get("organization_name", "")
        primary = branding.get("primary_color") or "#1d3a2f"
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%B %d, %Y")
        buffer = BytesIO()
        doc = BaseDocTemplate(buffer, pagesize=LETTER, leftMargin=22 * mm, rightMargin=22 * mm, topMargin=20 * mm, bottomMargin=20 * mm, title="Board Recruitment Strategy")
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")

        def footer(canvas, _doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(HexColor("#6b7a72"))
            canvas.drawString(doc.leftMargin, 12 * mm, f"{org} — Board Recruitment Strategy")
            canvas.drawRightString(doc.leftMargin + doc.width, 12 * mm, f"Page {canvas.getPageNumber()}")
            canvas.restoreState()

        doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=footer)])
        h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20, leading=25, textColor=HexColor(primary), spaceAfter=4)
        h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=HexColor(primary), spaceBefore=14, spaceAfter=6, keepWithNext=1)
        h3 = ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=2, keepWithNext=1)
        body = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=16, spaceAfter=6)
        bullet = ParagraphStyle("bullet", parent=body, leftIndent=12, bulletIndent=2, spaceAfter=4)
        meta = ParagraphStyle("meta", parent=body, textColor=HexColor("#5a6a61"))
        story = []
        logo = branding.get("logo_data", "")
        if logo.startswith("data:image"):
            try:
                image_bytes = b64.b64decode(logo.split(",", 1)[1])
                img = Image(BytesIO(image_bytes))
                ratio = img.imageWidth / max(img.imageHeight, 1)
                img.drawHeight = 16 * mm
                img.drawWidth = min(16 * mm * ratio, 60 * mm)
                img.hAlign = "LEFT"
                story.extend([img, Spacer(1, 6)])
            except Exception:
                pass
        story.extend([Paragraph("Board Recruitment Strategy", h1), Paragraph(org, ParagraphStyle("org", parent=body, fontSize=12, leading=16)), Paragraph(today, meta), Spacer(1, 10)])
        esc = lambda t: str(t).replace("&", "&amp;").replace("<", "&lt;")
        if structured.get("executive_summary"):
            story.extend([Paragraph("Executive Summary", h2), Paragraph(esc(structured["executive_summary"]), body)])
        story.append(Paragraph("1. Board Members We Are Recruiting", h2))
        for role in structured.get("roles", [])[:5]:
            story.append(KeepTogether([Paragraph(f"<b>{esc(role.get('role_name', ''))}</b> — {esc(role.get('person_sought', ''))}", bullet)]))
        story.append(Paragraph("2. Recruitment Channels", h2))
        for entry in structured.get("channels", []):
            story.append(KeepTogether([Paragraph(esc(entry.get("channel", "")).upper(), h3), Paragraph(esc(entry.get("approach", "")), body)]))
        story.append(Paragraph("3. Selection Criteria", h2))
        for criterion in structured.get("selection_criteria", []):
            story.append(Paragraph(f"• {esc(criterion)}", bullet))
        for block, title in [(STRATEGY_TIMELINE_TEXT, "4. Recruitment Timeline"), (STRATEGY_ROADMAP_TEXT, "5. Your Recruitment Execution Roadmap"), (STRATEGY_NEXT_STEP_TEXT, "Your Next Step")]:
            story.append(Paragraph(title, h2))
            paragraphs = [p for p in block.split("\n\n")[1:] if p.strip()] or [block]
            for paragraph in paragraphs:
                parts = paragraph.split("\n", 1)
                if len(parts) == 2 and parts[0].isupper() and len(parts[0]) < 70:
                    story.append(KeepTogether([Paragraph(esc(parts[0]), h3), Paragraph(esc(parts[1]), body)]))
                else:
                    story.append(Paragraph(esc(paragraph.replace("\n", " ")), body))
        doc.build(story)
        return Response(content=buffer.getvalue(), media_type="application/pdf",
                        headers={"Content-Disposition": 'attachment; filename="Board Recruitment Strategy.pdf"'})

    @router.get("/workspace/material-pdf/{material_id}")
    async def material_pdf(material_id: str, request: Request):
        from io import BytesIO
        import base64 as b64
        from fastapi.responses import Response
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, KeepTogether, Image
        member = await current_member(request)
        material = await db.generated_materials.find_one({"material_id": material_id, "user_id": member["user_id"]}, {"_id": 0})
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        current = next((v for v in material["versions"] if v["version"] == material["current_version"]), None)
        text = (current or {}).get("display_text", "")
        profile = await db.recruitment_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "branding": 1})
        branding = (profile or {}).get("branding", {})
        org = (await db.opportunities.find_one({"user_id": member["user_id"]}, {"_id": 0, "organization_name": 1}) or {}).get("organization_name", "")
        primary = branding.get("primary_color") or "#1d3a2f"
        title = material["title"]
        buffer = BytesIO()
        doc = BaseDocTemplate(buffer, pagesize=LETTER, leftMargin=22 * mm, rightMargin=22 * mm, topMargin=20 * mm, bottomMargin=20 * mm, title=title)
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")

        def footer(canvas, _doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(HexColor("#6b7a72"))
            canvas.drawString(doc.leftMargin, 12 * mm, f"{org} — {title}" if org else title)
            canvas.drawRightString(doc.leftMargin + doc.width, 12 * mm, f"Page {canvas.getPageNumber()}")
            canvas.restoreState()

        doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=footer)])
        h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=19, leading=24, textColor=HexColor(primary), spaceAfter=4)
        h3 = ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=HexColor(primary), spaceBefore=12, spaceAfter=4, keepWithNext=1)
        body = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=16, spaceAfter=7, firstLineIndent=0)
        bullet = ParagraphStyle("bullet", parent=body, leftIndent=12, spaceAfter=4)
        meta = ParagraphStyle("meta", parent=body, textColor=HexColor("#5a6a61"))
        esc = lambda t: str(t).replace("&", "&amp;").replace("<", "&lt;")
        story = []
        logo = branding.get("logo_data", "")
        if logo.startswith("data:image"):
            try:
                image_bytes = b64.b64decode(logo.split(",", 1)[1])
                img = Image(BytesIO(image_bytes))
                ratio = img.imageWidth / max(img.imageHeight, 1)
                img.drawHeight = 15 * mm
                img.drawWidth = min(15 * mm * ratio, 58 * mm)
                img.hAlign = "LEFT"
                story.extend([img, Spacer(1, 6)])
            except Exception:
                pass
        story.append(Paragraph(esc(title), h1))
        if org:
            story.append(Paragraph(esc(org), meta))
        story.append(Spacer(1, 8))
        lines = [line.rstrip() for line in text.split("\n")]
        if lines and lines[0].strip().upper() == title.upper():
            lines = lines[1:]
        buffer_paragraph = []

        def flush():
            if buffer_paragraph:
                story.append(Paragraph(esc(" ".join(buffer_paragraph)), body))
                buffer_paragraph.clear()

        for line in lines:
            stripped = line.strip()
            if not stripped:
                flush()
                continue
            if stripped.startswith("- ") or stripped.startswith("• "):
                flush()
                story.append(Paragraph(f"• {esc(stripped[2:])}", bullet))
            elif stripped == stripped.upper() and 2 < len(stripped) < 80 and any(c.isalpha() for c in stripped):
                flush()
                story.append(Paragraph(esc(stripped.title() if len(stripped) > 45 else stripped), h3))
            else:
                buffer_paragraph.append(stripped)
        flush()
        doc.build(story)
        return Response(content=buffer.getvalue(), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{title}.pdf"'})

    @router.post("/workspace/applications/{application_id}/decision")
    async def candidate_decision(application_id: str, payload: dict, request: Request):
        """Move Forward / Do Not Move Forward. Never sends emails; prepares candidate-specific links idempotently."""
        member = await current_member(request)
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
        org = await db.opportunities.find_one({"user_id": user_id}, {"_id": 0, "organization_name": 1})
        for agreement_type in ["board_member_agreement", "confidentiality_agreement", "conflict_of_interest_agreement"]:
            existing = await db.signature_requests.find_one(
                {"owner_user_id": user_id, "application_id": application_id, "agreement_type": agreement_type, "status": {"$ne": "Void"}}, {"_id": 0, "status": 1})
            if existing:
                prepared[agreement_type] = existing["status"]
                continue
            agreement = await get_current_material(db, user_id, agreement_type, "")
            if not agreement or not agreement["current"] or agreement["material"].get("status") != "Approved":
                prepared[agreement_type] = "Agreement not approved yet"
                continue
            await db.signature_requests.insert_one({
                "request_id": new_id(), "token": secrets.token_urlsafe(24), "owner_user_id": user_id,
                "application_id": application_id, "agreement_type": agreement_type,
                "agreement_title": GENERATION_TYPES[agreement_type]["title"],
                "material_id": agreement["material"]["material_id"],
                "agreement_version": agreement["current"]["version"],
                "document_snapshot": agreement["current"]["display_text"],
                "organization_name": (org or {}).get("organization_name", ""),
                "board_member_name": application.get("profile_snapshot", {}).get("full_name", ""),
                "board_member_email": application.get("applicant_email", ""),
                "status": "Ready for Signature", "created_at": now_iso(), "updated_at": now_iso()})
            prepared[agreement_type] = "Ready for Signature"
        profile_link = await db.board_profile_links.find_one({"user_id": user_id, "application_id": application_id}, {"_id": 0, "token": 1})
        if not profile_link:
            snapshot = application.get("profile_snapshot", {})
            await db.board_profile_links.insert_one({
                "token": secrets.token_urlsafe(24), "user_id": user_id, "application_id": application_id,
                "status": "Ready", "created_at": now_iso(),
                "prefill": {"full_name": snapshot.get("full_name", ""), "email": application.get("applicant_email", ""),
                            "professional_title": snapshot.get("profession", ""), "employer": snapshot.get("employer", ""),
                            "linkedin": snapshot.get("linkedin", ""), "location": snapshot.get("location", "")}})
        prepared["board_member_profile"] = "Ready"
        return {"status": "Moving Forward", "prepared": prepared}

    # ---------- Owner review progress ----------
    @router.get("/workspace/board-profile-link/{application_id}")
    async def get_profile_link_status(application_id: str, request: Request):
        member = await current_member(request)
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
