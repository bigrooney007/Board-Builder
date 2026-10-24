"""Exercise the current post-payment form rather than bypassing its new gate."""
from playwright.async_api import expect
BASE='http://127.0.0.1:8765'

async def complete_leader(page,service,token,width=None,audience_player=None):
 await page.get_by_test_id('paid-leader-questionnaire').wait_for()
 data=await (await page.request.get(BASE+f'/api/services/{service}/customer/{token}/leader-questions')).json()
 if data.get('completed'):return
 await page.get_by_test_id('paid-leader-questionnaire').wait_for()
 if width:await page.screenshot(path=f'test_reports/current-flow-{service}-paid-leader-{width}.png',full_page=True)
 if not data.get('details_completed'):
  for i,q in enumerate(data['questions']):
   value=data.get('answers',{}).get(q['id']) or ('3' if q['key'] in ('board_count','board_size','desired_count') else '100000' if q['type']=='number' else '2027-12-31' if q['type']=='date' else 'Help children access learning through agreed programs and partnerships.')
   if q['type']=='multiselect':await page.get_by_role('checkbox',name=q['options'][0],exact=True).check()
   elif q['type']=='select':await page.get_by_role('combobox').select_option(q['options'][0])
   else:await page.get_by_label('Your answer',exact=True).fill(str(value))
   await page.get_by_role('button',name=data['copy']['leader_submit'] if i==len(data['questions'])-1 else 'SAVE AND CONTINUE',exact=True).click()
   if i<len(data['questions'])-1:await expect(page.get_by_text(f'Question {i+2} of {len(data["questions"])}',exact=True)).to_be_visible()
 if service=='board-fundraising':
  if audience_player:await audience_player(page,True)
  else:
   await page.get_by_role('button',name='START MY GAME',exact=True).click()
   for _ in range(3):await page.get_by_role('button',name='NO, CONTINUE',exact=True).click()
   await page.get_by_role('textbox',name='Your personal participation',exact=True).fill('I will discuss practical contributions with our board.')
   await page.get_by_role('button',name='REVIEW MY CONTRIBUTION',exact=True).click();await page.get_by_role('button',name='SUBMIT MY CONTRIBUTION',exact=True).click()
 await page.get_by_role('button',name='SAVE ORGANIZATION BRANDING',exact=True).wait_for()

async def start_quote(page,service,name,email,organization,width=None,values=None,landing=None):
 if landing:
  await page.goto(BASE+landing)
  await page.get_by_role('button',name='GET A FREE QUOTE',exact=True).first.click()
 else:await page.goto(BASE+'/services/'+service+'/quote')
 await page.wait_for_url('**/services/'+service+'/quote')
 await page.get_by_test_id('service-quote-form').wait_for()
 data=await (await page.request.get(BASE+'/api/services/'+service+'/questions')).json()
 copy=data['copy']
 await page.get_by_label(copy['quote_name_label'],exact=True).fill(name)
 await page.get_by_label(copy['quote_email_label'],exact=True).fill(email)
 await page.get_by_label(copy['quote_organization_label'],exact=True).fill(organization)
 for q in data['questions']:
  value=(values or {}).get(q['key']) or ('3' if q['key'] in {'desired_count','board_size','board_count'} else '100000' if q['type']=='number' else '2027-12-31' if q['type']=='date' else 'Within two months' if 'timing' in q['key'] else 'Build education partnerships and help more children access learning.')
  if q['type']=='select':await page.get_by_label(q['prompt'],exact=True).select_option(q['options'][0])
  elif q['type']=='multiselect':await page.get_by_role('checkbox',name=q['options'][0],exact=True).check()
  else:await page.get_by_label(q['prompt'],exact=True).fill(str(value))
 if width:await page.screenshot(path='test_reports/current-quote-form-'+service+'-'+str(width)+'.png',full_page=True)
 async with page.expect_response(lambda r:r.url.endswith('/services/'+service+'/quote') and r.request.method=='POST') as submitted:
  await page.get_by_role('button',name=copy['question_submit'],exact=True).click()
 response=await submitted.value;assert response.status==201,await response.text();result=await response.json()
 await page.wait_for_url('**/services/'+service+'/received/*')
 row=await (await page.request.get(BASE+'/api/services/'+service+'/customer/'+result['token'])).json()
 return result['token'],row

async def open_customer_dashboard(page,service,ident):
 await page.goto(BASE+'/admin/services/'+service+'/customers/'+ident)
 await page.get_by_test_id('service-customer-profile').wait_for()
 await page.get_by_role('button',name='Open Customer Dashboard',exact=True).click()
 await page.wait_for_url('**/services/'+service+'/dashboard/**')
 if service=='recruitment':await page.get_by_role('heading',name='Board Member Recommendations',exact=True).wait_for()
 elif service=='board-recommitment':await page.get_by_role('heading',name='Recommitment Setup',exact=True).wait_for()
 elif service=='strategic-planning':await page.get_by_test_id('guided-planning-workspace').wait_for()
 else:await page.get_by_test_id('fundraising-workspace').wait_for()
