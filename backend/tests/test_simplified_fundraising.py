"""Real simplified customer handlers with disposable Mongo and substituted providers."""
import copy
import io
import os
import sys
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import AsyncMock,MagicMock,patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT))
import fundraising_audiences as audience

class Configuration(unittest.TestCase):
    def test_shared_five_questions_and_exact_personal_participation(self):
        config=audience.configuration(7)
        self.assertTrue(all(len(rows)==5 for rows in config['questions'].values()))
        self.assertEqual(config['participation_question'],'How do you see yourself participating and supporting your organization to reach this fundraising goal?')
        self.assertEqual(len(audience.configuration(6)['questions']['individuals']),6)
    def test_skips_and_complete_five_answer_audiences(self):
        value=answers();value['audiences']['businesses']=[]
        result=audience.clean_response(value,submitting=True,version=7)
        self.assertEqual(result['workflow_version'],7)
        self.assertFalse(result['audiences']['businesses'])
        self.assertEqual(result['audiences']['individuals'][0]['ask'],'Fund mentoring places, $500 each.')
    def test_board_recommendations_precede_all_leader_recommendations(self):
        leader={**answers(),'board_member_id':'lead'};guest={**answers(),'board_member_id':'guest'}
        proposals,_=audience.proposed_audiences([leader,guest],[{'member_id':'lead','full_name':'Lead','is_primary':True},{'member_id':'guest','full_name':'Guest'}])
        self.assertEqual([p['contributor'] for p in proposals],['Guest']*3+['Lead']*3)

def answers(name='Sample'):
    return {'workflow_version':7,'audiences':{cat:[{'id':name+'-'+cat,'who_why':name+' '+cat+' care about youth employment.','where':'Existing community networks.','attraction':'Show the programme outcomes.','process':'Ask for an introduction, discuss interests, then invite support.','ask':'Fund mentoring places, $500 each.'}] for cat in audience.CATEGORIES},'category_status':{cat:'complete' for cat in audience.CATEGORIES},'involvement':'I can introduce two interested employers.','progress':{'category':2,'question':4,'phase':'review','audience_index':0}}

