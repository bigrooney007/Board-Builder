"""Server-side Claude generation service (Phase 3). All AI calls happen here only."""
import io
import json
import logging
import os
import re
import uuid

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)

REVIEW_WARNING = "This document is generated as a working template. Review it against your bylaws, policies and applicable legal requirements before using it."

# generation type registry: module, title, schema description (JSON the model must return)
GENERATION_TYPES = {
    "recruitment_strategy": {"module": 2, "title": "Board Recruitment Strategy", "per_application": False, "schema": {
        "objective": "string — what the organization is trying to accomplish through recruitment",
        "board_members_to_recruit": {"number": "string — the founder's stated number, do not override", "note": "string — empty unless their information creates a clear conflict; then: 'You indicated that you want to recruit [X] people. Based on the requirements you described, you may want to review whether this number gives you enough capacity to cover every priority.'"},
        "candidate_profiles": [{"profile_name": "string", "why_needed": "string", "skills": ["string"], "relevant_experience": "string", "useful_relationships": "string", "fundraising_contribution": "string", "priorities_supported": "string"}],
        "recruitment_positioning": "string — why a qualified professional should want to join this board",
        "recruitment_channels": [{"channel": "string (LinkedIn, Board Applicant Network, professional associations, community networks, personal introductions, existing supporters — where appropriate)", "how_to_use": "string"}],
        "selection_criteria": ["string"],
        "recruitment_timeline": [{"period": "string", "actions": "string"}],
        "launch_plan": ["string — what to do first, second and next"],
    }},
    "board_opportunity": {"module": 3, "title": "Board Opportunity", "per_application": False, "schema": {
        "title": "string — board opportunity title", "organization_name": "string", "mission": "string",
        "why_recruiting": "string", "what_accomplish": "string", "number_sought": "string",
        "candidate_profiles": ["string"], "responsibilities": ["string"], "fundraising_expectations": "string",
        "meeting_structure": "string", "time_commitment": "string", "geographic_requirements": "string",
        "benefits_of_serving": "string", "application_deadline": "string — or 'Open until positions are filled'",
        "how_to_apply": "string",
    }},
    "application_questions": {"module": 3, "title": "Board Application — Organization-Specific Questions", "per_application": False, "schema": {
        "custom_questions": [{"label": "string — the question", "type": "one of: text, textarea, yes_no", "why": "string — why this question matters for this organization"}],
    }},
    "linkedin_post": {"module": 3, "title": "LinkedIn Recruitment Post", "per_application": False, "schema": {
        "post_text": "string — complete LinkedIn post ready to publish, includes the application link placeholder [APPLICATION LINK]", "hashtags": ["string"],
    }},
    "social_posts": {"module": 3, "title": "Social Media Recruitment Posts", "per_application": False, "schema": {
        "facebook": "string", "instagram": "string", "x": "string — short post for X (Twitter)",
    }},
    "recruitment_emails": {"module": 3, "title": "Recruitment Emails", "per_application": False, "schema": {
        "supporter_announcement": {"subject": "string", "body": "string"},
        "personal_invitation": {"subject": "string", "body": "string"},
        "follow_up": {"subject": "string", "body": "string"},
    }},
    "linkedin_launch_instructions": {"module": 3, "title": "LinkedIn Launch Instructions", "per_application": False, "schema": {
        "steps": [{"title": "string", "instructions": "string — practical instructions covering where to post, how to structure the post, how to use the application link, how to ask others to share, how to contact potential prospects, how to follow up, how to maintain campaign activity"}],
    }},
    "interview_guide": {"module": 4, "title": "Interview Guide", "per_application": True, "schema": {
        "applicant_overview": "string — concise factual summary",
        "strengths": [{"strength": "string", "evidence": "string — evidence in the application/CV connected to the organization's needs"}],
        "areas_to_clarify": ["string"],
        "organization_questions": ["string"],
        "cv_questions": ["string — based on the applicant's actual professional experience"],
        "commitment_questions": ["string — time, meetings, responsibility, teamwork, governance, willingness to execute"],
        "fundraising_questions": ["string — only areas relevant to this opportunity"],
        "concerns_to_explore": ["string — phrase uncertain issues as matters requiring clarification; no accusations; never label unqualified"],
        "scorecard": [{"category": "string — from the founder's approved selection criteria", "description": "string"}],
    }},
    "interview_invitation": {"module": 4, "title": "Interview Invitation", "per_application": True, "schema": {"subject": "string", "body": "string — concise invitation"}},
    "after_interview_email": {"module": 4, "title": "After-Interview Email", "per_application": True, "schema": {"subject": "string", "body": "string — respectful email matching the chosen result"}},
    "reference_request_email": {"module": 5, "title": "Reference Request Email", "per_application": True, "schema": {"subject": "string", "body": "string"}},
    "reference_call_script": {"module": 5, "title": "Reference Call Script", "per_application": True, "schema": {"introduction": "string", "questions": ["string"], "closing": "string"}},
    "reference_evaluation_form": {"module": 5, "title": "Reference Evaluation Form", "per_application": True, "schema": {"sections": [{"title": "string", "items": ["string"]}]}},
    "onboarding_agenda": {"module": 6, "title": "Onboarding Agenda", "per_application": True, "schema": {
        "items": [{"topic": "string — cover welcome; introductions; mission/program overview; organizational priorities; board role; governance expectations; fundraising expectations; committees/responsibilities; important policies; next 90 days; questions; next meeting/action", "details": "string"}],
    }},
    "organization_overview": {"module": 6, "title": "Organization Overview", "per_application": True, "schema": {
        "sections": [{"title": "string — mission; history where supplied; programs; people served; priorities; leadership; board role; fundraising priorities; key terminology; important contacts. When information is missing use content 'Information to Add' — never invent", "content": "string"}],
    }},
    "board_manual": {"module": 6, "title": "Board Manual", "per_application": True, "schema": {
        "sections": [{"title": "string — organization overview; mission; board purpose; board responsibilities; meeting expectations; governance expectations; fundraising expectations; committees; conflict-of-interest expectations; confidentiality expectations; communication; key policies; annual expectations; new-board-member 90-day expectations", "content": "string"}],
    }},
    "board_member_agreement": {"module": 6, "title": "Board Member Agreement", "per_application": True, "agreement": True, "schema": {
        "title": "string", "sections": [{"title": "string — board member name; organization; board term where known; attendance; participation; governance responsibilities; confidentiality; conflicts of interest; fundraising responsibility; committee/service responsibility; preparation for meetings; organizational representation; agreed commitments", "content": "string"}], "acknowledgement": "string",
    }},
    "confidentiality_agreement": {"module": 6, "title": "Confidentiality Agreement", "per_application": True, "agreement": True, "schema": {
        "title": "string", "sections": [{"title": "string — confidential organizational information; donor information; financial information; staff information; board discussions; program/client information where appropriate; electronic information; use/disclosure expectations; return/deletion of confidential information where appropriate. Do not invent jurisdiction-specific legal clauses when jurisdiction information is unavailable", "content": "string"}], "acknowledgement": "string",
    }},
    "conflict_of_interest_agreement": {"module": 6, "title": "Conflict of Interest Agreement", "per_application": True, "agreement": True, "schema": {
        "title": "string", "sections": [{"title": "string — duty to disclose actual/potential conflicts; financial interests; business relationships; family/personal relationships; gifts or benefits where relevant; disclosure process; recusal where appropriate; annual disclosure expectation", "content": "string"}], "acknowledgement": "string",
    }},
    "ninety_day_plan": {"module": 6, "title": "New Board Member 90-Day Plan", "per_application": True, "schema": {
        "first_30_days": ["string — learn, attend, understand mission, complete onboarding"],
        "days_31_60": ["string — begin assigned responsibilities and relationship building"],
        "days_61_90": ["string — take ownership of agreed board/fundraising responsibilities"],
        "notes": "string — customized to candidate strengths, assigned responsibility, organizational priorities and fundraising expectations",
    }},
}

