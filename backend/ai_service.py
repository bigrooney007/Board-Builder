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
    "powerhouse_board_blueprint": {"module": 1, "title": "The Board Members Your Organization Needs", "per_application": False, "schema": {
        "priority_roles": [{"role_name": "string — e.g. 'Fundraising & Philanthropy Leader'", "summary": "string — exactly TWO concise sentences: (1) why this role complements the existing board; (2) what this person will help accomplish based on the type of board the organization said it wants to build"}],
        "detailed_roles": [{"role_name": "string — SAME roles as priority_roles, same order, no extras", "why_this_role_matters": "string", "professional_background_to_look_for": "string", "relevant_skills": ["string"], "useful_networks": "string", "how_this_role_contributes": "string", "how_this_complements_the_present_board": "string"}],
        "internal_analysis": {"present_board_brings": "string — internal use only", "important_gaps": "string — internal use only", "board_needed": "string — internal use only"},
    }, "note": "priority_roles: NO MORE THAN FIVE roles. If the customer said they want to recruit fewer than five people, produce exactly that number. detailed_roles must contain the SAME roles only."},
    "recruitment_strategy": {"module": 2, "title": "Board Recruitment Strategy", "per_application": False, "schema": {
        "executive_summary": "string — NO MORE than TWO short sentences stating the roles being recruited, the channels being used, and that recruitment begins immediately",
        "roles": [{"role_name": "string — a priority board role from Module 1, same order", "person_sought": "string — ONE short sentence describing the type of person being sought"}],
        "channels": [{"channel": "string — ONLY one of: 'Personal Network', 'Referral Network', 'Public Outreach'. Include ONLY channels the customer's intake answers make available. Never include a channel they said they cannot or do not want to use.", "approach": "string — a VERY BRIEF one-to-two sentence practical approach for this channel, mentioning the customer's actual selected outlets where relevant. Never multiple paragraphs."}],
        "selection_criteria": ["string — one concise quality applicants should demonstrate, adapted to the organization's selected board type (mission alignment, relevant skills for a priority role, willingness and capacity to serve, understanding of the board role, ability to contribute to the kind of board being built, participation in meetings and agreed responsibilities, professional conduct and credibility). Never numeric scores. Never statutory/legal requirements."],
    }, "note": "Keep every section concise and practical. No long consulting essays, no repetition of the full Module 1 analysis, no long channel instructions. The timeline and execution roadmap are added by the platform — do not write them."},
    "board_opportunity": {"module": 3, "title": "Board Opportunity", "per_application": False, "schema": {
        "title": "string — professional board opportunity title",
        "introduction": "string — 2 to 4 sentence organization/opportunity introduction",
        "about_the_organization": "string — the organization and its mission in natural prose",
        "who_we_are_looking_for": "string — the priority board roles from Module 1, concisely, in natural prose or a short list",
        "what_board_members_will_contribute": "string",
        "board_expectations": "string",
        "meeting_time_and_location": "string — meeting frequency, time commitment and location/geographic information as supplied",
        "how_to_apply": "string — must contain the exact application URL supplied in the context",
    }, "note": "Write as a real professional board opportunity announcement. Never print internal field labels such as 'Why Recruiting:' or 'Fundraising Contribution:'. Use only the priority roles identified in Module 1 — never invent 10-12 candidate profiles."},
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
    "linkedin_launch_instructions": {"module": 3, "title": "LinkedIn Jobs Launch Guide", "per_application": False, "schema": {
        "steps": [{"title": "string", "instructions": "string — practical instructions covering where to post, how to structure the post, how to use the application link, how to ask others to share, how to contact potential prospects, how to follow up, how to maintain campaign activity. When discussing budget say: 'You can begin with a small controlled test budget, such as $20 where the option is available, and increase it only if you choose. LinkedIn's available posting and promotion options may vary.' NEVER state that LinkedIn charges $20 as a universal platform fact. Do not fabricate LinkedIn screenshots or exact current UI labels."}],
    }},
    "board_recruitment_job_post": {"module": 3, "title": "Board Recruitment Job Post", "per_application": False, "schema": {
        "title": "string — professional posting title", "post_body": "string — complete professional board-opportunity posting for LinkedIn Jobs or another professional/volunteer platform, includes the application link placeholder [APPLICATION LINK]. Clearly represent the actual nature of the board opportunity; NEVER describe an unpaid nonprofit board role as salaried employment.",
    }},
    "personal_invitation_email": {"module": 3, "title": "Personal Invitation Email", "per_application": False, "schema": {
        "subject": "string", "body": "string — a warm personal email inviting someone the founder already knows to consider the board opportunity, includes the application link placeholder [APPLICATION LINK]",
    }},
    "personal_invitation_message": {"module": 3, "title": "Personal Invitation Message", "per_application": False, "schema": {
        "message": "string — a concise direct message version for LinkedIn, Facebook, text or another direct-message channel, includes the application link placeholder [APPLICATION LINK]",
    }},
    "referral_request_email": {"module": 3, "title": "Referral Request Email", "per_application": False, "schema": {
        "subject": "string", "body": "string — a professional email asking board members, supporters and colleagues to share the board opportunity with qualified people in their networks, includes the application link placeholder [APPLICATION LINK]",
    }},
    "referral_request_message": {"module": 3, "title": "Referral Request Message", "per_application": False, "schema": {
        "message": "string — a concise direct-message version of the referral request for LinkedIn, text or other channels, includes the application link placeholder [APPLICATION LINK]",
    }},
    "general_interview_invitation": {"module": 4, "title": "General Interview Invitation", "per_application": False, "schema": {"subject": "string", "body": "string — general invitation to a board introductory/interview conversation, with [APPLICANT NAME] and scheduling placeholders"}},
    "general_interview_invitation_message": {"module": 4, "title": "Interview Invitation — Short Message", "per_application": False, "schema": {"message": "string — a concise direct-message version of the interview invitation for LinkedIn, text message, Facebook Messenger or another messaging channel. Includes [APPLICANT NAME], the organization name, thanks for their interest, the invitation to interview and a scheduling placeholder. NO email subject line. Keep it short — a few sentences, not another email."}},
    "general_rejection_email": {"module": 4, "title": "Application Rejection Email", "per_application": True, "schema": {"subject": "string", "body": "string — respectful, concise email for an applicant the organization has decided not to invite to interview"}},
    "conditional_offer": {"module": 5, "title": "Conditional Board Appointment Email", "per_application": True, "schema": {"subject": "string", "body": "string — tells the applicant the organization would like them to join the board; clearly states the appointment remains conditional/pending completion of the relevant reference or background checks and the organization's final appointment requirements where relevant; explains what happens next and any profile forms or agreements they need to complete. Use the words 'conditional board appointment'; NEVER 'confidential board position'. Never make false statements about legal requirements."}},
    "after_interview_rejection": {"module": 5, "title": "After-Interview Rejection Email", "per_application": True, "schema": {"subject": "string", "body": "string — respectful, concise email for an applicant who was interviewed but will not move forward"}},
    "onboarding_script": {"module": 6, "title": "Board Member Onboarding Script", "per_application": False, "schema": {
        "sections": [{"title": "string — welcome; mission and story as supplied; what the organization needs; the board member's role and responsibility; expectations; how they can begin contributing; questions; next steps", "talking_points": ["string — practical founder-facing talking points for the onboarding conversation or meeting"]}],
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
    "interview_invitation_message": {"module": 4, "title": "Interview Invitation — Short Message", "per_application": True, "schema": {"message": "string — a concise personalized direct-message invitation for LinkedIn, text message or another messaging channel: the candidate's name, the organization name, thanks for their interest, the invitation to interview and scheduling information where supplied. NO email subject line. A few sentences only."}},
    "after_interview_thank_you": {"module": 4, "title": "After-Interview Thank-You Email", "per_application": True, "schema": {"subject": "string", "body": "string — thanks the applicant for their time and their interest in the mission, tells them the organization is completing its review and that they will receive a decision/follow-up shortly. NEVER states or implies whether they were accepted or rejected."}},
    "formal_appointment_email": {"module": 6, "title": "Formal Board Appointment Email", "per_application": True, "schema": {"subject": "string", "body": "string — formally welcomes the person as a Board Member or Advisory Board Member (match the organization's selected board type), confirms their appointment, and covers next steps such as the first board meeting where information was supplied"}},
    "board_member_portfolio": {"module": 6, "title": "Board Member Portfolio", "per_application": True, "schema": {
        "sections": [{"title": "string — cover: professional summary/bio; board role and why they were recruited; skills and expertise; relevant networks and relationships; board and leadership experience; fundraising interests; committee interests; agreed board responsibilities where known", "content": "string"}],
    }, "note": "Use ONLY the application, CV, board role and Board Member Profile Form information supplied. NEVER include referee responses, internal interview notes, selection scoring or internal evaluation material."},
    "portfolio_email": {"module": 6, "title": "Board Member Portfolio Email", "per_application": True, "schema": {"subject": "string", "body": "string — a short professional email to the board member sharing their completed Board Member Portfolio"}},
    "after_interview_email": {"module": 4, "title": "After-Interview Email", "per_application": True, "schema": {"subject": "string", "body": "string — respectful email matching the chosen result"}},
    "reference_request_email": {"module": 5, "title": "Reference Request Email", "per_application": True, "schema": {"subject": "string", "body": "string"}},
    "reference_call_script": {"module": 5, "title": "Reference Call Guide", "per_application": True, "schema": {"introduction": "string", "questions": ["string"], "closing": "string"}},
    "reference_evaluation_form": {"module": 5, "title": "Reference Evaluation Form", "per_application": True, "schema": {"sections": [{"title": "string", "items": ["string"]}]}},
    "onboarding_agenda": {"module": 6, "title": "Onboarding Agenda", "per_application": True, "schema": {
        "items": [{"topic": "string — cover welcome; introductions; mission/program overview; organizational priorities; board role; governance expectations; fundraising expectations; committees/responsibilities; important policies; next 90 days; questions; next meeting/action", "details": "string"}],
    }},
    "organization_overview": {"module": 5, "title": "Organization Overview", "per_application": False, "schema": {
        "sections": [{"title": "string — mission; history where supplied; programs; people served; priorities; leadership; board role; fundraising priorities; key terminology; important contacts. When information is missing use content 'Information to Add' — never invent", "content": "string"}],
    }},
    "board_manual": {"module": 5, "title": "Board Manual", "per_application": False, "schema": {
        "sections": [{"title": "string — organization overview; mission; board purpose; board responsibilities; meeting expectations; governance expectations; fundraising expectations; committees; conflict-of-interest expectations; confidentiality expectations; communication; key policies; annual expectations; new-board-member 90-day expectations", "content": "string"}],
    }},
    "board_member_agreement": {"module": 5, "title": "Board Member Agreement", "per_application": False, "agreement": True, "schema": {
        "title": "string", "sections": [{"title": "string — board member name; organization; board term where known; attendance; participation; governance responsibilities; confidentiality; conflicts of interest; fundraising responsibility; committee/service responsibility; preparation for meetings; organizational representation; agreed commitments", "content": "string"}], "acknowledgement": "string",
    }},
    "confidentiality_agreement": {"module": 5, "title": "Confidentiality Agreement", "per_application": False, "agreement": True, "schema": {
        "title": "string", "sections": [{"title": "string — confidential organizational information; donor information; financial information; staff information; board discussions; program/client information where appropriate; electronic information; use/disclosure expectations; return/deletion of confidential information where appropriate. Do not invent jurisdiction-specific legal clauses when jurisdiction information is unavailable", "content": "string"}], "acknowledgement": "string",
    }},
    "conflict_of_interest_agreement": {"module": 5, "title": "Conflict of Interest Agreement", "per_application": False, "agreement": True, "schema": {
        "title": "string", "sections": [{"title": "string — duty to disclose actual/potential conflicts; financial interests; business relationships; family/personal relationships; gifts or benefits where relevant; disclosure process; recusal where appropriate; annual disclosure expectation", "content": "string"}], "acknowledgement": "string",
    }},
    "ninety_day_plan": {"module": 6, "title": "New Board Member 90-Day Plan", "per_application": True, "schema": {
        "first_30_days": ["string — learn, attend, understand mission, complete onboarding"],
        "days_31_60": ["string — begin assigned responsibilities and relationship building"],
        "days_61_90": ["string — take ownership of agreed board/fundraising responsibilities"],
        "notes": "string — customized to candidate strengths, assigned responsibility, organizational priorities and fundraising expectations",
    }},
    "first_board_meeting_invitation": {"module": 6, "title": "First Board Meeting Invitation Email", "per_application": False, "schema": {
        "subject": "string", "body": "string — one professional, warm, editable email inviting the newly assembled board to its first board meeting and beginning their service together. Use the supplied meeting details exactly; where a detail was not supplied write '[To be confirmed]'. Never invent meeting logistics.",
    }},
}

SYSTEM_MESSAGE = (
    "You are the Nonprofit Board Builder recruitment assistant. You work ONLY from the information provided in the prompt: "
    "the nonprofit's submitted information, the confirmed recruitment profile, previously approved recruitment materials, and "
    "applicant application information and CV where provided. Never invent facts, real people, statistics or history that was not provided. "
    "WRITING RULES: everything you write must sound like it was professionally written by a real nonprofit founder, executive director or experienced nonprofit consultant. "
    "Never use emojis, smileys, decorative icons, unnecessary symbols, exaggerated marketing language, inflated adjectives, or generic AI phrases such as 'pivotal moment', 'unlock', 'game-changing', 'transformative journey', 'dive into' or similar. "
    "Prefer straightforward sentences. Avoid repetitive introductions, excessive headings and excessive bullet lists. Write as the organization or founder where appropriate. "
    "Emails must read like real professional emails. Formal documents must read like real organizational documents. "
    "BOARD TYPE: always match the organization's selected board type. If they are building an Advisory Board, refer to the Advisory Board, Advisory Board Members, Advisory Board Opportunity, Advisory Board Application and Advisory Board Appointment where appropriate, and focus on professional expertise, strategic advice, relationships, introductions, subject-matter expertise, community connections, mission support and fundraising support where the organization expects it. Never automatically state that Advisory Board Members govern the nonprofit, hold fiduciary responsibility, vote as Directors, oversee the Executive Director or carry statutory governance duties unless the organization explicitly supplied those responsibilities. If a governing/working board, use appropriate director/board-member terminology and keep the organization's stated expectations at full strength. "
    "Never write the phrase 'Information to Add' in anything intended to be publicly shared or sent to another person; instead use the neutral placeholder in square brackets naming exactly what is missing, e.g. '[Application deadline]'. "
    "Never claim documents have been reviewed by a lawyer and never give legal advice. "
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


STRATEGY_TIMELINE_TEXT = """4. RECRUITMENT TIMELINE

DAY 1
Launch the recruitment campaign. Begin Personal Network outreach where applicable, begin Referral Network outreach where applicable, and publish through your selected Public Outreach channels where applicable.

WITHIN 48 HOURS
Review the first applications and responses. Begin inviting qualified applicants to interview — do not wait until the campaign closes.

WEEKS 1-2
Continue recruitment outreach. Review applicants as they arrive, interview qualified applicants, follow up with strong prospects and continue accepting additional applications while interviews are taking place.

WEEK 3
Complete final interviews and verification for candidates moving forward. Finalize board-member selections, complete required onboarding information, agreements and preparation, and begin onboarding the new board members."""

STRATEGY_ROADMAP_TEXT = """5. YOUR RECRUITMENT EXECUTION ROADMAP

STEP 2 — BUILD YOUR RECRUITMENT STRATEGY
You have now identified the channels you will use to reach the professionals your organization needs.

STEP 3 — LAUNCH YOUR RECRUITMENT CAMPAIGN
Create your recruitment materials, publish your board opportunity and begin personally reaching the professionals and networks identified in your strategy.

STEP 4 — INTERVIEW YOUR APPLICANTS
Review applicants as they arrive and invite qualified candidates to interview. Begin interviewing within the first 48 hours where qualified applicants are available and continue interviews over the next two weeks.

STEP 5 — COMPLETE REFERENCES AND BACKGROUND CHECKS
For the candidates you want to move forward with, complete the reference and verification steps your organization has chosen to use.

STEP 6 — ONBOARD YOUR NEW BOARD MEMBERS
Complete the appointment and onboarding process so your new board members understand the organization, their responsibilities and how they will begin contributing."""

STRATEGY_NEXT_STEP_TEXT = """YOUR NEXT STEP
Your recruitment strategy is ready. The next step is to create the materials you will use to reach applicants and launch your recruitment campaign.

CONTINUE TO STEP 3 — CREATE MY RECRUITMENT MATERIALS"""


def structured_to_display(generation_type: str, structured: dict) -> str:
    meta = GENERATION_TYPES[generation_type]
    if generation_type == "recruitment_strategy":
        lines = ["BOARD RECRUITMENT STRATEGY", "", "EXECUTIVE SUMMARY", structured.get("executive_summary", ""), "", "1. BOARD MEMBERS WE ARE RECRUITING"]
        for role in structured.get("roles", [])[:5]:
            lines.append(f"- {role.get('role_name', '')}: {role.get('person_sought', '')}")
        lines.extend(["", "2. RECRUITMENT CHANNELS"])
        for entry in structured.get("channels", []):
            lines.extend([str(entry.get("channel", "")).upper(), entry.get("approach", ""), ""])
        lines.append("3. SELECTION CRITERIA")
        for criterion in structured.get("selection_criteria", []):
            lines.append(f"- {criterion}")
        lines.extend(["", STRATEGY_TIMELINE_TEXT, "", STRATEGY_ROADMAP_TEXT, "", STRATEGY_NEXT_STEP_TEXT])
        return "\n".join(line.rstrip() for line in lines).strip()
    if generation_type == "powerhouse_board_blueprint":
        lines = ["THE BOARD MEMBERS YOUR ORGANIZATION NEEDS", ""]
        for index, role in enumerate(structured.get("priority_roles", [])[:5], 1):
            lines.extend([f"{index}. {role.get('role_name', '')}", role.get("summary", ""), ""])
        return "\n".join(lines).strip()
    lines = [meta["title"].upper(), ""]
    lines.extend(_format_value(structured))
    if meta.get("agreement"):
        lines.extend(["", REVIEW_WARNING])
    return "\n".join(line.rstrip() for line in lines).strip()


def blueprint_detailed_text(structured: dict) -> str:
    lines = ["BOARD RECRUITMENT PROFILE — DETAILED REPORT", ""]
    for index, role in enumerate(structured.get("detailed_roles", []) or structured.get("priority_roles", []), 1):
        lines.append(f"{index}. {role.get('role_name', '')}")
        for key in ["why_this_role_matters", "professional_background_to_look_for", "useful_networks", "how_this_role_contributes", "how_this_complements_the_present_board"]:
            if role.get(key):
                lines.append(f"{key.replace('_', ' ').capitalize()}: {role[key]}")
        if role.get("relevant_skills"):
            lines.append("Relevant skills: " + ", ".join(role["relevant_skills"]))
        lines.append("")
    return "\n".join(lines).strip()


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
        + (f"SPECIAL REQUIREMENTS: {meta['note']}\n\n" if meta.get("note") else "")
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
