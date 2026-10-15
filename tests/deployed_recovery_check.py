"""Live public deployment checks. No logins, charges, email sends or form writes."""
import asyncio
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from playwright.async_api import async_playwright, expect

BASE = "https://nonprofitboardbuilder.com"
OUT = Path("test_reports/deployed-recovery")
PRODUCTS = [
    ("recruitment", "/recruit", "/recruit/start", "recruit-home"),
    ("board-fundraising-game", "/board-fundraising-game", "/board-fundraising/start", "bfg"),
    ("strategic-planning", "/strategic-planning", "/strategic-planning/start", "strategic-planning"),
    ("board-recommitment", "/board-recommitment", "/board-recommitment/start", "board-recommitment"),
]


def fetch(path):
    try:
        with urlopen(Request(BASE + path, headers={"Cache-Control": "no-cache", "User-Agent": "NBB-Owner-Deployment-Check"}), timeout=45) as response:
            return response.status, response.read().decode()
    except HTTPError as error:
        return error.code, error.read().decode()


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []
    def record(name, passed, **details):
        checks.append({"check": name, "passed": bool(passed), **details})
        print(json.dumps(checks[-1]), flush=True)
    status, home = await asyncio.to_thread(fetch, "/")
    record("public_homepage", status == 200, status=status)
    scripts = re.findall(r'<script[^>]+src="([^"]+)', home)
    main_js = next((p for p in scripts if "/static/js/main." in p), None)
    if main_js:
        status, bundle = await asyncio.to_thread(fetch, main_js)
        record("deployed_recovery_features", status == 200 and "offer-text-roadmap" in bundle and "/app/board-recruitment/setup/materials" in bundle,
               status=status, asset=main_js)
        record("no_v2_entry_routes_in_bundle", "/v2/recruit" not in bundle and "/v2/board-fundraising-game" not in bundle)
    else:
        record("deployed_recovery_features", False, reason="Main JavaScript asset not found")
    for path in ["/api", "/api/game/content"] + ["/api/platform/homepages/" + k for p in PRODUCTS for k in (p[0], "offer-" + p[0])]:
        try:
            status, body = await asyncio.to_thread(fetch, path)
            value = json.loads(body)
            passed = status == 200
            if "/homepages/" in path: passed = passed and isinstance(value.get("content"), dict)
            record(path, passed, status=status)
        except Exception as error:
            record(path, False, error=str(error)[:200])
    for path in ["/api/admin/platform/homepages", "/api/workspace/interview-scheduling", "/api/members/me"]:
        status, _ = await asyncio.to_thread(fetch, path)
        record("private_access:" + path, status in (401, 403), status=status)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for width, height in [(1440, 1000), (390, 844)]:
            context = await browser.new_context(viewport={"width": width, "height": height})
            page = await context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            # Suppress analytics and all other mutation requests during public checks.
            async def read_only(route):
                if route.request.method not in ("GET", "HEAD", "OPTIONS"):
                    return await route.fulfill(status=204, body="")
                await route.continue_()
            await page.route("**/api/**", read_only)
            for product, home_path, start, prefix in PRODUCTS:
                errors.clear()
                try:
                    await page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
                    link = page.locator(f'a[href="{start}"]').first
                    await expect(link).to_be_visible(timeout=20000)
                    await link.click()
                    await page.wait_for_url("**" + start)
                    await expect(page.locator("form")).to_be_visible(timeout=20000)
                    await page.goto(BASE + home_path, wait_until="domcontentloaded", timeout=60000)
                    await expect(page.locator("h1")).to_be_visible()
                    await expect(page.locator(f'a[href="{start}"]').first).to_be_visible()
                    count = page.get_by_test_id(prefix + "-testimonial-count")
                    await expect(count).to_contain_text("1 /")
                    await page.get_by_test_id(prefix + "-testimonial-next").click()
                    await expect(count).to_contain_text("2 /")
                    no_overflow = await page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                    await page.screenshot(path=str(OUT / f"{product}-{width}.png"), full_page=True)
                    await page.locator(f'a[href="{start}"]').first.click()
                    await page.wait_for_url("**" + start)
                    await expect(page.locator("form")).to_be_visible(timeout=20000)
                    no_overflow = no_overflow and await page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                    record(f"browser:{product}:{width}", no_overflow and not errors, no_overflow=no_overflow, javascript_errors=list(errors))
                except Exception as error:
                    record(f"browser:{product}:{width}", False, error=str(error)[:1000], javascript_errors=list(errors))
                    await page.screenshot(path=str(OUT / f"FAILED-{product}-{width}.png"), full_page=True)
            await context.close()
        await browser.close()
    report = {"origin": BASE, "passed": all(r["passed"] for r in checks), "checks": checks,
              "customer_forms_submitted": False, "live_emails_sent": 0,
              "paid_workflows_tested": False, "admin_editing_tested": False}
    (OUT / "report.json").write_text(json.dumps(report, indent=2))
    if not report["passed"]: raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
