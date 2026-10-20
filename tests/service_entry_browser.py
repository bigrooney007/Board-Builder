"""Current contact dialogs, published page copy and configurable question counts."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright,expect

BASE='http://127.0.0.1:8765'
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'
SERVICES=[('recruitment','/recruit'),('board-recommitment','/board-recommitment'),('strategic-planning','/strategic-planning')]

async def main():
 results=[]
 async with async_playwright() as playwright:
  browser=await playwright.chromium.launch()
  for width in (1440,390):
   context=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844})
   auth=(await (await context.request.get(BASE+'/__test/session')).json())['token'];headers={'Authorization':'Bearer '+auth}
   await context.add_cookies([{'name':'admin_access_token','value':auth,'url':BASE,'httpOnly':True,'sameSite':'Lax'}])
   page=await context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
   for service,path in SERVICES:
    api='/api/admin/services/'+service
    original=(await (await context.request.get(BASE+api+'/settings',headers=headers)).json())['config']
    stored=(await (await context.request.get(BASE+'/api/platform/homepages/'+service)).json()).get('content') or {}
    try:
     await page.goto(BASE+'/admin/services/'+service)
     await page.get_by_role('button',name='Landing Page Editor',exact=True).click()
     headline=f'Our {service.replace("-"," ").title()} Process {width}'
     await page.get_by_label('Headline',exact=True).fill(headline)
     await page.get_by_label('Process Eyebrow',exact=True).fill('YOUR GUIDED PROCESS')
     await page.get_by_role('button',name='SAVE HOME PAGE TEXT',exact=True).click()
     await page.get_by_text('Home page text saved.',exact=True).wait_for()
     await page.reload();await page.get_by_role('button',name='Landing Page Editor',exact=True).click()
     await expect(page.get_by_label('Headline',exact=True)).to_have_value(headline)
     await page.get_by_role('button',name='Free Entry Questions' if service=='strategic-planning' else 'Entry Questions',exact=True).click()
     await page.get_by_label('Number of questions to show',exact=True).fill('2')
     await page.get_by_role('button',name='Apply Question Count',exact=True).click()
     subtitle='Use your own words to explain what matters to your organization.'
     await page.get_by_label('Question 1 subtitle',exact=True).fill(subtitle)
     await page.get_by_role('button',name='Save and Publish Settings',exact=True).click()
     await page.get_by_role('status').filter(has_text='published').wait_for()
     await page.reload();await page.get_by_role('button',name='Free Entry Questions' if service=='strategic-planning' else 'Entry Questions',exact=True).click()
     await expect(page.get_by_label('Number of questions to show',exact=True)).to_have_value('2')
     await expect(page.get_by_label('Question 1 subtitle',exact=True)).to_have_value(subtitle)
     await page.goto(BASE+path);await expect(page.locator('h1')).to_have_text(headline)
     await expect(page.get_by_text('YOUR GUIDED PROCESS',exact=True)).to_be_visible()
     assert await page.locator('a[href^="/login"],a[href^="/register"]').count()==0
     logo=page.locator('header img[alt="Nonprofit Board Builder"]');await expect(logo).to_have_attribute('src','/nonprofit-board-builder-logo.jpg')
     await expect(logo).to_have_js_property('naturalWidth',1280)
     assert await page.locator('main').evaluate('element=>element.scrollWidth<=innerWidth+2')
     intro=page.locator('.recruit-hero-sub,.guided-hero>p').first
     assert await intro.evaluate('element=>getComputedStyle(element).color')=='rgb(0, 0, 0)'
     cta=page.locator('.recruit-hero .bfg-btn-primary,.guided-hero-cta').first
     await cta.click();await page.get_by_role('dialog').wait_for();assert page.url==BASE+path
     await page.keyboard.press('Escape');await expect(page.get_by_role('dialog')).to_have_count(0);await expect(cta).to_be_focused()
     await cta.click();modal=page.get_by_role('dialog');await expect(modal.locator('input')).to_have_count(3)
     assert await modal.locator('input[type="password"],a').count()==0
     await modal.get_by_label('Full name',exact=True).fill('Sample Service Leader')
     await modal.get_by_label('Email address',exact=True).fill(f'entry-{service}-{width}@example.org')
     await modal.get_by_label('Organization name',exact=True).fill('Sample Community Organization')
     await page.screenshot(path=f'test_reports/current-entry-modal-{service}-{width}.png',full_page=True)
     await modal.get_by_role('button',name='CONTINUE',exact=True).click()
     await page.wait_for_url('**/services/'+service+'/start?lead=*')
     await expect(page.get_by_text('Question 1 of 2',exact=True)).to_be_visible()
     await expect(page.get_by_text(subtitle,exact=True)).to_be_visible()
     text=(await page.locator('body').inner_text()).lower()
     assert 'free' not in text and 'retrieve your access' not in text and 'log in' not in text,text
     await page.get_by_label('Your answer',exact=True).fill('We want our board to help support learning in our community.')
     await page.get_by_role('button',name='SAVE AND CONTINUE',exact=True).click()
     await expect(page.get_by_text('Question 2 of 2',exact=True)).to_be_visible()
     await page.get_by_role('button',name='Previous',exact=True).click()
     await expect(page.get_by_label('Your answer',exact=True)).to_have_value('We want our board to help support learning in our community.')
     await page.get_by_role('button',name='SAVE AND CONTINUE',exact=True).click()
     await page.get_by_label('Your answer',exact=True).fill('Agree on the contributions we can realistically make.')
     await page.get_by_role('button',name='SAVE MY ANSWERS',exact=True).click()
     await page.wait_for_url('**/services/'+service+'/received/*')
     assert await page.locator('body').evaluate('element=>element.scrollWidth<=innerWidth+2')
     assert not errors,errors
     results.append({'service':service,'width':width,'case':'editable_landing_contact_popup_count_subtitle_saved_answers_no_login','passed':True})
    except Exception:
     print('Service entry browser failure:',service,width,page.url)
     print('Visible editor labels:',await page.locator('input,textarea,select').evaluate_all("elements=>elements.map(element=>({label:element.getAttribute('aria-label'),parent:element.parentElement.textContent.slice(0,100)}))"))
     print('Page messages:',await page.locator('[role=alert],.admin-message').all_text_contents())
     await page.screenshot(path=f'test_reports/current-entry-failure-{service}-{width}.png',full_page=True)
     Path(f'test_reports/current-entry-failure-{service}-{width}.html').write_text(await page.content())
     raise
    finally:
     current=await (await context.request.get(BASE+api+'/settings',headers=headers)).json()
     draft=await (await context.request.put(BASE+api+'/draft',headers=headers,data={'config':original,'revision':current['revision']})).json()
     restored=await context.request.post(BASE+api+'/publish',headers=headers,data={'revision':draft['revision']});assert restored.ok,await restored.text()
     restored=await context.request.put(BASE+'/api/admin/platform/homepages/'+service,headers=headers,data={'content':stored});assert restored.ok,await restored.text()
   await page.goto(BASE+'/meet-rooney');await page.get_by_test_id('meet-rooney-page').wait_for()
   gap=await page.locator('.professional-intro').evaluate("element=>element.querySelector('.professional-rich p').getBoundingClientRect().top-element.querySelector('h1').getBoundingClientRect().bottom")
   assert 20<=gap<=40,gap
   assert await page.locator('.professional-intro .professional-rich p').first.evaluate('element=>getComputedStyle(element).color')=='rgb(0, 0, 0)'
   assert await page.locator('.professional-navy .professional-rich p').first.evaluate('element=>getComputedStyle(element).color')=='rgb(255, 255, 255)'
   assert await page.locator('body').evaluate('element=>element.scrollWidth<=innerWidth+2')
   await page.screenshot(path=f'test_reports/current-meet-rooney-spacing-{width}.png',full_page=True)
   results.append({'width':width,'case':'meet_rooney_spacing_and_black_white_contrast','passed':True})
   await context.close()
  await browser.close()
 Path('test_reports/current-service-entry-browser.json').write_text(json.dumps(results,indent=2))
 print('PASS service entry and editor browser checks:',len(results))

asyncio.run(main())
