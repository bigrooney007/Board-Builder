"""Small shared guards for paid setup, profile approval and saved collections."""
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException

GROUP_PRODUCTS = {"board-fundraising-game", "strategic-planning"}
PROFILE_KEY = "recruitment_assessment_profiles"


def require_setup(journey):
    if not journey.get("setup_complete"):
        raise HTTPException(409, "Complete your organization details after payment before opening these resources.")


def validate_meeting(value):
    if not isinstance(value, dict):
        raise HTTPException(422, "Set your next board meeting date, time and timezone.")
    meeting = {key: str(value.get(key, "")).strip()[:100] for key in ("date", "time", "timezone")}
    try:
        datetime.strptime(meeting["date"], "%Y-%m-%d")
        datetime.strptime(meeting["time"], "%H:%M")
        ZoneInfo(meeting["timezone"])
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise HTTPException(422, "Choose a valid meeting date, time and timezone.") from exc
    return meeting


async def approved_profiles(db, journey):
    if journey.get("product") != "recruit":
        return None
    resource = await db.v2_resources.find_one({"journey_id": journey["journey_id"], "key": PROFILE_KEY, "submission_id": ""}, {"_id": 0})
    if not resource or resource.get("status") != "approved" or resource.get("approved_revision") != resource.get("revision"):
        return None
    return next((version for version in resource.get("approved_versions", []) if version["revision"] == resource["revision"]), None)


async def require_pack_profiles(db, journey):
    if journey.get("product") == "recruit" and not await approved_profiles(db, journey):
        raise HTTPException(409, "Review and approve the board member recruitment profiles before preparing your recruitment pack.")


async def require_open_group(db, journey):
    final = await db.v2_resources.find_one({"journey_id": journey["journey_id"], "key": {"$in": ["final_strategy", "final_plan"]}, "status": "approved"}, {"_id": 0})
    if final:
        raise HTTPException(409, "Your final document is approved and saved. Download it from your resource collection.")


def resource_usage(resource):
    key = resource.get("key", "")
    if key == PROFILE_KEY:
        return "Use these approved profiles to describe the people and contributions your organization needs. Your recruitment materials use these exact approved profiles."
    if key == "participant_form":
        return "Share the online form link with the people you want to involve. The printable version is available for reference. Completed online responses notify you by email."
    if key in {"final_strategy", "final_plan"}:
        return "Download this approved document and share it with your board and contributors. Your organization can now carry out the decisions independently."
    if key in {"interview_guide", "reactivation_conversation_script"}:
        return "Use this guide to prepare your conversation with this person. Their original response remains available separately."
    if key == "facilitation_guide":
        return "Read this before your meeting and keep it beside you while you guide the group through discussion and approval."
    if "invitation" in key or key in {"interview_invitation", "before_interview_rejection", "recommitment_appreciation"}:
        return "Copy the approved message into your email account, add any necessary practical details, and send it to the intended recipient."
    if resource.get("group") == "References and appointments":
        return "Download the editable template and complete the candidate-specific details before using it. Record only reference information and appointment decisions your organization has actually confirmed."
    if resource.get("group") == "Recruitment campaign":
        return "Use this approved material to promote your board opportunity. Share the application link after you confirm your campaign launch."
    return "Download or copy this approved resource and use it with your organization. Complete any clearly marked blank fields in your downloaded copy where applicable."
