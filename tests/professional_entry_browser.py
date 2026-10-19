"""Part One browser acceptance against real React/API/Mongo and controlled providers."""
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright, expect

BASE = "http://127.0.0.1:8765"
assert os.environ.get("RECOVERY_ACCEPTANCE") == "1"
DEFAULTS = json.loads(Path("frontend/src/content/professionalEntry.json").read_text())


async def fill_consultation(page, email):
    for label, value in (("Full name", "Sample Nonprofit Leader"), ("Email address", email), ("Organization name", "BrightPath Sample Organization"), ("Organization website (optional)", "https://example.org"), ("Your role in the organization", "Executive Director"), ("What would you like to discuss?", "We want to strengthen our board and agree on a practical direction.")):
        await page.get_by_label(label, exact=True).fill(value)


async def main():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for width in (1440, 768, 390):
            context = await browser.new_context(viewport={"width": width, "height": 1000 if width > 390 else 844})
            auth = (await (await context.request.get(BASE + "/__test/session")).json())["token"]
            headers = {"Authorization": "Bearer " + auth}
            for section in ("home", "personal"):
                response = await context.request.put(BASE + "/api/admin/professional/content/" + section, data=DEFAULTS[section], headers=headers)
                assert response.ok, await response.text()
            page = await context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(BASE)
            for i, destination in enumerate(("/recruit", "/board-fundraising", "/strategic-planning", "/board-recommitment")):
                link = page.get_by_role("link", name=DEFAULTS["home"]["products"][i]["cta"], exact=True)
                await expect(link).to_have_attribute("href", destination)
                await expect(page.get_by_role("heading", name=DEFAULTS["home"]["products"][i]["title"], exact=True)).to_be_visible()
            await expect(page.get_by_role("link", name="MEET ROONEY", exact=True).first).to_have_attribute("href", "/meet-rooney")
            assert await page.locator("body").evaluate("e=>e.scrollWidth<=window.innerWidth+2")
            await page.screenshot(path=f"test_reports/current-part-one-directory-{width}.png", full_page=True)
            results.append({"width": width, "case": "four_service_directory_and_layout", "passed": True})

            for path, testid, startpath in (("/recruit", "recruitment-landing-page", "/recruit/start"), ("/strategic-planning", "strategic-planning-landing-page", "/strategic-planning/start"), ("/board-recommitment", "board-recommitment-landing-page", "/board-recommitment/start")):
                await page.goto(BASE + path)
                await page.get_by_test_id(testid).wait_for()
                await page.locator(f'a[href="{startpath}"]').first.click()
                await page.wait_for_url(BASE + startpath)
                await expect(page.locator("form").first).to_be_visible()
            await page.goto(BASE + "/board-fundraising?entry=directory")
            await page.wait_for_url(BASE + "/board-fundraising-game?entry=directory")
            await page.get_by_test_id("fundraising-home-page").wait_for()
            await page.goto(BASE + "/join-a-board")
            await page.get_by_test_id("join-page-navigation").wait_for()
            await page.goto(BASE + "/board-opportunities")
            await expect(page.locator("h1")).to_be_visible()
            await page.goto(BASE + "/blog")
            await expect(page.locator("h1")).to_be_visible()
            feed = await context.request.get(BASE + "/api/blog/feed.xml")
            assert feed.ok and "<rss" in await feed.text()
            results.append({"width": width, "case": "restored_product_intake_links_game_alias_blog_rss_applicant_network", "passed": True})

            await page.goto(BASE + "/meet-rooney")
            await page.get_by_test_id("meet-rooney-page").wait_for()
            await expect(page.get_by_role("img", name="Rooney Akpesiri", exact=True)).to_have_attribute("src", DEFAULTS["personal"]["portrait"])
            await expect(page.get_by_role("link", name="DEVELOP MY FUNDRAISING STRATEGY", exact=True)).to_have_attribute("href", "https://autofundraiser.com/")
            await expect(page.get_by_test_id("rooney-testimonial-count")).to_have_text("1 / 8")
            await page.get_by_role("button", name="Next testimonial", exact=True).click()
            await expect(page.get_by_test_id("rooney-testimonial-count")).to_have_text("2 / 8")
            assert "free consultation" not in (await page.locator("body").inner_text()).lower()
            assert await page.locator("body").evaluate("e=>e.scrollWidth<=window.innerWidth+2")
            await page.screenshot(path=f"test_reports/current-part-one-rooney-{width}.png", full_page=True)
            results.append({"width": width, "case": "personal_portrait_biography_product_choices_carousel_layout", "passed": True})

            await context.add_cookies([{"name": "admin_access_token", "value": auth, "url": BASE, "httpOnly": True, "sameSite": "Lax"}])
            await page.goto(BASE + "/admin?tab=directory")
            await page.get_by_test_id("professional-admin").wait_for()
            await page.get_by_label("Hero Headline", exact=True).fill("My Four Services " + str(width))
            await page.get_by_role("button", name="Save Main Homepage", exact=True).click()
            await page.get_by_role("status").filter(has_text="Your changes are saved").wait_for()
            await page.goto(BASE)
            await page.get_by_role("heading", name="My Four Services " + str(width), exact=True).wait_for()
            await page.reload()
            await page.get_by_role("heading", name="My Four Services " + str(width), exact=True).wait_for()
            await page.goto(BASE + "/admin?tab=professional")
            await page.get_by_label("Main headline", exact=True).fill("My Personal Introduction " + str(width))
            await page.get_by_role("button", name="Save Personal Page", exact=True).click()
            await page.get_by_role("status").filter(has_text="Your changes are saved").wait_for()
            await page.goto(BASE + "/meet-rooney")
            await page.get_by_role("heading", name="My Personal Introduction " + str(width), exact=True).wait_for()
            await page.reload()
            await page.get_by_role("heading", name="My Personal Introduction " + str(width), exact=True).wait_for()
            results.append({"width": width, "case": "admin_directory_and_personal_edit_persistence_after_refresh", "passed": True})

            await page.get_by_role("link", name="BOOK A SESSION WITH ROONEY · $197", exact=True).first.click()
            await page.wait_for_url(BASE + "/consultation")
            await fill_consultation(page, f"consultation-{width}@example.org")
            await page.get_by_role("button", name="CONTINUE TO SECURE PAYMENT · $197", exact=True).click()
            await page.wait_for_url("**/__test/consultation-checkout/*")
            await page.get_by_role("button", name="Complete Payment", exact=True).click()
            await page.wait_for_url("**/consultation/confirmed?*")
            await page.get_by_role("heading", name="Your Consultation Payment Is Confirmed.", exact=True).wait_for()
            token = parse_qs(urlparse(page.url).query)["token"][0]
            mail = await (await context.request.get(BASE + "/__test/consultation-mail")).json()
            assert any(f"consultation-{width}@example.org" in message.get("to", []) and "/consultation/resume/" + token in message["html"] for message in mail["messages"])
            await page.reload()
            await page.get_by_role("heading", name="Your Consultation Payment Is Confirmed.", exact=True).wait_for()
            assert await page.locator("body").evaluate("e=>e.scrollWidth<=window.innerWidth+2")
            await page.screenshot(path=f"test_reports/current-part-one-paid-{width}.png", full_page=True)
            await page.route("https://calendly.com/**", lambda route: route.fulfill(status=200, content_type="text/html", body="<h1>Controlled Calendly destination</h1>"))
            await page.get_by_role("button", name="CHOOSE MY MEETING TIME →", exact=True).click()
            await page.wait_for_url("https://calendly.com/**")
            params = parse_qs(urlparse(page.url).query)
            assert params["email"] == [f"consultation-{width}@example.org"]
            assert set(params) == {"name", "email", "utm_content"}
            assert token not in page.url
            await page.goto(BASE + "/consultation/resume/" + token)
            await page.get_by_role("heading", name="Your Consultation Payment Is Confirmed.", exact=True).wait_for()
            await expect(page.get_by_role("button", name="CONTINUE TO SECURE PAYMENT · $197", exact=True)).to_have_count(0)
            results.append({"width": width, "case": "controlled_197_payment_email_paid_resume_and_calendly_handoff", "passed": True})

            await page.goto(BASE + "/consultation")
            await fill_consultation(page, f"cancelled-{width}@example.org")
            await page.get_by_role("button", name="CONTINUE TO SECURE PAYMENT · $197", exact=True).click()
            await page.wait_for_url("**/__test/consultation-checkout/*")
            await page.get_by_role("button", name="Cancel Payment", exact=True).click()
            await page.wait_for_url("**/consultation/resume/*?checkout=cancelled")
            await page.get_by_text(DEFAULTS["consultation"]["cancelMessage"], exact=True).wait_for()
            await expect(page.get_by_role("button", name="CHOOSE MY MEETING TIME →", exact=True)).to_have_count(0)
            results.append({"width": width, "case": "cancelled_payment_never_reveals_booking", "passed": True})

            await page.goto(BASE + "/admin?tab=professional")
            await page.get_by_role("button", name="Consultation Customers", exact=True).click()
            record = page.locator("article.professional-record").filter(has_text=f"consultation-{width}@example.org")
            await record.get_by_role("button", name="Open Full Consultation Record", exact=True).click()
            await page.get_by_label("Private notes before the session", exact=True).fill("Private preparation notes.")
            await page.get_by_label("Private notes after the session", exact=True).fill("Private follow-up notes.")
            await page.get_by_role("button", name="Save Private Notes", exact=True).click()
            await page.get_by_role("status").filter(has_text="Your private notes are saved").wait_for()
            await page.get_by_role("button", name="Resend Secure Booking Link", exact=True).click()
            await page.get_by_role("status").filter(has_text="Booking email delivery: sent").wait_for()
            await expect(page.get_by_test_id("consultation-record")).to_contain_text("link opened")
            results.append({"width": width, "case": "separate_consultation_admin_private_notes_and_resend", "passed": True})
            assert not errors, errors
            await context.close()
        await browser.close()
    Path("test_reports/current-part-one-browser.json").write_text(json.dumps({"provider_transport": "simulated", "cases": results}, indent=2))
    print(json.dumps({"part_one_browser_passed": len(results), "provider_transport": "simulated"}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
