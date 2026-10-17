"""Simplified Fundraising Game entry, recovery and admin extensions of existing services.

Existing payment verification, member permissions, personal game links, synchronized
meetings, document renderer and portfolio records remain authoritative.
"""
import asyncio
import copy
import hashlib
import json
import logging
import os
import re
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, EmailStr, Field
from auth_service import authenticate_admin
from member_auth import authenticate_member, require_entitlement
from workflow_delivery import deliver_once
from document_renderer import render_document_pdf

VERSION = 7
SOURCE = "fundraising-game-simplified"
DEFAULT = json.loads(Path(__file__).with_name('fundraising_launch_content.json').read_text())
logger = logging.getLogger(__name__)

def now(): return datetime.now(timezone.utc).isoformat()
def origin(): return (os.environ.get('PUBLIC_ORIGIN') or 'https://nonprofitboardbuilder.com').rstrip('/')
def digest(value): return hashlib.sha256(str(value).encode()).hexdigest()
async def content(db):
    saved = await db.site_content.find_one({'key': SOURCE}, {'_id': 0}) or {}
    def merge(base,override):
        if isinstance(base,dict) and isinstance(override,dict):return {k:merge(v,override.get(k,v)) for k,v in base.items()}
        return copy.deepcopy(override)
    return merge(DEFAULT,saved.get('content',{}))

