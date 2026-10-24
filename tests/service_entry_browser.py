"""Four real offer editors, single-page quote forms and separate customer profiles."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright,expect
from quote_browser_helpers import start_quote
BASE='http://127.0.0.1:8765'
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'
SERVICES=[('recruitment','/recruit'),('board-recommitment','/board-recommitment'),('strategic-planning','/strategic-planning'),('board-fundraising','/board-fundraising')]
async def main():
 results=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch()
  for width in (1440,390):
   ctx=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844});auth=(await (await ctx.request.get(BASE+'/__test/session')).json())['token'];headers={'Authorization':'Bearer '+auth};await ctx.add_cookies([{'name':'admin_access_token','value':auth,'url':BASE,'httpOnly':True,'sameSite':'Lax'}]);page=await ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   for service,path in SERVICES:
    base='/api/admin/services/'+service;original=(await (await ctx.request.get(BASE+base+'/settings',headers=headers)).json())['config']
    homepage=(await (await ctx.request.get(BASE+'/api/platform/homepages/'+service)).json()).get('content') or {}
    fundraising=(await (await ctx.request.get(BASE+'/api/admin/fundraising/content',headers=headers)).json())['content'] if service=='board-fundraising' else None
    try:
     await page.goto(BASE+'/admin/services/'+service);await page.get_by_role('link',name='Edit Landing Page',exact=True).click();await page.wait_for_url('**/settings/landing')
     heading='Our '+service.replace('-',' ').title()+' Process '+str(width)
     await page.get_by_label('Page heading' if service=='board-fundraising' else 'Headline',exact=True).fill(heading)
     await page.get_by_role('button',name='Save Website Content' if service=='board-fundraising' else 'SAVE HOME PAGE TEXT',exact=True).click();await page.get_by_text('Home page text saved.' if service!='board-fundraising' else 'Your changes are saved. Refresh the public page to see them.',exact=True).wait_for()
     await page.reload();await expect(page.get_by_label('Page heading' if service=='board-fundraising' else 'Headline',exact=True)).to_have_value(heading)
     await page.goto(BASE+'/admin/services/'+service);await page.get_by_role('link',name='Edit Quote Form',exact=True).click();await page.wait_for_url('**/settings/quote')
     await page.get_by_label('Number of questions to show',exact=True).fill('2');await page.get_by_role('button',name='Apply Question Count',exact=True).click();subtitle='Tell us about your organization. Your quote will arrive by email in one hour.'
     await page.get_by_label('Quote form subtitle',exact=True).fill(subtitle);await page.get_by_role('button',name='Save and Publish',exact=True).click();await page.get_by_role('status').filter(has_text='published').wait_for();await page.reload();await expect(page.get_by_label('Number of questions to show',exact=True)).to_have_value('2')
     confirmation='We received your request. Look out for our email in your inbox within one hour.'
     for section,label,value in [('confirmation','Confirmation message',confirmation),('first-email','First Email message',original['first_email']['body']+'\n\nWe look forward to helping your organization.'),('followups','Follow-Up 1 message',original['followups'][0]['body']+'\n\nYour organization can return when ready.'),('post-payment','Question 1 subtitle','Tell us the details in your own words.')]:
      await page.goto(BASE+'/admin/services/'+service+'/settings/'+section);await page.get_by_label(label,exact=True).fill(value);await page.get_by_role('button',name='Save and Publish',exact=True).click();await page.get_by_role('status').filter(has_text='published').wait_for();await page.reload();await expect(page.get_by_label(label,exact=True)).to_have_value(value)
      if section=='first-email':
       await expect(page.get_by_label('Delay after completed quote submission (minutes)',exact=True)).to_have_value('60');await page.get_by_role('button',name='Preview First Email',exact=True).click();await expect(page.locator('.service-email-preview')).to_contain_text('We look forward to helping your organization.')
      elif section=='followups':await expect(page.get_by_label('Minutes after previous successful email',exact=True).first).to_have_value('2880')
     await page.goto(BASE+path);await expect(page.locator('h1')).to_have_text(heading);await page.get_by_role('button',name='GET A FREE QUOTE',exact=True).first.click();await page.wait_for_url('**/services/'+service+'/quote');await page.get_by_test_id('service-quote-form').wait_for();await expect(page.get_by_text(subtitle,exact=True)).to_be_visible();await expect(page.get_by_role('dialog')).to_have_count(0)
     assert await page.locator('form input[type="password"]').count()==0
     assert await page.locator('form input,form textarea,form select').count()==5
     token,row=await start_quote(page,service,'Edited Quote '+service+' '+str(width),'edited-'+service+'-'+str(width)+'@example.org','Sample Community Organization',width,landing=path)
     await page.get_by_role('heading',name=original['customer_copy']['received_heading'],exact=True).wait_for();await expect(page.get_by_text(confirmation,exact=True)).to_be_visible()
     await page.goto(BASE+'/admin/services/'+service);await page.get_by_role('link',name='Edited Quote '+service+' '+str(width),exact=True).click();await page.wait_for_url('**/customers/'+row['customer_id']);await page.get_by_test_id('service-customer-profile').wait_for();await expect(page.get_by_test_id('service-customer-list')).to_have_count(0);await expect(page.get_by_test_id('customer-quote-answers')).to_be_visible();assert await page.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2')
     await page.screenshot(path='test_reports/current-separate-customer-profile-'+service+'-'+str(width)+'.png',full_page=True)
     results.append({'service':service,'width':width,'landing_and_quote_edits_persist_single_page_form_and_separate_profile':True})
    finally:
     current=await (await ctx.request.get(BASE+base+'/settings',headers=headers)).json();draft=await ctx.request.put(BASE+base+'/draft',headers=headers,data={'config':original,'revision':current['revision']});assert draft.ok,await draft.text();published=await ctx.request.post(BASE+base+'/publish',headers=headers,data={'revision':(await draft.json())['revision']});assert published.ok,await published.text()
     if fundraising is not None:response=await ctx.request.put(BASE+'/api/admin/fundraising/content',headers=headers,data=fundraising)
     else:response=await ctx.request.put(BASE+'/api/admin/platform/homepages/'+service,headers=headers,data={'content':homepage})
     assert response.ok,await response.text()
   assert not errors,errors;await ctx.close()
  await browser.close()
 Path('test_reports/current-service-entry-browser.json').write_text(json.dumps(results,indent=2));print('PASS service entry and editor browser checks:',len(results))
asyncio.run(main())
