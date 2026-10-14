"""Desktop/mobile checks against actual V2 React UI in the local fixture app.

Build frontend locally, start tests/v2_local_app.py, then run this script.
Only loopback origins with the synthetic fixture marker are accepted. Missing
frontend dependencies/build are reported as blocked, never as browser success.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

import httpx
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))
from backend.tests.test_v2_journeys import intake_answers
from tests.v2_layout_harness import check_layout


async def check(base, artifact_dir):
    parsed = urlparse(base)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("This harness only tests a local synthetic fixture, never production.")
    async with httpx.AsyncClient() as client:
        try:
            health = (await client.get(base + "/test/health")).json()
        except Exception as exc:
            raise SystemExit("BLOCKED: start tests/v2_local_app.py before browser acceptance.") from exc
        if health.get("fixture") is not True or health.get("providers") != "synthetic":
            raise SystemExit("Refusing a server that is not the synthetic fixture app.")
        if not health.get("frontend_build"):
            raise SystemExit("BLOCKED: actual frontend/build/index.html is missing. No browser checks ran.")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    findings = []
    async with async_playwright() as playwright:
        executable = os.environ.get("NBB_V2_BROWSER_EXECUTABLE") or ("/usr/bin/chromium" if Path("/usr/bin/chromium").exists() else None)
        browser = await playwright.chromium.launch(executable_path=executable, args=["--no-sandbox"])
        for device, width, height in (("desktop", 1440, 1000), ("mobile", 390, 844)):
            context = await browser.new_context(viewport={"width": width, "height": height})
            response = await context.request.post(base + "/api/v2/preview-access", data={"key": "synthetic-preview-only-key"})
            assert response.status == 200, await response.text()
            page = await context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            for product in ("recruit", "board-fundraising-game", "strategic-planning", "board-recommitment"):
                await page.goto(base + "/", wait_until="networkidle")
                await page.locator(f'.nBB-home-card-button[href="/v2/{product}"]').click()
                await page.wait_for_url(base + "/v2/" + product)
                await page.get_by_role("link", name="Start for Free", exact=True).first.wait_for()
                assert "noindex" in await page.locator('meta[name="robots"]').get_attribute("content")
                overflow = await page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                assert not overflow, f"{device} {product}: horizontal overflow"
                assert not errors, errors
                await check_layout(page, f"{device} {product} education")
                await page.screenshot(path=str(artifact_dir / f"{device}-{product}.png"), full_page=True)
                await page.get_by_role("link", name="Start for Free", exact=True).first.click()
                await page.wait_for_url(base + f"/v2/{product}/start")
                await page.get_by_role("heading", name="Tell us about your organization.", exact=True).wait_for()
                await check_layout(page, f"{device} {product} free entry")
                findings.append(f"PASS {device} {product}: main homepage to education to free intake, noindex, no overflow")
            # Use the genuine API intake and browser checkout/receipt rather than
            # writing a paid entitlement into the fixture database.
            for product in ("recruit", "board-fundraising-game", "strategic-planning", "board-recommitment"):
                created = await context.request.post(base + "/api/v2/journeys", data={"product": product, "name": "Synthetic Leader", "email": "leader@example.test", "organization": "Synthetic Education Trust", "board_count": 5, "desired_count": 2, "goal_amount": 25000})
                assert created.status == 200, await created.text()
                draft = await created.json()
                jid = draft["journey_id"]
                headers = {"X-V2-Draft": draft["draft_token"]}
                saved = await context.request.put(base + f"/api/v2/journeys/{jid}/answers", data={"answers": intake_answers(product)}, headers=headers)
                assert saved.status == 200, await saved.text()
                await page.evaluate("({jid, token}) => sessionStorage.setItem('nbb:v2:draft:' + jid, token)", {"jid": jid, "token": draft["draft_token"]})
                await page.goto(base + f"/v2/{product}/offer?journey_id={jid}", wait_until="networkidle")
                await page.get_by_role("heading", name=re.compile("get|develop|find|next", re.I)).first.wait_for()
                assert await page.locator("iframe").count() == 0, "V2 conversion must not gate sales with a video"
                calendly = page.locator('a[href="https://calendly.com/boardbuilder/recruitboard"]')
                assert await calendly.count() > 0
                await check_layout(page, f"{device} {product} offer")
                assert await page.locator('input[type="file"]').count() == 0, "Branding belongs after payment"
                await page.get_by_role("button", name=re.compile(r"Get my .*197")).click()
                await page.get_by_role("button", name="Pay $197 in this synthetic test").click()
                await page.wait_for_url(re.compile(r"/v2/setup/"), timeout=20000)
                await page.get_by_label("Organization name", exact=True).wait_for()
                assert await page.locator('input[type="file"]').count() == 1
                if product in {"board-fundraising-game", "strategic-planning"}:
                    await page.get_by_label("Meeting date", exact=True).fill("2026-11-30")
                    await page.get_by_label("Meeting time", exact=True).fill("18:00")
                    await page.get_by_label("Time zone", exact=True).fill("Europe/London")
                await page.get_by_role("button", name=re.compile(r"Save and")).click()
                await page.wait_for_url(re.compile(r"/v2/resources/"), timeout=20000)
                await page.get_by_role("heading", level=1).wait_for()
                if product == "recruit":
                    await page.get_by_role("heading", name="Approve Your Board Member Recruitment Profiles", exact=True).wait_for()
                    await page.get_by_role("link", name="View and edit", exact=True).first.click()
                    await page.get_by_test_id("v2-resource-approve").wait_for(state="visible", timeout=20000)
                    await page.get_by_test_id("v2-resource-approve").click()
                    await page.get_by_role("link", name="Open my recruitment pack", exact=True).click()
                    await page.get_by_role("heading", name="Your Board Recruitment Pack", exact=True).wait_for()
                assert not errors, errors
                assert not await page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                await check_layout(page, f"{device} {product} resources")
                await page.screenshot(path=str(artifact_dir / f"{device}-{product}-resources.png"), full_page=True)
                findings.append(f"PASS {device} {product}: offer without branding, synthetic $197 checkout, paid setup, profile-first recruitment or meeting-first invitations, resources")
            await context.close()
        await browser.close()
    (artifact_dir / "results.json").write_text(json.dumps({"origin": base, "provider_mode": "synthetic", "results": findings}, indent=2))
    print("\n".join(findings))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8765")
    parser.add_argument("--artifacts", default="/tmp/nbb-v2-browser-results")
    args = parser.parse_args()
    asyncio.run(check(args.base.rstrip("/"), Path(args.artifacts)))
