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

FIXTURE_VERSION = "v4"
FRESH_TEST_VERSION = "fresh-v1"
RECRUITMENT_FIXTURE_VERSION = "v8"
STRATEGIC_FIXTURE_VERSION = "v7"
RECOMMITMENT_FIXTURE_VERSION = "v9"
FUNDRAISING_FIXTURE_VERSION = "v7"
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
            "The immediate priorities should be revenue diversification, board capacity, program outcome evidence and operating discipline. I would turn those priorities into 90-day actions with named owners, clear resources and a Board review point.",
            "In the first 90 days I would finalize the scorecard, establish the fundraising and partnership pipelines, assign clear owners, and review progress at every Board meeting.",
        ),
    ]
    role_options = {
        "Founder perspective:": (
            "I would participate in the Strategic Execution and Board Development working groups.",
            "I am willing to lead overall strategic execution, staff coordination and Board accountability for the plan.",
            "I am happy to support fundraising strategy, Board recruitment and partnership development where founder leadership is useful.",
        ),
        "Board Chair perspective:": (
            "I would join or help shape a Partnerships and Board Development working group.",
            "I am willing to lead corporate partnerships, employer engagement and Board accountability at Board level.",
            "I am happy to support fundraising strategy, Board recruitment and relationship development.",
        ),
        "Treasurer perspective:": (
            "I would join or help shape a Finance and Resource Development working group.",
            "I am willing to lead Board-level budget oversight, cash visibility and financial performance reporting.",
            "I am happy to support fundraising pipeline reporting, risk review and operational discipline.",
        ),
        "Marketing perspective:": (
            "I would join or help shape a Marketing, Visibility and Partnerships working group.",
            "I am willing to lead Board-level marketing, communications and visibility review.",
            "I am happy to support fundraising messaging, corporate-partner storytelling and digital outreach.",
        ),
    }
    rows.append(role_options.get(lens, (
        "I would like to join a working group connected to the areas where my experience can be useful.",
        "I am willing to lead in an area that matches my experience and that I explicitly agree to take responsibility for.",
        "I am happy to support other strategic areas where my expertise, relationships or perspective can help.",
    )))
    response = {}
    for index, answers in enumerate(rows, 1):
        for question_index, answer in enumerate(answers, 1):
            response[f"s{index}_q{question_index}"] = f"{lens} {answer}"
    return response



def strategic_preview_form_content(answers: dict) -> dict:
    supplied=answers.get("program_details") if isinstance(answers.get("program_details"),list) else []
    programs=[x for x in supplied if isinstance(x,dict) and str(x.get("name","")).strip()]
    if not programs:
        programs=[{"name":x.strip(),"description":"","present_work":""} for x in str(answers.get("programs") or "").split("\n") if x.strip()]
    rows=[
        ("Mission",[
            f"From your view, does our present mission still clearly explain who we serve, how we serve them and the change we are trying to create? What would you keep or change, and why?\n\nPresent mission: {answers.get('mission','')}",
            "What wording, focus or emphasis would make the mission more useful for guiding the organization's decisions over the next few years?",
        ]),
        ("Goals",[
            f"Looking at our present goals for the next 12 to 24 months, which goals feel most important, which should change, and what goal do you believe we are missing?\n\nPresent goals: {answers.get('goals','')}",
            "From what you know about the organization and the people we serve, what do you believe we should realistically be trying to achieve during this planning period?",
        ]),
        ("Objectives",[
            f"Our objectives should help us achieve our goals. Looking at what we presently have, which objectives are useful, which need to change, and what specific objectives should we add?\n\nPresent objectives: {answers.get('objectives','')}",
            "What evidence or result would make you say that these objectives are actually being achieved?",
        ]),
    ]
    for program in programs:
        name=str(program.get("name","")).strip()
        starting=" | ".join(x for x in [str(program.get("description","")).strip(),str(program.get("present_work","")).strip()] if x)
        rows.append((f"Program: {name}",[
            f"Thinking specifically about {name}, what do you believe this program should accomplish for the people it serves? What should we protect, change or improve?\n\nPresent program information: {starting}",
            f"From what you have observed, what would make {name} more effective, useful or sustainable, and what should the organization do differently in delivering it?",
        ]))
    rows.extend([
        ("Team & Capacity",[
            f"Who do we presently have available to help execute this strategy — staff, Board Members, volunteers, contractors or other supporters? Where do you see enough capacity and where are we stretched?\n\nPresent information: {answers.get('team_building','')}",
            "What people, skills or leadership capacity do you believe we need to add or strengthen to execute the strategy successfully?",
        ]),
        ("Marketing & Visibility",[
            f"Who most needs to know about our work, and what do you believe they need to understand about us?\n\nPresent information: {answers.get('marketing','')}",
            "From what you have seen, where should we be more visible and what would help the right people notice, trust and engage with the organization?",
        ]),
        ("Partnerships",[
            f"Which types of organizations, institutions, businesses or community groups could materially strengthen our mission, and what could a useful partnership actually help us accomplish?\n\nPresent information: {answers.get('partnerships','')}",
            "Are there relationships or partnership opportunities you believe we should prioritize because of what you know or have observed?",
        ]),
        ("Fundraising",[
            f"From your perspective, what is working and not working about how we presently raise money?\n\nPresent information: {answers.get('fundraising','')}",
            "Who do you believe is most likely to care about funding this work, where can we reach them, and what should we do to build enough trust to ask for support?",
        ]),
        ("Technology",[
            f"What work do we need technology to make easier, faster or more reliable, and where are our present tools getting in the way?\n\nPresent information: {answers.get('technology','')}",
            "What technology capability do you believe the organization genuinely needs in order to execute this strategy well?",
        ]),
        ("Budget & Resources",[
            f"Looking at the direction we are considering, where do you believe the organization will need to spend, invest or secure additional resources?\n\nPresent information: {answers.get('budget','')}",
            "What budget or resource decisions do you believe the Board needs to understand before committing to the strategy?",
        ]),
        ("Action Planning",[
            f"Based on everything above, what do you believe the organization should do first, next and after that to begin executing this strategy?\n\nPresent actions already planned or underway: {answers.get('action_planning','')}",
            "What practical actions, decisions or resources do you believe are most important in the first 90 days after this Strategic Plan is adopted?",
        ]),
        ("Roles We Will Play",[
            "Which Board committee, working group or recurring area of Board work would you genuinely be interested in joining or helping shape? If no formal committee exists yet, describe the kind of group or area you would be happy to participate in.",
            "Which areas of this Strategic Plan would you personally be willing to LEAD at Board level? Only name areas you would genuinely be comfortable accepting responsibility for.",
            "Which areas would you be happy to SUPPORT without being the lead? Describe the kind of contribution, expertise, relationships or help you would be comfortable providing.",
        ]),
    ])
    sections=[]
    for index,(title,prompts) in enumerate(rows,1):
        sections.append({
            "key":f"s{index}",
            "title":title,
            "questions":[{"id":f"s{index}_q{q_index}","prompt":prompt,"type":"long","options":[],"required":True}
                         for q_index,prompt in enumerate(prompts,1)],
        })
    return {
        "introduction":(
            f"{ORG_NAME} is preparing its next Strategic Plan. We want your own thinking before the Board meets together. "
            "There are no right or wrong answers. Speak from what you have observed, what you know, and what you genuinely believe would help the organization. "
            "Your ideas remain attributable to you during the live Board session so the group can review every contribution together."
        ),
        "sections":sections,
    }

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


