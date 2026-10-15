"""Production-bundle browser checks with real content API/Mongo and substituted
customer/payment/email providers. No production endpoints or credentials used.
"""
import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from playwright.async_api import async_playwright, expect

BASE = "http://127.0.0.1:8765"
OUT = Path("test_reports")
PRODUCTS = [
    ("recruitment", "/recruit", "/recruit/start", "/recruit/walkthrough?token=synthetic", "recruit-home"),
    ("board-fundraising-game", "/board-fundraising-game", "/board-fundraising/start", "/game/upgrade", "bfg"),
    ("strategic-planning", "/strategic-planning", "/strategic-planning/start", "/strategic-planning/video?token=synthetic", "strategic-planning"),
    ("board-recommitment", "/board-recommitment", "/board-recommitment/start", "/board-recommitment/video?token=synthetic", "board-recommitment"),
]
TYPES = ["board_opportunity", "board_recruitment_job_post", "recruitment_emails", "social_posts", "referral_request_email"]


def material(kind, status="Generated"):
    return {"material_id": kind, "type": kind, "title": kind, "status": status, "current_version": 1,
            "application_id": "", "versions": [{"version": 1, "display_text": "Synthetic campaign text", "text": "Synthetic campaign text", "rendered_text": "Synthetic campaign text", "structured": {}}]}


