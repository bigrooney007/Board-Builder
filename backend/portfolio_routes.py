"""Board Fundraising Game Phase 6: Board Fundraising Portfolios and Execution Materials.
Portfolios assembled deterministically (no AI). One AI call per approved portfolio version = full Execution Pack."""
import asyncio
import calendar
import html
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timezone

import resend
from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ai_service import parse_json_response
from member_auth import authenticate_member, new_uuid, require_entitlement

GAME_ENTITLEMENT = "board_fundraising_game"

SYSTEM_ROLES = [
    ("recruit_team", "Help recruit people for the fundraising team", "Recruit people for the fundraising team"),
    ("identify_volunteers", "Help identify potential fundraising volunteers", "Identify potential fundraising volunteers"),
    ("manage_team", "Help manage or coordinate part of the fundraising team", "Manage or coordinate part of the fundraising team"),
    ("research_funders", "Help research potential funders", "Research potential funders"),
    ("identify_corporate_system", "Help identify corporate prospects", "Identify corporate prospects"),
    ("identify_grants_system", "Help identify grant opportunities", "Identify grant opportunities"),
    ("develop_materials", "Help develop fundraising materials", "Develop fundraising materials"),
    ("case_for_support", "Help develop the Case for Support", "Develop the Case for Support"),
    ("corporate_materials", "Help create corporate partnership materials", "Create corporate partnership materials"),
    ("improve_technology", "Help improve fundraising technology", "Improve fundraising technology"),
    ("crm_oversight", "Help select or oversee the CRM/donor system", "Select or oversee the CRM/donor system"),
    ("organise_data", "Help organise fundraising data", "Organise fundraising data"),
    ("develop_processes", "Help develop fundraising processes", "Develop fundraising processes"),
    ("communications", "Help with communications/content", "Support communications/content"),
    ("plan_events", "Help plan fundraising events", "Plan fundraising events"),
    ("monitor_execution", "Help monitor execution/accountability", "Monitor execution/accountability"),
    ("review_performance", "Help review fundraising performance", "Review fundraising performance"),
    ("other_system", "Other", "Other"),
]

DIRECT_ACTIVITIES = [
    ("identify_donors", "Identify potential donors", "Identify potential donors"),
    ("identify_corporate", "Identify potential businesses/corporate partners", "Identify potential businesses/corporate partners"),
    ("identify_grants", "Identify potential grant opportunities", "Identify potential grant opportunities"),
    ("make_introductions", "Make introductions", "Make introductions"),
    ("invite_funders", "Invite potential funders to meetings or events", "Invite potential funders to meetings or events"),
    ("cultivate_relationships", "Help cultivate relationships before an ask", "Help cultivate relationships before an ask"),
    ("attend_donor_meetings", "Attend donor meetings", "Attend donor meetings"),
    ("attend_corporate_meetings", "Attend corporate sponsor/partner meetings", "Attend corporate sponsor/partner meetings"),
    ("make_ask", "Personally make the ask", "Personally make the ask"),
    ("joint_ask", "Participate in an ask with someone else", "Participate in an ask with someone else"),
    ("follow_up", "Follow up with potential funders", "Follow up with potential funders"),
    ("steward_donors", "Steward existing donors", "Steward existing donors"),
    ("steward_corporate", "Steward corporate partners", "Steward corporate partners"),
    ("thank_supporters", "Thank supporters", "Thank supporters"),
    ("support_events", "Organise or support fundraising events", "Organise or support fundraising events"),
    ("promote_social", "Promote fundraising through my social media", "Promote fundraising through social media"),
    ("promote_professional", "Promote fundraising through my professional network", "Promote fundraising through professional networks"),
    ("share_campaigns", "Share fundraising campaigns with people I know", "Share fundraising campaigns"),
    ("host_gathering", "Host a small fundraising gathering", "Host a small fundraising gathering"),
    ("other_direct", "Other", "Other"),
]

SYSTEM_ROLE_BY_OPTION = {option: (key, label) for key, option, label in SYSTEM_ROLES}
SYSTEM_ROLE_BY_OPTION.update({label: (key, label) for key, _, label in SYSTEM_ROLES})
DIRECT_BY_OPTION = {option: (key, label) for key, option, label in DIRECT_ACTIVITIES}
DIRECT_BY_OPTION.update({label: (key, label) for key, _, label in DIRECT_ACTIVITIES})

V3_BUILD_ROLE_MAP = {
    "Identify potential funders": "research_funders",
    "Research potential funders": "research_funders",
    "Recruit people to help with fundraising": "recruit_team",
    "Manage or coordinate the fundraising team": "manage_team",
    "Build or manage the CRM / donor database": "crm_oversight",
    "Set up or manage fundraising technology": "improve_technology",
    "Create or improve fundraising materials": "develop_materials",
    "Create fundraising content": "communications",
    "Manage follow-up and relationship tracking": "develop_processes",
    "Help organize fundraising events": "plan_events",
    "Track fundraising activity and results": "review_performance",
    "Help improve the fundraising strategy and process": "develop_processes",
}
V3_RAISE_ACTIVITY_MAP = {
    "Introduce the organization to people I know": "make_introductions",
    "Introduce the organization to businesses I know": "make_introductions",
    "Introduce the organization to grantmakers or funders I know": "make_introductions",
    "Identify potential individual donors": "identify_donors",
    "Identify potential business partners or sponsors": "identify_corporate",
    "Identify potential grant opportunities": "identify_grants",
    "Attend donor or funder meetings": "attend_donor_meetings",
    "Make fundraising asks": "make_ask",
    "Follow up with potential funders": "follow_up",
    "Build relationships with potential funders": "cultivate_relationships",
    "Steward and thank existing funders": "steward_donors",
    "Invite people to fundraising events": "invite_funders",
    "Share fundraising campaigns and content with my network": "share_campaigns",
    "Host a small gathering or introduction meeting": "host_gathering",
}
SYSTEM_KEYS = {key for key, _, _ in SYSTEM_ROLES}
DIRECT_KEYS = {key for key, _, _ in DIRECT_ACTIVITIES}

AUDIENCE_RELEVANT_KEYS = {"identify_donors", "identify_corporate", "identify_grants", "make_introductions",
                          "invite_funders", "cultivate_relationships", "make_ask", "joint_ask", "follow_up",
                          "host_gathering", "share_campaigns"}

INVOLVEMENT_DISPLAY = {"I can lead": "Lead", "I can actively support": "Actively Support", "I can advise when needed": "Advise"}

COMMITMENT_KEYWORDS = [
    (r"introduc", ["make_introductions"]),
    (r"steward|thank", ["steward_corporate", "steward_donors", "thank_supporters"]),
    (r"crm|donor system|database", ["crm_oversight"]),
    (r"grant", ["identify_grants", "identify_grants_system"]),
    (r"event|gathering", ["support_events", "plan_events", "host_gathering"]),
    (r"social media", ["promote_social"]),
    (r"volunteer", ["identify_volunteers"]),
    (r"recruit", ["recruit_team"]),
    (r"research", ["research_funders"]),
    (r"case for support", ["case_for_support"]),
    (r"material", ["develop_materials", "corporate_materials"]),
    (r"technolog", ["improve_technology"]),
    (r"data", ["organise_data"]),
    (r"corporate|business|company", ["identify_corporate", "attend_corporate_meetings", "identify_corporate_system"]),
    (r"donor", ["identify_donors", "attend_donor_meetings"]),
    (r"follow.?up", ["follow_up"]),
]

