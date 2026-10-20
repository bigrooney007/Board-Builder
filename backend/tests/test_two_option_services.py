"""Two package purchase, retained setup, dashboard ownership and resource isolation."""
import os
import secrets
import unittest
import uuid
from datetime import datetime,timedelta,timezone
from http.cookies import SimpleCookie

import test_guided_services as shared
from guided_service_defaults import PACKAGES,package
import guided_services as gs


class PackageContract(unittest.TestCase):
    def test_four_distinct_server_verified_products(self):
        self.assertEqual([p['amount'] for p in PACKAGES['board-fundraising'].values()],[49700,149700])
        self.assertEqual([p['amount'] for p in PACKAGES['strategic-planning'].values()],[49700,199700])
        self.assertEqual(len({p['product'] for choices in PACKAGES.values() for p in choices.values()}),4)
        with self.assertRaises(ValueError):package('board-fundraising','client-supplied-cheap-price')


@unittest.skipUnless(os.environ.get('RECOVERY_ACCEPTANCE')=='1','Requires disposable Mongo and controlled providers')
class TwoOptionHTTP(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=shared.GuidedHTTP.asyncSetUp
    asyncTearDown=shared.GuidedHTTP.asyncTearDown
    req=shared.GuidedHTTP.req
    lead=shared.GuidedHTTP.lead
    paid=shared.GuidedHTTP.paid

    async def paid_option(self,service,choice='self-facilitated'):
        token,base,row=await self.lead(service)
        await self.req('POST',base+'/checkout?package='+choice)
        row=await self.db.guided_service_customers.find_one({'customer_id':row['customer_id']},{'_id':0})
        self.sessions[row['session_id']].update(payment_status='paid',status='complete')
        await self.req('POST',base+'/confirm',{})
        await self.req('PUT',base+'/branding',{'primary_color':'#123456'})
        row=await self.db.guided_service_customers.find_one({'customer_id':row['customer_id']},{'_id':0})
        return token,base,row

    async def handover(self,row):
        base='/admin/services/'+row['service']+'/customers/'+row['customer_id']
        invitation=await self.req('POST',base+'/handover',{'prepared_confirmed':True},admin=True)
        token=invitation['url'].split('/')[-1]
        response=await self.client.post('/api/services/'+row['service']+'/handover/'+token,json={'confirmed':True})
        self.assertEqual(response.status_code,200,response.text)
        cookie=SimpleCookie();cookie.load(response.headers['set-cookie'])
        return invitation,{'Cookie':'guided_operator_session='+cookie['guided_operator_session'].value}

    async def test_free_fundraising_saves_six_questions_and_stops_before_payment(self):
        token,base,row=await self.lead('board-fundraising')
        self.assertEqual(len(row['question_snapshot']),6)
        self.assertEqual(row['answers']['next_board_meeting']['timezone'],'Europe/London')
        self.assertEqual(row['payment_status'],'unpaid');self.assertFalse(self.created)
        self.assertEqual(await self.db.game_profiles.count_documents({}),0)
        await self.req('GET',base+'/fundraising',status=402)
        await self.req('GET',base+'/book',status=402)

    async def test_both_services_both_packages_stripe_amount_sku_and_branding_booking(self):
        for service,choices in PACKAGES.items():
            for key,option in choices.items():
                token,base,row=await self.paid_option(service,key)
                self.assertEqual(row['amount_paid'],option['amount'])
                self.assertEqual(row['purchased_package'],key)
                self.assertEqual(self.created[-1]['metadata']['offer_source'],option['product'])
                self.assertEqual((await self.req('GET',base))['answers'],row['answers'])
                await self.req('GET',base+'/book',status=303)
                resumed=await self.req('POST',base+'/checkout?package='+key)
                self.assertIn('/setup/',resumed['resume_url'])
        self.assertEqual(len(self.created),4)

    async def test_wrong_package_amount_or_metadata_never_grants_access(self):
        token,base,row=await self.lead('board-fundraising')
        await self.req('POST',base+'/checkout?package=self-facilitated')
        row=await self.db.guided_service_customers.find_one({'customer_id':row['customer_id']})
        session=self.sessions[row['session_id']];session.update(payment_status='paid',status='complete')
        original=dict(session)
        for key,value in [('amount_subtotal',149700),('currency','eur')]:
            session.update(original);session[key]=value
            await self.req('POST',base+'/confirm',{},409)
            await self.req('PUT',base+'/branding',{'primary_color':'#123456'},402)
        session.update(original);session['metadata']={**original['metadata'],'guided_package':'rooney-facilitated'}
        await self.req('POST',base+'/confirm',{},409)

    async def test_first_email_one_hour_has_two_customer_links_and_payment_stops_both_sales_options(self):
        from unittest.mock import patch
        patch.object(gs,'origin',return_value='https://nonprofitboardbuilder.com').start()
        for service in PACKAGES:
            token,base,row=await self.lead(service)
            at=datetime.fromisoformat(row['submitted_at'])
            await gs.automation_tick(self.db,at+timedelta(minutes=59),row['customer_id'])
            self.assertIsNone(await self.db.workflow_email_deliveries.find_one({'user_id':row['workspace_user_id']}))
            for _ in range(2):await gs.automation_tick(self.db,at+timedelta(hours=1),row['customer_id'])
            delivery=await self.db.workflow_email_deliveries.find_one({'user_id':row['workspace_user_id'],'event_key':'guided-first-invitation'})
            self.assertEqual(delivery['recipient'],row['email']);self.assertIn(token,delivery['link']);self.assertIn('$497',delivery['text'])
            self.assertIn('package=self-facilitated',delivery['secondary_links'][0]['url']);self.assertIn('package=self-facilitated',self.mail.call_args.args[0]['html'])
            await self.req('POST',base+'/checkout?package=rooney-facilitated')
            paid=await self.db.guided_service_customers.find_one({'customer_id':row['customer_id']})
            self.sessions[paid['session_id']].update(payment_status='paid',status='complete')
            await self.req('POST',base+'/confirm',{})
            await gs.automation_tick(self.db,at+timedelta(days=40),row['customer_id'])
            self.assertEqual(await self.db.workflow_email_deliveries.count_documents({'user_id':row['workspace_user_id'],'event_key':{'$regex':'^guided-followup'}}),0)

    async def test_handover_preserves_fundraising_project_and_leader_can_run_real_tools(self):
        token,base,row=await self.paid_option('board-fundraising')
        operator='/api/services/board-fundraising/operator/'+row['customer_id']
        self.assertEqual((await self.client.get(operator)).status_code,401)
        before=await self.db.game_profiles.find_one({'user_id':row['workspace_user_id']},{'_id':0})
        invitation,headers=await self.handover(row)
        self.assertIn('48',__import__('guided_service_defaults').defaults('board-fundraising')['handover_email']['body'])
        result=await self.client.get(operator,headers=headers);self.assertEqual(result.status_code,200,result.text)
        state=await self.client.get('/api/game/launch/state',headers=headers);self.assertEqual(state.status_code,200,state.text)
        self.assertTrue(state.json()['self_facilitated']);self.assertEqual(state.json()['profile']['goal'],before['goal'])
        started=await self.client.post('/api/game/self-play',headers=headers);self.assertEqual(started.status_code,201,started.text)
        self.assertTrue(started.json()['token'])
        self.assertEqual(await self.db.game_profiles.count_documents({'user_id':row['workspace_user_id']}),1)
        support=await self.client.post(operator+'/support',headers=headers,json={'message':'Help me prepare our board meeting.'});self.assertEqual(support.status_code,201,support.text)

    async def test_planning_handover_preserves_project_and_authorizes_existing_session(self):
        token,base,row=await self.paid_option('strategic-planning')
        admin='/admin/services/strategic-planning/customers/'+row['customer_id']+'/planning'
        setup={'mission':'Our existing mission.','planning_period':'Next 24 months','planning_meeting':{'meeting_date':'2026-12-01','start_time':'16:00','timezone_name':'Europe/London'},'response_deadline':'2026-11-20','programs':[{'id':'school','name':'After-School Education'}]}
        await self.req('PUT',admin+'/setup',setup,admin=True)
        await self.req('POST',admin+'/leader-form',{},admin=True)
        invitation,headers=await self.handover(row)
        operator='/api/services/strategic-planning/operator/'+row['customer_id']+'/planning'
        result=await self.client.get(operator,headers=headers);self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['project']['programs'][0]['id'],'school');self.assertEqual(len(result.json()['participants']),1)
        session=await self.client.get('/api/guided/strategic-planning/session?session_id='+row['workspace_user_id'],headers=headers)
        self.assertEqual(session.status_code,200,session.text)
        self.assertEqual(await self.db.sp_projects.count_documents({'guided_service_customer_id':row['customer_id']}),1)

    async def test_handover_denies_professional_unprepared_expired_forged_and_revoked_access(self):
        token,base,row=await self.paid_option('board-fundraising','rooney-facilitated')
        admin='/admin/services/board-fundraising/customers/'+row['customer_id']
        await self.req('POST',admin+'/handover',{'prepared_confirmed':True},403,True)
        token,base,row=await self.paid_option('board-fundraising')
        admin='/admin/services/board-fundraising/customers/'+row['customer_id']
        await self.req('POST',admin+'/handover',{'prepared_confirmed':False},409,True)
        invitation,headers=await self.handover(row)
        bad=await self.client.post('/api/services/board-fundraising/handover/'+secrets.token_urlsafe(32),json={'confirmed':True});self.assertEqual(bad.status_code,410)
        await self.req('POST',admin+'/revoke-handover',{},admin=True)
        self.assertEqual((await self.client.get('/api/game/launch/state',headers=headers)).status_code,403)
        invitation=await self.req('POST',admin+'/handover',{'prepared_confirmed':True},admin=True)
        await self.db.guided_service_customers.update_one({'customer_id':row['customer_id']},{'$set':{'handover.expires_at':(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()}})
        self.assertEqual((await self.client.get('/api/services/board-fundraising/handover/'+invitation['url'].split('/')[-1])).status_code,410)

    async def test_operator_cannot_open_another_organization_service_or_admin_record(self):
        _,_,first=await self.paid_option('strategic-planning');invitation,headers=await self.handover(first)
        _,_,second=await self.paid_option('strategic-planning')
        self.assertEqual((await self.client.get('/api/services/strategic-planning/operator/'+second['customer_id']+'/planning',headers=headers)).status_code,403)
        self.assertEqual((await self.client.get('/api/admin/services/strategic-planning/customers/'+first['customer_id'],headers=headers)).status_code,401)
        self.assertEqual((await self.client.get('/api/game/launch/state',headers=headers)).status_code,403)
        r=await self.client.get('/api/guided/strategic-planning/session?session_id='+second['workspace_user_id'],headers=headers);self.assertEqual(r.status_code,403,r.text)

    async def test_unpaid_and_paid_video_links_remain_independent_of_followup_schedule(self):
        token,base,row=await self.lead('board-fundraising')
        admin='/admin/services/board-fundraising/customers/'+row['customer_id']
        at=datetime.fromisoformat(row['submitted_at'])+timedelta(hours=1)
        await gs.automation_tick(self.db,at,row['customer_id'])
        preview=await self.req('POST',admin+'/video-preview',{'video_url':'https://www.youtube.com/watch?v=recorded'},admin=True)
        self.assertIn('/offer/',preview['html']);self.assertIn('package=self-facilitated',preview['html'])
        await self.req('POST',admin+'/video-send',{**preview,'request_id':str(uuid.uuid4()),'approved':True},admin=True)
        saved=await self.db.guided_service_customers.find_one({'customer_id':row['customer_id']});self.assertEqual(saved['followup_index'],0)
        await self.req('POST',base+'/checkout?package=self-facilitated');saved=await self.db.guided_service_customers.find_one({'customer_id':row['customer_id']});self.sessions[saved['session_id']].update(payment_status='paid',status='complete');await self.req('POST',base+'/confirm',{})
        preview=await self.req('POST',admin+'/video-preview',{'video_url':'https://youtu.be/recorded'},admin=True);self.assertIn('/setup/',preview['html']);self.assertNotIn('/offer/',preview['html'])

    async def test_fundraising_portfolios_reuse_confirmed_roles_approval_and_pdf(self):
        token,public,row=await self.paid_option('board-fundraising','rooney-facilitated');uid=row['workspace_user_id']
        pid=str(uuid.uuid4());await self.db.game_board_members.insert_one({'member_id':pid,'user_id':uid,'full_name':'Sample Board Member','email':'board@example.org','game_version':7,'removed':False})
        await self.db.game_audience_responses.insert_one({'board_member_id':pid,'user_id':uid,'completed':True,'involvement':'I can introduce school partners.'})
        await self.db.game_strategies.insert_one({'strategy_id':'approved-strategy','user_id':uid,'schema_version':7,'status':'adopted','adopted_at':gs.now(),'document_sections':[{'key':'audience_schools','title':'School Partners','text':'Develop relationships with local school leaders.'}]})
        base='/admin/services/board-fundraising/customers/'+row['customer_id']+'/fundraising/tool/game'
        await self.req('POST',base+'/launch/roles',{'member_id':pid,'role':'Introduce interested school partners after confirming permission.','confirmed':True},admin=True)
        await self.req('POST',base+'/portfolios/prepare',{},admin=True)
        docs=await self.req('GET',base+'/launch/portfolios',admin=True);self.assertEqual(len(docs['portfolios']),1)
        portfolio=docs['portfolios'][0];self.assertIn('school partners',portfolio['portfolio_text']);self.assertEqual(portfolio['agreed_role'],'Introduce interested school partners after confirming permission.')
        await self.req('GET','/board-portfolio/'+portfolio['token']+'/document.pdf',status=404)
        await self.req('POST',base+'/launch/portfolios/'+portfolio['portfolio_id']+'/approve',{'version':portfolio['version'],'confirmed':True},admin=True)
        pdf=await self.req('GET','/board-portfolio/'+portfolio['token']+'/document.pdf');self.assertTrue(pdf.content.startswith(b'%PDF-'))
        for _ in range(2):await self.req('POST',base+'/portfolios/'+portfolio['portfolio_id']+'/send',{'origin_url':'https://nonprofitboardbuilder.com','resend':False},admin=True)
        sent=await self.db.workflow_email_deliveries.count_documents({'user_id':uid,'event_key':{'$regex':'^portfolio:'}});self.assertEqual(sent,1)

    async def test_planning_portfolios_keep_existing_template_and_require_fresh_approval_after_edit(self):
        token,public,row=await self.paid_option('strategic-planning','rooney-facilitated');ident=row['customer_id']
        base='/admin/services/strategic-planning/customers/'+ident+'/planning';pid=str(uuid.uuid4())
        await self.db.sp_participants.insert_one({'participant_id':pid,'project_id':ident,'name':'Sample Planning Member','email':'planning@example.org','role':'Board Member','status':'COMPLETED'})
        await self.db.sp_plans.insert_one({'project_id':ident,'final_status':'Approved','final_display_text':'Only the adopted planning decisions.','final_share_token':secrets.token_urlsafe(32)})
        payload={'delegates':[{'participant_id':pid,'responsibilities':['Introduce the agreed education partners.']}],'responsibilities_confirmed':True}
        data=await self.req('POST',base+'/portfolios/prepare',payload,admin=True)
        port=data['portfolios'][0];self.assertIn('YOUR DELEGATED RESPONSIBILITY',port['text']);self.assertIn('Introduce the agreed education partners.',port['text'])
        path=base+'/portfolios/'+port['delegation_id']
        await self.req('GET',path+'/download',status=403,admin=True)
        await self.req('POST',path+'/approve',{'version':port['version'],'confirmed':True},admin=True)
        approved=await self.req('GET',path+'/download',admin=True);self.assertTrue(approved.content.startswith(b'%PDF-'))
        public_path='/guided/strategic-planning/leadership-portfolio/'+port['token']
        visible=await self.req('GET',public_path);self.assertIn('Introduce the agreed education partners.',visible['display_text'])
        for _ in range(2):await self.req('POST',path+'/send',{'recipient':'member'},admin=True)
        self.assertEqual(await self.db.workflow_email_deliveries.count_documents({'user_id':row['workspace_user_id'],'event_key':{'$regex':'^planning-portfolio:'}}),1)
        edited=await self.req('PUT',path,{'version':port['version'],'text':port['text']+'\n\nOnly the confirmed partners.'},admin=True)
        await self.req('GET',public_path,status=404);await self.req('GET',path+'/download',status=403,admin=True)
        await self.req('POST',path+'/approve',{'version':port['version'],'confirmed':True},409,True)
        await self.req('POST',path+'/approve',{'version':edited['portfolio']['version'],'confirmed':True},admin=True)
