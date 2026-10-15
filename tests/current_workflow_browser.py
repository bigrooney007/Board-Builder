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
                admin=(await api.get(f"/__test/session?variant={width}")).json()["token"]
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
                for index in range(12):
                    await expect(review.get_by_text(f"Audience {index+1} of 12",exact=False).first).to_be_visible()
                    await expect(review.get_by_role("textbox",name="How much to ask",exact=True)).to_be_visible()
                    await review.get_by_role("button",name="ADOPT THIS AUDIENCE AND APPROACH" if index==0 else "REJECT THIS AUDIENCE",exact=True).click()
                    await expect(review.get_by_text("Decision: adopted" if index==0 else "Decision: rejected",exact=True)).to_be_visible()
                    await review.get_by_role("button",name="NEXT FUNDING AUDIENCE" if index<11 else "DISCUSS PARTICIPATION",exact=True).click()
                await expect(review.get_by_role("heading",name="How Each Person Would Like To Participate")).to_be_visible()
                await review.get_by_role("combobox",name="Person agreeing to participate").select_option(label="Alex Morgan")
                await review.get_by_role("textbox",name="Confirmed contribution").fill("Introduce employers within the first quarter.")
                await review.get_by_role("checkbox",name="This person has explicitly agreed to this contribution.").check()
                await review.get_by_role("button",name="SAVE CONFIRMED PARTICIPATION",exact=True).click()
                await expect(review.get_by_text("Alex Morgan: Introduce employers within the first quarter.",exact=True)).to_be_visible()
                await review.get_by_role("button",name="REVIEW THE AGREED STRATEGY",exact=True).click()
                await expect(review.get_by_role("heading",name="What We Have Agreed To Do Together",exact=True)).to_be_visible()
                await review.get_by_role("checkbox",name="I confirm that this is the direction agreed during our meeting.").check()
                await review.get_by_role("button",name="ADOPT OUR AGREED DIRECTION",exact=True).click()
                await review.get_by_role("button",name="PREPARE OUR STRATEGY FOR FINAL APPROVAL",exact=True).click()
                await expect(review.get_by_role("heading",name="Review And Approve The Exact Final Wording",exact=True)).to_be_visible()
                await review.get_by_role("checkbox",name="I approve this exact wording for delivery to the leader and participants.").check()
                await review.get_by_role("button",name="APPROVE, SAVE AND EMAIL THE STRATEGY",exact=True).click()
                await expect(review.get_by_role("heading",name="Your Approved Fundraising Strategy",exact=True)).to_be_visible()
                async with page.expect_download() as download:
                    await review.get_by_role("button",name="DOWNLOAD APPROVED STRATEGY",exact=True).click()
                assert (await download.value).suggested_filename=="fundraising-strategy.pdf"
                # Join as a participant through the same personal meeting controls.
                state=(await api.get("/api/game/group/session",headers={"Authorization":"Bearer "+await page.evaluate("localStorage.getItem('memberToken')")})).json()
                participant_context=await browser.new_context(viewport={"width":width,"height":height})
                participant_page=await participant_context.new_page()
                await participant_page.goto(BASE+"/group-game/"+state["session"]["token"])
                await participant_page.get_by_role("button",name="Alex",exact=True).click()
                await participant_page.get_by_role("button",name="Join The Game",exact=True).click()
                await participant_page.get_by_role("checkbox",name="I acknowledge the agreed direction and the contribution I have personally accepted.").check()
                await participant_page.get_by_role("button",name="I ACKNOWLEDGE OUR AGREED STRATEGY",exact=True).click()
                await expect(participant_page.get_by_text("You have acknowledged this agreed direction.",exact=True)).to_be_visible()
                await participant_context.close()
                assert not await page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2"),"Fundraising mobile/desktop overflow"
                results.append({"viewport":width,"check":"current fundraising group reviews all 12 proposals, confirms participation, adopts, approves, downloads and captures delivery; participant independently acknowledges","passed":True})
                await launch("strategic-planning","loaded")
                sid=__import__('urllib.parse',fromlist=['parse_qs']).parse_qs(__import__('urllib.parse',fromlist=['urlparse']).urlparse(page.url).query)["session_id"][0]
                await page.goto(BASE+"/strategic-planning/session?session_id="+sid)
                await expect(page.get_by_text("Welcome to your Strategic Planning Session.",exact=False)).to_be_visible()
                await page.get_by_role("button",name="START STRATEGIC PLANNING SESSION",exact=True).click()
                for index in range(15):
                    await expect(page.locator(".sp-session-topline")).to_contain_text(f"Section {index+1} of 15")
                    if index in {0,14}:
                        card=page.locator("button.sp-idea-card").nth(0 if index==0 else 1)
                        await card.click();await expect(card).to_have_class(__import__('re').compile("selected"))
                    await page.get_by_role("button",name="SAVE BOARD DECISION & NEXT" if index<14 else "SAVE & END STRATEGIC PLANNING SESSION",exact=True).click()
                await expect(page.get_by_role("heading",name="What We Have Agreed To Achieve Together",exact=True)).to_be_visible()
                await page.get_by_role("button",name="APPROVE OUR AGREED DIRECTION",exact=True).click()
                await expect(page.get_by_role("textbox",name="Strategic Plan for Board review")).to_be_visible(timeout=15000)
                await page.get_by_role("button",name="APPROVE & ADOPT WITH THE BOARD",exact=True).click()
                await expect(page.get_by_role("heading",name="Strategic Plan Adopted",exact=True)).to_be_visible()
                results.append({"viewport":width,"check":"current planning discusses all 15 questions, explicitly selects ideas, reviews adopted direction, generates and approves final plan","passed":True})
                assert not await page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2"),"Mobile/desktop overflow"
                assert not errors,errors
                await page.screenshot(path=str(OUT/f"current-workflow-{width}.png"),full_page=True)
                await context.close()
            await browser.close()
    (OUT/"current-workflow-browser.json").write_text(json.dumps(results,indent=2))
    print(f"PASS: {len(results)} current desktop/mobile browser checks")

if __name__=="__main__":asyncio.run(main())
