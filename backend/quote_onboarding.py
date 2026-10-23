"""Paid leader questions reuse original records and Game/Planning form engines."""
import copy
import math
import secrets
from datetime import datetime
from fastapi import HTTPException, Request
from pydantic import BaseModel
from quote_defaults import VERSION


class LeaderAnswers(BaseModel):
    answers: dict
    submit: bool = False


def validate_answers(questions, previous, incoming, submit):
    known = {q['id']: q for q in questions}
    if not isinstance(incoming, dict) or set(incoming)-set(known):
        raise HTTPException(422, 'An answer does not belong to this saved question version.')
    values = {**previous, **incoming}
    for key, value in values.items():
        q = known[key]
        if len(str(value)) > 18000 or isinstance(value, bool):
            raise HTTPException(422, 'An answer is too long or has an unsupported format.')
        if value in ('', [], None):
            continue
        kind = q['type']
        if kind == 'number':
            try:
                if not math.isfinite(float(value)): raise ValueError()
            except (TypeError, ValueError): raise HTTPException(422, 'Enter a valid number.')
        elif kind == 'meeting':
            try:
                from zoneinfo import ZoneInfo
                datetime.fromisoformat(value['date']+'T'+value['time']); ZoneInfo(value['timezone'])
            except (ValueError, KeyError, TypeError): raise HTTPException(422, 'Enter the meeting date, time and time zone.')
        elif kind == 'multiselect':
            if not isinstance(value, list) or any(v not in q['options'] for v in value): raise HTTPException(422, 'Choose from the configured options.')
        elif not isinstance(value, str):
            raise HTTPException(422, 'Enter a text answer.')
        if kind == 'select' and value not in q['options']: raise HTTPException(422, 'Choose from the configured options.')
        if kind == 'date':
            try: datetime.fromisoformat(value)
            except ValueError: raise HTTPException(422, 'Enter a valid date.')
    if submit and any(q['required'] and (values.get(q['id']) in (None, '', []) or isinstance(values.get(q['id']), str) and not values[q['id']].strip()) for q in questions):
        raise HTTPException(422, 'Complete each required question before submitting.')
    return values


async def require_completed(db, row):
    if row.get('flow_kind') != VERSION: return
    if not row.get('leader_completed_at'):
        raise HTTPException(409, 'Complete your detailed leader questionnaire before booking.')
    if row['service'] == 'board-fundraising':
        person = await db.game_board_members.find_one({'user_id':row['workspace_user_id'], 'is_primary': True, 'removed':{'$ne':True}}) or {}
        if not await db.game_audience_responses.find_one({'board_member_id':person.get('member_id'), 'completed':True}):
            raise HTTPException(409, 'Complete your fundraising ideas before booking.')


