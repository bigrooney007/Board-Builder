import asyncio
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
from content_templates import (activation_adoption_meeting_email, activation_planning_email,
                               activation_review_email, activation_signature)
from reactivation_routes import build_portfolio_pdf, email_html, origin_of

logger = logging.getLogger(__name__)

PRIORITY_OPTIONS = ["Individual Donors", "Major Donors / Philanthropists", "Businesses / Corporate Partnerships & Sponsorships", "Foundations / Grants", "Fundraising Events", "Community / Faith-Based Giving", "Digital / Online Fundraising", "Other"]
PARTICIPATION_OPTIONS = ["Helping identify potential supporters", "Making introductions where I have an appropriate relationship", "Helping build relationships with potential supporters", "Participating in meetings with prospective supporters", "Supporting business / corporate partnership conversations", "Helping identify foundation or grant opportunities", "Reviewing fundraising proposals, messages or materials", "Sharing the organization's work within my networks", "Speaking about the organization and its mission", "Supporting fundraising events", "Helping thank and steward supporters", "Helping plan or coordinate fundraising activity", "I would like more information or training before deciding", "Other"]
GREATER_RESPONSIBILITY_OPTIONS = ["Yes", "I would like to discuss this", "Not at this time"]

FORM_SECTIONS = [
    {"key": "who", "title": "Who Should We Build Fundraising Relationships With?", "questions": [
        {"id": "individuals_supporters", "type": "long", "required": True},
        {"id": "business_supporters", "type": "long", "required": True},
        {"id": "foundation_supporters", "type": "long", "required": True},
    ]},
    {"key": "reach", "title": "Where Can We Find and Reach Them?", "questions": [
        {"id": "where_to_find", "type": "long", "required": True},
    ]},
    {"key": "understanding", "title": "What Should They Understand About Our Work?", "questions": [
        {"id": "what_to_understand", "type": "long", "required": True},
    ]},
    {"key": "attract", "title": "How Should We Attract and Engage Them?", "questions": [
        {"id": "attract_engage", "type": "long", "required": True},
        {"id": "build_trust", "type": "long", "required": True},
    ]},
    {"key": "existing", "title": "Relationships and Opportunities Already Around You", "questions": [
        {"id": "existing_relationships", "type": "long", "required": False},
    ]},
    {"key": "priorities", "title": "Priority Fundraising Opportunities", "questions": [
        {"id": "priority_opportunities", "type": "multi", "options": PRIORITY_OPTIONS, "required": True, "max_selections": 3},
        {"id": "priorities_explanation", "type": "long", "required": False},
    ]},
    {"key": "participation", "title": "How You May Be Willing to Participate", "questions": [
        {"id": "participation_willingness", "type": "multi", "options": PARTICIPATION_OPTIONS, "required": True},
    ]},
    {"key": "greater", "title": "Greater Responsibility — Initial Willingness Only", "questions": [
        {"id": "greater_responsibility_interest", "type": "select", "options": GREATER_RESPONSIBILITY_OPTIONS, "required": True},
        {"id": "greater_responsibility_detail", "type": "long", "required": False, "show_if": {"greater_responsibility_interest": "Yes"}},
    ]},
    {"key": "support", "title": "Support Needed", "questions": [
        {"id": "support_needed", "type": "long", "required": True},
    ]},
    {"key": "first", "title": "What Should Happen First?", "questions": [
        {"id": "first_moves", "type": "long", "required": True},
    ]},
    {"key": "final", "title": "Final Optional Input", "questions": [
        {"id": "final_thoughts", "type": "long", "required": False},
    ]},
]

QUESTION_META = {q["id"]: q for section in FORM_SECTIONS for q in section["questions"]}
REQUIRED_QUESTION_IDS = [qid for qid, q in QUESTION_META.items() if q["required"]]

HELPER_TEXT = {
    "individuals_supporters": "Think about people whose experiences, professions, interests, values, community connections or personal stories may naturally connect them to our work. You may include specific names if you genuinely know someone we should consider, but names are not required.",
    "business_supporters": "Think about businesses that serve the same community, benefit when the people we serve succeed, have relevant community or social-impact priorities, or would find genuine value in being connected to this work.",
    "foundation_supporters": "You may think about the causes they fund, communities they support, locations they serve or types of programs they typically invest in. Include specific names only if you actually know them.",
    "where_to_find": "Think about professional associations, community groups, events, conferences, faith communities, business networks, online communities, local institutions, partnerships, referrals or other places where these potential supporters already gather or engage.",
    "what_to_understand": "What would help someone understand why this mission matters and why supporting it is worthwhile?",
    "attract_engage": "Examples may include useful information, reports, community events, educational resources, volunteer opportunities, webinars, stories, introductions, partnerships, special invitations or other valuable ways of engaging people. These are examples only.",
    "build_trust": "Think about the steps between someone first hearing about us and becoming ready for a funding conversation.",
    "existing_relationships": "If yes, tell us who or what they are and, where relevant, whether you know them directly, have an indirect connection, or simply believe they would be a strong prospect. Listing a relationship here does NOT commit you to making an introduction. It simply helps us understand the opportunities and relationships that may already exist around the Board.",
    "priority_opportunities": "Select up to 3.",
    "participation_willingness": "This is an expression of current willingness. It is not your final fundraising assignment.",
}

RELATIONSHIP_NOTE = "Listing a relationship here does NOT commit you to making an introduction. It simply helps us understand the opportunities and relationships that may already exist around the Board."
CONFIRMATION_TEXT = "I understand that my responses are part of the Board's fundraising planning process and may be combined with ideas from other Board Members to help develop the organization's Fundraising Strategy Plan."


def default_prompts(organization: str) -> Dict[str, str]:
    return {
        "individuals_supporters": f"Based on what you know about {organization} and the people we serve, what kinds of INDIVIDUALS do you believe would have the strongest reason to care about and financially support our mission?",
        "business_supporters": f"What kinds of BUSINESSES or companies do you believe would have a strong reason to support or partner with {organization}, and why?",
        "foundation_supporters": "What kinds of FOUNDATIONS, GRANTMAKERS or philanthropic organizations do you believe may be a strong fit for our work?",
        "where_to_find": "Where do you believe we can realistically find, meet or become visible to the kinds of individuals, businesses and grantors you identified?",
        "what_to_understand": f"What do you believe potential supporters most need to understand about {organization}, the people we serve and the difference this work can make?",
        "attract_engage": f"What could {organization} do or offer that would make potential supporters want to learn more about us and stay connected before we ask them for financial support?",
        "build_trust": f"Once someone becomes aware of {organization}, what do you believe is the best way for us to build enough relationship and trust with them before making a funding ask?",
        "existing_relationships": f"Are there any individuals, businesses, foundations, professional groups, community organizations or other relationships you believe {organization} should consider as part of this fundraising strategy?",
        "priority_opportunities": f"Which fundraising opportunities do you believe {organization} should prioritize first?",
        "priorities_explanation": "Optional — Is there anything you would like to explain about the priorities you selected?",
        "participation_willingness": "As we eventually begin executing the fundraising strategy, which kinds of fundraising support would you currently feel most comfortable helping with?",
        "greater_responsibility_interest": "Is there one area of fundraising or resource development that you would be open to DISCUSSING taking greater responsibility for as the Board begins executing the plan?",
        "greater_responsibility_detail": "What area would you be interested in discussing, and what kind of contribution do you believe you could realistically make?",
        "support_needed": f"What information, tools, materials, training or support would help you feel prepared to participate effectively in fundraising for {organization}?",
        "first_moves": "Once our fundraising strategy is agreed, what do you believe are the first 2-3 things we should focus on to begin moving it forward?",
        "final_thoughts": f"Is there anything else you believe we should consider as we build the fundraising strategy for {organization}?",
    }


