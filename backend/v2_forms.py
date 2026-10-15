"""Isolated V2 participant forms and explicit board decisions.

Existing source submissions stay immutable. Public tokens authorize one form, never
an organization's response collection. Shared links use independent browser drafts.
"""
import base64
import hashlib
import json
import re
import secrets
from v2_admin_test import form_token
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Request, Response

from v2_form_content import (
    AUDIENCE_FIELDS, FUNDRAISING_CATEGORIES, INTAKE_FIELDS,
    RECOMMIT_ACTIVE, RECOMMIT_ADVISORY, RECOMMIT_STEP_DOWN, RECOMMITMENT_OPTIONS,
    build_strategic_form, fundraising_form, recommitment_questions, validate_recommitment,
)

MAX_FORM_BYTES = 250_000
MAX_CV_BYTES = 10 * 1024 * 1024
GROUP_PRODUCTS = {'board-fundraising-game', 'strategic-planning'}


def core():
    import v2_core
    return v2_core


def clean_email(value):
    return core().validate_email(value)


def clean_text(value, limit=12000):
    if not isinstance(value, str):
        raise HTTPException(422, 'Answers must be text.')
    if len(value) > limit:
        raise HTTPException(422, f'An answer is longer than {limit} characters.')
    return value.strip()


def bounded_answers(value):
    if not isinstance(value, dict):
        raise HTTPException(422, 'Please provide your answers.')
    try:
        encoded = json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, 'Answers must contain valid JSON values.') from exc
    if len(encoded.encode()) > MAX_FORM_BYTES:
        raise HTTPException(413, 'This response is too large. Please shorten your answers.')
    return value


def validate_intake(product, answers):
    """Same established introductory fields; partial answers may be saved."""
    bounded_answers(answers)
    if product not in INTAKE_FIELDS:
        raise HTTPException(422, 'Choose a supported board service.')
    cleaned = {}
    for key in INTAKE_FIELDS[product]:
        if key not in answers:
            continue
        value = answers[key]
        if key == 'program_details':
            if not isinstance(value, list) or len(value) > 20:
                raise HTTPException(422, 'Add your programs separately, with no more than 20 programs.')
            cleaned[key] = [{field: clean_text(item.get(field, ''), 3000) for field in ('name', 'description', 'present_work')}
                            for item in value if isinstance(item, dict)]
        else:
            cleaned[key] = clean_text(value)
    if product == 'board-recommitment' and cleaned.get('need_by'):
        try:
            datetime.strptime(cleaned['need_by'], '%Y-%m-%d')
        except ValueError as exc:
            raise HTTPException(422, 'Choose a valid date for when you need the Board to recommit') from exc
    return cleaned


def complete_intake(product, answers):
    if product not in INTAKE_FIELDS:
        return False
    for key in INTAKE_FIELDS[product]:
        value = answers.get(key)
        if key == 'program_details':
            if not isinstance(value, list) or not value or any(not isinstance(p, dict) or not str(p.get('name', '')).strip() for p in value):
                return False
        elif not isinstance(value, str) or not value.strip():
            return False
    return True


async def initialize_forms(db, journey):
    c = core()
    jid = journey['journey_id']
    updates = {}
    if not journey.get('form_token'):
        updates['form_token'] = form_token(db, journey['product'])
    if not journey.get('group_token'):
        updates['group_token'] = form_token(db, journey['product'])
    if updates:
        await db.v2_journeys.update_one({'journey_id': jid}, {'$set': updates})
        journey.update(updates)
    if journey['product'] in GROUP_PRODUCTS:
        leader = await db.v2_invitations.find_one({'journey_id': jid, 'role': 'Leader'}, {'_id': 0})
        if not leader:
            leader = {'invitation_id': c.new_id(), 'journey_id': jid, 'name': journey['name'], 'email': journey['email'],
                      'role': 'Leader', 'form_token': form_token(db, journey['product']), 'status': 'prepared',
                      'delivery_status': 'not_sent', 'created_at': c.now_iso()}
            await db.v2_invitations.update_one({'journey_id': jid, 'role': 'Leader'}, {'$setOnInsert': leader}, upsert=True)
            leader = await db.v2_invitations.find_one({'journey_id': jid, 'role': 'Leader'}, {'_id': 0})
        journey['leader_form_token'] = leader['form_token']
        await db.v2_journeys.update_one({'journey_id': jid}, {'$set': {'leader_form_token': leader['form_token']}})
    return journey


