"""Part Three uses real legacy participant, interpretation, portfolio and signing routes."""
import asyncio,copy,os,unittest,uuid
from unittest.mock import patch
import test_guided_services as shared_tests
import guided_services as gs
from guided_service_defaults import defaults
class RecommitmentConfiguration(unittest.TestCase):
 def test_editable_labels_preserve_three_structured_decisions(self):
  from guided_recommitment import participant_defaults,decisions
  config=defaults('board-recommitment');config['participant_form']['labels']['step_down']='I need to leave my current role.';gs.validate_config('board-recommitment',config)
  self.assertEqual(set(decisions()),{'active','advisory','step_down'});self.assertEqual(len(config['question_groups']['entry']),4)

@unittest.skipUnless(os.environ.get('RECOVERY_ACCEPTANCE')=='1','Requires disposable Mongo and controlled providers')
class RecommitmentHTTP(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=shared_tests.GuidedHTTP.asyncSetUp;asyncTearDown=shared_tests.GuidedHTTP.asyncTearDown;req=shared_tests.GuidedHTTP.req;lead=shared_tests.GuidedHTTP.lead;paid=shared_tests.GuidedHTTP.paid;complete_leader=shared_tests.GuidedHTTP.complete_leader
 async def setup_service(self):
  token,base,row=await self.paid('board-recommitment');ab='/admin/services/board-recommitment/customers/'+row['customer_id']
  await self.req('PUT',base+'/branding',{'primary_color':'#123456'})
  await self.req('PUT',ab+'/tool/reactivation/setup',{'mission':'Help children access learning.','why_recommit':'Clarify who can actively contribute.','board_help_accomplish':'Develop school partnerships.','need_by':'2026-11-01','logo_data_url':''},admin=True)
  await self.req('POST',ab+'/tool/reactivation/recommitment-form/generate',{},admin=True);await self.req('POST',ab+'/tool/reactivation/recommitment-form/approve',{},admin=True)
  return token,base,row,ab
 async def add_person(self,ab,email='member@example.org'):
  result=await self.req('POST',ab+'/participants',{'name':'Sample Board Member','email':email,'role':'Board Member','notes':'Private facilitator note'},admin=True);return result['member']['member_record_id']
 async def submit_person(self,row,pid,choice='active'):
  from guided_recommitment import decisions
  person=await self.db.reactivation_board_members.find_one({'member_record_id':pid});r=await self.req('GET','/board-recommitment/'+person['form_token']);form=r['guided_form'];answers={}
  for q in form['questions']:
   if not q['archived'] and choice in q['show_for']:answers[q['id']]=[q['options'][0]] if q['type']=='multiselect' else q['options'][0] if q['type']=='select' else 'I can introduce two school partners, subject to agreement.'
  result=await self.req('POST','/board-recommitment/'+person['form_token'],{'full_name':person['name'],'email':person['email'],'recommitment':decisions()[choice],'guided_answers':answers},201)
  return person,r,answers
 async def test_free_submission_independent_price_and_one_hour_email(self):
  token,base,row=await self.lead('board-recommitment');self.assertEqual(len(row['question_snapshot']),4);from datetime import datetime,timedelta
  await gs.automation_tick(self.db,datetime.fromisoformat(row['submitted_at'])+timedelta(minutes=60));email=await self.db.workflow_email_deliveries.find_one({'user_id':row['workspace_user_id']});self.assertIn('Recommitted',email['subject']);self.assertIn('/api/services/board-recommitment/pay/',email['link'])
  await self.req('POST',base+'/checkout');self.assertEqual(self.created[0]['metadata']['offer_source'],'rooney_guided_board_recommitment_497')
 async def test_invitation_unique_form_and_duplicate_send_idempotent(self):
  token,base,row,ab=await self.setup_service();pid=await self.add_person(ab);again=await self.add_person(ab);self.assertEqual(pid,again)
  draft=await self.req('POST',ab+'/participants/'+pid+'/message-preview',{'kind':'board_invitation'},admin=True);payload={**draft,'approved':True,'request_id':str(uuid.uuid4())};before=self.mail.call_count
  await self.req('POST',ab+'/participants/'+pid+'/message-send',payload,admin=True);await self.req('POST',ab+'/participants/'+pid+'/message-send',payload,admin=True);self.assertEqual(self.mail.call_count,before+1)
  self.assertIn('Clarify who can actively contribute',draft['body']);self.assertIn('/board-recommitment/',draft['link']);self.assertNotIn('497',draft['body'])
 async def test_all_three_decisions_saved_without_automatic_role_change(self):
  token,base,row,ab=await self.setup_service()
  for choice in ('active','advisory','step_down'):
   pid=await self.add_person(ab,choice+'@example.org');person,form,answers=await self.submit_person(row,pid,choice);saved=await self.db.reactivation_board_members.find_one({'member_record_id':pid});self.assertEqual(saved['response']['decision_id'],choice);self.assertEqual(saved['response']['guided_answers'],answers);self.assertNotIn('decision_confirmed',saved);self.assertNotIn('conversation_outcome',saved)
   notice=await self.db.workflow_email_deliveries.find_one({'event_key':'guided-recommitment-response-'+pid});self.assertEqual(notice['recipient'],row['email']);self.assertIn('/services/board-recommitment/resources/',notice['link'])
 async def test_question_versions_and_private_participant_isolation(self):
  token,base,row,ab=await self.setup_service();pid=await self.add_person(ab);person=await self.db.reactivation_board_members.find_one({'member_record_id':pid});original=await self.req('GET','/board-recommitment/'+person['form_token']);config=await self.req('GET','/admin/services/board-recommitment/settings',admin=True);c=config['config'];c['participant_form']['questions'][0]['prompt']='A newly published question';saved=await self.req('PUT','/admin/services/board-recommitment/draft',{'config':c,'revision':config['revision']},admin=True);await self.req('POST','/admin/services/board-recommitment/publish',{'revision':saved['revision']},admin=True)
  old=await self.req('GET','/board-recommitment/'+person['form_token']);self.assertEqual(old['guided_form'],original['guided_form']);self.assertNotIn('participants',old)
  t2,b2,row2=await self.paid('board-recommitment');await self.req('POST',b2+'/participants/'+pid+'/message-preview',{'kind':'board_invitation'},404)
 async def test_interpretation_conversation_edit_approve_email_and_decision(self):
  token,base,row,ab=await self.setup_service();pid=await self.add_person(ab);await self.submit_person(row,pid)
  for action in ('analysis','conversation-script'):await self.req('POST',ab+'/tool/reactivation/board-members/'+pid+'/'+action,{},admin=True)
  for _ in range(30):
   docs=await self.db.generated_materials.find({'user_id':row['workspace_user_id'],'application_id':pid}).to_list(20)
   if len(docs)>=2 and all(m['status']!='Generating' for m in docs):break
   await asyncio.sleep(.02)
  guide=next(m for m in docs if m['type']=='reactivation_conversation_script');await self.req('PUT',base+'/conversation/'+guide['material_id'],{'display_text':'Ask which introductions they can realistically make and what support they need.'});guide=await self.db.generated_materials.find_one({'material_id':guide['material_id']});before=self.mail.call_count
  for _ in range(2):await self.req('POST',base+'/conversation/'+guide['material_id']+'/approve',{'version':guide['current_version']})
  self.assertEqual(self.mail.call_count,before+1)
  await self.req('PUT',ab+'/participants/'+pid+'/decision',{'outcome':'Continuing as an Active Board Member','role':'Partnerships Board Member','conclusion':'Two school introductions, after confirming availability.','confirmed':False},422,True)
  await self.req('PUT',ab+'/participants/'+pid+'/decision',{'outcome':'Continuing as an Active Board Member','role':'Partnerships Board Member','conclusion':'Two school introductions, after confirming availability.','confirmed':True},admin=True)
  await self.req('POST',ab+'/tool/reactivation/board-members/'+pid+'/portfolio',{},admin=True);portfolio=await self.db.generated_materials.find_one({'user_id':row['workspace_user_id'],'application_id':pid,'type':'reactivation_board_member_portfolio'});self.assertIsNotNone(portfolio)
  approved=await self.req('POST',ab+'/tool/reactivation/materials/'+portfolio['material_id']+'/approve-portfolio',{},admin=True)
  download=await self.req('GET','/portfolio/'+approved['share_token']+'/pdf')
  self.assertEqual(download.headers['content-type'],'application/pdf');self.assertEqual(download.headers['cache-control'],'no-store');self.assertTrue(download.content.startswith(b'%PDF-'))
  from io import BytesIO
  from pypdf import PdfReader
  text='\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(download.content)).pages)
  self.assertIn('Sample Learning Nonprofit',text);self.assertIn('Sample Board Member',text)
  await self.req('GET','/portfolio/not-a-valid-portfolio-token/pdf',status=404)
  draft=await self.req('POST',ab+'/participants/'+pid+'/message-preview',{'kind':'portfolio_delivery'},admin=True);self.assertIn('/portfolio/',draft['link'])
  await self.req('POST',ab+'/participants/'+pid+'/message-send',{**draft,'request_id':str(uuid.uuid4()),'approved':True},admin=True);await self.req('POST',ab+'/deliver',{'approved':True,'request_id':str(uuid.uuid4())},admin=True)
 async def test_confirmation_communications_require_actual_confirmed_decision(self):
  token,base,row,ab=await self.setup_service();pid=await self.add_person(ab);await self.submit_person(row,pid,'step_down')
  await self.req('POST',ab+'/participants/'+pid+'/message-preview',{'kind':'step_down_acknowledgement'},409,True)
  await self.req('PUT',ab+'/participants/'+pid+'/decision',{'outcome':'Stepping Down From the Board','role':'','conclusion':'Departure acknowledged after the organization completed its required procedure.','confirmed':True},admin=True)
  await self.req('POST',ab+'/participants/'+pid+'/message-preview',{'kind':'step_down_acknowledgement'},admin=True);await self.req('POST',ab+'/tool/reactivation/board-members/'+pid+'/portfolio',{},409,True)
