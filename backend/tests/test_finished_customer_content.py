"""Finished resource/email presentation, without production credentials or data."""
import ast
import importlib.util
import io
import re
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from finished_content import clean_resource_text, resource_lines


class FinishedCustomerContent(unittest.TestCase):
    def test_structural_labels_removed_without_changing_meaning(self):
        raw = "Title: Our Board\nHeadline: Join our mission\nBody: Content: Welcome to our work.\n\nTitle to Property\nOur governing body meets monthly.\nSubject: Your invitation"
        result = clean_resource_text(raw)
        self.assertEqual(result, "Our Board\nJoin our mission\nWelcome to our work.\n\nTitle to Property\nOur governing body meets monthly.\nSubject: Your invitation")

    def test_nested_resources_keep_actual_headings_and_topic_information(self):
        value = {"title": "Our Board Manual", "sections": [{"headline": "Our responsibilities", "body": "We guide the mission.",
                  "meeting_frequency": "Monthly", "paragraphs": ["We prepare in advance."],
                  "post_text": "Share the opportunity.", "email_body": "Thank you for your interest."}]}
        text = "\n".join(resource_lines(value))
        self.assertNotRegex(text, r"(?im)^\s*(title|headline|heading|body|content|sections|paragraphs)\s*:")
        for phrase in ("Our Board Manual", "Our responsibilities", "We guide the mission.", "Meeting Frequency: Monthly", "We prepare in advance."):
            self.assertIn(phrase, text)
        self.assertNotIn("Post Text:", text)
        self.assertNotIn("Email Body:", text)

    def test_all_four_product_resource_formats_use_finished_text(self):
        # Load the real formatter, substituting only an unusable AI transport.
        chat = types.ModuleType("emergentintegrations.llm.chat")
        chat.LlmChat = lambda *a, **k: self.fail("No AI provider should be used by a renderer")
        chat.UserMessage = object
        modules = {"emergentintegrations": types.ModuleType("emergentintegrations"),
                   "emergentintegrations.llm": types.ModuleType("emergentintegrations.llm"), chat.__name__: chat}
        spec = importlib.util.spec_from_file_location("finished_resource_service", ROOT / "backend/ai_service.py")
        service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(service)
        resources = {
            "organization_overview": {"title": "BrightPath Youth Alliance", "sections": [{"heading": "Our purpose", "content": "We support young people."}]},
            "activation_followup_email": {"subject": "Our agreed next step", "body": "Thank you for your contribution."},
            "strategic_session_final_plan": {"title": "Our Strategic Plan", "sections": [{"headline": "Our priorities", "body": "Deliver the approved mentoring programme."}]},
            "board_member_agreement": {"title": "Board Member Agreement", "sections": [{"heading": "Our commitment", "body": "We will prepare for meetings."}]},
        }
        for kind, value in resources.items():
            with self.subTest(kind=kind):
                result = service.structured_to_display(kind, value)
                self.assertNotRegex(result, r"(?im)^\s*(title|headline|heading|body|content|sections)\s*:")
                self.assertTrue(any(word in result for word in ("young people", "contribution", "mentoring", "prepare")))

    def test_pdf_contains_finished_copy_without_drafting_labels(self):
        from document_renderer import render_document_pdf
        from pypdf import PdfReader
        pdf = render_document_pdf(title="Board Recruitment Pack", org_name="BrightPath Youth Alliance",
            body_text="Headline: Join our board\nBody: Help young people thrive.\nTitle: Your contribution\nContent: Share your experience.")
        text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
        self.assertNotRegex(text, r"(?im)^\s*(title|headline|body|content)\s*:")
        self.assertIn("Join our board", text)
        self.assertIn("Help young people thrive.", text)
        self.assertIn("Share your experience.", text)

    def test_customer_launch_email_has_no_environment_labels(self):
        import asyncio
        import os
        from unittest.mock import AsyncMock
        from opportunity_emails import send_campaign_launch_email
        class Rows:
            async def to_list(self, limit): return []
        database = types.SimpleNamespace(generated_materials=types.SimpleNamespace(find=lambda *a, **k: Rows()),
            opportunities=types.SimpleNamespace(update_one=AsyncMock()))
        send = AsyncMock(return_value="provider-confirmation")
        opportunity = {"opportunity_id": "one", "slug": "our-board", "user_id": "real-customer", "organization_name": "BrightPath", "broadcast_status": "Sent", "broadcast_mode": "live"}
        with patch("dashboard_return.send_dashboard_return", new=AsyncMock()), patch("opportunity_emails._send", send), patch.dict(os.environ, {"POSTAL_ADDRESS": "Our office"}):
            asyncio.run(send_campaign_launch_email(database, opportunity, {"email": "customer@example.org"}, "https://nonprofitboardbuilder.com"))
        args = send.await_args.args
        self.assertNotRegex(args[2] + args[3], r"(?i)\b(test|live)\b")
        self.assertIn("Has Launched", args[2])
        self.assertIn("/board-opportunities/our-board/apply", args[3])
        self.assertIn("/app/board-recruitment", args[3])

    def test_new_customer_checkouts_are_not_gated_by_preview_flags(self):
        tree = ast.parse((ROOT / "backend/payment_routes.py").read_text())
        handlers = [node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
                    and node.name in {"create_guided_checkout", "create_game_checkout", "create_supported_checkout"}]
        self.assertTrue(handlers)
        for node in handlers:
            text = ast.get_source_segment((ROOT / "backend/payment_routes.py").read_text(), node)
            self.assertNotIn("NBB_V2_ENABLED", text)
            self.assertNotIn("Program access is not open yet", text)


if __name__ == "__main__":
    unittest.main()
