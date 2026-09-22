"""Strategic Planning: admin-only service-delivery pathway.

Replicates the verified Activation planning architecture: hosted secure Board Member
forms, person-specific tokens, original responses, async Claude consolidation, board
review, area ownership, development packs and final plan assembly. Reuses the shared
email/PDF/extraction engines.
"""
import asyncio
import calendar
import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Union

import resend
from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ai_service import generate_structured, parse_json_response
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

def board_builder_recommendations(title: str, mission: str = "") -> list:
    key=title.lower()
    if "mission" in key:return ["Keep the present mission statement when it remains accurate, focused and emotionally meaningful to the organization.","If change is needed, protect the organization’s core purpose while clarifying who it serves, the change it creates and the distinct contribution it makes."]
    if "program" in key:return ["Test every program against the mission, demonstrated community need, measurable outcomes, delivery capacity and sustainable funding.","Give each program its own objective, success measures, resource requirements and accountable leader."]
    if "fundrais" in key:return ["Build fundraising around clearly defined audiences, where to find them, how to attract them and a relationship process from first awareness through stewardship.","Connect fundraising targets to the actual people, systems, materials, budget and Board participation required for execution."]
    if "team" in key:return ["Define the leadership, staff, Board, volunteer and specialist capacity required by the plan, including what must be recruited or developed.","Separate governance and strategic leadership from day-to-day operational responsibility."]
    if "technology" in key:return ["Choose technology from the workflow and information the organization must manage, then assign ownership for adoption and data quality."]
    if "budget" in key:return ["Cost the complete strategy, connect every major cost to an action and identify the funding source or assumption behind it."]
    if "marketing" in key or "communication" in key:return ["Define the exact audience, message, proof, channel, desired action and publishing responsibility for every priority communication effort."]
    if "partnership" in key:return ["Prioritize partners with clear mission alignment, complementary assets and a specific mutual value proposition."]
    if "goal" in key or "objective" in key:return ["Use a specific outcome, success measure, accountable owner and timeframe while keeping the goal connected to the mission."]
    if "operation" in key:return ["Translate the strategy into repeatable processes with clear ownership, handoffs, tools and accountability points."]
    if "action" in key or "priorit" in key:return ["Sequence the work by dependency and capacity, then assign owners, deadlines, resources and a recurring review rhythm."]
    return ["Review this area against the mission, community need, present capacity, required resources, measurable results and the Board leadership needed to execute it."]


def strategic_research_posts(name: str, mission: str = "") -> list:
    mission_text = mission or "our mission"
    return [
        f"""We are reviewing the future direction of {name}, and we do not want to build our next Strategic Plan only from inside the organization. We want to hear from people who experience, work around, or understand the needs connected to our mission.

Please share what you believe the real need is, who is most affected, and what would make the strongest difference. Your perspective will help our Board test its assumptions before agreeing the organization's next direction.""",
        f"""What does our community need most in relation to {mission_text}? We are asking this before our Board finalizes the next Strategic Plan because community experience should help us understand whether the priorities we see internally match what people are actually experiencing.

Tell us what you have observed personally: what is working, what is not working, what is missing, and what change you believe would matter most.""",
        f"""Help shape the next chapter of {name}. We are gathering community insight before our Board agrees the organization's future priorities, programs and approach.

From what you have seen or experienced, tell us which needs deserve greater attention, what approaches could work better, and what the organization should understand before making its next strategic decisions.""",
        f"""Good strategy starts by listening. If you have lived experience, professional knowledge, community relationships or another useful perspective connected to our work, we would value your input.

Please tell us what you believe the organization should protect, change, strengthen or begin doing so that its next Strategic Plan responds to real needs rather than assumptions.""",
        f"""{name}'s Board is preparing its next Strategic Plan. Before we agree the direction, we want to hear from the people and communities who can see things we may not see from inside the organization.

Take a few minutes to tell us about the need, the people most affected, the approaches you believe could make a difference, what is currently missing, and how people or organizations in the community could help.""",
    ]


