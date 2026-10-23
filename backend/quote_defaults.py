"""Current quote funnel defaults. Historic question snapshots and purchases are immutable."""
from copy import deepcopy

VERSION = "free-quote-2026-10"
PRICING_VERSION = "all-four-497-2026-10-24"
TEST_EMAIL = "fundraisingschoolfornonprofits@gmail.com"
IMPACT_KEY = "desired_outcome_impact"
IMPACT = {
    "recruitment": "When you recruit these board members, how would they help you and your organization?",
    "board-recommitment": "Getting your board members to recommit or step down, how would that help you and your organization?",
    "board-fundraising": "Getting your board members to raise money, how would that help your organization?",
    "strategic-planning": "Taking your board members through strategic planning, how would that help you and your organization?",
}
BRIDGES = {
    "recruitment": "That gives us a clear starting point for identifying the board members you need and preparing your recruitment campaign.",
    "board-recommitment": "We can help you begin a structured recommitment process, understand the responses and prepare the conversations needed to move forward.",
    "board-fundraising": "The Fundraising Game gives your board a structured way to contribute ideas, agree on funding audiences and decide how each person will participate.",
    "strategic-planning": "Our guided setup will show you how to involve your board, facilitate the planning discussion and turn agreed decisions into a strategic plan.",
}
HEADINGS = {
    "recruitment": "Tell Us About Your Board Recruitment Needs.",
    "board-recommitment": "Tell Us About Your Board Recommitment Needs.",
    "board-fundraising": "Tell Us About Your Board and Fundraising Goal.",
    "strategic-planning": "Tell Us About Your Strategic Planning Needs.",
}

def quote_questions(service):
    from guided_service_defaults import question as q
    rows = [q("leader_role", "What is your role in the organization?", kind="text")]
    if service == "recruitment":
        rows += [q("desired_count", "How many board members do you want to recruit?", "Tell us if you are not sure yet.", kind="text"), q("location_preference", "Where would you like these board members to be located?", "You can describe a location or say that remote participation is suitable.")]
    elif service == "board-recommitment":
        rows += [q("board_count", "How many board members need to recommit?", kind="text"), q("why_recommit", "Why do these board members need to recommit?")]
    elif service == "board-fundraising":
        rows += [q("board_size", "How many board members do you have?", kind="number"), q("fundraising_goal", "How much money is your organization trying to raise?", "Enter the amount in US dollars.", kind="number"), q("fundraising_deadline", "When does your organization need this funding?", "Tell us the date or timing you are working towards.", kind="text"), q("funding_consequences", "What happens if your organization does not raise this money?")]
    else:
        rows += [q("board_count", "How many board members does your organization have?", kind="text"), q("planning_meeting_preference", "Which upcoming board meeting would you like to use for strategic planning?", "If your meeting is not scheduled yet, please say so.", kind="text")]
    rows += [q(IMPACT_KEY, IMPACT[service], "Explain in your own words what achieving this result would mean for you and your organization.", semantic_role=IMPACT_KEY)]
    return rows

FIRST_COPY = {
    "recruitment": ("Let's Launch Your Board Recruitment Campaign", "You indicated that your organization is looking to recruit {{board_count}} board members, preferably located in {{location_preference}}.", "We can work with you to identify the exact type of board members your organization needs, create your recruitment materials and launch your recruitment campaign.\n\nDuring our campaign launch session, we will work together to get your recruitment process started. You will also receive the materials needed to manage applications and appoint suitable candidates.", "The cost of launching your board recruitment campaign with us is $497.", "Launch My Recruitment Campaign | $497"),
    "board-recommitment": ("Let's Get Your Board Members Recommitted", "You indicated that {{board_count}} board members need to recommit to supporting your organization.", "First, we will prepare a recommitment form for your board members. As they respond, we will help you interpret their answers and prepare the appropriate conversation for each person.\n\nThis process is designed to help your board members make clear decisions about stepping up to their responsibilities or stepping down.", "The cost of our Board Recommitment process is $497.", "Get My Board Recommitted | $497"),
    "board-fundraising": ("Let's Get Your Board Members Fundraising", "You indicated that your organization has {{board_count}} board members and is working toward raising {{fundraising_goal}}.", "Through The Fundraising Game, you and your board members will identify the people and institutions with the strongest reasons to support your mission. You will work together to agree on how to reach those funders and how each board member will participate.\n\nDuring our setup session, I will show you how to prepare the process for your next board meeting.", "The cost of The Fundraising Game is $497.", "Get My Board Fundraising | $497"),
    "strategic-planning": ("Let's Get Your Board Involved in Strategic Planning", "You indicated that you want to involve {{board_count}} board members in shaping your organization's future.", "You can facilitate this process yourself using our strategic planning system. During our guided setup session, I will show you how to prepare the process, invite your board members and facilitate the meeting. I will also show you how to turn the decisions made during the meeting into your organization's strategic plan.", "Guided Strategic Planning Setup costs $497. Professional facilitation of the actual board meeting is a separate service with its own quote, which we can discuss during our session.", "Prepare My Strategic Planning Session | $497"),
}

