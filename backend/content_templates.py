"""Single source of truth for customer-facing Reactivation email and script templates."""


def _signature(founder_name: str, founder_title: str, organization: str) -> str:
    return founder_name + (f"\n{founder_title}" if founder_title else "") + f"\n{organization}"


def recommitment_outreach_email(kind: str, first: str, founder_name: str, founder_title: str, organization: str) -> dict:
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
            f"As we continue strengthening the Board of {organization}, we are taking time to make sure every Board Member has clarity about their role, capacity and how they would like to contribute moving forward.\n\n"
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