def form_payload(content: dict, organization: str = "") -> dict:
    prompts = content.get("question_prompts", {})
    defaults = default_prompts(organization or "our organization")
    return {
        "title": "Board Fundraising Planning Form",
        "introduction": content.get("introduction", ""),
        "goal_context": content.get("goal_context", ""),
        "relationship_note": RELATIONSHIP_NOTE,
        "confirmation_text": CONFIRMATION_TEXT,
        "sections": [
            {"key": section["key"], "title": section["title"], "questions": [
                {"id": q["id"], "type": q["type"], "required": q["required"],
                 "options": q.get("options", []), "max_selections": q.get("max_selections", 0),
                 "show_if": q.get("show_if", {}), "helper": HELPER_TEXT.get(q["id"], ""),
                 "prompt": prompts.get(q["id"]) or defaults.get(q["id"], "")}
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
    individuals_supporters: str = Field(min_length=1)
    business_supporters: str = Field(min_length=1)
    foundation_supporters: str = Field(min_length=1)
    where_to_find: str = Field(min_length=1)
    what_to_understand: str = Field(min_length=1)
    attract_engage: str = Field(min_length=1)
    build_trust: str = Field(min_length=1)
    existing_relationships: str = ""
    priority_opportunities: List[str] = Field(min_length=1, max_length=3)
    priorities_explanation: str = ""
    participation_willingness: List[str] = Field(min_length=1)
    greater_responsibility_interest: str = Field(min_length=1)
    greater_responsibility_detail: str = ""
    support_needed: str = Field(min_length=1)
    first_moves: str = Field(min_length=1)
    final_thoughts: str = ""
    confirmation: bool


def build_planning_email(kind: str, participant: dict, founder_name: str, founder_title: str, organization: str, form_link: str, goal_line: str = "", deadline: str = "") -> dict:
    first = (participant.get("name") or "").split(" ")[0] or "Board Member"
    signature = founder_name + (f"\n{founder_title}" if founder_title else "") + f"\n{organization}"
    deadline_line = f"Please complete the form by {deadline}.\n\n" if deadline else ""
    if kind == "reminder":
        subject = f"Reminder: Your Input on Our Fundraising Plan | {organization}"
        body = (
            f"Dear {first},\n\n"
            f"I wanted to follow up on the Board Fundraising Planning Form I sent you for {organization}.\n\n"
            "We are bringing the Board's ideas together to build our Fundraising Strategy Plan, and I would like to make sure your perspective is included before we move forward.\n\n"
            "You can complete your form using your secure link below:\n\n"
            "[COMPLETE MY FUNDRAISING PLANNING FORM]\n\n"
            + (f"Please complete it by {deadline}.\n\n" if deadline else "")
            + "The form is simply asking for your ideas, perspective and the ways you may be comfortable supporting the fundraising work. It does not assign you a final fundraising responsibility.\n\n"
            f"Thank you for taking the time to contribute to the process.\n\n{signature}"
        )
    else:
        subject = f"Your Input on Our Fundraising Plan | {organization}"
        goal_paragraph = f"{goal_line}\n\n" if goal_line else ""
        body = (
            f"Dear {first},\n\n"
            f"We are beginning the process of building the fundraising strategy for {organization}, and I want the Board involved in shaping it from the beginning.\n\n"
            f"{goal_paragraph}"
            "Rather than creating the plan and bringing it to the Board after the fact, I want us to build it together.\n\n"
            "I am asking you to complete the short Board Fundraising Planning Form below. Your ideas, experience, relationships and perspective will help us think through:\n\n"
            "- who we should be building fundraising relationships with;\n"
            "- where those potential supporters can be found;\n"
            "- how we can attract and engage them;\n"
            "- which fundraising opportunities we should prioritize;\n"
            "- and how the Board may be able to support the work.\n\n"
            "[COMPLETE MY FUNDRAISING PLANNING FORM]\n\n"
            "There are no right or wrong answers. This form is about gathering your thinking before the strategy is built. Your responses do not assign you a final fundraising responsibility.\n\n"
            "Once the responses are collected, they will be brought together with the organization's fundraising goals and priorities to develop the Fundraising Strategy Plan. The plan will then come back to the Board for us to review together before we adopt it and agree how we will execute it.\n\n"
            f"{deadline_line}"
            f"Thank you for taking the time to contribute your ideas and help us build this together.\n\n{signature}"
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


def execution_horizon(money_needed_by: str) -> str:
    text = (money_needed_by or "").lower()
    if not text.strip():
        return ""
    for token, horizon in [("30 day", "60 DAYS"), ("45 day", "60 DAYS"), ("60 day", "60 DAYS"), ("1 month", "60 DAYS"),
                           ("2 month", "60 DAYS"), ("90 day", "90 DAYS"), ("3 month", "90 DAYS"), ("120 day", "120 DAYS"),
                           ("4 month", "120 DAYS"), ("5 month", "120 DAYS"), ("6 month", "120 DAYS"), ("12 month", "120 DAYS"), ("year", "120 DAYS")]:
        if token in text:
            return horizon
    return ""


def _sd_block(lines: list, heading: str, value) -> None:
    if value is None or value == "" or value == []:
        return
    lines.append(heading.upper())
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                for key, sub in item.items():
                    label = key.replace("_", " ").title()
                    if isinstance(sub, list):
                        if sub:
                            lines.append(f"{label}:")
                            lines.extend([f"  - {entry}" for entry in sub if entry])
                    elif sub:
                        lines.append(f"{label}: {sub}")
                lines.append("")
            elif item:
                lines.append(f"- {item}")
    elif isinstance(value, dict):
        for key, sub in value.items():
            label = key.replace("_", " ").title()
            if isinstance(sub, list):
                if sub:
                    lines.append(f"{label}:")
                    lines.extend([f"  - {entry}" for entry in sub if entry])
            elif sub:
                lines.append(f"{label}:")
                lines.append(str(sub))
    else:
        lines.append(str(value))
    lines.append("")


def strategy_display(structured: dict, organization: str) -> str:
    if "ideal_funding_audiences" not in structured:
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
    lines = ["FUNDRAISING STRATEGY PLAN", organization, "FOR BOARD REVIEW", ""]
    _sd_block(lines, "1. Executive Summary", structured.get("executive_summary", ""))
    goal = structured.get("fundraising_goal") or {}
    goal_block = {}
    for key, label in [("amount", "amount_we_need_to_raise"), ("what_the_money_is_for", "what_we_are_raising_it_for"),
                       ("when_the_money_is_needed", "when_we_need_it"),
                       ("what_the_funding_will_make_possible", "what_this_funding_will_make_possible"),
                       ("why_the_timing_matters", "why_the_timing_matters")]:
        if goal.get(key):
            goal_block[label] = goal[key]
    _sd_block(lines, "2. Our Fundraising Goal", goal_block)
    audiences = structured.get("ideal_funding_audiences") or {}
    lines.append("3. OUR IDEAL FUNDING AUDIENCES")
    lines.append("")
    for key, label in [("individual_donors", "Ideal Individual Donors"),
                       ("businesses_and_corporate_partners", "Ideal Businesses / Corporate Sponsors & Partners"),
                       ("grantors_and_foundations", "Ideal Grantors / Foundations"),
                       ("other_relevant_audiences", "Other Priority Funding Audiences")]:
        _sd_block(lines, label, audiences.get(key) or [])
    _sd_block(lines, "4. Where We Will Find Our Funding Audiences", structured.get("where_to_find_each_funding_audience") or [])
    _sd_block(lines, "5. How We Will Attract & Engage Them", structured.get("attraction_and_visibility_system") or [])
    process = structured.get("fundraising_process") or []
    lines.append("6. OUR FUNDRAISING PROCESS")
    lines.append("")
    for journey in process:
        lines.append(str(journey.get("audience", "")).upper())
        lines.append("KNOW → LIKE → TRUST → ASK → FOLLOW UP → STEWARD")
        for step in ["know", "like", "trust", "ask", "follow_up", "steward"]:
            if journey.get(step):
                lines.append(f"{step.replace('_', ' ').upper()}: {journey[step]}")
        lines.append("")
    _sd_block(lines, "7. Content & Materials We Need", structured.get("content_and_materials_needed") or {})
    _sd_block(lines, "8. People & Execution Roles", structured.get("people_and_execution_roles") or {})
    timeline = structured.get("execution_timeline") or {}
    horizon = timeline.get("horizon", "").strip() or "EXECUTION"
    lines.append(f"9. OUR {horizon.replace(' DAYS', '')}-DAY EXECUTION CALENDAR" if "DAY" in horizon.upper() else "9. OUR EXECUTION CALENDAR")
    lines.append("")
    if timeline.get("horizon_basis"):
        lines.extend([timeline["horizon_basis"], ""])
    _sd_block(lines, "Execution Phases", timeline.get("phases") or [])
    _sd_block(lines, "10. Budget & Resource Requirements", structured.get("budget_and_resource_requirements") or {})
    _sd_block(lines, "11. Final Strategic Recommendations", structured.get("final_strategic_recommendations") or {})
    return "\n".join(lines).strip()


def parse_plan_ideas(text: str) -> list:
    """Split a strategy plan's display text into reviewable idea sections (heading + content)."""
    ideas = []
    current = None
    for line in (text or "").splitlines():
        stripped = line.strip()
        is_heading = (stripped and stripped == stripped.upper() and any(ch.isalpha() for ch in stripped)
                      and len(stripped) < 90 and stripped != "FUNDRAISING STRATEGY PLAN")
        if is_heading:
            if current and current["content"].strip():
                ideas.append(current)
            key = "".join(ch if ch.isalnum() else "-" for ch in stripped.lower()).strip("-")
            while "--" in key:
                key = key.replace("--", "-")
            current = {"key": key, "title": stripped, "content": ""}
        elif current is not None:
            current["content"] += line + "\n"
    if current and current["content"].strip():
        ideas.append(current)
    for idea in ideas:
        idea["content"] = idea["content"].strip()
    return ideas


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
    if "meeting_objective" not in structured:
        lines = ["PLAN ADOPTION FACILITATION GUIDE", organization, ""]
        for heading, key in GUIDE_SECTIONS:
            lines.extend([heading.upper(), str(structured.get(key, "")), ""])
        return "\n".join(lines).strip()
    lines = ["FUNDRAISING STRATEGY REVIEW & ADOPTION — FACILITATION GUIDE", organization, ""]
    _sd_block(lines, "Meeting Objective", structured.get("meeting_objective", ""))
    _sd_block(lines, "1. Before the Meeting", structured.get("before_the_meeting") or [])
    _sd_block(lines, "2. Welcome & Purpose", structured.get("welcome_and_purpose") or {})
    _sd_block(lines, "3. How We Built This Plan", structured.get("how_we_built_this_plan") or {})
    _sd_block(lines, "4. Reconnect to the Fundraising Goal", structured.get("reconnect_to_fundraising_goal") or {})
    _sd_block(lines, "5. Review the Fundraising Strategy", structured.get("strategy_review") or [])
    _sd_block(lines, "6. Work Through Board Questions / Changes", structured.get("work_through_changes") or {})
    _sd_block(lines, "7. Confirm the Fundraising Priorities", structured.get("confirm_fundraising_priorities") or {})
    _sd_block(lines, "8. Adopt the Strategy as Our Working Fundraising Document", structured.get("adoption_discussion") or {})
    _sd_block(lines, "9. What the Board Will Help Carry", structured.get("what_the_board_will_help_carry") or {})
    _sd_block(lines, "10. Individual Board Member Responsibility Discussions", structured.get("individual_responsibility_discussions") or [])
    _sd_block(lines, "11. Support & Resources Needed", structured.get("support_and_resources") or {})
    _sd_block(lines, "12. Immediate Execution Priorities", structured.get("immediate_execution_priorities") or {})
    _sd_block(lines, "13. Record the Plan Adoption Conclusion", structured.get("plan_adoption_conclusion_reminder") or [])
    _sd_block(lines, "14. Closing", structured.get("closing") or {})
    return "\n".join(lines).strip()


def toolkit_display(structured: dict, organization: str) -> str:
    lines = ["BOARD FUNDRAISING EXECUTION TOOLKIT", organization, ""]
    _sd_block(lines, "Overview", structured.get("overview", ""))
    resources = structured.get("how_to_use_your_fundraising_resources") or []
    if resources:
        lines.extend(["HOW TO USE YOUR FUNDRAISING RESOURCES", ""])
        for entry in resources:
            if entry.get("resource"):
                lines.append(str(entry["resource"]).upper())
                lines.extend([str(entry.get("purpose", "")), ""])
    _sd_block(lines, "Before You Reach Out Checklist", structured.get("before_you_reach_out_checklist") or [])
    _sd_block(lines, "Prospect / Funder Conversation Preparation Guide", structured.get("conversation_preparation_guide") or {})
    _sd_block(lines, "Meeting Preparation Checklist", structured.get("meeting_preparation_checklist") or [])
    _sd_block(lines, "Conversation Notes & Report-Back Template", structured.get("conversation_notes_and_report_back") or {})
    _sd_block(lines, "Follow-Up Tracker", structured.get("follow_up_tracker") or {})
    for heading, key in [("STEWARDSHIP TOOLS", "stewardship_tools"), ("STRATEGY-SPECIFIC TOOLS", "strategy_specific_tools")]:
        tools = structured.get(key) or []
        if not tools:
            continue
        lines.extend([heading, ""])
        for tool in tools:
            lines.append(str(tool.get("title", "")).upper())
            for label, k in [("Why this tool is needed", "why_this_tool_is_needed"), ("When to use this", "when_to_use"), ("Format", "format")]:
                if tool.get(k):
                    lines.append(f"{label}: {tool[k]}")
            lines.extend([str(tool.get("content", "")), ""])
    return "\n".join(lines).strip()


def case_display(structured: dict, organization: str) -> str:
    lines = ["THE CASE FOR SUPPORT", organization, ""]
    _sd_block(lines, "Why This Work Matters", structured.get("opening_case", ""))
    _sd_block(lines, "The Need / Challenge", structured.get("the_need", ""))
    _sd_block(lines, "Who We Serve", structured.get("who_we_serve", ""))
    _sd_block(lines, "What We Do", structured.get("what_we_do", ""))
    _sd_block(lines, "How Our Approach Helps", structured.get("how_our_approach_helps", ""))
    _sd_block(lines, "The Difference This Work Is Making", structured.get("difference_we_are_making", ""))
    funding = structured.get("funding_priority") or {}
    fblock = {}
    for key, label in [("what_we_are_raising_money_for", "What We Are Raising Money For"), ("amount", "Amount"),
                       ("when_the_money_is_needed", "When The Money Is Needed"), ("why_now", "Why Now")]:
        if funding.get(key):
            fblock[label] = funding[key]
    _sd_block(lines, "What We Are Raising Money For", fblock)
    _sd_block(lines, "What Your Support Will Make Possible", structured.get("what_your_support_will_make_possible") or [])
    _sd_block(lines, "How You Can Help", structured.get("how_you_can_help") or [])
    next_step = structured.get("next_step") or {}
    if any(str(v).strip() for v in next_step.values()):
        lines.extend(["LET'S TALK / NEXT STEP", ""])
        if next_step.get("invitation"):
            lines.extend([next_step["invitation"], ""])
        contact = next_step.get("contact_name", "")
        if contact and next_step.get("contact_title"):
            contact = f"{contact} — {next_step['contact_title']}"
        if contact:
            lines.append(contact)
        for key in ["email", "phone", "website", "donation_url"]:
            if next_step.get(key):
                lines.append(str(next_step[key]))
    return "\n".join(lines).strip()


COMM_STAGES = [("stage_1_introduce_impact", "STAGE 1 — INTRODUCE IMPACT"),
               ("stage_2_case_for_support", "STAGE 2 — CASE FOR SUPPORT"),
               ("stage_3_follow_up_and_ask", "STAGE 3 — FOLLOW UP & ASK")]


def comm_display(structured: dict, organization: str) -> str:
    lines = ["BOARD FUNDRAISING COMMUNICATION SYSTEM", organization, ""]
    _sd_block(lines, "Overview", structured.get("overview", ""))
    _sd_block(lines, "How to Use This System", structured.get("how_to_use_this_system") or [])
    for seq in structured.get("audience_sequences") or []:
        lines.extend([f"AUDIENCE: {str(seq.get('audience', '')).upper()}", ""])
        if seq.get("why_this_audience_matters"):
            lines.extend([str(seq["why_this_audience_matters"]), ""])
        for stage_key, stage_title in COMM_STAGES:
            stage = seq.get(stage_key) or {}
            if not stage:
                continue
            lines.extend([stage_title, ""])
            if stage.get("purpose"):
                lines.extend([f"Purpose: {stage['purpose']}", ""])
            if stage.get("email_subject") or stage.get("email_body"):
                lines.append("EMAIL")
                if stage.get("email_subject"):
                    lines.append(f"Subject: {stage['email_subject']}")
                lines.extend(["", str(stage.get("email_body", "")), ""])
            script = stage.get("call_script") or {}
            if any(str(v).strip() for v in script.values()):
                lines.extend(["CALL SCRIPT", ""])
                for key, value in script.items():
                    if value:
                        lines.extend([key.replace("_", " ").upper(), str(value), ""])
    _sd_block(lines, "Report Back to the Organization", structured.get("report_back_to_the_organization") or {})
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


class IdeaReview(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    key: str
    title: str = ""
    decision: str
    reason: str = ""


class ReviewSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")
    position: str
    discussion_points: str = ""
    contribution: str = Field(min_length=1)
    support_needs: str = ""
    full_name: str = ""
    email: str = ""
    role: str = ""
    idea_reviews: List[IdeaReview] = []


class MeetingPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    meeting_date: str = ""
    meeting_time: str = ""
    meeting_link: str = ""
    meeting_notes: str = ""


class FollowupEditPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)


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
            "founder_title": reactivation.get("founder_title", "") or intake.get("founder_title", ""),
            "founder_phone": intake.get("phone", "") or ((await db.funnel_leads.find_one({"email": (founder or {}).get("email", "")}, {"_id": 0, "phone": 1}, sort=[("created_at", -1)]) or {}).get("phone", "")),
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
            {"owner_user_id": user_id, "final_outcome": "Joined Board"},
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
            {"user_id": user_id, "conversation_outcome": "Continuing as an Active Board Member"},
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
            if not app or app.get("final_outcome") != "Joined Board":
                raise HTTPException(status_code=404, detail="Only formally appointed Board Members can be added from Recruitment")
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

    @router.get("/activation/planning-email")
    async def planning_email(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        form = await current_form(user_id)
        if form.get("status") != "Approved" or not form.get("approved_version"):
            raise HTTPException(status_code=409, detail="Approve your Board Fundraising Planning Form before generating the email")
        context = await founder_context(user_id)
        goal_line = (form.get("content") or {}).get("goal_context", "").strip()
        email = build_planning_email("initial", {"name": ""}, context["founder_name"], context["founder_title"], context["organization"], "", goal_line)
        return {"subject": email["subject"], "body": email["body"], "form_link": "",
                "note": "Each Board Member automatically receives their OWN secure form link when you send their individual email. No shared link is used."}

    # ---------------- FOUNDER: SEND / REMIND ----------------

    async def send_context(user_id: str, record: dict, request: Request, kind: str) -> dict:
        context = await founder_context(user_id)
        form = await current_form(user_id)
        goal_line = (form.get("content") or {}).get("goal_context", "").strip()
        form_link = f"{origin_of(request)}/planning-form/{record['form_token']}"
        return build_planning_email(kind, record, context["founder_name"], context["founder_title"], context["organization"], form_link, goal_line) | {
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
            "form": form_payload(content, context["organization"]),
        }

    @router.post("/planning-form/{token}", status_code=201)
    async def submit_planning_form(token: str, payload: PlanningSubmission):
        record = await db.activation_participants.find_one({"form_token": token}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This form link is not valid")
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
        delivery = await db.activation_delivery.find_one({"user_id": user_id}, {"_id": 0}) or {}
        planning_snapshot = {
            "expected_responses": delivery.get("expected_planning_responses", 0),
            "responses_included": len(completed),
            "participant_ids": [p["participant_id"] for p in completed],
            "proceed_authorized_with_available": delivery.get("proceed_decision", "") == "yes",
            "ready_reason": delivery.get("ready_reason", ""),
            "frozen_at": now,
        }
        await db.activation_strategies.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "status": "Generating", "generation_error": "",
                      "planning_snapshot": planning_snapshot, "updated_at": now},
             "$setOnInsert": {"review_version": 0, "review_versions": [], "created_at": now}},
            upsert=True)
        import json as jsonlib
        intake_context = {key: intake.get(key, "") for key in [
            "your_name", "organization_name", "fundraising_goal", "amount_needed", "money_accomplish",
            "current_methods", "written_strategy", "fundraising_calendar", "fundraising_carriers",
            "present_board", "active_board", "board_fundraising_involvement", "board_fundraising_activities",
            "perceived_barriers", "board_skills_relationships", "direction_12_24", "organization_priorities",
            "previous_fundraising_planning", "broader_strategic_planning", "desired_change", "success_definition", "anything_else",
            "money_needed_by", "present_donors", "present_business_sponsors", "present_corporate_relationships",
            "present_grantors", "other_funding_relationships", "individuals_type", "individuals_approach",
            "businesses_type", "businesses_approach", "grantors_type", "grantors_approach"]}
        responses_block = [
            {"participant_id": p["participant_id"], "board_member_name": p["name"], "board_role": p.get("role", "Board Member"),
             "form_version_answered": p.get("form_version", 0), "their_response": p.get("response", {})}
            for p in completed]
        all_participants = await db.activation_participants.find({"user_id": user_id}, {"_id": 0, "name": 1, "status": 1}).to_list(300)
        status_block = {
            "board_members_invited": len(all_participants),
            "responses_received": len(completed),
            "completed_members": [p["name"] for p in completed],
            "outstanding_members": [p["name"] for p in all_participants if p.get("status") != "COMPLETED"],
        }
        profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data": 1}) or {}
        org_facts = {key: value for key, value in (profile.get("data") or {}).items()
                     if isinstance(value, str) and value.strip() and key not in {"logo_data"}}
        horizon = execution_horizon(str(intake.get("money_needed_by", "")))
        timeline_block = {
            "verified_fundraising_deadline_or_timeline": intake.get("money_needed_by", ""),
            "EXECUTION_HORIZON": horizon or ("Select exactly 60 DAYS, 90 DAYS or 120 DAYS from the verified fundraising deadline/timeline above. "
                                             "If no fundraising deadline/timeline was supplied, use 90 DAYS as a recommended initial planning cycle and state clearly that it is not an organization-supplied deadline."),
            "note": "This horizon comes from the organization's actual fundraising deadline/timeline — never from any Planning Form submission deadline.",
        }
        context = ("ORGANIZATION CONTEXT:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"]}, indent=1)
                   + "\n\nVERIFIED ORGANIZATION PROFILE INFORMATION:\n" + jsonlib.dumps(org_facts, indent=1, default=str)
                   + "\n\nFOUNDER ACTIVATION INTAKE (the founder's authoritative fundraising information):\n" + jsonlib.dumps(intake_context, indent=1, default=str)
                   + "\n\nEXECUTION TIMELINE SOURCE:\n" + jsonlib.dumps(timeline_block, indent=1, default=str)
                   + "\n\nPLANNING RESPONSE STATUS (factual — do not describe outstanding members' opinions):\n" + jsonlib.dumps(status_block, indent=1, default=str)
                   + "\n\nEVERY COMPLETED BOARD MEMBER PLANNING RESPONSE (preserve who said what; ideas are input, not commitments):\n" + jsonlib.dumps(responses_block, indent=1, default=str))

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

    @router.get("/activation/strategy-review-email")
    async def strategy_review_email(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        strategy = await current_strategy(user_id)
        if strategy.get("status") != "Ready for Board Review" or not strategy.get("review_version"):
            raise HTTPException(status_code=409, detail="Approve your Fundraising Strategy Plan for Board review before generating the email")
        token = strategy.get("shared_review_token")
        if not token:
            token = secrets.token_urlsafe(32)
            await db.activation_strategies.update_one({"user_id": user_id}, {"$set": {"shared_review_token": token}})
        context = await founder_context(user_id)
        review_link = f"{origin_of(request)}/strategy-review/{token}"
        email = activation_review_email(context["organization"], review_link,
                                        activation_signature(context["founder_name"], context["founder_title"], context["organization"]))
        return {"subject": email["subject"], "body": email["body"], "review_link": review_link}

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
        record = await db.activation_participants.find_one({"review_token": token}, {"_id": 0})
        if record:
            context = await founder_context(record["user_id"])
            text = await review_version_text(record["user_id"], record.get("review_version") or 0)
            return {"organization_name": context["organization"],
                    "submitted": record.get("review_status") == "REVIEWED",
                    "reviewer": {"name": record.get("name", ""), "role": record.get("role", "")},
                    "requires_identity": False,
                    "strategy_text": text, "ideas": parse_plan_ideas(text),
                    "options": REVIEW_OPTIONS}
        strategy = await db.activation_strategies.find_one({"shared_review_token": token}, {"_id": 0})
        if not strategy or not strategy.get("review_versions"):
            raise HTTPException(status_code=404, detail="This review link is not valid")
        context = await founder_context(strategy["user_id"])
        text = strategy["review_versions"][-1]["display_text"]
        return {"organization_name": context["organization"], "submitted": False,
                "reviewer": {"name": "", "role": ""}, "requires_identity": True,
                "strategy_text": text, "ideas": parse_plan_ideas(text), "options": REVIEW_OPTIONS}

    @router.post("/strategy-review/{token}", status_code=201)
    async def submit_review(token: str, payload: ReviewSubmission):
        record = await db.activation_participants.find_one({"review_token": token}, {"_id": 0})
        shared_strategy = None
        if not record:
            shared_strategy = await db.activation_strategies.find_one({"shared_review_token": token}, {"_id": 0})
            if not shared_strategy:
                raise HTTPException(status_code=404, detail="This review link is not valid")
            if not payload.full_name.strip() or "@" not in payload.email:
                raise HTTPException(status_code=422, detail="Please provide your name and email so your review can be recorded")
            email = payload.email.lower()
            record = await db.activation_participants.find_one({"user_id": shared_strategy["user_id"], "email": email}, {"_id": 0})
            if not record:
                record = {
                    "participant_id": str(uuid.uuid4()), "user_id": shared_strategy["user_id"],
                    "name": payload.full_name, "email": email, "phone": "", "role": payload.role,
                    "source": "self_identified", "status": "NOT SENT", "form_token": secrets.token_urlsafe(32),
                    "form_version": 0, "call_notes": "", "review_status": "NOT SENT",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.activation_participants.insert_one({**record})
        if record.get("review_status") == "REVIEWED":
            raise HTTPException(status_code=409, detail="This review has already been submitted")
        if payload.position not in REVIEW_OPTIONS:
            raise HTTPException(status_code=422, detail="Invalid review selection")
        if payload.position != REVIEW_OPTIONS[0] and not payload.discussion_points.strip():
            raise HTTPException(status_code=422, detail="Please share what you would like the Board to discuss before the plan is adopted")
        now = datetime.now(timezone.utc).isoformat()
        review = {"position": payload.position, "discussion_points": payload.discussion_points,
                  "contribution": payload.contribution, "support_needs": payload.support_needs}
        review_updates = {"review_status": "REVIEWED", "review": review, "review_submitted_at": now}
        if shared_strategy and not record.get("review_version"):
            review_updates["review_version"] = shared_strategy.get("review_version", 0)
        result = await db.activation_participants.update_one(
            {"participant_id": record["participant_id"], "review_status": {"$ne": "REVIEWED"}},
            {"$set": review_updates})
        context = await founder_context(record["user_id"])
        if result.modified_count:
            try:
                if context["founder_email"]:
                    first = (record.get("name") or "").split(" ")[0]
                    founder_first = context["founder_name"].split(" ")[0] if context["founder_name"] else "there"
                    origin = os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com"
                    view_url = f"{origin}/app/activation/self-guided/module/4"
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
        reviewed_participants = [{"participant_id": p["participant_id"], "name": p["name"],
                                  "role": p.get("role", "Board Member"), "email": p.get("email", ""),
                                  "planning_submitted_at": p.get("submitted_at", ""),
                                  "review_submitted_at": p.get("review_submitted_at", ""),
                                  "position": (p.get("review") or {}).get("position", "")}
                                 for p in participants if p.get("review_status") == "REVIEWED"]
        members = []
        for p in participants:
            response = p.get("response") or {}
            members.append({"participant_id": p["participant_id"], "name": p["name"], "role": p.get("role", "Board Member"),
                            "participation_activities": response.get("participation_willingness") or response.get("participation_activities", []),
                            "ownership_interest": response.get("greater_responsibility_detail") or response.get("greater_responsibility_interest") or response.get("ownership", ""),
                            "support_needed": response.get("support_needed", []),
                            "review_contribution": (p.get("review") or {}).get("contribution", ""),
                            "review_support": (p.get("review") or {}).get("support_needs", ""),
                            "agreed_responsibility": p.get("agreed_responsibility", ""),
                            "responsibility_status": p.get("responsibility_status", "No Fundraising Responsibility Agreed Yet")})
        return {"strategy": strategy_summary(strategy),
                "reviewed_text": (strategy.get("review_versions") or [{}])[-1].get("display_text", "") if strategy else "",
                "reviews": reviews, "reviewed_participants": reviewed_participants,
                "adoption": adoption, "members": members,
                "module5_ready": module5_ready(adoption)}

    @router.post("/activation/adoption/strategy/generate")
    async def generate_revised_strategy(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        reviewed_text = await ready_review_text(user_id)
        adoption = await current_adoption(user_id)
        if adoption.get("revised_status") == "Generating":
            return {"status": "Generating"}
        intake = await activation_intake(user_id)
        context_info = await founder_context(user_id)
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_adoptions.update_one({"user_id": user_id}, {"$set": {
            "user_id": user_id, "revised_status": "Generating", "revised_error": "", "updated_at": now},
            "$setOnInsert": {"created_at": now}}, upsert=True)
        participants = await db.activation_participants.find({"user_id": user_id}, {"_id": 0}).to_list(300)
        import json as jsonlib
        responses_block = [{"board_member_name": p["name"], "board_role": p.get("role", "Board Member"),
                            "their_planning_response": p.get("response", {})} for p in participants if p.get("response")]
        reviews_block = [{"board_member_name": p["name"], "board_role": p.get("role", "Board Member"),
                          "their_review": p.get("review", {})} for p in participants if p.get("review_status") == "REVIEWED"]
        context = ("ORGANIZATION CONTEXT:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"]}, indent=1)
                   + "\n\nTHE FUNDRAISING STRATEGY PLAN THE BOARD REVIEWED:\n" + reviewed_text
                   + "\n\nEVERY BOARD MEMBER REVIEW — overall position, suggestions and discussion points (preserve who said what):\n" + jsonlib.dumps(reviews_block, indent=1, default=str)
                   + "\n\nORIGINAL BOARD MEMBER PLANNING RESPONSES:\n" + jsonlib.dumps(responses_block, indent=1, default=str)
                   + "\n\nACTIVATION INTAKE HIGHLIGHTS:\n" + jsonlib.dumps({key: intake.get(key, "") for key in [
                       "fundraising_goal", "amount_needed", "money_accomplish", "organization_priorities",
                       "desired_change", "success_definition"]}, indent=1, default=str))

        async def run_generation():
            try:
                structured = await generate_structured("activation_revised_strategy", context)
                await db.activation_adoptions.update_one({"user_id": user_id}, {"$set": {
                    "revised_status": "Draft", "revised_structured": structured,
                    "revised_text": strategy_display(structured, context_info["organization"]),
                    "revised_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Revised strategy generation failed for %s: %s", user_id, exc)
                await db.activation_adoptions.update_one({"user_id": user_id}, {"$set": {
                    "revised_status": "Failed", "revised_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating"}

    @router.put("/activation/adoption/meeting")
    async def save_meeting_details(payload: MeetingPayload, request: Request):
        member = await activation_member(request)
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_adoptions.update_one({"user_id": member["user_id"]}, {"$set": {
            "user_id": member["user_id"], "meeting_date": payload.meeting_date, "meeting_time": payload.meeting_time,
            "meeting_link": payload.meeting_link, "meeting_notes": payload.meeting_notes, "updated_at": now},
            "$setOnInsert": {"created_at": now}}, upsert=True)
        return {"status": "saved"}

    @router.get("/activation/adoption/meeting-email")
    async def adoption_meeting_email(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        adoption = await current_adoption(user_id)
        if not adoption.get("meeting_date") or not adoption.get("meeting_time"):
            raise HTTPException(status_code=409, detail="Save your adoption meeting date and time before generating the invitation email")
        strategy = await current_strategy(user_id)
        plan_text = ((strategy.get("review_versions") or [{}])[-1].get("display_text", "")) or adoption.get("revised_text")
        if not plan_text:
            raise HTTPException(status_code=409, detail="Generate the Fundraising Strategy Plan before generating the invitation email")
        token = adoption.get("plan_share_token")
        if not token:
            token = secrets.token_urlsafe(32)
            await db.activation_adoptions.update_one({"user_id": user_id}, {"$set": {"plan_share_token": token}})
        context = await founder_context(user_id)
        plan_link = f"{origin_of(request)}/strategy-plan/{token}"
        meeting_lines = f"Date: {adoption['meeting_date']}\nTime: {adoption['meeting_time']}"
        if adoption.get("meeting_link"):
            meeting_lines += f"\nMeeting link: {adoption['meeting_link']}"
        if adoption.get("meeting_notes"):
            meeting_lines += f"\n{adoption['meeting_notes']}"
        email = activation_adoption_meeting_email(context["organization"], meeting_lines, plan_link,
                                                  activation_signature(context["founder_name"], context["founder_title"], context["organization"]))
        return {"subject": email["subject"], "body": email["body"], "plan_link": plan_link}

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
        willingness = [{"board_member_name": p["name"], "board_role": p.get("role", ""),
                        "planning_response": p.get("response", {})} for p in participants if p.get("response")]
        profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data": 1}) or {}
        org_facts = {key: value for key, value in (profile.get("data") or {}).items()
                     if isinstance(value, str) and value.strip() and key not in {"logo_data"}}
        context = ("ORGANIZATION:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"],
                                                       "founder_name": context_info["founder_name"]}, indent=1)
                   + "\n\nVERIFIED ORGANIZATION INFORMATION:\n" + jsonlib.dumps(org_facts, indent=1, default=str)
                   + "\n\nTHE EXACT FUNDRAISING STRATEGY PLAN VERSION BEING PRESENTED TO THE BOARD:\n" + reviewed_text
                   + "\n\nEVERY ORIGINAL BOARD MEMBER FUNDRAISING PLANNING RESPONSE (input for discussion — NOT final responsibilities; preserve who said what):\n" + jsonlib.dumps(willingness, indent=1, default=str)
                   + "\n\nFOUNDER FUNDRAISING INFORMATION:\n" + jsonlib.dumps({key: intake.get(key, "") for key in [
                       "fundraising_goal", "amount_needed", "money_accomplish", "money_needed_by", "organization_priorities",
                       "fundraising_carriers", "board_fundraising_involvement", "desired_change", "success_definition"]}, indent=1, default=str))

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
        return {"guide_status": adoption.get("guide_status", "NONE"),
                "revised_status": adoption.get("revised_status", "NONE"),
                "toolkit_gate": module5_ready(adoption)}

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
        adoption = await current_adoption(user_id)
        current_plan = adoption.get("revised_text", "")
        updates = {"user_id": user_id, "plan_status": payload.status, "updated_at": now}
        if payload.status == "Adopted as Presented":
            updates.update({"adopted_text": current_plan or await ready_review_text(user_id), "finalized": True, "adopted_at": now})
        elif payload.status == "Adopted With Changes":
            updates["finalized"] = False
            if not adoption.get("draft_adopted_text"):
                updates["draft_adopted_text"] = current_plan or await ready_review_text(user_id)
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

    @router.get("/strategy-plan/{token}")
    async def public_strategy_plan(token: str):
        adoption = await db.activation_adoptions.find_one({"plan_share_token": token}, {"_id": 0})
        if not adoption:
            raise HTTPException(status_code=404, detail="This plan link is not valid")
        strategy = await current_strategy(adoption["user_id"])
        text = adoption.get("adopted_text") or adoption.get("revised_text") or ((strategy.get("review_versions") or [{}])[-1].get("display_text", ""))
        if not text:
            raise HTTPException(status_code=404, detail="This plan link is not valid")
        context = await founder_context(adoption["user_id"])
        return {"organization_name": context["organization"], "text": text}

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
        participants = await db.activation_participants.find({"user_id": member["user_id"]}, {"_id": 0}).sort("created_at", 1).to_list(300)
        members = [{"participant_id": p["participant_id"], "name": p["name"], "role": p.get("role", "Board Member"),
                    "email": p.get("email", ""),
                    "agreed_responsibility": p.get("agreed_responsibility", ""),
                    "responsibility_status": p.get("responsibility_status", "No Fundraising Responsibility Agreed Yet"),
                    "followup_status": p.get("followup_status", "NONE"),
                    "followup_subject": p.get("followup_subject", ""),
                    "followup_body": p.get("followup_body", ""),
                    "followup_error": p.get("followup_error", "")} for p in participants]
        return {"gate_open": module5_ready(adoption), "plan_status": adoption.get("plan_status", ""),
                "members": members, "responsibility_statuses": RESPONSIBILITY_STATUSES,
                "toolkit": {"status": toolkit.get("status", "NONE"), "display_text": toolkit.get("display_text", ""),
                            "generation_error": toolkit.get("generation_error", "")},
                "case": case_summary(await current_case(member["user_id"]), request),
                "communication_system": comm_summary(await current_comm(member["user_id"]))}

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
        responsibilities = [{"board_role": p.get("role", "Board Member"),
                             "agreed_responsibility": p.get("agreed_responsibility", ""),
                             "responsibility_status": p.get("responsibility_status", "")} for p in participants]
        context = ("ORGANIZATION:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"]}, indent=1)
                   + "\n\nFINAL ADOPTED FUNDRAISING STRATEGY PLAN:\n" + adoption.get("adopted_text", "")
                   + "\n\nPLAN ADOPTION CONCLUSION (founder's recorded Board-level decisions only):\n" + adoption.get("conclusion", "")
                   + "\n\nACTUAL AGREED FUNDRAISING RESPONSIBILITY CATEGORIES (no names — use only to understand what types of tools the Board needs; never assign or invent responsibilities):\n" + jsonlib.dumps(responsibilities, indent=1, default=str)
                   + "\n\nVERIFIED FUNDRAISING INFORMATION:\n" + jsonlib.dumps({key: intake.get(key, "") for key in [
                       "fundraising_goal", "amount_needed", "money_accomplish", "money_needed_by"]}, indent=1, default=str))

        async def run_generation():
            try:
                structured = await generate_structured("activation_execution_toolkit", context)
                structured["strategy_specific_tools"] = (structured.get("strategy_specific_tools") or [])[:3]
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

    # ---------------- MODULE 5: CASE FOR SUPPORT ----------------

    async def current_case(user_id: str) -> dict:
        return await db.activation_cases.find_one({"user_id": user_id}, {"_id": 0}) or {}

    def case_summary(case: dict, request: Request) -> dict:
        share_link = ""
        if case.get("case_share_token") and case.get("approved_versions"):
            share_link = f"{origin_of(request)}/case-for-support/{case['case_share_token']}"
        return {"status": case.get("status", "NONE"), "display_text": case.get("display_text", ""),
                "generation_error": case.get("generation_error", ""),
                "approved_version": case.get("approved_version", 0), "share_link": share_link,
                "share_is_current": case.get("status") == "Approved" and bool(share_link)}

    @router.post("/activation/case-for-support/generate")
    async def generate_case(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        adoption = await current_adoption(user_id)
        if not module5_ready(adoption):
            raise HTTPException(status_code=409, detail="The Fundraising Strategy Plan must be adopted and finalized before the Case for Support is created")
        case = await current_case(user_id)
        if case.get("status") == "Generating":
            return {"status": "Generating"}
        intake = await activation_intake(user_id)
        context_info = await founder_context(user_id)
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_cases.update_one({"user_id": user_id}, {"$set": {
            "user_id": user_id, "status": "Generating", "generation_error": "", "updated_at": now},
            "$setOnInsert": {"approved_version": 0, "approved_versions": [], "created_at": now}}, upsert=True)
        profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data": 1}) or {}
        org_facts = {key: value for key, value in (profile.get("data") or {}).items()
                     if isinstance(value, str) and value.strip() and key not in {"logo_data"}}
        overview_material = await db.generated_materials.find_one(
            {"user_id": user_id, "type": "organization_overview", "application_id": "", "status": "Approved"},
            {"_id": 0, "current.display_text": 1})
        overview_text = ((overview_material or {}).get("current") or {}).get("display_text", "")
        import json as jsonlib
        contact_block = {
            "contact_name": context_info["founder_name"], "contact_title": context_info["founder_title"],
            "email": context_info["founder_email"], "phone": context_info["founder_phone"],
            "website": org_facts.get("website", ""),
        }
        context = ("ORGANIZATION:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"]}, indent=1)
                   + "\n\nFINAL ADOPTED FUNDRAISING STRATEGY PLAN (primary strategic authority):\n" + adoption.get("adopted_text", "")
                   + "\n\nVERIFIED ORGANIZATION PROFILE INFORMATION:\n" + jsonlib.dumps(org_facts, indent=1, default=str)
                   + ("\n\nAPPROVED ORGANIZATION OVERVIEW (verified organizational context):\n" + overview_text[:8000] if overview_text else "")
                   + "\n\nVERIFIED FOUNDER FUNDRAISING INFORMATION:\n" + jsonlib.dumps({key: intake.get(key, "") for key in [
                       "fundraising_goal", "amount_needed", "money_accomplish", "money_needed_by",
                       "direction_12_24", "organization_priorities"]}, indent=1, default=str)
                   + "\n\nACTUAL ORGANIZATION / FUNDRAISING CONTACT INFORMATION (use only what is supplied; never invent a donation URL):\n" + jsonlib.dumps(contact_block, indent=1, default=str))

        async def run_generation():
            try:
                structured = await generate_structured("activation_case_for_support", context)
                await db.activation_cases.update_one({"user_id": user_id}, {"$set": {
                    "status": "Draft", "structured": structured,
                    "display_text": case_display(structured, context_info["organization"]),
                    "updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Case for Support generation failed for %s: %s", user_id, exc)
                await db.activation_cases.update_one({"user_id": user_id}, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating"}

    @router.put("/activation/case-for-support")
    async def edit_case(payload: TextPayload, request: Request):
        member = await activation_member(request)
        case = await current_case(member["user_id"])
        if not case.get("display_text"):
            raise HTTPException(status_code=409, detail="Generate your Case for Support first")
        await db.activation_cases.update_one({"user_id": member["user_id"]}, {"$set": {
            "display_text": payload.text, "status": "Draft", "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Draft"}

    @router.post("/activation/case-for-support/approve")
    async def approve_case(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        case = await current_case(user_id)
        if case.get("status") not in {"Draft", "Approved"} or not case.get("display_text"):
            raise HTTPException(status_code=409, detail="There is no draft Case for Support ready to approve")
        now = datetime.now(timezone.utc).isoformat()
        version = case.get("approved_version", 0) + 1
        updates = {"status": "Approved", "approved_version": version, "approved_at": now, "updated_at": now}
        if not case.get("case_share_token"):
            updates["case_share_token"] = secrets.token_urlsafe(32)
        await db.activation_cases.update_one({"user_id": user_id}, {
            "$set": updates,
            "$push": {"approved_versions": {"version": version, "display_text": case["display_text"], "approved_at": now}}})
        refreshed = await current_case(user_id)
        return {"status": "Approved", "approved_version": version,
                "share_link": f"{origin_of(request)}/case-for-support/{refreshed['case_share_token']}"}

    @router.get("/activation/case-for-support/pdf")
    async def case_pdf(request: Request):
        member = await activation_member(request)
        case = await current_case(member["user_id"])
        if not case.get("display_text"):
            raise HTTPException(status_code=404, detail="No Case for Support available")
        context = await founder_context(member["user_id"])
        issuer = {"issued_by": context["founder_name"], "issuer_title": context["founder_title"],
                  "organization": context["organization"], "issue_date": datetime.now(timezone.utc).strftime("%B %d, %Y")}
        return build_portfolio_pdf("The Case for Support", "", issuer, case["display_text"])

    @router.get("/case-for-support/{token}")
    async def public_case_for_support(token: str):
        case = await db.activation_cases.find_one({"case_share_token": token}, {"_id": 0})
        if not case or not case.get("approved_versions"):
            raise HTTPException(status_code=404, detail="This link is not valid")
        approved = case["approved_versions"][-1]
        context = await founder_context(case["user_id"])
        return {"organization_name": context["organization"], "text": approved["display_text"]}

    @router.get("/case-for-support/{token}/pdf")
    async def public_case_pdf(token: str):
        case = await db.activation_cases.find_one({"case_share_token": token}, {"_id": 0})
        if not case or not case.get("approved_versions"):
            raise HTTPException(status_code=404, detail="This link is not valid")
        approved = case["approved_versions"][-1]
        context = await founder_context(case["user_id"])
        issuer = {"issued_by": context["founder_name"], "issuer_title": context["founder_title"],
                  "organization": context["organization"], "issue_date": datetime.now(timezone.utc).strftime("%B %d, %Y")}
        return build_portfolio_pdf("The Case for Support", "", issuer, approved["display_text"])

    # ---------------- MODULE 5: BOARD FUNDRAISING COMMUNICATION SYSTEM ----------------

    async def current_comm(user_id: str) -> dict:
        return await db.activation_comm_systems.find_one({"user_id": user_id}, {"_id": 0}) or {}

    def comm_summary(comm: dict) -> dict:
        return {"status": comm.get("status", "NONE"), "display_text": comm.get("display_text", ""),
                "generation_error": comm.get("generation_error", "")}

    @router.post("/activation/communication-system/generate")
    async def generate_comm_system(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        adoption = await current_adoption(user_id)
        if not module5_ready(adoption):
            raise HTTPException(status_code=409, detail="The Fundraising Strategy Plan must be adopted and finalized before the Communication System is created")
        case = await current_case(user_id)
        if case.get("status") != "Approved" or not case.get("approved_versions") or not case.get("case_share_token"):
            raise HTTPException(status_code=409, detail="Approve your Case for Support first — the Stage 2 communications must contain the real secure Case for Support link")
        comm = await current_comm(user_id)
        if comm.get("status") == "Generating":
            return {"status": "Generating"}
        intake = await activation_intake(user_id)
        context_info = await founder_context(user_id)
        case_url = f"{origin_of(request)}/case-for-support/{case['case_share_token']}"
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_comm_systems.update_one({"user_id": user_id}, {"$set": {
            "user_id": user_id, "status": "Generating", "generation_error": "", "updated_at": now},
            "$setOnInsert": {"created_at": now}}, upsert=True)
        import json as jsonlib
        context = ("ORGANIZATION:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"]}, indent=1)
                   + "\n\nFINAL ADOPTED FUNDRAISING STRATEGY PLAN:\n" + adoption.get("adopted_text", "")
                   + "\n\nAPPROVED CASE FOR SUPPORT:\n" + case["approved_versions"][-1]["display_text"]
                   + "\n\nEXACT APPROVED CASE FOR SUPPORT SHARE URL (use exactly this URL in Stage 2 — never invent another link):\n" + case_url
                   + "\n\nVERIFIED FUNDRAISING INFORMATION:\n" + jsonlib.dumps({key: intake.get(key, "") for key in [
                       "fundraising_goal", "amount_needed", "money_accomplish", "money_needed_by"]}, indent=1, default=str)
                   + "\n\nORGANIZATION / FUNDRAISING CONTACT (for directing serious conversations back to the organization):\n"
                   + jsonlib.dumps({"contact_name": context_info["founder_name"], "contact_title": context_info["founder_title"],
                                    "email": context_info["founder_email"], "phone": context_info["founder_phone"]}, indent=1, default=str))

        async def run_generation():
            try:
                structured = await generate_structured("activation_board_communication_system", context)
                structured["audience_sequences"] = (structured.get("audience_sequences") or [])[:4]
                await db.activation_comm_systems.update_one({"user_id": user_id}, {"$set": {
                    "status": "Draft", "structured": structured,
                    "display_text": comm_display(structured, context_info["organization"]),
                    "case_version_used": case.get("approved_version", 0),
                    "updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Communication system generation failed for %s: %s", user_id, exc)
                await db.activation_comm_systems.update_one({"user_id": user_id}, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating"}

    @router.put("/activation/communication-system")
    async def edit_comm_system(payload: TextPayload, request: Request):
        member = await activation_member(request)
        comm = await current_comm(member["user_id"])
        if not comm.get("display_text"):
            raise HTTPException(status_code=409, detail="Generate your Board Fundraising Communication System first")
        await db.activation_comm_systems.update_one({"user_id": member["user_id"]}, {"$set": {
            "display_text": payload.text, "status": "Draft", "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Draft"}

    @router.post("/activation/communication-system/approve")
    async def approve_comm_system(request: Request):
        member = await activation_member(request)
        comm = await current_comm(member["user_id"])
        if comm.get("status") not in {"Draft", "Approved"} or not comm.get("display_text"):
            raise HTTPException(status_code=409, detail="There is no draft Communication System ready to approve")
        await db.activation_comm_systems.update_one({"user_id": member["user_id"]}, {"$set": {
            "status": "Approved", "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Approved"}

    @router.get("/activation/communication-system/pdf")
    async def comm_system_pdf(request: Request):
        member = await activation_member(request)
        comm = await current_comm(member["user_id"])
        if not comm.get("display_text"):
            raise HTTPException(status_code=404, detail="No Communication System available")
        context = await founder_context(member["user_id"])
        issuer = {"issued_by": context["founder_name"], "issuer_title": context["founder_title"],
                  "organization": context["organization"], "issue_date": datetime.now(timezone.utc).strftime("%B %d, %Y")}
        return build_portfolio_pdf("Board Fundraising Communication System", "", issuer, comm["display_text"])

    @router.post("/activation/members/{participant_id}/followup-email/generate")
    async def generate_followup_email(participant_id: str, request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        record = await owned_participant(user_id, participant_id)
        adoption = await current_adoption(user_id)
        if not module5_ready(adoption):
            raise HTTPException(status_code=409, detail="The Fundraising Strategy Plan must be adopted and your Plan Adoption Conclusion recorded before follow-up emails are prepared")
        context_info = await founder_context(user_id)
        organization = context_info["organization"]
        first = (record.get("name") or "").split(" ")[0] or "Board Member"
        signature = context_info["founder_name"] + (f"\n{context_info['founder_title']}" if context_info["founder_title"] else "") + f"\n{organization}"
        status = record.get("responsibility_status", "No Fundraising Responsibility Agreed Yet")
        if status == "Responsibility Agreed" and record.get("agreed_responsibility", "").strip():
            if record.get("fp_status") not in {"Approved", "SENT"} or not record.get("fp_share_token"):
                raise HTTPException(status_code=409, detail="Approve this member's Fundraising Portfolio first — the delivery email includes only an APPROVED Portfolio link")
            portfolio_link = f"{origin_of(request)}/fundraising-portfolio/{record['fp_share_token']}"
            subject = f"Your Fundraising Portfolio | {organization}"
            body = (
                f"Dear {first},\n\n"
                f"Thank you again for helping us build and adopt the Fundraising Strategy Plan for {organization}.\n\n"
                f"During our discussion, we agreed that you will help us with:\n\n{record['agreed_responsibility'].strip()}\n\n"
                "I have now brought that agreement together with the Fundraising Strategy we adopted and your own fundraising-planning input into your individual Fundraising Portfolio.\n\n"
                f"You can review your Portfolio here:\n\n{portfolio_link}\n\n"
                "Your Portfolio is designed to give you a clear reference for your part of the plan — why your role matters, what you agreed to help carry, your immediate priorities, and how your work connects to the wider fundraising strategy.\n\n"
                "Thank you for taking ownership of this part of the work. We will continue to work together and make sure you have the information, tools and support needed to move it forward.\n\n"
                f"{signature}"
            )
        elif status == "Follow-Up Needed":
            support = str((record.get("response") or {}).get("support_needed", "")).strip()
            support_line = f"You also mentioned that {support[:300]} would help you participate effectively, and we will make sure that is part of the conversation.\n\n" if support else ""
            subject = f"Following Up on Our Fundraising Plan | {organization}"
            body = (
                f"Dear {first},\n\n"
                f"Thank you again for helping us build and adopt the Fundraising Strategy Plan for {organization}.\n\n"
                "During our discussion, we agreed that we still need a little more clarity before confirming the specific part of the fundraising plan you will help carry.\n\n"
                "I would like us to continue that conversation so we can agree on a responsibility that makes sense for the strategy and is realistic for you.\n\n"
                f"{support_line}"
                "Once we have agreed the way forward, I will prepare your individual Fundraising Portfolio so you have a clear reference for your role and immediate priorities.\n\n"
                f"Thank you again for being part of this process.\n\n{signature}"
            )
        else:
            subject = f"Thank You for Helping Shape Our Fundraising Plan | {organization}"
            body = (
                f"Dear {first},\n\n"
                f"Thank you for helping us build and adopt the Fundraising Strategy Plan for {organization}.\n\n"
                "We have not yet agreed a specific individual fundraising responsibility together, and there is no pressure to do so right now.\n\n"
                "As the Board begins moving the strategy forward, I would welcome a conversation whenever it would be helpful to explore where your experience and interests could best support the work.\n\n"
                f"Thank you again for being part of this process.\n\n{signature}"
            )
        await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": {
            "followup_status": "Draft", "followup_subject": subject, "followup_body": body,
            "followup_error": "", "followup_updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Draft", "subject": subject, "body": body}

    @router.put("/activation/members/{participant_id}/followup-email")
    async def edit_followup_email(participant_id: str, payload: FollowupEditPayload, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        if not record.get("followup_body"):
            raise HTTPException(status_code=409, detail="Generate this follow-up email first")
        await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": {
            "followup_subject": payload.subject, "followup_body": payload.body, "followup_status": "Draft"}})
        return {"status": "Draft"}

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
        if "your_execution_timeline" not in structured:
            lines = ["FUNDRAISING PORTFOLIO", member_name, ""]
            for heading, key in FP_SECTIONS:
                value = str(structured.get(key, "") or "").strip()
                if value:
                    lines.extend([heading.upper(), value, ""])
            return "\n".join(lines).strip()
        lines = [str(structured.get("member_name") or member_name).upper(), "FUNDRAISING PORTFOLIO", ""]
        if structured.get("board_role"):
            lines.extend([f"Board Role: {structured['board_role']}", ""])
        _sd_block(lines, "About This Portfolio", structured.get("fundraising_plan_context", ""))
        _sd_block(lines, "Your Role in Our Fundraising Plan", structured.get("your_role_in_our_fundraising_plan", ""))
        _sd_block(lines, "Why Your Role Matters", structured.get("why_your_role_matters", ""))
        _sd_block(lines, "What You Will Help Us Accomplish", structured.get("what_you_will_help_us_accomplish") or [])
        _sd_block(lines, "Your Fundraising Responsibilities", structured.get("your_fundraising_responsibilities") or [])
        _sd_block(lines, "Who You Will Help Us Reach", structured.get("who_you_will_help_us_reach") or [])
        journeys = structured.get("how_you_will_help_build_relationships") or []
        if journeys:
            lines.extend(["HOW YOU WILL HELP BUILD RELATIONSHIPS", ""])
            for entry in journeys:
                if entry.get("stage") and entry.get("your_part"):
                    lines.append(f"{str(entry['stage']).upper()}: {entry['your_part']}")
            lines.append("")
        tools = structured.get("tools_you_can_use") or {}
        if (tools.get("available_now") or tools.get("being_prepared")):
            lines.append("TOOLS YOU CAN USE")
            if tools.get("available_now"):
                lines.append("Available Now:")
                lines.extend([f"  - {item}" for item in tools["available_now"] if item])
            if tools.get("being_prepared"):
                lines.append("Being Prepared:")
                lines.extend([f"  - {item}" for item in tools["being_prepared"] if item])
            lines.append("")
        _sd_block(lines, "Your Immediate Priorities", structured.get("your_immediate_priorities") or [])
        timeline = structured.get("your_execution_timeline") or {}
        horizon = str(timeline.get("horizon", "")).strip().upper()
        heading = f"YOUR FIRST {horizon.replace(' DAYS', '')} DAYS" if "DAY" in horizon else "YOUR EXECUTION TIMELINE"
        phases = timeline.get("phases") or []
        if phases:
            lines.extend([heading, ""])
            for phase in phases:
                if phase.get("period"):
                    lines.append(str(phase["period"]).upper())
                if phase.get("your_focus"):
                    lines.append(f"Your Focus: {phase['your_focus']}")
                if phase.get("how_it_supports_the_plan"):
                    lines.append(f"How It Supports the Plan: {phase['how_it_supports_the_plan']}")
                lines.append("")
        support = structured.get("support_and_resources") or {}
        if support.get("what_you_said_would_help") or support.get("what_the_organization_will_provide"):
            lines.append("SUPPORT AND RESOURCES")
            if support.get("what_you_said_would_help"):
                lines.append("What You Said Would Help:")
                lines.extend([f"  - {item}" for item in support["what_you_said_would_help"] if item])
            if support.get("what_the_organization_will_provide"):
                lines.append("What the Organization Will Provide:")
                lines.extend([f"  - {item}" for item in support["what_the_organization_will_provide"] if item])
            lines.append("")
        _sd_block(lines, "How We Will Work Together", structured.get("how_we_will_work_together", ""))
        _sd_block(lines, "Moving the Mission Forward", structured.get("moving_the_mission_forward", ""))
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
        toolkit_titles = "\n".join(f"- {tool.get('title', '')}" for key in ["email_tools", "text_tools", "call_scripts", "stewardship_tools", "strategy_specific_tools"]
                                   for tool in (toolkit.get("structured", {}) or {}).get(key, []) if tool.get("title")) if toolkit.get("status") == "Approved" else ""
        context = ("ORGANIZATION:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"],
                                                       "direction": intake.get("direction_12_24", "")}, indent=1)
                   + f"\n\nBOARD MEMBER: {record['name']} — Board Role: {record.get('role', 'Board Member')}"
                   + f"\n\nEXACT AGREED FUNDRAISING RESPONSIBILITY (founder-recorded — HIGHEST AUTHORITY; never expand or contradict it):\n{record['agreed_responsibility']}"
                   + "\n\nFINAL ADOPTED FUNDRAISING STRATEGY PLAN (read its actual 60/90/120-day execution horizon from this document — never assume 90 days):\n" + adoption.get("adopted_text", "")
                   + "\n\nPLAN ADOPTION CONCLUSION (actual Board-level decisions only):\n" + adoption.get("conclusion", "")
                   + "\n\nTHIS MEMBER'S OWN ORIGINAL FUNDRAISING PLANNING RESPONSE (supporting context only — never overrides the agreed responsibility):\n" + jsonlib.dumps(record.get("response", {}), indent=1, default=str)
                   + ("\n\nAPPROVED EXECUTION TOOLKIT TOOL TITLES (optional supplementary context — reference relevant titles by name only; never expand responsibility because a tool exists):\n" + toolkit_titles if toolkit_titles else ""))

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
