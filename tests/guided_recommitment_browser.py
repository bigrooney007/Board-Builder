"""Part Three desktop/mobile: paid setup, actual board form and admin decisions."""
import asyncio,json,os,uuid
from pathlib import Path
from playwright.async_api import async_playwright,expect
from quote_browser_helpers import complete_leader,start_quote,open_customer_dashboard
BASE='http://127.0.0.1:8765'
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'
async def main():
 results=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch()
  for width in (1440,390):
   ctx=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844});auth=(await (await ctx.request.get(BASE+'/__test/session')).json())['token'];headers={'Authorization':'Bearer '+auth}
   page=await ctx.new_page();token,row=await start_quote(page,'board-recommitment','Sample Recommitment Leader',f'recommit-leader-{width}@example.org','Sample Recommitment Organization',width,landing='/board-recommitment');base='/api/services/board-recommitment/customer/'+token;ident=row['customer_id'];ab='/api/admin/services/board-recommitment/customers/'+ident
   await page.wait_for_url('**/services/board-recommitment/received/*');await page.goto(BASE+'/services/board-recommitment/offer/'+token);await page.get_by_role('button',name='ACTIVATE MY BOARD RECOMMITMENT',exact=True).click();await page.get_by_role('button',name='Complete Payment',exact=True).click();await page.wait_for_url('**/services/board-recommitment/setup/*');await complete_leader(page,'board-recommitment',token,width);await page.get_by_role('button',name='SAVE ORGANIZATION BRANDING',exact=True).click();await page.get_by_role('link',name='BOOK MY BOARD RECOMMITMENT ACTIVATION CALL →',exact=True).wait_for()
   await ctx.add_cookies([{'name':'admin_access_token','value':auth,'url':BASE,'httpOnly':True,'sameSite':'Lax'}]);await page.screenshot(path=f'test_reports/current-flow-recommitment-booking-{width}.png',full_page=True);await open_customer_dashboard(page,'board-recommitment',ident);await page.get_by_label("Organization's mission",exact=True).fill('Help children access learning.');await page.get_by_label('Why recommitment is needed',exact=True).fill('Clarify which contributions members can make.');await page.get_by_label('Agreed responsibilities and intended contributions',exact=True).fill('Help develop school partnerships.');await page.get_by_label('Requested response deadline',exact=True).fill('2026-11-30');await page.get_by_role('button',name='Save Recommitment Setup',exact=True).click();await page.get_by_role('button',name='Prepare Recommitment Form',exact=True).click();await page.get_by_role('button',name='Approve Recommitment Form',exact=True).click();await page.screenshot(path=f'test_reports/current-workstation-recommitment-{width}.png',full_page=True)
   await expect(page.get_by_label('Board member full name',exact=True)).to_have_count(1);await page.get_by_label('Board member full name',exact=True).fill('Sample Board Member');await page.get_by_label('Board member email address',exact=True).fill(f'recommit-member-{width}@example.org');await page.get_by_role('button',name='Add Board Member',exact=True).click();await page.get_by_role('button',name='Prepare or Resend Invitation',exact=True).first.click();await page.get_by_test_id('service-email-composer').wait_for();await page.get_by_role('button',name='Approve and Send Email',exact=True).click()
   data=await (await ctx.request.get(BASE+ab+'/recommitment',headers=headers)).json();person=data['participants'][0];form_token=person['form_url'].rsplit('/',1)[1];form=await (await ctx.request.get(BASE+'/api/board-recommitment/'+form_token)).json()
   member=await ctx.new_page();await member.goto(person['form_url'].replace('https://nonprofitboardbuilder.com',BASE));await member.get_by_label(form['guided_form']['labels']['active'],exact=True).check()
   for q in form['guided_form']['questions']:
    if q['archived'] or 'active' not in q['show_for']:continue
    section=member.locator('section.guided-question').filter(has=member.get_by_role('heading',name=q['prompt'],exact=True))
    if q['type']=='multiselect':await section.get_by_role('checkbox').first.check()
    elif q['type']=='select':await section.get_by_role('combobox').select_option(q['options'][0])
    else:await section.get_by_label('Your answer',exact=True).fill('I can discuss introducing school partners and need support with scheduling.')
   await member.screenshot(path=f'test_reports/current-flow-recommitment-member-form-{width}.png',full_page=True);await member.get_by_role('button',name='SAVE MY RECOMMITMENT RESPONSE',exact=True).click();await member.get_by_role('heading',name='Thank You for Sharing Your Decision',exact=True).wait_for();assert await member.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2')
   await page.get_by_role('button',name='Refresh Recommitment Responses',exact=True).click();await page.get_by_role('button',name='Review Board Member',exact=True).first.click();await page.get_by_role('button',name='Prepare Response Interpretation',exact=True).click();await page.get_by_role('button',name='Generate Conversation Guide',exact=True).click();await page.get_by_label('Agreed role',exact=True).fill('Partnerships Board Member');await page.get_by_label('Agreed responsibilities, availability, support and next steps',exact=True).fill('Discuss and agree on two school introductions before any commitment is made.');await page.get_by_role('checkbox',name="This records the member's agreement",exact=False).check();await page.get_by_role('button',name='Save Confirmed Recommitment Decision',exact=True).click();await page.get_by_role('button',name='Generate Agreed Board Member Portfolio',exact=True).click();assert await page.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2');await page.screenshot(path=f'test_reports/current-guided-recommitment-{width}.png',full_page=True)
   hand=await ctx.request.post(BASE+'/api/admin/services/board-recommitment/customers/'+ident+'/handover',headers=headers,data={'prepared_confirmed':True});assert hand.ok,await hand.text()
   invitation=await hand.json();owner=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844});client=await owner.new_page()
   await client.goto(BASE+invitation['url'].split('8765')[-1]);await client.get_by_role('button',name='OPEN MY DASHBOARD',exact=True).click();await client.wait_for_url('**/services/board-recommitment/dashboard/*')
   await client.get_by_role('heading',name='Recommitment Setup',exact=True).first.wait_for();await client.screenshot(path=f'test_reports/current-workstation-board-recommitment-client-{width}.png',full_page=True)
   assert await client.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2');await owner.close()
   results.append({'width':width,'case':'free_paid_branding_setup_invitation_active_response_interpretation_confirmed_decision_portfolio','passed':True});await ctx.close()
  await browser.close()
 Path('test_reports/current-guided-recommitment-browser.json').write_text(json.dumps(results,indent=2));print('PASS guided Recommitment browser checks:',len(results))
asyncio.run(main())