SYSTEM_MESSAGE = (
    "You are the Nonprofit Board Builder recruitment assistant. You work ONLY from the information provided in the prompt: "
    "the nonprofit's submitted information, the confirmed recruitment profile, previously approved recruitment materials, and "
    "applicant application information and CV where provided. Never invent facts, real people, statistics or history that was not provided. "
    "When required information is missing, write 'Information to Add'. Never claim documents have been reviewed by a lawyer and never give legal advice. "
    "You must respond with a single valid JSON object matching the requested schema exactly — no markdown, no code fences, no commentary."
)


def _format_value(value, indent=0):
    pad = "  " * indent
    lines = []
    if isinstance(value, dict):
        for key, item in value.items():
            label = key.replace("_", " ").title()
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{label}:")
                lines.extend(_format_value(item, indent + 1))
            else:
                lines.append(f"{pad}{label}: {item}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.extend(_format_value(item, indent))
                lines.append("")
            else:
                lines.append(f"{pad}- {item}")
    else:
        lines.append(f"{pad}{value}")
    return lines


def structured_to_display(generation_type: str, structured: dict) -> str:
    meta = GENERATION_TYPES[generation_type]
    lines = [meta["title"].upper(), ""]
    lines.extend(_format_value(structured))
    if meta.get("agreement"):
        lines.extend(["", REVIEW_WARNING])
    return "\n".join(line.rstrip() for line in lines).strip()


def parse_json_response(text: str) -> dict:
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)```\s*$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("The model did not return JSON")
    return json.loads(text[start:end + 1])


async def generate_structured(generation_type: str, context: str, instructions: str = "") -> dict:
    """Deliberate, single Claude call. Returns structured dict. Raises on failure."""
    meta = GENERATION_TYPES[generation_type]
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    chat = LlmChat(api_key=api_key, session_id=f"nbb-{generation_type}-{uuid.uuid4()}", system_message=SYSTEM_MESSAGE).with_model("anthropic", model)
    prompt = (
        f"GENERATION TYPE: {meta['title']}\n\n"
        f"CONTEXT (the only information you may use):\n{context}\n\n"
        + (f"ADDITIONAL INSTRUCTIONS:\n{instructions}\n\n" if instructions else "")
        + "Respond with one JSON object matching exactly this schema (descriptions explain each field):\n"
        + json.dumps(meta["schema"], indent=1)
    )
    response = await chat.send_message(UserMessage(text=prompt))
    text = response if isinstance(response, str) else getattr(response, "text", str(response))
    structured = parse_json_response(text)
    if generation_type == "application_questions":
        structured["custom_questions"] = structured.get("custom_questions", [])[:5]
    return structured


def extract_cv_text(content: bytes, filename: str) -> str:
    """Securely extract usable text from a CV file. Never exposes file publicly."""
    extension = os.path.splitext(filename or "")[1].lower()
    try:
        if extension == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            return "\n".join((page.extract_text() or "") for page in reader.pages)[:20000]
        if extension == ".docx":
            import docx
            document = docx.Document(io.BytesIO(content))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)[:20000]
        if extension == ".doc":
            return content.decode("latin-1", errors="ignore")[:20000]
    except Exception as exc:
        logger.warning("CV text extraction failed for %s: %s", filename, exc)
    return ""
