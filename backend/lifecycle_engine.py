"""Customer lifecycle email engines (BFG unpaid/paid, Recruitment unpaid/paid) + accountability stages.
State-based: before every send the contact's CURRENT state is recomputed; obsolete emails are cancelled.
Board Applicant Network operational emails are intentionally untouched by this engine."""
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import resend

INITIAL_OFFSETS_HOURS = [24, 72, 120, 168]  # Day 1 / 3 / 5 / 7
MONTHLY_HOURS = 24 * 30

BFG_STAGES = [
    (1, "COMPLETE YOUR ORGANIZATION INFORMATION", "/game/setup"),
    (2, "INVITE YOUR BOARD MEMBERS AND OTHERS IN YOUR ORGANIZATION", "/game/dashboard"),
    (3, "COMPLETE YOUR BOARD FUNDRAISING DAY/NIGHT", "/game/dashboard"),
    (4, "SEND OUT THE FINAL STRATEGY AND BOARD PORTFOLIOS", "/game/dashboard"),
    (5, "START EXECUTING WITH YOUR BOARD", "/game/dashboard"),
]
RECRUIT_STAGES = [
    (1, "IDENTIFY THE BOARD MEMBERS YOU NEED TO RECRUIT", "/members/recruitment"),
    (2, "LAUNCH YOUR BOARD RECRUITMENT CAMPAIGN", "/members/recruitment"),
    (3, "SELECT AND INTERVIEW BOARD MEMBERS", "/members/recruitment"),
    (4, "RUN REFERENCE AND BACKGROUND CHECKS", "/members/recruitment"),
    (5, "ONBOARD NEW BOARD MEMBERS", "/members/recruitment"),
    (6, "INVITE THEM TO THEIR FIRST BOARD MEETING", "/members/recruitment"),
]


def now():
    return datetime.now(timezone.utc)


def iso(dt=None):
    return (dt or now()).isoformat()


async def compute_bfg_stage(db, member) -> int:
    """Five paid accountability stages. Returns the current INCOMPLETE stage (1-5)."""
    user_id = member["user_id"]
    situation = await db.game_situations.find_one({"user_id": user_id}, {"_id": 0, "completed": 1, "completed_at": 1})
    if not (situation and (situation.get("completed") or situation.get("completed_at"))):
        return 1
    invited = await db.game_board_members.count_documents(
        {"user_id": user_id, "removed": {"$ne": True}, "invitation_status": "invited"})
    if invited < 1:
        return 2
    transcript = await db.game_meeting_transcripts.find_one({"user_id": user_id}, {"_id": 0, "transcript_id": 1})
    group_done = await db.group_game_sessions.find_one({"user_id": user_id, "status": "completed"}, {"_id": 0, "session_id": 1})
    if not (group_done and transcript):
        return 3
    sent = await db.game_board_members.find_one({"user_id": user_id, "strategy_sent_at": {"$exists": True, "$nin": ["", None]}}, {"_id": 0})
    delivery = await db.game_postgame_delivery.find_one({"user_id": user_id}, {"_id": 0}) if not sent else None
    if not sent and not (delivery and delivery.get("sent_count", 0) > 0):
        return 4
    return 5


async def compute_recruit_stage(db, member) -> int:
    """Six recruitment accountability stages (best effort from existing collections)."""
    user_id = member["user_id"]
    profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0}) or \
        await db.fbb_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}
    if not profile:
        return 1
    campaign = await db.recruitment_campaigns.find_one({"user_id": user_id}, {"_id": 0}) or {}
    if not campaign:
        return 2
    status = str(campaign.get("status", ""))
    if status in {"", "draft", "launched", "active"}:
        interviewing = await db.applicants.count_documents({"campaign_user_id": user_id, "status": {"$in": ["Interviewing", "Under Review", "Contacted"]}})
        if not interviewing:
            return 3
    checks = await db.applicants.count_documents({"campaign_user_id": user_id, "status": {"$in": ["Reference Check", "Background Check"]}})
    placed = await db.applicants.count_documents({"campaign_user_id": user_id, "status": "Placed on Board"})
    if placed:
        return 6
    if checks:
        return 5
    return 4


