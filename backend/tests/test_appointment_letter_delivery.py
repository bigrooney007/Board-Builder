"""Offline check of the actual conditional and unconditional letter/email content."""
import ast
import asyncio
import io
from datetime import datetime, timezone
from pathlib import Path
import unittest

from pypdf import PdfReader

BACKEND = Path(__file__).resolve().parents[1]


class Collection:
    def __init__(self, record=None):
        self.record = record

    async def find_one(self, *args, **kwargs):
        return self.record


class Db:
    opportunities = Collection({"organization_name": "BrightPath Youth Alliance"})
    generated_materials = Collection()


def load_email_builders():
    tree = ast.parse((BACKEND / "workspace_routes.py").read_text())
    factory = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "create_workspace_router")
    selected = [node for node in factory.body if isinstance(node, ast.AsyncFunctionDef)
                and node.name in {"board_appointment_letter", "recruitment_portfolio_email_content"}]
    for node in selected:
        node.decorator_list = []
    namespace = {"db": Db(), "datetime": datetime, "timezone": timezone,
                 "get_profile": lambda database, user_id: profile()}
    import sys
    sys.path.insert(0, str(BACKEND))
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])), "workspace_routes.py", "exec"), namespace)
    return namespace


async def profile():
    return {"data": {"organization_name": "BrightPath Youth Alliance"},
            "branding": {"primary_color": "#3730a3"},
            "onboarding_session": {"date": "2026-10-15", "time": "14:30", "timezone": "Europe/London", "link": "https://example.org/board"}}


class AppointmentLetterDelivery(unittest.TestCase):
    def test_letter_status_matches_real_appointment_and_portfolio_email(self):
        funcs = load_email_builders()
        member = {"user_id": "owner", "first_name": "Sam", "last_name": "Founder"}
        material = {"share_token": "private-portfolio-token"}
        for status, conditional in (("Conditional", True), ("Unconditional", False)):
            application = {"application_id": "candidate", "appointment_offer_type": status,
                           "applicant_email": "alex@example.org", "profile_snapshot": {"full_name": "Alex Candidate"}}
            letter = asyncio.run(funcs["board_appointment_letter"](member, application))
            text = " ".join(" ".join(page.extract_text().split()) for page in PdfReader(io.BytesIO(letter["pdf"])).pages)
            self.assertIn("BrightPath Youth Alliance", text)
            self.assertIn("Alex Candidate", text)
            self.assertEqual("pending" in text.lower(), conditional)
            if not conditional:
                self.assertNotIn("reference", text.lower())
                self.assertNotIn("background check", text.lower())
            email = asyncio.run(funcs["recruitment_portfolio_email_content"](
                member, application, material, "https://example.org"))
            self.assertIn("Appointment Letter", email["subject"])
            self.assertEqual(email["letter_status"], "conditional" if conditional else "unconditional")
            self.assertIn("attached to this email", email["body"])
            self.assertEqual("https://example.org/portfolio/private-portfolio-token", email["portfolio_link"])


if __name__ == "__main__":
    unittest.main()
