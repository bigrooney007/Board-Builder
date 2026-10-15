"""Synthetic data for the real current client routes, not parallel test forms."""
import secrets
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import strategic_questionnaire as planning
import fundraising_audiences as fundraising

WORKFLOWS = {"recruitment": "original-recruitment-materials-page", "board-fundraising-game": fundraising.VERSION,
             "strategic-planning": planning.VERSION, "board-recommitment": "original-recommitment"}


WORKFLOW_FILES = {
    "recruitment": ("recruit_free_routes.py", "workspace_routes.py", "workspace_service.py", "../frontend/src/funnels/RecruitmentGamePage.jsx", "../frontend/src/member/RecruitmentSetupMaterialsPage.jsx"),
    "board-fundraising-game": ("fundraising_audiences.py", "fundraising_review.py", "game_routes.py", "game_night_routes.py", "game_meeting_routes.py", "group_game_routes.py", "strategy_pdf.py", "../frontend/src/game/AudienceQuestionnaire.jsx", "../frontend/src/game/AudienceGroupReview.jsx", "../frontend/src/game/GameDashboardPage.jsx"),
    "strategic-planning": ("strategic_questionnaire.py", "strategic_questions.json", "strategic_planning_routes.py", "guided_product_routes.py", "../frontend/src/funnels/StrategicPlanningFormPage.jsx", "../frontend/src/funnels/StrategicPlanningSessionPage.jsx", "../frontend/src/funnels/StrategicPlanningDashboard.jsx"),
    "board-recommitment": ("reactivation_routes.py", "reactivation_plan_routes.py", "guided_product_routes.py", "../frontend/src/funnels/BoardRecommitmentDashboard.jsx"),
}


def workflow_fingerprint(product):
    """A changed client workflow automatically gets new preloaded test records.

    Old synthetic records remain intact. Existing customers are never reseeded.
    Backend configuration is authoritative even when frontend sources are packaged
    separately in production.
    """
    config = planning.form_content() if product == "strategic-planning" else fundraising.configuration() if product == "board-fundraising-game" else WORKFLOWS[product]
    digest = hashlib.sha256(json.dumps(config,sort_keys=True).encode())
    root = Path(__file__).resolve().parent
    for name in ("ai_service.py", "content_templates.py", *WORKFLOW_FILES[product]):
        path = root / name
        if path.is_file():
            digest.update(name.encode()); digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def planning_answers(name="Sample leader"):
    # Answers are examples; question wording always comes from the live configuration.
    examples = ["Help 1,000 young people move into education and employment within 24 months.",
        "Increase youth employment placements and develop sustainable funding.", "Develop mentoring and employer-supported training programmes.",
        "Young people aged 12 to 24 should gain confidence, skills and sustained employment.", "We have a small staff and several committed employer partners.",
        "Strengthen programme leadership and volunteer training.", "Use a shared relationship system and record participant outcomes.",
        "Publish participant outcomes and invite employers to programme visits.", "Build relationships with schools and employers.",
        "Develop individual donor and business sponsorship relationships.", "Confirm the proposed budget before committing additional expenditure.",
        "Review funding concentration and staff capacity each quarter.", "Start with employer mapping in the first quarter, then review results before expansion.",
        "Review participant outcomes and fundraising progress at each board meeting.", f"{name} is willing to help introduce local employers, subject to agreeing the specific work."]
    return dict(zip(planning.KEYS, examples))


def fundraising_answers(name="Sample leader", index=0):
    categories = {k: [] for k in fundraising.CATEGORIES}
    for cat, who in (("individuals", "Former mentors"), ("businesses", "Local employers"), ("grantmakers", "Youth opportunity foundations")):
        categories[cat] = [{"id": f"sample-{index}-{cat}", "who_why": f"{who} may support young people's education and employment.",
            "where": "Community and professional networks", "attraction": "Share credible programme outcomes and arrange a visit.",
            "process": "Ask for an introduction, understand their priorities, agree a suitable proposal and follow up.",
            "ask": "Support a youth mentoring cohort.", "amount": "The appropriate amount needs confirmation."}]
    return fundraising.clean_response({"audiences": categories, "involvement": f"{name} would like to make introductions to potential supporters.",
        "category_status": {k: "complete" for k in fundraising.CATEGORIES}, "progress": {"category": 2, "phase": "review", "question": 5, "audience_index": 0}}, submitting=True)


