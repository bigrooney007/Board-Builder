"""Independent defaults for Rooney's guided services, using stable question keys."""
from copy import deepcopy

PRICES = {"recruitment": 49700, "board-recommitment": 49700, "strategic-planning": 199700, "board-fundraising": 149700}
NAMES = {"recruitment": "Board Recruitment", "board-recommitment": "Board Recommitment", "strategic-planning": "Strategic Planning", "board-fundraising": "Board Fundraising"}
PRODUCTS = {key: "rooney_guided_" + key.replace("-", "_") + "_" + str(value // 100) for key, value in PRICES.items()}
# Parts Three and Four activate their public funnels only after their own verification.
ACTIVE_SERVICES = set(NAMES)
FLOW_VERSION = "founder-guided-2026"

# Existing professional purchase identifiers stay valid; new self-facilitation
# purchases have their own SKU and operator entitlement.
PACKAGES = {service: {
    "self-facilitated": {"amount": 49700, "product": "rooney_guided_" + service.replace("-", "_") + "_self_497", "name": "Guided Setup and Self-Facilitation"},
    "rooney-facilitated": {"amount": PRICES[service], "product": PRODUCTS[service], "name": "Rooney-Facilitated " + NAMES[service]},
} for service in ("board-fundraising", "strategic-planning")}


def package(service, key=None):
    key = key or "rooney-facilitated"
    if service in PACKAGES:
        if key not in PACKAGES[service]:
            raise ValueError("Choose a valid service option.")
        return {"key": key, **PACKAGES[service][key]}
    return {"key": "guided", "amount": PRICES[service], "product": PRODUCTS[service], "name": "Guided " + NAMES[service]}

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
PLANNING_ENTRY = [
    question("vision", "Where do you see your organization in the next 12 to 24 months?", "Imagine that your organization has become successful according to your own expectations. What should it look like, and what should it be accomplishing?"),
    question("goals", "What goals do you believe your organization needs to achieve to reach that destination?", "Describe the major things your organization must accomplish over the next 12 to 24 months."),
    question("requirements", "What do you believe your organization will need to achieve these goals?", "Think about the people, funding, programs, partnerships, technology, equipment, properties, infrastructure or other resources that may be necessary."),
]

FUNDRAISING_ENTRY = [
    question("mission", "What is your organization's mission?", "Use your existing mission statement."),
    question("board_size", "How many board members does your organization currently have?", "Enter the number of people currently serving on your board.", kind="number"),
    question("fundraising_goal", "How much money is your organization looking to raise?", "Enter your fundraising goal in US dollars.", kind="number"),
    question("fundraising_deadline", "When does your organization need to raise this money?", "Choose the date by which your organization needs the funding.", kind="date"),
    question("funding_consequences", "What will happen if your organization doesn't raise the money it needs?", "Explain what this would mean for your organization, its programs or the people you serve."),
    question("next_board_meeting", "When is your organization's next board meeting?", "Enter the meeting date, start time and time zone.", kind="meeting"),
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
    "strategic-planning": email("Let's Get Your Board Working Together to Build Your Organization", """Hello {{first_name}},

Thank you for sharing your vision for {{organization}} and what you would like your organization to achieve over the next 12 to 24 months.

You have a picture of where you want your organization to go. The next step is to bring your board members into the process so you can begin developing that future together.

I'd like us to meet and prepare your organization for a guided strategic planning process. We'll start by helping you and your board members share your ideas about the organization's future, the goals it should pursue, the programs it should strengthen, and the resources and people it will need.

Then I'll facilitate your board's strategic planning session, where we'll review everyone's contributions, discuss the available ideas, and agree on the direction your organization should take.

We'll use those agreed decisions to develop your organization's strategic plan, which you and your board members can review and adopt.

The goal is to help your organization leave the process with a plan that reflects the thinking and agreement of the people responsible for helping you carry it out.

Our professionally facilitated Strategic Planning service costs $1,997.""", "PAY $1,997 AND START OUR STRATEGIC PLANNING", delay_minutes=60),
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
    "strategic-planning": [
        ("Does your board share your vision?", "You have described the future you want for your organization. Bringing your board into the planning process helps you explore that direction together."),
        ("Involve the people who will help carry out your plan", "A plan is easier to use when the people responsible have helped develop it. Our facilitated process gives each board member space to contribute before you agree on priorities."),
        ("Agree on priorities before deciding what you need", "Your goals should guide the people, funding and technology you seek. We will help your board connect those needs to its agreed direction."),
        ("Turn individual ideas into agreed priorities", "Your board members may have different ideas about the future. A facilitated session helps you discuss those ideas and record the decisions your organization actually adopts."),
        ("Your invitation to begin strategic planning", "If you are ready to bring your board into planning, your answers remain saved. Use your personal link to begin the $1,997 professionally facilitated service."),
    ],
}

def defaults(service):
    from strategic_questionnaire import QUESTIONS
    entry = RECRUITMENT_QUESTIONS if service == "recruitment" else RECOMMITMENT_QUESTIONS if service == "board-recommitment" else FUNDRAISING_ENTRY if service == "board-fundraising" else PLANNING_ENTRY
    groups = {"entry": deepcopy(entry)}
    if service == "strategic-planning":
        from guided_planning import planning_questions
        groups.update({name: planning_questions(name, QUESTIONS) for name in ("leader", "board")})
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
        result["landing"].update({"processHeading":"Begin a Guided Recommitment Process", "promise":"Understand who is ready to contribute, what they can commit to, and which conversations your organization needs to have.", "deliverablesHeading":"The Forms, Guidance and Resources to Continue Independently", "finalHeading":"Ready to Clarify Your Board's Commitment?", "steps":[["1","Start for Free","Answer the introductory questions about your board and the contributions your organization needs."],["2","Receive Your Personal Invitation","We will email your next steps. The guided service costs $497, with branding and session booking after payment."],["3","Prepare the Process With Rooney","Clarify your expectations, prepare the communications and invite your board members to respond."],["4","Review Each Person's Decision","Members can recommit, propose another role or explain why they need to step down. Their response does not automatically change their formal role."],["5","Agree on the Way Forward","Use the conversation guidance, approved responsibilities, portfolios and other resources to continue the process with your organization."]], "outcomes":["Personal recommitment invitations and forms","Saved board member responses","Response interpretation and conversation guides","Confirmed outcomes kept separate from initial preferences","Approved responsibilities, portfolios and relevant agreements"]})
    if service == "strategic-planning":
        result["landing"] = {"headline":"Get Your Board Members Working Together to Build Your Organization", "description":"Bring your board members together to agree on where your organization should be in the next 12 to 24 months, develop a strategic plan, and begin taking responsibility for moving the organization forward.", "cta":"START MY STRATEGIC PLANNING FOR FREE"}
        result["landing"].update({"processHeading":"Build Your Plan Through a Facilitated Board Process", "promise":"Bring everyone's original ideas into the discussion and build the plan from the decisions your organization actually adopts.", "deliverablesHeading":"A Strategic Plan Your Board Has Helped Develop", "finalHeading":"Ready to Bring Your Board Into Strategic Planning?", "steps":[["1","Share Your Initial Thinking for Free","Tell us about your vision, goals and the resources your organization may need. Your introductory answers are saved."],["2","Begin the Facilitated Service","Your personal invitation explains the $1,997 service. After payment, provide your branding and book an initial meeting with Rooney."],["3","Invite Independent Contributions","Prepare separate planning forms for the leader and board members. Review each existing program individually."],["4","Discuss and Record Agreed Decisions","Rooney facilitates the board session, moving through each subject and program while recording adopted ideas, agreed responsibilities and outstanding decisions."],["5","Review and Adopt the Plan","Rooney prepares and edits the draft. Each participant reviews the released version, adopts it or requests a change."],["6","Receive Your Approved Plan","After the required approvals, download and share the branded strategic plan. Your organization carries out the agreed work independently."]], "outcomes":["Independent leader and board member contributions","Individual discussion of each program","Recorded adopted decisions and meeting notes","An editable, branded strategic plan","Version-specific board review and adoption","Secure access to the final approved plan"]})
        result["delivery_email"] = email("Your Approved Strategic Plan", "Hello {{first_name}},\n\nYour approved strategic plan for {{organization}} is ready. Use your secure link to read and download it, and share the approved version with your authorized board members. The plan records the decisions adopted during your facilitated process and the responsibilities that were confirmed.", "OPEN MY STRATEGIC PLAN")
        result["operational_emails"] = {
            "planning_invitation": email("Your Invitation to Help Plan {{organization}}'s Future", "Hello {{participant_name}},\n\n{{leader_name}} invites you to contribute to {{organization}}'s strategic planning process.\n\nPlanning period: {{planning_period}}.\nBoard meeting: {{meeting_details}}.\nPlease complete your form by {{response_deadline}}.\n\nShare your own ideas freely. You will not see other people's private responses while completing your form. We will discuss the contributions together during the planning meeting.", "COMPLETE MY PLANNING FORM"),
            "response_notice": email("A Board Member Has Completed the Strategic Planning Form", "Hello {{first_name}},\n\n{{participant_name}} has submitted their ideas for {{organization}}. You can review their original responses before your upcoming planning meeting through your secure link.", "VIEW RESPONSE"),
            "review_invitation": email("Please Review Your Organization's Strategic Plan", "Hello {{participant_name}},\n\nRooney has prepared the strategic plan for {{organization}} from the decisions recorded during your planning session. Please read the released review version and either adopt it or request a change. Your decision will be recorded against this specific version. Individual adoption does not replace your organization's formal governance requirements.", "REVIEW AND ADOPT THE PLAN"),
        }
    result["operational_emails"].update({
        "access_recovery":email("Your {{service_name}} Access Link", "Hello {{first_name}},\n\nYour paid service for {{organization}} remains available. Use your secure link to return to branding and booking. Your approved resources are also available below.", "CONTINUE MY PAID SERVICE"),
        "signature_invitation":email("Please Review and Sign Your Board Agreement", "Please review the document reflecting your agreed role and responsibilities with {{organization}}. Sign if it correctly records your agreement. A finalized copy will remain available after signing.", "REVIEW MY AGREEMENT"),
        "signature_completed":email("A Board Agreement Has Been Signed", "Hello {{first_name}},\n\nA board agreement for {{organization}} has been signed. Use your secure resources link to retrieve the finalized document.", "OPEN SIGNED AGREEMENT"),
        "signed_copy":email("Your Board Agreement Is Signed", "Hello {{participant_name}},\n\nYour signature on the agreed document for {{organization}} has been recorded. You can retrieve the finalized agreement using your secure link.", "OPEN MY SIGNED AGREEMENT"),
        "profile_response_notice":email("A Board Member Has Completed Their Profile", "Hello {{first_name}},\n\nA board member has completed their profile for {{organization}}. Open your secure resources to review their information before agreeing on responsibilities.", "REVIEW BOARD MEMBER PROFILE"),
        "board_profile_invitation":email("Please Complete Your Board Member Profile", "Please share your skills, interests, availability and the contribution you would like to make to {{organization}}. The organization will discuss and confirm responsibilities with you. Completing this form does not appoint you to the board.", "COMPLETE MY BOARD MEMBER PROFILE"),
        "interview_guide_ready":email("Your Applicant Interview Guide Is Ready", "Hello {{first_name}},\n\nYour interview guide for a board applicant is ready. Use your secure resources link to review it and prepare for the conversation.", "OPEN INTERVIEW GUIDE"),
        "campaign_launched":email("Your Board Recruitment Campaign Is Published", "Hello {{first_name}},\n\nYour approved opportunity for {{organization}} is published on Nonprofit Board Builder and its application form is ready. Open your resources to copy your campaign link and promotional materials. The actual applicant-network delivery status is shown with your campaign. Share through your own channels to publish elsewhere.", "OPEN MY RECRUITMENT CAMPAIGN"),
        "conversation_guide_approved":email("Your Approved Conversation Guide", "Hello {{first_name}},\n\nYour approved conversation guide for {{organization}} is saved with your resources. Use it to explore the board member's stated views respectfully and record what you agree together.", "OPEN APPROVED CONVERSATION GUIDE"),
    })
    return result


# Extend the existing independent configuration, retaining every admin edit.
_original_defaults = defaults

def defaults(service):
    if service == "board-fundraising":
        result = _original_defaults("recruitment")
        result["question_groups"] = {"entry": deepcopy(FUNDRAISING_ENTRY)}
        result["landing"] = {"headline": "Get Your Board Members Fundraising by Your Next Board Meeting", "description": "Bring your board together to develop a fundraising approach they understand and can help carry out.", "cta": "START MY BOARD FUNDRAISING FOR FREE"}
        result["first_email"] = email("Let's Get Your Board Members Raising Money Together", """Hello {{first_name}},

Thank you for telling us about {{organization}}, your fundraising goal and the board members you want to involve. Your goal is {{fundraising_goal}}, with funding needed by {{fundraising_deadline}}.

We'll begin with a preparation meeting. We'll guide you through the existing fundraising questions: who should fund your mission and why, where to find them, how to attract their interest, how to develop relationships and raise money, and what to ask for. We'll also help you invite your board members to contribute their own ideas.

You can choose how much help you want.

Guided setup and self-facilitation: $497. We'll prepare the process with you, invite your board members, and show you how to facilitate the Group Game. After setup, we'll hand over your prepared dashboard so you can run the meeting, record agreed decisions and use the platform to develop your fundraising strategy and member resources.

Rooney-facilitated Board Fundraising: $1,497. Rooney will prepare the process, facilitate your board's Group Game, help the group agree on its funding audiences and participation, and professionally review and complete the strategy and relevant board member portfolios.

Both options begin with preparation. The difference is who runs the board meeting and professionally completes the final materials.""", "PAY $1,497 AND HAVE ROONEY FACILITATE", delay_minutes=60)
        result["followups"] = [email(subject, "Hello {{first_name}},\n\n" + body + "\n\nYour information for {{organization}} remains saved. Choose guided setup at $497 or Rooney's full facilitation at $1,497 through your personal link.", after_previous_minutes=4320) for subject,body in [
            ("Bring your board into the fundraising discussion", "Your board members can contribute ideas and relationships you cannot supply alone. We can help you prepare the process and agree on a shared approach."),
            ("A fundraising approach your board helped develop", "The Group Game gives every member space to suggest funding audiences and discuss practical ways to reach them."),
            ("Choose how much facilitation you need", "We can prepare you to run the meeting yourself, or Rooney can facilitate it and professionally complete the final materials."),
            ("Agree on how each member can participate", "Use your meeting to record responsibilities people have actually accepted, alongside the funding audiences your board adopts."),
            ("Your invitation to start board fundraising", "Your saved answers are ready for the next step whenever you want to begin.")]]
        result["operational_emails"]["response_notice"] = email("A Board Member Has Shared Their Fundraising Ideas", "Hello {{first_name}},\n\n{{participant_name}} has completed their fundraising responses for {{organization}}. Use your secure link to read their original ideas before your board meeting.", "VIEW FUNDRAISING IDEAS")
    else:
        result = _original_defaults(service)
    if service == "strategic-planning":
        result["first_email"] = email("Let's Build Your Organization's Strategic Plan Together", """Hello {{first_name}},

Thank you for sharing your vision for {{organization}} and what you want to achieve over the next 12 to 24 months. Your board members have an important role in helping your organization reach that future.

We'll begin with a preparation meeting, set up your planning forms and help invite your board members to share their original ideas.

Guided setup and self-facilitation: $497. We'll prepare your project, walk you through the forms, invitations and meeting tools, and show you how to facilitate the board session. We'll hand over your prepared dashboard so you can discuss everyone's ideas, record adopted decisions, develop and edit the plan, arrange board review and generate the supported member resources.

Rooney-facilitated Strategic Planning: $1,997. Rooney will prepare the process and facilitate your board's planning session, helping the group agree on its goals, program priorities and responsibilities. He'll use those decisions and the relevant meeting transcript to prepare and edit your strategic plan, guide board review, and professionally complete the relevant leadership portfolios.

Both options begin with preparation. The difference is whether you run the planning process or Rooney facilitates it and professionally completes the final materials.""", "PAY $1,997 AND HAVE ROONEY FACILITATE", delay_minutes=60)
    if service in PACKAGES:
        result["first_email"]["self_cta"] = "PAY $497 AND PREPARE MY " + NAMES[service].upper()
        result["handover_email"] = email("Your {{service_name}} Dashboard Is Ready", "Hello {{first_name}},\n\nYour {{service_name}} project for {{organization}} has been prepared. Use your personal invitation to accept control of the existing dashboard. Your answers, invitations and resources are already there. You can run your meeting and continue the process independently.\n\nThis invitation expires after 48 hours. If it expires, Rooney can issue another without charging you again.", "ACCEPT MY DASHBOARD")
    result["customer_copy"] = {
        "received_heading": "Thank You. We've Received Your " + NAMES[service] + " Information.",
        "received_body": "We'll review what you've shared about your organization and email the next steps. Please look out for an email from Nonprofit Board Builder.",
        "offer_heading": "Let's Begin Your " + NAMES[service],
        "offer_intro": "Your information is saved. Choose how you would like to proceed. Both options begin with a preparation meeting." if service in PACKAGES else "Your information is saved. After payment, provide your branding and book your guided session with Rooney.",
        "self_heading": "Guided Setup and Self-Facilitation",
        "self_description": "We will prepare your project with you, invite your board members and show you how to run the process. We will then hand over your prepared dashboard, including its saved responses, meeting tools and documents.",
        "professional_heading": "Let Rooney Facilitate the Process",
        "professional_description": "Rooney prepares your project, facilitates the board meeting, and professionally reviews and completes your agreed strategy or plan and relevant board member materials.",
        "branding_intro": "Your payment is confirmed. Save your organization's branding before choosing your preparation meeting time.",
        "booking_heading": "Your " + NAMES[service] + " Process Is Ready to Begin.",
        "booking_description": "The next step is to meet with Rooney, review your organization's situation and prepare the process together.",
        "booking_cta": "BOOK MY " + NAMES[service].upper() + (" PREPARATION SESSION" if service in PACKAGES else " SESSION"),
        "question_submit": "SUBMIT MY BOARD FUNDRAISING INFORMATION" if service == "board-fundraising" else "SAVE MY ANSWERS",
        "dashboard_heading": "Your " + NAMES[service] + " Dashboard",
        "handover_heading": "Your Prepared Dashboard Is Ready",
        "handover_description": "Accept your personal invitation to continue with the project Rooney prepared with you. Your saved information and invitations will remain available.",
        "handover_cta": "ACCEPT MY DASHBOARD",
    }
    if service == "strategic-planning":
        result["customer_copy"]["planning_form_intro"]="Share your own ideas about your organization's future. Your contributions will be discussed together during your board planning meeting. You can return through your personal link to finish your answers."
    if service == "recruitment":
        result["customer_copy"]["professional_description"] = "After your $497 payment, provide your organization's branding and book your recruitment session. Together, you and Rooney will review the recommended board member profiles, agree on the people to recruit, prepare and approve your campaign materials, and publish the opportunity when the required information is ready. You retain the campaign link, applications, interview resources and onboarding materials to continue independently."
    elif service == "board-recommitment":
        result["customer_copy"]["professional_description"] = "After your $497 payment, provide your organization's branding and book your recommitment session. Together, you and Rooney will clarify what your board needs to contribute, prepare your communications and forms, and invite members to respond. You receive notifications, conversation guidance and the resources to record agreed decisions and prepare portfolios. Each person's formal role changes only through your organization's appropriate decisions."
    if service == "board-fundraising":
        result["operational_emails"]["fundraising_invitation"] = email("You're Invited to Share Your Fundraising Ideas", "Hello {{participant_name}},\n\n{{leader_name}} invites you to help {{organization}} work towards its fundraising goal of {{fundraising_goal}} by {{fundraising_deadline}}.\n\nShare your own ideas freely about who would fund the mission and how your organization could reach them. Your responses will be discussed at your next board meeting.\n\n{{meeting_details}}\n\nUse your personal link to play the individual Game. You do not need to purchase anything.", "PLAY MY FUNDRAISING GAME")
        result["operational_emails"]["strategy_ready"] = email("Your Board's Fundraising Strategy Is Ready", "Hello {{first_name}},\n\nYour board's adopted fundraising strategy has been reviewed and is ready to use. Open your strategy to read, download and share it with your board. Your strategy records the funding audiences and responsibilities agreed during the meeting.\n\nYou can also book a conversation with Rooney about the strategy and its execution.", "VIEW MY APPROVED STRATEGY")
        result["operational_emails"]["fundraising_portfolio_delivery"] = email("Your Approved Board Fundraising Portfolio", "Hello {{participant_name}},\n\nYour organization has approved your individual fundraising portfolio. It describes the responsibility you agreed to undertake and includes the board's adopted approaches. Use your personal link to read and download it.", "VIEW MY APPROVED PORTFOLIO")
    result["customer_copy"]["self_cta"]="PAY $497 AND PREPARE MY PROCESS"
    result["customer_copy"]["professional_cta"]="PAY $"+format(PRICES[service]//100,",")+" AND HAVE ROONEY FACILITATE" if service in PACKAGES else "PAY $"+str(PRICES[service]//100)+" AND BEGIN MY GUIDED SERVICE"
    return result
