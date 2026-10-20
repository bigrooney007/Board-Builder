"""Screenshots of each public entry and its real content-management workstation."""
import asyncio,json,os,re
from pathlib import Path
from playwright.async_api import async_playwright,expect
BASE='http://127.0.0.1:8765'
assert os.environ.get('RECOVERY_ACCEPTANCE')=='1'

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch()
  for width in (1440,390):
   ctx=await browser.new_context(viewport={'width':width,'height':1000 if width>390 else 844});page=await ctx.new_page()
   for slug,path in [('directory','/'),('recruitment','/recruit'),('recommitment','/board-recommitment'),('planning','/strategic-planning'),('fundraising','/board-fundraising'),('fundraising-explanation','/how-the-fundraising-game-works'),('meet-rooney','/meet-rooney'),('consultation','/consultation'),('applicant-network','/join-a-board'),('marketplace','/board-opportunities'),('blog','/blog')]:
    await page.goto(BASE+path);await page.locator('main').first.wait_for();await page.locator('h1').first.wait_for();await page.evaluate('document.fonts.ready');await page.screenshot(path=f'test_reports/current-public-{slug}-{width}.png',full_page=True)
    assert await page.locator('body').evaluate('e=>e.scrollWidth<=innerWidth+2'),path
    assert not re.search(r'\$\s*\d',await page.locator('main').first.inner_text()),'Public amount remains on '+path
   auth=(await (await ctx.request.get(BASE+'/__test/session')).json())['token'];headers={'Authorization':'Bearer '+auth};await ctx.add_cookies([{'name':'admin_access_token','value':auth,'url':BASE,'httpOnly':True,'sameSite':'Lax'}])
   await page.goto(BASE+'/admin?tab=blog');await page.get_by_test_id('admin-blog-section').wait_for();await expect(page.get_by_role('button',name='Monday',exact=False).filter(has_text='Board Recruitment')).to_be_visible();await expect(page.locator('.blog-weekdays button')).to_have_count(5)
   await page.get_by_text('Automatic generation and publishing',exact=True).click();await page.screenshot(path=f'test_reports/current-workstation-blog-{width}.png',full_page=True)
   for service in ['recruitment','board-recommitment','strategic-planning','board-fundraising']:
    await page.goto(BASE+'/admin/services/'+service);await page.get_by_role('button',name='First Response Email',exact=True).click();await page.get_by_role('button',name='Preview Complete Sample Email',exact=True).click();await page.get_by_role('heading',name='Sample Email Preview',exact=True).wait_for();assert await page.locator('.service-email-preview p').evaluate_all("rows=>rows.every(e=>getComputedStyle(e).textAlign==='left')");await page.screenshot(path=f'test_reports/current-workstation-email-{service}-{width}.png',full_page=True)
    await page.get_by_role('button',name='Customer Page Text',exact=True).click();await page.get_by_label('received heading',exact=True).wait_for();await page.screenshot(path=f'test_reports/current-workstation-page-editor-{service}-{width}.png',full_page=True)
   await ctx.close()
  await browser.close()
 print('PASS screenshot gallery: public pages, all service email/page editors and five-pathway automatic blog workstation, desktop and mobile')
asyncio.run(main())
