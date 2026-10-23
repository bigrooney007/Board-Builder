"""Desktop/mobile guided Recruitment actual React/API acceptance."""
import asyncio,json,os,uuid
from pathlib import Path
from playwright.async_api import async_playwright,expect
from quote_browser_helpers import complete_leader
BASE='http://127.0.0.1:8765'
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'
async def main():
 results=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch()
  for width in (1440,390):
   context=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844})
   auth=(await (await context.request.get(BASE+'/__test/session')).json())['token'];headers={'Authorization':'Bearer '+auth}
   page=await context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
   await page.goto(BASE+'/recruit');await page.locator('.recruit-hero .bfg-btn-primary, .guided-hero-cta').first.click()
   await page.get_by_label('Full name',exact=True).fill('Sample Guided Leader');await page.get_by_label('Email address',exact=True).fill(f'guided-{width}@example.org');await page.get_by_label('Organization name',exact=True).fill('Sample Learning Nonprofit')
   await page.get_by_role('button',name='CONTINUE TO MY QUOTE',exact=True).click();await page.wait_for_url('**/services/recruitment/start?lead=*')
   await page.screenshot(path=f'test_reports/current-flow-recruitment-questions-{width}.png',full_page=True)
   token=page.url.split('lead=')[1];base='/api/services/recruitment/customer/'+token
   details=await (await context.request.get(BASE+base)).json();ident=details['customer_id'];ab='/api/admin/services/recruitment/customers/'+ident
   for i in range(len(details['question_snapshot'])):
    await page.get_by_label('Your answer',exact=True).fill('We help children access learning.' if i<len(details['question_snapshot'])-1 else '1')
    await page.get_by_role('button',name='GET MY FREE QUOTE' if i==len(details['question_snapshot'])-1 else 'SAVE AND CONTINUE',exact=True).click()
    if i<len(details['question_snapshot'])-1:await expect(page.get_by_text(f"Question {i+2} of {len(details['question_snapshot'])}",exact=True)).to_be_visible()
   await page.wait_for_url('**/services/recruitment/received/*');await expect(page.get_by_role('heading',name="Your Board Recruitment Quote Request Has Been Received.",exact=True)).to_be_visible();assert 'PAY $497' not in await page.locator('body').inner_text()
   await page.screenshot(path=f'test_reports/current-flow-recruitment-received-{width}.png',full_page=True)
   await page.goto(BASE+'/services/recruitment/offer/'+token);await page.get_by_role('button',name='ACTIVATE MY BOARD RECRUITMENT',exact=True).wait_for();await page.screenshot(path=f'test_reports/current-flow-recruitment-offer-{width}.png',full_page=True);await page.get_by_role('button',name='ACTIVATE MY BOARD RECRUITMENT',exact=True).click();await page.get_by_role('heading',name='Controlled Stripe checkout: $497',exact=True).wait_for();await page.get_by_role('button',name='Complete Payment',exact=True).click()
   await page.wait_for_url('**/services/recruitment/setup/*');await complete_leader(page,'recruitment',token,width);await page.get_by_label('Primary organization color',exact=True).wait_for();await page.screenshot(path=f'test_reports/current-flow-recruitment-branding-{width}.png',full_page=True);await page.get_by_label('Primary organization color',exact=True).fill('#123456');await page.get_by_role('button',name='SAVE ORGANIZATION BRANDING',exact=True).click();await page.get_by_role('link',name='BOOK MY BOARD RECRUITMENT ACTIVATION CALL →',exact=True).wait_for()
   await context.add_cookies([{'name':'admin_access_token','value':auth,'url':BASE,'httpOnly':True,'sameSite':'Lax'}])
   assert (await context.request.post(BASE+'/__test/guided-work/'+ident)).ok
   await page.goto(BASE+'/admin/services/recruitment');await page.get_by_role('button',name='Open Service Workspace',exact=True).first.click()
   await page.get_by_label('Role or profile',exact=True).wait_for();await page.screenshot(path=f'test_reports/current-workstation-recruitment-{width}.png',full_page=True);await page.get_by_role('button',name='Approve Agreed Board Member Profiles',exact=True).click()
   await page.get_by_label('Available interview dates and times',exact=True).fill('October 30, 2026 at 10:00 UTC');await page.get_by_role('button',name='Save Interview Arrangements',exact=True).click();
   async with page.expect_response(lambda r: r.url.endswith('/generate-materials') and r.request.method=='POST') as queued:
    await page.get_by_role('button',name='GENERATE RECRUITMENT MATERIALS',exact=True).click()
   assert (await queued.value).ok
   assert (await context.request.post(BASE+'/__test/guided-work/'+ident)).ok
   await page.get_by_role('button',name='Refresh Generated Resources',exact=True).click();await page.get_by_text('Board Member Manual · Generated',exact=True).wait_for();await page.screenshot(path=f'test_reports/current-flow-recruitment-materials-{width}.png',full_page=True)
   docs=await (await context.request.get(BASE+ab+'/tool/workspace/materials',headers=headers)).json()
   for doc in docs['materials']:
    response=await context.request.post(BASE+ab+'/tool/workspace/materials/'+doc['material_id']+'/approve',headers=headers,data={});assert response.ok,await response.text()
   page.on('dialog',lambda d:d.accept())
   await page.get_by_role('button',name='LAUNCH BOARD RECRUITMENT CAMPAIGN',exact=True).click();await page.get_by_role('link',name='Open Published Campaign and Application',exact=True).wait_for()
   await page.get_by_role('button',name='SEND RECRUITMENT MATERIALS',exact=True).click();await page.get_by_role('button',name='Approve and Send Email',exact=True).click();await expect(page.get_by_test_id('service-email-composer')).to_have_count(0)
   await page.goto(BASE+'/services/recruitment/resources/'+token);await page.get_by_role('heading',name='Your Board Recruitment Resources',exact=True).wait_for();await expect(page.get_by_text('Sample Learning Nonprofit',exact=True).first).to_be_visible()
   assert await page.locator('body').evaluate('e=>e.scrollWidth<=window.innerWidth+2');assert not errors,errors
   await page.screenshot(path=f'test_reports/current-guided-recruitment-{width}.png',full_page=True)
   hand=await context.request.post(BASE+'/api/admin/services/recruitment/customers/'+ident+'/handover',headers=headers,data={'prepared_confirmed':True});assert hand.ok,await hand.text()
   invitation=await hand.json();owner=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844});client=await owner.new_page()
   await client.goto(BASE+invitation['url'].split('8765')[-1]);await client.get_by_role('button',name='OPEN MY DASHBOARD',exact=True).click();await client.wait_for_url('**/services/recruitment/dashboard/*')
   await client.get_by_role('heading',name='Board Member Recommendations',exact=True).first.wait_for();await client.screenshot(path=f'test_reports/current-workstation-recruitment-client-{width}.png',full_page=True)
   assert await client.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2');await owner.close()
   results.append({'width':width,'case':'free_intake_payment_branding_admin_approval_campaign_and_resources','passed':True})
   await page.goto(BASE+'/admin/services/recruitment');await page.get_by_role('button',name='Refresh Customer Records',exact=True).wait_for();await page.get_by_role('button',name='Entry Questions',exact=True).click();await expect(page.get_by_role('heading',name='Entry Questions',exact=True)).to_be_visible();print('Question editor accessible names:',await page.locator('textarea').evaluate_all('(elements)=>elements.map(e=>({label:e.getAttribute("aria-label"),parent:e.parentElement.tagName}))'));await page.screenshot(path=f'test_reports/current-guided-question-editor-{width}.png',full_page=True);Path(f'test_reports/current-guided-question-editor-{width}.html').write_text(await page.content());await page.get_by_label('Question 1 wording',exact=True).fill('What does your organization want its board to help accomplish?');await page.get_by_role('button',name='Save and Publish Settings',exact=True).click();await page.get_by_role('status').filter(has_text='published').wait_for();await page.reload();await page.get_by_role('button',name='Entry Questions',exact=True).click();await expect(page.get_by_label('Question 1 wording',exact=True)).to_have_value('What does your organization want its board to help accomplish?')
   response=await context.request.get(BASE+'/api/services/recruitment/questions');assert (await response.json())['questions'][0]['prompt']=='What does your organization want its board to help accomplish?'
   results.append({'width':width,'case':'admin_question_edit_publish_persistence_actual_customer_questions','passed':True})
   await context.close()
  await browser.close()
 Path('test_reports/current-guided-browser.json').write_text(json.dumps(results,indent=2));print('PASS guided Recruitment browser checks:',len(results))
asyncio.run(main())
