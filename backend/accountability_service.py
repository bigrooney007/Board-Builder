import asyncio
import html
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import resend

from member_auth import new_uuid
from resend_service import send_automation_error

CHECKIN_DAYS = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 21]
PRODUCT = "recruitment_self_guided"
EMAIL_TYPE = "Recruit With Rooney Accountability"

STAGES = {
    "not_started": {
        "focus": "getting your board recruitment started",
        "opening": "Just checking in. Have you had a chance to start identifying the board members your organization needs?",
        "support": "If something is holding you back or there is anything you need from me before you begin, reply and let me know. Start with Step 1 below and let's get your board recruitment moving.",
        "cta": "START BUILDING MY BOARD",
        "module": 1,
    },
    "module1": {
        "focus": "identifying the board members your organization needs",
        "opening": "I'm checking in to see how you're getting on identifying the board members your organization needs.",
        "support": "If you're stuck on what skills, experience or relationships your board is missing, or you want me to look at anything with you, reply to this email and let me know. I'm right here with you as we build your board.",
        "cta": "CONTINUE BUILDING MY BOARD",
        "module": 1,
    },
    "module2": {
        "focus": "your board recruitment strategy",
        "opening": "How are you getting on with your board recruitment strategy?",
        "support": "This is where we decide exactly how you're going to reach the professionals your board needs. If you're unsure about any of the channels or want my input, reply and let me know.",
        "cta": "CONTINUE BUILDING MY BOARD",
        "module": 2,
    },
    "module3": {
        "focus": "your recruitment launch",
        "opening": "I'm checking in on your recruitment launch. Have you created your recruitment materials and started putting the opportunity in front of potential board members?",
        "support": "If you want me to look at anything before you publish it, or you're unsure what to do next, reply and let me know.",
        "cta": "CONTINUE BUILDING MY BOARD",
        "module": 3,
    },
    "module4": {
        "focus": "your applications and interviews",
        "opening": "How are your applications and interviews going?",
        "support": "If qualified applicants are coming in, keep moving. Review them as they arrive and begin interviewing the people who look like a strong fit. If you need help thinking through an applicant or preparing for an interview, reply and let me know.",
        "cta": "CONTINUE BUILDING MY BOARD",
        "module": 4,
    },
    "module5": {
        "focus": "the candidates you're moving forward with",
        "opening": "You're getting close. How are things going with the candidates you're moving forward with?",
        "support": "If you're stuck on references, agreements, onboarding materials or anything else at this stage, reply to this email and let me know. Let's keep moving so you can bring the right people properly into the organization.",
        "cta": "CONTINUE BUILDING MY BOARD",
        "module": 5,
    },
    "module6": {
        "focus": "bringing your new board members properly into the organization",
        "opening": "You're at the point where we're bringing your new board members properly into the organization.",
        "support": "Make sure the people you've selected understand the organization, their responsibilities and how they can begin contributing. If you want help thinking through the onboarding or your first board meeting, reply and let me know.",
        "cta": "CONTINUE BUILDING MY BOARD",
        "module": 6,
    },
}

ROTATION_OPENINGS = [
    None,
    "I'm checking in again to see where you are with {focus}.",
    "How are things moving with {focus}?",
    "I wanted to check in and see how you're progressing with {focus}.",
    "Have you been able to move this step forward with {focus}?",
]

