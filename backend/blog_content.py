"""The five blog pathways. Each angle joins one pain, belief and desired outcome.

Legacy topic libraries remain untouched. These briefs are saved with each draft so
the administrator can see the thinking used to write it.
"""
BLOG_BRIEF_VERSION = 1


def angle(key, title, pain, belief, outcome):
    return dict(topic_id=key, topic_title=title, pain_point=pain, limiting_belief=belief, desired_outcome=outcome)


BLOG_CATEGORIES = {
    "recruitment": {
        "name": "Board Recruitment", "day": 0, "publish_day": "Monday",
        "audience": "Nonprofit founders and executive directors who need capable, committed board members.",
        "mechanism": "Identify the board mix the organization needs now, attract applicants with a leadership opportunity, assess alignment and bring selected people through clear onboarding.",
        "cta_label": "Ready to recruit the board members your organization needs?",
        "cta_button": "Start Building Your Board", "cta_url": "/recruit", "accent": "#818cf8",
        "angles": [
            angle("right-mix", "Recruit the Board Your Organization Needs at This Stage", "The founder carries responsibilities the present board cannot help with.", "Any willing person will help if we can fill the vacant seats.", "A deliberate mix of people whose experience and commitment help move the organization forward."),
            angle("beyond-friends", "Find Board Members Beyond the People You Already Know", "Recruitment stalls after asking the same friends and contacts.", "Good board members only come through a founder's personal network.", "An active recruitment campaign that reaches professionals who connect with the mission."),
            angle("fundraising-experience", "Recruit Board Members Who Can Help You Build Fundraising Capacity", "The founder needs fundraising support and keeps searching for one person to carry everything.", "Recruiting a wealthy person or fundraising expert will solve every funding problem.", "Board leaders who contribute experience, relationships and strategic support to a shared fundraising direction."),
            angle("leadership-invitation", "Give Capable Professionals a Reason to Join Your Board", "The recruitment post attracts few suitable applicants.", "People should join simply because the cause is good or the organization needs help.", "A clear leadership invitation that shows the mission, next phase and contribution the board can make."),
            angle("alignment", "Find Out How a Board Candidate Really Wants to Contribute", "Impressive resumes lead to appointments that do not become active participation.", "A strong job title proves someone will be the right board member.", "Rich conversations that reveal the person's mindset, alignment and intended contribution before appointment."),
            angle("start-serving", "Help New Board Members Begin With Clear Responsibility", "New members accept an appointment and then wait to be told what to do.", "Once someone agrees to join, they automatically understand what serving means.", "New members who understand the organization and the responsibilities they have accepted through proper onboarding."),
        ],
    },
    "fundraising_activation": {
        "name": "Board Fundraising", "day": 1, "publish_day": "Tuesday",
        "audience": "Nonprofit founders and executive directors carrying fundraising while their board stays on the sidelines.",
        "mechanism": "The Board Fundraising Game lets members contribute their own ideas about who to raise from, where to find them, how to attract them and how to raise money. Build and adopt a shared plan with responsibilities aligned to each member.",
        "cta_label": "Ready to get your board involved in fundraising?",
        "cta_button": "Explore the Board Fundraising Game", "cta_url": "/board-fundraising-game", "accent": "#a78bfa",
        "angles": [
            angle("shared-plan", "Get Your Board Involved in Building the Fundraising Plan", "The founder writes the plan and struggles to get board members to act on it.", "The leader must work out the strategy first and then convince the board to execute it.", "A board that helps shape the fundraising direction and understands its part in carrying it forward."),
            angle("own-contribution", "Let Your Board Members Tell You How They Can Support Fundraising", "Repeated requests to raise money produce avoidance and discomfort.", "Every board member has to support fundraising in the same way.", "Members choosing useful contributions that fit their strengths, relationships and willingness to participate."),
            angle("beyond-training", "Turn Your Board's Fundraising Ideas Into Commitments", "Members attend another fundraising training but still take little action.", "One more training session will create the ownership the board is missing.", "An agreed fundraising plan that gives members specific responsibilities they helped choose."),
            angle("relationships", "Help Your Board See the Fundraising Value of Its Relationships", "Board members say they do not know anyone rich enough to help.", "Only wealthy contacts can make a board member useful to fundraising.", "Members recognizing suitable individuals, businesses and grantors they can help the organization reach."),
            angle("meeting-action", "Make Your Next Board Meeting the Start of Fundraising Action", "Fundraising is discussed at meetings without anybody taking the next step.", "A shared fundraising target is enough to tell everyone what they should do.", "A practical direction with named responsibilities and next actions that members understand."),
            angle("shared-load", "Build a Board That Helps You Carry the Fundraising", "The founder feels alone with every fundraising decision and follow-up.", "If the founder stops doing everything, fundraising will stop.", "Board members owning agreed parts of the work so the organization has broader fundraising participation."),
        ],
    },
    "strategic_planning": {
        "name": "Strategic Planning", "day": 2, "publish_day": "Wednesday",
        "audience": "Nonprofit founders and executive directors who need their board to agree on direction and help execute it.",
        "mechanism": "Collect the leader's and board members' original ideas, deliberate together, adopt a realistic direction, develop a useful plan and assign responsibilities through delegation.",
        "cta_label": "Ready to build a plan your board can help execute?",
        "cta_button": "Start Strategic Planning With Your Board", "cta_url": "/strategic-planning", "accent": "#60a5fa",
        "angles": [
            angle("plan-ownership", "Build a Strategic Plan Your Board Has a Reason to Own", "An approved plan sits untouched while the founder keeps carrying the work.", "Board approval of a document means members are ready to execute it.", "A plan members helped build, with clear responsibilities they understand and accept."),
            angle("one-direction", "Give Your Board a Shared Direction for the Next Phase", "Every meeting introduces new priorities and the organization keeps changing direction.", "Agreeing with every good idea is how a leader keeps the board engaged.", "An adopted set of priorities that guides decisions and keeps the organization focused."),
            angle("original-ideas", "Use the Thinking Already Sitting Around Your Board Table", "Useful board experience remains silent while one person writes the strategy.", "A good plan must come from the founder or an outside expert.", "A shared plan built from the actual knowledge and ideas of the people responsible for the organization."),
            angle("real-capacity", "Build a Strategic Plan Your Organization Can Carry", "Ambitious goals leave the team overwhelmed and unsure where to begin.", "A serious strategy must promise more activity than the organization can currently manage.", "A clear direction that connects desired results to capacity, resources and realistic responsibilities."),
            angle("delegation", "Help Your Board Leave Strategic Planning Knowing What It Owns", "People agree with the plan but wait for the founder to assign every next action.", "Once the plan is written, responsibility will naturally sort itself out.", "Members leaving the process with agreed roles and useful portfolios for their contributions."),
            angle("usable-plan", "Make Your Strategic Plan Useful Between Board Meetings", "The strategy sounds impressive but does not guide everyday choices.", "Professional planning requires language so formal that only experts can interpret it.", "A plain-language plan that explains the direction well enough for members to act on it."),
        ],
    },
    "reactivation": {
        "name": "Board Recommitment", "day": 3, "publish_day": "Thursday",
        "audience": "Nonprofit founders and executive directors whose existing board members are disengaged or unclear about their contribution.",
        "mechanism": "Invite individual recommitment, understand members' own responses, hold informed conversations and help continuing members accept clear responsibilities, followed by onboarding and portfolios.",
        "cta_label": "Ready to get your board members building with you again?",
        "cta_button": "Start the Board Recommitment Process", "cta_url": "/board-recommitment", "accent": "#c084fc",
        "angles": [
            angle("willing-capable", "Find Out Who Is Ready to Recommit to Your Board", "The founder cannot tell who still has the willingness and capacity to serve.", "Remaining on the board list means a person is still committed.", "Clarity about who is ready to contribute and what each person can realistically take on."),
            angle("respectful-conversation", "Have the Board Conversation You Have Been Putting Off", "The leader avoids discussing inactivity because personal relationships are involved.", "Asking someone to clarify their commitment will damage the relationship.", "A respectful conversation grounded in the member's own responses and the organization's needs."),
            angle("real-responsibility", "Give Recommitted Board Members Something Clear to Own", "Members promise to become more active but participation remains vague.", "A renewed promise to support the mission is specific enough to change behavior.", "An agreed contribution with clear responsibilities the member can act on."),
            angle("understand-disengagement", "Understand Why Your Board Stopped Participating", "Reminders and meeting invitations produce little response.", "Inactive members are all disengaged for the same reason.", "A clearer understanding of each member's situation so the next conversation addresses the actual barrier."),
            angle("room-to-step-forward", "Give Your Present Board a Clear Opportunity to Step Forward", "The founder assumes every inactive member has to be replaced immediately.", "There is no useful contribution left in the people already on the board.", "A fair opportunity for willing members to recommit with renewed direction and responsibility."),
            angle("follow-through", "Carry Board Recommitment Into the Work After the Meeting", "A promising recommitment meeting fades without any change in the work.", "The conversation alone completes the recommitment process.", "Members supported by onboarding, clear portfolios and a next meeting focused on their agreed work."),
        ],
    },
    "board_applicant_network": {
        "name": "Joining Nonprofit Boards", "day": 4, "publish_day": "Friday",
        "audience": "Professionals and people interested in serving on a nonprofit board. Speak to the prospective applicant directly, not to an organization recruiting members.",
        "mechanism": "Join the Board Applicant Network, share professional experience, causes and contribution interests, and become available for consideration by nonprofits recruiting board members. Board appointments depend on the organization's selection process.",
        "cta_label": "Ready to put your experience to work on a nonprofit board?",
        "cta_button": "Join the Board Applicant Network", "cta_url": "/join-a-board", "accent": "#67e8f9",
        "angles": [
            angle("first-board", "Your Professional Experience Can Be Useful on a Nonprofit Board", "You want meaningful board service but assume your background is not impressive enough.", "Only chief executives and wealthy people belong on nonprofit boards.", "Recognizing the leadership value of your experience and putting yourself forward for suitable opportunities."),
            angle("find-opportunities", "Make Yourself Visible to Nonprofits Looking for Board Members", "You want to serve but do not know which organizations are recruiting.", "You have to know the founder personally before you can be considered for a board.", "A profile in the Board Applicant Network that helps nonprofits understand your interests and possible contribution."),
            angle("mission-fit", "Find a Nonprofit Mission You Want to Help Carry", "You want to contribute but worry about accepting a role that has little connection to your values.", "You should accept the first board invitation because another may never come.", "A thoughtful search for board service aligned with the causes you care about and the contribution you want to make."),
            angle("first-experience", "Put Yourself Forward for Your First Nonprofit Board Role", "You hesitate because every opportunity seems to be for people with board experience.", "You must already have served on a board before your skills will be useful to one.", "A clear account of your transferable experience that helps an organization consider your potential contribution."),
            angle("contribution", "Explain the Contribution You Want to Make as a Board Member", "Your profile lists job titles without showing how an organization could benefit from your involvement.", "A resume will explain your interest and contribution for you.", "A board applicant profile that connects your experience, causes and intended support."),
            angle("meaningful-service", "Turn Your Interest in a Cause Into Meaningful Board Service", "You care about a cause and want a deeper way to support it.", "Giving money or volunteering for occasional activities are the only ways to contribute.", "Exploring board service as a way to contribute leadership and professional judgment to a mission you value."),
        ],
    },
}

LEGACY_BLOG_CATEGORIES = {
    "transformation": {"name": "Board Leadership", "cta_label": "Build a board that helps carry your mission.", "cta_button": "Explore Our Board Services", "cta_url": "/"},
    "weekly": {"name": "Nonprofit Board Leadership", "cta_label": "Build a board that helps carry your mission.", "cta_button": "Explore Our Board Services", "cta_url": "/"},
}
