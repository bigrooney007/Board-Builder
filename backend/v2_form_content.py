"""Pure, shared board form content. Strategic participant questions are extracted unchanged from the established guided planning journey."""


def build_strategic_form(a: dict, p: dict) -> dict:
    programs=a.get("programs") or a.get("areas") or ""
    supplied_programs=a.get("program_details") if isinstance(a.get("program_details"),list) else []
    program_details=[]
    for item in supplied_programs[:20]:
        if not isinstance(item,dict):continue
        name=str(item.get("name","")).strip()
        if not name:continue
        program_details.append({"name":name,"description":str(item.get("description","")).strip(),"present_work":str(item.get("present_work","")).strip()})
    if not program_details:
        program_details=[{"name":x.strip(" -•\t"),"description":"","present_work":""} for x in str(programs).split("\n") if x.strip()][:12]

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

    for program in program_details:
        name=program["name"];description=program.get("description","");present_work=program.get("present_work","")
        starting="\n\nPresent program information: "+(" | ".join(x for x in [description,present_work] if x) or "No additional description supplied.")
        sections_data.append((f"Program: {name}",[
            f"Thinking specifically about {name}, what do you believe this program should accomplish for the people it serves? What should we protect, change or improve?{starting}",
            f"From what you have observed, what would make {name} more effective, useful or sustainable, and what should the organization do differently in delivering it?",
        ]))

    sections_data.extend([
        ("Team & Capacity",[
            f"Who do we presently have available to help execute this strategy — staff, Board Members, volunteers, contractors or other supporters? Where do you see enough capacity and where are we stretched?\n\nPresent information: {str(a.get('team_building') or '').strip()}",
            "What people, skills or leadership capacity do you believe we need to add or strengthen to execute the strategy successfully?",
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
            f"Based on everything above, what should the organization do first, next and after that? Compare what is already happening with what needs to happen next.\n\nWhat the organization says it is presently doing and looking towards doing: {str(a.get('action_planning') or '').strip()}",
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
    return content

# These are the existing free-intake field keys, unchanged.
INTAKE_FIELDS = {
    'recruit': ('mission', 'current_board', 'desired_board_members', 'board_type', 'support_needs', 'why_join'),
    'board-fundraising-game': ('1', '2', '3', '4', '5'),
    'strategic-planning': ('mission', 'goals', 'objectives', 'program_details', 'team_building', 'technology', 'marketing', 'partnerships', 'fundraising', 'budget', 'action_planning'),
    'board-recommitment': ('mission', 'why_recommit', 'board_help_accomplish', 'need_by'),
}
FUNDRAISING_CATEGORIES = ('individuals', 'businesses', 'grantmakers')
AUDIENCE_FIELDS = ('funder', 'why', 'where', 'attract', 'relationship', 'ask', 'amount')
AUDIENCE_QUESTIONS = {
    'individuals': [
        {'id': 'funder', 'prompt': 'Which type of individual are you thinking about?'},
        {'id': 'why', 'prompt': 'Why would they have strong reasons to support your mission?'},
        {'id': 'where', 'prompt': 'Where could your organization find people who fit this description?'},
        {'id': 'attract', 'prompt': 'How could your organization attract their interest and build credibility with them?'},
        {'id': 'relationship', 'prompt': 'How could your organization develop a relationship with these people and raise money from them?'},
        {'id': 'ask', 'prompt': 'What would you ask them to support?'},
        {'id': 'amount', 'prompt': 'How much would you ask them to give, and why would that amount be appropriate?'},
    ],
    'businesses': [
        {'id': 'funder', 'prompt': 'Which type of business are you thinking about?'},
        {'id': 'why', 'prompt': 'Why might those businesses support your mission?'},
        {'id': 'where', 'prompt': 'Where could your organization find these businesses?'},
        {'id': 'attract', 'prompt': 'How could your organization attract their interest and establish credibility?'},
        {'id': 'relationship', 'prompt': 'How could your organization develop relationships with these businesses and raise financial support?'},
        {'id': 'ask', 'prompt': 'What would you ask them to fund?'},
        {'id': 'amount', 'prompt': 'How much would you ask for, and why would that amount be appropriate?'},
    ],
    'grantmakers': [
        {'id': 'funder', 'prompt': 'Which type of grantmaker are you thinking about?'},
        {'id': 'why', 'prompt': 'Why do their funding priorities align with your mission?'},
        {'id': 'where', 'prompt': 'Where could your organization identify these grantmakers?'},
        {'id': 'attract', 'prompt': 'How could your organization develop a suitable approach and demonstrate credibility?'},
        {'id': 'relationship', 'prompt': 'How would you develop the relationship and apply or request support?'},
        {'id': 'ask', 'prompt': 'What would you ask them to fund?'},
        {'id': 'amount', 'prompt': 'What amount would be appropriate, and why?'},
    ],
}


def fundraising_form(journey: dict) -> dict:
    return {
        'introduction': f"Share your own fundraising ideas for {journey.get('organization', 'your organization')}. Complete one audience before starting another. You can skip a category, go back to edit and say when you are unsure. Your contributions will be attributed to you during the group discussion.",
        'sections': [{'key': category, 'title': category.title(), 'questions': AUDIENCE_QUESTIONS[category], 'repeatable': True} for category in FUNDRAISING_CATEGORIES],
        'questions': [{'id': 'participation', 'prompt': 'How would you personally be willing to participate in helping your organization raise money?', 'type': 'long', 'required': True}],
    }


def recommitment_questions(organization: str, active: str, advisory: str, step_down: str) -> list:
    """Labels/options retained from the established BoardRecommitmentFormPage."""
    expertise = ['Fundraising', 'Major Gifts', 'Grant Writing', 'Finance / Accounting', 'Legal', 'Human Resources', 'Marketing / Communications', 'Public Relations', 'Strategic Planning', 'Organizational Development', 'Nonprofit Leadership', 'Corporate Partnerships', 'Government Relations', 'Education', 'Youth Development', 'Healthcare', 'Mental Health', 'Technology / AI', 'Program Development', 'Operations', 'Project Management', 'Community Engagement', 'Volunteer Management', 'Events', 'Advocacy', 'Other']
    contributions = ['Fundraising / Resource Development', 'Marketing & Communications', 'Programs & Impact', 'Partnerships', 'Finance', 'Governance / Board Development', 'Strategic Planning', 'Technology', 'Volunteer Development', 'Community Engagement', 'Operations', 'Board Recruitment', 'Other']
    availability = ['Less than 2 hours', '2–4 hours', '5–8 hours', '9–12 hours', '12+ hours']
    def q(key, prompt, choices=None, required=True, when=None, multi=False):
        return {'id': key, 'prompt': prompt, 'type': 'multi' if multi else ('choice' if choices else 'long'), 'options': choices or [], 'required': required, **({'when': when} if when else {})}
    return [
        q('recommitment', 'Which path best reflects how you want to move forward?', [active, advisory, step_down]),
        q('why_joined', f'Why do you want to continue serving on the Board of {organization}?', when=[active]),
        q('expertise', 'What professional skills, experience or expertise can you bring?', expertise, when=[active], multi=True),
        q('expertise_other', 'Other expertise', required=False, when=[active]),
        q('participation_barriers', 'What has made it difficult for you to participate as actively as you would like?', when=[active]),
        q('contribution_interests', 'Where would you most like to contribute moving forward? Select up to 3.', contributions, when=[active, advisory], multi=True),
        q('ownership_area', 'What area are you willing to take greater responsibility for?', when=[active]),
        q('leadership_interest', 'Are you ready to take on a leadership or committee responsibility?', ['Yes', 'I would like to discuss this'], when=[active]),
        q('leadership_area', 'What responsibility would you be interested in leading?', required=False, when=[active]),
        q('strengths_resources', 'What skills, relationships, resources or strengths can you bring to the Board?', when=[active, advisory]),
        q('monthly_availability', 'How much time can you realistically give each month?', availability, when=[active, advisory]),
        q('experience_improvement', 'What can the organization do to help you contribute effectively?', when=[active]),
        q('decision_reason', 'Please tell us why this role or decision fits you now.', when=[advisory, step_down]),
        q('anything_else', 'Is there anything else you would like the Founder or Board leadership to know?', required=False),
    ]


RECOMMIT_ACTIVE = "I am ready to recommit, remain an active Board Member and step up in my role."
RECOMMIT_ADVISORY = "I would like to transition into an Advisory Board role."
RECOMMIT_STEP_DOWN = "I would like to step down from the Board."
RECOMMITMENT_OPTIONS = [RECOMMIT_ACTIVE, RECOMMIT_ADVISORY, RECOMMIT_STEP_DOWN]


def validate_recommitment(payload, variant: str = "full") -> None:
    from fastapi import HTTPException
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
