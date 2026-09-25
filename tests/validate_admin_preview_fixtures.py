from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Admin preview fixture contract failed: missing {label}")

preview = read("backend/admin_dashboard_preview_routes.py")
ui = read("frontend/src/admin/DashboardPreviewSection.jsx")

# Fresh fixture identities must change whenever the clean dashboards materially change.
for version_line in (
    'RECRUITMENT_FIXTURE_VERSION = "v8"',
    'STRATEGIC_FIXTURE_VERSION = "v7"',
    'RECOMMITMENT_FIXTURE_VERSION = "v9"',
    'FUNDRAISING_FIXTURE_VERSION = "v7"',
):
    require(preview, version_line, f"fresh fixture version {version_line}")

require(preview, 'if product == "board-recommitment"', "isolated Recommitment fixture identity")
require(preview, 'hashlib.sha256(member["user_id"].encode("utf-8")).hexdigest()[:16]', "Recommitment fixture full-member identity hash")
require(preview, 'tag = f"{fixture_version}-{identity_suffix}"', "versioned guided-product fixture IDs")
require(preview, 'tag = f"{FUNDRAISING_FIXTURE_VERSION}-{suffix(member)}"', "versioned Fundraising fixture IDs")
require(ui, "fully preloaded test journey", "Admin explanation of preloaded test journeys")
require(preview, 'member = await preview_member(admin, f"{product}-{fixture_version}")', "product-isolated preview identity")

# Recruitment: questions, recommendations, campaign assets, applicants, onboarding and Portfolio.
for needle, label in (
    ("RECRUITMENT_FIXTURE_VERSION", "Recruitment fixture"),
    ("recruitment_answers()", "six Recruitment answers"),
    ("recommended_roles", "recommended Board roles"),
    ("board_recruitment_job_post", "recruitment campaign job post"),
    ("recruitment_emails", "recruitment email"),
    ("social_posts", "recruitment social copy"),
    ("referral_request_email", "recruitment referral email"),
    ("opportunity_applications", "test applicants"),
    ("interview_guide", "candidate interview guide"),
    ("conditional_offer", "conditional appointment email"),
    ("unconditional_offer", "final appointment email"),
    ("onboarding_script", "onboarding facilitation content"),
    ("board_member_portfolio", "Recruitment Board Member Portfolio"),
):
    require(preview, needle, label)

# Strategic Planning: all organization fields, meeting, same-form responses, transcript, final plan, roles and Portfolios.
for needle, label in (
    ('"objectives":', "Strategic objectives"),
    ('"program_details":', "individual Strategic programs"),
    ('"team_building":', "Strategic team structure"),
    ('"technology":', "Strategic technology"),
    ('"marketing":', "Strategic marketing"),
    ('"partnerships":', "Strategic partnerships"),
    ('"fundraising":', "Strategic fundraising"),
    ('"budget":', "Strategic budget"),
    ('"action_planning":', "Strategic action planning"),
    ('"planning_meeting": {', "Strategic meeting"),
    ('"Lead User",', "founder same-form participation"),
    ("strategic_response(", "Board Member Strategic responses"),
    ("strategic_transcript()", "Strategic session transcript"),
    ("strategic_preview_final_plan()", "final Strategic Plan"),
    ('"active_delegation": {"delegates": delegates', "Strategic confirmed roles"),
    ('"leadership_portfolios": portfolios', "Strategic Leadership Portfolios"),
):
    require(preview, needle, label)

# Board Recommitment: setup, two forms, responses, call records, final outcomes and each transition output.
for needle, label in (
    ('"why_recommit":', "Recommitment reason"),
    ('"board_help_accomplish":', "Recommitment Board purpose"),
    ('"need_by":', "Recommitment deadline"),
    ('"form_variant": "active_advisory"', "no-step-down Recommitment form"),
    ('"form_variant": "full"', "full Recommitment form"),
    ('"direction": "Remain and Step Up"', "active recommitment response"),
    ('"direction": "Move to Advisory Board"', "Advisory response"),
    ('"direction": "Step Down"', "step-down response"),
    ("PRELOADED TEST CONVERSATION TRANSCRIPT", "Recommitment conversation transcript"),
    ('"conversation_conclusion":', "authoritative conversation conclusion"),
    ('"confirmed_role":', "founder-confirmed Recommitment role"),
    ("reactivation_response_analysis", "response interpretation"),
    ("reactivation_conversation_script", "person-specific conversation script"),
    ("reactivation_board_member_portfolio", "active/advisory Board Portfolio"),
    ("reactivation_stepped_down_followup", "step-down email"),
    ("reactivation_email_drafts", "approved Recommitment outreach emails"),
):
    require(preview, needle, label)

# Board Fundraising Game: founder reality, Board games, meeting, Group Game, transcript, strategy and execution.
for needle, label in (
    ('"current_individual_donors":', "current individual donors"),
    ('"current_businesses":', "current business supporters"),
    ('"current_grantors":', "current grantors"),
    ('"current_individual_donor_profile":', "present individual donor profile"),
    ('"current_individual_donor_motivation":', "present individual donor motivation"),
    ('"current_individual_donor_process":', "present individual donor method"),
    ('"current_business_profile":', "present business supporter profile"),
    ('"current_business_support":', "present business supporter focus"),
    ('"current_business_process":', "present business supporter method"),
    ('"current_grantor_profile":', "present grantor profile"),
    ('"current_grantor_support":', "present grantor focus"),
    ('"current_grantor_process":', "present grantor method"),
    ('"participation": {', "founder participation"),
    ("primary_answers", "founder four strategic answers"),
    ('"section_id": 5', "Board Member participation answers"),
    ('"funding_deadline": "2027-06-30"', "funding deadline"),
    ('"status": "completed", "current_round": 4, "game_version": "four-area-v1"', "completed four-round Group Game"),
    ("group_rounds =", "all Group Game rounds"),
    ("fundraising_meeting_transcript()", "Fundraising meeting transcript"),
    ('"mode": "final"', "final Fundraising Strategy"),
    ('"status": "adopted"', "adopted Fundraising Strategy"),
    ("board_portfolios", "Board Fundraising Portfolios"),
    ("execution_toolkits", "Board execution toolkits"),
    ("game_relationships", "relationship mapping examples"),
):
    require(preview, needle, label)

# Launcher must seed each product before issuing the preview member cookie.
for needle, label in (
    ("await seed_recruitment_preview(member)", "Recruitment launch seeding"),
    ("await seed_fundraising_preview(member)", "Fundraising launch seeding"),
    ('session_id = await seed_guided_product(member, product, config)', "Strategic/Recommitment launch seeding"),
):
    require(preview, needle, label)

print("Admin preview fixture contract: PASS")
