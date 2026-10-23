"""Part Four HTTP acceptance against disposable Mongo and controlled providers."""
import copy, json, os, unittest, uuid, asyncio
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
import test_guided_services as shared_tests
import guided_services as gs
from guided_service_defaults import defaults,PRICES,PRODUCTS
import guided_planning as gp

class PlanningConfiguration(unittest.TestCase):
    def test_three_entry_questions_and_independent_planning_groups(self):
        c=defaults('strategic-planning');gs.validate_config('strategic-planning',c)
        self.assertEqual([q['key'] for q in c['question_groups']['entry']],['leader_role','board_count','planning_meeting_preference','desired_outcome_impact'])
        self.assertEqual(len(c['followups']),5);self.assertEqual(len(set(t['subject'] for t in c['followups'])),5)
        self.assertNotEqual(c['question_groups']['leader'][0]['prompt'],c['question_groups']['board'][0]['prompt'])
        self.assertEqual(PRICES['strategic-planning'],9700)
        self.assertEqual(__import__('guided_service_defaults').package('strategic-planning','rooney-facilitated')['amount'],199700)
    def test_programs_keep_distinct_stable_ids_and_adopt_only_selected(self):
        c=defaults('strategic-planning');p={'mission':'Our actual mission','programs':[{'id':'school','name':'After-School Education'},{'id':'coding','name':'Youth Coding'}]}
        f=gp.form_content(c,'board',p);programs=[s for s in f['sections'] if s['program_id']]
        self.assertEqual([s['key'] for s in programs],['program_school','program_coding'])
        self.assertNotEqual(programs[0]['questions'][0]['id'],programs[1]['questions'][0]['id'])

