import asyncio
import uuid
from datetime import datetime, timezone

from accountability_service import CHECKIN_DAYS, origin_url, send_rooney_email, utc_now, within_send_window
from reactivation_accountability import email_html
from resend_service import send_automation_error

PRODUCT = "activation_self_guided"
EMAIL_TYPE = "activation_accountability"
PURCHASE_SOURCE = "direct_diy_board_activation_497"


async def activation_stage(db, user_id: str) -> dict:
    progress = await db.course_progress.find({"user_id": user_id, "product": PRODUCT}, {"_id": 0}).to_list(20)
    completed_modules = {r["module_number"] for r in progress if r.get("completed")}
    form = await db.activation_planning_forms.find_one({"user_id": user_id}, {"_id": 0, "status": 1}) or {}
    participants = await db.activation_participants.find({"user_id": user_id}, {"_id": 0, "status": 1, "responsibility_status": 1, "fp_status": 1}).to_list(300)
    invited = sum(1 for p in participants if p["status"] in {"SENT", "COMPLETED"})
    received = sum(1 for p in participants if p["status"] == "COMPLETED")
    strategy = await db.activation_strategies.find_one({"user_id": user_id}, {"_id": 0, "status": 1}) or {}
    reviewed = await db.activation_participants.count_documents({"user_id": user_id, "review_status": "REVIEWED"})
    adoption = await db.activation_adoptions.find_one({"user_id": user_id}, {"_id": 0}) or {}
    adopted = bool(adoption.get("conclusion", "").strip() and adoption.get("plan_status") in {"Adopted as Presented", "Adopted With Changes"} and adoption.get("finalized"))
    toolkit = await db.activation_toolkits.find_one({"user_id": user_id}, {"_id": 0, "status": 1}) or {}
    agreed = [p for p in participants if p.get("responsibility_status") == "Responsibility Agreed"]
    portfolios_approved = sum(1 for p in participants if p.get("fp_status") in {"Approved", "SENT"})
    if adopted and toolkit.get("status") == "Approved" and agreed and portfolios_approved >= len(agreed):
        return {"stage": "completed"}
    if not progress and 1 not in completed_modules:
        return {"stage": "get_started"}
    if form.get("status") not in {"Approved"}:
        return {"stage": "start_planning"}
    if invited == 0 or received == 0:
        return {"stage": "board_input"}
    if strategy.get("status") not in {"Ready for Board Review"}:
        return {"stage": "build_strategy"}
    if reviewed == 0:
        return {"stage": "board_review"}
    if not adopted:
        return {"stage": "facilitate_adoption"}
    if toolkit.get("status") != "Approved":
        return {"stage": "equip_board"}
    return {"stage": "complete_board"}


