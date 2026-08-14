import asyncio
import html
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Dict, List

import resend
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from member_auth import authenticate_member, require_entitlement
from ai_service import generate_structured
from reactivation_routes import build_portfolio_pdf, email_html, origin_of

logger = logging.getLogger(__name__)

AUDIENCE_OPTIONS = ["Individuals", "Major Donors", "Local Businesses", "Large Corporations", "Foundations", "Government", "Faith Communities", "Community Organizations", "Alumni / Former Participants", "Families / Parents", "Professional Associations", "Other"]
OPPORTUNITY_OPTIONS = ["Individual Giving", "Major Gifts", "Corporate Sponsorships", "Corporate Partnerships", "Grants / Foundations", "Government Funding", "Events", "Monthly Giving", "Faith Community Support", "Online Campaigns", "Earned Revenue", "Other"]
NETWORK_OPTIONS = ["Business Owners", "Corporate Executives", "Potential Major Donors", "Foundations / Philanthropic Contacts", "Government Leaders", "Community Leaders", "Faith Leaders", "Schools / Universities", "Healthcare Leaders", "Media", "Professional Associations", "Other", "None"]
OUTREACH_OPTIONS = ["Personal Introductions", "One-to-One Meetings", "Email Outreach", "Corporate Meetings", "Community Events", "Fundraising Events", "Social Media / Content", "Speaking Engagements", "Partnership Outreach", "Grant Applications", "Direct Mail", "Other"]
PARTICIPATION_OPTIONS = ["Making Introductions", "Attending Donor Meetings", "Corporate Sponsorship Outreach", "Corporate Partnership Meetings", "Identifying Potential Funders", "Thanking / Stewarding Donors", "Grant / Foundation Research", "Reviewing Proposals", "Fundraising Events", "Speaking About the Mission", "Sharing Fundraising Content", "Hosting / Inviting People to Events", "Personal Giving", "Helping With Fundraising Planning", "Asking for Donations", "I Would Like Training Before Participating", "Other"]
SUPPORT_OPTIONS = ["Clear Fundraising Plan", "Talking Points", "Email Templates", "Text Message Scripts", "Call Scripts", "Case for Support", "Organization Overview", "Training", "List of Potential Funders", "Clear Personal Responsibilities", "Someone to Attend Meetings With Me", "Other"]

FORM_SECTIONS = [
    {"key": "goal", "title": "Our Fundraising Goal", "questions": [
        {"id": "goal_important", "type": "long", "required": True},
        {"id": "goal_clarity", "type": "long", "required": False},
    ]},
    {"key": "audiences", "title": "Who Should Care About This Mission?", "questions": [
        {"id": "funding_audiences", "type": "multi", "options": AUDIENCE_OPTIONS, "required": True},
        {"id": "audiences_why", "type": "long", "required": True},
    ]},
    {"key": "opportunities", "title": "Fundraising Opportunities", "questions": [
        {"id": "opportunities", "type": "multi", "options": OPPORTUNITY_OPTIONS, "required": True},
        {"id": "opportunity_priority", "type": "long", "required": True},
    ]},
    {"key": "relationships", "title": "Relationships We Already Have", "questions": [
        {"id": "network_categories", "type": "multi", "options": NETWORK_OPTIONS, "required": True},
        {"id": "specific_relationships", "type": "long", "required": False},
    ]},
    {"key": "attracting", "title": "Attracting Funders", "questions": [
        {"id": "why_support", "type": "long", "required": True},
        {"id": "talk_about", "type": "long", "required": True},
    ]},
    {"key": "outreach", "title": "Ways to Reach People", "questions": [
        {"id": "outreach_methods", "type": "multi", "options": OUTREACH_OPTIONS, "required": True},
        {"id": "outreach_add", "type": "long", "required": False},
    ]},
    {"key": "involvement", "title": "Board Involvement", "questions": [
        {"id": "participation_activities", "type": "multi", "options": PARTICIPATION_OPTIONS, "required": True},
    ]},
    {"key": "ownership", "title": "What You Could Own", "questions": [
        {"id": "ownership", "type": "long", "required": True},
    ]},
    {"key": "support", "title": "Support You Need", "questions": [
        {"id": "support_needed", "type": "multi", "options": SUPPORT_OPTIONS, "required": True},
    ]},
    {"key": "ninety", "title": "90-Day Priorities", "questions": [
        {"id": "ninety_day_priorities", "type": "long", "required": True},
    ]},
    {"key": "additional", "title": "Additional Ideas", "questions": [
        {"id": "fundraising_idea", "type": "long", "required": False},
        {"id": "final_thoughts", "type": "long", "required": False},
    ]},
]

QUESTION_META = {q["id"]: q for section in FORM_SECTIONS for q in section["questions"]}
REQUIRED_QUESTION_IDS = [qid for qid, q in QUESTION_META.items() if q["required"]]

RELATIONSHIP_NOTE = "Selecting a type of relationship does not mean you are committing to making an introduction. It simply helps us understand what may already exist around our Board."
OWNERSHIP_EXAMPLES = "Examples (only as helpful guidance): corporate relationships, donor stewardship, events, fundraising communications, identifying prospects."
CONFIRMATION_TEXT = "I understand that my responses are part of the Board's fundraising planning process and may be combined with ideas from other Board Members to help develop the organization's Fundraising Strategy Plan."


def default_prompts(organization: str) -> Dict[str, str]:
    return {
        "goal_important": "What stands out to you as most important about what we are trying to fund or accomplish?",
        "goal_clarity": "Is there anything about the fundraising goal or priority that you believe needs greater clarity?",
        "funding_audiences": "Who do you believe we should be building relationships with to support this mission?",
        "audiences_why": "Why do you believe these people or organizations may care about our work?",
        "opportunities": "Which fundraising opportunities do you believe we should explore or strengthen?",
        "opportunity_priority": "Which of these do you believe represents the greatest opportunity for the organization right now, and why?",
        "network_categories": "What types of relationships or networks do you already have that may be useful as we build our fundraising relationships?",
        "specific_relationships": "Are there specific relationships or networks you would be comfortable exploring on behalf of the organization?",
        "why_support": f"What do you believe would make someone want to support {organization}?",
        "talk_about": "What stories, results, programs or parts of the mission do you think we should talk about more when building relationships with potential funders?",
        "outreach_methods": "What do you believe are the best ways for us to reach and build relationships with potential supporters?",
        "outreach_add": "What would you add or do differently?",
        "participation_activities": "Which fundraising activities would you personally be comfortable helping with?",
        "ownership": "Is there a part of the fundraising process you would be willing to take responsibility for or help lead?",
        "support_needed": "What would help you participate more effectively in fundraising?",
        "ninety_day_priorities": "If we could accomplish three fundraising things in the next 90 days, what do you think they should be?",
        "fundraising_idea": "What fundraising idea or opportunity do you believe we should consider that we may not have discussed yet?",
        "final_thoughts": "Is there anything else you would like the organization to consider as we build this fundraising plan together?",
    }


def form_payload(content: dict) -> dict:
    prompts = content.get("question_prompts", {})
    return {
        "title": "Board Fundraising Planning Form",
        "introduction": content.get("introduction", ""),
        "goal_context": content.get("goal_context", ""),
        "relationship_note": RELATIONSHIP_NOTE,
        "ownership_examples": OWNERSHIP_EXAMPLES,
        "confirmation_text": CONFIRMATION_TEXT,
        "sections": [
            {"key": section["key"], "title": section["title"], "questions": [
                {"id": q["id"], "type": q["type"], "required": q["required"],
                 "options": q.get("options", []), "prompt": prompts.get(q["id"], "")}
                for q in section["questions"]
            ]}
            for section in FORM_SECTIONS
        ],
    }


class ParticipantCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1)
    email: EmailStr
    phone: str = ""
    role: str = ""


class ParticipantImport(BaseModel):
    source: str
    ref_id: str


class SendRequest(BaseModel):
    type: str = "initial"


class FormEditPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    introduction: str = Field(min_length=1)
    goal_context: str = ""
    question_prompts: Dict[str, str]


class CallNotes(BaseModel):
    notes: str = ""


class PlanningSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")
    full_name: str = Field(min_length=1)
    email: EmailStr
    role: str = ""
    goal_important: str = Field(min_length=1)
    goal_clarity: str = ""
    funding_audiences: List[str] = Field(min_length=1)
    audiences_why: str = Field(min_length=1)
    opportunities: List[str] = Field(min_length=1)
    opportunity_priority: str = Field(min_length=1)
    network_categories: List[str] = Field(min_length=1)
    specific_relationships: str = ""
    why_support: str = Field(min_length=1)
    talk_about: str = Field(min_length=1)
    outreach_methods: List[str] = Field(min_length=1)
    outreach_add: str = ""
    participation_activities: List[str] = Field(min_length=1)
    ownership: str = Field(min_length=1)
    support_needed: List[str] = Field(min_length=1)
    ninety_day_priorities: str = Field(min_length=1)
    fundraising_idea: str = ""
    final_thoughts: str = ""
    confirmation: bool


