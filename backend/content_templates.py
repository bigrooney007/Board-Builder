"""Single source of truth for customer-facing Reactivation email and script templates."""


def _signature(founder_name: str, founder_title: str, organization: str) -> str:
    return founder_name + (f"\n{founder_title}" if founder_title else "") + f"\n{organization}"


def recommitment_outreach_email(kind: str, first: str, founder_name: str, founder_title: str, organization: str, mission: str = "", goals: str = "") -> dict:
    signature = _signature(founder_name, founder_title, organization)
    if kind == "reminder":
        return {
            "subject": f"Reminder: Board Member Recommitment Form | {organization}",
            "body": (
                f"Dear {first},\n\n"
                f"I wanted to follow up on the Board Member Profile & Recommitment Form I sent you for {organization}.\n\n"
                "We are using the responses from each Board Member to understand where everyone is, how people would like to contribute moving forward, and what support or clarity may be needed.\n\n"
                "If you have not completed yours yet, please use the link below:\n\n"
                "[COMPLETE MY FORM]\n\n"
                "Your response will help us prepare for the conversation about your Board role and how we move forward together.\n\n"
                f"Thank you,\n{signature}"
            ),
            "button_label": "COMPLETE MY FORM",
        }
    greeting = f"Dear {first}," if first else "Dear Board Member,"
    return {
        "subject": f"Board Recommitment & Profile | {organization}",
        "body": (
            f"{greeting}\n\n"
            + why
            + f"As we continue strengthening the Board of {organization}, we are taking time to make sure every Board Member has clarity about their role, capacity and how they would like to contribute moving forward.\n\n"
            "Please take a few minutes to complete your Board Member Profile & Recommitment Form.\n\n"
            "Your responses will help us understand:\n"
            "- how you would like to continue contributing\n"
            "- the expertise and experience you bring\n"
            "- the areas where you would most like to help\n"
            "- the level of time you can realistically commit\n"
            "- any support or clarity you need from the organization\n\n"
            "This is not about pressuring anyone to stay.\n\n"
            "It is about having an honest understanding of where each Board Member is and making sure the people serving on the Board are positioned to contribute meaningfully.\n\n"
            "[COMPLETE MY BOARD MEMBER PROFILE & RECOMMITMENT FORM]\n\n"
            f"Thank you for taking the time to complete it.\n\n{signature}"
        ),
        "button_label": "COMPLETE MY BOARD MEMBER PROFILE & RECOMMITMENT FORM",
    }


def recommitment_reminder_call_script(first: str, founder_first: str, organization: str) -> str:
    return (
        f"Hi {first}, it's {founder_first} from {organization}.\n\n"
        "I wanted to quickly follow up on the Board Member Profile & Recommitment Form I sent you.\n\n"
        "We're asking every Board Member to complete it because I want to understand where everyone is, what people realistically have capacity for, and how each person would like to contribute moving forward.\n\n"
        "This isn't about pressuring anyone.\n\n"
        "I want us to have an honest picture of who is able to continue serving actively, where people need more clarity, and where we may need to make changes so the Board can function properly.\n\n"
        "I can resend the link to you now if that would help.\n\n"
        "Is there anything that's making it difficult for you to complete it?"
    )


def recommitment_form_intro(organization: str, mission: str) -> str:
    mission_line = f"\n\nOur mission: {mission}" if mission else ""
    return (
        f"Board Member Profile & Recommitment Form — {organization}\n\n"
        f"As we continue strengthening the Board of {organization}, we are asking every Board Member to complete this Profile & Recommitment Form.{mission_line}\n\n"
        "Your responses will help us understand how you would like to continue contributing, the expertise and experience you bring, the areas where you would most like to help, the time you can realistically commit, and any support or clarity you need from the organization.\n\n"
        "This is not about pressuring anyone to stay. It is about having an honest understanding of where each Board Member is, so the people serving on the Board are positioned to contribute meaningfully."
    )

# ---------------- Strategic Planning static emails ----------------

def sp_signature(founder_name: str, founder_title: str, organization: str) -> str:
    return founder_name + (f"\n{founder_title}" if founder_title else "") + f"\n{organization}"


def sp_form_invitation_email(first: str, organization: str, signature: str) -> dict:
    body = (
        f"Dear {first},\n\n"
        f"We are beginning the process of building the strategic plan for {organization}, and I want the Board involved in shaping it.\n\n"
        "Rather than creating the plan and bringing it to the Board after the fact, I want us to build it together.\n\n"
        "Your ideas, experience and perspective will help shape our direction, priorities and how each of us can contribute.\n\n"
        "Please complete the Strategic Planning Form below.\n\n"
        "[COMPLETE MY STRATEGIC PLANNING FORM]\n\n"
        "Your responses will be combined with the ideas of the other Board Members as we build the plan.\n\n"
        f"Thank you for helping us build this together.\n\n{signature}"
    )
    return {"subject": f"Help Us Build Our Strategic Plan | {organization}", "body": body,
            "button_label": "COMPLETE MY STRATEGIC PLANNING FORM"}