async def seed_current_workflow(db, member, product, *, preloaded=False, intro=False):
    user = member["user_id"]; now = datetime.now(timezone.utc).isoformat()
    sid = "current-test-" + user; lead_token = "lead-" + user
    config = {"strategic-planning": ("strategic_planning_497", "strategic_planning"), "board-fundraising-game": ("board_fundraising_game_497", "board_fundraising_game")}
    source, offer = config[product]
    await db.payment_transactions.update_one({"session_id": sid}, {"$setOnInsert": {"session_id": sid, "user_id": user, "claimed_by_user_id": user,
        "payment_status": "paid", "status": "completed", "purchase_source": source, "offer_source": offer, "guided_lead_token": lead_token,
        "lead_email": member["email"], "payment_email": member["email"], "internal_preview": True, "amount": 0, "currency": "usd", "created_at": now}}, upsert=True)
    if product == "board-fundraising-game":
        await db.members.update_one({"user_id": user}, {"$addToSet": {"entitlements": "board_fundraising_game"}})
        await db.game_profiles.update_one({"user_id": user}, {"$setOnInsert": {"user_id": user, "workflow_version": fundraising.VERSION,
            "organization": {"name": "BrightPath Youth Alliance", "mission": "Help young people enter education and employment."},
            "primary_user": {"full_name": "Sample Leader", "email": member["email"]}, "goal": {"amount": 500000, "purpose": "Youth education and employment"},
            "profile_completed": True, "welcome_email_sent": True, "internal_preview": True, "created_at": now}}, upsert=True)
        free = fundraising_answers()
        await db.game_free_responses.update_one({"user_id": user}, {"$setOnInsert": {"user_id": user, **({} if intro else free), "completed": not intro, "created_at": now}}, upsert=True)
        if preloaded:
            for index, name in enumerate(("Sample Leader", "Alex Morgan", "Taylor Reed", "Jordan Ellis")):
                mid = f"{user}-person-{index}"
                await db.game_board_members.update_one({"member_id": mid}, {"$setOnInsert": {"member_id": mid, "user_id": user, "full_name": name,
                    "email": member["email"] if index == 0 else f"sample-{index}-{user}@nonprofitboardbuilder.internal", "board_title": "", "participant_role": "board_member",
                    "is_primary": index == 0, "game_version": fundraising.VERSION, "token": secrets.token_urlsafe(24), "invitation_status": "invited", "removed": False,
                    "internal_preview": True, "created_at": now}}, upsert=True)
                await db.game_audience_responses.update_one({"board_member_id": mid}, {"$setOnInsert": {"response_id": mid, "board_member_id": mid,
                    "user_id": user, **fundraising_answers(name, index), "completed": True, "completed_at": now, "created_at": now}}, upsert=True)
            await db.game_nights.update_one({"user_id": user}, {"$setOnInsert": {"user_id": user, "meeting_date": "2026-11-15", "start_time": "18:00", "timezone": "UTC", "funding_deadline": "2027-11-15", "status": "scheduled"}}, upsert=True)
            await db.game_situations.update_one({"user_id": user}, {"$setOnInsert": {"user_id": user, "workflow_version": fundraising.VERSION, "completed": True, "current_step": 0}}, upsert=True)
            from fundraising_review import AudienceReview
            await AudienceReview(db).prepare(user)
        return "/game/questions" if intro else "/game/dashboard" if preloaded else f"/purchase/success?session_id={sid}"
    answers = {} if intro else planning_answers()
    await db.guided_product_leads.update_one({"token": lead_token}, {"$setOnInsert": {"token": lead_token, "product": product, "name": "Sample Leader", "email": member["email"],
        "organization": "BrightPath Youth Alliance", "board_count": 3, "prepayment_answers": answers, "prepayment_complete": not intro,
        "questionnaire_version": planning.VERSION, "internal_preview": True, "followup_status": "converted", "created_at": now}}, upsert=True)
    if not intro:
        await db.guided_product_intakes.update_one({"session_id": sid}, {"$setOnInsert": {"session_id": sid, "product": product, "answers": answers, "internal_preview": True, "created_at": now}}, upsert=True)
    if preloaded:
        pid = "planning-" + user
        await db.sp_projects.update_one({"guided_session_id": sid}, {"$setOnInsert": {"project_id": pid, "guided_session_id": sid, "organization_name": "BrightPath Youth Alliance",
            "founder_name": "Sample Leader", "founder_email": member["email"], "founder_title": "Executive Director", "mission": "Help young people enter education and employment.",
            "questionnaire_version": planning.VERSION, "generic_form_token": secrets.token_urlsafe(32), "internal_preview": True,
            "planning_meeting": {"meeting_date": "2026-11-15", "start_time": "18:00", "timezone_name": "UTC"}, "created_at": now}}, upsert=True)
        content = planning.form_content()
        await db.sp_forms.update_one({"project_id": pid}, {"$setOnInsert": {"project_id": pid, "content": content, "status": "Approved", "version": 1, "created_at": now}}, upsert=True)
        for index, name in enumerate(("Sample Leader", "Alex Morgan", "Taylor Reed", "Jordan Ellis")):
            await db.sp_participants.update_one({"participant_id": f"{pid}-{index}"}, {"$setOnInsert": {"participant_id": f"{pid}-{index}", "project_id": pid, "name": name,
                "email": member["email"] if index == 0 else f"sample-{index}-{user}@nonprofitboardbuilder.internal", "role": "Lead User" if index == 0 else "Board Member",
                "form_token": secrets.token_urlsafe(32), "review_token": secrets.token_urlsafe(32), "status": "COMPLETED", "form_version": 1,
                "response": planning_answers(name), "questionnaire_version": planning.VERSION, "response_questions": [{"id":q["key"],"prompt":q["prompt"],"section":q["title"]} for q in planning.QUESTIONS],
                "submitted_at": now, "created_at": now}}, upsert=True)
        await db.sp_sessions.update_one({"project_id": pid}, {"$setOnInsert": {"project_id": pid, "share_token": secrets.token_urlsafe(32), "status": "NOT STARTED", "decisions": {}, "current_section_index": 0, "created_at": now}}, upsert=True)
        await db.sp_plans.update_one({"project_id": pid}, {"$setOnInsert": {"project_id": pid, "meeting_guide_text": "Review each of the 15 questions. Discuss contributors' ideas and select the decisions the group agrees to adopt. Confirm participation individually before final adoption.", "created_at": now}}, upsert=True)
    return f"/strategic-planning/start?token={lead_token}" if intro else f"/strategic-planning/dashboard?session_id={sid}" if preloaded else f"/purchase/success?session_id={sid}"