MATERIALS_MAP = {
    "identify_donors": ["Ideal Donor Identification Guide", "Prospect Research Checklist (Name, Connection to mission, Connection to organisation, Giving capacity indicators, Existing relationship, Who can make introduction, Reason they may care, Best next action)", "Personal Network Discovery Questions", "Prospect Submission Template"],
    "identify_corporate": ["Ideal Business Partner Guide", "Corporate Prospect Research Checklist (Company, Industry, Location, Mission alignment, CSR/community priorities, Audience overlap, Existing relationship, Decision-maker, Potential partnership reason, Suggested next action)", "Corporate Prospect Submission Template"],
    "identify_grants": ["Grant Opportunity Fit Guide", "Grant Research Checklist (Funder, Programme, Funding focus, Geography, Population, Amount available, Deadline, Eligibility, Mission fit, Purpose fit, Restrictions, Next action)", "Grant Go/No-Go Checklist", "Grant Opportunity Submission Template"],
    "make_introductions": ["Warm Introduction Email", "LinkedIn Introduction Message", "Text/WhatsApp Introduction Message", "Verbal Introduction Script", "Introduction Handoff Checklist", "Follow-Up Message If The Person Does Not Respond"],
    "invite_funders": ["Meeting Invitation Email", "Event Invitation Email", "LinkedIn Invitation", "Text/WhatsApp Invitation", "Follow-Up Invitation", "Confirmation Message"],
    "cultivate_relationships": ["Cultivation Conversation Guide", "Discovery Questions", "30-Day Relationship-Building Plan", "Impact Follow-Up Email", "Invitation To Learn More", "Signals That The Relationship May Be Ready For An Ask"],
    "attend_donor_meetings": ["Donor Meeting Preparation Checklist", "Board Member Role During The Meeting", "Questions To Ask", "Mission Talking Points", "Notes To Capture", "Post-Meeting Follow-Up Checklist"],
    "attend_corporate_meetings": ["Corporate Meeting Preparation Checklist", "Business Discovery Questions", "Partnership Talking Points", "Board Member Role During The Meeting", "Information To Capture", "Follow-Up Checklist"],
    "make_ask": ["Ask Preparation Sheet", "Donation Ask Conversation Script", "Transition Into The Ask", "Example Ask Language", "Common Questions And Suggested Responses", "What To Do If They Say Yes", "What To Do If They Say Maybe", "What To Do If They Say No", "Follow-Up Email"],
    "joint_ask": ["Joint Ask Preparation Guide", "Who Says What", "Board Member Supporting Role", "Questions The Board Member Can Answer", "Follow-Up Responsibilities"],
    "follow_up": ["First Follow-Up Email", "Second Follow-Up Email", "Final Follow-Up Email", "Follow-Up Call Script", "Follow-Up Tracking Checklist"],
    "steward_donors": ["Donor Stewardship Guide", "Thank-You Email", "Thank-You Call Script", "Impact Update Email", "Personal Check-In Message", "90-Day Stewardship Touchpoint Plan", "Renewal/Continued Support Conversation Guide"],
    "steward_corporate": ["Corporate Partner Stewardship Guide", "Thank-You Email", "Impact Update Template", "Partnership Check-In Agenda", "Employee Engagement Follow-Up Ideas", "Partnership Renewal Conversation Guide", "90-Day Corporate Stewardship Plan"],
    "thank_supporters": ["Thank-You Email", "Thank-You Call Script", "Thank-You Text Message", "Handwritten Note Template", "Impact Follow-Up Reminder"],
    "support_events": ["Event Fundraising Checklist", "Board Member Event Role Checklist", "Guest Invitation Template", "Sponsor Invitation Template", "Event Follow-Up Message", "Post-Event Prospect Follow-Up Checklist"],
    "promote_social": ["Social Media Promotion Guide", "LinkedIn Post", "Facebook Post", "Instagram Caption", "Short Campaign Update", "Direct Message To A Contact", "Content Sharing Schedule"],
    "promote_professional": ["Professional Network Email", "LinkedIn Message", "Professional Group Post", "Conversation Talking Points", "Introduction Request"],
    "share_campaigns": ["Campaign Sharing Email", "Personal Social Post", "Text/WhatsApp Message", "LinkedIn Message", "Follow-Up Sharing Message"],
    "host_gathering": ["Small Gathering Planning Checklist", "Guest List Planning Guide", "Invitation Email", "Invitation Message", "Simple Gathering Agenda", "Mission Introduction Script", "Transition To Support Conversation", "Follow-Up Email"],
    "recruit_team": ["Role Definition Worksheet", "Candidate Profile", "Recruitment Message", "Outreach Email", "Interview/Conversation Questions", "Recruitment Tracking Checklist"],
    "identify_volunteers": ["Role Definition Worksheet", "Candidate Profile", "Recruitment Message", "Outreach Email", "Interview/Conversation Questions", "Recruitment Tracking Checklist"],
    "manage_team": ["Fundraising Team Coordination Guide", "Weekly Meeting Agenda", "Responsibility Tracker Structure", "Follow-Up Checklist", "Accountability Questions"],
    "research_funders": ["Prospect Research Guide", "Research Fields", "Qualification Checklist", "Prospect Summary Template"],
    "identify_corporate_system": ["Ideal Business Partner Guide", "Corporate Prospect Research Checklist", "Corporate Prospect Submission Template"],
    "identify_grants_system": ["Grant Opportunity Fit Guide", "Grant Research Checklist", "Grant Go/No-Go Checklist", "Grant Opportunity Submission Template"],
    "develop_materials": ["Fundraising Materials Development Checklist", "Information Collection Checklist", "Review Checklist", "Approval Workflow"],
    "case_for_support": ["Case For Support Development Guide", "Required Information Checklist", "Recommended Structure (The Need, The Organisation, The Solution, The Impact, The Opportunity, The Ask)", "Review Questions"],
    "corporate_materials": ["Corporate Partnership Material Checklist", "Partnership Value Proposition Worksheet", "Sponsorship/Partnership Offer Structure", "Corporate Review Checklist"],
    "improve_technology": ["Fundraising Technology Needs Checklist", "Technology Evaluation Criteria", "Current System Review Questions", "Implementation Planning Checklist"],
    "crm_oversight": ["CRM Requirements Checklist", "CRM Evaluation Scorecard", "Data Fields Checklist", "Implementation Checklist", "CRM Governance Checklist"],
    "organise_data": ["Fundraising Data Organisation Checklist", "Recommended Data Categories", "Prospect Record Structure", "Donor Record Structure", "Data Maintenance Routine"],
    "develop_processes": ["Fundraising Process Design Guide using the adopted KNOW - LIKE - TRUST - ASK - FOLLOW UP - STEWARD framework", "Process Responsibility Checklist", "Handoff Checklist", "Process Review Questions"],
    "communications": ["Fundraising Communications Checklist", "Content Planning Guide", "Story Collection Questions", "Impact Content Template", "Monthly Content Planning Structure"],
    "plan_events": ["Fundraising Event Planning Checklist", "Responsibility Matrix", "Event Timeline", "Sponsor/Donor Engagement Checklist", "Post-Event Follow-Up Plan"],
    "monitor_execution": ["Fundraising Accountability Checklist", "Weekly Execution Review Questions", "Monthly Board Fundraising Review Template", "Action Tracker Structure", "Escalation Questions"],
    "review_performance": ["Fundraising Performance Review Guide", "Metrics To Review (prospects identified, introductions made, meetings held, asks made, follow-ups completed, new donors, new corporate partners, grants submitted, grants awarded, money raised, stewardship activity — where relevant)", "Monthly Performance Review Questions", "Strategy Adjustment Checklist"],
}
CUSTOM_MATERIALS = ["Execution Guide", "First Actions", "Checklist", "Relevant Scripts Or Templates — only where directly useful"]

