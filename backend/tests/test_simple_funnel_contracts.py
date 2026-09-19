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


def test_required_game_statements_are_not_duplicated_as_paragraphs():
    homepage = source("frontend/src/game/GameHomePage.jsx")
    assert ".slice(0, 3).map" in homepage
    assert 'data-testid="bfg-system-heading"' in homepage
    assert 'data-testid="bfg-strategy-heading"' in homepage


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
