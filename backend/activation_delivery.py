"""Email-led Board Fundraising Activation delivery: setup state, factual tracking, deterministic emails. ZERO AI."""
import html
import logging
import os
import secrets
from datetime import date, datetime, timedelta, timezone

import resend
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from member_auth import authenticate_member, require_entitlement

logger = logging.getLogger(__name__)

DWR_SOURCE = "activate_my_board_with_rooney_2997"
SETTINGS_KEY = "activation_delivery"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _origin() -> str:
    return os.environ.get("PUBLIC_ORIGIN") or "https://nonprofitboardbuilder.com"


def _email_html(body: str, buttons: list) -> str:
    rendered = "".join(
        f"<p style='margin:26px 8px 26px 0;display:inline-block;'><a href='{html.escape(url)}' "
        f"style='background:{'#000' if index == 0 else '#fff'};color:{'#fff' if index == 0 else '#000'};"
        f"border:2px solid #000;padding:14px 22px;text-decoration:none;font-weight:bold;display:inline-block;'>"
        f"{html.escape(label)}</a></p>"
        for index, (label, url) in enumerate(buttons))
    paragraphs = []
    for block in body.split("\n\n"):
        if block.strip() == "[BUTTONS]":
            paragraphs.append(f"<div>{rendered}</div>")
        else:
            paragraphs.append(f"<p style='margin:0 0 16px;'>{html.escape(block).replace(chr(10), '<br/>')}</p>")
    return f"<div style='max-width:640px;margin:auto;font-family:Arial,sans-serif;color:#000;font-size:16px;line-height:1.55;'>{''.join(paragraphs)}</div>"


async def _send_email(to: str, subject: str, body: str, buttons: list) -> bool:
    try:
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        await resend.Emails.send_async({
            "from": os.environ["NONPROFIT_SENDER"], "to": [to],
            "subject": subject, "html": _email_html(body, buttons),
        })
        return True
    except Exception:
        logger.exception("Activation delivery email failed (%s)", subject)
        return False


async def _customer_context(db, user_id: str) -> dict:
    member = await db.members.find_one({"user_id": user_id}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1}) or {}
    intake = await db.board_activation_intakes.find_one({"user_id": user_id}, {"_id": 0, "organization_name": 1, "your_name": 1, "email": 1}, sort=[("submitted_at", -1)]) or {}
    name = f"{member.get('first_name', '')} {member.get('last_name', '')}".strip() or intake.get("your_name", "")
    return {
        "first_name": (name.split(" ")[0] if name else "there"),
        "full_name": name,
        "email": member.get("email", "") or intake.get("email", ""),
        "organization": intake.get("organization_name", "") or "your organization",
    }


async def _counts(db, user_id: str, expected: int) -> dict:
    participants = await db.activation_participants.find({"user_id": user_id}, {"_id": 0, "name": 1, "status": 1}).to_list(300)
    received = sum(1 for p in participants if p.get("status") == "COMPLETED")
    outstanding_names = [p.get("name", "") for p in participants if p.get("status") != "COMPLETED"]
    return {
        "expected": expected,
        "received": received,
        "outstanding": max(expected - received, 0),
        "outstanding_names": outstanding_names,
        "sent": sum(1 for p in participants if p.get("status") in {"SENT", "COMPLETED"}),
        "total": len(participants),
    }


async def _engagement_type(db, user_id: str) -> str:
    purchase = await db.purchases.find_one({"user_id": user_id, "purchase_source": DWR_SOURCE}, {"_id": 0, "purchase_id": 1})
    return "dwr" if purchase else "diy"


async def get_lead_days(db):
    doc = await db.marketing_settings.find_one({"key": SETTINGS_KEY}, {"_id": 0}) or {}
    value = doc.get("meeting_readiness_lead_days")
    return value if isinstance(value, int) and value >= 0 else None


