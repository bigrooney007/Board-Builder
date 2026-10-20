"""Guided Recommitment adapters over the existing forms, records and materials."""
import copy
import secrets
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from consultation_routes import no_cache, origin
from guided_service_defaults import question
from guided_services import admin_record, context, continuation, email_text, now, owner_id, preview_email, record_by_token, render, settings
from guided_workspace import current_version, delegated_request, material_snapshot, notify_guided_owner
from workflow_delivery import deliver_once
SERVICE='board-recommitment'
OUTCOMES={'active':'Continuing as an Active Board Member','advisory':'Transitioning to an Advisory Role','step_down':'Stepping Down From the Board'}

def decisions():
    from recommitment_decisions import RECOMMIT_ACTIVE, RECOMMIT_ADVISORY, RECOMMIT_STEP_DOWN
    return {'active':RECOMMIT_ACTIVE,'advisory':RECOMMIT_ADVISORY,'step_down':RECOMMIT_STEP_DOWN}

def participant_defaults():
    def q(key,prompt,groups,required=True,kind='textarea',**kw):return question(key,prompt,required=required,kind=kind,show_for=groups,**kw)
    return {'title':'Your Board Recommitment Decision','introduction':'Please reflect on your continued involvement with your organization. Tell us what fits your circumstances now and explain your decision in your own words. Your response will help the organization prepare a respectful conversation with you. Submitting this form does not automatically change your formal board position.',
        'decision_prompt':'How would you like to move forward?','decision_help':'Choose the option that best reflects your present intentions.',
        'labels':{'active':'Recommit and Step Up','advisory':'Discuss an Advisory or Alternative Role','step_down':'Step Down From the Board'},
        'thank_you':'Thank you for sharing your decision. Your organization will review what you have said and follow up with you about the appropriate next steps.',
        'questions':[
            q('why_joined','Why would you like to continue serving this organization?',['active']),
            q('expertise','What expertise could you contribute?',['active'],kind='multiselect',options=['Fundraising','Finance / Accounting','Legal','Marketing / Communications','Strategic Planning','Partnerships','Education','Technology','Operations','Other']),
            q('participation_barriers','What has made participation difficult, and what would help?',['active']),
            q('contribution_interests','Which areas would you like to support?',['active'],kind='multiselect',options=['Fundraising / Resource Development','Marketing & Communications','Programs & Impact','Partnerships','Finance','Governance / Board Development','Strategic Planning','Technology','Volunteer Development','Community Engagement','Operations','Other']),
            q('ownership_area','What responsibility would you be willing to discuss taking on?',['active']),
            q('leadership_interest','Would you like to discuss leading a particular area?',['active'],False,'select',options=['Yes','I would like to discuss this','No']),
            q('leadership_area','Which area would you like to discuss leading?',['active'],False),
            q('strengths_resources','What strengths, experience, relationships or resources could you contribute?',['active','advisory']),
            q('monthly_availability','What time can you realistically make available?',['active','advisory']),
            q('experience_improvement','What support would help you contribute effectively?',['active']),
            q('decision_reason','What has led you to this decision, and what would you like us to understand?',['advisory','step_down']),
            q('anything_else','Is there anything else you would like to share?',['active','advisory','step_down'],False)]}

async def guided_context(db,record,freeze=False):
    row=await db.guided_service_customers.find_one({'workspace_user_id':record['user_id'],'service':SERVICE,'payment_status':'paid'},{'_id':0})
    if not row:return {}
    config,_,version=await settings(db,SERVICE)
    form=record.get('guided_form_snapshot') or {**copy.deepcopy(config['participant_form']),'version':version}
    if freeze and record.get('member_record_id') and not record.get('guided_form_snapshot'):
        await db.reactivation_board_members.update_one({'member_record_id':record['member_record_id']},{'$set':{'guided_form_snapshot':form}})
    return {'guided_form':form,'branding':row.get('branding') or {},'decision_options':[{'id':key,'label':form['labels'][key],'value':value} for key,value in decisions().items()]}

