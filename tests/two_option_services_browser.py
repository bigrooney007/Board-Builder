"""New guided Fundraising packages through payment, preparation, ownership and delivery."""
import asyncio,json,os,re
from pathlib import Path
from playwright.async_api import async_playwright,expect
BASE='http://127.0.0.1:8765'
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'

async def play(page,primary=False):
 await page.get_by_role('button',name='START MY GAME',exact=True).click()
 await page.get_by_role('button',name='YES',exact=True).click()
 for i,value in enumerate(['Teachers in Pittsburgh benefit from the children we help.','Local teachers communities.','Share the approved teaching resource.','Build trust through email, then meet teachers and invite suitable support.','Ask for $100 to provide one backpack.']):
  await page.get_by_role('textbox',name='Your audience answer',exact=True).fill(value)
  await page.get_by_role('button',name='NEXT QUESTION' if i<4 else 'SAVE THIS AUDIENCE AND CONTINUE',exact=True).click()
 for _ in range(3):await page.get_by_role('button',name='NO, CONTINUE',exact=True).click()
 await page.get_by_role('textbox',name='Your personal participation',exact=True).fill('I can introduce interested teachers after agreeing the approach.')
 await page.get_by_role('button',name='REVIEW MY CONTRIBUTION',exact=True).click()
 await page.get_by_role('button',name='SUBMIT MY CONTRIBUTION',exact=True).click()
 if not primary:await page.get_by_role('heading',name='Your Fundraising Ideas Are Saved',exact=True).wait_for()