def strategic_preview_final_plan() -> str:
    return """STRATEGIC PLAN
BrightPath Youth Alliance

EXECUTIVE SUMMARY
BrightPath Youth Alliance will grow youth reach and outcomes while building the Board, revenue, partnership and operating capacity required to sustain that growth. The next planning period centers on measurable youth outcomes, diversified revenue, stronger employer and corporate partnerships, disciplined visibility and clear execution ownership.

MISSION
BrightPath Youth Alliance helps young people ages 12 to 24 in underserved communities build the skills, relationships and opportunities they need to move into education, employment and stable adulthood.

GOALS
- Serve 1,000 young people during the next 24 months.
- Diversify revenue so growth is not dependent on grants or the founder.
- Build a Board with clear strategic ownership for fundraising, partnerships, visibility and accountability.
- Strengthen evidence of youth outcomes and use it consistently in fundraising, partnerships and Board decision-making.

OBJECTIVES
- Establish one quarterly scorecard covering participant reach, outcomes, unrestricted revenue, corporate partners and Board execution.
- Build three managed fundraising pipelines: individuals, businesses and grant funders.
- Recruit the professional Board capability needed for fundraising, corporate partnerships and marketing.
- Create repeatable 90-day execution cycles with named owners and Board review points.

PROGRAMS

Board Recruitment
Description: Recruit the specific professional capability the organization needs rather than filling seats.
Board-agreed direction: Use a Board skills map, structured application and interview process, explicit contribution expectations and disciplined onboarding.

Board Fundraising Game
Description: Build the fundraising strategy with the Board and translate Board ideas into execution roles.
Board-agreed direction: Use one fundraising planning process to identify audiences, relationship pathways, Board roles, follow-up ownership and required fundraising materials.

Strategic Planning
Description: Turn Board thinking into a concise Strategic Plan and accountable execution.
Board-agreed direction: Every major strategic area must have a clear direction, execution owner, milestones, evidence of progress and a recurring Board review point.

Board Recommitment
Description: Confirm who is prepared to carry responsibility during the next stage of growth.
Board-agreed direction: Use individual recommitment conversations to confirm capacity, contribution area and the right Active, Advisory or Step-Down pathway.

TEAM BUILDING / TEAM STRUCTURE
Clarify which responsibilities belong to staff and which require Board leadership. Rooney remains responsible for overall execution and staff coordination. Maya leads Board-level corporate partnerships. Daniel leads Board-level budget and financial-performance oversight. Aisha leads Board-level marketing and visibility review.

TECHNOLOGY
Use one lightweight CRM for fundraising and partnership prospects, one outcome dashboard and shared project tracking. Add technology only when it simplifies a recurring process the team is committed to maintaining.

MARKETING
Publish evidence-led content consistently. Use youth outcomes, participant stories with consent, useful insight and partner visibility to build trust with funders, employers, families and community partners.

PARTNERSHIPS
Prioritize qualified employers, schools, community organizations and corporate partners that can expand opportunity for young people. Assign a relationship owner and next action to every priority relationship.

FUNDRAISING
Operate three parallel pipelines for individuals, businesses and grants. Track every qualified prospect, relationship owner, stage, next action and ask. Board Members contribute through introductions, cultivation, selected asks and stewardship according to the responsibility they explicitly accept.

BUDGET
Separate the cost of maintaining current delivery from the additional cost of growth. Connect every strategic priority to its actual people, technology, communications and evaluation costs, and review cash visibility quarterly.

ACTION PLANNING
Days 1–30: finalize the scorecard, confirm execution owners, configure the CRM and establish the fundraising and partnership pipelines.
Days 31–60: launch the agreed visibility rhythm, map warm relationships, begin qualified employer/corporate outreach and strengthen outcome evidence.
Days 61–90: move qualified relationships into meetings, proposals and asks; review execution evidence at the Board meeting; repair weak systems and begin the next 90-day cycle.
"""


    

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
        "desired_board_members": (
            "I believe we need one experienced fundraiser who understands major donors and can help the board build an individual-giving system; "
            "one corporate partnerships or business-development leader who can open employer and sponsor relationships; and one senior marketing "
            "and communications leader who can strengthen visibility, fundraising messaging and partner-facing content."
        ),
        "important_areas": (
            "Fundraising strategy, individual giving, corporate partnerships, grant development, marketing and communications, "
            "program evaluation, finance, governance, technology, employer relationships, community engagement and board accountability."
        ),
        "support_needs": (
            "We want the new Board Members to help diversify revenue, open corporate relationships, strengthen fundraising discipline, "
            "improve visibility and help the organization execute a clear growth strategy. They must be willing to carry defined Board-level responsibility."
        ),
        "board_type": "Working Board",
        "why_join": (
            "The right Board Member can directly help expand opportunity for young people, shape the next stage of a growing organization, "
            "use their professional experience on meaningful strategic work, build relationships with other committed leaders and see the results of the role they agreed to carry."
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

    async def preview_member(admin: dict, fixture_version: str = FIXTURE_VERSION) -> dict:
        fingerprint = hashlib.sha256(admin["user_id"].encode("utf-8")).hexdigest()[:16]
        user_id = f"admin-dashboard-preview-{fixture_version}-{fingerprint}"
        email = f"dashboard-preview-{fixture_version}-{fingerprint}@nonprofitboardbuilder.internal"
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
                    "admin_preview_fixture_version": fixture_version,
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
        tag = f"{RECRUITMENT_FIXTURE_VERSION}-{suffix(member)}"
        token = f"admin-preview-recruitment-{tag}"
        lead_id = f"admin-preview-recruitment-lead-{tag}"
        answers = recruitment_answers()
        recommended_roles = [
            {
                "role_name": "Board Member — Fundraising and Major Gifts",
                "why_this_person_is_important": "BrightPath needs Board-level fundraising experience to reduce dependence on grants and the founder, build a disciplined individual-giving pipeline and help the full Board participate confidently in fundraising.",
                "how_this_person_can_support": "Shape major-donor strategy, help identify and cultivate qualified donors, coach Board Members on introductions and asks, strengthen stewardship and review fundraising pipeline progress at Board level.",
            },
            {
                "role_name": "Board Member — Corporate Partnerships",
                "why_this_person_is_important": "Employer and corporate relationships are central to BrightPath's youth-employment mission and growth plan, but the current Board lacks someone who has built strategic business partnerships at scale.",
                "how_this_person_can_support": "Open employer and sponsor relationships, help define the corporate partnership proposition, join priority meetings, advise on partnership pipelines and help convert warm relationships into sustained organizational support.",
            },
            {
                "role_name": "Board Member — Marketing and Communications",
                "why_this_person_is_important": "BrightPath needs stronger visibility and clearer evidence-led messaging so funders, employers, families and community partners understand the value of the mission and can see credible results.",
                "how_this_person_can_support": "Guide Board-level communications strategy, sharpen fundraising and partnership messaging, help turn outcomes into credible stories, strengthen digital visibility and review campaign performance.",
            },
        ]
        assessment_result = {
            "summary": "BrightPath should recruit three Board Members whose professional capability directly closes its fundraising, corporate partnership and marketing gaps.",
            "priority_roles": recommended_roles,
        }

        async def seed_material(material_type: str, title: str, structured: dict, display_text: str, application_id: str = "", status: str = "Approved"):
            material_id = f"admin-preview-recruitment-{material_type}-{application_id or 'org'}-{tag}"
            version = {
                "version": 1, "structured": structured, "display_text": display_text,
                "source": "admin_preview_fixture", "input_context_summary": "Preloaded Admin Preview fixture", "created_at": now,
            }
            await db.generated_materials.update_one(
                {"user_id": member["user_id"], "type": material_type, "application_id": application_id},
                {"$set": {
                    "material_id": material_id, "user_id": member["user_id"], "type": material_type,
                    "application_id": application_id, "module": 1, "title": title,
                    "versions": [version], "current_version": 1, "status": status,
                    "approved_at": now if status == "Approved" else "", "internal_preview": True,
                    "created_at": now, "updated_at": now,
                }},
                upsert=True,
            )
            return material_id

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
                    "question_5_completed": True,
                    "question_6_completed": True,
                    "result_generated": True,
                    "generation_status": "ready",
                    "video_page_viewed": True,
                    "checkout_started": True,
                    "paid": True,
                    "welcome_completed": True,
                    "intake_completed": True,
                    "dashboard_entered": True,
                },
                "result": assessment_result,
                "result_generated_at": now,
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
                    "desired_board_members": answers["desired_board_members"],
                    "accomplish": answers["support_needs"],
                    "board_type": answers["board_type"],
                    "why_join": answers["why_join"],
                    "new_members_needed": "3",
                },
                "free_assessment_result": assessment_result,
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
                    "desired_board_skills": [row["role_name"] for row in recommended_roles],
                    "priorities": answers["support_needs"],
                    "important_areas": answers["important_areas"],
                    "desired_board_members_founder_view": answers["desired_board_members"],
                    "board_kind": answers["board_type"],
                    "why_join_board": answers["why_join"],
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
                "confirmed": True,
                "recruitment_profile_confirmed": True,
                "confirmed_at": now,
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
                "status": "Published",
                "custom_questions": [],
                "application_saved": True,
                "email_content": {"subject": "Join the Board of BrightPath Youth Alliance", "body": "We are recruiting three Board Members with fundraising, corporate partnership and marketing experience."},
                "broadcast_initiated": True,
                "broadcast_id": f"admin-preview-broadcast-{tag}",
                "broadcast_status": "Sent",
                "broadcast_mode": "test",
                "published_at": now,
                "internal_preview": True,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )

        await seed_material(
            "powerhouse_board_blueprint",
            "The Board Members Your Organization Needs",
            assessment_result,
            "THE BOARD MEMBERS YOUR ORGANIZATION NEEDS\n\n" + "\n\n".join(
                f"{i+1}. {role['role_name']}\nWhy this person matters: {role['why_this_person_is_important']}\nRole they can play: {role['how_this_person_can_support']}"
                for i, role in enumerate(recommended_roles)
            ),
        )
        await seed_material(
            "board_recruitment_job_post",
            "Recruitment Job Post",
            {"headline": "Join the Board of BrightPath Youth Alliance", "roles": [r["role_name"] for r in recommended_roles]},
            "JOIN THE BOARD OF BRIGHTPATH YOUTH ALLIANCE\n\nBrightPath is recruiting three Board Members with fundraising, corporate partnership and marketing/communications experience. Board Members will carry clear strategic responsibility and help expand opportunity for young people ages 12 to 24.",
        )
        await seed_material(
            "recruitment_emails",
            "Recruitment Email",
            {"subject": "Help us find three strategic Board Members"},
            "Subject: Help us find three strategic Board Members\n\nBrightPath Youth Alliance is recruiting experienced leaders in fundraising, corporate partnerships and marketing/communications. Please share this opportunity with people who care about youth opportunity and are ready to carry real Board-level responsibility.",
        )
        await seed_material(
            "social_posts",
            "Social Media Recruitment Post",
            {"post": "BrightPath Youth Alliance is recruiting three strategic Board Members."},
            "BrightPath Youth Alliance is recruiting three Board Members who can help us strengthen fundraising, corporate partnerships and marketing. We are looking for people who want to do meaningful strategic work, not simply add a Board title to their résumé.",
        )
        await seed_material(
            "referral_request_email",
            "Referral Email",
            {"subject": "Who should we invite to consider our Board?"},
            "Subject: Who should we invite to consider our Board?\n\nWe are looking for experienced fundraising, corporate partnership and marketing leaders who care about youth opportunity. If someone comes to mind, please introduce us or forward our Board opportunity.",
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
                    "Previous volunteer development-committee experience with a youth mentoring nonprofit. "
                    "PROFESSIONAL REFERENCES: Elena Foster, Senior Vice President, Fictional Growth Partners, former supervisor, "
                    "elena.foster.preview@nonprofitboardbuilder.internal, +1 555 010 5101. "
                    "David Okoro, Executive Director, Fictional Youth Mentoring Collaborative, nonprofit partner, "
                    "david.okoro.preview@nonprofitboardbuilder.internal, +1 555 010 5102."
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


        # Preload the organization-level onboarding library so the later dashboard stages
        # are immediately inspectable instead of waiting for generation.
        org_materials = [
            ("organization_overview", "Organization Overview",
             f"{ORG_NAME}\n\nMISSION\n{MISSION}\n\nWHO WE SERVE\nYoung people ages 12 to 24 in underserved communities.\n\nCURRENT PRIORITIES\nDiversify revenue, expand employer partnerships, strengthen Board capacity and improve outcome evidence."),
            ("board_manual", "Board Manual",
             f"BOARD MANUAL\n{ORG_NAME}\n\nOUR MISSION\n{MISSION}\n\nHOW THE BOARD WORKS\nThe Board governs, provides strategic leadership, protects the mission, supports resource development and holds the organization accountable without replacing staff.\n\nBOARD MEMBER COMMITMENT\nAttend meetings, prepare, carry agreed responsibilities, disclose conflicts, protect confidential information and communicate early when support is needed.\n\nORGANIZATION COMMITMENT TO BOARD MEMBERS\nProvide timely information, clear decisions, useful materials, staff access and realistic expectations."),
            ("board_member_agreement", "Board Member Agreement",
             "BOARD MEMBER AGREEMENT\n\nI agree to prepare for and attend Board meetings, act in the best interests of BrightPath Youth Alliance, carry the responsibilities I explicitly accept, support fundraising appropriately, maintain confidentiality and disclose conflicts of interest."),
            ("confidentiality_agreement", "Confidentiality Agreement",
             "CONFIDENTIALITY AGREEMENT\n\nBoard Members protect non-public information concerning participants, applicants, donors, partners, staff, finances and Board discussions and use that information only for authorized organizational purposes."),
            ("conflict_of_interest_agreement", "Conflict of Interest Agreement",
             "CONFLICT OF INTEREST AGREEMENT\n\nBoard Members disclose actual or potential conflicts promptly, do not use their Board position for improper private benefit and follow the organization's process for recusal and documentation."),
            ("onboarding_agenda", "Board Member Onboarding Agenda",
             "BOARD MEMBER ONBOARDING AGENDA\n\n1. Welcome and introductions\n2. Mission, programs and current priorities\n3. The role of the Board and the role of staff\n4. Documents, governance and agreements\n5. Each person's Board role and contribution focus\n6. First 90 days and immediate next action\n7. Questions and close"),
            ("onboarding_script", "Board Member Onboarding Facilitation Guide",
             f"BOARD MEMBER ONBOARDING FACILITATION GUIDE\n{ORG_NAME}\n\nWELCOME\nThank everyone for choosing to serve. Explain that onboarding is designed to make roles clear before execution begins.\n\nMISSION AND ORGANIZATION\nRead and discuss the mission: {MISSION}\n\nROLE OF THE BOARD\nClarify governance, strategic leadership, fundraising participation and accountability.\n\nROLE AGREEMENT\nConfirm each person's specific contribution focus, support needed and first action.\n\nCLOSE\nRead back agreed responsibilities, answer questions and explain how Portfolios and ongoing execution support will work."),
        ]
        for material_type, title, display_text in org_materials:
            await seed_material(material_type, title, {"preview": True}, display_text)

        jordan_id = f"admin-preview-applicant-jordan-{tag}"
        # Jordan remains the early-stage candidate so the Applicants area still has a realistic person to move manually.
        await seed_material(
            "interview_invitation", "Interview Invitation — Jordan Ellis",
            {"subject": f"Board Interview | {ORG_NAME}"},
            f"Dear Jordan,\n\nThank you for applying to join the Board of {ORG_NAME}. We would like to invite you to a Board candidate interview to explore your corporate-partnership experience, your interest in the mission and the responsibility you would be comfortable carrying.\n\nWe will coordinate the interview time directly.",
            application_id=jordan_id,
        )

        for candidate_id, candidate_name, focus in [
            (priya_id, "Priya Mensah", "Fundraising and Major Gifts"),
            (marcus_id, "Marcus Chen", "Marketing and Communications"),
        ]:
            await seed_material(
                "interview_invitation", f"Interview Invitation — {candidate_name}",
                {"subject": f"Board Interview | {ORG_NAME}"},
                f"Dear {candidate_name.split()[0]},\n\nThank you for your interest in joining the Board of {ORG_NAME}. We would like to invite you to a candidate interview focused on the {focus} role and the contribution you would be prepared to make.",
                application_id=candidate_id,
            )
            guide_id = await seed_material(
                "interview_guide", f"Tailored Interview Guide — {candidate_name}",
                {"candidate": candidate_name, "role": focus},
                f"TAILORED BOARD CANDIDATE INTERVIEW GUIDE\n\nCandidate: {candidate_name}\nRole being considered: Board Member — {focus}\n\n1. What connects you personally to BrightPath's mission?\n2. Based on your experience, what would you want to understand before accepting responsibility for {focus}?\n3. Tell us about a situation where you used your professional experience to help an organization move a strategic priority forward.\n4. Which fundraising or Board activities would you genuinely be willing to carry?\n5. What time can you realistically commit each month?\n6. What support would help you follow through?\n\nINTERVIEWER NOTE\nCompare the candidate's answers with the approved Board profile. Do not infer willingness from expertise alone.",
                application_id=candidate_id,
            )
            await db.opportunity_applications.update_one(
                {"application_id": candidate_id},
                {"$set": {"interview_guide": {"status": "Ready", "material_id": guide_id, "generated_at": now}, "updated_at": now}},
            )

        await seed_material(
            "conditional_offer", "Conditional Board Appointment Email — Priya Mensah",
            {"subject": f"Conditional Board Appointment | {ORG_NAME}"},
            "Dear Priya,\n\nWe would like to offer you a Board position focused on Fundraising and Major Gifts, conditional on completion of the remaining reference/background-check process. Your onboarding session is scheduled for October 8, 2026 at 6:00 PM Eastern Time.",
            application_id=priya_id,
        )

        # Marcus is the fully completed candidate used to test final appointment, Portfolio and post-onboarding execution.
        await db.opportunity_applications.update_one(
            {"application_id": marcus_id},
            {"$set": {
                "status": "Selected",
                "final_outcome": "Joined Board",
                "board_role_recommendation": {
                    "recommended_role": "Board Member — Marketing and Communications",
                    "why_this_role_fits": "Marcus's senior marketing, brand and executive-communications experience directly matches the approved Board gap and the contribution discussed through recruitment and onboarding.",
                },
                "board_role": "Board Member — Marketing and Communications",
                "portfolio_role_rationale": "Marcus will provide Board-level leadership for visibility, fundraising messaging and partner storytelling without becoming operational staff.",
                "portfolio_role_approved": True,
                "portfolio_role_approved_at": now,
                "onboarding_conclusion.saved_at": now,
                "updated_at": now,
            }},
        )
        for material_type, title, display_text in [
            ("unconditional_offer", "Unconditional Board Appointment Offer Email",
             "Dear Marcus,\n\nWe are pleased to offer you a position on the Board of BrightPath Youth Alliance as Board Member — Marketing and Communications. Your onboarding session is scheduled for October 8, 2026 at 6:00 PM Eastern Time."),
            ("onboarding_email", "Board Member Onboarding Email",
             "Dear Marcus,\n\nWelcome to the Board of BrightPath Youth Alliance. Before our onboarding session, please review the Organization Overview, Board Manual and agreements. During the session we will confirm how your marketing and communications experience will be used and your first 90-day priorities."),
            ("formal_appointment_letter", "Formal Board Appointment Letter",
             "FORMAL BOARD APPOINTMENT\n\nBrightPath Youth Alliance confirms the appointment of Marcus Chen as Board Member — Marketing and Communications. The appointment follows completion of the recruitment, reference, onboarding and role-confirmation process."),
            ("formal_appointment_email", "Final Board Appointment Email",
             "Dear Marcus,\n\nYour appointment to the Board of BrightPath Youth Alliance is confirmed. Thank you for accepting the Board Member — Marketing and Communications role. Your Portfolio summarizes the responsibility agreed during onboarding."),
            ("board_member_portfolio", "Board Member Portfolio — Marcus Chen",
             f"BOARD MEMBER PORTFOLIO\nMarcus Chen\n{ORG_NAME}\n\nYOUR BOARD ROLE\nBoard Member — Marketing and Communications\n\nWHY YOUR ROLE MATTERS\nBrightPath needs Board-level leadership that can turn program evidence into credible visibility, fundraising messaging and partner communication.\n\nYOUR RESPONSIBILITIES\n- Lead quarterly Board review of visibility, messaging and campaign performance.\n- Help strengthen the case for support and partner-facing content.\n- Identify and support two partner-story opportunities in the first 90 days.\n\nHOW THE ORGANIZATION WILL SUPPORT YOU\nProvide timely impact data, participant stories with consent, campaign priorities and a clear staff contact.\n\nFIRST 90 DAYS\nReview the existing case for support, propose the first 90-day communications priorities and identify the first two partner stories."),
            ("portfolio_email", "Portfolio Email — Marcus Chen",
             "Subject: Your Board Member Portfolio | BrightPath Youth Alliance\n\nDear Marcus,\n\nYour Board Member Portfolio is ready. It captures the Board role and responsibilities we confirmed through recruitment and onboarding. Please review it and keep it as the working reference for the contribution you agreed to carry."),
        ]:
            await seed_material(material_type, title, {"candidate": "Marcus Chen"}, display_text, application_id=marcus_id)

    async def seed_guided_product(member: dict, product: str, config: dict) -> str:
        now = now_iso()
        fixture_version = (
            STRATEGIC_FIXTURE_VERSION if product == "strategic-planning"
            else RECOMMITMENT_FIXTURE_VERSION if product == "board-recommitment"
            else FIXTURE_VERSION
        )
        identity_suffix = (
            hashlib.sha256(member["user_id"].encode("utf-8")).hexdigest()[:16]
            if product == "board-recommitment"
            else suffix(member)
        )
        tag = f"{fixture_version}-{identity_suffix}"
        session_id = f"admin_preview_{product.replace('-', '_')}_{tag}"
        lead_token = f"admin-preview-{product}-{tag}"
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
                "program_details": [
                    {"name":"Board Recruitment","description":"Recruit the exact Board capability the organization needs.","present_work":"We currently recruit mainly through referrals and are moving to a skills-based recruitment process."},
                    {"name":"Board Fundraising Game","description":"Build the fundraising strategy with the Board.","present_work":"We are using the Game to move Board fundraising from occasional requests to a shared system."},
                    {"name":"Strategic Planning","description":"Create and execute one Board-owned Strategic Plan.","present_work":"We are replacing document-only planning with Board discussion, decisions, roles and 90-day execution cycles."},
                    {"name":"Board Recommitment","description":"Clarify who is prepared to carry responsibility in the next phase.","present_work":"We are moving from general Board membership to explicit recommitment and defined roles."},
                ],
                "team_building": "Strengthen staff leadership and give board members defined strategic ownership instead of general volunteer tasks.",
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
                    "logo_data_url": PREVIEW_LOGO_DATA,
                    "organization_details_saved_at": now,
                    "planning_meeting": {
                        "meeting_date": "2026-10-15",
                        "start_time": "18:00",
                        "timezone_name": "America/New_York",
                        "saved_at": now,
                    },
                    "status": "Active",
                    "generic_form_token": f"admin-preview-sp-form-{tag}",
                    "internal_preview": True,
                    "created_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )
            preview_form = strategic_preview_form_content(answers)
            await db.sp_forms.update_one(
                {"project_id": project_id},
                {"$setOnInsert": {
                    "form_id": f"admin-preview-sp-form-record-{tag}",
                    "project_id": project_id,
                    "status": "Approved",
                    "content": preview_form,
                    "approved_version": 1,
                    "approved_at": now,
                    "internal_preview": True,
                    "created_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )
            response_questions = [
                {"id": question["id"], "prompt": question["prompt"], "section": section["title"]}
                for section in preview_form["sections"]
                for question in section["questions"]
            ]
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
                is_lead = role == "Lead User"
                participant_doc = {
                    "participant_id": participant_id,
                    "project_id": project_id,
                    "name": name,
                    "email": email,
                    "role": role,
                    "expertise": expertise,
                    "status": "COMPLETED",
                    "form_token": f"{participant_id}-form",
                    "form_version": 1,
                    "review_status": "NOT SENT",
                    "review_token": f"{participant_id}-review",
                    "response": strategic_response(lens),
                    "response_questions": response_questions,
                    "internal_preview": True,
                    "created_at": now,
                }
                participant_doc["submitted_at"] = now
                await db.sp_participants.update_one(
                    {"participant_id": participant_id},
                    {"$setOnInsert": participant_doc},
                    upsert=True,
                )
            await db.sp_sessions.update_one(
                {"project_id": project_id},
                {"$setOnInsert": {
                    "project_id": project_id,
                    "decisions": {"preview": "Board decisions are represented in the preloaded final plan and transcript."},
                    "transcript": strategic_transcript(),
                    "status": "COMPLETED",
                    "current_section_index": 99,
                    "completed_at": now,
                    "internal_preview": True,
                    "created_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )
            final_plan_text = strategic_preview_final_plan()
            delegates = [
                {
                    "delegation_id": f"admin-preview-sp-delegate-rooney-{tag}",
                    "participant_id": f"admin-preview-sp-lead-{tag}",
                    "name": "Rooney Akpesiri", "email": member["email"], "role": "Founder and Executive Director — Strategic Execution Lead",
                    "responsibilities": ["Coordinate overall Strategic Plan execution", "Keep staff work aligned to Board-adopted priorities", "Bring progress, barriers and decisions to the Board"],
                    "areas": ["Strategic execution", "Board accountability"], "first_action": "Publish the first 90-day execution scorecard.",
                    "support_needed": "Timely Board decisions and clear staff ownership.", "reporting_rhythm": "Progress review at every Board meeting",
                    "source": "Explicit Strategic Planning Session agreement",
                },
                {
                    "delegation_id": f"admin-preview-sp-delegate-maya-{tag}",
                    "participant_id": f"admin-preview-sp-maya-{tag}",
                    "name": "Maya Thompson", "email": f"maya.thompson-{tag}@nonprofitboardbuilder.internal", "role": "Board Partnerships Lead",
                    "responsibilities": ["Lead Board-level corporate partnership development", "Open qualified employer relationships", "Review partnership pipeline progress"],
                    "areas": ["Partnerships", "Fundraising"], "first_action": "Identify the first 20 qualified employer and corporate prospects.",
                    "support_needed": "Corporate proposition, impact evidence and staff follow-up.", "reporting_rhythm": "Monthly pipeline review",
                    "source": "Explicit Strategic Planning Session agreement",
                },
                {
                    "delegation_id": f"admin-preview-sp-delegate-daniel-{tag}",
                    "participant_id": f"admin-preview-sp-daniel-{tag}",
                    "name": "Daniel Brooks", "email": f"daniel.brooks-{tag}@nonprofitboardbuilder.internal", "role": "Treasurer — Finance and Performance Lead",
                    "responsibilities": ["Lead Board-level budget oversight", "Create quarterly cash visibility", "Review fundraising and strategic scorecard performance"],
                    "areas": ["Budget", "Fundraising"], "first_action": "Separate the base budget from the growth budget and add a quarterly cash forecast.",
                    "support_needed": "Current finance data and fundraising pipeline reporting.", "reporting_rhythm": "Quarterly finance review plus monthly fundraising dashboard",
                    "source": "Explicit Strategic Planning Session agreement",
                },
                {
                    "delegation_id": f"admin-preview-sp-delegate-aisha-{tag}",
                    "participant_id": f"admin-preview-sp-aisha-{tag}",
                    "name": "Aisha Patel", "email": f"aisha.patel-{tag}@nonprofitboardbuilder.internal", "role": "Board Marketing and Visibility Lead",
                    "responsibilities": ["Lead Board-level marketing and visibility review", "Strengthen fundraising and partner-facing messaging", "Review evidence-led content performance"],
                    "areas": ["Marketing", "Partnerships"], "first_action": "Create the first 90-day evidence-led content rhythm.",
                    "support_needed": "Outcome data, participant stories with consent and partner examples.", "reporting_rhythm": "Quarterly Board visibility review",
                    "source": "Explicit Strategic Planning Session agreement",
                },
            ]
            portfolios = []
            for delegate in delegates:
                token_value = f"admin-preview-sp-portfolio-{delegate['participant_id']}-{tag}"
                text_value = (
                    f"BOARD MEMBER LEADERSHIP PORTFOLIO\n{delegate['name']}\n{ORG_NAME}\n\n"
                    f"YOUR CONFIRMED ROLE\n{delegate['role']}\n\nYOUR RESPONSIBILITIES\n- " + "\n- ".join(delegate["responsibilities"]) +
                    f"\n\nYOUR FIRST ACTION\n{delegate['first_action']}\n\nREPORTING RHYTHM\n{delegate['reporting_rhythm']}\n\n"
                    "Your Executive Assistant uses the adopted Strategic Plan and this confirmed Portfolio as its authority."
                )
                portfolios.append({
                    "delegation_id": delegate["delegation_id"], "participant_id": delegate["participant_id"],
                    "name": delegate["name"], "email": delegate["email"], "role": delegate["role"],
                    "areas": delegate["areas"], "responsibilities": delegate["responsibilities"], "text": text_value,
                    "token": token_value, "url": f"/strategic-leadership-portfolio/{token_value}",
                    "assistant_access_started_at": now, "assistant_access_included_until": "2027-03-31", "sent_at": now,
                })
            await db.sp_plans.update_one(
                {"project_id": project_id},
                {"$set": {
                    "project_id": project_id,
                    "status": "PLAN READY",
                    "display_text": final_plan_text,
                    "share_token": f"admin-preview-sp-review-{tag}",
                    "areas": [],
                    "meeting_status": "Approved",
                    "meeting_guide_text": (
                        f"STRATEGIC PLANNING SESSION FACILITATION GUIDE\n{ORG_NAME}\n\n"
                        "Move through Mission, Goals, Objectives, each Program, Team, Technology, Marketing, Partnerships, Fundraising, Budget, Action Planning and Roles. "
                        "Show the organization's present information first, then the attributed Board ideas. Ask the Board what should be kept, changed or added. "
                        "For Mission, explicitly offer the option to leave the Mission Statement unchanged. Confirm roles aloud before ending the session."
                    ),
                    "meeting_transcript": strategic_transcript(),
                    "final_status": "Approved",
                    "final_display_text": final_plan_text,
                    "final_share_token": f"admin-preview-sp-final-{tag}",
                    "final_approved_at": now,
                    "active_delegation": {"delegates": delegates, "assignments": {d["participant_id"]: "\n".join(d["responsibilities"]) for d in delegates}, "transcript": strategic_transcript(), "manual_assignments_authoritative": True, "saved_at": now},
                    "leadership_portfolios": portfolios,
                    "internal_preview": True,
                    "created_at": now,
                    "updated_at": now,
                }},
                upsert=True,
            )

        elif product == "board-recommitment":
            await db.board_reactivation_intakes.update_one(
                {"guided_session_id": session_id},
                {"$set": {
                    "user_id": member["user_id"],
                    "session_id": session_id,
                    "organization_name": ORG_NAME,
                    "founder_title": "Founder and Executive Director",
                    "phone": "+44 7700 900123",
                    "logo_data_url": PREVIEW_LOGO_DATA,
                    "mission": MISSION,
                    "organization_goals": GOALS,
                    "why_recommit": "BrightPath is entering a growth phase and needs every continuing Board Member to move from general support into a clear, realistic responsibility the organization can rely on.",
                    "board_help_accomplish": "Diversify revenue, build corporate partnerships, strengthen visibility and financial oversight, improve outcome measurement and hold the Strategic Plan accountable.",
                    "need_by": "2026-11-01",
                    "direction_12_24": "Grow program reach, diversify revenue and build a board that carries strategic leadership responsibility.",
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
                    "updated_at": now,
                }, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            recommitment_yes = "I am ready to recommit, remain an active Board Member and step up in my role."
            recommitment_advisory = "I would like to transition into an Advisory Board role."
            recommitment_no = "I would like to step down from the Board."
            members = [
                {
                    "id": f"admin-preview-recommit-maya-{tag}",
                    "name": "Maya Thompson",
                    "email": f"maya.recommit-{tag}@nonprofitboardbuilder.internal",
                    "role": "Board Chair",
                    "form_variant": "active_advisory",
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
                    "form_variant": "active_advisory",
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
                    "form_variant": "full",
                    "direction": "Move to Advisory Board",
                    "response": {
                        "full_name": "Aisha Patel",
                        "email": f"aisha.recommit-{tag}@nonprofitboardbuilder.internal",
                        "phone": "+1 555 010 3103",
                        "recommitment": recommitment_advisory,
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
                    "form_variant": "full",
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
                if row["direction"] == "Move to Advisory Board":
                    final_outcome = "Transitioning to an Advisory Role"
                    confirmed_role = "Advisory Board Member — Marketing and Communications"
                elif row["direction"] == "Step Down":
                    final_outcome = "Stepping Down From the Board"
                    confirmed_role = ""
                else:
                    final_outcome = "Continuing as an Active Board Member"
                    confirmed_role = (
                        "Board Chair — Corporate Partnerships and Board Accountability"
                        if row["name"] == "Maya Thompson"
                        else "Treasurer — Finance and Fundraising Performance"
                    )
                await db.reactivation_board_members.update_one(
                    {"member_record_id": row["id"]},
                    {"$set": {
                        "member_record_id": row["id"],
                        "user_id": member["user_id"],
                        "name": row["name"],
                        "email": row["email"],
                        "phone": response["phone"],
                        "role": row["role"],
                        "source": "internal_admin_preview",
                        "status": "COMPLETED",
                        "form_variant": row.get("form_variant", "full"),
                        "form_token": f"{row['id']}-form",
                        "last_sent_at": now,
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
                        "direction_source": "form_response",
                        "conversation_conclusion": recommitment_conclusion(row["name"], row["role"], row["direction"]),
                        "conversation_outcome": final_outcome,
                        "outcome_saved_at": now,
                        "confirmed_role": confirmed_role,
                        "confirmed_role_at": now if confirmed_role else "",
                        "internal_preview": True,
                        "updated_at": now,
                    }, "$setOnInsert": {"created_at": now}},
                    upsert=True,
                )
            form_token = f"admin-preview-recommitment-form-{tag}"
            await db.reactivation_forms.update_one(
                {"user_id": member["user_id"]},
                {"$set": {
                    "user_id": member["user_id"], "status": "Approved", "generic_token": form_token,
                    "intro_text": (
                        f"{ORG_NAME} is asking every Board Member to make a clear decision about how they will serve in the next phase. "
                        f"Our mission is: {MISSION}\n\nWhy recommitment matters: BrightPath is entering a growth phase and needs continuing Board Members to carry clear responsibilities. "
                        "We need the Board to help diversify revenue, build partnerships, strengthen visibility, improve financial oversight and hold the Strategic Plan accountable. "
                        "We need the renewed commitment in place by November 1, 2026."
                    ),
                    "approved_at": now, "updated_at": now, "created_at": now, "internal_preview": True,
                }},
                upsert=True,
            )
            for variant, label in [
                ("active_advisory", "Active Board / Advisory Board"),
                ("full", "Full Recommitment / Transition"),
            ]:
                await db.reactivation_email_drafts.update_one(
                    {"user_id": member["user_id"], "variant": variant},
                    {"$set": {
                        "user_id": member["user_id"], "variant": variant, "status": "Approved",
                        "subject": f"Your Board Recommitment | {ORG_NAME}",
                        "body": (
                            f"Dear Board Member,\n\n{ORG_NAME} is preparing for its next phase and we are asking every Board Member to make a clear decision about how they will serve. "
                            f"Please complete the {label} form before November 1, 2026. Your response will help us prepare for a one-on-one conversation about the role that is realistic and useful for you.\n\n"
                            "Thank you for the time, experience and relationships you have already contributed."
                        ),
                        "approved_at": now, "created_at": now, "updated_at": now, "internal_preview": True,
                    }},
                    upsert=True,
                )

            for row in members:
                response = row["response"]
                member_id = row["id"]
                analysis_text = (
                    f"RECOMMITMENT RESPONSE INTERPRETATION — {row['name']}\n\n"
                    f"Chosen path: {response['recommitment']}\n"
                    f"Realistic availability: {response.get('monthly_availability') or 'Not stated'}\n"
                    f"Contribution / ownership: {response.get('ownership_area') or response.get('decision_reason') or 'Discuss in the conversation'}\n\n"
                    f"Conversation direction: {row['direction']}. The founder should use the one-on-one conversation to confirm the actual agreement rather than treating the form as the final contract."
                )
                for material_type, title, display_text in [
                    ("reactivation_response_analysis", "Recommitment Response Interpretation", analysis_text),
                    ("reactivation_conversation_script", "One-on-One Recommitment Conversation Script",
                     f"ONE-ON-ONE CONVERSATION WITH {row['name'].upper()}\n\nOpen by thanking them for their service. Confirm their submitted choice. Discuss what is realistic now, the exact responsibility or transition, support needed, timing and next steps.\n\nPRELOADED CONVERSATION RECORD\n{recommitment_conclusion(row['name'], row['role'], row['direction'])}"),
                ]:
                    material_id = f"admin-preview-{material_type}-{member_id}-{tag}"
                    await db.generated_materials.update_one(
                        {"user_id": member["user_id"], "type": material_type, "application_id": member_id},
                        {"$set": {
                            "material_id": material_id, "user_id": member["user_id"], "type": material_type,
                            "application_id": member_id, "module": 1, "title": title, "status": "Approved",
                            "versions": [{"version":1,"structured":{},"display_text":display_text,"source":"admin_preview_fixture","created_at":now}],
                            "current_version": 1, "approved_at": now, "created_at": now, "updated_at": now, "internal_preview": True,
                        }},
                        upsert=True,
                    )

                if row["direction"] != "Step Down":
                    portfolio_type = "Advisory Board Member Portfolio" if row["direction"] == "Move to Advisory Board" else "Board Member Portfolio"
                    role_text = (
                        "Advisory Board Member — Marketing and Communications"
                        if row["direction"] == "Move to Advisory Board"
                        else ("Board Chair — Corporate Partnerships and Board Accountability" if row["name"] == "Maya Thompson" else "Treasurer — Finance and Fundraising Performance")
                    )
                    portfolio_text = (
                        f"{portfolio_type.upper()}\n\n{row['name']}\n\nYOUR ROLE ON THE BOARD\n{role_text}\n\n"
                        f"WHY YOUR ROLE MATTERS\nThis role connects {row['name']}'s actual experience and realistic availability to a responsibility BrightPath needs in its next phase.\n\n"
                        "WHAT YOU WILL HELP US ACCOMPLISH\n- Strengthen execution of the Strategic Plan\n- Carry the responsibility confirmed in the one-on-one conversation\n- Report progress and barriers at the agreed rhythm\n\n"
                        f"HOW WE WILL WORK TOGETHER\n{recommitment_conclusion(row['name'], row['role'], row['direction'])}\n\n"
                        "YOUR FIRST 90 DAYS\n- Confirm the first action\n- Complete the first agreed piece of work\n- Bring progress, evidence and barriers to the Board or founder\n\n"
                        "Your Executive Assistant uses this approved Portfolio and the actual conversation agreement as its authority."
                    )
                    portfolio_id = f"admin-preview-reactivation-portfolio-{member_id}-{tag}"
                    await db.generated_materials.update_one(
                        {"user_id": member["user_id"], "type": "reactivation_board_member_portfolio", "application_id": member_id},
                        {"$set": {
                            "material_id": portfolio_id, "user_id": member["user_id"], "type": "reactivation_board_member_portfolio",
                            "application_id": member_id, "module": 5, "title": portfolio_type, "status": "Approved",
                            "versions": [{"version":1,"structured":{"member":row["name"],"portfolio_type":portfolio_type},"display_text":portfolio_text,"source":"admin_preview_fixture","created_at":now}],
                            "current_version":1,"share_token":f"admin-preview-reactivation-portfolio-token-{member_id}-{tag}",
                            "approved_at":now,"sent_at":now,"sent_to":row["email"],"sent_version":1,
                            "created_at":now,"updated_at":now,"internal_preview":True,
                        }},
                        upsert=True,
                    )
                else:
                    material_id = f"admin-preview-reactivation-departure-{member_id}-{tag}"
                    await db.generated_materials.update_one(
                        {"user_id": member["user_id"], "type": "reactivation_stepped_down_followup", "application_id": member_id},
                        {"$set": {
                            "material_id":material_id,"user_id":member["user_id"],"type":"reactivation_stepped_down_followup",
                            "application_id":member_id,"module":5,"title":"Board Departure Email","status":"Approved",
                            "versions":[{"version":1,"structured":{},"display_text":f"Thank you {row['name']} for your Board service. This confirms the respectful departure and the transition steps agreed in our conversation.","source":"admin_preview_fixture","created_at":now}],
                            "current_version":1,"approved_at":now,"created_at":now,"updated_at":now,"internal_preview":True,
                        }},
                        upsert=True,
                    )

        return session_id

    async def seed_fundraising_preview(member: dict) -> None:
        now = now_iso()
        tag = f"{FUNDRAISING_FIXTURE_VERSION}-{suffix(member)}"
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
                "current_individual_donor_profile": "About 35 recurring or repeat individual donors, mostly personal contacts and former volunteers.",
                "current_individual_donor_motivation": "They care about youth opportunity, have seen the programs directly or trust the founder and volunteers who introduced them.",
                "current_individual_donor_process": "Most gifts come through personal outreach, year-end emails and occasional event follow-up.",
                "current_individual_donors": "We have about 35 recurring or repeat individual donors, mostly personal contacts and former volunteers. There is no formal major-donor pipeline yet.",
                "individual_fundraising_process": "Most individual gifts come through personal outreach, year-end emails and occasional event follow-up. We do not yet have a consistent cultivation, ask, follow-up and stewardship rhythm.",
                "current_business_profile": "Three small business sponsors and several warm employer relationships.",
                "current_business_support": "They sponsor youth-employment activities, provide employer access and support selected events.",
                "current_business_process": "Support usually begins through a warm introduction, followed by a short overview, a conversation and manual follow-up.",
                "current_businesses": "We have three small business sponsors and several warm employer relationships, but no structured corporate partnership pipeline.",
                "business_fundraising_process": "Business support usually begins through a warm introduction from the founder or a Board Member. We send a short overview, hold a conversation and follow up manually, but there is no shared pipeline or standard partnership process yet.",
                "current_grantor_profile": "Foundation and government grantors focused on youth employment, education access and economic mobility.",
                "current_grantor_support": "They fund program delivery, participant support and selected capacity costs.",
                "current_grantor_process": "Staff monitor familiar funders and public opportunities, then prepare tailored applications and follow up through each decision cycle.",
                "current_grantors": "About 55% of current revenue comes from foundation and government grants. Grant prospecting is mostly reactive.",
                "grant_fundraising_process": "Staff monitor familiar funders and public opportunities, then prepare applications when a relevant deadline appears. We need a more proactive research, cultivation, calendar and follow-up process.",
            },
            "participation": {
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
            1: "Individuals who care about youth opportunity, workforce mobility and mentoring; local business owners; employers that hire early-career talent; and grant funders focused on education, workforce development and economic mobility.",
            2: "Board and staff networks, employer associations, chambers of commerce, professional groups, alumni networks, community foundations, local business events and funder databases filtered for youth and workforce priorities.",
            3: "Use credible youth outcomes, employer stories, practical insight about youth employment, small mission-connected events and warm introductions to earn attention before asking for money.",
            4: "Move each prospect through a clear relationship process: help them know us, stay connected, see proof of impact, build trust, receive an appropriate ask, get consistent follow-up and then be stewarded after they give.",
        }
        for section_id, first in primary_answers.items():
            await db.game_section_responses.update_one(
                {"board_member_id": primary_id, "section_id": section_id},
                {"$setOnInsert": {
                    "board_member_id": primary_id,
                    "user_id": member["user_id"],
                    "section_id": section_id,
                    "first_response": [first],
                    "first_move_locked": True,
                    "final_response": [first],
                    "guided_selections": {},
                    "additional_ideas": {},
                    "stage_responses": {},
                    "preferences": [],
                    "do_not_want": [],
                    "group_game_ideas": [first],
                    "extras": {"second_response": first},
                    "fine_tuning": {"completed": True},
                    "approved_entries": [{"text": first, "source": "founder"}],
                    "approved_display": first,
                    "completed": True,
                    "completed_at": now,
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
                "funding_deadline": "2027-06-30",
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


        group_session_id = f"admin-preview-group-session-{tag}"
        group_token = f"admin-preview-group-token-{tag}"
        await db.group_game_sessions.update_one(
            {"session_id": group_session_id},
            {"$set": {
                "session_id": group_session_id, "user_id": member["user_id"], "token": group_token,
                "status": "completed", "current_round": 4, "game_version": "four-area-v1",
                "started_at": now, "completed_at": now,
                "updated_at": now, "created_at": now, "internal_preview": True,
            }},
            upsert=True,
        )

        participant_rows = [
            (primary_id, primary_token, "Rooney"),
            *[(person_id, token, name.split(" ")[0]) for person_id, token, name, _email, _title, _ideas in board_people],
        ]
        for board_member_id, slot_id, first_name in participant_rows:
            await db.group_game_participants.update_one(
                {"session_id": group_session_id, "board_member_id": board_member_id},
                {"$set": {
                    "participant_id": f"admin-preview-group-participant-{board_member_id}-{tag}",
                    "session_id": group_session_id, "board_member_id": board_member_id, "slot_id": slot_id,
                    "name": first_name, "device_id": f"admin-preview-device-{board_member_id}",
                    "joined_at": now, "last_active_at": now, "internal_preview": True,
                }},
                upsert=True,
            )

        group_rounds = [
            ("who_should_fund", "Who Should Fund Our Mission", [
                "Professionals and business owners who care about youth opportunity, workforce mobility and mentoring.",
                "Employers that need early-career talent and want visible local community impact.",
                "Foundations and public funders focused on youth employment, education access and economic mobility.",
                "PRESENT INDIVIDUAL DONORS: About 35 recurring or repeat donors, mostly personal contacts and former volunteers who care about youth opportunity.",
                "PRESENT CORPORATE SPONSORS / BUSINESS PARTNERS: Three small business sponsors and several warm employer relationships supporting youth-employment activities and selected events.",
                "PRESENT GRANTORS: Foundation and government funders focused on youth employment, education access and economic mobility.",
            ]),
            ("where_to_find", "Where We Can Consistently Find Them", [
                "Start with Board and staff networks, employer associations, chambers of commerce and professional groups.",
                "Use a weekly prospect-research routine and assign every qualified prospect to a relationship owner.",
                "Use community foundations and funder databases to identify grantors whose priorities and geography match the mission.",
            ]),
            ("attract_attention", "How We Will Attract Their Attention", [
                "Publish credible youth outcomes, employer stories and useful youth-employment insight before making most asks.",
                "Use warm introductions and small mission-connected briefings to create direct relationships.",
                "Give businesses a clear partnership proposition tied to youth talent, community impact and measurable outcomes.",
            ]),
            ("fundraising_process", "The Process We Will Use To Raise Money", [
                "Use Know, Like, Trust, Ask, Follow Up and Steward as the common relationship pathway.",
                "Every prospect must have a relationship owner, stage, next action and follow-up point.",
                "Stewardship begins immediately after support is secured and should prepare the relationship for the next gift or partnership.",
                "PRESENT INDIVIDUAL DONOR METHOD: Personal outreach, year-end emails and event follow-up.",
                "PRESENT BUSINESS / SPONSOR METHOD: Warm introductions, a short overview, a conversation and manual follow-up.",
                "PRESENT GRANTOR METHOD: Monitor relevant opportunities, prepare tailored applications and follow up through each decision cycle.",
            ]),
            ("team", "Team", [
                "Rooney coordinates the fundraising system and staff follow-up.",
                "Maya opens and develops corporate and employer relationships.",
                "Daniel helps maintain fundraising performance visibility and Board accountability.",
                "Aisha strengthens fundraising messaging, partner stories and campaign visibility.",
            ]),
            ("technology", "Technology", [
                "Use one lightweight CRM for prospects, relationship owners, stages and next actions.",
                "Use one shared fundraising dashboard for monthly Board review.",
                "Keep fundraising materials in one shared cloud folder so Board Members can find current versions quickly.",
            ]),
            ("materials", "Materials", [
                "Complete one case for support tied to the $500,000 goal and youth outcomes.",
                "Create a corporate partnership one-pager and employer briefing deck.",
                "Prepare major-donor conversation guides, follow-up messages and stewardship templates.",
            ]),
            ("budget", "Budget", [
                "Fund the smallest CRM and prospect-research setup the team will actually maintain.",
                "Budget for communications support, donor stewardship and only the cultivation activities required by the strategy.",
                "Use existing staff, Board leadership, templates and current subscriptions before buying additional capacity.",
            ]),
            ("execution", "Execution And Accountability", [
                "Days 1–30: configure the system, finalize core materials, map warm relationships and confirm owners.",
                "Days 31–60: launch visibility, introductions, prospect research and cultivation.",
                "Days 61–90: move ready relationships into meetings, proposals and asks while continuing follow-up and stewardship.",
                "Review fundraising responsibilities, evidence, barriers and next actions at every Board meeting until the June 30, 2027 deadline.",
            ]),
        ][:4]
        for round_number, (section_key, title, ideas) in enumerate(group_rounds, 1):
            round_id = f"admin-preview-group-round-{round_number}-{tag}"
            idea_rows = []
            selected_ids = []
            results = []
            for index, idea_text in enumerate(ideas):
                idea_id = f"admin-preview-group-idea-{round_number}-{index + 1}-{tag}"
                idea_rows.append({
                    "idea_id": idea_id, "session_id": group_session_id, "round_number": round_number,
                    "section_key": section_key, "text": idea_text, "normalized": idea_text.lower(),
                    "contributor_names": ["Board discussion"], "contributor_ids": [], "order": index,
                    "internal_preview": True,
                })
                selected_ids.append(idea_id)
                results.append({
                    "idea_id": idea_id, "text": idea_text, "suggested_by": "Board discussion",
                    "total_score": 1, "first_place_count": 1 if index == 0 else 0,
                    "selection_count": 1, "order": index, "rank": index + 1,
                    "prioritised": True, "additional": False, "decision_source": "board_checkbox",
                })
            await db.group_game_rounds.update_one(
                {"session_id": group_session_id, "round_number": round_number},
                {"$set": {
                    "round_id": round_id, "session_id": group_session_id, "round_number": round_number,
                    "section_key": section_key, "title": title,
                    "instruction": f"Admin Preview completed Board discussion for {title}.",
                    "status": "closed", "required_rank": 0, "idea_count": len(idea_rows),
                    "started_at": now, "closed_at": now, "created_at": now, "internal_preview": True,
                }},
                upsert=True,
            )
            for idea_row in idea_rows:
                await db.group_game_ideas.update_one(
                    {"idea_id": idea_row["idea_id"]}, {"$set": idea_row}, upsert=True)
            await db.group_game_host_decisions.update_one(
                {"session_id": group_session_id, "round_number": round_number},
                {"$set": {
                    "session_id": group_session_id, "round_number": round_number,
                    "selected_idea_ids": selected_ids, "additional_agreed_ideas": [],
                    "created_at": now, "updated_at": now, "internal_preview": True,
                }},
                upsert=True,
            )
            await db.group_game_results.update_one(
                {"session_id": group_session_id, "round_number": round_number},
                {"$set": {
                    "session_id": group_session_id, "round_number": round_number, "round_id": round_id,
                    "section_key": section_key, "title": title, "results": results, "computed_at": now,
                    "internal_preview": True,
                }},
                upsert=True,
            )

        transcript_id = f"admin-preview-fundraising-transcript-{tag}"
        await db.game_meeting_transcripts.update_one(
            {"user_id": member["user_id"]},
            {"$set": {
                "transcript_id": transcript_id, "user_id": member["user_id"],
                "text": fundraising_meeting_transcript(), "source": "admin_preview_fixture",
                "filename": "BrightPath-Board-Fundraising-Meeting-Transcript.txt",
                "submitted_at": now, "created_at": now, "updated_at": now, "internal_preview": True,
            }},
            upsert=True,
        )

        strategy_id = f"admin-preview-final-fundraising-strategy-{tag}"
        strategy_data = {
            "executive_summary": (
                "BrightPath Youth Alliance will pursue $500,000 by June 30, 2027 through one Board-owned fundraising system. "
                "The strategy prioritizes mission-aligned individuals, employers and grant funders, moves every qualified relationship through a consistent Know, Like, Trust, Ask, Follow Up and Steward pathway, and gives each Board Member a specific execution responsibility."
            ),
            "fundraising_goal": {
                "amount": "$500,000", "currency": "USD", "deadline": "June 30, 2027",
                "purpose": "Fund program growth, fundraising capacity and employer-partnership expansion.",
                "summary": "The deadline drives the execution calendar. System setup happens first, then the Board moves qualified relationships toward decisions early enough to pursue the full goal before June 30, 2027.",
            },
            "fundraising_audiences": {
                "individuals": [
                    {"title": "Mission-aligned professionals and business owners", "explanation": "People who care about youth opportunity, education, mentoring and economic mobility and have the capacity to make meaningful individual gifts.", "focus": "Start with warm Board, staff and alumni connections."},
                    {"title": "High-capacity people connected to existing supporters", "explanation": "Qualified people who can be introduced through trusted relationships rather than cold outreach.", "focus": "Use relationship mapping before prospecting outside the network."},
                ],
                "businesses": [
                    {"title": "Employers seeking early-career talent", "explanation": "Companies whose workforce needs connect directly to BrightPath's youth-employment mission.", "focus": "Lead with talent pathways, measurable community impact and employee engagement."},
                    {"title": "Local and regional businesses with youth or community-investment priorities", "explanation": "Businesses whose geography, customers, workforce or social-impact priorities overlap with the communities BrightPath serves.", "focus": "Pursue strategic partnerships, not one-off logo sponsorships."},
                ],
                "grantors": [
                    {"title": "Youth employment and workforce funders", "explanation": "Foundations and public funders whose priorities match youth employment, education access, mentoring and economic mobility.", "focus": "Research eligible costs and application calendars proactively."},
                ],
            },
            "where_to_find": {
                "priorities": [
                    {"title": "Board and staff relationship maps", "explanation": "Start with trusted personal, professional, employer and community relationships."},
                    {"title": "Employer associations and chambers of commerce", "explanation": "Use places where business decision makers already gather."},
                    {"title": "Community foundations and funder databases", "explanation": "Use filters for mission, geography, eligible costs and decision calendars."},
                ],
                "additional_ideas": ["Professional associations, alumni networks and local business events."],
            },
            "attraction": {
                "priorities": [
                    {"title": "Evidence-led youth outcome content", "explanation": "Show credible results, useful insight and participant stories with consent before asking for support."},
                    {"title": "Warm introductions and small briefings", "explanation": "Use trusted people to create direct conversations with qualified prospects."},
                    {"title": "Employer-facing partnership proposition", "explanation": "Explain how partnership creates value for young people, employers and the community."},
                ],
                "additional_ideas": ["Site visits and selected mission-connected events for qualified prospects."],
            },
            "fundraising_process": {
                "individuals": {
                    "how_this_process_works": "Use warm relationships and evidence to move qualified individuals from awareness to an appropriate gift, then steward the relationship for long-term support.",
                    "know": ["Board or staff introduction", "Evidence-led content or event encounter"],
                    "like": ["Personal follow-up", "Useful mission-connected insight", "Small-group briefing"],
                    "trust": ["Youth outcome evidence", "Transparent explanation of funding use", "Leadership conversation"],
                    "ask": ["Make a specific gift request matched to capacity and relationship maturity"],
                    "follow_up": ["Record next action immediately and follow up until the prospect gives a clear answer"],
                    "steward": ["Thank promptly, report impact and maintain a meaningful relationship after the gift"],
                },
                "businesses": {
                    "how_this_process_works": "Target employers and businesses with a real mission/business connection, reach the correct decision maker and develop a partnership proposition before asking for financial support.",
                    "know": ["Warm Board introduction", "Employer-network visibility"],
                    "like": ["Share useful youth-employment insight", "Invite decision makers to a briefing"],
                    "trust": ["Show employer outcomes, community evidence and clear partnership delivery"],
                    "ask": ["Present a specific partnership or sponsorship proposition"],
                    "follow_up": ["Track decision maker, proposal status, next action and internal decision timeline"],
                    "steward": ["Report partnership outcomes and develop the relationship beyond the first contribution"],
                },
                "grantors": {
                    "how_this_process_works": "Research funders whose priorities and eligible costs actually fit BrightPath, understand the decision calendar and cultivate where possible before submitting.",
                    "know": ["Funder research and Board/staff relationships"],
                    "like": ["Attend relevant funder briefings and communicate where appropriate"],
                    "trust": ["Demonstrate mission alignment, outcomes and delivery capacity"],
                    "ask": ["Submit a tailored application or proposal against the actual funder's requirements"],
                    "follow_up": ["Track clarification requests, decisions and future cycles"],
                    "steward": ["Deliver reports, communicate outcomes and prepare for renewal"],
                },
            },
            "board_fundraising_process": {
                "know": ["Identify people, businesses and grantors in each Board Member's own network who match the approved funder profiles."],
                "like": ["Use the Board Member's relationship to enable an introduction or first conversation."],
                "trust": ["Bring the organization into the relationship with credible evidence, stories and clear follow-through."],
                "ask": ["The Board Member joins or enables an appropriate ask according to the responsibility they agreed to carry."],
                "follow_up": ["Keep every introduced relationship in the shared pipeline with a next action and owner."],
                "steward": ["Board Members help maintain important relationships they opened while staff manages consistent organization follow-up."],
            },
            "team_roles": [
                {"role": "Fundraising system coordination", "assigned": "Rooney Akpesiri", "responsibility": "Coordinate the fundraising pipeline, staff follow-up, materials and Board accountability."},
                {"role": "Corporate partnerships and introductions", "assigned": "Maya Thompson", "responsibility": "Open at least five qualified corporate/employer relationships in the first month and help develop partnership opportunities."},
                {"role": "Finance and fundraising performance", "assigned": "Daniel Brooks", "responsibility": "Help build the fundraising dashboard and review pipeline, revenue and budget performance with the Board."},
                {"role": "Fundraising communications and visibility", "assigned": "Aisha Patel", "responsibility": "Strengthen the case for support, publish evidence-led content and develop partner stories."},
            ],
            "execution_resources": {
                "people": ["Founder/fundraising coordinator", "Board relationship owners", "Board finance oversight", "Board communications support"],
                "technology": ["One lightweight CRM", "Shared fundraising dashboard", "Email platform", "Shared cloud files"],
                "materials": ["Case for support", "Corporate partnership one-pager", "Impact evidence sheet", "Major donor conversation guide", "Follow-up and stewardship templates"],
                "resources": ["Board relationship maps", "Outcome data", "Participant stories with consent", "Employer and funder research"],
                "content": ["Evidence-led youth outcome posts", "Partner stories", "Useful youth-employment insight", "Qualified prospect briefing content"],
            },
            "execution_budget": {
                "required_now": [
                    {"item": "CRM / prospect tracking", "why_needed": "One reliable place for prospects, owners, stages and next actions.", "lowest_cost_approach": "Use the smallest system the team can maintain consistently.", "cost": "PRICE TO CONFIRM"},
                    {"item": "Prospect research and communications support", "why_needed": "Support proactive pipeline building and consistent visibility.", "lowest_cost_approach": "Start with Board networks, public sources and existing staff/templates.", "cost": "PRICE TO CONFIRM"},
                ],
                "later_or_optional": [
                    {"item": "Large paid prospect database", "why_later": "Only add after the team is consistently using the core pipeline.", "lowest_cost_approach": "Use public and relationship-led research first.", "cost": "PRICE TO CONFIRM"},
                ],
                "cost_reduction_options": ["Reuse existing subscriptions and brand assets.", "Use Board networks before buying prospect lists.", "Create repeatable templates before outsourcing routine materials."],
                "budget_summary": "Start lean. Fund only the capacity, technology and activity required to execute the adopted strategy, and confirm real prices before approving spend.",
            },
            "execution_timeline": {
                "phase_1_build_the_system": ["Days 1–30: configure CRM and dashboard, complete relationship maps, finalize core materials and confirm owners."],
                "phase_2_build_know_like_trust": ["Days 31–60: launch evidence-led visibility, warm introductions, employer outreach and funder cultivation."],
                "phase_3_ask_campaign": ["Days 61–90 and onward: move qualified relationships into asks, proposals and decisions as soon as trust and timing permit."],
                "follow_up_and_steward": ["Track follow-up continuously and begin stewardship immediately after any gift or partnership is secured."],
                "business_timeline": ["Work each employer/business relationship around its real budget and decision calendar rather than waiting for one organization-wide campaign date."],
                "grantor_timeline": ["Track each grantor's actual application and decision timeline and work backward from the June 30, 2027 funding deadline."],
            },
            "board_priorities": [
                {"area": "First 30 Days", "items": ["Set up the shared system", "Map warm relationships", "Finalize the case for support", "Open the first five corporate relationships"]},
                {"area": "Board Accountability", "items": ["Review every delegated fundraising responsibility and next action at each Board meeting"]},
            ],
            "additional_board_ideas": [
                {"area": "Future Experiments", "items": ["Consider a small employer briefing event after the core pipeline is operating consistently"]},
            ],
            "next_step": "Your final fundraising strategy is ready. Review it with your board, send it to every participant and move into execution using the Board Portfolios, Execution Materials and Relationship Mapping.",
        }
        strategy_data = {key: strategy_data[key] for key in (
            "fundraising_audiences", "where_to_find", "attraction", "fundraising_process"
        )}
        await db.game_strategies.update_one(
            {"strategy_id": strategy_id},
            {"$set": {
                "strategy_id": strategy_id, "user_id": member["user_id"], "mode": "final",
                "status": "adopted", "version": 1, "schema_version": 3,
                "prepared_by": f"The Board of {ORG_NAME}", "generated_at": now, "adopted_at": now,
                "share_token": f"admin-preview-fundraising-strategy-share-{tag}", "data": strategy_data,
                "section_edits": {}, "source": "admin_preview_fixture", "internal_preview": True,
                "created_at": now, "updated_at": now,
            }},
            upsert=True,
        )
        await db.game_strategy_jobs.update_one(
            {"user_id": member["user_id"], "mode": "final"},
            {"$set": {
                "user_id": member["user_id"], "mode": "final", "status": "done", "strategy_id": strategy_id,
                "error": "", "started_at": now, "finished_at": now, "internal_preview": True,
            }},
            upsert=True,
        )

        portfolio_specs = {
            primary_id: {
                "name": "Rooney Akpesiri", "email": member["email"], "availability": "4–6 hours per month",
                "role": "Fundraising System Coordinator",
                "commitment": "Coordinate the fundraising pipeline, staff follow-up, materials and Board accountability.",
                "activities": ["Maintain the shared pipeline", "Coordinate follow-up and staff execution", "Prepare Board fundraising progress updates"],
            },
            board_people[0][0]: {
                "name": "Maya Thompson", "email": board_people[0][3], "availability": "2–4 hours per month",
                "role": "Corporate Partnerships Lead",
                "commitment": "Open and develop qualified corporate and employer relationships and join selected partnership asks.",
                "activities": ["Make warm corporate introductions", "Join priority employer meetings", "Help steward relationships she opens"],
            },
            board_people[1][0]: {
                "name": "Daniel Brooks", "email": board_people[1][3], "availability": "2–4 hours per month",
                "role": "Fundraising Performance Lead",
                "commitment": "Help build the fundraising dashboard and review pipeline, revenue and budget performance.",
                "activities": ["Review pipeline numbers", "Help structure the dashboard", "Support selected asks where appropriate"],
            },
            board_people[2][0]: {
                "name": "Aisha Patel", "email": board_people[2][3], "availability": "2–4 hours per month",
                "role": "Fundraising Communications Lead",
                "commitment": "Strengthen the case for support, evidence-led content and partner stories used in fundraising.",
                "activities": ["Improve case-for-support messaging", "Develop evidence-led content", "Support partner and donor storytelling"],
            },
        }
        for board_member_id, spec in portfolio_specs.items():
            portfolio_id = f"admin-preview-fundraising-portfolio-{board_member_id}-{tag}"
            portfolio_token = f"admin-preview-fundraising-portfolio-token-{board_member_id}-{tag}"
            system_roles = [{
                "item_id": f"{portfolio_id}-role-1", "role_key": "custom", "label": spec["role"],
                "source": "meeting_commitment", "involvement": "Board-agreed responsibility",
                "member_note": "", "commitment": spec["commitment"], "deadline": "2027-06-30",
                "requires_confirmation": False, "active": True,
            }]
            direct_activities = [
                {
                    "item_id": f"{portfolio_id}-activity-{index + 1}", "activity_key": "custom",
                    "label": activity, "source": "meeting_commitment",
                    "involvement": "Agreed execution activity", "member_note": "",
                    "commitment": activity, "deadline": "", "requires_confirmation": False, "active": True,
                }
                for index, activity in enumerate(spec["activities"])
            ]
            approved_snapshot = {
                "system_roles": system_roles, "direct_activities": direct_activities,
                "additional_commitments": [], "do_not_want": [], "availability": spec["availability"], "org_note": "",
            }
            await db.board_portfolios.update_one(
                {"portfolio_id": portfolio_id},
                {"$set": {
                    "portfolio_id": portfolio_id, "user_id": member["user_id"], "board_member_id": board_member_id,
                    "member_name": spec["name"], "member_email": spec["email"], "strategy_id": strategy_id,
                    "token": portfolio_token, "status": "materials_ready", "version": 1, "approved_version": 1,
                    "system_roles": system_roles, "direct_activities": direct_activities,
                    "additional_commitments": [], "do_not_want": [], "availability": spec["availability"],
                    "org_note": "", "change_request": "", "sent_at": now, "approved_at": now,
                    "approved_snapshot": approved_snapshot, "created_at": now, "updated_at": now, "internal_preview": True,
                }},
                upsert=True,
            )
            toolkit_id = f"admin-preview-toolkit-{portfolio_id}"
            await db.execution_toolkits.update_one(
                {"toolkit_id": toolkit_id},
                {"$set": {
                    "toolkit_id": toolkit_id, "portfolio_id": portfolio_id, "user_id": member["user_id"],
                    "board_member_id": board_member_id, "strategy_id": strategy_id, "portfolio_version": 1,
                    "status": "ready",
                    "data": {
                        "quick_start": [
                            "Review the responsibility in your approved Board Fundraising Portfolio.",
                            "Choose the first relationship, material or execution task you will move this week.",
                            "Record progress and the next action before the next Board meeting.",
                        ],
                        "scripts_and_templates": [
                            "Warm introduction message", "Fundraising meeting preparation checklist",
                            "Follow-up message", "Stewardship thank-you and impact update",
                        ],
                        "relationship_mapping": "Use your professional, business and community network to identify people, businesses and grantors that match the Board-approved funding audiences.",
                    },
                    "ready_email_sent": True, "generated_at": now, "created_at": now, "updated_at": now, "internal_preview": True,
                }},
                upsert=True,
            )
            await db.game_strategy_deliveries.update_one(
                {"strategy_id": strategy_id, "board_member_id": board_member_id},
                {"$set": {
                    "user_id": member["user_id"], "strategy_id": strategy_id, "board_member_id": board_member_id,
                    "email": spec["email"], "member_name": spec["name"], "status": "sent", "error": "",
                    "sent_at": now, "updated_at": now, "created_at": now, "internal_preview": True,
                }},
                upsert=True,
            )

        relationship_rows = [
            (board_people[0][0], "Maya Thompson", "Business", "Jordan Wells", "Fictional Regional Employers Council", "Former employer-network colleague", "Strong fit because the council represents employers hiring early-career talent."),
            (board_people[1][0], "Daniel Brooks", "Individual", "Elena Price", "Fictional Financial Advisory Group", "Professional colleague", "High-capacity professional who has supported youth education and mentoring."),
            (board_people[2][0], "Aisha Patel", "Business", "Samira Cole", "Fictional Impact Brands", "Marketing industry contact", "Brand has a community-investment priority around youth opportunity."),
        ]
        for index, (board_member_id, member_name, funder_type, person_name, organization_name, how_know, why_match) in enumerate(relationship_rows, 1):
            relationship_id = f"admin-preview-game-relationship-{index}-{tag}"
            await db.game_relationships.update_one(
                {"relationship_id": relationship_id},
                {"$set": {
                    "relationship_id": relationship_id, "user_id": member["user_id"],
                    "board_member_id": board_member_id, "member_name": member_name,
                    "funder_type": funder_type, "name": person_name, "organization": organization_name,
                    "email": "", "phone": "", "other_contact": "", "how_know": how_know, "why_match": why_match,
                    "willing_intro": True, "willing_participate": True, "willing_ask": False, "willing_org_ask": True,
                    "created_at": now, "internal_preview": True,
                }},
                upsert=True,
            )

    async def seed_fresh_client_test(member: dict, product: str, config: dict) -> str:
        """Create only the state a real customer would have immediately after payment."""
        now = now_iso()
        tag = suffix(member)
        if config.get("entitlements"):
            await db.members.update_one(
                {"user_id": member["user_id"]},
                {"$addToSet": {"entitlements": {"$each": config["entitlements"]}},
                 "$set": {"updated_at": now, "internal_client_test": True}},
            )

        if product == "recruitment":
            lead_id = f"admin-fresh-recruitment-lead-{tag}"
            session_id = f"admin-fresh-recruitment-session-{tag}"
            assessment_token = f"admin-fresh-recruitment-assessment-{tag}"
            recruitment_answers = {
                "mission": MISSION,
                "current_board": "We have five Board Members. The Board Chair and Treasurer are active, while the remaining members participate inconsistently and the founder still carries most relationship-building work.",
                "desired_board_members": "We need Board Members with fundraising, employer/corporate partnership and marketing or communications experience.",
                "support_needs": "Build diversified revenue, expand employer partnerships, strengthen visibility and help the Board carry clear strategic responsibilities.",
                "board_type": "A strategic Board that helps govern, opens relationships, strengthens fundraising and follows through on agreed responsibilities.",
                "why_join": "The mission gives experienced professionals a concrete opportunity to expand education and employment pathways for young people.",
            }
            await db.funnel_leads.update_one(
                {"lead_id": lead_id},
                {"$set": {
                    "lead_id": lead_id, "offer_source": "recruitment",
                    "name": "Rooney Akpesiri", "email": member["email"],
                    "organization": ORG_NAME, "desired_count": "3",
                    "answers": {"new_members_needed": "3", **recruitment_answers},
                    "member_user_id": member["user_id"], "internal_preview": True,
                    "created_at": now, "updated_at": now,
                }},
                upsert=True,
            )
            await db.recruitment_free_assessments.update_one(
                {"lead_id": lead_id},
                {"$set": {
                    "token": assessment_token, "lead_id": lead_id, "name": "Rooney Akpesiri",
                    "email": member["email"], "organization": ORG_NAME, "desired_count": 3,
                    "answers": recruitment_answers,
                    "state": {"paid": True, "result_generated": False, "generation_status": "not_started"},
                    "result": None, "member_user_id": member["user_id"], "internal_preview": True,
                    "created_at": now, "updated_at": now,
                }},
                upsert=True,
            )
            await db.members.update_one(
                {"user_id": member["user_id"]},
                {"$addToSet": {"lead_ids": lead_id}, "$set": {"updated_at": now}},
            )
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {
                    "session_id": session_id, "lead_id": lead_id,
                    "offer_source": "recruitment", "purchase_source": "recruitment_497",
                    "selected_tier": "497", "amount": 0, "currency": "usd",
                    "status": "completed", "payment_status": "paid",
                    "claimed_by_user_id": member["user_id"], "internal_preview": True,
                    "created_at": now, "updated_at": now,
                }},
                upsert=True,
            )
            return f"/recruit/welcome?session_id={session_id}"

        if product == "board-fundraising-game":
            await db.game_profiles.update_one(
                {"user_id": member["user_id"]},
                {"$set": {
                    "user_id": member["user_id"],
                    "organization": {"name": ORG_NAME, "mission": MISSION, "website": ""},
                    "goal": {
                        "amount": "500000",
                        "purpose": "Grow programs, strengthen fundraising capacity and expand employer partnerships.",
                        "deadline": "",
                    },
                    "primary_user": {
                        "full_name": "Rooney Akpesiri", "email": member["email"],
                        "job_title": "Founder and Executive Director",
                    },
                    "profile_completed": True, "situation_completed": False,
                    "internal_preview": True, "updated_at": now,
                }, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            await db.game_situations.update_one(
                {"user_id": member["user_id"]},
                {"$set": {
                    "sections": {
                        "current_reality": {
                            "current_individual_donor_profile": "About 35 repeat individual donors, mostly personal contacts and former volunteers.",
                            "current_individual_donor_motivation": "They care about youth opportunity and trust people already connected to the organization.",
                            "current_individual_donor_process": "Personal outreach, year-end emails and event follow-up.",
                            "current_individual_donors": "About 35 repeat individual donors, mostly personal contacts and former volunteers. We do not yet have a formal major-donor pipeline.",
                            "current_business_profile": "Three small business sponsors and several warm employer relationships.",
                            "current_business_support": "They support youth-employment activity, selected events and employer access.",
                            "current_business_process": "Warm introductions, a short overview, a conversation and manual follow-up.",
                            "current_businesses": "Three small business sponsors and several warm employer relationships. Corporate outreach is still informal.",
                            "current_grantor_profile": "Foundation and government grantors focused on youth employment and education.",
                            "current_grantor_support": "They fund program delivery, participant support and selected capacity costs.",
                            "current_grantor_process": "Research relevant opportunities, prepare tailored applications and follow up through each decision cycle.",
                            "current_grantors": "Foundation and government grants provide more than half of current revenue. Prospecting is mostly reactive.",
                        },
                        "participation": {
                            "raise": ["Join fundraising meetings", "Help steward relationships"],
                            "raise_other": "", "time": "2–4 hours per month", "anything_else": "I want every Board Member to leave with a role that fits their strengths and relationships.",
                        },
                    },
                    "current_step": 0, "completed": False, "internal_preview": True,
                    "created_at": now, "updated_at": now,
                }},
                upsert=True,
            )
            primary_id = f"admin-fresh-game-primary-{tag}"
            primary_token = f"admin-fresh-game-primary-token-{tag}"
            await db.game_board_members.update_one(
                {"member_id": primary_id},
                {"$set": {
                    "member_id": primary_id, "user_id": member["user_id"], "token": primary_token,
                    "full_name": "Rooney Akpesiri", "email": member["email"],
                    "board_title": "Founder and Executive Director", "is_primary": True,
                    "game_version": 3, "total_sections": 4, "invitation_status": "self",
                    "removed": False, "internal_preview": True, "created_at": now, "updated_at": now,
                }},
                upsert=True,
            )
            fresh_game_answers = {
                1: "Individuals who care about youth opportunity, employers seeking early-career talent, local businesses and grant funders focused on education, workforce development and economic mobility.",
                2: "Board and staff networks, chambers of commerce, employer associations, alumni networks, community foundations, professional groups and relevant funder databases.",
                3: "Use credible youth outcomes, employer stories, practical insight, mission-connected events and warm introductions to earn attention before asking for money.",
                4: "Move each prospect through a clear relationship process: know, like, trust, ask, follow up and steward.",
            }
            for section_id, answer in fresh_game_answers.items():
                await db.game_section_responses.update_one(
                    {"board_member_id": primary_id, "section_id": section_id},
                    {"$set": {
                        "board_member_id": primary_id, "user_id": member["user_id"], "section_id": section_id,
                        "first_response": [answer], "first_move_locked": False, "final_response": [],
                        "fine_tuning": {"completed": False}, "completed": False,
                        "internal_preview": True, "created_at": now, "updated_at": now,
                    }},
                    upsert=True,
                )
            return "/game/welcome"

        session_id = f"admin_fresh_{product.replace('-', '_')}_{tag}"
        lead_token = f"admin-fresh-{product}-{tag}"
        offer_source = "strategic_planning" if product == "strategic-planning" else "board_recommitment"
        await db.guided_product_leads.update_one(
            {"token": lead_token},
            {"$set": {
                "token": lead_token, "product": product,
                "name": "Rooney Akpesiri", "email": member["email"],
                "organization": ORG_NAME, "board_count": 5,
                "internal_preview": True, "followup_status": "converted",
                "created_at": now, "updated_at": now,
            }},
            upsert=True,
        )
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "session_id": session_id, "status": "completed", "payment_status": "paid",
                "offer_source": offer_source, "purchase_source": config["purchase_source"],
                "guided_lead_token": lead_token, "lead_email": member["email"],
                "payment_email": member["email"], "payment_phone": "+44 7700 900123",
                "claimed_by_user_id": member["user_id"], "amount": 0, "currency": "usd",
                "internal_preview": True, "created_at": now, "updated_at": now,
            }},
            upsert=True,
        )
        return f"/{product}/welcome?session_id={session_id}"

    @router.post("/fresh/{product}")
    async def launch_fresh_client_test(product: str, request: Request, response: Response):
        admin = await authenticate_admin(request, db)
        config = PRODUCTS.get(product)
        if not config:
            raise HTTPException(status_code=404, detail="Unknown product dashboard")
        run_seed = hashlib.sha256(
            f"{admin['user_id']}:{product}:{now_iso()}".encode("utf-8")
        ).hexdigest()[:12]
        member = await preview_member(admin, f"{product}-{FRESH_TEST_VERSION}-{run_seed}")
        await db.members.update_one(
            {"user_id": member["user_id"]},
            {"$set": {
                "internal_client_test": True,
                "client_test_product": product,
                "client_test_started_at": now_iso(),
            }},
        )
        member = await db.members.find_one({"user_id": member["user_id"]}, {"_id": 0})
        start_url = await seed_fresh_client_test(member, product, config)
        set_member_cookie(response, create_member_token(member["user_id"], member["email"]))
        return {
            "dashboard_url": start_url,
            "start_url": start_url,
            "product": product,
            "mode": "fresh",
            "test_member_email": member["email"],
        }

    @router.post("/{product}")
    async def launch_dashboard_preview(product: str, request: Request, response: Response):
        admin = await authenticate_admin(request, db)
        config = PRODUCTS.get(product)
        if not config:
            raise HTTPException(status_code=404, detail="Unknown product dashboard")
        fixture_version = (
            RECRUITMENT_FIXTURE_VERSION if product == "recruitment"
            else STRATEGIC_FIXTURE_VERSION if product == "strategic-planning"
            else RECOMMITMENT_FIXTURE_VERSION if product == "board-recommitment"
            else FUNDRAISING_FIXTURE_VERSION if product == "board-fundraising-game"
            else FIXTURE_VERSION
        )
        # Keep every product preview in its own isolated member identity. Two products may
        # legitimately share the same fixture version number, but they must never share
        # preview-member state, entitlements or downstream records.
        member = await preview_member(admin, f"{product}-{fixture_version}")
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