def build_planning_email(kind: str, participant: dict, founder_name: str, founder_title: str, organization: str, form_link: str) -> dict:
    first = (participant.get("name") or "").split(" ")[0]
    signature = founder_name + (f"\n{founder_title}" if founder_title else "") + f"\n{organization}"
    if kind == "reminder":
        subject = "Reminder: Help Us Build Our Fundraising Plan"
        body = (
            f"Dear {first},\n\n"
            f"I wanted to follow up on the Board Fundraising Planning Form for {organization}.\n\n"
            "We are using the Board's ideas to build our fundraising strategy, and I would like your perspective included before we move into the next stage.\n\n"
            "If you have not completed your form yet, please use your link below:\n\n"
            "[COMPLETE MY FUNDRAISING PLANNING FORM]\n\n"
            f"Thank you for helping us build this plan together.\n\n{signature}"
        )
    else:
        subject = f"Help Us Build Our Fundraising Plan | {organization}"
        body = (
            f"Dear {first},\n\n"
            f"We are beginning the process of building the fundraising plan for {organization}, and I want the Board involved in shaping it.\n\n"
            "Rather than creating the plan and bringing it to the Board after the fact, I want us to build it together.\n\n"
            "Your ideas, experience, relationships and perspective can help us determine who we should be building relationships with, which fundraising opportunities we should prioritize, and how each of us can contribute.\n\n"
            "Please complete the short Board Fundraising Planning Form below.\n\n"
            "[COMPLETE MY FUNDRAISING PLANNING FORM]\n\n"
            "Your responses will be combined with the ideas of the other Board Members and our organizational priorities as we build the Fundraising Strategy Plan.\n\n"
            f"Thank you for helping us build this together.\n\n{signature}"
        )
    return {"subject": subject, "body": body, "button_label": "COMPLETE MY FUNDRAISING PLANNING FORM", "form_link": form_link}


REVIEW_OPTIONS = [
    "I support the plan as written",
    "I support the overall direction but have suggestions",
    "I have issues I believe we should discuss before adopting the plan",
]

STRATEGY_SECTIONS = [
    ("Executive Summary", "executive_summary"), ("1. Fundraising Goal", "fundraising_goal"),
    ("2. What We Are Raising Money For", "what_we_are_raising_money_for"),
    ("3. Who We Should Build Relationships With", "who_we_should_build_relationships_with"),
    ("4. Priority Fundraising Opportunities", "priority_fundraising_opportunities"),
    ("5. What We Need People to Understand About the Mission", "what_people_should_understand"),
    ("6. How We Will Build Fundraising Relationships", "how_we_will_build_relationships"),
    ("7. Relationships Already Around the Board", "relationships_around_the_board"),
    ("8. How the Board Can Participate", "how_the_board_can_participate"),
    ("9. Founder and Staff Responsibilities", "founder_staff_responsibilities"),
    ("10. What We Need to Execute", "what_we_need_to_execute"),
    ("11. The Next 90 Days", "next_90_days"),
    ("12. 12-Month Fundraising Direction", "twelve_month_direction"),
    ("13. How We Will Know the Plan Is Moving", "how_we_know_plan_is_moving"),
    ("14. Items for Board Review", "items_for_board_review"),
    ("15. Next Step: Review and Adopt the Plan", "next_step_review_and_adopt"),
]


def strategy_display(structured: dict, organization: str) -> str:
    lines = ["FUNDRAISING STRATEGY PLAN", organization, ""]
    for heading, key in STRATEGY_SECTIONS:
        value = structured.get(key, "")
        lines.append(heading.upper())
        if isinstance(value, list):
            lines.extend([f"- {item}" for item in value])
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines).strip()


GUIDE_SECTIONS = [
    ("1. Objective for the Discussion", "objective"), ("2. Before the Discussion", "before_discussion"),
    ("3. Open the Discussion", "open_discussion"), ("4. Reconnect Everyone to What We Are Trying to Accomplish", "reconnect"),
    ("5. Review the Fundraising Strategy", "review_strategy"), ("6. Work Through the Board's Feedback", "work_through_feedback"),
    ("7. Confirm What We Are Prioritizing", "confirm_priorities"), ("8. Confirm What the Board Will Carry", "confirm_board_carry"),
    ("9. Establish Individual Ownership", "establish_individual_ownership"), ("10. Identify What Board Members Need to Execute", "identify_needs"),
    ("11. Agree on What Happens First", "agree_first_90"), ("12. Confirm the Way Forward", "confirm_way_forward"),
    ("13. Close With Ownership", "close_with_ownership"),
]

PLAN_STATUSES = ["Adopted as Presented", "Adopted With Changes", "Further Review Needed"]
RESPONSIBILITY_STATUSES = ["Responsibility Agreed", "Follow-Up Needed", "No Fundraising Responsibility Agreed Yet"]


def guide_display(structured: dict, organization: str) -> str:
    lines = ["PLAN ADOPTION FACILITATION GUIDE", organization, ""]
    for heading, key in GUIDE_SECTIONS:
        lines.extend([heading.upper(), str(structured.get(key, "")), ""])
    return "\n".join(lines).strip()


def toolkit_display(structured: dict, organization: str) -> str:
    lines = ["BOARD FUNDRAISING EXECUTION TOOLKIT", organization, "", "OVERVIEW", structured.get("overview", ""), ""]
    for heading, key in [("EMAIL TOOLS", "email_tools"), ("TEXT MESSAGE TOOLS", "text_tools"),
                         ("CALL SCRIPTS", "call_scripts"), ("FOLLOW-UP AND STEWARDSHIP", "stewardship_tools")]:
        tools = structured.get(key) or []
        if not tools:
            continue
        lines.extend([heading, ""])
        for tool in tools:
            lines.append(str(tool.get("title", "")).upper())
            if tool.get("when_to_use"):
                lines.append(f"When to use this: {tool['when_to_use']}")
            lines.extend([str(tool.get("content", "")), ""])
    return "\n".join(lines).strip()


class TextPayload(BaseModel):
    text: str = Field(min_length=1)


class PlanStatusPayload(BaseModel):
    status: str


class ResponsibilityPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    agreed_responsibility: str = ""
    responsibility_status: str


class StrategyEditPayload(BaseModel):
    display_text: str = Field(min_length=1)


class ReviewSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")
    position: str
    discussion_points: str = ""
    contribution: str = Field(min_length=1)
    support_needs: str = ""


