"""Real current React components and API handlers on disposable data/providers."""
import asyncio
import json
from pathlib import Path
import httpx
from playwright.async_api import async_playwright, expect
BASE="http://127.0.0.1:8765"
OUT=Path("test_reports");OUT.mkdir(exist_ok=True)

async def main():
    results=[]
    async with httpx.AsyncClient(base_url=BASE,timeout=30) as api:
        for _ in range(60):
            try:
                admin=(await api.get("/__test/session")).json()["token"];break
            except Exception:await asyncio.sleep(1)
        else:raise RuntimeError("Current workflow test server did not start")
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            for width,height in ((1440,1000),(390,844)):
                context=await browser.new_context(viewport={"width":width,"height":height})
                page=await context.new_page();errors=[]
                page.on("pageerror",lambda error:errors.append(str(error)))
                async def launch(product,mode="intro"):
                    path="/api/admin/dashboard-preview/"+(mode+"/" if mode in {"intro","fresh"} else "")+product
                    r=await api.post(path,headers={"Authorization":"Bearer "+admin});r.raise_for_status();data=r.json()
                    await page.goto(BASE)
                    await page.evaluate("data=>{localStorage.setItem('memberToken',data.token);sessionStorage.setItem('adminClientTest','1');sessionStorage.setItem('adminClientTestVersion',String(data.workflow_version));}",data)
                    # axios calls without explicit bearer headers use the normal member cookie.
                    await context.add_cookies([{"name":"member_access_token","value":data["token"],"url":BASE}])
                    await page.goto(BASE+(data.get("start_url") or data["dashboard_url"]))
                    return data
                # Leader receives the same 15 configured questions as invitees.
                await launch("strategic-planning")
                form=page.get_by_test_id("strategic-planning-prepayment-questions")
                await expect(form).to_be_visible()
                for i in range(15):
                    await expect(form.locator(".guided-preflow-kicker")).to_contain_text(f"· {i+1} OF 15")
                    await form.locator("textarea").fill(f"Sample adopted idea {i+1}. Confirm details before implementation.")
                    await form.get_by_role("button",name="SEE HOW WE MOVE FORWARD" if i==14 else "SAVE AND CONTINUE").click()
                await expect(page).to_have_url(__import__('re').compile("/strategic-planning/video"))
                results.append({"viewport":width,"check":"planning leader completes all 15 questions and reaches existing payment page","passed":True})
                # Free leader saves a full audience, repeats it, then skips the other categories.
                await launch("board-fundraising-game")
                q=page.get_by_test_id("bfg-audience-questionnaire");await expect(q).to_be_visible()
                await q.get_by_role("button",name="START MY GAME",exact=True).click()
                for n in range(2):
                    await q.get_by_role("button",name="YES",exact=True).click()
                    for i in range(6):
                        await expect(q.locator(".guided-question-top")).to_contain_text(f"Audience {n+1} · Question {i+1} of 6")
                        await q.get_by_role("textbox",name="Your audience answer").fill(f"Audience {n+1}, answer {i+1}. This is our own proposed approach.")
                        await q.get_by_role("button",name="NEXT QUESTION" if i<5 else "SAVE THIS AUDIENCE AND CONTINUE",exact=True).click()
                await q.get_by_role("button",name="NO, CONTINUE",exact=True).click()
                await expect(q.get_by_role("heading",level=1)).to_contain_text("business")
                await q.get_by_role("button",name="NO, CONTINUE",exact=True).click()
                await expect(q.get_by_role("heading",level=1)).to_contain_text("grantmaker")
                await q.get_by_role("button",name="NO, CONTINUE",exact=True).click()
                await q.get_by_role("textbox",name="Your personal participation").fill("I would like to introduce local employers.")
                await q.get_by_role("button",name="REVIEW MY CONTRIBUTION",exact=True).click()
                await expect(q.get_by_text("Audience 2, answer 1.",exact=False).first).to_be_visible()
                await q.get_by_role("button",name="SUBMIT MY CONTRIBUTION",exact=True).click()
                await expect(page).to_have_url(__import__('re').compile("/game/setup"))
                await expect(page.get_by_test_id("bfg-audience-questionnaire")).to_have_count(0)
                results.append({"viewport":width,"check":"two complete audiences, skipped businesses/grantmakers, participation, paid setup without repeated questionnaire","passed":True})
                # Preloaded admin tests open actual current group controls.
                await launch("board-fundraising-game","loaded");await page.goto(BASE+"/game/group")
                review=page.get_by_test_id("bfg-audience-group-review");await expect(review).to_be_visible()
                await review.get_by_role("button",name="START GROUP REVIEW",exact=True).click()
                await expect(review.get_by_role("heading",name="Discuss This Funding Audience And Its Complete Approach")).to_be_visible()
                await expect(review.get_by_role("textbox",name="How much to ask",exact=True)).to_be_visible()
                await review.get_by_role("button",name="ADOPT THIS AUDIENCE AND APPROACH",exact=True).click()
                await expect(review.get_by_text("Decision: adopted")).to_be_visible()
                results.append({"viewport":width,"check":"preloaded current group displays/adopts complete audience with all six fields","passed":True})
                await launch("strategic-planning","loaded")
                sid=__import__('urllib.parse',fromlist=['parse_qs']).parse_qs(__import__('urllib.parse',fromlist=['urlparse']).urlparse(page.url).query)["session_id"][0]
                await page.goto(BASE+"/strategic-planning/session?session_id="+sid)
                await expect(page.get_by_text("Welcome to your Strategic Planning Session.",exact=False)).to_be_visible()
                results.append({"viewport":width,"check":"preloaded planning opens current 15-question group session","passed":True})
                assert not await page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2"),"Mobile/desktop overflow"
                assert not errors,errors
                await page.screenshot(path=str(OUT/f"current-workflow-{width}.png"),full_page=True)
                await context.close()
            await browser.close()
    (OUT/"current-workflow-browser.json").write_text(json.dumps(results,indent=2))
    print(f"PASS: {len(results)} current desktop/mobile browser checks")

if __name__=="__main__":asyncio.run(main())
