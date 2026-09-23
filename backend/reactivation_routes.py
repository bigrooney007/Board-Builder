import asyncio
import html
import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import resend
from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from auth_service import authenticate_admin
from board_fix_master import get_master_record, master_prefill
from member_auth import authenticate_member, require_entitlement
from ai_service import generate_structured
from content_templates import (
    recommitment_form_intro,
    recommitment_outreach_email,
    recommitment_reminder_call_script,
)

logger = logging.getLogger(__name__)

RECOMMIT_ACTIVE = "I am ready to recommit, remain an active Board Member and step up in my role."
RECOMMIT_ADVISORY = "I would like to transition into an Advisory Board role."
RECOMMIT_STEP_DOWN = "I would like to step down from the Board."
RECOMMITMENT_OPTIONS = [RECOMMIT_ACTIVE, RECOMMIT_ADVISORY, RECOMMIT_STEP_DOWN]

LEGACY_RECOMMIT_YES = "Yes, I am ready to recommit and continue serving."
LEGACY_RECOMMIT_NO = "No, I am not able to recommit to serving on the Board."
LEGACY_RECOMMIT_UNSURE = "I am not sure yet. I need more information or would like to discuss my role before deciding."

ADVISORY_OPTION = "Transition to an Advisory Board / Advisory Role"
SUPPORT_OPTION = "Transition to Another Volunteer/Support Role"  # legacy compatibility only


class BoardMemberCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1)
    email: EmailStr
    phone: str = ""
    role: str = ""
    form_variant: str = "full"

class RecommitmentBrandingUpdate(BaseModel):
    organization_name: str = Field(min_length=1)
    logo_data_url: str = ""


class RecommitmentSetupUpdate(BaseModel):
    mission: str = Field(min_length=1, max_length=6000)
    why_recommit: str = Field(min_length=1, max_length=6000)
    board_help_accomplish: str = Field(min_length=1, max_length=6000)
    need_by: str = Field(min_length=1, max_length=20)
    logo_data_url: str = ""


class ImportRequest(BaseModel):
    application_id: str


class SendRequest(BaseModel):
    type: str = "initial"


class CallNotes(BaseModel):
    notes: str = ""


class RecommitmentEmailDraftPayload(BaseModel):
    variant: str = "full"
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=12000)


class RecommitmentAssistantPayload(BaseModel):
    message: str = Field(default="", max_length=6000)
    material_type: str = Field(default="", max_length=240)


class RecommitmentSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")
    full_name: str = Field(min_length=1)
    email: EmailStr
    phone: str = ""
    form_variant: str = "full"
    recommitment: str
    why_joined: str = ""
    expertise: List[str] = []
    expertise_other: str = ""
    participation_barriers: str = ""
    contribution_interests: List[str] = []
    ownership_area: str = ""
    leadership_interest: str = ""
    leadership_area: str = ""
    strengths_resources: str = ""
    monthly_availability: str = ""
    experience_improvement: str = ""
    decision_reason: str = ""
    advisory_openness: str = ""
    decision_support: str = ""
    anything_else: str = ""


def origin_of(request: Request) -> str:
    configured = os.environ.get("PUBLIC_ORIGIN") or request.headers.get("origin")
    if configured:
        return configured
    forwarded = request.headers.get("x-forwarded-host")
    return f"https://{forwarded}" if forwarded else "https://nonprofitboardbuilder.com"


def build_outreach_email(kind: str, member: dict, founder_name: str, founder_title: str, organization: str, form_link: str, mission: str = "", goals: str = "") -> dict:
    first = (member.get("name") or "").split(" ")[0]
    email = recommitment_outreach_email(kind, first, founder_name, founder_title, organization, mission=mission, goals=goals)
    return {**email, "form_link": form_link}


def email_html(body: str, button_label: str, link: str) -> str:
    button = (
        f"<p style='margin:26px 0;'><a href='{html.escape(link)}' style='background:#000;color:#fff;padding:14px 22px;"
        f"text-decoration:none;font-weight:bold;display:inline-block;'>{html.escape(button_label)}</a></p>"
    )
    paragraphs = []
    for block in body.split("\n\n"):
        if block.strip().startswith("[") and block.strip().endswith("]"):
            paragraphs.append(button)
        else:
            paragraphs.append(f"<p style='margin:0 0 16px;'>{html.escape(block).replace(chr(10), '<br/>')}</p>")
    return f"<div style='max-width:640px;margin:auto;font-family:Arial,sans-serif;color:#000;font-size:16px;line-height:1.55;'>{''.join(paragraphs)}</div>"


def build_portfolio_pdf(title: str, member_name: str, issuer: dict, text: str):
    from io import BytesIO
    from fastapi.responses import Response
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer

    buffer = BytesIO()
    organization = issuer.get("organization") or issuer.get("organization_name", "")
    doc = BaseDocTemplate(buffer, pagesize=LETTER, leftMargin=22 * mm, rightMargin=22 * mm, topMargin=22 * mm, bottomMargin=22 * mm, title=title)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")

    def decorate(canvas, _doc):
        canvas.saveState()
        canvas.setLineWidth(1.1)
        canvas.setStrokeColorRGB(0, 0, 0)
        canvas.rect(11 * mm, 11 * mm, LETTER[0] - 22 * mm, LETTER[1] - 22 * mm)
        if canvas.getPageNumber() > 1:
            canvas.setFont("Helvetica", 8)
            canvas.drawString(doc.leftMargin, 13.5 * mm, f"{organization} — {title}")
            canvas.drawRightString(doc.leftMargin + doc.width, 13.5 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=decorate)])
    cover_title = ParagraphStyle("cover", fontName="Helvetica-Bold", fontSize=24, leading=30, alignment=1)
    cover_name = ParagraphStyle("covername", fontName="Helvetica", fontSize=15, leading=20, alignment=1)
    issuer_style = ParagraphStyle("issuer", fontName="Helvetica", fontSize=11, leading=17, alignment=0)
    heading = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=14, leading=18, spaceBefore=16, spaceAfter=6, keepWithNext=1)
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=16, spaceAfter=7)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=12, spaceAfter=4)
    escape = lambda t: str(t).replace("&", "&amp;").replace("<", "&lt;")

    story = [Spacer(1, 150), Paragraph(escape(title).upper(), cover_title), Spacer(1, 14)]
    if member_name:
        story.append(Paragraph(escape(member_name), cover_name))
    story.append(Spacer(1, 170))
    issuer_lines = [f"Issued By: {issuer.get('issued_by', '')}"]
    if issuer.get("issuer_title"):
        issuer_lines.append(f"Title: {issuer['issuer_title']}")
    issuer_lines.extend([f"Organization: {organization}", f"Date: {issuer.get('issue_date', '')}"])
    story.append(Paragraph("<br/>".join(escape(line) for line in issuer_lines), issuer_style))
    story.append(PageBreak())

    lines = text.split("\n")
    started = False
    for line in lines:
        stripped = line.strip()
        if not started:
            if stripped and stripped != stripped.upper() or (stripped and stripped == escape(member_name)):
                started = True
            elif stripped.upper() == title.upper() or stripped == member_name or not stripped:
                continue
            else:
                started = True
        if not stripped:
            story.append(Spacer(1, 4))
        elif stripped.startswith("- "):
            story.append(Paragraph("• " + escape(stripped[2:]), bullet))
        elif stripped == stripped.upper() and len(stripped) < 90 and any(ch.isalpha() for ch in stripped):
            story.append(Paragraph(escape(stripped), heading))
        else:
            story.append(Paragraph(escape(stripped), body))
    doc.build(story)
    filename = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in f"{title}-{member_name}".replace(" ", "-"))
    return Response(content=buffer.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}.pdf"'})


