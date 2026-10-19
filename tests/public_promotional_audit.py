"""Read-only production browser audit. Never submits a form, checkout or email."""
import asyncio,json,re
from datetime import datetime,timezone
from pathlib import Path
from playwright.async_api import async_playwright
ORIGIN='https://nonprofitboardbuilder.com'
PAGES=[('/',r'board|organization'),('/meet-rooney',r'rooney'),('/consultation',r'consultation'),('/recruit',r'recruit|board'),('/board-fundraising',r'fundraising'),('/board-fundraising-game',r'fundraising'),('/board-recommitment',r'recommit|board'),('/strategic-planning',r'strategic|board'),('/join-a-board',r'board'),('/board-opportunities',r'board|opportunit'),('/blog',r'blog|insights|fundraising'),('/how-the-fundraising-game-works',r'fundraising'),('/organize-board-fundraising-game',r'fundraising')]
async def main():
 rows=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch();context=await browser.new_context()
  for path,expected in PAGES:
   page=await context.new_page();row={'url':ORIGIN+path}
   try:
    response=await page.goto(row['url'],wait_until='domcontentloaded',timeout=30000)
    await page.locator('h1').first.wait_for(timeout=12000)
    await page.wait_for_timeout(1200)
    heading=await page.locator('h1').first.inner_text();final=page.url
    wanted_path=path if path not in ('/board-fundraising','/organize-board-fundraising-game') else '/board-fundraising-game' if path=='/board-fundraising' else '/how-the-fundraising-game-works'
    actual_path=re.sub(r'\?.*','',final.removeprefix(ORIGIN)).rstrip('/') or '/'
    row.update(status=response.status if response else None,final_url=final,heading=heading,title=await page.title(),http_available=bool(response and response.status==200),route_resolves_as_expected=actual_path==wanted_path and bool(re.search(expected,heading,re.I)))
    if path=='/':row['four_service_links_visible']=all([await page.locator(f'a[href="{link}"]').count()>0 for link in ('/recruit','/board-fundraising','/strategic-planning','/board-recommitment')])
   except Exception as exc:row.update(http_available=False,route_resolves_as_expected=False,error=str(exc)[:300])
   rows.append(row);await page.close()
  for path in ('/api/blog/feed.xml','/sitemap.xml','/api/blog/sitemap.xml'):
   row={'url':ORIGIN+path}
   try:
    response=await context.request.get(row['url'],timeout=20000);body=await response.text();row.update(status=response.status,http_available=response.ok,route_resolves_as_expected=response.ok and bool(re.search(r'<(?:rss|urlset)',body)))
   except Exception as exc:row.update(http_available=False,error=str(exc)[:200])
   rows.append(row)
  await browser.close()
 report={'checked_at':datetime.now(timezone.utc).isoformat(),'read_only':True,'deployment_commit_verified':False,'pages':rows}
 Path('test_reports').mkdir(exist_ok=True);Path('test_reports/current-public-promotional-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
asyncio.run(main())