def sp_generic_form_invitation_email(organization: str, link: str, signature: str) -> dict:
    body = (
        "Dear Board Member,\n\n"
        f"We are beginning the process of building the strategic plan for {organization}, and I want the Board involved in shaping it.\n\n"
        "Rather than creating the plan and bringing it to the Board after the fact, I want us to build it together.\n\n"
        "Your ideas, experience and perspective will help shape our direction, priorities and how each of us can contribute.\n\n"
        "Please complete the Strategic Planning Form using the link below.\n\n"
        f"{link}\n\n"
        "Your responses will be combined with the ideas of the other Board Members as we build the plan.\n\n"
        f"Thank you for helping us build this together.\n\n{signature}"
    )
    return {"subject": f"Help Us Build Our Strategic Plan | {organization}", "body": body, "form_link": link}


def sp_review_invitation_email(first: str, organization: str, signature: str) -> dict:
    body = (
        f"Dear {first},\n\n"
        f"The ideas the Board shared have been consolidated into the Foundational Strategic Plan for {organization}.\n\n"
        "Before area owners develop the detailed plans, I want every Board Member to review the consolidated thinking, challenge it, improve it and add anything that is missing.\n\n"
        "For each strategic area you can support it as written, suggest a change, add an idea, or flag it for Board discussion.\n\n"
        "[REVIEW THE FOUNDATIONAL PLAN]\n\n"
        f"Thank you for helping us refine this together.\n\n{signature}"
    )
    return {"subject": f"Review Our Foundational Strategic Plan | {organization}", "body": body,
            "button_label": "REVIEW THE FOUNDATIONAL PLAN"}


def activation_signature(founder_name: str, founder_title: str, organization: str) -> str:
    return founder_name + (f"\n{founder_title}" if founder_title else "") + f"\n{organization}"


def activation_planning_email(organization: str, form_link: str, signature: str) -> dict:
    return {
        "subject": f"Help Us Build Our Fundraising Plan | {organization}",
        "body": (
            "Dear Board Members,\n\n"
            f"We are beginning the process of building the fundraising plan for {organization}, and I want the Board involved in shaping it.\n\n"
            "Rather than creating the plan and bringing it to the Board after the fact, I want us to build it together.\n\n"
            "Your ideas, experience, relationships and perspective can help us determine who we should be building relationships with, which fundraising opportunities we should prioritize, and how each of us can contribute.\n\n"
            "Please complete the short Board Fundraising Planning Form here:\n\n"
            f"{form_link}\n\n"
            "Your responses will be combined with the ideas of the other Board Members and our organizational priorities as we build the Fundraising Strategy Plan.\n\n"
            f"Thank you for helping us build this together.\n\n{signature}"
        ),
    }


def activation_review_email(organization: str, review_link: str, signature: str) -> dict:
    return {
        "subject": f"Please Review Our Fundraising Strategy Plan | {organization}",
        "body": (
            "Dear Board Members,\n\n"
            f"Thank you for contributing your ideas to the fundraising planning process for {organization}.\n\n"
            "We have now brought the Board's input together with the organization's fundraising goals and priorities and developed the Fundraising Strategy Plan for Board review.\n\n"
            "Before we move into adopting the plan, please review the strategy and share any suggestions, concerns or issues you believe the Board should discuss.\n\n"
            "Please review the complete Fundraising Strategy Plan here:\n\n"
            f"{review_link}\n\n"
            "Your review will help us prepare for the Board discussion where we will work through the strategy and agree on the way forward.\n\n"
            f"Thank you for helping us build this together.\n\n{signature}"
        ),
    }


def activation_adoption_meeting_email(organization: str, meeting_lines: str, plan_link: str, signature: str) -> dict:
    meeting_block = f"MEETING DETAILS\n\n{meeting_lines}\n\n" if meeting_lines.strip() else ""
    return {
        "subject": f"Board Meeting: Review & Adopt Our Fundraising Strategy Plan | {organization}",
        "body": (
            "Dear Board Members,\n\n"
            f"Thank you for contributing your ideas and perspective to the fundraising planning process for {organization}.\n\n"
            "We have now brought together the Board's input, the organization's fundraising goals and priorities, and the information we have about where the organization is going to develop our Fundraising Strategy Plan.\n\n"
            "The next step is for us to come together as a Board to review the plan, strengthen anything that needs strengthening, agree on the direction we want to take, and adopt the strategy as the working fundraising document for the organization.\n\n"
            "Please review the Fundraising Strategy Plan before the meeting:\n\n"
            f"{plan_link}\n\n"
            "You do not need to complete another form. Please simply come to the meeting with any questions, concerns, suggestions or changes you believe we should discuss.\n\n"
            f"{meeting_block}"
            "During the meeting we will:\n\n"
            "- review the major decisions and recommendations in the strategy;\n"
            "- discuss anything the Board believes should be changed or strengthened;\n"
            "- confirm the fundraising priorities we want to pursue;\n"
            "- adopt the strategy as our working fundraising document;\n"
            "- discuss how the Board will help execute the plan;\n"
            "- and agree the immediate way forward.\n\n"
            f"Thank you again for helping us build this together.\n\n{signature}"
        ),
    }


def checkout_recovery_email(first_name: str, organization: str, offer_name: str, offer_link: str) -> dict:
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    org_part = f" at {organization}" if organization else ""
    return {
        "subject": "You started building your board — your next step is ready",
        "body": (
            f"{greeting}\n\n"
            f"You took the first step toward transforming your board{org_part}, and you were moments away from getting started with {offer_name}.\n\n"
            "If you got pulled away, no problem. Your next step is right where you left it:\n\n"
            f"{offer_link}\n\n"
            "If you have a question before you get started, just reply to this email and I'll personally answer it.\n\n"
            "Rooney Akpesiri\nThe Nonprofit Board Builder"
        ),
    }
