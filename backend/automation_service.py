import asyncio
import hashlib
import html
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional
from zoneinfo import ZoneInfo

from resend_service import (
    add_to_segment,
    create_segment_broadcast,
    remove_from_segment,
    send_automation_error,
    update_contact_properties,
)


FUNDRAISING_SIGNALS = {
    "Fundraising", "Corporate partnerships", "Grant development", "Major donors",
    "Making professional introductions", "Connecting the nonprofit with businesses",
    "Connecting nonprofits with businesses", "Corporate partnership conversations",
    "Identifying potential donors", "Introducing major donors",
    "Serving on a fundraising committee", "Helping create fundraising strategy",
    "Creating fundraising strategy",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def reporting_period(reference: Optional[datetime] = None) -> tuple[datetime, datetime]:
    end = reference or utc_now()
    return end - timedelta(days=7), end


def parse_requested_members(value: Any) -> int:
    try:
        return max(int(str(value).strip()), 0)
    except (TypeError, ValueError):
        return 0


def report_id(report_type: str, period_start: datetime) -> str:
    prefix = "NPR" if report_type == "nonprofit" else "APR"
    return f"{prefix}-{period_start.strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"


def secure_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def plural(count: int, singular: str, plural_word: Optional[str] = None) -> str:
    return singular if count == 1 else (plural_word or f"{singular}s")


async def nonprofit_metrics(db, start: datetime, end: datetime) -> Dict[str, int]:
    start_iso, end_iso = start.isoformat(), end.isoformat()
    recent = await db.board_applicants.find(
        {"created_at": {"$gte": start_iso, "$lt": end_iso}}, {"_id": 0}
    ).to_list(10000)
    fundraising_count = sum(
        1 for item in recent
        if FUNDRAISING_SIGNALS.intersection(set(item.get("skills", [])) | set(item.get("fundraising_activities", [])))
    )
    ready_count = sum(1 for item in recent if item.get("availability") in {"Immediately", "Within 30 days"})
    active_count = await db.board_applicants.count_documents({"status": {"$nin": ["Paused", "Withdrawn"]}})
    return {
        "new_applicant_count": len(recent),
        "fundraising_applicant_count": fundraising_count,
        "immediately_available_applicant_count": ready_count,
        "total_active_applicant_count": active_count,
    }


async def applicant_metrics(db, start: datetime, end: datetime) -> Dict[str, int]:
    assessments = await db.board_assessments.find(
        {"submitted_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}}, {"_id": 0}
    ).to_list(10000)
    recruiting = [item for item in assessments if parse_requested_members(item.get("new_board_members_needed")) > 0]
    return {
        "new_board_assessment_count": len(assessments),
        "recruiting_nonprofit_count": len(recruiting),
        "requested_board_member_count": sum(parse_requested_members(item.get("new_board_members_needed")) for item in recruiting),
        "fundraising_need_count": sum(1 for item in assessments if "Fundraising" in item.get("areas_carried_alone", [])),
    }


async def eligible_nonprofits(db) -> list[dict]:
    return await db.nonprofit_contacts.find(
        {"email_permission": True, "resend_sync_status": "Synced"}, {"_id": 0}
    ).to_list(10000)


async def eligible_applicants(db) -> list[dict]:
    return await db.board_applicants.find(
        {"board_opportunity_consent": True, "resend_segment_status": "Synced", "status": {"$nin": ["Paused", "Withdrawn"]}},
        {"_id": 0},
    ).to_list(10000)


def email_footer() -> str:
    return f"""
      <p style="margin-top:28px;font-size:12px;color:#66746c;">{html.escape(os.environ['POSTAL_ADDRESS'])}</p>
      <p style="font-size:12px;"><a href="{{{{{{RESEND_UNSUBSCRIBE_URL}}}}}}">Unsubscribe</a> · <a href="{{{{{{RESEND_PREFERENCES_URL}}}}}}">Manage email preferences</a></p>
    """


def nonprofit_subject(count: int) -> str:
    if count == 0:
        return "Your Weekly Nonprofit Board Building Report"
    if count == 1:
        return "1 Professional With Fundraising Experience Joined Our Board Network This Week"
    return f"{count} Professionals With Fundraising Experience Joined Our Board Network This Week"


def applicant_subject(count: int) -> str:
    if count == 0:
        return "Your Weekly Board Applicant Network Report"
    if count == 1:
        return "1 Nonprofit Said It Wants to Recruit New Board Members This Week"
    return f"{count} Nonprofits Said They Want to Recruit New Board Members This Week"


def nonprofit_email(metrics: Dict[str, int]) -> str:
    new_count = metrics["new_applicant_count"]
    fundraising_count = metrics["fundraising_applicant_count"]
    ready_count = metrics["immediately_available_applicant_count"]
    active_count = metrics["total_active_applicant_count"]
    return f"""
    <div style="font-family:Arial,sans-serif;line-height:1.65;color:#17221c;max-width:700px;margin:auto;">
      <h1 style="color:#083d2a;">Your Weekly Nonprofit Board Building Report</h1>
      <p>Hi {{{{{{first_name}}}}}},</p>
      <p>New professionals are joining the Nonprofit Board Builder Applicant Network because they are interested in using their skills, experience and relationships to serve nonprofits.</p>
      <h2 style="color:#087e5b;">This Week</h2>
      <p><strong>{new_count}</strong> new {plural(new_count, 'professional')} joined the Board Applicant Network.<br>
      <strong>{fundraising_count}</strong> indicated fundraising-related experience or strengths.<br>
      <strong>{ready_count}</strong> said they may be ready to join a board immediately or within 30 days.<br>
      There are now <strong>{active_count}</strong> active {plural(active_count, 'professional')} in the Board Applicant Network.</p>
      <p>These professionals are telling us:</p>
      <ul><li>the skills and experience they can bring;</li><li>the causes they want to support;</li><li>the types of boards they are willing to join;</li><li>how they can contribute to fundraising;</li><li>the locations and communities where they want to serve;</li><li>how much time they are available to commit.</li></ul>
      <p>But qualified professionals cannot join your board if your organization has not started the process.</p>
      <h2 style="color:#083d2a;">Is Your Present Board Helping Your Nonprofit Raise Money and Fulfil Its Mission?</h2>
      <p>Nonprofit Board Builder helps you:</p>
      <ul><li>reactivate present board members;</li><li>identify who is still committed;</li><li>allow inactive members to recommit or step down respectfully;</li><li>identify the exact skills and experience missing from your board;</li><li>recruit qualified new board members;</li><li>activate present and new board members around fundraising;</li><li>build the strategy, team, materials and execution system required to raise money.</li></ul>
      <h2 style="color:#083d2a;">Ready to Transform Your Board?</h2>
      <p>Text:<br><strong>I am ready — [Your Full Name] — [Organization Name]</strong><br>to:<br><strong>+1 719-428-5598</strong></p>
      <p><a href="{{{{{{nonprofit_action_url}}}}}}" style="display:inline-block;background:#087e5b;color:#fff;text-decoration:none;padding:13px 20px;border-radius:5px;font-weight:bold;">Text I Am Ready</a></p>
      <p style="font-size:13px;color:#66746c;">Include your full name and organization name so we can find your board assessment and follow up with you.</p>
      <p>Do not wait until your organization urgently needs money, leadership or board support.<br>Start building the powerhouse fundraising board your nonprofit needs now.</p>
      <p>—<br><strong>Nonprofit Board Builder</strong><br>Helping nonprofits reactivate, recruit and activate powerhouse fundraising boards.</p>
      {email_footer()}
    </div>"""


def applicant_email(metrics: Dict[str, int]) -> str:
    assessment_count = metrics["new_board_assessment_count"]
    recruiting_count = metrics["recruiting_nonprofit_count"]
    requested_count = metrics["requested_board_member_count"]
    fundraising_count = metrics["fundraising_need_count"]
    return f"""
    <div style="font-family:Arial,sans-serif;line-height:1.65;color:#17221c;max-width:700px;margin:auto;">
      <h1 style="color:#083d2a;">Your Weekly Board Applicant Network Report</h1>
      <p>Hi {{{{{{first_name}}}}}},</p>
      <p>Nonprofits are completing the Nonprofit Board Builder assessment because they want to strengthen their present boards and recruit people with the skills, experience and relationships their missions need.</p>
      <h2 style="color:#087e5b;">This Week</h2>
      <p><strong>{assessment_count}</strong> {plural(assessment_count, 'nonprofit')} completed a board assessment.<br>
      <strong>{recruiting_count}</strong> said they want to recruit new board members.<br>
      Together, they indicated a need for approximately <strong>{requested_count}</strong> new board members.<br>
      <strong>{fundraising_count}</strong> said fundraising is one of the areas where they need board support.</p>
      <p>These are potential opportunities currently being reviewed. Completing a Board Applicant profile does not guarantee placement or an introduction.</p>
      <h2 style="color:#083d2a;">Nonprofits Need More Than Names on Their Boards</h2>
      <p>They need people willing to:</p>
      <ul><li>attend meetings consistently;</li><li>accept responsibility;</li><li>contribute their professional skills;</li><li>make meaningful introductions;</li><li>support fundraising;</li><li>strengthen governance;</li><li>help build the organization;</li><li>use their experience and relationships to advance the mission.</li></ul>
      <h2 style="color:#083d2a;">Are You Currently Available to Be Considered?</h2>
      <p>Text:<br><strong>Available to Serve — [Your Full Name]</strong><br>to:<br><strong>+1 719-428-5598</strong></p>
      <p><a href="{{{{{{applicant_action_url}}}}}}" style="display:inline-block;background:#087e5b;color:#fff;text-decoration:none;padding:13px 20px;border-radius:5px;font-weight:bold;">Confirm I Am Available</a></p>
      <p style="font-size:13px;color:#66746c;">Include your full name so we can find your Board Applicant profile and contact you when a suitable opportunity is available.</p>
      <p>Please keep your professional profile, location, availability and board preferences current.<br>We will contact you when we identify an opportunity that may align with your experience, causes and availability.</p>
      <p>—<br><strong>Nonprofit Board Builder — Board Opportunities</strong><br>Connecting committed professionals with nonprofits that need their skills, experience and leadership.</p>
      {email_footer()}
    </div>"""


async def prepare_recipients(
    db, report: Dict[str, Any], recipients: Iterable[Dict[str, Any]], report_type: str,
) -> int:
    count = 0
    public_url = os.environ["PUBLIC_APP_URL"].rstrip("/")
    route = "board-transformation-ready" if report_type == "nonprofit" else "available-to-serve"
    property_key = "nonprofit_action_url" if report_type == "nonprofit" else "applicant_action_url"
    for contact in recipients:
        token = secure_token()
        email = contact["email"].lower()
        full_name = contact.get("name") or f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        organization = contact.get("organization_name", "")
        action_url = f"{public_url}/{route}?token={token}"
        await db.weekly_report_recipients.update_one(
            {"report_id": report["report_id"], "email": email, "report_type": report_type},
            {"$setOnInsert": {
                "report_id": report["report_id"], "report_type": report_type,
                "email": email, "resend_contact_id": contact.get("resend_contact_id", ""),
                "full_name": full_name, "organization_name": organization,
                "token_hash": token_hash(token), "eligible_at": utc_now().isoformat(),
                "action_clicked": False, "no_action_status": "Waiting",
            }},
            upsert=True,
        )
        await update_contact_properties(email, {property_key: action_url})
        count += 1
    return count


async def create_weekly_report(
    db, report_type: str, *, reference: Optional[datetime] = None,
    segment_override: Optional[str] = None, recipients_override: Optional[list[dict]] = None,
    send: bool = True,
) -> Dict[str, Any]:
    start, end = reporting_period(reference)
    period_key = start.date().isoformat()
    existing = await db.weekly_reports.find_one(
        {"report_type": report_type, "period_start_key": period_key}, {"_id": 0}
    )
    if existing:
        return existing
    identifier = report_id(report_type, start)
    metrics = await (nonprofit_metrics(db, start, end) if report_type == "nonprofit" else applicant_metrics(db, start, end))
    recipients = recipients_override if recipients_override is not None else await (eligible_nonprofits(db) if report_type == "nonprofit" else eligible_applicants(db))
    report = {
        "report_id": identifier, "report_type": report_type, "period_start_key": period_key,
        "reporting_period_start": start.isoformat(), "reporting_period_end": end.isoformat(),
        **metrics,
        ("eligible_nonprofit_recipient_count" if report_type == "nonprofit" else "eligible_applicant_recipient_count"): len(recipients),
        "resend_broadcast_id": "",
        "send_status": "Preparing", "sent_at": "", "no_action_processing_status": "Waiting",
        "error_details": "", "created_at": utc_now().isoformat(),
    }
    try:
        await db.weekly_reports.insert_one(report.copy())
    except Exception:
        return await db.weekly_reports.find_one(
            {"report_type": report_type, "period_start_key": period_key}, {"_id": 0}
        )
    try:
        await prepare_recipients(db, report, recipients, report_type)
        if report_type == "nonprofit":
            segment_id = segment_override or os.environ["RESEND_SEGMENT_NONPROFIT_LEADERS_ID"]
            subject, body, sender = nonprofit_subject(metrics["fundraising_applicant_count"]), nonprofit_email(metrics), os.environ["NONPROFIT_SENDER"]
        else:
            segment_id = segment_override or os.environ["RESEND_SEGMENT_BOARD_APPLICANTS_ID"]
            subject, body, sender = applicant_subject(metrics["recruiting_nonprofit_count"]), applicant_email(metrics), os.environ["BOARD_APPLICANT_SENDER"]
        broadcast_id = await create_segment_broadcast(
            segment_id=segment_id, sender=sender, subject=subject, html_content=body,
            name=f"{report_type.title()} Weekly Report — {start.date().isoformat()}", send=send,
        )
        report.update({
            "resend_broadcast_id": broadcast_id,
            "send_status": "Sent" if send else "Draft Test",
            "sent_at": utc_now().isoformat() if send else "",
        })
        await db.weekly_reports.update_one({"report_id": identifier}, {"$set": report})
    except Exception as exc:
        report.update({"send_status": "Failed", "error_details": str(exc)[:1000]})
        await db.weekly_reports.update_one({"report_id": identifier}, {"$set": report})
        await send_automation_error(
            db, failure_key=f"weekly:{identifier}", automation=f"Weekly {report_type} report",
            contact_or_report_type=report_type, error=str(exc), submission_saved=True,
            email_sent=False, corrective_action="Review the Resend segment, sender verification and Broadcast API configuration, then create the report manually if required.",
        )
    return report


async def process_no_action(db, *, reference: Optional[datetime] = None) -> int:
    cutoff = (reference or utc_now()) - timedelta(hours=72)
    reports = await db.weekly_reports.find(
        {"send_status": "Sent", "sent_at": {"$lte": cutoff.isoformat()}, "no_action_processing_status": {"$ne": "Completed"}},
        {"_id": 0},
    ).to_list(1000)
    processed = 0
    for report in reports:
        try:
            recipients = await db.weekly_report_recipients.find(
                {"report_id": report["report_id"], "action_clicked": False, "no_action_status": "Waiting"}, {"_id": 0}
            ).to_list(10000)
            segment_id = os.environ[
                "RESEND_SEGMENT_NONPROFIT_NO_ACTION_ID" if report["report_type"] == "nonprofit" else "RESEND_SEGMENT_APPLICANT_NO_ACTION_ID"
            ]
            for recipient in recipients:
                await add_to_segment(recipient["email"], segment_id)
                await db.weekly_report_recipients.update_one(
                    {"report_id": report["report_id"], "email": recipient["email"]},
                    {"$set": {"no_action_status": "Added", "no_action_processed_at": utc_now().isoformat()}},
                )
            await db.weekly_reports.update_one(
                {"report_id": report["report_id"]},
                {"$set": {"no_action_processing_status": "Completed", "no_action_processed_at": utc_now().isoformat()}},
            )
            processed += 1
        except Exception as exc:
            await db.weekly_reports.update_one(
                {"report_id": report["report_id"]},
                {"$set": {"no_action_processing_status": "Failed", "no_action_error": str(exc)[:1000]}},
            )
            await send_automation_error(
                db, failure_key=f"no-action:{report['report_id']}", automation="72-hour No Action processing",
                contact_or_report_type=report["report_type"], error=str(exc), submission_saved=True,
                email_sent=False, corrective_action="Review Resend contact and No Action segment access, then place unresponsive contacts in the correct segment manually.",
            )
    return processed


async def record_action(db, action_type: str, token: str) -> Optional[Dict[str, str]]:
    report_type = "nonprofit" if action_type == "board-transformation-ready" else "applicant"
    recipient = await db.weekly_report_recipients.find_one(
        {"token_hash": token_hash(token), "report_type": report_type}, {"_id": 0}
    )
    if not recipient:
        return None
    now = utc_now().isoformat()
    status = "Ready for Board Transformation" if report_type == "nonprofit" else "Available to Serve"
    await db.weekly_report_recipients.update_one(
        {"report_id": recipient["report_id"], "email": recipient["email"]},
        {"$set": {"action_clicked": True, "click_date_time": now, "status": status, "no_action_status": "Removed"}},
    )
    if report_type == "nonprofit":
        await db.nonprofit_contacts.update_one(
            {"email": recipient["email"]}, {"$set": {"weekly_action_status": status, "weekly_action_at": now}}
        )
        segment_id = os.environ["RESEND_SEGMENT_NONPROFIT_NO_ACTION_ID"]
        message = f"I am ready — {recipient['full_name']} — {recipient.get('organization_name', '')}".strip(" —")
    else:
        await db.board_applicants.update_one(
            {"email": recipient["email"]}, {"$set": {"weekly_action_status": status, "weekly_action_at": now}}
        )
        segment_id = os.environ["RESEND_SEGMENT_APPLICANT_NO_ACTION_ID"]
        message = f"Available to Serve — {recipient['full_name']}"
    await remove_from_segment(recipient["email"], segment_id)
    return {"phone": "+17194285598", "display_phone": "+1 719-428-5598", "message": message, "status": status}


def schedule_matches(prefix: str, now: datetime) -> bool:
    if os.environ.get(f"{prefix}_ENABLED", "false").lower() != "true":
        return False
    zone_now = now.astimezone(ZoneInfo(os.environ[f"{prefix}_TIMEZONE"]))
    target_hour, target_minute = map(int, os.environ[f"{prefix}_TIME"].split(":"))
    return zone_now.strftime("%A").lower() == os.environ[f"{prefix}_DAY"].lower() and zone_now.hour == target_hour and zone_now.minute == target_minute


async def automation_loop(db) -> None:
    while True:
        now = utc_now()
        try:
            if schedule_matches("NONPROFIT_WEEKLY_REPORT", now):
                await create_weekly_report(db, "nonprofit", reference=now)
            if schedule_matches("APPLICANT_WEEKLY_REPORT", now):
                await create_weekly_report(db, "applicant", reference=now)
            await process_no_action(db, reference=now)
        except Exception as exc:
            await send_automation_error(
                db, failure_key=f"scheduler:{now.strftime('%Y-%m-%dT%H')}", automation="Weekly report scheduler",
                contact_or_report_type="scheduler", error=str(exc), submission_saved=True,
                email_sent=False, corrective_action="Review scheduler environment settings and backend logs.",
            )
        await asyncio.sleep(60)