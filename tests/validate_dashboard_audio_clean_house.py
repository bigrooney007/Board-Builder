from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Dashboard audio contract failed: missing {label}")

def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"Dashboard audio contract failed: found retired {label}")

voice = read("backend/voice_content.py")
voice_routes = read("backend/voice_routes.py")
button = read("frontend/src/clean/DashboardAudioButton.jsx")
admin = read("frontend/src/admin/DashboardSectionAudioAdmin.jsx")
platform_videos = read("frontend/src/admin/PlatformVideosSection.jsx")
legacy_voice_admin = read("frontend/src/admin/VoiceGuidedAdmin.jsx")
recruitment = read("frontend/src/member/BoardRecruitmentPage.jsx")
fundraising = read("frontend/src/game/GameDashboardPage.jsx")
recommitment = read("frontend/src/member/BoardRecommitmentDashboard.jsx")
strategic = read("frontend/src/funnels/StrategicPlanningDashboard.jsx")

groups = {
    "recruitment": [
        "dash_rct_questions","dash_rct_identify","dash_rct_materials","dash_rct_launch","dash_rct_applicants",
        "dash_rct_interviews","dash_rct_references","dash_rct_background","dash_rct_onboarding_prep",
        "dash_rct_onboarding_session","dash_rct_portfolios",
    ],
    "fundraising": [
        "dash_bfg_founder_game","dash_bfg_meeting","dash_bfg_board","dash_bfg_group","dash_bfg_strategy","dash_bfg_execution",
    ],
    "recommitment": [
        "dash_rec_questions","dash_rec_forms","dash_rec_responses","dash_rec_decisions",
    ],
    "strategic": [
        "dash_sp_organization","dash_sp_meeting","dash_sp_founder_form","dash_sp_board_forms",
        "dash_sp_facilitation","dash_sp_session","dash_sp_plan",
    ],
}

all_ids = [item for ids in groups.values() for item in ids]
if len(all_ids) != 28 or len(set(all_ids)) != 28:
    raise SystemExit("Dashboard audio contract failed: expected exactly 28 unique dashboard clips")

for narration_id in all_ids:
    require(voice, f'"{narration_id}"', f"voice script {narration_id}")
    require(admin, f'"{narration_id}"', f"Admin audio asset {narration_id}")

for tutorial, prefix in (
    ("dashboard-recruitment", "dash_rct_"),
    ("dashboard-fundraising-game", "dash_bfg_"),
    ("dashboard-recommitment", "dash_rec_"),
    ("dashboard-strategic-planning", "dash_sp_"),
):
    require(voice_routes, f'"{tutorial}": "{prefix}"', f"public audio manifest {tutorial}")

require(voice_routes, 'environment = "live" if tutorial_name.startswith("dashboard-")', "Live-only dashboard audio manifest")
require(voice_routes, 'environment: str = ""', "explicit audio environment selection")
require(voice_routes, 'not str(row.get("category") or "").startswith("DASHBOARD_AUDIO_")', "dashboard clips excluded from legacy bulk generation")
require(legacy_voice_admin, 'startsWith("DASHBOARD_AUDIO_")', "dashboard clips excluded from legacy voice library")

require(button, 'aria-label={playing ? "Pause section audio" : "Play section audio"}', "accessible icon-only audio control")
require(button, "<Volume2", "play audio icon")
require(button, "<Pause", "pause audio icon")
forbid(button, "AUDIO COMING SOON", "missing-audio text")
forbid(button, "PLAY AUDIO", "play-audio text")
require(button, "dashboard-recruitment", "Recruitment dashboard audio manifest")
require(button, "dashboard-fundraising-game", "Fundraising dashboard audio manifest")
require(button, "dashboard-recommitment", "Recommitment dashboard audio manifest")
require(button, "dashboard-strategic-planning", "Strategic dashboard audio manifest")

for dashboard, name in (
    (recruitment, "Recruitment"),
    (fundraising, "Fundraising"),
    (recommitment, "Recommitment"),
    (strategic, "Strategic Planning"),
):
    require(dashboard, "DashboardAudioButton", f"{name} dashboard audio control")
    forbid(dashboard, "PLAY SECTION VIDEO", f"{name} dashboard section video control")

require(platform_videos, "The 8 Core Videos Within The Platform", "eight core video admin")
require(platform_videos, "<DashboardSectionAudioAdmin />", "dedicated dashboard audio admin")
forbid(platform_videos, "<RecruitmentSectionVideosAdmin />", "Recruitment section video admin")
forbid(platform_videos, "<RecommitmentSectionVideosAdmin />", "Recommitment section video admin")
forbid(platform_videos, "<StrategicPlanningSectionVideosAdmin />", "Strategic section video admin")

require(admin, "Audio is never generated automatically", "explicit generation cost protection")
require(admin, "GENERATE TEST AUDIO", "Test ElevenLabs action")
require(admin, "GENERATE LIVE AUDIO", "Live ElevenLabs action")
require(admin, "REGENERATE LIVE AUDIO", "Live regeneration action")
require(admin, "without another deployment", "database-backed audio update guidance")

print("Dashboard contextual audio contract: PASS")
