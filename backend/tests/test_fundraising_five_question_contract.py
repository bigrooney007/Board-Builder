"""Dependency-free checks for the free five-question journey and paid board handoff."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


class FundraisingFiveQuestionContractTests(unittest.TestCase):
    def test_opening_form_starts_free_game_and_direct_demo_is_separate(self):
        start = source("frontend/src/game/GameStartPage.jsx")
        app = source("frontend/src/App.js")
        demo = source("frontend/src/game/GameDemonstrationPage.jsx")
        self.assertIn('navigate("/game/questions")', start)
        self.assertIn('path="/game/demonstration" element={<GameDemonstrationPage />}', app)
        self.assertIn('path="/game/questions" element={<GameFreeQuestionsPage />}', app)
        self.assertIn('path="/game/upgrade" element={<GameUpgradePage />}', app)
        self.assertNotIn('if (!member) return <Navigate', demo)

    def test_free_api_records_raw_input_and_never_calls_generation(self):
        tree = ast.parse(source("backend/game_routes.py"))
        create_router = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "create_game_router")
        functions = {node.name: node for node in create_router.body if isinstance(node, ast.AsyncFunctionDef)}
        save = ast.get_source_segment(source("backend/game_routes.py"), functions["save_free_game_answer"])
        self.assertIn('f"answers.{question_number}": payload.answer', save)
        self.assertIn('range(1, question_number)', save)
        self.assertNotIn("generate", save)
        self.assertNotIn("openai", save.lower())
        self.assertNotIn(".strip()[:", save)

    def test_paid_path_imports_five_answers_and_group_uses_them(self):
        night = source("backend/game_night_routes.py")
        group = source("backend/group_game_routes.py")
        meeting = source("backend/game_meeting_routes.py")
        strategy = source("backend/strategy_routes.py")
        self.assertIn('"original_answers": original', night)
        self.assertIn('"game_version": 5, "total_sections": 6', night)
        self.assertIn('"current_question": 5', night)
        self.assertIn('f"original_answers.{question_number}": payload.answer', night)
        self.assertIn('"involvement": payload.involvement', night)
        for downstream in (group, meeting, strategy):
            self.assertIn('get("original_answers")', downstream)
        self.assertIn('cancel_path: "/game/upgrade"', source("frontend/src/game/GameUpgradePage.jsx"))

    def test_homepage_promise_has_three_meeting_steps_and_four_outcomes(self):
        tree = ast.parse(source("backend/game_routes.py"))
        content = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == "DEFAULT_CONTENT" for target in node.targets))
        self.assertEqual(content["headline"], "GET YOUR BOARD MEMBERS RAISING MONEY FROM YOUR NEXT BOARD MEETING")
        self.assertEqual(len(content["stages"]), 3)
        self.assertEqual(len(content["outcomes"]), 4)
        self.assertEqual(len(content["agent_questions"]), 5)


if __name__ == "__main__":
    unittest.main()