STAGE_EMAILS = {
    "get_started": {"subject": "Let's Activate Your Board", "cta": "START ACTIVATING MY BOARD", "path": "/activation-start-here", "paragraphs": [
        "You have made the decision to stop carrying fundraising alone.",
        "Now let's do the work.",
        "Start with Module 1 so you understand how fundraising Board ownership is created, then move into the planning process with your Board.",
        "People who plan together execute together.",
    ]},
    "start_planning": {"subject": "Start the Planning Process With Your Board", "cta": "START THE PLANNING PROCESS", "path": "/app/activation/self-guided/module/2", "paragraphs": [
        "Do not create a fundraising plan and hand it to your Board.",
        "Generate your Board Fundraising Planning Form, review it, approve it and get it in front of your Board Members.",
        "Their ideas, experience and relationships should help shape how your organization raises money.",
    ]},
    "board_input": {"subject": "Get Your Board's Input on the Fundraising Plan", "cta": "GET MY BOARD'S INPUT", "path": "/app/activation/self-guided/module/2", "paragraphs": [
        "Your planning form is ready, but your Board's ideas are still outstanding.",
        "Send each participating Board Member their planning form link, and follow up with anyone who has not responded.",
        "The more of your Board that participates in building the plan, the more of your Board will help execute it.",
    ]},
    "build_strategy": {"subject": "Build the Fundraising Strategy", "cta": "BUILD MY FUNDRAISING STRATEGY", "path": "/app/activation/self-guided/module/3", "paragraphs": [
        "Your Board has shared its ideas. Now turn that thinking into one coherent Fundraising Strategy Plan.",
        "Build the strategy from your intake and the Board's actual responses, review it, and approve it for Board review.",
    ]},
    "board_review": {"subject": "Get the Board to Review the Plan", "cta": "SEND THE PLAN FOR REVIEW", "path": "/app/activation/self-guided/module/3", "paragraphs": [
        "Your Fundraising Strategy Plan is ready for Board review.",
        "Send each Board Member their secure review link so their suggestions and concerns are on the table before the adoption discussion.",
    ]},
    "facilitate_adoption": {"subject": "Facilitate the Adoption of Your Fundraising Plan", "cta": "FACILITATE PLAN ADOPTION", "path": "/app/activation/self-guided/module/4", "paragraphs": [
        "The Board has reviewed the plan. Now bring everyone together, work through the feedback and agree on the direction.",
        "Record the adoption outcome and what each Board Member actually agreed to carry.",
        "This is where participation becomes ownership.",
    ]},
    "equip_board": {"subject": "Equip Your Board to Execute", "cta": "EQUIP MY BOARD", "path": "/app/activation/self-guided/module/5", "paragraphs": [
        "Your plan is adopted. Now give your Board practical tools to begin carrying their part of the work.",
        "Generate your Board Fundraising Execution Toolkit from the adopted strategy and the responsibilities your Board agreed to carry.",
    ]},
    "complete_board": {"subject": "Complete Your Fundraising Board", "cta": "GO TO MY FUNDRAISING BOARD", "path": "/app/activation/self-guided/my-fundraising-board", "paragraphs": [
        "Your Board is equipped. The last step is to give each participating member their individual Fundraising Portfolio.",
        "Go to My Fundraising Board, generate each member's Fundraising Portfolio and send it to them.",
    ]},
    "completed": {"subject": "Your Fundraising Board Is Ready to Execute", "cta": "OPEN MY FUNDRAISING BOARD", "path": "/app/activation/self-guided/my-fundraising-board", "paragraphs": [
        "Your Board helped build the fundraising plan, reviewed and adopted the strategy, agreed how members will help carry the work, and now has the tools and individual direction needed to begin taking action.",
        "Your job now is to keep the plan moving, support Board Members in carrying their responsibilities and keep fundraising connected to the mission.",
    ]},
}


def compose_stage_email(first_name: str, stage: str) -> dict:
    spec = STAGE_EMAILS.get(stage) or STAGE_EMAILS["get_started"]
    cta_url = f"{origin_url()}{spec['path']}"
    return {"subject": spec["subject"], "module": 0,
            "html": email_html(first_name, spec["paragraphs"], spec["cta"], cta_url)}


async def ensure_activation_engagements(db) -> None:
    async for purchase in db.purchases.find({"purchase_source": PURCHASE_SOURCE}, {"_id": 0}):
        existing = await db.activation_engagements.find_one({"purchase_id": purchase["purchase_id"]}, {"_id": 0, "engagement_id": 1})
        if existing:
            continue
        member = await db.members.find_one({"user_id": purchase["user_id"]}, {"_id": 0, "email": 1, "first_name": 1, "user_id": 1})
        if not member or member["email"].lower().endswith("@example.com"):
            continue
        now = utc_now().isoformat()
        engagement = {
            "engagement_id": str(uuid.uuid4()), "user_id": member["user_id"],
            "purchase_id": purchase["purchase_id"], "session_id": purchase.get("session_id", ""),
            "email": member["email"], "first_name": member.get("first_name", ""),
            "purchased_at": purchase["purchased_at"], "status": "active",
            "welcome_sent_at": "", "completion_sent_at": "", "sends": [],
            "created_at": now, "updated_at": now,
        }
        try:
            await db.activation_engagements.insert_one(engagement.copy())
        except Exception:
            continue


