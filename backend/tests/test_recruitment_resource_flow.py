"""Offline regression checks. No database, paid generation or email delivery is used.

Run: python -m unittest discover -s backend/tests -p test_recruitment_resource_flow.py
The route closures are loaded from their actual source with service boundaries injected,
so these checks do not import the application's live infrastructure during discovery.
"""
import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import File, Form, HTTPException
from pydantic import EmailStr, TypeAdapter, ValidationError

BACKEND = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


chat = types.ModuleType("emergentintegrations.llm.chat")
chat.LlmChat = chat.UserMessage = None
with patch.dict(sys.modules, {"emergentintegrations.llm.chat": chat}):
    ai = load_module("recruitment_test_ai", BACKEND / "ai_service.py")
with patch.dict(sys.modules, {"ai_service": ai}):
    service = load_module("recruitment_test_service", BACKEND / "workspace_service.py")


def route_functions(filename, factory, names, namespace):
    tree = ast.parse((BACKEND / filename).read_text())
    parent = next(node for node in tree.body if getattr(node, "name", None) == factory) if factory else tree
    selected = []
    for node in parent.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list = []
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(getattr(target, "id", None) in names for target in node.targets):
            selected.append(node)
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *selected], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(BACKEND / filename), "exec"), namespace)
    return namespace


def matches(record, query):
    for key, expected in query.items():
        actual = record.get(key)
        if isinstance(expected, dict):
            if "$ne" in expected and actual == expected["$ne"]:
                return False
            if "$in" in expected and actual not in expected["$in"]:
                return False
        elif actual != expected:
            return False
    return True


class Collection:
    def __init__(self, records=()):
        self.records = copy.deepcopy(list(records))

    async def find_one(self, query, *args, **kwargs):
        return copy.deepcopy(next((row for row in self.records if matches(row, query)), None))

    async def insert_one(self, record):
        self.records.append(copy.deepcopy(record))

    async def update_one(self, query, update, upsert=False):
        record = next((row for row in self.records if matches(row, query)), None)
        if record is None and upsert:
            record = copy.deepcopy(query)
            self.records.append(record)
            record.update(update.get("$setOnInsert", {}))
        if record is not None:
            record.update(copy.deepcopy(update.get("$set", {})))
            for key, value in update.get("$push", {}).items():
                record.setdefault(key, []).append(copy.deepcopy(value))


def material(kind, status="Approved", structured=None, text="Approved organization document"):
    return {"user_id": "owner", "type": kind, "application_id": "", "material_id": "doc-" + kind,
            "status": status, "current_version": 1,
            "versions": [{"version": 1, "structured": structured or {}, "display_text": text}]}