@unittest.skipUnless(os.environ.get('RECOVERY_ACCEPTANCE')=='1','Requires disposable local Mongo and test providers')
class SimplifiedHTTP(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from tests import current_workflow_app as fixture
        from motor.motor_asyncio import AsyncIOMotorClient
        import httpx
        self.fixture=fixture;self.mongo=AsyncIOMotorClient(os.environ['MONGO_URL']);self.db=self.mongo.nbb_simplified_fundraising_unit_tests
        for name in await self.db.list_collection_names():await self.db[name].delete_many({})
        self.app=fixture.build_app(self.db)
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://test')
        await self.db.users.insert_one({'user_id':'launch-admin','email':'admin@example.org','role':'admin'})
        self.admin={'Authorization':'Bearer '+fixture.create_access_token('launch-admin','admin@example.org')};self.headers=self.admin
    async def asyncTearDown(self):await self.client.aclose();self.mongo.close()
    async def call(self,method,path,body=None,status=200,headers=None):
        r=await self.client.request(method,'/api'+path,json=body,headers=headers if headers is not None else self.headers)
        self.assertEqual(r.status_code,status,r.text[:1200])
        return r if 'application/json' not in r.headers.get('content-type','') else r.json()
    async def fresh(self):
        row=await self.call('POST','/admin/fundraising/test-start')
        self.headers={'Authorization':'Bearer '+row['token']};self.user=row['member']['user_id']
        lead=await self.call('POST','/fundraising/leads',{'name':'Sample Leader','email':'lead@example.org','organization':'BrightPath','visitor_id':'unique-browser-123456','marketing_consent':True},201)
        self.lead=lead
        result=await self.call('POST','/payments/game-checkout',{'origin_url':'http://test','result_token':lead['token']})
        self.assertTrue(result['simulated']);self.assertTrue(result['checkout_url'].endswith('/game/setup'))
        return lead
    async def setup_and_complete_leader(self):
        await self.fresh()
        await self.call('PUT','/game/night',{'meeting_date':'2026-12-01','start_time':'16:00','timezone_name':'Europe/London'},409)
        await self.call('PUT','/game/launch/organization',{'fundraising_goal':100000,'mission':'Help young people enter employment.','annual_budget':'$150,000','website':'https://example.org','community':'Young people seeking work'})
        own=await self.call('POST','/game/self-play',status=201);self.own=own
        config=await self.call('GET','/game/play/'+own['token']+'/audience-response')
        self.assertEqual(config['configuration']['workflow_version'],7)
        await self.call('POST','/game/play/'+own['token']+'/audience-response/complete',answers('Leader'))
        await self.call('PUT','/game/night',{'meeting_date':'2026-12-01','start_time':'16:00','timezone_name':'Europe/London','meeting_format':'online','meeting_link':'https://example.org/meeting'})
    async def add_guest(self,name='Sample Guest'):
        row=await self.call('POST','/game/board-members',{'full_name':name,'email':name.replace(' ','').lower()+'@example.org','board_title':'Treasurer'},201)
        p=row['board_member'];await self.call('POST','/game/board-members/'+p['member_id']+'/invite',{'origin_url':'http://test'})
        await self.call('POST','/game/play/'+p['token']+'/audience-response/complete',answers(name))
        return p
    async def group(self):
        result=await self.call('GET','/game/group/session');return result['audience_review']
    async def action(self,**payload):
        review=await self.group();return await self.call('POST','/game/group/audience/action',{'revision':review['revision'],**payload})
    async def test_complete_customer_journey_and_guarded_portfolio_delivery(self):
        await self.setup_and_complete_leader();guest=await self.add_guest()
        await self.call('POST','/game/group/prepare');review=await self.group()
        self.assertEqual(review['workflow_version'],7);self.assertEqual(review['proposals'][0]['contributor'],'Sample Guest');self.assertEqual(review['proposals'][-1]['contributor'],'Sample Leader')
        await self.call('POST','/game/group/start')
        await self.call('POST','/game/group/audience/action',{'revision':(await self.group())['revision'],'action':'progress','index':1},409)
        chosen=None
        for i,proposal in enumerate((await self.group())['proposals']):
            if i==0:chosen=proposal
            await self.action(action='decision',proposal_id=proposal['id'],status='adopted' if i==0 else 'rejected',strategy=proposal['strategy'])
            await self.action(action='progress',index=i+1)
        await self.action(action='commitment',member_id=guest['member_id'],contribution='Introduce two interested employers.',confirmed=True,audience_ids=[chosen['id']])
        await self.action(action='summary');review=await self.group()
        await self.action(action='adopt',confirmed=True,summary_revision=review['summary']['revision'])
        closed=await self.call('POST','/game/group/audience/close',{'confirmed':True});self.assertTrue(closed['closed'])
        state=await self.call('GET','/game/launch/state');strategy=state['strategy']
        self.assertEqual(strategy['status'],'adopted');self.assertEqual(strategy['schema_version'],7);self.assertEqual(len(strategy['agreed_audiences']),1)
        self.assertNotIn('Leader businesses',strategy['document_text'])
        await self.call('PUT','/game/launch/branding',{'primary_color':'#123456','secondary_color':'#eeeeee'})
        pdf=await self.call('GET','/game/group/audience/download');self.assertEqual(pdf.content[:4],b'%PDF')
        await self.call('POST','/game/portfolios/prepare')
        self.assertFalse((await self.call('GET','/game/launch/portfolios'))['portfolios'])
        await self.call('POST','/game/launch/roles',{'member_id':guest['member_id'],'role':'Introduce two interested employers.','confirmed':True})
        await self.call('POST','/game/portfolios/prepare');row=(await self.call('GET','/game/launch/portfolios'))['portfolios'][0]
        self.assertIn('Introduce two interested employers.',row['portfolio_text'])
        await self.call('POST',f"/game/portfolios/{row['portfolio_id']}/send",{'origin_url':'http://test'},409)
        await self.call('POST',f"/game/launch/portfolios/{row['portfolio_id']}/approve",{'version':row['version'],'confirmed':True})
        await self.call('POST',f"/game/portfolios/{row['portfolio_id']}/send",{'origin_url':'http://test'})
        await self.call('POST',f"/game/portfolios/{row['portfolio_id']}/send",{'origin_url':'http://test'})
        self.assertEqual(await self.db.workflow_email_deliveries.count_documents({'event_key':f"portfolio:{row['portfolio_id']}:{row['version']}"}),1)
        public=await self.call('GET','/board-portfolio/'+row['token']);self.assertEqual(public['approved_text'],row['portfolio_text'])
    async def test_admin_content_is_authoritative_and_requires_admin(self):
        data=await self.call('GET','/admin/fundraising/content');data['content']['home']['title']='My own homepage wording'
        await self.call('PUT','/admin/fundraising/content',data['content'])
        self.assertEqual((await self.call('GET','/fundraising/content'))['content']['home']['title'],'My own homepage wording')
        await self.call('PUT','/admin/fundraising/content',data['content'],401,headers={})
    async def test_marketing_consent_paid_stop_unsubscribe_and_duplicate_protection(self):
        from fundraising_launch import send_due
        lead=await self.call('POST','/fundraising/leads',{'name':'New Lead','email':'new@example.org','organization':'Example','visitor_id':'lead-browser-123456','marketing_consent':True},201)
        await self.db.funnel_leads.update_one({'lead_id':lead['lead_id']},{'$set':{'created_at':(datetime.now(timezone.utc)-timedelta(days=4)).isoformat()}})
        with patch('fundraising_launch.deliver_once',new=AsyncMock(return_value={'status':'sent'})) as send:
            await send_due(self.db);self.assertEqual(send.await_count,1);self.assertIn('unsubscribe_url',send.await_args.kwargs)
        row=await self.db.funnel_leads.find_one({'lead_id':lead['lead_id']})
        await self.call('GET','/fundraising/unsubscribe/'+row['unsubscribe_token'])
        with patch('fundraising_launch.deliver_once',new=AsyncMock()) as send:await send_due(self.db);send.assert_not_awaited()
        await self.db.funnel_leads.update_one({'lead_id':lead['lead_id']},{'$set':{'unsubscribed':False,'marketing_consent':True,'paid_at':datetime.now(timezone.utc).isoformat()}})
        with patch('fundraising_launch.deliver_once',new=AsyncMock()) as send:await send_due(self.db);send.assert_not_awaited()
    async def test_legacy_founder_export_keeps_full_original_wording(self):
        from pypdf import PdfReader
        await self.db.sp_projects.insert_one({'project_id':'historical','organization_name':'For All the Children','founder_name':'Katherine','founder_email':'founder@example.org'})
        await self.db.sp_participants.insert_one({'project_id':'historical','email':'founder@example.org','name':'Katherine','original_response':{'q1':'Every original word must remain, including this final sentence.'},'response':{'q1':'Later edited summary'}})
        rows=await self.call('GET','/admin/fundraising/legacy-planning');self.assertEqual(len(rows['projects']),1)
        response=await self.call('GET','/admin/fundraising/legacy-planning/historical/founder.pdf')
        text='\n'.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(response.content)).pages)
        self.assertIn('Every original word must remain, including this final sentence.',text);self.assertNotIn('Later edited summary',text)
        await self.call('GET','/admin/fundraising/legacy-planning/historical/founder.pdf',status=401,headers={})
    async def test_unique_funnel_visitors_and_refreshes_are_not_extra_customers(self):
        for _ in range(3):await self.call('POST','/fundraising/events',{'kind':'homepage','visitor_id':'same-visitor-12345'})
        data=await self.call('GET','/admin/fundraising/overview');self.assertEqual(data['counts']['unique_homepage_visitors'],1)
    async def test_real_checkout_adapter_and_verified_claim_preserve_progress(self):
        from types import SimpleNamespace
        from member_auth import create_member_token
        lead=await self.call('POST','/fundraising/leads',{'name':'Paying Leader','email':'paying@example.org','organization':'BrightPath','visitor_id':'paying-browser-123456'},201,headers={})
        account={'user_id':'real-account','email':'paying@example.org','first_name':'Paying','last_name':'Leader','entitlements':[],'account_status':'active'}
        await self.db.members.insert_one(account.copy())
        headers={'Authorization':'Bearer '+create_member_token(account['user_id'],account['email'])}
        with patch('payment_routes.resolve_game_price_id',return_value='price_497'),patch('payment_routes.stripe.checkout.Session.create',return_value=SimpleNamespace(id='cs_paid',url='https://checkout.stripe.test/session')) as checkout:
            await self.call('POST','/payments/game-checkout',{'origin_url':'http://test','result_token':lead['token']},headers={})
            kwargs=checkout.call_args.kwargs
        self.assertEqual(kwargs['customer_email'],account['email']);self.assertEqual(kwargs['metadata']['selected_tier'],'497')
        self.assertEqual((await self.db.payment_transactions.find_one({'session_id':'cs_paid'}))['amount'],49700)
        self.assertFalse((await self.db.members.find_one({'user_id':'real-account'}))['entitlements'])
        session=SimpleNamespace(id='cs_paid',payment_status='unpaid',metadata=kwargs['metadata'],customer='cus_example',payment_intent='pi_example',amount_total=49700,currency='usd',customer_details={'email':account['email']})
        with patch('member_routes.stripe.checkout.Session.retrieve',return_value=session):
            await self.call('POST','/members/claim-purchase',{'session_id':'cs_paid'},402,headers=headers)
            session.payment_status='paid'
            with patch('fundraising_launch.deliver_once',new=AsyncMock(return_value={'status':'sent'})):
                await self.call('POST','/members/claim-purchase',{'session_id':'cs_paid'},headers=headers)
                await self.call('PUT','/game/launch/organization',{'fundraising_goal':50000,'mission':'Our real supplied mission.','annual_budget':'Not yet confirmed','community':'Young people'},headers=headers)
                await self.call('POST','/members/claim-purchase',{'session_id':'cs_paid'},headers=headers)
        profile=await self.db.game_profiles.find_one({'user_id':'real-account'})
        self.assertEqual(profile['workflow_version'],7);self.assertTrue(profile['profile_completed']);self.assertEqual(profile['organization']['name'],'BrightPath')
        self.assertEqual((await self.db.game_journey_progress.find_one({'user_id':'real-account'}))['stage'],'questions')
        self.assertEqual(await self.db.purchases.count_documents({'session_id':'cs_paid'}),1)

    async def test_partial_setup_is_saved_without_premature_completion(self):
        await self.fresh()
        await self.call('PUT','/game/launch/draft',{'stage':'organization','values':{'mission':'Part of my mission','fundraising_goal':'','private_admin':'must not be stored'}})
        state=await self.call('GET','/game/launch/state')
        self.assertEqual(state['draft']['organization']['mission'],'Part of my mission');self.assertNotIn('private_admin',state['draft']['organization']);self.assertFalse(state['profile']['profile_completed'])
        duplicate=await self.call('POST','/fundraising/leads',{'name':'Sample Leader','email':'lead@example.org','organization':'BrightPath','visitor_id':'unique-browser-123456'},201)
        self.assertEqual(duplicate['token'],self.lead['token'])

    async def test_all_five_followups_use_one_sequence_per_email_and_stop_after_payment(self):
        import fundraising_launch as launch
        from workflow_delivery import deliver_once as original_delivery
        lead=await self.call('POST','/fundraising/leads',{'name':'Consenting Lead','email':'consent@example.org','organization':'Example','visitor_id':'consent-browser-123456','marketing_consent':True},201,headers={})
        created=datetime.now(timezone.utc)-timedelta(days=16)
        await self.db.funnel_leads.update_one({'lead_id':lead['lead_id']},{'$set':{'created_at':created.isoformat()}})
        # Real durable delivery, with only the external provider substituted.
        async def capture(*args,**kwargs):
            with patch('workflow_delivery.resend.Emails.send_async',new=AsyncMock(return_value={'id':'provider-example'})):return await original_delivery(*args,**kwargs)
        for index in range(1,6):
            await self.db.workflow_email_deliveries.update_many({},{'$set':{'updated_at':(created+timedelta(days=(index-1)*3)).isoformat()}})
            with patch.object(launch,'deliver_once',side_effect=capture):await launch.send_due(self.db);await launch.send_due(self.db)
            self.assertEqual(await self.db.workflow_email_deliveries.count_documents({'event_key':{'$regex':'^followup:'}}),index)
        other=await self.call('POST','/fundraising/leads',{'name':'Consenting Lead','email':'consent@example.org','organization':'Example','visitor_id':'another-browser-123456','marketing_consent':True},201,headers={})
        await self.db.funnel_leads.update_one({'lead_id':other['lead_id']},{'$set':{'created_at':created.isoformat()}})
        with patch.object(launch,'deliver_once',new=AsyncMock()) as send:await launch.send_due(self.db);send.assert_not_awaited()
        await self.db.payment_transactions.insert_one({'session_id':'paid-before-claim','lead_email':'consent@example.org','payment_status':'paid'})
        await self.db.workflow_email_deliveries.delete_many({})
        with patch.object(launch,'deliver_once',new=AsyncMock()) as send:await launch.send_due(self.db);send.assert_not_awaited()

    async def test_test_payment_rejects_another_synthetic_owner(self):
        await self.fresh();lead=self.lead
        other=await self.call('POST','/admin/fundraising/test-start',headers=self.admin)
        await self.call('POST','/payments/game-checkout',{'origin_url':'http://test','result_token':lead['token']},403,headers={'Authorization':'Bearer '+other['token']})

if __name__=='__main__':unittest.main()
