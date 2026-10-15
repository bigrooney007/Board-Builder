"""Read-only checks of the public deployment. No intake, login or payment POSTs."""
import argparse
import asyncio
import json
from pathlib import Path

import requests
from playwright.async_api import async_playwright

ORIGIN = "https://nonprofitboardbuilder.com"
PRODUCTS = ("recruit", "board-fundraising-game", "strategic-planning", "board-recommitment")


async def check(artifacts):
    artifacts.mkdir(parents=True, exist_ok=True)
    results = []
    api_ready = False
    for path in ("/", "/api", "/api/v2/access", *[f"/api/v2/landing-content/{product}" for product in PRODUCTS]):
        try:
            response = requests.get(ORIGIN + path, timeout=20, headers={"Cache-Control": "no-cache"})
            passed = response.status_code == 200
            if path == "/api/v2/access":
                api_ready = passed and response.json().get("allowed") is True
                passed = api_ready
            elif path.startswith("/api/v2/landing-content/"):
                passed = passed and bool(response.json().get("content", {}).get("headline"))
            results.append({"path": path, "passed": passed, "status": response.status_code})
        except Exception as exc:
            results.append({"path": path, "passed": False, "error": type(exc).__name__})
    if api_ready:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(args=["--no-sandbox"])
            for width, height in ((1440, 1000), (390, 844)):
                context = await browser.new_context(viewport={"width": width, "height": height})
                page = await context.new_page()
                for product in PRODUCTS:
                    try:
                        await page.goto(ORIGIN + "/", wait_until="networkidle", timeout=30000)
                        await page.locator(f'.nBB-home-card-button[href="/v2/{product}"]').click(timeout=15000)
                        await page.get_by_role("link", name="Start for Free", exact=True).first.wait_for(timeout=15000)
                        assert not await page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                        await page.screenshot(path=str(artifacts / f"live-{width}-{product}.png"), full_page=True)
                        await page.get_by_role("link", name="Start for Free", exact=True).first.click()
                        await page.get_by_role("heading", name="Tell us about your organization.", exact=True).wait_for(timeout=15000)
                        results.append({"product": product, "width": width, "passed": True, "scope": "homepage to education to free form, no form submitted"})
                    except Exception as exc:
                        results.append({"product": product, "width": width, "passed": False, "error": type(exc).__name__})
                await context.close()
            await browser.close()
    report = {"origin": ORIGIN, "read_only": True, "paid_provider_delivery_verified": False, "passed": bool(api_ready and all(row["passed"] for row in results)), "checks": results}
    (artifacts / "results.json").write_text(json.dumps(report, indent=2))
    print("LIVE_PUBLIC_SMOKE_RESULT=" + json.dumps(report))
    return report["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", default="/tmp/nbb-v2-live-results")
    raise SystemExit(0 if asyncio.run(check(Path(parser.parse_args().artifacts))) else 1)
