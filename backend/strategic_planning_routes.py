"""Strategic Planning: admin-only service-delivery pathway.

Replicates the verified Activation planning architecture: hosted secure Board Member
forms, person-specific tokens, original responses, async Claude consolidation, board
review, area ownership, development packs and final plan assembly. Reuses the shared
email/PDF/extraction engines.
"""
import asyncio
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Union

import resend
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ai_service import generate_structured
from content_templates import (
    sp_form_invitation_email,
    sp_generic_form_invitation_email,
    sp_review_invitation_email,
    sp_signature,
)
from auth_service import authenticate_admin
from reactivation_routes import build_portfolio_pdf, email_html, origin_of
from reference_routes import extract_reference_text

logger = logging.getLogger(__name__)

REVIEW_CHOICES = ["Support as Written", "Suggest a Change", "Add an Idea", "Flag for Board Discussion"]
AREA_STATUSES = ["NOT ASSIGNED", "ASSIGNED", "IN DEVELOPMENT", "SUBMITTED", "READY FOR BOARD"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def assign_question_ids(sections: list) -> list:
    cleaned = []
    for s_index, section in enumerate(sections or [], start=1):
        questions = []
        for q_index, question in enumerate(section.get("questions", []) or [], start=1):
            questions.append({
                "id": f"s{s_index}_q{q_index}",
                "prompt": str(question.get("prompt", "")).strip(),
                "type": question.get("type") if question.get("type") in {"long", "short", "multi"} else "long",
                "options": [str(o) for o in (question.get("options") or [])],
                "required": bool(question.get("required", True)),
            })
        cleaned.append({"key": f"s{s_index}", "title": str(section.get("title", "")).strip(), "questions": questions})
    return cleaned


def plan_display(structured: dict, organization: str) -> str:
    lines = ["FOUNDATIONAL STRATEGIC PLAN", organization, ""]
    for area in structured.get("areas", []):
        lines.extend([str(area.get("area", "")).upper(), "", "DIRECTION", str(area.get("direction", "")), "", "IDEAS SHARED BY THE BOARD"])
        lines.extend([f"- {idea}" for idea in area.get("ideas_shared", [])])
        lines.extend(["", "PROPOSED PRIORITIES"])
        lines.extend([f"- {priority}" for priority in area.get("proposed_priorities", [])])
        lines.append("")
    return "\n".join(lines).strip()


def pack_display(structured: dict, area: str, organization: str) -> str:
    lines = ["STRATEGIC AREA DEVELOPMENT PACK", organization, "", "STRATEGIC AREA", area, "",
             "MISSION / DIRECTION FOR THIS AREA", str(structured.get("mission_direction", "")), "", "AGREED FOUNDATIONAL PRIORITIES"]
    lines.extend([f"- {p}" for p in structured.get("foundational_priorities", [])])
    lines.extend(["", "IDEAS SUBMITTED FOR THIS AREA"])
    lines.extend([f"- {i}" for i in structured.get("ideas", [])])
    if structured.get("refinement_comments"):
        lines.extend(["", "BOARD REFINEMENT COMMENTS"])
        lines.extend([f"- {c}" for c in structured.get("refinement_comments", [])])
    if structured.get("open_questions"):
        lines.extend(["", "QUESTIONS STILL NEEDING RESOLUTION"])
        lines.extend([f"- {q}" for q in structured.get("open_questions", [])])
    lines.extend(["", "YOUR ASSIGNMENT", str(structured.get("development_instruction", ""))])
    return "\n".join(lines).strip()


def final_display(structured: dict, organization: str) -> str:
    lines = ["STRATEGIC PLAN", organization, ""]
    for section in structured.get("sections", []):
        lines.extend([str(section.get("heading", "")).upper(), str(section.get("content", "")), ""])
    return "\n".join(lines).strip()


class ProjectCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    organization_name: str = Field(min_length=1)
    founder_name: str = Field(min_length=1)
    founder_email: EmailStr
    founder_title: str = ""
    mission: str = ""


class ProjectGenerate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    organization_name: str = Field(min_length=1)
    founder_name: str = Field(min_length=1)
    founder_email: EmailStr
    founder_title: str = ""
    mission: str = ""
    form_content: str = Field(min_length=20)


class ParticipantCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1)
    email: EmailStr
    role: str = ""
    expertise: str = ""


class FormEdit(BaseModel):
    introduction: str = Field(min_length=1)
    sections: List[dict]


class TextPayload(BaseModel):
    text: str = Field(min_length=1)


class FormSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")
    full_name: str = Field(min_length=1)
    email: EmailStr
    answers: Dict[str, Union[str, List[str]]]


class AreaReview(BaseModel):
    area_key: str
    choice: str
    comment: str = ""


class ReviewSubmissionPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")
    full_name: str = Field(min_length=1)
    responses: List[AreaReview] = Field(min_length=1)


class OwnerAssignment(BaseModel):
    participant_id: str


class AreaStatusPayload(BaseModel):
    status: str


class AdoptionPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    conclusion: str = Field(min_length=1)
    adopted: bool


class AreaPlanSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    plan_text: str = Field(min_length=1)

