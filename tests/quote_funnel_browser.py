"""Four actual quote/payment/profile/dashboard flows, including fresh-browser access."""
import asyncio,json,os
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright,expect
from quote_browser_helpers import complete_leader,start_quote,open_customer_dashboard
BASE='http://127.0.0.1:8765'
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'
SERVICES=[('recruitment','/recruit'),('board-fundraising','/board-fundraising'),('strategic-planning','/strategic-planning'),('board-recommitment','/board-recommitment')]

async def dashboard_ready(page,service):
 if service=='recruitment':await page.get_by_role('heading',name='Board Member Recommendations',exact=True).wait_for()
 elif service=='board-recommitment':await page.get_by_role('heading',name='Recommitment Setup',exact=True).wait_for()
 elif service=='strategic-planning':await page.get_by_test_id('guided-planning-workspace').wait_for()
 else:await page.get_by_test_id('fundraising-workspace').wait_for()

async def main():
 results=[];Path('test_reports').mkdir(exist_ok=True);logo=Path('test_reports/current-quote-branding.png');Image.new('RGB',(80,80),'#4338ca').save(logo)
 async with async_playwright() as p:
  browser=await p.chromium.launch()
  for width in (1440,390):
   ctx=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844})
   auth=(await (await ctx.request.get(BASE+'/__test/session')).json())['token'];headers={'Authorization':'Bearer '+auth}
   page=await ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   for service,path in SERVICES:
    name='Quote Customer '+service+' '+str(width)
    token,row=await start_quote(page,service,name,'quote-'+service+'-'+str(width)+'@example.org','Example Learning Organization',width,landing=path)
    ident=row['customer_id'];admin='/api/admin/services/'+service+'/customers/'+ident
    await page.get_by_role('heading',name='Thank You. We Have Received Your Request.',exact=True).wait_for()
    await expect(page.get_by_text('We will be in touch within the next few hours. Please look out for our email in your inbox.',exact=True)).to_be_visible()
    await page.screenshot(path=f'test_reports/current-quote-{service}-received-{width}.png',full_page=True)
    record=await (await ctx.request.get(BASE+admin,headers=headers)).json();assert not record['customer'].get('first_email_sent_at');assert not record['deliveries']
    # Advance only this synthetic record's scheduler clock. The production
    # route and background engine still enforce the configured 60-minute delay.
    delivery=await (await ctx.request.post(BASE+'/__test/quote-clock/'+ident)).json();assert delivery['status']=='sent';assert '$497' in delivery['text'];assert '/api/services/'+service+'/pay/' in delivery['link']
    await page.goto(delivery['link']);await page.get_by_role('heading',name='Controlled Stripe checkout: $497',exact=True).wait_for();await page.screenshot(path=f'test_reports/current-email-checkout-{service}-{width}.png',full_page=True);await page.get_by_role('button',name='Complete Payment',exact=True).click()
    await page.wait_for_url('**/services/'+service+'/setup/*');await complete_leader(page,service,token,width)
    await page.locator('input[type="file"]').set_input_files(logo);await page.get_by_label('Primary organization color',exact=True).fill('#4338ca');await page.get_by_role('button',name='SAVE ORGANIZATION BRANDING',exact=True).click();await page.get_by_role('link',name='BOOK MY',exact=False).wait_for()
    response=await ctx.request.get(BASE+f'/api/services/{service}/customer/{token}/book',max_redirects=0);assert response.status==303
    await page.screenshot(path=f'test_reports/current-quote-{service}-booking-{width}.png',full_page=True)
    await ctx.add_cookies([{'name':'admin_access_token','value':auth,'url':BASE,'httpOnly':True,'sameSite':'Lax'}])
    await page.goto(BASE+'/admin');await page.get_by_test_id('service-admin-home').wait_for();await expect(page.get_by_role('link',name='Blog & Content',exact=True)).to_be_visible()
    await page.goto(BASE+'/admin/services/'+service);await page.get_by_role('link',name=name,exact=True).wait_for();await page.screenshot(path=f'test_reports/current-admin-{service}-customer-list-{width}.png',full_page=True);await page.get_by_role('link',name=name,exact=True).click();await page.wait_for_url('**/customers/'+ident)
    await page.get_by_test_id('service-customer-profile').wait_for();await expect(page.get_by_test_id('service-customer-list')).to_have_count(0);await expect(page.get_by_test_id('customer-quote-answers')).to_contain_text(name);await expect(page.get_by_test_id('customer-post-payment-answers')).to_contain_text('#4338ca');await expect(page.get_by_test_id('customer-post-payment-answers').get_by_role('img')).to_be_visible()
    assert await page.get_by_role('button',name='Record Video',exact=True).count()==0
    assert await page.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2')
    await page.screenshot(path=f'test_reports/current-admin-{service}-customer-profile-{width}.png',full_page=True)
    if service=='recruitment':assert (await ctx.request.post(BASE+'/__test/guided-work/'+ident)).ok
    await open_customer_dashboard(page,service,ident);link=page.url;assert '#access=' in link
    await page.screenshot(path=f'test_reports/current-workstation-{service}-direct-owner-{width}.png',full_page=True)
    # A copied address must open for a customer in a fresh browser without
    # administrator credentials, while keeping the same saved organization.
    fresh=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844});customer=await fresh.new_page();await customer.goto(link);await dashboard_ready(customer,service)
    assert await customer.get_by_text('Opening your saved project',exact=False).count()==0
    assert await customer.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2')
    await customer.screenshot(path=f'test_reports/current-workstation-{service}-shared-customer-{width}.png',full_page=True);await customer.reload();await dashboard_ready(customer,service);await fresh.close()
    record=await (await ctx.request.get(BASE+admin,headers=headers)).json();assert record['customer']['payment_status']=='paid';assert record['customer']['leader_completed_at'];assert record['customer']['branding']['primary_color']=='#4338ca'
    results.append({'service':service,'width':width,'single_page_quote_hour_delayed_email_497_payment_paid_form_branding_profile_and_shareable_dashboard':True})
   legacy=await (await ctx.request.post(BASE+'/__test/legacy-sales-lead/board-fundraising')).json()
   await page.goto(legacy['url']);await page.get_by_role('heading',name='Controlled Stripe checkout: $497',exact=True).wait_for()
   await expect(page.locator('.guided-question')).to_have_count(0)
   await page.screenshot(path=f'test_reports/current-legacy-email-checkout-{width}.png',full_page=True)
   await page.get_by_role('button',name='Complete Payment',exact=True).click();await page.wait_for_url('**/services/board-fundraising/setup/*')
   await complete_leader(page,'board-fundraising',legacy['token'],width)
   await page.get_by_role('button',name='SAVE ORGANIZATION BRANDING',exact=True).click();await page.get_by_role('link',name='BOOK MY',exact=False).wait_for()
   results.append({'service':'board-fundraising','width':width,'previously_sent_start_link_goes_to_checkout_before_paid_questions':True})
   await page.goto(BASE+'/admin');await page.get_by_role('link',name='Blog & Content',exact=True).click();await page.wait_for_url('**/admin/blog');await page.get_by_test_id('admin-blog-section').wait_for();await page.get_by_text('Automatic generation and publishing',exact=True).click();await expect(page.get_by_role('checkbox',name='Generate and publish weekday articles automatically',exact=True)).to_be_checked();await page.screenshot(path=f'test_reports/current-admin-blog-automation-{width}.png',full_page=True)
   assert not errors,errors;await ctx.close()
  await browser.close()
 Path('test_reports/current-quote-browser.json').write_text(json.dumps(results,indent=2));print('PASS current quote browser journeys:',len(results))
asyncio.run(main())