async def form_context(db, journey, invitation=None):
    product = journey['product']
    brand = journey.get('branding') or {}
    if product == 'recruit' and (journey.get('campaign_snapshot') or {}).get('resources'):
        brand = journey['campaign_snapshot'].get('branding') or brand
    organization = brand.get('organization_name') or journey.get('organization', '')
    result = {'journey_id': journey['journey_id'], 'product': product, 'organization': organization,
              'organization_name': organization, 'branding': brand,
              'logo_data_url': brand.get('logo_data', ''),
              'prefill': {'name': invitation.get('name', ''), 'full_name': invitation.get('name', ''), 'email': invitation.get('email', '')} if invitation else {},
              'submitted': bool(invitation and invitation.get('submission_id'))}
    if product == 'strategic-planning':
        result.update(build_strategic_form(journey.get('answers') or {}, {'organization_name': organization,
                      'mission': (journey.get('answers') or {}).get('mission', '')}))
        result['questions'] = [q for section in result['sections'] for q in section['questions']]
    elif product == 'board-fundraising-game':
        result.update(fundraising_form(journey))
        if invitation and invitation.get('role') == 'Leader':
            result['earlier_intake_answers'] = journey.get('answers') or {}
            result['earlier_intake_questions'] = {'1': 'The audience you identified and why they may give', '2': 'Where you could find that audience', '3': 'How you could attract their interest', '4': 'What you would ask them to support and how much', '5': 'How you would develop the relationship and raise money'}
    elif product == 'board-recommitment':
        from content_templates import recommitment_form_intro
        a = journey.get('answers') or {}
        introduction = recommitment_form_intro(organization, a.get('mission', '')).replace(' — ', ': ')
        for label, key in [('Why we are asking you to recommit', 'why_recommit'), ('What we need our Board to help accomplish', 'board_help_accomplish'), ('When we need this recommitment in place', 'need_by')]:
            if a.get(key):
                introduction += f'\n\n{label}: {a[key]}'
        result.update({'introduction': introduction, 'questions': recommitment_questions(organization, RECOMMIT_ACTIVE, RECOMMIT_ADVISORY, RECOMMIT_STEP_DOWN),
                       'sections': [], 'form_variant': 'full', 'recommitment_options': RECOMMITMENT_OPTIONS})
    else:
        from workspace_service import CORE_QUESTIONS
        application = await db.v2_resources.find_one({'journey_id': journey['journey_id'], 'key': 'application_questions'}, {'_id': 0}) or {}
        questions = [dict(q, prompt=q['label']) for q in CORE_QUESTIONS]
        launched_resources = (journey.get('campaign_snapshot') or {}).get('resources') or {}
        approved_application = launched_resources.get('application_questions') or next(iter(reversed(application.get('approved_versions') or [])), None)
        if approved_application and approved_application.get('branding'):
            result['branding'] = approved_application['branding']
            result['logo_data_url'] = result['branding'].get('logo_data', '')
            result['organization'] = result['organization_name'] = result['branding'].get('organization_name') or organization
        structured = (approved_application or {}).get('structured') or (application.get('structured') if application.get('status') == 'approved' else {}) or {}
        custom = structured.get('questions') or structured.get('custom_questions') or []
        if isinstance(custom, list):
            for i, q in enumerate(custom):
                if isinstance(q, str):
                    q = {'prompt': q}
                if isinstance(q, dict) and (q.get('prompt') or q.get('question') or q.get('label')):
                    questions.append({'id': str(q.get('id') or f'custom_{i+1}'), 'prompt': str(q.get('prompt') or q.get('question') or q.get('label')), 'label': str(q.get('prompt') or q.get('question') or q.get('label')),
                                      'type': q.get('type', 'textarea'), 'required': bool(q.get('required', False))})
        opportunity = await db.v2_resources.find_one({'journey_id': journey['journey_id'], 'key': 'board_opportunity'}, {'_id': 0}) or {}
        # Only approved public resource text is used as applicant-facing content.
        approved = launched_resources.get('board_opportunity') or next(iter(reversed(opportunity.get('approved_versions') or [])), None)
        result.update({'introduction': (approved or {}).get('text', '') if approved else f'Apply to serve on the board of {organization}.',
                       'questions': questions, 'core_questions': questions, 'sections': [], 'application_open': campaign_active(journey)})
    return result


def campaign_active(journey):
    campaign = journey.get('campaign') or {}
    return (journey.get('campaign_status') or campaign.get('status')) == 'active'


def validate_fundraising(answers, draft=False):
    rows = answers.get('audiences', [])
    if not isinstance(rows, list):
        raise HTTPException(422, 'Provide your funding audiences as a list.')
    cleaned = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or row.get('category') not in FUNDRAISING_CATEGORIES:
            raise HTTPException(422, 'Choose Individuals, Businesses or Grantmakers for each audience.')
        audience_id = clean_text(row.get('audience_id') or secrets.token_urlsafe(12), 100)
        if audience_id in seen:
            raise HTTPException(422, 'Each funding audience needs a separate identity.')
        seen.add(audience_id)
        data = {'audience_id': audience_id, 'category': row['category']}
        for field in AUDIENCE_FIELDS:
            data[field] = clean_text(row.get(field, ''))
            if not draft and not data[field]:
                raise HTTPException(422, 'Complete each audience before submitting. If you are unsure, say so in your answer.')
        cleaned.append(data)
    participation = clean_text(answers.get('participation', ''))
    if not draft and not participation:
        raise HTTPException(422, 'Tell us how you would personally be willing to participate. You can say if you are unsure.')
    return {'audiences': cleaned, 'participation': participation}


def validate_submission(product, answers, context, name, email):
    bounded_answers(answers)
    if product == 'board-fundraising-game':
        return validate_fundraising(answers)
    if product == 'board-recommitment':
        defaults = {'full_name': name, 'email': email, 'form_variant': 'full', 'recommitment': '', 'why_joined': '',
                    'expertise': [], 'expertise_other': '', 'participation_barriers': '', 'contribution_interests': [],
                    'ownership_area': '', 'leadership_interest': '', 'leadership_area': '', 'strengths_resources': '',
                    'monthly_availability': '', 'experience_improvement': '', 'decision_reason': '', 'advisory_openness': '',
                    'decision_support': '', 'anything_else': '', 'phone': ''}
        for key in defaults:
            if key in answers:
                if isinstance(defaults[key], list):
                    if not isinstance(answers[key], list) or any(not isinstance(v, str) for v in answers[key]):
                        raise HTTPException(422, 'Please select valid choices.')
                    defaults[key] = [clean_text(v, 300) for v in answers[key]]
                else:
                    defaults[key] = clean_text(answers[key])
        defaults.update({'full_name': name, 'email': email, 'form_variant': 'full'})
        validate_recommitment(SimpleNamespace(**defaults), 'full')
        return defaults
    cleaned = {}
    if product == 'recruit':
        answers = {**answers, 'full_name': name, 'email': email}
        if not answers.get('location'):
            answers['location'] = ', '.join(str(answers.get(k) or '').strip() for k in ('city', 'state_region', 'country') if answers.get(k))
    missing = []
    for q in context['questions']:
        key = q['id']
        value = answers.get(key, '')
        if isinstance(value, list):
            value = [clean_text(x, 2000) for x in value]
        else:
            value = clean_text(value)
        if q.get('required') and not value:
            missing.append(q.get('prompt') or q.get('label') or key)
        cleaned[key] = value
    if missing:
        raise HTTPException(422, 'Please answer every required question: ' + '; '.join(missing))
    # Preserve legacy source application fields if supplied.
    if product == 'recruit':
        from workspace_service import LEGACY_APPLICATION_FIELDS
        for key in LEGACY_APPLICATION_FIELDS:
            if key in answers:
                cleaned[key] = clean_text(answers[key])
    return cleaned


