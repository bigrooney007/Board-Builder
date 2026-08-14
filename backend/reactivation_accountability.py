import asyncio
import uuid
from datetime import datetime, timezone

from accountability_service import CHECKIN_DAYS, origin_url, send_rooney_email, utc_now, within_send_window
from resend_service import send_automation_error

PRODUCT = "reactivation_self_guided"
EMAIL_TYPE = "reactivation_accountability"


def email_html(first_name: str, paragraphs: list, cta_label: str, cta_url: str) -> str:
    import html as html_lib
    parts = ["<div style='background:#ffffff;padding:26px;font-family:Arial,Helvetica,sans-serif;max-width:620px;margin:auto;color:#000;'>"]
    parts.append(f"<p style='font-size:17px;line-height:1.6;margin:0 0 16px;'>Hi {html_lib.escape(first_name) or 'there'},</p>")
    parts.extend(f"<p style='font-size:17px;line-height:1.6;margin:0 0 16px;'>{html_lib.escape(p)}</p>" for p in paragraphs)
    parts.append(f"<p style='margin:24px 0;'><a href='{cta_url}' style='background:#000;color:#fff;padding:14px 22px;text-decoration:none;font-weight:bold;display:inline-block;'>{html_lib.escape(cta_label)}</a></p>")
    parts.append("<p style='font-size:17px;line-height:1.6;margin:24px 0 0;'>Rooney Akpesiri<br/>The Nonprofit Board Builder</p></div>")
    return "".join(parts)


async def reactivation_stage(db, user_id: str) -> dict:
    records = await db.course_progress.find({"user_id": user_id, "product": PRODUCT}, {"_id": 0}).to_list(20)
    completed_modules = {record["module_number"] for record in records if record.get("completed")}
    members = await db.reactivation_board_members.find({"user_id": user_id}, {"_id": 0, "status": 1, "conversation_conclusion": 1, "conversation_outcome": 1}).to_list(200)
    total = len(members)
    sent = sum(1 for m in members if m["status"] in {"SENT", "COMPLETED"})
    responded = sum(1 for m in members if m["status"] == "COMPLETED")
    conversations_done = sum(1 for m in members if (m.get("conversation_conclusion") or "").strip() and m.get("conversation_outcome"))
    active_members = [m for m in members if m.get("conversation_outcome") == "Continuing as an Active Board Member"]
    approved = await db.generated_materials.count_documents({"user_id": user_id, "type": "reactivation_board_member_portfolio", "status": {"$in": ["Approved"]}})
    if all(number in completed_modules for number in range(1, 6)):
        return {"stage": "completed"}
    if total == 0 or sent == 0:
        return {"stage": "start" if 1 not in completed_modules else "send_forms"}
    if responded < sent:
        return {"stage": "follow_up"}
    if conversations_done < responded:
        return {"stage": "conversations"}
    if active_members and approved < len(active_members):
        return {"stage": "portfolios"}
    return {"stage": "my_board"}


