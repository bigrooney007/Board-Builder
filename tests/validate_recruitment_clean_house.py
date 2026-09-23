from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Recruitment contract failed: missing {label}")


def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"Recruitment contract failed: found retired {label}")


app = read("frontend/src/App.js")
public = read("frontend/src/funnels/RecruitFreePage.jsx")
dashboard = read("frontend/src/member/BoardRecruitmentPage.jsx")
questions = read("frontend/src/member/RecruitmentGameIntake.jsx")
workspace = read("backend/workspace_routes.py")
member = read("backend/member_routes.py")
voice = read("backend/voice_content.py")
platform = read("frontend/src/clean/platform.js")

require(app, 'path="/app/board-recruitment/questions"', "six-question route")
require(app, 'path="/app/board-recruitment/game" element={<Navigate to="/app/board-recruitment/questions"', "legacy game redirect")
forbid(app, '/>\\n      <Route path="/app/board-recruitment', "escaped JSX route newline")

require(public, 'navigate("/recruit/walkthrough")', "public Recruitment handoff to demonstration page")
forbid(public, "QUESTION 1 OF 4", "public four-question assessment UI")
forbid(public, "saveAnswer", "public strategic-question handler")

for title in (
    "ANSWER THE SIX RECRUITMENT QUESTIONS",
    "IDENTIFY THE BOARD MEMBERS YOUR ORGANIZATION NEEDS",
    "BUILD YOUR BOARD APPLICATION AND RECRUITMENT MATERIALS",
    "LAUNCH YOUR RECRUITMENT CAMPAIGN",
    "APPLICANTS",
    "INTERVIEWS",
    "REFERENCE CHECKS",
    "BACKGROUND CHECK",
    "PREPARE ONBOARDING AND THE APPOINTMENT",
    "RUN THE BOARD MEMBER ONBOARDING SESSION",
    "BOARD MEMBER PORTFOLIOS",
):
    require(dashboard, title, f"dashboard section: {title}")

require(dashboard, 'status={progress<3?"Locked":"Prepare"}', "approval gate for downstream Recruitment stages")
require(dashboard, 'SupportBox productKey="recruitment_self_guided"', "persistent Recruitment support")

for key in ("mission", "current_board", "desired_board_members", "support_needs", "board_type", "why_join"):
    require(questions, f'key: "{key}"', f"six-question key {key}")
for audio in range(1, 7):
    require(questions, f'audio: "rct_question_{audio}"', f"question {audio} narration")

require(workspace, '"materials_approved"', "campaign-material approval readiness")
require(workspace, 'Review and approve all four recruitment campaign materials before launching your campaign', "campaign launch approval guard")
require(workspace, '@router.post("/onboarding-live/share")', "live onboarding share route")
require(workspace, '@router.post("/onboarding-live/start")', "live onboarding start route")
require(workspace, '@router.post("/onboarding-live/progress")', "live onboarding progress route")
require(workspace, '@router.post("/onboarding-live/complete")', "live onboarding complete route")
require(workspace, '"portfolio_role_approved"', "portfolio role approval state")
require(workspace, 'asyncio.create_task(background_prepare_board_role', "background Board-role recommendation")

require(member, 'extra_entitlements.append("recruitment_selection_onboarding")', "$497 selection/onboarding entitlement")
require(member, 'lead_updates["phone"] = purchase["payment_phone"]', "Stripe phone preservation")

for audio in range(1, 7):
    require(voice, f'"rct_question_{audio}"', f"Recruitment question {audio} voice asset")
for key in ("questions", "identify", "materials", "launch", "applicants", "interviews", "references", "background", "onboarding-prep", "onboarding-session", "portfolios"):
    require(platform, f'["{key}",', f"section video key {key}")

print("Recruitment clean-house contract: PASS")
