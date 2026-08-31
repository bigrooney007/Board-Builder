import html
import os
import secrets
from datetime import datetime
from typing import Any, Dict

import resend


SUPPORT_PREFERENCES = {"diy": "Do It Yourself", "guided": "Guided Support", "self_guided": "Self-Guided Recruitment", "done_with_you": "Done With You", "undecided": "I'm Not Sure Yet"}

REQUIRED_ANSWERS = {
    "recruitment": {"new_members_needed"},
    "reactivation": {"disengaged_count"},
    "fundraising_activation": {"board_member_count"},
    "board_transformation": {
        "present_board", "active_board", "need_recruit", "reactivate_inactive",
        "board_fundraising_now", "want_fundraising",
    },
    "board_fix": set(),
}


def validate_answers(source: str, answers: Dict[str, Any]) -> None:
    missing = []
    for key in REQUIRED_ANSWERS[source]:
        value = answers.get(key)
        if value is None or value == "" or value == []:
            missing.append(key)
    if missing:
        raise ValueError(f"Missing required answers: {', '.join(sorted(missing))}")
    if source == "recruitment" and answers.get("support_preference") and answers.get("support_preference") not in SUPPORT_PREFERENCES:
        raise ValueError("Support preference must be one of: diy, guided, done_with_you, undecided")
    if answers.get("present_board", "") == "" or answers.get("active_board", "") == "":
        return
    present = int(answers["present_board"])
    active = int(answers["active_board"])
    if present < 0 or active < 0 or active > present:
        raise ValueError("Board numbers must be valid and active members cannot exceed the present board size")


def create_lead_id(now: datetime) -> str:
    return f"NBB-L-{now.strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"


def recruitment_result(answers: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "present_board": answers.get("present_board", ""), "active_board": answers.get("active_board", ""),
        "new_members_needed": answers.get("new_members_needed", answers.get("additional_needed", "")),
        "accomplish": answers.get("accomplish_areas", answers.get("accomplish", answers.get("priorities", ""))),
        "strengthen_areas": answers.get("accomplish_areas", answers.get("strengthen_areas", answers.get("capacity_areas", []))),
        "board_type": answers.get("board_type", ""),
        "next_step": "The next step is to choose how you want to recruit your board.",
    }


def reactivation_result(answers: Dict[str, Any]) -> Dict[str, Any]:
    present, active = int(answers["present_board"]), int(answers["active_board"])
    observations = []
    if present > active and answers["recommitment_conversations"] in {"No", "Some of them", "I am not sure"}:
        observations.append("Your first step should be a structured recommitment process. Every present board member needs a clear opportunity to decide whether they remain willing and able to serve before you decide who stays, who steps up and who may need to step down.")
    if "They attend but do not accept responsibility" in answers["inactive_situations"]:
        observations.append("Your board does not simply have an attendance problem. Present members need clear responsibilities connected to the priorities of the organization.")
    if answers["strategic_planning"] != "Yes":
        observations.append("Your board also needs shared direction. When board members help determine where the organization is going, it becomes easier to give them responsibility for helping move it forward.")
    if "Allow inactive members to step down" in answers["desired_changes"]:
        observations.append("The goal is not to pressure people into serving. The process should give members a respectful opportunity to recommit or acknowledge that they can no longer give the organization what the role requires.")
    if not observations:
        observations.append("Your strongest starting point is to connect each board member with clear priorities, expectations and meaningful responsibility.")
    return {
        "present_board": present, "active_board": active,
        "members_needing_reengagement": max(0, present - active),
        "priorities": answers["priorities"], "desired_changes": answers["desired_changes"],
        "observations": observations,
        "next_step": "The next step is to launch a structured recommitment process, determine who is prepared to continue, reset expectations, assign meaningful responsibilities and move the reactivated board into execution.",
    }