STAGE_EMAILS = {
    "start": {"subject": "Let's Reactivate Your Board", "module": 1, "cta": "CONTINUE REACTIVATING MY BOARD", "paragraphs": [
        "You have made the decision to stop carrying a Board that is not functioning the way your organization needs it to function.",
        "Now let's do the work.",
        "Start with Step 1 so you understand why Boards disengage, then move into the Reactivation process.",
        "The goal is simple: find out who is ready to stand up, have the conversations that need to happen, and give the people who remain clear responsibility.",
    ]},
    "send_forms": {"subject": "Have You Sent Your Board Recommitment Forms?", "module": 2, "cta": "GO TO MY RECOMMITMENT FORMS", "paragraphs": [
        "You cannot reactivate your Board by guessing what everyone is thinking.",
        "Your Board Members need the opportunity to tell you where they are, what they realistically have capacity for, and whether they are willing and able to continue serving actively.",
        "If you have not sent the Board Member Profile & Recommitment Form yet, this is the next thing to do.",
        "Send it to your current Board Members and start getting the information you need before the conversations begin.",
    ]},
    "follow_up": {"subject": "Do Not Let the Recommitment Forms Sit There", "module": 2, "cta": "FOLLOW UP WITH MY BOARD", "paragraphs": [
        "If some of your Board Members have not completed their Recommitment Form, follow up.",
        "You already have the reminder email and reminder call script inside your Reactivation workspace.",
        "The goal is not to pressure anyone. The goal is to get clarity.",
        "You need to know who is ready to stand up, who needs greater clarity about their role, and who may no longer have the capacity to carry Board responsibility.",
    ]},
    "conversations": {"subject": "Now Have the Conversations", "module": 3, "cta": "HAVE THE CONVERSATIONS", "paragraphs": [
        "The Recommitment Form gives you information. The conversation gives you clarity.",
        "For each Board Member who has responded, use their individual Difficult Conversation Script and talk through what they are actually willing and able to carry moving forward.",
        "Do not finish the conversation with: \"I'll try to help more.\" Get clarity about what they are prepared to own.",
        "And if active Board service is no longer realistic, have that conversation too.",
    ]},
    "portfolios": {"subject": "Do Not Stop at \"I'll Help More\"", "module": 5, "cta": "GO TO MY BOARD", "paragraphs": [
        "A Board Member saying they will become more active is not the end of the process.",
        "What are they actually going to own?",
        "Once you have completed the conversation, turn what was agreed into their Board Member Portfolio.",
        "That Portfolio gives each continuing Board Member clarity about where they fit, what they will help accomplish and what responsibility they are expected to carry.",
    ]},
    "my_board": {"subject": "Look at the Board You Can Build With Now", "module": 5, "cta": "VIEW MY BOARD", "paragraphs": [
        "You started this process because your Board was not functioning the way your organization needed it to.",
        "Now look at what has changed.",
        "You know who is ready to serve. You know where your continuing members can contribute. You have had the conversations that needed to happen.",
        "And the people who are staying can leave with clear responsibility.",
        "Go to My Board and review the people you can now start building with.",
    ]},
}


def compose_stage_email(first_name: str, stage: str) -> dict:
    template = STAGE_EMAILS.get(stage, STAGE_EMAILS["start"])
    cta_url = f"{origin_url()}/app/reactivation/self-guided/module/{template['module']}"
    return {"subject": template["subject"], "html": email_html(first_name, template["paragraphs"], template["cta"], cta_url), "module": template["module"]}


async def enroll_reactivation_engagement(db, member: dict, purchase: dict) -> dict:
    engagement = await db.reactivation_engagements.find_one({"purchase_id": purchase["purchase_id"]}, {"_id": 0})
    if not engagement:
        active = await db.reactivation_engagements.find_one({"user_id": member["user_id"], "status": "active"}, {"_id": 0})
        if active:
            return active
        now = utc_now().isoformat()
        engagement = {
            "engagement_id": str(uuid.uuid4()), "user_id": member["user_id"],
            "purchase_id": purchase["purchase_id"], "session_id": purchase["session_id"],
            "email": member["email"], "first_name": member.get("first_name", ""),
            "purchased_at": purchase["purchased_at"], "status": "active",
            "welcome_sent_at": "", "completion_sent_at": "", "sends": [],
            "created_at": now, "updated_at": now,
        }
        try:
            await db.reactivation_engagements.insert_one(engagement.copy())
        except Exception:
            engagement = await db.reactivation_engagements.find_one({"purchase_id": purchase["purchase_id"]}, {"_id": 0})
    now = utc_now().isoformat()
    claimed = await db.reactivation_engagements.update_one(
        {"engagement_id": engagement["engagement_id"], "welcome_sent_at": ""},
        {"$set": {"welcome_sent_at": now, "updated_at": now}})
    if claimed.modified_count == 1:
        message = compose_stage_email(engagement.get("first_name", ""), "start")
        try:
            await send_rooney_email(engagement["email"], message["subject"], message["html"])
        except Exception as exc:
            await db.reactivation_engagements.update_one(
                {"engagement_id": engagement["engagement_id"]},
                {"$set": {"welcome_sent_at": "", "welcome_error": str(exc)[:300]}})
    return engagement


