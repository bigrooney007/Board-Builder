"""Dependency-free contracts for the four public-to-dashboard customer journeys."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class FourCustomerJourneysContractTests(unittest.TestCase):
    def test_every_self_guided_checkout_uses_the_shared_account_page(self):
        payment = source("backend/payment_routes.py")
        self.assertGreaterEqual(payment.count('/purchase/success?session_id='), 4)
        self.assertIn('"offer_source": "board_fundraising_game"', payment)
        self.assertIn('"metadata": {"offer_source": product.replace("-", "_")', payment)

    def test_account_page_continues_to_the_first_useful_action(self):
        success = source("frontend/src/member/PurchaseSuccessPage.jsx")
        for purchase, destination in (
            ("recruitment_497", "/app/board-recruitment/setup"),
            ("board_fundraising_game_497", "/game/setup"),
            ("strategic_planning_497", "/strategic-planning/dashboard"),
            ("board_recommitment_497", "/board-recommitment/dashboard"),
        ):
            self.assertIn(purchase, success)
            self.assertIn(destination, success)
        self.assertIn("CREATE ACCOUNT AND CONTINUE", success)

    def test_old_welcome_pages_are_compatibility_redirects(self):
        app = source("frontend/src/App.js")
        self.assertIn('<Route path="/recruit/welcome" element={<Navigate to="/app/board-recruitment/setup" replace />} />', app)
        self.assertIn('<Route path="/game/welcome" element={<Navigate to="/game/setup" replace />} />', app)
        self.assertIn('GuidedPaidContinue product="strategic-planning"', app)
        self.assertIn('GuidedPaidContinue product="board-recommitment"', app)

    def test_recruitment_setup_and_dashboard_follow_the_approved_stage_order(self):
        setup = source("frontend/src/member/RecruitCampaignSetupPage.jsx")
        dashboard = source("frontend/src/member/BoardRecruitmentPage.jsx")
        for phrase in ("STEP 1 · BOARD PROFILES", "STEP 2 · INTERVIEW SCHEDULING",
                       "STEP 3 · REVIEW CAMPAIGN MATERIALS", "STEP 4 · LAUNCH"):
            self.assertIn(phrase, setup)
        ids = ["br-section-questions", "br-section-identify", "br-section-materials", "br-section-campaign",
               "br-section-applicants", "br-section-references", "br-section-background", "br-section-selection",
               "br-section-onboarding-prep", "br-section-onboarding-session", "br-section-portfolios"]
        positions = [dashboard.index(f'["{item}"') for item in ids]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("<InterviewsWorkspace/>", dashboard)
        self.assertIn("<CandidateSelectionWorkspace/>", dashboard)
        self.assertIn("<FormalAppointmentWorkspace/>", dashboard)

    def test_game_setup_collects_reality_participation_then_meeting_before_invites(self):
        setup = source("frontend/src/game/GameSituationPage.jsx")
        dashboard = source("frontend/src/game/GameDashboardPage.jsx")
        self.assertIn('navigate("/play/" + self.data.token)', setup)
        self.assertNotIn('setPhase("capacity")', setup)
        self.assertIn('setPhase("meeting")', setup)
        self.assertIn('/game/dashboard#bfg-board-members-section', setup)
        self.assertLess(dashboard.index('number={1}'), dashboard.index('number={2}'))
        self.assertLess(dashboard.index('number={2}'), dashboard.index('number={3}'))

    def test_strategic_board_invites_open_after_the_meeting_and_plan_review_stays_live(self):
        dashboard = source("frontend/src/funnels/StrategicPlanningDashboard.jsx")
        session = source("frontend/src/funnels/StrategicPlanningSessionPage.jsx")
        board = source("frontend/src/funnels/StrategicSessionWatchPage.jsx")
        self.assertIn('locked={!meetingReady}', dashboard)
        self.assertIn('setOpen("4")', dashboard)
        self.assertIn("SAVE AGREED EDITS TO SHARED SCREEN", session)
        self.assertIn("APPROVE & ADOPT WITH THE BOARD", session)
        self.assertIn("Review The Strategic Plan Together", board)

    def test_private_return_links_are_hashed_and_product_bound(self):
        backend = source("backend/dashboard_return.py")
        member = source("backend/member_routes.py")
        frontend = source("frontend/src/member/DashboardReturnPage.jsx")
        self.assertIn("hashlib.sha256", backend)
        self.assertIn("dashboard_return_tokens", backend)
        self.assertIn('@router.post("/dashboard-return/{token}")', member)
        self.assertIn("window.history.replaceState", frontend)
        self.assertIn("window.location.replace(data.dashboard_url)", frontend)

    def test_admin_controls_cover_the_four_videos_and_every_form_dashboard_audio_group(self):
        videos = source("frontend/src/admin/PlatformVideosSection.jsx")
        audio = source("frontend/src/admin/DashboardSectionAudioAdmin.jsx")
        voice = source("backend/voice_content.py")
        for key in ("recruitment_upgrade", "game_homepage", "strategic_planning_demonstration", "board_recommitment_demonstration"):
            self.assertIn(key, videos)
        for group in ("Board Fundraising Game · Lead And Board Forms", "Board Recruitment Dashboard Audio",
                      "Board Fundraising Game Dashboard Audio", "Board Recommitment Dashboard Audio",
                      "Strategic Planning Dashboard Audio"):
            self.assertIn(group, audio)
        self.assertIn("dash_rct_selection", audio)
        self.assertIn("Tell us who they are and why you believe they would give", voice)

    def test_video_offer_pages_display_only_the_short_guarantee_label(self):
        cards = source("frontend/src/components/DemoOfferCards.jsx")
        offers = source("frontend/src/funnels/OfferVideoPage.jsx")
        self.assertIn("100% Guarantee", cards)
        self.assertIn("100% Guarantee", offers)
        self.assertNotIn("card.guarantee", cards)
        self.assertNotIn("REQUEST A REFUND", cards + offers)
        guided = source("frontend/src/funnels/GuidedProductPages.jsx")
        self.assertNotIn("refund 100%", guided)


if __name__ == "__main__":
    unittest.main()