def activation_result(answers: Dict[str, Any]) -> Dict[str, Any]:
    strategic = "In Place" if answers.get("strategic_planning") == "Yes" else "Needs Attention"
    strategy = "In Place" if answers.get("fundraising_strategy") == "Yes" else "Needs Attention"
    responsibilities = "In Place" if answers.get("individual_responsibilities") == "Yes" else "Needs Attention"
    observations = []
    if answers.get("fundraising_strategy") in {"No", "I am not sure"}:
        observations.append("Before board members can execute fundraising consistently, the organization needs a clear fundraising direction they can understand and help implement.")
    if answers.get("fundraising_strategy") == "Yes, but the board is not meaningfully involved":
        observations.append("Your organization already has a fundraising strategy. The next gap is turning that strategy into responsibilities the board can help execute.")
    if answers.get("individual_responsibilities") in {"No", "Some do", "I am not sure"}:
        observations.append("Your board cannot become a fundraising board simply by being told to raise money. Each person needs a defined responsibility connected to their strengths and relationships.")
    if answers.get("fundraising_involvement") == "One person does most of it":
        observations.append("Fundraising is currently concentrated in too few hands. The next step is to distribute meaningful fundraising responsibilities across the board.")
    if not observations:
        observations.append("Your starting point is to connect the board's present fundraising participation with the specific areas you want members to help execute.")
    return {
        "strategic_direction": strategic, "fundraising_strategy": strategy,
        "individual_responsibilities": responsibilities,
        "fundraising_participation": answers.get("fundraising_involvement", ""),
        "board_member_count": answers.get("board_member_count", ""),
        "fundraising_need": answers.get("fundraising_need", ""), "fundraising_areas": answers.get("fundraising_areas", []),
        "observations": observations,
        "next_step": "The next step is to involve the board in the fundraising plan, assign individual responsibilities, create the materials people need and establish a consistent execution process.",
    }


def board_transformation_result(answers: Dict[str, Any]) -> Dict[str, Any]:
    present, active = int(answers["present_board"]), int(answers["active_board"])
    recruit = answers["need_recruit"] in {"Yes", "Not Sure"}
    reactivate = present > active and answers["reactivate_inactive"] in {
        "Yes — all of them if possible", "Yes — some of them", "Not Sure"}
    activate = answers["board_fundraising_now"] in {"Some do", "Very little", "No", "Not Sure"} and answers["want_fundraising"] == "Yes"
    recommendations = []
    if reactivate:
        recommendations.append("reactivate")
    if recruit:
        recommendations.append("recruit")
    if activate:
        recommendations.append("activate")
    return {
        "present_board": present, "active_board": active,
        "inactive_members": max(0, present - active),
        "recommendations": recommendations,
    }


def build_result(source: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "recruitment": recruitment_result,
        "reactivation": reactivation_result,
        "fundraising_activation": activation_result,
        "board_transformation": board_transformation_result,
    }[source](answers)


async def send_owner_lead_email(lead: Dict[str, Any]) -> str:
    resend.api_key = os.environ["RESEND_API_KEY"]
    subjects = {
        "recruitment": "New Recruitment Lead",
        "reactivation": "New Reactivation Lead",
        "fundraising_activation": "New Fundraising Activation Lead",
        "board_transformation": "New Board Transformation Lead",
        "board_fix": "New Board Fix Lead",
    }
    rows = [
        ("Name", lead["name"]), ("Email", lead["email"]), ("Phone", lead["phone"]),
        ("Organization", lead["organization"]), ("Website", lead.get("website") or "Not provided"),
        ("Location", f"{lead['city']}, {lead['state_region']}, {lead['country']}"),
        ("Offer source", lead["offer_source"]), ("Submission ID", lead["lead_id"]),
        ("Date and time", lead["created_at"]),
    ]
    answers = dict(lead["answers"])
    if lead["offer_source"] == "recruitment":
        support = answers.pop("support_preference", "")
        accomplish = answers.pop("accomplish_areas", [])
        other = str(answers.pop("accomplish_other", "") or "").strip()
        accomplish_text = ", ".join(accomplish) if isinstance(accomplish, list) else str(accomplish)
        if other:
            accomplish_text = f"{accomplish_text}. Other: {other}" if accomplish_text else f"Other: {other}"
        rows.append(("Preferred Level of Support", SUPPORT_PREFERENCES.get(support, support or "Not provided")))
        rows.append(("What They Need Their New Board Members to Help Accomplish", accomplish_text or "Not provided"))
    rows.extend((key.replace("_", " ").title(), ", ".join(value) if isinstance(value, list) else value) for key, value in answers.items())
    table = "".join(f"<tr><td style='padding:9px;border-bottom:1px solid #dddddd;font-weight:bold;vertical-align:top;'>{html.escape(str(label))}</td><td style='padding:9px;border-bottom:1px solid #dddddd;'>{html.escape(str(value))}</td></tr>" for label, value in rows)
    response = await resend.Emails.send_async({
        "from": os.environ["NONPROFIT_SENDER"], "to": [os.environ["OWNER_NOTIFICATION_EMAIL"]],
        "subject": f"{subjects[lead['offer_source']]} — {lead['organization']}",
        "html": f"<div style='max-width:760px;margin:auto;font-family:Arial,sans-serif;color:#000;'><h1>{subjects[lead['offer_source']]}</h1><table style='width:100%;border-collapse:collapse;'>{table}</table></div>",
    })
    return response.get("id") if isinstance(response, dict) else response.id