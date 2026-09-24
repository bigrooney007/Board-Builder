from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Platform communications contract failed: missing {label}")

service = read("backend/platform_communications.py")
recruit = read("backend/recruit_free_routes.py")
recruit_ui = read("frontend/src/funnels/RecruitWalkthroughPage.jsx")
guided = read("backend/guided_product_routes.py")
member = read("backend/member_routes.py")
game = read("backend/game_routes.py")
game_ui = read("frontend/src/game/GameResumePage.jsx")
app = read("frontend/src/App.js")
strategic = read("backend/strategic_planning_routes.py")
game_night = read("backend/game_night_routes.py")
recommitment = read("backend/reactivation_routes.py")
opportunity = read("backend/public_opportunity_routes.py")
applicant = read("backend/applicant_routes.py")
facilitated = read("backend/facilitated_game_application_routes.py")

for pathway in ("recruitment", "board-fundraising-game", "strategic-planning", "board-recommitment"):
    require(service, f'"{pathway}"', f"homepage email pathway {pathway}")
require(service, "OWNER_NOTIFICATION_EMAIL", "owner recipient")
require(service, "CONTINUE WHERE I STOPPED", "immediate prospect return CTA")
require(service, "platform_email_events", "homepage email idempotency log")
require(service, "owner_status", "owner delivery state")
require(service, "prospect_status", "prospect delivery state")

require(recruit, 'pathway="recruitment"', "Recruitment homepage owner/prospect email")
require(recruit, "/recruit/walkthrough?token=", "Recruitment emailed return token")
require(recruit_ui, 'searchParams.get("token")', "Recruitment walkthrough token recovery")

require(guided, "notify_homepage_lead", "guided homepage communication call")
require(guided, 'next_url=f"{root}/{payload.product}/video?token={token}"', "Strategic/Recommitment immediate return URL")

require(member, 'pathway="board-fundraising-game"', "Fundraising Game homepage communication")
require(member, "game_resume_tokens", "Fundraising Game secure resume token")
require(member, '@router.post("/game-resume/{resume_token}")', "Fundraising Game resume endpoint")
require(game, "homepage_capture", "authenticated Fundraising Game homepage capture")
require(game_ui, "/members/game-resume/", "Fundraising Game resume redemption UI")
require(app, 'path="/game/resume/:token"', "Fundraising Game resume frontend route")

require(strategic, "Strategic Planning Response Received", "Strategic Planning purchaser response alert")
require(strategic, "owner_notification_status", "Strategic Planning alert state")
require(game_night, "Board Fundraising Game Response Received", "Fundraising Game purchaser response alert")
require(game_night, "owner_notification_status", "Fundraising Game alert state")
require(recommitment, "Board Member Recommitment Received", "Recommitment purchaser response alert")
require(recommitment, "result.modified_count", "idempotent Recommitment alert")
require(opportunity, "Board Application Received", "Recruitment application purchaser alert")
require(opportunity, "owner_notification_status", "Recruitment application alert state")

require(applicant, "send_owner_applicant_profile", "Board Applicant Network owner alert")
require(facilitated, "OWNER_NOTIFICATION_EMAIL", "Facilitated Game application owner alert")

print("Platform communications contract: PASS")