def create_activation_planning_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def activation_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {"activation_self_guided"})
        return member

    async def activation_intake(user_id: str) -> dict:
        return await db.board_activation_intakes.find_one({"user_id": user_id}, {"_id": 0}, sort=[("submitted_at", -1)]) or {}

    async def founder_context(user_id: str) -> dict:
        founder = await db.members.find_one({"user_id": user_id}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1})
        intake = await activation_intake(user_id)
        organization = intake.get("organization_name", "")
        profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data.organization_name": 1, "data.mission": 1}) or {}
        if not organization:
            organization = profile.get("data", {}).get("organization_name", "")
        reactivation = await db.board_reactivation_intakes.find_one({"user_id": user_id}, {"_id": 0, "founder_title": 1}, sort=[("submitted_at", -1)]) or {}
        return {
            "founder_name": f"{founder['first_name']} {founder['last_name']}".strip() if founder else "",
            "founder_email": (founder or {}).get("email", ""),
            "founder_title": reactivation.get("founder_title", ""),
            "organization": organization or "your organization",
            "mission": profile.get("data", {}).get("mission", ""),
        }

    async def owned_participant(user_id: str, participant_id: str) -> dict:
        record = await db.activation_participants.find_one({"user_id": user_id, "participant_id": participant_id}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Board Member not found")
        return record

    def public_participant(record: dict) -> dict:
        return {key: record.get(key, "") for key in [
            "participant_id", "name", "email", "phone", "role", "status", "source",
            "last_sent_at", "last_reminder_at", "submitted_at", "call_notes", "form_version",
        ]}

    async def current_form(user_id: str) -> dict:
        return await db.activation_planning_forms.find_one({"user_id": user_id}, {"_id": 0}) or {}

    def form_summary(form: dict) -> dict:
        if not form:
            return {"status": "NONE", "approved_version": 0}
        return {
            "status": form.get("status", "NONE"),
            "approved_version": form.get("approved_version", 0),
            "content": form_payload(form.get("content", {})) if form.get("content") else None,
            "edited_since_generation": form.get("content_source") == "edited",
            "generation_error": form.get("generation_error", ""),
            "approved_at": form.get("approved_at", ""),
            "updated_at": form.get("updated_at", ""),
        }

    # ---------------- FOUNDER: WORKSPACE OVERVIEW ----------------

    @router.get("/activation/planning")
    async def planning_overview(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        participants = await db.activation_participants.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).to_list(300)
        known_emails = {p["email"] for p in participants}
        suggestions = []
        joined = await db.opportunity_applications.find(
            {"owner_user_id": user_id, "$or": [{"final_outcome": "Joined Board"}, {"status": "Selected"}]},
            {"_id": 0, "application_id": 1, "profile_snapshot": 1, "applicant_email": 1},
        ).to_list(100)
        for app in joined:
            email = (app.get("applicant_email") or "").lower()
            if email and email not in known_emails:
                known_emails.add(email)
                suggestions.append({"source": "recruitment", "ref_id": app["application_id"],
                                    "name": app.get("profile_snapshot", {}).get("full_name", ""), "email": email,
                                    "label": "Joined through Recruitment"})
        reactivation_members = await db.reactivation_board_members.find(
            {"user_id": user_id, "conversation_outcome": {"$ne": "Stepping Down From the Board"}},
            {"_id": 0, "member_record_id": 1, "name": 1, "email": 1, "role": 1},
        ).to_list(200)
        for record in reactivation_members:
            email = (record.get("email") or "").lower()
            if email and email not in known_emails:
                known_emails.add(email)
                suggestions.append({"source": "reactivation", "ref_id": record["member_record_id"],
                                    "name": record.get("name", ""), "email": email,
                                    "label": "Current Board Member from Reactivation"})
        invited = sum(1 for p in participants if p["status"] in {"SENT", "COMPLETED"})
        received = sum(1 for p in participants if p["status"] == "COMPLETED")
        form = await current_form(user_id)
        intake = await activation_intake(user_id)
        return {
            "form": form_summary(form),
            "has_intake": bool(intake),
            "participants": [public_participant(p) for p in participants],
            "suggestions": suggestions,
            "progress": {"invited": invited, "received": received, "waiting": invited - received,
                         "selected": len(participants)},
        }

    # ---------------- FOUNDER: PARTICIPANTS ----------------

    @router.post("/activation/participants", status_code=201)
    async def add_participant(payload: ParticipantCreate, request: Request):
        member = await activation_member(request)
        email = str(payload.email).lower()
        existing = await db.activation_participants.find_one({"user_id": member["user_id"], "email": email}, {"_id": 0})
        if existing:
            return {"status": "exists", "participant": public_participant(existing)}
        record = {
            "participant_id": str(uuid.uuid4()), "user_id": member["user_id"],
            "name": payload.name, "email": email, "phone": payload.phone, "role": payload.role,
            "source": "manual", "status": "NOT SENT", "form_token": secrets.token_urlsafe(32),
            "form_version": 0, "call_notes": "", "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.activation_participants.insert_one({**record})
        return {"status": "created", "participant": public_participant(record)}

    @router.post("/activation/participants/import", status_code=201)
    async def import_participant(payload: ParticipantImport, request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        if payload.source == "recruitment":
            app = await db.opportunity_applications.find_one(
                {"owner_user_id": user_id, "application_id": payload.ref_id},
                {"_id": 0, "profile_snapshot": 1, "applicant_email": 1, "final_outcome": 1, "status": 1})
            if not app or not (app.get("final_outcome") == "Joined Board" or app.get("status") == "Selected"):
                raise HTTPException(status_code=404, detail="Board Member not found")
            name = app.get("profile_snapshot", {}).get("full_name", "")
            email = (app.get("applicant_email") or "").lower()
            phone = app.get("profile_snapshot", {}).get("phone", "")
            role = "Board Member"
        elif payload.source == "reactivation":
            record = await db.reactivation_board_members.find_one(
                {"user_id": user_id, "member_record_id": payload.ref_id}, {"_id": 0, "name": 1, "email": 1, "phone": 1, "role": 1, "conversation_outcome": 1})
            if not record:
                raise HTTPException(status_code=404, detail="Board Member not found")
            if record.get("conversation_outcome") == "Stepping Down From the Board":
                raise HTTPException(status_code=409, detail="This person has stepped down from the Board and cannot be added as a current participant")
            name, email = record.get("name", ""), (record.get("email") or "").lower()
            phone, role = record.get("phone", ""), record.get("role", "Board Member")
        else:
            raise HTTPException(status_code=422, detail="Unknown source")
        existing = await db.activation_participants.find_one({"user_id": user_id, "email": email}, {"_id": 0})
        if existing:
            return {"status": "exists", "participant": public_participant(existing)}
        participant = {
            "participant_id": str(uuid.uuid4()), "user_id": user_id, "name": name, "email": email,
            "phone": phone, "role": role or "Board Member", "source": payload.source,
            "source_ref_id": payload.ref_id, "status": "NOT SENT", "form_token": secrets.token_urlsafe(32),
            "form_version": 0, "call_notes": "", "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.activation_participants.insert_one({**participant})
        return {"status": "created", "participant": public_participant(participant)}

    @router.delete("/activation/participants/{participant_id}")
    async def remove_participant(participant_id: str, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        if record["status"] != "NOT SENT":
            raise HTTPException(status_code=409, detail="This Board Member has already been sent the planning form")
        await db.activation_participants.delete_one({"participant_id": participant_id, "user_id": member["user_id"]})
        return {"status": "removed"}

    # ---------------- FOUNDER: MASTER FORM ----------------

    @router.post("/activation/planning-form/generate")
    async def generate_form(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        intake = await activation_intake(user_id)
        if not intake:
            raise HTTPException(status_code=409, detail="Your Activation intake was not found. Please complete the Activation intake first.")
        context_info = await founder_context(user_id)
        form = await current_form(user_id)
        if form.get("status") == "Generating":
            return {"status": "Generating"}
        now = datetime.now(timezone.utc).isoformat()
        base = {
            "form_id": form.get("form_id") or str(uuid.uuid4()), "user_id": user_id,
            "status": "Generating", "generation_error": "", "updated_at": now,
        }
        await db.activation_planning_forms.update_one(
            {"user_id": user_id},
            {"$set": base, "$setOnInsert": {"approved_version": 0, "approved_versions": [], "created_at": now}},
            upsert=True,
        )
        org_context = {
            "founder_name": intake.get("your_name", "") or context_info["founder_name"],
            "organization_name": context_info["organization"],
            "mission": context_info["mission"],
            "organization_direction_12_24_months": intake.get("direction_12_24", ""),
            "organization_priorities": intake.get("organization_priorities", ""),
            "fundraising_goal": intake.get("fundraising_goal", ""),
            "amount_needed": intake.get("amount_needed", ""),
            "what_money_will_accomplish": intake.get("money_accomplish", ""),
            "current_fundraising_methods": intake.get("current_methods", []),
            "written_strategy_status": intake.get("written_strategy", ""),
            "fundraising_calendar_status": intake.get("fundraising_calendar", ""),
            "who_carries_fundraising": intake.get("fundraising_carriers", []),
            "total_board_members": intake.get("present_board", ""),
            "active_board_members": intake.get("active_board", ""),
            "current_board_fundraising_involvement": intake.get("board_fundraising_involvement", ""),
            "current_board_fundraising_activities": intake.get("board_fundraising_activities", []),
            "known_board_skills_and_relationships": intake.get("board_skills_relationships", ""),
            "known_fundraising_barriers": intake.get("perceived_barriers", ""),
        }
        import json as jsonlib
        context = "VERIFIED ORGANIZATION AND BOARD CONTEXT (the only facts you may use):\n" + jsonlib.dumps(org_context, indent=1, default=str)

        async def run_generation():
            try:
                structured = await generate_structured("activation_planning_form", context)
                content = {
                    "introduction": structured.get("introduction", "").strip(),
                    "goal_context": structured.get("goal_context", "").strip(),
                    "question_prompts": default_prompts(context_info["organization"]),
                }
                await db.activation_planning_forms.update_one({"user_id": user_id}, {"$set": {
                    "status": "Draft", "content": content, "content_source": "generated",
                    "updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Planning form generation failed for %s: %s", user_id, exc)
                await db.activation_planning_forms.update_one({"user_id": user_id}, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating"}

    @router.get("/activation/planning-form")
    async def get_form(request: Request):
        member = await activation_member(request)
        return form_summary(await current_form(member["user_id"]))

    @router.put("/activation/planning-form")
    async def save_form(payload: FormEditPayload, request: Request):
        member = await activation_member(request)
        form = await current_form(member["user_id"])
        if not form or not form.get("content"):
            raise HTTPException(status_code=409, detail="Generate your Board Fundraising Planning Form first")
        prompts = dict(form["content"].get("question_prompts", {}))
        for qid, prompt in payload.question_prompts.items():
            if qid in QUESTION_META and prompt.strip():
                prompts[qid] = prompt.strip()
        content = {"introduction": payload.introduction, "goal_context": payload.goal_context, "question_prompts": prompts}
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_planning_forms.update_one({"user_id": member["user_id"]}, {"$set": {
            "content": content, "content_source": "edited", "status": "Draft", "updated_at": now}})
        return {"status": "Draft"}

    @router.post("/activation/planning-form/approve")
    async def approve_form(request: Request):
        member = await activation_member(request)
        form = await current_form(member["user_id"])
        if not form or not form.get("content") or form.get("status") not in {"Draft", "Approved"}:
            raise HTTPException(status_code=409, detail="There is no draft form ready to approve")
        now = datetime.now(timezone.utc).isoformat()
        version = form.get("approved_version", 0) + 1
        await db.activation_planning_forms.update_one({"user_id": member["user_id"]}, {"$set": {
            "status": "Approved", "approved_version": version, "approved_at": now, "updated_at": now},
            "$push": {"approved_versions": {"version": version, "content": form["content"], "approved_at": now}}})
        return {"status": "Approved", "approved_version": version}

    # ---------------- FOUNDER: SEND / REMIND ----------------

    async def send_context(user_id: str, record: dict, request: Request, kind: str) -> dict:
        context = await founder_context(user_id)
        form_link = f"{origin_of(request)}/planning-form/{record['form_token']}"
        return build_planning_email(kind, record, context["founder_name"], context["founder_title"], context["organization"], form_link) | {
            "founder_email": context["founder_email"]}

    @router.get("/activation/participants/{participant_id}/email-preview")
    async def email_preview(participant_id: str, request: Request, type: str = "initial"):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        email = await send_context(member["user_id"], record, request, type)
        email.pop("founder_email", None)
        return {"to_name": record["name"], "to_email": record["email"], **email}

    async def deliver_planning_email(user_id: str, record: dict, request: Request, kind: str):
        form = await current_form(user_id)
        if form.get("status") != "Approved" or not form.get("approved_version"):
            raise HTTPException(status_code=409, detail="Approve your Board Fundraising Planning Form before sending it to Board Members")
        email = await send_context(user_id, record, request, kind)
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        message = {
            "from": os.environ["NONPROFIT_SENDER"], "to": [record["email"]],
            "subject": email["subject"],
            "html": email_html(email["body"], email["button_label"], email["form_link"]),
        }
        if email.get("founder_email"):
            message["reply_to"] = [email["founder_email"]]
        try:
            await resend.Emails.send_async(message)
        except Exception as exc:
            logger.exception("Planning form send failed for %s", record["participant_id"])
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc
        now = datetime.now(timezone.utc).isoformat()
        updates = {"last_reminder_at": now} if kind == "reminder" else {"last_sent_at": now}
        if record["status"] == "NOT SENT":
            updates["status"] = "SENT"
        if not record.get("form_version"):
            updates["form_version"] = form["approved_version"]
        await db.activation_participants.update_one({"participant_id": record["participant_id"]}, {"$set": updates})
        return now

    @router.post("/activation/participants/{participant_id}/send")
    async def send_form(participant_id: str, payload: SendRequest, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        if payload.type == "reminder" and record["status"] != "SENT":
            raise HTTPException(status_code=409, detail="Reminders are only available for Board Members who have been sent the form but have not completed it")
        sent_at = await deliver_planning_email(member["user_id"], record, request, payload.type)
        return {"status": "sent", "sent_at": sent_at}

    @router.post("/activation/participants/send-all-unsent")
    async def send_all_unsent(request: Request):
        member = await activation_member(request)
        records = await db.activation_participants.find({"user_id": member["user_id"], "status": "NOT SENT"}, {"_id": 0}).to_list(300)
        sent = 0
        for record in records:
            await deliver_planning_email(member["user_id"], record, request, "initial")
            sent += 1
        return {"status": "sent", "count": sent}

    # ---------------- FOUNDER: CALL SCRIPT / NOTES / RESPONSE ----------------

    @router.get("/activation/participants/{participant_id}/call-script")
    async def call_script(participant_id: str, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        context = await founder_context(member["user_id"])
        first = (record.get("name") or "").split(" ")[0]
        founder_first = context["founder_name"].split(" ")[0] if context["founder_name"] else "me"
        script = (
            f"Hi {first}, it's {founder_first} from {context['organization']}.\n\n"
            "I wanted to quickly follow up on the Fundraising Planning Form I sent you.\n\n"
            "We're building the fundraising plan with the Board rather than creating it first and asking everyone to execute it later.\n\n"
            "I want your ideas and perspective included before we move into building the final strategy.\n\n"
            "If you haven't had a chance to complete it yet, I can resend your link now.\n\n"
            "Is there anything you need from me before you complete it?"
        )
        return {"script": script, "call_notes": record.get("call_notes", ""), "form_status": record["status"]}

    @router.put("/activation/participants/{participant_id}/call-notes")
    async def save_call_notes(participant_id: str, payload: CallNotes, request: Request):
        member = await activation_member(request)
        await owned_participant(member["user_id"], participant_id)
        await db.activation_participants.update_one(
            {"participant_id": participant_id}, {"$set": {"call_notes": payload.notes}})
        return {"status": "saved"}

    @router.get("/activation/participants/{participant_id}/response")
    async def view_response(participant_id: str, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        if record["status"] != "COMPLETED" or not record.get("response"):
            raise HTTPException(status_code=404, detail="This Board Member has not completed their planning form yet")
        return {"participant": public_participant(record), "response": record["response"],
                "submitted_at": record.get("submitted_at", ""), "form_version": record.get("form_version", 0)}

    # ---------------- PUBLIC: BOARD MEMBER FORM ----------------

    async def participant_by_token(token: str) -> dict:
        record = await db.activation_participants.find_one({"form_token": token}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This form link is not valid")
        return record

    async def form_version_content(user_id: str, version: int) -> dict:
        form = await current_form(user_id)
        for entry in form.get("approved_versions", []):
            if entry["version"] == version:
                return entry["content"]
        latest = form.get("approved_versions", [])
        if latest:
            return latest[-1]["content"]
        raise HTTPException(status_code=409, detail="This planning form is not available yet")

    @router.get("/planning-form/{token}")
    async def public_form(token: str):
        record = await participant_by_token(token)
        context = await founder_context(record["user_id"])
        version = record.get("form_version") or 0
        content = await form_version_content(record["user_id"], version)
        return {
            "organization_name": context["organization"],
            "submitted": record["status"] == "COMPLETED",
            "prefill": {"full_name": record.get("name", ""), "email": record.get("email", ""), "role": record.get("role", "")},
            "form": form_payload(content),
        }

    @router.post("/planning-form/{token}", status_code=201)
    async def submit_planning_form(token: str, payload: PlanningSubmission):
        record = await participant_by_token(token)
        if record["status"] == "COMPLETED":
            raise HTTPException(status_code=409, detail="This response has already been submitted")
        if not payload.confirmation:
            raise HTTPException(status_code=422, detail="The confirmation is required")
        now = datetime.now(timezone.utc).isoformat()
        response = payload.model_dump()
        response["email"] = str(payload.email).lower()
        result = await db.activation_participants.update_one(
            {"participant_id": record["participant_id"], "status": {"$ne": "COMPLETED"}},
            {"$set": {"status": "COMPLETED", "response": response, "submitted_at": now,
                      "name": payload.full_name, "email": response["email"],
                      "role": payload.role or record.get("role", "")}},
        )
        context = await founder_context(record["user_id"])
        if result.modified_count:
            try:
                if context["founder_email"]:
                    first = payload.full_name.split(" ")[0]
                    founder_first = context["founder_name"].split(" ")[0] if context["founder_name"] else "there"
                    origin = os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com"
                    view_url = f"{origin}/app/activation/self-guided/module/2?participant={record['participant_id']}"
                    body = (
                        f"Hi {founder_first},\n\n"
                        f"{payload.full_name} has completed their Board Fundraising Planning Form for {context['organization']}.\n\n"
                        "Their ideas are now available in your Board Fundraising Activation workspace and will be included when you build your Fundraising Strategy Plan.\n\n"
                        f"[VIEW {first.upper()}'S RESPONSE]\n\n"
                        "Nonprofit Board Builder"
                    )
                    resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
                    await resend.Emails.send_async({
                        "from": os.environ["NONPROFIT_SENDER"], "to": [context["founder_email"]],
                        "subject": f"Fundraising Planning Response Received | {payload.full_name}",
                        "html": email_html(body, f"VIEW {first.upper()}'S RESPONSE", view_url),
                    })
            except Exception:
                logger.exception("Founder planning notification failed for %s", record["participant_id"])
        return {"status": "submitted", "organization_name": context["organization"]}

    # ---------------- MODULE 3: FUNDRAISING STRATEGY ----------------

    async def current_strategy(user_id: str) -> dict:
        return await db.activation_strategies.find_one({"user_id": user_id}, {"_id": 0}) or {}

    def strategy_summary(strategy: dict) -> dict:
        if not strategy:
            return {"status": "NONE", "review_version": 0}
        return {"status": strategy.get("status", "NONE"), "review_version": strategy.get("review_version", 0),
                "display_text": strategy.get("display_text", ""), "generation_error": strategy.get("generation_error", ""),
                "responses_included": strategy.get("responses_included", []), "updated_at": strategy.get("updated_at", "")}

    def reviewer_row(record: dict) -> dict:
        row = public_participant(record)
        row.update({"review_status": record.get("review_status", "NOT SENT"),
                    "review_position": (record.get("review") or {}).get("position", ""),
                    "review_submitted_at": record.get("review_submitted_at", ""),
                    "last_review_sent_at": record.get("last_review_sent_at", ""),
                    "last_review_reminder_at": record.get("last_review_reminder_at", ""),
                    "review_version": record.get("review_version", 0)})
        return row

    @router.get("/activation/strategy")
    async def strategy_overview(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        participants = await db.activation_participants.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).to_list(300)
        invited = sum(1 for p in participants if p["status"] in {"SENT", "COMPLETED"})
        received = sum(1 for p in participants if p["status"] == "COMPLETED")
        review_invited = sum(1 for p in participants if p.get("review_status") in {"SENT", "REVIEWED"})
        reviews_received = sum(1 for p in participants if p.get("review_status") == "REVIEWED")
        return {
            "strategy": strategy_summary(await current_strategy(user_id)),
            "planning": {"invited": invited, "received": received, "waiting": invited - received, "included": received},
            "reviewers": [reviewer_row(p) for p in participants],
            "review_progress": {"invited": review_invited, "received": reviews_received, "waiting": review_invited - reviews_received},
        }

    @router.post("/activation/strategy/generate")
    async def generate_strategy(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        intake = await activation_intake(user_id)
        if not intake:
            raise HTTPException(status_code=409, detail="Your Activation intake was not found. Complete the Activation intake first.")
        strategy = await current_strategy(user_id)
        if strategy.get("status") == "Generating":
            return {"status": "Generating"}
        context_info = await founder_context(user_id)
        completed = await db.activation_participants.find({"user_id": user_id, "status": "COMPLETED"}, {"_id": 0}).to_list(300)
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_strategies.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "status": "Generating", "generation_error": "", "updated_at": now},
             "$setOnInsert": {"review_version": 0, "review_versions": [], "created_at": now}},
            upsert=True)
        import json as jsonlib
        intake_context = {key: intake.get(key, "") for key in [
            "your_name", "organization_name", "fundraising_goal", "amount_needed", "money_accomplish",
            "current_methods", "written_strategy", "fundraising_calendar", "fundraising_carriers",
            "present_board", "active_board", "board_fundraising_involvement", "board_fundraising_activities",
            "perceived_barriers", "board_skills_relationships", "direction_12_24", "organization_priorities",
            "previous_fundraising_planning", "broader_strategic_planning", "desired_change", "success_definition", "anything_else"]}
        responses_block = [
            {"board_member_name": p["name"], "board_role": p.get("role", "Board Member"), "their_response": p.get("response", {})}
            for p in completed]
        context = ("ORGANIZATION CONTEXT:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"]}, indent=1)
                   + "\n\nFOUNDER ACTIVATION INTAKE:\n" + jsonlib.dumps(intake_context, indent=1, default=str)
                   + "\n\nEVERY COMPLETED BOARD MEMBER PLANNING RESPONSE (preserve who said what):\n" + jsonlib.dumps(responses_block, indent=1, default=str))

        async def run_generation():
            try:
                structured = await generate_structured("activation_fundraising_strategy", context)
                await db.activation_strategies.update_one({"user_id": user_id}, {"$set": {
                    "status": "Draft", "structured": structured,
                    "display_text": strategy_display(structured, context_info["organization"]),
                    "content_source": "generated",
                    "responses_included": [p["participant_id"] for p in completed],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Strategy generation failed for %s: %s", user_id, exc)
                await db.activation_strategies.update_one({"user_id": user_id}, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating"}

    @router.get("/activation/strategy/status")
    async def strategy_status(request: Request):
        member = await activation_member(request)
        return strategy_summary(await current_strategy(member["user_id"]))

    @router.put("/activation/strategy")
    async def edit_strategy(payload: StrategyEditPayload, request: Request):
        member = await activation_member(request)
        strategy = await current_strategy(member["user_id"])
        if not strategy or not strategy.get("display_text"):
            raise HTTPException(status_code=409, detail="Build your Fundraising Strategy Plan first")
        await db.activation_strategies.update_one({"user_id": member["user_id"]}, {"$set": {
            "display_text": payload.display_text, "content_source": "edited", "status": "Draft",
            "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Draft"}

    @router.post("/activation/strategy/approve-review")
    async def approve_strategy_for_review(request: Request):
        member = await activation_member(request)
        strategy = await current_strategy(member["user_id"])
        if not strategy or not strategy.get("display_text") or strategy.get("status") not in {"Draft", "Ready for Board Review"}:
            raise HTTPException(status_code=409, detail="There is no draft strategy ready to approve")
        now = datetime.now(timezone.utc).isoformat()
        version = strategy.get("review_version", 0) + 1
        await db.activation_strategies.update_one({"user_id": member["user_id"]}, {"$set": {
            "status": "Ready for Board Review", "review_version": version, "approved_at": now, "updated_at": now},
            "$push": {"review_versions": {"version": version, "display_text": strategy["display_text"], "approved_at": now,
                                          "responses_included": strategy.get("responses_included", [])}}})
        return {"status": "Ready for Board Review", "review_version": version}

    def build_review_email(kind: str, participant: dict, founder_name: str, founder_title: str, organization: str, review_link: str) -> dict:
        first = (participant.get("name") or "").split(" ")[0]
        signature = founder_name + (f"\n{founder_title}" if founder_title else "") + f"\n{organization}"
        if kind == "reminder":
            subject = "Reminder: Please Review Our Fundraising Strategy Plan"
            body = (
                f"Dear {first},\n\n"
                f"I wanted to follow up on the Fundraising Strategy Plan for {organization}.\n\n"
                "Before we move into adopting the plan, I would like your review included — any suggestions, concerns or issues you believe the Board should discuss.\n\n"
                "If you have not reviewed the plan yet, please use your link below:\n\n"
                "[REVIEW OUR FUNDRAISING STRATEGY PLAN]\n\n"
                f"Thank you for helping us build this together.\n\n{signature}"
            )
        else:
            subject = f"Please Review Our Fundraising Strategy Plan | {organization}"
            body = (
                f"Dear {first},\n\n"
                f"Thank you for contributing your ideas to the fundraising planning process for {organization}.\n\n"
                "We have now brought the Board's input together with the organization's fundraising goals and priorities and developed the Fundraising Strategy Plan for Board review.\n\n"
                "Before we move into adopting the plan, I would like you to review the strategy and share any suggestions, concerns or issues you believe the Board should discuss.\n\n"
                "Please review the plan using your link below:\n\n"
                "[REVIEW OUR FUNDRAISING STRATEGY PLAN]\n\n"
                "Your feedback will help us prepare for the Board discussion where we will work through the strategy and agree on the way forward.\n\n"
                f"Thank you for helping us build this together.\n\n{signature}"
            )
        return {"subject": subject, "body": body, "button_label": "REVIEW OUR FUNDRAISING STRATEGY PLAN", "form_link": review_link}

    async def review_send_context(user_id: str, record: dict, request: Request, kind: str) -> dict:
        context = await founder_context(user_id)
        token = record.get("review_token")
        if not token:
            token = secrets.token_urlsafe(32)
            await db.activation_participants.update_one({"participant_id": record["participant_id"]}, {"$set": {"review_token": token}})
        link = f"{origin_of(request)}/strategy-review/{token}"
        email = build_review_email(kind, record, context["founder_name"], context["founder_title"], context["organization"], link)
        email["founder_email"] = context["founder_email"]
        return email

    @router.get("/activation/reviewers/{participant_id}/email-preview")
    async def review_email_preview(participant_id: str, request: Request, type: str = "initial"):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        email = await review_send_context(member["user_id"], record, request, type)
        email.pop("founder_email", None)
        return {"to_name": record["name"], "to_email": record["email"], **email}

    @router.post("/activation/reviewers/{participant_id}/send")
    async def send_review(participant_id: str, payload: SendRequest, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        strategy = await current_strategy(member["user_id"])
        if strategy.get("status") != "Ready for Board Review" or not strategy.get("review_version"):
            raise HTTPException(status_code=409, detail="Approve your Fundraising Strategy Plan for Board review before sending it")
        review_status = record.get("review_status", "NOT SENT")
        if payload.type == "reminder" and review_status != "SENT":
            raise HTTPException(status_code=409, detail="Reminders are only available for Board Members who have been sent the plan but have not reviewed it")
        email = await review_send_context(member["user_id"], record, request, payload.type)
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        message = {"from": os.environ["NONPROFIT_SENDER"], "to": [record["email"]], "subject": email["subject"],
                   "html": email_html(email["body"], email["button_label"], email["form_link"])}
        if email.get("founder_email"):
            message["reply_to"] = [email["founder_email"]]
        try:
            await resend.Emails.send_async(message)
        except Exception as exc:
            logger.exception("Strategy review send failed for %s", participant_id)
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc
        now = datetime.now(timezone.utc).isoformat()
        updates = {"last_review_reminder_at": now} if payload.type == "reminder" else {"last_review_sent_at": now}
        if review_status == "NOT SENT":
            updates["review_status"] = "SENT"
        if not record.get("review_version"):
            updates["review_version"] = strategy["review_version"]
        await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": updates})
        return {"status": "sent", "sent_at": now}

    @router.get("/activation/reviewers/{participant_id}/review")
    async def view_review(participant_id: str, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        if record.get("review_status") != "REVIEWED" or not record.get("review"):
            raise HTTPException(status_code=404, detail="This Board Member has not reviewed the plan yet")
        return {"participant": reviewer_row(record), "review": record["review"],
                "review_submitted_at": record.get("review_submitted_at", ""), "review_version": record.get("review_version", 0)}

    # ---------------- PUBLIC: STRATEGY REVIEW ----------------

    async def reviewer_by_token(token: str) -> dict:
        record = await db.activation_participants.find_one({"review_token": token}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This review link is not valid")
        return record

    async def review_version_text(user_id: str, version: int) -> str:
        strategy = await current_strategy(user_id)
        for entry in strategy.get("review_versions", []):
            if entry["version"] == version:
                return entry["display_text"]
        versions = strategy.get("review_versions", [])
        if versions:
            return versions[-1]["display_text"]
        raise HTTPException(status_code=409, detail="This strategy plan is not available yet")

    @router.get("/strategy-review/{token}")
    async def public_review(token: str):
        record = await reviewer_by_token(token)
        context = await founder_context(record["user_id"])
        return {"organization_name": context["organization"],
                "submitted": record.get("review_status") == "REVIEWED",
                "reviewer": {"name": record.get("name", ""), "role": record.get("role", "")},
                "strategy_text": await review_version_text(record["user_id"], record.get("review_version") or 0),
                "options": REVIEW_OPTIONS}

    @router.post("/strategy-review/{token}", status_code=201)
    async def submit_review(token: str, payload: ReviewSubmission):
        record = await reviewer_by_token(token)
        if record.get("review_status") == "REVIEWED":
            raise HTTPException(status_code=409, detail="This review has already been submitted")
        if payload.position not in REVIEW_OPTIONS:
            raise HTTPException(status_code=422, detail="Invalid review selection")
        if payload.position != REVIEW_OPTIONS[0] and not payload.discussion_points.strip():
            raise HTTPException(status_code=422, detail="Please share what you would like the Board to discuss before the plan is adopted")
        now = datetime.now(timezone.utc).isoformat()
        review = payload.model_dump()
        result = await db.activation_participants.update_one(
            {"participant_id": record["participant_id"], "review_status": {"$ne": "REVIEWED"}},
            {"$set": {"review_status": "REVIEWED", "review": review, "review_submitted_at": now}})
        context = await founder_context(record["user_id"])
        if result.modified_count:
            try:
                if context["founder_email"]:
                    first = (record.get("name") or "").split(" ")[0]
                    founder_first = context["founder_name"].split(" ")[0] if context["founder_name"] else "there"
                    origin = os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com"
                    view_url = f"{origin}/app/activation/self-guided/module/3?reviewer={record['participant_id']}"
                    body = (
                        f"Hi {founder_first},\n\n"
                        f"{record.get('name', '')} has reviewed the Fundraising Strategy Plan for {context['organization']}.\n\n"
                        f"Their position: {payload.position}\n\n"
                        "Their full review is available in your Board Fundraising Activation workspace and will help you prepare for the adoption discussion.\n\n"
                        f"[VIEW {first.upper()}'S REVIEW]\n\n"
                        "Nonprofit Board Builder"
                    )
                    resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
                    await resend.Emails.send_async({
                        "from": os.environ["NONPROFIT_SENDER"], "to": [context["founder_email"]],
                        "subject": f"Fundraising Strategy Review Received | {record.get('name', '')}",
                        "html": email_html(body, f"VIEW {first.upper()}'S REVIEW", view_url)})
            except Exception:
                logger.exception("Founder review notification failed for %s", record["participant_id"])
        return {"status": "submitted", "organization_name": context["organization"]}

    # ---------------- MODULE 4: PLAN ADOPTION ----------------

    async def current_adoption(user_id: str) -> dict:
        return await db.activation_adoptions.find_one({"user_id": user_id}, {"_id": 0}) or {}

    def module5_ready(adoption: dict) -> bool:
        return bool(adoption.get("conclusion", "").strip()
                    and adoption.get("plan_status") in {"Adopted as Presented", "Adopted With Changes"}
                    and adoption.get("finalized"))

    async def ready_review_text(user_id: str) -> str:
        strategy = await current_strategy(user_id)
        if strategy.get("status") != "Ready for Board Review" or not strategy.get("review_versions"):
            raise HTTPException(status_code=409, detail="Approve your Fundraising Strategy Plan for Board review first")
        return strategy["review_versions"][-1]["display_text"]

    @router.get("/activation/adoption")
    async def adoption_overview(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        strategy = await current_strategy(user_id)
        adoption = await current_adoption(user_id)
        participants = await db.activation_participants.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).to_list(300)
        reviews = [{"name": p["name"], "role": p.get("role", "Board Member"),
                    "position": (p.get("review") or {}).get("position", ""),
                    "discussion_points": (p.get("review") or {}).get("discussion_points", ""),
                    "contribution": (p.get("review") or {}).get("contribution", ""),
                    "support_needs": (p.get("review") or {}).get("support_needs", "")}
                   for p in participants if p.get("review_status") == "REVIEWED"]
        members = []
        for p in participants:
            response = p.get("response") or {}
            members.append({"participant_id": p["participant_id"], "name": p["name"], "role": p.get("role", "Board Member"),
                            "participation_activities": response.get("participation_activities", []),
                            "ownership_interest": response.get("ownership", ""),
                            "support_needed": response.get("support_needed", []),
                            "review_contribution": (p.get("review") or {}).get("contribution", ""),
                            "review_support": (p.get("review") or {}).get("support_needs", ""),
                            "agreed_responsibility": p.get("agreed_responsibility", ""),
                            "responsibility_status": p.get("responsibility_status", "No Fundraising Responsibility Agreed Yet")})
        return {"strategy": strategy_summary(strategy),
                "reviewed_text": (strategy.get("review_versions") or [{}])[-1].get("display_text", "") if strategy else "",
                "reviews": reviews, "adoption": adoption, "members": members,
                "module5_ready": module5_ready(adoption)}

    @router.post("/activation/adoption/guide/generate")
    async def generate_guide(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        reviewed_text = await ready_review_text(user_id)
        adoption = await current_adoption(user_id)
        if adoption.get("guide_status") == "Generating":
            return {"status": "Generating"}
        intake = await activation_intake(user_id)
        context_info = await founder_context(user_id)
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_adoptions.update_one({"user_id": user_id}, {"$set": {
            "user_id": user_id, "guide_status": "Generating", "guide_error": "", "updated_at": now},
            "$setOnInsert": {"created_at": now}}, upsert=True)
        participants = await db.activation_participants.find({"user_id": user_id}, {"_id": 0}).to_list(300)
        import json as jsonlib
        reviews = [{"board_member_name": p["name"], "board_role": p.get("role", ""), "review": p.get("review", {})}
                   for p in participants if p.get("review_status") == "REVIEWED"]
        willingness = [{"board_member_name": p["name"], "board_role": p.get("role", ""),
                        "planning_response": p.get("response", {})} for p in participants if p.get("response")]
        context = ("ORGANIZATION:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"],
                                                       "founder_name": context_info["founder_name"]}, indent=1)
                   + "\n\nFUNDRAISING STRATEGY PLAN APPROVED FOR BOARD REVIEW:\n" + reviewed_text
                   + "\n\nACTUAL BOARD REVIEWS OF THIS PLAN:\n" + jsonlib.dumps(reviews, indent=1, default=str)
                   + "\n\nBOARD MEMBER PLANNING RESPONSES (willingness/ownership context):\n" + jsonlib.dumps(willingness, indent=1, default=str)
                   + "\n\nACTIVATION INTAKE HIGHLIGHTS:\n" + jsonlib.dumps({key: intake.get(key, "") for key in [
                       "fundraising_goal", "amount_needed", "money_accomplish", "organization_priorities",
                       "desired_change", "success_definition"]}, indent=1, default=str))

        async def run_generation():
            try:
                structured = await generate_structured("activation_facilitation_guide", context)
                await db.activation_adoptions.update_one({"user_id": user_id}, {"$set": {
                    "guide_status": "Draft", "guide_text": guide_display(structured, context_info["organization"]),
                    "updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Facilitation guide generation failed for %s: %s", user_id, exc)
                await db.activation_adoptions.update_one({"user_id": user_id}, {"$set": {
                    "guide_status": "Failed", "guide_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating"}

    @router.get("/activation/adoption/status")
    async def adoption_status(request: Request):
        member = await activation_member(request)
        adoption = await current_adoption(member["user_id"])
        return {"guide_status": adoption.get("guide_status", "NONE"), "toolkit_gate": module5_ready(adoption)}

    @router.put("/activation/adoption/guide")
    async def edit_guide(payload: TextPayload, request: Request):
        member = await activation_member(request)
        adoption = await current_adoption(member["user_id"])
        if not adoption.get("guide_text"):
            raise HTTPException(status_code=409, detail="Generate your Facilitation Guide first")
        await db.activation_adoptions.update_one({"user_id": member["user_id"]}, {"$set": {
            "guide_text": payload.text, "guide_status": "Draft", "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Draft"}

    @router.post("/activation/adoption/guide/approve")
    async def approve_guide(request: Request):
        member = await activation_member(request)
        adoption = await current_adoption(member["user_id"])
        if adoption.get("guide_status") not in {"Draft", "Approved"} or not adoption.get("guide_text"):
            raise HTTPException(status_code=409, detail="There is no draft guide ready to approve")
        await db.activation_adoptions.update_one({"user_id": member["user_id"]}, {"$set": {
            "guide_status": "Approved", "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Approved"}

    @router.get("/activation/adoption/guide/pdf")
    async def guide_pdf(request: Request):
        member = await activation_member(request)
        adoption = await current_adoption(member["user_id"])
        if not adoption.get("guide_text"):
            raise HTTPException(status_code=404, detail="No guide available")
        context = await founder_context(member["user_id"])
        issuer = {"issued_by": context["founder_name"], "issuer_title": context["founder_title"],
                  "organization": context["organization"], "issue_date": datetime.now(timezone.utc).strftime("%B %d, %Y")}
        return build_portfolio_pdf("Plan Adoption Facilitation Guide", "", issuer, adoption["guide_text"])

    @router.put("/activation/adoption/conclusion")
    async def save_conclusion(payload: TextPayload, request: Request):
        member = await activation_member(request)
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_adoptions.update_one({"user_id": member["user_id"]}, {"$set": {
            "user_id": member["user_id"], "conclusion": payload.text, "updated_at": now},
            "$setOnInsert": {"created_at": now}}, upsert=True)
        return {"status": "saved"}

    @router.put("/activation/adoption/plan-status")
    async def set_plan_status(payload: PlanStatusPayload, request: Request):
        member = await activation_member(request)
        if payload.status not in PLAN_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid plan status")
        user_id = member["user_id"]
        now = datetime.now(timezone.utc).isoformat()
        updates = {"user_id": user_id, "plan_status": payload.status, "updated_at": now}
        if payload.status == "Adopted as Presented":
            updates.update({"adopted_text": await ready_review_text(user_id), "finalized": True, "adopted_at": now})
        elif payload.status == "Adopted With Changes":
            adoption = await current_adoption(user_id)
            updates["finalized"] = False
            if not adoption.get("draft_adopted_text"):
                updates["draft_adopted_text"] = await ready_review_text(user_id)
        else:
            updates["finalized"] = False
        await db.activation_adoptions.update_one({"user_id": user_id}, {"$set": updates, "$setOnInsert": {"created_at": now}}, upsert=True)
        return {"status": payload.status, "module5_ready": module5_ready(await current_adoption(user_id))}

    @router.put("/activation/adoption/adopted-plan")
    async def edit_adopted_plan(payload: TextPayload, request: Request):
        member = await activation_member(request)
        adoption = await current_adoption(member["user_id"])
        if adoption.get("plan_status") != "Adopted With Changes":
            raise HTTPException(status_code=409, detail="Manual strategy edits are available when the plan status is Adopted With Changes")
        await db.activation_adoptions.update_one({"user_id": member["user_id"]}, {"$set": {
            "draft_adopted_text": payload.text, "finalized": False, "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "saved"}

    @router.post("/activation/adoption/finalize")
    async def finalize_adopted_plan(request: Request):
        member = await activation_member(request)
        adoption = await current_adoption(member["user_id"])
        if adoption.get("plan_status") != "Adopted With Changes" or not adoption.get("draft_adopted_text"):
            raise HTTPException(status_code=409, detail="There is no edited plan to finalize")
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_adoptions.update_one({"user_id": member["user_id"]}, {"$set": {
            "adopted_text": adoption["draft_adopted_text"], "finalized": True, "adopted_at": now, "updated_at": now}})
        return {"status": "finalized"}

    @router.put("/activation/participants/{participant_id}/responsibility")
    async def save_responsibility(participant_id: str, payload: ResponsibilityPayload, request: Request):
        member = await activation_member(request)
        await owned_participant(member["user_id"], participant_id)
        if payload.responsibility_status not in RESPONSIBILITY_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid responsibility status")
        await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": {
            "agreed_responsibility": payload.agreed_responsibility, "responsibility_status": payload.responsibility_status}})
        return {"status": "saved"}

    # ---------------- MODULE 5: EXECUTION TOOLKIT ----------------

    async def current_toolkit(user_id: str) -> dict:
        return await db.activation_toolkits.find_one({"user_id": user_id}, {"_id": 0}) or {}

    @router.get("/activation/toolkit")
    async def toolkit_overview(request: Request):
        member = await activation_member(request)
        adoption = await current_adoption(member["user_id"])
        toolkit = await current_toolkit(member["user_id"])
        return {"gate_open": module5_ready(adoption), "plan_status": adoption.get("plan_status", ""),
                "toolkit": {"status": toolkit.get("status", "NONE"), "display_text": toolkit.get("display_text", ""),
                            "generation_error": toolkit.get("generation_error", "")}}

    @router.post("/activation/toolkit/generate")
    async def generate_toolkit(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        adoption = await current_adoption(user_id)
        if not module5_ready(adoption):
            raise HTTPException(status_code=409, detail="The Fundraising Strategy Plan must be adopted and finalized before execution tools are generated")
        toolkit = await current_toolkit(user_id)
        if toolkit.get("status") == "Generating":
            return {"status": "Generating"}
        intake = await activation_intake(user_id)
        context_info = await founder_context(user_id)
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_toolkits.update_one({"user_id": user_id}, {"$set": {
            "user_id": user_id, "status": "Generating", "generation_error": "", "updated_at": now},
            "$setOnInsert": {"created_at": now}}, upsert=True)
        participants = await db.activation_participants.find({"user_id": user_id}, {"_id": 0}).to_list(300)
        import json as jsonlib
        responsibilities = [{"board_member_name": p["name"], "board_role": p.get("role", ""),
                             "agreed_responsibility": p.get("agreed_responsibility", ""),
                             "responsibility_status": p.get("responsibility_status", "")} for p in participants]
        context = ("ORGANIZATION:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"]}, indent=1)
                   + "\n\nFINAL ADOPTED FUNDRAISING STRATEGY PLAN:\n" + adoption.get("adopted_text", "")
                   + "\n\nPLAN ADOPTION CONCLUSION (founder's own words):\n" + adoption.get("conclusion", "")
                   + "\n\nAGREED BOARD MEMBER RESPONSIBILITIES:\n" + jsonlib.dumps(responsibilities, indent=1, default=str)
                   + "\n\nINTAKE HIGHLIGHTS:\n" + jsonlib.dumps({key: intake.get(key, "") for key in [
                       "fundraising_goal", "amount_needed", "money_accomplish"]}, indent=1, default=str))

        async def run_generation():
            try:
                structured = await generate_structured("activation_execution_toolkit", context)
                await db.activation_toolkits.update_one({"user_id": user_id}, {"$set": {
                    "status": "Draft", "structured": structured,
                    "display_text": toolkit_display(structured, context_info["organization"]),
                    "updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Toolkit generation failed for %s: %s", user_id, exc)
                await db.activation_toolkits.update_one({"user_id": user_id}, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating"}

    @router.put("/activation/toolkit")
    async def edit_toolkit(payload: TextPayload, request: Request):
        member = await activation_member(request)
        toolkit = await current_toolkit(member["user_id"])
        if not toolkit.get("display_text"):
            raise HTTPException(status_code=409, detail="Generate your Execution Toolkit first")
        await db.activation_toolkits.update_one({"user_id": member["user_id"]}, {"$set": {
            "display_text": payload.text, "status": "Draft", "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Draft"}

    @router.post("/activation/toolkit/approve")
    async def approve_toolkit(request: Request):
        member = await activation_member(request)
        toolkit = await current_toolkit(member["user_id"])
        if toolkit.get("status") not in {"Draft", "Approved"} or not toolkit.get("display_text"):
            raise HTTPException(status_code=409, detail="There is no draft toolkit ready to approve")
        await db.activation_toolkits.update_one({"user_id": member["user_id"]}, {"$set": {
            "status": "Approved", "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Approved"}

    @router.get("/activation/toolkit/pdf")
    async def toolkit_pdf(request: Request):
        member = await activation_member(request)
        toolkit = await current_toolkit(member["user_id"])
        if not toolkit.get("display_text"):
            raise HTTPException(status_code=404, detail="No toolkit available")
        context = await founder_context(member["user_id"])
        issuer = {"issued_by": context["founder_name"], "issuer_title": context["founder_title"],
                  "organization": context["organization"], "issue_date": datetime.now(timezone.utc).strftime("%B %d, %Y")}
        return build_portfolio_pdf("Board Fundraising Execution Toolkit", "", issuer, toolkit["display_text"])

    # ---------------- MY FUNDRAISING BOARD + FUNDRAISING PORTFOLIO ----------------

    FP_SECTIONS = [
        ("Your Role in Our Fundraising Plan", "your_role"), ("Why Your Role Matters", "why_role_matters"),
        ("What You Will Help Us Accomplish", "what_you_accomplish"), ("Your Fundraising Responsibilities", "your_responsibilities"),
        ("Who You Will Help Us Reach", "who_you_reach"), ("How You Will Help Build Relationships", "build_relationships"),
        ("Tools You Can Use", "tools_you_can_use"), ("Your Immediate Priorities", "immediate_priorities"),
        ("Your First 90 Days", "first_90_days"), ("Support and Resources", "support_resources"),
        ("How We Will Work Together", "work_together"), ("Moving the Mission Forward", "moving_mission"),
    ]

    def fp_display(structured: dict, member_name: str) -> str:
        lines = ["FUNDRAISING PORTFOLIO", member_name, ""]
        for heading, key in FP_SECTIONS:
            value = str(structured.get(key, "") or "").strip()
            if value:
                lines.extend([heading.upper(), value, ""])
        return "\n".join(lines).strip()

    def fp_row(record: dict) -> dict:
        return {"fp_status": record.get("fp_status", "NONE"), "fp_text": record.get("fp_text", ""),
                "fp_version": record.get("fp_version", 0), "fp_sent_at": record.get("fp_sent_at", ""),
                "fp_sent_version": record.get("fp_sent_version", 0), "fp_error": record.get("fp_error", "")}

    @router.get("/activation/my-board")
    async def my_fundraising_board(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        adoption = await current_adoption(user_id)
        toolkit = await current_toolkit(user_id)
        participants = await db.activation_participants.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).to_list(300)
        members = [{**public_participant(p), **fp_row(p),
                    "agreed_responsibility": p.get("agreed_responsibility", ""),
                    "responsibility_status": p.get("responsibility_status", "No Fundraising Responsibility Agreed Yet")}
                   for p in participants]
        return {"ready": module5_ready(adoption) and toolkit.get("status") == "Approved",
                "plan_status": adoption.get("plan_status", ""),
                "counts": {"participating": len(participants),
                           "responsibility_agreed": sum(1 for m in members if m["responsibility_status"] == "Responsibility Agreed"),
                           "follow_up_needed": sum(1 for m in members if m["responsibility_status"] == "Follow-Up Needed"),
                           "portfolios_approved": sum(1 for m in members if m["fp_status"] in {"Approved", "SENT"}),
                           "portfolios_sent": sum(1 for m in members if m["fp_status"] == "SENT")},
                "adopted_strategy": adoption.get("adopted_text", ""),
                "toolkit_text": toolkit.get("display_text", "") if toolkit.get("status") == "Approved" else "",
                "members": members}

    @router.post("/activation/members/{participant_id}/portfolio/generate")
    async def generate_fundraising_portfolio(participant_id: str, request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        record = await owned_participant(user_id, participant_id)
        adoption = await current_adoption(user_id)
        if not module5_ready(adoption):
            raise HTTPException(status_code=409, detail="The Fundraising Strategy Plan must be adopted before Fundraising Portfolios are generated")
        if record.get("responsibility_status") != "Responsibility Agreed" or not record.get("agreed_responsibility", "").strip():
            raise HTTPException(status_code=409, detail="Clarify and record this Board Member's agreed fundraising responsibility before generating their Fundraising Portfolio")
        if record.get("fp_status") == "Generating":
            return {"status": "Generating"}
        context_info = await founder_context(user_id)
        toolkit = await current_toolkit(user_id)
        intake = await activation_intake(user_id)
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": {"fp_status": "Generating", "fp_error": ""}})
        import json as jsonlib
        context = ("ORGANIZATION:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"],
                                                       "direction": intake.get("direction_12_24", "")}, indent=1)
                   + f"\n\nBOARD MEMBER: {record['name']} — Board Role: {record.get('role', 'Board Member')}"
                   + f"\n\nEXACT AGREED FUNDRAISING RESPONSIBILITY (highest authority):\n{record['agreed_responsibility']}"
                   + "\n\nFINAL ADOPTED FUNDRAISING STRATEGY PLAN:\n" + adoption.get("adopted_text", "")
                   + "\n\nPLAN ADOPTION CONCLUSION:\n" + adoption.get("conclusion", "")
                   + "\n\nTHIS MEMBER'S OWN PLANNING RESPONSE:\n" + jsonlib.dumps(record.get("response", {}), indent=1, default=str)
                   + "\n\nTHIS MEMBER'S OWN STRATEGY REVIEW:\n" + jsonlib.dumps(record.get("review", {}), indent=1, default=str)
                   + "\n\nAPPROVED EXECUTION TOOLKIT TOOL TITLES (reference by name only):\n"
                   + "\n".join(f"- {tool.get('title', '')}" for key in ["email_tools", "text_tools", "call_scripts", "stewardship_tools"]
                               for tool in (toolkit.get("structured", {}) or {}).get(key, [])))

        async def run_generation():
            try:
                structured = await generate_structured("activation_fundraising_portfolio", context)
                await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": {
                    "fp_status": "Draft", "fp_text": fp_display(structured, record["name"]), "fp_updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Fundraising portfolio generation failed for %s: %s", participant_id, exc)
                await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": {
                    "fp_status": "Failed", "fp_error": str(exc)[:300]}})

        asyncio.create_task(run_generation())
        return {"status": "Generating", "started_at": now}

    @router.get("/activation/members/{participant_id}/portfolio")
    async def get_fundraising_portfolio(participant_id: str, request: Request):
        member = await activation_member(request)
        return fp_row(await owned_participant(member["user_id"], participant_id))

    @router.put("/activation/members/{participant_id}/portfolio")
    async def edit_fundraising_portfolio(participant_id: str, payload: TextPayload, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        if not record.get("fp_text"):
            raise HTTPException(status_code=409, detail="Generate this Fundraising Portfolio first")
        await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": {"fp_text": payload.text, "fp_status": "Draft"}})
        return {"status": "Draft"}

    @router.post("/activation/members/{participant_id}/portfolio/approve")
    async def approve_fundraising_portfolio(participant_id: str, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        if record.get("fp_status") not in {"Draft", "Approved", "SENT"} or not record.get("fp_text"):
            raise HTTPException(status_code=409, detail="There is no draft portfolio ready to approve")
        updates = {"fp_status": "Approved", "fp_version": record.get("fp_version", 0) + 1,
                   "fp_approved_text": record["fp_text"], "fp_approved_at": datetime.now(timezone.utc).isoformat()}
        if not record.get("fp_share_token"):
            updates["fp_share_token"] = secrets.token_urlsafe(32)
        await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": updates})
        return {"status": "Approved", "fp_version": updates["fp_version"]}

    async def fp_issuer(user_id: str) -> dict:
        context = await founder_context(user_id)
        return {"issued_by": context["founder_name"], "issuer_title": context["founder_title"],
                "organization": context["organization"], "issue_date": datetime.now(timezone.utc).strftime("%B %d, %Y")}

    @router.get("/activation/members/{participant_id}/portfolio/pdf")
    async def fundraising_portfolio_pdf(participant_id: str, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        text = record.get("fp_approved_text") or record.get("fp_text")
        if not text:
            raise HTTPException(status_code=404, detail="No portfolio available")
        return build_portfolio_pdf("Fundraising Portfolio", record["name"], await fp_issuer(member["user_id"]), text)

    @router.get("/activation/members/{participant_id}/portfolio/email-preview")
    async def fp_email_preview(participant_id: str, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        if record.get("fp_status") not in {"Approved", "SENT"} or not record.get("fp_share_token"):
            raise HTTPException(status_code=409, detail="Approve this Fundraising Portfolio before preparing its email")
        context = await founder_context(member["user_id"])
        first = (record.get("name") or "").split(" ")[0]
        link = f"{origin_of(request)}/fundraising-portfolio/{record['fp_share_token']}"
        signature = context["founder_name"] + (f"\n{context['founder_title']}" if context["founder_title"] else "") + f"\n{context['organization']}"
        body = (
            f"Dear {first},\n\n"
            f"Thank you for helping us build and adopt the fundraising plan for {context['organization']}.\n\n"
            "Based on the responsibilities we agreed on, I have prepared your individual Fundraising Portfolio.\n\n"
            "It shows where you fit in the fundraising strategy, what you will help us accomplish, the responsibilities you agreed to carry and the tools available to help you begin taking action.\n\n"
            "Please review your Fundraising Portfolio here:\n\n"
            "[VIEW MY FUNDRAISING PORTFOLIO]\n\n"
            f"Thank you for taking ownership of your part of the plan and helping us move the mission forward.\n\n{signature}"
        )
        return {"to_name": record["name"], "to_email": record["email"],
                "subject": f"Your Fundraising Portfolio | {context['organization']}",
                "body": body, "button_label": "VIEW MY FUNDRAISING PORTFOLIO", "form_link": link}

    @router.post("/activation/members/{participant_id}/portfolio/send")
    async def send_fundraising_portfolio(participant_id: str, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        if record.get("fp_status") not in {"Approved", "SENT"}:
            raise HTTPException(status_code=409, detail="Approve this Fundraising Portfolio before sending it")
        email = await fp_email_preview(participant_id, request)
        context = await founder_context(member["user_id"])
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        message = {"from": os.environ["NONPROFIT_SENDER"], "to": [record["email"]], "subject": email["subject"],
                   "html": email_html(email["body"], email["button_label"], email["form_link"])}
        if context["founder_email"]:
            message["reply_to"] = [context["founder_email"]]
        try:
            await resend.Emails.send_async(message)
        except Exception as exc:
            logger.exception("Fundraising portfolio send failed for %s", participant_id)
            raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": {
            "fp_status": "SENT", "fp_sent_at": now, "fp_sent_version": record.get("fp_version", 1)}})
        return {"status": "sent", "sent_at": now}

    @router.get("/fundraising-portfolio/{token}")
    async def public_fundraising_portfolio(token: str):
        record = await db.activation_participants.find_one({"fp_share_token": token}, {"_id": 0})
        if not record or record.get("fp_status") not in {"Approved", "SENT"} or not record.get("fp_approved_text"):
            raise HTTPException(status_code=404, detail="This portfolio link is not valid")
        issuer = await fp_issuer(record["user_id"])
        return {"member_name": record["name"], "organization_name": issuer["organization"],
                "issued_by": issuer["issued_by"], "issuer_title": issuer["issuer_title"],
                "text": record["fp_approved_text"]}

    @router.get("/fundraising-portfolio/{token}/pdf")
    async def public_fundraising_portfolio_pdf(token: str):
        record = await db.activation_participants.find_one({"fp_share_token": token}, {"_id": 0})
        if not record or record.get("fp_status") not in {"Approved", "SENT"} or not record.get("fp_approved_text"):
            raise HTTPException(status_code=404, detail="This portfolio link is not valid")
        return build_portfolio_pdf("Fundraising Portfolio", record["name"], await fp_issuer(record["user_id"]), record["fp_approved_text"])

    return router