async def group_context(db, journey, shared=False):
    jid = journey['journey_id']
    submissions = await db.v2_submissions.find({'journey_id': jid}, {'_id': 0}).sort('submitted_at', 1).to_list(1000)
    decisions = await db.v2_decisions.find({'journey_id': jid}, {'_id': 0}).to_list(2000)
    commitments = await db.v2_commitments.find({'journey_id': jid}, {'_id': 0}).to_list(2000)
    sections = []
    if journey['product'] == 'board-fundraising-game':
        for category in FUNDRAISING_CATEGORIES:
            ideas = []
            for submission in submissions:
                for audience in (submission.get('answers') or {}).get('audiences', []):
                    if audience.get('category') == category:
                        ideas.append({'source_id': f"{submission['submission_id']}:{audience['audience_id']}", 'participant_id': submission['participant_id'],
                                      'name': submission['name'], 'content': audience, 'title': audience.get('funder', '')})
            # Keep all approaches. Normalized audience groups only aid comparison.
            overlap = {}
            for idea in ideas:
                normalized = re.sub(r'\W+', ' ', idea['title'].casefold()).strip()
                overlap.setdefault(normalized, []).append(idea['source_id'])
            sections.append({'key': category, 'title': category.title(), 'ideas': ideas,
                             'overlap_groups': [{'title': key, 'source_ids': ids} for key, ids in overlap.items() if len(ids) > 1]})
    else:
        context = await form_context(db, journey)
        for section in context['sections']:
            ideas = []
            for submission in submissions:
                for q in section['questions']:
                    value = (submission.get('answers') or {}).get(q['id'])
                    if value:
                        ideas.append({'source_id': f"{submission['submission_id']}:{q['id']}", 'participant_id': submission['participant_id'],
                                      'name': submission['name'], 'content': value, 'question': q['prompt'], 'title': section['title']})
            sections.append({'key': section['key'], 'title': section['title'], 'ideas': ideas,
                             'allow_keep_current_mission': section['title'] == 'Mission',
                             'current_mission': (journey.get('answers') or {}).get('mission', '') if section['title'] == 'Mission' else ''})
    invitations = await db.v2_invitations.find({'journey_id': jid}, {'_id': 0}).to_list(1000)
    people = {i['invitation_id']: {'participant_id': i['invitation_id'], 'name': i['name'], 'participation': '', 'submitted': False} for i in invitations}
    for submission in submissions:
        people[submission['participant_id']] = {'participant_id': submission['participant_id'], 'name': submission['name'], 'participation': (submission.get('answers') or {}).get('participation', ''), 'submitted': True}
    participants = list(people.values())
    # Never return leader emails, access tokens, drafts, application CVs or invitations in meeting views.
    safe_journey = {k: journey.get(k) for k in ('journey_id', 'product', 'organization', 'branding', 'meeting', 'goal_amount')}
    final = await db.v2_resources.find_one({'journey_id': jid, 'key': {'$in': ['final_strategy', 'final_plan']}, 'status': 'approved'}, {'_id': 0, 'resource_id': 1})
    return {'journey': safe_journey, 'sections': sections, 'decisions': decisions, 'commitments': [c for c in commitments if c.get('consent_confirmed') is True],
            'participants': participants, 'decision_version': journey.get('decision_version', 0), 'read_only': bool(shared or final), 'final_resource_id': (final or {}).get('resource_id')}


async def build_final_preview(db, journey):
    """Render only actual adopted records and explicitly confirmed commitments."""
    context = await group_context(db, journey)
    adopted = [d for d in context['decisions'] if d.get('status') == 'adopted']
    if not adopted:
        raise HTTPException(409, 'Adopt the decisions agreed during your meeting before preparing the final document.')
    is_fundraising = journey['product'] == 'board-fundraising-game'
    title = 'Fundraising Strategy' if is_fundraising else 'Strategic Plan'
    organization = (journey.get('branding') or {}).get('organization_name') or journey['organization']
    lines = [title, organization, '', 'This document records the decisions your organization adopted. Review the wording and confirm the final version before it is saved and emailed.', '']
    if is_fundraising and journey.get('goal_amount'):
        lines += ['Fundraising goal', f"Your stated fundraising goal is ${float(journey['goal_amount']):,.2f}.", '']
    titles = {s['key']: s['title'] for s in context['sections']}
    order = list(titles)
    for category in order:
        rows = [d for d in adopted if d['category'] == category]
        if not rows:
            continue
        lines += [titles[category], '']
        for d in rows:
            lines += [d['title'], '']
            if is_fundraising:
                content = d['content']
                for field, label in [('funder', 'The approved funding audience'), ('why', 'Why this audience may support your mission'), ('where', 'Where your organization will find this audience'), ('attract', 'How your organization will attract interest and establish credibility'), ('relationship', 'How your organization will develop the relationship and raise money'), ('ask', 'What your organization will ask this audience to support'), ('amount', 'The proposed amount and why it is appropriate')]:
                    if content.get(field):
                        lines += [label, content[field], '']
            else:
                lines += [d['content'], '']
    confirmed = [c for c in context['commitments'] if c.get('consent_confirmed') is True]
    adopted_ids = {d['decision_id'] for d in adopted}
    if is_fundraising and any(set(c.get('audience_ids', [])) - adopted_ids for c in confirmed):
        raise HTTPException(409, 'A participation commitment refers to an audience that is no longer adopted. Review and reconfirm that contribution before preparing the final strategy.')
    if is_fundraising:
        lines += ['Agreed participation commitments', '']
        if not confirmed:
            lines += ['The group has not confirmed individual participation commitments. No responsibilities have been assigned automatically.', '']
        for commitment in confirmed:
            lines += [f"{commitment['name']} has agreed to the following contribution:", commitment['responsibility'], '']
            related = [d['title'] for d in adopted if d['decision_id'] in commitment.get('audience_ids', [])]
            if related:
                lines += ['Related approved audiences: ' + '; '.join(related) + '.', '']
    return {'key': 'final_strategy' if is_fundraising else 'final_plan', 'title': title,
            'text': '\n'.join(lines).strip(), 'structured': {'adopted_decisions': adopted, 'confirmed_commitments': confirmed},
            'decision_version': journey.get('decision_version', 0)}