@unittest.skipUnless(os.environ.get('RECOVERY_ACCEPTANCE')=='1','Requires disposable Mongo and controlled providers')
class PlanningHTTP(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=shared_tests.GuidedHTTP.asyncSetUp
    asyncTearDown=shared_tests.GuidedHTTP.asyncTearDown
    req=shared_tests.GuidedHTTP.req
    lead=shared_tests.GuidedHTTP.lead
    paid=shared_tests.GuidedHTTP.paid
    complete_leader=shared_tests.GuidedHTTP.complete_leader

    async def prepared(self):
        token,public,row=await self.paid('strategic-planning')
        import base64,io
        from PIL import Image
        logo=io.BytesIO();Image.new('RGB',(12,12),'#123456').save(logo,format='WEBP')
        await self.req('PUT',public+'/branding',{'primary_color':'#123456','secondary_color':'#abcdef','logo_data':'data:image/webp;base64,'+base64.b64encode(logo.getvalue()).decode()})
        base='/admin/services/strategic-planning/customers/'+row['customer_id']+'/planning'
        await self.req('PUT',base+'/setup',{'mission':'Help children access learning.','planning_period':'2027 to 2028','planning_meeting':{'meeting_date':'2026-11-15','start_time':'10:00','timezone_name':'Europe/London'},'response_deadline':'2026-11-10','programs':[{'id':'school','name':'After-School Education'},{'id':'coding','name':'Youth Coding'}]},admin=True)
        lead=await self.req('POST',base+'/leader-form',{},admin=True)
        board=await self.req('POST',base+'/participants',{'name':'Sample Board Member','email':'board@example.org'},201,True)
        return token,public,row,base,lead,board

    async def contribute(self,token):
        form=await self.req('GET','/strategic-planning-form/'+token)
        if form.get('submitted'):return form,form['existing_answers']
        answers={q['id']:'Agreed original idea for '+s['title'] for s in form['form']['sections'] for q in s['questions']}
        await self.req('PUT','/strategic-planning-form/'+token,{'answers':answers})
        await self.req('POST','/strategic-planning-form/'+token,{'full_name':form['prefill']['full_name'],'email':form['prefill']['email'],'answers':answers},201)
        return form,answers

    async def completed_meeting(self):
        token,public,row,base,lead,board=await self.prepared()
        await self.contribute(lead['url'].split('/')[-1]);await self.contribute(board['form_token'])
        session='/guided/strategic-planning';sid=row['workspace_user_id'];body={'session_id':sid}
        await self.req('POST',session+'/session/share',body,admin=True)
        await self.req('POST',session+'/session/start',body,admin=True)
        data=await self.req('GET',session+'/session?session_id='+sid,admin=True)
        decisions={s['key']:[s['ideas'][0]['idea_id']] for s in data['sections']}
        reviewed=await self.req('POST',session+'/session/complete',{**body,'decisions':decisions,'transcript':'A separate rejected suggestion to build a space station was not adopted.'},admin=True)
        await self.req('POST',session+'/session/adopt',{**body,'confirmed':True,'revision':reviewed['decision_revision']},admin=True)
        return token,public,row,base,lead,board,reviewed

    async def test_one_hour_invitation_497_activation_product_paid_branding_and_booking(self):
        token,public,row=await self.lead('strategic-planning')
        at=datetime.fromisoformat(row['submitted_at']);await gs.automation_tick(self.db,at+timedelta(minutes=59));self.mail.assert_not_called()
        await gs.automation_tick(self.db,at+timedelta(hours=1));self.assertEqual(self.mail.call_count,1)
        self.assertIn('$97',self.mail.call_args.args[0]['html']);self.assertNotIn('$1,997',self.mail.call_args.args[0]['html'])
        await self.req('POST',public+'/checkout');r=await self.db.guided_service_customers.find_one({'customer_id':row['customer_id']})
        self.assertEqual(self.created[0]['metadata']['offer_source'],__import__('guided_service_defaults').package('strategic-planning')['product'])
        self.sessions[r['session_id']].update(payment_status='paid',status='complete');await self.req('POST',public+'/confirm',{})
        await self.req('GET',public+'/book',status=409);await self.complete_leader(public,'strategic-planning');await self.req('PUT',public+'/branding',{'primary_color':'#123456'});await self.req('GET',public+'/book',status=303)
        previous=self.mail.call_count;await gs.automation_tick(self.db,at+timedelta(days=40));self.assertEqual(previous,self.mail.call_count)
        self.assertEqual(await self.db.payment_transactions.count_documents({'session_id':r['session_id'],'purchase_source':{'$in':['strategic_planning_497','strategic_planning_supported_2997']}}),0)

    async def test_independent_forms_programs_answers_notifications_and_secure_links(self):
        token,public,row,base,lead,board=await self.prepared()
        leader=await self.req('GET',lead['url'].replace('/strategic-planning-form/','/strategic-planning-form/'))
        member=await self.req('GET','/strategic-planning-form/'+board['form_token'])
        self.assertTrue(leader['existing_answers']);self.assertFalse(member['existing_answers'])
        self.assertNotEqual(leader['form']['sections'][0]['questions'][0]['prompt'],member['form']['sections'][0]['questions'][0]['prompt'])
        invitation=await self.req('POST',base+'/participants/'+board['participant_id']+'/message-preview',{},admin=True)
        self.assertIn('2026-11-15',invitation['body']);self.assertIn('2026-11-10',invitation['body'])
        message={**invitation,'request_id':str(uuid.uuid4()),'approved':True}
        await self.req('POST',base+'/participants/'+board['participant_id']+'/message-send',message,admin=True)
        sent=self.mail.call_count;await self.req('POST',base+'/participants/'+board['participant_id']+'/message-send',message,admin=True);self.assertEqual(sent,self.mail.call_count)
        f,answers=await self.contribute(board['form_token']);self.assertIn('sp24_03__school',answers);self.assertIn('sp24_03__coding',answers)
        await self.req('GET','/strategic-planning-response/'+board['participant_id'],status=403)
        details=await self.req('GET',public+'/planning');self.assertEqual(details['participants'][1]['status'],'COMPLETED');self.assertNotIn('form_token',details['participants'][1])
        self.assertIn('form_snapshot',(await self.db.sp_participants.find_one({'participant_id':board['participant_id']})))
        self.assertTrue(await self.db.workflow_email_deliveries.find_one({'event_key':'planning-response-'+board['participant_id']}))

    async def test_question_versions_and_cross_organization_isolation(self):
        token,public,row,base,lead,board=await self.prepared();form=await self.req('GET','/strategic-planning-form/'+board['form_token'])
        config=await self.req('GET','/admin/services/strategic-planning/settings',admin=True);c=config['config'];c['question_groups']['board']=[{**c['question_groups']['board'][0],'prompt':'A new published board question'}]
        save=await self.req('PUT','/admin/services/strategic-planning/draft',{'config':c,'revision':config['revision']},admin=True);await self.req('POST','/admin/services/strategic-planning/publish',{'revision':save['revision']},admin=True)
        old=await self.req('GET','/strategic-planning-form/'+board['form_token']);self.assertEqual(old['form'],form['form'])
        await self.req('POST','/strategic-planning-form/'+board['form_token'],{'full_name':'Other person','email':'other@example.org','answers':{}},403)
        _,_,second=await self.paid('strategic-planning');other='/admin/services/strategic-planning/customers/'+second['customer_id']+'/planning'
        await self.req('POST',other+'/participants/'+board['participant_id']+'/message-preview',{},404,True)
        await self.req('GET',base,status=401)
        await self.req('GET','/guided/strategic-planning/session?session_id='+row['workspace_user_id'],status=401)

    async def test_session_decisions_transcript_consent_program_topics_and_owner_agreement(self):
        token,public,row,base,lead,board=await self.prepared();sid=row['workspace_user_id'];sp='/guided/strategic-planning'
        await self.req('POST',sp+'/session/start',{'session_id':sid},409,True)
        await self.contribute(lead['url'].split('/')[-1]);await self.contribute(board['form_token'])
        shared=await self.req('POST',sp+'/session/share',{'session_id':sid},admin=True);await self.req('GET',sp+'/session/watch/'+shared['share_token'],status=403)
        await self.req('GET',sp+'/session/watch/'+shared['share_token']+'?participant_token='+board['form_token'])
        await self.req('PUT',base+'/recording',{'active':True,'consent_confirmed':False},422,True);await self.req('PUT',base+'/recording',{'active':True,'consent_confirmed':True},admin=True)
        await self.req('POST',sp+'/session/start',{'session_id':sid},admin=True)
        data=await self.req('GET',sp+'/session?session_id='+sid,admin=True);keys=[s['key'] for s in data['sections']];self.assertIn('program_school',keys);self.assertIn('program_coding',keys)
        await self.req('POST',sp+'/session/progress',{'session_id':sid,'current_section_index':len(keys)-1},admin=True)
        await self.req('PUT',base+'/discussion',{'section_key':keys[0],'confirmed_owner':'Sample member','owner_agreement_confirmed':False},422,True)
        source=data['sections'][0]['ideas'][0]['idea_id'];idea=await self.req('POST',sp+'/session/idea',{'session_id':sid,'section_key':keys[0],'text':'Agreed combined wording','source_idea_ids':[source]},admin=True)
        await self.req('POST',sp+'/session/decision',{'session_id':sid,'section_key':keys[0],'decision':[idea['idea']['idea_id']]},admin=True)
        await self.req('POST',sp+'/session/transcript',{'session_id':sid,'transcript':'Corrected meeting notes.'},admin=True)
        current=await self.req('GET',sp+'/session?session_id='+sid,admin=True);self.assertEqual(current['transcript'],'Corrected meeting notes.')
        await self.req('POST',sp+'/session/transcript',{'session_id':sid,'transcript':'a'*80000},admin=True)
        self.assertEqual(len((await self.req('GET',sp+'/session?session_id='+sid,admin=True))['transcript']),80000)
        extra=await self.req('POST',base+'/subjects',{'name':'New Community Program','confirmed':True},admin=True)
        added=await self.req('POST',sp+'/session/idea',{'session_id':sid,'section_key':extra['section']['key'],'text':'Discuss this new program before adopting any commitment.'},admin=True)
        await self.req('POST',sp+'/session/decision',{'session_id':sid,'section_key':extra['section']['key'],'decision':[added['idea']['idea_id']]},admin=True)


    async def test_generation_review_changes_version_adoption_final_delivery_and_downloads(self):
        token,public,row,base,lead,board,reviewed=await self.completed_meeting();sid=row['workspace_user_id'];contexts=[]
        async def generated(kind,context,instructions=''):
            contexts.append(json.loads(context));return {'sections':[{'heading':'Vision','content':'Agreed original idea for Vision'},{'heading':'After-School Education','content':'Agreed original idea for After-School Education'},{'heading':'Youth Coding','content':'Agreed original idea for Youth Coding'}]}
        with patch('strategic_planning_routes.generate_structured',side_effect=generated):
            await self.req('POST','/guided/strategic-planning/session-plan',{'session_id':sid},admin=True)
            for _ in range(100):
                plan=await self.db.sp_plans.find_one({'project_id':row['customer_id']})
                if plan.get('final_status')!='Generating':break
                await asyncio.sleep(.01)
        self.assertEqual(plan['final_status'],'Draft');self.assertEqual(contexts[0]['planning_period'],'2027 to 2028');self.assertIn('explicitly_adopted_decisions',contexts[0])
        self.assertNotIn('space station',json.dumps(contexts[0]['explicitly_adopted_decisions']))
        self.assertEqual((await self.req('GET',public+'/planning'))['plan']['text'],'')
        await self.req('POST','/guided/strategic-planning/final-plan/approve',{'session_id':sid},409,True)
        await self.req('PUT',base+'/plan',{'text':plan['final_display_text'],'expected_version':0},admin=True)
        people=await self.db.sp_participants.find({'project_id':row['customer_id']}).to_list(10)
        await self.req('POST',base+'/prepare-review',{'approved':True,'version':1},admin=True)
        await self.req('GET','/strategic-plan-review/'+board['review_token'],status=409)
        await self.req('POST',base+'/release-review',{'confirmed':True,'version':1},admin=True)
        view=await self.req('GET','/strategic-plan-review/'+board['review_token']);self.assertEqual(view['plan_version'],1)
        await self.req('POST','/strategic-plan-review/'+board['review_token'],{'full_name':board['name'],'plan_version':1,'decision':'request_change','requested_changes':'Clarify the first program priority.'},201)
        await self.req('POST',base+'/finalize',{'version':1,'organization_approval_confirmed':True},409,True)
        await self.req('PUT',base+'/plan',{'text':plan['final_display_text']+'\n\nAn agreed clarification.','expected_version':1},admin=True)
        await self.req('GET','/strategic-plan-review/'+board['review_token'],status=409)
        await self.req('POST',base+'/prepare-review',{'approved':True,'version':2},admin=True);await self.req('POST',base+'/release-review',{'confirmed':True,'version':2},admin=True)
        await self.req('POST','/strategic-plan-review/'+board['review_token'],{'full_name':board['name'],'plan_version':1,'decision':'adopt'},409)
        for person in people:await self.req('POST','/strategic-plan-review/'+person['review_token'],{'full_name':person['name'],'plan_version':2,'decision':'adopt'},201)
        final=await self.req('POST',base+'/finalize',{'version':2,'organization_approval_confirmed':True},admin=True)
        public_plan=await self.req('GET',final['share_url']);self.assertEqual(public_plan['branding']['primary_color'],'#123456')
        for ext in ('pdf','docx','txt'):
            download=await self.req('GET',public+'/planning/download?format='+ext);self.assertGreater(len(download.content),40)
        msg=await self.req('POST',base+'/delivery-preview',{},admin=True);message={**msg,'approved':True,'request_id':str(uuid.uuid4())}
        await self.req('POST',base+'/deliver',message,admin=True);sent=self.mail.call_count;await self.req('POST',base+'/deliver',message,admin=True);self.assertEqual(self.mail.call_count,sent)
        saved=await self.db.sp_plans.find_one({'project_id':row['customer_id']});self.assertEqual(len(saved['versions']),3)

    async def test_interrupted_generation_can_resume_without_repeating_the_meeting(self):
        token,public,row,base,lead,board,reviewed=await self.completed_meeting()
        await self.db.sp_plans.update_one({'project_id':row['customer_id']},{'$set':{'final_status':'Generating','generation_request_id':'interrupted','generation_started_at':(datetime.now(timezone.utc)-timedelta(minutes=11)).isoformat()}})
        async def generated(*args):return {'sections':[{'heading':'Agreed Direction','content':'The adopted priorities remain saved.'}]}
        with patch('strategic_planning_routes.generate_structured',side_effect=generated):
            await self.req('POST','/guided/strategic-planning/session-plan',{'session_id':row['workspace_user_id']},admin=True)
            for _ in range(100):
                plan=await self.db.sp_plans.find_one({'project_id':row['customer_id']})
                if plan['final_status']!='Generating':break
                await asyncio.sleep(.01)
        self.assertEqual(plan['final_status'],'Draft');self.assertNotEqual(plan['generation_request_id'],'interrupted')
        self.assertEqual((await self.db.sp_sessions.find_one({'project_id':row['customer_id']}))['status'],'COMPLETED')