async def _notify_ready(db, delivery: dict, counts: dict, reason: str) -> None:
    context = await _customer_context(db, delivery["user_id"])
    origin = _origin()
    basis = ("All expected responses were received."
             if reason == "all_responses"
             else "The client authorized proceeding with the responses received so far.")
    if delivery.get("engagement_type") == "dwr":
        claim = await db.activation_delivery.update_one(
            {"user_id": delivery["user_id"], "rooney_notified_at": {"$in": [None, ""]}},
            {"$set": {"rooney_notified_at": _now()}})
        if claim.modified_count:
            body = (
                "It is time to build the Fundraising Strategy for this Done-With-Rooney Activation client.\n\n"
                f"Client name: {context['full_name']}\n"
                f"Organization: {context['organization']}\n"
                "Engagement type: Activate My Board With Rooney ($2,997 — Done With You)\n"
                f"Expected responses: {counts['expected']}\n"
                f"Responses received: {counts['received']}\n"
                f"Board meeting date: {delivery.get('next_board_meeting_date', '')}\n"
                f"Readiness basis: {basis}\n\n"
                "Open the client workspace to review every planning response and build the Fundraising Strategy. "
                "Strategy generation remains fully under your control — nothing has been generated automatically.\n\n"
                "[BUTTONS]"
            )
            await _send_email(
                os.environ["OWNER_NOTIFICATION_EMAIL"],
                f"ACTION REQUIRED: Build Fundraising Strategy | {context['organization']}",
                body, [("OPEN CLIENT WORKSPACE", f"{origin}/admin")])
    else:
        claim = await db.activation_delivery.update_one(
            {"user_id": delivery["user_id"], "diy_ready_email_sent_at": {"$in": [None, ""]}},
            {"$set": {"diy_ready_email_sent_at": _now()}})
        if claim.modified_count and context["email"]:
            body = (
                f"Dear {context['first_name']},\n\n"
                f"Your Board's Fundraising Planning responses for {context['organization']} are now ready for the next step.\n\n"
                f"Expected responses: {counts['expected']}\n"
                f"Responses received: {counts['received']}\n\n"
                "Return to your Board Fundraising Activation workspace to build and review your Fundraising Strategy. "
                "After that, you will receive the communication to send your Board and the Review & Adoption Facilitation Guide you need to take the plan to your Board meeting.\n\n"
                "[BUTTONS]\n\n"
                "Thank you,\nNonprofit Board Builder"
            )
            await _send_email(
                context["email"],
                f"Your Board Fundraising Strategy Is Ready for the Next Step | {context['organization']}",
                body, [("BUILD MY FUNDRAISING STRATEGY", f"{origin}/app/activation/resources")])


async def mark_ready(db, delivery: dict, reason: str) -> bool:
    counts = await _counts(db, delivery["user_id"], int(delivery.get("expected_planning_responses", 0)))
    result = await db.activation_delivery.update_one(
        {"user_id": delivery["user_id"], "ready": {"$ne": True}},
        {"$set": {
            "ready": True, "ready_reason": reason, "ready_at": _now(),
            "ready_responses_received": counts["received"],
            "ready_responses_expected": counts["expected"],
            "authorized_with_incomplete_responses": reason == "customer_authorized",
            "updated_at": _now()}})
    if not result.modified_count:
        return False
    await _notify_ready(db, delivery, counts, reason)
    return True