async def main():
    OUT.mkdir(exist_ok=True)
    async with httpx.AsyncClient() as http:
        for _ in range(60):
            try:
                token = (await http.get(BASE + "/__test/session")).json()["token"]
                break
            except Exception:
                await asyncio.sleep(1)
        else:
            raise RuntimeError("Local acceptance server did not start")
    results = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for width, height in [(1440, 1000), (390, 844)]:
            context = await browser.new_context(viewport={"width": width, "height": height})
            await context.add_cookies([{"name": "admin_access_token", "value": token, "url": BASE}])
            page = await context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            state = {"product": "strategic-planning", "schedule": {}, "profile": False, "launched": False,
                     "fail_schedule": False, "fail_launch": False, "publishes": 0, "checkout": [],
                     "materials": [material("powerhouse_board_blueprint")] + [material(k) for k in TYPES]}

            async def intercept(route):
                req = route.request
                path = urlparse(req.url).path.removeprefix("/api")
                if path.startswith(("/platform/homepages/", "/admin/platform/homepages")) or path == "/game/content":
                    return await route.continue_()
                body = req.post_data_json if req.method in ("POST", "PUT", "PATCH") and req.post_data else {}
                data = {}
                status = 200
                if path == "/members/me":
                    data = {"member": {"user_id": "synthetic-owner", "first_name": "Sample", "email": "sample@example.test", "entitlements": ["recruitment_workspace"]}}
                elif path == "/auth/me": data = {"user_id": "acceptance-admin", "role": "admin"}
                elif path == "/admin/applicants": data = []
                elif path.startswith("/payments/"):
                    state["checkout"].append({"path": path, "body": body})
                    data = {"checkout_url": BASE + "/__checkout-captured"}
                elif path.startswith("/guided/context/"):
                    data = {"product": state["product"], "prepayment_complete": True}
                elif path == "/game/free": data = {"complete": True, "unlocked": False, "goal_amount": 250000}
                elif path.startswith("/recruit/free/"):
                    data = {"token": "synthetic", "lead_id": "synthetic-lead", "result": {"priority_roles": []},
                            "answers": {k: "Synthetic answer" for k in ["mission", "current_board", "desired_board_members", "board_type", "support_needs", "why_join"]}}
                elif path == "/workspace/interview-scheduling":
                    if req.method == "PUT":
                        if state["fail_schedule"]:
                            status, data = 422, {"detail": "Synthetic scheduling failure"}
                        else:
                            state["schedule"] = body
                    if status == 200: data = {"scheduling": state["schedule"]}
                elif path == "/workspace/board-profiles":
                    data = {"priority_roles": [{"role_name": "Community Leader", "why_this_person_is_important": "Local knowledge", "how_this_person_can_support": "Build relationships"}],
                            "material": state["materials"][0], "desired_count": 1}
                elif path == "/workspace/materials": data = {"materials": state["materials"]}
                elif path.startswith("/workspace/materials/") and req.method == "PUT":
                    kind = path.split("/")[-1]
                    item = next(m for m in state["materials"] if m["material_id"] == kind)
                    item["versions"][0]["display_text"] = body["display_text"]
                    data = {"material": item}
                elif path.startswith("/workspace/materials/") and path.endswith("/approve"):
                    kind = path.split("/")[-2]
                    next(m for m in state["materials"] if m["material_id"] == kind)["status"] = "Approved"
                    if kind == "powerhouse_board_blueprint": state["profile"] = True
                elif path == "/workspace/opportunity/publish":
                    state["publishes"] += 1
                    if state["fail_launch"]: status, data = 503, {"detail": "Synthetic launch failure"}
                    else: state["launched"] = True; data = {"status": "Published"}
                elif path == "/workspace/opportunity":
                    approved = all(m["status"] == "Approved" for m in state["materials"])
                    data = {"opportunity": {"slug": "synthetic", "status": "Published" if state["launched"] else "Draft", "organization_name": "Synthetic Organization"},
                            "readiness": {"profiles_approved": state["profile"], "scheduling_saved": bool(state["schedule"]), "application_saved": True, "materials_approved": approved},
                            "preparation": {"status": "Complete"}, "core_questions": []}
                elif path.endswith("/applications"): data = {"applications": []}
                elif path == "/platform/videos": data = {"videos": []}
                await route.fulfill(status=status, json=data)

            await page.route("**/api/**", intercept)
            for product, home, start, offer, prefix in PRODUCTS:
                state["product"] = product
                # Exercise the actual existing admin and real save endpoint for each page.
                for key, field, destination in [(product, "Headline", home), ("offer-" + product, "Heading", offer)]:
                    await page.goto(BASE + "/admin?tab=homepages")
                    editor = page.get_by_test_id("clean-homepage-editor")
                    await expect(editor).to_be_visible()
                    await editor.locator("select").select_option(key)
                    control = editor.locator("label").filter(has=page.get_by_text(field, exact=True)).locator("input,textarea")
                    await expect(control).to_be_visible()
                    marker = f"My exact {width} words for {key}"
                    await control.fill(marker)
                    extra_fields = ["Introduction", "Steps Heading", "Steps 1", "Self Guided Description", "Supported Description", "Offer Heading"] if key.startswith("offer-") else ["Intro Heading"] if product in ("recruitment", "board-fundraising-game") else ["Process Heading", "Deliverables Heading", "Final Heading"]
                    extras = []
                    for label in extra_fields:
                        value = marker + " " + label
                        extra = editor.locator("label").filter(has=page.get_by_text(label, exact=True)).locator("input,textarea")
                        await expect(extra).to_be_visible()
                        await extra.fill(value)
                        extras.append((label, value))
                    if key == "board-fundraising-game":
                        version = editor.locator("label").filter(has=page.get_by_text("Content Version", exact=True)).locator("input")
                        await version.fill("1")  # Older saved content must still win.
                    await editor.get_by_role("button", name="SAVE HOME PAGE TEXT").click()
                    await expect(editor.get_by_text("Home page text saved.", exact=True)).to_be_visible()
                    await page.reload()
                    await editor.locator("select").select_option(key)
                    await expect(control).to_have_value(marker)
                    for label, value in extras:
                        await expect(editor.locator("label").filter(has=page.get_by_text(label, exact=True)).locator("input,textarea")).to_have_value(value)
                    await page.goto(BASE + destination)
                    await expect(page.locator("h1")).to_have_text(marker)
                    for _, value in extras:
                        await expect(page.get_by_text(value, exact=False).first).to_be_visible()
                    assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                    assert errors == [], errors
                    if key.startswith("offer-"):
                        roadmap = page.get_by_test_id("offer-text-roadmap")
                        await expect(roadmap).to_be_visible()
                        assert await roadmap.evaluate("e => getComputedStyle(e).display") == "block"
                        assert await page.locator("iframe").count() == 0
                        assert await roadmap.evaluate("e => Math.abs(e.getBoundingClientRect().x + e.clientWidth/2 - innerWidth/2) < 3")
                        # Both original checkout handoffs must retain their paths/payloads.
                        for choice in ["self-guided", "supported"]:
                            await page.goto(BASE + destination)
                            await page.get_by_test_id(f"{product}-{choice}-buy").click()
                            await page.wait_for_url("**/__checkout-captured")
                            call = state["checkout"][-1]
                            expected = "/payments/supported-checkout" if choice == "supported" else (
                                "/payments/checkout" if product == "recruitment" else "/payments/game-checkout" if product == "board-fundraising-game" else "/payments/guided-checkout")
                            assert call["path"] == expected, call
                            if product == "recruitment" and choice == "self-guided": assert call["body"]["tier"] == "497"
                    else:
                        count = page.get_by_test_id(prefix + "-testimonial-count")
                        await expect(count).to_contain_text("1 /")
                        await page.get_by_test_id(prefix + "-testimonial-next").click()
                        await expect(count).to_contain_text("2 /")
                        await page.get_by_test_id(prefix + "-testimonial-previous").click()
                        await expect(count).to_contain_text("1 /")
                        await page.locator(f'a[href="{start}"]').first.click()
                        await page.wait_for_url("**" + start)
                        await expect(page.locator("form")).to_be_visible()
                    assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                    results.append({"width": width, "page": key, "saved_reload": True, "passed": True})
            # Real setup/material components, with safe substituted customer API state.
            await page.goto(BASE + "/app/board-recruitment/setup")
            await page.get_by_role("button", name="APPROVE THESE BOARD MEMBERS", exact=True).click()
            await expect(page.get_by_test_id("interview-scheduling-setup")).to_be_visible()
            await page.get_by_label("I will give candidates available times").check()
            await page.get_by_label("Your available interview dates and times").fill("Tuesday 10 AM UTC")
            state["fail_schedule"] = True
            await page.get_by_role("button", name="SAVE INTERVIEW SCHEDULING", exact=True).click()
            await expect(page.get_by_role("alert")).to_have_text("Synthetic scheduling failure")
            assert page.url.endswith("/setup")
            assert state["publishes"] == 0
            state["fail_schedule"] = False
            await page.get_by_role("button", name="SAVE INTERVIEW SCHEDULING", exact=True).click()
            await page.wait_for_url("**/setup/materials")
            assert state["schedule"]["availability"] == "Tuesday 10 AM UTC"
            await page.reload()
            await page.get_by_test_id("edit-board_opportunity").click()
            await page.get_by_test_id("edit-board_opportunity-textarea").fill("Synthetic approved opportunity after editing")
            await page.get_by_test_id("save-board_opportunity").click()
            await page.reload()
            await expect(page.get_by_test_id("material-board_opportunity-display")).to_have_text("Synthetic approved opportunity after editing")
            for kind in TYPES:
                await expect(page.get_by_test_id("material-" + kind)).to_be_visible()
                await page.get_by_test_id("approve-" + kind).click()
            # Separate launch instance refreshes readiness using its existing polling.
            await expect(page.get_by_test_id("publish-button")).to_be_enabled(timeout=15000)
            assert state["publishes"] == 0
            state["fail_launch"] = True
            await page.get_by_test_id("publish-button").click()
            await expect(page.get_by_text("Synthetic launch failure", exact=True)).to_be_visible()
            assert page.url.endswith("/setup/materials")
            assert errors == [], errors
            state["fail_launch"] = False
            await page.get_by_test_id("publish-button").click()
            await page.wait_for_url("**/app/board-recruitment#br-section-applicants")
            await page.goto(BASE + "/app/board-recruitment/setup/materials")
            await page.wait_for_url("**/app/board-recruitment#br-section-applicants")
            assert state["publishes"] == 2  # One failed attempt, one successful launch, no refresh POST.
            results.append({"width": width, "recruitment": "approval/schedule/failure/retry/materials/launch/recovery", "passed": True})
            # Destination URL is checked; the unchanged dashboard itself is outside this fixture.
            await page.goto(BASE + "/recruit/walkthrough?token=synthetic")
            await expect(page.get_by_test_id("offer-text-roadmap")).to_be_visible()
            await page.screenshot(path=str(OUT / f"recovery-{width}.png"), full_page=True)
            await context.close()
        await browser.close()
    report = {"passed": True, "cases": results, "real_mongo_content": True, "customer_apis_and_providers": "substituted", "live_delivery_verified": False}
    (OUT / "recovery-browser.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    asyncio.run(main())