ROTATION_SUBJECTS = [
    "Checking in on your board recruitment",
    "How is your board recruitment going?",
    "Checking in with you",
    "Where are you with your board recruitment?",
    "Checking in on your board",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def origin_url() -> str:
    return os.environ.get("PUBLIC_ORIGIN", "https://nonprofitboardbuilder.com")


def rooney_sender() -> str:
    raw = os.environ["NONPROFIT_SENDER"]
    address = raw.split("<")[-1].rstrip(">").strip() if "<" in raw else raw.strip().strip('"')
    return f"Rooney Akpesiri <{address}>"


def email_html(first_name: str, paragraphs: list, cta_label: str, cta_url: str) -> str:
    greeting = f"Hi {html.escape(first_name)}," if first_name.strip() else "Hi,"
    body = "".join(f'<p style="margin:0 0 18px;">{html.escape(text)}</p>' for text in paragraphs)
    return (
        '<div style="max-width:560px;margin:0 auto;background:#ffffff;color:#000000;'
        'font-family:Arial,sans-serif;font-size:17px;line-height:1.6;padding:28px;">'
        f'<p style="margin:0 0 18px;">{greeting}</p>{body}'
        f'<p style="margin:24px 0 0;"><a href="{cta_url}" style="display:inline-block;background:#087e5b;'
        'color:#ffffff;padding:14px 26px;border-radius:6px;text-decoration:none;font-weight:bold;'
        f'font-size:16px;">{html.escape(cta_label)}</a></p></div>'
    )


async def send_rooney_email(to_email: str, subject: str, html_body: str) -> str:
    resend.api_key = os.environ["RESEND_API_KEY"]
    response = await resend.Emails.send_async({
        "from": rooney_sender(),
        "to": [to_email],
        "reply_to": os.environ["OWNER_NOTIFICATION_EMAIL"].strip('"'),
        "subject": subject,
        "html": html_body,
    })
    return (response or {}).get("id", "")


async def current_stage(db, user_id: str) -> dict:
    records = await db.course_progress.find(
        {"user_id": user_id, "product": PRODUCT}, {"_id": 0}
    ).to_list(20)
    if not records:
        return {"stage": "not_started", "module": 1}
    completed = {record["module_number"] for record in records if record.get("completed")}
    if all(number in completed for number in range(1, 6)):
        return {"stage": "completed", "module": 5}
    module = next(number for number in range(1, 6) if number not in completed)
    return {"stage": f"module{module}", "module": module}


def compose_checkin(first_name: str, stage: str, variant: int, final_day: bool) -> dict:
    template = STAGES[stage]
    module = template["module"]
    cta_url = f"{origin_url()}/app/recruitment/self-guided/module/{module}"
    if final_day:
        paragraphs = [
            "I'm checking in with you one more time as we come to the end of these three weeks together. "
            "I can see you're still working through your board recruitment, so keep moving.",
            f"From what I can see, you're currently working on {template['focus']}. "
            "If there is something holding you up, reply and tell me exactly where you're stuck. "
            "You still have the Recruitment system and everything we've created for your organization, "
            "so continue from where you are and finish the process.",
        ]
        return {"subject": "One more check-in from me", "html": email_html(first_name, paragraphs, "CONTINUE BUILDING MY BOARD", cta_url), "module": module}
    rotation = ROTATION_OPENINGS[variant % len(ROTATION_OPENINGS)]
    opening = template["opening"] if rotation is None else rotation.format(focus=template["focus"])
    subject = ROTATION_SUBJECTS[variant % len(ROTATION_SUBJECTS)]
    paragraphs = [opening, template["support"]]
    return {"subject": subject, "html": email_html(first_name, paragraphs, template["cta"], cta_url), "module": module}


def compose_welcome(first_name: str) -> dict:
    paragraphs = [
        "Welcome. Over the next two weeks, you and I are going to work through the process of "
        "recruiting the board members your nonprofit needs.",
        "Start with Step 1 now. Follow my instructions as you go, take action, and if there is anywhere "
        "you get stuck or need my help, reply to this email and let me know. I will also be checking in "
        "with you every 48 hours to see how you are getting on.",
    ]
    cta_url = f"{origin_url()}/app/recruitment/self-guided/module/1"
    return {"subject": "Welcome — Let's Build Your Board", "html": email_html(first_name, paragraphs, "START BUILDING MY BOARD", cta_url)}


def compose_completion(first_name: str) -> dict:
    paragraphs = [
        "You did it. You worked through the process and completed your board recruitment journey.",
        "More importantly, you now understand the process and have the tools and resources to recruit "
        "board members again whenever your nonprofit needs them. If you need my help as you begin working "
        "with your new board, you know where to find me.",
    ]
    cta_url = f"{origin_url()}/app/recruitment/self-guided/results"
    return {"subject": "You Built Your Board", "html": email_html(first_name, paragraphs, "VIEW MY RECRUITMENT RESULTS", cta_url)}


async def enroll_rooney_engagement(db, member: dict, purchase: dict) -> dict:
    engagement = await db.rooney_engagements.find_one({"purchase_id": purchase["purchase_id"]}, {"_id": 0})
    if not engagement:
        active = await db.rooney_engagements.find_one({"user_id": member["user_id"], "status": "active"}, {"_id": 0})
        if active:
            return active
        now = utc_now().isoformat()
        engagement = {
            "engagement_id": new_uuid(),
            "user_id": member["user_id"],
            "purchase_id": purchase["purchase_id"],
            "session_id": purchase["session_id"],
            "email": member["email"],
            "first_name": member.get("first_name", ""),
            "purchased_at": purchase["purchased_at"],
            "status": "active",
            "welcome_sent_at": "",
            "completion_sent_at": "",
            "sends": [],
            "created_at": now,
            "updated_at": now,
        }
        try:
            await db.rooney_engagements.insert_one(engagement.copy())
        except Exception:
            engagement = await db.rooney_engagements.find_one({"purchase_id": purchase["purchase_id"]}, {"_id": 0})
    await send_welcome_if_needed(db, engagement)
    return engagement


async def send_welcome_if_needed(db, engagement: dict) -> bool:
    now = utc_now().isoformat()
    claimed = await db.rooney_engagements.update_one(
        {"engagement_id": engagement["engagement_id"], "welcome_sent_at": ""},
        {"$set": {"welcome_sent_at": now, "updated_at": now}},
    )
    if claimed.modified_count != 1:
        return False
    message = compose_welcome(engagement.get("first_name", ""))
    try:
        email_id = await send_rooney_email(engagement["email"], message["subject"], message["html"])
        await db.rooney_engagements.update_one(
            {"engagement_id": engagement["engagement_id"]},
            {"$set": {"welcome_email_id": email_id, "welcome_status": "sent"}},
        )
        return True
    except Exception as exc:
        await db.rooney_engagements.update_one(
            {"engagement_id": engagement["engagement_id"]},
            {"$set": {"welcome_sent_at": "", "welcome_status": "failed", "welcome_error": str(exc)[:400]}},
        )
        await send_automation_error(
            db, failure_key=f"rooney-welcome:{engagement['engagement_id']}",
            process="Recruit With Rooney welcome email", contact_email=engagement["email"],
            error=str(exc), submission_saved=True, owner_notification_sent=False,
            corrective_action="Verify the Resend sender configuration, then re-run the accountability processor.",
        )
        return False


def within_send_window(now: datetime) -> bool:
    local = now.astimezone(ZoneInfo(os.environ.get("LEAD_NURTURE_TIMEZONE", "America/New_York").strip('"')))
    return 8 <= local.hour < 20


async def process_engagement(db, engagement: dict, now: datetime, ignore_window: bool = False) -> dict:
    engagement_id = engagement["engagement_id"]
    result = {"engagement_id": engagement_id, "action": "none"}
    purchase = await db.purchases.find_one({"purchase_id": engagement["purchase_id"]}, {"_id": 0})
    if purchase and purchase.get("payment_status") == "refunded":
        await db.rooney_engagements.update_one(
            {"engagement_id": engagement_id},
            {"$set": {"status": "ended_refunded", "updated_at": now.isoformat()}},
        )
        result["action"] = "ended_refunded"
        return result
    stage_info = await current_stage(db, engagement["user_id"])
    if stage_info["stage"] == "completed":
        claimed = await db.rooney_engagements.update_one(
            {"engagement_id": engagement_id, "completion_sent_at": ""},
            {"$set": {"completion_sent_at": now.isoformat(), "status": "completed", "updated_at": now.isoformat()}},
        )
        if claimed.modified_count == 1:
            message = compose_completion(engagement.get("first_name", ""))
            try:
                email_id = await send_rooney_email(engagement["email"], message["subject"], message["html"])
                await db.rooney_engagements.update_one(
                    {"engagement_id": engagement_id},
                    {"$push": {"sends": {"day": "completion", "email_type": EMAIL_TYPE, "subject": message["subject"],
                                          "module": 6, "stage": "completed", "status": "sent",
                                          "sent_at": now.isoformat(), "email_id": email_id}}},
                )
                result["action"] = "completion_sent"
            except Exception as exc:
                await db.rooney_engagements.update_one(
                    {"engagement_id": engagement_id},
                    {"$set": {"completion_sent_at": "", "status": "active"}},
                )
                await send_automation_error(
                    db, failure_key=f"rooney-completion:{engagement_id}",
                    process="Recruit With Rooney completion email", contact_email=engagement["email"],
                    error=str(exc), submission_saved=True, owner_notification_sent=False,
                    corrective_action="Verify the Resend sender configuration, then re-run the accountability processor.",
                )
                result["action"] = "completion_failed"
        else:
            await db.rooney_engagements.update_one(
                {"engagement_id": engagement_id, "status": "active"},
                {"$set": {"status": "completed", "updated_at": now.isoformat()}},
            )
            result["action"] = "already_completed"
        return result
    purchased_at = datetime.fromisoformat(engagement["purchased_at"])
    if purchased_at.tzinfo is None:
        purchased_at = purchased_at.replace(tzinfo=timezone.utc)
    elapsed_days = int((now - purchased_at).total_seconds() // 86400)
    sent_days = {send["day"] for send in engagement.get("sends", [])}
    due = [day for day in CHECKIN_DAYS if day <= elapsed_days and day not in sent_days]
    if not due:
        return result
    if not ignore_window and not within_send_window(now):
        result["action"] = "outside_window"
        return result
    day = max(due)
    for missed in due[:-1]:
        await db.rooney_engagements.update_one(
            {"engagement_id": engagement_id, "sends.day": {"$ne": missed}},
            {"$push": {"sends": {"day": missed, "email_type": EMAIL_TYPE, "status": "skipped",
                                  "recorded_at": now.isoformat()}}},
        )
    claimed = await db.rooney_engagements.update_one(
        {"engagement_id": engagement_id, "sends.day": {"$ne": day}},
        {"$push": {"sends": {"day": day, "email_type": EMAIL_TYPE, "status": "sending",
                              "claimed_at": now.isoformat()}}},
    )
    if claimed.modified_count != 1:
        result["action"] = "already_claimed"
        return result
    stage = stage_info["stage"]
    variant = sum(1 for send in engagement.get("sends", []) if send.get("stage") == stage and send.get("status") == "sent")
    message = compose_checkin(engagement.get("first_name", ""), stage, variant, final_day=(day == 21))
    try:
        email_id = await send_rooney_email(engagement["email"], message["subject"], message["html"])
        update = {"$set": {"sends.$.status": "sent", "sends.$.sent_at": now.isoformat(),
                           "sends.$.module": message["module"], "sends.$.stage": stage,
                           "sends.$.variant": variant, "sends.$.subject": message["subject"],
                           "sends.$.email_id": email_id, "updated_at": now.isoformat()}}
        if day == 21:
            update["$set"]["status"] = "ended"
        await db.rooney_engagements.update_one(
            {"engagement_id": engagement_id, "sends.day": day}, update,
        )
        result.update({"action": "checkin_sent", "day": day, "stage": stage, "variant": variant})
    except Exception as exc:
        await db.rooney_engagements.update_one(
            {"engagement_id": engagement_id},
            {"$pull": {"sends": {"day": day, "status": "sending"}}},
        )
        await send_automation_error(
            db, failure_key=f"rooney-checkin:{engagement_id}:{day}",
            process=f"Recruit With Rooney Day {day} check-in", contact_email=engagement["email"],
            error=str(exc), submission_saved=True, owner_notification_sent=False,
            corrective_action="Verify the Resend sender configuration, then re-run the accountability processor.",
        )
        result.update({"action": "checkin_failed", "day": day})
    return result


async def process_accountability(db, now: datetime = None, ignore_window: bool = False) -> list:
    now = now or utc_now()
    results = []
    async for engagement in db.rooney_engagements.find({"status": "active"}, {"_id": 0}):
        try:
            results.append(await process_engagement(db, engagement, now, ignore_window))
        except Exception as exc:
            results.append({"engagement_id": engagement.get("engagement_id", ""), "action": "error", "error": str(exc)[:300]})
    return results


async def accountability_loop(db) -> None:
    while True:
        try:
            await process_accountability(db)
        except Exception:
            pass
        await asyncio.sleep(900)
