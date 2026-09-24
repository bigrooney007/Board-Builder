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
game_routes = read("backend/game_routes.py")
night_backend = read("backend/game_night_routes.py")
night_frontend = read("frontend/src/game/GameNightSection.jsx")
group_backend = read("backend/group_game_routes.py")
group_frontend = read("frontend/src/game/GroupGamePage.jsx")
meeting_backend = read("backend/game_meeting_routes.py")
postgame = read("backend/postgame_routes.py")
portfolio_backend = read("backend/portfolio_routes.py")
portfolio_edit = read("frontend/src/game/PortfolioEditPage.jsx")
member_strategy = read("frontend/src/game/FinalStrategyMemberPage.jsx")
assistant_page = read("frontend/src/game/BoardExecutionAssistantPage.jsx")
voice = read("backend/voice_content.py")\naudio_button = read("frontend/src/clean/DashboardAudioButton.jsx")

for title in (
    "PLAY THE BOARD FUNDRAISING GAME",
    "SET YOUR BOARD MEETING AND FUNDING DEADLINE",
    "INVITE YOUR BOARD MEMBERS TO PLAY",
    "RUN THE GROUP BOARD FUNDRAISING GAME",
    "FINAL FUNDRAISING STRATEGY AND DELEGATION",
    "SHARE THE STRATEGY AND MOVE INTO EXECUTION",
):
    require(dashboard, title, f"dashboard section: {title}")

forbid(dashboard, "WorkingStrategyCard", "early working-strategy dashboard card")
require(dashboard, "DelegationReviewStage", "post-strategy founder delegation review")
require(dashboard, 'memberApi.post("/game/portfolios/prepare")', "automatic delegation draft preparation")
require(dashboard, 'SupportBox productKey="board_fundraising_game"', "persistent support")
require(dashboard, "DashboardAudioButton", "Fundraising dashboard audio control")
for audio_id in ("dash_bfg_founder_game","dash_bfg_meeting","dash_bfg_board","dash_bfg_group","dash_bfg_strategy","dash_bfg_execution"):
    require(voice, f'"{audio_id}"', f"Fundraising dashboard audio {audio_id}")
require(audio_button, "PLAY AUDIO", "shared dashboard audio play control")

for key in (
    "current_individual_donors",
    "current_businesses",
    "current_grantors",
    "current_team",
    "current_technology",
    "current_materials",
    "current_budget",
):
    require(game_content, f'"key": "{key}"', f"founder current-reality question {key}")

require(game_content, '"skippable": True', "skippable existing-funder questions")
require(game_routes, '@router.put("/game/branding")', "organization logo storage")
require(situation, "START MY BOARD FUNDRAISING GAME", "founder Game introduction")
require(situation, "Skip — We Don't Have This Yet", "founder skippable funder questions")

for clip in (
    "a1_deeper", "a2_deeper", "a3_deeper", "a4_deeper",
    "reality_technology", "reality_materials", "reality_budget",
    "part_build", "part_raise", "part_time", "part_anything",
):
    require(voice, f'"{clip}"', f"audio slot {clip}")
require(play, 'stage === "first"', "strategic-question audio stage")
require(play, "NarrationControl", "visible participant narration controls")
require(situation, "NarrationControl", "visible founder narration controls")

require(night_backend, "funding_deadline: str", "funding deadline model")
require(night_backend, '"goal.deadline": payload.funding_deadline.strip()', "funding deadline synchronization into fundraising goal")
require(night_frontend, 'data-testid="bfg-funding-deadline"', "funding deadline field")
require(night_frontend, "30, 60, 90, 120 days", "deadline execution guidance")

require(group_backend, "TOTAL_ROUNDS = 9", "nine-screen Group Game")
for key in ("who_should_fund", "where_to_find", "attract_attention", "fundraising_process", "team", "technology", "materials", "budget", "execution"):
    require(group_backend, f'"section_key": "{key}"', f"Group Game round {key}")
require(group_backend, "deadline_execution_recommendations", "deadline-driven Group Game execution recommendation")
require(group_backend, "current_technology", "current technology in Group Game")
require(group_backend, "current_materials", "current materials in Group Game")
require(group_backend, "current_budget", "current budget in Group Game")

require(group_frontend, 'memberApi.post("/game/meeting/compile-final")', "background final strategy generation at Group Game completion")
require(group_frontend, "LiveMeetingRecorder", "meeting discussion transcription")

require(meeting_backend, "days_available_until_funding_deadline", "deadline-derived execution window")
require(meeting_backend, "two-to-four-page operating roadmap", "concise final strategy contract")
require(meeting_backend, "Board Members use their own networks", "Board network fundraising strategy")
require(meeting_backend, "ROLE / CAPACITY NEEDED", "unfilled team-capacity protection")

require(postgame, "FOUNDER_DELEGATION_APPROVED_STATUSES", "founder delegation approval statuses")
require(postgame, "require_founder_approved_delegation", "strategy delivery delegation gate")
require(postgame, "participating_members", "strategy recipients limited to actual participants")
require(portfolio_backend, "founder_approved_count", "founder delegation readiness count")
require(portfolio_edit, "APPROVE THIS DELEGATION", "founder delegation approval action")
require(member_strategy, "How Do I Get Involved?", "strategy-to-Portfolio CTA")
require(assistant_page, "suggested_materials", "execution assistant material shortcuts")

print("Board Fundraising Game clean-house contract: PASS")
