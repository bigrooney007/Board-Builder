from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_recruitment_submission_notifies_purchasing_user_with_direct_application_link():
    routes = source("backend/public_opportunity_routes.py")
    dashboard = source("frontend/src/member/workspace/ApplicantModules.jsx")
    assert '"owner_user_id": opportunity["user_id"]' in routes
    assert 'Board Application Received | {applicant_name}' in routes
    assert "application_id={application['application_id']}#br-section-applicants" in routes
    assert 'get("application_id")' in dashboard


def test_fundraising_game_completion_notifies_once_with_direct_response_link():
    routes = source("backend/game_night_routes.py")
    dashboard = source("frontend/src/game/BoardMembersSection.jsx")
    assert 'newly_completed = completed_count >= total_sections and not record.get("completed_at")' in routes
    assert 'newly_completed and not record.get("is_primary")' in routes
    assert "response={record['member_id']}#bfg-board-members-section" in routes
    assert 'get("response")' in dashboard


def test_strategic_planning_response_goes_to_project_purchaser_not_platform_owner():
    routes = source("backend/strategic_planning_routes.py")
    response_block = routes[routes.index('@router.post("/strategic-planning-form/{token}"'):routes.index('@router.get("/strategic-planning-response/{participant_id}")')]
    assert 'project["founder_email"]' in response_block
    assert "/strategic-planning-response/{record['participant_id']}" in response_block
    assert "notify_owner(" not in response_block


def test_recommitment_response_links_to_current_dashboard_and_opens_member():
    routes = source("backend/reactivation_routes.py")
    dashboard = source("frontend/src/member/BoardRecommitmentDashboard.jsx")
    assert "board-recommitment/dashboard?" in routes
    assert "member={record['member_record_id']}#recommitment-responses" in routes
    assert 'get("member")' in dashboard
    assert 'requested===row.member_record_id' in dashboard


def test_every_notification_records_delivery_status_without_rolling_back_response():
    for path in [
        "backend/public_opportunity_routes.py",
        "backend/game_night_routes.py",
        "backend/strategic_planning_routes.py",
        "backend/reactivation_routes.py",
    ]:
        routes = source(path)
        assert 'owner_notification_status": "Sent"' in routes
        assert 'owner_notification_status": "Failed"' in routes