async def sync_details(db, row):
    from guided_services import now, owner_id
    from quote_personalization import mapping
    values = mapping(row); uid = owner_id(row)
    await db.recruitment_profiles.update_one({'user_id':uid}, {'$set':{'data.organization_name':row['organization'], 'data.mission':values.get('mission',''), 'data.present_board':values.get('current_board',''), 'data.desired_board_members_founder_view':values.get('desired_board_members',''), 'data.priorities':values.get('board_type',''), 'data.founder_title':values.get('leader_role') or 'Organization Leader'}})
    if row['service'] == 'recruitment':
        await db.funnel_leads.update_one({'lead_id':row['customer_id']}, {'$set':{'answers':values}})
        await db.guided_service_customers.update_one({'customer_id':row['customer_id'], 'profiles_approved':{'$ne':True}}, {'$set':{'analysis':{'status':'queued'}, 'analysis_attempts':0}})
    elif row['service'] == 'board-recommitment':
        await db.board_reactivation_intakes.update_one({'user_id':uid}, {'$set':{'mission':values.get('mission',''), 'why_recommit':values.get('why_recommit',''), 'board_help_accomplish':values.get('board_help_accomplish','')}})
    elif row['service'] == 'board-fundraising':
        await db.game_profiles.update_one({'user_id':uid}, {'$set':{'organization.mission':values.get('mission',''), 'organization.board_member_count':int(float(values.get('board_size') or 0)), 'organization.funding_consequences':values.get('funding_consequences',''), 'goal.amount':float(values.get('fundraising_goal') or 0), 'goal.deadline':values.get('fundraising_deadline',''), 'profile_completed':True}})
    elif row['service'] == 'strategic-planning':
        from guided_planning import form_content
        from guided_services import settings, new_id
        config, _, _ = await settings(db, row['service'])
        config['question_groups']['leader'] = row['leader_question_snapshot']
        project = await db.sp_projects.find_one({'project_id':row['customer_id']}, {'_id':0})
        snapshot = form_content(config, 'leader', project)
        person = {'participant_id':new_id(), 'project_id':row['customer_id'], 'name':row['name'], 'email':row['email'], 'role':'Lead User', 'form_token':secrets.token_urlsafe(32), 'review_token':secrets.token_urlsafe(32), 'review_status':'NOT SENT', 'form_version':row.get('leader_question_version','initial'), 'form_snapshot':snapshot, 'created_at':now()}
        await db.sp_participants.update_one({'project_id':row['customer_id'], 'email':row['email']}, {'$setOnInsert':person}, upsert=True)
        await db.sp_participants.update_one({'project_id':row['customer_id'], 'email':row['email']}, {'$set':{'response':row['leader_answers'], 'draft_answers':row['leader_answers'], 'status':'COMPLETED', 'submitted_at':now()}})