async def process_reactivation_engagement(db, engagement: dict, now: datetime, ignore_window: bool = False) -> dict:
    engagement_id = engagement["engagement_id"]
    result = {"engagement_id": engagement_id, "action": "none"}
    purchase = await db.purchases.find_one({"purchase_id": engagement["purchase_id"]}, {"_id": 0})
    if purchase and purchase.get("payment_status") == "refunded":
        await db.reactivation_engagements.update_one({"engagement_id": engagement_id}, {"$set": {"status": "ended_refunded", "updated_at": now.isoformat()}})
        return {**result, "action": "ended_refunded"}
    stage_info = await reactivation_stage(db, engagement["user_id"])
    stage = stage_info["stage"]
    if stage == "completed":
        claimed = await db.reactivation_engagements.update_one(
            {"engagement_id": engagement_id, "completion_sent_at": ""},
            {"$set": {"completion_sent_at": now.isoformat(), "status": "completed", "updated_at": now.isoformat()}})
        if claimed.modified_count == 1:
            message = compose_stage_email(engagement.get("first_name", ""), "my_board")
            try:
                await send_rooney_email(engagement["email"], message["subject"], message["html"])
                result["action"] = "completion_sent"
            except Exception:
                await db.reactivation_engagements.update_one({"engagement_id": engagement_id}, {"$set": {"completion_sent_at": "", "status": "active"}})
                result["action"] = "completion_failed"
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
        return {**result, "action": "outside_window"}
    day = max(due)
    for missed in due[:-1]:
        await db.reactivation_engagements.update_one(
            {"engagement_id": engagement_id, "sends.day": {"$ne": missed}},
            {"$push": {"sends": {"day": missed, "email_type": EMAIL_TYPE, "status": "skipped", "recorded_at": now.isoformat()}}})
    claimed = await db.reactivation_engagements.update_one(
        {"engagement_id": engagement_id, "sends.day": {"$ne": day}},
        {"$push": {"sends": {"day": day, "email_type": EMAIL_TYPE, "status": "sending", "claimed_at": now.isoformat()}}})
    if claimed.modified_count != 1:
        return {**result, "action": "already_claimed"}
    last_stage_sent = next((send.get("stage") for send in reversed(engagement.get("sends", [])) if send.get("status") == "sent"), "")
    message = compose_stage_email(engagement.get("first_name", ""), stage)
    if stage == last_stage_sent and stage in {"send_forms", "follow_up"}:
        message = compose_stage_email(engagement.get("first_name", ""), "follow_up")
        stage = "follow_up"
    try:
        email_id = await send_rooney_email(engagement["email"], message["subject"], message["html"])
        update = {"$set": {"sends.$.status": "sent", "sends.$.sent_at": now.isoformat(), "sends.$.stage": stage,
                           "sends.$.module": message["module"], "sends.$.subject": message["subject"],
                           "sends.$.email_id": email_id, "updated_at": now.isoformat()}}
        if day == max(CHECKIN_DAYS):
            update["$set"]["status"] = "ended"
        await db.reactivation_engagements.update_one({"engagement_id": engagement_id, "sends.day": day}, update)
        result.update({"action": "checkin_sent", "day": day, "stage": stage})
    except Exception as exc:
        await db.reactivation_engagements.update_one({"engagement_id": engagement_id}, {"$pull": {"sends": {"day": day, "status": "sending"}}})
        await send_automation_error(
            db, failure_key=f"reactivation-checkin:{engagement_id}:{day}",
            process=f"Reactivation Day {day} check-in", contact_email=engagement["email"],
            error=str(exc), submission_saved=True, owner_notification_sent=False,
            corrective_action="Verify the Resend sender configuration, then re-run the reactivation accountability processor.")
        result.update({"action": "checkin_failed", "day": day})
    return result


async def process_reactivation_accountability(db, now: datetime = None, ignore_window: bool = False) -> list:
    now = now or utc_now()
    results = []
    async for engagement in db.reactivation_engagements.find({"status": "active"}, {"_id": 0}):
        try:
            results.append(await process_reactivation_engagement(db, engagement, now, ignore_window))
        except Exception as exc:
            results.append({"engagement_id": engagement.get("engagement_id", ""), "action": "error", "error": str(exc)[:300]})
    return results


async def reactivation_accountability_loop(db) -> None:
    while True:
        try:
            await process_reactivation_accountability(db)
        except Exception:
            pass
        await asyncio.sleep(900)