def compact_session_idea(value: str, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    shortened = text[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return shortened + "…"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def months_from_now_iso(months: int = 6) -> str:
    current = datetime.now(timezone.utc)
    month_index = current.month - 1 + months
    year = current.year + month_index // 12
    month = month_index % 12 + 1
    day = min(current.day, calendar.monthrange(year, month)[1])
    return current.replace(year=year, month=month, day=day).isoformat()


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
        projects = await db.sp_projects.find(
            {"internal_preview": {"$ne": True}}, {"_id": 0}
        ).sort("created_at", -1).to_list(200)
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
        # The guided Strategic Planning journey stores its approved form as
        # the current content document.  This is authoritative when approved
        # and must be readable by both the lead-user and generic form links.
        if form.get("status") == "Approved" and form.get("content"):
            return form["content"]
        raise HTTPException(status_code=409, detail="This planning form is not available yet")

    @router.get("/strategic-planning-form/{token}")
    async def public_form(token: str):
        record = await db.sp_participants.find_one({"form_token": token}, {"_id": 0})
        if record:
            project = await owned_project(record["project_id"])
            content = await approved_form_content(record["project_id"], record.get("form_version") or 0)
            is_lead = record.get("role") == "Lead User"
            return {"organization_name": project["organization_name"], "logo_data_url": project.get("logo_data_url", ""),
                    "submitted": record["status"] == "COMPLETED" and not is_lead,
                    "is_lead_user": is_lead,
                    "existing_answers": record.get("response", {}) if is_lead else {},
                    "prefill": {"full_name": record.get("name", ""), "email": record.get("email", "")},
                    "form": content}
        project = await db.sp_projects.find_one({"generic_form_token": token}, {"_id": 0})
        if not project:
            raise HTTPException(status_code=404, detail="This form link is not valid")
        content = await approved_form_content(project["project_id"], 0)
        return {"organization_name": project["organization_name"], "logo_data_url": project.get("logo_data_url", ""), "submitted": False,
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
        if record["status"] == "COMPLETED" and record.get("role") != "Lead User":
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
        update_filter = {"participant_id": record["participant_id"]} if record.get("role") == "Lead User" else {"participant_id": record["participant_id"], "status": {"$ne": "COMPLETED"}}
        result = await db.sp_participants.update_one(
            update_filter,
            {"$set": {"status": "COMPLETED", "response": answers, "submitted_at": now,
                      "name": payload.full_name, "email": str(payload.email).lower(),
                      "response_questions": [{"id": q["id"], "prompt": q["prompt"], "section": q["section"]} for q in questions]}})
        if result.modified_count and record.get("role") != "Lead User":
            origin = os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com"
            try:
                if project.get("founder_email"):
                    await send_email(
                        project["founder_email"],
                        f"Strategic Planning Response Received | {payload.full_name}",
                        f"Hi {str(project.get('founder_name') or 'there').split(' ')[0]},\n\n"
                        f"{payload.full_name} has completed their Strategic Planning Form for {project['organization_name']}.\n\n"
                        "Open their response to review every answer before your Strategic Planning Session.\n\n"
                        "Nonprofit Board Builder",
                        f"VIEW {payload.full_name.split(' ')[0].upper()}'S RESPONSE",
                        f"{origin.rstrip('/')}/strategic-planning-response/{record['participant_id']}")
                    await db.sp_participants.update_one(
                        {"participant_id": record["participant_id"]},
                        {"$set": {"owner_notification_status": "Sent", "owner_notification_sent_at": now_iso()}})
            except Exception as exc:
                logger.exception("Strategic Planning purchaser notification failed for %s", record["participant_id"])
                await db.sp_participants.update_one(
                    {"participant_id": record["participant_id"]},
                    {"$set": {"owner_notification_status": "Failed", "owner_notification_error": str(exc)[:300]}})
        return {"status": "submitted", "organization_name": project["organization_name"]}

    @router.get("/strategic-planning-response/{participant_id}")
    async def public_response(participant_id: str):
        record = await db.sp_participants.find_one({"participant_id": participant_id, "status": "COMPLETED"}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This Strategic Planning response is not available")
        project = await owned_project(record["project_id"])
        prompts = {q["id"]: q for q in record.get("response_questions", [])}
        if not prompts:
            form = await db.sp_forms.find_one({"project_id": record["project_id"]}, {"_id": 0}) or {}
            for section in (form.get("content") or {}).get("sections", []):
                for q in section.get("questions", []):
                    prompts[q.get("id","")] = {**q, "section": section.get("title","")}
        rows = []
        for qid, value in (record.get("response") or {}).items():
            q = prompts.get(qid, {})
            rows.append({"section": q.get("section", ""), "question": q.get("prompt") or "Strategic Planning Question", "answer": value})
        return {"organization_name": project["organization_name"], "name": record.get("name", ""), "submitted_at": record.get("submitted_at", ""), "responses": rows}

    @router.get("/strategic-planning-response/{participant_id}/pdf")
    async def public_response_pdf(participant_id: str):
        record = await db.sp_participants.find_one({"participant_id": participant_id, "status": "COMPLETED"}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This Strategic Planning response is not available")
        project = await owned_project(record["project_id"])
        prompts = {q["id"]: q for q in record.get("response_questions", [])}
        if not prompts:
            form = await db.sp_forms.find_one({"project_id": record["project_id"]}, {"_id": 0}) or {}
            for section in (form.get("content") or {}).get("sections", []):
                for q in section.get("questions", []):
                    prompts[q.get("id","")] = {**q, "section": section.get("title","")}
        lines = ["STRATEGIC PLANNING RESPONSE", "", f"Board Member: {record.get('name','')}", f"Organization: {project['organization_name']}", ""]
        for qid, value in (record.get("response") or {}).items():
            q = prompts.get(qid, {})
            rendered = ", ".join(value) if isinstance(value, list) else str(value or "")
            lines.extend([str(q.get("section", "")).upper(), str(q.get("prompt") or "Strategic Planning Question"), rendered, ""])
        return build_portfolio_pdf("STRATEGIC PLANNING RESPONSE", record.get("name","Board Member"),
                                   {"organization_name": project["organization_name"], "issued_by": record.get("name","Board Member")},
                                   "\n".join(lines))

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

    async def area_assignment_by_token(token: str):
        plan = await db.sp_plans.find_one({"areas.pack_token": token}, {"_id": 0})
        if plan:
            area = next(a for a in plan["areas"] if a.get("pack_token") == token)
            participant=await db.sp_participants.find_one({"project_id":plan["project_id"],"participant_id":area.get("owner_participant_id","")},{"_id":0}) or {}
            return plan,area,participant
        participants=await db.sp_participants.find({"area_assignment_tokens":{"$exists":True}},{"_id":0}).to_list(500)
        for participant in participants:
            for area_key,assignment_token in (participant.get("area_assignment_tokens") or {}).items():
                if assignment_token==token:
                    plan=await db.sp_plans.find_one({"project_id":participant["project_id"]},{"_id":0})
                    area=next((a for a in (plan or {}).get("areas",[]) if a.get("area_key")==area_key),None)
                    if plan and area:return plan,area,participant
        raise HTTPException(status_code=404, detail="This link is not valid")

    async def area_by_pack_token(token: str):
        plan,area,_=await area_assignment_by_token(token)
        return plan,area

    @router.get("/area-pack/{token}")
    async def public_pack(token: str):
        plan, area, assignment_person = await area_assignment_by_token(token)
        if area.get("pack_status") != "Approved":
            raise HTTPException(status_code=409, detail="This Area Development Pack is not available yet")
        project = await owned_project(plan["project_id"])
        owner = assignment_person or (await owned_participant(plan["project_id"], area["owner_participant_id"]) if area.get("owner_participant_id") else {})
        return {"organization_name": project["organization_name"], "area": area["area"],
                "owner_name": owner.get("name", ""), "pack_text": area.get("pack_text", ""),
                "foundational_plan": plan.get("display_text",""), "submitted_plan": area.get("submitted_plan",""),
                "submitted": bool(area.get("submitted_plan")), "submitted_at": area.get("plan_submitted_at", ""), "draft_text": area.get("detailed_plan_text",""), "draft_status": area.get("detailed_plan_status","NONE"), "approved": area.get("detailed_plan_status")=="Approved"}

    @router.post("/area-pack/{token}/generate")
    async def generate_area_plan(token: str):
        plan, area, assignment_person = await area_assignment_by_token(token)
        if area.get("pack_status") != "Approved":
            raise HTTPException(status_code=409, detail="This Area Development Pack is not available yet")
        if area.get("detailed_plan_status") == "Approved":
            raise HTTPException(status_code=409, detail="This detailed plan is approved and locked.")
        project = await owned_project(plan["project_id"])
        owner = assignment_person or (await owned_participant(plan["project_id"], area["owner_participant_id"]) if area.get("owner_participant_id") else {})
        context = (
            f"ORGANIZATION: {project['organization_name']}\nMISSION: {project.get('mission','')}\n"
            f"BOARD MEMBER: {owner.get('name','')}\nSTRATEGIC AREA: {area.get('area','')}\n"
            f"FOUNDATIONAL DIRECTION: {area.get('direction','')}\n"
            f"APPROVED PRIORITIES: {area.get('proposed_priorities',[])}\n"
            f"BOARD IDEAS: {area.get('ideas_shared',[])}\n"
            f"BOARD MEMBER'S OWN PLANNING RESPONSE: {owner.get('response',{})}\n"
            f"FOUNDATIONAL STRATEGIC PLAN: {plan.get('display_text','')}"
        )
        prompt = """Build ONLY this board member\'s detailed plan for the assigned strategic area from the supplied facts and Board decisions. The Board-agreed direction and selected ideas are the authority. Preserve the contributors\' original logic, distinctive wording and intended meaning wherever practical. Your job is to make those agreed ideas executable, not to replace, sanitize, average or rewrite them into generic strategy language. The Board Member must still recognize the Board\'s own thinking in the draft. Nonprofit Board Builder recommendations may strengthen execution only where they do not contradict or displace the agreed ideas. Do not invent facts, dates, budgets, people, programs or commitments. If a required detail was not supplied, write a clear decision placeholder instead of guessing. Use these headings in this exact order: Strategic Area / Purpose; What We Must Accomplish; Priorities/Objectives; Step-by-Step Actions; People/Team Required; Technology/Tools Required; Leadership/Oversight Role; Budget/Cost to Execute at 100%; Timeline/Milestones; Measures/How We Know It\'s Working. The output must be practical, detailed, editable and ready for the board member to refine."""
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
        if area.get("detailed_plan_status") == "Approved": raise HTTPException(409,"This detailed plan is approved and locked.")
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

    async def owned_project(project_id: str) -> dict:
        project = await db.sp_projects.find_one({"project_id": project_id}, {"_id": 0})
        if not project:
            raise HTTPException(status_code=404, detail="Strategic Planning project not found")
        return project

    async def send_email(to_email: str, subject: str, body: str, button_label: str, link: str, reply_to: str = ""):
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        message = {"from": os.environ["NONPROFIT_SENDER"], "to": [to_email],
                   "subject": subject, "html": email_html(body, button_label, link)}
        if reply_to:
            message["reply_to"] = [reply_to]
        await resend.Emails.send_async(message)

    async def ensure_execution_access(project: dict) -> dict:
        scope_id=f"strategic:{project['project_id']}"
        existing=await db.executive_assistant_access.find_one({"scope_id":scope_id},{"_id":0})
        if existing:return existing
        started=now_iso();record={"scope_id":scope_id,"product":"strategic-planning","project_id":project["project_id"],
            "organization_name":project.get("organization_name",""),"leader_name":project.get("founder_name",""),
            "leader_email":project.get("founder_email",""),"started_at":started,"included_until":months_from_now_iso(6),
            "subscription_status":"included","created_at":started,"updated_at":started}
        await db.executive_assistant_access.insert_one(record.copy());return record

    def execution_access_state(access: dict) -> str:
        if access.get("subscription_status")=="active":return "active"
        try:
            if datetime.fromisoformat(str(access.get("included_until","")).replace("Z","+00:00"))>datetime.now(timezone.utc):
                return "included"
        except Exception:
            pass
        return "renewal_required"

    async def meter_assistant(scope_id: str, token: str, member_name: str, request_text: str, answer: str, material: str=""):
        await db.executive_assistant_usage.insert_one({"usage_id":str(uuid.uuid4()),"scope_id":scope_id,
            "product":"strategic-planning","assistant_token":token,"member_name":member_name,
            "material_type":material,"input_characters":len(request_text),"output_characters":len(answer),
            "created_at":now_iso()})


    def generic_form_email(project: dict, link: str) -> dict:
        organization = project["organization_name"]
        signature = sp_signature(project["founder_name"], project.get("founder_title", ""), organization)
        return sp_generic_form_invitation_email(organization, link, signature)

    def review_email(project: dict, participant: dict, link: str) -> dict:
        first = (participant.get("name") or "").split(" ")[0]
        organization = project["organization_name"]
        signature = sp_signature(project["founder_name"], project.get("founder_title", ""), organization)
        return {**sp_review_invitation_email(first, organization, signature), "form_link": link}

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
        for a in plan.get("areas",[]): areas.append({**a,"owner_name":by.get(a.get("owner_participant_id",""),{}).get("name",""),"collaborator_names":[by.get(pid,{}).get("name","") for pid in a.get("collaborator_participant_ids",[]) if by.get(pid)]})
        return {**p,"participants":participants,"form":form,"lead_form_token":next((x.get("form_token","") for x in participants if x.get("role")=="Lead User"),""),"plan":{"status":plan.get("status","NONE"),"display_text":plan.get("display_text",""),"share_url":(f"/strategic-draft/{plan.get('share_token')}" if plan.get("share_token") else "")},"areas":areas,"meeting_guide_text":plan.get("meeting_guide_text",""),"final_plan":{"status":plan.get("final_status","NONE"),"display_text":plan.get("final_display_text",""),"share_token":plan.get("final_share_token",""),"share_url":(f"/strategic-plan/{plan.get('final_share_token')}" if plan.get("final_share_token") else "")},"portfolios":plan.get("leadership_portfolios",[]),"presentation_meeting":plan.get("presentation_meeting",{}),"active_delegation":plan.get("active_delegation",{}),"follow_up_meeting":plan.get("follow_up_meeting",{})}

    @router.get("/workspace")
    async def workspace(session_id:str):
        _,lead,intake=await paid(session_id);p=await ensure_project(session_id);research=await db.sp_community_research.find_one({"project_id":p["project_id"]},{"_id":0})
        return {"organization_name":p.get("organization_name") or lead.get("organization",""),"organization_answers":intake.get("answers") or {},"project":await detail(p),"community_research":research}

    @router.put("/organization")
    async def save_organization(request: Request):
        body=await request.json();sid=str(body.get("session_id", ""));name=str(body.get("organization_name", "")).strip();answers=body.get("answers") or {};logo=str(body.get("logo_data_url", ""))
        if not name or not str(answers.get("mission", "")).strip():raise HTTPException(422,"Enter the organization name and mission statement")
        if logo and (not logo.startswith("data:image/") or len(logo)>2_500_000):raise HTTPException(422,"Upload a PNG, JPG or WebP logo smaller than 1.8 MB")
        p=await ensure_project(sid);now=now_iso()
        await db.guided_product_intakes.update_one({"session_id":sid,"product":"strategic-planning"},{"$set":{"answers":answers,"updated_at":now}})
        updates={"organization_name":name,"mission":str(answers.get("mission", "")).strip(),"organization_details_saved_at":now,"updated_at":now}
        if logo:updates["logo_data_url"]=logo
        await db.sp_projects.update_one({"project_id":p["project_id"]},{"$set":updates})
        await db.sp_forms.update_one({"project_id":p["project_id"]},{"$set":{"status":"Needs Regeneration","updated_at":now}})
        await db.sp_community_research.update_one(
            {"project_id":p["project_id"]},
            {"$set":{"social_posts":strategic_research_posts(name, str(answers.get("mission") or "")),"updated_at":now}},
        )
        return {"saved":True}

    @router.post("/prepare-form")
    async def prepare_form(request:Request):
        body=await request.json();sid=body.get("session_id","");p=await ensure_project(sid);_,_,intake=await paid(sid);a=intake.get("answers") or {}
        programs=a.get("programs") or a.get("areas") or ""
        program_lines=[x.strip(" -•\t") for x in str(programs).split("\n") if x.strip()][:12]

        sections_data=[
            ("Mission",[
                f"From your view, does our present mission still clearly explain who we serve, how we serve them and the change we are trying to create? What would you keep or change, and why?\n\nPresent mission: {str(a.get('mission') or p.get('mission') or '').strip()}",
                "What wording, focus or emphasis would make the mission more useful for guiding the organization's decisions over the next few years?",
            ]),
            ("Goals",[
                f"Looking at our present goals for the next 12 to 24 months, which goals feel most important, which should change, and what goal do you believe we are missing?\n\nPresent goals: {str(a.get('goals') or '').strip()}",
                "From what you know about the organization and the people we serve, what do you believe we should realistically be trying to achieve during this planning period?",
            ]),
            ("Objectives",[
                f"Our objectives should help us achieve our goals. Looking at what we presently have, which objectives are useful, which need to change, and what specific objectives should we add?\n\nPresent objectives: {str(a.get('objectives') or '').strip()}",
                "What evidence or result would make you say that these objectives are actually being achieved?",
            ]),
        ]

        for program in program_lines:
            sections_data.append((f"Program: {program}",[
                f"Thinking specifically about {program}, what do you believe this program should accomplish for the people it serves? What should we protect, change or improve?",
                f"From what you have observed, what would make {program} more effective, useful or sustainable, and what should the organization do differently in delivering it?",
            ]))

        sections_data.extend([
            ("Team & Capacity",[
                f"Who do we presently have available to help execute this strategy — staff, Board Members, volunteers, contractors or other supporters? Where do you see enough capacity and where are we stretched?\n\nPresent information: {str(a.get('team_building') or '').strip()}",
                "What people, skills or leadership capacity do you believe we need to add or strengthen to execute the strategy successfully?",
            ]),
            ("Operations",[
                f"From what you have observed, which internal systems or processes help the organization work well and which ones make execution harder?\n\nPresent information: {str(a.get('operations') or '').strip()}",
                "What operational change would make the biggest practical difference to our ability to deliver the strategy consistently?",
            ]),
            ("Marketing & Visibility",[
                f"Who most needs to know about our work, and what do you believe they need to understand about us?\n\nPresent information: {str(a.get('marketing') or '').strip()}",
                "From what you have seen, where should we be more visible and what would help the right people notice, trust and engage with the organization?",
            ]),
            ("Partnerships",[
                f"Which types of organizations, institutions, businesses or community groups could materially strengthen our mission, and what could a useful partnership actually help us accomplish?\n\nPresent information: {str(a.get('partnerships') or '').strip()}",
                "Are there relationships or partnership opportunities you believe we should prioritize because of what you know or have observed?",
            ]),
            ("Fundraising",[
                f"From your perspective, what is working and not working about how we presently raise money?\n\nPresent information: {str(a.get('fundraising') or '').strip()}",
                "Who do you believe is most likely to care about funding this work, where can we reach them, and what should we do to build enough trust to ask for support?",
            ]),
            ("Technology",[
                f"What work do we need technology to make easier, faster or more reliable, and where are our present tools getting in the way?\n\nPresent information: {str(a.get('technology') or '').strip()}",
                "What technology capability do you believe the organization genuinely needs in order to execute this strategy well?",
            ]),
            ("Budget & Resources",[
                f"Looking at the direction we are considering, where do you believe the organization will need to spend, invest or secure additional resources?\n\nPresent information: {str(a.get('budget') or '').strip()}",
                "What budget or resource decisions do you believe the Board needs to understand before committing to the strategy?",
            ]),
            ("Action Planning",[
                f"Based on everything above, what do you believe the organization should do first, next and after that to begin executing this strategy?\n\nPresent actions already planned or underway: {str(a.get('action_planning') or '').strip()}",
                "What practical actions, decisions or resources do you believe are most important in the first 90 days after this Strategic Plan is adopted?",
            ]),
            ("Roles We Will Play",[
                "Which Board committee, working group or recurring area of Board work would you genuinely be interested in joining or helping shape? If no formal committee exists yet, describe the kind of group or area you would be happy to participate in.",
                "Which areas of this Strategic Plan would you personally be willing to LEAD at Board level? Only name areas you would genuinely be comfortable accepting responsibility for.",
                "Which areas would you be happy to SUPPORT without being the lead? Describe the kind of contribution, expertise, relationships or help you would be comfortable providing.",
            ]),
        ])

        sections=[]
        for i,(title,prompts) in enumerate(sections_data,1):
            sections.append({
                "key":f"s{i}",
                "title":title,
                "questions":[{"id":f"s{i}_q{j}","prompt":prompt,"type":"long","options":[],"required":True} for j,prompt in enumerate(prompts,1)],
            })

        goal=str(a.get("goals") or "build a clear, practical direction for the organization").strip()
        content={
            "introduction":(
                f"{p['organization_name']} is preparing its next Strategic Plan. We want your own thinking before the Board meets together. "
                "There are no right or wrong answers. Speak from what you have observed, what you know, and what you genuinely believe would help the organization. "
                "Your ideas will remain attributable to you during the Board's Strategic Planning Session so the group can review every contribution together. "
                f"Our present planning direction is to {goal}."
            ),
            "sections":sections,
        }
        now=now_iso()
        await db.sp_forms.update_one(
            {"project_id":p["project_id"]},
            {"$set":{"status":"Approved","content":content,"approved_version":1,"approved_at":now,"updated_at":now},
             "$setOnInsert":{"form_id":str(uuid.uuid4()),"created_at":now}},
            upsert=True,
        )
        return {"status":"Approved"}

    @router.post("/branding")
    async def save_branding(request: Request):
        body=await request.json();sid=body.get("session_id","");logo=str(body.get("logo_data_url", ""))
        if not logo.startswith("data:image/") or len(logo)>2_500_000: raise HTTPException(422,"Upload a PNG or JPG logo smaller than 1.8 MB")
        p=await ensure_project(sid);await db.sp_projects.update_one({"project_id":p["project_id"]},{"$set":{"logo_data_url":logo,"updated_at":now_iso()}})
        return {"status":"saved"}

    @router.get("/form-email")
    async def guided_form_email(session_id:str,request:Request):
        p=await ensure_project(session_id);form=await db.sp_forms.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if form.get("status")!="Approved":raise HTTPException(409,"Prepare the Strategic Planning Form first")
        link=f"{origin_of(request)}/strategic-planning-form/{p['generic_form_token']}";e=generic_form_email(p,link);return {**e,"form_link":link}

    @router.post("/invite")
    async def invite_participant(request: Request):
        body=await request.json();sid=body.get("session_id","");name=str(body.get("name","")).strip();email=str(body.get("email","")).strip().lower();p=await ensure_project(sid)
        if not name or "@" not in email:raise HTTPException(422,"Enter the Board Member's name and email address")
        form=await db.sp_forms.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if form.get("status")!="Approved":raise HTTPException(409,"Prepare the Strategic Planning Form first")
        participant=await db.sp_participants.find_one({"project_id":p["project_id"],"email":email},{"_id":0})
        if not participant:
            participant={"participant_id":str(uuid.uuid4()),"project_id":p["project_id"],"name":name,"email":email,"role":"Board Member","status":"INVITED","form_token":secrets.token_urlsafe(32),"review_status":"NOT SENT","review_token":secrets.token_urlsafe(32),"created_at":now_iso()};await db.sp_participants.insert_one(participant.copy())
        link=f"{origin_of(request)}/strategic-planning-form/{participant['form_token']}";e=generic_form_email(p,link);await send_email(email,e["subject"],e["body"],e["button_label"],link,reply_to=p.get("founder_email",""));await db.sp_participants.update_one({"participant_id":participant["participant_id"]},{"$set":{"name":name,"status":"SENT","sent_at":now_iso()}})
        return {"status":"sent","participant_id":participant["participant_id"]}

    def strategic_section_context(title: str, answers: dict, project: dict) -> str:
        key=title.lower()
        if "mission" in key:return str(answers.get("mission") or project.get("mission") or "").strip()
        if key=="goals":return str(answers.get("goals") or "").strip()
        if "objective" in key:return str(answers.get("objectives") or "").strip()
        if key.startswith("program:"):return title.split(":",1)[1].strip()
        if "team" in key:return str(answers.get("team_building") or "").strip()
        if "operation" in key:return str(answers.get("operations") or "").strip()
        if "marketing" in key:return str(answers.get("marketing") or "").strip()
        if "partnership" in key:return str(answers.get("partnerships") or "").strip()
        if "fundrais" in key:return str(answers.get("fundraising") or "").strip()
        if "technology" in key:return str(answers.get("technology") or "").strip()
        if "budget" in key:return str(answers.get("budget") or "").strip()
        if "action" in key:return str(answers.get("action_planning") or "").strip()
        return ""

    def facilitator_prompt_for(title: str, current_context: str = "") -> dict:
        key=str(title or "").lower()
        context_note=f" Start by reading the organization's present information on screen: {current_context}" if current_context else ""
        if "mission" in key:
            return {
                "title":"Facilitate The Mission Discussion",
                "say":"We are testing whether our present mission still expresses who we serve, the change we exist to create and the core purpose we want to protect."+context_note,
                "questions":[
                    "Does the mission still feel true to why this organization exists?",
                    "Which ideas would make it clearer without making it longer or losing our core purpose?",
                    "Do we want to change the mission, or deliberately leave it as it is?",
                ],
                "decision":"Before moving on, either select the ideas that should shape the mission or choose Leave Mission Statement As It Is.",
            }
        if "goal" in key:
            return {"title":"Facilitate The Goals Discussion","say":"We are deciding what the organization should actually accomplish during this planning period."+context_note,
                    "questions":["Which goals matter most over the next 12 to 24 months?","What goal is missing, unrealistic or no longer important?","How will we know we are making meaningful progress?"],
                    "decision":"Select the goal ideas the Board wants carried into the Strategic Plan."}
        if "objective" in key:
            return {"title":"Facilitate The Objectives Discussion","say":"Objectives are the measurable things we must achieve in order to reach our goals."+context_note,
                    "questions":["Which objectives directly move our goals forward?","What result or evidence should each objective produce?","Is anything here activity rather than an actual objective?"],
                    "decision":"Select the objective ideas the Board agrees should guide execution."}
        if "program:" in key:
            program=title.split(":",1)[1].strip() if ":" in title else title
            return {"title":f"Facilitate The {program} Discussion","say":f"Now test {program} as its own part of the strategy. The question is not simply whether we like the program, but what it should accomplish and how it should improve."+context_note,
                    "questions":[f"What should {program} accomplish for the people it serves?",f"What should we protect, change, stop or improve in {program}?","What would make this program more effective and sustainable?"],
                    "decision":f"Select the ideas the Board wants to shape {program} in the Strategic Plan."}
        if "team" in key or "capacity" in key:
            return {"title":"Facilitate The People & Capacity Discussion","say":"A strategy cannot execute itself. We are identifying the people and leadership capacity we already have and what is still missing."+context_note,
                    "questions":["Who do we already have who can help execute this plan?","Where are we stretched or dependent on too few people?","What skills, staff, volunteers, Board leadership or outside support do we need to add?"],
                    "decision":"Select the people/capacity ideas that must be reflected in the plan."}
        if "operation" in key:
            return {"title":"Facilitate The Operations Discussion","say":"We are looking at the systems and ways of working that will either support or frustrate execution."+context_note,
                    "questions":["Which recurring processes are working well?","Where are we depending on memory, one person or inconsistent follow-up?","What operational change would make execution more reliable?"],
                    "decision":"Select the operational changes the Board wants built into the strategy."}
        if "marketing" in key or "visibility" in key:
            return {"title":"Facilitate The Marketing & Visibility Discussion","say":"We are deciding who needs to know about our work, what they need to understand and how we earn their attention and trust."+context_note,
                    "questions":["Which audiences matter most?","What evidence, stories or insight should they consistently see?","Where should we become more visible and what action do we want people to take?"],
                    "decision":"Select the marketing and visibility ideas the Board agrees should shape the plan."}
        if "partnership" in key:
            return {"title":"Facilitate The Partnerships Discussion","say":"We are identifying relationships that can materially strengthen the mission, not collecting a long list of names."+context_note,
                    "questions":["What kinds of partners would create real value for the mission?","What could we offer them and what could they help us accomplish?","Which relationships should we prioritize first?"],
                    "decision":"Select the partnership ideas the Board wants to pursue."}
        if "fundrais" in key:
            return {"title":"Facilitate The Fundraising Discussion","say":"We are deciding how the organization will build a sustainable funding system rather than leaving fundraising as one person's job."+context_note,
                    "questions":["Who is most likely to care about funding this work?","Where do we find them and how do we build enough trust before asking?","What role should the Board realistically play in relationships, introductions, cultivation or stewardship?"],
                    "decision":"Select the fundraising ideas that should become part of the strategy."}
        if "technology" in key:
            return {"title":"Facilitate The Technology Discussion","say":"Technology should support the workflow we need, not become a strategy by itself."+context_note,
                    "questions":["What work do we need technology to make easier or more reliable?","Where are current tools creating friction or lost information?","What capability is essential before we add more tools?"],
                    "decision":"Select only the technology ideas that genuinely help execute the plan."}
        if "budget" in key:
            return {"title":"Facilitate The Budget & Resources Discussion","say":"We are testing whether the strategy is financially realistic and identifying what execution will actually require."+context_note,
                    "questions":["What will this strategy genuinely cost to execute?","Which resources are already available and which must be raised or added?","What financial information does the Board need in order to monitor the plan responsibly?"],
                    "decision":"Select the budget/resource ideas the Board wants reflected in the plan."}
        if "action" in key:
            return {"title":"Facilitate Action Planning","say":"Now turn the strategy into a first execution cycle. Focus on what happens first, next and after that, not on writing another document."+context_note,
                    "questions":["What must happen in the first 30 days?","What should be achieved in the first 90 days?","What decisions, resources or dependencies could block execution if we do not address them now?"],
                    "decision":"Select the actions the Board agrees should shape the first execution cycle. The next screen is where you discuss who is willing to help carry the work."}
        if "roles we will play" in key:
            return {"title":"Facilitate Roles We Will Play","say":"These ideas came from what people themselves said they would be willing to join, lead or support. They are starting points, not assignments.",
                    "questions":["Is what you wrote still a role you would be comfortable playing?","What exact responsibility would you be willing to accept?","Is there any role you want to narrow, change, add or decline?","Do you need any support before agreeing to take responsibility?"],
                    "decision":"Say any explicit role agreement or decline aloud so the transcript records it. If the Board prefers to finalize roles afterward, say that clearly and move on."}
        return {"title":f"Facilitate {title}","say":"Review the present context and the ideas people submitted before the meeting."+context_note,
                "questions":["What do these ideas mean in practice?","Which ideas should shape the organization's direction?","What needs clarification before we move on?"],
                "decision":"Select the ideas the Board agrees should influence this section."}

    def build_session_sections(form: dict, people: list, saved: dict, answers: dict, project: dict) -> list:
        sections=[]
        for section in (form.get("content") or {}).get("sections",[]):
            ideas=[]
            for person in people:
                response=person.get("response") or {}
                for question in section.get("questions",[]):
                    raw=response.get(question.get("id"))
                    if isinstance(raw,list): raw=", ".join(str(x) for x in raw if str(x).strip())
                    raw=str(raw or "").strip()
                    if not raw:continue
                    idea_id=f"{person['participant_id']}:{question['id']}"
                    ideas.append({
                        "idea_id":idea_id,
                        "participant_id":person["participant_id"],
                        "participant_name":person.get("name","Board Member"),
                        "question_id":question.get("id",""),
                        "question":question.get("prompt",""),
                        "idea":compact_session_idea(raw),
                    })
            saved_decision=(saved.get("decisions") or {}).get(section["key"],[])
            selected=[]
            if isinstance(saved_decision,list):
                valid_ids={idea["idea_id"] for idea in ideas}
                for item in saved_decision:
                    item=str(item)
                    if item in valid_ids and item not in selected:selected.append(item)
                    elif ":" not in item:
                        for idea in ideas:
                            if idea["participant_id"]==item and idea["idea_id"] not in selected:selected.append(idea["idea_id"])
            sections.append({
                "key":section["key"],
                "title":section["title"],
                "current_context":strategic_section_context(section["title"],answers,project),
                "facilitator_prompt":facilitator_prompt_for(
                    section["title"], strategic_section_context(section["title"],answers,project)
                ),
                "ideas":ideas,
                "recommendations":board_builder_recommendations(section["title"],project.get("mission","")),
                "allow_keep_current_mission":"mission" in section["title"].lower(),
                "selected_idea_ids":selected,
                "decision_mode":saved_decision if isinstance(saved_decision,str) and saved_decision.startswith("__") else "selected_ideas",
                "is_action_planning":"action" in section["title"].lower(),
                "is_role_planning":"roles we will play" in section["title"].lower(),
            })
        return sections

    @router.get("/session")
    async def strategic_session(session_id: str):
        p=await ensure_project(session_id);_,_,intake=await paid(session_id)
        form=await db.sp_forms.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        people=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300)
        saved=await db.sp_sessions.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        sections=build_session_sections(form,people,saved,intake.get("answers") or {},p)
        return {"organization_name":p["organization_name"],"sections":sections,"transcript":saved.get("transcript",""),
                "status":saved.get("status","NOT STARTED"),"share_token":saved.get("share_token",""),
                "current_section_index":saved.get("current_section_index",0)}

    @router.post("/session/share")
    async def share_strategic_session(request: Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));saved=await db.sp_sessions.find_one({"project_id":p["project_id"]},{"_id":0}) or {};token=saved.get("share_token") or secrets.token_urlsafe(32)
        await db.sp_sessions.update_one({"project_id":p["project_id"]},{"$set":{"project_id":p["project_id"],"share_token":token,"current_section_index":saved.get("current_section_index",0),"updated_at":now_iso()}},upsert=True)
        return {"share_token":token}

    @router.post("/session/start")
    async def start_strategic_session(request: Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""))
        form=await db.sp_forms.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        people=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300)
        if not (form.get("content") or {}).get("sections"):raise HTTPException(409,"Generate the Strategic Planning Form first")
        if not people:raise HTTPException(409,"At least one completed Strategic Planning Form is required")
        saved=await db.sp_sessions.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        await db.sp_sessions.update_one({"project_id":p["project_id"]},{"$set":{"project_id":p["project_id"],"status":"IN PROGRESS",
            "started_at":saved.get("started_at") or now_iso(),"current_section_index":saved.get("current_section_index",0),"updated_at":now_iso()}},upsert=True)
        return {"status":"IN PROGRESS"}

    @router.post("/session/transcript")
    async def save_strategic_session_transcript(request: Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));transcript=str(body.get("transcript","")).strip()[:60000]
        await db.sp_sessions.update_one({"project_id":p["project_id"]},{"$set":{"project_id":p["project_id"],"transcript":transcript,"updated_at":now_iso()}},upsert=True)
        return {"saved":True}

    @router.post("/session/progress")
    async def update_strategic_session_progress(request: Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));index=max(0,int(body.get("current_section_index",0)))
        await db.sp_sessions.update_one({"project_id":p["project_id"]},{"$set":{"project_id":p["project_id"],"current_section_index":index,"status":"IN PROGRESS","updated_at":now_iso()}},upsert=True)
        return {"current_section_index":index}

    @router.post("/session/decision")
    async def save_strategic_session_decision(request: Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));key=str(body.get("section_key","")).strip();decision=body.get("decision")
        _,_,intake=await paid(body.get("session_id",""))
        form=await db.sp_forms.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        people=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300)
        saved=await db.sp_sessions.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        sections=build_session_sections(form,people,saved,intake.get("answers") or {},p);section=next((x for x in sections if x["key"]==key),None)
        if not section:raise HTTPException(422,"Choose a valid strategic section")
        if isinstance(decision,list):
            valid={idea["idea_id"] for idea in section["ideas"]};clean=[]
            for idea_id in decision:
                idea_id=str(idea_id)
                if idea_id in valid and idea_id not in clean:clean.append(idea_id)
            if not clean:
                await db.sp_sessions.update_one({"project_id":p["project_id"]},{"$unset":{f"decisions.{key}":""},"$set":{"updated_at":now_iso()}},upsert=True)
                return {"section_key":key,"decision":[]}
            stored=clean
        elif decision=="__keep_current__" and section["allow_keep_current_mission"]:
            stored=decision
        elif decision=="__use_all_ideas__":
            stored=decision
        else:raise HTTPException(422,"Choose at least one Board idea")
        await db.sp_sessions.update_one({"project_id":p["project_id"]},{"$set":{"project_id":p["project_id"],f"decisions.{key}":stored,"updated_at":now_iso()}},upsert=True)
        return {"section_key":key,"decision":stored}

    @router.get("/session/watch/{token}")
    async def watch_strategic_session(token: str):
        saved=await db.sp_sessions.find_one({"share_token":token},{"_id":0})
        if not saved:raise HTTPException(404,"This Strategic Planning session link is not valid")
        p=await db.sp_projects.find_one({"project_id":saved["project_id"]},{"_id":0}) or {}
        intake=await db.guided_product_intakes.find_one({"session_id":p.get("guided_session_id"),"product":"strategic-planning"},{"_id":0}) or {}
        form=await db.sp_forms.find_one({"project_id":saved["project_id"]},{"_id":0}) or {}
        people=await db.sp_participants.find({"project_id":saved["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300)
        sections=build_session_sections(form,people,saved,intake.get("answers") or {},p)
        index=min(saved.get("current_section_index",0),max(0,len(sections)-1))
        section=sections[index] if sections else None
        if section:
            selected=set(section.get("selected_idea_ids") or [])
            section={**section,"ideas":[{**idea,"selected":idea["idea_id"] in selected} for idea in section["ideas"]]}
            section.pop("facilitator_prompt",None)
        return {"organization_name":p.get("organization_name",""),"status":saved.get("status","NOT STARTED"),
                "current_section_index":index,"section":section,"total_sections":len(sections)}

    @router.post("/session/complete")
    async def complete_strategic_session(request: Request):
        body=await request.json();sid=body.get("session_id","");decisions=body.get("decisions") or {};transcript=str(body.get("transcript","")).strip()[:60000]
        p=await ensure_project(sid);_,_,intake=await paid(sid)
        form=await db.sp_forms.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        people=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300)
        saved=await db.sp_sessions.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        sections=build_session_sections(form,people,saved,intake.get("answers") or {},p)
        if not transcript:raise HTTPException(422,"Keep the microphone transcript running or paste the session transcript before ending the Strategic Planning Session")
        for section in sections:
            value=decisions.get(section["key"])
            if section["allow_keep_current_mission"] and value=="__keep_current__":continue
            if value=="__use_all_ideas__":continue
            if not isinstance(value,list) or not value:raise HTTPException(422,f"Choose at least one agreed idea for {section['title']}")

        full_ideas={}
        for section in (form.get("content") or {}).get("sections",[]):
            for person in people:
                response=person.get("response") or {}
                for question in section.get("questions",[]):
                    raw=response.get(question.get("id"))
                    if isinstance(raw,list):raw=", ".join(str(x) for x in raw if str(x).strip())
                    raw=str(raw or "").strip()
                    if raw:
                        full_ideas[f"{person['participant_id']}:{question['id']}"]={
                            "participant_id":person["participant_id"],"participant_name":person.get("name","Board Member"),
                            "question":question.get("prompt",""),"text":raw,
                        }

        areas=[]
        for section in sections:
            decision=decisions.get(section["key"])
            all_for_section=[full_ideas.get(idea["idea_id"]) for idea in section["ideas"] if full_ideas.get(idea["idea_id"])]
            if decision=="__keep_current__":
                agreed=[{"participant_name":"Board Decision","text":p.get("mission","")}]
                direction=p.get("mission","");mode="keep_current"
            elif decision=="__use_all_ideas__":
                agreed=all_for_section;direction="Use all submitted ideas together with the live Board discussion.";mode="use_all_ideas"
            else:
                agreed=[full_ideas[x] for x in decision if x in full_ideas]
                direction="\n\n".join(x["text"] for x in agreed);mode="selected_ideas"
            areas.append({"area_key":section["key"],"area":section["title"],"current_context":section.get("current_context",""),
                          "agreed_ideas":agreed,"ideas_shared":all_for_section,"direction":direction,"decision_mode":mode,"status":"READY FOR PLAN"})

        now=now_iso()
        await db.sp_sessions.update_one({"project_id":p["project_id"]},{"$set":{"project_id":p["project_id"],"decisions":decisions,
            "transcript":transcript,"status":"COMPLETED","completed_at":now,"updated_at":now}},upsert=True)
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"areas":areas,"meeting_transcript":transcript,
            "status":"SESSION COMPLETED","final_status":"NONE","final_display_text":"","final_share_token":"","active_delegation":{},"updated_at":now},
            "$setOnInsert":{"created_at":now}},upsert=True)
        return {"status":"COMPLETED","area_count":len(areas)}

    @router.post("/community-research")
    async def community_research(request:Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));existing=await db.sp_community_research.find_one({"project_id":p["project_id"]},{"_id":0})
        if existing:
            updates={}
            if not existing.get("social_posts"):updates["social_posts"]=strategic_research_posts(p["organization_name"],p.get("mission",""))
            if not existing.get("token"):updates["token"]=secrets.token_urlsafe(32)
            if updates:
                updates["updated_at"]=now_iso()
                await db.sp_community_research.update_one({"project_id":p["project_id"]},{"$set":updates})
                existing.update(updates)
            return existing
        token=secrets.token_urlsafe(32);posts=strategic_research_posts(p["organization_name"],p.get("mission",""))
        doc={"project_id":p["project_id"],"token":token,"social_posts":posts,"response_count":0,"created_at":now_iso()};await db.sp_community_research.insert_one(doc.copy());return doc

    @router.get("/community-research/{token}")
    async def public_community_research(token:str):
        doc=await db.sp_community_research.find_one({"token":token},{"_id":0})
        if not doc:raise HTTPException(404,"This Community Need Research link is not valid")
        p=await owned_project(doc["project_id"])
        return {"organization_name":p["organization_name"],"mission":p.get("mission",""),"questions":[
            "From what you have personally observed or experienced, what is the most important need or challenge connected to this mission, and why does it matter?",
            "Who is most affected by this need? What does the problem actually look like in their day-to-day life or experience?",
            "Based on what you know, what approach do you believe would make the strongest difference? What should organizations working on this issue do more of, less of, or differently?",
            "What do you believe is currently missing from the way this need is being addressed? Think about services, access, relationships, information, funding, trust or anything else you have noticed.",
            "How could you, your organization, your network or other people in the community realistically help address this need? What contribution or connection could make a difference?"
        ]}

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
        research=await db.sp_community_research.find_one({"project_id":p["project_id"]},{"_id":0})
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
        form=await db.sp_forms.find_one({"project_id":p["project_id"]},{"_id":0}) or {};people=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300)
        if not people:raise HTTPException(409,"At least one completed Strategic Planning Form is required")
        _,_,intake=await paid(sid)
        guide_sections=build_session_sections(form,people,{},intake.get("answers") or {},p)
        titles=[section.get("title","") for section in guide_sections]
        text=(f"STRATEGIC PLANNING SESSION FACILITATION GUIDE\n{p['organization_name']}\n\n"
              "PURPOSE\nThis is one live Board Strategic Planning Session. Board Members have already contributed their individual thinking. The purpose of the session is to review those ideas together, decide which ideas should shape the organization\'s direction, discuss what execution will require, and agree who will help carry the work forward.\n\n"
              "1. PREPARE THE ROOM\nCreate the shared Board screen link and place it in the meeting chat so everyone can follow the same strategic section. Explain that only the Lead User clicks selections; everyone else discusses. Ask everyone for consent before starting microphone transcription. Keep transcription running until the Action Planning and delegation discussion is complete.\n\n"
              "2. REVIEW ONE STRATEGIC SECTION AT A TIME\nFor each section, begin with the organization\'s present information, then review the concise idea cards contributed before the meeting. Invite the people who shared ideas to explain or clarify them in their own words. Do not rush the conversation and do not let the system replace what people actually mean.\n\n"
              "3. CLICK THE IDEAS THE BOARD AGREES SHOULD SHAPE THE PLAN\nThe Lead User selects every idea the Board agrees should influence that section. More than one idea may be selected. The order of selection does NOT assign ownership. For Mission, the Board may explicitly choose to leave the present Mission Statement as it is. The full original responses remain preserved behind the concise cards.\n\n"
              "4. MOVE THROUGH THE COMPLETE STRATEGY\nReview the sections in this order:\n- "+"\n- ".join(titles)+"\n\n"
              "5. COMPLETE ACTION PLANNING\nAt the Action Planning section, agree what should happen first, next and after that. Keep this conversation focused on execution priorities, sequence, resources and immediate actions.\n\n"
              "6. REVIEW THE ROLES PEOPLE SAID THEY WOULD BE WILLING TO PLAY\nThe final screen shows the committee/working-group interests, areas people said they would be willing to lead, and areas they said they would be happy to support. Treat these as each person's own starting point, not an assignment. Ask: 'You said you would be willing to help here. Is that still right, and what would you be comfortable taking responsibility for?' If the Board agrees a different or additional role, say the person's name and the exact agreed responsibility aloud so the transcript records the change. Nobody should be given a role simply because they suggested an idea.\n\n"
              "7. READ BACK THE AGREEMENT BEFORE ENDING\nBefore ending the session, summarize the major strategy decisions and read back any responsibilities explicitly agreed in the room. If the Board chooses not to finalize roles in the meeting, say that clearly. Each participant's own form preferences remain available afterward as proposed starting points for the Lead User to confirm, edit or remove before anything is sent.\n\n"
              "8. END THE SESSION\nEnd the Strategic Planning Session only after every strategic section has an agreed direction, Action Planning is complete and the Roles We Will Play screen has been discussed. Return to the dashboard and generate the Strategic Plan. The system preserves participant-stated willingness, uses the transcript for explicit meeting agreements, and requires the Lead User to confirm or edit every delegation before portfolios or emails are created."
              "\n\nSECTION-BY-SECTION FACILITATION\n\n"
              + "\n\n".join(
                  f"{index}. {section['title'].upper()}\n"
                  f"WHAT TO SAY\n{section['facilitator_prompt']['say']}\n\n"
                  "QUESTIONS TO PUT TO THE BOARD\n- " + "\n- ".join(section['facilitator_prompt']['questions']) + "\n\n"
                  f"BEFORE YOU MOVE ON\n{section['facilitator_prompt']['decision']}"
                  for index,section in enumerate(guide_sections,1)
              ))
        now=now_iso();await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"meeting_status":"Approved","meeting_guide_text":text,"updated_at":now},"$setOnInsert":{"created_at":now}},upsert=True)
        return {"status":"Approved","guide":text}

    @router.post("/session-plan")
    async def generate_session_plan(request: Request):
        sid=(await request.json()).get("session_id","")
        p=await ensure_project(sid)
        session=await db.sp_sessions.find_one({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}) or {}
        plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if not session or not plan.get("areas"):
            raise HTTPException(409,"Complete the Strategic Planning Session first")
        if plan.get("final_status")=="Generating":
            return {"status":"Generating"}

        _,_,intake=await paid(sid)
        await db.sp_plans.update_one(
            {"project_id":p["project_id"]},
            {"$set":{"final_status":"Generating","final_generation_error":"","updated_at":now_iso()}}
        )

        async def run_generation():
            try:
                people=await db.sp_participants.find({"project_id":p["project_id"]},{"_id":0}).to_list(300)
                research=await db.sp_community_research.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
                context=(
                    f"ORGANIZATION: {p['organization_name']}\n"
                    f"ORGANIZATION STARTING MISSION: {p.get('mission','')}\n\n"
                    f"ORGANIZATION INTAKE / STARTING REALITY:\n{json.dumps(intake.get('answers') or {},default=str)}\n\n"
                    f"BOARD-SELECTED STRATEGIC SECTIONS. Each agreed_ideas entry contains the FULL ORIGINAL RESPONSE behind the concise session card:\n{json.dumps(plan.get('areas'),default=str)}\n\n"
                    f"LIVE STRATEGIC PLANNING SESSION TRANSCRIPT:\n{session.get('transcript','')}\n\n"
                    f"COMMUNITY NEED RESEARCH (context/evidence only, not Board authority):\n{json.dumps(research.get('responses') or [],default=str)}"
                )
                generated=await generate_structured(
                    "strategic_session_final_plan",
                    context,
                    "Build the professional Strategic Plan exactly from the Board's selected ideas and live session conclusions. Do not attribute the final plan to individual contributors. Do not introduce a second planning or adoption process."
                )
                display=final_display(generated,p["organization_name"])

                known=[{"participant_id":x.get("participant_id",""),"name":x.get("name",""),"email":x.get("email",""),"role":x.get("role","")} for x in people]
                if not any((x.get("email") or "").lower()==(p.get("founder_email") or "").lower() for x in known):
                    known.append({"participant_id":"","name":p.get("founder_name",""),"email":p.get("founder_email",""),"role":"Organization Leader"})

                # Participant-stated willingness is the baseline proposal.
                # It is never sent or treated as a final assignment until the Lead User confirms it.
                form=await db.sp_forms.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
                role_section=next((section for section in (form.get("content") or {}).get("sections",[])
                                   if "roles we will play" in str(section.get("title","")).lower()),None)
                role_questions=(role_section or {}).get("questions",[])
                preference_delegates={}
                for person in people:
                    response=person.get("response") or {}
                    committee=str(response.get(role_questions[0]["id"],"")).strip() if len(role_questions)>0 else ""
                    lead_pref=str(response.get(role_questions[1]["id"],"")).strip() if len(role_questions)>1 else ""
                    support_pref=str(response.get(role_questions[2]["id"],"")).strip() if len(role_questions)>2 else ""
                    if not any([committee,lead_pref,support_pref]):
                        continue
                    responsibilities=[]
                    if lead_pref:
                        responsibilities.append(f"Willing to lead: {lead_pref}")
                    if support_pref:
                        responsibilities.append(f"Willing to support: {support_pref}")
                    preference_delegates[person["participant_id"]]={
                        "delegation_id":str(uuid.uuid4()),
                        "participant_id":person["participant_id"],
                        "name":person.get("name",""),
                        "email":person.get("email",""),
                        "role":person.get("role",""),
                        "responsibilities":responsibilities,
                        "areas":[committee] if committee else [],
                        "first_action":"",
                        "support_needed":"",
                        "reporting_rhythm":"",
                        "source":"Participant-stated willingness from Strategic Planning Form",
                        "declared_preferences":{
                            "committee_or_group":committee,
                            "willing_to_lead":lead_pref,
                            "willing_to_support":support_pref,
                        },
                    }

                api_key=os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY","")
                model=os.environ.get("CLAUDE_MODEL","claude-sonnet-4-6")
                system=("You extract execution responsibilities that people EXPLICITLY AGREED TO during one nonprofit Board Strategic Planning Session. "
                        "The planning-form preferences supplied separately are statements of willingness, not assignments. "
                        "Use the transcript only to identify explicit live-session agreements, changes or additions. "
                        "A person may receive multiple responsibilities. Include a person who did not complete the planning form when the transcript clearly names them and gives them responsibility. "
                        "Do not infer responsibility merely because somebody suggested an idea, spoke about a topic, is knowledgeable about it, or said before the meeting that they might be willing to help. "
                        "Do not invent names, emails, roles, responsibilities, deadlines or consensus. Return only JSON.")
                prompt=(f"KNOWN PEOPLE:\n{json.dumps(known,default=str)}\n\n"
                        f"PARTICIPANT-STATED WILLINGNESS FROM THEIR OWN FORMS (context only; NOT automatically agreed roles):\n{json.dumps(list(preference_delegates.values()),default=str)}\n\n"
                        f"BOARD-SELECTED STRATEGIC AREAS:\n{json.dumps(plan.get('areas'),default=str)}\n\n"
                        f"STRATEGIC PLANNING SESSION TRANSCRIPT:\n{session.get('transcript','')}\n\n"
                        '{"delegations":[{"name":"","participant_id":"","responsibilities":[""],"areas":[""],"first_action":"","support_needed":"","reporting_rhythm":""}],"declined_participant_ids":[""]}\n'
                        "Return that exact JSON shape. Include only responsibilities explicitly agreed in the live session. "
                        "If the transcript clearly shows that a known participant declined or withdrew the role they had previously said they might be willing to take, put their exact known participant_id in declined_participant_ids. "
                        "Do not mark someone declined merely because their role was not discussed.")
                try:
                    chat=LlmChat(api_key=api_key,session_id=f"sp-session-delegation-{p['project_id']}-{uuid.uuid4()}",system_message=system).with_model("anthropic",model)
                    raw=await chat.send_message(UserMessage(text=prompt))
                    parsed=parse_json_response(raw if isinstance(raw,str) else getattr(raw,"text",str(raw)))
                    extracted=parsed.get("delegations") or []
                    declined_ids={str(x) for x in (parsed.get("declined_participant_ids") or []) if str(x)}
                except Exception:
                    logger.exception("Strategic session delegation extraction failed for %s",p["project_id"])
                    extracted=[]
                    declined_ids=set()

                by_id={x.get("participant_id"):x for x in known if x.get("participant_id")}
                by_name={str(x.get("name","")).strip().lower():x for x in known if str(x.get("name","")).strip()}
                delegates=[item for pid,item in preference_delegates.items() if pid not in declined_ids]
                delegate_index={d.get("participant_id"):index for index,d in enumerate(delegates) if d.get("participant_id")}
                for item in extracted:
                    if not isinstance(item,dict):
                        continue
                    name=str(item.get("name","")).strip()
                    responsibilities=[str(x).strip() for x in (item.get("responsibilities") or []) if str(x).strip()]
                    if not name or not responsibilities:
                        continue
                    known_person=by_id.get(str(item.get("participant_id",""))) or by_name.get(name.lower()) or {}
                    participant_id=known_person.get("participant_id","")
                    live_delegate={
                        "delegation_id":delegates[delegate_index[participant_id]]["delegation_id"] if participant_id in delegate_index else str(uuid.uuid4()),
                        "participant_id":participant_id,
                        "name":known_person.get("name") or name,
                        "email":known_person.get("email",""),
                        "role":known_person.get("role",""),
                        "responsibilities":responsibilities[:20],
                        "areas":[str(x).strip() for x in (item.get("areas") or []) if str(x).strip()][:20],
                        "first_action":str(item.get("first_action","")).strip()[:2000],
                        "support_needed":str(item.get("support_needed","")).strip()[:2000],
                        "reporting_rhythm":str(item.get("reporting_rhythm","")).strip()[:1000],
                        "source":"Explicit Strategic Planning Session agreement",
                        "declared_preferences":preference_delegates.get(participant_id,{}).get("declared_preferences",{}),
                    }
                    if participant_id in delegate_index:
                        delegates[delegate_index[participant_id]]=live_delegate
                    else:
                        delegates.append(live_delegate)

                assignments={(d.get("participant_id") or d["delegation_id"]):"\n".join(d["responsibilities"]) for d in delegates}
                active={"delegates":delegates,"assignments":assignments,"transcript":session.get("transcript",""),
                        "source":"strategic_planning_session_transcript","manual_assignments_authoritative":False,
                        "saved_at":now_iso(),"next_meeting_guide":"Ask each delegated leader to report progress, evidence, barriers, decisions required and the next action."}

                await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{
                    "status":"PLAN READY","structured":generated,"display_text":display,
                    "final_status":"Draft","final_display_text":display,"final_share_token":"",
                    "active_delegation":active,"generated_from_session_at":now_iso(),"updated_at":now_iso()
                }})
            except Exception as exc:
                logger.exception("Strategic session plan generation failed for %s",p["project_id"])
                await db.sp_plans.update_one(
                    {"project_id":p["project_id"]},
                    {"$set":{"final_status":"Failed","final_generation_error":str(exc)[:500],"updated_at":now_iso()}}
                )

        asyncio.create_task(run_generation())
        return {"status":"Generating"}

    @router.post("/auto-delegate")
    async def auto_delegate(request:Request):
        sid=(await request.json()).get("session_id","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};people=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300);areas=plan.get("areas",[])
        if not people or not areas:raise HTTPException(409,"Board responses and a Strategic Plan Draft are required first")
        # Assign for alignment while balancing workload. Every area gets an owner.
        # When there are more people than areas, extra participants become collaborators
        # so every participating Board Member has a meaningful strategic role.
        loads={pson["participant_id"]:0 for pson in people}
        for a in areas:
            words=(a.get("area","")+" "+a.get("direction","")).lower().split();scored=[]
            for pson in people:
                own=str(pson.get("response",{})).lower();alignment=sum(1 for w in words if len(w)>4 and w in own)
                scored.append((alignment,-loads[pson["participant_id"]],pson))
            scored.sort(key=lambda x:(x[0],x[1]),reverse=True);owner=scored[0][2];loads[owner["participant_id"]]+=1
            a["owner_participant_id"]=owner["participant_id"];a["collaborator_participant_ids"]=[];a["status"]="ASSIGNED"
        unassigned=[p for p in people if loads[p["participant_id"]]==0]
        for pson in unassigned:
            best=max(areas,key=lambda a:sum(1 for w in (a.get("area","")+" "+a.get("direction","")).lower().split() if len(w)>4 and w in str(pson.get("response",{})).lower()))
            best.setdefault("collaborator_participant_ids",[]).append(pson["participant_id"])
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"areas":areas}});return {"status":"ASSIGNED","area_count":len(areas)}

    @router.post("/send-area-assignment")
    async def area_assignment(request:Request):
        body=await request.json();sid=body.get("session_id","");key=body.get("area_key","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};area=next((x for x in plan.get("areas",[]) if x.get("area_key")==key),None)
        if not area or not area.get("owner_participant_id"):raise HTTPException(409,"Assign this strategic area first")
        recipients=[area["owner_participant_id"]]+area.get("collaborator_participant_ids",[]);sent=0
        for pid in recipients:
            person=await db.sp_participants.find_one({"project_id":p["project_id"],"participant_id":pid},{"_id":0})
            if not person: continue
            assignments=person.get("area_assignment_tokens") or {};token=assignments.get(key) or secrets.token_urlsafe(32);assignments[key]=token
            await db.sp_participants.update_one({"participant_id":pid},{"$set":{"area_assignment_tokens":assignments}})
            if pid==area["owner_participant_id"]:
                area["pack_token"]=token
            area["pack_status"]="Approved";area["pack_text"]=pack_display({"mission_direction":area.get("direction",""),"foundational_priorities":area.get("proposed_priorities",[]),"ideas":area.get("ideas_shared",[]),"development_instruction":"Use the agreed idea, every other idea shared for this section, and the Strategic Planning Session transcript below to build the first draft. Define exactly what must be done, the people and technology required, your role in leading and overseeing it, the full cost of executing it at 100%, and a step-by-step action plan for the planning period.\n\nSESSION TRANSCRIPT:\n"+area.get("meeting_transcript","")},area["area"],p["organization_name"])
            link=f"{origin_of(request)}/area-pack/{token}";e=pack_email(p,area,person,link);await send_email(person["email"],e["subject"],e["body"],e["button_label"],e["form_link"],reply_to=p.get("founder_email",""));sent+=1
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"areas":plan["areas"]}})
        return {"status":"sent","count":sent}

    @router.post("/send-delegation")
    async def send_delegation(request: Request):
        body=await request.json();sid=body.get("session_id","");pid=body.get("participant_id","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};person=await db.sp_participants.find_one({"project_id":p["project_id"],"participant_id":pid},{"_id":0})
        if not person:raise HTTPException(404,"This Board Member is not available")
        owned=[a for a in plan.get("areas",[]) if a.get("owner_participant_id")==pid]
        if not owned:raise HTTPException(409,"No strategic sections have been delegated to this Board Member")
        assignments=person.get("area_assignment_tokens") or {};links=[]
        for area in owned:
            key=area["area_key"];token=assignments.get(key) or secrets.token_urlsafe(32);assignments[key]=token;area["pack_token"]=token;area["pack_status"]="Approved"
            area["pack_text"]=pack_display({"mission_direction":area.get("direction",""),"foundational_priorities":area.get("proposed_priorities",[]),"ideas":area.get("ideas_shared",[]),"development_instruction":"Use the agreed idea, every other idea shared for this section, and the Strategic Planning Session transcript below to build the first draft. Define exactly what must be done, the people and technology required, your role in leading and overseeing it, the full cost of executing it at 100%, and a step-by-step action plan for the planning period.\n\nSESSION TRANSCRIPT:\n"+area.get("meeting_transcript","")},area["area"],p["organization_name"])
            links.append((area["area"],f"{origin_of(request)}/area-pack/{token}"))
        await db.sp_participants.update_one({"participant_id":pid},{"$set":{"area_assignment_tokens":assignments}});await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"areas":plan["areas"]}})
        first=(person.get("name") or "Board Member").split()[0];listing="\n\n".join(f"{title}:\n{link}" for title,link in links);foundation_link=f"{origin_of(request)}/strategic-draft/{plan.get('share_token')}";body_text=f"Dear {first},\n\nDuring our Strategic Planning Session, the Board selected your contribution and delegated the following section{'s' if len(links)>1 else ''} to you. Review the Board's foundational strategy first, then open each assigned section. Every section contains the agreed direction, every idea shared by other participants, the meeting context and instructions for building the detailed plan you will present later in this same Board session. Open it now, let AI create the first working draft from the Board's agreed ideas, edit it so it reflects the Board's thinking and your judgment, then approve it when you are ready to present.\n\nBOARD FOUNDATIONAL STRATEGY:\n{foundation_link}\n\nYOUR DELEGATED SECTION{'S' if len(links)>1 else ''}:\n{listing}\n\nThank you for accepting responsibility for helping build this part of {p['organization_name']}'s future."
        await send_email(person["email"],f"Your Strategic Planning Delegation | {p['organization_name']}",body_text,"OPEN MY FIRST DELEGATED SECTION",links[0][1],reply_to=p.get("founder_email",""))
        return {"status":"sent","section_count":len(links)}

    @router.post("/final-plan")
    async def build_final(request:Request):
        sid=(await request.json()).get("session_id","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};areas=plan.get("areas",[])
        if not areas or any(a.get("detailed_plan_status")!="Approved" or not a.get("submitted_plan") for a in areas):raise HTTPException(409,"Every delegated strategic area needs an approved detailed plan before consolidation")
        context=f"ORGANIZATION: {p['organization_name']}\nMISSION: {p.get('mission','')}\n\nFOUNDATIONAL PLAN:\n{plan.get('display_text','')}\n\nEVERY AREA'S AGREED DIRECTION, EVERY SUBMITTED IDEA, NONPROFIT BOARD BUILDER RECOMMENDATIONS AND MEETING CONTEXT:\n{json.dumps(areas,default=str)}\n\nAPPROVED DETAILED AREA PLANS:\n"+"\n\n".join(f"{a['area']}:\n{a['submitted_plan']}" for a in areas);g=await generate_structured("strategic_final_plan",context,"Consolidate the agreed directions and approved detailed plans into one coherent present Strategic Plan for Board review. Preserve the Board\'s selected ideas, the builders\' approved wording and the organization\'s distinctive voice. Do not compress different agreed ideas into generic consensus language merely for neatness. Structure and connect the work so it reads coherently, but never improve it by silently replacing the Board\'s actual thinking. Recommendations may support execution only where consistent with Board-approved content. Do not invent new Board decisions.")
        display=final_display(g,p["organization_name"]);await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"final_status":"Draft","final_display_text":display,"final_share_token":"","updated_at":now_iso()}});return {"status":"Draft"}

    @router.post("/presentation-meeting")
    async def save_presentation_meeting(request: Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        required=["meeting_date","start_time","timezone_name","meeting_format"]
        if any(not str(body.get(k,"")).strip() for k in required):raise HTTPException(422,"Enter the presentation meeting date, time, time zone and format")
        meeting={k:str(body.get(k,"")).strip()[:500] for k in required+["meeting_link","meeting_location","note"]}
        meeting.update({"share_token":(plan.get("presentation_meeting") or {}).get("share_token") or secrets.token_urlsafe(32),"current_area_index":0,"status":"SCHEDULED","saved_at":now_iso()})
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"presentation_meeting":meeting,"updated_at":now_iso()}})
        return meeting

    @router.post("/presentation-meeting/progress")
    async def presentation_progress(request: Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));index=max(0,int(body.get("current_area_index",0)))
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"presentation_meeting.current_area_index":index,"presentation_meeting.status":"IN PROGRESS","updated_at":now_iso()}})
        return {"current_area_index":index}

    @router.get("/presentation-meeting/watch/{token}")
    async def watch_presentation(token: str):
        plan=await db.sp_plans.find_one({"presentation_meeting.share_token":token},{"_id":0})
        if not plan:raise HTTPException(404,"This presentation meeting link is not valid")
        p=await owned_project(plan["project_id"]);areas=plan.get("areas") or [];meeting=plan.get("presentation_meeting") or {};index=min(meeting.get("current_area_index",0),max(0,len(areas)-1))
        area=areas[index] if areas else None
        return {"organization_name":p["organization_name"],"status":meeting.get("status","SCHEDULED"),"current_area_index":index,"total_areas":len(areas),"area":area,"present_plan":plan.get("final_display_text",""),"approved_area_keys":meeting.get("approved_area_keys",[])}

    @router.post("/presentation-meeting/guide")
    async def presentation_guide(request: Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if not plan.get("areas"):raise HTTPException(409,"Complete the detailed strategic area plans first")
        guide=(f"STRATEGIC PLAN PRESENTATION AND DELEGATION MEETING GUIDE\n{p['organization_name']}\n\n"
               "THIS IS THE SECOND HALF OF THE SAME BOARD STRATEGIC PLANNING SESSION. Do not schedule another meeting unless your Board chooses to.\n\n"
               "1. KEEP TRANSCRIPTION RUNNING\nRemind everyone that the discussion is being transcribed with consent so the final plan and delegation reflect what the Board actually agrees.\n\n"
               "2. PRESENT ONE SECTION AT A TIME\nOpen the shared plan. Invite the person who built the section to present the agreed ideas, detailed plan, people and technology required, cost, action sequence and unresolved decisions.\n\n"
               "3. DISCUSS AND ADOPT THE SECTION\nInvite questions, corrections and additional ideas. Say every final change aloud. When the Board agrees, click BOARD AGREES WITH THIS SECTION before moving forward. The transcript explains the discussion; the approval click confirms that the Board adopted that section.\n\n"
               "4. DELEGATE EXECUTION OUT LOUD\nFor every adopted section, explicitly state who will lead, support or own each execution responsibility, the first action, support required and reporting rhythm. A responsibility may go to the person who built the section, another participant, the Lead User, or somebody who did not fill the form. If someone who is not already in the platform receives work, say their name clearly; their email can be added before the delegation is sent.\n\n"
               "5. REVIEW THE COMPLETE DELEGATION\nBefore closing, read back every person's name and responsibility so the transcript contains an unambiguous final delegation record.\n\n"
               "6. CLOSE THE SESSION\nStop transcription only after the Board has adopted every section and confirmed the execution delegation. The application will use the adopted sections and transcript to prepare the editable Final Strategic Plan, delegation emails, Leadership Portfolios and Executive Assistants.")
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"presentation_meeting.guide":guide,"updated_at":now_iso()}});return {"guide":guide}

    @router.post("/presentation-meeting/start-now")
    async def start_presentation_now(request: Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if not plan.get("final_display_text"):raise HTTPException(409,"Generate the Present Strategic Plan first")
        meeting=plan.get("presentation_meeting") or {};token=meeting.get("share_token") or secrets.token_urlsafe(32)
        meeting.update({"share_token":token,"current_area_index":meeting.get("current_area_index",0),"status":"IN PROGRESS",
                        "started_at":meeting.get("started_at") or now_iso(),"approved_area_keys":meeting.get("approved_area_keys") or []})
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"presentation_meeting":meeting,"updated_at":now_iso()}})
        return {"status":"IN PROGRESS","share_token":token,"current_area_index":meeting.get("current_area_index",0),"approved_area_keys":meeting.get("approved_area_keys",[])}

    @router.post("/presentation-meeting/approve-area")
    async def approve_presentation_area(request: Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));area_key=str(body.get("area_key","")).strip();plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};areas=plan.get("areas") or []
        if not area_key or not any(str(area.get("area_key",""))==area_key for area in areas):raise HTTPException(422,"Choose a valid strategic area")
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$addToSet":{"presentation_meeting.approved_area_keys":area_key},"$set":{"presentation_meeting.status":"IN PROGRESS","updated_at":now_iso()}})
        return {"status":"approved","area_key":area_key}

    @router.post("/presentation-meeting/send")
    async def send_presentation_meeting(request: Request):
        sid=(await request.json()).get("session_id","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};meeting=plan.get("presentation_meeting") or {}
        if not plan.get("final_display_text"):raise HTTPException(409,"Generate the Present Strategic Plan first")
        if not meeting.get("meeting_date"):raise HTTPException(409,"Save the presentation meeting details first")
        people=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300);link=f"{origin_of(request)}/strategic-presentation/{meeting['share_token']}";sent=0
        for person in people:
            first=(person.get("name") or "Board Member").split()[0];body=f"Dear {first},\n\nThe Present Strategic Plan for {p['organization_name']} is ready for our Board presentation and delegation meeting.\n\nDate: {meeting['meeting_date']}\nTime: {meeting['start_time']} {meeting['timezone_name']}\nFormat: {meeting['meeting_format']}\nMeeting link/location: {meeting.get('meeting_link') or meeting.get('meeting_location') or 'The organization will confirm this directly.'}\n\nOpen the shared plan below and prepare to present the section you developed.\n\n{link}"
            await send_email(person["email"],f"Strategic Plan Presentation Meeting | {p['organization_name']}",body,"OPEN PRESENT STRATEGIC PLAN",link,reply_to=p.get("founder_email",""));sent+=1
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"presentation_meeting.sent_at":now_iso(),"presentation_meeting.sent_count":sent}});return {"status":"sent","count":sent}

    @router.post("/presentation-meeting/complete")
    async def complete_presentation_meeting(request: Request):
        body=await request.json();sid=body.get("session_id","");transcript=str(body.get("transcript","")).strip()[:60000];p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};areas=plan.get("areas") or [];meeting=plan.get("presentation_meeting") or {};approved_keys=set(meeting.get("approved_area_keys") or []);required_keys={str(area.get("area_key","")) for area in areas if str(area.get("area_key",""))}
        if not transcript:raise HTTPException(422,"Record or paste the Board session transcript before completing the meeting")
        if required_keys and not required_keys.issubset(approved_keys):raise HTTPException(409,"Have the Board adopt every strategic section before completing the session")
        context=f"ORGANIZATION: {p['organization_name']}\nMISSION: {p.get('mission','')}\n\nPRESENT STRATEGIC PLAN:\n{plan.get('final_display_text','')}\n\nBOARD-ADOPTED AREA KEYS:\n{json.dumps(sorted(approved_keys))}\n\nDETAILED AREAS:\n{json.dumps(areas,default=str)}\n\nPRESENTATION AND DELEGATION MEETING TRANSCRIPT:\n{transcript}"
        generated=await generate_structured("strategic_final_plan",context,"Create the Final Strategic Plan from the Board-adopted sections and the final review/delegation transcript. The adopted section content is authoritative. Apply only changes, additions or corrections that the transcript clearly shows the Board agreed to. Preserve the organization\'s and contributors\' distinctive wording, reasoning and intent instead of smoothing it into generic strategy language. Preserve everything the Board did not change. Delegation decisions belong in the execution context and must not be used to rewrite unrelated strategy content. Do not invent decisions, consensus, facts or commitments.")
        display=final_display(generated,p["organization_name"])
        people=await db.sp_participants.find({"project_id":p["project_id"]},{"_id":0}).to_list(300)
        known=[{"participant_id":x.get("participant_id",""),"name":x.get("name",""),"email":x.get("email",""),"role":x.get("role","")} for x in people]
        if not any((x.get("email") or "").lower()==(p.get("founder_email") or "").lower() for x in known):
            known.append({"participant_id":"","name":p.get("founder_name",""),"email":p.get("founder_email",""),"role":"Organization Leader"})
        api_key=os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY","");model=os.environ.get("CLAUDE_MODEL","claude-sonnet-4-6")
        system=("You extract final execution delegation decisions from one nonprofit Board meeting transcript. "
            "Use only explicit delegation decisions supported by the transcript. A person may receive multiple responsibilities. "
            "Include people who did not fill the planning form if the meeting explicitly delegates work to them. "
            "Do not infer a delegation merely because someone presented an area or originally suggested an idea. "
            "Do not invent names, emails, responsibilities, authority, deadlines or consensus. Return only JSON.")
        prompt=(f"KNOWN PEOPLE AND EMAILS:\n{json.dumps(known,default=str)}\n\nFINAL STRATEGIC PLAN AFTER THE MEETING:\n{display}\n\nMEETING TRANSCRIPT:\n{transcript}\n\n"
            'Return exactly {"delegations":[{"name":"","participant_id":"","responsibilities":[""],"areas":[""],"first_action":"","support_needed":"","reporting_rhythm":""}]}. '
            "participant_id must be copied only when the person clearly matches a known person. Include only people explicitly given execution responsibility.")
        try:
            chat=LlmChat(api_key=api_key,session_id=f"sp-delegation-{p['project_id']}-{uuid.uuid4()}",system_message=system).with_model("anthropic",model)
            raw=await chat.send_message(UserMessage(text=prompt));parsed=parse_json_response(raw if isinstance(raw,str) else getattr(raw,"text",str(raw)));extracted=parsed.get("delegations") or []
        except Exception:
            logger.exception("Strategic delegation extraction failed for %s",p["project_id"]);extracted=[]
        by_id={x.get("participant_id"):x for x in known if x.get("participant_id")};by_name={str(x.get("name","")).strip().lower():x for x in known if str(x.get("name","")).strip()};delegates=[]
        for item in extracted:
            if not isinstance(item,dict):continue
            name=str(item.get("name","")).strip();responsibilities=[str(x).strip() for x in (item.get("responsibilities") or []) if str(x).strip()]
            if not name or not responsibilities:continue
            known_person=by_id.get(str(item.get("participant_id",""))) or by_name.get(name.lower()) or {}
            delegates.append({"delegation_id":str(uuid.uuid4()),"participant_id":known_person.get("participant_id",""),"name":known_person.get("name") or name,
                "email":known_person.get("email",""),"role":known_person.get("role",""),"responsibilities":responsibilities[:20],
                "areas":[str(x).strip() for x in (item.get("areas") or []) if str(x).strip()][:20],"first_action":str(item.get("first_action","")).strip()[:2000],
                "support_needed":str(item.get("support_needed","")).strip()[:2000],"reporting_rhythm":str(item.get("reporting_rhythm","")).strip()[:1000]})
        assignments={(d.get("participant_id") or d["delegation_id"]):"\n".join(d["responsibilities"]) for d in delegates}
        active={"delegates":delegates,"assignments":assignments,"transcript":transcript,"source":"presentation_delegation_transcript",
            "manual_assignments_authoritative":False,"saved_at":now_iso(),"next_meeting_guide":"Ask each delegated leader to present what they completed, evidence of progress, decisions required, barriers and the next action."}
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"final_status":"Draft","final_display_text":display,"final_share_token":"",
            "presentation_meeting.status":"COMPLETED","presentation_meeting.transcript":transcript,"presentation_meeting.completed_at":now_iso(),
            "active_delegation":active,"updated_at":now_iso()}})
        return {"status":"Draft","delegation_count":len(delegates)}


    @router.put("/final-plan/draft")
    async def edit_final_plan_draft(request:Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));text=str(body.get("display_text","")).strip()[:120000];plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if plan.get("final_status")=="Approved":raise HTTPException(409,"The Final Strategic Plan is already approved")
        if not text:raise HTTPException(422,"The Strategic Plan cannot be empty")
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"final_status":"Draft","final_display_text":text,"updated_at":now_iso()}});return {"status":"Draft"}

    @router.post("/final-plan/approve")
    async def approve_final_plan(request:Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if not plan.get("final_display_text"):raise HTTPException(409,"Generate and review the Strategic Plan Draft first")
        token=plan.get("final_share_token") or secrets.token_urlsafe(32);await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"final_status":"Approved","final_share_token":token,"final_approved_at":now_iso(),"updated_at":now_iso()}});return {"status":"Approved"}

    @router.get("/final-plan/pdf")
    async def guided_final_pdf(session_id:str,request:Request):
        p=await ensure_project(session_id);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if not plan.get("final_display_text"):raise HTTPException(404,"Final Strategic Plan is not ready")
        return build_portfolio_pdf("STRATEGIC PLAN",p["organization_name"],{"organization_name":p["organization_name"],"issued_by":p["founder_name"]},plan["final_display_text"])

    @router.post("/send-final-plan")
    async def send_guided_final_plan(request: Request):
        sid=(await request.json()).get("session_id","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if plan.get("final_status")!="Approved" or not plan.get("final_display_text") or not plan.get("final_share_token"):raise HTTPException(409,"Review, edit and approve the Final Strategic Plan first")
        people=await db.sp_participants.find({"project_id":p["project_id"],"status":"COMPLETED"},{"_id":0}).to_list(300);link=f"{origin_of(request)}/strategic-plan/{plan['final_share_token']}";sent=0
        for person in people:
            first=(person.get("name") or "Board Member").split()[0];body=f"Dear {first},\n\nOur complete Strategic Plan for {p['organization_name']} is ready. It reflects the directions agreed during our Strategic Planning Session and the final plan approved by the organization.\n\n[VIEW THE STRATEGIC PLAN]\n\nThank you for helping build the plan.\n\n{p.get('founder_name','')}\n{p['organization_name']}";await send_email(person["email"],f"Our Strategic Plan | {p['organization_name']}",body,"VIEW THE STRATEGIC PLAN",link,reply_to=p.get("founder_email",""));sent+=1
        return {"status":"sent","count":sent}

    @router.put("/active-delegation/people")
    async def save_delegated_people(request:Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};incoming=body.get("delegates") or [];people=await db.sp_participants.find({"project_id":p["project_id"]},{"_id":0}).to_list(300);by_id={x["participant_id"]:x for x in people};clean=[]
        for item in incoming[:100]:
            if not isinstance(item,dict):continue
            name=str(item.get("name","")).strip();responsibilities=[str(x).strip() for x in (item.get("responsibilities") or []) if str(x).strip()]
            if not name or not responsibilities:continue
            pid=str(item.get("participant_id",""));known=by_id.get(pid,{})
            clean.append({"delegation_id":str(item.get("delegation_id") or uuid.uuid4()),"participant_id":pid if known else "","name":name,
                "email":str(item.get("email") or known.get("email","")).strip().lower(),"role":str(item.get("role") or known.get("role","")).strip(),
                "responsibilities":responsibilities[:20],"areas":[str(x).strip() for x in (item.get("areas") or []) if str(x).strip()][:20],
                "first_action":str(item.get("first_action","")).strip()[:2000],"support_needed":str(item.get("support_needed","")).strip()[:2000],
                "reporting_rhythm":str(item.get("reporting_rhythm","")).strip()[:1000],
                "source":str(item.get("source","Lead User confirmed"))[:300],
                "declared_preferences":item.get("declared_preferences") if isinstance(item.get("declared_preferences"),dict) else {}})
        if not clean:raise HTTPException(422,"Keep at least one person with a delegated responsibility")
        active=plan.get("active_delegation") or {};active["delegates"]=clean;active["assignments"]={(d.get("participant_id") or d["delegation_id"]):"\n".join(d["responsibilities"]) for d in clean};active["manual_assignments_authoritative"]=True;active["saved_at"]=now_iso()
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"active_delegation":active,"updated_at":now_iso()}});return {"status":"saved","count":len(clean)}

    @router.post("/portfolios")
    async def portfolios(request:Request):
        sid=(await request.json()).get("session_id","");p=await ensure_project(sid);plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if plan.get("final_status")!="Approved" or not plan.get("final_display_text") or not plan.get("final_share_token"):raise HTTPException(409,"Review, edit and approve the Final Strategic Plan first")
        delegates=(plan.get("active_delegation") or {}).get("delegates") or []
        if not delegates:raise HTTPException(409,"Confirm at least one responsibility agreed during the Strategic Planning Session before creating execution portfolios")
        access=await ensure_execution_access(p);existing={x.get("delegation_id"):x for x in (plan.get("leadership_portfolios") or [])};rows=[]
        for delegate in delegates:
            delegation_id=delegate.get("delegation_id") or str(uuid.uuid4());previous=existing.get(delegation_id) or {};areas=delegate.get("areas") or [];responsibility="\n".join(f"- {x}" for x in delegate.get("responsibilities") or [])
            text=f"BOARD LEADERSHIP PORTFOLIO\n{delegate.get('name','')}\n{p['organization_name']}\n\nYOUR DELEGATED RESPONSIBILITY\n{responsibility}\n\nSTRATEGIC AREAS\n"+("\n".join(f"- {x}" for x in areas) or "- Use the responsibilities above as the authority for your execution role")
            if delegate.get("first_action"):text+=f"\n\nFIRST ACTION\n{delegate['first_action']}"
            if delegate.get("support_needed"):text+=f"\n\nSUPPORT REQUIRED\n{delegate['support_needed']}"
            if delegate.get("reporting_rhythm"):text+=f"\n\nREPORTING RHYTHM\n{delegate['reporting_rhythm']}"
            text+="\n\nHOW TO WORK WITH YOUR EXECUTIVE ASSISTANT\nYour assistant uses the approved Strategic Plan, this delegated portfolio and confirmed meeting context. Ask it to help you plan, prepare messages, create checklists, build resources and prepare Board updates that directly support this role."
            rows.append({"delegation_id":delegation_id,"participant_id":delegate.get("participant_id",""),"name":delegate.get("name",""),"email":delegate.get("email",""),
                "role":delegate.get("role",""),"areas":areas,"responsibilities":delegate.get("responsibilities") or [],"text":text,
                "token":previous.get("token") or secrets.token_urlsafe(24),"url":f"/strategic-leadership-portfolio/{previous.get('token') or ''}",
                "assistant_access_started_at":access.get("started_at"),"assistant_access_included_until":access.get("included_until"),"sent_at":previous.get("sent_at","")})
        for row in rows:row["url"]=f"/strategic-leadership-portfolio/{row['token']}"
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"leadership_portfolios":rows}})
        return {"status":"created","count":len(rows),"included_until":access.get("included_until")}

    @router.post("/leadership-portfolio/send")
    async def send_leadership_portfolio(request:Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));token=str(body.get("token",""))
        plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {};rows=plan.get("leadership_portfolios") or []
        row=next((x for x in rows if x.get("token")==token),None)
        if not row:raise HTTPException(404,"This delegation is not available")
        if not row.get("email"):raise HTTPException(422,"Add this person's email address before sending their delegation")
        origin=origin_of(request);experience_link=f"{origin}/strategic-leadership-portfolio/{token}";assistant_link=f"{origin}/strategic-leadership-assistant/{token}"
        first=(row.get("name") or "Board Member").split()[0]
        responsibility="\n".join(f"- {x}" for x in row.get("responsibilities") or [])
        body_text=(f"Dear {first},\n\n"
            f"Our Strategic Plan for {p['organization_name']} is ready. During the Strategic Planning Session, the Board also agreed on the responsibility you will help carry forward:\n\n"
            f"{responsibility}\n\n"
            "Use the secure link below. It opens the approved Strategic Plan first. When you finish reviewing it, click HOW I CAN GET INVOLVED to see your personal Board Leadership Portfolio, download it and open your Executive Assistant.\n\n"
            f"{experience_link}\n\n"
            "Please bookmark that page. It is your ongoing entry point to the plan, your role and your execution support.\n\n"
            "You can also bookmark your Executive Assistant directly here:\n"
            f"{assistant_link}\n\n"
            f"{p.get('founder_name','')}\n{p['organization_name']}")
        await send_email(row["email"],f"Your Strategic Plan And Board Role | {p['organization_name']}",body_text,"OPEN STRATEGIC PLAN & MY ROLE",experience_link,reply_to=p.get("founder_email",""))
        for item in rows:
            if item.get("token")==token:item["sent_at"]=now_iso()
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"leadership_portfolios":rows}})
        return {"status":"sent"}



    @router.post("/active-delegation")
    async def save_active_delegation(request:Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));plan=await db.sp_plans.find_one({"project_id":p["project_id"]},{"_id":0}) or {}
        if not plan.get("final_display_text"):raise HTTPException(409,"Generate the Final Strategic Plan before active delegation")
        assignments={str(k):str(v).strip()[:6000] for k,v in (body.get("assignments") or {}).items() if str(v).strip()};transcript=str(body.get("transcript","")).strip()[:30000]
        if not assignments and not transcript:raise HTTPException(422,"Enter at least one delegated responsibility or provide the delegation meeting transcript")
        existing_active=plan.get("active_delegation") or {}
        record={"assignments":assignments,"delegates":existing_active.get("delegates",[]),"transcript":transcript,"manual_assignments_authoritative":bool(assignments),"saved_at":now_iso(),"next_meeting_guide":"Ask each Board Member to present what they completed, evidence of progress, decisions required, barriers and the next action. Review one responsibility at a time. Record or upload the transcript with consent. Do not change the Strategic Plan automatically. The founder reviews the transcript and confirms every update before it changes the plan or a delegation."}
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"active_delegation":record,"updated_at":now_iso()}});return {"status":"saved"}

    @router.post("/support")
    async def guided_support(request: Request):
        body=await request.json();sid=body.get("session_id","");p=await ensure_project(sid);support_type=str(body.get("support_type","")).strip()[:200];message=str(body.get("message","")).strip()[:10000]
        if not support_type or not message:raise HTTPException(422,"Choose what you need help with and enter your message")
        record={"support_request_id":str(uuid.uuid4()),"project_id":p["project_id"],"session_id":sid,"name":p.get("founder_name",""),"organization":p.get("organization_name",""),"email":p.get("founder_email",""),"product":"Strategic Planning","support_type":support_type,"message":message,"created_at":now_iso(),"delivery_status":"Pending"}
        await db.support_requests.insert_one(record.copy());owner=os.environ.get("OWNER_NOTIFICATION_EMAIL") or os.environ.get("OWNER_EMAIL")
        if owner:
            try:
                resend.api_key=os.environ["RESEND_API_KEY"].strip('"');html="<h2>Strategic Planning Support Request</h2>"+"".join(f"<p><strong>{k}:</strong> {str(v)}</p>" for k,v in {"Name":record["name"],"Organization":record["organization"],"Email":record["email"],"Support type":support_type,"Message":message}.items());email_message={"from":os.environ["NONPROFIT_SENDER"],"to":[owner],"subject":f"Strategic Planning support request | {p['organization_name']}","html":html}
                if p.get("founder_email"):email_message["reply_to"]=[p["founder_email"]]
                await resend.Emails.send_async(email_message);await db.support_requests.update_one({"support_request_id":record["support_request_id"]},{"$set":{"delivery_status":"Sent"}})
            except Exception:
                logger.exception("Strategic Planning support notification failed")
                await db.support_requests.update_one({"support_request_id":record["support_request_id"]},{"$set":{"delivery_status":"Failed"}})
        return {"message":"Your support request has been received. We will be in touch through email."}

    @router.post("/follow-up-meeting")
    async def save_follow_up_meeting(request:Request):
        body=await request.json();p=await ensure_project(body.get("session_id",""));transcript=str(body.get("transcript","")).strip()[:40000]
        if not transcript:raise HTTPException(422,"Paste or upload the follow-up meeting transcript first")
        record={"transcript":transcript,"founder_confirmed":bool(body.get("founder_confirmed")),"saved_at":now_iso(),"status":"CONFIRMED" if body.get("founder_confirmed") else "AWAITING FOUNDER CONFIRMATION"}
        await db.sp_plans.update_one({"project_id":p["project_id"]},{"$set":{"follow_up_meeting":record,"updated_at":now_iso()}});return {"status":record["status"]}

    @router.get("/leadership-portfolio/{token}")
    async def leadership_portfolio(token:str):
        plan=await db.sp_plans.find_one({"leadership_portfolios.token":token,"final_status":"Approved"},{"_id":0})
        if not plan: raise HTTPException(404,"This Board Member Leadership Portfolio is not available")
        row=next((x for x in plan.get("leadership_portfolios",[]) if x.get("token")==token),None)
        if not row: raise HTTPException(404,"This Board Member Leadership Portfolio is not available")
        project=await owned_project(plan["project_id"])
        return {"title":"Board Member Leadership Portfolio","organization_name":project["organization_name"],"member_name":row.get("name",""),"areas":row.get("areas",[]),
                "display_text":row.get("text",""),"strategic_plan_text":plan.get("final_display_text",""),
                "strategic_plan_url":f"/strategic-plan/{plan.get('final_share_token')}" if plan.get("final_share_token") else "",
                "assistant_url":f"/strategic-leadership-assistant/{token}","issued_by":project.get("founder_name","")}

    @router.get("/leadership-portfolio/{token}/pdf")
    async def leadership_portfolio_pdf(token:str):
        plan=await db.sp_plans.find_one({"leadership_portfolios.token":token,"final_status":"Approved"},{"_id":0})
        if not plan: raise HTTPException(404,"This Board Member Leadership Portfolio is not available")
        row=next((x for x in plan.get("leadership_portfolios",[]) if x.get("token")==token),None)
        project=await owned_project(plan["project_id"])
        return build_portfolio_pdf("BOARD MEMBER LEADERSHIP PORTFOLIO",row.get("name",""),{"organization_name":project["organization_name"],"issued_by":project.get("founder_name","")},row.get("text",""))

    @router.get("/leadership-assistant/{token}")
    async def leadership_assistant(token:str):
        plan=await db.sp_plans.find_one({"leadership_portfolios.token":token,"final_status":"Approved"},{"_id":0})
        if not plan:raise HTTPException(404,"This Board Leadership Assistant is not available")
        row=next((x for x in plan.get("leadership_portfolios",[]) if x.get("token")==token),None);project=await owned_project(plan["project_id"]);access=await ensure_execution_access(project);state=execution_access_state(access);history=await db.sp_leadership_assistant_messages.find({"token":token},{"_id":0}).sort("created_at",1).to_list(200)
        suggestions=["Create my first 30-day action plan","Prepare my progress update for the next Board meeting","Create a stakeholder message","Create an execution checklist"]
        return {"member_name":row.get("name",""),"organization_name":project["organization_name"],"areas":row.get("areas",[]),"responsibilities":row.get("responsibilities",[]),
            "suggested_materials":suggestions,"messages":[{"role":x["role"],"text":x["text"]} for x in history],"access_status":state,
            "included_until":access.get("included_until",""),"leader_name":access.get("leader_name",""),"renewal_message":"Your organization's included Executive Assistant access has ended. Please ask your organization leader to renew Board Execution Support." if state=="renewal_required" else ""}

    @router.post("/leadership-assistant/{token}")
    async def use_leadership_assistant(token:str,request:Request):
        body=await request.json();message=str(body.get("message","")).strip()[:8000];material=str(body.get("material_type","")).strip()[:160]
        if not message:raise HTTPException(422,"Enter a request")
        plan=await db.sp_plans.find_one({"leadership_portfolios.token":token,"final_status":"Approved"},{"_id":0})
        if not plan:raise HTTPException(404,"This Board Leadership Assistant is not available")
        row=next((x for x in plan.get("leadership_portfolios",[]) if x.get("token")==token),None);project=await owned_project(plan["project_id"]);access=await ensure_execution_access(project)
        if execution_access_state(access)=="renewal_required":raise HTTPException(402,"Your organization's included Executive Assistant access has ended. Please ask your organization leader to renew Board Execution Support.")
        request_text=f"Create this ready-to-use resource: {material}.\n\n{message}" if material else message;approved_areas=[{"area":area.get("area",""),"agreed_direction":area.get("direction",""),"agreed_ideas":area.get("agreed_ideas",[]),"approved_detailed_plan":area.get("submitted_plan","")} for area in (plan.get("areas") or [])];context={"organization":{"organization_name":project.get("organization_name",""),"mission":project.get("mission",""),"founder_name":project.get("founder_name",""),"founder_title":project.get("founder_title","")},"final_strategic_plan":plan.get("final_display_text",""),"approved_strategic_areas":approved_areas,"delegated_leadership_portfolio":row,"active_delegation":plan.get("active_delegation",{}),"confirmed_board_session_transcript":plan.get("meeting_transcript","") or (plan.get("active_delegation") or {}).get("transcript",""),"follow_up_meeting":plan.get("follow_up_meeting",{})};history=await db.sp_leadership_assistant_messages.find({"token":token},{"_id":0}).sort("created_at",-1).limit(12).to_list(12);history.reverse();api_key=os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY","");model=os.environ.get("EXECUTIVE_ASSISTANT_MODEL","claude-haiku-4-5-20251001");provider=os.environ.get("EXECUTIVE_ASSISTANT_PROVIDER","anthropic");system="You are one nonprofit leader's secure Executive Assistant for executing an approved Strategic Plan. The organization\'s approved plan, Board-agreed strategic areas, confirmed meeting decisions and this person\'s delegated portfolio are authoritative. Preserve the organization\'s own wording, logic and decisions. Help only with responsibilities actually delegated to this person, while using organization-wide approved context when it helps them execute intelligently. Never expose another participant\'s private planning-form reflections merely because they exist. Never invent facts, authority, commitments or results. Do not turn a Board Member into unpaid staff. Do not mention AI."
        chat=LlmChat(api_key=api_key,session_id=f"sp-assistant-{token}-{uuid.uuid4()}",system_message=system).with_model(provider,model);response=await chat.send_message(UserMessage(text=f"AUTHORITATIVE CONTEXT:\n{json.dumps(context,default=str)}\n\nRECENT CONVERSATION:\n{json.dumps(history,default=str)}\n\nREQUEST:\n{request_text}"));answer=response if isinstance(response,str) else getattr(response,"text",str(response));await db.sp_leadership_assistant_messages.insert_many([{"message_id":str(uuid.uuid4()),"token":token,"role":"user","text":request_text,"created_at":now_iso()},{"message_id":str(uuid.uuid4()),"token":token,"role":"assistant","text":answer,"created_at":now_iso()}]);await meter_assistant(access["scope_id"],token,row.get("name",""),request_text,answer,material);return {"answer":answer}

    return router
