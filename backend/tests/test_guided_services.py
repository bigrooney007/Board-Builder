"""Guided Recruitment: actual HTTP, Mongo, legacy generators and controlled providers."""
import copy,hashlib,hmac,json,os,sys,time,unittest,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT))
import guided_services as gs
from guided_service_defaults import defaults,PRICES,PRODUCTS
class Configuration(unittest.TestCase):
    def test_independent_configuration_and_question_validation(self):
        first=defaults('recruitment');other=defaults('board-recommitment');first['first_email']['subject']='Changed'
        self.assertNotEqual(first['first_email']['subject'],other['first_email']['subject'])
        for s in PRICES:gs.validate_config(s,defaults(s))
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):gs.validate_questions([*first['question_groups']['entry'],first['question_groups']['entry'][0]])
        self.assertEqual(set(defaults('strategic-planning')['question_groups']),{'entry','leader','board'})
        self.assertEqual(len(defaults('recruitment')['followups']),5)
    def test_failed_analysis_default_never_claims_finished_profiles_or_human_review(self):
        row={'service':'recruitment','name':'Leader Name','organization':'Sample','answers':{},'question_snapshot':[],'payment_status':'unpaid','access_token':'saved'}
        message=gs.render(defaults('recruitment')['first_email'],gs.context(row))
        self.assertNotIn('prepared initial',message['body']);self.assertNotIn('personally reviewed',message['body'])

