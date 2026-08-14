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
            "adoption_conclusion", "submitted_plan"]},
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
        signature = project["founder_name"] + (f"\n{project['founder_title']}" if project.get("founder_title") else "") + f"\n{organization}"
        body = (
            f"Dear {first},\n\n"
            f"We are beginning the process of building the strategic plan for {organization}, and I want the Board involved in shaping it.\n\n"
            "Rather than creating the plan and bringing it to the Board after the fact, I want us to build it together.\n\n"
            "Your ideas, experience and perspective will help shape our direction, priorities and how each of us can contribute.\n\n"
            "Please complete the Strategic Planning Form below.\n\n"
            "[COMPLETE MY STRATEGIC PLANNING FORM]\n\n"
            "Your responses will be combined with the ideas of the other Board Members as we build the plan.\n\n"
            f"Thank you for helping us build this together.\n\n{signature}"
        )
        return {"subject": f"Help Us Build Our Strategic Plan | {organization}", "body": body,
                "button_label": "COMPLETE MY STRATEGIC PLANNING FORM", "form_link": link}

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
        signature = project["founder_name"] + (f"\n{project['founder_title']}" if project.get("founder_title") else "") + f"\n{organization}"
        body = (
            f"Dear {first},\n\n"
            f"The ideas the Board shared have been consolidated into the Foundational Strategic Plan for {organization}.\n\n"
            "Before area owners develop the detailed plans, I want every Board Member to review the consolidated thinking, challenge it, improve it and add anything that is missing.\n\n"
            "For each strategic area you can support it as written, suggest a change, add an idea, or flag it for Board discussion.\n\n"
            "[REVIEW THE FOUNDATIONAL PLAN]\n\n"
            f"Thank you for helping us refine this together.\n\n{signature}"
        )
        return {"subject": f"Review Our Foundational Strategic Plan | {organization}", "body": body,
                "button_label": "REVIEW THE FOUNDATIONAL PLAN", "form_link": link}

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
                "submitted": bool(area.get("submitted_plan")), "submitted_at": area.get("plan_submitted_at", "")}

    @router.post("/area-pack/{token}/submit", status_code=201)
    async def submit_area_plan(token: str, payload: AreaPlanSubmission):
        plan, area = await area_by_pack_token(token)
        if area.get("pack_status") != "Approved":
            raise HTTPException(status_code=409, detail="This Area Development Pack is not available yet")
        project = await owned_project(plan["project_id"])
        now = now_iso()
        await db.sp_plans.update_one(
            {"project_id": plan["project_id"], "areas.area_key": area["area_key"]},
            {"$set": {"areas.$.submitted_plan": payload.plan_text, "areas.$.plan_submitted_at": now,
                      "areas.$.status": "SUBMITTED"},
             "$push": {"areas.$.submission_history": {"plan_text": payload.plan_text, "submitted_at": now}}})
        origin = os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com"
        await notify_owner(
            f"Strategic Area Plan Submitted | {area['area']}",
            f"The detailed plan for the {area['area']} area of {project['organization_name']}'s strategic plan has been submitted.\n\n[OPEN STRATEGIC PLANNING]",
            "OPEN STRATEGIC PLANNING", f"{origin}/admin")
        return {"status": "submitted"}

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
        signature = project["founder_name"] + (f"\n{project['founder_title']}" if project.get("founder_title") else "") + f"\n{organization}"
        body = (
            "Dear Board Member,\n\n"
            f"We are beginning the process of building the strategic plan for {organization}, and I want the Board involved in shaping it.\n\n"
            "Rather than creating the plan and bringing it to the Board after the fact, I want us to build it together.\n\n"
            "Your ideas, experience and perspective will help shape our direction, priorities and how each of us can contribute.\n\n"
            "Please complete the Strategic Planning Form using the link below.\n\n"
            f"{link}\n\n"
            "Your responses will be combined with the ideas of the other Board Members as we build the plan.\n\n"
            f"Thank you for helping us build this together.\n\n{signature}"
        )
        return {"subject": f"Help Us Build Our Strategic Plan | {organization}", "body": body, "form_link": link}

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