async def process_activation_engagement(db, engagement: dict, now: datetime, ignore_window: bool = False) -> dict:
    engagement_id = engagement["engagement_id"]
    result = {"engagement_id": engagement_id, "action": "none"}
    purchase = await db.purchases.find_one({"purchase_id": engagement["purchase_id"]}, {"_id": 0})
    if purchase and purchase.get("payment_status") == "refunded":
        await db.activation_engagements.update_one({"engagement_id": engagement_id}, {"$set": {"status": "ended_refunded", "updated_at": now.isoformat()}})
        return {**result, "action": "ended_refunded"}
    stage_info = await activation_stage(db, engagement["user_id"])
    stage = stage_info["stage"]
    if stage == "completed":
        claimed = await db.activation_engagements.update_one(
            {"engagement_id": engagement_id, "completion_sent_at": ""},
            {"$set": {"completion_sent_at": now.isoformat(), "status": "completed", "updated_at": now.isoformat()}})
        if claimed.modified_count == 1:
            message = compose_stage_email(engagement.get("first_name", ""), "completed")
            try:
                await send_rooney_email(engagement["email"], message["subject"], message["html"])
                result["action"] = "completion_sent"
            except Exception:
                await db.activation_engagements.update_one({"engagement_id": engagement_id}, {"$set": {"completion_sent_at": "", "status": "active"}})
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
        await db.activation_engagements.update_one(
            {"engagement_id": engagement_id, "sends.day": {"$ne": missed}},
            {"$push": {"sends": {"day": missed, "email_type": EMAIL_TYPE, "status": "skipped", "recorded_at": now.isoformat()}}})
    claimed = await db.activation_engagements.update_one(
        {"engagement_id": engagement_id, "sends.day": {"$ne": day}},
        {"$push": {"sends": {"day": day, "email_type": EMAIL_TYPE, "status": "sending", "claimed_at": now.isoformat()}}})
    if claimed.modified_count != 1:
        return {**result, "action": "already_claimed"}
    message = compose_stage_email(engagement.get("first_name", ""), stage)
    try:
        email_id = await send_rooney_email(engagement["email"], message["subject"], message["html"])
        update = {"$set": {"sends.$.status": "sent", "sends.$.sent_at": now.isoformat(), "sends.$.stage": stage,
                           "sends.$.subject": message["subject"], "sends.$.email_id": email_id, "updated_at": now.isoformat()}}
        if day == max(CHECKIN_DAYS):
            update["$set"]["status"] = "ended"
        await db.activation_engagements.update_one({"engagement_id": engagement_id, "sends.day": day}, update)
        result.update({"action": "checkin_sent", "day": day, "stage": stage})
    except Exception as exc:
        await db.activation_engagements.update_one({"engagement_id": engagement_id}, {"$pull": {"sends": {"day": day, "status": "sending"}}})
        await send_automation_error(
            db, failure_key=f"activation-checkin:{engagement_id}:{day}",
            process=f"Activation Day {day} check-in", contact_email=engagement["email"],
            error=str(exc), submission_saved=True, owner_notification_sent=False,
            corrective_action="Verify the Resend sender configuration, then re-run the activation accountability processor.")
        result.update({"action": "checkin_failed", "day": day})
    return result


async def process_activation_accountability(db, now: datetime = None, ignore_window: bool = False) -> list:
    now = now or utc_now()
    await ensure_activation_engagements(db)
    results = []
    async for engagement in db.activation_engagements.find({"status": "active"}, {"_id": 0}):
        try:
            results.append(await process_activation_engagement(db, engagement, now, ignore_window))
        except Exception as exc:
            results.append({"engagement_id": engagement.get("engagement_id", ""), "action": "error", "error": str(exc)[:300]})
    return results


async def activation_accountability_loop(db) -> None:
    while True:
        try:
            await process_activation_accountability(db)
        except Exception:
            pass
        await asyncio.sleep(900)
