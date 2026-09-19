import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from resend_service import create_segment_broadcast, send_automation_error
import resend


SALES_EMAILS = {
    1: {
        "theme": "Reactivate the Present Board",
        "subject": "Your Present Board May Not Need to Be Replaced",
        "heading": "Your Present Board May Need to Be Reactivated",
        "paragraphs": [
            "Inactive board members are not always unwilling. Some have never been given clear expectations, meaningful responsibility or a role connected to their strengths.",
            "Nonprofit Board Builder helps you identify who remains committed, give each person a clear opportunity to recommit and allow those who cannot continue to step down respectfully.",
            "We will review your board assessment and explain what needs to happen next.",
        ],
    },
    2: {
        "theme": "Recruit the People Your Board Is Missing",
        "subject": "Stop Recruiting More of the Same Board Members",
        "heading": "Recruit the People Your Present Board Is Missing",
        "paragraphs": [
            "A strong board is not built by adding more names. It is built by identifying the skills, experience, relationships and fundraising capacity missing from the present board and recruiting people who fill those gaps.",
            "Nonprofit Board Builder helps you determine the exact board members your organization needs and build the process required to attract them.",
            "We will review your board and explain who you need to recruit.",
        ],
    },
    3: {
        "theme": "Activate the Board Around Fundraising",
        "subject": "Your Board Cannot Raise Money Without Clear Responsibilities",
        "heading": "Give Every Board Member a Fundraising Role",
        "paragraphs": [
            "Board members cannot support fundraising when nobody has shown them what to do.",
            "Nonprofit Board Builder helps each person contribute through their area of strength—making introductions, contacting businesses, supporting donors, reviewing proposals, building relationships or helping execute the fundraising strategy.",
            "We will review your assessment and explain how to activate your board.",
        ],
    },
    4: {
        "theme": "Build the Complete System",
        "subject": "A Fundraising Board Needs More Than Fundraising Expectations",
        "heading": "Build the Board and the System Together",
        "paragraphs": [
            "Telling board members to raise money is not a fundraising system. They need a clear strategy, defined responsibilities, the right materials, a fundraising team and a process for consistent execution.",
            "Nonprofit Board Builder helps you reactivate present members, recruit the people you are missing and activate the complete board around a system they can execute.",
            "We will contact you with the best way to move forward.",
        ],
    },
}


GUIDED_FOLLOWUPS = {
    "board-recommitment": [
        ("Your board recommitment process is ready", "You already took the first step. Watch the short Board Recommitment walkthrough and see how to give every board member a clear opportunity to recommit, contribute or step down gracefully."),
        ("Stop guessing which board members are still committed", "The recommitment process is designed to give you clear answers before your next board conversation. Your walkthrough is still waiting for you."),
        ("Passive board members need a clear choice", "When expectations stay unclear, disengagement can continue indefinitely. Use the Board Recommitment process to get the answers you need and move forward with clarity."),
        ("Ready to restart your Board Recommitment process?", "Your Board Recommitment walkthrough and guided process are still available. Return when you are ready to continue."),
    ],
    "strategic-planning": [
        ("Your strategic planning process is ready", "You already took the first step. Watch the short walkthrough and see how to build the roadmap with your board, create ownership and begin delegating leadership responsibility."),
        ("A strategic plan works better when the board helps build it", "Bring your board into the planning process so the roadmap is not simply handed to them after it is finished. Your Strategic Planning walkthrough is still waiting for you."),
        ("Turn your next board meeting into a planning meeting", "Use the guided Strategic Planning process to combine board perspectives, build the first draft and move organizational areas into clear leadership responsibility."),
        ("Ready to restart your Strategic Planning process?", "Your Strategic Planning walkthrough and guided process are still available. Return when you are ready to continue."),
    ],
}
GUIDED_FOLLOWUP_DAYS = [0, 2, 5, 10]

def guided_followup_html(lead: Dict[str, Any], subject: str, message: str) -> str:
    origin=(lead.get("origin_url") or "https://nonprofitboardbuilder.com").rstrip("/")
    link=f"{origin}/{lead['product']}/video?token={lead['token']}"
    first=(lead.get("name") or "").split(" ")[0]
    return f"""<div style="max-width:600px;margin:auto;font-family:Arial,sans-serif;color:#111827;font-size:17px;line-height:1.6;padding:28px;">
    <p>Hi {first},</p><p>{message}</p>
    <p style="margin:28px 0;"><a href="{link}" style="display:inline-block;background:#4f46e5;color:#fff;text-decoration:none;font-weight:800;padding:14px 20px;border-radius:8px;">WATCH THE WALKTHROUGH AND CONTINUE</a></p>
    <p>Nonprofit Board Builder</p></div>"""

