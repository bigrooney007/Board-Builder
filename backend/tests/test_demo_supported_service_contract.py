"""Dependency-free contracts for the four demonstration offers and supported-service handoff."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

class DemoSupportedServiceContractTests(unittest.TestCase):
    def test_all_four_demo_pages_show_two_paths_and_testimonials(self):
        recruit = source("frontend/src/funnels/RecruitWalkthroughPage.jsx")
        game = source("frontend/src/game/GameDemonstrationPage.jsx")
        guided = source("frontend/src/funnels/GuidedProductPages.jsx")
        for page in (recruit, game, guided):
            self.assertIn("DemoOfferCards", page)
            self.assertIn("TestimonialCarousel", page)
        self.assertIn('price:"$2,997"', recruit)
        self.assertIn('price:"$2,997"', game)
        self.assertIn('supportedPrice:"$2,497"', guided)
        self.assertIn('supportedPrice:"$2,997"', guided)
        self.assertIn("100% Outcome Guarantee", source("frontend/src/components/DemoOfferCards.jsx"))

    def test_supported_checkout_has_exact_products_prices_and_real_handoff(self):
        payments = source("backend/payment_routes.py")
        members = source("backend/member_routes.py")
        success = source("frontend/src/member/PurchaseSuccessPage.jsx")
        for offer, amount in (
            ("recruitment_supported_2997", "299700"),
            ("board_recommitment_supported_2497", "249700"),
            ("board_fundraising_game_supported_2997", "299700"),
            ("strategic_planning_supported_2997", "299700"),
        ):
            self.assertIn(offer, payments)
            self.assertIn(amount, payments)
            self.assertIn(offer, members)
            self.assertIn(offer, success)
        self.assertIn('@router.post("/supported-checkout")', payments)
        self.assertIn('@router.post("/supported-service/handoff-complete")', members)
        self.assertIn("/supported-service/thank-you", source("frontend/src/App.js"))

    def test_supported_clients_are_available_in_admin_operator_workspace(self):
        routes = source("backend/admin_service_routes.py")
        admin = source("frontend/src/admin/ClientDeliverySection.jsx")
        for offer in ("recruitment_supported_2997", "board_recommitment_supported_2497", "board_fundraising_game_supported_2997", "strategic_planning_supported_2997"):
            self.assertIn(offer, routes)
        self.assertIn("Supported-Service Clients", admin)
        self.assertIn("Take Me To This Client's Dashboard", admin)

    def test_onboarding_pages_have_centered_heading_video_and_dashboard_cta(self):
        recruit = source("frontend/src/funnels/RecruitWelcomePage.jsx")
        game = source("frontend/src/game/GameWelcomePage.jsx")
        guided = source("frontend/src/funnels/GuidedProductPages.jsx")
        self.assertIn("Welcome To Your Board Recruitment Platform", recruit)
        self.assertIn("GO TO MY DASHBOARD", recruit)
        self.assertIn("GO TO MY DASHBOARD", game)
        self.assertIn("GO TO MY DASHBOARD", guided)

if __name__ == "__main__":
    unittest.main()