@unittest.skipUnless(os.environ.get('RECOVERY_ACCEPTANCE')=='1','Requires disposable Mongo and controlled providers')
class GuidedHTTP(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import httpx
        from tests.current_workflow_app import build_app
        from tests.guided_service_fixtures import generation
        from motor.motor_asyncio import AsyncIOMotorClient
        from auth_service import create_access_token
        self.mongo=AsyncIOMotorClient(os.environ['MONGO_URL']);self.db=self.mongo.nbb_guided_tests
        for n in await self.db.list_collection_names():await self.db[n].delete_many({})
        await gs.indexes(self.db)
        await self.db.members.create_index('email',unique=True);await self.db.opportunities.create_index('user_id',unique=True)
        await self.db.users.insert_one({'user_id':'service-admin','email':'admin@example.test','role':'admin'})
        self.app=build_app(self.db);self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://test')
        self.headers={'Authorization':'Bearer '+create_access_token('service-admin','admin@example.test')};self.sessions={};self.created=[];self.mail=AsyncMock(return_value={'id':'controlled-email'})
        patch('resend.Emails.send_async',self.mail).start();patch('ai_service.generate_structured',side_effect=generation).start();patch('workspace_routes.generate_structured',side_effect=generation).start();patch('reactivation_routes.generate_structured',side_effect=generation).start()
        patch('payment_routes.resolve_offer_price_id',return_value='price_guided_497').start()
        def create(**kw):
            self.created.append(kw);sid='cs_test_'+uuid.uuid4().hex;service=kw['metadata']['guided_service']
            self.sessions[sid]={'id':sid,'metadata':kw['metadata'],'client_reference_id':kw['client_reference_id'],'amount_subtotal':PRICES[service],'amount_total':PRICES[service],'currency':'usd','payment_status':'unpaid','status':'open','livemode':False}
            return SimpleNamespace(id=sid,url='https://checkout.stripe.com/c/pay/'+sid)
        patch('stripe.checkout.Session.create',side_effect=create).start();patch('stripe.checkout.Session.retrieve',side_effect=lambda sid:self.sessions[sid]).start()
    async def asyncTearDown(self):patch.stopall();await self.client.aclose();self.mongo.close()
    async def req(self,method,path,body=None,status=200,admin=False):
        r=await self.client.request(method,'/api'+path,json=body,headers=self.headers if admin else {});self.assertEqual(r.status_code,status,r.text[:1200]);return r.json() if 'json' in r.headers.get('content-type','') else r
    async def lead(self,service='recruitment',submitted=True,**extra):
        r=await self.req('POST',f'/services/{service}/start',{'request_id':str(uuid.uuid4()),'name':'Sample Leader','email':'leader@example.org','organization':'Sample Learning Nonprofit',**extra});token=r['token'];base=f'/services/{service}/customer/{token}'
        if submitted:await self.req('PUT',base+'/answers',{'answers':{q['id']:'We help children access learning.' for q in r['record']['question_snapshot']},'submit':True})
        row=await self.db.guided_service_customers.find_one({'access_token':token},{'_id':0});return token,base,row
    async def paid(self,service='recruitment'):
        token,base,row=await self.lead(service);await self.req('POST',base+'/checkout');row=await self.db.guided_service_customers.find_one({'access_token':token},{'_id':0});self.sessions[row['session_id']].update(payment_status='paid',status='complete');await self.req('POST',base+'/confirm',{});row=await self.db.guided_service_customers.find_one({'access_token':token},{'_id':0});return token,base,row
    async def test_free_form_snapshot_and_thank_you_never_reveals_profiles(self):
        token,base,row=await self.lead();data=await self.req('GET',base)
        self.assertTrue(data['submitted_at']);self.assertNotIn('recommendations',data);self.assertNotIn('booking_url',data);self.assertEqual(await self.db.members.count_documents({}),0)
        await self.req('PUT',base+'/answers',{'answers':{},'submit':True},409)
    async def test_dynamic_add_reorder_archive_and_historic_answers(self):
        token,base,row=await self.lead();settings=await self.req('GET','/admin/services/recruitment/settings',admin=True);c=settings['config'];c['question_groups']['entry']=[{**c['question_groups']['entry'][1],'prompt':'Updated question'}]
        saved=await self.req('PUT','/admin/services/recruitment/draft',{'config':c,'revision':settings['revision']},admin=True);await self.req('POST','/admin/services/recruitment/publish',{'revision':saved['revision']},admin=True)
        current=await self.req('GET','/services/recruitment/questions');self.assertEqual(len(current['questions']),1);self.assertEqual(current['questions'][0]['prompt'],'Updated question')
        original=await self.req('GET',base);self.assertEqual(len(original['question_snapshot']),7);self.assertEqual(original['answers'],row['answers'])
        other=await self.req('GET','/admin/services/board-recommitment/settings',admin=True);self.assertNotEqual(other['config']['question_groups']['entry'][0]['prompt'],'Updated question')
    async def test_one_hour_initial_delivery_and_five_spaced_followups_idempotent(self):
        token,base,row=await self.lead();stamp=datetime.fromisoformat(row['submitted_at']);await gs.automation_tick(self.db,stamp+timedelta(minutes=59));self.mail.assert_not_called()
        await gs.automation_tick(self.db,stamp+timedelta(minutes=60));await gs.automation_tick(self.db,stamp+timedelta(minutes=60));self.assertEqual(self.mail.call_count,1)
        for i in range(1,6):await gs.automation_tick(self.db,stamp+timedelta(minutes=61,days=3*i))
        await gs.automation_tick(self.db,stamp+timedelta(days=30));self.assertEqual(self.mail.call_count,6)
    async def test_failed_first_delivery_retries_without_advancing_or_duplicates(self):
        token,base,row=await self.lead();self.mail.side_effect=RuntimeError('controlled provider failure');at=datetime.fromisoformat(row['submitted_at'])+timedelta(hours=2);await gs.automation_tick(self.db,at)
        failed=await self.db.guided_service_customers.find_one({'customer_id':row['customer_id']});self.assertNotIn('first_email_sent_at',failed)
        self.mail.side_effect=None;await gs.automation_tick(self.db,at);await gs.automation_tick(self.db,at);self.assertEqual(self.mail.call_count,2)
    async def test_unsubscribe_manual_stop_and_global_suppression_stop_promotions(self):
        token,base,row=await self.lead();await self.req('POST',f'/services/recruitment/unsubscribe/{row["unsubscribe_token"]}');await gs.automation_tick(self.db,datetime.now(timezone.utc)+timedelta(days=20));self.mail.assert_not_called()
        token,base,row=await self.lead(email='suppressed@example.org');await self.db.nurture_contacts.insert_one({'email':row['email'],'unsubscribed':True});await gs.automation_tick(self.db,datetime.now(timezone.utc)+timedelta(days=20));self.mail.assert_not_called()
    async def test_separate_checkout_and_same_open_checkout_reused(self):
        token,base,row=await self.lead();one=await self.req('POST',base+'/checkout');two=await self.req('POST',base+'/checkout');self.assertEqual(one,two);self.assertEqual(len(self.created),1);self.assertEqual(self.created[0]['metadata']['offer_source'],PRODUCTS['recruitment']);self.assertNotIn('197',self.created[0]['metadata']['offer_source'])
    async def test_unpaid_success_url_cannot_unlock_branding_booking_or_resources(self):
        token,base,row=await self.lead();await self.req('POST',base+'/checkout');r=await self.req('POST',base+'/confirm',{});self.assertNotEqual(r['payment_status'],'paid')
        await self.req('PUT',base+'/branding',{'primary_color':'#123456'},402);await self.req('GET',base+'/book',status=402);await self.req('GET',base+'/resources',status=402)
    async def test_wrong_amount_product_or_foreign_session_rejected(self):
        token,base,row=await self.lead();await self.req('POST',base+'/checkout');row=await self.db.guided_service_customers.find_one({'access_token':token});session=self.sessions[row['session_id']];session.update(payment_status='paid',amount_subtotal=19700)
        await self.req('POST',base+'/confirm',{},409);session['amount_subtotal']=49700;session['metadata']['offer_source']='wrong';await self.req('POST',base+'/confirm',{},409);await self.req('POST',base+'/confirm',{'session_id':'foreign'},403)
    async def test_paid_then_branding_then_calendly_without_second_charge(self):
        token,base,row=await self.paid();await self.req('GET',base+'/book',status=409);await self.req('PUT',base+'/branding',{'primary_color':'#123456','secondary_color':'#abcdef'})
        r=await self.req('GET',base+'/book',status=303);self.assertIn('calendly.com',r.headers['location']);self.assertIn('email=leader%40example.org',r.headers['location']);self.assertNotIn('cs_test',r.headers['location']);again=await self.req('POST',base+'/checkout');self.assertIn('/setup/',again['resume_url']);self.assertEqual(len(self.created),1)
    async def test_existing_customer_records_and_campaign_never_overwritten(self):
        await self.db.members.insert_one({'user_id':'old','email':'leader@example.org','entitlements':['recruitment_self_guided']});await self.db.opportunities.insert_one({'user_id':'old','slug':'original','status':'Published'})
        token,base,row=await self.paid();self.assertNotEqual(row['workspace_user_id'],'old');self.assertEqual((await self.db.members.find_one({'user_id':'old'}))['entitlements'],['recruitment_self_guided']);self.assertEqual((await self.db.opportunities.find_one({'user_id':'old'}))['slug'],'original')
    async def test_payment_stops_all_prospect_emails_and_receipt_is_transactional(self):
        token,base,row=await self.paid();before=self.mail.call_count;await gs.automation_tick(self.db,datetime.now(timezone.utc)+timedelta(days=50));self.assertEqual(self.mail.call_count,before)
        self.assertTrue((await self.db.guided_service_customers.find_one({'customer_id':row['customer_id']}))['sequence_stopped'])
    async def test_analysis_private_edit_approve_and_full_material_generation(self):
        from guided_workspace import work_tick,RECRUITMENT_MATERIALS
        token,base,row=await self.paid();await work_tick(self.db,self.app,row['customer_id']);r=await self.req('GET','/admin/services/recruitment/customers/'+row['customer_id'],admin=True);roles=r['customer']['recommendations'];ab='/admin/services/recruitment/customers/'+row['customer_id']
        await self.req('POST',ab+'/generate-materials',{},409,True);await self.req('PUT',ab+'/profiles',{'roles':roles,'count':len(roles),'approved':True},admin=True)
        await self.req('POST',ab+'/generate-materials',{},admin=True);await work_tick(self.db,self.app,row['customer_id'])
        docs=await self.db.generated_materials.find({'user_id':row['workspace_user_id']}).to_list(100);self.assertTrue(set(RECRUITMENT_MATERIALS)<=set(m['type'] for m in docs))
        doc=next(m for m in docs if m['type']=='board_manual');tool=ab+'/tool/workspace/materials/'+doc['material_id'];await self.req('PUT',tool,{'display_text':'An edited manual approved by the organization.'},admin=True);await self.req('POST',tool+'/approve',{},admin=True)
        resources=await self.req('GET',base+'/resources');self.assertEqual(next(m for m in resources['materials'] if m['type']=='board_manual')['text'],'An edited manual approved by the organization.')
        for fmt in ('pdf','docx','txt'):self.assertGreater(len((await self.req('GET',base+'/materials/'+doc['material_id']+'/download?format='+fmt)).content),20)
        await self.req('PUT',tool,{'display_text':'Revised draft.'},admin=True);await self.req('GET',base+'/materials/'+doc['material_id']+'/download',status=403)
    async def test_authorization_scope_paid_token_and_admin_boundaries(self):
        token,base,row=await self.paid();token2,base2,row2=await self.paid();await self.req('GET','/admin/services/recruitment/customers/'+row['customer_id'],status=401)
        await self.req('POST',base+'/tool/game/group/finalize',{},403);await self.req('GET',base+'/tool/reactivation/roster',status=403)
        await self.req('GET',base+'/materials/not-owned/download',status=404);await self.req('GET',base.replace(token,'x'*43),status=404)
        from member_auth import create_member_token
        member=await self.db.members.find_one({'user_id':row['workspace_user_id']});bad=await self.client.get('/api/workspace/profile',headers={'Authorization':'Bearer '+create_member_token(member['user_id'],member['email'])});self.assertEqual(bad.status_code,403)
    async def test_manual_video_uses_paid_continuation_and_approval_with_dedupe(self):
        token,base,row=await self.paid();ab='/admin/services/recruitment/customers/'+row['customer_id'];draft=await self.req('POST',ab+'/video-preview',{'video_url':'https://youtu.be/actualvideo'},admin=True);self.assertNotIn('PAY $497',draft['cta']);body={**draft,'request_id':str(uuid.uuid4()),'approved':True}
        before=self.mail.call_count;await self.req('POST',ab+'/video-send',body,admin=True);await self.req('POST',ab+'/video-send',body,admin=True);self.assertEqual(self.mail.call_count,before+1)
        await self.req('POST',ab+'/video-send',{**body,'approved':False},409,True);await self.req('POST',ab+'/video-preview',{'video_url':'https://evil.example/video'},422,True)
    async def test_admin_current_sample_has_no_real_charge_and_scoped_mail(self):
        sample=await self.req('POST','/admin/services/recruitment/test-start',{},admin=True);row=await self.db.guided_service_customers.find_one({'customer_id':sample['customer_id']});ab='/admin/services/recruitment/customers/'+sample['customer_id'];base='/services/recruitment/customer/'+row['access_token']
        await self.req('POST',ab+'/test-advance',{'action':'run-email'},409,True);await self.req('PUT',base+'/answers',{'answers':{q['id']:'Sample mission and needs' for q in row['question_snapshot']},'submit':True});await self.req('POST',base+'/checkout',{},409)
        await self.req('POST',ab+'/test-advance',{'action':'run-email'},admin=True);self.mail.assert_not_called();await self.req('POST',ab+'/test-advance',{'action':'pay'},admin=True);await self.req('GET',base+'/resources');self.assertEqual(len(self.created),0)
    async def test_campaign_launch_is_explicit_idempotent_and_application_cv_notification_work(self):
        from guided_workspace import work_tick
        token,base,row=await self.paid();ab='/admin/services/recruitment/customers/'+row['customer_id'];await work_tick(self.db,self.app,row['customer_id']);row=await self.db.guided_service_customers.find_one({'customer_id':row['customer_id']})
        await self.req('PUT',ab+'/profiles',{'roles':row['recommendations'],'count':1,'approved':True},admin=True)
        await self.req('PUT',ab+'/interview-details',{'method':'availability','availability':'October 30, 2026 at 10:00 UTC','preferred_method':'Video meeting','contact_person':'Sample Leader'},admin=True)
        await self.req('POST',ab+'/generate-materials',{},admin=True);await work_tick(self.db,self.app,row['customer_id'])
        docs=await self.db.generated_materials.find({'user_id':row['workspace_user_id']}).to_list(100)
        for m in docs:await self.req('POST',ab+'/tool/workspace/materials/'+m['material_id']+'/approve',{},admin=True)
        await self.req('POST',ab+'/launch',{'confirmed':False},409,True)
        with patch('workspace_routes.send_opportunity_broadcast',new_callable=AsyncMock) as broadcast:
            result=await self.req('POST',ab+'/launch',{'confirmed':True,'network_consent':False},admin=True);await self.req('POST',ab+'/launch',{'confirmed':True,'network_consent':False},admin=True);broadcast.assert_not_called()
        self.assertEqual(result['status'],'Published');self.assertEqual(result['broadcast_status'],'Not requested');slug=result['opportunity']['slug']
        public=await self.req('GET','/public/board-opportunities/'+slug);self.assertEqual(public['organization_name'],row['organization'])
        r=await self.client.post('/api/public/board-opportunities/'+slug+'/apply',data={'payload':json.dumps({'full_name':'Sample Candidate','email':'candidate@example.org','location':'Pittsburgh','profession':'Educator','why_interested':'I can help develop school partnerships.'})},files={'cv':('Sample-CV.txt',b'Example resume','text/plain')});self.assertIn(r.status_code,(400,422))
        import io
        from reportlab.pdfgen import canvas
        buffer=io.BytesIO();c=canvas.Canvas(buffer);c.drawString(20,700,'Sample Educator CV');c.save()
        r=await self.client.post('/api/public/board-opportunities/'+slug+'/apply',data={'payload':json.dumps({'full_name':'Sample Candidate','email':'candidate@example.org','location':'Pittsburgh','profession':'Educator','why_interested':'I can help develop school partnerships.'})},files={'cv':('Sample-CV.pdf',buffer.getvalue(),'application/pdf')});self.assertEqual(r.status_code,201,r.text);applicant=r.json();aid=applicant['application_id']
        cv=await self.req('GET',base+'/tool/workspace/applications/'+aid+'/cv');self.assertTrue(cv.content.startswith(b'%PDF'))
        notice=await self.db.workflow_email_deliveries.find_one({'event_key':'guided-application-'+aid});self.assertEqual(notice['recipient'],'leader@example.org');self.assertIn('/services/recruitment/resources/',notice['link'])
        draft=await self.req('POST',base+'/applicants/'+aid+'/preview',{'action':'invite'});self.assertIn('October 30',draft['body']);await self.req('POST',base+'/applicants/'+aid+'/send',{**draft,'request_id':str(uuid.uuid4()),'approved':True})
        saved=await self.db.opportunity_applications.find_one({'application_id':aid});self.assertEqual(saved['status'],'Interview Invited');self.assertEqual(saved['interview_guide']['status'],'Ready')
        await self.req('POST',ab+'/deliver',{'approved':True,'request_id':str(uuid.uuid4())},admin=True)