def lifecycle_key(product, paid):
    return f"{product}:{'paid' if paid else 'unpaid'}"


async def get_template(db, product, paid, stage, sequence):
    return await db.lifecycle_templates.find_one({
        "product": product, "payment_state": "paid" if paid else "unpaid",
        "stage": stage, "sequence": sequence}, {"_id": 0})


async def upsert_template(db, template):
    await db.lifecycle_templates.update_one(
        {"template_id": template["template_id"]},
        {"$set": {**template, "updated_at": iso()}}, upsert=True)


async def send_lifecycle_email(db, contact, template, deep_link):
    api_key = os.environ.get("RESEND_API_KEY", "")
    status = "sent"
    error = ""
    if not api_key or not template.get("body"):
        status = "skipped"
        error = "missing_api_key" if not api_key else "template_body_pending"
    else:
        try:
            resend.api_key = api_key
            body_html = template["body"].replace("\n", "<br/>")
            first = (contact.get("first_name") or contact.get("name") or "").split(" ")[0]
            body_html = body_html.replace("[FIRST NAME]", first).replace("[First Name]", first)
            button = (f"<p style='margin:24px 0;'><a href='{deep_link}' style='background:#4f46e5;color:#ffffff;"
                      f"padding:12px 22px;border-radius:8px;text-decoration:none;font-weight:700;'>"
                      f"{template.get('cta_label', 'Continue')}</a></p>")
            await resend.Emails.send_async({
                "from": os.environ.get("RESEND_FROM_EMAIL", "Board Fundraising Game <team@boardfundraisinggame.com>"),
                "to": [contact["email"]],
                "subject": template["subject"],
                "html": f"<div style='font-family:Arial,sans-serif;font-size:15px;line-height:1.65;color:#1f2937;'>{body_html}{button}</div>",
            })
        except Exception as exc:  # never crash the loop
            status = "failed"
            error = str(exc)[:300]
    await db.lifecycle_email_log.insert_one({
        "log_id": str(uuid.uuid4()), "email": contact["email"], "user_id": contact.get("user_id", ""),
        "template_id": template.get("template_id", ""), "subject": template.get("subject", ""),
        "product": template.get("product", ""), "lifecycle": template.get("payment_state", ""),
        "stage": template.get("stage", 0), "sequence": template.get("sequence", 0),
        "scheduled_at": contact.get("_due_at", ""), "sent_at": iso(), "status": status, "reason": error,
    })
    return status


def origin_url():
    return os.environ.get("APP_PUBLIC_URL", "").rstrip("/") or "https://nonprofit-board-ai.emergent.host"


async def process_contact_state(db, contact, product, paid, stage, deep_path):
    """Advance/reset lifecycle state, send due emails, cancel obsolete ones."""
    key = {"email": contact["email"], "product": product}
    state = await db.lifecycle_state.find_one(key, {"_id": 0})
    lifecycle = lifecycle_key(product, paid)
    state_sig = f"{lifecycle}:{stage}"
    if not state or state.get("state_sig") != state_sig:
        cancelled = bool(state)
        await db.lifecycle_state.update_one(key, {"$set": {
            **key, "state_sig": state_sig, "lifecycle": lifecycle, "stage": stage,
            "sequence_sent": 0, "entered_at": iso(), "last_sent_at": "", "status": "active",
            "user_id": contact.get("user_id", ""),
        }}, upsert=True)
        if cancelled:
            await db.lifecycle_email_log.insert_one({
                "log_id": str(uuid.uuid4()), "email": contact["email"], "user_id": contact.get("user_id", ""),
                "template_id": "", "subject": "", "product": product,
                "lifecycle": state.get("lifecycle", ""), "stage": state.get("stage", 0),
                "sequence": 0, "scheduled_at": "", "sent_at": iso(),
                "status": "cancelled", "reason": "state_changed"})
        return
    if state.get("status") != "active" or contact.get("lifecycle_optout"):
        return
    entered = datetime.fromisoformat(state["entered_at"])
    sequence_sent = state.get("sequence_sent", 0)
    if sequence_sent < len(INITIAL_OFFSETS_HOURS):
        due = entered + timedelta(hours=INITIAL_OFFSETS_HOURS[sequence_sent])
        next_sequence = sequence_sent + 1
    else:
        last = datetime.fromisoformat(state["last_sent_at"]) if state.get("last_sent_at") else entered
        due = last + timedelta(hours=MONTHLY_HOURS)
        next_sequence = sequence_sent + 1
    if now() < due:
        return
    sequence_number = min(next_sequence, len(INITIAL_OFFSETS_HOURS) + 1)  # 5 == monthly callback template
    template = await get_template(db, product, paid, stage, sequence_number)
    if not template:
        template = await get_template(db, product, paid, 0, sequence_number)  # stage-agnostic fallback
    contact["_due_at"] = iso(due)
    if template:
        deep_link = f"{origin_url()}{template.get('cta_destination') or deep_path}"
        await send_lifecycle_email(db, contact, template, deep_link)
    await db.lifecycle_state.update_one(key, {"$set": {
        "sequence_sent": next_sequence, "last_sent_at": iso()}})


