"""Admin-only launchers and realistic test fixtures for the four customer product dashboards."""
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from auth_service import authenticate_admin
from member_auth import create_member_token, set_member_cookie


PRODUCTS = {
    "recruitment": {
        "entitlements": ["recruitment_self_guided", "recruitment_selection_onboarding"],
        "dashboard_path": "/app/board-recruitment",
    },
    "board-fundraising-game": {
        "entitlements": ["board_fundraising_game"],
        "dashboard_path": "/game/dashboard",
    },
    "strategic-planning": {
        "entitlements": [],
        "dashboard_path": "/strategic-planning/dashboard",
        "purchase_source": "strategic_planning_497",
    },
    "board-recommitment": {
        "entitlements": ["reactivation_self_guided"],
        "dashboard_path": "/board-recommitment/dashboard",
        "purchase_source": "board_recommitment_497",
    },
}

FIXTURE_VERSION = "v3"
ORG_NAME = "BrightPath Youth Alliance"
MISSION = (
    "BrightPath Youth Alliance helps young people ages 12 to 24 in underserved communities "
    "build the skills, relationships and opportunities they need to move into education, employment and stable adulthood."
)
GOALS = (
    "Serve 1,000 young people over the next 24 months, strengthen the board, diversify revenue, "
    "build a repeatable corporate partnership pipeline and improve how outcomes are measured and communicated."
)

