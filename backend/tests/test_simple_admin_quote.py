"""The owner's single-page quote and separate customer/dashboard navigation contract."""
import copy,json,os,secrets,unittest,uuid
from datetime import datetime,timedelta,timezone
from http.cookies import SimpleCookie
from urllib.parse import urlsplit,parse_qs
import test_guided_services as shared
import guided_services as gs
from guided_service_defaults import defaults,PRICES

class SimpleDefaults(unittest.TestCase):
 def test_exact_quote_sets_and_48_hour_followups(self):
  keys={'recruitment':['leader_role','desired_count','recruitment_timing','location_preference','desired_outcome_impact'],'board-recommitment':['leader_role','board_count','why_recommit','recommitment_timing'],'board-fundraising':['leader_role','board_size','fundraising_goal','desired_outcome_impact'],'strategic-planning':['leader_role','board_count','desired_outcome_impact']}
  for service,expected in keys.items():
   c=defaults(service);self.assertEqual([q['key'] for q in c['question_groups']['entry']],expected)
   self.assertEqual(c['first_email']['delay_minutes'],60)
   self.assertEqual([t['after_previous_minutes'] for t in c['followups']],[2880]*5)
   self.assertNotIn('video_email',c);gs.validate_config(service,c)

@unittest.skipUnless(os.environ.get('RECOVERY_ACCEPTANCE')=='1','Disposable Mongo and controlled providers required')
class SimpleHTTP(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=shared.GuidedHTTP.asyncSetUp
 asyncTearDown=shared.GuidedHTTP.asyncTearDown
 req=shared.GuidedHTTP.req
 lead=shared.GuidedHTTP.lead
 paid=shared.GuidedHTTP.paid
 complete_leader=shared.GuidedHTTP.complete_leader
 async def quote(self,service='recruitment',**extra):
  form=await self.req('GET','/services/'+service+'/questions')
  values={q['id']:('100000' if q['key']=='fundraising_goal' else '3' if q['key'] in {'desired_count','board_size','board_count'} else 'Within two months' if 'timing' in q['key'] else 'We need board members to build school partnerships.') for q in form['questions']}
  payload={'request_id':str(uuid.uuid4()),'name':'Customer Leader','email':'customer@example.org','organization':'Community Learning','answers':values,'question_version':form['version'],**extra}
  result=await self.req('POST','/services/'+service+'/quote',payload,201)
  row=await self.db.guided_service_customers.find_one({'customer_id':result['customer_id']},{'_id':0})
  return payload,result,row
 async def test_all_four_single_page_quotes_save_once_and_first_email_waits_one_hour(self):
  for service in PRICES:
   payload,result,row=await self.quote(service)
   self.assertEqual(row['answers'],payload['answers']);self.assertEqual(row['name'],payload['name']);self.assertEqual(row['payment_status'],'unpaid')
   again=await self.req('POST','/services/'+service+'/quote',payload,201);self.assertEqual(again,result)
   at=datetime.fromisoformat(row['submitted_at'])
   before=self.mail.call_count
   await gs.automation_tick(self.db,at+timedelta(minutes=59),only_id=row['customer_id']);self.assertEqual(self.mail.call_count,before)
   await gs.automation_tick(self.db,at+timedelta(hours=1),only_id=row['customer_id']);self.assertEqual(self.mail.call_count,before+1)
   self.assertIn('$497',self.mail.call_args.args[0]['html'])
   await gs.automation_tick(self.db,at+timedelta(hours=1),only_id=row['customer_id']);self.assertEqual(self.mail.call_count,before+1)
 async def test_followups_begin_48_hours_after_successful_first_delivery_and_stop_on_payment(self):
  for service in PRICES:
   _,_,row=await self.quote(service);first=datetime.fromisoformat(row['submitted_at'])+timedelta(hours=1)
   await gs.automation_tick(self.db,first,only_id=row['customer_id']);count=self.mail.call_count
   await gs.automation_tick(self.db,first+timedelta(hours=47,minutes=59),only_id=row['customer_id']);self.assertEqual(self.mail.call_count,count)
   await gs.automation_tick(self.db,first+timedelta(hours=48),only_id=row['customer_id']);self.assertEqual(self.mail.call_count,count+1)
   await gs.automation_tick(self.db,first+timedelta(hours=96),only_id=row['customer_id']);self.assertEqual(self.mail.call_count,count+2)
   await self.db.guided_service_customers.update_one({'customer_id':row['customer_id']},{'$set':{'payment_status':'paid','purchased_package':'self-facilitated' if service in {'strategic-planning','board-fundraising'} else 'guided'}})
   await gs.automation_tick(self.db,first+timedelta(days=20),only_id=row['customer_id'])
   sales=await self.db.workflow_email_deliveries.count_documents({'user_id':row['workspace_user_id'],'event_key':{'$regex':'^guided-followup-'}});self.assertEqual(sales,2)
 async def test_invalid_quote_does_not_create_a_customer_and_questions_have_versions(self):
  form=await self.req('GET','/services/recruitment/questions')
  payload={'request_id':str(uuid.uuid4()),'name':'Leader','email':'leader@example.org','organization':'Org','answers':{},'question_version':form['version']}
  await self.req('POST','/services/recruitment/quote',payload,422)
  self.assertEqual(await self.db.guided_service_customers.count_documents({}),0)
  _,_,row=await self.quote();saved=copy.deepcopy(row['question_snapshot'])
  current=await self.req('GET','/admin/services/recruitment/settings',admin=True);c=current['config'];c['question_groups']['entry']=c['question_groups']['entry'][:2]
  draft=await self.req('PUT','/admin/services/recruitment/draft',{'config':c,'revision':current['revision']},admin=True);await self.req('POST','/admin/services/recruitment/publish',{'revision':draft['revision']},admin=True)
  self.assertEqual((await self.req('GET','/services/recruitment/questions'))['questions'],c['question_groups']['entry'])
  self.assertEqual((await self.db.guided_service_customers.find_one({'customer_id':row['customer_id']}))['question_snapshot'],saved)
 async def test_customer_lists_hide_samples_but_keep_real_completed_quotes(self):
  _,_,row=await self.quote()
  for email in ['roacreativemarketing@gmail.com','fundraisingschoolfornonprofits@gmail.com','globalbusnonprofitsols@gmail.com','globalbusnonprofitsol@gmail.com']:
   _,_,sample=await self.quote(email=email);await self.db.guided_service_customers.update_one({'customer_id':sample['customer_id']},{'$set':{'quote_form_version':'previous-quote-form'}})
  await self.lead(submitted=False,email='unfinished@example.org')
  for flag in ['internal_test','client_flow_test','test_payment']:
   _,_,sample=await self.quote(email=flag+'@example.org');await self.db.guided_service_customers.update_one({'customer_id':sample['customer_id']},{'$set':{flag:True}})
  records=await self.req('GET','/admin/services/recruitment/customers',admin=True)
  self.assertEqual(records['total'],1);self.assertEqual(records['customers'][0]['customer_id'],row['customer_id'])
  self.assertEqual(await self.db.guided_service_customers.count_documents({}),9)
  self.assertEqual(await self.db.guided_service_customers.count_documents({'archived_from_customer_list':True,'sequence_stopped':True}),7)
  _,_,new=await self.quote(email='fundraisingschoolfornonprofits@gmail.com');self.assertFalse(new['client_flow_test'])
  self.assertEqual((await self.req('GET','/admin/services/recruitment/customers',admin=True))['total'],2)
 async def test_customer_pagination_has_no_embedded_workspace_and_keeps_records(self):
  _,_,row=await self.quote()
  samples=[]
  for n in range(1000):
   item={**row,'customer_id':str(uuid.uuid4()),'workspace_user_id':'guided-'+str(uuid.uuid4()),'token_hash':secrets.token_hex(32),'request_id':str(uuid.uuid4()),'name':'Customer '+str(n).zfill(4),'email':str(n)+'@example.org'};samples.append(item)
  await self.db.guided_service_customers.insert_many(samples)
  first=await self.req('GET','/admin/services/recruitment/customers',admin=True);second=await self.req('GET','/admin/services/recruitment/customers?skip=50',admin=True)
  self.assertEqual(first['total'],1001);self.assertEqual(len(first['customers']),50);self.assertEqual(len(second['customers']),50)
  self.assertFalse({r['customer_id'] for r in first['customers']}&{r['customer_id'] for r in second['customers']})
  single=await self.req('GET','/admin/services/recruitment/customers?search=Customer%200999',admin=True);self.assertEqual(single['total'],1)
 async def test_direct_paid_dashboard_link_is_copyable_reusable_scoped_and_revocable(self):
  await self.req('POST','/admin/services/recruitment/customers/no-id/dashboard-access',{},401)
  _,_,unpaid=await self.quote();await self.req('POST','/admin/services/recruitment/customers/'+unpaid['customer_id']+'/dashboard-access',{},402,True)
  for service in PRICES:
   _,_,row=await self.paid(service);admin='/admin/services/'+service+'/customers/'+row['customer_id']
   link=await self.req('POST',admin+'/dashboard-access',{},admin=True);repeat=await self.req('POST',admin+'/dashboard-access',{},admin=True);self.assertEqual(link,repeat)
   token=parse_qs(urlsplit(link['url']).fragment)['access'][0]
   self.assertNotIn(token,urlsplit(link['url']).path)
   for _ in range(2):
    access=await self.client.post('/api/services/'+service+'/dashboard-access',json={'token':token,'customer_id':row['customer_id']});self.assertEqual(access.status_code,200,access.text)
    cookie=SimpleCookie();cookie.load(access.headers['set-cookie']);headers={'Cookie':'guided_operator_session='+cookie['guided_operator_session'].value}
    response=await self.client.get('/api/services/'+service+'/operator/'+row['customer_id'],headers=headers);self.assertEqual(response.status_code,200,response.text)
    self.assertEqual(response.json()['customer']['customer_id'],row['customer_id'])
    wrong=await self.client.get('/api/services/'+service+'/operator/another-customer',headers=headers);self.assertEqual(wrong.status_code,403)
   await self.req('POST','/services/'+service+'/dashboard-access',{'token':token,'customer_id':'another-customer'},403)
   await self.req('POST',admin+'/revoke-handover',{},admin=True)
   await self.req('POST','/services/'+service+'/dashboard-access',{'token':token},404)
   self.assertEqual((await self.client.get('/api/services/'+service+'/operator/'+row['customer_id'],headers=headers)).status_code,403)
 async def test_video_features_are_removed_and_do_not_send_email(self):
  _,_,row=await self.quote();base='/admin/services/recruitment/customers/'+row['customer_id'];before=self.mail.call_count
  for path,method in [('video-preview','POST'),('video-send','POST'),('video-recording','POST'),('video-assignment','GET')]:await self.req(method,base+'/'+path,{},404,True)
  self.assertEqual(self.mail.call_count,before)
  for service in PRICES:self.assertNotIn('video_email',(await self.req('GET','/admin/services/'+service+'/settings',admin=True))['config'])