async def run_activation_delivery_checks(db) -> None:
    """Deterministic loop: readiness by response count, 3-day outstanding reminder, meeting-readiness email. ZERO AI."""
    if os.environ.get("DB_NAME") == "test_database":
        return
    if os.environ.get("ACTIVATION_DELIVERY_EMAILS_ENABLED", "true").lower() != "true":
        return
    lead_days = await get_lead_days(db)
    now = datetime.now(timezone.utc)
    docs = await db.activation_delivery.find(
        {"launched_at": {"$nin": [None, ""]}, "ready": {"$ne": True}}, {"_id": 0}).to_list(200)
    for delivery in docs:
        try:
            expected = int(delivery.get("expected_planning_responses", 0))
            counts = await _counts(db, delivery["user_id"], expected)
            if expected > 0 and counts["received"] >= expected:
                await mark_ready(db, delivery, "all_responses")
                continue
            context = None
            launched = datetime.fromisoformat(delivery["launched_at"])
            if not delivery.get("three_day_reminder_sent_at") and now >= launched + timedelta(days=3):
                claim = await db.activation_delivery.update_one(
                    {"user_id": delivery["user_id"], "three_day_reminder_sent_at": {"$in": [None, ""]}},
                    {"$set": {"three_day_reminder_sent_at": _now()}})
                if claim.modified_count:
                    context = await _customer_context(db, delivery["user_id"])
                    names = ", ".join(n for n in counts["outstanding_names"] if n)
                    body = (
                        f"Dear {context['first_name']},\n\n"
                        f"We are still waiting for some of your Board Members to complete the Fundraising Planning Form for {context['organization']}.\n\n"
                        f"Expected responses: {counts['expected']}\n"
                        f"Responses received: {counts['received']}\n"
                        f"Still outstanding: {counts['outstanding']}\n\n"
                        + (f"Still waiting on: {names}\n\n" if names else "")
                        + "Please contact the Board Members who have not yet responded and ask them to complete their form so we can bring everyone's ideas together before your upcoming Board meeting.\n\n"
                        "You do not need to log back into the platform at this stage. We will continue monitoring the responses and let you know when it is time for the next step.\n\n"
                        "Thank you,\nNonprofit Board Builder"
                    )
                    if context["email"]:
                        await _send_email(context["email"], f"Board Fundraising Planning — Responses Still Outstanding | {context['organization']}", body, [])
            if lead_days is None or delivery.get("readiness_email_sent_at") or delivery.get("proceed_decision") == "yes":
                continue
            meeting = delivery.get("next_board_meeting_date", "")
            try:
                meeting_date = date.fromisoformat(meeting)
            except (TypeError, ValueError):
                continue
            if now.date() >= meeting_date - timedelta(days=lead_days):
                claim = await db.activation_delivery.update_one(
                    {"user_id": delivery["user_id"], "readiness_email_sent_at": {"$in": [None, ""]}},
                    {"$set": {"readiness_email_sent_at": _now()}})
                if claim.modified_count:
                    context = context or await _customer_context(db, delivery["user_id"])
                    origin = _origin()
                    token = delivery["proceed_token"]
                    body = (
                        f"Dear {context['first_name']},\n\n"
                        "Your next Board meeting is approaching and we are still waiting for some of the Fundraising Planning Forms.\n\n"
                        f"Expected responses: {counts['expected']}\n"
                        f"Responses received: {counts['received']}\n"
                        f"Still outstanding: {counts['outstanding']}\n\n"
                        "We can either continue waiting for the remaining responses or move forward using the information and Board input we have received so far.\n\n"
                        "Would you like us to proceed with the responses currently available?\n\n"
                        "[BUTTONS]\n\n"
                        "Thank you,\nNonprofit Board Builder"
                    )
                    if context["email"]:
                        await _send_email(
                            context["email"], f"Your Board Meeting Is Approaching | {context['organization']}", body,
                            [("YES — PROCEED WITH THE RESPONSES WE HAVE", f"{origin}/api/activation/proceed/{token}?decision=yes"),
                             ("NO — I WANT TO WAIT FOR MORE RESPONSES", f"{origin}/api/activation/proceed/{token}?decision=no")])
        except Exception:
            logger.exception("Activation delivery check failed for %s", delivery.get("user_id"))