EXECUTION_SYSTEM_MESSAGE = """You are the Execution Material Generator for the Board Fundraising Game.
Your job is to equip one nonprofit board member to execute the specific responsibilities they approved in their Board Fundraising Portfolio.
Use the organisation's Adopted Fundraising Strategy as the authoritative fundraising context.
Generate only the materials required for the board member's approved responsibilities.
Personalise the materials using the organisation's real mission, fundraising goal, fundraising purpose, priority audiences, fundraising process and relevant strategy information.
Do not invent donor names, prospect names, company names, grantmaker names, existing relationships, commitments, financial results or organisational facts.
Where a specific name or amount is required but has not been provided, use a clear placeholder such as [Prospect Name], [Company Name], [Funder Name] or [Ask Amount].
Do not assign the board member responsibilities outside their approved portfolio.
Do not include fundraising activities they explicitly rejected or did not approve.
Make every script, checklist, template and guide practical enough to use immediately.
Keep the language professional, natural and concise.
Return only structured JSON using the required output schema."""

EXECUTION_OUTPUT_SCHEMA = {
    "board_member_name": "string",
    "organisation_name": "string",
    "portfolio_summary": "string — 2-3 concise sentences summarising this board member's approved fundraising role",
    "material_packs": [{
        "role_key": "string — the role/activity key supplied in the context",
        "role_title": "string — the role/activity title supplied in the context",
        "pack_title": "string — a natural pack title for this responsibility",
        "materials": [{
            "material_type": "string — email | message | script | checklist | guide | template | plan | questions | structure",
            "title": "string — the required material title",
            "purpose": "string — one concise sentence explaining when to use it",
            "content": "string — the complete ready-to-use material as plain text (use line breaks and simple dashes for lists; no markdown headings, no HTML)",
        }],
    }],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def months_from_now_iso(months: int = 6) -> str:
    current = datetime.now(timezone.utc)
    month_index = current.month - 1 + months
    year = current.year + month_index // 12
    month = month_index % 12 + 1
    day = min(current.day, calendar.monthrange(year, month)[1])
    return current.replace(year=year, month=month, day=day).isoformat()


def fmt_goal(profile: dict) -> str:
    amount = (profile.get("goal") or {}).get("amount") or 0
    return f"${int(amount):,}" if amount else ""


def fmt_deadline(profile: dict) -> str:
    raw = (profile.get("goal") or {}).get("deadline", "")
    if not raw:
        return ""
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%B %-d, %Y")
    except Exception:
        return raw


def match_commitment_keys(text: str, available_keys: set) -> str:
    lowered = str(text).lower()
    for pattern, keys in COMMITMENT_KEYWORDS:
        if re.search(pattern, lowered):
            for key in keys:
                if key in available_keys:
                    return key
    return ""


def clean_item(item: dict, kind: str) -> dict:
    key = str(item.get("role_key" if kind == "system" else "activity_key", "")).strip()[:60] or "custom"
    valid = SYSTEM_KEYS if kind == "system" else DIRECT_KEYS
    if key not in valid and key != "custom":
        key = "custom"
    cleaned = {
        ("role_key" if kind == "system" else "activity_key"): key,
        "label": str(item.get("label", "")).strip()[:200],
        "source": item.get("source") if item.get("source") in {"individual_game", "individual_game_v3", "meeting_commitment", "organisation_added"} else "organisation_added",
        "member_note": str(item.get("member_note", ""))[:4000],
        "commitment": str(item.get("commitment", ""))[:4000],
        "deadline": str(item.get("deadline", ""))[:120],
        "requires_confirmation": bool(item.get("requires_confirmation")),
        "active": bool(item.get("active", True)),
        "item_id": str(item.get("item_id", "")) or new_uuid(),
    }
    if kind == "system":
        cleaned["involvement"] = str(item.get("involvement", ""))[:80]
    else:
        cleaned["audiences"] = [str(a)[:200] for a in (item.get("audiences") or [])][:12]
    return cleaned


class EditPayload(BaseModel):
    system_roles: list = Field(default_factory=list)
    direct_activities: list = Field(default_factory=list)
    additional_commitments: list = Field(default_factory=list)
    org_note: str = Field(default="", max_length=6000)


class StatusPayload(BaseModel):
    status: str = Field(min_length=1)


class SendPayload(BaseModel):
    origin_url: str = Field(min_length=1)


class RespondPayload(BaseModel):
    action: str = Field(min_length=1)
    comment: str = Field(default="", max_length=8000)


class GeneratePayload(BaseModel):
    origin_url: str = Field(default="")

class AssistantPayload(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    material_type: str = Field(default="", max_length=160)


def create_portfolio_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def game_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {GAME_ENTITLEMENT})
        return member

    async def get_profile(user_id: str) -> dict:
        return await db.game_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}

    async def ensure_execution_access(user_id: str) -> dict:
        scope_id=f"fundraising:{user_id}"
        existing=await db.executive_assistant_access.find_one({"scope_id":scope_id},{"_id":0})
        if existing:return existing
        profile=await get_profile(user_id);primary=profile.get("primary_user") or {};organization=profile.get("organization") or {};started=now_iso()
        record={"scope_id":scope_id,"product":"board-fundraising-game","user_id":user_id,"organization_name":organization.get("name",""),
            "leader_name":primary.get("full_name",""),"leader_email":primary.get("email",""),"started_at":started,
            "included_until":months_from_now_iso(6),"subscription_status":"included","created_at":started,"updated_at":started}
        await db.executive_assistant_access.insert_one(record.copy());return record

    def execution_access_state(access: dict) -> str:
        if access.get("subscription_status")=="active":return "active"
        try:
            if datetime.fromisoformat(str(access.get("included_until","")).replace("Z","+00:00"))>datetime.now(timezone.utc):
                return "included"
        except Exception:
            pass
        return "renewal_required"

    async def meter_assistant(scope_id: str, portfolio: dict, request_text: str, answer: str, material: str=""):
        await db.executive_assistant_usage.insert_one({"usage_id":new_uuid(),"scope_id":scope_id,"product":"board-fundraising-game",
            "portfolio_id":portfolio.get("portfolio_id",""),"member_name":portfolio.get("member_name",""),"material_type":material,
            "input_characters":len(request_text),"output_characters":len(answer),"created_at":now_iso()})

    async def adopted_strategy(user_id: str) -> dict:
        strategy = await db.game_strategies.find_one(
            {"user_id": user_id, "status": "adopted"}, {"_id": 0}, sort=[("adopted_at", -1)])
        if not strategy:
            raise HTTPException(status_code=409, detail="Adopt a fundraising strategy before creating Board Fundraising Portfolios")
        return strategy

    async def get_portfolio(user_id: str, portfolio_id: str) -> dict:
        portfolio = await db.board_portfolios.find_one(
            {"portfolio_id": portfolio_id, "user_id": user_id}, {"_id": 0})
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return portfolio

    async def portfolio_by_token(token: str) -> dict:
        portfolio = await db.board_portfolios.find_one({"token": token}, {"_id": 0})
        if not portfolio:
            raise HTTPException(status_code=404, detail="This portfolio link is not valid")
        return portfolio

    def strategy_audiences(strategy: dict) -> list:
        data = (strategy.get("data") or {}).get("fundraising_audiences") or {}
        priorities = data.get("priorities") or []
        if not priorities:
            priorities = [item for key in ("individuals", "businesses", "grantors") for item in (data.get(key) or [])]
        return [str(item.get("title", "")).strip() for item in priorities if isinstance(item, dict) and item.get("title")][:10]

    async def toolkit_for(portfolio: dict) -> dict:
        return await db.execution_toolkits.find_one(
            {"portfolio_id": portfolio["portfolio_id"], "portfolio_version": portfolio.get("approved_version") or portfolio.get("version", 1)},
            {"_id": 0}, sort=[("created_at", -1)]) or {}

    # ---------- Preparation (deterministic, no AI) ----------

    async def build_draft(user_id: str, record: dict, strategy: dict, commitments: list) -> dict:
        member_id = record["member_id"]
        audiences = strategy_audiences(strategy)
        system_response = await db.game_section_responses.find_one(
            {"user_id": user_id, "board_member_id": member_id, "section_id": 9}, {"_id": 0}) or {}
        direct_response = await db.game_section_responses.find_one(
            {"user_id": user_id, "board_member_id": member_id, "section_id": 10}, {"_id": 0}) or {}
        participation_response = await db.game_section_responses.find_one(
            {"user_id": user_id, "board_member_id": member_id, "section_id": 5}, {"_id": 0}) or {}
        participation = participation_response.get("extras") or {}
        audience_response = await db.game_audience_responses.find_one(
            {"user_id": user_id, "board_member_id": member_id, "completed": True}, {"_id": 0}) or {}
        system_roles = []
        for pref in system_response.get("preferences") or []:
            mapping = SYSTEM_ROLE_BY_OPTION.get(str(pref.get("option", "")).strip())
            if not mapping:
                continue
            key, label = mapping
            system_roles.append({
                "item_id": new_uuid(), "role_key": key, "label": label, "source": "individual_game",
                "involvement": str(pref.get("involvement", "")), "member_note": str(pref.get("note", "")),
                "commitment": "", "deadline": "", "requires_confirmation": False, "active": True,
            })
        if not system_roles:
            for option in participation.get("build") or []:
                option=str(option).strip()
                if not option:continue
                key=V3_BUILD_ROLE_MAP.get(option,"custom")
                label=option if key!="custom" else (str(participation.get("build_other","")).strip() or option)
                system_roles.append({"item_id":new_uuid(),"role_key":key,"label":label,"source":"individual_game_v3",
                    "involvement":"","member_note":"","commitment":"","deadline":"","requires_confirmation":False,"active":True})
        direct_activities = []
        for pref in direct_response.get("preferences") or []:
            mapping = DIRECT_BY_OPTION.get(str(pref.get("option", "")).strip())
            if not mapping:
                continue
            key, label = mapping
            direct_activities.append({
                "item_id": new_uuid(), "activity_key": key, "label": label, "source": "individual_game",
                "member_note": str(pref.get("note", "")), "commitment": "", "deadline": "",
                "audiences": audiences if key in AUDIENCE_RELEVANT_KEYS else [],
                "requires_confirmation": False, "active": True,
            })
        if not direct_activities:
            for option in participation.get("raise") or []:
                option=str(option).strip()
                if not option:continue
                key=V3_RAISE_ACTIVITY_MAP.get(option,"custom")
                label=option if key!="custom" else (str(participation.get("raise_other","")).strip() or option)
                direct_activities.append({"item_id":new_uuid(),"activity_key":key,"label":label,"source":"individual_game_v3",
                    "member_note":"","commitment":"","deadline":"","audiences":audiences if key in AUDIENCE_RELEVANT_KEYS else [],
                    "requires_confirmation":False,"active":True})
        do_not_want = [str(item) for item in (direct_response.get("do_not_want") or [])]
        member_commitments = [c for c in commitments if c.get("board_member_id") == member_id]
        additional = []
        available = {role["role_key"] for role in system_roles} | {act["activity_key"] for act in direct_activities}
        for commitment in member_commitments:
            text = commitment.get("edited_commitment") or commitment.get("commitment") or ""
            if not text.strip():
                continue
            matched = match_commitment_keys(text, available)
            attached = False
            if matched:
                for role in system_roles:
                    if role["role_key"] == matched and not role["commitment"]:
                        role["commitment"] = text
                        role["deadline"] = role["deadline"] or str(commitment.get("deadline", ""))
                        role["source"] = role["source"] if role["source"] == "individual_game" else "meeting_commitment"
                        attached = True
                        break
                if not attached:
                    for act in direct_activities:
                        if act["activity_key"] == matched and not act["commitment"]:
                            act["commitment"] = text
                            act["deadline"] = act["deadline"] or str(commitment.get("deadline", ""))
                            attached = True
                            break
            if not attached:
                additional.append({"text": text, "deadline": str(commitment.get("deadline", ""))})
        final_team_roles=(strategy.get("data") or {}).get("board_roles") or (strategy.get("data") or {}).get("team_roles") or []
        full_name=str(record.get("full_name","")).strip()
        full_key=re.sub(r"[^a-z0-9 ]","",full_name.lower()).strip()
        first_key=(full_key.split() or [""])[0]
        for final_role in final_team_roles:
            if not isinstance(final_role,dict):continue
            assigned=str(final_role.get("name") or final_role.get("assigned","")).strip()
            assigned_key=re.sub(r"[^a-z0-9 ]","",assigned.lower()).strip()
            if not assigned_key or assigned_key=="role capacity needed":continue
            if assigned_key!=full_key and assigned_key!=first_key and full_key not in assigned_key:continue
            role_title=str(final_role.get("role","")).strip() or "Board fundraising responsibility"
            responsibility=str(final_role.get("responsibility","")).strip()
            combined=(role_title+(f": {responsibility}" if responsibility else "")).strip()
            matched=match_commitment_keys(combined,available);attached=False
            if matched:
                for role in system_roles:
                    if role.get("role_key")==matched:
                        role["commitment"]=responsibility or role.get("commitment","")
                        role["label"]=role.get("label") or role_title
                        role["source"]="meeting_commitment";attached=True;break
                if not attached:
                    for activity in direct_activities:
                        if activity.get("activity_key")==matched:
                            activity["commitment"]=responsibility or activity.get("commitment","")
                            activity["label"]=activity.get("label") or role_title
                            activity["source"]="meeting_commitment";attached=True;break
            if not attached:
                role_key_text=re.sub(r"[^a-z0-9 ]","",role_title.lower()).strip()
                if not any(re.sub(r"[^a-z0-9 ]","",str(role.get("label","")).lower()).strip()==role_key_text and str(role.get("commitment","")).strip()==responsibility for role in system_roles):
                    system_roles.append({"item_id":new_uuid(),"role_key":"custom","label":role_title,"source":"meeting_commitment",
                        "involvement":"Board-agreed responsibility","member_note":"","commitment":responsibility,"deadline":"",
                        "requires_confirmation":False,"active":True})
        involvement = str(audience_response.get("involvement") or "").strip()
        if involvement and not any(involvement in str(item.get("commitment") or "") for item in system_roles + direct_activities):
            additional.append({"text": involvement, "deadline": ""})
        if str(participation.get("additional_idea","")).strip():
            additional.append({"text":str(participation.get("additional_idea","")).strip(),"deadline":""})
        return {
            "portfolio_id": new_uuid(), "user_id": user_id,
            "board_member_id": member_id, "member_name": record["full_name"],
            "member_email": record.get("email", ""),
            "strategy_id": strategy["strategy_id"],
            "token": secrets.token_urlsafe(24),
            "status": "draft", "version": 1, "approved_version": 0,
            "system_roles": system_roles, "direct_activities": direct_activities,
            "additional_commitments": additional,
            "do_not_want": do_not_want,
            "availability": str(participation.get("time","")),
            "org_note": "", "change_request": "",
            "sent_at": "", "approved_at": "", "approved_snapshot": None,
            "created_at": now_iso(), "updated_at": now_iso(),
        }

    @router.post("/game/portfolios/prepare")
    async def prepare_portfolios(request: Request):
        member = await game_member(request)
        strategy = await adopted_strategy(member["user_id"])
        review_id = strategy.get("meeting_review_id", "")
        commitments = await db.meeting_execution_commitments.find(
            {"review_id": review_id, "review_status": {"$in": ["keep", "edited"]}}, {"_id": 0}).to_list(500) if review_id else []
        records = await db.game_board_members.find(
            {"user_id": member["user_id"], "removed": {"$ne": True}}, {"_id": 0}).sort("created_at", 1).to_list(200)
        group_session = await db.group_game_sessions.find_one(
            {"user_id": member["user_id"], "status": {"$ne": "archived"}},
            {"_id": 0, "session_id": 1},
            sort=[("created_at", -1)],
        )
        joined_ids = set()
        if group_session:
            joined_rows = await db.group_game_participants.find(
                {"session_id": group_session["session_id"]},
                {"_id": 0, "board_member_id": 1},
            ).to_list(300)
            joined_ids = {row.get("board_member_id") for row in joined_rows}
        participating_records = []
        for record in records:
            audience_response = await db.game_audience_responses.find_one({
                "user_id": member["user_id"],
                "board_member_id": record["member_id"],
                "completed": True,
            }, {"_id": 0, "response_id": 1})
            response_count = await db.game_section_responses.count_documents({
                "user_id": member["user_id"],
                "board_member_id": record["member_id"],
                "completed": True,
            })
            if audience_response or response_count > 0 or record["member_id"] in joined_ids:
                participating_records.append(record)
        created = 0
        for record in participating_records:
            existing = await db.board_portfolios.find_one(
                {"user_id": member["user_id"], "board_member_id": record["member_id"]}, {"_id": 0, "portfolio_id": 1})
            if existing:
                continue
            draft = await build_draft(member["user_id"], record, strategy, commitments)
            await db.board_portfolios.insert_one(draft.copy())
            created += 1
        return {"status": "prepared", "created": created}

    # ---------- Organisation dashboard ----------

    @router.get("/game/portfolios")
    async def list_portfolios(request: Request):
        member = await game_member(request)
        strategy = await adopted_strategy(member["user_id"])
        profile = await get_profile(member["user_id"])
        rows = await db.board_portfolios.find(
            {"user_id": member["user_id"]}, {"_id": 0}).sort("created_at", 1).to_list(300)
        portfolios = []
        toolkit_ready = 0
        approved = 0
        founder_approved = 0
        for row in rows:
            toolkit = await toolkit_for(row)
            ready = toolkit.get("status") == "ready"
            if ready:
                toolkit_ready += 1
            if row["status"] in {"ready_to_send", "sent", "approved", "materials_ready"}:
                founder_approved += 1
            if row["status"] in {"approved", "materials_ready"}:
                approved += 1
            portfolios.append({
                "portfolio_id": row["portfolio_id"], "member_name": row["member_name"],
                "status": row["status"],
                "system_count": len([r for r in row.get("system_roles", []) if r.get("active", True)]),
                "direct_count": len([a for a in row.get("direct_activities", []) if a.get("active", True)]),
                "change_request": row.get("change_request", ""),
                "toolkit_status": toolkit.get("status", "not_generated"),
                "sent_at": row.get("sent_at", ""), "approved_at": row.get("approved_at", ""),
            })
        access=await ensure_execution_access(member["user_id"]) if approved>=1 else {}
        return {
            "goal_display": fmt_goal(profile), "goal_deadline": fmt_deadline(profile),
            "strategy_id": strategy["strategy_id"],
            "portfolios": portfolios,
            "total": len(portfolios), "founder_approved_count": founder_approved,
            "approved_count": approved, "toolkit_ready_count": toolkit_ready,
            "execution_ready": approved >= 1,
            "executive_assistant_access":{"status":execution_access_state(access) if access else "not_started","included_until":access.get("included_until","") if access else ""},
        }

    @router.get("/game/portfolios/{portfolio_id}")
    async def portfolio_detail(portfolio_id: str, request: Request):
        member = await game_member(request)
        portfolio = await get_portfolio(member["user_id"], portfolio_id)
        profile = await get_profile(member["user_id"])
        strategy = await adopted_strategy(member["user_id"])
        toolkit = await toolkit_for(portfolio)
        return {
            "portfolio": portfolio,
            "organization_name": (profile.get("organization") or {}).get("name", ""),
            "goal_display": fmt_goal(profile), "goal_deadline": fmt_deadline(profile),
            "strategy_share_token": strategy.get("share_token", ""),
            "strategy_audiences": strategy_audiences(strategy),
            "toolkit_status": toolkit.get("status", "not_generated"),
            "catalog": {
                "system_roles": [{"role_key": key, "label": label} for key, _, label in SYSTEM_ROLES],
                "direct_activities": [{"activity_key": key, "label": label} for key, _, label in DIRECT_ACTIVITIES],
                "involvement_options": list(INVOLVEMENT_DISPLAY.keys()),
            },
        }

    @router.put("/game/portfolios/{portfolio_id}")
    async def edit_portfolio(portfolio_id: str, payload: EditPayload, request: Request):
        member = await game_member(request)
        portfolio = await get_portfolio(member["user_id"], portfolio_id)
        if portfolio["status"] in {"approved", "materials_ready"}:
            raise HTTPException(status_code=409, detail="An approved portfolio can no longer be edited directly")
        do_not_want = set(portfolio.get("do_not_want") or [])
        system_roles = [clean_item(item, "system") for item in (payload.system_roles or [])[:60] if isinstance(item, dict)]
        direct_activities = []
        for item in (payload.direct_activities or [])[:60]:
            if not isinstance(item, dict):
                continue
            cleaned = clean_item(item, "direct")
            if cleaned["label"] in do_not_want and cleaned["source"] == "organisation_added":
                cleaned["requires_confirmation"] = True
            direct_activities.append(cleaned)
        additional = []
        for item in (payload.additional_commitments or [])[:60]:
            if isinstance(item, dict) and str(item.get("text", "")).strip():
                additional.append({"text": str(item.get("text", ""))[:4000], "deadline": str(item.get("deadline", ""))[:120]})
        await db.board_portfolios.update_one(
            {"portfolio_id": portfolio_id},
            {"$set": {"system_roles": system_roles, "direct_activities": direct_activities,
                      "additional_commitments": additional, "org_note": payload.org_note.strip(),
                      "updated_at": now_iso()}})
        return {"status": "saved"}

    @router.post("/game/portfolios/{portfolio_id}/status")
    async def set_status(portfolio_id: str, payload: StatusPayload, request: Request):
        member = await game_member(request)
        portfolio = await get_portfolio(member["user_id"], portfolio_id)
        if payload.status not in {"ready_to_send", "draft"}:
            raise HTTPException(status_code=422, detail="Invalid status")
        if portfolio["status"] in {"approved", "materials_ready"}:
            raise HTTPException(status_code=409, detail="This portfolio is already approved")
        await db.board_portfolios.update_one(
            {"portfolio_id": portfolio_id}, {"$set": {"status": payload.status, "updated_at": now_iso()}})
        return {"status": payload.status}

    # ---------- Emails ----------

    def signature_html(profile: dict, member: dict) -> str:
        primary = profile.get("primary_user") or {}
        organization = profile.get("organization") or {}
        lines = [
            primary.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
            primary.get("job_title", ""), organization.get("name", ""), organization.get("website", ""),
        ]
        return "".join(f"<p style='margin:2px 0;'>{html.escape(line)}</p>" for line in lines if line and line.strip())

    def game_button(link: str, label: str) -> str:
        return (f"<p style='margin:22px 0;'><a href='{html.escape(link)}' "
                f"style='background:#4f46e5;color:#ffffff;padding:13px 26px;border-radius:999px;"
                f"text-decoration:none;font-weight:bold;display:inline-block;'>{html.escape(label)}</a></p>")

    async def send_game_email(to_email: str, reply_to: str, subject: str, body_html: str, raise_on_error: bool = True):
        try:
            resend.api_key = os.environ["RESEND_API_KEY"]
            await resend.Emails.send_async({
                "from": os.environ["GAME_EMAIL_SENDER"], "to": [to_email],
                "reply_to": reply_to, "subject": subject,
                "html": f"<div style='max-width:600px;margin:auto;font-family:Arial,sans-serif;color:#111;line-height:1.6;'>{body_html}</div>",
            })
        except Exception as exc:
            if raise_on_error:
                raise HTTPException(status_code=502, detail="The email could not be sent. Please try again.") from exc

    async def send_portfolio_email(member: dict, portfolio: dict, profile: dict, origin: str):
        organization = (profile.get("organization") or {}).get("name", "your organisation")
        first_name = portfolio["member_name"].split(" ")[0]
        link = f"{origin.rstrip('/')}/board-portfolio/{portfolio['token']}"
        assistant_link = f"{origin.rstrip('/')}/board-assistant/{portfolio['token']}"
        body = (
            f"<p>Hi {html.escape(first_name)},</p>"
            f"<p>Thank you for helping {html.escape(organization)} build and adopt its fundraising strategy.</p>"
            f"<p>Your Board Fundraising Portfolio is now ready.</p>"
            f"<p>Your portfolio shows how you will help raise money for our organization and the commitments you made during Game Night.</p>"
            f"<p>Please review your portfolio and confirm that it accurately reflects how you want to participate.</p>"
            f"{game_button(link, 'Review My Board Fundraising Portfolio')}"
            f"<p>You can also view the fundraising strategy your board adopted during Game Night from inside your portfolio.</p>"
            f"<p>After you approve your portfolio, bookmark your personal fundraising assistant. It will help you execute your agreed role and create the materials you need.</p>"
            f"{game_button(assistant_link, 'Bookmark My Fundraising Assistant')}"
            f"<div style='margin-top:26px;'>{signature_html(profile, member)}</div>"
        )
        subject = f"Your Board Fundraising Portfolio For {organization} Is Ready"
        await send_game_email(portfolio["member_email"], member["email"], subject, body)

    @router.post("/game/portfolios/{portfolio_id}/send")
    async def send_portfolio(portfolio_id: str, payload: SendPayload, request: Request):
        member = await game_member(request)
        portfolio = await get_portfolio(member["user_id"], portfolio_id)
        if not portfolio.get("member_email"):
            raise HTTPException(status_code=409, detail="This board member has no email address")
        profile = await get_profile(member["user_id"])
        await send_portfolio_email(member, portfolio, profile, payload.origin_url)
        updates = {"sent_at": now_iso(), "updated_at": now_iso()}
        if portfolio["status"] in {"ready_to_send", "change_requested"}:
            updates["status"] = "sent"
            if portfolio["status"] == "change_requested":
                updates["version"] = portfolio.get("version", 1) + 1
                updates["change_request"] = ""
        await db.board_portfolios.update_one({"portfolio_id": portfolio_id}, {"$set": updates})
        return {"status": "sent"}

    @router.post("/game/portfolios/send-all")
    async def send_all_ready(payload: SendPayload, request: Request):
        member = await game_member(request)
        profile = await get_profile(member["user_id"])
        rows = await db.board_portfolios.find(
            {"user_id": member["user_id"], "status": "ready_to_send"}, {"_id": 0}).to_list(300)
        sent = 0
        for portfolio in rows:
            if not portfolio.get("member_email"):
                continue
            try:
                await send_portfolio_email(member, portfolio, profile, payload.origin_url)
            except HTTPException:
                continue
            await db.board_portfolios.update_one(
                {"portfolio_id": portfolio["portfolio_id"]},
                {"$set": {"status": "sent", "sent_at": now_iso(), "updated_at": now_iso()}})
            sent += 1
        return {"status": "sent", "count": sent}

    @router.get("/game/portfolios/{portfolio_id}/toolkit")
    async def org_view_toolkit(portfolio_id: str, request: Request):
        member = await game_member(request)
        portfolio = await get_portfolio(member["user_id"], portfolio_id)
        toolkit = await toolkit_for(portfolio)
        if toolkit.get("status") != "ready":
            raise HTTPException(status_code=404, detail="Execution materials are not ready yet")
        return {"member_name": portfolio["member_name"], "toolkit": toolkit.get("data") or {},
                "generated_at": toolkit.get("generated_at", "")}

    @router.post("/game/portfolios/{portfolio_id}/generate-updated-toolkit")
    async def org_generate_updated(portfolio_id: str, payload: GeneratePayload, request: Request):
        member = await game_member(request)
        portfolio = await get_portfolio(member["user_id"], portfolio_id)
        if portfolio["status"] not in {"approved", "materials_ready"}:
            raise HTTPException(status_code=409, detail="The portfolio must be approved before generating execution materials")
        return await start_generation(portfolio, payload.origin_url)

    # ---------- Board member (secure token, no account) ----------

    def portfolio_view(portfolio: dict, profile: dict, strategy: dict, toolkit: dict) -> dict:
        organization = profile.get("organization") or {}
        return {
            "member_name": portfolio["member_name"],
            "member_first_name": portfolio["member_name"].split(" ")[0],
            "organization_name": organization.get("name", ""),
            "goal_display": fmt_goal(profile), "goal_deadline": fmt_deadline(profile),
            "status": portfolio["status"], "version": portfolio.get("version", 1),
            "org_note": portfolio.get("org_note", ""),
            "change_request": portfolio.get("change_request", ""),
            "approved_at": portfolio.get("approved_at", ""),
            "strategy_share_token": strategy.get("share_token", ""),
            "system_roles": [{**{k: v for k, v in role.items()},
                              "involvement_display": INVOLVEMENT_DISPLAY.get(role.get("involvement", ""), role.get("involvement", ""))}
                             for role in portfolio.get("system_roles", []) if role.get("active", True)],
            "direct_activities": [act for act in portfolio.get("direct_activities", []) if act.get("active", True)],
            "additional_commitments": portfolio.get("additional_commitments", []),
            "toolkit_status": toolkit.get("status", "not_generated"),
        }

    @router.get("/board-portfolio/{token}")
    async def public_portfolio(token: str):
        portfolio = await portfolio_by_token(token)
        profile = await get_profile(portfolio["user_id"])
        strategy = await db.game_strategies.find_one(
            {"strategy_id": portfolio["strategy_id"]}, {"_id": 0, "share_token": 1}) or {}
        toolkit = await toolkit_for(portfolio)
        view = portfolio_view(portfolio, profile, strategy, toolkit)
        record = await db.game_board_members.find_one(
            {"member_id": portfolio["board_member_id"]}, {"_id": 0, "token": 1}) or {}
        view["play_token"] = record.get("token", "")
        return view

    @router.get("/board-portfolio/{token}/toolkit/download")
    async def download_toolkit_zip(token: str):
        portfolio = await portfolio_by_token(token)
        toolkit = await toolkit_for(portfolio)
        if not toolkit or toolkit.get("status") != "ready":
            raise HTTPException(status_code=409, detail="Execution materials are not ready yet")
        import io
        import re as _re
        import zipfile
        from docx import Document as DocxDocument
        from fastapi.responses import Response as HttpResponse
        profile = await get_profile(portfolio["user_id"])
        org = (profile.get("organization") or {}).get("name", "Organization")
        safe = lambda t: _re.sub(r"[^A-Za-z0-9]+", "-", str(t or "")).strip("-") or "File"
        buffer = io.BytesIO()
        index = 0
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for pack in (toolkit.get("data") or {}).get("material_packs", []) or []:
                for material in pack.get("materials", []) or []:
                    index += 1
                    document = DocxDocument()
                    document.add_heading(str(material.get("title", "Execution Material")), level=1)
                    if material.get("purpose"):
                        document.add_paragraph(str(material["purpose"]))
                    for line in str(material.get("content", "")).split("\n"):
                        document.add_paragraph(line)
                    doc_buffer = io.BytesIO()
                    document.save(doc_buffer)
                    archive.writestr(f"{index:02d}-{safe(material.get('title'))}.docx", doc_buffer.getvalue())
        if index == 0:
            raise HTTPException(status_code=409, detail="No execution materials available yet")
        filename = f"{safe(org)}-{safe(portfolio.get('member_name'))}-Execution-Materials.zip"
        return HttpResponse(content=buffer.getvalue(), media_type="application/zip",
                            headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    @router.post("/board-portfolio/{token}/respond")
    async def public_respond(token: str, payload: RespondPayload):
        portfolio = await portfolio_by_token(token)
        if payload.action == "approve":
            if portfolio["status"] not in {"sent", "ready_to_send", "draft", "change_requested"}:
                return {"status": portfolio["status"]}
            snapshot = {
                "version": portfolio.get("version", 1),
                "system_roles": [role for role in portfolio.get("system_roles", []) if role.get("active", True)],
                "direct_activities": [act for act in portfolio.get("direct_activities", []) if act.get("active", True)],
                "additional_commitments": portfolio.get("additional_commitments", []),
                "org_note": portfolio.get("org_note", ""),
                "approved_at": now_iso(),
            }
            await db.board_portfolios.update_one(
                {"portfolio_id": portfolio["portfolio_id"]},
                {"$set": {"status": "approved", "approved_at": now_iso(),
                          "approved_version": portfolio.get("version", 1),
                          "approved_snapshot": snapshot, "change_request": "", "updated_at": now_iso()}})
            await ensure_execution_access(portfolio["user_id"])
            return {"status": "approved"}
        if payload.action == "request_change":
            if not payload.comment.strip():
                raise HTTPException(status_code=422, detail="Tell us what should change")
            await db.board_portfolios.update_one(
                {"portfolio_id": portfolio["portfolio_id"]},
                {"$set": {"status": "change_requested", "change_request": payload.comment.strip(), "updated_at": now_iso()}})
            return {"status": "change_requested"}
        raise HTTPException(status_code=422, detail="Unknown action")

    # ---------- Execution material generation (the ONE AI action) ----------

    async def run_toolkit_generation(toolkit_id: str, portfolio: dict, origin: str):
        try:
            profile = await get_profile(portfolio["user_id"])
            strategy = await db.game_strategies.find_one(
                {"strategy_id": portfolio["strategy_id"]}, {"_id": 0}) or {}
            data = strategy.get("data") or {}
            snapshot = portfolio.get("approved_snapshot") or {}
            roles = snapshot.get("system_roles") or []
            activities = snapshot.get("direct_activities") or []
            packs_required = []
            for role in roles:
                key = role.get("role_key", "custom")
                packs_required.append({
                    "role_key": key, "role_title": role.get("label", ""),
                    "kind": "system_building",
                    "involvement": INVOLVEMENT_DISPLAY.get(role.get("involvement", ""), role.get("involvement", "")),
                    "board_member_note": role.get("member_note", ""),
                    "game_night_commitment": role.get("commitment", ""),
                    "deadline": role.get("deadline", ""),
                    "required_materials": MATERIALS_MAP.get(key, CUSTOM_MATERIALS),
                })
            for act in activities:
                key = act.get("activity_key", "custom")
                packs_required.append({
                    "role_key": key, "role_title": act.get("label", ""),
                    "kind": "direct_fundraising",
                    "board_member_note": act.get("member_note", ""),
                    "game_night_commitment": act.get("commitment", ""),
                    "deadline": act.get("deadline", ""),
                    "relevant_priority_audiences": act.get("audiences", []),
                    "required_materials": MATERIALS_MAP.get(key, CUSTOM_MATERIALS),
                })
            organization = profile.get("organization") or {}
            context = {
                "organisation": {
                    "name": organization.get("name", ""), "mission": organization.get("mission", ""),
                    "who_they_serve": organization.get("who_served", ""), "website": organization.get("website", ""),
                },
                "adopted_strategy": {
                    "fundraising_goal": fmt_goal(profile), "deadline": fmt_deadline(profile),
                    "goal_purpose": (profile.get("goal") or {}).get("purpose", ""),
                    "priority_fundraising_audiences": data.get("fundraising_audiences", {}),
                    "where_to_find_them": data.get("where_to_find", {}),
                    "attraction_strategy": data.get("attraction", {}),
                    "fundraising_process": data.get("fundraising_process", {}),
                    "execution_timeline": data.get("execution_timeline", {}),
                    "materials_identified": data.get("materials", {}),
                },
                "board_member": {
                    "name": portfolio["member_name"],
                    "board_title": "Board Member",
                    "additional_game_night_commitments": snapshot.get("additional_commitments", []),
                },
                "approved_responsibilities_and_required_material_packs": packs_required,
            }
            api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
            model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
            chat = LlmChat(api_key=api_key, session_id=f"bfg-toolkit-{uuid.uuid4()}",
                           system_message=EXECUTION_SYSTEM_MESSAGE).with_model("anthropic", model)
            prompt = (
                "EXECUTION PACK CONTEXT (the only information you may use):\n"
                f"{json.dumps(context, indent=1)}\n\n"
                "Create one material pack per approved responsibility listed above, containing exactly the required materials named for that responsibility "
                "(for custom responsibilities create only the materials that are directly useful). "
                "Respond with ONE JSON object matching exactly this schema. Return only JSON — no markdown, no commentary:\n"
                + json.dumps(EXECUTION_OUTPUT_SCHEMA, indent=1)
            )
            response = await chat.send_message(UserMessage(text=prompt))
            text = response if isinstance(response, str) else getattr(response, "text", str(response))
            result = parse_json_response(text)
            if not result.get("material_packs"):
                raise ValueError("empty toolkit")
            await db.execution_toolkits.update_one(
                {"toolkit_id": toolkit_id},
                {"$set": {"status": "ready", "data": result, "generated_at": now_iso(), "updated_at": now_iso()}})
            await db.board_portfolios.update_one(
                {"portfolio_id": portfolio["portfolio_id"], "status": "approved"},
                {"$set": {"status": "materials_ready", "updated_at": now_iso()}})
            toolkit = await db.execution_toolkits.find_one({"toolkit_id": toolkit_id}, {"_id": 0})
            if toolkit and not toolkit.get("ready_email_sent") and portfolio.get("member_email") and origin:
                profile_doc = await get_profile(portfolio["user_id"])
                member = await db.members.find_one({"user_id": portfolio["user_id"]}, {"_id": 0}) or {}
                organization = (profile_doc.get("organization") or {}).get("name", "your organisation")
                first_name = portfolio["member_name"].split(" ")[0]
                link = f"{origin.rstrip('/')}/board-portfolio/{portfolio['token']}"
                assistant_link = f"{origin.rstrip('/')}/board-assistant/{portfolio['token']}"
                primary = profile_doc.get("primary_user") or {}
                lines = [primary.get("full_name", ""), primary.get("job_title", ""), organization]
                signature = "".join(f"<p style='margin:2px 0;'>{html.escape(line)}</p>" for line in lines if line and line.strip())
                body = (
                    f"<p>Hi {html.escape(first_name)},</p>"
                    f"<p>Your fundraising execution materials for {html.escape(organization)} are ready.</p>"
                    f"<p>These resources were created around the fundraising responsibilities you approved in your Board Fundraising Portfolio.</p>"
                    f"{game_button(link, 'Open My Execution Toolkit')}"
                    f"<p>Your personal fundraising assistant is also ready. Bookmark this secure link so you can return whenever you need a message, script, checklist or guidance.</p>"
                    f"{game_button(assistant_link, 'Open And Bookmark My Fundraising Assistant')}"
                    f"<div style='margin-top:26px;'>{signature}</div>"
                )
                await send_game_email(portfolio["member_email"], member.get("email", ""),
                                      "Your Fundraising Execution Toolkit Is Ready", body, raise_on_error=False)
                await db.execution_toolkits.update_one(
                    {"toolkit_id": toolkit_id}, {"$set": {"ready_email_sent": True}})
        except Exception:
            await db.execution_toolkits.update_one(
                {"toolkit_id": toolkit_id},
                {"$set": {"status": "failed", "updated_at": now_iso()}})

    async def start_generation(portfolio: dict, origin: str) -> dict:
        version = portfolio.get("approved_version") or portfolio.get("version", 1)
        existing = await db.execution_toolkits.find_one(
            {"portfolio_id": portfolio["portfolio_id"], "portfolio_version": version},
            {"_id": 0}, sort=[("created_at", -1)])
        if existing and existing.get("status") == "ready":
            return {"status": "ready"}
        if existing and existing.get("status") == "generating":
            return {"status": "generating"}
        if existing and existing.get("status") == "failed":
            result = await db.execution_toolkits.update_one(
                {"toolkit_id": existing["toolkit_id"], "status": "failed"},
                {"$set": {"status": "generating", "updated_at": now_iso()}})
            if result.modified_count == 0:
                return {"status": "generating"}
            toolkit_id = existing["toolkit_id"]
        else:
            toolkit_id = new_uuid()
            record = {
                "toolkit_id": toolkit_id, "portfolio_id": portfolio["portfolio_id"],
                "user_id": portfolio["user_id"], "board_member_id": portfolio["board_member_id"],
                "strategy_id": portfolio["strategy_id"], "portfolio_version": version,
                "status": "generating", "data": None, "ready_email_sent": False,
                "generated_at": "", "created_at": now_iso(), "updated_at": now_iso(),
            }
            await db.execution_toolkits.insert_one(record.copy())
        asyncio.create_task(run_toolkit_generation(toolkit_id, portfolio, origin))
        return {"status": "generating"}

    @router.post("/board-portfolio/{token}/generate-materials")
    async def public_generate(token: str, payload: GeneratePayload):
        portfolio = await portfolio_by_token(token)
        if portfolio["status"] not in {"approved", "materials_ready"}:
            raise HTTPException(status_code=409, detail="Approve your portfolio before generating execution materials")
        return await start_generation(portfolio, payload.origin_url)

    @router.get("/board-portfolio/{token}/toolkit")
    async def public_toolkit(token: str):
        portfolio = await portfolio_by_token(token)
        toolkit = await toolkit_for(portfolio)
        status = toolkit.get("status", "not_generated")
        return {"status": status,
                "toolkit": toolkit.get("data") if status == "ready" else None,
                "generated_at": toolkit.get("generated_at", "")}

    async def assistant_context(portfolio: dict) -> dict:
        profile = await get_profile(portfolio["user_id"])
        strategy = await db.game_strategies.find_one({"strategy_id": portfolio["strategy_id"]}, {"_id": 0}) or {}
        relationships = await db.game_relationships.find({"user_id": portfolio["user_id"], "board_member_id": portfolio["board_member_id"]}, {"_id": 0}).to_list(200)
        snapshot = portfolio.get("approved_snapshot") or portfolio
        return {"organization": profile.get("organization") or {}, "fundraising_goal": profile.get("goal") or {},
                "adopted_strategy": strategy.get("data") or {}, "board_member": portfolio.get("member_name", ""),
                "approved_roles": snapshot.get("system_roles") or [], "approved_activities": snapshot.get("direct_activities") or [],
                "additional_commitments": snapshot.get("additional_commitments") or [], "this_member_relationships": relationships}

    @router.get("/board-assistant/{token}")
    async def board_assistant(token: str):
        portfolio = await portfolio_by_token(token)
        if portfolio.get("status") not in {"approved", "materials_ready"}:raise HTTPException(409,"Approve the Board Fundraising Portfolio before starting execution")
        profile=await get_profile(portfolio["user_id"]);access=await ensure_execution_access(portfolio["user_id"]);state=execution_access_state(access);snapshot=portfolio.get("approved_snapshot") or portfolio;suggestions=[]
        for item in (snapshot.get("system_roles") or [])+(snapshot.get("direct_activities") or []):
            key=item.get("role_key") or item.get("activity_key") or "custom"
            for title in MATERIALS_MAP.get(key,CUSTOM_MATERIALS)[:4]:
                if title not in suggestions:suggestions.append(title)
        history=await db.board_assistant_messages.find({"portfolio_id":portfolio["portfolio_id"]},{"_id":0}).sort("created_at",1).to_list(200)
        return {"member_name":portfolio["member_name"],"organization_name":(profile.get("organization") or {}).get("name",""),"suggested_materials":suggestions[:12],
            "messages":[{"role":x["role"],"text":x["text"]} for x in history],"access_status":state,"included_until":access.get("included_until",""),
            "leader_name":access.get("leader_name",""),"renewal_message":"Your organization's included Executive Assistant access has ended. Please ask your organization leader to renew Board Execution Support." if state=="renewal_required" else ""}

    @router.post("/board-assistant/{token}")
    async def use_board_assistant(token: str,payload:AssistantPayload):
        portfolio=await portfolio_by_token(token)
        if portfolio.get("status") not in {"approved","materials_ready"}:raise HTTPException(409,"Approve the Board Fundraising Portfolio before starting execution")
        access=await ensure_execution_access(portfolio["user_id"])
        if execution_access_state(access)=="renewal_required":raise HTTPException(402,"Your organization's included Executive Assistant access has ended. Please ask your organization leader to renew Board Execution Support.")
        context=await assistant_context(portfolio);request_text=(f"Create this ready-to-use fundraising material: {payload.material_type}.\n\nAdditional instruction: {payload.message}" if payload.material_type else payload.message)
        api_key=os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY","");model=os.environ.get("EXECUTIVE_ASSISTANT_MODEL","claude-haiku-4-5-20251001");provider=os.environ.get("EXECUTIVE_ASSISTANT_PROVIDER","anthropic")
        system=("You are one delegated leader's secure fundraising execution assistant. Use only the supplied organization, adopted strategy, approved Board Fundraising Portfolio, this person's relationships and conversation. The Portfolio is the authority for understanding this person's role and for recommending the scripts, messages, checklists, research templates, tracking tools and other execution materials that will help them perform it. Give practical, ready-to-use help only for responsibilities this person actually approved or was delegated. Never invent facts, people, relationships, commitments, results or authority. Use clear placeholders when missing facts are required. Do not mention AI.")
        history=await db.board_assistant_messages.find({"portfolio_id":portfolio["portfolio_id"]},{"_id":0}).sort("created_at",-1).limit(12).to_list(12);history.reverse()
        prompt=f"AUTHORITATIVE CONTEXT:\n{json.dumps(context,default=str)}\n\nRECENT CONVERSATION:\n{json.dumps(history,default=str)}\n\nDELEGATED LEADER REQUEST:\n{request_text}"
        chat=LlmChat(api_key=api_key,session_id=f"board-assistant-{portfolio['portfolio_id']}-{uuid.uuid4()}",system_message=system).with_model(provider,model);response=await chat.send_message(UserMessage(text=prompt));answer=response if isinstance(response,str) else getattr(response,"text",str(response));now=now_iso()
        await db.board_assistant_messages.insert_many([{"message_id":new_uuid(),"portfolio_id":portfolio["portfolio_id"],"role":"user","text":request_text,"created_at":now},{"message_id":new_uuid(),"portfolio_id":portfolio["portfolio_id"],"role":"assistant","text":answer,"created_at":now_iso()}]);await meter_assistant(access["scope_id"],portfolio,request_text,answer,payload.material_type)
        return {"answer":answer}

    return router