class RecruitmentResourceFlow(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = {"date": "2026-10-15", "time": "14:30", "timezone": "Europe/London", "format": "Virtual", "link": "https://example.org/our-meeting"}
        self.member = {"user_id": "owner", "first_name": "Sam", "last_name": "Founder", "email": "sam@example.org", "lead_ids": ["lead"]}
        self.application = {"application_id": "candidate", "owner_user_id": "owner", "applicant_email": "alex@example.org", "profile_snapshot": {"full_name": "Alex Candidate", "location": "London, UK"}, "answers": {"why_interested": "I can help develop partnerships"}, "cv_text": "Partnerships director", "background_check": {"status": "Not started"}}
        self.docs = [material(kind) for kind in ("organization_overview", "board_manual", "board_member_agreement", "confidentiality_agreement", "conflict_of_interest_agreement")]
        self.profile = {"user_id": "owner", "confirmed": True, "data": {"organization_name": "Community Works", "mission": "Build community opportunities"}, "onboarding_session": self.session}
        self.db = types.SimpleNamespace(
            recruitment_profiles=Collection([self.profile]), funnel_leads=Collection(),
            generated_materials=Collection(self.docs), opportunities=Collection([{"user_id": "owner", "slug": "community-works", "organization_name": "Community Works"}]),
            opportunity_applications=Collection([self.application]), reference_processes=Collection(),
            signature_requests=Collection(), share_links=Collection(), board_profile_links=Collection())
        self.ai_generate = AsyncMock(return_value={"subject": "Congratulations, Alex", "body": "Dear Alex,\n\nWelcome to the Board. Please review your onboarding packet below.\n\nSam"})
        self.ns = {
            "db": self.db, "os": os, "secrets": secrets, "HTTPException": HTTPException,
            "GENERATION_TYPES": ai.GENERATION_TYPES,
            "current_member": AsyncMock(return_value=self.member), "require_entitlement": lambda *args: None,
            "owned_application": AsyncMock(return_value=self.application),
            "get_profile": service.get_profile, "get_lead": service.get_lead,
            "get_current_material": service.get_current_material, "build_org_context": service.build_org_context,
            "application_context_text": service.application_context_text,
            "appointment_onboarding_packet": service.appointment_onboarding_packet,
            "campaign_material_with_link": service.campaign_material_with_link,
            "reference_context": AsyncMock(return_value=""), "ensure_opportunity": AsyncMock(return_value={"slug": "community-works"}),
            "generate_structured": self.ai_generate, "save_generation": service.save_generation,
            "new_id": service.new_id, "now_iso": service.now_iso,
        }
        route_functions("workspace_routes.py", "create_workspace_router", {"generate", "ensure_share_token", "replace_link", "origin_of", "MODULE3_LINK_TYPES", "CAMPAIGN_TYPES", "GOVERNANCE_BYLAWS_TYPES", "RETIRED_REFERENCE_MATERIAL_TYPES"}, self.ns)
        self.request = types.SimpleNamespace(headers={"origin": "https://example.org"})

    async def generate(self, kind):
        payload = types.SimpleNamespace(type=kind, application_id="candidate", instructions="", referee_id="")
        with patch.dict(os.environ, {"PUBLIC_ORIGIN": "https://example.org"}):
            return await self.ns["generate"](payload, self.request)

    async def test_both_offers_include_same_complete_onboarding_packet(self):
        bodies = []
        for kind in ("conditional_offer", "unconditional_offer"):
            with self.subTest(kind=kind):
                result = await self.generate(kind)
                body = result["versions"][-1]["structured"]["body"]
                bodies.append(body)
                for value in self.session.values():
                    self.assertIn(value, body)
                for title in ("Organization Overview", "Board Manual", "Board Member Agreement", "Confidentiality", "Conflict", "Board Member Profile"):
                    self.assertIn(title.lower(), body.lower())
                self.assertEqual(body.count("https://example.org/shared/"), 2)
                self.assertEqual(body.count("https://example.org/sign/"), 3)
                self.assertEqual(body.count("https://example.org/board-profile/"), 1)
                self.assertEqual(result["status"], "Generated")
        self.assertEqual(bodies[0].split("YOUR ONBOARDING SESSION")[1], bodies[1].split("YOUR ONBOARDING SESSION")[1])
        self.assertEqual(len(self.db.signature_requests.records), 3)
        self.assertEqual(len(self.db.share_links.records), 2)
        self.assertEqual(len(self.db.board_profile_links.records), 1)
        self.assertEqual(self.db.board_profile_links.records[0]["prefill"]["location"], "London, UK")
        self.assertIn("CONDITIONAL APPOINTMENT STATUS", self.ai_generate.call_args_list[0].args[1])
        self.assertNotIn("CONDITIONAL APPOINTMENT STATUS", self.ai_generate.call_args_list[1].args[1])
        self.assertEqual(self.db.reference_processes.records, [])
        self.assertNotIn("emails_sent", self.db.opportunity_applications.records[0])

    async def test_offers_block_missing_documents_and_meeting_details_before_ai(self):
        cases = [("board_manual", None), (None, "date"), (None, "timezone"), (None, "format"), (None, "link")]
        for kind in ("conditional_offer", "unconditional_offer"):
            for missing_doc, missing_detail in cases:
                with self.subTest(kind=kind, missing_doc=missing_doc, missing_detail=missing_detail):
                    self.db.generated_materials.records = copy.deepcopy(self.docs)
                    self.db.recruitment_profiles.records = [copy.deepcopy(self.profile)]
                    if missing_doc:
                        self.db.generated_materials.records = [d for d in self.docs if d["type"] != missing_doc]
                    if missing_detail:
                        self.db.recruitment_profiles.records[0]["onboarding_session"].pop(missing_detail)
                    with self.assertRaises(HTTPException) as caught:
                        await self.generate(kind)
                    self.assertEqual(caught.exception.status_code, 409)
        self.ai_generate.assert_not_awaited()
        self.assertEqual(self.db.signature_requests.records, [])

    async def test_in_person_offer_requires_location_not_video_link(self):
        session = self.db.recruitment_profiles.records[0]["onboarding_session"]
        session.update({"format": "In Person", "link": ""})
        with self.assertRaises(HTTPException):
            await self.generate("unconditional_offer")
        session["location"] = "Community Hall, London"
        result = await self.generate("unconditional_offer")
        self.assertIn(session["location"], result["versions"][-1]["structured"]["body"])

    async def test_empty_offer_is_not_saved_as_a_finished_email(self):
        self.ai_generate.return_value = {"subject": "Welcome", "body": ""}
        with self.assertRaises(HTTPException) as caught:
            await self.generate("conditional_offer")
        self.assertEqual(caught.exception.status_code, 503)
        self.assertFalse(any(d["type"] == "conditional_offer" for d in self.db.generated_materials.records))

    async def test_reference_buttons_generate_reply_emails_without_form_side_effects(self):
        for kind in ("candidate_referee_request", "reference_request_email"):
            await self.generate(kind)
            context = self.ai_generate.call_args.args[1]
            self.assertIn("REFERENCE METHOD:", context)
            self.assertIn("reply", context.lower())
            self.assertNotIn("/reference-form/", context)
        self.assertEqual(self.db.reference_processes.records, [])
        self.assertNotIn("emails_sent", self.db.opportunity_applications.records[0])

    async def test_context_uses_original_answers_and_approved_founder_edited_profiles(self):
        answers = {"mission": "Mission detail", "current_board": "Current strengths", "support_needs": "Future support", "desired_board_members": "Desired expertise", "board_type": "Advisory Board", "why_join": "Our compelling invitation", "new_members_needed": "3"}
        self.db.funnel_leads.records = [{"lead_id": "lead", "offer_source": "recruitment", "organization": "Community Works", "answers": answers}]
        approved = [{"role_name": "Founder-edited partnerships profile", "how_this_person_can_support": "Leadership of partnership direction"}]
        self.db.generated_materials.records += [material("powerhouse_board_blueprint", structured={"priority_roles": approved, "board_snapshot": "Outdated suggestion"}), material("recruitment_strategy", "Generated", text="Unapproved strategy"), material("board_opportunity", "Edited", text="Unapproved opportunity")]
        context = await service.build_org_context(self.db, "owner", self.member)
        for answer in answers.values():
            self.assertIn(answer, context)
        self.assertIn(approved[0]["role_name"], context)
        for excluded in ("Outdated suggestion", "Unapproved strategy", "Unapproved opportunity"):
            self.assertNotIn(excluded, context)


class CampaignAndApplication(unittest.IsolatedAsyncioTestCase):
    def test_every_campaign_item_carries_the_exact_application_url(self):
        url = "https://example.org/board-opportunities/community/apply"
        for kind, field in (("board_recruitment_job_post", "post_body"), ("recruitment_emails", "body"), ("referral_request_email", "message")):
            result = service.campaign_material_with_link(kind, {field: "Join our Board"}, url)
            self.assertIn(url, result[field])
        result = service.campaign_material_with_link("social_posts", {"posts": [{"post_text": "Apply: [APPLICATION LINK]"}, {"post_text": "Help shape our next phase"}, {"post_text": "Our leadership invitation"}]}, url)
        self.assertTrue(all(url in post["post_text"] for post in result["posts"]))
        self.assertEqual(ai.structured_to_display("social_posts", result).count(url), 3)
        self.assertIn("Legacy social post", ai.structured_to_display("social_posts", {"post_text": "Legacy social post"}))
        with self.assertRaises(ValueError):
            service.campaign_material_with_link("social_posts", {"posts": [{"post_text": "Only one"}]}, url)

    def public_route(self):
        saved = AsyncMock(return_value={"application_id": "created"})
        ns = {"published_opportunity": AsyncMock(return_value={"custom_questions": []}), "create_application": saved,
              "store_cv": AsyncMock(), "json": json, "HTTPException": HTTPException, "Form": Form, "File": File,
              "CORE_QUESTIONS": service.CORE_QUESTIONS, "LEGACY_APPLICATION_FIELDS": service.LEGACY_APPLICATION_FIELDS,
              "EmailStr": EmailStr, "TypeAdapter": TypeAdapter, "ValidationError": ValidationError}
        route_functions("public_opportunity_routes.py", "create_public_opportunity_router", {"public_apply"}, ns)
        return ns, saved

    async def test_short_application_submits_without_cv(self):
        ns, saved = self.public_route()
        answers = {"full_name": "Alex Candidate", "email": "Alex@example.org", "location": "London, UK", "profession": "Partnerships director", "why_interested": "I can guide sustainable partnerships"}
        result = await ns["public_apply"]("community", None, json.dumps(answers), None)
        self.assertEqual(result["application_id"], "created")
        self.assertEqual(saved.call_args.args[2]["email"], "alex@example.org")
        self.assertEqual(saved.call_args.args[4], {})
        self.assertEqual(saved.call_args.args[3]["why_interested"], answers["why_interested"])
        ns["store_cv"].assert_not_awaited()

    async def test_old_open_form_keeps_legacy_answers(self):
        ns, saved = self.public_route()
        answers = {"full_name": "Alex", "email": "alex@example.org", "city": "London", "country": "UK", "profession": "Director", "why_interested": "Mission", "skills_experience": "Existing application detail"}
        await ns["public_apply"]("community", None, json.dumps(answers), None)
        self.assertEqual(saved.call_args.args[2]["location"], "London, UK")
        self.assertEqual(saved.call_args.args[3]["skills_experience"], "Existing application detail")

    async def test_invalid_or_incomplete_applications_do_not_create_records(self):
        ns, saved = self.public_route()
        base = {"full_name": "Alex", "email": "alex@example.org", "location": "London", "profession": "Director", "why_interested": "Mission"}
        for answers in (["not a form"], {}, {**base, "email": "not an email"}, {**base, "why_interested": "  "}, {**base, "profession": None}):
            with self.assertRaises(HTTPException) as caught:
                await ns["public_apply"]("community", None, json.dumps(answers), None)
            self.assertEqual(caught.exception.status_code, 422)
        saved.assert_not_awaited()


class RecruitmentNarrationRevision(unittest.TestCase):
    def test_replaced_script_requires_new_recording_and_preserves_custom_text(self):
        voice = load_module("recruitment_test_voice", BACKEND / "voice_script_state.py")
        old = "The old automated reference process."
        stored = {"text": old, "script_version": 2, "source_revision": voice.SOURCE_REVISION}
        updated = voice.resolve_script("Reply directly by email.", stored, superseded_hashes=(voice.script_hash(old),))
        self.assertEqual(updated["text"], "Reply directly by email.")
        self.assertEqual(updated["script_version"], 3)
        self.assertEqual(voice.recording_status({"status": "ready", "script_version": 2}, updated), "needs_regeneration")
        custom = voice.resolve_script("Reply directly by email.", {**stored, "text": "Professor's own revised wording."}, superseded_hashes=(voice.script_hash(old),))
        self.assertEqual(custom["text"], "Professor's own revised wording.")
        self.assertEqual(custom["script_version"], 2)


if __name__ == "__main__":
    unittest.main()
