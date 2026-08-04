import asyncio
import html
import os
from typing import Any, Dict, Iterable

import resend


SECTION_FIELDS = [
    (
        "Contact and Organization",
        [
            ("Name", "name"), ("Email", "email"), ("Phone number", "phone"),
            ("Organization", "organization_name"), ("Website", "website"),
            ("Mission", "mission"), ("Location", "location"),
            ("Annual budget", "annual_budget"),
            ("Most important result needed from the board", "most_important_board_result"),
        ],
    ),
    (
        "Present Board",
        [
            ("Board size required by the bylaws", "bylaws_board_size"),
            ("Present number of board members", "current_board_size"),
            ("Active board members", "active_board_members"),
            ("Inactive or inconsistent board members", "inactive_board_members"),
            ("Present board condition", "present_board_condition"),
            ("Type of board", "board_type"),
            ("Commitment conversations", "commitment_conversations"),
            ("Willingness to allow inactive members to step down", "willing_to_allow_step_down"),
            ("Bylaw clarity", "bylaw_clarity"),
        ],
    ),
    (
        "Board Recruitment Needs",
        [
            ("Number of new board members required", "new_board_members_needed"),
            ("Recruitment timeline", "recruitment_timeline"),
            ("Areas the founder is carrying alone", "areas_carried_alone"),
            ("Missing skills, experience and networks", "missing_skills_networks"),
            ("Expected benefit of new board members", "expected_new_member_benefit"),
            ("People already identified", "people_already_identified"),
            ("Benefits of joining the board", "benefits_of_joining"),
            ("Previous recruitment experience", "previous_recruitment_experience"),
        ],
    ),
    (
        "Fundraising Activation",
        [
            ("Present board fundraising involvement", "present_fundraising_involvement"),
            ("Areas board members can support", "board_support_areas"),
            ("Fundraising strategy", "written_fundraising_strategy"),
            ("Understanding of individual responsibilities", "individual_responsibilities"),
            ("Board participation in planning", "board_participation_in_planning"),
            ("Missing fundraising-system elements", "missing_fundraising_elements"),
            ("Desired result", "desired_result"), ("Support required", "support_required"),
            ("Additional information", "additional_information"),
        ],
    ),
]


def format_value(value: Any) -> str:
    if isinstance(value, list):
        value = "; ".join(value)
    return html.escape(str(value or "Not provided"))


def render_rows(fields: Iterable, assessment: Dict[str, Any]) -> str:
    rows = []
    for label, key in fields:
        value = assessment.get(key)
        if key == "location":
            value = ", ".join(
                filter(None, [assessment.get("city"), assessment.get("state_region"), assessment.get("country")])
            )
        rows.append(
            f'<tr><td style="padding:9px 12px;border-bottom:1px solid #dfe9e2;font-weight:700;vertical-align:top;width:36%;">{html.escape(label)}</td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #dfe9e2;vertical-align:top;">{format_value(value)}</td></tr>'
        )
    return "".join(rows)


def build_email_html(assessment: Dict[str, Any]) -> str:
    sections = "".join(
        f'<h2 style="margin:28px 0 10px;color:#14532d;font-size:20px;">{title}</h2>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #dfe9e2;border-radius:8px;border-collapse:collapse;">{render_rows(fields, assessment)}</table>'
        for title, fields in SECTION_FIELDS
    )
    return f"""
    <div style="font-family:Arial,sans-serif;color:#17241c;line-height:1.55;max-width:760px;margin:auto;">
      <h1 style="color:#0b3b24;font-size:26px;">New Board Assessment</h1>
      <p><strong>Assessment number:</strong> {format_value(assessment['assessment_number'])}<br>
      <strong>Submission date and time:</strong> {format_value(assessment['submitted_at'])}</p>
      {sections}
    </div>
    """


async def send_owner_assessment_email(assessment: Dict[str, Any]) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    sender_email = os.environ.get("SENDER_EMAIL")
    owner_email = os.environ.get("OWNER_NOTIFICATION_EMAIL") or os.environ.get("OWNER_EMAIL")
    if not api_key or not sender_email or not owner_email:
        raise RuntimeError("Missing RESEND_API_KEY, SENDER_EMAIL, or OWNER_NOTIFICATION_EMAIL")

    resend.api_key = api_key
    params = {
        "from": sender_email,
        "to": [owner_email],
        "subject": f"New Board Assessment — {assessment['organization_name']}",
        "html": build_email_html(assessment),
    }
    await asyncio.to_thread(resend.Emails.send, params)