class Lead(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    organization: str = Field(min_length=1,max_length=300)
    visitor_id: str = Field(min_length=12,max_length=100)
    marketing_consent: bool = False
    resume_token: str = Field(default='',max_length=100)

class Organization(BaseModel):
    fundraising_goal: float = Field(gt=0,le=1e12)
    mission: str = Field(min_length=1,max_length=10000)
    annual_budget: str = Field(min_length=1,max_length=1000)
    website: str = Field(default='',max_length=2000)
    community: str = Field(min_length=1,max_length=6000)

async def activate_purchase(db, member, lead_token, session_id):
    """Called only after the existing Stripe verification confirms a paid purchase."""
    lead = await db.funnel_leads.find_one({'result_token': lead_token,'lead_source': SOURCE},{'_id':0})
    if not lead or lead['email'].lower() != member['email'].lower():
        raise HTTPException(409,'Use the email entered before checkout to claim this purchase')
    await db.funnel_leads.update_one({'lead_id':lead['lead_id']},{'$set':{'paid_at':lead.get('paid_at') or now(),'stage':'paid','member_user_id':member['user_id'],'session_id':session_id,'followup_stopped':True}})
    # Never replace an existing historical organization/game to sell a second one.
    existing = await db.game_profiles.find_one({'user_id':member['user_id']},{'_id':0})
    if existing and existing.get('workflow_version')!=7:
        historical=await db.purchases.find_one({'user_id':member['user_id'],'entitlement':'board_fundraising_game','session_id':{'$ne':session_id}},{'_id':0})
        if historical:raise HTTPException(409,'This account already has a purchased game. Contact support before starting another.')
        await db.legacy_game_profiles.update_one({'user_id':member['user_id']},{'$setOnInsert':{'user_id':member['user_id'],'profile':existing,'archived_at':now()}},upsert=True)
        await db.game_profiles.update_one({'user_id':member['user_id']},{'$set':{'workflow_version':7,'simplified_product':True,'organization':{'name':lead['organization']},'primary_user':{'full_name':lead['name'],'email':member['email']},'profile_completed':False,'goal':{}}})
    name = lead['name']
    await db.game_profiles.update_one({'user_id':member['user_id']},{'$setOnInsert':{'user_id':member['user_id'],'workflow_version':7,'simplified_product':True,
        'organization':{'name':lead['organization']},'primary_user':{'full_name':name,'email':member['email']},'profile_completed':False,'created_at':now()},'$set':{'updated_at':now()}},upsert=True)
    if not await db.game_journey_progress.find_one({'user_id':member['user_id']}):
        await touch(db,member['user_id'],'organization','/game/setup')
    await deliver_once(db,member['user_id'],'launch-welcome:'+session_id,member['email'],'Your Fundraising Game Is Ready','Your payment is confirmed. Save your organization details, answer your own fundraising questions, then set your meeting and invite your board. Your progress is saved so you can return whenever you need to.',origin()+'/login?next=%2Fgame%2Fsetup')

async def touch(db,user,stage,path):
    await db.game_journey_progress.update_one({'user_id':user},{'$set':{'stage':stage,'path':path,'updated_at':now(),'completed':stage=='complete'},'$setOnInsert':{'user_id':user,'created_at':now()}},upsert=True)

async def event(db, visitor, kind, lead_id=''):
    if kind not in {'homepage','page_two','contact','checkout'}: raise HTTPException(422,'Unknown funnel event')
    key=digest(f'{visitor}:{kind}:{lead_id}:{datetime.now(timezone.utc).date().isoformat()}')
    await db.funnel_events.update_one({'event_id':key},{'$setOnInsert':{'event_id':key,'source':SOURCE,'visitor_id':visitor,'kind':kind,'lead_id':lead_id,'created_at':now()},'$inc':{'views':1},'$set':{'last_seen_at':now()}},upsert=True)

async def send_due(db):
    """Existing Resend transport with durable keys, paid-stop checks and consent."""
    templates=(await content(db))['followups']
    threshold=(datetime.now(timezone.utc)-timedelta(days=3)).isoformat()
    leads=await db.funnel_leads.find({'lead_source':SOURCE,'internal_preview':{'$ne':True},'marketing_consent':True,'unsubscribed':{'$ne':True},'paid_at':{'$exists':False},'created_at':{'$lte':threshold}},{'_id':0}).to_list(1000)
    for lead in leads:
        created=datetime.fromisoformat(lead['created_at'])
        sequence_owner='launch-sequence:'+digest(lead['email'].lower())
        for index,template in enumerate(templates,1):
            due=created+timedelta(days=index*3)
            if due>datetime.now(timezone.utc): break
            # Recheck immediately before dispatch, including unclaimed paid checkouts.
            current=await db.funnel_leads.find_one({'lead_id':lead['lead_id']},{'_id':0})
            paid=await db.payment_transactions.find_one({'launch_lead_token':lead['result_token'],'payment_status':'paid'},{'_id':0,'session_id':1})
            paid_account=await db.members.find_one({'email':lead['email'].lower(),'entitlements':'board_fundraising_game'},{'_id':0,'user_id':1})
            other_payment=await db.payment_transactions.find_one({'lead_email':lead['email'].lower(),'payment_status':'paid'},{'_id':0,'session_id':1})
            if current.get('paid_at') or current.get('unsubscribed') or paid or paid_account or other_payment: break
            previous=await db.workflow_email_deliveries.find_one({'user_id':sequence_owner,'event_key':'followup:'+str(index)},{'_id':0})
            if previous and previous.get('status') in ('sent','captured'): continue
            # Do not send multiple overdue promotional messages on the same day.
            recent=await db.workflow_email_deliveries.find_one({'user_id':sequence_owner,'status':{'$in':['sent','captured']},'updated_at':{'$gte':(datetime.now(timezone.utc)-timedelta(days=3)).isoformat()}},{'_id':0})
            if recent: break
            link=origin()+'/api/fundraising/return/'+lead['result_token']+'?email='+str(index)
            unsubscribe=origin()+'/api/fundraising/unsubscribe/'+lead['unsubscribe_token']
            await deliver_once(db,sequence_owner,'followup:'+str(index),lead['email'],template['subject'],template['body'],link,unsubscribe_url=unsubscribe)
            break
    # Transactional recovery is separate, capped and bound to a purchased account.
    stale=(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat()
    for progress in await db.game_journey_progress.find({'completed':False,'updated_at':{'$lte':stale}},{'_id':0}).to_list(500):
        member=await db.members.find_one({'user_id':progress['user_id']},{'_id':0}) or {}
        if 'board_fundraising_game' not in member.get('entitlements',[]): continue
        for attempt in (1,2):
            record=await db.workflow_email_deliveries.find_one({'user_id':member['user_id'],'event_key':f'resume:{progress["stage"]}:{attempt}'},{'_id':0})
            if record and record.get('status') in ('sent','captured'): continue
            if attempt==2:
                first=await db.workflow_email_deliveries.find_one({'user_id':member['user_id'],'event_key':f'resume:{progress["stage"]}:1'},{'_id':0}) or {}
                if first.get('updated_at','')>(datetime.now(timezone.utc)-timedelta(days=3)).isoformat():break
                if progress['updated_at']>(datetime.now(timezone.utc)-timedelta(days=4)).isoformat():break
            # Authentication is required; the next path resumes saved state.
            link=origin()+'/login?next='+quote(progress['path'],safe='')
            await deliver_once(db,member['user_id'],f'resume:{progress["stage"]}:{attempt}',member['email'],'Continue Your Fundraising Game','Your progress is saved. Sign in to continue from where you stopped.',link)
            break

    # Participants resume their own personal form; responses never appear in email.
    drafts=await db.game_audience_responses.find({'workflow_version':7,'completed':False,'updated_at':{'$lte':stale}},{'_id':0}).to_list(1000)
    for draft in drafts:
        person=await db.game_board_members.find_one({'member_id':draft['board_member_id'],'removed':{'$ne':True},'is_primary':{'$ne':True}},{'_id':0})
        if not person or not person.get('invited_at'):continue
        for attempt in (1,2):
            key='participant-resume:'+person['member_id']+':'+str(attempt)
            sent=await db.workflow_email_deliveries.find_one({'user_id':person['user_id'],'event_key':key},{'_id':0}) or {}
            if sent.get('status') in ('sent','captured'):continue
            if attempt==2:
                first=await db.workflow_email_deliveries.find_one({'user_id':person['user_id'],'event_key':'participant-resume:'+person['member_id']+':1'},{'_id':0}) or {}
                if first.get('updated_at','')>(datetime.now(timezone.utc)-timedelta(days=3)).isoformat():break
                if draft['updated_at']>(datetime.now(timezone.utc)-timedelta(days=4)).isoformat():break
            await deliver_once(db,person['user_id'],key,person['email'],'Continue Your Fundraising Ideas','Your answers are saved. You can return to your personal questionnaire and continue where you stopped.',origin()+'/play/'+person['token'])
            break
    # Retry only stable transactional notices. Marketing retries still pass the
    # consent, unsubscribe and purchase checks above; portfolios require approval.
    failures=await db.workflow_email_deliveries.find({'status':'failed','event_key':{'$regex':'^(launch-welcome:|help:|meeting-strategy-ready:)'}},{'_id':0}).to_list(200)
    for row in failures:
        await deliver_once(db,row['user_id'],row['event_key'],row['recipient'],row['subject'],row['text'],row['link'])

async def recovery_loop(db):
    while True:
        try: await send_due(db)
        except Exception: logger.exception('Fundraising follow-up processing failed')
        await asyncio.sleep(300)


def create_fundraising_launch_router(db):
    router=APIRouter(prefix='/api')
    async def owner(request):
        member=await authenticate_member(request,db);require_entitlement(member,{'board_fundraising_game'})
        return member
    async def profile(member):
        return await db.game_profiles.find_one({'user_id':member['user_id']},{'_id':0}) or {}
    async def admin(request, action, target=''):
        actor=await authenticate_admin(request,db)
        await db.admin_access_audit.insert_one({'actor':actor['user_id'],'action':action,'target':target,'created_at':now()})
        return actor

    @router.get('/fundraising/content')
    async def site_content(): return {'content':await content(db),'price':497,'currency':'usd'}

    @router.post('/fundraising/leads',status_code=201)
    async def capture(payload:Lead,request:Request):
        test_member=None
        if request.headers.get("Authorization"):
            try:candidate=await authenticate_member(request,db)
            except HTTPException:candidate={}  # Contact capture itself is public; only verified test identities gain a simulation scope.
            if candidate.get("internal_dashboard_preview"):test_member=candidate
        # Returning bearer token permits updating this one lead, never another's.
        lead=await db.funnel_leads.find_one({'result_token':payload.resume_token,'lead_source':SOURCE},{'_id':0}) if payload.resume_token else None
        if lead and (lead['email'].lower()!=str(payload.email).lower() or bool(lead.get('internal_preview'))!=bool(test_member) or (test_member and lead.get('test_user_id')!=test_member['user_id'])): lead=None
        if not lead:
            lead={'lead_id':secrets.token_urlsafe(24),'result_token':secrets.token_urlsafe(32),'lead_source':SOURCE,'offer_source':'board_fundraising_game',
                  'created_at':now(),'unsubscribe_token':secrets.token_urlsafe(32),'visitor_id':payload.visitor_id,'stage':'contact'}
            capture_key=digest((test_member['user_id'] if test_member else '')+payload.visitor_id+str(payload.email).lower())
            lead['capture_key']=capture_key
            await db.funnel_leads.update_one({'capture_key':capture_key,'lead_source':SOURCE},{'$setOnInsert':lead.copy()},upsert=True)
            lead=await db.funnel_leads.find_one({'capture_key':capture_key,'lead_source':SOURCE},{'_id':0})
        await db.funnel_leads.update_one({'lead_id':lead['lead_id']},{'$set':{'name':payload.name.strip(),'email':str(payload.email).lower(),'organization':payload.organization.strip(),
            'marketing_consent':payload.marketing_consent,'consent_recorded_at':now(),'updated_at':now()}})
        if test_member:
            await db.funnel_leads.update_one({'lead_id':lead['lead_id']},{'$set':{'internal_preview':True,'test_user_id':test_member['user_id']}})
        await event(db,payload.visitor_id,'contact',lead['lead_id'])
        return {'token':lead['result_token'],'lead_id':lead['lead_id'],'next':'/how-the-fundraising-game-works?lead='+lead['result_token']}

    @router.get('/fundraising/leads/{token}')
    async def lead_context(token:str):
        lead=await db.funnel_leads.find_one({'result_token':token,'lead_source':SOURCE},{'_id':0})
        if not lead: raise HTTPException(404,'This saved introduction is not available')
        return {k:lead.get(k,'') for k in ('name','email','organization','lead_id','paid_at','stage')}

    @router.post('/fundraising/events')
    async def record_event(payload:dict):
        visitor=str(payload.get('visitor_id',''))
        if not 12<=len(visitor)<=100: raise HTTPException(422,'Invalid visitor identifier')
        lead=await db.funnel_leads.find_one({'result_token':payload.get('lead_token',''),'lead_source':SOURCE},{'_id':0})
        kind=payload.get('kind');await event(db,visitor,kind,lead['lead_id'] if lead else '')
        if lead and kind=='page_two':await db.funnel_leads.update_one({'lead_id':lead['lead_id']},{'$set':{'page_two_at':now()}})
        return {'saved':True}

    @router.get('/fundraising/return/{token}')
    async def return_lead(token:str,email:int=0):
        lead=await db.funnel_leads.find_one({'result_token':token,'lead_source':SOURCE},{'_id':0})
        if not lead: raise HTTPException(404,'This link is not available')
        await db.fundraising_followup_clicks.insert_one({'lead_id':lead['lead_id'],'sequence_email':email,'created_at':now()})
        await db.funnel_leads.update_one({'lead_id':lead['lead_id']},{'$set':{'last_followup_email':email,'last_followup_click_at':now()}})
        return RedirectResponse(origin()+'/how-the-fundraising-game-works?lead='+token,status_code=303)

    @router.get('/fundraising/unsubscribe/{token}')
    @router.post('/fundraising/unsubscribe/{token}')
    async def unsubscribe(token:str):
        source=await db.funnel_leads.find_one({'unsubscribe_token':token,'lead_source':SOURCE},{'_id':0})
        if not source:raise HTTPException(404,'This unsubscribe link is not available')
        result=await db.funnel_leads.update_many({'email':source['email'],'lead_source':SOURCE},{'$set':{'unsubscribed':True,'marketing_consent':False,'unsubscribed_at':now()}})
        if not result.matched_count: raise HTTPException(404,'This unsubscribe link is not available')
        return Response('You have unsubscribed from Fundraising Game promotional follow-ups. Necessary account messages are unaffected.',media_type='text/plain')

    @router.get('/game/launch/state')
    async def state(request:Request):
        member=await owner(request);p=await profile(member)
        people=await db.game_board_members.find({'user_id':member['user_id'],'removed':{'$ne':True}},{'_id':0}).to_list(300)
        leader=next((x for x in people if x.get('is_primary')),None)
        response=await db.game_audience_responses.find_one({'board_member_id':leader['member_id']},{'_id':0}) if leader else None
        night=await db.game_nights.find_one({'user_id':member['user_id']},{'_id':0}) or {}
        strategy=await db.game_strategies.find_one({'user_id':member['user_id'],'status':'adopted'},{'_id':0},sort=[('adopted_at',-1)])
        draft=await db.game_setup_drafts.find_one({'user_id':member['user_id']},{'_id':0}) or {}
        return {'draft':draft,'profile':p,'leader':leader,'response':response,'night':night,'people':people,'strategy':strategy,'configuration_version':7,'internal_test':bool(member.get('internal_dashboard_preview'))}

    @router.put('/game/launch/draft')
    async def setup_draft(payload:dict,request:Request):
        member=await owner(request);p=await profile(member)
        if p.get('workflow_version')!=7:raise HTTPException(409,'Use your saved game format')
        stage=payload.get('stage');values=payload.get('values') or {}
        allowed={'organization':{'fundraising_goal','mission','annual_budget','website','community'},'meeting':{'meeting_date','start_time','timezone_name','meeting_format','meeting_link','meeting_location'}}
        if stage not in allowed or not isinstance(values,dict):raise HTTPException(422,'Unknown setup stage')
        if stage=='organization' and p.get('profile_completed'):return {'saved':True,'completed':True}
        if len(json.dumps(values))>30000:raise HTTPException(422,'Keep the saved setup within its size limit')
        clean={k:v for k,v in values.items() if k in allowed[stage] and isinstance(v,(str,int,float))}
        await db.game_setup_drafts.update_one({'user_id':member['user_id']},{'$set':{stage:clean,'updated_at':now()},'$setOnInsert':{'user_id':member['user_id']}},upsert=True)
        await touch(db,member['user_id'],stage,'/game/setup')
        return {'saved':True}

    @router.put('/game/launch/organization')
    async def save_organization(payload:Organization,request:Request):
        member=await owner(request);p=await profile(member)
        if p.get('workflow_version')!=7: raise HTTPException(409,'Continue your saved game in its existing format')
        await db.game_profiles.update_one({'user_id':member['user_id']},{'$set':{'organization.mission':payload.mission,'organization.annual_budget':payload.annual_budget,
            'organization.website':payload.website,'organization.beneficiaries':payload.community,'goal':{'amount':payload.fundraising_goal,'purpose':'Reach our organization’s fundraising goal'},'profile_completed':True,'updated_at':now()}})
        await touch(db,member['user_id'],'questions','/game/setup')
        return {'saved':True}

    @router.post('/game/launch/progress')
    async def save_progress(payload:dict,request:Request):
        member=await owner(request)
        stage=payload.get('stage')
        paths={'organization':'/game/setup','questions':'/game/setup','meeting':'/game/setup','invitations':'/game/setup','workspace':'/game/dashboard','complete':'/game/dashboard'}
        if stage not in paths: raise HTTPException(422,'Unknown stage')
        await touch(db,member['user_id'],stage,paths[stage]);return {'saved':True}

    @router.post('/game/launch/help',status_code=201)
    async def help_request(payload:dict,request:Request):
        member=await owner(request);text=str(payload.get('message','')).strip()
        if not 5<=len(text)<=10000:raise HTTPException(422,'Describe where you need help')
        ident=secrets.token_urlsafe(24)
        row={'request_id':ident,'user_id':member['user_id'],'customer_email':member['email'],'message':text,'status':'open','created_at':now()}
        await db.help_requests.insert_one(row.copy())
        result=await deliver_once(db,member['user_id'],'help:'+ident,os.environ.get('OWNER_NOTIFICATION_EMAIL','rooney@nonprofitboardbuilder.com'),'Fundraising Game Assistance Requested','A customer has asked for help. Open the administrator view to read and follow up.',origin()+'/admin?tab=help')
        return {'saved':True,'notification_status':result['status']}

    @router.put('/game/launch/branding')
    async def branding(payload:dict,request:Request):
        member=await owner(request)
        colors={k:str(payload.get(k,'')).strip() for k in ('primary_color','secondary_color')}
        if any(v and not re.fullmatch(r'#[0-9a-fA-F]{6}',v) for v in colors.values()):raise HTTPException(422,'Choose valid brand colors')
        await db.game_profiles.update_one({'user_id':member['user_id']},{'$set':{**{'branding.'+k:v for k,v in colors.items()},'updated_at':now()}})
        return {'branding':colors}

    @router.post('/game/launch/roles')
    async def confirm_role(payload:dict,request:Request):
        member=await owner(request)
        person=await db.game_board_members.find_one({'user_id':member['user_id'],'member_id':payload.get('member_id'),'removed':{'$ne':True}},{'_id':0})
        strategy=await db.game_strategies.find_one({'user_id':member['user_id'],'schema_version':7,'status':'adopted'},{'_id':0})
        if not person or not strategy:raise HTTPException(409,'Complete the meeting and choose a participating board member first')
        role=str(payload.get('role','')).strip()
        if not role or len(role)>12000 or payload.get('confirmed') is not True:raise HTTPException(422,'Record the role this person explicitly agreed to undertake')
        await db.game_board_members.update_one({'member_id':person['member_id']},{'$set':{'launch_role':role,'launch_role_confirmed':True,'launch_role_confirmed_at':now()}})
        existing=await db.board_portfolios.find_one({'user_id':member['user_id'],'board_member_id':person['member_id']},{'_id':0})
        if existing and existing.get('agreed_role')!=role:
            await db.board_portfolios.update_one({'portfolio_id':existing['portfolio_id']},{'$set':{'leader_approved_at':'','status':'draft','role_changed':True}})
        return {'confirmed':True}

    @router.get('/game/launch/portfolios')
    async def launch_portfolios(request:Request):
        member=await owner(request)
        rows=await db.board_portfolios.find({'user_id':member['user_id'],'workflow_version':7},{'_id':0}).to_list(300)
        return {'portfolios':rows}

    @router.put('/game/launch/portfolios/{portfolio_id}')
    async def edit_launch_portfolio(portfolio_id:str,payload:dict,request:Request):
        member=await owner(request)
        row=await db.board_portfolios.find_one({'user_id':member['user_id'],'portfolio_id':portfolio_id,'workflow_version':7},{'_id':0})
        if not row:raise HTTPException(404,'Portfolio not found')
        if row.get('leader_approved_at'):raise HTTPException(409,'The approved portfolio is saved. Reopen it explicitly before making changes.')
        text=str(payload.get('text','')).strip()
        if not text or len(text)>100000:raise HTTPException(422,'Keep a complete portfolio within the document limit')
        result=await db.board_portfolios.update_one({'portfolio_id':portfolio_id,'leader_approved_at':{'$in':['',None]}},{'$set':{'portfolio_text':text,'status':'draft','updated_at':now()},'$inc':{'version':1}})
        if not result.modified_count:raise HTTPException(409,'This portfolio changed. Reload before editing again.')
        return {'saved':True}

    @router.post('/game/launch/portfolios/{portfolio_id}/approve')
    async def approve_launch_portfolio(portfolio_id:str,payload:dict,request:Request):
        member=await owner(request)
        row=await db.board_portfolios.find_one({'user_id':member['user_id'],'portfolio_id':portfolio_id,'workflow_version':7},{'_id':0})
        if not row:raise HTTPException(404,'Portfolio not found')
        person=await db.game_board_members.find_one({'user_id':member['user_id'],'member_id':row['board_member_id']},{'_id':0}) or {}
        if not person.get('launch_role_confirmed') or person.get('launch_role')!=row.get('agreed_role') or row.get('role_changed'):raise HTTPException(409,'Generate the portfolio from the currently confirmed role first')
        if payload.get('confirmed') is not True or payload.get('version')!=row['version']:raise HTTPException(409,'Review and approve the current portfolio version')
        result=await db.board_portfolios.update_one({'portfolio_id':portfolio_id,'version':row['version']},{'$set':{'leader_approved_at':now(),'leader_approved_version':row['version'],'leader_approved_text':row['portfolio_text'],'status':'ready_to_send'}})
        if not result.matched_count:raise HTTPException(409,'This portfolio changed. Review the current version before approval.')
        return {'approved':True}

    @router.post('/game/launch/portfolios/{portfolio_id}/reopen')
    async def reopen_portfolio(portfolio_id:str,payload:dict,request:Request):
        member=await owner(request)
        if payload.get('confirmed') is not True:raise HTTPException(422,'Confirm that you want to revise the portfolio')
        result=await db.board_portfolios.update_one({'user_id':member['user_id'],'portfolio_id':portfolio_id,'workflow_version':7},{'$set':{'leader_approved_at':'','status':'draft'},'$inc':{'version':1}})
        if not result.matched_count:raise HTTPException(404,'Portfolio not found')
        return {'reopened':True}

    @router.get('/board-portfolio/{token}/document.pdf')
    async def portfolio_document(token:str):
        row=await db.board_portfolios.find_one({'token':token,'workflow_version':7},{'_id':0})
        if not row or not row.get('leader_approved_at'):raise HTTPException(404,'This approved portfolio is not available')
        p=await db.game_profiles.find_one({'user_id':row['user_id']},{'_id':0}) or {}
        return Response(render_document_pdf(title='Board Fundraising Portfolio',org_name=(p.get('organization') or {}).get('name',''),body_text=row['leader_approved_text'],branding=p.get('branding') or {},prepared_for=row['member_name']),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="board-fundraising-portfolio.pdf"'})

    @router.post('/game/launch/test-participants')
    async def sample_participants(payload:dict,request:Request):
        member=await owner(request)
        p=await profile(member)
        if not member.get('internal_dashboard_preview') or p.get('workflow_version')!=7:raise HTTPException(403,'This control is only available inside your isolated admin simulation')
        import fundraising_audiences as questions
        rows=[]
        for index,name in enumerate(('Alex Morgan','Taylor Reed','Jordan Ellis')):
            ident='launch-sample-'+digest(member['user_id']+str(index))[:24]
            row={'member_id':ident,'user_id':member['user_id'],'full_name':name,'email':ident+'@nonprofitboardbuilder.internal','board_title':'Board Member','game_version':7,'total_sections':6,'participant_role':'board_member','token':secrets.token_urlsafe(32),'invitation_status':'not_invited','invited_at':'','last_reminder_at':'','internal_preview':True,'removed':False,'created_at':now(),'updated_at':now()}
            await db.game_board_members.update_one({'member_id':ident},{'$setOnInsert':row},upsert=True)
            row=await db.game_board_members.find_one({'member_id':ident},{'_id':0})
            if payload.get('prefill') is True:
                fields={'who_why':name+' suggests former mentors who care about youth employment.','where':'Community and professional networks.','attraction':'Share the approved programme outcomes.','process':'Ask for an introduction, listen to their interests and invite suitable support.','ask':'Support mentoring places at $500 each.'}
                config=questions.configuration(7)
                bucket={'id':'sample-'+str(index),**{q['key']:fields.get(q['key'],'A sample response to '+q['prompt']) for q in config['questions']['individuals']}}
                value=questions.clean_response({'workflow_version':7,'audiences':{'individuals':[bucket]},'category_status':{cat:'complete' for cat in config['categories']},'involvement':name+' would like to introduce interested employers.'},submitting=True,version=7)
                await db.game_audience_responses.update_one({'board_member_id':ident},{'$setOnInsert':{**value,'board_member_id':ident,'user_id':member['user_id'],'response_id':secrets.token_hex(16),'completed':True,'created_at':now(),'updated_at':now(),'completed_at':now()}},upsert=True)
            rows.append({'name':name,'url':'/play/'+row['token'],'member_id':ident})
        return {'participants':rows,'prefilled':payload.get('prefill') is True}

    @router.post('/admin/fundraising/test-start')
    async def fresh_test(request:Request):
        actor=await admin(request,'start-current-fundraising-test')
        from member_auth import create_member_token
        user='admin-dashboard-preview-launch-'+secrets.token_hex(12)
        row={'user_id':user,'email':user+'@nonprofitboardbuilder.internal','first_name':'Sample','last_name':'Leader','entitlements':[],
             'account_status':'active','internal_client_test':True,'internal_dashboard_preview':True,'created_at':now()}
        await db.members.insert_one(row.copy())
        return {'token':create_member_token(user,row['email']),'member':row,'url':'/','workflow_version':7}

    @router.get('/admin/fundraising/content')
    async def admin_content(request:Request):await admin(request,'read-content');return {'content':await content(db)}

    @router.put('/admin/fundraising/content')
    async def save_content(payload:dict,request:Request):
        await admin(request,'edit-content')
        if len(json.dumps(payload))>200000:raise HTTPException(422,'Keep the content within the editor limit')
        def validate(template,value):
            if isinstance(template,str):return isinstance(value,str) and len(value)<=20000
            if isinstance(template,list):return isinstance(value,list) and len(value)<=100 and all(validate(template[0],v) for v in value)
            if isinstance(template,dict):return isinstance(value,dict) and set(value)==set(template) and all(validate(v,value[k]) for k,v in template.items())
            return isinstance(value,type(template))
        if not validate(DEFAULT,payload) or len(payload['how']['steps'])!=5 or len(payload['followups'])!=5:raise HTTPException(422,'Preserve the page fields, five steps and five follow-up emails')
        for i,row in enumerate(payload['followups'],1):row['day']=i*3
        await db.site_content.update_one({'key':SOURCE},{'$set':{'content':payload,'updated_at':now()}},upsert=True)
        return {'saved':True,'content':await content(db)}

    @router.get('/admin/fundraising/overview')
    async def overview(request:Request,start:str='',end:str=''):
        await admin(request,'read-overview')
        bounds={}
        if start: bounds['$gte']=datetime.fromisoformat(start).replace(tzinfo=timezone.utc).isoformat()
        if end: bounds['$lt']=(datetime.fromisoformat(end).replace(tzinfo=timezone.utc)+timedelta(days=1)).isoformat()
        query={'lead_source':SOURCE,**({'created_at':bounds} if bounds else {})}
        leads=await db.funnel_leads.find(query,{'_id':0,'result_token':0,'unsubscribe_token':0}).sort('created_at',-1).to_list(5000)
        # Verified payment state, including buyers who have not claimed accounts yet.
        paid_ids={x.get('lead_id') for x in await db.payment_transactions.find({'payment_status':'paid','launch_lead_token':{'$exists':True}},{'_id':0,'lead_id':1}).to_list(10000)}
        for lead in leads:
            lead['paid']=bool(lead.get('paid_at') or lead['lead_id'] in paid_ids)
            lead['followup_delivery']=await db.workflow_email_deliveries.find({'user_id':'launch-sequence:'+digest(lead['email'].lower())},{'_id':0,'event_key':1,'status':1,'updated_at':1,'provider_id':1}).to_list(5)
            lead['followup_clicks']=await db.fundraising_followup_clicks.count_documents({'lead_id':lead['lead_id']})
        events=await db.funnel_events.find({'source':SOURCE,**({'created_at':bounds} if bounds else {})},{'_id':0}).to_list(50000)
        visitors={x['visitor_id'] for x in events if x['kind']=='homepage'}
        counts={'unique_homepage_visitors':len(visitors),'identified_leads':len(leads),'page_two':sum(bool(x.get('page_two_at')) for x in leads),'checkout_started':sum(bool(x.get('checkout_started_at')) for x in leads),'paid':sum(x['paid'] for x in leads)}
        counts['dropoffs']=len(leads)-counts['paid']
        counts['homepage_page_views']=sum(x.get('views',1) for x in events if x['kind']=='homepage')
        conversions={'visitor_to_lead':round(100*len(leads)/len(visitors),1) if visitors else 0,'lead_to_paid':round(100*counts['paid']/len(leads),1) if leads else 0}
        conversions.update(homepage_to_page_two=round(100*counts['page_two']/len(visitors),1) if visitors else 0,page_two_to_checkout=round(100*counts['checkout_started']/counts['page_two'],1) if counts['page_two'] else 0,checkout_to_paid=round(100*counts['paid']/counts['checkout_started'],1) if counts['checkout_started'] else 0,lead_dropoff=round(100*counts['dropoffs']/len(leads),1) if leads else 0)
        customers=await db.purchases.find({'entitlement':'board_fundraising_game'},{'_id':0}).sort('created_at',-1).to_list(5000)
        ids=[x['user_id'] for x in customers]
        profiles={x['user_id']:x for x in await db.game_profiles.find({'user_id':{'$in':ids}},{'_id':0}).to_list(5000)}
        members={x['user_id']:x for x in await db.members.find({'user_id':{'$in':ids}},{'_id':0,'email':1,'first_name':1,'last_name':1,'user_id':1}).to_list(5000)}
        for row in customers:
            row['organization_name']=(profiles.get(row['user_id'],{}).get('organization') or {}).get('name','')
            person=members.get(row['user_id'],{})
            row['customer_name']=(person.get('first_name','')+' '+person.get('last_name','')).strip();row['customer_email']=person.get('email','')
        help_rows=await db.help_requests.find({'status':'open'},{'_id':0}).sort('created_at',-1).to_list(500)
        strategies=await db.game_strategies.find({'status':'adopted'},{'_id':0,'strategy_id':1,'user_id':1,'adopted_at':1,'document_text':1}).sort('adopted_at',-1).to_list(1000)
        return {'counts':counts,'conversions':conversions,'leads':leads,'customers':customers,'help_requests':help_rows,'strategies':strategies}

    @router.get('/admin/fundraising/strategies/{strategy_id}/document.pdf')
    async def download_strategy(strategy_id:str,request:Request):
        await admin(request,'export-final-strategy',strategy_id)
        strategy=await db.game_strategies.find_one({'strategy_id':strategy_id,'status':'adopted'},{'_id':0})
        if not strategy:raise HTTPException(404,'Adopted strategy not found')
        p=await db.game_profiles.find_one({'user_id':strategy['user_id']},{'_id':0}) or {}
        from strategy_pdf import build_strategy_pdf
        strategy['branding']=p.get('branding') or {}
        return Response(build_strategy_pdf(strategy,(p.get('organization') or {}).get('name','')),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="adopted-fundraising-strategy.pdf"'})

    @router.get('/admin/fundraising/customer/{user_id}')
    async def inspect_customer(user_id:str,request:Request):
        await admin(request,'inspect-customer',user_id)
        customer=await db.members.find_one({'user_id':user_id},{'_id':0,'password_hash':0})
        if not customer:raise HTTPException(404,'Customer not found')
        records={}
        for name in ('game_profiles','game_board_members','game_audience_responses','game_nights','group_game_sessions','game_strategies','board_portfolios'):
            records[name]=await db[name].find({'user_id':user_id},{'_id':0}).to_list(1000)
        return {'customer':customer,'workspace':records}

    @router.get('/admin/fundraising/legacy-planning')
    async def legacy(request:Request,search:str='For All the Children'):
        await admin(request,'search-legacy-planning',search)
        pattern=re.escape(search[:200]);rows=await db.sp_projects.find({'$or':[{'organization_name':{'$regex':pattern,'$options':'i'}},{'founder_name':{'$regex':pattern,'$options':'i'}}]},{'_id':0}).to_list(200)
        return {'projects':rows}

    @router.get('/admin/fundraising/legacy-planning/{project_id}/founder.pdf')
    async def original_founder(project_id:str,request:Request):
        await admin(request,'export-original-founder',project_id)
        project=await db.sp_projects.find_one({'project_id':project_id},{'_id':0})
        if not project:raise HTTPException(404,'Project not found')
        person=await db.sp_participants.find_one({'project_id':project_id,'$or':[{'is_founder':True},{'is_primary':True},{'email':project.get('founder_email','')}]},{'_id':0},sort=[('created_at',1)])
        if not person:raise HTTPException(404,'No saved founder submission was found. No replacement or summary has been generated.')
        answers=person.get('original_response') or person.get('submitted_response') or person.get('response') or {}
        if not answers:raise HTTPException(404,'The founder has no stored responses to export')
        form=await db.sp_forms.find_one({'project_id':project_id},{'_id':0}) or {}
        form_content=next((v['content'] for v in form.get('approved_versions',[]) if v.get('version')==person.get('form_version')),form.get('content') or {})
        labels={q.get('id'):q.get('prompt') for sec in form_content.get('sections',[]) for q in sec.get('questions',[])}
        labels.update({q['id']:q['prompt'] for q in person.get('response_questions',[]) if q.get('id') and q.get('prompt')})
        text='\n\n'.join((labels.get(k) or k)+'\n'+(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False)) for k,v in answers.items())
        return Response(render_document_pdf(title='Founder Strategic Planning Submission',org_name=project['organization_name'],body_text=text,prepared_for=person.get('name',project.get('founder_name','')),preserve_source_text=True),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="founder-original-submission.pdf"','X-Submission-Source':'original-response' if person.get('original_response') else 'stored-founder-response'})
    return router


def portfolio_tools(name, role, organization):
    """Practical, editable worksheets for the accepted role, without new duties."""
    org=organization.get('name') or 'our organization'
    tools=[{'name':'Your Agreed Action Worksheet','text':
        'Board member: '+name+'\nAgreed responsibility: '+role+
        '\nApproved audience or activity this supports: ____________________'
        '\nFirst action within this responsibility: ____________________'
        '\nInformation or permission needed from the organization: ____________________'
        '\nTiming agreed with the lead user: ____________________'
        '\nHow I will report back: ____________________'},
        {'name':'Progress Update You Can Adapt','text':
        'Hello,\n\nHere is my update on the responsibility I accepted: '+role+
        '\n\nI have completed: ____________________'
        '\nMy next agreed action is: ____________________'
        '\nI need your guidance or approval on: ____________________'
        '\n\n'+name}]
    lower=role.lower()
    if any(word in lower for word in ('introduc','outreach','contact','relationship','invite','donor','prospect','funder','grant')):
        tools.append({'name':'Contact and Handoff Record','text':
            'Use this only for contacts relevant to your accepted responsibility. Do not add private contact information without appropriate permission.'
            '\nPerson or organization: ____________________'
            '\nConnection to the approved audience and mission: ____________________'
            '\nExisting relationship and permission to make contact: ____________________'
            '\nRelevant approved approach: ____________________'
            '\nLast conversation and agreed next step: ____________________'
            '\nWho needs the handoff: ____________________'})
    if 'introduc' in lower:
        tools.append({'name':'Warm Introduction Message','text':
            'Subject: An introduction to '+org+
            '\n\nHello [contact name],\n\nI would like to introduce you to [lead user name] at '+org+
            '. Their mission is: '+(organization.get('mission') or '[insert the approved mission]')+
            '\n\nI thought a conversation could be relevant because [explain the actual connection to the approved audience]. Would you be comfortable with me making an introduction?'
            '\n\nThank you,\n'+name+
            '\n\nConfirm permission before sharing contact details. Add only facts you know and use the approach your board approved.'})
    if any(word in lower for word in ('grant','research','identify','prospect')):
        tools.append({'name':'Opportunity Fit Worksheet','text':
            'Opportunity: ____________________'
            '\nWhich approved audience does it fit? ____________________'
            '\nEvidence of mission and community alignment: ____________________'
            '\nKnown eligibility, restrictions and deadline: ____________________'
            '\nApproved funding request it could support: ____________________'
            '\nQuestions still requiring confirmation: ____________________'
            '\nRecommendation for the lead user to review: ____________________'})
    return tools


async def build_portfolio_draft(db,user_id,record,strategy):
    """Use confirmed responsibilities and approved content; no AI assignments."""
    if not record.get('launch_role_confirmed'):raise HTTPException(409,'Confirm this board member’s agreed role before generating a portfolio')
    role=record.get('launch_role','')
    response=await db.game_audience_responses.find_one({'user_id':user_id,'board_member_id':record['member_id'],'completed':True},{'_id':0}) or {}
    profile=await db.game_profiles.find_one({'user_id':user_id},{'_id':0}) or {}
    tools=portfolio_tools(record['full_name'],role,profile.get('organization') or {})
    context='\n\n'.join(s['title']+'\n'+s['text'] for s in strategy.get('document_sections',[]) if s['key'].startswith('audience_'))
    text=record['full_name']+'\n\nYOUR AGREED FUNDRAISING RESPONSIBILITY\n'+role+'\n\nYOUR ORIGINAL PARTICIPATION IDEAS\n'+(response.get('involvement') or 'No personal participation statement was submitted.')+'\n\nTHE BOARD’S ADOPTED FUNDRAISING APPROACHES\n'+context+'\n\nUSING YOUR PORTFOLIO\nUse your agreed responsibility above to guide your contribution. The approaches in this document are the ones your board adopted. Confirm any wording, contact details, timing or expenditure with your organization before communicating externally. If circumstances change, discuss the change with your lead user rather than assuming a different responsibility.'
    text+='\n\nPRACTICAL RESOURCES FOR YOUR AGREED ROLE\n\n'+'\n\n'.join(tool['name']+'\n'+tool['text'] for tool in tools)
    return {'portfolio_id':secrets.token_urlsafe(24),'user_id':user_id,'board_member_id':record['member_id'],'member_name':record['full_name'],'member_email':record.get('email',''),
        'strategy_id':strategy['strategy_id'],'token':secrets.token_urlsafe(32),'workflow_version':7,'status':'draft','version':1,'approved_version':0,'leader_approved_at':'',
        'agreed_role':role,'portfolio_text':text,'practical_resources':tools,'original_participation':response.get('involvement',''),'system_roles':[{'item_id':secrets.token_hex(12),'role_key':'custom','label':role,'source':'meeting_commitment','commitment':role,'requires_confirmation':False,'active':True}],
        'direct_activities':[],'additional_commitments':[],'do_not_want':[],'availability':'','org_note':'','change_request':'','sent_at':'','approved_at':'','approved_snapshot':None,'created_at':now(),'updated_at':now()}