def create_v2_form_router(db):
    router = APIRouter(prefix='/api/v2')

    async def public_token(token):
        c = core()
        c.enabled()
        invitation = await db.v2_invitations.find_one({'form_token': token}, {'_id': 0})
        journey = await db.v2_journeys.find_one({'journey_id': invitation['journey_id']} if invitation else {'form_token': token}, {'_id': 0})
        if not journey:
            raise HTTPException(404, 'This form link is not available.')
        c.ensure_paid(journey)
        from v2_journey_flow import require_setup
        require_setup(journey)
        return journey, invitation

    async def draft_for(token, journey, draft_token='', invitation=None):
        if draft_token:
            draft = await db.v2_public_drafts.find_one({'draft_token': draft_token, 'form_token': token, 'journey_id': journey['journey_id']}, {'_id': 0})
            if not draft:
                raise HTTPException(404, 'This saved draft is not available from this form link.')
            return draft
        if invitation:
            return await db.v2_public_drafts.find_one({'invitation_id': invitation['invitation_id'], 'form_token': token}, {'_id': 0})
        return None

    async def notify_submission(journey, submission):
        from v2_email import queue_email
        notices = {
            'recruit': ('You Have a New Board Applicant', 'Someone has submitted an application for your board recruitment opportunity. You can review the application and generate an interview guide to prepare for your conversation.'),
            'board-fundraising-game': ('A Board Member Has Shared Their Fundraising Ideas', 'One of your invited participants has completed the Fundraising Game. You can review their ideas ahead of your group fundraising discussion.'),
            'strategic-planning': ('A Board Member Has Completed the Strategic Planning Form', 'A board member has submitted their ideas for your strategic planning process. You can review their responses before your planning meeting.'),
            'board-recommitment': ('You Have a New Board Recommitment Response', 'A board member has completed the recommitment form. Review their response and prepare a conversation guide for your follow-up discussion.'),
        }
        subject, body = notices[journey['product']]
        await queue_email(db, f"submission:{submission['submission_id']}:leader", journey['email'], subject, body,
                          journey_id=journey['journey_id'], action_path=f"/v2/responses/{journey['journey_id']}/{submission['submission_id']}")
        if journey['product'] == 'recruit' and journey.get('applicant_confirmation_enabled', True):
            await queue_email(db, f"submission:{submission['submission_id']}:confirmation", submission['email'], 'Your Board Application Has Been Received',
                              f"Thank you for your interest in serving on the board of {journey['organization']}. The organization has received your application and will contact you about any next steps.", journey_id=journey['journey_id'])

    @router.get('/forms/{token}')
    async def get_form(token: str, draft_token: str = ''):
        journey, invitation = await public_token(token)
        result = await form_context(db, journey, invitation)
        draft = await draft_for(token, journey, draft_token, invitation)
        if draft:
            result.update({'answers': draft.get('answers', {}), 'draft_token': draft['draft_token'], 'submitted': bool(draft.get('submission_id'))})
        else:
            from v2_admin_test import is_admin_test
            if is_admin_test(db) and not result.get('submitted'):
                from v2_admin_test_samples import response_answers
                name = (invitation or {}).get('name') or 'Sample Prospective Board Member'
                email = (invitation or {}).get('email') or 'sample-form@example.test'
                result['answers'] = response_answers(result, name, email)
        return result

    @router.put('/forms/{token}/draft')
    async def save_draft(token: str, request: Request):
        journey, invitation = await public_token(token)
        body = await request.json()
        answers = bounded_answers(body.get('answers'))
        draft = await draft_for(token, journey, body.get('draft_token', ''), invitation)
        if draft and draft.get('submission_id'):
            raise HTTPException(409, 'This response has already been submitted.')
        if invitation and invitation.get('submission_id'):
            raise HTTPException(409, 'This response has already been submitted.')
        if not draft:
            draft = {'draft_token': secrets.token_urlsafe(32), 'form_token': token, 'journey_id': journey['journey_id'],
                     'participant_id': invitation['invitation_id'] if invitation else core().new_id(),
                     'invitation_id': invitation['invitation_id'] if invitation else '', 'created_at': core().now_iso()}
            await db.v2_public_drafts.insert_one(dict(draft))
        await db.v2_public_drafts.update_one({'draft_token': draft['draft_token'], 'submission_id': {'$exists': False}},
                                          {'$set': {'answers': answers, 'updated_at': core().now_iso()}})
        return {'saved': True, 'draft_token': draft['draft_token']}

    @router.post('/forms/{token}/submit')
    async def submit_form(token: str, request: Request):
        journey, invitation = await public_token(token)
        upload = None
        if 'multipart/form-data' in request.headers.get('content-type', ''):
            form = await request.form()
            try:
                body = json.loads(str(form.get('payload') or '{}'))
            except (ValueError, TypeError) as exc:
                raise HTTPException(422, 'Invalid application payload.') from exc
            upload = form.get('cv')
        else:
            body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(422, 'Invalid form submission.')
        answers = bounded_answers(body.get('answers') or {})
        name = clean_text(body.get('name') or body.get('full_name') or answers.get('full_name') or '', 200)
        if not name:
            raise HTTPException(422, 'Enter your name.')
        email = clean_email(body.get('email') or answers.get('email'))
        if invitation and email != invitation['email']:
            raise HTTPException(403, 'Use the email address this personal invitation was sent to.')
        if journey['product'] == 'recruit' and not campaign_active(journey):
            raise HTTPException(410, 'This recruitment campaign is not accepting applications.')
        draft = await draft_for(token, journey, body.get('draft_token', ''), invitation)
        if not draft:
            # An idempotency key supports safe retries even when autosave has not run.
            key = clean_text(body.get('idempotency_key', ''), 200)
            if not key and not invitation:
                raise HTTPException(422, 'Save your response before submitting, then try again.')
            digest = hashlib.sha256(f'{token}:{key}'.encode()).hexdigest()
            draft = await db.v2_public_drafts.find_one({'submit_digest': digest, 'journey_id': journey['journey_id']}, {'_id': 0})
            if not draft:
                draft = {'draft_token': secrets.token_urlsafe(32), 'form_token': token, 'journey_id': journey['journey_id'],
                         'participant_id': invitation['invitation_id'] if invitation else core().new_id(),
                         'invitation_id': invitation['invitation_id'] if invitation else '', 'submit_digest': digest, 'created_at': core().now_iso()}
                await db.v2_public_drafts.update_one({'submit_digest': digest, 'journey_id': journey['journey_id']}, {'$setOnInsert': draft}, upsert=True)
                draft = await db.v2_public_drafts.find_one({'submit_digest': digest, 'journey_id': journey['journey_id']}, {'_id': 0})
        existing = await db.v2_submissions.find_one({'journey_id': journey['journey_id'], 'participant_id': draft['participant_id']}, {'_id': 0})
        if existing:
            await notify_submission(journey, existing)
            return {'submitted': True, 'submission_id': existing['submission_id']}
        context = await form_context(db, journey, invitation)
        answers = validate_submission(journey['product'], answers, context, name, email)
        cv = {}
        if upload and getattr(upload, 'filename', ''):
            if journey['product'] != 'recruit':
                raise HTTPException(422, 'Supporting documents are only accepted for board applications.')
            filename = upload.filename.rsplit('/', 1)[-1].rsplit('\\', 1)[-1][:200]
            suffix = filename.rsplit('.', 1)[-1].lower()
            if suffix not in {'pdf', 'doc', 'docx', 'txt'}:
                raise HTTPException(422, 'Upload a PDF, Word document or text CV.')
            content = await upload.read(MAX_CV_BYTES + 1)
            if len(content) > MAX_CV_BYTES:
                raise HTTPException(413, 'Your CV is too large. The maximum size is 10 MB.')
            if suffix == 'pdf' and not content.startswith(b'%PDF-'):
                raise HTTPException(422, 'This file does not contain a valid PDF.')
            if suffix == 'docx' and not content.startswith(b'PK'):
                raise HTTPException(422, 'This file does not contain a valid DOCX document.')
            if suffix == 'doc' and not content.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
                raise HTTPException(422, 'This file does not contain a valid Word document.')
            from ai_service import extract_cv_text
            text = content.decode('utf-8', errors='replace')[:20000] if suffix == 'txt' else extract_cv_text(content, filename)
            cv = {'filename': filename, 'mime': {'pdf': 'application/pdf', 'doc': 'application/msword', 'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'txt': 'text/plain'}[suffix],
                  'content_base64': base64.b64encode(content).decode(), 'text': str(text or '')[:120000]}
        submission = {'submission_id': core().new_id(), 'journey_id': journey['journey_id'], 'participant_id': draft['participant_id'],
                      'name': name, 'email': email, 'answers': answers,
                      'source_questions': {'sections': context.get('sections', []), 'questions': context.get('questions', [])},
                      'submitted_at': core().now_iso(), **({'cv': cv} if cv else {})}
        await db.v2_submissions.update_one({'journey_id': journey['journey_id'], 'participant_id': draft['participant_id']}, {'$setOnInsert': submission}, upsert=True)
        submission = await db.v2_submissions.find_one({'journey_id': journey['journey_id'], 'participant_id': draft['participant_id']}, {'_id': 0})
        await db.v2_public_drafts.update_one({'draft_token': draft['draft_token']}, {'$set': {'submission_id': submission['submission_id'], 'submitted_at': submission['submitted_at']}})
        if invitation:
            await db.v2_invitations.update_one({'invitation_id': invitation['invitation_id']}, {'$set': {'status': 'submitted', 'submission_id': submission['submission_id'], 'submitted_at': submission['submitted_at']}})
        await notify_submission(journey, submission)
        return {'submitted': True, 'submission_id': submission['submission_id']}

    async def owner(request, jid):
        core().enabled()
        journey = await core().require_owner(request, db, jid)
        from v2_journey_flow import require_setup, validate_meeting
        require_setup(journey)
        if journey['product'] in GROUP_PRODUCTS:
            validate_meeting(journey.get('meeting'))
        return journey

    async def invitation_template(journey, invitation=None):
        link = f"{core().origin()}/v2/forms/{(invitation or {}).get('form_token') or journey['form_token']}"
        if journey['product'] == 'board-recommitment':
            from content_templates import recommitment_outreach_email
            a = journey.get('answers') or {}
            template = recommitment_outreach_email('initial', (invitation or {}).get('name', '').split(' ')[0], journey['name'], '', journey['organization'], mission=a.get('mission', ''), goals=a.get('board_help_accomplish', ''))
            template['body'] = template['body'].replace('[COMPLETE MY BOARD MEMBER PROFILE & RECOMMITMENT FORM]', link)
        else:
            title = 'Fundraising Game' if journey['product'] == 'board-fundraising-game' else 'Strategic Planning Form'
            template = {'subject': f"Please Share Your Ideas: {title} | {journey['organization']}",
                        'body': f"Dear {(invitation or {}).get('name') or 'Board Member'},\n\nPlease share your own ideas for {journey['organization']} before our next meeting. Your responses will help us discuss the options and agree on the decisions together.\n\nComplete your {title}:\n{link}\n\nYou can save your progress and return to this link. Please say when you are unsure rather than inventing an answer.\n\nThank you,\n{journey['name']}\n{journey['organization']}"}
        return {**template, 'form_link': link}

    def invitation_public(invitation):
        return {k: v for k, v in invitation.items() if k not in {'_id'}}

    @router.get('/journeys/{jid}/invitations')
    async def get_invitations(jid: str, request: Request):
        journey = await owner(request, jid)
        rows = await db.v2_invitations.find({'journey_id': jid}, {'_id': 0}).to_list(1000)
        template = await invitation_template(journey)
        outbox = await db.v2_email_outbox.find({'journey_id': jid}, {'_id': 0}).to_list(3000)
        by_key = {row.get('event_key'): row for row in outbox}
        for row in rows:
            row['form_link'] = f"{core().origin()}/v2/forms/{row['form_token']}"
            event = by_key.get(row.get('last_event_key') or f"invitation:{row['invitation_id']}")
            if event:
                row['delivery_status'] = event.get('status', 'queued')
        return {'invitations': rows, 'invitation_template': template, 'form_link': template['form_link']}

    async def send_invitation(journey, invitation, request_key=''):
        if invitation.get('submission_id'):
            raise HTTPException(409, 'This participant has already responded.')
        from v2_email import queue_email
        template = await invitation_template(journey, invitation)
        event_key = f"invitation:{invitation['invitation_id']}" + (':' + hashlib.sha256(request_key.encode()).hexdigest()[:24] if request_key else '')
        event = await queue_email(db, event_key, invitation['email'], template['subject'], template['body'],
                                  journey_id=journey['journey_id'], action_path=f"/v2/forms/{invitation['form_token']}")
        await db.v2_invitations.update_one({'invitation_id': invitation['invitation_id']}, {'$set': {'status': 'invited', 'delivery_status': event.get('status', 'pending'), 'last_event_key': event_key, 'sent_requested_at': core().now_iso()}})
        return event

    @router.post('/journeys/{jid}/invitations')
    async def create_invitation(jid: str, request: Request):
        journey = await owner(request, jid)
        if journey['product'] == 'recruit':
            raise HTTPException(422, 'Use your recruitment outreach materials and approved public application link.')
        body = await request.json()
        name = clean_text(body.get('name', ''), 200)
        if not name:
            raise HTTPException(422, 'Enter the participant name.')
        email = clean_email(body.get('email'))
        row = await db.v2_invitations.find_one({'journey_id': jid, 'email': email}, {'_id': 0})
        if not row:
            row = {'invitation_id': core().new_id(), 'journey_id': jid, 'name': name, 'email': email, 'role': clean_text(body.get('role') or 'Board Member', 100),
                   'form_token': form_token(db, journey['product']), 'status': 'prepared', 'delivery_status': 'not_sent', 'created_at': core().now_iso()}
            await db.v2_invitations.update_one({'journey_id': jid, 'email': email}, {'$setOnInsert': row}, upsert=True)
            row = await db.v2_invitations.find_one({'journey_id': jid, 'email': email}, {'_id': 0})
        if body.get('send') is True:
            event = await send_invitation(journey, row)
            row['status'] = 'invited'
            row['delivery_status'] = event.get('status', 'pending')
        return {**invitation_public(row), 'template': await invitation_template(journey, row)}

    @router.post('/journeys/{jid}/invitations/{iid}/send')
    async def resend_invitation(jid: str, iid: str, request: Request):
        journey = await owner(request, jid)
        invitation = await db.v2_invitations.find_one({'journey_id': jid, 'invitation_id': iid}, {'_id': 0})
        if not invitation:
            raise HTTPException(404, 'This invitation is not available.')
        try:
            body = await request.json()
        except ValueError:
            body = {}
        request_key = clean_text(body.get('idempotency_key', ''), 200)
        event = await send_invitation(journey, invitation, request_key)
        return {'queued': True, 'email': event}

    @router.get('/journeys/{jid}/responses')
    async def get_responses(jid: str, request: Request):
        await owner(request, jid)
        rows = await db.v2_submissions.find({'journey_id': jid}, {'_id': 0}).sort('submitted_at', -1).to_list(1000)
        for row in rows:
            if row.get('cv'):
                row['cv'] = {k: row['cv'].get(k) for k in ('filename', 'mime')}
        return {'responses': rows}

    async def response(jid, sid):
        row = await db.v2_submissions.find_one({'journey_id': jid, 'submission_id': sid}, {'_id': 0})
        if not row:
            raise HTTPException(404, 'This response is not available.')
        return row

    @router.get('/journeys/{jid}/responses/{sid}')
    async def get_response(jid: str, sid: str, request: Request):
        journey = await owner(request, jid)
        row = await response(jid, sid)
        if row.get('cv'):
            row['cv'] = {k: row['cv'].get(k) for k in ('filename', 'mime', 'text')}
        opportunity = await db.v2_resources.find_one({'journey_id': jid, 'key': 'board_opportunity', 'status': 'approved'}, {'_id': 0, 'text': 1}) or {}
        prepared = await db.v2_resources.find({'journey_id': jid, 'submission_id': sid}, {'_id': 0, 'resource_id': 1, 'key': 1, 'title': 1, 'status': 1}).to_list(20)
        return {**row, 'organization': journey['organization'], 'product': journey['product'], 'branding': journey.get('branding') or {}, 'board_opportunity': opportunity.get('text', ''), 'prepared_resources': prepared}

    @router.get('/journeys/{jid}/responses/{sid}/cv')
    async def get_cv(jid: str, sid: str, request: Request):
        await owner(request, jid)
        row = await response(jid, sid)
        if not row.get('cv', {}).get('content_base64'):
            raise HTTPException(404, 'No supporting document was uploaded.')
        filename = row['cv']['filename'].replace('"', '').replace('\n', '').replace('\r', '')
        return Response(base64.b64decode(row['cv']['content_base64']), media_type=row['cv']['mime'],
                        headers={'Content-Disposition': f'attachment; filename="{filename}"', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})

    @router.get('/journeys/{jid}/meeting')
    async def get_meeting(jid: str, request: Request):
        journey = await owner(request, jid)
        return {'meeting': journey.get('meeting') or {}}

    @router.put('/journeys/{jid}/meeting')
    async def save_meeting(jid: str, request: Request):
        journey = await owner(request, jid)
        if journey['product'] not in GROUP_PRODUCTS:
            raise HTTPException(422, 'This service does not require a group meeting.')
        body = await request.json()
        meeting = {k: clean_text(body.get(k, ''), 100) for k in ('date', 'time', 'timezone')}
        try:
            datetime.strptime(meeting['date'], '%Y-%m-%d')
            datetime.strptime(meeting['time'], '%H:%M')
            ZoneInfo(meeting['timezone'])
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise HTTPException(422, 'Choose a valid meeting date, time and timezone.') from exc
        await db.v2_journeys.update_one({'journey_id': jid}, {'$set': {'meeting': meeting, 'updated_at': core().now_iso()}})
        from v2_email import queue_email
        fingerprint = hashlib.sha256(json.dumps(meeting, sort_keys=True).encode()).hexdigest()[:16]
        await queue_email(db, f'meeting:{jid}:{fingerprint}', journey['email'], 'Your Board Meeting Details Are Saved',
                          f"Your meeting is set for {meeting['date']} at {meeting['time']} ({meeting['timezone']}). You can open your group session now to prepare and review the submitted ideas. Your facilitation guide is available with your resources.", journey_id=jid, action_path=f'/v2/group/{jid}')
        return {'meeting': meeting}

    @router.get('/journeys/{jid}/group')
    async def get_group(jid: str, request: Request):
        journey = await owner(request, jid)
        if journey['product'] not in GROUP_PRODUCTS:
            raise HTTPException(422, 'This service does not have a group session.')
        return await group_context(db, journey)

    @router.post('/journeys/{jid}/group/share')
    async def share_group(jid: str, request: Request):
        journey = await owner(request, jid)
        if journey['product'] not in GROUP_PRODUCTS:
            raise HTTPException(422, 'This service does not have a group session.')
        await db.v2_journeys.update_one({'journey_id': jid}, {'$set': {'group_shared': True, 'group_shared_at': core().now_iso()}})
        return {'group_link': f"{core().origin()}/v2/meeting/{journey['group_token']}"}

    @router.get('/meeting/{token}')
    async def shared_group(token: str):
        core().enabled()
        journey = await db.v2_journeys.find_one({'group_token': token, 'group_shared': True}, {'_id': 0})
        if not journey or journey.get('product') not in GROUP_PRODUCTS:
            raise HTTPException(404, 'This group session is not available.')
        core().ensure_paid(journey)
        return await group_context(db, journey, shared=True)

    @router.post('/journeys/{jid}/decisions')
    async def save_decision(jid: str, request: Request):
        journey = await owner(request, jid)
        if journey['product'] not in GROUP_PRODUCTS:
            raise HTTPException(422, 'This service does not have group decisions.')
        body = await request.json()
        async with core().journey_lock(db, jid):
            journey = await core().find_journey(db, jid)
            from v2_journey_flow import require_open_group
            await require_open_group(db, journey)
            context = await group_context(db, journey)
            section = next((s for s in context['sections'] if s['key'] == body.get('category')), None)
            if not section:
                raise HTTPException(422, 'Choose an existing meeting topic.')
            status = body.get('status')
            if status not in {'adopted', 'rejected'}:
                raise HTTPException(422, 'Explicitly adopt or reject the idea.')
            source_ids = body.get('source_ids') or []
            if not isinstance(source_ids, list) or any(not isinstance(s, str) for s in source_ids):
                raise HTTPException(422, 'Provide valid source contributions.')
            source_ids = list(dict.fromkeys(source_ids))
            allowed = {idea['source_id'] for idea in section['ideas']}
            if any(s not in allowed for s in source_ids):
                raise HTTPException(422, 'Every source contribution must belong to this organization and meeting topic.')
            keep_mission = body.get('keep_existing_mission') is True or body.get('content') == '__keep_current__'
            if keep_mission:
                if not section.get('allow_keep_current_mission') or not section.get('current_mission'):
                    raise HTTPException(422, 'There is no existing mission statement to retain for this topic.')
                content = section['current_mission']
                source_ids = []
            elif journey['product'] == 'board-fundraising-game':
                value = body.get('content')
                if not isinstance(value, dict):
                    raise HTTPException(422, 'Provide the complete agreed audience strategy.')
                content = validate_fundraising({'audiences': [{**value, 'category': section['key']}], 'participation': 'Meeting decision'})['audiences'][0]
            else:
                content = clean_text(body.get('content', ''), 50000)
                if not content:
                    raise HTTPException(422, 'Enter the wording your group agreed.')
            did = body.get('decision_id')
            existing = await db.v2_decisions.find_one({'journey_id': jid, 'decision_id': did}, {'_id': 0}) if did else None
            if did and not existing:
                raise HTTPException(404, 'This decision is not available.')
            if status == 'adopted':
                conflicts = [d for d in context['decisions'] if d.get('status') == 'adopted' and d['decision_id'] != did and set(d.get('source_ids', [])) & set(source_ids)]
                if conflicts:
                    raise HTTPException(409, 'A source idea is already adopted. Edit or reject that decision before combining it into another.')
            title = clean_text(body.get('title') or section['title'], 300)
            data = {'decision_id': did or core().new_id(), 'journey_id': jid, 'category': section['key'], 'title': title,
                    'content': content, 'source_ids': source_ids, 'status': status, 'revision': (existing or {}).get('revision', 0) + 1,
                    'keep_existing_mission': keep_mission, 'updated_at': core().now_iso()}
            if existing and all(existing.get(k) == data[k] for k in ('category', 'title', 'content', 'source_ids', 'status', 'keep_existing_mission')):
                return existing
            await db.v2_decisions.update_one({'journey_id': jid, 'decision_id': data['decision_id']}, {'$set': data, '$setOnInsert': {'created_at': core().now_iso()}}, upsert=True)
            await core().touch_decisions(db, jid)
            return data

    @router.post('/journeys/{jid}/commitments')
    async def save_commitment(jid: str, request: Request):
        journey = await owner(request, jid)
        if journey['product'] != 'board-fundraising-game':
            raise HTTPException(422, 'Participation commitments belong to the Fundraising Game.')
        body = await request.json()
        if body.get('consent_confirmed') is not True:
            raise HTTPException(422, 'Confirm that this person agreed to the contribution before saving it.')
        async with core().journey_lock(db, jid):
            journey = await core().find_journey(db, jid)
            from v2_journey_flow import require_open_group
            await require_open_group(db, journey)
            context = await group_context(db, journey)
            participant = next((p for p in context['participants'] if p['participant_id'] == body.get('participant_id')), None)
            if not participant:
                raise HTTPException(422, 'Select an invited participant or a person who submitted their ideas.')
            responsibility = clean_text(body.get('responsibility', ''))
            if not responsibility:
                raise HTTPException(422, 'Record the contribution this person agreed to make.')
            audience_ids = body.get('audience_ids') or []
            allowed = {d['decision_id'] for d in context['decisions'] if d['status'] == 'adopted'}
            if not isinstance(audience_ids, list) or any(a not in allowed for a in audience_ids):
                raise HTTPException(422, 'Connect the contribution only to adopted audiences.')
            cid = body.get('commitment_id')
            existing = await db.v2_commitments.find_one({'journey_id': jid, 'commitment_id': cid}, {'_id': 0}) if cid else None
            if cid and not existing:
                raise HTTPException(404, 'This participation commitment is not available.')
            data = {'commitment_id': cid or core().new_id(), 'journey_id': jid, 'participant_id': participant['participant_id'],
                    'name': participant['name'], 'responsibility': responsibility, 'audience_ids': list(dict.fromkeys(audience_ids)),
                    'consent_confirmed': True, 'confirmed_at': core().now_iso()}
            if existing and all(existing.get(k) == data[k] for k in ('participant_id', 'responsibility', 'audience_ids', 'consent_confirmed')):
                return existing
            await db.v2_commitments.update_one({'journey_id': jid, 'commitment_id': data['commitment_id']}, {'$set': data}, upsert=True)
            await core().touch_decisions(db, jid)
            return data

    @router.delete('/journeys/{jid}/commitments/{cid}')
    async def withdraw_commitment(jid: str, cid: str, request: Request):
        journey = await owner(request, jid)
        if journey['product'] != 'board-fundraising-game':
            raise HTTPException(422, 'Participation commitments belong to the Fundraising Game.')
        async with core().journey_lock(db, jid):
            from v2_journey_flow import require_open_group
            await require_open_group(db, journey)
            row = await db.v2_commitments.find_one({'journey_id': jid, 'commitment_id': cid}, {'_id': 0})
            if not row:
                raise HTTPException(404, 'This participation commitment is not available.')
            if row.get('consent_confirmed') is True:
                await db.v2_commitments.update_one({'journey_id': jid, 'commitment_id': cid}, {'$set': {'consent_confirmed': False, 'withdrawn_at': core().now_iso()}})
                await core().touch_decisions(db, jid)
        return {'withdrawn': True}

    @router.post('/journeys/{jid}/final-preview')
    async def final_preview(jid: str, request: Request):
        journey = await owner(request, jid)
        if journey['product'] not in GROUP_PRODUCTS:
            raise HTTPException(422, 'This service does not have a final group document.')
        async with core().journey_lock(db, jid):
            journey = await core().find_journey(db, jid)
            final = await db.v2_resources.find_one({'journey_id': jid, 'key': {'$in': ['final_strategy', 'final_plan']}, 'status': 'approved'}, {'_id': 0})
            if final:
                from v2_resources import public_resource
                return public_resource(final)
            preview = await build_final_preview(db, journey)
            resource = await db.v2_resources.find_one({'journey_id': jid, 'key': preview['key']}, {'_id': 0})
            if resource and resource.get('decision_version') == preview['decision_version']:
                from v2_resources import public_resource
                return public_resource(resource)
            now = core().now_iso()
            data = {'resource_id': (resource or {}).get('resource_id') or core().new_id(), 'journey_id': jid,
                    'key': preview['key'], 'title': preview['title'], 'group': 'Final approved document', 'text': preview['text'],
                    'structured': preview['structured'], 'decision_version': preview['decision_version'], 'decisions_changed': False, 'submission_id': '',
                    'revision': (resource or {}).get('revision', 0) + 1, 'status': 'ready', 'approved_revision': None,
                    'approved_versions': (resource or {}).get('approved_versions', []), 'error': '', 'updated_at': now}
            await db.v2_resources.update_one({'journey_id': jid, 'key': preview['key']}, {'$set': data, '$setOnInsert': {'created_at': now}}, upsert=True)
            from v2_resources import public_resource
            return public_resource(data)

    return router
