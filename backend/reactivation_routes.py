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
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from auth_service import authenticate_admin
from member_auth import authenticate_member, require_entitlement
from ai_service import generate_structured

logger = logging.getLogger(__name__)

RECOMMITMENT_OPTIONS = [
    "Yes — I am ready to continue serving actively.",
    "Yes — but I need greater clarity about my role and responsibilities.",
    "Yes — but my current time/capacity is limited and I need a role that reflects that.",
    "I am unsure and would like to discuss what continued Board service would involve.",
    "No — I am no longer able to continue serving actively in my current Board role.",
]
ADVISORY_OPTION = "Transition to an Advisory Board / Advisory Role"
SUPPORT_OPTION = "Transition to Another Volunteer/Support Role"


class BoardMemberCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1)
    email: EmailStr
    phone: str = ""
    role: str = ""


class ImportRequest(BaseModel):
    application_id: str


class SendRequest(BaseModel):
    type: str = "initial"


class CallNotes(BaseModel):
    notes: str = ""


class RecommitmentSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")
    full_name: str = Field(min_length=1)
    preferred_name: str = ""
    email: EmailStr
    phone: str = ""
    city_state: str = ""
    linkedin: str = ""
    current_position: str = ""
    employer: str = ""
    industry: str = ""
    years_experience: str = ""
    expertise: List[str] = Field(min_length=1)
    expertise_other: str = ""
    networks: List[str] = Field(min_length=1)
    why_joined: str = Field(min_length=1)
    how_recruited: str = Field(min_length=1)
    original_role_expectation: str = Field(min_length=1)
    role_clarity: str = Field(min_length=1)
    clarity_help: str = ""
    board_experience: str = Field(min_length=1)
    participation_barriers: str = Field(min_length=1)
    board_improvement: str = Field(min_length=1)
    strategic_clarity: str = Field(min_length=1)
    planning_participation: str = Field(min_length=1)
    planning_involvement_desire: str = ""
    recommitment: str
    advisory_openness: str = ""
    support_role_openness: str = ""
    contribution_interests: List[str] = Field(min_length=1)
    fundraising_comfort: List[str] = Field(min_length=1)
    ownership_areas: str = Field(min_length=1)
    leadership_interest: str = Field(min_length=1)
    support_needed: str = Field(min_length=1)
    monthly_availability: str = Field(min_length=1)
    meeting_participation: str = Field(min_length=1)
    constraints: str = ""
    meaningful_service: str = Field(min_length=1)
    anything_else: str = ""
    confirmation: bool


def origin_of(request: Request) -> str:
    configured = os.environ.get("PUBLIC_ORIGIN") or request.headers.get("origin")
    if configured:
        return configured
    forwarded = request.headers.get("x-forwarded-host")
    return f"https://{forwarded}" if forwarded else "https://nonprofitboardbuilder.com"