def register_routes(router, db):
    from guided_services import record_by_token, settings, public_record, provision_workspace, now, admin_record, owner_id, new_id

    async def data(row, request):
        if row.get('payment_status') != 'paid': raise HTTPException(402, 'Payment has not been confirmed.')
        config, _, version = await settings(db, row['service'])
        if not row.get('leader_question_snapshot'):
            questions = [copy.deepcopy(q) for q in config['question_groups']['leader'] if not q['archived']]
            first = {q['key']:row.get('answers',{}).get(q['id'],'') for q in row['question_snapshot']}
            initial = {q['id']:first[q['key']] for q in questions if q['key'] in first}
            await db.guided_service_customers.update_one({'customer_id':row['customer_id'], 'leader_question_snapshot':{'$exists':False}}, {'$set':{'leader_question_snapshot':questions, 'leader_answers':initial, 'leader_question_version':version}})
            row = await db.guided_service_customers.find_one({'customer_id':row['customer_id']}, {'_id':0})
        first = {q['key']:row.get('answers',{}).get(q['id'],'') for q in row['question_snapshot']}
        answers = {q['id']:first[q['key']] for q in row['leader_question_snapshot'] if q['key'] in first}
        answers.update(row.get('leader_answers') or {})
        from quote_personalization import mapping
        values=mapping(row)
        result = {'context':{'organization_name':row['organization'],'member':{'is_primary':True},'branding':row.get('branding') or {},'goal_display':str(values.get('fundraising_goal','')),'deadline':str(values.get('fundraising_deadline',''))},'questions':row['leader_question_snapshot'], 'answers':answers, 'completed':bool(row.get('leader_completed_at')), 'details_completed':bool(row.get('leader_details_completed_at')), 'copy':config['customer_copy']}
        if row['service']=='board-fundraising' and row.get('leader_details_completed_at') and not row.get('leader_completed_at'):
            from guided_workspace import delegated_request
            response = await delegated_request(request.app,db,row,'POST','game/self-play',{})
            if response.status_code not in (200,201):raise HTTPException(response.status_code,'Your saved fundraising questionnaire could not be opened. Please try again.')
            result['audience_token']=response.json()['token']
        return result

    @router.get('/services/{service}/customer/{token}/leader-questions')
    async def leader_questions(service:str, token:str, request:Request):
        return await data(await record_by_token(db,service,token,True), request)

    @router.put('/services/{service}/customer/{token}/leader-questions')
    async def leader_answers(service:str, token:str, payload:LeaderAnswers, request:Request):
        row=await record_by_token(db,service,token,True)
        await data(row,request)
        row=await db.guided_service_customers.find_one({'customer_id':row['customer_id']},{'_id':0})
        if row.get('leader_details_completed_at'):
            if all(row.get('leader_answers',{}).get(k)==v for k,v in payload.answers.items()):return await data(row,request)
            raise HTTPException(409,'Your leader questionnaire is saved. Contact Rooney if it needs a correction.')
        original={q['key']:row.get('answers',{}).get(q['id'],'') for q in row['question_snapshot']}
        initial={q['id']:original[q['key']] for q in row['leader_question_snapshot'] if q['key'] in original}
        answers=validate_answers(row['leader_question_snapshot'],{**initial,**row.get('leader_answers',{})},payload.answers,payload.submit)
        updates={'leader_answers':answers,'updated_at':now()}
        if payload.submit:
            updates['leader_details_completed_at']=now()
            if service!='board-fundraising':updates['leader_completed_at']=now()
        await db.guided_service_customers.update_one({'customer_id':row['customer_id'],'leader_details_completed_at':{'$exists':False}},{'$set':updates})
        saved=await db.guided_service_customers.find_one({'customer_id':row['customer_id']},{'_id':0})
        if payload.submit:await sync_details(db,saved)
        return await data(saved,request)

    @router.post('/services/board-fundraising/customer/{token}/leader-complete')
    async def complete_fundraising(token:str):
        row=await record_by_token(db,'board-fundraising',token,True)
        if not row.get('leader_details_completed_at'):raise HTTPException(409,'Complete your organization questions first.')
        person=await db.game_board_members.find_one({'user_id':owner_id(row),'is_primary':True,'removed':{'$ne':True}}) or {}
        if not await db.game_audience_responses.find_one({'board_member_id':person.get('member_id'),'completed':True}):raise HTTPException(409,'Complete your audience-specific fundraising ideas first.')
        await db.guided_service_customers.update_one({'customer_id':row['customer_id']},{'$set':{'leader_completed_at':now()}})
        return {'completed':True}

    @router.post('/admin/services/{service}/test-post-payment')
    async def test_paid(service:str,request:Request):
        from auth_service import authenticate_admin
        from guided_services import check_service, digest
        from guided_service_defaults import FLOW_VERSION, package
        actor=await authenticate_admin(request,db);check_service(service,True);config,_,version=await settings(db,service)
        ident=new_id();token=secrets.token_urlsafe(32)
        snapshot=[q for q in config['question_groups']['entry'] if not q['archived']]
        # Synthetic quote answers only. The detailed questions are the current
        # published version and remain available for the owner to complete.
        answers={q['id']:('3' if q['type']=='number' else 'Sample organization priorities') for q in snapshot}
        row={'customer_id':ident,'request_id':new_id(),'service':service,'flow_version':FLOW_VERSION,'flow_kind':VERSION,'name':'Sample Nonprofit Leader','email':'sample-leader@nonprofitboardbuilder.internal','organization':'Sample Community Organization','access_token':token,'token_hash':digest(token),'unsubscribe_token':secrets.token_urlsafe(32),'workspace_user_id':'admin-dashboard-preview-guided-'+ident,'question_snapshot':snapshot,'question_version':version,'answers':answers,'leader_question_snapshot':[q for q in config['question_groups']['leader'] if not q['archived']],'leader_question_version':version,'leader_answers':{},'payment_status':'paid','purchased_package':package(service)['key'],'amount_paid':0,'test_payment':True,'paid_at':now(),'booking_status':'not_booked','internal_test':True,'test_owner':actor['user_id'],'created_at':now(),'updated_at':now(),'submitted_at':now(),'sequence_stopped':True}
        await db.guided_service_customers.insert_one(copy.deepcopy(row));await provision_workspace(db,row)
        return {'customer_id':ident,'url':f'/services/{service}/setup/{token}','internal_test':True}