PREVIEW_LOGO_DATA = (
    "data:image/svg+xml;utf8,"
    "%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20width='640'%20height='180'%20viewBox='0%200%20640%20180'%3E"
    "%3Crect%20width='640'%20height='180'%20rx='28'%20fill='%234F46E5'/%3E"
    "%3Ccircle%20cx='86'%20cy='90'%20r='46'%20fill='%23FFFFFF'/%3E"
    "%3Cpath%20d='M63%2092l18%2018%2032-42'%20fill='none'%20stroke='%234F46E5'%20stroke-width='12'%20stroke-linecap='round'%20stroke-linejoin='round'/%3E"
    "%3Ctext%20x='155'%20y='79'%20font-family='Arial,sans-serif'%20font-size='34'%20font-weight='700'%20fill='%23FFFFFF'%3EBrightPath%20Youth%3C/text%3E"
    "%3Ctext%20x='155'%20y='120'%20font-family='Arial,sans-serif'%20font-size='30'%20font-weight='700'%20fill='%23E0E7FF'%3EAlliance%3C/text%3E"
    "%3C/svg%3E"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def suffix(member: dict) -> str:
    return member["user_id"][-16:]


def strategic_response(lens: str) -> dict:
    rows = [
        (
            "The mission is clear about young people and opportunity. I would make the promise more specific by naming the transition we want young people to achieve and the communities we are prioritizing.",
            "I would keep the mission concise, then use one supporting statement to explain the pathway from mentoring and skills to education, employment and stable adulthood.",
        ),
        (
            "The two-year goals are directionally strong. I want the board to add a measurable revenue target, a board-capacity target and a clear outcome target for young people.",
            "I would use a quarterly scorecard so the board can see participant reach, outcomes, unrestricted revenue, corporate partners and board execution in one place.",
        ),
        (
            "Each goal needs a small number of measurable objectives with named owners and deadlines.",
            "I would create objectives for program reach, outcome measurement, corporate partnerships, individual giving, board recruitment and communications.",
        ),
        (
            "Board Recruitment should focus on the exact professional capability we are missing, especially fundraising, corporate partnerships and communications.",
            "I would recruit against a board skills map, use a structured application and interview process, and make contribution expectations explicit before appointment.",
        ),
        (
            "The Board Fundraising Game should become the board's shared fundraising planning process rather than a one-time exercise.",
            "I would use it to identify funder audiences, relationship pathways, board roles, follow-up ownership and the fundraising materials we actually need.",
        ),
        (
            "Strategic Planning should connect board ideas to accountable execution instead of ending with a document.",
            "I would require each major strategic area to have an owner, budget, milestones, evidence of progress and a recurring board review point.",
        ),
        (
            "Board Recommitment should clarify who is ready to carry responsibility during the next phase.",
            "I would use individual recommitment conversations to confirm capacity, contribution areas and whether someone should remain active, move to advisory support or step down.",
        ),
        (
            "We need stronger leadership capacity around fundraising, partnerships, communications and program evaluation.",
            "I would define which responsibilities belong to staff and which require board leadership, then recruit or develop capacity around the gaps.",
        ),
        (
            "Our operating processes are too dependent on the founder remembering the next step.",
            "I would document the recurring workflows for donor follow-up, partnership outreach, volunteer onboarding, program reporting and board accountability.",
        ),
        (
            "Our visibility is inconsistent and too focused on announcing activities instead of demonstrating outcomes and expertise.",
            "I would build a monthly content rhythm around youth outcomes, participant stories with consent, useful insight, partner visibility and clear ways to engage.",
        ),
        (
            "We have relationships, but we do not yet manage partnerships as a pipeline with clear next actions.",
            "I would segment schools, employers, community organizations and corporate partners, then assign relationship owners and next steps.",
        ),
        (
            "Fundraising is still too dependent on grants and the founder. The board needs a defined role in prospecting, introductions, cultivation and stewardship.",
            "I would build three parallel pipelines for individuals, businesses and grant funders, then track every prospect, relationship owner, next action and ask.",
        ),
        (
            "We should use one simple system for contacts, opportunities, follow-up and reporting rather than disconnected spreadsheets.",
            "I would configure a lightweight CRM and dashboard that the team can maintain consistently before adding more technology.",
        ),
        (
            "The budget should show the full cost of growth, including people, fundraising systems, communications, technology and evaluation.",
            "I would build a base budget and a growth budget, then connect every strategic priority to its actual execution cost.",
        ),
        (
            "The immediate priorities should be revenue diversification, board capacity, program outcome evidence and operating discipline.",
            "I would sequence the work so the organization first builds the people and systems required to execute the larger growth goals.",
        ),
        (
            "Major actions need owners, dates and review points. We currently have intentions that are not always converted into accountable projects.",
            "I would use 90-day execution cycles with a named owner, success measure, required resources and a board review at the end of each cycle.",
        ),
        (
            "I am willing to lead corporate partnerships and support fundraising strategy, communications and board recruitment.",
            "I would serve on a revenue and partnerships working group and take responsibility for opening qualified corporate conversations from my network.",
        ),
    ]
    response = {}
    for index, (first, second) in enumerate(rows, 1):
        response[f"s{index}_q1"] = f"{lens} {first}"
        response[f"s{index}_q2"] = f"{lens} {second}"
    return response


def strategic_transcript() -> str:
    return """Rooney: Thank you everyone. We are going section by section and agreeing the starting direction the Board wants carried forward.

Maya: On mission, I would keep the focus on young people ages 12 to 24, but I want the outcome to be clearer. We should be able to say that the pathway leads toward education, employment and stable adulthood.

Daniel: I agree. I do not think the mission needs to become longer. The detail can sit underneath it.

Aisha: On goals, I want us to add measurable revenue diversification. We cannot plan to reach more young people and leave the funding system vague.

Rooney: Agreed. We will retain the current mission direction, make the outcome language sharper, and build measurable goals around reach, outcomes, revenue and board capacity.

Maya: For the programs, I want Board Recruitment and Recommitment treated as capacity infrastructure. They are how we make sure the right people are actually carrying the strategy.

Daniel: For fundraising, we need three pipelines: individuals, businesses and grants. Every prospect should have an owner and a next action.

Aisha: Marketing should support those pipelines. Our content should show evidence, useful insight and credible stories, then give people a clear next step.

Rooney: For operations, we will document the recurring workflows and move away from founder memory being the operating system.

Maya: I can lead partnerships. Daniel can lead budget and financial tracking. Aisha can lead marketing and visibility. Rooney remains responsible for overall execution and staff coordination.

Rooney: Confirmed. We will build this into 90-day execution cycles and review progress at every board meeting."""
    

def strategic_presentation_transcript() -> str:
    return """Rooney: We are reviewing the detailed plans and confirming only the changes the Board agrees today.

Daniel: The budget section should separate the cost of maintaining current delivery from the additional cost of growth. I also want a quarterly cash forecast attached to the strategic scorecard.

Maya: On partnerships, the first 90 days should focus on twenty qualified employers and corporate prospects rather than a very broad list. I will lead introductions and help the team define the corporate proposition.

Aisha: Marketing should publish two strong evidence-led pieces each week and one partner or participant story each month, subject to consent. I will lead the board-level review of visibility.

Rooney: Agreed. Fundraising will use one CRM pipeline across individuals, businesses and grants. The board will review movement, next actions and asks monthly.

Board: Agreed.

Rooney: Those are the confirmed modifications. Everything else in the present plan remains as written."""
    

def fundraising_meeting_transcript() -> str:
    return """Rooney: We have completed the Group Game. I want us to confirm the fundraising decisions before we finish.

Maya: Our strongest individual donor audience is professionals and business owners who care about youth employment, mentoring and opportunity. Board introductions should be the first route into that audience.

Daniel: For businesses, we should prioritize employers that need early-career talent, have local operations, or already invest in youth and workforce development.

Aisha: Visibility needs to happen before most asks. We should use participant outcomes, employer stories and useful insight to build familiarity and trust.

Rooney: What is the agreed process?

Daniel: Every prospect goes into one pipeline. We identify the relationship owner, the next action and the ask. We follow the same Know, Like, Trust, Ask, Follow Up and Steward pathway.

Maya: I will open five corporate introductions in the first month.

Aisha: I will help build the case-for-support content and the monthly partner story.

Daniel: I will help set up the dashboard and review the pipeline numbers.

Rooney: Agreed. Our first 90 days are system setup, warm introductions, visibility and cultivation. Concentrated asks begin after the strongest relationships have moved through the pathway. We will review the pipeline at every board meeting."""
    

def recommitment_conclusion(name: str, role: str, direction: str) -> str:
    if direction == "Move to Advisory Board":
        return (
            f"{name} confirmed that active Board service is no longer realistic at the level the organization now requires. "
            "We agreed to move them from the active Board into an advisory relationship focused on marketing and communications. "
            "They can contribute one to two hours per month when a specific request is made and will not carry recurring governance "
            "or execution responsibility. The founder will send the advisory transition confirmation and clarify how future requests will work."
        )
    if direction == "Step Down":
        return (
            f"{name} confirmed that they are not able to recommit to active Board service because of changed work and family commitments. "
            "We agreed on a respectful departure from the Board with no continuing governance obligation. They are willing to remain supportive "
            "of the mission and may make an occasional introduction when appropriate. The founder will send the departure confirmation and complete the transition."
        )
    return (
        f"{name} confirmed that they want to continue serving as {role}. We agreed that their primary contribution "
        "will be a defined board-level responsibility rather than general support. They can commit four to six hours "
        "per month, will attend scheduled Board meetings, and will report progress on the responsibility they accept. "
        "The organization will provide clear information, deadlines, access to the right staff contact and the materials needed to execute."
    )


def recruitment_answers() -> dict:
    return {
        "mission": MISSION,
        "current_board": (
            "We currently have five board members. Our Chair is a secondary-school leader with strong community credibility. "
            "Our Treasurer is a chartered accountant and supports finance and budgeting. One member is a youth social worker "
            "who understands our participants and programs. One member is an attorney who helps with governance. One member "
            "is a community organizer with local relationships. The board is committed, but we do not currently have deep "
            "fundraising leadership, corporate partnership experience or strong marketing and communications expertise."
        ),
        "important_areas": (
            "Fundraising strategy, individual giving, corporate partnerships, grant development, marketing and communications, "
            "program evaluation, finance, governance, technology, employer relationships, community engagement and board accountability."
        ),
        "support_needs": (
            "We want to recruit three new board members. We need one person with senior fundraising and major-donor experience who can "
            "help build an individual giving system and coach the board on fundraising. We need one person with corporate partnerships "
            "or business development experience who can open employer and sponsor relationships. We need one marketing and communications "
            "leader who can strengthen visibility, messaging and digital reach. All three must be willing to carry clear board-level responsibility."
        ),
    }


def applicant_answers() -> dict:
    return {
        "full_name": "Jordan Ellis",
        "email": "jordan.ellis@nonprofitboardbuilder.internal",
        "phone": "+1 555 010 2040",
        "city": "Atlanta",
        "state_region": "Georgia",
        "country": "United States",
        "profession": "Director of Corporate Partnerships",
        "employer": "Fictional Growth Partners",
        "linkedin": "https://www.linkedin.com/in/jordan-ellis-preview",
        "board_experience": "I previously served for three years on the development committee of a youth mentoring nonprofit.",
        "why_interested": "I care about helping young people build access to employment and professional networks, and I want to contribute practical partnership experience.",
        "skills_experience": "Corporate partnerships, sponsorship development, business development, relationship management, proposal development and executive presentations.",
        "fundraising_support": "Warm introductions, corporate sponsorship conversations, prospect strategy, cultivation meetings and selected asks where I have an appropriate relationship.",
        "relationships": "Employers, local business leaders, professional associations and corporate social-impact teams.",
        "monthly_time": "5 to 6 hours per month",
        "attend_meetings": "Yes",
        "accept_responsibility": "Yes",
        "causes": "Youth opportunity, workforce development, education and economic mobility.",
    }



def create_admin_dashboard_preview_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/admin/dashboard-preview")

    async def preview_member(admin: dict) -> dict:
        fingerprint = hashlib.sha256(admin["user_id"].encode("utf-8")).hexdigest()[:16]
        user_id = f"admin-dashboard-preview-{FIXTURE_VERSION}-{fingerprint}"
        email = f"dashboard-preview-{FIXTURE_VERSION}-{fingerprint}@nonprofitboardbuilder.internal"
        now = now_iso()
        await db.members.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "email": email,
                    "first_name": "Rooney",
                    "last_name": "Admin Preview",
                    "internal_admin_entitlement": True,
                    "internal_dashboard_preview": True,
                    "review_mode": True,
                    "admin_preview_fixture_version": FIXTURE_VERSION,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "password_hash": "",
                    "lead_ids": [],
                    "stripe_customer_id": "",
                    "entitlements": [],
                    "created_at": now,
                },
            },
            upsert=True,
        )
        return await db.members.find_one({"user_id": user_id}, {"_id": 0})

    async def seed_recruitment_preview(member: dict) -> None:
        now = now_iso()
        tag = suffix(member)
        token = f"admin-preview-recruitment-{tag}"
        lead_id = f"admin-preview-recruitment-lead-{tag}"
        answers = recruitment_answers()
        opportunity_id = f"admin-preview-recruitment-opportunity-{tag}"
        opportunity_slug = f"brightpath-youth-alliance-preview-{tag}"

        await db.recruitment_free_assessments.update_one(
            {"token": token},
            {"$setOnInsert": {
                "token": token,
                "lead_id": lead_id,
                "name": "Rooney Akpesiri",
                "email": member["email"],
                "organization": ORG_NAME,
                "desired_count": 3,
                "answers": answers,
                "state": {
                    "lead_created": True,
                    "question_1_completed": True,
                    "question_2_completed": True,
                    "question_3_completed": True,
                    "question_4_completed": True,
                    "result_generated": False,
                    "video_page_viewed": True,
                    "checkout_started": True,
                    "paid": True,
                    "welcome_completed": True,
                    "intake_completed": True,
                    "dashboard_entered": True,
                },
                "result": None,
                "member_user_id": member["user_id"],
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )

        await db.funnel_leads.update_one(
            {"lead_id": lead_id},
            {"$setOnInsert": {
                "lead_id": lead_id,
                "result_token": token,
                "member_user_id": member["user_id"],
                "offer_source": "recruitment",
                "lead_source": "internal_admin_preview",
                "name": "Rooney Akpesiri",
                "email": member["email"],
                "organization": ORG_NAME,
                "phone": "+44 7700 900123",
                "website": "https://example.org/brightpath",
                "city": "Atlanta",
                "state_region": "Georgia",
                "country": "United States",
                "answers": {
                    "mission": answers["mission"],
                    "present_board": answers["current_board"],
                    "important_areas": answers["important_areas"],
                    "accomplish": answers["support_needs"],
                    "new_members_needed": "3",
                },
                "free_assessment_result": None,
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )

        await db.members.update_one(
            {"user_id": member["user_id"]},
            {"$addToSet": {"lead_ids": lead_id}},
        )

        await db.recruitment_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$setOnInsert": {
                "data": {
                    "organization_name": ORG_NAME,
                    "mission": MISSION,
                    "present_board": answers["current_board"],
                    "new_members_count": "3",
                    "current_board_strengths": "Education, finance, governance, youth services and community relationships.",
                    "desired_board_skills": ["Fundraising", "Corporate Partnerships", "Marketing and Communications"],
                    "priorities": answers["support_needs"],
                    "important_areas": answers["important_areas"],
                    "founder_title": "Founder and Executive Director",
                    "city": "Atlanta",
                    "state_region": "Georgia",
                    "country": "United States",
                },
                "strategy_intake": {
                    "meeting_frequency": "Monthly board meeting with committee work between meetings.",
                    "geography": "United States, with virtual participation available.",
                    "network": "Existing relationships with schools, youth-service organizations, employers and local business leaders.",
                    "recruitment_channels": "LinkedIn, professional associations, referrals, employer networks and nonprofit board-matching platforms.",
                    "time_expectation": "Approximately 5 hours per month plus board meetings.",
                },
                "branding": {
                    "logo_data": PREVIEW_LOGO_DATA,
                    "primary_color": "#4F46E5",
                    "secondary_color": "#F8FAFC",
                },
                "onboarding_session": {
                    "date": "2026-10-08",
                    "time": "18:00",
                    "timezone": "Eastern Time (ET)",
                    "format": "Virtual",
                    "link": "https://example.org/brightpath-onboarding",
                    "location": "",
                    "prepare": "Please review the Organization Overview, Board Manual and agreements before the session.",
                    "status": "Scheduled",
                },
                "confirmed": False,
                "recruitment_profile_confirmed": False,
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )

        await db.opportunities.update_one(
            {"opportunity_id": opportunity_id},
            {"$setOnInsert": {
                "opportunity_id": opportunity_id,
                "user_id": member["user_id"],
                "slug": opportunity_slug,
                "organization_name": ORG_NAME,
                "status": "Draft",
                "custom_questions": [],
                "application_saved": False,
                "email_content": {},
                "broadcast_initiated": False,
                "broadcast_id": "",
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )

        applicants = [
            {
                "application_id": f"admin-preview-applicant-jordan-{tag}",
                "email": "jordan.ellis@nonprofitboardbuilder.internal",
                "name": "Jordan Ellis",
                "profession": "Director of Corporate Partnerships",
                "employer": "Fictional Growth Partners",
                "source": "Board Application Form",
                "status": "Applied",
                "interview_completed": False,
                "reference_check_status": "Not started",
                "background_check": {"status": "Not started"},
                "answers": applicant_answers(),
                "notes": (
                    "PRELOADED TEST NOTES: Jordan has strong corporate partnership experience and previous youth-nonprofit committee service. "
                    "Use this candidate to test the interview invitation, candidate-specific interview guide, interview completion and decision controls."
                ),
                "cv_text": (
                    "Jordan Ellis. Director of Corporate Partnerships. Twelve years of business development and partnership experience. "
                    "Led employer engagement, sponsorship proposals, executive relationship management and community-investment partnerships. "
                    "Previous volunteer development-committee experience with a youth mentoring nonprofit."
                ),
            },
            {
                "application_id": f"admin-preview-applicant-priya-{tag}",
                "email": "priya.mensah@nonprofitboardbuilder.internal",
                "name": "Priya Mensah",
                "profession": "Major Gifts and Development Director",
                "employer": "Fictional Community Foundation",
                "source": "LinkedIn",
                "status": "Moving Forward",
                "interview_completed": True,
                "reference_check_status": "In Progress",
                "background_check": {
                    "status": "In progress",
                    "required": "Yes",
                    "requested_date": "2026-09-18",
                    "completed_date": "",
                    "notes": "Local provider contacted. Verification is still in progress.",
                },
                "answers": {
                    "full_name": "Priya Mensah",
                    "email": "priya.mensah@nonprofitboardbuilder.internal",
                    "phone": "+1 555 010 2050",
                    "city": "Atlanta",
                    "state_region": "Georgia",
                    "country": "United States",
                    "profession": "Major Gifts and Development Director",
                    "employer": "Fictional Community Foundation",
                    "linkedin": "https://www.linkedin.com/in/priya-mensah-preview",
                    "board_experience": "Four years on a community arts board, including service on the development committee.",
                    "why_interested": "I want to help a youth-serving organization build a stronger fundraising system and donor relationships.",
                    "skills_experience": "Major gifts, donor strategy, stewardship, grant fundraising, campaign planning and Board fundraising coaching.",
                    "fundraising_support": "Prospect strategy, donor introductions, cultivation, selected asks, stewardship and fundraising coaching.",
                    "relationships": "Philanthropic advisors, foundation staff, major donors and nonprofit development professionals.",
                    "monthly_time": "4 to 5 hours per month",
                    "attend_meetings": "Yes",
                    "accept_responsibility": "Yes",
                    "causes": "Youth opportunity, education and economic mobility.",
                },
                "notes": "PRELOADED TEST NOTES: Interview completed. Priya is moving forward. Use this candidate to test the automated reference process and background-check record.",
                "cv_text": "Priya Mensah. Major Gifts and Development Director. Fifteen years in nonprofit fundraising, donor stewardship, campaigns and Board development.",
            },
            {
                "application_id": f"admin-preview-applicant-marcus-{tag}",
                "email": "marcus.chen@nonprofitboardbuilder.internal",
                "name": "Marcus Chen",
                "profession": "Vice President of Marketing",
                "employer": "Fictional Impact Brands",
                "source": "Referral",
                "status": "Conditional Appointment",
                "interview_completed": True,
                "reference_check_status": "Completed",
                "background_check": {
                    "status": "Not Required",
                    "required": "No",
                    "requested_date": "",
                    "completed_date": "",
                    "notes": "The organization documented that no background check is required for this Board role.",
                },
                "answers": {
                    "full_name": "Marcus Chen",
                    "email": "marcus.chen@nonprofitboardbuilder.internal",
                    "phone": "+1 555 010 2060",
                    "city": "Atlanta",
                    "state_region": "Georgia",
                    "country": "United States",
                    "profession": "Vice President of Marketing",
                    "employer": "Fictional Impact Brands",
                    "linkedin": "https://www.linkedin.com/in/marcus-chen-preview",
                    "board_experience": "Served on a nonprofit communications advisory committee and led pro bono campaigns.",
                    "why_interested": "I want to help BrightPath become more visible to employers, funders and families.",
                    "skills_experience": "Brand strategy, communications, digital marketing, campaign planning, storytelling and executive communications.",
                    "fundraising_support": "Campaign messaging, case-for-support development, partner stories and introductions to business contacts.",
                    "relationships": "Marketing leaders, agency executives, local business owners and corporate communications teams.",
                    "monthly_time": "4 hours per month",
                    "attend_meetings": "Yes",
                    "accept_responsibility": "Yes",
                    "causes": "Youth development, employment pathways and education.",
                },
                "notes": "PRELOADED TEST NOTES: References are complete, no background check is required, agreements are signed and the Board Member Profile is complete. Use this candidate to test Final Appointment, Onboarding Conclusion, Appointment Letter and Portfolio.",
                "cv_text": "Marcus Chen. Vice President of Marketing. Eighteen years leading brand, communications and growth campaigns. Pro bono nonprofit campaign experience.",
                "emails_sent": {"conditional_offer": now},
                "onboarding_conclusion": {
                    "board_role": "Board Member — Marketing and Communications",
                    "agreed_primary_contribution_area": "Marketing, visibility and partner storytelling",
                    "agreed_responsibility": "Provide board-level leadership for the annual communications plan and help turn program evidence into credible fundraising and partnership content.",
                    "agreed_leadership": "Lead quarterly Board review of visibility, messaging and campaign performance.",
                    "how_their_experience_will_be_used": "Use brand strategy and executive communications experience to strengthen the case for support, digital visibility and partner communications.",
                    "organization_support_agreed": "Provide timely impact data, participant stories with consent, campaign priorities and access to the staff contact responsible for communications.",
                    "immediate_next_steps": "Review the current case for support, propose the first 90-day communications priorities and identify two partner-story opportunities.",
                    "private_notes": "Admin preview fixture. Click Save Onboarding Conclusion to test the real save action.",
                },
            },
        ]

        for row in applicants:
            snapshot = {
                "full_name": row["name"],
                "email": row["email"],
                "phone": row["answers"].get("phone", ""),
                "linkedin": row["answers"].get("linkedin", ""),
                "profession": row["profession"],
                "employer": row["employer"],
                "city": row["answers"].get("city", ""),
                "state_region": row["answers"].get("state_region", ""),
                "country": row["answers"].get("country", ""),
            }
            doc = {
                "application_id": row["application_id"],
                "owner_user_id": member["user_id"],
                "opportunity_id": opportunity_id,
                "applicant_email": row["email"],
                "source": row["source"],
                "status": row["status"],
                "profile_snapshot": snapshot,
                "answers": row["answers"],
                "notes": row["notes"],
                "cv_file_id": "",
                "cv_filename": f"{row['name'].replace(' ', '-')}-Preview-CV.pdf",
                "cv_text": row["cv_text"],
                "interview_guide": {"status": "Pending"},
                "interview_completed": row["interview_completed"],
                "reference_check_status": row["reference_check_status"],
                "references": [],
                "background_check": row["background_check"],
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }
            if row.get("emails_sent"):
                doc["emails_sent"] = row["emails_sent"]
            if row.get("onboarding_conclusion"):
                doc["onboarding_conclusion"] = row["onboarding_conclusion"]
            await db.opportunity_applications.update_one(
                {"application_id": row["application_id"]},
                {"$setOnInsert": doc},
                upsert=True,
            )

        priya_id = f"admin-preview-applicant-priya-{tag}"
        await db.reference_processes.update_one(
            {"owner_user_id": member["user_id"], "application_id": priya_id},
            {"$setOnInsert": {
                "process_id": f"admin-preview-reference-priya-{tag}",
                "owner_user_id": member["user_id"],
                "application_id": priya_id,
                "candidate_name": "Priya Mensah",
                "candidate_email": "priya.mensah@nonprofitboardbuilder.internal",
                "candidate_token": f"admin-preview-priya-candidate-{tag}",
                "status": "In Progress",
                "references": [
                    {
                        "reference_id": f"admin-preview-priya-ref-1-{tag}",
                        "name": "Elena Ruiz",
                        "position": "Chief Development Officer",
                        "organization": "Fictional Civic Trust",
                        "relationship": "Former supervisor",
                        "duration": "5 years",
                        "email": f"elena.ruiz-{tag}@nonprofitboardbuilder.internal",
                        "phone": "+1 555 010 4101",
                        "referee_token": f"admin-preview-priya-ref-token-1-{tag}",
                        "status": "Completed",
                        "response": {
                            "capacity": "I supervised Priya directly for five years while she led major-gift strategy and donor stewardship.",
                            "reliability": "Priya is highly reliable, prepares thoroughly and consistently follows through on commitments.",
                            "strengths": "Relationship building, strategic thinking, calm leadership and the ability to translate fundraising goals into practical action.",
                            "teamwork": "I have no conduct concerns. Priya works well across teams and communicates directly when expectations need clarification.",
                            "recommendation": "Yes. I would be comfortable recommending Priya for nonprofit Board service.",
                        },
                        "completed_at": now,
                    },
                    {
                        "reference_id": f"admin-preview-priya-ref-2-{tag}",
                        "name": "Samuel Okafor",
                        "position": "Executive Director",
                        "organization": "Fictional Youth Futures Network",
                        "relationship": "Nonprofit partner",
                        "duration": "3 years",
                        "email": f"samuel.okafor-{tag}@nonprofitboardbuilder.internal",
                        "phone": "+1 555 010 4102",
                        "referee_token": f"admin-preview-priya-ref-token-2-{tag}",
                        "status": "Sent",
                    },
                ],
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )

        marcus_id = f"admin-preview-applicant-marcus-{tag}"
        await db.reference_processes.update_one(
            {"owner_user_id": member["user_id"], "application_id": marcus_id},
            {"$setOnInsert": {
                "process_id": f"admin-preview-reference-marcus-{tag}",
                "owner_user_id": member["user_id"],
                "application_id": marcus_id,
                "candidate_name": "Marcus Chen",
                "candidate_email": "marcus.chen@nonprofitboardbuilder.internal",
                "candidate_token": f"admin-preview-marcus-candidate-{tag}",
                "status": "Completed",
                "references": [
                    {
                        "reference_id": f"admin-preview-marcus-ref-1-{tag}",
                        "name": "Diana Lee",
                        "position": "Chief Executive Officer",
                        "organization": "Fictional Impact Brands",
                        "relationship": "Current colleague",
                        "duration": "7 years",
                        "email": f"diana.lee-{tag}@nonprofitboardbuilder.internal",
                        "phone": "+1 555 010 4201",
                        "referee_token": f"admin-preview-marcus-ref-token-1-{tag}",
                        "status": "Completed",
                        "response": {
                            "capacity": "Marcus and I have worked together for seven years in senior leadership.",
                            "reliability": "He is dependable, clear about commitments and follows through.",
                            "strengths": "Strategic communications, executive judgement, collaboration and brand leadership.",
                            "teamwork": "I have no concerns relevant to a position of responsibility.",
                            "recommendation": "Yes. I recommend Marcus for Board service.",
                        },
                        "completed_at": now,
                    },
                    {
                        "reference_id": f"admin-preview-marcus-ref-2-{tag}",
                        "name": "Tanya Brooks",
                        "position": "Executive Director",
                        "organization": "Fictional Community Arts Alliance",
                        "relationship": "Pro bono nonprofit client",
                        "duration": "4 years",
                        "email": f"tanya.brooks-{tag}@nonprofitboardbuilder.internal",
                        "phone": "+1 555 010 4202",
                        "referee_token": f"admin-preview-marcus-ref-token-2-{tag}",
                        "status": "Completed",
                        "response": {
                            "capacity": "Marcus led a pro bono communications campaign for our organization and continued advising us after launch.",
                            "reliability": "He was consistent, practical and responsive throughout the work.",
                            "strengths": "He listens carefully, simplifies complex messaging and brings strong professional networks.",
                            "teamwork": "No concerns. He was respectful with staff, volunteers and Board Members.",
                            "recommendation": "Yes. I would confidently recommend him.",
                        },
                        "completed_at": now,
                    },
                ],
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )

        profile_token = f"admin-preview-board-profile-marcus-{tag}"
        await db.board_profile_links.update_one(
            {"user_id": member["user_id"], "application_id": marcus_id},
            {"$setOnInsert": {
                "token": profile_token,
                "user_id": member["user_id"],
                "application_id": marcus_id,
                "status": "Completed",
                "prefill": {
                    "full_name": "Marcus Chen",
                    "email": "marcus.chen@nonprofitboardbuilder.internal",
                    "professional_title": "Vice President of Marketing",
                    "employer": "Fictional Impact Brands",
                    "linkedin": "https://www.linkedin.com/in/marcus-chen-preview",
                    "location": "Atlanta, Georgia",
                },
                "internal_preview": True,
                "created_at": now,
            }},
            upsert=True,
        )
        await db.board_profile_responses.update_one(
            {"user_id": member["user_id"], "application_id": marcus_id},
            {"$setOnInsert": {
                "response_id": f"admin-preview-board-profile-response-marcus-{tag}",
                "user_id": member["user_id"],
                "application_id": marcus_id,
                "data": {
                    "full_name": "Marcus Chen",
                    "email": "marcus.chen@nonprofitboardbuilder.internal",
                    "professional_title": "Vice President of Marketing",
                    "employer": "Fictional Impact Brands",
                    "skills": "Brand strategy, communications, digital marketing, executive messaging and partnership storytelling",
                    "desired_contribution": "Lead board-level communications strategy and help strengthen fundraising and partner-facing materials.",
                    "monthly_capacity": "4 hours per month",
                    "leadership_interest": "Yes — marketing and communications",
                    "networks": "Marketing executives, agency leaders, local businesses and corporate communications teams.",
                },
                "submitted_at": now,
                "internal_preview": True,
            }},
            upsert=True,
        )

        for agreement_type, title in [
            ("board_member_agreement", "Board Member Agreement"),
            ("confidentiality_agreement", "Confidentiality Agreement"),
            ("conflict_of_interest_agreement", "Conflict of Interest Agreement"),
        ]:
            await db.signature_requests.update_one(
                {"owner_user_id": member["user_id"], "application_id": marcus_id, "agreement_type": agreement_type},
                {"$setOnInsert": {
                    "request_id": f"admin-preview-{agreement_type}-{tag}",
                    "token": f"admin-preview-sign-{agreement_type}-{tag}",
                    "owner_user_id": member["user_id"],
                    "application_id": marcus_id,
                    "agreement_type": agreement_type,
                    "agreement_title": title,
                    "material_id": f"admin-preview-material-{agreement_type}-{tag}",
                    "agreement_version": 1,
                    "document_snapshot": f"{title}\n\nThis is a realistic Admin Preview agreement for BrightPath Youth Alliance. Use the live generator in Step 7 to test creation of the organization's actual document.",
                    "board_member_name": "Marcus Chen",
                    "board_member_email": "marcus.chen@nonprofitboardbuilder.internal",
                    "organization_name": ORG_NAME,
                    "status": "Signed",
                    "signed": {
                        "typed_signature": "Marcus Chen",
                        "email": "marcus.chen@nonprofitboardbuilder.internal",
                        "date": "2026-09-20",
                        "signed_at": now,
                        "method": "typed",
                        "signature_image": "",
                    },
                    "internal_preview": True,
                    "created_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )


    async def seed_guided_product(member: dict, product: str, config: dict) -> str:
        now = now_iso()
        tag = suffix(member)
        session_id = f"admin_preview_{FIXTURE_VERSION}_{product.replace('-', '_')}_{tag}"
        lead_token = f"admin-preview-{FIXTURE_VERSION}-{product}-{tag}"
        await db.guided_product_leads.update_one(
            {"token": lead_token},
            {"$setOnInsert": {
                "token": lead_token,
                "product": product,
                "name": "Rooney Akpesiri",
                "email": member["email"],
                "organization": ORG_NAME,
                "board_count": 5,
                "internal_preview": True,
                "followup_status": "converted",
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$setOnInsert": {
                "session_id": session_id,
                "status": "completed",
                "payment_status": "paid",
                "offer_source": "internal_admin_preview",
                "purchase_source": config["purchase_source"],
                "guided_lead_token": lead_token,
                "lead_email": member["email"],
                "claimed_by_user_id": member["user_id"],
                "amount": 0,
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )
        answers = {"mission": MISSION, "goals": GOALS}
        if product == "strategic-planning":
            answers.update({
                "objectives": (
                    "Increase program reach to 1,000 young people, build a diversified fundraising pipeline, recruit three strategic board members, "
                    "and implement a quarterly organization scorecard."
                ),
                "programs": "Board Recruitment\nBoard Fundraising Game\nStrategic Planning\nBoard Recommitment",
                "team_building": "Strengthen staff leadership and give board members defined strategic ownership instead of general volunteer tasks.",
                "operations": "Document recurring workflows, clarify decision rights and use 90-day execution cycles with accountability reviews.",
                "marketing": "Publish consistent evidence-led content, strengthen participant and partner storytelling, and connect visibility to fundraising and partnerships.",
                "partnerships": "Build a managed pipeline of schools, employers, community partners and corporate sponsors with named relationship owners.",
                "fundraising": "Diversify beyond grants by building individual donor, corporate partnership and grant pipelines with board participation.",
                "technology": "Use one CRM for prospects and relationships, a simple outcome dashboard and shared project tracking for strategic execution.",
                "budget": "Current annual operating budget is approximately $650,000. Growth requires additional investment in fundraising capacity, communications, technology and evaluation.",
                "priorities": "Revenue diversification, board capacity, measurable youth outcomes, corporate partnerships and repeatable operating systems.",
                "action_planning": "Work in 90-day cycles with named owners, deadlines, resources, measures and a board review at the end of each cycle.",
                "next_meeting": "October 15, 2026 at 6:00 PM Eastern Time",
            })
        await db.guided_product_intakes.update_one(
            {"session_id": session_id},
            {"$setOnInsert": {
                "session_id": session_id,
                "product": product,
                "answers": answers,
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )

        if product == "strategic-planning":
            project_id = f"admin-preview-sp-{tag}"
            await db.sp_projects.update_one(
                {"guided_session_id": session_id},
                {"$setOnInsert": {
                    "project_id": project_id,
                    "guided_session_id": session_id,
                    "organization_name": ORG_NAME,
                    "founder_name": "Rooney Akpesiri",
                    "founder_email": member["email"],
                    "founder_title": "Founder and Executive Director",
                    "mission": MISSION,
                    "status": "Active",
                    "generic_form_token": f"admin-preview-sp-form-{tag}",
                    "internal_preview": True,
                    "created_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )
            people = [
                (
                    f"admin-preview-sp-lead-{tag}",
                    "Rooney Akpesiri",
                    member["email"],
                    "Lead User",
                    "Founder and Executive Director",
                    "Founder perspective:",
                ),
                (
                    f"admin-preview-sp-maya-{tag}",
                    "Maya Thompson",
                    f"maya.thompson-{tag}@nonprofitboardbuilder.internal",
                    "Board Chair",
                    "Education leadership and community relationships",
                    "Board Chair perspective:",
                ),
                (
                    f"admin-preview-sp-daniel-{tag}",
                    "Daniel Brooks",
                    f"daniel.brooks-{tag}@nonprofitboardbuilder.internal",
                    "Treasurer",
                    "Finance, risk and business operations",
                    "Treasurer perspective:",
                ),
                (
                    f"admin-preview-sp-aisha-{tag}",
                    "Aisha Patel",
                    f"aisha.patel-{tag}@nonprofitboardbuilder.internal",
                    "Board Member",
                    "Marketing, communications and partnerships",
                    "Marketing perspective:",
                ),
            ]
            for participant_id, name, email, role, expertise, lens in people:
                await db.sp_participants.update_one(
                    {"participant_id": participant_id},
                    {"$setOnInsert": {
                        "participant_id": participant_id,
                        "project_id": project_id,
                        "name": name,
                        "email": email,
                        "role": role,
                        "expertise": expertise,
                        "status": "COMPLETED",
                        "form_token": f"{participant_id}-form",
                        "review_status": "NOT SENT",
                        "review_token": f"{participant_id}-review",
                        "response": strategic_response(lens),
                        "submitted_at": now,
                        "internal_preview": True,
                        "created_at": now,
                    }},
                    upsert=True,
                )
            participant_ids = [row[0] for row in people]
            decisions = {f"s{index}": participant_ids[(index - 1) % len(participant_ids)] for index in range(1, 18)}
            await db.sp_sessions.update_one(
                {"project_id": project_id},
                {"$setOnInsert": {
                    "project_id": project_id,
                    "decisions": decisions,
                    "transcript": strategic_transcript(),
                    "status": "NOT STARTED",
                    "current_section_index": 0,
                    "internal_preview": True,
                    "created_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )
            await db.sp_plans.update_one(
                {"project_id": project_id},
                {"$setOnInsert": {
                    "project_id": project_id,
                    "status": "NONE",
                    "display_text": "",
                    "areas": [],
                    "presentation_meeting": {
                        "meeting_date": "2026-10-29",
                        "start_time": "18:00",
                        "timezone_name": "America/New_York",
                        "meeting_format": "Virtual",
                        "meeting_link": "https://example.org/admin-preview-strategic-meeting",
                        "meeting_location": "",
                        "note": "Admin preview presentation meeting.",
                        "status": "SCHEDULED",
                        "transcript": strategic_presentation_transcript(),
                    },
                    "active_delegation": {
                        "assignments": {},
                        "transcript": (
                            "Rooney: Maya will lead corporate partnerships, Daniel will lead budget and financial tracking, "
                            "Aisha will lead marketing and visibility, and I will coordinate implementation across the plan. "
                            "Each leader will bring evidence of progress and decisions required to the next board meeting."
                        ),
                    },
                    "follow_up_meeting": {
                        "transcript": (
                            "Rooney: We reviewed the first 30 days. Maya opened four qualified employer conversations. "
                            "Daniel completed the base and growth budget. Aisha established the content calendar. "
                            "The Board agreed to keep the present direction and increase follow-up discipline in the corporate pipeline."
                        ),
                    },
                    "internal_preview": True,
                    "created_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )

        elif product == "board-recommitment":
            await db.board_reactivation_intakes.update_one(
                {"guided_session_id": session_id},
                {"$setOnInsert": {
                    "user_id": member["user_id"],
                    "organization_name": ORG_NAME,
                    "founder_title": "Founder and Executive Director",
                    "phone": "+44 7700 900123",
                    "mission": MISSION,
                    "organization_goals": GOALS,
                    "direction_12_24": "Grow program reach, diversify revenue and build a board that carries strategic leadership responsibility.",
                    "board_help_accomplish": "Fundraising, corporate partnerships, visibility, financial oversight, outcome measurement and strategic accountability.",
                    "active_board_vision": "A board where every member owns a clear contribution area and reports progress against agreed priorities.",
                    "current_skills": "Education, finance, legal, youth services and community relationships.",
                    "missing_skills": "Fundraising leadership, corporate partnerships, marketing and communications.",
                    "disengage_reason": "Roles became too general and meetings focused on updates rather than clear ownership and execution.",
                    "expected_contribution": "Attend meetings, carry an agreed board-level responsibility, make introductions where appropriate and follow through on assignments.",
                    "actually_happening": "A small number of members carry most of the work while several members mainly attend meetings and offer general advice.",
                    "founder_desired_outcomes": "Leave the process with a smaller, clearer and more committed active board.",
                    "founder_board_support_needed": "Revenue growth, partnerships, visibility, governance and accountability.",
                    "guided_session_id": session_id,
                    "guided_answers": answers,
                    "internal_preview": True,
                    "submitted_at": now,
                }},
                upsert=True,
            )
            audit_answers = {
                "co_leader_1": 2, "co_leader_2": 2,
                "co_facilitator_1": 2, "co_facilitator_2": 1,
                "co_architect_1": 3, "co_architect_2": 2,
                "co_mobilizer_1": 1, "co_mobilizer_2": 2,
                "co_evaluator_1": 2, "co_evaluator_2": 2,
                "co_reporter_1": 2, "co_reporter_2": 1,
            }
            await db.founder_board_audits.update_one(
                {"user_id": member["user_id"]},
                {"$setOnInsert": {
                    "user_id": member["user_id"],
                    "answers": audit_answers,
                    "desired_outcomes": "Create a board where every continuing member has a clear reason for serving and a specific responsibility they are prepared to own.",
                    "board_support_needed": "Help build fundraising, corporate partnerships, visibility, financial oversight and accountability for strategic priorities.",
                    "result": None,
                    "internal_preview": True,
                    "created_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )
            recommitment_yes = "Yes, I am ready to recommit and continue serving."
            recommitment_unsure = "I am not sure yet. I need more information or would like to discuss my role before deciding."
            recommitment_no = "No, I am not able to recommit to serving on the Board."
            members = [
                {
                    "id": f"admin-preview-recommit-maya-{tag}",
                    "name": "Maya Thompson",
                    "email": f"maya.recommit-{tag}@nonprofitboardbuilder.internal",
                    "role": "Board Chair",
                    "direction": "Remain and Step Up",
                    "response": {
                        "full_name": "Maya Thompson",
                        "email": f"maya.recommit-{tag}@nonprofitboardbuilder.internal",
                        "phone": "+1 555 010 3101",
                        "recommitment": recommitment_yes,
                        "why_joined": "I joined because I believe young people need stronger pathways into education, employment and professional networks.",
                        "expertise": ["Education", "Leadership", "Community Partnerships"],
                        "expertise_other": "",
                        "participation_barriers": "The main barrier has been unclear ownership between meetings.",
                        "contribution_interests": ["Corporate partnerships", "Board leadership", "Fundraising"],
                        "ownership_area": "I am willing to own employer and corporate partnership development at board level.",
                        "leadership_interest": "Yes",
                        "leadership_area": "Corporate partnerships and employer engagement",
                        "strengths_resources": "School and employer relationships, facilitation skills and senior leadership experience.",
                        "monthly_availability": "5 to 6 hours per month",
                        "experience_improvement": "Clear priorities, written responsibilities and a short progress review at every board meeting.",
                        "decision_reason": "",
                        "advisory_openness": "",
                        "decision_support": "",
                        "anything_else": "I want the board to spend more time helping build the future and less time only hearing updates.",
                    },
                },
                {
                    "id": f"admin-preview-recommit-daniel-{tag}",
                    "name": "Daniel Brooks",
                    "email": f"daniel.recommit-{tag}@nonprofitboardbuilder.internal",
                    "role": "Treasurer",
                    "direction": "Remain and Step Up",
                    "response": {
                        "full_name": "Daniel Brooks",
                        "email": f"daniel.recommit-{tag}@nonprofitboardbuilder.internal",
                        "phone": "+1 555 010 3102",
                        "recommitment": recommitment_yes,
                        "why_joined": "I wanted to help a growing youth organization build strong financial discipline and sustainable funding.",
                        "expertise": ["Finance", "Accounting", "Risk Management"],
                        "expertise_other": "",
                        "participation_barriers": "I have sometimes received financial information too late to help shape decisions.",
                        "contribution_interests": ["Finance", "Fundraising", "Operations"],
                        "ownership_area": "I can own board-level financial planning, cash visibility and fundraising performance reporting.",
                        "leadership_interest": "Yes",
                        "leadership_area": "Finance and performance reporting",
                        "strengths_resources": "Financial modelling, budgeting, controls and business contacts.",
                        "monthly_availability": "4 hours per month",
                        "experience_improvement": "A board pack sent in advance with the key numbers, decisions and risks clearly identified.",
                        "decision_reason": "",
                        "advisory_openness": "",
                        "decision_support": "",
                        "anything_else": "I am willing to help set up a simple fundraising dashboard as long as staff maintain the underlying data.",
                    },
                },
                {
                    "id": f"admin-preview-recommit-aisha-{tag}",
                    "name": "Aisha Patel",
                    "email": f"aisha.recommit-{tag}@nonprofitboardbuilder.internal",
                    "role": "Board Member",
                    "direction": "Move to Advisory Board",
                    "response": {
                        "full_name": "Aisha Patel",
                        "email": f"aisha.recommit-{tag}@nonprofitboardbuilder.internal",
                        "phone": "+1 555 010 3103",
                        "recommitment": recommitment_unsure,
                        "why_joined": "I care about youth opportunity and originally joined because the organization needed marketing support.",
                        "expertise": ["Marketing", "Communications", "Brand Strategy"],
                        "expertise_other": "",
                        "participation_barriers": "My work schedule has changed and I cannot consistently carry an active board workload.",
                        "contribution_interests": ["Marketing", "Communications"],
                        "ownership_area": "I could advise on major campaigns, but I do not think I can own an active monthly responsibility.",
                        "leadership_interest": "I would like to discuss this",
                        "leadership_area": "",
                        "strengths_resources": "Brand strategy, communications planning and creative-industry relationships.",
                        "monthly_availability": "1 to 2 hours per month",
                        "experience_improvement": "A lighter advisory role with specific requests and more notice.",
                        "decision_reason": "",
                        "advisory_openness": "Yes, I would be open to an advisory role.",
                        "decision_support": "I need clarity on what an advisory role would require before deciding.",
                        "anything_else": "I want to stay connected to the mission even if active board service is no longer realistic.",
                    },
                },
                {
                    "id": f"admin-preview-recommit-marcus-{tag}",
                    "name": "Marcus Reed",
                    "email": f"marcus.recommit-{tag}@nonprofitboardbuilder.internal",
                    "role": "Board Member",
                    "direction": "Step Down",
                    "response": {
                        "full_name": "Marcus Reed",
                        "email": f"marcus.recommit-{tag}@nonprofitboardbuilder.internal",
                        "phone": "+1 555 010 3104",
                        "recommitment": recommitment_no,
                        "why_joined": "",
                        "expertise": [],
                        "expertise_other": "",
                        "participation_barriers": "",
                        "contribution_interests": [],
                        "ownership_area": "",
                        "leadership_interest": "",
                        "leadership_area": "",
                        "strengths_resources": "",
                        "monthly_availability": "",
                        "experience_improvement": "",
                        "decision_reason": "My work and family commitments have changed and I cannot give the board the consistency the next phase requires.",
                        "advisory_openness": "I am open to occasional introductions after I step down.",
                        "decision_support": "",
                        "anything_else": "I want to make the transition cleanly and remain supportive of the mission.",
                    },
                },
            ]
            for row in members:
                response = row["response"]
                await db.reactivation_board_members.update_one(
                    {"member_record_id": row["id"]},
                    {"$setOnInsert": {
                        "member_record_id": row["id"],
                        "user_id": member["user_id"],
                        "name": row["name"],
                        "email": row["email"],
                        "phone": response["phone"],
                        "role": row["role"],
                        "source": "internal_admin_preview",
                        "status": "COMPLETED",
                        "form_token": f"{row['id']}-form",
                        "response": response,
                        "submitted_at": now,
                        "call_notes": (
                            f"PRELOADED TEST CONVERSATION TRANSCRIPT FOR {row['name'].upper()}:\n"
                            f"Rooney: I want us to be clear about what service looks like in the next phase.\n"
                            f"{row['name']}: I want my role to match the time and contribution I can realistically carry.\n"
                            f"Rooney: We reviewed your response, the organization's priorities and the responsibility that would make sense.\n"
                            f"{row['name']}: I understand the options and I want the final role to be specific rather than general.\n"
                            f"Rooney: We agreed to record the conclusion clearly and use it as the authority for the next step."
                        ),
                        "conversation_direction": row["direction"],
                        "conversation_conclusion": recommitment_conclusion(row["name"], row["role"], row["direction"]),
                        "internal_preview": True,
                        "created_at": now,
                    }},
                    upsert=True,
                )
        return session_id

    async def seed_fundraising_preview(member: dict) -> None:
        now = now_iso()
        tag = suffix(member)
        await db.game_profiles.update_one(
            {"user_id": member["user_id"]},
            {"$setOnInsert": {
                "user_id": member["user_id"],
                "organization": {
                    "name": ORG_NAME,
                    "mission": MISSION,
                    "website": "https://example.org/brightpath",
                },
                "goal": {
                    "amount": "500000",
                    "purpose": "Fund program growth, fundraising capacity and employer-partnership expansion.",
                    "deadline": "2027-06-30",
                },
                "primary_user": {
                    "full_name": "Rooney Akpesiri",
                    "email": member["email"],
                    "job_title": "Founder and Executive Director",
                },
                "profile_completed": True,
                "situation_completed": True,
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )
        situation_sections = {
            "current_reality": {
                "current_individual_donors": "We have about 35 recurring or repeat individual donors, mostly personal contacts and former volunteers. There is no formal major-donor pipeline yet.",
                "current_businesses": "We have three small business sponsors and several warm employer relationships, but no structured corporate partnership pipeline.",
                "current_grantors": "About 55% of current revenue comes from foundation and government grants. Grant prospecting is mostly reactive.",
                "current_team": "The founder leads fundraising with support from one part-time coordinator. Board participation is inconsistent and usually request-based.",
                "current_resources": "We have participant stories, basic outcome data, a website, email list and presentation deck, but no unified case for support or prospect CRM.",
            },
            "participation": {
                "build": ["Make introductions", "Research potential funders", "Help build fundraising materials"],
                "build_other": "",
                "raise": ["Join fundraising meetings", "Make direct asks with support", "Help steward relationships"],
                "raise_other": "",
                "time": "2–4 hours per month",
                "anything_else": "I want every board member to leave with a specific fundraising role that fits their relationships and strengths.",
            },
            "team": {
                "who_handles": "Founder coordinates the system; Board Chair supports corporate partnerships; Treasurer tracks fundraising performance; staff maintains CRM follow-up.",
                "board_involvement": "Board members make warm introductions, join selected meetings, help with asks where appropriate and steward relationships they open.",
            },
            "technology": {
                "tools": ["One CRM for prospects and next actions", "Shared fundraising dashboard", "Email platform"],
                "tech_working": "The CRM must be simple enough for staff to update weekly and visible enough for the board to review monthly.",
            },
            "materials": {
                "materials": ["Case for support", "Corporate partnership one-pager", "Impact evidence sheet", "Major donor conversation guide", "Follow-up email templates"],
            },
            "financial": {
                "budget": "Allocate budget for CRM, prospect research, communications support, donor stewardship and selected cultivation events.",
            },
            "reflections": {
                "next_steps": "Set up the system, assign relationship owners, map warm prospects, build the core materials and begin a 90-day cultivation cycle.",
            },
        }
        existing_situation = await db.game_situations.find_one({"user_id": member["user_id"]}, {"_id": 0})
        if not existing_situation:
            await db.game_situations.insert_one({
                "user_id": member["user_id"],
                "sections": situation_sections,
                "current_step": 6,
                "completed": True,
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            })
        primary_id = f"admin-preview-game-primary-{tag}"
        primary_token = f"admin-preview-game-primary-token-{tag}"
        await db.game_board_members.update_one(
            {"member_id": primary_id},
            {"$setOnInsert": {
                "member_id": primary_id,
                "user_id": member["user_id"],
                "token": primary_token,
                "full_name": "Rooney Akpesiri",
                "email": member["email"],
                "board_title": "Founder and Executive Director",
                "is_primary": True,
                "game_version": 3,
                "total_sections": 4,
                "invitation_status": "self",
                "invited_at": "",
                "last_reminder_at": "",
                "removed": False,
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )
        primary_answers = {
            1: (
                "Individuals who care about youth opportunity, workforce mobility and mentoring; local business owners; employers that hire early-career talent; and grant funders focused on education, workforce development and economic mobility.",
                "Prioritize warm prospects whose values, lived experience, customer base, workforce needs or giving priorities directly connect to the young people we serve. Start with people and institutions where a board or staff relationship already exists.",
            ),
            2: (
                "Board and staff networks, employer associations, chambers of commerce, professional groups, alumni networks, community foundations, local business events and funder databases filtered for youth and workforce priorities.",
                "Create a weekly prospecting routine. Each board member maps ten relationships, staff researches aligned grantors and businesses, and every qualified prospect enters one shared pipeline with an owner and next action.",
            ),
            3: (
                "Use credible youth outcomes, employer stories, practical insight about youth employment, small mission-connected events and warm introductions to earn attention before asking for money.",
                "Build a content and engagement rhythm around useful insight, proof of impact and direct relationship-building. Every visibility activity should give the right funder a reason to respond, attend, meet or learn more.",
            ),
            4: (
                "Move each prospect through Know, Like, Trust, Ask, Follow Up and Steward. Record the relationship owner, current stage, next action and planned ask in the CRM.",
                "Run a monthly pipeline review. Warm introductions happen first, cultivation has a clear purpose, asks are specific, follow-up is scheduled before the meeting ends and stewardship begins immediately after a commitment.",
            ),
        }
        for section_id, (first, second) in primary_answers.items():
            await db.game_section_responses.update_one(
                {"board_member_id": primary_id, "section_id": section_id},
                {"$setOnInsert": {
                    "board_member_id": primary_id,
                    "user_id": member["user_id"],
                    "section_id": section_id,
                    "first_response": [first],
                    "first_move_locked": False,
                    "final_response": [],
                    "guided_selections": {},
                    "additional_ideas": {},
                    "stage_responses": {},
                    "preferences": [],
                    "do_not_want": [],
                    "group_game_ideas": [],
                    "extras": {"second_response": second},
                    "fine_tuning": {},
                    "approved_entries": [],
                    "approved_display": "",
                    "completed": False,
                    "internal_preview": True,
                    "created_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )
        board_people = [
            (
                f"admin-preview-game-maya-{tag}",
                f"admin-preview-game-maya-token-{tag}",
                "Maya Thompson",
                f"maya.game-{tag}@nonprofitboardbuilder.internal",
                "Board Chair",
                [
                    "Professionals and business owners who believe in youth opportunity and can make gifts between $1,000 and $25,000.",
                    "Employers that need diverse early-career talent and want visible local community impact.",
                    "Foundations funding youth employment, mentoring, education access and economic mobility.",
                ],
            ),
            (
                f"admin-preview-game-daniel-{tag}",
                f"admin-preview-game-daniel-token-{tag}",
                "Daniel Brooks",
                f"daniel.game-{tag}@nonprofitboardbuilder.internal",
                "Treasurer",
                [
                    "High-capacity individuals connected to board members, alumni and professional networks.",
                    "Financial services, technology and professional-services firms with workforce or community-investment priorities.",
                    "Grantors whose eligible costs include program delivery, evaluation, capacity building and workforce outcomes.",
                ],
            ),
            (
                f"admin-preview-game-aisha-{tag}",
                f"admin-preview-game-aisha-token-{tag}",
                "Aisha Patel",
                f"aisha.game-{tag}@nonprofitboardbuilder.internal",
                "Board Member",
                [
                    "People who respond to credible participant stories, evidence and direct invitations from trusted peers.",
                    "Consumer brands and employers whose audiences overlap with young people and families in our service communities.",
                    "Funders looking for measurable outcomes and strong community voice.",
                ],
            ),
        ]
        section_texts = {
            2: ["Warm board introductions, employer networks, professional associations and local business communities.", "Use a weekly prospect research block and assign every prospect to a relationship owner."],
            3: ["Publish evidence-led stories, useful youth-employment insight and partner outcomes before making most asks.", "Invite qualified prospects into small briefings, site visits and one-to-one conversations."],
            4: ["Use Know, Like, Trust, Ask, Follow Up and Steward as the common relationship process.", "Track next actions and stewardship so no qualified relationship disappears after one conversation."],
        }
        for person_id, token, name, email, title, audience_ideas in board_people:
            await db.game_board_members.update_one(
                {"member_id": person_id},
                {"$setOnInsert": {
                    "member_id": person_id,
                    "user_id": member["user_id"],
                    "token": token,
                    "full_name": name,
                    "email": email,
                    "board_title": title,
                    "participant_role": "board_member",
                    "game_version": 3,
                    "total_sections": 5,
                    "invitation_status": "invited",
                    "invited_at": now,
                    "last_reminder_at": "",
                    "removed": False,
                    "completed_at": now,
                    "internal_preview": True,
                    "created_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )
            for section_id in range(1, 5):
                ideas = audience_ideas if section_id == 1 else section_texts[section_id]
                approved = [{"text": idea, "source": "board_member"} for idea in ideas]
                await db.game_section_responses.update_one(
                    {"board_member_id": person_id, "section_id": section_id},
                    {"$setOnInsert": {
                        "board_member_id": person_id,
                        "user_id": member["user_id"],
                        "section_id": section_id,
                        "first_response": [ideas[0]],
                        "first_move_locked": True,
                        "final_response": ideas,
                        "extras": {"second_response": ideas[-1]},
                        "fine_tuning": {"completed": True},
                        "approved_entries": approved,
                        "approved_display": "\n".join(ideas),
                        "completed": True,
                        "completed_at": now,
                        "internal_preview": True,
                        "created_at": now,
                        "updated_at": now,
                    }},
                    upsert=True,
                )
            await db.game_section_responses.update_one(
                {"board_member_id": person_id, "section_id": 5},
                {"$setOnInsert": {
                    "board_member_id": person_id,
                    "user_id": member["user_id"],
                    "section_id": 5,
                    "first_move_locked": True,
                    "completed": True,
                    "completed_at": now,
                    "extras": {
                        "build": ["Make introductions", "Research potential funders"],
                        "build_other": "",
                        "raise": ["Join fundraising meetings", "Help steward relationships"],
                        "raise_other": "",
                        "time": "2–4 hours per month",
                        "additional_idea": f"{name} wants a named list of prospects and a clear next action before each board meeting.",
                    },
                    "internal_preview": True,
                    "created_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )
        await db.game_nights.update_one(
            {"user_id": member["user_id"]},
            {"$setOnInsert": {
                "user_id": member["user_id"],
                "name": f"{ORG_NAME} Board Fundraising Night",
                "meeting_date": "2026-10-08",
                "start_time": "18:00",
                "timezone": "America/New_York",
                "meeting_format": "online",
                "meeting_link": "https://example.org/admin-preview-fundraising-night",
                "meeting_location": "",
                "note": "Admin preview meeting. Board members should bring their relationship maps.",
                "status": "scheduled",
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )
        await db.game_meeting_transcripts.update_one(
            {"user_id": member["user_id"]},
            {"$setOnInsert": {
                "transcript_id": f"admin-preview-game-transcript-{tag}",
                "user_id": member["user_id"],
                "text": fundraising_meeting_transcript(),
                "source": "pasted",
                "filename": "",
                "internal_preview": True,
                "created_at": now,
                "submitted_at": now,
            }},
            upsert=True,
        )

    @router.post("/{product}")
    async def launch_dashboard_preview(product: str, request: Request, response: Response):
        admin = await authenticate_admin(request, db)
        config = PRODUCTS.get(product)
        if not config:
            raise HTTPException(status_code=404, detail="Unknown product dashboard")
        member = await preview_member(admin)
        if config["entitlements"]:
            await db.members.update_one(
                {"user_id": member["user_id"]},
                {"$addToSet": {"entitlements": {"$each": config["entitlements"]}},
                 "$set": {"updated_at": now_iso()}},
            )
            member = await db.members.find_one({"user_id": member["user_id"]}, {"_id": 0})

        dashboard_url = config["dashboard_path"]
        if product == "recruitment":
            await seed_recruitment_preview(member)
        elif product == "board-fundraising-game":
            await seed_fundraising_preview(member)
        elif product in {"strategic-planning", "board-recommitment"}:
            session_id = await seed_guided_product(member, product, config)
            dashboard_url = f"{dashboard_url}?session_id={session_id}"

        set_member_cookie(response, create_member_token(member["user_id"], member["email"]))
        return {"dashboard_url": dashboard_url, "product": product}

    return router
