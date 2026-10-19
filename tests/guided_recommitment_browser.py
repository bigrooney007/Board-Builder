"""Part Three desktop/mobile: paid setup, actual board form and admin decisions."""
import asyncio,json,os,uuid
from pathlib import Path
from playwright.async_api import async_playwright,expect
BASE='http://127.0.0.1:8765'
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'
async def main():
 results=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch()
  for width in (1440,390):
   ctx=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844});auth=(await (await ctx.request.get(BASE+'/__test/session')).json())['token'];headers={'Authorization':'Bearer '+auth}
   page=await ctx.new_page();await page.goto(BASE+'/board-recommitment');await page.locator('a[href="/board-recommitment/start"]').first.click();await page.get_by_label('Full name',exact=True).fill('Sample Recommitment Leader');await page.get_by_label('Email address',exact=True).fill(f'recommit-leader-{width}@example.org');await page.get_by_label('Organization name',exact=True).fill('Sample Recommitment Organization');await page.get_by_role('button',name='START FOR FREE',exact=True).click();await page.wait_for_url('**/services/board-recommitment/start?lead=*');token=page.url.split('lead=')[1];base='/api/services/board-recommitment/customer/'+token
   row=await (await ctx.request.get(BASE+base)).json();ident=row['customer_id'];ab='/api/admin/services/board-recommitment/customers/'+ident
   for i in range(len(row['question_snapshot'])):
    await page.get_by_label('Your answer',exact=True).fill('We need to clarify the responsibilities our board members can agree to undertake.');await page.get_by_role('button',name='SAVE MY ANSWERS' if i==len(row['question_snapshot'])-1 else 'SAVE AND CONTINUE',exact=True).click()
   await page.wait_for_url('**/services/board-recommitment/received/*');await page.goto(BASE+'/services/board-recommitment/offer/'+token);await page.get_by_role('button',name='PAY $497 AND BEGIN MY GUIDED SERVICE',exact=True).click();await page.get_by_role('button',name='Complete Payment',exact=True).click();await page.wait_for_url('**/services/board-recommitment/setup/*');await page.get_by_role('button',name='SAVE ORGANIZATION BRANDING',exact=True).click();await page.get_by_role('link',name='BOOK MY BOARD RECOMMITMENT SESSION →',exact=True).wait_for()
   await ctx.add_cookies([{'name':'admin_access_token','value':auth,'url':BASE,'httpOnly':True,'sameSite':'Lax'}]);await page.goto(BASE+'/admin/services/board-recommitment');await page.get_by_role('button',name='Open Service Workspace',exact=True).first.click();await page.get_by_label("Organization's mission",exact=True).fill('Help children access learning.');await page.get_by_label('Why recommitment is needed',exact=True).fill('Clarify which contributions members can make.');await page.get_by_label('Agreed responsibilities and intended contributions',exact=True).fill('Help develop school partnerships.');await page.get_by_label('Requested response deadline',exact=True).fill('2026-11-30');await page.get_by_role('button',name='Save Recommitment Setup',exact=True).click();await page.get_by_role('button',name='Prepare Recommitment Form',exact=True).click();await page.get_by_role('button',name='Approve Recommitment Form',exact=True).click()
   await page.get_by_label('Board member full name',exact=True).fill('Sample Board Member');await page.get_by_label('Board member email address',exact=True).fill(f'recommit-member-{width}@example.org');await page.get_by_role('button',name='Add Board Member',exact=True).click();await page.get_by_role('button',name='Prepare or Resend Invitation',exact=True).first.click();await page.get_by_test_id('service-email-composer').wait_for();await page.get_by_role('button',name='Approve and Send Email',exact=True).click()
   data=await (await ctx.request.get(BASE+ab+'/recommitment',headers=headers)).json();person=data['participants'][0];form_token=person['form_url'].rsplit('/',1)[1];form=await (await ctx.request.get(BASE+'/api/board-recommitment/'+form_token)).json()
   member=await ctx.new_page();await member.goto(person['form_url'].replace('https://nonprofitboardbuilder.com',BASE));await member.get_by_label(form['guided_form']['labels']['active'],exact=True).check()
   for q in form['guided_form']['questions']:
    if q['archived'] or 'active' not in q['show_for']:continue
    section=member.locator('section.guided-question').filter(has=member.get_by_role('heading',name=q['prompt'],exact=True))
    if q['type']=='multiselect':await section.get_by_role('checkbox').first.check()
    elif q['type']=='select':await section.get_by_role('combobox').select_option(q['options'][0])
    else:await section.get_by_label('Your answer',exact=True).fill('I can discuss introducing school partners and need support with scheduling.')
   await member.get_by_role('button',name='SAVE MY RECOMMITMENT RESPONSE',exact=True).click();await member.get_by_role('heading',name='Thank You for Sharing Your Decision',exact=True).wait_for();assert await member.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2')
   await page.get_by_role('button',name='Refresh Recommitment Responses',exact=True).click();await page.get_by_role('button',name='Review Board Member',exact=True).first.click();await page.get_by_role('button',name='Prepare Response Interpretation',exact=True).click();await page.get_by_role('button',name='Generate Conversation Guide',exact=True).click();await page.get_by_label('Agreed role',exact=True).fill('Partnerships Board Member');await page.get_by_label('Agreed responsibilities, availability, support and next steps',exact=True).fill('Discuss and agree on two school introductions before any commitment is made.');await page.get_by_role('checkbox',name="This records the member's agreement",exact=False).check();await page.get_by_role('button',name='Save Confirmed Recommitment Decision',exact=True).click();await page.get_by_role('button',name='Generate Agreed Board Member Portfolio',exact=True).click();assert await page.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2');await page.screenshot(path=f'test_reports/current-guided-recommitment-{width}.png',full_page=True)
   results.append({'width':width,'case':'free_paid_branding_setup_invitation_active_response_interpretation_confirmed_decision_portfolio','passed':True});await ctx.close()
  await browser.close()
 Path('test_reports/current-guided-recommitment-browser.json').write_text(json.dumps(results,indent=2));print('PASS guided Recommitment browser checks:',len(results))
asyncio.run(main())