async def validated_response(db,record,payload):
    info=await guided_context(db,record,True)
    if not info:return None
    form=info['guided_form'];choice=next((key for key,value in decisions().items() if value==payload.recommitment),None)
    if not choice:raise HTTPException(422,'Choose one of the three recommitment decisions.')
    if str(payload.email).lower()!=record['email'].lower():raise HTTPException(403,'Use the email address associated with your personal form link.')
    values=payload.guided_answers or {};questions=[q for q in form['questions'] if not q['archived'] and choice in q['show_for']]
    known={q['id']:q for q in questions}
    if set(values)-set(known):raise HTTPException(422,'An answer does not belong to this decision and form version.')
    response=payload.model_dump()
    for q in questions:
        value=values.get(q['id'],'')
        if q['required'] and (not value or isinstance(value,str) and not value.strip()):raise HTTPException(422,'Please complete each required question.')
        if not isinstance(value,(str,list)) or len(str(value))>18000:raise HTTPException(422,'Use a text answer or the configured choices.')
        if q['type'] in {'select','multiselect'}:
            choices=value if isinstance(value,list) else [value]
            if any(x and x not in q['options'] for x in choices):raise HTTPException(422,'Choose from the available answers.')
        if q['key'] in response:response[q['key']]=value
    response.update({'guided_answers':values,'question_snapshot':form,'decision_id':choice})
    return response

async def participant(db,row,ident):
    record=await db.reactivation_board_members.find_one({'user_id':owner_id(row),'member_record_id':ident},{'_id':0})
    if not record:raise HTTPException(404,'Board member not found for this organization.')
    return record

class Person(BaseModel):
    name:str=Field(min_length=1,max_length=200)
    email:EmailStr
    role:str=Field(default='',max_length=300)
    notes:str=Field(default='',max_length=6000)

async def message_for(db,row,record,kind):
    config,_,_=await settings(db,SERVICE)
    allowed={'board_invitation','conversation_invite','active_confirmation','alternative_discussion','step_down_acknowledgement','portfolio_delivery'}
    if kind not in allowed:raise HTTPException(422,'Choose a supported recommitment communication.')
    if kind=='active_confirmation' and not(record.get('decision_confirmed') and record.get('conversation_outcome')==OUTCOMES['active']):raise HTTPException(409,'Confirm the agreed active role before sending this confirmation.')
    if kind=='step_down_acknowledgement' and not(record.get('decision_confirmed') and record.get('conversation_outcome')==OUTCOMES['step_down']):raise HTTPException(409,'Confirm the appropriate organizational decision before acknowledging a departure.')
    form_url=origin()+'/board-recommitment/'+record['form_token'];link=form_url
    if kind=='portfolio_delivery':
        material=await db.generated_materials.find_one({'user_id':owner_id(row),'application_id':record['member_record_id'],'type':'reactivation_board_member_portfolio','status':'Approved'},{'_id':0})
        if not material or not material.get('share_token'):raise HTTPException(409,'Approve this board member’s portfolio before sending it.')
        link=origin()+'/portfolio/'+material['share_token']
    intake=await db.board_reactivation_intakes.find_one({'user_id':owner_id(row)},{'_id':0}) or {}
    values={**context(row),'participant_name':record['name'],'leader_name':row['name'],'agreed_purpose':intake.get('why_recommit','')+'\n\n'+intake.get('board_help_accomplish',''),'form_url':form_url,'responsibilities':record.get('conversation_conclusion','')}
    return render(config['operational_emails'][kind],values),link

