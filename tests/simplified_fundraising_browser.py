"""Desktop/mobile acceptance through the actual simplified React pages and APIs."""
import asyncio
import json
import os
import time
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright
BASE='http://127.0.0.1:8765'
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'

async def main():
    for _ in range(80):
        try:
            with urllib.request.urlopen(BASE+'/__test/session'):break
        except Exception:await asyncio.sleep(.25)
    results=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        for width in (1440,390):
            context=await browser.new_context(viewport={'width':width,'height':1000 if width==1440 else 844},accept_downloads=True)
            auth=(await (await context.request.get(BASE+'/__test/session')).json())['token']
            await context.set_extra_http_headers({'Authorization':'Bearer '+auth})
            response=await context.request.post(BASE+'/api/admin/fundraising/test-start');assert response.ok,await response.text()
            test=await response.json();page=await context.new_page();errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            await page.add_init_script('(token)=>localStorage.setItem("memberToken",token)',test['token']) if False else None
            await page.goto(BASE);await page.evaluate('(token)=>localStorage.setItem("memberToken",token)',test['token']);await page.reload()
            await page.get_by_test_id('fundraising-home-page').wait_for()
            await page.get_by_role('heading',name='The Fundraising Game',exact=True).wait_for()
            assert await page.get_by_text('Imagine walking into your next board meeting',exact=False).count()==1
            assert await page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth+2')
            await page.screenshot(path=f'test_reports/current-simplified-home-{width}.png',full_page=True)
            results.append({'width':width,'case':'supplied_homepage_and_layout','passed':True})
            await page.get_by_role('button',name='Play The Fundraising Game With Your Board',exact=True).first.click()
            await page.get_by_label('Full name',exact=True).fill('Sample Leader')
            await page.get_by_label('Email address',exact=True).fill('leader@example.test')
            await page.get_by_label('Organization name',exact=True).fill('BrightPath Youth Alliance')
            await page.get_by_role('button',name='See How The Fundraising Game Works',exact=True).click()
            await page.wait_for_url('**/how-the-fundraising-game-works?lead=*')
            await page.get_by_test_id('fundraising-how-page').wait_for()
            await page.get_by_text('Start The Fundraising Game Today: $497.',exact=True).wait_for()
            await page.get_by_role('button',name='Play The Fundraising Game With Your Board',exact=True).first.click()
            await page.wait_for_url('**/game/setup')
            await page.get_by_label('Fundraising goal',exact=True).fill('100000')
            await page.get_by_label('Mission statement',exact=True).fill('Help young people enter employment.')
            await page.get_by_label('Annual budget',exact=True).fill('$150,000')
            await page.get_by_label('Organization website',exact=True).fill('https://example.org')
            await page.get_by_label('Who or what community your organization serves',exact=True).fill('Young people seeking employment')
            await page.get_by_role('button',name='Save and Start The Game',exact=True).click()
            await page.wait_for_url('**/play/*')
            await page.get_by_role('button',name='START MY GAME',exact=True).click()
            await page.get_by_role('button',name='YES',exact=True).click()
            for index,value in enumerate(['Former mentors care about youth employment.','Community networks.','Share programme outcomes.','Ask for introductions and invite support.','Fund mentoring places, $500 each.']):
                await page.get_by_role('textbox',name='Your audience answer').fill(value)
                await page.get_by_role('button',name='NEXT QUESTION' if index<4 else 'SAVE THIS AUDIENCE AND CONTINUE',exact=True).click()
            for _ in range(3):await page.get_by_role('button',name='NO, CONTINUE',exact=True).click()
            await page.get_by_role('textbox',name='Your personal participation').fill('I can introduce local employers.')
            await page.get_by_role('button',name='REVIEW MY CONTRIBUTION',exact=True).click()
            await page.get_by_role('button',name='SUBMIT MY CONTRIBUTION',exact=True).click()
            await page.wait_for_url('**/game/setup')
            await page.get_by_label('Board meeting date',exact=True).fill('2026-12-01')
            await page.get_by_label('Meeting start time',exact=True).fill('16:00')
            await page.get_by_label('Time zone',exact=True).fill('Europe/London')
            await page.get_by_role('button',name='Save Meeting and Invite My Board',exact=True).click()
            await page.get_by_role('heading',name='Invite your board members',exact=True).wait_for()
            results.append({'width':width,'case':'contact_payment_setup_five_questions_before_meeting','passed':True})
            await page.get_by_role('button',name='Open My Workspace',exact=True).click()
            await page.wait_for_url('**/game/dashboard')
            await page.get_by_test_id('fundraising-workspace').wait_for()
            assert await page.get_by_role('button',name='Download Final Fundraising Strategy',exact=True).is_disabled()
            assert await page.get_by_role('button',name='Generate Board Portfolios',exact=True).is_disabled()
            assert await page.locator('body').evaluate('(e)=>e.scrollWidth<=window.innerWidth+2')
            await page.screenshot(path=f'test_reports/current-simplified-workspace-{width}.png',full_page=True)
            results.append({'width':width,'case':'real_workspace_locked_outputs_and_responses','passed':True})
            await page.goto(BASE+'/admin?tab=home')
            await page.get_by_test_id('fundraising-admin').wait_for()
            await page.get_by_label('Page heading',exact=True).fill('Our board fundraising homepage')
            await page.get_by_role('button',name='Save Website Content',exact=True).click()
            await page.get_by_text('Your changes are saved and appear on the public website after refresh.',exact=True).wait_for()
            await page.goto(BASE)
            await page.get_by_role('heading',name='Our board fundraising homepage',exact=True).wait_for()
            results.append({'width':width,'case':'admin_edit_save_public_refresh','passed':True})
            assert not errors,errors
            await context.close()
        await browser.close()
    Path('test_reports/current-simplified-browser.json').write_text(json.dumps({'passed':True,'cases':results},indent=2))
    print('PASS:',len(results),'simplified desktop/mobile browser checks')

if __name__=='__main__':Path('test_reports').mkdir(exist_ok=True);asyncio.run(main())
