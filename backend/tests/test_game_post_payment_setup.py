"""Checks the paid Board Fundraising Game sequence without requiring a live database."""
import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def complete_situation():
    source = (ROOT / "backend/game_routes.py").read_text()
    function = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == "situation_is_complete")
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "game_routes.py", "exec"), namespace)
    return namespace["situation_is_complete"]


def paid_situation():
    reality = {"reviewed": "yes", "setup_version": "post_payment_v2"}
    for group, prefix in (("individuals", "individual_donor"), ("businesses", "business"), ("grantors", "grantor")):
        reality[f"{group}_status"] = "current"
        for field in ("profile", "where", "attraction", "support", "process", "seeking"):
            reality[f"current_{prefix}_{field}"] = f"Real {prefix} {field}"
    reality["current_individual_donor_motivation"] = "They trust the mission"
    return {"completed": True, "current_step": 4, "sections": {
        "current_reality": reality,
        "team": {"who_handles": "Our staff", "board_involvement": "Board makes introductions"},
        "technology": {"tools": "Donor spreadsheet", "tech_working": "Manual follow-up"},
        "materials": {"materials": "Case for support"},
    }}


class PostPaymentSetupTests(unittest.TestCase):
    def test_current_supporters_need_the_separate_deep_answers_and_new_targets(self):
        is_complete = complete_situation()
        situation = paid_situation()
        self.assertTrue(is_complete(situation))
        situation["sections"]["current_reality"]["current_business_seeking"] = ""
        self.assertFalse(is_complete(situation))

    def test_absent_funders_are_explicitly_skippable_without_invented_answers(self):
        is_complete = complete_situation()
        situation = paid_situation()
        situation["sections"]["current_reality"]["businesses_status"] = "none"
        for key in list(situation["sections"]["current_reality"]):
            if key.startswith("current_business_"):
                situation["sections"]["current_reality"][key] = ""
        self.assertTrue(is_complete(situation))

    def test_team_resources_and_final_review_cannot_be_skipped(self):
        is_complete = complete_situation()
        situation = paid_situation()
        situation["sections"]["materials"]["materials"] = ""
        self.assertFalse(is_complete(situation))
        situation["sections"]["materials"]["materials"] = "None yet"
        situation["current_step"] = 3
        self.assertFalse(is_complete(situation))
        situation["current_step"] = 4
        situation["sections"]["current_reality"].pop("reviewed")
        self.assertFalse(is_complete(situation))

    def test_previously_completed_games_retain_their_progress(self):
        self.assertTrue(complete_situation()({"completed": True, "current_step": 3,
            "sections": {"current_reality": {"reviewed": "yes"}}}))

    def test_invitations_and_lead_participation_have_server_side_sequence_checks(self):
        source = (ROOT / "backend/game_night_routes.py").read_text()
        for route in ("add_board_member", "invite_board_member", "invite_all"):
            start = source.index(f"async def {route}(")
            end = source.find("    @router.", start)
            self.assertIn('await require_board_setup(member["user_id"])', source[start:end if end != -1 else None])
        self.assertIn('if record.get("is_primary"):', source[source.index("async def complete_five_ideas("):])
        self.assertIn("not situation_is_complete(situation)", source)

    def test_the_final_strategy_receives_raw_funder_targets_capacity_goal_and_deadline(self):
        for path in ("backend/game_meeting_routes.py", "backend/strategy_routes.py"):
            source = (ROOT / path).read_text()
            for value in ("current_individual_donor_seeking", "current_business_seeking",
                          "current_grantor_seeking", "current_individual_donor_motivation",
                          "current_team_and_resources", '"deadline": goal.get("deadline", "")'):
                self.assertIn(value, source)


if __name__ == "__main__":
    unittest.main()
