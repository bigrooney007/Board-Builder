"""Static regression checks for the deterministic public funnels."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_game_homepage_has_one_source_of_truth():
    game_routes = source("backend/game_routes.py")
    assert 'find_one({"key": "game_site_content"}' not in game_routes
    assert "return DEFAULT_CONTENT" in game_routes
    assert "status_code=409" in game_routes


def test_game_sales_routes_use_the_demonstration():
    app = source("frontend/src/App.js")
    payments = source("backend/payment_routes.py")
    lifecycle = source("backend/lifecycle_engine.py")
    assert '<Route path="/game/demonstration" element={<GameDemonstrationPage />} />' in app
    assert '<Route path="/game/unlock" element={<Navigate to="/game/demonstration" replace />} />' in app
    assert 'resolve_cancel_url(payload, "/game/demonstration")' in payments
    assert '"/game/demonstration"' in lifecycle


def test_new_game_buyers_can_secure_access_before_playing():
    welcome = source("frontend/src/game/GameWelcomePage.jsx")
    assert 'member?.account_status === "free_game_guest"' in welcome
    assert 'memberApi.post("/members/complete-guest-account", password)' in welcome


def test_removed_game_statements_are_not_rendered():
    homepage = source("frontend/src/game/GameHomePage.jsx")
    game_routes = source("backend/game_routes.py")
    assert ".slice(0, 3).map" in homepage
    assert 'data-testid="bfg-system-heading"' not in homepage
    assert 'data-testid="bfg-strategy-heading"' not in homepage
    assert "To Raise Money Exponentially, You Need A Fundraising System." not in game_routes
    assert "To Build A Fundraising System, You Need A Fundraising Strategy." not in game_routes


def test_recruitment_helper_does_not_leave_an_empty_paragraph():
    page = source("frontend/src/funnels/RecruitmentHomePage.jsx")
    content = source("frontend/src/content/siteContent.js")
    assert "{copy.formText ? <p>{copy.formText}</p> : null}" in page
    assert '"formText": ""' in content


def test_facilitated_game_never_falls_back_to_recruitment_booking():
    route = source("backend/facilitated_game_application_routes.py")
    payments = source("backend/payment_routes.py")
    assert "calendly.com/boardbuilder/recruitboard" not in route
    assert "booking_url" not in route
    assert '@router.post("/facilitated-game-checkout")' not in payments


def test_recruitment_dashboard_follows_the_single_forward_flow():
    dashboard = source("frontend/src/member/BoardRecruitmentPage.jsx")
    ordered_ids = [
        "br-section-intake", "br-section-identify", "br-section-materials", "br-section-campaign",
        "br-section-applicants", "br-section-references", "br-section-onboarding",
        "br-section-facilitation", "br-section-portfolio", "br-section-support", "br-section-first-meeting",
    ]
    positions = [dashboard.index(test_id) for test_id in ordered_ids]
    assert positions == sorted(positions)
    assert "RecruitmentMaterials" in dashboard
    assert "RecruitmentCampaignLaunch" in dashboard
    assert "AutomatedReferenceChecks" in dashboard
    assert "FirstBoardMeetingWorkspace" in dashboard


def test_recruitment_reference_check_has_one_automated_path():
    modules = source("frontend/src/member/workspace/ApplicantModules.jsx")
    workspace = source("backend/workspace_routes.py")
    assert 'data-testid="automated-reference-workspace"' in modules
    assert "Generate Candidate Referee Request Email" not in modules
    assert "Generate Reference Check Email" not in modules
    assert "Generate Reference Call Guide" not in modules
    assert "Generate Reference Record & Evaluation Form" not in modules
    assert "MANUAL_REFERENCE_MATERIAL_TYPES" in workspace
    assert "Manual reference materials have been replaced by the automated reference-check process." in workspace


def test_conditional_appointment_carries_every_onboarding_link():
    workspace = source("backend/workspace_routes.py")
    refinement = source("backend/refinement_routes.py")
    start = workspace.index('if payload.type == "conditional_offer"')
    end = workspace.index('if payload.type in {"formal_appointment_letter", "formal_appointment_email"}', start)
    conditional = workspace[start:end]
    assert "Complete the automated reference check" in conditional
    assert "organization_overview" in conditional
    assert "board_manual" in conditional
    assert "board_member_agreement" in conditional
    assert "confidentiality_agreement" in conditional
    assert "conflict_of_interest_agreement" in conditional
    assert "Board Member Profile Form" in conditional
    assert "BOARD ONBOARDING SESSION" in conditional
    assert "expected_tokens" in refinement
    assert "Regenerate the Conditional Appointment Email so it carries every approved onboarding link." in refinement


def test_recruitment_purchase_enters_dashboard_and_game_is_the_intake():
    success = source("frontend/src/member/PurchaseSuccessPage.jsx")
    app = source("frontend/src/App.js")
    dashboard = source("frontend/src/member/BoardRecruitmentPage.jsx")
    assert 'claimed_source === "recruitment_497"' in success
    assert 'navigate("/app/board-recruitment")' in success
    game = source("frontend/src/member/RecruitmentGameIntake.jsx")
    assert '<Route path="/app/board-recruitment" element={<BoardRecruitmentPage />} />' in app
    assert 'title="PLAY THE BOARD RECRUITMENT GAME"' in dashboard
    assert 'RecruitmentGameIntake' in dashboard
    assert 'QUESTION {step + 1} OF 4' in game


def test_guided_products_keep_intake_and_execution_inside_the_dashboard():
    guided = source("frontend/src/funnels/GuidedProductPages.jsx")
    strategic = source("frontend/src/funnels/StrategicPlanningDashboard.jsx")
    recommitment = source("frontend/src/member/BoardRecommitmentDashboard.jsx")
    assert "GO TO MY DASHBOARD" in guided
    assert "<Navigate replace" in guided
    assert "Tell Us About Your Organization" in guided
    assert "START MICROPHONE TRANSCRIPTION" in strategic
    assert "END SESSION AND START DELEGATION" in strategic
    assert "FounderBoardAudit" in recommitment
    audit = source("backend/guided_product_routes.py")
    assert 'require_entitlement(member, {"reactivation_self_guided"})' in audit


def test_strategic_form_uses_two_questions_per_section_and_individual_programs():
    route = source("backend/strategic_planning_routes.py")
    assert 'return [f"Review the organization\'s present {label}' in route
    assert '"What would you do differently in this area?' in route
    assert 'for program in program_lines:' in route
    assert '@router.post("/session/complete")' in route
    assert '"meeting_transcript":transcript' in route
    assert '@router.post("/send-delegation")' in route
    assert 'following section{\'s\' if len(links)>1 else \'\'}' in route


def test_admin_can_open_all_four_isolated_product_dashboards_without_a_customer_login():
    route = source("backend/admin_dashboard_preview_routes.py")
    admin = source("frontend/src/admin/DashboardPreviewSection.jsx")
    server = source("backend/server.py")
    assert 'admin = await authenticate_admin(request, db)' in route
    assert 'set_member_cookie(response, create_member_token' in route
    assert '"internal_preview": True' in route
    assert '"internal_admin_entitlement": True' in route
    for product in ["recruitment", "board-fundraising-game", "strategic-planning", "board-recommitment"]:
        assert f'"{product}"' in route
        assert f'key: "{product}"' in admin
    assert "create_admin_dashboard_preview_router(db)" in server


def test_admin_dashboard_preview_records_are_hidden_from_customer_reporting():
    contacts = source("backend/admin_contacts_routes.py")
    game = source("backend/game_routes.py")
    strategic = source("backend/strategic_planning_routes.py")
    fbb = source("backend/fbb_routes.py")
    assert '"internal_dashboard_preview": {"$ne": True}' in contacts
    assert '"internal_preview": {"$ne": True}' in game
    assert '"internal_preview": {"$ne": True}' in strategic
    assert '"internal_preview": {"$ne": True}' in fbb