class DeliverySetup(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    expected_planning_responses: int = Field(ge=1, le=300)
    next_board_meeting_date: str = Field(min_length=1)
    meeting_time: str = ""


def _page(title: str, message: str) -> HTMLResponse:
    return HTMLResponse(
        "<div style='font-family:Arial,Helvetica,sans-serif;padding:48px;text-align:center;max-width:640px;margin:auto;'>"
        f"<h2>{html.escape(title)}</h2><p style='font-size:17px;line-height:1.6;'>{html.escape(message)}</p></div>")


def create_activation_delivery_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def activation_member(request: Request) -> dict:
        member = await authenticate_member(request, db)
        require_entitlement(member, {"activation_self_guided"})
        return member

    def public_delivery(delivery: dict) -> dict:
        return {key: delivery.get(key, "") for key in [
            "expected_planning_responses", "next_board_meeting_date", "meeting_time",
            "launched_at", "ready", "ready_reason", "ready_at", "proceed_decision",
            "engagement_type", "three_day_reminder_sent_at", "readiness_email_sent_at"]}

    @router.get("/activation/delivery")
    async def delivery_state(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        delivery = await db.activation_delivery.find_one({"user_id": user_id}, {"_id": 0}) or {}
        if not delivery.get("engagement_type"):
            delivery["engagement_type"] = await _engagement_type(db, user_id)
        counts = await _counts(db, user_id, int(delivery.get("expected_planning_responses", 0) or 0))
        form = await db.activation_planning_forms.find_one({"user_id": user_id}, {"_id": 0, "status": 1}) or {}
        intake = await db.board_activation_intakes.find_one({"user_id": user_id}, {"_id": 0, "intake_id": 1}, sort=[("submitted_at", -1)])
        return {
            "delivery": public_delivery(delivery),
            "progress": counts,
            "form_status": form.get("status", "NONE"),
            "has_intake": bool(intake),
            "operator": bool(member.get("operator_mode")),
        }

    @router.put("/activation/delivery/setup")
    async def save_setup(payload: DeliverySetup, request: Request):
        member = await activation_member(request)
        try:
            date.fromisoformat(payload.next_board_meeting_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Enter the Board meeting date as a valid date") from exc
        now = _now()
        await db.activation_delivery.update_one(
            {"user_id": member["user_id"]},
            {"$set": {
                "expected_planning_responses": payload.expected_planning_responses,
                "next_board_meeting_date": payload.next_board_meeting_date,
                "meeting_time": payload.meeting_time, "updated_at": now},
             "$setOnInsert": {"user_id": member["user_id"], "created_at": now}},
            upsert=True)
        return {"status": "saved"}

    @router.post("/activation/delivery/launch")
    async def launch(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        delivery = await db.activation_delivery.find_one({"user_id": user_id}, {"_id": 0}) or {}
        if delivery.get("launched_at"):
            return {"status": "launched", "launched_at": delivery["launched_at"]}
        if not delivery.get("expected_planning_responses") or not delivery.get("next_board_meeting_date"):
            raise HTTPException(status_code=409, detail="Enter how many responses you expect and your next Board meeting date first")
        form = await db.activation_planning_forms.find_one({"user_id": user_id}, {"_id": 0, "status": 1}) or {}
        if form.get("status") != "Approved":
            raise HTTPException(status_code=409, detail="Approve your Board Fundraising Planning Form before starting the tracking process")
        counts = await _counts(db, user_id, int(delivery["expected_planning_responses"]))
        if counts["sent"] < 1:
            raise HTTPException(status_code=409, detail="Send the Planning Form to at least one Board Member before starting the tracking process")
        now = _now()
        await db.activation_delivery.update_one(
            {"user_id": user_id},
            {"$set": {
                "launched_at": now,
                "engagement_type": await _engagement_type(db, user_id),
                "proceed_token": delivery.get("proceed_token") or secrets.token_urlsafe(32),
                "updated_at": now}})
        return {"status": "launched", "launched_at": now}

    @router.get("/activation/proceed/{token}")
    async def proceed(token: str, decision: str = ""):
        delivery = await db.activation_delivery.find_one({"proceed_token": token}, {"_id": 0})
        if not delivery or not delivery.get("launched_at"):
            return _page("This link is not valid", "Please contact us if you believe this is an error.")
        if decision not in {"yes", "no"}:
            return _page("Choice not recognized", "Please use one of the two buttons in the email we sent you.")
        organization = (await _customer_context(db, delivery["user_id"]))["organization"]
        if delivery.get("ready"):
            return _page("Your Fundraising Strategy Process Is Already Moving Forward",
                         f"The planning process for {organization} has already moved to the strategy stage. We will be in touch by email about the next step.")
        now = _now()
        await db.activation_delivery.update_one(
            {"user_id": delivery["user_id"]},
            {"$set": {"proceed_decision": decision, "proceed_decided_at": now, "updated_at": now}})
        if decision == "no":
            return _page("We Will Keep Waiting for More Responses",
                         f"Your choice has been recorded. We will continue tracking the Fundraising Planning responses for {organization} and let you know by email when it is time for the next step. You can change this decision from the same email at any time.")
        await mark_ready(db, delivery, "customer_authorized")
        return _page("Thank You — We Are Moving Forward",
                     f"Your choice has been recorded. The Fundraising Strategy process for {organization} will now move forward using the Board input received so far. Watch your inbox for the next step.")

    return router
