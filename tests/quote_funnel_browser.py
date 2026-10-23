"""Current public quote + immediate test email + owner paid setup on desktop/mobile."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright,expect
from quote_browser_helpers import complete_leader
BASE='http://127.0.0.1:8765'
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'
SERVICES=[('recruitment','/recruit'),('board-recommitment','/board-recommitment'),('board-fundraising','/board-fundraising'),('strategic-planning','/strategic-planning')]

async def main():
 results=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch(args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'])
  for width in (1440,390):
   ctx=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844},permissions=['camera','microphone'])
   auth=(await (await ctx.request.get(BASE+'/__test/session')).json())['token'];headers={'Authorization':'Bearer '+auth}
   page=await ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   for service,path in SERVICES:
    await page.goto(BASE+path);await page.get_by_role('button',name='GET A FREE QUOTE',exact=True).first.click()
    await page.get_by_label('Full name',exact=True).fill('Quote Flow Reviewer');await page.get_by_label('Email address',exact=True).fill('fundraisingschoolfornonprofits@gmail.com');await page.get_by_label('Organization name',exact=True).fill('Example Learning Organization')
    await page.get_by_role('button',name='CONTINUE TO MY QUOTE',exact=True).click();await page.wait_for_url(f'**/services/{service}/start?lead=*');token=page.url.split('lead=')[1]
    row=await (await ctx.request.get(BASE+f'/api/services/{service}/customer/{token}')).json();ident=row['customer_id'];assert row['client_flow_test']
    for i,q in enumerate(row['question_snapshot']):
     value='3' if q['type']=='number' or q['key'] in {'desired_count','board_count'} else '2027-12-31' if q['key']=='fundraising_deadline' else 'Build relationships with local businesses and expand our education work.'
     await page.get_by_label('Your answer',exact=True).fill(value)
     if q['key']=='desired_outcome_impact':await page.screenshot(path=f'test_reports/current-quote-{service}-impact-{width}.png',full_page=True)
     await page.get_by_role('button',name='GET MY FREE QUOTE' if i==len(row['question_snapshot'])-1 else 'SAVE AND CONTINUE',exact=True).click()
     if i<len(row['question_snapshot'])-1:await expect(page.get_by_text(f'Question {i+2} of {len(row["question_snapshot"])}',exact=True)).to_be_visible()
    await page.wait_for_url(f'**/services/{service}/received/*');await page.screenshot(path=f'test_reports/current-quote-{service}-received-{width}.png',full_page=True)
    record=await (await ctx.request.get(BASE+f'/api/admin/services/{service}/customers/{ident}',headers=headers)).json()
    assert record['customer']['desired_outcome_impact']=='Build relationships with local businesses and expand our education work.'
    assert record['customer']['first_email_sent_at'];assert len(record['deliveries'])==1
    assert record['deliveries'][0]['status']=='sent';assert record['customer']['payment_status']=='unpaid'
    assert 'local businesses' in record['deliveries'][0]['text']
    denied=await ctx.request.post(BASE+f'/api/services/{service}/customer/{token}/checkout');assert denied.status==409
    await ctx.add_cookies([{'name':'admin_access_token','value':auth,'url':BASE,'httpOnly':True,'sameSite':'Lax'}])
    await page.goto(BASE+f'/admin/services/{service}?customer={ident}');await page.get_by_test_id('guided-customer-workspace').wait_for();await page.get_by_role('heading',name='What This Customer Wants to Accomplish',exact=True).wait_for()
    assert await page.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2')
    await page.screenshot(path=f'test_reports/current-quote-{service}-owner-table-{width}.png',full_page=True)
    if service=='recruitment':
     await page.get_by_role('button',name='Record Video',exact=True).click();await page.get_by_role('button',name='Stop Recording',exact=True).wait_for();await page.wait_for_timeout(1200);await page.get_by_role('button',name='Stop Recording',exact=True).click();await page.get_by_role('button',name='Save Private Recording',exact=True).click();await page.get_by_text('Video status: recorded',exact=True).wait_for();await expect(page.get_by_role('button',name='Submit to Moses for Editing',exact=True)).to_be_disabled();await page.screenshot(path=f'test_reports/current-quote-recording-contract-pending-{width}.png',full_page=True)
    await page.get_by_role('button',name='Test Post-Payment Journey',exact=True).click();await page.wait_for_url(f'**/services/{service}/setup/*');paid_token=page.url.split('/')[-1]
    await complete_leader(page,service,paid_token,width)
    await page.get_by_role('button',name='SAVE ORGANIZATION BRANDING',exact=True).click();await page.get_by_role('link',name='BOOK MY',exact=False).wait_for()
    response=await ctx.request.get(BASE+f'/api/services/{service}/customer/{paid_token}/book',max_redirects=0);assert response.status==303
    await page.screenshot(path=f'test_reports/current-quote-{service}-booking-{width}.png',full_page=True)
    results.append({'service':service,'width':width,'quote_immediate_delivery_postpayment_to_booking':True})
   assert not errors,errors
   await ctx.close()
  await browser.close()
 Path('test_reports/current-quote-browser.json').write_text(json.dumps(results,indent=2));print('PASS current quote browser journeys:',len(results))
asyncio.run(main())