async def main():
 results=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch()
  for width,choice in ((1440,'self-facilitated'),(390,'self-facilitated')):
   ctx=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844},accept_downloads=True);page=await ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   auth=(await (await ctx.request.get(BASE+'/__test/session')).json())['token'];headers={'Authorization':'Bearer '+auth}
   try:
    await page.goto(BASE+'/board-fundraising');await page.get_by_test_id('fundraising-home-page').wait_for()
    await page.get_by_role('button',name='START MY BOARD FUNDRAISING FOR FREE',exact=True).first.click()
    await page.get_by_label('Full name',exact=True).fill('Sample Fundraising Leader');await page.get_by_label('Email address',exact=True).fill(f'fundraising-{choice}-{width}@example.org');await page.get_by_label('Organization name',exact=True).fill('Sample Fundraising Organization')
    await page.screenshot(path=f'test_reports/current-flow-fundraising-contact-{choice}-{width}.png',full_page=True)
    await page.get_by_role('button',name='CONTINUE',exact=True).click();await page.wait_for_url('**/services/board-fundraising/start?lead=*');token=page.url.split('lead=')[1]
    row=await (await ctx.request.get(BASE+'/api/services/board-fundraising/customer/'+token)).json();ident=row['customer_id'];assert len(row['question_snapshot'])==6
    await page.screenshot(path=f'test_reports/current-flow-fundraising-questions-{choice}-{width}.png',full_page=True)
    for i,value in enumerate(['Help children learn.','3','100000','2027-12-31','Children would lose access to our learning program.']):
     await page.get_by_label('Your answer',exact=True).fill(value);await page.get_by_role('button',name='SAVE AND CONTINUE',exact=True).click();await expect(page.get_by_text(f'Question {i+2} of 6',exact=True)).to_be_visible()
    for label,value in [('Meeting date','2026-12-01'),('Meeting start time','16:00'),('Meeting time zone','Europe/London')]:await page.get_by_label(label,exact=True).fill(value)
    await page.get_by_role('button',name='SUBMIT MY BOARD FUNDRAISING INFORMATION',exact=True).click();await page.wait_for_url('**/services/board-fundraising/received/*')
    await page.screenshot(path=f'test_reports/current-flow-fundraising-received-{choice}-{width}.png',full_page=True)
    await page.goto(BASE+'/services/board-fundraising/offer/'+token);price='497' if choice=='self-facilitated' else '1,497'
    button=page.get_by_role('button',name='ACTIVATE MY BOARD FUNDRAISING',exact=True);await button.wait_for();await page.screenshot(path=f'test_reports/current-flow-fundraising-offers-{choice}-{width}.png',full_page=True);await button.click()
    await page.get_by_role('heading',name='Controlled Stripe checkout: $'+price.replace(',',''),exact=True).wait_for();await page.get_by_role('button',name='Complete Payment',exact=True).click();await page.wait_for_url('**/services/board-fundraising/setup/*')
    await page.get_by_label('Primary organization color',exact=True).fill('#4438cc');await page.get_by_role('button',name='SAVE ORGANIZATION BRANDING',exact=True).click();await page.get_by_role('link',name='BOOK MY BOARD FUNDRAISING ACTIVATION CALL →',exact=True).wait_for()
    await page.screenshot(path=f'test_reports/current-flow-fundraising-branding-booking-{choice}-{width}.png',full_page=True)
    await ctx.add_cookies([{'name':'admin_access_token','value':auth,'url':BASE,'httpOnly':True,'sameSite':'Lax'}]);data=await (await ctx.request.get(BASE+'/api/admin/services/board-fundraising/customers/'+ident,headers=headers)).json();uid=data['customer']['workspace_user_id']
    await page.goto(BASE+'/admin/services/board-fundraising');await page.get_by_role('button',name='Open Service Workspace',exact=True).first.click();await page.get_by_test_id('dashboard-handover').wait_for();await page.screenshot(path=f'test_reports/current-workstation-fundraising-admin-{choice}-{width}.png',full_page=True)
    await page.get_by_role('link',name='Open Fundraising Preparation and Facilitation',exact=True).click();await page.get_by_role('button',name='Open Lead User Fundraising Questions',exact=True).click();await page.wait_for_url('**/play/*');await play(page,True);await page.wait_for_url('**/admin/fundraising/customer/*')
    await page.get_by_test_id('fundraising-workspace').wait_for();member_headers={**headers,'X-Fundraising-Customer':uid}
    added=await ctx.request.post(BASE+'/api/game/board-members',headers=member_headers,data={'full_name':'Alex Example','email':f'board-{choice}-{width}@example.org'});assert added.ok,await added.text();person=(await added.json())['board_member']
    sent=await ctx.request.post(BASE+'/api/game/board-members/'+person['member_id']+'/invite',headers=member_headers,data={'origin_url':BASE});assert sent.ok,await sent.text()
    participant=await browser.new_context(viewport={'width':width,'height':844});pp=await participant.new_page();await pp.goto(BASE+'/play/'+person['token']);await play(pp)
    await page.screenshot(path=f'test_reports/current-workstation-fundraising-prepared-{choice}-{width}.png',full_page=True)
    if choice=='self-facilitated':
     hand=await ctx.request.post(BASE+'/api/admin/services/board-fundraising/customers/'+ident+'/handover',headers=headers,data={'prepared_confirmed':True});assert hand.ok,await hand.text();hand=await hand.json()
     owner=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844},accept_downloads=True);await page.close();await ctx.close();ctx=owner;page=await ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));member_headers={}
     await page.goto(BASE+hand['url'].split('8765')[-1]);await page.get_by_role('button',name='OPEN MY DASHBOARD',exact=True).click();await page.wait_for_url('**/services/board-fundraising/dashboard/*');await page.get_by_test_id('fundraising-workspace').wait_for();await expect(page.get_by_text('SELF-FACILITATED: ORGANIZATION IN CONTROL',exact=True)).to_be_visible()
    await page.screenshot(path=f'test_reports/current-workstation-fundraising-operator-{choice}-{width}.png',full_page=True)
    await page.get_by_role('button',name='Start The Group Game',exact=True).click();review=page.get_by_test_id('bfg-audience-group-review');await review.wait_for();microphone=page.get_by_role('dialog',name='Enable your meeting microphone');await microphone.get_by_role('button',name='Continue Without Microphone',exact=True).click()
    await review.get_by_role('button',name='START GROUP REVIEW',exact=True).click();state=await (await ctx.request.get(BASE+'/api/game/group/session',headers=member_headers)).json();group_token=state['session']['token']
    await pp.goto(BASE+'/group-game/'+group_token);await pp.get_by_role('button',name='Alex',exact=True).click();await pp.get_by_role('button',name='Join The Game',exact=True).click();await pp.get_by_role('heading',name='Our Group Fundraising Discussion',exact=True).wait_for()
    await page.screenshot(path=f'test_reports/current-flow-fundraising-group-{choice}-{width}.png',full_page=True)
    for i in range(2):
     await review.get_by_role('button',name='Approve Audience' if i==0 else 'Disapprove Audience',exact=True).click();await expect(review.get_by_text('Decision: adopted' if i==0 else 'Decision: rejected',exact=True)).to_be_visible();await review.get_by_role('button',name='NEXT FUNDING AUDIENCE' if i==0 else 'DISCUSS PARTICIPATION',exact=True).click()
    await review.get_by_role('combobox',name='Person agreeing to participate',exact=True).select_option(label='Alex Example');await review.get_by_role('textbox',name='Confirmed contribution',exact=True).fill('Introduce teachers who agree to an introduction.');await review.get_by_role('checkbox',name='This person has explicitly agreed to this contribution.',exact=True).check();await review.get_by_role('button',name='SAVE CONFIRMED PARTICIPATION',exact=True).click()
    transcript=await ctx.request.post(BASE+'/api/game/meeting/transcript',headers=member_headers,data={'text':'The board adopted the teachers audience and Alex agreed to introduce teachers after obtaining permission.'});assert transcript.ok,await transcript.text()
    await review.get_by_role('button',name='REVIEW THE AGREED STRATEGY',exact=True).click();panel=page.get_by_test_id('transcript-contributions');await panel.get_by_role('checkbox',name='I have reviewed the transcript and recorded the ideas and responsibilities the board agreed to adopt.',exact=True).check();await panel.get_by_role('button',name='Confirm Transcript Review',exact=True).click();await panel.get_by_text('Your review is saved.',exact=False).wait_for();await review.get_by_role('button',name='REVIEW THE AGREED STRATEGY',exact=True).click();await page.get_by_test_id('written-strategy-preview').wait_for()
    await review.get_by_role('checkbox',name='I confirm that this is the direction agreed during our meeting.',exact=True).check();await review.get_by_role('button',name='ADOPT OUR AGREED DIRECTION',exact=True).click();await pp.get_by_role('checkbox',name='I acknowledge the agreed direction and the contribution I have personally accepted.',exact=True).check();await pp.get_by_role('button',name='Adopt This Strategy',exact=True).click();await pp.get_by_text('You have acknowledged this agreed direction.',exact=True).wait_for();await review.get_by_role('button',name='Close Meeting and Prepare Our Strategy',exact=True).click();await review.get_by_role('heading',name='Thank you for playing The Fundraising Game.',exact=True).wait_for()
    await page.goto(BASE+('/services/board-fundraising/dashboard/'+ident if choice=='self-facilitated' else '/admin/fundraising/customer/'+uid));editor=page.get_by_test_id('admin-strategy-review');await editor.wait_for();await editor.get_by_role('button',name='Save Strategy Draft',exact=True).click();await editor.get_by_role('checkbox',name='I approve this exact saved strategy for the organization.',exact=True).check();await editor.get_by_role('button',name='Approve and Email Strategy to Lead User',exact=True).click();await page.get_by_role('button',name='Download Final Fundraising Strategy',exact=True).wait_for();await page.screenshot(path=f'test_reports/current-flow-fundraising-strategy-{choice}-{width}.png',full_page=True)
    async with page.expect_download() as downloaded:await page.get_by_role('button',name='Download Final Fundraising Strategy',exact=True).click()
    path=f'test_reports/current-two-options-strategy-{choice}-{width}.pdf';await (await downloaded.value).save_as(path)
    from pypdf import PdfReader
    text='\n'.join(p.extract_text() or '' for p in PdfReader(path).pages);assert 'Ideal Funding Audience:' in text and 'Alex Example suggests' not in text
    portfolios=page.get_by_test_id('fundraising-portfolios');await portfolios.wait_for();await portfolios.get_by_text("Alex Example's Agreed Role",exact=True).click();await portfolios.get_by_label('Agreed role for Alex Example',exact=True).fill('Introduce interested teachers after they give permission.');role_panel=portfolios.locator('details').filter(has=page.get_by_text("Alex Example's Agreed Role",exact=True));await role_panel.get_by_role('checkbox',name='This person agreed to these responsibilities',exact=True).check();await role_panel.get_by_role('button',name='Save Confirmed Role',exact=True).click();await portfolios.get_by_role('button',name='Generate Board Portfolios',exact=True).click();await portfolios.get_by_label('Portfolio for Alex Example',exact=True).wait_for();await portfolios.get_by_role('checkbox',name='I approve this exact portfolio and its agreed responsibilities',exact=True).check();await portfolios.get_by_role('button',name='Approve Portfolio',exact=True).click();await portfolios.get_by_role('link',name='Download Approved Portfolio',exact=True).wait_for();await page.screenshot(path=f'test_reports/current-flow-fundraising-portfolios-{choice}-{width}.png',full_page=True)
    assert not errors,errors;assert await page.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2');results.append({'width':width,'package':choice,'case':'free_checkout_branding_preparation_invites_handover_group_adoption_strategy_portfolio_delivery','passed':True});await participant.close()
   except Exception:
    await page.screenshot(path=f'test_reports/current-two-options-failure-{choice}-{width}.png',full_page=True);Path(f'test_reports/current-two-options-failure-{choice}-{width}.html').write_text(await page.content());raise
   finally:await ctx.close()
  await browser.close()
 Path('test_reports/current-two-options-browser.json').write_text(json.dumps(results,indent=2));print('PASS two-option Fundraising browser journeys:',len(results))
asyncio.run(main())
