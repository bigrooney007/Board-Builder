from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Board Recommitment contract failed: missing {label}")

def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"Board Recommitment contract failed: found retired {label}")

dashboard = read("frontend/src/member/BoardRecommitmentDashboard.jsx")
questions = read("frontend/src/member/RecommitmentQuestionsPage.jsx")
forms_section = read("frontend/src/member/RecommitmentFormsSection.jsx")
direct_invite = read("frontend/src/member/RecommitmentInviteBoardMembers.jsx")
public_form = read("frontend/src/funnels/BoardRecommitmentFormPage.jsx")
understand = read("frontend/src/member/ReactivationUnderstand.jsx")
final_stage = read("frontend/src/member/RecommitmentFinalStage.jsx")
portfolio_workflow = read("frontend/src/member/ReactivationStep5.jsx")
portfolio_page = read("frontend/src/pages/PortfolioPage.jsx")
assistant_page = read("frontend/src/pages/RecommitmentAssistantPage.jsx")
backend = read("backend/reactivation_routes.py")
voice = read("backend/voice_content.py")
audio_button = read("frontend/src/clean/DashboardAudioButton.jsx")
app = read("frontend/src/App.js")

for title in (
    "ANSWER FOUR IMPORTANT QUESTIONS",
    "PREPARE AND SEND THE RECOMMITMENT FORMS",
    "REVIEW RESPONSES AND PREPARE THE CONVERSATION",
    "CONFIRM THE FINAL OUTCOME AND MOVE EACH PERSON FORWARD",
):
    require(dashboard, title, f"dashboard section: {title}")

for retired in ("FounderBoardAudit", "ProgressSummary", "ReactivationStep3", "RecommitmentInviteBoardMembers"):
    forbid(dashboard, retired, f"old standalone dashboard stage {retired}")

require(dashboard, 'SupportBox productKey="reactivation_self_guided"', "persistent Recommitment support")
require(dashboard, "DashboardAudioButton", "per-section Recommitment audio control")
for audio_id in ("dash_rec_questions","dash_rec_forms","dash_rec_responses","dash_rec_decisions"):
    require(voice, f'"{audio_id}"', f"Recommitment dashboard audio {audio_id}")
require(audio_button, "PLAY AUDIO", "shared dashboard audio play control")

for key in ("mission", "why_recommit", "board_help_accomplish", "need_by"):
    require(questions, f'key: "{key}"', f"founder setup question {key}")
require(questions, "logo_data_url", "organization logo on setup")
require(app, 'path="/board-recommitment/questions"', "canonical four-question route")

require(backend, '@router.get("/reactivation/setup")', "setup read endpoint")
require(backend, '@router.put("/reactivation/setup")', "setup save endpoint")
require(backend, "RECOMMIT_ACTIVE", "active recommitment choice")
require(backend, "RECOMMIT_ADVISORY", "Advisory Board choice")
require(backend, "RECOMMIT_STEP_DOWN", "step-down choice")
require(public_form, 'form.form_variant === "active_advisory"', "no-step-down form variant")
require(public_form, "STEP_DOWN", "full form step-down option")
forbid(public_form, "I am not sure yet", "unsure public form pathway")

require(forms_section, "Active Board / Advisory Board", "active/advisory form card")
require(forms_section, "Full Recommitment / Transition", "full transition form card")
require(forms_section, "COPY APPROVED EMAIL", "copyable approved outreach email")
require(forms_section, "RecommitmentInviteBoardMembers", "direct platform sending inside forms section")
require(direct_invite, 'value="active_advisory"', "direct-send no-step-down form variant")
require(direct_invite, 'value="full"', "direct-send full form variant")
forbid(direct_invite, 'value="standard"', "retired standard form selector")
require(backend, '@router.put("/reactivation/recommitment-email-draft")', "editable outreach email")
require(backend, '@router.post("/reactivation/recommitment-email-draft/approve")', "outreach email approval")

require(understand, "DOWNLOAD RESPONSE", "response download")
require(understand, "INTERPRET RESPONSE", "response interpretation")
require(understand, "GENERATE INDIVIDUAL CALL SCRIPT", "individual conversation script")
forbid(understand, "/app/reactivation/self-guided/module/", "legacy module links")

require(backend, "direction_source", "form-derived conversation direction")
require(backend, 'RECOMMIT_ACTIVE: "Remain and Step Up"', "active call direction")
require(backend, 'RECOMMIT_ADVISORY: "Move to Advisory Board"', "advisory call direction")
require(backend, 'RECOMMIT_STEP_DOWN: "Step Down"', "step-down call direction")

require(final_stage, "Continuing as an Active Board Member", "active final outcome")
require(final_stage, "Transitioning to an Advisory Role", "advisory final outcome")
require(final_stage, "Stepping Down From the Board", "step-down final outcome")
forbid(final_stage, "Transitioning to Another Support Role", "support-role final pathway")
require(final_stage, "confirmed-role", "founder-confirmed role save")
require(backend, "Record what you and this Board Member actually agreed before generating their Portfolio", "Portfolio conversation-agreement gate")
require(backend, "Confirm or edit this person's final Board role before generating their Portfolio", "Portfolio role gate")

require(portfolio_workflow, "COPY EMAIL", "copy Portfolio email")
require(portfolio_workflow, "SEND PORTFOLIO FROM PLATFORM", "platform Portfolio send")
require(backend, '@router.get("/portfolio-assistant/{token}")', "Recommitment execution assistant read")
require(backend, '@router.post("/portfolio-assistant/{token}")', "Recommitment execution assistant action")
require(portfolio_page, "OPEN MY EXECUTIVE ASSISTANT", "Portfolio-to-assistant CTA")
require(assistant_page, "approved Board Member Portfolio", "assistant authority explanation")


print("Board Recommitment clean-house contract: PASS")
