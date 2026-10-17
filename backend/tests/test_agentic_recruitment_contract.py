"""Offline checks for the paid result boundary and launch/portfolio dependencies.

Run without application services: python -m unittest discover -s backend/tests -p test_agentic_recruitment_contract.py
"""
import ast
import asyncio
from pathlib import Path
import types
import unittest


BACKEND = Path(__file__).resolve().parents[1]


def load_function(filename, name, parent=None, globals_=None):
    tree = ast.parse((BACKEND / filename).read_text())
    nodes = tree.body if parent is None else next(node.body for node in tree.body if getattr(node, "name", None) == parent)
    function = next(node for node in nodes if getattr(node, "name", None) == name)
    function.decorator_list = []
    namespace = dict(globals_ or {})
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, function], type_ignores=[])), filename, "exec"), namespace)
    return namespace[name]


class HttpError(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail


class Collection:
    def __init__(self, rows):
        self.rows = rows

    def find(self, query, projection):
        types_ = query["type"]["$in"]
        self.result = [row for row in self.rows if row["type"] in types_]
        return self

    async def to_list(self, limit):
        return self.result[:limit]

    async def find_one(self, query, projection=None):
        return next((row for row in self.rows if row.get("application_id") == query.get("application_id")
                     and row.get("user_id") == query.get("user_id")), None)


class AgenticRecruitmentContract(unittest.IsolatedAsyncioTestCase):
    def test_public_result_is_hidden_before_payment(self):
        public_assessment = load_function("recruit_free_routes.py", "public_assessment")
        doc = {"token": "private-link", "answers": {"mission": "Our mission"},
               "result": {"priority_roles": [{"role_name": "Community leadership"}]}, "_id": "mongo-id"}
        self.assertNotIn("result", public_assessment(doc))
        self.assertNotIn("_id", public_assessment(doc))
        self.assertIn("result", public_assessment(doc, include_result=True))

    async def test_result_generation_requires_paid_owner(self):
        doc = {"token": "private-link", "member_user_id": "owner", "state": {"paid": False}}
        async def find(*args):
            return object(), doc
        async def member(*args):
            return {"user_id": "owner"}
        called = []
        async def generate(*args):
            called.append(True)
            return {"priority_roles": []}
        result = load_function("recruit_free_routes.py", "result", "create_recruit_free_router", {
            "db": object(), "find_assessment": find, "authenticate_member": member,
            "generate_result_for_doc": generate, "HTTPException": HttpError,
        })
        with self.assertRaises(HttpError) as raised:
            await result("private-link", object())
        self.assertEqual(raised.exception.status_code, 403)
        self.assertFalse(called)
        doc["state"]["paid"] = True
        self.assertEqual((await result("private-link", object()))["result"], {"priority_roles": []})

    async def test_launch_requires_campaign_documents_and_support_communications(self):
        campaign = ["board_opportunity", "board_recruitment_job_post", "recruitment_emails", "social_posts", "referral_request_email"]
        onboarding = ["organization_overview", "board_manual", "board_member_agreement", "confidentiality_agreement", "conflict_of_interest_agreement", "onboarding_agenda"]
        support = ["general_interview_invitation", "recruitment_communications"]
        rows = [{"user_id": "owner", "type": kind, "application_id": "", "status": "Approved"}
                for kind in campaign + onboarding + support]
        db = types.SimpleNamespace(generated_materials=Collection(rows))
        async def material(*args):
            return {"material": {"status": "Approved"}}
        async def profile(*args):
            return {"interview_scheduling": {"method": "link"}}
        readiness = load_function("workspace_routes.py", "opportunity_readiness", "create_workspace_router", {
            "db": db, "CAMPAIGN_TYPES": campaign, "ONBOARDING_PREP_TYPES": onboarding,
            "SUPPORT_PREP_TYPES": support, "get_current_material": material, "get_profile": profile,
        })
        complete = await readiness("owner", {"application_saved": True})
        self.assertTrue(all(complete[key] for key in ("profiles_approved", "scheduling_saved", "application_saved",
                                                      "materials_approved", "onboarding_approved", "support_approved")))
        rows[-1]["status"] = "Generated"
        incomplete = await readiness("owner", {"application_saved": True})
        self.assertFalse(incomplete["support_approved"])
        self.assertEqual(incomplete["support_approved_count"], 1)

    async def test_no_portfolio_role_recommendation_before_profile_response(self):
        application = {"application_id": "candidate", "owner_user_id": "owner", "applicant_email": "candidate@example.org"}
        db = types.SimpleNamespace(board_profile_responses=Collection([]))
        async def owned(*args):
            return application
        recommend = load_function("workspace_routes.py", "prepare_board_role_recommendation", "create_workspace_router", {
            "db": db, "owned_application": owned, "HTTPException": HttpError,
        })
        with self.assertRaises(HttpError) as raised:
            await recommend("owner", "candidate")
        self.assertEqual(raised.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
