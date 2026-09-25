from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Admin preview contract failed: missing {label}")

def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"Admin preview contract failed: found retired {label}")

preview = read("backend/admin_dashboard_preview_routes.py")
admin = read("frontend/src/admin/DashboardPreviewSection.jsx")

for version, label in [
    ('RECRUITMENT_FIXTURE_VERSION = "v8"', "Recruitment fixture version"),
    ('STRATEGIC_FIXTURE_VERSION = "v7"', "Strategic Planning fixture version"),
    ('RECOMMITMENT_FIXTURE_VERSION = "v9"', "Recommitment fixture version"),
    ('FUNDRAISING_FIXTURE_VERSION = "v6"', "Fundraising fixture version"),
]:
    require(preview, version, label)

# Recruitment must open with the clean six-question flow and later stages already inspectable.
for key in ("mission", "current_board", "desired_board_members", "support_needs", "board_type", "why_join"):
    require(preview, f'"{key}"', f"Recruitment answer {key}")
require(preview, '"result_generated": True', "Recruitment result ready")
require(preview, '"powerhouse_board_blueprint"', "approved Recruitment Board profiles")
for material in ("board_recruitment_job_post", "recruitment_emails", "social_posts", "referral_request_email"):
    require(preview, f'"{material}"', f"Recruitment campaign material {material}")
require(preview, '"interview_guide"', "preloaded Recruitment interview guide")
require(preview, '"organization_overview"', "onboarding Organization Overview")
require(preview, '"board_manual"', "onboarding Board Manual")
require(preview, '"formal_appointment_letter"', "final appointment letter")
require(preview, '"board_member_portfolio"', "Recruitment Board Member Portfolio")
require(preview, '"portfolio_email"', "Recruitment Portfolio email")

# Strategic Planning must include the full clean journey through adopted plan and execution.
require(preview, '"program_details"', "individual Strategic Planning programs")
require(preview, '"planning_meeting"', "Strategic Planning meeting")
require(preview, '"status": "COMPLETED"', "completed Strategic Planning session")
require(preview, "strategic_transcript()", "Strategic Planning transcript")
require(preview, "STRATEGIC PLANNING SESSION FACILITATION GUIDE", "Strategic Planning facilitation guide")
require(preview, "strategic_preview_final_plan()", "full Strategic Plan")
require(preview, '"final_status": "Approved"', "adopted Strategic Plan")
require(preview, '"leadership_portfolios": portfolios', "Strategic Leadership Portfolios")
forbid(preview, '("Operations",[', "retired Operations form section")

# Recommitment must use only the current two forms and three clean outcomes.
require(preview, '"active_advisory"', "Active/Advisory Recommitment form")
require(preview, '"full"', "full Recommitment form")
require(preview, "I am ready to recommit, remain an active Board Member and step up in my role.", "active Recommitment choice")
require(preview, "I would like to transition into an Advisory Board role.", "Advisory choice")
require(preview, "I would like to step down from the Board.", "step-down choice")
require(preview, '"reactivation_response_analysis"', "Recommitment response interpretation")
require(preview, '"reactivation_conversation_script"', "Recommitment conversation script")
require(preview, '"reactivation_board_member_portfolio"', "Recommitment Portfolio")
require(preview, '"reactivation_stepped_down_followup"', "Recommitment departure output")
forbid(preview, '"form_variant": "standard"', "retired standard Recommitment form variant")
forbid(preview, "I am not sure yet. I need more information or would like to discuss my role before deciding.", "retired unsure Recommitment answer in fixture")

# Fundraising Game must be testable after the individual games, meeting, Group Game and execution.
require(preview, '"fine_tuning": {"completed": True}', "completed founder Fundraising Game")
require(preview, '"funding_deadline": "2027-06-30"', "funding deadline")
require(preview, '"status": "completed", "current_round": 9', "completed nine-screen Group Game")
require(preview, "fundraising_meeting_transcript()", "Board Fundraising meeting transcript")
require(preview, '"schema_version": 2', "current Fundraising Strategy schema")
require(preview, '"status": "adopted"', "adopted Fundraising Strategy")
require(preview, '"status": "materials_ready"', "approved Board Fundraising Portfolios")
require(preview, "db.execution_toolkits", "execution toolkit collection")
require(preview, "db.game_strategy_deliveries", "strategy delivery records")
require(preview, "db.game_relationships", "Board relationship mapping")

require(preview, 'member = await preview_member(admin, f"{product}-{fixture_version}")', "product-isolated preview member identity")
forbid(preview, "founder_board_audits.update_one", "retired Founder Board Audit preview fixture")

# Admin must still expose all four real dashboards.
for product in ("recruitment", "board-fundraising-game", "strategic-planning", "board-recommitment"):
    require(admin, f'key: "{product}"', f"Admin preview card for {product}")

print("Admin dashboard preview fixtures contract: PASS")
