"""One admin button opens each isolated, prefilled paid journey through booking."""
import asyncio,json,os,re
from pathlib import Path
from playwright.async_api import async_playwright,expect
BASE='http://127.0.0.1:8765'
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'
SERVICES=['recruitment','board-recommitment','board-fundraising','strategic-planning']

async def main():
 results=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch()
  for width in (1440,390):
   ctx=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844});auth=(await (await ctx.request.get(BASE+'/__test/session')).json())['token'];headers={'Authorization':'Bearer '+auth};await ctx.add_cookies([{'name':'admin_access_token','value':auth,'url':BASE,'httpOnly':True,'sameSite':'Lax'}]);page=await ctx.new_page();errors=[];requests=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
   await page.route('https://calendly.com/**',lambda route:route.fulfill(status=200,content_type='text/html',body='<h1>Configured Calendly destination reached</h1>'))
   for service in SERVICES:
    admin='/api/admin/services/'+service
    before=(await (await ctx.request.get(BASE+admin+'/customers',headers=headers)).json())['total']
    await page.goto(BASE+'/admin/services/'+service);button=page.locator('.service-shortcuts').get_by_role('button',name='Test Post-Payment Flow',exact=True);await expect(button).to_have_count(1)
    async with page.expect_response(lambda r:r.url.endswith('/services/'+service+'/test-post-payment') and r.request.method=='POST') as launched:await button.click()
    response=await launched.value;assert response.ok,await response.text();sample=await response.json();await page.wait_for_url('**/services/'+service+'/setup/*');token=page.url.rsplit('/',1)[-1];base='/api/services/'+service+'/customer/'+token
    await page.get_by_test_id('paid-leader-questionnaire').wait_for();await page.screenshot(path=f'test_reports/current-admin-post-payment-{service}-start-{width}.png',full_page=True)
    data=await (await ctx.request.get(BASE+base+'/leader-questions')).json();assert all(data['answers'].get(q['id']) for q in data['questions'])
    for i,q in enumerate(data['questions']):
     await expect(page.get_by_role('heading',name=q['prompt'],exact=True)).to_be_visible()
     if q['type'] in ('text','textarea','number','date'):assert await page.get_by_label('Your answer',exact=True).input_value()
     elif q['type']=='select':assert await page.get_by_role('combobox').input_value()
     elif q['type']=='multiselect':assert await page.get_by_role('checkbox').evaluate_all('rows=>rows.some(x=>x.checked)')
     await page.get_by_role('button',name=data['copy']['leader_submit'] if i==len(data['questions'])-1 else 'SAVE AND CONTINUE',exact=True).click()
     if i<len(data['questions'])-1:await expect(page.get_by_text(f'Question {i+2} of {len(data["questions"])}',exact=True)).to_be_visible()
    if service=='board-fundraising':
     await page.get_by_role('button',name='START MY GAME',exact=True).click()
     for _ in range(3):await page.get_by_role('button',name='NO, CONTINUE',exact=True).click()
     assert await page.get_by_role('textbox',name='Your personal participation',exact=True).input_value()
     await page.get_by_role('button',name='REVIEW MY CONTRIBUTION',exact=True).click();await page.get_by_role('button',name='SUBMIT MY CONTRIBUTION',exact=True).click()
    await page.get_by_role('button',name='SAVE ORGANIZATION BRANDING',exact=True).click();booking=page.get_by_role('link',name='BOOK MY',exact=False);await booking.wait_for();assert await page.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2');await page.screenshot(path=f'test_reports/current-admin-post-payment-{service}-booking-{width}.png',full_page=True)
    await booking.click();await page.wait_for_url(re.compile(r'https://calendly\.com/'));await page.get_by_role('heading',name='Configured Calendly destination reached',exact=True).wait_for()
    listed=await (await ctx.request.get(BASE+admin+'/customers',headers=headers)).json();assert listed['total']==before;assert sample['customer_id'] not in {row['customer_id'] for row in listed['customers']}
    saved=await (await ctx.request.get(BASE+admin+'/customers/'+sample['customer_id'],headers=headers)).json();assert saved['customer']['internal_test'];assert saved['customer']['leader_completed_at'];assert saved['customer']['branding_saved_at'];assert saved['customer']['payment_status']=='paid'
    results.append({'service':service,'width':width,'one_button_prefilled_paid_setup_to_calendly_without_quote_charge_or_existing_customer':True})
   assert not any('/checkout' in url or '/quote' in url for url in requests if '/api/services/' in url),requests
   assert not errors,errors;await ctx.close()
  await browser.close()
 Path('test_reports/current-admin-post-payment-browser.json').write_text(json.dumps(results,indent=2));print('PASS one-button admin post-payment browser checks:',len(results))
asyncio.run(main())