def create_guided_recommitment_router(db):
    router=APIRouter(prefix='/api',dependencies=[Depends(no_cache)])
    async def actor(request,ident=None,token=None):return await admin_record(db,SERVICE,ident,request,True) if ident else await record_by_token(db,SERVICE,token,True)

    @router.get('/admin/services/board-recommitment/customers/{ident}/recommitment')
    @router.get('/services/board-recommitment/customer/{token}/recommitment')
    async def workspace(request:Request,ident:str=None,token:str=None):
        row=await actor(request,ident,token);people=await db.reactivation_board_members.find({'user_id':owner_id(row)},{'_id':0}).sort('created_at',1).to_list(500)
        for person in people:
            if token or '/operator/' in request.url.path:
                person.pop('private_notes',None);person.pop('call_notes',None)
            person['form_url']=origin()+'/board-recommitment/'+person.pop('form_token')
            person['decision_status']='Decision confirmed' if person.get('decision_confirmed') else 'Follow-up conversation needed' if person.get('follow_up_needed') else 'Responded' if person.get('status')=='COMPLETED' else 'Awaiting response' if person.get('status')=='SENT' else 'Not yet invited'
        materials=await db.generated_materials.find({'user_id':owner_id(row)},{'_id':0}).to_list(500)
        if token:materials=[m for m in materials if m.get('status')=='Approved' or m['type']=='reactivation_conversation_script']
        form=await db.reactivation_forms.find_one({'user_id':owner_id(row)},{'_id':0}) or {}
        return {'participants':people,'materials':materials,'setup':await db.board_reactivation_intakes.find_one({'user_id':owner_id(row)},{'_id':0}) or {},'form':form,'branding':row.get('branding',{})}

    async def existing_people(row):
        owners=[]
        member=await db.members.find_one({'email':row['email']},{'_id':0})
        if member:owners.append(member['user_id'])
        earlier=await db.guided_service_customers.find({'email':row['email'],'organization':row['organization'],'payment_status':'paid','customer_id':{'$ne':row['customer_id']}},{'_id':0,'workspace_user_id':1}).to_list(50)
        owners.extend(p['workspace_user_id'] for p in earlier)
        people=[]
        for uid in owners:
            profile=await db.recruitment_profiles.find_one({'user_id':uid},{'_id':0}) or {}
            intake=await db.board_reactivation_intakes.find_one({'user_id':uid},{'_id':0}) or {}
            org=(profile.get('data') or {}).get('organization_name') or intake.get('organization_name') or ''
            if org.strip().casefold()!=row['organization'].strip().casefold():continue
            for p in await db.reactivation_board_members.find({'user_id':uid},{'_id':0}).to_list(300):people.append({'source_id':'member:'+p['member_record_id'],'name':p['name'],'email':p['email'],'role':p.get('role','')})
            for p in await db.opportunity_applications.find({'owner_user_id':uid,'status':'Selected'},{'_id':0}).to_list(300):people.append({'source_id':'applicant:'+p['application_id'],'name':(p.get('profile_snapshot') or {}).get('full_name',''),'email':p['applicant_email'],'role':p.get('board_role','')})
        return people

    @router.get('/admin/services/board-recommitment/customers/{ident}/existing-members')
    async def existing(ident:str,request:Request):return {'people':await existing_people(await actor(request,ident))}

    @router.post('/admin/services/board-recommitment/customers/{ident}/import-member')
    async def import_person(ident:str,payload:dict,request:Request):
        row=await actor(request,ident);source=next((p for p in await existing_people(row) if p['source_id']==payload.get('source_id')),None)
        if not source or payload.get('confirmed') is not True:raise HTTPException(422,'Confirm that this existing member belongs to this organization and should join this recommitment engagement.')
        response=await delegated_request(request.app,db,row,'POST','reactivation/board-members',{k:source[k] for k in ('name','email','role')});person=response.json()['member']
        await db.reactivation_board_members.update_one({'member_record_id':person['member_record_id']},{'$set':{'source_member_reference':source['source_id']}})
        await guided_context(db,await participant(db,row,person['member_record_id']),True)
        return response.json()

    @router.post('/admin/services/board-recommitment/customers/{ident}/participants')
    async def add(ident:str,payload:Person,request:Request):
        row=await actor(request,ident);response=await delegated_request(request.app,db,row,'POST','reactivation/board-members',payload.model_dump());record=response.json()['member']
        saved=await participant(db,row,record['member_record_id']);await guided_context(db,saved,True)
        await db.reactivation_board_members.update_one({'member_record_id':record['member_record_id']},{'$set':{'private_notes':payload.notes}})
        return response.json()

    @router.post('/admin/services/board-recommitment/customers/{ident}/participants/{person_id}/message-preview')
    @router.post('/services/board-recommitment/customer/{token}/participants/{person_id}/message-preview')
    async def preview(person_id:str,payload:dict,request:Request,ident:str=None,token:str=None):
        row=await actor(request,ident,token);record=await participant(db,row,person_id);await guided_context(db,record,True);message,link=await message_for(db,row,record,payload.get('kind','board_invitation'))
        return {**message,'kind':payload.get('kind','board_invitation'),'recipient':record['email'],'link':link,'html':preview_email(message,link)}

    @router.post('/admin/services/board-recommitment/customers/{ident}/participants/{person_id}/message-send')
    @router.post('/services/board-recommitment/customer/{token}/participants/{person_id}/message-send')
    async def send(person_id:str,payload:dict,request:Request,ident:str=None,token:str=None):
        row=await actor(request,ident,token);record=await participant(db,row,person_id);kind=payload.get('kind','board_invitation');default,link=await message_for(db,row,record,kind)
        if not payload.get('approved'):raise HTTPException(409,'Review and approve the email before sending.')
        message={k:str(payload.get(k,default[k]))[:20000] for k in default};key='guided-recommitment-'+person_id+'-'+str(uuid.UUID(payload['request_id']))
        result=await deliver_once(db,owner_id(row),key,record['email'],message['subject'],email_text(message),link,cta_label=message['cta'])
        if result['status'] in {'sent','captured'} and kind=='board_invitation':
            await db.reactivation_board_members.update_one({'member_record_id':person_id,'status':{'$ne':'COMPLETED'}},{'$set':{'status':'SENT','last_sent_at':now(),'invitation_delivery':result['status']}})
        return result

    @router.put('/admin/services/board-recommitment/customers/{ident}/participants/{person_id}/decision')
    @router.put('/services/board-recommitment/customer/{token}/participants/{person_id}/decision')
    async def decision(person_id:str,payload:dict,request:Request,ident:str=None,token:str=None):
        row=await actor(request,ident,token);record=await participant(db,row,person_id)
        if record.get('status')!='COMPLETED':raise HTTPException(409,'A submitted response is required before confirming the outcome.')
        if not payload.get('confirmed') or payload.get('outcome') not in OUTCOMES.values() or not str(payload.get('conclusion','')).strip():raise HTTPException(422,'Record the actual agreement and confirm the appropriate organizational decision.')
        if payload['outcome']!=OUTCOMES['step_down'] and not str(payload.get('role','')).strip():raise HTTPException(422,'Record the agreed role.')
        await delegated_request(request.app,db,row,'PUT',f'reactivation/board-members/{person_id}/conclusion',{'conclusion':str(payload['conclusion'])[:12000]})
        await delegated_request(request.app,db,row,'PUT',f'reactivation/board-members/{person_id}/outcome',{'outcome':payload['outcome']})
        if payload['outcome']!=OUTCOMES['step_down']:await delegated_request(request.app,db,row,'PUT',f'reactivation/board-members/{person_id}/confirmed-role',{'role':payload['role']})
        await db.reactivation_board_members.update_one({'member_record_id':person_id},{'$set':{'decision_confirmed':True,'decision_confirmed_at':now(),'follow_up_needed':False},'$push':{'decision_history':{'outcome':payload['outcome'],'conclusion':payload['conclusion'],'role':payload.get('role',''),'confirmed_at':now()}}})
        return {'status':'saved'}

    @router.post('/services/board-recommitment/customer/{token}/participants/{person_id}/conversation')
    async def customer_conversation(token:str,person_id:str,request:Request):
        row=await actor(request,token=token);await participant(db,row,person_id)
        return (await delegated_request(request.app,db,row,'POST',f'reactivation/board-members/{person_id}/conversation-script',{})).json()

    @router.put('/services/board-recommitment/customer/{token}/conversation/{material_id}')
    async def customer_edit(token:str,material_id:str,payload:dict):
        row=await record_by_token(db,SERVICE,token,True);material,_=await material_snapshot(db,row,material_id)
        if material['type']!='reactivation_conversation_script':raise HTTPException(403,'Only a conversation guide can be edited here.')
        text=str(payload.get('display_text','')).strip()
        if not text or len(text)>100000:raise HTTPException(422,'Add the conversation guide content.')
        version=max(v['version'] for v in material['versions'])+1
        await db.generated_materials.update_one({'material_id':material_id},{'$push':{'versions':{'version':version,'display_text':text,'structured':{},'source':'edited','created_at':now()}},'$set':{'current_version':version,'status':'Draft'}})
        return {'status':'saved'}

    @router.post('/services/board-recommitment/customer/{token}/conversation/{material_id}/approve')
    async def customer_approve(token:str,material_id:str,payload:dict):
        row=await record_by_token(db,SERVICE,token,True);material,version=await material_snapshot(db,row,material_id)
        if material['type']!='reactivation_conversation_script' or payload.get('version')!=version['version']:raise HTTPException(409,'Review the latest conversation guide before approval.')
        await db.generated_materials.update_one({'material_id':material_id},{'$set':{'status':'Approved','approved_at':now()}})
        return await notify_guided_owner(db,owner_id(row),'guided-approved-conversation-'+material_id+'-'+str(version['version']),'Your Approved Conversation Guide','Your approved conversation guide is saved with your resources. Use it to explore the board member’s stated views respectfully and record what you agree together.')

    @router.post('/admin/services/board-recommitment/customers/{ident}/participants/{person_id}/agreements/{kind}')
    async def agreement(ident:str,person_id:str,kind:str,request:Request):
        row=await actor(request,ident);record=await participant(db,row,person_id)
        if kind not in {'board_member_agreement','confidentiality_agreement','conflict_of_interest_agreement'}:raise HTTPException(422,'Choose a supported board agreement.')
        if not record.get('decision_confirmed') or record.get('conversation_outcome')==OUTCOMES['step_down']:raise HTTPException(409,'Confirm the continuing member’s agreed role and responsibilities first.')
        from ai_service import generate_structured
        from workspace_service import save_generation,build_org_context
        member=await db.members.find_one({'user_id':owner_id(row)},{'_id':0})
        source=await build_org_context(db,owner_id(row),member)
        source+='\n\nACTUAL AGREEMENT: '+record.get('conversation_conclusion','')+'\nAGREED ROLE: '+record.get('confirmed_role','')
        structured=await generate_structured(kind,source,'Use only the recorded agreement. Do not invent terms, obligations, dates or legal requirements. Human review is required before release.')
        return await save_generation(db,owner_id(row),kind,structured,'Confirmed recommitment agreement',person_id)

    @router.post('/admin/services/board-recommitment/customers/{ident}/participants/{person_id}/signature')
    async def signature(ident:str,person_id:str,payload:dict,request:Request):
        row=await actor(request,ident);record=await participant(db,row,person_id);material,version=await material_snapshot(db,row,payload.get('material_id'),True)
        if not record.get('decision_confirmed') or material.get('application_id')!=person_id or material['type'] not in {'board_member_agreement','confidentiality_agreement','conflict_of_interest_agreement'}:raise HTTPException(409,'Approve this member’s agreed document first.')
        query={'owner_user_id':owner_id(row),'application_id':person_id,'material_id':material['material_id'],'agreement_version':version['version']}
        item=await db.signature_requests.find_one(query,{'_id':0})
        if not item:
            item={**query,'request_id':str(uuid.uuid4()),'token':secrets.token_urlsafe(40),'agreement_type':material['type'],'agreement_title':material['title'],'document_snapshot':version['display_text'],'organization_name':row['organization'],'board_member_name':record['name'],'board_member_email':record['email'],'status':'Ready for Signature','created_at':now(),'updated_at':now()}
            await db.signature_requests.insert_one(item.copy())
        if payload.get('approved'):
            config,_,_=await settings(db,SERVICE);message=render(config['operational_emails']['signature_invitation'],context(row))
            result=await deliver_once(db,owner_id(row),'guided-signature-invitation-'+item['request_id'],record['email'],message['subject'],email_text(message),origin()+'/sign/'+item['token'],cta_label=message['cta'])
            return {'request_id':item['request_id'],**result}
        return {'request_id':item['request_id'],'preview_url':origin()+'/sign/'+item['token']}
    from service_handover import register_operator_routes
    register_operator_routes(router,'/admin/services/board-recommitment/customers/{ident}','/services/board-recommitment/operator/{ident}')
    return router
