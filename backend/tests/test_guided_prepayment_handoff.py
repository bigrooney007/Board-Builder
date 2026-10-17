"""Offline paid-handoff contract: saved public answers seed existing workspaces once."""
import ast
import asyncio
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets
import unittest

BACKEND = Path(__file__).resolve().parents[1]
FIELDS = {
    "board-recommitment": ("mission", "why_recommit", "board_help_accomplish", "need_by"),
    "strategic-planning": ("mission", "goals", "objectives", "program_details", "team_building", "technology", "marketing", "partnerships", "fundraising", "budget", "action_planning"),
}


class Collection:
    def __init__(self, records=()):
        self.records = [copy.deepcopy(record) for record in records]

    async def find_one(self, query, *args, **kwargs):
        return copy.deepcopy(next((row for row in self.records if all(row.get(key) == value for key, value in query.items())), None))

    async def insert_one(self, record):
        self.records.append(copy.deepcopy(record))

    async def update_one(self, query, update, upsert=False):
        row = next((record for record in self.records if all(record.get(key) == value for key, value in query.items())), None)
        if row is None and upsert:
            row = {**query, **copy.deepcopy(update.get("$setOnInsert", {}))}
            self.records.append(row)
        if row is not None:
            row.update(copy.deepcopy(update.get("$set", {})))


class Db:
    def __init__(self, lead):
        self.guided_product_leads = Collection([lead])
        self.guided_product_intakes = Collection()
        self.board_reactivation_intakes = Collection()
        self.sp_projects = Collection()
        self.sp_participants = Collection()


def builders(db):
    tree = ast.parse((BACKEND / "guided_product_routes.py").read_text())
    factory = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "create_guided_product_router")
    selected = [node for node in factory.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in {"clean_preanswers", "complete_preanswers", "hydrate_paid_journey"}]
    namespace = {"db": db, "prepayment_fields": FIELDS, "datetime": datetime, "timezone": timezone,
                 "timedelta": timedelta, "secrets": secrets}
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])), "guided_product_routes.py", "exec"), namespace)
    return namespace


class PaidHandoff(unittest.IsolatedAsyncioTestCase):
    async def test_strategic_answers_create_one_ready_organization_and_one_lead_participant(self):
        answers = {key: f"Provided {key} answer" for key in FIELDS["strategic-planning"] if key != "program_details"}
        answers["program_details"] = [{"name": "Youth Mentoring", "description": "Mentoring", "present_work": "Weekly"}]
        db = Db({"token": "lead", "email": "lead@example.org", "name": "Alex Founder",
                 "organization": "BrightPath", "prepayment_answers": answers})
        functions = builders(db)
        self.assertTrue(functions["complete_preanswers"]("strategic-planning", answers))
        tx = {"guided_lead_token": "lead", "session_id": "paid-session"}
        await functions["hydrate_paid_journey"](tx, "strategic-planning", {"user_id": "owner"})
        await functions["hydrate_paid_journey"](tx, "strategic-planning", {"user_id": "owner"})
        self.assertEqual(len(db.guided_product_intakes.records), 1)
        self.assertEqual(db.guided_product_intakes.records[0]["answers"], answers)
        self.assertEqual(len(db.sp_projects.records), 1)
        self.assertTrue(db.sp_projects.records[0]["organization_details_saved_at"])
        self.assertEqual(len(db.sp_participants.records), 1)
        self.assertEqual(db.sp_participants.records[0]["role"], "Lead User")

    async def test_recommitment_answers_arrive_before_board_member_outreach(self):
        answers = {"mission": "Youth opportunity", "why_recommit": "Board needs to step up",
                   "board_help_accomplish": "Help build partnerships", "need_by": "2026-11-15"}
        db = Db({"token": "lead", "email": "lead@example.org", "name": "Alex Founder",
                 "organization": "BrightPath", "prepayment_answers": answers})
        functions = builders(db)
        tx = {"guided_lead_token": "lead", "session_id": "paid-session"}
        await functions["hydrate_paid_journey"](tx, "board-recommitment", {"user_id": "owner"})
        await functions["hydrate_paid_journey"](tx, "board-recommitment", {"user_id": "owner"})
        self.assertEqual(len(db.board_reactivation_intakes.records), 1)
        intake = db.board_reactivation_intakes.records[0]
        self.assertEqual(intake["need_by"], answers["need_by"])
        self.assertEqual(intake["why_recommit"], answers["why_recommit"])
        self.assertEqual(intake["board_help_accomplish"], answers["board_help_accomplish"])
        self.assertEqual(db.guided_product_intakes.records[0]["answers"], answers)


if __name__ == "__main__":
    unittest.main()