LANDINGS = {
    "recruitment": ("Launch Your Board Recruitment Campaign in Just 30 Minutes.", "Let us work with you to identify the exact kind of board members your organization needs, create the materials required to recruit them and launch a campaign that attracts suitable people to apply to join your board.", [("Identify the Board Members You Need", "Consider your mission, current board and the people who can help you achieve your goals."), ("Create Your Recruitment Materials", "Prepare the campaign materials needed to communicate the opportunity and attract suitable candidates."), ("Launch Your Recruitment Campaign", "Work together to launch your campaign in a 30-minute working session when the necessary information and approvals are ready."), ("Receive Applications and Select Your Board Members", "Review applications and decide who should join your organization.")]),
    "board-recommitment": ("Get Your Board Members to Step Up or Step Down in Seven Days.", "Let us help you address disengagement on your board. Understand which board members are ready to recommit to meaningful participation and prepare the conversations needed to get them contributing again or make a decision to step down.", [("Send the Recommitment Form", "Invite board members to explain their willingness and ability to continue contributing."), ("Interpret Their Responses", "Understand each person's commitment and readiness to participate."), ("Have the Conversations That Lead to Action", "Use personalized conversation guidance to establish expectations and clarify each person's decision. Individual responses and outcomes can take longer than seven days.")]),
    "board-fundraising": ("Get Your Board Members Fundraising by Your Next Board Meeting.", "Bring your board members into the process of developing and executing your organization's fundraising strategy. Decide who should fund your mission, how to attract those funders, what to ask them to support and how each board member will participate.", [("Play The Fundraising Game", "Contribute your ideas about the organization's mission, funding needs and potential donors."), ("Your Board Members Play Their Own Game", "Each person shares their fundraising ideas and how they can help."), ("Come Together at Your Board Meeting", "Discuss the audiences and approaches your board wants to pursue."), ("Adopt Your Fundraising Strategy", "Agree on the strategy and the responsibilities each person accepts.")]),
    "strategic-planning": ("Get Your Board Members Building Your Organization With You by Your Next Board Meeting.", "Bring your board members into deciding where your organization should be in the next 24 months and how everyone will contribute to getting there.", [("Share Your Vision for the Next 24 Months", "Explain where you want the organization to be and what it should accomplish."), ("Invite Your Board Members to Share Their Perspectives", "Give every board member the opportunity to contribute their own ideas."), ("Agree on the Organization's Direction", "Discuss goals, programs, resources, partnerships and responsibilities."), ("Adopt Your Strategic Plan", "Turn your agreed decisions into a plan you can use and share with stakeholders.")]),
}

def apply_defaults(service, base):
    from guided_service_defaults import email
    result = deepcopy(base)
    # Keep the established detailed questionnaire, now collected after payment.
    if service != "strategic-planning":
        result["question_groups"]["leader"] = deepcopy(base["question_groups"]["entry"])
        if service == "board-fundraising":
            result["question_groups"]["leader"] = [q for q in result["question_groups"]["leader"] if q["key"] != "next_board_meeting"]
    result["question_groups"]["entry"] = quote_questions(service)
    result["quote_version"] = VERSION
    result["pricing_version"] = PRICING_VERSION
    subject, summary, process, price, cta = FIRST_COPY[service]
    result["first_email"] = email(subject, "Hi {{first_name}},\n\nThank you for requesting a free quote for {{service_name}} for {{organization_name}}.\n\n" + summary + "\n\n{{personalized_outcome}}\n\n" + process + "\n\nWe begin the work together on our first call. Your dashboard contains the tools and resources to continue independently.\n\n" + price + "\n\nOnce you make payment, you will complete the detailed leader questions, provide your organization's branding and choose a time to meet with me.", cta, delay_minutes=60, incomplete_cta="Complete My Quote Request", preview_text="Your next steps for {{organization_name}}")
    result["paid_email"] = email("Your {{service_name}} Payment Is Confirmed", "Hi {{first_name}},\n\nYour payment is confirmed. Complete your detailed leader questionnaire, save your organization's logo and colors, then choose a convenient time for our session. Your information is saved and you can return without paying again.", "Complete My Leader Questionnaire")
    for item in result["followups"]:
        item["body"] = item["body"].replace("$497", "${{price}}")
        item["after_previous_minutes"] = 4320
    headline, description, steps = LANDINGS[service]
    result["landing"].update(headline=headline, description=description, cta="GET A FREE QUOTE")
    result["landing"]["steps"] = [[str(i+1), title, text] for i, (title, text) in enumerate(steps)]
    result["customer_copy"].update({"contact_heading": HEADINGS[service], "contact_cta": "CONTINUE TO MY QUOTE", "contact_email_notice": "Complete the short questions next. Look out for my email within one hour after submitting your quote request.", "question_submit": "GET MY FREE QUOTE", "received_heading": "Your " + ("Board Recommitment Request" if service == "board-recommitment" else "Board Fundraising Request" if service == "board-fundraising" else "Board Recruitment Quote Request" if service == "recruitment" else "Strategic Planning Quote Request") + " Has Been Received.", "received_body": "Thank you for sharing what you want to accomplish. We will email you the next steps within the next hour. Please look out for my email in your inbox.\n\nRooney A. The Nonprofit Board Builder", "leader_heading": "Tell Us More About Your Organization", "leader_intro": "Your payment is confirmed. Complete the leader questions below, then provide your branding and book our session. You can save and return through your secure link.", "leader_submit": "SAVE MY LEADER QUESTIONNAIRE", "leader_saved": "Your leader questionnaire is saved. Please confirm your organization branding below.", "offer_intro": "Complete your payment, answer the detailed leader questions, provide your organization's branding and choose a convenient time to meet with Rooney.", "activation_description": "Your guided setup session and platform provide the tools and structure to continue independently. We begin your process together on the first call. Additional professional facilitation, if needed, is quoted separately."})
    return result
