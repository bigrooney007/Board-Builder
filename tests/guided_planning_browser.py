"""Actual guided Planning pages on desktop/mobile, with controlled external providers."""
import asyncio,json,os
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
   page=await ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   try:
    await page.goto(BASE+'/strategic-planning');await page.locator('a[href="/strategic-planning/start"]').first.click()
    await page.get_by_label('Full name',exact=True).fill('Sample Planning Leader');await page.get_by_label('Email address',exact=True).fill(f'planning-leader-{width}@example.org');await page.get_by_label('Organization name',exact=True).fill('Sample Planning Organization');await page.get_by_role('button',name='START FOR FREE',exact=True).click();await page.wait_for_url('**/services/strategic-planning/start?lead=*');token=page.url.split('lead=')[1];public='/api/services/strategic-planning/customer/'+token
    row=await (await ctx.request.get(BASE+public)).json();ident=row['customer_id'];base='/api/admin/services/strategic-planning/customers/'+ident+'/planning'
    assert len(row['question_snapshot'])==3
    for i in range(3):
     await page.get_by_label('Your answer',exact=True).fill('Expand access to learning through agreed programs and partnerships.');await page.get_by_role('button',name='SAVE MY ANSWERS' if i==2 else 'SAVE AND CONTINUE',exact=True).click()
    await page.wait_for_url('**/services/strategic-planning/received/*');await page.goto(BASE+'/services/strategic-planning/offer/'+token);await page.get_by_role('button',name='PAY $1,997 AND BEGIN MY GUIDED SERVICE',exact=True).click();await page.get_by_role('button',name='Complete Payment',exact=True).click();await page.wait_for_url('**/services/strategic-planning/setup/*');await page.get_by_role('button',name='SAVE ORGANIZATION BRANDING',exact=True).click();await page.get_by_role('link',name='BOOK MY STRATEGIC PLANNING SESSION →',exact=True).wait_for()
    await ctx.add_cookies([{'name':'admin_access_token','value':auth,'url':BASE,'httpOnly':True,'sameSite':'Lax'}]);await page.goto(BASE+'/admin/services/strategic-planning');await page.get_by_role('button',name='Open Service Workspace',exact=True).first.click();await page.get_by_label('Existing organization mission',exact=True).fill('Help children access learning.');await page.get_by_label('Board planning meeting date',exact=True).fill('2026-11-15');await page.get_by_label('Board planning meeting start time',exact=True).fill('10:00');await page.get_by_label('Individual response deadline',exact=True).fill('2026-11-10');await page.get_by_role('button',name='Add Existing Program',exact=True).click();await page.get_by_label('Program 1 name',exact=True).fill('After-School Education');await page.get_by_role('button',name='Add Existing Program',exact=True).click();await page.get_by_label('Program 2 name',exact=True).fill('Youth Coding');await page.get_by_role('button',name='Save Planning Setup',exact=True).click();await page.get_by_role('button',name='Prepare Lead User Planning Form',exact=True).click();await page.get_by_label('Planning participant full name',exact=True).fill('Sample Planning Board Member');await page.get_by_label('Planning participant email address',exact=True).fill(f'planning-board-{width}@example.org');await page.get_by_role('button',name='Add Planning Participant',exact=True).click();await expect(page.get_by_role('heading',name='Sample Planning Board Member · Board Member',exact=True)).to_be_visible()
    data=await (await ctx.request.get(BASE+base,headers=headers)).json();assert len(data['participants'])==2
    for person in data['participants']:
     form=await (await ctx.request.get(BASE+'/api/strategic-planning-form/'+person['form_token'])).json();assert person['role']=='Lead User' or not form['existing_answers'];member=await ctx.new_page();await member.goto(BASE+'/strategic-planning-form/'+person['form_token']);questions=[q for s in form['form']['sections'] for q in s['questions']]
     for i,q in enumerate(questions):
      await member.get_by_label('Your answer',exact=True).fill('Support this agreed priority through our existing programs and confirmed contributions.');await member.get_by_role('button',name='SUBMIT MY PLANNING IDEAS' if i==len(questions)-1 else 'SAVE AND CONTINUE',exact=True).click()
     await member.get_by_role('heading',name='Thank You for Sharing Your Ideas',exact=True).wait_for();await member.close()
    await page.get_by_role('button',name='Refresh Planning Workspace',exact=True).click();await page.get_by_role('button',name='Open Live Strategic Planning Controls',exact=True).click();await page.get_by_role('button',name='START STRATEGIC PLANNING SESSION',exact=True).click();await page.get_by_role('heading',name='Vision',exact=True).wait_for()
    section_count=len((await (await ctx.request.get(BASE+'/api/guided/strategic-planning/session?session_id='+data['session_id'],headers=headers)).json())['sections'])
    for i in range(section_count):
     await page.get_by_role('checkbox',name='Adopt this idea',exact=True).first.check()
     if i<section_count-1:await page.get_by_role('button',name='Next Subject',exact=True).click()
    await page.get_by_role('button',name='COMPLETE STRATEGIC PLANNING SESSION',exact=True).click();await page.get_by_role('heading',name='Review the Agreed Decisions',exact=True).wait_for();await page.get_by_role('button',name='Confirm Agreed Decisions and Generate Plan',exact=True).click()
    await page.get_by_label('Complete strategic plan',exact=True).wait_for();await page.get_by_role('button',name='Save Plan Draft',exact=True).click();await page.get_by_role('button',name='Approve Plan and Prepare Board Review',exact=True).click();page.on('dialog',lambda d:d.accept());await page.get_by_role('button',name='Release Current Plan for Board Review',exact=True).click()
    data=await (await ctx.request.get(BASE+base,headers=headers)).json()
    for person in data['participants']:
     member=await ctx.new_page();await member.goto(BASE+'/strategic-plan-review/'+person['review_token']);await member.get_by_role('button',name='ADOPT THIS STRATEGIC PLAN',exact=True).click();await member.get_by_role('status').filter(has_text='decision').wait_for();assert await member.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2');await member.close()
    await page.get_by_role('button',name='Refresh Planning Workspace',exact=True).click();await page.get_by_role('checkbox',name='The applicable formal organizational approval has been confirmed',exact=True).check();await page.get_by_role('button',name='FINALIZE STRATEGIC PLAN',exact=True).click();await page.get_by_role('button',name='EMAIL FINAL PLAN',exact=True).click();await page.get_by_role('button',name='Approve and Send Email',exact=True).click()
    await page.goto(BASE+'/services/strategic-planning/resources/'+token);await page.get_by_role('heading',name='Your Approved Strategic Plan',exact=True).wait_for();assert await page.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2');assert not errors,errors;await page.screenshot(path=f'test_reports/current-guided-planning-{width}.png',full_page=True)
    results.append({'width':width,'case':'free_1997_branding_setup_independent_forms_programs_admin_session_adoption_review_delivery_downloads','passed':True})
   except Exception:
    await page.screenshot(path=f'test_reports/current-guided-planning-failure-{width}.png',full_page=True);Path(f'test_reports/current-guided-planning-failure-{width}.html').write_text(await page.content());raise
   finally:await ctx.close()
  await browser.close()
 Path('test_reports/current-guided-planning-browser.json').write_text(json.dumps(results,indent=2));print('PASS guided Planning browser checks:',len(results))
asyncio.run(main())
