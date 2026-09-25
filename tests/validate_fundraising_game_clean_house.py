from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Board Fundraising Game contract failed: missing {label}")


def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"Board Fundraising Game contract failed: found retired {label}")


dashboard = read("frontend/src/game/GameDashboardPage.jsx")
situation = read("frontend/src/game/GameSituationPage.jsx")
play = read("frontend/src/game/GamePlayPage.jsx")
game_content = read("backend/game_content_v3.py")
night_backend = read("backend/game_night_routes.py")
group_backend = read("backend/group_game_routes.py")
group_frontend = read("frontend/src/game/GroupGamePage.jsx")
strategy_backend = read("backend/strategy_routes.py")
meeting_backend = read("backend/game_meeting_routes.py")
review_backend = read("backend/meeting_review_routes.py")
strategy_render = read("frontend/src/game/strategyRender.jsx")
strategy_pdf = read("backend/strategy_pdf.py")
postgame = read("backend/postgame_routes.py")
portfolio_backend = read("backend/portfolio_routes.py")
portfolio_edit = read("frontend/src/game/PortfolioEditPage.jsx")
member_strategy = read("frontend/src/game/FinalStrategyMemberPage.jsx")
assistant_page = read("frontend/src/game/BoardExecutionAssistantPage.jsx")
voice = read("backend/voice_content.py")
audio_button = read("frontend/src/clean/DashboardAudioButton.jsx")

for title in (
    "PLAY THE BOARD FUNDRAISING GAME",
    "SET YOUR BOARD MEETING AND FUNDING DEADLINE",
    "INVITE YOUR BOARD MEMBERS TO PLAY",
    "RUN THE GROUP BOARD FUNDRAISING GAME",
    "FINAL FUNDRAISING STRATEGY AND DELEGATION",
    "SHARE THE STRATEGY AND MOVE INTO EXECUTION",
):
    require(dashboard, title, f"dashboard section: {title}")

for key in (
    "current_individual_donor_profile", "current_individual_donor_motivation", "current_individual_donor_process",
    "current_business_profile", "current_business_support", "current_business_process",
    "current_grantor_profile", "current_grantor_support", "current_grantor_process",
):
    require(game_content, f'"key": "{key}"', f"lead present-funder field {key}")

for key in ("current_team", "current_technology", "current_materials", "current_budget"):
    forbid(game_content, f'"key": "{key}"', f"lead current-reality question {key}")

require(game_content, '"skippable": True', "optional absent-funder groups")
forbid(game_content, "build_question", "system-building participation question")
require(situation, 'get("review") === "1"', "completed founder Game review mode")
require(play, 'get("review") === "1"', "completed Board Member Game review mode")
require(dashboard, "?review=1", "dashboard review action opens the saved Game")
require(situation, "withLegacySummaries", "production-record compatibility summaries")
forbid(play, "part_build", "Board Member system-building participation screen")

for clip in ("a1_deeper", "a2_deeper", "a3_deeper", "a4_deeper", "part_raise", "part_time", "part_anything"):
    require(voice, f'"{clip}"', f"audio slot {clip}")
require(play, "NarrationControl", "visible participant narration controls")
require(situation, "NarrationControl", "visible founder narration controls")
require(audio_button, "<Volume2", "icon-only section audio control")
forbid(audio_button, "AUDIO COMING SOON", "audio coming-soon label")
forbid(audio_button, "PLAY AUDIO", "audio text label")

require(night_backend, '"current_reality", "participation", "guided", "mini_strategy"', "source-controlled game structure")
require(night_backend, "key not in structural_keys", "old database content override protection")

require(group_backend, "TOTAL_ROUNDS = 4", "four-round Group Game")
require(group_backend, 'GROUP_GAME_VERSION = "four-area-v1"', "four-round session version")
round_defs = group_backend.split("ROUND_DEFS = [", 1)[1].split("]\n\nAREA_DEFS", 1)[0]
for key in ("who_should_fund", "where_to_find", "attract_attention", "fundraising_process"):
    require(round_defs, f'"section_key": "{key}"', f"Group Game round {key}")
for key in ("team", "technology", "materials", "budget", "execution"):
    forbid(round_defs, f'"section_key": "{key}"', f"Group Game round {key}")
require(group_backend, "PRESENT INDIVIDUAL DONORS", "present donors in audience round")
require(group_backend, "PRESENT CORPORATE SPONSORS / BUSINESS PARTNERS", "present business supporters in audience round")
require(group_backend, "PRESENT GRANTORS", "present grantors in audience round")
require(group_backend, "PRESENT INDIVIDUAL DONOR METHOD", "present donor method in process round")
require(group_backend, "PRESENT BUSINESS / SPONSOR METHOD", "present business method in process round")
require(group_backend, "PRESENT GRANTOR METHOD", "present grantor method in process round")
require(group_frontend, 'memberApi.post("/game/meeting/compile-final")', "final strategy generation after round four")

for source, filter_name, label in (
    (strategy_backend, "CORE_STRATEGY_KEYS", "working strategy"),
    (meeting_backend, "CORE_STRATEGY_KEYS", "final strategy"),
    (review_backend, "EDITABLE_SECTION_KEYS", "reviewed final strategy"),
):
    require(source, filter_name, f"four-part filter in {label}")
    for key in ("fundraising_audiences", "where_to_find", "attraction", "fundraising_process"):
        require(source, f'"{key}"', f"{key} in {label}")

require(strategy_backend, '"schema_version": 3', "working strategy schema v3")
require(meeting_backend, '"schema_version": 3', "final strategy schema v3")
require(strategy_render, "export const STRATEGY_SECTIONS", "four-part strategy renderer")
require(strategy_pdf, "V3_SECTIONS", "four-part strategy PDF")

require(postgame, "FOUNDER_DELEGATION_APPROVED_STATUSES", "founder delegation approval statuses")
require(postgame, "require_founder_approved_delegation", "strategy delivery delegation gate")
require(portfolio_backend, "founder_approved_count", "founder delegation readiness count")
require(portfolio_edit, "APPROVE THIS DELEGATION", "founder delegation approval action")
require(member_strategy, "How Do I Get Involved?", "strategy-to-Portfolio CTA")
require(assistant_page, "suggested_materials", "execution assistant material shortcuts")

print("Board Fundraising Game four-area contract: PASS")