async def scan_once(db):
    members = await db.members.find({}, {"_id": 0, "user_id": 1, "email": 1, "first_name": 1,
                                         "last_name": 1, "entitlements": 1, "lifecycle_optout": 1,
                                         "created_at": 1}).to_list(4000)
    for member in members:
        if not member.get("email"):
            continue
        entitlements = set(member.get("entitlements") or [])
        # --- Board Fundraising Game engine ---
        has_game_activity = bool(await db.game_profiles.find_one({"user_id": member["user_id"]}, {"_id": 0, "user_id": 1}))
        if "board_fundraising_game" in entitlements:
            stage = await compute_bfg_stage(db, member)
            if stage <= 5:
                path = next((p for n, _, p in BFG_STAGES if n == stage), "/game/dashboard")
                completed = stage == 5 and await db.game_relationships.find_one({"user_id": member["user_id"]}, {"_id": 0})
                if not completed:
                    await process_contact_state(db, dict(member), "board_fundraising_game", True, stage, path)
        elif has_game_activity:
            await process_contact_state(db, dict(member), "board_fundraising_game", False, 0, "/game/demonstration")
        # --- Board Recruitment engine ---
        recruitment_paid = bool(entitlements & {"fbb_recruitment", "recruitment_self_guided", "fundraising_board_builder"})
        recruitment_lead = bool(await db.leads.find_one(
            {"$or": [{"email": member["email"]}, {"user_id": member["user_id"]}],
             "offer_source": "recruitment"}, {"_id": 0, "lead_id": 1}))
        if recruitment_paid:
            stage = await compute_recruit_stage(db, member)
            await process_contact_state(db, dict(member), "board_recruitment", True, stage, "/members")
        elif recruitment_lead:
            await process_contact_state(db, dict(member), "board_recruitment", False, 0, "/recruit")
    # --- Unpaid game leads without accounts (captured contacts) ---
    # New-contact admin notification
    await notify_new_contacts(db)


async def notify_new_contacts(db):
    admin_email = os.environ.get("ADMIN_NOTIFICATION_EMAIL", "")
    cursor = db.members.find({"admin_notified": {"$ne": True}}, {"_id": 0, "user_id": 1, "email": 1,
                                                                 "first_name": 1, "last_name": 1, "created_at": 1}).limit(50)
    async for member in cursor:
        if admin_email and os.environ.get("RESEND_API_KEY"):
            try:
                resend.api_key = os.environ["RESEND_API_KEY"]
                await resend.Emails.send_async({
                    "from": os.environ.get("RESEND_FROM_EMAIL", "Board Fundraising Game <team@boardfundraisinggame.com>"),
                    "to": [admin_email],
                    "subject": "New contact entered the platform",
                    "html": (f"<p>Name: {member.get('first_name','')} {member.get('last_name','')}</p>"
                             f"<p>Email: {member.get('email','')}</p>"
                             f"<p>Created: {member.get('created_at','')}</p>"
                             f"<p>Source: member signup</p>"),
                })
            except Exception:
                pass
        await db.members.update_one({"user_id": member["user_id"]}, {"$set": {"admin_notified": True}})


async def run_lifecycle_loop(db):
    while True:
        try:
            await scan_once(db)
        except Exception:
            pass
        await asyncio.sleep(1800)
