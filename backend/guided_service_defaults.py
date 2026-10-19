"""Independent defaults for Rooney's guided services, using stable question keys."""
from copy import deepcopy

PRICES = {"recruitment": 49700, "board-recommitment": 49700, "strategic-planning": 199700}
NAMES = {"recruitment": "Board Recruitment", "board-recommitment": "Board Recommitment", "strategic-planning": "Strategic Planning"}
PRODUCTS = {key: "rooney_guided_" + key.replace("-", "_") + "_" + str(value // 100) for key, value in PRICES.items()}
# Parts Three and Four activate their public funnels only after their own verification.
ACTIVE_SERVICES = {"recruitment", "board-recommitment"}
FLOW_VERSION = "founder-guided-2026"

def question(key, prompt, help="", required=True, kind="textarea", **extra):
    return {"id": key, "key": key, "prompt": prompt, "help": help, "required": required, "type": kind, "options": [], "archived": False, **extra}

RECRUITMENT_QUESTIONS = [
    question("mission", "What is your organization's mission?", "Who do you serve, and what change are you working to create?"),
    question("current_board", "Who is presently on your board, and how does each person help the organization?", "Include their expertise, relationships and actual contributions. If you have no board yet, tell us."),
    question("desired_board_members", "What kind of people do you believe your organization should recruit to the board?", "Share the expertise, relationships and contributions you already have in mind."),
    question("board_type", "What is happening in your organization, and what do you want your board to help accomplish next?", "Explain your present situation and priorities in your own words."),
    question("support_needs", "In which areas does your organization need the board's support most?", "Consider leadership, fundraising, governance, operations, partnerships or other needs."),
    question("why_join", "What skills, experience, relationships or capabilities do you already have, and what is still missing?", "Include support available beyond your current board so we avoid duplicating it."),
    question("desired_count", "How many new board members would you like to recruit?", "Enter a number, or tell us if you are not sure yet.", kind="text"),
]
RECOMMITMENT_QUESTIONS = [
    question("mission", "What is your organization's mission?"),
    question("why_recommit", "Why do you believe your board members need to recommit to your organization at this time?"),
    question("board_help_accomplish", "What do you want your board members to start doing or contributing after recommitting?"),
    question("board_count", "How many board members are currently serving, and how many would you like to involve in the recommitment process?"),
]

def email(subject, body, cta="CONTINUE WITH {{service_name}}", **extra):
    return {"subject": subject, "headline": "", "body": body, "cta": cta, "support": "", "signature": "Rooney Akpesiri\nNonprofit Board Builder", "enabled": True, **extra}

FIRST = {
    "recruitment": email("Let's Get Your Board Recruitment Campaign Launched", """Hello {{first_name}},

Thank you for sharing the information about {{organization}} and the board members your organization needs.

{{recommendation_update}}

The next step is to work through these recommendations together and launch your recruitment campaign.

During our guided recruitment session, we'll review the board member profiles identified for your organization and agree on the exact people you want to recruit.

We'll then prepare the recruitment materials your organization needs and launch your board recruitment campaign.

By the end of our session, your recruitment campaign can be live, with the tools and resources you need to continue attracting and reviewing applicants.

You'll also have access to your recruitment applications, applicant notifications, interview materials, and board onboarding resources.

The complete guided board recruitment service costs $497.""", "PAY $497 AND LAUNCH MY BOARD RECRUITMENT", delay_minutes=60),
    "board-recommitment": email("Let's Get Your Board Members Recommitted and Ready to Step Up", """Hello {{first_name}},

Thank you for sharing what is happening with your board at {{organization}}.

You've explained why you want your board members to recommit and what you need them to begin contributing to your organization.

The next step is to begin the recommitment process.

I'd like us to meet so we can review your situation, prepare the communication and recommitment forms your board members will receive, and begin helping each person decide how they want to move forward.

Our goal is to help you get clear commitments from the board members who are ready to continue, understand where others may need a different role, and begin putting the right responsibilities in place.

During our session, we'll prepare the resources you need and begin inviting your board members to respond.

As responses come in, you'll have the tools to understand each person's position, follow up with them, and move towards a board that is ready to contribute to your organization.

The complete guided Board Recommitment service costs $497.""", "PAY $497 AND START MY BOARD RECOMMITMENT", delay_minutes=60),
    "strategic-planning": email("Let's Develop Your Organization's Strategic Plan", "Hello {{first_name}},\n\nThank you for sharing what {{organization}} needs. We can work with you and your board to discuss your priorities and adopt a strategic plan.\n\nThe guided Strategic Planning service costs $1,997.", "CONTINUE MY STRATEGIC PLANNING", delay_minutes=60),
}
FOLLOWUP_THEMES = {
    "recruitment": [
        ("The board support your organization needs", "You described the support your board needs. Our guided session will help you agree on the people to recruit and launch a campaign to reach them."),
        ("Give the right people a clear invitation", "A clear board opportunity helps suitable people understand how they can contribute. We can prepare that opportunity with you and get your campaign launched."),
        ("Move from board needs to an active campaign", "You do not need to work through recruitment alone. We will review the recommended profiles together and prepare the materials and application process."),
        ("Keep recruiting after our session", "You will leave with a published opportunity, an application link and the resources to review applicants and continue recruitment independently."),
        ("Your invitation to launch your recruitment campaign", "If you are ready to move forward, your saved recruitment information is waiting. Use your link to begin the $497 guided service."),
    ],
    "board-recommitment": [
        ("When attending meetings is not enough", "Your organization needs contributions as well as attendance. A guided recommitment process can help your board members clarify how they intend to participate."),
        ("Who is ready to take responsibility?", "Knowing which board members are willing to contribute helps you plan with greater clarity. We can help you begin those conversations."),
        ("Step up, change roles or step aside", "A respectful recommitment process gives each member a way to explain what fits them now, without assuming everyone will choose the same path."),
        ("Know what each member is willing to contribute", "Clear commitments give you a practical basis for moving forward. We will help you prepare the forms, communications and follow-up resources."),
        ("Your invitation to begin board recommitment", "If you are ready to clarify your board's involvement, use your saved link to begin the $497 guided recommitment service."),
    ],
    "strategic-planning": [("Bring your board into planning", "We can help your organization agree on its direction and the priorities your board will adopt.")] * 5,
}

def defaults(service):
    from strategic_questionnaire import QUESTIONS
    entry = RECRUITMENT_QUESTIONS if service == "recruitment" else RECOMMITMENT_QUESTIONS if service == "board-recommitment" else [question("mission", "What is your organization's mission?"), question("priorities", "What do you want your organization to accomplish over the next 12 to 24 months?")]
    groups = {"entry": deepcopy(entry)}
    if service == "strategic-planning":
        groups.update({name: [question(q["key"], q["prompt"], q.get("help", "")) for q in QUESTIONS] for name in ("leader", "board")})
    result = {"question_groups": groups, "first_email": deepcopy(FIRST[service]),
        "followups": [email(subject, "Hello {{first_name}},\n\n" + body + "\n\nYour information for {{organization}} remains saved.", after_previous_minutes=4320) for subject, body in FOLLOWUP_THEMES[service]],
        "sequence_paused": False,
        "video_email": email("I Recorded a Video for You About Your {{service_name}}", "Hello {{first_name}},\n\nI've recorded a short video for you about the information you shared regarding {{organization}}.\n\nYou can watch your video using the link below.\n\n{{continuation_message}}"),
        "booking_url": "https://calendly.com/boardbuilder/recruitboard",
        "paid_email": email("Your {{service_name}} Payment Is Confirmed", "Hello {{first_name}},\n\nYour payment is confirmed. Use your secure link to upload your organization's logo and choose its colors. You can then book your guided session with Rooney. You can return through this link without paying again.", "CONTINUE TO BRANDING AND BOOKING"),
        "delivery_email": email("Your {{service_name}} Resources", "Hello {{first_name}},\n\nYour approved resources for {{organization}} are available through your secure link. You can review and download them whenever you need them.\n\nUse the materials to continue the process with your organization. Recruitment customers can share their published campaign and application link, then review applicants and prepare interviews from the same resources page.", "OPEN MY APPROVED RESOURCES"),
        "operational_emails": {
            "application_notice": email("You Have a New Board Applicant", "Hello {{first_name}},\n\n{{applicant_name}} has submitted a board application for {{organization}}. Open your secure link to review the application and any supporting CV, prepare an interview guide, and decide on the next step.", "VIEW APPLICATION"),
            "interview_invite": email("An Invitation to Discuss Your Board Application", "Hello {{applicant_name}},\n\nThank you for your interest in serving on the board of {{organization}}. We would like to invite you to a conversation about the board opportunity and the contribution you would like to make.\n\n{{interview_details}}", "VIEW BOARD OPPORTUNITY"),
            "applicant_reject": email("Your Board Application", "Hello {{applicant_name}},\n\nThank you for your interest in supporting {{organization}} and for taking the time to apply. We will not be inviting you to interview for this opportunity. We appreciate your willingness to contribute and wish you well.", "VIEW BOARD OPPORTUNITY"),
            "board_invitation": email("Please Share Your Board Recommitment Decision", "Hello {{participant_name}},\n\n{{leader_name}} invites you to reflect on your continued involvement with {{organization}}.\n\n{{agreed_purpose}}\n\nPlease use your personal form link to tell us whether you would like to recommit, discuss another role, or step down. Explain your decision in your own words. We will review your response and discuss the way forward with you.", "COMPLETE MY RECOMMITMENT FORM"),
            "response_notice": email("A Board Member Has Completed Their Recommitment Form", "Hello {{first_name}},\n\n{{participant_name}} has shared their recommitment response for {{organization}}. You can review what they said through your secure link. Their stated preference is a starting point for discussion, rather than an automatic change to their board role.", "REVIEW RESPONSE"),
            "conversation_invite": email("Let's Discuss Your Board Involvement", "Hello {{participant_name}},\n\nThank you for sharing your thoughts about your continued involvement with {{organization}}. We would like to arrange a conversation to explore your concerns, expectations and possible contribution. Please reply so we can agree on a suitable time.", "VIEW YOUR RECOMMITMENT FORM"),
            "active_confirmation": email("Your Agreed Board Contribution", "Hello {{participant_name}},\n\nThank you for confirming how you will continue supporting {{organization}}.\n\n{{responsibilities}}\n\nYour approved resources are available through the link below.", "OPEN MY RESOURCES"),
            "alternative_discussion": email("Your Proposed Alternative Role", "Hello {{participant_name}},\n\nThank you for explaining the way you would like to support {{organization}}. We would like to discuss whether this proposed role meets your needs and the organization's priorities. No change to your formal board position has been made automatically.", "VIEW YOUR RECOMMITMENT FORM"),
            "step_down_acknowledgement": email("Acknowledging Your Board Service", "Hello {{participant_name}},\n\nThank you for your service to {{organization}}. Following our discussion and the appropriate organizational decisions, we acknowledge the agreed end of your board role.\n\n{{responsibilities}}\n\nWe appreciate your contribution and the opportunity to stay connected.", "VIEW YOUR RECOMMITMENT FORM"),
            "portfolio_delivery": email("Your Approved Board Member Portfolio", "Hello {{participant_name}},\n\nYour approved portfolio for {{organization}} sets out the role, responsibilities and next steps you have agreed. Please review it through your secure link and keep a copy for your work with the organization.", "OPEN MY APPROVED PORTFOLIO"),
        },
        "landing": {"headline": "Launch Your Board Recruitment Campaign in 30 Minutes." if service == "recruitment" else "Get Your Board Members to Recommit and Step Up", "description": "Start for free by telling us about your board. During your $497 guided session, Rooney will help you agree on the people to recruit, prepare your materials and launch your campaign when the necessary information and approvals are ready." if service == "recruitment" else "Help your present board members decide how they will contribute to your organization's future, clarify their responsibilities, and begin taking action to support your mission.", "cta": "START BOARD RECRUITMENT FOR FREE" if service == "recruitment" else "START MY BOARD RECOMMITMENT FOR FREE"}}

    if service == "board-recommitment":
        from guided_recommitment import participant_defaults
        result["participant_form"] = participant_defaults()
        result["delivery_email"]["body"] = "Hello {{first_name}},\n\nYour approved Board Recommitment resources for {{organization}} are ready. Use your secure link to review the board members' responses, retrieve approved conversation guides and portfolios, and continue the process with your organization. Record final arrangements only after the appropriate conversations and organizational decisions."
        result["operational_emails"]["active_confirmation"]["body"] = "Hello {{participant_name}},\n\nThank you for confirming how you will continue supporting {{organization}}.\n\n{{responsibilities}}\n\nYour organization will share your approved portfolio and any further resources separately."
        result["operational_emails"]["active_confirmation"]["cta"] = "VIEW MY RECOMMITMENT FORM"
    return result