async def send_guided_followups(db, *, reference: Optional[datetime]=None) -> Dict[str,int]:
    now=reference or utc_now(); processed=sent=0
    leads=await db.guided_product_leads.find({"followup_status":"active","next_followup_at":{"$lte":now.isoformat()}},{"_id":0}).to_list(500)
    resend.api_key=os.environ["RESEND_API_KEY"]
    for lead in leads:
        processed+=1
        paid=await db.payment_transactions.find_one({"guided_lead_token":lead["token"],"payment_status":"paid"},{"_id":0,"session_id":1})
        if paid:
            await db.guided_product_leads.update_one({"token":lead["token"]},{"$set":{"followup_status":"converted","converted_at":now.isoformat()}})
            continue
        templates=GUIDED_FOLLOWUPS.get(lead.get("product"),[])
        step=int(lead.get("followup_step",0))
        if step>=len(templates):
            # The app continues light re-engagement monthly until purchase.
            step=len(templates)-1
            monthly=True
        else:
            monthly=False
        subject,message=templates[step]
        try:
            await resend.Emails.send_async({"from":os.environ["NONPROFIT_SENDER"],"to":[lead["email"]],"subject":subject,"html":guided_followup_html(lead,subject,message)})
            sent+=1
            next_step=step+1
            if monthly or next_step>=len(templates):
                next_at=now+timedelta(days=30)
            else:
                next_at=now+timedelta(days=GUIDED_FOLLOWUP_DAYS[next_step]-GUIDED_FOLLOWUP_DAYS[step])
            await db.guided_product_leads.update_one({"token":lead["token"]},{"$set":{"followup_step":next_step,"last_followup_at":now.isoformat(),"next_followup_at":next_at.isoformat()}})
        except Exception as exc:
            await db.guided_product_leads.update_one({"token":lead["token"]},{"$set":{"followup_error":str(exc)[:500],"next_followup_at":(now+timedelta(days=1)).isoformat()}})
    return {"processed":processed,"sent":sent}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def scheduled_week(reference: datetime) -> str:
    iso = reference.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def theme_number(reference: datetime) -> int:
    return ((reference.isocalendar().week - 1) % 4) + 1


def sales_email_html(template: Dict[str, Any]) -> str:
    paragraphs = "".join(f'<p style="margin:0 0 18px;">{text}</p>' for text in template["paragraphs"][:2])
    closing = template["paragraphs"][2]
    return f"""
    <div style="max-width:600px;margin:0 auto;background:#ffffff;color:#000000;font-family:Arial,sans-serif;font-size:18px;line-height:1.55;padding:32px;">
      <h1 style="margin:0 0 22px;color:#000000;font-size:29px;line-height:1.2;">{template['heading']}</h1>
      {paragraphs}
      <div style="margin:26px 0;padding:28px;background:#000000;color:#ffffff;text-align:center;font-size:22px;line-height:1.5;font-weight:700;">
        I AM READY — YOUR FULL NAME — ORGANIZATION NAME<br>
        +1 719-428-5598
      </div>
      <p style="margin:0 0 18px;">{closing}</p>
      <p style="margin:0 0 24px;"><strong>Nonprofit Board Builder</strong></p>
      <p style="margin:0;font-size:18px;color:#000000;">{os.environ['POSTAL_ADDRESS']}<br>
      <a style="color:#000000;text-decoration:underline;" href="{{{{{{RESEND_UNSUBSCRIBE_URL}}}}}}">Unsubscribe</a></p>
    </div>"""


async def send_weekly_nonprofit_sales_email(
    db, *, reference: Optional[datetime] = None,
    segment_override: Optional[str] = None, send: bool = True,
) -> Dict[str, Any]:
    now = reference or utc_now()
    week = scheduled_week(now)
    number = theme_number(now)
    template = SALES_EMAILS[number]
    duplicate_key = {
        "audience": "Nonprofit Board Builder — Nonprofit Leaders",
        "campaign_theme": template["theme"],
        "scheduled_week": week,
    }
    existing = await db.weekly_sales_emails.find_one(duplicate_key, {"_id": 0})
    if existing:
        return existing
    record = {
        **duplicate_key,
        "resend_broadcast_id": "",
        "send_status": "Preparing",
        "send_date_time": "",
        "error": "",
        "created_at": utc_now().isoformat(),
    }
    try:
        await db.weekly_sales_emails.insert_one(record.copy())
    except Exception:
        return await db.weekly_sales_emails.find_one(duplicate_key, {"_id": 0})
    try:
        broadcast_id = await create_segment_broadcast(
            segment_id=segment_override or os.environ["RESEND_NONPROFIT_LEADERS_SEGMENT_ID"],
            sender=os.environ["NONPROFIT_SENDER"],
            subject=template["subject"],
            html_content=sales_email_html(template),
            name=f"NBB Weekly Sales Email — {template['theme']} — {week}",
            send=send,
        )
        record.update({
            "resend_broadcast_id": broadcast_id,
            "send_status": "Sent" if send else "Draft Test",
            "send_date_time": utc_now().isoformat() if send else "",
        })
        await db.weekly_sales_emails.update_one(duplicate_key, {"$set": record})
    except Exception as exc:
        record.update({"send_status": "Failed", "error": str(exc)[:1000]})
        await db.weekly_sales_emails.update_one(duplicate_key, {"$set": record})
        await send_automation_error(
            db,
            failure_key=f"weekly-sales:{week}:{number}",
            process="Weekly nonprofit sales Broadcast",
            contact_email="",
            error=str(exc),
            submission_saved=True,
            owner_notification_sent=False,
            corrective_action="Review the verified nonprofit sender, Nonprofit Leaders Segment and Resend Broadcast access, then send the approved weekly template manually if required.",
        )
    return record


def schedule_matches(now: datetime) -> bool:
    if os.environ.get("NONPROFIT_WEEKLY_EMAIL_ENABLED", "false").lower() != "true":
        return False
    local = now.astimezone(ZoneInfo(os.environ["NONPROFIT_WEEKLY_EMAIL_TIMEZONE"]))
    hour, minute = map(int, os.environ["NONPROFIT_WEEKLY_EMAIL_TIME"].split(":"))
    return (
        local.strftime("%A").lower() == os.environ["NONPROFIT_WEEKLY_EMAIL_DAY"].lower()
        and local.hour == hour and local.minute == minute
    )


async def automation_loop(db) -> None:
    while True:
        now = utc_now()
        if schedule_matches(now):
            await send_weekly_nonprofit_sales_email(db, reference=now)
        await send_guided_followups(db, reference=now)
        await asyncio.sleep(60)