from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Strategic Planning contract failed: missing {label}")

def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"Strategic Planning contract failed: found retired {label}")

dashboard = read("frontend/src/funnels/StrategicPlanningDashboard.jsx")
setup = read("frontend/src/funnels/StrategicOrganizationSetupPage.jsx")
form_page = read("frontend/src/funnels/StrategicPlanningFormPage.jsx")
session_page = read("frontend/src/funnels/StrategicPlanningSessionPage.jsx")
backend = read("backend/strategic_planning_routes.py")
guided = read("frontend/src/funnels/GuidedProductPages.jsx")
clean_backend = read("backend/clean_platform_routes.py")
platform_js = read("frontend/src/clean/platform.js")
admin = read("frontend/src/admin/PlatformVideosSection.jsx")
app = read("frontend/src/App.js")

for title in (
    "TELL US ABOUT YOUR ORGANIZATION",
    "SET YOUR NEXT STRATEGIC PLANNING MEETING",
    "COMPLETE YOUR OWN STRATEGIC PLANNING FORM",
    "INVITE YOUR BOARD AND COLLECT THEIR IDEAS",
    "PREPARE FOR THE STRATEGIC PLANNING SESSION",
    "RUN THE STRATEGIC PLANNING SESSION",
    "REVIEW THE STRATEGIC PLAN, CONFIRM ROLES AND MOVE INTO EXECUTION",
):
    require(dashboard, title, f"dashboard section: {title}")

for retired in (
    "Launch Community Need Research",
    "Generate The Strategic Planning Form",
    "Confirm Delegation And Give Everyone Their Execution Tools",
):
    forbid(dashboard, retired, f"retired dashboard stage: {retired}")

require(dashboard, 'videoKey="organization"', "organization section video")
require(dashboard, 'videoKey="meeting"', "meeting section video")
require(dashboard, 'videoKey="founder-form"', "founder-form section video")
require(dashboard, 'videoKey="board-forms"', "Board forms section video")
require(dashboard, 'videoKey="facilitation-guide"', "facilitation-guide section video")
require(dashboard, 'videoKey="live-session"', "live-session section video")
require(dashboard, 'videoKey="plan-execution"', "plan/execution section video")
require(dashboard, "SUPPORT THROUGHOUT THE PROCESS", "persistent support")

for key in (
    "mission", "goals", "objectives", "program_details", "team_building", "technology",
    "marketing", "partnerships", "fundraising", "budget", "action_planning",
):
    require(setup, f'key:"{key}"', f"organization setup field {key}")
require(setup, "logo_data_url", "organization logo data")
require(setup, "ADD ANOTHER PROGRAM", "separate program builder")
require(app, 'path="/strategic-planning/organization"', "canonical organization setup route")
require(guided, 'product!=="strategic-planning"&&!context.intake?.answers', "legacy intake bypass for Strategic Planning")

require(backend, '@router.get("/planning-meeting")', "planning meeting read")
require(backend, '@router.put("/planning-meeting")', "planning meeting save")
require(dashboard, "meeting_date", "meeting date UI")
require(dashboard, "start_time", "meeting time UI")
require(dashboard, "timezone_name", "meeting timezone UI")

require(backend, 'role":"Lead User"', "Lead User form record")
require(dashboard, "preparingForm.current", "automatic Strategic Planning Form preparation")
require(dashboard, "lead_form_token", "founder uses same Strategic Planning Form")
require(form_page, "planning_meeting", "meeting details on participant form")
require(dashboard, "VIEW RESPONSE", "participant response review")
require(dashboard, "DOWNLOAD", "participant response download")
require(dashboard, "RESEND FORM", "participant form reminder")

require(backend, '@router.get("/facilitation-guide/pdf")', "downloadable facilitation guide")
require(dashboard, "DOWNLOAD GUIDE", "facilitation guide download action")
require(session_page, "START MICROPHONE TRANSCRIPTION", "live meeting transcription")
require(session_page, "shared Board screen", "shared Board screen")
require(backend, '"allow_keep_current_mission":"mission" in section["title"].lower()', "mission preservation control")
require(session_page, "LEAVE THE MISSION STATEMENT THE WAY IT IS", "mission unchanged action")

require(session_page, 'axios.post(`${API}/guided/strategic-planning/session-plan`', "automatic final plan trigger at session completion")
require(dashboard, "triggeringPlan.current", "dashboard fallback final-plan trigger")
require(backend, "Executive Summary; Mission; Goals; Objectives; Programs; Team Building / Team Structure; Technology; Marketing; Partnerships; Fundraising; Budget; Action Planning", "canonical final plan order")
require(backend, "Every program must be its own named subsection", "program-specific final plan")
require(backend, "Do not create a separate Operations section", "no standalone Operations section")
require(backend, '"share_token":plan.get("share_token") or secrets.token_urlsafe(32)', "Board review token before adoption")
require(dashboard, "COPY BOARD REVIEW LINK", "Board review link")
require(dashboard, "SEND REVIEW LINK TO PARTICIPANTS", "send Board review link")
require(dashboard, "APPROVE & ADOPT STRATEGIC PLAN", "founder adoption action")

require(dashboard, "Everybody who completed the planning process appears here", "participant role confirmation")
require(dashboard, "Confirmed Board / leadership role", "role confirmation")
require(dashboard, "CREATE LEADERSHIP PORTFOLIOS & ASSISTANTS", "portfolio generation")
require(backend, '@router.post("/leadership-portfolio/send")', "Portfolio delivery")
require(backend, '@router.get("/leadership-assistant/{token}")', "Strategic Leadership Assistant")
require(backend, "Do not infer responsibility merely because somebody suggested an idea", "delegation inference protection")

require(clean_backend, "STRATEGIC_PLANNING_SECTION_VIDEO_DEFINITIONS", "Strategic Planning section video backend")
require(platform_js, "STRATEGIC_PLANNING_SECTION_VIDEO_KEYS", "Strategic Planning section video frontend")
require(admin, "Strategic Planning Dashboard Section Videos", "Strategic Planning video admin")

print("Strategic Planning clean-house contract: PASS")
