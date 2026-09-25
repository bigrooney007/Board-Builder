"""Dependency-free contract checks for the customer-facing Fundraising Game v4 flow."""
import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def literal_assignment(path: str, name: str):
    tree = ast.parse(source(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} is not assigned in {path}")


class FundraisingV4ContractTests(unittest.TestCase):
    def test_individual_game_has_all_six_audience_dimensions_and_involvement(self):
        routes = source("backend/game_night_routes.py")
        play = source("frontend/src/game/GamePlayPage.jsx")
        self.assertEqual(
            literal_assignment("backend/game_night_routes.py", "AUDIENCE_FIELDS"),
            ("audience", "reason", "where", "attraction", "funding_ask", "process"),
        )
        self.assertEqual(play.count('["audience",'), 3)
        self.assertEqual(play.count('["reason",'), 3)
        self.assertEqual(play.count('["where",'), 3)
        self.assertEqual(play.count('["attraction",'), 3)
        self.assertEqual(play.count('["funding_ask",'), 3)
        self.assertEqual(play.count('["process",'), 3)
        self.assertIn('data-testid="bfg-involvement"', play)
        self.assertIn('@router.post("/game/play/{token}/audience-response/complete")', routes)
        self.assertIn("Complete every question for each audience you selected", routes)

    def test_lead_present_context_has_five_fields_for_each_audience(self):
        page = source("frontend/src/game/GameSituationPage.jsx")
        for audience in ("individual_donor", "business", "grantor"):
            for field in ("profile", "where", "attraction", "support", "process"):
                self.assertIn(f'current_{audience}_{field}', page)
        self.assertIn('reviewed: "yes"', page)
        self.assertIn('Number(situation.data.current_step || 0)', page)

    def test_meeting_deadline_flows_into_the_profile_used_by_strategy_generation(self):
        night = source("backend/game_night_routes.py")
        group = source("backend/group_game_routes.py")
        strategy = source("backend/game_meeting_routes.py")
        self.assertIn('"funding_deadline": payload.funding_deadline.strip()', night)
        self.assertIn('"goal.deadline": payload.funding_deadline.strip()', night)
        self.assertIn('night.get("funding_deadline") or (profile.get("goal") or {}).get("deadline", "")', group)
        self.assertIn('"currency": "USD", "deadline": goal.get("deadline", "")', strategy)

    def test_group_game_has_the_six_required_board_decisions(self):
        group = source("backend/group_game_routes.py")
        self.assertIn("TOTAL_ROUNDS = 6", group)
        definitions = literal_assignment("backend/group_game_routes.py", "ROUND_DEFS")
        self.assertEqual(
            [row["section_key"] for row in definitions],
            ["funding_audiences", "where_to_find", "attraction", "funding_ask", "fundraising_process", "board_roles"],
        )
        self.assertIn("game_audience_responses", group)
        self.assertIn("PRESENT {audience_labels[audience_key]}", group)

    def test_final_strategy_is_v4_and_contains_only_the_required_plan_sections(self):
        strategy = source("backend/strategy_routes.py")
        final = source("backend/game_meeting_routes.py")
        expected = ["executive_summary", "fundraising_audiences", "where_to_find", "attraction", "funding_ask", "fundraising_process", "board_roles"]
        self.assertEqual(literal_assignment("backend/strategy_routes.py", "CORE_STRATEGY_KEYS"), expected)
        self.assertEqual(literal_assignment("backend/game_meeting_routes.py", "CORE_STRATEGY_KEYS"), expected)
        self.assertIn('"schema_version": 4', strategy)
        self.assertIn('"schema_version": 4', final)
        self.assertIn("Do not replace their ideas with your own", final)
        self.assertIn("Leave unsupported parts empty", final)
        self.assertIn('"schema_version": strategy.get("schema_version", 1)', strategy)

    def test_v4_response_view_does_not_repeat_legacy_sections(self):
        responses = source("frontend/src/game/BoardMembersSection.jsx")
        self.assertIn("!audienceResponse.audiences && data.responses.map", responses)

    def test_admin_previews_are_product_isolated_and_materials_are_on_demand(self):
        fixtures = source("backend/admin_dashboard_preview_routes.py")
        portfolio = source("frontend/src/game/BoardPortfolioPage.jsx")
        assistant = source("frontend/src/game/BoardExecutionAssistantPage.jsx")
        self.assertIn('hashlib.sha256(member["user_id"].encode("utf-8")).hexdigest()[:16]', fixtures)
        self.assertIn('delete_many({"user_id": member["user_id"], "internal_preview": True})', fixtures)
        self.assertNotIn('"material_packs": [{', fixtures)
        self.assertNotIn("<ToolkitView", portfolio)
        self.assertIn("Recommended For Your Role", assistant)
        self.assertIn("suggested_materials", assistant)

    def test_final_review_adoption_and_delegation_are_connected_in_customer_ui(self):
        app = source("frontend/src/App.js")
        dashboard = source("frontend/src/game/GameDashboardPage.jsx")
        final_page = source("frontend/src/game/FinalStrategyPage.jsx")
        review_routes = source("backend/meeting_review_routes.py")
        portfolios = source("backend/portfolio_routes.py")
        self.assertIn('path="/game/meeting-review/final" element={<FinalStrategyPage />}', app)
        self.assertIn("Every participant who joined the Group Game must select Adopt", final_page)
        self.assertIn("Every participant must adopt the final strategy", review_routes)
        self.assertIn('data-testid="bfg-start-delegation-btn"', final_page)
        self.assertIn("if audience_response or response_count > 0 or record[\"member_id\"] in joined_ids", portfolios)
        self.assertIn("ready={Boolean(postgame?.adopted)}", dashboard)

    def test_strategy_and_relationship_mapping_use_separate_emails(self):
        postgame = source("backend/postgame_routes.py")
        complete = source("frontend/src/game/GameNightCompletePage.jsx")
        self.assertIn("Open My Board Fundraising Portfolio", postgame)
        self.assertIn("Open My Personal Fundraising Assistant", postgame)
        self.assertIn('@router.post("/game/postgame/relationships/send")', postgame)
        self.assertIn("timedelta(hours=24)", postgame)
        self.assertIn("Send this as a separate email about 24 hours", complete)

    def test_audio_control_is_one_play_icon_and_preview_seeds_real_customer_collections(self):
        audio = source("frontend/src/game/NarrationControl.jsx")
        fixtures = source("backend/admin_dashboard_preview_routes.py")
        self.assertEqual(audio.count("<button"), 1)
        self.assertIn('aria-label="Play audio instructions"', audio)
        self.assertNotIn("Coming soon", audio)
        self.assertIn('FUNDRAISING_FIXTURE_VERSION = "v8"', fixtures)
        for collection in ("game_audience_responses", "group_game_rounds", "game_strategies", "meeting_review_sessions", "final_board_approvals", "board_portfolios", "game_relationship_deliveries"):
            self.assertIn(f"db.{collection}", fixtures)


if __name__ == "__main__":
    unittest.main()
