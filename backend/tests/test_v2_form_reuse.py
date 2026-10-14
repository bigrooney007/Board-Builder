"""Prove V2 shares the established planning methodology and recommitment rules.

The baseline is the exact user-approved undeployed revision. No server, customer
data, credentials, providers or live database are needed for these checks.
"""
import ast
import random
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from v2_form_content import build_strategic_form, validate_recommitment, RECOMMITMENT_OPTIONS
from v2_forms import complete_intake, validate_intake, validate_fundraising, group_context, build_final_preview
from tests.v2_fixture import Database

BASE = 'd627263044f606a819366d3b04fe7e240b8e254d'


def baseline(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True)


def original_strategic_builder():
    tree = ast.parse(baseline('backend/strategic_planning_routes.py'))
    prepare = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == 'prepare_form')
    begin = next(i for i, n in enumerate(prepare.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'programs' for t in n.targets))
    end = next(i for i, n in enumerate(prepare.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'now' for t in n.targets))
    function = ast.FunctionDef(name='original', args=ast.arguments(posonlyargs=[], args=[ast.arg(arg='a'), ast.arg(arg='p')], kwonlyargs=[], kw_defaults=[], defaults=[]), body=prepare.body[begin:end] + [ast.Return(ast.Name(id='content', ctx=ast.Load()))], decorator_list=[])
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), '<baseline-strategic>', 'exec'), namespace)
    return namespace['original']


def original_recommitment_validator():
    tree = ast.parse(baseline('backend/reactivation_routes.py'))
    submit = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == 'submit_recommitment')
    begin = next(i for i, n in enumerate(submit.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'allowed_choices' for t in n.targets))
    end = next(i for i, n in enumerate(submit.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'now' for t in n.targets))
    function = ast.FunctionDef(name='original', args=ast.arguments(posonlyargs=[], args=[ast.arg(arg='payload'), ast.arg(arg='variant')], kwonlyargs=[], kw_defaults=[], defaults=[]), body=submit.body[begin:end], decorator_list=[])
    namespace = {'HTTPException': HTTPException, 'RECOMMIT_ACTIVE': RECOMMITMENT_OPTIONS[0], 'RECOMMIT_ADVISORY': RECOMMITMENT_OPTIONS[1], 'RECOMMIT_STEP_DOWN': RECOMMITMENT_OPTIONS[2], 'RECOMMITMENT_OPTIONS': RECOMMITMENT_OPTIONS}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), '<baseline-recommitment>', 'exec'), namespace)
    return namespace['original']


class SharedBoardMethodologyTests(unittest.TestCase):
    def test_strategic_participant_questions_and_categories_match_baseline_exactly(self):
        original = original_strategic_builder()
        project = {'organization_name': 'Example Education Charity', 'mission': 'Our existing mission.'}
        configurations = [
            {},
            {'mission': 'Expand access to education.', 'goals': 'Support families.', 'programs': 'Mentoring\nParent workshops'},
            {'program_details': [{'name': 'Community Mentoring', 'description': 'Monthly sessions.', 'present_work': 'Volunteer training.'}], 'team_building': 'Board and staff.', 'budget': 'The approved budget is $10,000.'},
            {'program_details': [{}, {'name': ' Arts ', 'description': ' Art clinics. ', 'present_work': ' Workshops. '}]},
        ]
        for answers in configurations:
            with self.subTest(answers=answers):
                self.assertEqual(build_strategic_form(answers, project), original(answers, project))

    def test_all_existing_recommitment_conditional_validation_messages_are_preserved(self):
        original = original_recommitment_validator()
        rng = random.Random(20261014)
        fields = ['recommitment', 'why_joined', 'participation_barriers', 'ownership_area', 'strengths_resources', 'monthly_availability', 'experience_improvement', 'leadership_interest', 'leadership_area', 'decision_reason']
        def outcome(function, payload, variant):
            try:
                function(payload, variant)
                return None
            except HTTPException as exc:
                return exc.status_code, exc.detail
        for number in range(150):
            data = {key: rng.choice(['', 'Example answer.']) for key in fields}
            data.update(recommitment=rng.choice(RECOMMITMENT_OPTIONS + ['Unknown']), expertise=rng.choice([[], ['Finance']]), contribution_interests=rng.choice([[], ['Finance'], ['Finance'] * 4]), leadership_interest=rng.choice(['', 'Yes', 'I would like to discuss this']))
            payload = SimpleNamespace(**data)
            for variant in ('full', 'active_advisory'):
                with self.subTest(case=number, variant=variant):
                    self.assertEqual(outcome(validate_recommitment, payload, variant), outcome(original, payload, variant))

    def test_fundraising_all_categories_can_be_skipped_without_invented_audiences(self):
        answers = validate_fundraising({'audiences': [], 'participation': 'I would like to help, but I am unsure how yet.'})
        self.assertEqual(answers['audiences'], [])
        self.assertEqual(answers['participation'], 'I would like to help, but I am unsure how yet.')

    def test_fundraising_audience_answers_allow_explicit_uncertainty(self):
        audience = {'audience_id': 'one', 'category': 'grantmakers', **{key: 'I am unsure.' for key in ('funder', 'why', 'where', 'attract', 'relationship', 'ask', 'amount')}}
        self.assertEqual(validate_fundraising({'audiences': [audience], 'participation': 'I can discuss this.'})['audiences'], [audience])

    def test_fundraising_incomplete_audiences_and_duplicate_ids_are_rejected(self):
        with self.assertRaises(HTTPException):
            validate_fundraising({'audiences': [{'category': 'individuals', 'funder': 'Parents.'}], 'participation': 'I can help.'})
        audience = {'audience_id': 'duplicate', 'category': 'businesses', **{key: 'An answer.' for key in ('funder', 'why', 'where', 'attract', 'relationship', 'ask', 'amount')}}
        with self.assertRaises(HTTPException):
            validate_fundraising({'audiences': [audience, audience], 'participation': 'I can help.'})

    def test_intake_retains_original_free_field_keys_and_partial_draft_behavior(self):
        cleaned = validate_intake('board-recommitment', {'mission': '  Improve education.  ', 'need_by': '2026-11-01'})
        self.assertEqual(cleaned['mission'], 'Improve education.')
        self.assertFalse(complete_intake('board-recommitment', cleaned))
        with self.assertRaises(HTTPException):
            validate_intake('board-recommitment', {'need_by': '2026-02-30'})


class GroupDecisionIntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = Database()
        self.journey = {'journey_id': 'org-one', 'product': 'board-fundraising-game', 'organization': 'Synthetic Charity', 'email': 'leader@example.test', 'form_token': 'private-form', 'group_token': 'private-group', 'branding': {}, 'state': 'paid', 'decision_version': 1}
        self.audience = {'audience_id': 'audience-one', 'category': 'businesses', 'funder': 'Local software companies', 'why': 'They value technology education.', 'where': 'Technology industry events.', 'attract': 'Demonstrate participant outcomes.', 'relationship': 'Discuss a pilot sponsorship.', 'ask': 'Fund training materials.', 'amount': 'We are unsure and will discuss the amount.'}
        await self.db.v2_submissions.insert_one({'submission_id': 'submission-one', 'journey_id': 'org-one', 'participant_id': 'person-one', 'name': 'Synthetic Participant', 'email': 'private@example.test', 'answers': {'audiences': [self.audience], 'participation': 'I can introduce local businesses.'}, 'submitted_at': '2026-10-14', 'cv': {'text': 'PRIVATE CV', 'content_base64': 'PRIVATE FILE'}})
        await self.db.v2_decisions.insert_one({'decision_id': 'approved-one', 'journey_id': 'org-one', 'category': 'businesses', 'title': 'Technology business sponsorship', 'content': self.audience, 'source_ids': ['submission-one:audience-one'], 'status': 'adopted'})
        await self.db.v2_decisions.insert_one({'decision_id': 'rejected-one', 'journey_id': 'org-one', 'category': 'individuals', 'title': 'UNAPPROVED AUDIENCE', 'content': {**self.audience, 'funder': 'UNAPPROVED AUDIENCE'}, 'source_ids': [], 'status': 'rejected'})

    async def test_shared_group_contains_sources_and_decisions_without_contacts_or_tokens(self):
        shared = await group_context(self.db, self.journey, shared=True)
        rendered = str(shared)
        self.assertTrue(shared['read_only'])
        self.assertNotIn('private@example.test', rendered)
        self.assertNotIn('leader@example.test', rendered)
        self.assertNotIn('PRIVATE CV', rendered)
        self.assertNotIn('private-form', rendered)
        self.assertNotIn('private-group', rendered)
        self.assertEqual(shared['sections'][1]['ideas'][0]['content'], self.audience)

    async def test_final_preview_excludes_rejected_ideas_and_unconfirmed_roles(self):
        await self.db.v2_commitments.insert_one({'commitment_id': 'unconfirmed', 'journey_id': 'org-one', 'name': 'Synthetic Participant', 'responsibility': 'UNCONFIRMED RESPONSIBILITY', 'consent_confirmed': False, 'audience_ids': []})
        before = self.db.snapshot()['v2_submissions']
        preview = await build_final_preview(self.db, self.journey)
        self.assertIn('Local software companies', preview['text'])
        self.assertIn('We are unsure and will discuss the amount.', preview['text'])
        self.assertNotIn('UNAPPROVED AUDIENCE', preview['text'])
        self.assertNotIn('UNCONFIRMED RESPONSIBILITY', preview['text'])
        self.assertNotIn('private@example.test', preview['text'])
        self.assertEqual(self.db.snapshot()['v2_submissions'], before)

    async def test_confirmed_participation_is_included_only_with_agreed_audience(self):
        await self.db.v2_commitments.insert_one({'commitment_id': 'confirmed', 'journey_id': 'org-one', 'name': 'Synthetic Participant', 'responsibility': 'Introduce two local business contacts.', 'consent_confirmed': True, 'audience_ids': ['approved-one']})
        preview = await build_final_preview(self.db, self.journey)
        self.assertIn('Introduce two local business contacts.', preview['text'])
        self.assertIn('Technology business sponsorship', preview['text'])

    async def test_rejected_audience_requires_review_of_its_previous_participation_commitment(self):
        await self.db.v2_commitments.insert_one({'commitment_id': 'stale', 'journey_id': 'org-one', 'name': 'Synthetic Participant', 'responsibility': 'Support the rejected audience.', 'consent_confirmed': True, 'audience_ids': ['rejected-one']})
        with self.assertRaises(HTTPException) as outcome:
            await build_final_preview(self.db, self.journey)
        self.assertEqual(outcome.exception.status_code, 409)


if __name__ == '__main__':
    unittest.main()