def create_reactivation_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def reactivation_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {"reactivation_self_guided"})
        return member

    async def founder_context(user_id: str) -> dict:
        founder = await db.members.find_one({"user_id": user_id}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1})
        intake = await db.board_reactivation_intakes.find_one({"user_id": user_id}, {"_id": 0}, sort=[("submitted_at", -1)])
        organization = (intake or {}).get("organization_name", "")
        if not organization:
            profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data.organization_name": 1}) or {}
            organization = profile.get("data", {}).get("organization_name", "")
        return {
            "founder_name": f"{founder['first_name']} {founder['last_name']}".strip() if founder else "",
            "founder_email": (founder or {}).get("email", ""),
            "founder_title": (intake or {}).get("founder_title", ""),
            "founder_phone": (intake or {}).get("phone", "") or ((await db.funnel_leads.find_one({"email": (founder or {}).get("email", "")}, {"_id": 0, "phone": 1}, sort=[("created_at", -1)]) or {}).get("phone", "")),
            "organization": organization or "your organization",
            "transition_options": [ADVISORY_OPTION, "Step Down From the Board"],
            "mission": (intake or {}).get("mission", ""),
            "why_recommit": (intake or {}).get("why_recommit", ""),
            "board_help_accomplish": (intake or {}).get("board_help_accomplish", "") or (intake or {}).get("organization_goals", ""),
            "organization_goals": (intake or {}).get("board_help_accomplish", "") or (intake or {}).get("organization_goals", ""),
            "need_by": (intake or {}).get("need_by", ""),
            "logo_data_url": (intake or {}).get("logo_data_url", ""),
        }

    @router.get("/reactivation/branding")
    async def get_recommitment_branding(request: Request):
        member = await reactivation_member(request)
        context = await founder_context(member["user_id"])
        return {"organization_name": context["organization"], "logo_data_url": context.get("logo_data_url", "")}

    @router.put("/reactivation/branding")
    async def save_recommitment_branding(payload: RecommitmentBrandingUpdate, request: Request):
        member = await reactivation_member(request)
        logo = payload.logo_data_url.strip()
        if logo and (not logo.startswith("data:image/") or len(logo) > 2_500_000):
            raise HTTPException(422, "Upload a PNG, JPG or WebP logo smaller than 1.8 MB")
        existing = await db.board_reactivation_intakes.find_one(
            {"user_id": member["user_id"]}, {"_id": 0}, sort=[("submitted_at", -1)]
        )
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            await db.board_reactivation_intakes.update_one(
                {"user_id": member["user_id"], "guided_session_id": existing.get("guided_session_id", "")},
                {"$set": {"organization_name": payload.organization_name.strip(), "logo_data_url": logo, "submitted_at": now}},
            )
        else:
            await db.board_reactivation_intakes.insert_one({
                "user_id": member["user_id"], "organization_name": payload.organization_name.strip(),
                "logo_data_url": logo, "mission": "", "organization_goals": "", "submitted_at": now,
            })
        return {"saved": True, "organization_name": payload.organization_name.strip(), "logo_data_url": logo}

    @router.get("/reactivation/setup")
    async def get_recommitment_setup(request: Request):
        member = await reactivation_member(request)
        context = await founder_context(member["user_id"])
        answers = {
            "mission": context.get("mission", ""),
            "why_recommit": context.get("why_recommit", ""),
            "board_help_accomplish": context.get("board_help_accomplish", ""),
            "need_by": context.get("need_by", ""),
            "logo_data_url": context.get("logo_data_url", ""),
        }
        return {
            "organization_name": context.get("organization", ""),
            "answers": answers,
            "complete": all(str(answers.get(key) or "").strip() for key in ("mission", "why_recommit", "board_help_accomplish", "need_by")),
        }

    @router.put("/reactivation/setup")
    async def save_recommitment_setup(payload: RecommitmentSetupUpdate, request: Request):
        member = await reactivation_member(request)
        logo = payload.logo_data_url.strip()
        if logo and (not logo.startswith("data:image/") or len(logo) > 2_500_000):
            raise HTTPException(status_code=422, detail="Upload a PNG, JPG or WebP logo smaller than 1.8 MB")
        try:
            datetime.strptime(payload.need_by.strip(), "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=422, detail="Choose a valid date for when you need the Board to recommit")
        existing = await db.board_reactivation_intakes.find_one(
            {"user_id": member["user_id"]}, {"_id": 0}, sort=[("submitted_at", -1)]
        ) or {}
        now = datetime.now(timezone.utc).isoformat()
        query = {"user_id": member["user_id"]}
        if existing.get("guided_session_id"):
            query["guided_session_id"] = existing["guided_session_id"]
        updates = {
            "mission": payload.mission.strip(),
            "why_recommit": payload.why_recommit.strip(),
            "board_help_accomplish": payload.board_help_accomplish.strip(),
            "organization_goals": payload.board_help_accomplish.strip(),
            "need_by": payload.need_by.strip(),
            "logo_data_url": logo,
            "submitted_at": now,
        }
        await db.board_reactivation_intakes.update_one(
            query,
            {"$set": updates, "$setOnInsert": {"user_id": member["user_id"], "created_at": now}},
            upsert=True,
        )
        return {"saved": True, "answers": updates}

    async def owned_board_member(user_id: str, member_record_id: str) -> dict:
        record = await db.reactivation_board_members.find_one({"user_id": user_id, "member_record_id": member_record_id}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Board Member not found")
        return record

    def public_record(record: dict) -> dict:
        return {key: record.get(key, "") for key in [
            "member_record_id", "name", "email", "phone", "role", "status", "source", "form_variant",
            "last_sent_at", "last_reminder_at", "submitted_at", "call_notes", "conversation_direction",
            "conversation_outcome", "conversation_conclusion", "confirmed_role",
        ]}

    @router.get("/reactivation/roster")
    async def roster(request: Request):
        member = await reactivation_member(request)
        user_id = member["user_id"]
        records = await db.reactivation_board_members.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
        known_emails = {record["email"] for record in records}
        joined = await db.opportunity_applications.find(
            {"owner_user_id": user_id, "$or": [{"final_outcome": "Joined Board"}, {"status": "Selected"}]},
            {"_id": 0, "application_id": 1, "profile_snapshot": 1, "applicant_email": 1},
        ).to_list(50)
        existing_people = [
            {"application_id": app["application_id"], "name": app.get("profile_snapshot", {}).get("full_name", ""), "email": app.get("applicant_email", "")}
            for app in joined if (app.get("applicant_email") or "").lower() not in known_emails
        ]
        completed = sum(1 for record in records if record["status"] == "COMPLETED")
        return {
            "members": [public_record(record) for record in records],
            "existing_people": existing_people,
            "progress": {"total": len(records), "completed": completed, "waiting": len(records) - completed},
        }

    @router.post("/reactivation/board-members", status_code=201)
    async def add_board_member(payload: BoardMemberCreate, request: Request):
        member = await reactivation_member(request)
        email = str(payload.email).lower()
        existing = await db.reactivation_board_members.find_one({"user_id": member["user_id"], "email": email}, {"_id": 0})
        if existing:
            return {"status": "exists", "member": public_record(existing)}
        record = {
            "member_record_id": str(uuid.uuid4()), "user_id": member["user_id"],
            "name": payload.name, "email": email, "phone": payload.phone, "role": payload.role,
            "source": "manual", "status": "NOT SENT", "form_token": secrets.token_urlsafe(32),
            "call_notes": "", "form_variant": "active_advisory" if payload.form_variant == "active_advisory" else "full",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.reactivation_board_members.insert_one({**record})
        return {"status": "created", "member": public_record(record)}

    @router.post("/reactivation/board-members/import", status_code=201)
    async def import_board_member(payload: ImportRequest, request: Request):
        member = await reactivation_member(request)
        app = await db.opportunity_applications.find_one(
            {"owner_user_id": member["user_id"], "application_id": payload.application_id},
            {"_id": 0, "profile_snapshot": 1, "applicant_email": 1, "answers": 1},
        )
        if not app:
            raise HTTPException(status_code=404, detail="Board Member not found")
        snapshot = app.get("profile_snapshot", {})
        email = (app.get("applicant_email") or "").lower()
        existing = await db.reactivation_board_members.find_one({"user_id": member["user_id"], "email": email}, {"_id": 0})
        if existing:
            return {"status": "exists", "member": public_record(existing)}
        record = {
            "member_record_id": str(uuid.uuid4()), "user_id": member["user_id"],
            "name": snapshot.get("full_name", ""), "email": email,
            "phone": snapshot.get("phone", ""), "role": "Board Member",
            "source": "recruitment", "application_id": payload.application_id,
            "status": "NOT SENT", "form_token": secrets.token_urlsafe(32),
            "call_notes": "", "form_variant": "full", "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.reactivation_board_members.insert_one({**record})
        return {"status": "created", "member": public_record(record)}

    @router.get("/reactivation/board-members/{member_record_id}/email-preview")
    async def email_preview(member_record_id: str, request: Request, type: str = "initial"):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        context = await founder_context(member["user_id"])
        variant = "active_advisory" if record.get("form_variant") == "active_advisory" else "full"
        form_link = f"{origin_of(request)}/board-recommitment/{record['form_token']}?variant={variant}"
        email = build_outreach_email(type, record, context["founder_name"], context["founder_title"], context["organization"], form_link, context.get("mission",""), context.get("organization_goals",""))
        return {"to_name": record["name"], "to_email": record["email"], **email}

    @router.post("/reactivation/board-members/{member_record_id}/send")
    async def send_form(member_record_id: str, payload: SendRequest, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        context = await founder_context(member["user_id"])
        variant = "active_advisory" if record.get("form_variant") == "active_advisory" else "full"
        form_link = f"{origin_of(request)}/board-recommitment/{record['form_token']}?variant={variant}"
        email = build_outreach_email(payload.type, record, context["founder_name"], context["founder_title"], context["organization"], form_link, context.get("mission",""), context.get("organization_goals",""))
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        message = {
            "from": os.environ["NONPROFIT_SENDER"], "to": [record["email"]],
            "subject": email["subject"],
            "html": email_html(email["body"], email["button_label"], form_link),
        }
        if context["founder_email"]:
            message["reply_to"] = [context["founder_email"]]
        try:
            await resend.Emails.send_async(message)
        except Exception as exc:
            logger.exception("Recommitment form send failed for %s", member_record_id)
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc
        now = datetime.now(timezone.utc).isoformat()
        updates = {"last_reminder_at": now} if payload.type == "reminder" else {"last_sent_at": now}
        if record["status"] == "NOT SENT":
            updates["status"] = "SENT"
        await db.reactivation_board_members.update_one({"member_record_id": member_record_id}, {"$set": updates})
        return {"status": "sent", "sent_at": now}

    @router.get("/reactivation/board-members/{member_record_id}/call-script")
    async def call_script(member_record_id: str, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        context = await founder_context(member["user_id"])
        first = (record.get("name") or "").split(" ")[0]
        founder_first = context["founder_name"].split(" ")[0] if context["founder_name"] else "me"
        script = recommitment_reminder_call_script(first, founder_first, context["organization"])
        return {"script": script, "call_notes": record.get("call_notes", ""), "form_status": record["status"]}

    @router.put("/reactivation/board-members/{member_record_id}/call-notes")
    async def save_call_notes(member_record_id: str, payload: CallNotes, request: Request):
        member = await reactivation_member(request)
        await owned_board_member(member["user_id"], member_record_id)
        await db.reactivation_board_members.update_one(
            {"member_record_id": member_record_id}, {"$set": {"call_notes": payload.notes}}
        )
        return {"status": "saved"}

    @router.get("/reactivation/board-members/{member_record_id}/response")
    async def view_response(member_record_id: str, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        if record["status"] != "COMPLETED" or not record.get("response"):
            raise HTTPException(status_code=404, detail="This Board Member has not completed their form yet")
        return {"member": public_record(record), "response": record["response"], "submitted_at": record.get("submitted_at", "")}

    @router.get("/reactivation/board-members/{member_record_id}/response/pdf")
    async def download_response_pdf(member_record_id: str, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        if record["status"] != "COMPLETED" or not record.get("response"):
            raise HTTPException(status_code=404, detail="This Board Member has not completed their form yet")
        context = await founder_context(member["user_id"])
        response = record.get("response") or {}
        labels = {
            "recommitment": "Recommitment Choice", "why_joined": "Why They Want To Continue",
            "expertise": "Expertise", "participation_barriers": "Participation Barriers",
            "contribution_interests": "Contribution Interests", "ownership_area": "Responsibility They Could Own",
            "leadership_interest": "Leadership Interest", "leadership_area": "Leadership Area",
            "strengths_resources": "Strengths / Relationships / Resources", "monthly_availability": "Monthly Availability",
            "experience_improvement": "Support They Need From The Organization", "decision_reason": "Reason For Their Chosen Path",
            "anything_else": "Anything Else",
        }
        lines = ["BOARD RECOMMITMENT RESPONSE", "", f"Board Member: {record.get('name','')}", f"Email: {record.get('email','')}", ""]
        for key, label in labels.items():
            value = response.get(key)
            if not value:
                continue
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            lines.extend([label.upper(), str(value), ""])
        issuer = {
            "issued_by": context.get("founder_name", ""), "issuer_title": context.get("founder_title", ""),
            "organization": context.get("organization", ""), "issue_date": (record.get("submitted_at") or datetime.now(timezone.utc).isoformat())[:10],
        }
        return build_portfolio_pdf("Board Recommitment Response", record.get("name",""), issuer, "\n".join(lines))

    # ---------------- STEP 3: DIFFICULT CONVERSATIONS ----------------

    BASE_OUTCOMES = ["Continuing as an Active Board Member"]

    def allowed_outcomes() -> list:
        return list(BASE_OUTCOMES) + [
            "Transitioning to an Advisory Role",
            "Stepping Down From the Board",
        ]

    async def user_intake(user_id: str) -> dict:
        intake = await db.board_reactivation_intakes.find_one({"user_id": user_id}, {"_id": 0}, sort=[("submitted_at", -1)]) or {}
        audit = await db.founder_board_audits.find_one({"user_id": user_id}, {"_id": 0}) or {}
        intake["founder_desired_outcomes"] = audit.get("desired_outcomes", "")
        intake["founder_board_support_needed"] = audit.get("board_support_needed", "")
        master = await get_master_record(db, user_id=user_id)
        if master:
            for field, value in master_prefill("reactivation", master.get("data", {})).items():
                if not intake.get(field):
                    intake[field] = value
        return intake

    def script_display(structured: dict) -> str:
        lines = ["DIFFICULT CONVERSATION SCRIPT", "",
                 f"Board Member: {structured.get('member', '')}"]
        if structured.get("board_role"):
            lines.append(f"Current Board Role: {structured['board_role']}")
        lines.extend([f"Recommitment Response: {structured.get('recommitment_response', '')}", "",
                      f"BEFORE YOU SPEAK WITH {structured.get('member', '').split(' ')[0].upper()}", "",
                      "What They Told You", structured.get("what_they_told_you", ""), "",
                      "What You Need to Understand"])
        lines.extend([f"- {item}" for item in structured.get("what_you_need_to_understand", [])])
        lines.extend(["", "What Not to Lose Sight Of", structured.get("what_not_to_lose_sight_of", ""), "",
                      "1. OPEN THE CONVERSATION", structured.get("open_the_conversation", ""), "",
                      "2. UNDERSTAND THEIR EXPERIENCE"])
        for entry in structured.get("understand_their_experience", []):
            lines.extend(["", f"QUESTION: {entry.get('question', '')}",
                          f"WHY THIS MATTERS: {entry.get('why_this_matters', '')}",
                          f"LISTEN FOR: {entry.get('listen_for', '')}"])
            if entry.get("optional_follow_up"):
                lines.append(f"OPTIONAL FOLLOW-UP: {entry['optional_follow_up']}")
        lines.extend(["", "3. EXPLAIN WHAT THE ORGANIZATION NEEDS NOW"])
        lines.extend([f"- {item}" for item in structured.get("explain_what_the_organization_needs_now", [])])
        first = structured.get("member", "").split(" ")[0]
        lines.extend(["", f"4. DISCUSS WHERE {first.upper()} CAN CONTRIBUTE"])
        for entry in structured.get("discuss_where_they_can_contribute", []):
            lines.extend(["", f"QUESTION: {entry.get('question', '')}",
                          f"WHY THIS MATTERS: {entry.get('why_this_matters', '')}"])
        lines.extend(["", "5. MOVE FROM INTEREST TO RESPONSIBILITY"])
        lines.extend([f"- {item}" for item in structured.get("move_from_interest_to_responsibility", [])])
        lines.extend(["", "6. CLARIFY THE WAY FORWARD", structured.get("clarify_the_way_forward", ""), "",
                      "7. CLOSE WITH CLEAR NEXT STEPS", structured.get("close_with_clear_next_steps", "")])
        return "\n".join(lines)

    async def save_reactivation_material(user_id: str, material_type: str, title: str, member_record_id: str, structured: dict, display_text: str) -> dict:
        query = {"user_id": user_id, "type": material_type, "application_id": member_record_id}
        existing = await db.generated_materials.find_one(query, {"_id": 0, "versions.version": 1})
        now = datetime.now(timezone.utc).isoformat()
        version_number = (max((v["version"] for v in existing["versions"]), default=0) + 1) if existing else 1
        version = {"version": version_number, "structured": structured, "display_text": display_text, "source": "generated", "created_at": now}
        if existing:
            await db.generated_materials.update_one(query, {"$push": {"versions": version}, "$set": {"current_version": version_number, "status": "Draft", "updated_at": now}})
        else:
            await db.generated_materials.insert_one({
                "material_id": str(uuid.uuid4()), "user_id": user_id, "type": material_type,
                "application_id": member_record_id, "module": 3, "title": title,
                "versions": [version], "current_version": version_number, "status": "Draft",
                "created_at": now, "updated_at": now,
            })
        material = await db.generated_materials.find_one(query, {"_id": 0, "versions.structured": 0})
        return material

    def current_display(material: dict) -> str:
        current = next((v for v in material.get("versions", []) if v["version"] == material.get("current_version")), None)
        return (current or {}).get("display_text", "")

    def material_summary(material: Optional[dict]) -> Optional[dict]:
        if not material:
            return None
        return {"material_id": material["material_id"], "status": material["status"], "updated_at": material.get("updated_at", "")}

    @router.get("/reactivation/step3")
    async def step3(request: Request):
        member = await reactivation_member(request)
        user_id = member["user_id"]
        intake = await user_intake(user_id)
        records = await db.reactivation_board_members.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
        materials = await db.generated_materials.find(
            {"user_id": user_id, "type": "reactivation_conversation_script"},
            {"_id": 0, "material_id": 1, "application_id": 1, "status": 1, "updated_at": 1},
        ).to_list(300)
        material_by_member = {m["application_id"]: m for m in materials}
        analyses = await db.generated_materials.find(
            {"user_id": user_id, "type": "reactivation_response_analysis"},
            {"_id": 0, "material_id": 1, "application_id": 1, "status": 1, "updated_at": 1},
        ).to_list(300)
        analysis_by_member = {m["application_id"]: m for m in analyses}
        rows = []
        completed_conversations = follow_up = waiting = 0
        for record in records:
            recommitment = (record.get("response") or {}).get("recommitment", "")
            conclusion = record.get("conversation_conclusion", "")
            outcome = record.get("conversation_outcome", "")
            done = bool(conclusion.strip()) and bool(outcome)
            if record["status"] != "COMPLETED":
                waiting += 1
            elif done:
                completed_conversations += 1
                if outcome == "Follow-Up Conversation Needed":
                    follow_up += 1
            rows.append({**public_record(record), "recommitment": recommitment,
                         "conversation_conclusion": conclusion, "conversation_outcome": outcome,
                         "conversation_direction": record.get("conversation_direction", ""),
                         "conversation_complete": done,
                         "analysis": material_summary(analysis_by_member.get(record["member_record_id"])),
                         "script": material_summary(material_by_member.get(record["member_record_id"]))})
        return {
            "members": rows,
            "outcome_options": allowed_outcomes(),
            "directions": CONVERSATION_DIRECTIONS,
            "progress": {"total": len(records), "conversations_completed": completed_conversations,
                         "follow_up_needed": follow_up, "waiting_for_form": waiting},
        }

    @router.post("/reactivation/board-members/{member_record_id}/conversation-script")
    async def generate_conversation_script(member_record_id: str, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        if record["status"] != "COMPLETED" or not record.get("response"):
            raise HTTPException(status_code=409, detail="This Board Member has not completed their Recommitment & Profile Form yet. Their response is needed before a person-specific conversation script can be generated.")
        intake = await user_intake(member["user_id"])
        permitted = [
            "Transitioning to an Advisory Role",
            "Transitioning to Another Support Role",
            "Stepping Down From the Board",
        ]
        org_context = {key: intake.get(key, "") for key in [
            "organization_name", "mission", "why_recommit", "board_help_accomplish", "need_by", "direction_12_24", "active_board_vision",
            "present_board", "active_board", "disengaged_board", "current_skills", "missing_skills",
            "roles_defined", "roles_description", "expected_contribution", "actually_happening",
            "strategic_plan", "board_participated_planning", "planning_involvement",
            "disengage_reason", "disengage_when", "disengagement_signs", "reactivation_attempts", "attempts_outcome",
            "meeting_frequency", "typical_meeting", "clear_responsibilities_after_meetings",
            "founder_desired_outcomes", "founder_board_support_needed",
        ]}
        context = "ORGANIZATION CONTEXT AND BOARD REACTIVATION INTAKE (provided by the founder):\n" + json.dumps(org_context, indent=1, default=str)
        context += "\n\nORGANIZATION-PERMITTED TRANSITION OPTIONS (the ONLY transitions that may be mentioned): "
        context += ", ".join(permitted) if permitted else "The organization has not decided on transition options yet — do not present specific transition structures; the founder will decide the appropriate path in the conversation."
        context += ("\n\nTHIS BOARD MEMBER (their actual Board Member Profile & Recommitment Form response):\n"
                    + json.dumps({"name": record["name"], "current_board_role": record.get("role", ""), **record["response"]}, indent=1, default=str))
        analysis_material = await db.generated_materials.find_one(
            {"user_id": member["user_id"], "type": "reactivation_response_analysis", "application_id": member_record_id,
             "status": {"$nin": ["Generating", "Failed"]}}, {"_id": 0})
        if not analysis_material:
            raise HTTPException(status_code=409, detail="Generate Understanding Their Response for this Board Member first — the conversation script is built from that understanding.")
        context += "\n\nUNDERSTANDING THEIR RESPONSE (preparation for the conversation — NOT the final agreement):\n" + current_display(analysis_material)[:8000]
        if intake.get("bylaws_text"):
            context += "\n\nORGANIZATION BYLAWS EXTRACT (verified Board/governance context ONLY — never invent procedures or requirements):\n" + intake["bylaws_text"][:10000]
        if record.get("call_notes"):
            context += "\n\nFOUNDER'S PREVIOUS NOTES ABOUT THIS BOARD MEMBER:\n" + record["call_notes"]
        direction = record.get("conversation_direction", "")
        if not direction:
            choice = (record.get("response") or {}).get("recommitment", "")
            direction = {
                RECOMMIT_ACTIVE: "Remain and Step Up",
                RECOMMIT_ADVISORY: "Move to Advisory Board",
                RECOMMIT_STEP_DOWN: "Step Down",
                LEGACY_RECOMMIT_YES: "Remain and Step Up",
                LEGACY_RECOMMIT_NO: "Step Down",
            }.get(choice, "")
            if direction:
                await db.reactivation_board_members.update_one(
                    {"member_record_id": member_record_id},
                    {"$set": {"conversation_direction": direction, "direction_source": "form_response"}},
                )
        if direction:
            context += (f"\n\nCONVERSATION DIRECTION: {direction}\n"
                        + DIRECTION_GUIDANCE.get(direction, "")
                        + "\nThis direction comes from the Board Member's submitted choice unless the founder deliberately changes it. "
                          "Write the entire script specifically for this direction and this person — never a generic script.")
        query = {"user_id": member["user_id"], "type": "reactivation_conversation_script", "application_id": member_record_id}
        existing = await db.generated_materials.find_one(query, {"_id": 0, "material_id": 1, "status": 1})
        if existing and existing.get("status") == "Generating":
            return {"material_id": existing["material_id"], "status": "Generating"}
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            material_id = existing["material_id"]
            await db.generated_materials.update_one(query, {"$set": {"status": "Generating", "updated_at": now}})
        else:
            material_id = str(uuid.uuid4())
            await db.generated_materials.insert_one({
                "material_id": material_id, "user_id": member["user_id"], "type": "reactivation_conversation_script",
                "application_id": member_record_id, "module": 3, "title": "Difficult Conversation Script",
                "versions": [], "current_version": 0, "status": "Generating",
                "created_at": now, "updated_at": now,
            })

        async def run_generation():
            try:
                structured = await generate_structured("reactivation_conversation_script", context)
                structured["member"] = record["name"]
                structured["recommitment_response"] = record["response"].get("recommitment", "")
                await save_reactivation_material(member["user_id"], "reactivation_conversation_script", "Difficult Conversation Script", member_record_id, structured, script_display(structured))
            except Exception as exc:
                logging.getLogger(__name__).error("Conversation script generation failed for %s: %s", member_record_id, exc)
                await db.generated_materials.update_one(query, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_generation())
        return {"material_id": material_id, "status": "Generating"}

    async def owned_reactivation_material(user_id: str, material_id: str) -> dict:
        material = await db.generated_materials.find_one(
            {"material_id": material_id, "user_id": user_id, "type": {"$regex": "^reactivation_"}}, {"_id": 0})
        if not material:
            raise HTTPException(status_code=404, detail="Document not found")
        return material

    @router.get("/reactivation/materials/{material_id}")
    async def get_reactivation_material(material_id: str, request: Request):
        member = await reactivation_member(request)
        material = await owned_reactivation_material(member["user_id"], material_id)
        return {"material_id": material["material_id"], "type": material["type"], "title": material["title"],
                "application_id": material["application_id"], "status": material["status"],
                "updated_at": material.get("updated_at", ""), "display_text": current_display(material)}

    class MaterialEditPayload(BaseModel):
        display_text: str = Field(min_length=1)

    @router.put("/reactivation/materials/{material_id}")
    async def edit_reactivation_material(material_id: str, payload: MaterialEditPayload, request: Request):
        member = await reactivation_member(request)
        material = await owned_reactivation_material(member["user_id"], material_id)
        now = datetime.now(timezone.utc).isoformat()
        version_number = max((v["version"] for v in material["versions"]), default=0) + 1
        version = {"version": version_number, "structured": {}, "display_text": payload.display_text, "source": "edited", "created_at": now}
        await db.generated_materials.update_one(
            {"material_id": material_id},
            {"$push": {"versions": version}, "$set": {"current_version": version_number, "status": "Draft", "updated_at": now}})
        return {"status": "Draft", "version": version_number}

    @router.post("/reactivation/materials/{material_id}/approve")
    async def approve_reactivation_material(material_id: str, request: Request):
        member = await reactivation_member(request)
        await owned_reactivation_material(member["user_id"], material_id)
        now = datetime.now(timezone.utc).isoformat()
        await db.generated_materials.update_one({"material_id": material_id}, {"$set": {"status": "Approved", "approved_at": now, "updated_at": now}})
        return {"status": "Approved"}

    @router.get("/reactivation/materials/{material_id}/pdf")
    async def reactivation_material_pdf(material_id: str, request: Request):
        from fastapi.responses import Response
        from document_renderer import render_document_pdf
        member = await reactivation_member(request)
        material = await owned_reactivation_material(member["user_id"], material_id)
        text = current_display(material)
        intake = await user_intake(member["user_id"])
        created_by = {
            "name": f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
            "title": intake.get("founder_title", "") or "Founder",
            "organization": intake.get("organization_name", ""),
        }
        profile = await db.recruitment_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "branding": 1})
        branding = (profile or {}).get("branding", {})
        prepared_for = ""
        if material.get("application_id"):
            record = await db.reactivation_board_members.find_one({"member_record_id": material["application_id"]}, {"_id": 0, "name": 1})
            prepared_for = (record or {}).get("name", "")
        title = material["title"]
        pdf = render_document_pdf(title=title, org_name=created_by["organization"], body_text=text,
                                  branding=branding, created_by=created_by, prepared_for=prepared_for)
        filename = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in f"{title}".replace(" ", "-"))
        return Response(content=pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'})

    class ConclusionPayload(BaseModel):
        conclusion: str = ""

    @router.put("/reactivation/board-members/{member_record_id}/conclusion")
    async def save_conclusion(member_record_id: str, payload: ConclusionPayload, request: Request):
        member = await reactivation_member(request)
        await owned_board_member(member["user_id"], member_record_id)
        now = datetime.now(timezone.utc).isoformat()
        await db.reactivation_board_members.update_one(
            {"member_record_id": member_record_id},
            {"$set": {"conversation_conclusion": payload.conclusion, "conclusion_saved_at": now}})
        return {"status": "saved"}

    class OutcomePayload(BaseModel):
        outcome: str

    @router.put("/reactivation/board-members/{member_record_id}/outcome")
    async def save_outcome(member_record_id: str, payload: OutcomePayload, request: Request):
        member = await reactivation_member(request)
        await owned_board_member(member["user_id"], member_record_id)
        if payload.outcome not in allowed_outcomes():
            raise HTTPException(status_code=422, detail="This outcome is not available for your organization")
        now = datetime.now(timezone.utc).isoformat()
        await db.reactivation_board_members.update_one(
            {"member_record_id": member_record_id},
            {"$set": {"conversation_outcome": payload.outcome, "outcome_saved_at": now}})
        return {"status": "saved"}

    # ---------------- STEP 5: MY BOARD + PORTFOLIOS ----------------

    PORTFOLIO_TYPE = "reactivation_board_member_portfolio"
    OUTCOME_ACTIVE = "Continuing as an Active Board Member"
    OUTCOME_ADVISORY = "Transitioning to an Advisory Role"
    OUTCOME_SUPPORT = "Transitioning to Another Support Role"
    OUTCOME_STEP_DOWN = "Stepping Down From the Board"

    def portfolio_title_for(outcome: str) -> str:
        if outcome == OUTCOME_ADVISORY:
            return "Advisory Board Member Portfolio"
        if outcome == OUTCOME_SUPPORT:
            return "Support Role Portfolio"
        return "Board Member Portfolio"

    def portfolio_display(structured: dict) -> str:
        lines = [structured.get("portfolio_type", "Board Member Portfolio").upper(), "", structured.get("member", ""), "",
                 "YOUR ROLE ON THE BOARD", structured.get("your_role_on_the_board", ""), "",
                 "WHY YOUR ROLE MATTERS", structured.get("why_your_role_matters", ""), "",
                 "WHAT YOU WILL HELP US ACCOMPLISH"]
        lines.extend(f"- {item}" for item in structured.get("what_you_will_help_us_accomplish", []))
        lines.extend(["", "YOUR AREAS OF RESPONSIBILITY"])
        lines.extend(f"- {item}" for item in structured.get("your_areas_of_responsibility", []))
        lines.extend(["", "HOW YOUR EXPERIENCE CAN HELP", structured.get("how_your_experience_can_help", "")])
        if structured.get("relationships_and_resources"):
            lines.extend(["", "RELATIONSHIPS AND RESOURCES YOU CAN HELP OPEN", structured["relationships_and_resources"]])
        if structured.get("your_role_in_fundraising"):
            lines.extend(["", "YOUR ROLE IN FUNDRAISING", structured["your_role_in_fundraising"]])
        lines.extend(["", "HOW WE WILL WORK TOGETHER", structured.get("how_we_will_work_together", ""), "",
                      "YOUR IMMEDIATE PRIORITIES"])
        lines.extend(f"- {item}" for item in structured.get("your_immediate_priorities", []))
        lines.extend(["", "YOUR FIRST 90 DAYS"])
        lines.extend(f"- {item}" for item in structured.get("your_first_90_days", []))
        lines.extend(["", "MOVING FORWARD TOGETHER", structured.get("moving_forward_together", "")])
        return "\n".join(lines)

    def portfolio_summary(material: Optional[dict]) -> Optional[dict]:
        if not material:
            return None
        status = material["status"]
        if status == "Approved" and material.get("sent_at") and material.get("sent_version") == material.get("current_version"):
            status = "SENT"
        return {"material_id": material["material_id"], "status": status,
                "share_token": material.get("share_token", ""), "sent_at": material.get("sent_at", ""), "updated_at": material.get("updated_at", "")}

    @router.get("/reactivation/my-board")
    async def my_board(request: Request):
        member = await reactivation_member(request)
        user_id = member["user_id"]
        intake = await user_intake(user_id)
        records = await db.reactivation_board_members.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
        materials = await db.generated_materials.find(
            {"user_id": user_id, "type": PORTFOLIO_TYPE},
            {"_id": 0, "material_id": 1, "application_id": 1, "status": 1, "share_token": 1, "sent_at": 1, "updated_at": 1, "sent_version": 1, "current_version": 1}).to_list(300)
        by_member = {m["application_id"]: m for m in materials}
        email_materials = await db.generated_materials.find(
            {"user_id": user_id, "type": {"$in": ["reactivation_stepped_down_followup", "reactivation_advisory_confirmation", "reactivation_recommitment_confirmation"]}},
            {"_id": 0, "material_id": 1, "application_id": 1, "type": 1, "status": 1, "updated_at": 1}).to_list(300)
        emails_by_member = {m["application_id"]: m for m in email_materials}
        analyses = await db.generated_materials.find(
            {"user_id": user_id, "type": "reactivation_response_analysis", "status": {"$nin": ["Generating", "Failed"]}},
            {"_id": 0, "application_id": 1}).to_list(300)
        analyzed_ids = {m["application_id"] for m in analyses}
        groups = {"active": [], "advisory": [], "support": [], "stepping_down": [], "follow_up": [], "waiting": []}
        for record in records:
            outcome = record.get("conversation_outcome", "")
            response = record.get("response") or {}
            row = {**public_record(record), "conversation_outcome": outcome,
                   "conversation_conclusion": record.get("conversation_conclusion", ""),
                   "conversation_direction": record.get("conversation_direction", ""),
                   "analyzed": record["member_record_id"] in analyzed_ids,
                   "professional_role": response.get("current_position", ""), "employer": response.get("employer", ""),
                   "expertise": response.get("expertise", []), "contribution_interests": response.get("contribution_interests", []),
                   "outcome_email": material_summary(emails_by_member.get(record["member_record_id"])),
                   "portfolio": portfolio_summary(by_member.get(record["member_record_id"]))}
            if outcome == OUTCOME_ACTIVE:
                groups["active"].append(row)
            elif outcome == OUTCOME_ADVISORY:
                groups["advisory"].append(row)
            elif outcome == OUTCOME_SUPPORT:
                groups["support"].append(row)
            elif outcome == OUTCOME_STEP_DOWN:
                groups["stepping_down"].append(row)
            elif record["status"] != "COMPLETED":
                groups["waiting"].append(row)
            else:
                groups["follow_up"].append(row)
        approved = sum(1 for m in materials if m["status"] == "Approved" or m.get("sent_at"))
        return {"groups": groups, "organization": intake.get("organization_name", ""),
                "summary": {"reviewed": len(records), "active": len(groups["active"]), "advisory": len(groups["advisory"]),
                            "support": len(groups["support"]), "stepping_down": len(groups["stepping_down"]),
                            "follow_up": len(groups["follow_up"]), "waiting": len(groups["waiting"]),
                            "portfolios_approved": approved}}

    class ConfirmedRolePayload(BaseModel):
        role: str = Field(min_length=1, max_length=500)

    @router.put("/reactivation/board-members/{member_record_id}/confirmed-role")
    async def save_confirmed_role(member_record_id: str, payload: ConfirmedRolePayload, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        if record.get("conversation_outcome") not in {OUTCOME_ACTIVE, OUTCOME_ADVISORY}:
            raise HTTPException(status_code=409, detail="Confirm the final active or Advisory Board outcome before setting this role")
        await db.reactivation_board_members.update_one(
            {"member_record_id": member_record_id},
            {"$set": {"confirmed_role": payload.role.strip(), "confirmed_role_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"status": "saved", "confirmed_role": payload.role.strip()}

    def eligible_for_portfolio(record: dict) -> str:
        outcome = record.get("conversation_outcome", "")
        if outcome in {OUTCOME_ACTIVE, OUTCOME_ADVISORY}:
            if not str(record.get("confirmed_role") or "").strip():
                raise HTTPException(status_code=409, detail="Confirm or edit this person's final Board role before generating their Portfolio.")
            return outcome
        if outcome == OUTCOME_SUPPORT:
            if not (record.get("conversation_conclusion") or "").strip():
                raise HTTPException(status_code=409, detail="Record the Conversation Conclusion describing the agreed support role before creating this Portfolio.")
            return outcome
        if outcome == OUTCOME_STEP_DOWN:
            raise HTTPException(status_code=409, detail="This person is not continuing as an active Board Member, so an active Board Member Portfolio is not required.")
        raise HTTPException(status_code=409, detail="Complete the conversation and record the final outcome before creating this person's Portfolio.")

    @router.post("/reactivation/board-members/{member_record_id}/portfolio")
    async def generate_portfolio(member_record_id: str, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        outcome = eligible_for_portfolio(record)
        intake = await user_intake(member["user_id"])
        context_org = {key: intake.get(key, "") for key in [
            "organization_name", "mission", "direction_12_24", "board_help_accomplish", "active_board_vision",
            "current_skills", "missing_skills", "expected_contribution", "meeting_frequency"]}
        founder = await founder_context(member["user_id"])
        title = portfolio_title_for(outcome)
        context = f"PORTFOLIO TYPE: {title}\n\nORGANIZATION:\n" + json.dumps({**context_org, "founder_name": founder["founder_name"]}, indent=1, default=str)
        context += "\n\nTHIS BOARD MEMBER (their Recommitment/Profile response):\n" + json.dumps(
            {"name": record["name"], "previous_board_role": record.get("role", ""),
             "founder_confirmed_role": record.get("confirmed_role", ""), **(record.get("response") or {})}, indent=1, default=str)
        context += f"\n\nFOUNDER-CONFIRMED ROLE (authoritative for this Portfolio): {record.get('confirmed_role','')}"
        context += f"\n\nFOUNDER-SELECTED CONVERSATION OUTCOME: {outcome}"
        context += "\n\nFOUNDER'S CONVERSATION CONCLUSION (what was ACTUALLY agreed — highest authority):\n" + (record.get("conversation_conclusion") or "No conclusion recorded yet.")
        try:
            structured = await generate_structured("board_member_portfolio", context)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Generation failed: {str(exc)[:300]}. Your information is preserved — you can try again.") from exc
        structured["member"] = record["name"]
        structured["portfolio_type"] = title
        material = await save_reactivation_material(member["user_id"], PORTFOLIO_TYPE, title, member_record_id, structured, portfolio_display(structured))
        full = await db.generated_materials.find_one({"material_id": material["material_id"]}, {"_id": 0})
        return {**material, "display_text": current_display(full)}

    @router.post("/reactivation/materials/{material_id}/approve-portfolio")
    async def approve_portfolio(material_id: str, request: Request):
        member = await reactivation_member(request)
        material = await owned_reactivation_material(member["user_id"], material_id)
        now = datetime.now(timezone.utc).isoformat()
        updates = {"status": "Approved", "approved_at": now, "updated_at": now}
        if not material.get("share_token"):
            updates["share_token"] = secrets.token_urlsafe(24)
        await db.generated_materials.update_one({"material_id": material_id}, {"$set": updates})
        refreshed = await db.generated_materials.find_one({"material_id": material_id}, {"_id": 0, "share_token": 1})
        return {"status": "Approved", "share_token": refreshed["share_token"]}

    async def portfolio_email_content(user_id: str, record: dict, material: dict, origin: str) -> dict:
        context = await founder_context(user_id)
        first = (record.get("name") or "").split(" ")[0]
        title = material["title"]
        advisory = "Advisory" in title
        organization = context["organization"]
        link = f"{origin}/portfolio/{material['share_token']}"
        signature = context["founder_name"] + (f"\n{context['founder_title']}" if context["founder_title"] else "") + f"\n{organization}"
        if advisory:
            subject = f"Your Advisory Board Member Portfolio | {organization}"
            body = (
                f"Dear {first},\n\n"
                f"Thank you for taking the time to complete the Board Recommitment process and for the conversation about the best way for you to continue supporting {organization}.\n\n"
                "Based on what we discussed, I have put together your Advisory Board Member Portfolio.\n\n"
                f"It outlines the advisory relationship we discussed, where your experience can create value, and how you can continue helping move {organization} forward.\n\n"
                "Please review your Portfolio using the link below:\n\n"
                "[VIEW MY ADVISORY BOARD MEMBER PORTFOLIO]\n\n"
                "I appreciate your continued support of the organization, and I look forward to staying connected as we move forward.\n\n"
                f"{signature}")
            button = "VIEW MY ADVISORY BOARD MEMBER PORTFOLIO"
        else:
            subject = f"Your Board Member Portfolio | {organization}"
            body = (
                f"Dear {first},\n\n"
                "Thank you for taking the time to complete the Board Recommitment process and for the conversation about how you would like to contribute moving forward.\n\n"
                "Based on what we discussed, I have put together your Board Member Portfolio.\n\n"
                f"It outlines where your experience can create value, the areas of responsibility we discussed, and how you can help move {organization} forward.\n\n"
                "Please review your Portfolio using the link below:\n\n"
                "[VIEW MY BOARD MEMBER PORTFOLIO]\n\n"
                "I appreciate your willingness to continue contributing to the organization, and I look forward to working together as we move forward.\n\n"
                f"{signature}")
            button = "VIEW MY BOARD MEMBER PORTFOLIO"
        return {"to_name": record["name"], "to_email": record["email"], "subject": subject, "body": body,
                "button_label": button, "portfolio_link": link}

    @router.get("/reactivation/board-members/{member_record_id}/portfolio-email")
    async def preview_portfolio_email(member_record_id: str, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        material = await db.generated_materials.find_one(
            {"user_id": member["user_id"], "type": PORTFOLIO_TYPE, "application_id": member_record_id}, {"_id": 0})
        if not material or material["status"] != "Approved" or not material.get("share_token"):
            raise HTTPException(status_code=409, detail="Approve this Portfolio before preparing the email.")
        return await portfolio_email_content(member["user_id"], record, material, origin_of(request))

    class PortfolioEmailSend(BaseModel):
        subject: str = Field(min_length=1)
        body: str = Field(min_length=1)

    @router.post("/reactivation/board-members/{member_record_id}/portfolio-email")
    async def send_portfolio_email(member_record_id: str, payload: PortfolioEmailSend, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        material = await db.generated_materials.find_one(
            {"user_id": member["user_id"], "type": PORTFOLIO_TYPE, "application_id": member_record_id}, {"_id": 0})
        if not material or material["status"] != "Approved" or not material.get("share_token"):
            raise HTTPException(status_code=409, detail="Approve this Portfolio before sending the email.")
        defaults = await portfolio_email_content(member["user_id"], record, material, origin_of(request))
        link = defaults["portfolio_link"]
        body = payload.body if "[" in payload.body else payload.body + f"\n\n[{defaults['button_label']}]"
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        context = await founder_context(member["user_id"])
        message = {"from": os.environ["NONPROFIT_SENDER"], "to": [record["email"]],
                   "subject": payload.subject, "html": email_html(body, defaults["button_label"], link)}
        if context["founder_email"]:
            message["reply_to"] = [context["founder_email"]]
        try:
            await resend.Emails.send_async(message)
        except Exception as exc:
            logger.exception("Portfolio email send failed for %s", member_record_id)
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc
        now = datetime.now(timezone.utc).isoformat()
        await db.generated_materials.update_one(
            {"material_id": material["material_id"]},
            {"$set": {"sent_at": now, "sent_to": record["email"], "sent_version": material["current_version"], "updated_at": now}})
        return {"status": "sent", "sent_at": now}

    # ---------------- PUBLIC PORTFOLIO ----------------

    async def shared_portfolio(token: str) -> dict:
        material = await db.generated_materials.find_one(
            {"share_token": token, "type": {"$regex": "board_member_portfolio$"}}, {"_id": 0})
        if not material or material["status"] not in {"Approved"}:
            raise HTTPException(status_code=404, detail="This Portfolio is not available")
        return material

    async def portfolio_issuer(material: dict) -> dict:
        context = await founder_context(material["user_id"])
        return {"issued_by": context["founder_name"], "issuer_title": context["founder_title"],
                "organization": context["organization"],
                "issue_date": (material.get("approved_at") or material.get("updated_at", ""))[:10]}

    async def portfolio_member_name(material: dict) -> str:
        if material["type"].startswith("reactivation_"):
            record = await db.reactivation_board_members.find_one({"member_record_id": material["application_id"]}, {"_id": 0, "name": 1})
            return (record or {}).get("name", "")
        application = await db.opportunity_applications.find_one(
            {"application_id": material["application_id"]}, {"_id": 0, "profile_snapshot.full_name": 1, "applicant_email": 1})
        snapshot = (application or {}).get("profile_snapshot") or {}
        return snapshot.get("full_name") or (application or {}).get("applicant_email", "")

    @router.get("/portfolio/{token}")
    async def public_portfolio(token: str):
        material = await shared_portfolio(token)
        issuer = await portfolio_issuer(material)
        return {"title": material["title"], "member_name": await portfolio_member_name(material),
                "display_text": current_display(material),
                "assistant_url": f"/portfolio-assistant/{token}" if material.get("type") == PORTFOLIO_TYPE else "",
                **issuer}

    @router.get("/portfolio/{token}/pdf")
    async def public_portfolio_pdf(token: str):
        material = await shared_portfolio(token)
        issuer = await portfolio_issuer(material)
        member_name = await portfolio_member_name(material)
        return build_portfolio_pdf(material["title"], member_name, issuer, current_display(material))

    # ---------------- RECOMMITMENT EXECUTION ASSISTANT ----------------

    async def recommitment_assistant_context(material: dict) -> dict:
        record = await db.reactivation_board_members.find_one(
            {"member_record_id": material["application_id"]}, {"_id": 0}) or {}
        context = await founder_context(material["user_id"])
        return {
            "organization": context.get("organization", ""),
            "mission": context.get("mission", ""),
            "why_recommitment_matters": context.get("why_recommit", ""),
            "what_the_board_needs_to_help_accomplish": context.get("board_help_accomplish", ""),
            "need_by": context.get("need_by", ""),
            "board_member": record.get("name", ""),
            "confirmed_role": record.get("confirmed_role", ""),
            "final_outcome": record.get("conversation_outcome", ""),
            "authoritative_conversation_agreement": record.get("conversation_conclusion", ""),
            "approved_portfolio": current_display(material),
        }

    @router.get("/portfolio-assistant/{token}")
    async def recommitment_portfolio_assistant(token: str):
        material = await shared_portfolio(token)
        if material.get("type") != PORTFOLIO_TYPE:
            raise HTTPException(status_code=404, detail="This Recommitment Executive Assistant is not available")
        history = await db.reactivation_assistant_messages.find(
            {"material_id": material["material_id"]}, {"_id": 0, "role": 1, "text": 1}
        ).sort("created_at", 1).to_list(120)
        context = await recommitment_assistant_context(material)
        suggestions = [
            "Help me plan my first 30 days in this role",
            "Turn my Portfolio into a practical checklist",
            "Help me prepare for my next Board meeting",
            "What should I work on first?",
            "Draft a message or email I need for this responsibility",
            "Help me break one of my responsibilities into next actions",
        ]
        return {
            "member_name": context.get("board_member", ""),
            "organization_name": context.get("organization", ""),
            "confirmed_role": context.get("confirmed_role", ""),
            "suggested_actions": suggestions,
            "messages": history,
        }

    @router.post("/portfolio-assistant/{token}")
    async def use_recommitment_portfolio_assistant(token: str, payload: RecommitmentAssistantPayload):
        material = await shared_portfolio(token)
        if material.get("type") != PORTFOLIO_TYPE:
            raise HTTPException(status_code=404, detail="This Recommitment Executive Assistant is not available")
        context = await recommitment_assistant_context(material)
        request_text = (
            f"Create or help me execute this item: {payload.material_type}.\n\nAdditional request: {payload.message}"
            if payload.material_type else payload.message
        ).strip()
        if not request_text:
            raise HTTPException(status_code=422, detail="Tell the assistant what you need help with")
        recent = await db.reactivation_assistant_messages.find(
            {"material_id": material["material_id"]}, {"_id": 0, "role": 1, "text": 1}
        ).sort("created_at", -1).limit(12).to_list(12)
        recent.reverse()
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
        if not api_key:
            raise HTTPException(status_code=503, detail="Executive Assistant is not configured yet")
        provider = os.environ.get("EXECUTIVE_ASSISTANT_PROVIDER", "anthropic")
        model = os.environ.get("EXECUTIVE_ASSISTANT_MODEL", "claude-haiku-4-5-20251001")
        system = (
            "You are one Board Member's secure execution assistant. Help this person execute only the responsibilities "
            "contained in the approved Board Member Portfolio and the founder's authoritative conversation agreement. "
            "Do not invent organization facts, authority, commitments, relationships, deadlines or responsibilities. "
            "If a requested action falls outside the approved role, say that the founder or Board leadership should confirm it first. "
            "Turn responsibilities into practical next actions, checklists, drafts, preparation notes and ready-to-use materials. "
            "Use clear placeholders when a missing fact is required. Do not mention AI."
        )
        prompt = (
            "AUTHORITATIVE RECOMMITMENT CONTEXT:\n" + json.dumps(context, indent=1, default=str)
            + "\n\nRECENT CONVERSATION:\n" + json.dumps(recent, indent=1, default=str)
            + "\n\nBOARD MEMBER REQUEST:\n" + request_text
        )
        try:
            chat = LlmChat(
                api_key=api_key,
                session_id=f"recommitment-assistant-{material['material_id']}-{uuid.uuid4()}",
                system_message=system,
            ).with_model(provider, model)
            response = await chat.send_message(UserMessage(text=prompt))
            answer = response if isinstance(response, str) else getattr(response, "text", str(response))
        except Exception as exc:
            logger.exception("Recommitment assistant failed for %s", material["material_id"])
            raise HTTPException(status_code=502, detail="The Executive Assistant could not respond right now. Please try again.") from exc
        now = datetime.now(timezone.utc).isoformat()
        await db.reactivation_assistant_messages.insert_many([
            {"message_id": str(uuid.uuid4()), "material_id": material["material_id"], "role": "user", "text": request_text, "created_at": now},
            {"message_id": str(uuid.uuid4()), "material_id": material["material_id"], "role": "assistant", "text": answer, "created_at": datetime.now(timezone.utc).isoformat()},
        ])
        return {"answer": answer}

    # ---------------- PUBLIC SECURE FORM ----------------

    async def record_by_token(token: str) -> dict:
        record = await db.reactivation_board_members.find_one({"form_token": token}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This form link is not valid")
        return record

    @router.get("/board-recommitment/{token}")
    async def public_form_context(token: str):
        record = await db.reactivation_board_members.find_one({"form_token": token}, {"_id": 0})
        if record:
            context = await founder_context(record["user_id"])
            form = await db.reactivation_forms.find_one({"user_id": record["user_id"]}, {"_id": 0, "intro_text": 1, "status": 1})
            return {
                "organization_name": context["organization"],
                "logo_data_url": context.get("logo_data_url", ""),
                "founder_name": context["founder_name"],
                "founder_title": context["founder_title"],
                "introduction": (form or {}).get("intro_text", "") if (form or {}).get("status") == "Approved" else "",
                "submitted": record["status"] == "COMPLETED",
                "form_variant": record.get("form_variant", "full"),
                "recommitment_options": RECOMMITMENT_OPTIONS,
                "prefill": {"full_name": record.get("name", ""), "email": record.get("email", ""), "phone": record.get("phone", ""), "role": record.get("role", "")},
            }
        form = await db.reactivation_forms.find_one({"generic_token": token, "status": "Approved"}, {"_id": 0})
        if not form:
            raise HTTPException(status_code=404, detail="This form link is not valid")
        context = await founder_context(form["user_id"])
        return {
            "organization_name": context["organization"],
            "logo_data_url": context.get("logo_data_url", ""),
            "founder_name": context["founder_name"],
            "founder_title": context["founder_title"],
            "introduction": form.get("intro_text", ""),
            "submitted": False,
            "form_variant": "full",
            "recommitment_options": RECOMMITMENT_OPTIONS,
            "prefill": {"full_name": "", "email": "", "phone": "", "role": ""},
        }

    @router.post("/board-recommitment/{token}", status_code=201)
    async def submit_recommitment(token: str, payload: RecommitmentSubmission, request: Request):
        record = await db.reactivation_board_members.find_one({"form_token": token}, {"_id": 0})
        if not record:
            form = await db.reactivation_forms.find_one({"generic_token": token, "status": "Approved"}, {"_id": 0})
            if not form:
                raise HTTPException(status_code=404, detail="This form link is not valid")
            email = str(payload.email).lower()
            record = await db.reactivation_board_members.find_one({"user_id": form["user_id"], "email": email}, {"_id": 0})
            if not record:
                record = {
                    "member_record_id": str(uuid.uuid4()), "user_id": form["user_id"],
                    "name": payload.full_name, "email": email, "phone": payload.phone, "role": "",
                    "source": "recommitment_link", "status": "SENT", "form_token": secrets.token_urlsafe(32),
                    "form_variant": "active_advisory" if payload.form_variant == "active_advisory" else "full",
                    "call_notes": "", "created_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.reactivation_board_members.insert_one({**record})
        if record["status"] == "COMPLETED":
            raise HTTPException(status_code=409, detail="This response has already been submitted")
        variant = record.get("form_variant") or ("active_advisory" if payload.form_variant == "active_advisory" else "full")
        allowed_choices = [RECOMMIT_ACTIVE, RECOMMIT_ADVISORY] if variant == "active_advisory" else RECOMMITMENT_OPTIONS
        if payload.recommitment not in allowed_choices:
            raise HTTPException(status_code=422, detail="This choice is not available on this Recommitment Form")
        if payload.recommitment == RECOMMIT_ACTIVE:
            required = [payload.why_joined, payload.participation_barriers, payload.ownership_area,
                        payload.strengths_resources, payload.monthly_availability, payload.experience_improvement]
            if any(not value.strip() for value in required) or not payload.expertise or not (1 <= len(payload.contribution_interests) <= 3):
                raise HTTPException(status_code=422, detail="Please answer every required question")
            if payload.leadership_interest not in {"Yes", "I would like to discuss this"}:
                raise HTTPException(status_code=422, detail="Please answer every required question")
            if payload.leadership_interest == "Yes" and not payload.leadership_area.strip():
                raise HTTPException(status_code=422, detail="Please tell us the area or responsibility you would be interested in leading")
        elif payload.recommitment == RECOMMIT_ADVISORY:
            if not payload.decision_reason.strip() or not payload.strengths_resources.strip() or not payload.monthly_availability.strip():
                raise HTTPException(status_code=422, detail="Please tell us why Advisory Board service fits you, what you can contribute and your realistic availability")
        elif payload.recommitment == RECOMMIT_STEP_DOWN and not payload.decision_reason.strip():
            raise HTTPException(status_code=422, detail="Please briefly tell us what has led to your decision to step down")
        now = datetime.now(timezone.utc).isoformat()
        response = payload.model_dump()
        response["email"] = str(payload.email).lower()
        await db.reactivation_board_members.update_one(
            {"member_record_id": record["member_record_id"], "status": {"$ne": "COMPLETED"}},
            {"$set": {"status": "COMPLETED", "response": response, "form_variant": variant,
                      "submitted_at": now, "name": payload.full_name, "email": response["email"]}},
        )
        context = await founder_context(record["user_id"])
        try:
            if context["founder_email"]:
                first = payload.full_name.split(" ")[0]
                founder_first = context["founder_name"].split(" ")[0] if context["founder_name"] else "there"
                guided = await db.board_reactivation_intakes.find_one(
                    {"user_id": record["user_id"], "guided_session_id": {"$exists": True, "$ne": ""}},
                    {"_id": 0, "guided_session_id": 1}, sort=[("submitted_at", -1)]) or {}
                if guided.get("guided_session_id"):
                    view_url = (f"{origin_of(request)}/board-recommitment/dashboard?"
                                f"session_id={guided['guided_session_id']}&member={record['member_record_id']}#recommitment-responses")
                else:
                    view_url = f"{origin_of(request)}/app/reactivation/self-guided/module/3?member={record['member_record_id']}"
                body = (
                    f"Hi {founder_first},\n\n"
                    f"{payload.full_name} has completed their Board Member Profile & Recommitment Form for {context['organization']}.\n\n"
                    "Their responses are now available in your Board Reactivation workspace and will help you prepare for your conversation with them.\n\n"
                    f"[VIEW {first.upper()}'S RESPONSE]\n\n"
                    "Nonprofit Board Builder"
                )
                resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
                await resend.Emails.send_async({
                    "from": os.environ["NONPROFIT_SENDER"], "to": [context["founder_email"]],
                    "subject": f"Board Member Recommitment Received | {payload.full_name}",
                    "html": email_html(body, f"VIEW {first.upper()}'S RESPONSE", view_url),
                })
                await db.reactivation_board_members.update_one(
                    {"member_record_id": record["member_record_id"]},
                    {"$set": {"owner_notification_status": "Sent", "owner_notification_sent_at": now}})
        except Exception:
            logger.exception("Founder recommitment notification failed for %s", record["member_record_id"])
            await db.reactivation_board_members.update_one(
                {"member_record_id": record["member_record_id"]},
                {"$set": {"owner_notification_status": "Failed"}})
        return {"status": "submitted", "organization_name": context["organization"]}

    # ---------------- STEP 2: RECOMMITMENT FORM WORKFLOW ----------------

    class FormTextPayload(BaseModel):
        text: str = Field(min_length=1)

    @router.get("/reactivation/recommitment-form")
    async def get_recommitment_form(request: Request):
        member = await reactivation_member(request)
        form = await db.reactivation_forms.find_one({"user_id": member["user_id"]}, {"_id": 0}) or {}
        completed = await db.reactivation_board_members.count_documents({"user_id": member["user_id"], "status": "COMPLETED"})
        context = await founder_context(member["user_id"])
        token = form.get("generic_token", "")
        origin = origin_of(request)
        return {
            "status": form.get("status", "NONE"),
            "intro_text": form.get("intro_text", ""),
            "generic_token": token,
            "responses_received": completed,
            "active_advisory_link": f"{origin}/board-recommitment/{token}?variant=active_advisory" if token else "",
            "full_link": f"{origin}/board-recommitment/{token}?variant=full" if token else "",
        }

    @router.post("/reactivation/recommitment-form/generate")
    async def generate_recommitment_form(request: Request):
        member = await reactivation_member(request)
        context = await founder_context(member["user_id"])
        intake = await user_intake(member["user_id"])
        required_setup = [intake.get("mission"), intake.get("why_recommit"), intake.get("board_help_accomplish"), intake.get("need_by")]
        if any(not str(value or "").strip() for value in required_setup):
            raise HTTPException(status_code=409, detail="Answer the four Board Recommitment setup questions before generating the forms")
        intro = recommitment_form_intro(context["organization"], intake.get("mission", ""))
        intro += (
            f"\n\nWhy we are asking you to recommit: {intake.get('why_recommit', '').strip()}"
            f"\n\nWhat we need the Board to help accomplish: {intake.get('board_help_accomplish', '').strip()}"
            f"\n\nWhen we need this recommitment in place: {intake.get('need_by', '').strip()}"
        )
        existing = await db.reactivation_forms.find_one({"user_id": member["user_id"]}, {"_id": 0, "generic_token": 1})
        token = (existing or {}).get("generic_token") or secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc).isoformat()
        await db.reactivation_forms.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"status": "Draft", "intro_text": intro, "generic_token": token, "updated_at": now},
             "$setOnInsert": {"created_at": now}}, upsert=True)
        origin = origin_of(request)
        return {
            "status": "Draft", "intro_text": intro, "generic_token": token,
            "active_advisory_link": f"{origin}/board-recommitment/{token}?variant=active_advisory",
            "full_link": f"{origin}/board-recommitment/{token}?variant=full",
        }

    @router.put("/reactivation/recommitment-form")
    async def edit_recommitment_form(payload: FormTextPayload, request: Request):
        member = await reactivation_member(request)
        form = await db.reactivation_forms.find_one({"user_id": member["user_id"]}, {"_id": 0, "status": 1})
        if not form:
            raise HTTPException(status_code=409, detail="Generate the Recommitment Form first")
        await db.reactivation_forms.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"intro_text": payload.text, "status": "Draft", "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Draft"}

    @router.post("/reactivation/recommitment-form/approve")
    async def approve_recommitment_form(request: Request):
        member = await reactivation_member(request)
        form = await db.reactivation_forms.find_one({"user_id": member["user_id"]}, {"_id": 0, "status": 1})
        if not form:
            raise HTTPException(status_code=409, detail="Generate the Recommitment Form first")
        await db.reactivation_forms.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"status": "Approved", "approved_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Approved"}

    @router.get("/reactivation/recommitment-email")
    async def recommitment_email(request: Request, variant: str = "full"):
        member = await reactivation_member(request)
        form = await db.reactivation_forms.find_one({"user_id": member["user_id"]}, {"_id": 0, "status": 1, "generic_token": 1})
        if not form or form.get("status") != "Approved":
            raise HTTPException(status_code=409, detail="Generate and approve the Recommitment Form first")
        clean_variant = "active_advisory" if variant == "active_advisory" else "full"
        context = await founder_context(member["user_id"])
        link = f"{origin_of(request)}/board-recommitment/{form['generic_token']}?variant={clean_variant}"
        email = recommitment_outreach_email(
            "initial", "", context["founder_name"], context["founder_title"], context["organization"],
            mission=context.get("mission", ""), goals=context.get("board_help_accomplish", ""),
        )
        variant_note = (
            "This version asks the Board Member to choose between recommitting as an active Board Member and moving into an Advisory Board role."
            if clean_variant == "active_advisory"
            else "This version also gives the Board Member the option to step down from the Board gracefully."
        )
        return {**email, "form_link": link, "variant": clean_variant, "variant_note": variant_note}

    async def recommitment_email_draft(user_id: str, variant: str, origin: str) -> dict:
        clean_variant = "active_advisory" if variant == "active_advisory" else "full"
        saved = await db.reactivation_email_drafts.find_one(
            {"user_id": user_id, "variant": clean_variant}, {"_id": 0}) or {}
        form = await db.reactivation_forms.find_one(
            {"user_id": user_id, "status": "Approved"}, {"_id": 0, "generic_token": 1})
        if not form:
            raise HTTPException(status_code=409, detail="Generate and approve the Recommitment Form first")
        context = await founder_context(user_id)
        form_link = f"{origin}/board-recommitment/{form['generic_token']}?variant={clean_variant}"
        if saved.get("subject") and saved.get("body"):
            return {**saved, "form_link": form_link}
        generated = recommitment_outreach_email(
            "initial", "", context["founder_name"], context["founder_title"], context["organization"],
            mission=context.get("mission", ""), goals=context.get("board_help_accomplish", ""),
        )
        return {
            "variant": clean_variant, "status": "Draft",
            "subject": generated["subject"], "body": generated["body"], "form_link": form_link,
        }

    @router.get("/reactivation/recommitment-email-draft")
    async def get_recommitment_email_draft(request: Request, variant: str = "full"):
        member = await reactivation_member(request)
        return await recommitment_email_draft(member["user_id"], variant, origin_of(request))

    @router.put("/reactivation/recommitment-email-draft")
    async def save_recommitment_email_draft(payload: RecommitmentEmailDraftPayload, request: Request):
        member = await reactivation_member(request)
        clean_variant = "active_advisory" if payload.variant == "active_advisory" else "full"
        now = datetime.now(timezone.utc).isoformat()
        await db.reactivation_email_drafts.update_one(
            {"user_id": member["user_id"], "variant": clean_variant},
            {"$set": {
                "subject": payload.subject.strip(), "body": payload.body.strip(), "status": "Draft",
                "updated_at": now,
            }, "$setOnInsert": {"user_id": member["user_id"], "variant": clean_variant, "created_at": now}},
            upsert=True,
        )
        return await recommitment_email_draft(member["user_id"], clean_variant, origin_of(request))

    @router.post("/reactivation/recommitment-email-draft/approve")
    async def approve_recommitment_email_draft(request: Request, variant: str = "full"):
        member = await reactivation_member(request)
        clean_variant = "active_advisory" if variant == "active_advisory" else "full"
        draft = await recommitment_email_draft(member["user_id"], clean_variant, origin_of(request))
        now = datetime.now(timezone.utc).isoformat()
        await db.reactivation_email_drafts.update_one(
            {"user_id": member["user_id"], "variant": clean_variant},
            {"$set": {
                "subject": draft["subject"], "body": draft["body"], "status": "Approved",
                "approved_at": now, "updated_at": now,
            }, "$setOnInsert": {"user_id": member["user_id"], "variant": clean_variant, "created_at": now}},
            upsert=True,
        )
        return await recommitment_email_draft(member["user_id"], clean_variant, origin_of(request))

    # ---------------- STEP 3: UNDERSTAND THEIR RESPONSE ----------------

    ANALYSIS_TYPE = "reactivation_response_analysis"
    CONVERSATION_DIRECTIONS = ["Remain and Step Up", "Step Down", "Move to Advisory Board"]
    DIRECTION_GUIDANCE = {
        "Remain and Step Up": "This Board Member is remaining on the Board and agreeing to step up. The script must address their commitment, their responsibilities, their increased role, expectations going forward, and the appropriate conversation points to confirm all of it clearly and warmly.",
        "Step Down": "This Board Member is stepping down. The script must help the founder acknowledge their decision respectfully, conduct the conversation professionally, clarify the transition, address any relevant organizational process, and establish clear next steps.",
        "Move to Advisory Board": "This Board Member is transitioning from the governing Board into an advisory role. The script must clarify the transition, what the advisory relationship means, expectations, future involvement, and next steps.",
    }

    class DirectionPayload(BaseModel):
        direction: str = ""

    def analysis_display(structured: dict, name: str) -> str:
        first = name.split(" ")[0].upper() if name else "THIS BOARD MEMBER"

        def block(title, value, empty="None identified from their response"):
            if isinstance(value, list):
                return [title] + ([f"- {item}" for item in value] if value else [f"- {empty}"]) + [""]
            return [title, value or "", ""]

        lines = [f"UNDERSTANDING {first}'S RESPONSE", ""]
        lines += block("RECOMMITMENT POSITION", structured.get("recommitment_position", ""))
        lines += block("WHAT THEY APPEAR TO BE COMMUNICATING", structured.get("what_they_are_communicating", ""))
        lines += block("WHAT WE KNOW ABOUT THIS PERSON", structured.get("what_we_know_about_this_person", []))
        lines += block("WHAT MAY BE AFFECTING THEIR PARTICIPATION", structured.get("what_may_be_affecting_their_participation", []), "None supplied in their response")
        lines += block("WHAT THEY WANT MOVING FORWARD", structured.get("what_they_want_moving_forward", ""))
        if structured.get("realistic_capacity"):
            lines += block("REALISTIC CAPACITY", structured["realistic_capacity"])
        lines += block("WHAT THE ORGANIZATION SHOULD PAY ATTENTION TO", structured.get("what_the_organization_should_pay_attention_to", []))
        if structured.get("potential_fit_with_organization_needs"):
            lines += block("POTENTIAL FIT WITH ORGANIZATION NEEDS", structured["potential_fit_with_organization_needs"])
        lines += block("WHAT STILL NEEDS TO BE CLARIFIED IN THE CONVERSATION", structured.get("what_still_needs_to_be_clarified", []))
        lines += block("CONVERSATION OBJECTIVE", structured.get("conversation_objective", ""))
        lines += block("BOTTOM LINE FOR THE FOUNDER", structured.get("founder_bottom_line", ""))
        return "\n".join(lines).strip()

    @router.get("/reactivation/understand")
    async def understand_step(request: Request):
        member = await reactivation_member(request)
        user_id = member["user_id"]
        records = await db.reactivation_board_members.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
        materials = await db.generated_materials.find(
            {"user_id": user_id, "type": {"$in": [ANALYSIS_TYPE, "reactivation_conversation_script"]}},
            {"_id": 0, "material_id": 1, "application_id": 1, "type": 1, "status": 1, "updated_at": 1}).to_list(300)
        by_member = {m["application_id"]: m for m in materials if m.get("type") == ANALYSIS_TYPE}
        scripts_by_member = {m["application_id"]: m for m in materials if m.get("type") == "reactivation_conversation_script"}
        rows = []
        analyzed = 0
        for record in records:
            response = record.get("response") or {}
            analysis = material_summary(by_member.get(record["member_record_id"]))
            if analysis and analysis["status"] not in {"Generating", "Failed"}:
                analyzed += 1
            rows.append({**public_record(record),
                         "recommitment": response.get("recommitment", ""),
                         "recommitment": response.get("recommitment", ""),
                         "professional_role": response.get("current_position", ""), "employer": response.get("employer", ""),
                         "expertise": response.get("expertise", []), "contribution_interests": response.get("contribution_interests", []),
                         "monthly_availability": response.get("monthly_availability", ""),
                         "conversation_direction": record.get("conversation_direction", ""),
                         "analysis": analysis,
                         "script": material_summary(scripts_by_member.get(record["member_record_id"]))})
        completed = sum(1 for r in records if r["status"] == "COMPLETED")
        return {"members": rows, "directions": CONVERSATION_DIRECTIONS,
                "progress": {"total": len(records), "responded": completed, "analyzed": analyzed,
                             "waiting": len(records) - completed}}

    @router.post("/reactivation/board-members/{member_record_id}/analysis")
    async def generate_analysis(member_record_id: str, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        if record["status"] != "COMPLETED" or not record.get("response"):
            raise HTTPException(status_code=409, detail="This Board Member has not completed their Recommitment Form yet — their response is needed before it can be understood.")
        query = {"user_id": member["user_id"], "type": ANALYSIS_TYPE, "application_id": member_record_id}
        existing = await db.generated_materials.find_one(query, {"_id": 0, "material_id": 1, "status": 1})
        if existing and existing.get("status") == "Generating":
            return {"material_id": existing["material_id"], "status": "Generating"}
        intake = await user_intake(member["user_id"])
        org_context = {key: intake.get(key, "") for key in [
            "organization_name", "mission", "direction_12_24", "board_help_accomplish", "active_board_vision",
            "disengage_reason", "expected_contribution", "actually_happening",
            "founder_desired_outcomes", "founder_board_support_needed"]}
        context = ("ORGANIZATION CONTEXT:\n" + json.dumps(org_context, indent=1, default=str)
                   + "\n\nTHIS BOARD MEMBER'S ACTUAL PROFILE & RECOMMITMENT FORM RESPONSE:\n"
                   + json.dumps({"name": record["name"], "current_board_role": record.get("role", ""), **record["response"]}, indent=1, default=str))
        master = await get_master_record(db, user_id=member["user_id"])
        if master and master.get("data"):
            context += ("\n\nCOMPLETE BOARD FIX MASTER INTAKE (the founder's own description of the organization, its board, goals and priorities):\n"
                        + json.dumps(master["data"], indent=1, default=str)[:6000])
        if intake.get("bylaws_text"):
            context += "\n\nORGANIZATION BYLAWS EXTRACT (verified Board/governance context ONLY — never invent legal requirements or procedures):\n" + intake["bylaws_text"][:10000]
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            material_id = existing["material_id"]
            await db.generated_materials.update_one(query, {"$set": {"status": "Generating", "updated_at": now}})
        else:
            material_id = str(uuid.uuid4())
            await db.generated_materials.insert_one({
                "material_id": material_id, "user_id": member["user_id"], "type": ANALYSIS_TYPE,
                "application_id": member_record_id, "module": 3, "title": "Understanding Their Response",
                "versions": [], "current_version": 0, "status": "Generating",
                "created_at": now, "updated_at": now})

        async def run_analysis():
            try:
                structured = await generate_structured(ANALYSIS_TYPE, context)
                await save_reactivation_material(member["user_id"], ANALYSIS_TYPE, "Understanding Their Response",
                                                 member_record_id, structured, analysis_display(structured, record["name"]))
            except Exception as exc:
                logger.error("Response analysis failed for %s: %s", member_record_id, exc)
                await db.generated_materials.update_one(query, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_analysis())
        return {"material_id": material_id, "status": "Generating"}

    # ---------------- SUMMARY OF YOUR ENTIRE BOARD ----------------

    SUMMARY_TYPE = "reactivation_board_summary"
    SUMMARY_RECORD_ID = "board-summary"

    def board_summary_display(structured: dict) -> str:
        def block(title, value):
            if isinstance(value, list):
                return [title] + ([f"- {item}" for item in value] if value else ["- None identified."]) + [""]
            return [title, value or "", ""]
        lines = ["SUMMARY OF YOUR ENTIRE BOARD", ""]
        if (structured.get("summary_status") or "").strip():
            lines += block("BOARD SUMMARY STATUS", structured["summary_status"])
        lines += block("YOUR BOARD AT A GLANCE", structured.get("board_at_a_glance", ""))
        lines.append("YOUR CONFIRMED ACTIVE BOARD")
        active = structured.get("confirmed_active_board", []) or []
        if not active:
            lines.append("- No Board Members have a confirmed recommitment recorded yet.")
        for entry in active:
            lines.append("")
            lines.append(entry.get("member_name", ""))
            if entry.get("current_board_role"):
                lines.append(f"Current Board Role: {entry['current_board_role']}")
            if entry.get("what_they_bring"):
                lines.append(f"What They Bring: {entry['what_they_bring']}")
            if entry.get("agreed_contribution"):
                lines.append(f"Agreed Contribution: {entry['agreed_contribution']}")
            if entry.get("agreed_responsibility"):
                lines.append(f"Agreed Responsibility: {entry['agreed_responsibility']}")
            if entry.get("realistic_capacity"):
                lines.append(f"Realistic Capacity: {entry['realistic_capacity']}")
            if entry.get("organization_support_agreed"):
                lines.append(f"Support the Organization Agreed to Provide: {entry['organization_support_agreed']}")
        lines.append("")
        if structured.get("advisory_transitions"):
            lines.append("ADVISORY TRANSITIONS")
            for entry in structured["advisory_transitions"]:
                line = f"- {entry.get('member_name', '')}"
                if entry.get("agreed_advisory_direction"):
                    line += f" — {entry['agreed_advisory_direction']}"
                lines.append(line)
            lines.append("")
        if structured.get("stepped_down"):
            lines.append("BOARD MEMBERS WHO HAVE STEPPED DOWN")
            for entry in structured["stepped_down"]:
                line = f"- {entry.get('member_name', '')} — Stepping Down"
                if entry.get("agreed_transition_next_step"):
                    line += f". Next step: {entry['agreed_transition_next_step']}"
                lines.append(line)
            lines.append("")
        if structured.get("still_to_be_resolved"):
            lines.append("STILL TO BE RESOLVED")
            for entry in structured["still_to_be_resolved"]:
                lines.append(f"- {entry.get('member_name', '')} — {entry.get('current_status', '')}")
            lines.append("")
        lines += block("THE STRENGTHS YOUR BOARD NOW HAS", structured.get("strengths_of_your_confirmed_board", []))
        lines += block("WHAT YOUR BOARD CAN HELP CARRY NOW", structured.get("what_your_board_can_help_carry_now", []))
        lines += block("HOW YOU NEED TO SUPPORT THIS BOARD", structured.get("support_you_need_to_provide_your_board", []))
        lines += block("AREAS NOT YET COVERED", structured.get("areas_not_yet_covered", []))
        lines += block("WHAT THIS MEANS FOR YOUR NEXT STEP", structured.get("what_this_means_for_the_next_step", ""))
        return "\n".join(lines).strip()

    @router.get("/reactivation/board-summary")
    async def get_board_summary(request: Request):
        member = await reactivation_member(request)
        material = await db.generated_materials.find_one(
            {"user_id": member["user_id"], "type": SUMMARY_TYPE, "application_id": SUMMARY_RECORD_ID}, {"_id": 0})
        if not material:
            return {"status": "NONE"}
        return {"material_id": material["material_id"], "status": material["status"],
                "display_text": current_display(material), "updated_at": material.get("updated_at", "")}

    @router.post("/reactivation/board-summary")
    async def generate_board_summary(request: Request):
        member = await reactivation_member(request)
        user_id = member["user_id"]
        records = await db.reactivation_board_members.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
        responded = [r for r in records if r["status"] == "COMPLETED" and r.get("response")]
        if not responded:
            raise HTTPException(status_code=409, detail="At least one Board Member needs to complete the Recommitment Form before the board can be summarized.")
        query = {"user_id": user_id, "type": SUMMARY_TYPE, "application_id": SUMMARY_RECORD_ID}
        existing = await db.generated_materials.find_one(query, {"_id": 0, "material_id": 1, "status": 1})
        if existing and existing.get("status") == "Generating":
            return {"material_id": existing["material_id"], "status": "Generating"}
        intake = await user_intake(user_id)
        org_context = {key: intake.get(key, "") for key in [
            "organization_name", "mission", "direction_12_24", "board_help_accomplish", "active_board_vision",
            "current_skills", "missing_skills", "disengage_reason", "expected_contribution", "actually_happening",
            "founder_desired_outcomes", "founder_board_support_needed"]}

        def roster_entry(record: dict) -> dict:
            response = record.get("response") or {}
            outcome = record.get("conversation_outcome", "")
            conclusion = (record.get("conversation_conclusion") or "").strip()
            resolved = bool(conclusion) and outcome in {OUTCOME_ACTIVE, OUTCOME_ADVISORY, OUTCOME_SUPPORT, OUTCOME_STEP_DOWN}
            entry = {
                "name": record["name"], "current_board_role": record.get("role", ""),
                "form_status": "Completed" if record["status"] == "COMPLETED" else "Form not completed yet",
                "recommitment_answer": response.get("recommitment", ""),
                "conversation_status": "Conversation completed" if conclusion else "Conversation not completed yet",
                "final_recorded_outcome": outcome or "No final outcome recorded yet",
                "resolution": "RESOLVED" if resolved else "UNRESOLVED",
            }
            if conclusion:
                entry["conversation_conclusion_authoritative"] = conclusion[:2500]
            if resolved and outcome == OUTCOME_ACTIVE:
                entry["original_form_background_only"] = {key: response.get(key, "") for key in [
                    "why_joined", "expertise", "expertise_other", "participation_barriers", "contribution_interests",
                    "ownership_area", "leadership_interest", "leadership_area", "strengths_resources",
                    "monthly_availability", "experience_improvement"]}
            return entry

        roster = [roster_entry(record) for record in records]
        status_flag = "COMPLETE" if roster and all(entry["resolution"] == "RESOLVED" for entry in roster) else "INCOMPLETE"
        context = f"BOARD SUMMARY STATUS: {status_flag}\n\nORGANIZATION CONTEXT:\n" + json.dumps(org_context, indent=1, default=str)
        master = await get_master_record(db, user_id=user_id)
        if master and master.get("data"):
            context += ("\n\nCOMPLETE BOARD FIX MASTER INTAKE (the founder's own description of the organization, its board, goals and priorities):\n"
                        + json.dumps(master["data"], indent=1, default=str)[:8000])
        if intake.get("bylaws_text"):
            context += "\n\nORGANIZATION BYLAWS EXTRACT (verified Board/governance context ONLY — never invent legal requirements):\n" + intake["bylaws_text"][:10000]
        context += ("\n\nCOMPLETE CURRENT BOARD ROSTER — the saved Conversation Conclusion and final recorded outcome are the AUTHORITATIVE "
                    "source of each member's Board status and agreed contribution; original form responses are supporting background only; "
                    "UNRESOLVED members belong under Still To Be Resolved and are neither confirmed nor departed:\n\n")
        for entry in roster:
            context += json.dumps(entry, indent=1, default=str)[:6000] + "\n\n"
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            material_id = existing["material_id"]
            await db.generated_materials.update_one(query, {"$set": {"status": "Generating", "updated_at": now}})
        else:
            material_id = str(uuid.uuid4())
            await db.generated_materials.insert_one({
                "material_id": material_id, "user_id": user_id, "type": SUMMARY_TYPE,
                "application_id": SUMMARY_RECORD_ID, "module": 3, "title": "Summary of Your Entire Board",
                "versions": [], "current_version": 0, "status": "Generating",
                "created_at": now, "updated_at": now})

        async def run_summary():
            try:
                structured = await generate_structured(SUMMARY_TYPE, context)
                await save_reactivation_material(user_id, SUMMARY_TYPE, "Summary of Your Entire Board",
                                                 SUMMARY_RECORD_ID, structured, board_summary_display(structured))
            except Exception as exc:
                logger.error("Board summary generation failed for %s: %s", user_id, exc)
                await db.generated_materials.update_one(query, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_summary())
        return {"material_id": material_id, "status": "Generating"}

    @router.put("/reactivation/board-members/{member_record_id}/direction")
    async def save_direction(member_record_id: str, payload: DirectionPayload, request: Request):
        member = await reactivation_member(request)
        await owned_board_member(member["user_id"], member_record_id)
        if payload.direction and payload.direction not in CONVERSATION_DIRECTIONS:
            raise HTTPException(status_code=422, detail="Invalid conversation direction")
        await db.reactivation_board_members.update_one(
            {"member_record_id": member_record_id},
            {"$set": {"conversation_direction": payload.direction}})
        return {"status": "saved"}

    # ---------------- DASHBOARD OUTCOME EMAILS ----------------

    OUTCOME_EMAIL_TYPES = {
        "Continuing as an Active Board Member": ("reactivation_recommitment_confirmation", "Board Member Recommitment Confirmation Email"),
        "Stepping Down From the Board": ("reactivation_stepped_down_followup", "Stepped-Down Follow-Up Email"),
        "Transitioning to an Advisory Role": ("reactivation_advisory_confirmation", "Advisory Board Confirmation Email"),
    }

    @router.post("/reactivation/board-members/{member_record_id}/outcome-email")
    async def generate_outcome_email(member_record_id: str, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        outcome = record.get("conversation_outcome", "")
        if outcome not in OUTCOME_EMAIL_TYPES:
            raise HTTPException(status_code=409, detail="Record the final outcome (Recommitting, Advisory or Stepping Down) before generating this email.")
        if not (record.get("conversation_conclusion") or "").strip():
            raise HTTPException(status_code=409, detail="Save the Conversation Conclusion — what you and this Board Member actually agreed — before generating this email.")
        material_type, title = OUTCOME_EMAIL_TYPES[outcome]
        intake = await user_intake(member["user_id"])
        context_data = await founder_context(member["user_id"])
        context = (f"ORGANIZATION: {context_data['organization']}\nFOUNDER: {context_data['founder_name']}"
                   + (f" ({context_data['founder_title']})" if context_data.get("founder_title") else "")
                   + f"\n\nBOARD MEMBER: {record['name']} — current role: {record.get('role', 'Board Member')}"
                   + f"\n\nRECORDED FINAL OUTCOME: {outcome}"
                   + "\n\nFOUNDER'S SAVED CONVERSATION CONCLUSION (the AUTHORITATIVE record of what was ACTUALLY agreed):\n"
                   + record["conversation_conclusion"]
                   + "\n\nTHE BOARD MEMBER'S OWN FORM RESPONSES (background only — never turn a form selection into an agreed responsibility unless the Conversation Conclusion confirms it):\n"
                   + json.dumps(record.get("response") or {}, indent=1, default=str)[:6000])
        if material_type == "reactivation_recommitment_confirmation":
            contact = ", ".join(filter(None, [context_data.get("founder_email", ""), context_data.get("founder_phone", "")]))
            if contact:
                context += f"\n\nFOUNDER CONTACT DETAILS FOR THE SIGN-OFF: {contact}"
            analysis_material = await db.generated_materials.find_one(
                {"user_id": member["user_id"], "type": "reactivation_response_analysis", "application_id": member_record_id,
                 "status": {"$nin": ["Generating", "Failed"]}}, {"_id": 0})
            if analysis_material:
                context += "\n\nBACKGROUND ONLY — UNDERSTANDING THEIR RESPONSE (NOT authoritative; the Conversation Conclusion overrides it):\n" + current_display(analysis_material)[:4000]
        if outcome == "Stepping Down From the Board":
            if intake.get("bylaws_text"):
                context += "\n\nORGANIZATION BYLAWS EXTRACT (use ONLY procedures actually stated here):\n" + intake["bylaws_text"][:15000]
            elif intake.get("resignation_process"):
                context += "\n\nORGANIZATION'S DESCRIBED RESIGNATION PROCESS (use this, never invent requirements):\n" + intake["resignation_process"]
            else:
                context += "\n\nNo bylaws or resignation process were provided — do NOT cite any procedure; confirm next steps generally."
        try:
            structured = await generate_structured(material_type, context)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Generation failed: {str(exc)[:300]}. Your information is preserved — you can try again.") from exc
        display = f"SUBJECT: {structured.get('subject', '')}\n\n{structured.get('body', '')}"
        material = await save_reactivation_material(member["user_id"], material_type, title, member_record_id, structured, display)
        full = await db.generated_materials.find_one({"material_id": material["material_id"]}, {"_id": 0})
        return {**material, "display_text": current_display(full), "to_name": record["name"], "to_email": record.get("email", "")}

    @router.get("/reactivation/board-members/{member_record_id}/outcome-email")
    async def get_outcome_email(member_record_id: str, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        outcome = record.get("conversation_outcome", "")
        if outcome not in OUTCOME_EMAIL_TYPES:
            raise HTTPException(status_code=404, detail="No outcome email applies to this Board Member")
        material_type, _ = OUTCOME_EMAIL_TYPES[outcome]
        material = await db.generated_materials.find_one(
            {"user_id": member["user_id"], "type": material_type, "application_id": member_record_id}, {"_id": 0})
        if not material:
            raise HTTPException(status_code=404, detail="This email has not been generated yet")
        return {"material_id": material["material_id"], "status": material["status"],
                "display_text": current_display(material), "to_name": record["name"], "to_email": record.get("email", "")}

    # ---------------- ADMIN ----------------

    @router.get("/admin/reactivation/overview")
    async def admin_overview(request: Request):
        await authenticate_admin(request, db)
        purchases = await db.purchases.find({"entitlement": "reactivation_self_guided"}, {"_id": 0, "user_id": 1}).to_list(500)
        rows = []
        for purchase in purchases:
            context = await founder_context(purchase["user_id"])
            total = await db.reactivation_board_members.count_documents({"user_id": purchase["user_id"]})
            sent = await db.reactivation_board_members.count_documents({"user_id": purchase["user_id"], "status": {"$in": ["SENT", "COMPLETED"]}})
            completed = await db.reactivation_board_members.count_documents({"user_id": purchase["user_id"], "status": "COMPLETED"})
            rows.append({"user_id": purchase["user_id"], "customer": context["founder_name"], "organization": context["organization"],
                         "board_members": total, "forms_sent": sent, "forms_completed": completed})
        return {"customers": rows}

    return router
