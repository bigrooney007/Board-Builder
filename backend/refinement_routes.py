"""Recruitment refinement routes: reference-check automation, applicant emails, admin CSV import,
owner review progress, branding settings."""
import csv
import io
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

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

REFEREE_QUESTIONS = [
    ("reliability", "How would you describe the candidate's reliability and follow-through?"),
    ("professionalism", "How would you describe the candidate's professionalism?"),
    ("collaboration", "How would you describe the candidate's ability to work collaboratively with others?"),
    ("leadership", "How would you describe the candidate's leadership abilities?"),
    ("strongest_qualities", "What would you describe as the candidate's strongest professional qualities?"),
    ("board_service_qualities", "Based on your experience with this person, what qualities do you believe they could bring to nonprofit board service?"),
    ("concerns", "Are there any concerns or considerations you believe the organization should be aware of when considering this individual for a leadership or board position?"),
]
REFEREE_IDENTITY_FIELDS = ["name", "position", "organization", "relationship", "duration"]
RECOMMEND_OPTIONS = ["Yes", "No", "With Reservations"]

SENDABLE_TYPES = {"after_interview_thank_you", "conditional_offer", "formal_appointment_email", "portfolio_email", "after_interview_rejection", "general_rejection_email", "interview_invitation"}


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
        subject = payload.subject.strip() or f"Reference Information Requested — {org}"
        if payload.body.strip():
            import html as _html
            paragraphs = "".join(f"<p>{_html.escape(line)}</p>" if line.strip() else "<br/>" for line in payload.body.split("\n"))
            body = paragraphs + f"<p><a href='{url}' style='display:inline-block;background:#087e5b;color:#fff;padding:13px 22px;border-radius:6px;text-decoration:none;font-weight:bold;'>Provide My References</a></p>"
        else:
            body = (f"<p>Hello {process.get('candidate_name') or 'there'},</p>"
                    f"<p>We are continuing with your board recruitment process at {org}. As part of our appointment process, please provide two professional references using the secure form below.</p>"
                    f"<p><a href='{url}' style='display:inline-block;background:#087e5b;color:#fff;padding:13px 22px;border-radius:6px;text-decoration:none;font-weight:bold;'>Provide My References</a></p>"
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
        opportunity = await db.opportunities.find_one({"user_id": process["owner_user_id"]}, {"_id": 0, "organization_name": 1})
        org = (opportunity or {}).get("organization_name", "the organization")
        url = f"{origin_of(request)}/referee-form/{reference['referee_token']}"
        body = (f"<p>Hello {reference['name']},</p>"
                f"<p>{process.get('candidate_name') or 'A candidate'} has identified you as a professional reference. {org} is considering them for board service and would value your perspective.</p>"
                f"<p>Please complete the short confidential reference form below. Your responses are shared only with {org}.</p>"
                f"<p><a href='{url}' style='display:inline-block;background:#087e5b;color:#fff;padding:13px 22px;border-radius:6px;text-decoration:none;font-weight:bold;'>Complete the Reference Form</a></p>"
                f"<p>Thank you for your time.</p>")
        await _send("BOARD_APPLICANT_SENDER", reference["email"], f"Reference Requested for {process.get('candidate_name', '')} — {org}", _wrap("Reference Requested", body))
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
                "status": "Not Sent", "response": None,
            })
        if len(references) != 2:
            raise HTTPException(status_code=422, detail="Please provide two references")
        await db.reference_processes.update_one({"candidate_token": token},
            {"$set": {"references": references, "status": "References Submitted", "references_submitted_at": now_iso(), "updated_at": now_iso()}})
        await db.opportunity_applications.update_one({"application_id": process["application_id"]},
            {"$set": {"reference_check_status": "References Submitted"}})
        process["references"] = references
        for reference in references:
            try:
                await email_referee(request, process, reference)
            except Exception:
                pass
        return {"status": "submitted", "message": "Thank you. Your references have been recorded and each referee will receive a secure reference form."}

    @router.get("/public/referee-form/{token}")
    async def view_referee_form(token: str):
        process = await db.reference_processes.find_one({"references.referee_token": token}, {"_id": 0, "candidate_name": 1, "references": 1})
        if not process:
            raise HTTPException(status_code=404, detail="This form is not available")
        reference = next(r for r in process["references"] if r["referee_token"] == token)
        return {"candidate_name": process["candidate_name"], "referee_name": reference["name"],
                "completed": reference["status"] == "Completed",
                "identity": {field: reference.get(field, "") for field in REFEREE_IDENTITY_FIELDS},
                "questions": [{"id": qid, "label": label} for qid, label in REFEREE_QUESTIONS],
                "recommend_options": RECOMMEND_OPTIONS}

    @router.post("/public/referee-form/{token}", status_code=201)
    async def submit_referee_form(token: str, payload: dict):
        process = await db.reference_processes.find_one({"references.referee_token": token}, {"_id": 0})
        if not process:
            raise HTTPException(status_code=404, detail="This form is not available")
        reference = next(r for r in process["references"] if r["referee_token"] == token)
        if reference["status"] == "Completed":
            raise HTTPException(status_code=409, detail="This reference has already been completed")
        missing = [label for qid, label in REFEREE_QUESTIONS if not str(payload.get(qid, "")).strip()]
        if missing:
            raise HTTPException(status_code=422, detail="Please answer every question. Only the additional comments are optional.")
        if payload.get("recommend") not in RECOMMEND_OPTIONS:
            raise HTTPException(status_code=422, detail="Please choose whether you would recommend this individual (Yes, No, or With Reservations)")
        response = {qid: str(payload.get(qid, ""))[:4000] for qid, _ in REFEREE_QUESTIONS}
        response["recommend"] = payload["recommend"]
        response["comments"] = str(payload.get("comments", ""))[:4000]
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
        return {"status": "submitted", "message": "Thank you. Your reference has been recorded confidentially."}

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