def build_outreach_email(kind: str, member: dict, founder_name: str, founder_title: str, organization: str, form_link: str) -> dict:
    first = (member.get("name") or "").split(" ")[0]
    signature = founder_name + (f"\n{founder_title}" if founder_title else "") + f"\n{organization}"
    if kind == "reminder":
        subject = f"Reminder: Board Member Recommitment Form | {organization}"
        body = (
            f"Dear {first},\n\n"
            f"I wanted to follow up on the Board Member Profile & Recommitment Form I sent you for {organization}.\n\n"
            "We are using the responses from each Board Member to understand where everyone is, how people would like to contribute moving forward, and what support or clarity may be needed.\n\n"
            "If you have not completed yours yet, please use the link below:\n\n"
            "[COMPLETE MY FORM]\n\n"
            "Your response will help us prepare for the conversation about your Board role and how we move forward together.\n\n"
            f"Thank you,\n{signature}"
        )
        button_label = "COMPLETE MY FORM"
    else:
        subject = f"Board Recommitment & Profile | {organization}"
        body = (
            f"Dear {first},\n\n"
            f"As we continue strengthening the Board of {organization}, we are taking time to make sure every Board Member has clarity about their role, capacity and how they would like to contribute moving forward.\n\n"
            "Please take a few minutes to complete your Board Member Profile & Recommitment Form.\n\n"
            "Your responses will help us understand:\n"
            "- how you would like to continue contributing\n"
            "- the expertise and experience you bring\n"
            "- the areas where you would most like to help\n"
            "- the level of time you can realistically commit\n"
            "- any support or clarity you need from the organization\n\n"
            "This is not about pressuring anyone to stay.\n\n"
            "It is about having an honest understanding of where each Board Member is and making sure the people serving on the Board are positioned to contribute meaningfully.\n\n"
            "[COMPLETE MY BOARD MEMBER PROFILE & RECOMMITMENT FORM]\n\n"
            f"Thank you for taking the time to complete it.\n\n{signature}"
        )
        button_label = "COMPLETE MY BOARD MEMBER PROFILE & RECOMMITMENT FORM"
    return {"subject": subject, "body": body, "button_label": button_label, "form_link": form_link}


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
    doc = BaseDocTemplate(buffer, pagesize=LETTER, leftMargin=22 * mm, rightMargin=22 * mm, topMargin=22 * mm, bottomMargin=22 * mm, title=title)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")

    def decorate(canvas, _doc):
        canvas.saveState()
        canvas.setLineWidth(1.1)
        canvas.setStrokeColorRGB(0, 0, 0)
        canvas.rect(11 * mm, 11 * mm, LETTER[0] - 22 * mm, LETTER[1] - 22 * mm)
        if canvas.getPageNumber() > 1:
            canvas.setFont("Helvetica", 8)
            canvas.drawString(doc.leftMargin, 13.5 * mm, f"{issuer.get('organization', '')} — {title}")
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
    issuer_lines.extend([f"Organization: {issuer.get('organization', '')}", f"Date: {issuer.get('issue_date', '')}"])
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
            "organization": organization or "your organization",
            "transition_options": (intake or {}).get("transition_options", []),
        }

    async def owned_board_member(user_id: str, member_record_id: str) -> dict:
        record = await db.reactivation_board_members.find_one({"user_id": user_id, "member_record_id": member_record_id}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Board Member not found")
        return record

    def public_record(record: dict) -> dict:
        return {key: record.get(key, "") for key in [
            "member_record_id", "name", "email", "phone", "role", "status", "source",
            "last_sent_at", "last_reminder_at", "submitted_at", "call_notes",
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
            "call_notes": "", "created_at": datetime.now(timezone.utc).isoformat(),
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
            "call_notes": "", "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.reactivation_board_members.insert_one({**record})
        return {"status": "created", "member": public_record(record)}

    @router.get("/reactivation/board-members/{member_record_id}/email-preview")
    async def email_preview(member_record_id: str, request: Request, type: str = "initial"):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        context = await founder_context(member["user_id"])
        form_link = f"{origin_of(request)}/board-recommitment/{record['form_token']}"
        email = build_outreach_email(type, record, context["founder_name"], context["founder_title"], context["organization"], form_link)
        return {"to_name": record["name"], "to_email": record["email"], **email}

    @router.post("/reactivation/board-members/{member_record_id}/send")
    async def send_form(member_record_id: str, payload: SendRequest, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        context = await founder_context(member["user_id"])
        form_link = f"{origin_of(request)}/board-recommitment/{record['form_token']}"
        email = build_outreach_email(payload.type, record, context["founder_name"], context["founder_title"], context["organization"], form_link)
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
        script = (
            f"Hi {first}, it's {founder_first} from {context['organization']}.\n\n"
            "I wanted to quickly follow up on the Board Member Profile & Recommitment Form I sent you.\n\n"
            "We're asking every Board Member to complete it because I want to understand where everyone is, what people realistically have capacity for, and how each person would like to contribute moving forward.\n\n"
            "This isn't about pressuring anyone.\n\n"
            "I want us to have an honest picture of who is able to continue serving actively, where people need more clarity, and where we may need to make changes so the Board can function properly.\n\n"
            "I can resend the link to you now if that would help.\n\n"
            "Is there anything that's making it difficult for you to complete it?"
        )
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

    # ---------------- STEP 3: DIFFICULT CONVERSATIONS ----------------

    BASE_OUTCOMES = ["Continuing as an Active Board Member", "Follow-Up Conversation Needed"]

    def allowed_outcomes(transition_options: list) -> list:
        outcomes = list(BASE_OUTCOMES)
        if ADVISORY_OPTION in transition_options:
            outcomes.append("Transitioning to an Advisory Role")
        if SUPPORT_OPTION in transition_options:
            outcomes.append("Transitioning to Another Support Role")
        if "Step Down From the Board" in transition_options:
            outcomes.append("Stepping Down From the Board")
        return outcomes

    async def user_intake(user_id: str) -> dict:
        return await db.board_reactivation_intakes.find_one({"user_id": user_id}, {"_id": 0}, sort=[("submitted_at", -1)]) or {}

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
        if structured.get("fundraising_and_relationships"):
            lines.extend(["", "6. CLARIFY FUNDRAISING AND RELATIONSHIP EXPECTATIONS", structured["fundraising_and_relationships"]])
        lines.extend(["", "7. CLARIFY THE WAY FORWARD", structured.get("clarify_the_way_forward", ""), "",
                      "8. CLOSE WITH CLEAR NEXT STEPS", structured.get("close_with_clear_next_steps", "")])
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
                         "conversation_complete": done,
                         "script": material_summary(material_by_member.get(record["member_record_id"]))})
        return {
            "members": rows,
            "outcome_options": allowed_outcomes(intake.get("transition_options", [])),
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
        transition_options = intake.get("transition_options", [])
        permitted = [option for option in transition_options if option not in {"We Have Not Decided Yet"}]
        org_context = {key: intake.get(key, "") for key in [
            "organization_name", "mission", "direction_12_24", "board_help_accomplish", "active_board_vision",
            "present_board", "active_board", "disengaged_board", "current_skills", "missing_skills",
            "roles_defined", "roles_description", "expected_contribution", "actually_happening",
            "strategic_plan", "board_participated_planning", "planning_involvement",
            "disengage_reason", "disengage_when", "disengagement_signs", "reactivation_attempts", "attempts_outcome",
            "meeting_frequency", "typical_meeting", "clear_responsibilities_after_meetings",
        ]}
        context = "ORGANIZATION CONTEXT AND BOARD REACTIVATION INTAKE (provided by the founder):\n" + json.dumps(org_context, indent=1, default=str)
        context += "\n\nORGANIZATION-PERMITTED TRANSITION OPTIONS (the ONLY transitions that may be mentioned): "
        context += ", ".join(permitted) if permitted else "The organization has not decided on transition options yet — do not present specific transition structures; the founder will decide the appropriate path in the conversation."
        context += ("\n\nTHIS BOARD MEMBER (their actual Board Member Profile & Recommitment Form response):\n"
                    + json.dumps({"name": record["name"], "current_board_role": record.get("role", ""), **record["response"]}, indent=1, default=str))
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
        from io import BytesIO
        from fastapi.responses import Response
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer
        member = await reactivation_member(request)
        material = await owned_reactivation_material(member["user_id"], material_id)
        text = current_display(material)
        buffer = BytesIO()
        doc = BaseDocTemplate(buffer, pagesize=LETTER, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm, title=material["title"])
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")

        def decorate(canvas, _doc):
            canvas.saveState()
            canvas.setLineWidth(0.9)
            canvas.rect(10 * mm, 10 * mm, LETTER[0] - 20 * mm, LETTER[1] - 20 * mm)
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(doc.leftMargin + doc.width, 12.5 * mm, f"Page {canvas.getPageNumber()}")
            canvas.restoreState()

        doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=decorate)])
        heading = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=12.5, leading=16, spaceBefore=12, spaceAfter=5, keepWithNext=1)
        body = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=15.5, spaceAfter=6)
        bullet = ParagraphStyle("bullet", parent=body, leftIndent=12, spaceAfter=4)
        escape = lambda t: str(t).replace("&", "&amp;").replace("<", "&lt;")
        story = []
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                story.append(Spacer(1, 4))
            elif stripped.startswith("- "):
                story.append(Paragraph("• " + escape(stripped[2:]), bullet))
            elif stripped == stripped.upper() and len(stripped) < 90 and any(ch.isalpha() for ch in stripped):
                story.append(Paragraph(escape(stripped), heading))
            else:
                story.append(Paragraph(escape(stripped), body))
        doc.build(story)
        filename = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in f"{material['title']}".replace(" ", "-"))
        return Response(content=buffer.getvalue(), media_type="application/pdf",
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
        intake = await user_intake(member["user_id"])
        if payload.outcome not in allowed_outcomes(intake.get("transition_options", [])):
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
        groups = {"active": [], "advisory": [], "support": [], "stepping_down": [], "follow_up": [], "waiting": []}
        for record in records:
            outcome = record.get("conversation_outcome", "")
            response = record.get("response") or {}
            row = {**public_record(record), "conversation_outcome": outcome,
                   "conversation_conclusion": record.get("conversation_conclusion", ""),
                   "professional_role": response.get("current_position", ""), "employer": response.get("employer", ""),
                   "expertise": response.get("expertise", []), "contribution_interests": response.get("contribution_interests", []),
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

    def eligible_for_portfolio(record: dict) -> str:
        outcome = record.get("conversation_outcome", "")
        if outcome in {OUTCOME_ACTIVE, OUTCOME_ADVISORY}:
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
            {"name": record["name"], "current_board_role": record.get("role", ""), **(record.get("response") or {})}, indent=1, default=str)
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
                "display_text": current_display(material), **issuer}

    @router.get("/portfolio/{token}/pdf")
    async def public_portfolio_pdf(token: str):
        material = await shared_portfolio(token)
        issuer = await portfolio_issuer(material)
        member_name = await portfolio_member_name(material)
        return build_portfolio_pdf(material["title"], member_name, issuer, current_display(material))

    # ---------------- PUBLIC SECURE FORM ----------------

    async def record_by_token(token: str) -> dict:
        record = await db.reactivation_board_members.find_one({"form_token": token}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This form link is not valid")
        return record

    @router.get("/board-recommitment/{token}")
    async def public_form_context(token: str):
        record = await record_by_token(token)
        context = await founder_context(record["user_id"])
        return {
            "organization_name": context["organization"],
            "submitted": record["status"] == "COMPLETED",
            "allow_advisory": ADVISORY_OPTION in context["transition_options"],
            "allow_support_role": SUPPORT_OPTION in context["transition_options"],
            "recommitment_options": RECOMMITMENT_OPTIONS,
            "prefill": {"full_name": record.get("name", ""), "email": record.get("email", ""), "phone": record.get("phone", ""), "role": record.get("role", "")},
        }

    @router.post("/board-recommitment/{token}", status_code=201)
    async def submit_recommitment(token: str, payload: RecommitmentSubmission, request: Request):
        record = await record_by_token(token)
        if record["status"] == "COMPLETED":
            raise HTTPException(status_code=409, detail="This response has already been submitted")
        if not payload.confirmation:
            raise HTTPException(status_code=422, detail="The confirmation is required")
        if payload.recommitment not in RECOMMITMENT_OPTIONS:
            raise HTTPException(status_code=422, detail="Invalid recommitment selection")
        now = datetime.now(timezone.utc).isoformat()
        response = payload.model_dump()
        response["email"] = str(payload.email).lower()
        await db.reactivation_board_members.update_one(
            {"member_record_id": record["member_record_id"], "status": {"$ne": "COMPLETED"}},
            {"$set": {"status": "COMPLETED", "response": response, "submitted_at": now, "name": payload.full_name, "email": response["email"]}},
        )
        context = await founder_context(record["user_id"])
        try:
            if context["founder_email"]:
                first = payload.full_name.split(" ")[0]
                founder_first = context["founder_name"].split(" ")[0] if context["founder_name"] else "there"
                view_url = f"{origin_of(request)}/app/reactivation/self-guided/module/2?member={record['member_record_id']}"
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
        except Exception:
            logger.exception("Founder recommitment notification failed for %s", record["member_record_id"])
        return {"status": "submitted", "organization_name": context["organization"]}

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