class AreaPlanEdit(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    plan_text: str = Field(min_length=1)


def create_strategic_planning_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def admin(request: Request) -> dict:
        return await authenticate_admin(request, db)

    async def owned_project(project_id: str) -> dict:
        project = await db.sp_projects.find_one({"project_id": project_id}, {"_id": 0})
        if not project:
            raise HTTPException(status_code=404, detail="Strategic Planning project not found")
        return project

    async def owned_participant(project_id: str, participant_id: str) -> dict:
        record = await db.sp_participants.find_one({"project_id": project_id, "participant_id": participant_id}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Board Member not found")
        return record

    def participant_row(record: dict) -> dict:
        return {key: record.get(key, "") for key in [
            "participant_id", "name", "email", "role", "expertise", "status",
            "last_sent_at", "submitted_at", "review_status", "review_submitted_at", "last_review_sent_at"]}

    def area_row(area: dict, participants_by_id: dict) -> dict:
        owner = participants_by_id.get(area.get("owner_participant_id", ""), {})
        return {**{k: area.get(k, "") for k in [
            "area_key", "area", "direction", "status", "owner_participant_id",
            "pack_status", "pack_generation_error", "last_pack_sent_at", "plan_submitted_at",
            "adoption_conclusion", "submitted_plan", "detailed_plan_text", "detailed_plan_status", "detailed_plan_approved_at"]},
            "adopted": area.get("adopted", False),
            "proposed_priorities": area.get("proposed_priorities", []),
            "owner_name": owner.get("name", "")}

    async def send_email(to_email: str, subject: str, body: str, button_label: str, link: str, reply_to: str = ""):
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        message = {"from": os.environ["NONPROFIT_SENDER"], "to": [to_email],
                   "subject": subject, "html": email_html(body, button_label, link)}
        if reply_to:
            message["reply_to"] = [reply_to]
        await resend.Emails.send_async(message)

    async def notify_owner(subject: str, body: str, button_label: str, link: str):
        owner = os.environ.get("OWNER_NOTIFICATION_EMAIL") or os.environ.get("OWNER_EMAIL", "")
        if not owner:
            return
        try:
            await send_email(owner, subject, body, button_label, link)
        except Exception:
            logger.exception("Strategic planning owner notification failed")

    # ---------------- PROJECTS ----------------

    @router.post("/admin/sp/projects", status_code=201)
    async def create_project(payload: ProjectCreate, request: Request):
        await admin(request)
        project = {
            "project_id": str(uuid.uuid4()), "organization_name": payload.organization_name,
            "founder_name": payload.founder_name, "founder_email": str(payload.founder_email).lower(),
            "founder_title": payload.founder_title, "mission": payload.mission,
            "status": "Active", "created_at": now_iso(),
        }
        await db.sp_projects.insert_one({**project})
        return {"project": project}

    @router.get("/admin/sp/projects")
    async def list_projects(request: Request):
        await admin(request)
        projects = await db.sp_projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
        rows = []
        for project in projects:
            participants = await db.sp_participants.count_documents({"project_id": project["project_id"]})
            completed = await db.sp_participants.count_documents({"project_id": project["project_id"], "status": "COMPLETED"})
            plan = await db.sp_plans.find_one({"project_id": project["project_id"]}, {"_id": 0, "status": 1})
            rows.append({**project, "participant_count": participants, "responses_received": completed,
                         "plan_status": (plan or {}).get("status", "NONE")})
        return {"projects": rows}

    @router.get("/admin/sp/projects/{project_id}")
    async def project_detail(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        participants = await db.sp_participants.find({"project_id": project_id}, {"_id": 0}).sort("created_at", 1).to_list(300)
        form = await db.sp_forms.find_one({"project_id": project_id}, {"_id": 0}) or {}
        plan = await db.sp_plans.find_one({"project_id": project_id}, {"_id": 0}) or {}
        by_id = {p["participant_id"]: p for p in participants}
        return {
            "project": {**project, "generic_form_token": project.get("generic_form_token", "")},
            "participants": [participant_row(p) for p in participants],
            "form": {"status": form.get("status", "NONE"), "introduction": form.get("content", {}).get("introduction", ""),
                     "sections": form.get("content", {}).get("sections", []), "approved_version": form.get("approved_version", 0),
                     "generation_error": form.get("generation_error", ""), "source_filename": form.get("source_filename", "")},
            "plan": {"status": plan.get("status", "NONE"), "display_text": plan.get("display_text", ""),
                     "generation_error": plan.get("generation_error", ""), "finalized_text": plan.get("finalized_text", ""),
                     "finalized_at": plan.get("finalized_at", ""), "review_version": plan.get("review_version", 0),
                     "owner_suggestions": plan.get("owner_suggestions", []), "suggestion_status": plan.get("suggestion_status", "NONE")},
            "action_plan": {"status": plan.get("action_status", "NONE"), "text": plan.get("action_text", ""),
                            "generation_error": plan.get("action_generation_error", ""), "share_token": plan.get("action_share_token", "")},
            "areas": [area_row(a, by_id) for a in plan.get("areas", [])],
            "final_plan": {"status": plan.get("final_status", "NONE"), "display_text": plan.get("final_display_text", ""),
                           "generation_error": plan.get("final_generation_error", ""), "share_token": plan.get("final_share_token", ""),
                           "meeting_status": plan.get("meeting_status", "NONE"), "meeting_guide_text": plan.get("meeting_guide_text", ""),
                           "meeting_generation_error": plan.get("meeting_generation_error", "")},
        }

    # ---------------- PARTICIPANTS ----------------

    @router.post("/admin/sp/projects/{project_id}/participants", status_code=201)
    async def add_participant(project_id: str, payload: ParticipantCreate, request: Request):
        await admin(request)
        await owned_project(project_id)
        email = str(payload.email).lower()
        existing = await db.sp_participants.find_one({"project_id": project_id, "email": email}, {"_id": 0})
        if existing:
            return {"status": "exists", "participant": participant_row(existing)}
        record = {
            "participant_id": str(uuid.uuid4()), "project_id": project_id,
            "name": payload.name, "email": email, "role": payload.role, "expertise": payload.expertise,
            "status": "NOT SENT", "form_token": secrets.token_urlsafe(32),
            "review_status": "NOT SENT", "review_token": secrets.token_urlsafe(32),
            "created_at": now_iso(),
        }
        await db.sp_participants.insert_one({**record})
        return {"status": "created", "participant": participant_row(record)}

    @router.delete("/admin/sp/projects/{project_id}/participants/{participant_id}")
    async def remove_participant(project_id: str, participant_id: str, request: Request):
        await admin(request)
        record = await owned_participant(project_id, participant_id)
        if record["status"] != "NOT SENT":
            raise HTTPException(status_code=409, detail="This Board Member has already been sent the planning form")
        await db.sp_participants.delete_one({"project_id": project_id, "participant_id": participant_id})
        return {"status": "removed"}

    # ---------------- MASTER FORM ----------------

    @router.post("/admin/sp/projects/{project_id}/form/upload")
    async def upload_form(project_id: str, request: Request, file: UploadFile = File(...)):
        await admin(request)
        project = await owned_project(project_id)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File is too large (10MB maximum)")
        text = extract_reference_text(content, file.filename or "")
        if not text.strip():
            raise HTTPException(status_code=422, detail="No readable text could be extracted from this file")
        now = now_iso()
        await db.sp_forms.update_one(
            {"project_id": project_id},
            {"$set": {"status": "Generating", "generation_error": "", "source_filename": file.filename or "",
                      "master_source_text": text[:120000], "updated_at": now},
             "$setOnInsert": {"form_id": str(uuid.uuid4()), "project_id": project_id,
                              "approved_version": 0, "approved_versions": [], "created_at": now}},
            upsert=True)

        async def run_structure():
            try:
                context = (
                    f"ORGANIZATION: {project['organization_name']}\nMISSION: {project.get('mission', '')}\n\n"
                    f"FOUNDER'S UPLOADED MASTER STRATEGIC PLANNING FORM (the ONLY authority for questions):\n{text[:60000]}"
                )
                structured = await generate_structured("strategic_planning_form_structure", context)
                content_payload = {"introduction": str(structured.get("introduction", "")).strip(),
                                   "sections": assign_question_ids(structured.get("sections", []))}
                await db.sp_forms.update_one({"project_id": project_id}, {"$set": {
                    "status": "Draft", "content": content_payload, "updated_at": now_iso()}})
            except Exception as exc:
                logger.error("SP form structuring failed for %s: %s", project_id, exc)
                await db.sp_forms.update_one({"project_id": project_id}, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300], "updated_at": now_iso()}})

        asyncio.create_task(run_structure())
        return {"status": "Generating"}

    @router.get("/admin/sp/projects/{project_id}/form")
    async def get_form(project_id: str, request: Request):
        await admin(request)
        form = await db.sp_forms.find_one({"project_id": project_id}, {"_id": 0, "master_source_text": 0}) or {}
        return {"status": form.get("status", "NONE"), "content": form.get("content"),
                "approved_version": form.get("approved_version", 0), "generation_error": form.get("generation_error", ""),
                "source_filename": form.get("source_filename", "")}

    @router.put("/admin/sp/projects/{project_id}/form")
    async def save_form(project_id: str, payload: FormEdit, request: Request):
        await admin(request)
        form = await db.sp_forms.find_one({"project_id": project_id}, {"_id": 0, "status": 1})
        if not form:
            raise HTTPException(status_code=409, detail="Upload the master Strategic Planning Form first")
        content = {"introduction": payload.introduction, "sections": assign_question_ids(payload.sections)}
        await db.sp_forms.update_one({"project_id": project_id}, {"$set": {
            "content": content, "status": "Draft", "updated_at": now_iso()}})
        return {"status": "Draft"}

    @router.post("/admin/sp/projects/{project_id}/form/approve")
    async def approve_form(project_id: str, request: Request):
        await admin(request)
        form = await db.sp_forms.find_one({"project_id": project_id}, {"_id": 0})
        if not form or not form.get("content") or form.get("status") not in {"Draft", "Approved"}:
            raise HTTPException(status_code=409, detail="There is no draft form ready to approve")
        now = now_iso()
        version = form.get("approved_version", 0) + 1
        await db.sp_forms.update_one({"project_id": project_id}, {"$set": {
            "status": "Approved", "approved_version": version, "approved_at": now, "updated_at": now},
            "$push": {"approved_versions": {"version": version, "content": form["content"], "approved_at": now}}})
        return {"status": "Approved", "approved_version": version}

    # ---------------- SEND FORM ----------------

    def planning_email(project: dict, participant: dict, link: str) -> dict:
        first = (participant.get("name") or "").split(" ")[0]
        organization = project["organization_name"]
        signature = sp_signature(project["founder_name"], project.get("founder_title", ""), organization)
        return {**sp_form_invitation_email(first, organization, signature), "form_link": link}

    @router.get("/admin/sp/projects/{project_id}/participants/{participant_id}/email-preview")
    async def form_email_preview(project_id: str, participant_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        record = await owned_participant(project_id, participant_id)
        email = planning_email(project, record, f"{origin_of(request)}/strategic-planning-form/{record['form_token']}")
        return {"to_name": record["name"], "to_email": record["email"], **email}

    @router.post("/admin/sp/projects/{project_id}/participants/{participant_id}/send")
    async def send_form(project_id: str, participant_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        record = await owned_participant(project_id, participant_id)
        form = await db.sp_forms.find_one({"project_id": project_id}, {"_id": 0, "status": 1, "approved_version": 1})
        if not form or form.get("status") != "Approved":
            raise HTTPException(status_code=409, detail="Approve the Strategic Planning Form before sending it to Board Members")
        email = planning_email(project, record, f"{origin_of(request)}/strategic-planning-form/{record['form_token']}")
        try:
            await send_email(record["email"], email["subject"], email["body"], email["button_label"], email["form_link"],
                             reply_to=project.get("founder_email", ""))
        except Exception as exc:
            logger.exception("SP form send failed for %s", participant_id)
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc
        now = now_iso()
        updates = {"last_sent_at": now}
        if record["status"] == "NOT SENT":
            updates["status"] = "SENT"
        if not record.get("form_version"):
            updates["form_version"] = form["approved_version"]
        await db.sp_participants.update_one({"participant_id": participant_id}, {"$set": updates})
        return {"status": "sent", "sent_at": now}

    @router.get("/admin/sp/projects/{project_id}/participants/{participant_id}/response")
    async def view_response(project_id: str, participant_id: str, request: Request):
        await admin(request)
        record = await owned_participant(project_id, participant_id)
        if record["status"] != "COMPLETED" or not record.get("response"):
            raise HTTPException(status_code=404, detail="This Board Member has not completed their planning form yet")
        return {"participant": participant_row(record), "response": record["response"],
                "questions": record.get("response_questions", []), "submitted_at": record.get("submitted_at", "")}

    # ---------------- PUBLIC: HOSTED FORM ----------------

    async def participant_by_form_token(token: str) -> dict:
        record = await db.sp_participants.find_one({"form_token": token}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This form link is not valid")
        return record

    async def approved_form_content(project_id: str, version: int) -> dict:
        form = await db.sp_forms.find_one({"project_id": project_id}, {"_id": 0}) or {}
        for entry in form.get("approved_versions", []):
            if entry["version"] == version:
                return entry["content"]
        versions = form.get("approved_versions", [])
        if versions:
            return versions[-1]["content"]
        raise HTTPException(status_code=409, detail="This planning form is not available yet")

    @router.get("/strategic-planning-form/{token}")
    async def public_form(token: str):
        record = await db.sp_participants.find_one({"form_token": token}, {"_id": 0})
        if record:
            project = await owned_project(record["project_id"])
            content = await approved_form_content(record["project_id"], record.get("form_version") or 0)
            return {"organization_name": project["organization_name"],
                    "submitted": record["status"] == "COMPLETED",
                    "prefill": {"full_name": record.get("name", ""), "email": record.get("email", "")},
                    "form": content}
        project = await db.sp_projects.find_one({"generic_form_token": token}, {"_id": 0})
        if not project:
            raise HTTPException(status_code=404, detail="This form link is not valid")
        content = await approved_form_content(project["project_id"], 0)
        return {"organization_name": project["organization_name"], "submitted": False,
                "prefill": {"full_name": "", "email": ""}, "form": content}

    @router.post("/strategic-planning-form/{token}", status_code=201)
    async def submit_form(token: str, payload: FormSubmission):
        record = await db.sp_participants.find_one({"form_token": token}, {"_id": 0})
        if not record:
            project_by_token = await db.sp_projects.find_one({"generic_form_token": token}, {"_id": 0})
            if not project_by_token:
                raise HTTPException(status_code=404, detail="This form link is not valid")
            email = str(payload.email).lower()
            record = await db.sp_participants.find_one({"project_id": project_by_token["project_id"], "email": email}, {"_id": 0})
            if not record:
                record = {
                    "participant_id": str(uuid.uuid4()), "project_id": project_by_token["project_id"],
                    "name": payload.full_name, "email": email, "role": "", "expertise": "",
                    "status": "SENT", "form_token": secrets.token_urlsafe(32),
                    "review_status": "NOT SENT", "review_token": secrets.token_urlsafe(32),
                    "created_at": now_iso(), "joined_via": "form_link",
                }
                await db.sp_participants.insert_one({**record})
        if record["status"] == "COMPLETED":
            raise HTTPException(status_code=409, detail="This response has already been submitted")
        project = await owned_project(record["project_id"])
        content = await approved_form_content(record["project_id"], record.get("form_version") or 0)
        questions = [q | {"section": s["title"]} for s in content.get("sections", []) for q in s["questions"]]
        answers = {}
        for question in questions:
            value = payload.answers.get(question["id"], [] if question["type"] == "multi" else "")
            if question["type"] == "multi":
                value = [str(v) for v in value] if isinstance(value, list) else ([str(value)] if value else [])
            else:
                value = str(value or "").strip()
            if question["required"] and not value:
                raise HTTPException(status_code=422, detail=f"Please answer: {question['prompt']}")
            answers[question["id"]] = value
        now = now_iso()
        result = await db.sp_participants.update_one(
            {"participant_id": record["participant_id"], "status": {"$ne": "COMPLETED"}},
            {"$set": {"status": "COMPLETED", "response": answers, "submitted_at": now,
                      "name": payload.full_name, "email": str(payload.email).lower(),
                      "response_questions": [{"id": q["id"], "prompt": q["prompt"], "section": q["section"]} for q in questions]}})
        if result.modified_count:
            origin = os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com"
            await notify_owner(
                f"Strategic Planning Response Received | {payload.full_name}",
                f"{payload.full_name} has completed their Strategic Planning Form for {project['organization_name']}.\n\n"
                "Their original response is available in the Strategic Planning workspace.\n\n[OPEN STRATEGIC PLANNING]",
                "OPEN STRATEGIC PLANNING", f"{origin}/admin")
        return {"status": "submitted", "organization_name": project["organization_name"]}

    @router.get("/strategic-planning-response/{participant_id}")
    async def public_response(participant_id: str):
        record = await db.sp_participants.find_one({"participant_id": participant_id, "status": "COMPLETED"}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This Strategic Planning response is not available")
        project = await owned_project(record["project_id"])
        prompts = {q["id"]: q for q in record.get("response_questions", [])}
        rows = []
        for qid, value in (record.get("response") or {}).items():
            q = prompts.get(qid, {})
            rows.append({"section": q.get("section", ""), "question": q.get("prompt", qid), "answer": value})
        return {"organization_name": project["organization_name"], "name": record.get("name", ""), "submitted_at": record.get("submitted_at", ""), "responses": rows}

    # ---------------- FOUNDATIONAL PLAN ----------------

    async def current_plan(project_id: str) -> dict:
        return await db.sp_plans.find_one({"project_id": project_id}, {"_id": 0}) or {}

    def response_context(record: dict) -> str:
        lines = [f"BOARD MEMBER: {record.get('name', '')} (role: {record.get('role', '')}; expertise: {record.get('expertise', '')})"]
        prompts = {q["id"]: q for q in record.get("response_questions", [])}
        for qid, value in (record.get("response") or {}).items():
            question = prompts.get(qid, {})
            rendered = ", ".join(value) if isinstance(value, list) else value
            if rendered:
                lines.append(f"  [{question.get('section', '')}] {question.get('prompt', qid)}: {rendered}")
        return "\n".join(lines)

    @router.post("/admin/sp/projects/{project_id}/plan/generate")
    async def generate_plan(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        responses = await db.sp_participants.find({"project_id": project_id, "status": "COMPLETED"}, {"_id": 0}).to_list(300)
        if not responses:
            raise HTTPException(status_code=409, detail="No Board Member responses have been received yet")
        plan = await current_plan(project_id)
        if plan.get("status") == "Generating":
            return {"status": "Generating"}
        now = now_iso()
        await db.sp_plans.update_one(
            {"project_id": project_id},
            {"$set": {"status": "Generating", "generation_error": "", "updated_at": now},
             "$setOnInsert": {"plan_id": str(uuid.uuid4()), "project_id": project_id, "review_version": 0,
                              "draft_history": [], "created_at": now}},
            upsert=True)
        context = (
            f"ORGANIZATION: {project['organization_name']}\nMISSION: {project.get('mission', '')}\n"
            f"FOUNDER: {project['founder_name']}\n\nEVERY ORIGINAL BOARD MEMBER RESPONSE (who said what):\n\n"
            + "\n\n".join(response_context(r) for r in responses)
        )

        async def run_generation():
            try:
                structured = await generate_structured("strategic_planning_foundational", context)
                areas = []
                for index, area in enumerate(structured.get("areas", []), start=1):
                    areas.append({"area_key": f"area{index}", "area": str(area.get("area", "")),
                                  "direction": str(area.get("direction", "")),
                                  "ideas_shared": [str(i) for i in area.get("ideas_shared", [])],
                                  "proposed_priorities": [str(p) for p in area.get("proposed_priorities", [])],
                                  "status": "NOT ASSIGNED", "owner_participant_id": "", "pack_status": "NONE",
                                  "pack_token": secrets.token_urlsafe(32), "adoption_conclusion": "", "adopted": False})
                await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
                    "status": "Draft", "structured": structured, "areas": areas,
                    "display_text": plan_display(structured, project["organization_name"]),
                    "responses_included": [r["participant_id"] for r in responses], "updated_at": now_iso()}})
            except Exception as exc:
                logger.error("SP plan generation failed for %s: %s", project_id, exc)
                await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300], "updated_at": now_iso()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating"}

    @router.get("/admin/sp/projects/{project_id}/plan/status")
    async def plan_status(project_id: str, request: Request):
        await admin(request)
        plan = await current_plan(project_id)
        return {"status": plan.get("status", "NONE"), "generation_error": plan.get("generation_error", ""),
                "final_status": plan.get("final_status", "NONE"), "final_generation_error": plan.get("final_generation_error", "")}

    @router.put("/admin/sp/projects/{project_id}/plan")
    async def edit_plan(project_id: str, payload: TextPayload, request: Request):
        await admin(request)
        plan = await current_plan(project_id)
        if not plan or not plan.get("display_text"):
            raise HTTPException(status_code=409, detail="Generate the Foundational Strategic Plan first")
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
            "display_text": payload.text, "status": "Draft", "updated_at": now_iso()}})
        return {"status": "Draft"}

    @router.post("/admin/sp/projects/{project_id}/plan/approve")
    async def approve_plan(project_id: str, request: Request):
        await admin(request)
        plan = await current_plan(project_id)
        if plan.get("status") not in {"Draft", "Approved"} or not plan.get("display_text"):
            raise HTTPException(status_code=409, detail="There is no draft plan ready to approve")
        now = now_iso()
        version = plan.get("review_version", 0) + 1
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
            "status": "Approved", "review_version": version, "approved_at": now, "updated_at": now},
            "$push": {"draft_history": {"version": version, "display_text": plan["display_text"], "approved_at": now}}})
        return {"status": "Approved", "review_version": version}

    # ---------------- BOARD REVIEW & REFINEMENT ----------------

    def review_email(project: dict, participant: dict, link: str) -> dict:
        first = (participant.get("name") or "").split(" ")[0]
        organization = project["organization_name"]
        signature = sp_signature(project["founder_name"], project.get("founder_title", ""), organization)
        return {**sp_review_invitation_email(first, organization, signature), "form_link": link}

    @router.get("/admin/sp/projects/{project_id}/participants/{participant_id}/review-email-preview")
    async def review_email_preview(project_id: str, participant_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        record = await owned_participant(project_id, participant_id)
        email = review_email(project, record, f"{origin_of(request)}/strategic-plan-review/{record['review_token']}")
        return {"to_name": record["name"], "to_email": record["email"], **email}

    @router.post("/admin/sp/projects/{project_id}/participants/{participant_id}/send-review")
    async def send_review(project_id: str, participant_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        record = await owned_participant(project_id, participant_id)
        plan = await current_plan(project_id)
        if plan.get("status") != "Approved":
            raise HTTPException(status_code=409, detail="Approve the Foundational Strategic Plan before sending it for Board review")
        email = review_email(project, record, f"{origin_of(request)}/strategic-plan-review/{record['review_token']}")
        try:
            await send_email(record["email"], email["subject"], email["body"], email["button_label"], email["form_link"],
                             reply_to=project.get("founder_email", ""))
        except Exception as exc:
            logger.exception("SP review send failed for %s", participant_id)
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc
        now = now_iso()
        updates = {"last_review_sent_at": now}
        if record.get("review_status") in {"", "NOT SENT", None}:
            updates["review_status"] = "SENT"
        if not record.get("review_version"):
            updates["review_version"] = plan.get("review_version", 1)
        await db.sp_participants.update_one({"participant_id": participant_id}, {"$set": updates})
        return {"status": "sent", "sent_at": now}

    @router.get("/admin/sp/projects/{project_id}/reviews")
    async def list_reviews(project_id: str, request: Request):
        await admin(request)
        records = await db.sp_participants.find(
            {"project_id": project_id, "review_status": "COMPLETED"}, {"_id": 0}).to_list(300)
        return {"reviews": [{"participant": participant_row(r), "responses": r.get("review_responses", []),
                             "review_submitted_at": r.get("review_submitted_at", "")} for r in records]}

    @router.get("/strategic-plan-review/{token}")
    async def public_review(token: str):
        record = await db.sp_participants.find_one({"review_token": token}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This review link is not valid")
        project = await owned_project(record["project_id"])
        plan = await current_plan(record["project_id"])
        if plan.get("status") not in {"Approved", "Finalized"}:
            raise HTTPException(status_code=409, detail="The Foundational Strategic Plan is not ready for review yet")
        return {"organization_name": project["organization_name"],
                "submitted": record.get("review_status") == "COMPLETED",
                "prefill": {"full_name": record.get("name", "")},
                "display_text": plan.get("display_text", ""),
                "areas": [{"area_key": a["area_key"], "area": a["area"]} for a in plan.get("areas", [])],
                "choices": REVIEW_CHOICES}

    @router.post("/strategic-plan-review/{token}", status_code=201)
    async def submit_review(token: str, payload: ReviewSubmissionPayload):
        record = await db.sp_participants.find_one({"review_token": token}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This review link is not valid")
        if record.get("review_status") == "COMPLETED":
            raise HTTPException(status_code=409, detail="This review has already been submitted")
        plan = await current_plan(record["project_id"])
        valid_areas = {a["area_key"] for a in plan.get("areas", [])}
        responses = []
        for item in payload.responses:
            if item.area_key not in valid_areas:
                raise HTTPException(status_code=422, detail="Unknown strategic area")
            if item.choice not in REVIEW_CHOICES:
                raise HTTPException(status_code=422, detail="Unknown review choice")
            responses.append({"area_key": item.area_key, "choice": item.choice, "comment": item.comment})
        now = now_iso()
        result = await db.sp_participants.update_one(
            {"participant_id": record["participant_id"], "review_status": {"$ne": "COMPLETED"}},
            {"$set": {"review_status": "COMPLETED", "review_responses": responses,
                      "review_submitted_at": now, "name": payload.full_name}})
        if result.modified_count:
            project = await owned_project(record["project_id"])
            origin = os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com"
            await notify_owner(
                f"Strategic Plan Review Received | {payload.full_name}",
                f"{payload.full_name} has completed their review of the Foundational Strategic Plan for {project['organization_name']}.\n\n[OPEN STRATEGIC PLANNING]",
                "OPEN STRATEGIC PLANNING", f"{origin}/admin")
        return {"status": "submitted"}

    @router.post("/admin/sp/projects/{project_id}/plan/finalize")
    async def finalize_plan(project_id: str, payload: TextPayload, request: Request):
        await admin(request)
        plan = await current_plan(project_id)
        if plan.get("status") not in {"Approved", "Finalized"}:
            raise HTTPException(status_code=409, detail="Approve the Foundational Strategic Plan before finalizing it")
        now = now_iso()
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
            "status": "Finalized", "finalized_text": payload.text, "display_text": payload.text,
            "finalized_at": now, "updated_at": now}})
        return {"status": "Finalized"}

    # ---------------- AREAS: ASSIGNMENT, PACKS, SUBMISSION, ADOPTION ----------------

    async def owned_area(project_id: str, area_key: str) -> dict:
        plan = await current_plan(project_id)
        for area in plan.get("areas", []):
            if area["area_key"] == area_key:
                return area
        raise HTTPException(status_code=404, detail="Strategic area not found")

    async def update_area(project_id: str, area_key: str, updates: dict):
        sets = {f"areas.$.{key}": value for key, value in updates.items()}
        await db.sp_plans.update_one({"project_id": project_id, "areas.area_key": area_key}, {"$set": sets})

    @router.post("/admin/sp/projects/{project_id}/areas/suggest-owners")
    async def suggest_owners(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        if plan.get("status") != "Finalized":
            raise HTTPException(status_code=409, detail="Finalize the Foundational Plan before assigning strategic areas")
        if plan.get("suggestion_status") == "Generating":
            return {"status": "Generating"}
        participants = await db.sp_participants.find({"project_id": project_id}, {"_id": 0}).to_list(300)
        areas = plan.get("areas", [])
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {"suggestion_status": "Generating"}})

        def keyword_suggestions():
            rows = []
            for area in areas:
                keywords = (area["area"] + " " + area.get("direction", "")).lower()
                best, best_score = None, 0
                for participant in participants:
                    profile = f"{participant.get('role', '')} {participant.get('expertise', '')}".lower()
                    own_ideas = " ".join(str(v) for v in (participant.get("response") or {}).values() if isinstance(v, str)).lower()
                    score = sum(1 for word in profile.split() if len(word) > 3 and word in keywords)
                    score += sum(1 for word in area["area"].lower().split() if len(word) > 3 and word in own_ideas)
                    if score > best_score:
                        best, best_score = participant, score
                rows.append({"area_key": area["area_key"], "area": area["area"],
                             "suggested_participant_id": (best or {}).get("participant_id", ""),
                             "suggested_name": (best or {}).get("name", ""),
                             "basis": "role, expertise and their own submitted ideas" if best_score else "no clear alignment found — assign manually"})
            return rows

        context = (
            f"ORGANIZATION: {project['organization_name']}\n\nSTRATEGIC AREAS NEEDING AN OWNER:\n"
            + "\n".join(f"- area_key: {a['area_key']} | AREA: {a['area']} | DIRECTION: {a.get('direction', '')} | PRIORITIES: {'; '.join(a.get('proposed_priorities', []))}" for a in areas)
            + "\n\nBOARD MEMBERS (their skills, experience and their own submitted planning responses):\n\n"
            + "\n\n".join(response_context(p) for p in participants)
        )

        async def run_suggestions():
            try:
                structured = await generate_structured("strategic_area_owner_recommendation", context)
                by_name = {p["name"].strip().lower(): p for p in participants}
                rows = []
                by_key = {a["area_key"]: a for a in areas}
                for item in structured.get("recommendations", []):
                    area = by_key.get(str(item.get("area_key", "")))
                    if not area:
                        continue
                    match = by_name.get(str(item.get("recommended_name", "")).strip().lower(), {})
                    rows.append({"area_key": area["area_key"], "area": area["area"],
                                 "suggested_participant_id": match.get("participant_id", ""),
                                 "suggested_name": match.get("name", ""),
                                 "basis": str(item.get("reason", "")) or "no clear alignment found — assign manually"})
                covered = {r["area_key"] for r in rows}
                rows.extend(r for r in keyword_suggestions() if r["area_key"] not in covered)
                await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
                    "owner_suggestions": rows, "suggestion_status": "Ready"}})
            except Exception as exc:
                logger.error("SP owner suggestion failed for %s: %s", project_id, exc)
                await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
                    "owner_suggestions": keyword_suggestions(), "suggestion_status": "Ready"}})

        asyncio.create_task(run_suggestions())
        return {"status": "Generating"}

    @router.put("/admin/sp/projects/{project_id}/areas/{area_key}/owner")
    async def assign_owner(project_id: str, area_key: str, payload: OwnerAssignment, request: Request):
        await admin(request)
        plan = await current_plan(project_id)
        if plan.get("status") != "Finalized":
            raise HTTPException(status_code=409, detail="Finalize the Foundational Plan before assigning strategic areas")
        await owned_area(project_id, area_key)
        await owned_participant(project_id, payload.participant_id)
        await update_area(project_id, area_key, {"owner_participant_id": payload.participant_id, "status": "ASSIGNED"})
        return {"status": "ASSIGNED"}

    @router.put("/admin/sp/projects/{project_id}/areas/{area_key}/status")
    async def set_area_status(project_id: str, area_key: str, payload: AreaStatusPayload, request: Request):
        await admin(request)
        if payload.status not in AREA_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid area status")
        await owned_area(project_id, area_key)
        await update_area(project_id, area_key, {"status": payload.status})
        return {"status": payload.status}

    @router.post("/admin/sp/projects/{project_id}/areas/{area_key}/pack/generate")
    async def generate_pack(project_id: str, area_key: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        area = await owned_area(project_id, area_key)
        if plan.get("status") != "Finalized":
            raise HTTPException(status_code=409, detail="Finalize the Foundational Plan before generating Area Development Packs")
        if not area.get("owner_participant_id"):
            raise HTTPException(status_code=409, detail="Assign an Area Owner before generating this pack")
        if area.get("pack_status") == "Generating":
            return {"status": "Generating"}
        await update_area(project_id, area_key, {"pack_status": "Generating", "pack_generation_error": ""})
        reviews = await db.sp_participants.find(
            {"project_id": project_id, "review_status": "COMPLETED"}, {"_id": 0, "name": 1, "review_responses": 1}).to_list(300)
        comments = []
        for reviewer in reviews:
            for response in reviewer.get("review_responses", []):
                if response["area_key"] == area_key and (response.get("comment") or response["choice"] != "Support as Written"):
                    comments.append(f"{reviewer['name']}: [{response['choice']}] {response.get('comment', '')}".strip())
        context = (
            f"ORGANIZATION: {project['organization_name']}\nSTRATEGIC AREA: {area['area']}\n\n"
            f"FINALIZED FOUNDATIONAL PLAN (full text):\n{plan.get('finalized_text', plan.get('display_text', ''))}\n\n"
            f"THIS AREA'S FOUNDATIONAL CONTENT:\nDirection: {area.get('direction', '')}\n"
            f"Ideas: {'; '.join(area.get('ideas_shared', []))}\nPriorities: {'; '.join(area.get('proposed_priorities', []))}\n\n"
            f"BOARD REFINEMENT COMMENTS FOR THIS AREA:\n" + ("\n".join(comments) if comments else "None")
        )

        async def run_pack():
            try:
                structured = await generate_structured("strategic_area_pack", context)
                await update_area(project_id, area_key, {
                    "pack_status": "Draft", "pack_structured": structured,
                    "pack_text": pack_display(structured, area["area"], project["organization_name"]),
                    "pack_updated_at": now_iso()})
            except Exception as exc:
                logger.error("SP pack generation failed for %s/%s: %s", project_id, area_key, exc)
                await update_area(project_id, area_key, {"pack_status": "Failed", "pack_generation_error": str(exc)[:300]})

        asyncio.create_task(run_pack())
        return {"status": "Generating"}

    @router.get("/admin/sp/projects/{project_id}/areas/{area_key}/pack")
    async def get_pack(project_id: str, area_key: str, request: Request):
        await admin(request)
        area = await owned_area(project_id, area_key)
        return {"pack_status": area.get("pack_status", "NONE"), "pack_text": area.get("pack_text", ""),
                "pack_generation_error": area.get("pack_generation_error", "")}

    @router.put("/admin/sp/projects/{project_id}/areas/{area_key}/pack")
    async def edit_pack(project_id: str, area_key: str, payload: TextPayload, request: Request):
        await admin(request)
        area = await owned_area(project_id, area_key)
        if not area.get("pack_text"):
            raise HTTPException(status_code=409, detail="Generate the Area Development Pack first")
        await update_area(project_id, area_key, {"pack_text": payload.text, "pack_status": "Draft"})
        return {"pack_status": "Draft"}

    @router.post("/admin/sp/projects/{project_id}/areas/{area_key}/pack/approve")
    async def approve_pack(project_id: str, area_key: str, request: Request):
        await admin(request)
        area = await owned_area(project_id, area_key)
        if area.get("pack_status") not in {"Draft", "Approved"} or not area.get("pack_text"):
            raise HTTPException(status_code=409, detail="There is no draft pack ready to approve")
        await update_area(project_id, area_key, {"pack_status": "Approved", "pack_approved_at": now_iso()})
        return {"pack_status": "Approved"}

    def pack_email(project: dict, area: dict, owner: dict, link: str) -> dict:
        first = (owner.get("name") or "").split(" ")[0]
        organization = project["organization_name"]
        signature = project["founder_name"] + (f"\n{project['founder_title']}" if project.get("founder_title") else "") + f"\n{organization}"
        body = (
            f"Dear {first},\n\n"
            f"The Board has developed and refined the foundational direction for the {area['area']} area of {organization}'s strategic plan.\n\n"
            f"Based on your strengths, skills and role, we are asking you to take that agreed foundation and develop the detailed plan for {area['area']}.\n\n"
            "Your secure Strategic Area Development Pack below contains the agreed direction, the Board's ideas and comments for your area, and what still needs resolution.\n\n"
            "[OPEN MY AREA DEVELOPMENT PACK]\n\n"
            "When your detailed plan is ready, you can submit it through the same link.\n\n"
            f"Thank you for carrying this forward.\n\n{signature}"
        )
        return {"subject": f"Your Strategic Area: {area['area']} | {organization}", "body": body,
                "button_label": "OPEN MY AREA DEVELOPMENT PACK", "form_link": link}

    @router.get("/admin/sp/projects/{project_id}/areas/{area_key}/pack-email-preview")
    async def pack_email_preview(project_id: str, area_key: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        area = await owned_area(project_id, area_key)
        if not area.get("owner_participant_id"):
            raise HTTPException(status_code=409, detail="Assign an Area Owner first")
        owner = await owned_participant(project_id, area["owner_participant_id"])
        email = pack_email(project, area, owner, f"{origin_of(request)}/area-pack/{area['pack_token']}")
        return {"to_name": owner["name"], "to_email": owner["email"], **email}

    @router.post("/admin/sp/projects/{project_id}/areas/{area_key}/pack/send")
    async def send_pack(project_id: str, area_key: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        area = await owned_area(project_id, area_key)
        if area.get("pack_status") != "Approved":
            raise HTTPException(status_code=409, detail="Approve the Area Development Pack before sending it")
        owner = await owned_participant(project_id, area["owner_participant_id"])
        email = pack_email(project, area, owner, f"{origin_of(request)}/area-pack/{area['pack_token']}")
        try:
            await send_email(owner["email"], email["subject"], email["body"], email["button_label"], email["form_link"],
                             reply_to=project.get("founder_email", ""))
        except Exception as exc:
            logger.exception("SP pack send failed for %s/%s", project_id, area_key)
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc
        now = now_iso()
        updates = {"last_pack_sent_at": now}
        if area.get("status") == "ASSIGNED":
            updates["status"] = "IN DEVELOPMENT"
        await update_area(project_id, area_key, updates)
        return {"status": "sent", "sent_at": now}

    # ---------------- PUBLIC: AREA PACK + PLAN SUBMISSION ----------------

    async def area_by_pack_token(token: str):
        plan = await db.sp_plans.find_one({"areas.pack_token": token}, {"_id": 0})
        if not plan:
            raise HTTPException(status_code=404, detail="This link is not valid")
        area = next(a for a in plan["areas"] if a["pack_token"] == token)
        return plan, area

    @router.get("/area-pack/{token}")
    async def public_pack(token: str):
        plan, area = await area_by_pack_token(token)
        if area.get("pack_status") != "Approved":
            raise HTTPException(status_code=409, detail="This Area Development Pack is not available yet")
        project = await owned_project(plan["project_id"])
        owner = await owned_participant(plan["project_id"], area["owner_participant_id"]) if area.get("owner_participant_id") else {}
        return {"organization_name": project["organization_name"], "area": area["area"],
                "owner_name": owner.get("name", ""), "pack_text": area.get("pack_text", ""),
                "submitted": bool(area.get("submitted_plan")), "submitted_at": area.get("plan_submitted_at", ""), "draft_text": area.get("detailed_plan_text",""), "draft_status": area.get("detailed_plan_status","NONE"), "approved": area.get("detailed_plan_status")=="Approved"}

    @router.post("/area-pack/{token}/generate")
    async def generate_area_plan(token: str):
        plan, area = await area_by_pack_token(token)
        if area.get("pack_status") != "Approved":
            raise HTTPException(status_code=409, detail="This Area Development Pack is not available yet")
        project = await owned_project(plan["project_id"])
        owner = await owned_participant(plan["project_id"], area["owner_participant_id"]) if area.get("owner_participant_id") else {}
        context = (
            f"ORGANIZATION: {project['organization_name']}\nMISSION: {project.get('mission','')}\n"
            f"BOARD MEMBER: {owner.get('name','')}\nSTRATEGIC AREA: {area.get('area','')}\n"
            f"FOUNDATIONAL DIRECTION: {area.get('direction','')}\n"
            f"APPROVED PRIORITIES: {area.get('proposed_priorities',[])}\n"
            f"BOARD IDEAS: {area.get('ideas_shared',[])}\n"
            f"BOARD MEMBER'S OWN PLANNING RESPONSE: {owner.get('response',{})}\n"
            f"FOUNDATIONAL STRATEGIC PLAN: {plan.get('display_text','')}"
        )
        prompt = """Build ONLY this board member's detailed plan for the assigned strategic area from the supplied facts and Board decisions. Do not invent facts, dates, budgets, people, programs or commitments. If a required detail was not supplied, write a clear decision placeholder instead of guessing. Use these headings in this exact order: Strategic Area / Purpose; What We Must Accomplish; Priorities/Objectives; Step-by-Step Actions; People/Team Required; Technology/Tools Required; Leadership/Oversight Role; Budget/Cost to Execute at 100%; Timeline/Milestones; Measures/How We Know It's Working. The output must be practical, detailed, editable and ready for the board member to refine."""
        g = await generate_structured("strategic_detailed_area_plan", context, prompt)
        sections = g.get("sections", [])
        text = "\n\n".join(f"{str(x.get('heading','')).upper()}\n{str(x.get('content',''))}" for x in sections).strip()
        if not text:
            text = str(g.get("display_text") or g.get("plan_text") or "").strip()
        if not text:
            raise HTTPException(status_code=502, detail="AI did not return a usable detailed plan. Please try again.")
        now=now_iso()
        await db.sp_plans.update_one({"project_id":plan["project_id"],"areas.area_key":area["area_key"]},{"$set":{"areas.$.detailed_plan_text":text,"areas.$.detailed_plan_status":"Draft","areas.$.status":"IN DEVELOPMENT","areas.$.detailed_plan_updated_at":now},"$push":{"areas.$.detailed_plan_versions":{"plan_text":text,"source":"ai","created_at":now}}})
        return {"status":"Draft","plan_text":text}

    @router.put("/area-pack/{token}/plan")
    async def save_area_plan(token: str, payload: AreaPlanEdit):
        plan, area = await area_by_pack_token(token)
        if area.get("pack_status") != "Approved": raise HTTPException(409,"This Area Development Pack is not available yet")
        if area.get("detailed_plan_status")=="Approved": raise HTTPException(409,"This detailed plan is approved and locked.")
        now=now_iso()
        await db.sp_plans.update_one({"project_id":plan["project_id"],"areas.area_key":area["area_key"]},{"$set":{"areas.$.detailed_plan_text":payload.plan_text,"areas.$.detailed_plan_status":"Draft","areas.$.detailed_plan_updated_at":now},"$push":{"areas.$.detailed_plan_versions":{"plan_text":payload.plan_text,"source":"edited","created_at":now}}})
        return {"status":"Draft"}

    @router.post("/area-pack/{token}/approve")
    async def approve_area_plan(token: str):
        plan, area = await area_by_pack_token(token)
        text=str(area.get("detailed_plan_text") or "").strip()
        if not text: raise HTTPException(409,"Generate and review the detailed plan before approving it")
        now=now_iso()
        await db.sp_plans.update_one({"project_id":plan["project_id"],"areas.area_key":area["area_key"]},{"$set":{"areas.$.detailed_plan_status":"Approved","areas.$.detailed_plan_approved_at":now,"areas.$.submitted_plan":text,"areas.$.plan_submitted_at":now,"areas.$.status":"SUBMITTED"},"$push":{"areas.$.submission_history":{"plan_text":text,"submitted_at":now,"approved":True}}})
        return {"status":"Approved"}

    @router.get("/area-pack/{token}/pdf")
    async def approved_area_plan_pdf(token: str):
        plan, area = await area_by_pack_token(token)
        if area.get("detailed_plan_status")!="Approved" or not area.get("submitted_plan"): raise HTTPException(409,"Approve the detailed plan before downloading it")
        project=await owned_project(plan["project_id"])
        owner=await owned_participant(plan["project_id"],area["owner_participant_id"]) if area.get("owner_participant_id") else {}
        return build_portfolio_pdf(f"DETAILED STRATEGIC PLAN — {area['area']}",project["organization_name"],{"organization_name":project["organization_name"],"issued_by":owner.get("name","Board Member")},area["submitted_plan"])

    @router.post("/area-pack/{token}/submit", status_code=201)
    async def submit_area_plan(token: str, payload: AreaPlanSubmission):
        # Backward-compatible endpoint: manual submission now saves a draft; explicit approval is required.
        plan, area = await area_by_pack_token(token)
        if area.get("pack_status") != "Approved": raise HTTPException(409,"This Area Development Pack is not available yet")
        now=now_iso()
        await db.sp_plans.update_one({"project_id":plan["project_id"],"areas.area_key":area["area_key"]},{"$set":{"areas.$.detailed_plan_text":payload.plan_text,"areas.$.detailed_plan_status":"Draft","areas.$.detailed_plan_updated_at":now}})
        return {"status":"Draft"}

    @router.put("/admin/sp/projects/{project_id}/areas/{area_key}/adoption")
    async def record_adoption(project_id: str, area_key: str, payload: AdoptionPayload, request: Request):
        await admin(request)
        area = await owned_area(project_id, area_key)
        if not area.get("submitted_plan"):
            raise HTTPException(status_code=409, detail="This area's detailed plan has not been submitted yet")
        await update_area(project_id, area_key, {
            "adoption_conclusion": payload.conclusion, "adopted": payload.adopted,
            "adoption_recorded_at": now_iso(), "status": "READY FOR BOARD" if not payload.adopted else area.get("status", "SUBMITTED")})
        return {"status": "recorded"}

    # ---------------- FINAL STRATEGIC PLAN ----------------

    @router.post("/admin/sp/projects/{project_id}/final-plan/generate")
    async def generate_final(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        adopted = [a for a in plan.get("areas", []) if a.get("adopted") and a.get("submitted_plan")]
        if not adopted:
            raise HTTPException(status_code=409, detail="No adopted area plans exist yet. Record the Board's adoption outcomes first.")
        if plan.get("final_status") == "Generating":
            return {"status": "Generating"}
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
            "final_status": "Generating", "final_generation_error": "", "updated_at": now_iso()}})
        context = (
            f"ORGANIZATION: {project['organization_name']}\nMISSION: {project.get('mission', '')}\n\n"
            f"FINALIZED FOUNDATIONAL PLAN:\n{plan.get('finalized_text', '')}\n\n"
            "ADOPTED STRATEGIC AREA PLANS (in order):\n\n"
            + "\n\n".join(
                f"AREA: {a['area']}\nBOARD ADOPTION CONCLUSION: {a.get('adoption_conclusion', '')}\nADOPTED DETAILED PLAN:\n{a['submitted_plan']}"
                for a in adopted)
        )

        async def run_final():
            try:
                structured = await generate_structured("strategic_final_plan", context)
                await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
                    "final_status": "Draft", "final_structured": structured,
                    "final_display_text": final_display(structured, project["organization_name"]),
                    "updated_at": now_iso()}})
            except Exception as exc:
                logger.error("SP final plan generation failed for %s: %s", project_id, exc)
                await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
                    "final_status": "Failed", "final_generation_error": str(exc)[:300], "updated_at": now_iso()}})

        asyncio.create_task(run_final())
        return {"status": "Generating"}

    @router.put("/admin/sp/projects/{project_id}/final-plan")
    async def edit_final(project_id: str, payload: TextPayload, request: Request):
        await admin(request)
        plan = await current_plan(project_id)
        if not plan.get("final_display_text"):
            raise HTTPException(status_code=409, detail="Build the Final Strategic Plan first")
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
            "final_display_text": payload.text, "final_status": "Draft", "updated_at": now_iso()}})
        return {"final_status": "Draft"}

    @router.post("/admin/sp/projects/{project_id}/final-plan/approve")
    async def approve_final(project_id: str, request: Request):
        await admin(request)
        plan = await current_plan(project_id)
        if plan.get("final_status") not in {"Draft", "Approved"} or not plan.get("final_display_text"):
            raise HTTPException(status_code=409, detail="There is no draft Final Strategic Plan ready to approve")
        token = plan.get("final_share_token") or secrets.token_urlsafe(32)
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
            "final_status": "Approved", "final_share_token": token, "final_approved_at": now_iso()}})
        return {"final_status": "Approved", "final_share_token": token}

    @router.post("/admin/sp/projects/{project_id}/meeting-guide/generate")
    async def generate_meeting_guide(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        submitted = [a for a in plan.get("areas", []) if a.get("submitted_plan")]
        if plan.get("status") != "Finalized" or not submitted:
            raise HTTPException(status_code=409, detail="The meeting guide needs the finalized plan and at least one submitted area plan")
        if plan.get("meeting_status") == "Generating":
            return {"status": "Generating"}
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {"meeting_status": "Generating", "meeting_generation_error": ""}})
        reviews = await db.sp_participants.find({"project_id": project_id, "review_status": "COMPLETED"}, {"_id": 0, "name": 1, "review_responses": 1}).to_list(300)
        flagged = []
        for reviewer in reviews:
            for r in reviewer.get("review_responses", []):
                if r["choice"] != "Support as Written" or r.get("comment"):
                    flagged.append(f"[{r['area_key']}] {reviewer['name']}: {r['choice']} — {r.get('comment', '')}")
        owners = {p["participant_id"]: p["name"] for p in await db.sp_participants.find({"project_id": project_id}, {"_id": 0}).to_list(300)}
        context = (f"ORGANIZATION: {project['organization_name']}\nFACILITATOR: {project['founder_name']}\n\n"
                   f"FINAL FOUNDATIONAL PLAN:\n{plan.get('finalized_text', '')}\n\n"
                   "AREAS, OWNERS AND SUBMITTED DETAILED PLANS (in order):\n\n"
                   + "\n\n".join(f"AREA: {a['area']} (Owner: {owners.get(a.get('owner_participant_id', ''), 'unassigned')})\n"
                                 f"SUBMITTED DETAILED PLAN:\n{a['submitted_plan']}" for a in submitted)
                   + "\n\nOUTSTANDING / FLAGGED ISSUES AND REFINEMENT HISTORY:\n" + ("\n".join(flagged) if flagged else "None"))

        async def run_guide():
            try:
                structured = await generate_structured("strategic_meeting_guide", context)
                text = "\n".join(["STRATEGIC PLAN ADOPTION MEETING FACILITATION GUIDE", project["organization_name"], ""]
                                 + [f"{str(s.get('heading', '')).upper()}\n{s.get('content', '')}\n" for s in structured.get("sections", [])]).strip()
                await db.sp_plans.update_one({"project_id": project_id}, {"$set": {"meeting_status": "Draft", "meeting_guide_text": text}})
            except Exception as exc:
                logger.error("SP meeting guide failed for %s: %s", project_id, exc)
                await db.sp_plans.update_one({"project_id": project_id}, {"$set": {"meeting_status": "Failed", "meeting_generation_error": str(exc)[:300]}})

        asyncio.create_task(run_guide())
        return {"status": "Generating"}

    @router.put("/admin/sp/projects/{project_id}/meeting-guide")
    async def edit_meeting_guide(project_id: str, payload: TextPayload, request: Request):
        await admin(request)
        if not (await current_plan(project_id)).get("meeting_guide_text"):
            raise HTTPException(status_code=409, detail="Generate the meeting facilitation guide first")
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {"meeting_guide_text": payload.text, "meeting_status": "Draft"}})
        return {"meeting_status": "Draft"}

    @router.post("/admin/sp/projects/{project_id}/meeting-guide/approve")
    async def approve_meeting_guide(project_id: str, request: Request):
        await admin(request)
        plan = await current_plan(project_id)
        if plan.get("meeting_status") not in {"Draft", "Approved"} or not plan.get("meeting_guide_text"):
            raise HTTPException(status_code=409, detail="There is no draft meeting guide ready to approve")
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {"meeting_status": "Approved"}})
        return {"meeting_status": "Approved"}

    @router.get("/admin/sp/projects/{project_id}/meeting-guide/pdf")
    async def meeting_guide_pdf(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        if not plan.get("meeting_guide_text"):
            raise HTTPException(status_code=404, detail="The meeting guide has not been generated yet")
        return build_portfolio_pdf("ADOPTION MEETING FACILITATION GUIDE", project["organization_name"],
                                   {"organization_name": project["organization_name"], "issued_by": project["founder_name"]},
                                   plan["meeting_guide_text"])

    @router.get("/admin/sp/projects/{project_id}/final-plan/email-preview")
    async def final_email_preview(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        if plan.get("final_status") != "Approved":
            raise HTTPException(status_code=409, detail="Approve the Final Strategic Plan before preparing the delivery email")
        link = f"{origin_of(request)}/strategic-plan/{plan['final_share_token']}"
        body = (f"Dear {project['founder_name'].split(' ')[0]},\n\n"
                f"The Strategic Plan for {project['organization_name']} is complete.\n\n"
                "It combines the detailed plans your Board Members developed and adopted, built on the foundation the whole Board shaped together.\n\n"
                "[VIEW OUR STRATEGIC PLAN]\n\n"
                "You can view it online or download the PDF from the same page.\n\nRooney Akpesiri\nThe Nonprofit Board Builder")
        return {"to_name": project["founder_name"], "to_email": project["founder_email"],
                "subject": f"Your Strategic Plan Is Ready | {project['organization_name']}",
                "body": body, "button_label": "VIEW OUR STRATEGIC PLAN", "form_link": link}

    @router.post("/admin/sp/projects/{project_id}/final-plan/send")
    async def send_final(project_id: str, request: Request):
        email = await final_email_preview(project_id, request)
        try:
            await send_email(email["to_email"], email["subject"], email["body"], email["button_label"], email["form_link"])
        except Exception as exc:
            logger.exception("SP final plan send failed for %s", project_id)
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc
        now = now_iso()
        await db.sp_plans.update_one({"project_id": project_id}, {"$push": {"final_sends": {"to_email": email["to_email"], "sent_at": now}}})
        return {"status": "sent", "sent_at": now}

    @router.get("/strategic-plan/{token}")
    async def public_final_plan(token: str):
        plan = await db.sp_plans.find_one({"final_share_token": token, "final_status": "Approved"}, {"_id": 0})
        if not plan:
            raise HTTPException(status_code=404, detail="This link is not valid")
        project = await owned_project(plan["project_id"])
        return {"title": "Strategic Plan", "organization_name": project["organization_name"],
                "display_text": plan["final_display_text"], "issued_by": project["founder_name"]}

    @router.get("/admin/sp/projects/{project_id}/final-plan/pdf")
    async def final_pdf(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        if not plan.get("final_display_text"):
            raise HTTPException(status_code=404, detail="The Final Strategic Plan has not been built yet")
        return build_portfolio_pdf("STRATEGIC PLAN", project["organization_name"],
                                   {"organization_name": project["organization_name"], "issued_by": project["founder_name"]},
                                   plan["final_display_text"])

    # ---------------- SIMPLIFIED PROJECT CREATION (pasted form content) ----------------

    @router.post("/admin/sp/projects/generate", status_code=201)
    async def generate_project(payload: ProjectGenerate, request: Request):
        await admin(request)
        project = {
            "project_id": str(uuid.uuid4()), "organization_name": payload.organization_name,
            "founder_name": payload.founder_name, "founder_email": str(payload.founder_email).lower(),
            "founder_title": payload.founder_title, "mission": payload.mission,
            "generic_form_token": secrets.token_urlsafe(32),
            "status": "Active", "created_at": now_iso(),
        }
        await db.sp_projects.insert_one({**project})
        project_id = project["project_id"]
        now = now_iso()
        text = payload.form_content
        await db.sp_forms.insert_one({
            "form_id": str(uuid.uuid4()), "project_id": project_id, "status": "Generating",
            "generation_error": "", "source_filename": "Pasted form content",
            "master_source_text": text[:120000], "approved_version": 0, "approved_versions": [],
            "created_at": now, "updated_at": now})

        async def run_structure():
            try:
                context = (
                    f"ORGANIZATION: {project['organization_name']}\nMISSION: {project.get('mission', '')}\n\n"
                    f"FOUNDER'S SUPPLIED MASTER STRATEGIC PLANNING FORM (the ONLY authority for questions):\n{text[:60000]}"
                )
                structured = await generate_structured("strategic_planning_form_structure", context)
                content_payload = {"introduction": str(structured.get("introduction", "")).strip(),
                                   "sections": assign_question_ids(structured.get("sections", []))}
                stamp = now_iso()
                await db.sp_forms.update_one({"project_id": project_id}, {"$set": {
                    "status": "Approved", "content": content_payload, "approved_version": 1,
                    "approved_at": stamp, "updated_at": stamp},
                    "$push": {"approved_versions": {"version": 1, "content": content_payload, "approved_at": stamp}}})
            except Exception as exc:
                logger.error("SP project form generation failed for %s: %s", project_id, exc)
                await db.sp_forms.update_one({"project_id": project_id}, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300], "updated_at": now_iso()}})

        asyncio.create_task(run_structure())
        return {"project": project, "status": "Generating"}

    # ---------------- GENERIC FORM LINK + EMAIL TO SEND ----------------

    def generic_form_email(project: dict, link: str) -> dict:
        organization = project["organization_name"]
        signature = sp_signature(project["founder_name"], project.get("founder_title", ""), organization)
        return sp_generic_form_invitation_email(organization, link, signature)

    @router.get("/admin/sp/projects/{project_id}/form-email")
    async def form_email(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        form = await db.sp_forms.find_one({"project_id": project_id}, {"_id": 0, "status": 1})
        if not form or form.get("status") != "Approved":
            raise HTTPException(status_code=409, detail="The Strategic Planning Form is not ready yet")
        if not project.get("generic_form_token"):
            token = secrets.token_urlsafe(32)
            await db.sp_projects.update_one({"project_id": project_id}, {"$set": {"generic_form_token": token}})
            project["generic_form_token"] = token
        link = f"{origin_of(request)}/strategic-planning-form/{project['generic_form_token']}"
        return generic_form_email(project, link)

    # ---------------- EMAIL DRAFT PLAN TO ALL RESPONDENTS ----------------

    @router.get("/admin/sp/projects/{project_id}/review-email-preview")
    async def bulk_review_email_preview(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        if plan.get("status") not in {"Approved", "Synchronized", "Finalized"}:
            raise HTTPException(status_code=409, detail="Approve the draft plan before preparing the Board review email")
        respondents = await db.sp_participants.find({"project_id": project_id, "status": "COMPLETED"}, {"_id": 0}).to_list(300)
        if not respondents:
            raise HTTPException(status_code=409, detail="No Board Members have completed the Strategic Planning Form yet")
        sample = review_email(project, respondents[0], "each Board Member receives their own secure review link automatically")
        return {"recipients": [{"name": r["name"], "email": r["email"]} for r in respondents],
                "subject": sample["subject"], "body": sample["body"]}

    @router.post("/admin/sp/projects/{project_id}/send-review-all")
    async def send_review_all(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        if plan.get("status") not in {"Approved", "Synchronized", "Finalized"}:
            raise HTTPException(status_code=409, detail="Approve the draft plan before sending it for Board review")
        respondents = await db.sp_participants.find({"project_id": project_id, "status": "COMPLETED"}, {"_id": 0}).to_list(300)
        if not respondents:
            raise HTTPException(status_code=409, detail="No Board Members have completed the Strategic Planning Form yet")
        sent, failed = [], []
        now = now_iso()
        for record in respondents:
            email = review_email(project, record, f"{origin_of(request)}/strategic-plan-review/{record['review_token']}")
            try:
                await send_email(record["email"], email["subject"], email["body"], email["button_label"], email["form_link"],
                                 reply_to=project.get("founder_email", ""))
            except Exception:
                logger.exception("SP bulk review send failed for %s", record["participant_id"])
                failed.append(record["name"])
                continue
            updates = {"last_review_sent_at": now}
            if record.get("review_status") in {"", "NOT SENT", None}:
                updates["review_status"] = "SENT"
            if not record.get("review_version"):
                updates["review_version"] = plan.get("review_version", 1)
            await db.sp_participants.update_one({"participant_id": record["participant_id"]}, {"$set": updates})
            sent.append(record["name"])
        return {"status": "sent", "sent": sent, "failed": failed, "sent_at": now}

    # ---------------- SYNCHRONIZE FOUNDATIONAL PLAN ----------------

    @router.post("/admin/sp/projects/{project_id}/plan/synchronize")
    async def synchronize_plan(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        if plan.get("status") == "Synchronizing":
            return {"status": "Synchronizing"}
        if plan.get("status") not in {"Approved", "Synchronized", "Finalized"}:
            raise HTTPException(status_code=409, detail="Approve the draft plan before synchronizing the Board's review")
        reviews = await db.sp_participants.find({"project_id": project_id, "review_status": "COMPLETED"}, {"_id": 0}).to_list(300)
        if not reviews:
            raise HTTPException(status_code=409, detail="No Board review responses have been received yet")
        responses = await db.sp_participants.find({"project_id": project_id, "status": "COMPLETED"}, {"_id": 0}).to_list(300)
        previous_status = plan.get("status")
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {"status": "Synchronizing", "generation_error": ""}})
        area_titles = {a["area_key"]: a["area"] for a in plan.get("areas", [])}
        review_lines = []
        for reviewer in reviews:
            for r in reviewer.get("review_responses", []):
                review_lines.append(f"{reviewer['name']} on [{area_titles.get(r['area_key'], r['area_key'])}]: {r['choice']}"
                                    + (f" — {r['comment']}" if r.get("comment") else ""))
        context = (
            f"ORGANIZATION: {project['organization_name']}\nMISSION: {project.get('mission', '')}\n\n"
            f"CURRENT DRAFT FOUNDATIONAL PLAN:\n{plan.get('display_text', '')}\n\n"
            "EVERY BOARD REVIEW CHOICE AND COMMENT:\n" + "\n".join(review_lines) + "\n\n"
            "ORIGINAL BOARD MEMBER RESPONSES:\n\n" + "\n\n".join(response_context(r) for r in responses)
        )

        async def run_sync():
            try:
                structured = await generate_structured("strategic_plan_synchronized", context)
                prior = {a["area"].strip().lower(): a for a in plan.get("areas", [])}
                areas = []
                for index, area in enumerate(structured.get("areas", []), start=1):
                    title = str(area.get("area", ""))
                    old = prior.get(title.strip().lower(), {})
                    areas.append({
                        "area_key": old.get("area_key", f"area{index}n"), "area": title,
                        "direction": str(area.get("direction", "")),
                        "ideas_shared": [str(i) for i in area.get("ideas_shared", [])],
                        "proposed_priorities": [str(p) for p in area.get("proposed_priorities", [])],
                        "status": old.get("status", "NOT ASSIGNED"),
                        "owner_participant_id": old.get("owner_participant_id", ""),
                        "pack_status": old.get("pack_status", "NONE"),
                        "pack_token": old.get("pack_token") or secrets.token_urlsafe(32),
                        "pack_text": old.get("pack_text", ""),
                        "submitted_plan": old.get("submitted_plan", ""),
                        "plan_submitted_at": old.get("plan_submitted_at", ""),
                        "adoption_conclusion": old.get("adoption_conclusion", ""),
                        "adopted": old.get("adopted", False)})
                await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
                    "status": "Synchronized", "structured": structured, "areas": areas,
                    "display_text": plan_display(structured, project["organization_name"]),
                    "synchronized_at": now_iso(), "updated_at": now_iso()}})
            except Exception as exc:
                logger.error("SP plan synchronization failed for %s: %s", project_id, exc)
                await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
                    "status": previous_status, "generation_error": f"Synchronization failed: {str(exc)[:280]}"}})

        asyncio.create_task(run_sync())
        return {"status": "Synchronizing"}

    # ---------------- ONE-PAGE ACTION PLAN ----------------

    @router.post("/admin/sp/projects/{project_id}/action-plan/generate")
    async def generate_action_plan(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        if plan.get("status") not in {"Synchronized", "Finalized"}:
            raise HTTPException(status_code=409, detail="Synchronize or finalize the Foundational Plan before generating the Action Plan")
        if plan.get("action_status") == "Generating":
            return {"status": "Generating"}
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {"action_status": "Generating", "action_generation_error": ""}})
        owners = {p["participant_id"]: p["name"] for p in await db.sp_participants.find({"project_id": project_id}, {"_id": 0}).to_list(300)}
        ownership = "\n".join(f"- {a['area']}: {owners.get(a.get('owner_participant_id', ''), 'unassigned')}" for a in plan.get("areas", []))
        context = (f"ORGANIZATION: {project['organization_name']}\nMISSION: {project.get('mission', '')}\n\n"
                   f"SYNCHRONIZED FOUNDATIONAL STRATEGIC PLAN:\n{plan.get('finalized_text') or plan.get('display_text', '')}\n\n"
                   f"AREA OWNERSHIP (where assigned):\n{ownership}")

        async def run_action():
            try:
                structured = await generate_structured("strategic_action_plan", context)
                text = "\n".join(["STRATEGIC PLANNING ACTION PLAN", project["organization_name"], ""]
                                 + [f"{str(s.get('heading', '')).upper()}\n{s.get('content', '')}\n" for s in structured.get("sections", [])]).strip()
                await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
                    "action_status": "Draft", "action_text": text, "action_updated_at": now_iso()}})
            except Exception as exc:
                logger.error("SP action plan failed for %s: %s", project_id, exc)
                await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
                    "action_status": "Failed", "action_generation_error": str(exc)[:300]}})

        asyncio.create_task(run_action())
        return {"status": "Generating"}

    @router.put("/admin/sp/projects/{project_id}/action-plan")
    async def edit_action_plan(project_id: str, payload: TextPayload, request: Request):
        await admin(request)
        if not (await current_plan(project_id)).get("action_text"):
            raise HTTPException(status_code=409, detail="Generate the Action Plan first")
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {"action_text": payload.text, "action_status": "Draft"}})
        return {"action_status": "Draft"}

    @router.post("/admin/sp/projects/{project_id}/action-plan/approve")
    async def approve_action_plan(project_id: str, request: Request):
        await admin(request)
        plan = await current_plan(project_id)
        if plan.get("action_status") not in {"Draft", "Approved"} or not plan.get("action_text"):
            raise HTTPException(status_code=409, detail="There is no draft Action Plan ready to approve")
        token = plan.get("action_share_token") or secrets.token_urlsafe(32)
        await db.sp_plans.update_one({"project_id": project_id}, {"$set": {
            "action_status": "Approved", "action_share_token": token, "action_approved_at": now_iso()}})
        return {"action_status": "Approved", "action_share_token": token}

    @router.get("/admin/sp/projects/{project_id}/action-plan/pdf")
    async def action_plan_pdf(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        if not plan.get("action_text"):
            raise HTTPException(status_code=404, detail="The Action Plan has not been generated yet")
        return build_portfolio_pdf("STRATEGIC PLANNING ACTION PLAN", project["organization_name"],
                                   {"organization_name": project["organization_name"], "issued_by": project["founder_name"]},
                                   plan["action_text"])

    @router.get("/admin/sp/projects/{project_id}/action-plan/email-preview")
    async def action_plan_email_preview(project_id: str, request: Request):
        await admin(request)
        project = await owned_project(project_id)
        plan = await current_plan(project_id)
        if plan.get("action_status") != "Approved":
            raise HTTPException(status_code=409, detail="Approve the Action Plan before preparing the delivery email")
        link = f"{origin_of(request)}/strategic-action-plan/{plan['action_share_token']}"
        body = (f"Dear {project['founder_name'].split(' ')[0]},\n\n"
                f"The one-page Strategic Planning Action Plan for {project['organization_name']} is ready.\n\n"
                "It summarizes your organization's immediate strategic direction and the practical next actions that follow from your Foundational Strategic Plan.\n\n"
                "[VIEW OUR ACTION PLAN]\n\n"
                "You can view it online or download the PDF from the same page.\n\nRooney Akpesiri\nThe Nonprofit Board Builder")
        return {"to_name": project["founder_name"], "to_email": project["founder_email"],
                "subject": f"Your Strategic Planning Action Plan | {project['organization_name']}",
                "body": body, "button_label": "VIEW OUR ACTION PLAN", "form_link": link}

    @router.post("/admin/sp/projects/{project_id}/action-plan/send")
    async def send_action_plan(project_id: str, request: Request):
        email = await action_plan_email_preview(project_id, request)
        try:
            await send_email(email["to_email"], email["subject"], email["body"], email["button_label"], email["form_link"])
        except Exception as exc:
            logger.exception("SP action plan send failed for %s", project_id)
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc
        now = now_iso()
        await db.sp_plans.update_one({"project_id": project_id}, {"$push": {"action_sends": {"to_email": email["to_email"], "sent_at": now}}})
        return {"status": "sent", "sent_at": now}

    @router.get("/strategic-action-plan/{token}")
    async def public_action_plan(token: str):
        plan = await db.sp_plans.find_one({"action_share_token": token, "action_status": "Approved"}, {"_id": 0})
        if not plan:
            raise HTTPException(status_code=404, detail="This link is not valid")
        project = await owned_project(plan["project_id"])
        return {"title": "Strategic Planning Action Plan", "organization_name": project["organization_name"],
                "display_text": plan["action_text"], "issued_by": project["founder_name"],
                "pdf_available": False}

    return router

# Guided $497 Strategic Planning dashboard adapter. Keeps the customer workflow separate from admin routing.
def create_guided_strategic_planning_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/guided/strategic-planning")

    async def paid(session_id: str):
        tx=await db.payment_transactions.find_one({"session_id":session_id,"payment_status":"paid","purchase_source":"strategic_planning_497"},{"_id":0})
        if not tx: raise HTTPException(status_code=402,detail="Paid Strategic Planning access could not be confirmed")
        lead=await db.guided_product_leads.find_one({"token":tx.get("guided_lead_token","")},{"_id":0}) or {}
        intake=await db.guided_product_intakes.find_one({"session_id":session_id,"product":"strategic-planning"},{"_id":0}) or {}
        return tx,lead,intake

    async def ensure_project(session_id: str):
        tx,lead,intake=await paid(session_id); p=await db.sp_projects.find_one({"guided_session_id":session_id},{"_id":0})
        if p:return p
        ans=intake.get("answers") or {}; now=now_iso(); p={"project_id":str(uuid.uuid4()),"guided_session_id":session_id,"organization_name":lead.get("organization") or "Organization","founder_name":lead.get("name") or "Organization Leader","founder_email":lead.get("email") or "","founder_title":"","mission":ans.get("mission",""),"status":"Active","generic_form_token":secrets.token_urlsafe(32),"created_at":now}
        await db.sp_projects.insert_one(p.copy());return p

    async def detail(p):
        participants=await db.sp_participants.find({"project_id":p["project_id"]},{"_id":0}).to_list(300);form=await db.sp_forms.find_one({"project_id":p["project_id"]},{"_id":0}) or {};plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};by={x["participant_id"]:x for x in participants};areas=[]
        for a in plan.get("areas",[]): areas.append({**a,"owner_name":by.get(a.get("owner_participant_id",""),{}).get("name","")})
        return {**p,"participants":participants,"form":form,"lead_form_token":next((x.get("form_token","") for x in participants if x.get("role")=="Lead User"),""),"plan":{"status":plan.get("status","NONE"),"display_text":plan.get("display_text",""),"share_url":(f"/strategic-draft/{plan.get('share_token')}" if plan.get("share_token") else "")},"areas":areas,"meeting_guide_text":plan.get("meeting_guide_text",""),"final_plan":{"status":plan.get("final_status","NONE"),"display_text":plan.get("final_display_text","")},"portfolios":plan.get("leadership_portfolios",[])}

    @router.get("/workspace")
    async def workspace(session_id:str):
        _,lead,_=await paid(session_id);p=await ensure_project(session_id);research=await db.sp_community_research.find_one({"project_id":p["project_id"]},{"_id":0})
        return {"organization_name":lead.get("organization",""),"project":await detail(p),"community_research":research}

    @router.post("/prepare-form")
    async def prepare_form(request:Request):
        body=await request.json();sid=body.get("session_id","");p=await ensure_project(sid);_,_,intake=await paid(sid);a=intake.get("answers") or {}
        programs=a.get("programs") or a.get("areas") or ""; program_lines=[x.strip(" -•\t") for x in str(programs).split("\n") if x.strip()][:12]
        qs=[
            ("Mission",[f"Our mission is: {a.get('mission') or p.get('mission') or 'Mission not supplied'}. Review it. What should remain, change or become clearer?"]),
            ("Goals",[f"Our lead user identified these present goals: {a.get('goals','')}. Review them. What should remain, change or be added for the next 12–24 months?"]),
            ("Objectives",[f"Our lead user identified these present objectives: {a.get('objectives','')}. Review them. What should remain, change or be added so progress is clear and measurable?"]),
        ]
        if program_lines: qs.append(("Programs",[f"Review this program or service: {x}. What should we continue, stop, improve or build so it contributes fully to our mission and goals?" for x in program_lines]))
        review_sections=[
            ("Team Building","team_building","team, staff, volunteer and leadership capacity"),
            ("Operations","operations","operational systems, policies and processes"),
            ("Marketing","marketing","marketing, visibility and communications"),
            ("Partnerships","partnerships","partnerships and relationships"),
            ("Fundraising","fundraising","fundraising approach and capacity"),
            ("Technology","technology","technology and tools"),
            ("Budget","budget","budget and the resources required for execution"),
            ("Organizational Priorities","priorities","organizational priorities"),
            ("Action Planning","action_planning","major actions and execution priorities"),
        ]
        for title,key,label in review_sections:
            supplied=str(a.get(key) or "").strip()
            qs.append((title,[f"Our lead user shared this about our {label}: {supplied or 'No current detail was supplied.'} Review this area. What should remain, change, be added or be prioritized?"]))
        qs[-1][1].append("Which areas are you personally willing and able to help lead or oversee? Explain why.")
        sections=[]
        for i,(title,prompts) in enumerate(qs,1):sections.append({"key":f"s{i}","title":title,"questions":[{"id":f"s{i}_q{j}","prompt":q,"type":"long","options":[],"required":True} for j,q in enumerate(prompts,1)]})
        content={"introduction":f"We are reviewing the complete direction of {p['organization_name']} together. Please answer from your experience and perspective as a Board Member. Your ideas will be combined with the rest of the Board's thinking to create our first Strategic Plan Draft.","sections":sections};now=now_iso()
        await db.sp_forms.update_one({"project_id":p["project_id"]},{"$set":{"status":"Approved","content":content,"approved_version":1,"approved_at":now,"updated_at":now},"$setOnInsert":{"form_id":str(uuid.uuid4()),"created_at":now}},upsert=True);return {"status":"Approved"}

    @router.get("/form-email")
    async def guided_form_email(session_id:str,request:Request):
        p=await ensure_project(session_id);form=await db.sp_forms.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if form.get("status")!="Approved":raise HTTPException(409,"Prepare the Strategic Planning Form first")
        link=f"{origin_of(request)}/strategic-planning-form/{p['generic_form_token']}";e=generic_form_email(p,link);return {**e,"form_link":link}

    @router.post("/community-research")
    async def community_research(request:Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));existing=await db.sp_community_research.find_one({"project_id":p["project_id"]},{"_id":0});
        if existing:return existing
        token=secrets.token_urlsafe(32);posts=[f"We are reviewing the future direction of {p['organization_name']} and want to hear directly from the community. Share what you believe the real need is and what would make the strongest difference.",f"What does our community need most in relation to {p.get('mission') or 'our mission'}? We are listening before we finalize our next strategic plan.",f"Help shape the next chapter of {p['organization_name']}. Tell us what is working, what is missing and what approach you believe would create the greatest impact.",f"Good strategy starts by listening. If you have lived experience, professional insight or community knowledge connected to our mission, we would value your perspective.",f"Our Board is preparing its next strategic plan. Take a few minutes to tell us about the need, the best way to address it and how you or others could help."]
        doc={"project_id":p["project_id"],"token":token,"social_posts":posts,"response_count":0,"created_at":now_iso()};await db.sp_community_research.insert_one(doc.copy());return doc

    @router.get("/community-research/{token}")
    async def public_community_research(token:str):
        doc=await db.sp_community_research.find_one({"token":token},{"_id":0})
        if not doc:raise HTTPException(404,"This Community Need Research link is not valid")
        p=await owned_project(doc["project_id"])
        return {"organization_name":p["organization_name"],"mission":p.get("mission",""),"questions":["What do you believe is the most important need or challenge connected to this mission?","Who is most affected by this need, and what does it look like in real life?","What approaches do you believe would make the strongest difference?","What is currently missing from the way this need is being addressed?","How could you, your organization, your network or your community help address this need?"]}

    @router.post("/community-research/{token}")
    async def submit_community_research(token:str,request:Request):
        doc=await db.sp_community_research.find_one({"token":token},{"_id":0})
        if not doc:raise HTTPException(404,"This Community Need Research link is not valid")
        body=await request.json();responses=body.get("answers") or []
        if len(responses)!=5 or any(not str(x).strip() for x in responses):raise HTTPException(422,"Please answer all five questions")
        await db.sp_community_research.update_one({"token":token},{"$push":{"responses":{"name":str(body.get("name","")).strip(),"email":str(body.get("email","")).strip(),"answers":responses,"submitted_at":now_iso()}},"$inc":{"response_count":1}})
        return {"status":"submitted"}

    @router.post("/generate-draft")
    async def generate_draft(request:Request):
        sid=(await request.json()).get("session_id","");p=await ensure_project(sid);responses=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300)
        if not responses:raise HTTPException(409,"At least one Board Member response is required")
        _,_,intake=await paid(sid); intake_answers=intake.get("answers") or {}
        context=(f"ORGANIZATION: {p['organization_name']}\nMISSION: {p.get('mission','')}\n\n"
                 f"LEAD USER INTAKE (starting organizational reality to be reviewed, not automatically treated as a Board decision):\n{intake_answers}\n\n"
                 "BOARD RESPONSES:\n"+ "\n\n".join(f"{x.get('name','Board Member')}: {x.get('response',{})}" for x in responses))
        research=await db.sp_community_research.find_one({"project_id":p["project_id"]},{"_id":0});
        if research: context+="\n\nCOMMUNITY NEED RESEARCH:\n"+str(research.get("responses",[]))
        structured=await generate_structured("strategic_planning_foundational",context,"Create the first Strategic Plan Draft from the lead-user starting context and the Board's actual review responses. The draft must explicitly cover Mission, Goals, Objectives, Programs, Team Building, Operations, Marketing, Partnerships, Fundraising, Technology, Budget, Organizational Priorities and Action Planning. Preserve supplied facts and Board ideas, reflect changes or disagreements rather than inventing consensus, and do not invent Board decisions.")
        display=plan_display(structured,p["organization_name"]);areas=[]
        for i,a in enumerate(structured.get("areas",[]),1):areas.append({"area_key":f"area_{i}","area":a.get("area",f"Area {i}"),"direction":a.get("direction",""),"proposed_priorities":a.get("proposed_priorities",[]),"ideas_shared":a.get("ideas_shared",[]),"status":"NOT ASSIGNED"})
        share_token=secrets.token_urlsafe(32)
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"status":"Approved","structured":structured,"display_text":display,"finalized_text":display,"areas":areas,"share_token":share_token,"updated_at":now_iso()},"$setOnInsert":{"created_at":now_iso()}},upsert=True);return {"status":"Approved"}

    @router.get("/strategic-draft/{token}")
    async def guided_public_draft(token: str):
        plan=await db.sp_plans.find_one({"share_token":token,"status":"Approved"},{"_id":0})
        if not plan: raise HTTPException(404,"This Strategic Plan Draft link is not valid")
        project=await owned_project(plan["project_id"])
        return {"title":"Strategic Plan Draft","organization_name":project["organization_name"],"display_text":plan.get("display_text",""),"issued_by":project.get("founder_name","")}

    @router.post("/send-draft-email")
    async def send_draft_email(request:Request):
        sid=(await request.json()).get("session_id","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};respondents=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300)
        if not plan.get("display_text"):raise HTTPException(409,"Generate the Strategic Plan Draft first")
        sent=0
        for r in respondents:
            link=f"{origin_of(request)}/strategic-draft/{plan.get('share_token')}";e=review_email(p,r,link);await send_email(r["email"],e["subject"],e["body"],e["button_label"],e["form_link"],reply_to=p.get("founder_email",""));sent+=1
        return {"status":"sent","count":sent}

    @router.post("/facilitation-guide")
    async def facilitation(request:Request):
        sid=(await request.json()).get("session_id","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if not plan.get("display_text"):raise HTTPException(409,"Generate the Strategic Plan Draft first")
        g=await generate_structured("strategic_meeting_guide",f"ORGANIZATION: {p['organization_name']}\n\nSTRATEGIC PLAN DRAFT:\n{plan['display_text']}","Create a practical facilitation guide for the Board's strategic planning review and delegation meeting. The meeting must review the draft, improve/remove ideas, then assign every strategic area to Board Members for deeper planning and future leadership/oversight.")
        text="\n\n".join(f"{x.get('heading','')}\n{x.get('content','')}" for x in g.get("sections",[]));await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"meeting_status":"Draft","meeting_guide_text":text}});return {"status":"Draft"}

    @router.post("/auto-delegate")
    async def auto_delegate(request:Request):
        sid=(await request.json()).get("session_id","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};people=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300);areas=plan.get("areas",[])
        if not people or not areas:raise HTTPException(409,"Board responses and a Strategic Plan Draft are required first")
        # deterministic round-robin coverage; preference score chooses starting order, then every area is assigned exactly once.
        for i,a in enumerate(areas):
            scored=[]
            for pson in people:
                words=(a.get("area","")+" "+a.get("direction","")).lower().split();own=str(pson.get("response",{})).lower();score=sum(1 for w in words if len(w)>4 and w in own);scored.append((score,pson))
            scored.sort(key=lambda x:x[0],reverse=True);owner=scored[i%len(scored)][1] if scored else people[i%len(people)];a["owner_participant_id"]=owner["participant_id"];a["status"]="ASSIGNED"
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"areas":areas}});return {"status":"ASSIGNED","area_count":len(areas)}

    @router.post("/send-area-assignment")
    async def area_assignment(request:Request):
        body=await request.json();sid=body.get("session_id","");key=body.get("area_key","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};area=next((x for x in plan.get("areas",[]) if x.get("area_key")==key),None)
        if not area or not area.get("owner_participant_id"):raise HTTPException(409,"Assign this strategic area first")
        owner=await db.sp_participants.find_one({"project_id":p["project_id"],"participant_id":area["owner_participant_id"]},{"_id":0});token=area.get("pack_token") or secrets.token_urlsafe(32);area["pack_token"]=token;area["pack_status"]="Approved";area["pack_text"]=pack_display({"mission_direction":area.get("direction",""),"foundational_priorities":area.get("proposed_priorities",[]),"ideas":area.get("ideas_shared",[]),"development_instruction":"Build the detailed plan for this strategic area. Define exactly what must be done, the people and technology required, your role in leading and overseeing it, the full cost of executing it at 100%, and a step-by-step action plan for the planning period."},area["area"],p["organization_name"]);await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"areas":plan["areas"]}})
        link=f"{origin_of(request)}/area-pack/{token}";e=pack_email(p,area,owner,link);await send_email(owner["email"],e["subject"],e["body"],e["button_label"],e["form_link"],reply_to=p.get("founder_email",""));return {"status":"sent"}

    @router.post("/final-plan")
    async def build_final(request:Request):
        sid=(await request.json()).get("session_id","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};areas=plan.get("areas",[])
        if not areas or any(a.get("detailed_plan_status")!="Approved" or not a.get("submitted_plan") for a in areas):raise HTTPException(409,"Every delegated strategic area needs an approved detailed plan before consolidation")
        context=f"ORGANIZATION: {p['organization_name']}\nMISSION: {p.get('mission','')}\n\nFOUNDATIONAL PLAN:\n{plan.get('display_text','')}\n\nAPPROVED DETAILED AREA PLANS:\n"+"\n\n".join(f"{a['area']}:\n{a['submitted_plan']}" for a in areas);g=await generate_structured("strategic_final_plan",context,"Consolidate only the supplied approved plans into one coherent final Strategic Plan. Do not invent new Board decisions.")
        display=final_display(g,p["organization_name"]);await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"final_status":"Approved","final_display_text":display,"final_share_token":secrets.token_urlsafe(32),"updated_at":now_iso()}});return {"status":"Approved"}

    @router.get("/final-plan/pdf")
    async def guided_final_pdf(session_id:str,request:Request):
        p=await ensure_project(session_id);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if not plan.get("final_display_text"):raise HTTPException(404,"Final Strategic Plan is not ready")
        return build_portfolio_pdf("STRATEGIC PLAN",p["organization_name"],{"organization_name":p["organization_name"],"issued_by":p["founder_name"]},plan["final_display_text"])

    @router.post("/portfolios")
    async def portfolios(request:Request):
        sid=(await request.json()).get("session_id","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if not plan.get("final_display_text"):raise HTTPException(409,"Generate the Final Strategic Plan first")
        people=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300);rows=[]
        for person in people:
            owned=[a for a in plan.get("areas",[]) if a.get("owner_participant_id")==person["participant_id"]];areas=[a["area"] for a in owned];text=f"BOARD MEMBER LEADERSHIP PORTFOLIO\n{person['name']}\n{p['organization_name']}\n\nYOUR STRATEGIC LEADERSHIP AREAS\n"+("\n".join(f"- {x}" for x in areas) or "- No strategic area assigned") +"\n\nYOUR RESPONSIBILITY\nProvide Board-level leadership and oversight for these areas. Work with the organization's leader to build the people, technology, materials, systems and execution structure required by the adopted Strategic Plan. As the execution structure becomes established, your role moves increasingly toward leadership and oversight rather than doing the day-to-day work."
            token=secrets.token_urlsafe(24);rows.append({"participant_id":person["participant_id"],"name":person["name"],"areas":areas,"text":text,"token":token,"url":f"/strategic-leadership-portfolio/{token}"})
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"leadership_portfolios":rows}});return {"status":"created","count":len(rows)}
    return router
