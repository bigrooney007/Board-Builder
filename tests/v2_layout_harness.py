"""Check shared V2 CSS in Chromium without frontend dependencies or providers.

These synthetic markup fixtures cover the page layout families and real product
copy. They verify typography, alignment and responsive sizing, not React routing,
checkout, application behavior or complete end-to-end acceptance. The separate
v2_browser_harness.py tests the built React app when its build is available.
"""

import argparse
import asyncio
import base64
import html
import json
import os
from pathlib import Path
import subprocess

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]


def escape(value):
    return html.escape(str(value), quote=True)


def fixtures():
    source = (ROOT / "frontend/src/v2/content.js").read_text()
    script = source.replace("export const ", "const ") + "\nconsole.log(JSON.stringify(PRODUCTS));"
    products = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    pages = {}
    button = '<button class="v2-btn">Save and continue</button>'
    field = '<label>Your answer<textarea rows="5">Synthetic test information only.</textarea></label>'
    for slug, product in products.items():
        image_path = ROOT / "frontend/public" / product["image"].lstrip("/")
        image = "data:image/png;base64," + base64.b64encode(image_path.read_bytes()).decode()
        steps = "".join(f'<li><span class="v2-step-number">{i + 1}</span><div><h3>{escape(title)}</h3><p>{escape(text)}</p></div></li>' for i, (title, text) in enumerate(product["teaching"]))
        # Match ProductLandingPage's side-by-side hero and centered mobile stack.
        pages[f"{slug}-education"] = (False, f'<section class="v2-hero"><div class="v2-hero-copy"><p class="v2-eyebrow">{escape(product["eyebrow"])}</p><h1>{escape(product["headline"])}</h1><p>{escape(product["intro"])}</p><a class="v2-button" href="#">Start for Free</a><span class="v2-hero-note">Learn the process before you decide to purchase.</span></div><img class="v2-product-image" src="{image}" alt="Product image"></section><section class="v2-education"><h2>What you and your organization will do</h2><ol class="v2-steps">{steps}</ol><a class="v2-button" href="#">Start for Free</a></section>')
        next_steps = "".join(f'<article><h3>{escape(title)}</h3><p>{escape(text)}</p></article>' for title, text in product["next"])
        pages[f"{slug}-offer"] = (False, f'<section class="v2-intro"><p class="v2-eyebrow">YOUR INTRODUCTORY ANSWERS ARE SAVED</p><h1>{escape(product["offerHeading"])}</h1><p>You have shared the starting information for your organization.</p></section><section class="v2-education v2-next-steps"><h2>What happens next</h2>{next_steps}</section><form class="v2-card v2-branding-card"><h2>Confirm the details for your resources</h2><div class="v2-branding-fields"><label>Organization name<input value="Synthetic Education Trust"></label><label>Organization logo, optional<input type="file"><small>PNG, JPEG or WebP, up to 1 MB.</small></label></div><section class="v2-purchase-options"><article class="v2-purchase-card"><h2>Get Everything I Need and Do It Myself</h2><p class="v2-price">$197<span>One purchase for {escape(product["name"])}</span></p><p>{escape(product["outcome"])}</p><button class="v2-button">Get my {escape(product["name"])} tools for $197</button></article><article class="v2-purchase-card"><h2>Let Us Work With You or Do It for You</h2><p>Book a conversation and we will discuss a separate quotation.</p><a class="v2-button" href="#">Book a Call</a></article></section></form>')
    titles = {
        "resources": "Your Board Recruitment Pack",
        "resource-editor": "Board Recruitment Announcement",
        "responses": "Submitted responses",
        "applicant-response": "Synthetic Candidate's response",
        "invitations": "Invite your board members and other participants",
        "campaign": "Launch your board recruitment campaign",
        "fundraising-group": "Your Group Fundraising Game",
        "strategic-group": "Your Group Strategic Planning Session",
        "shared-meeting": "Your board's group discussion",
    }
    for key, title in titles.items():
        content = f'<section class="v2-card"><h2>Your next action</h2><p>Review the information your organization supplied, then confirm the action you want to take.</p><div class="v2-actions">{button}<a class="v2-btn v2-btn-secondary" href="#">Download approved document</a></div><label>Shareable form link<input readonly value="https://example.test/v2/forms/a-very-long-opaque-test-link"></label></section>'
        if key == "resource-editor":
            content += '<article class="v2-document"><p class="v2-document-org">Synthetic Education Trust</p><h2>Board Recruitment Announcement</h2><div class="v2-document-text">A synthetic document for reviewing text size and comfortable reading widths.\n\nYour organization can edit this wording before approval.</div></article>' + field
        if key in {"resources", "responses"}:
            content += '<section class="v2-card"><h2>Your resources</h2><ul class="v2-resource-list"><li><div><a href="#">A resource title with a long organization name to test wrapping on narrow screens</a><small>Version 1 needs approval</small></div><a class="v2-btn" href="#">Review resource</a></li></ul></section>'
        pages[key] = (False, f'<div class="v2-action-page"><header><h1>{title}</h1><p>Read your organization\'s information and take the next action here.</p></header>{content}</div>')
    for key, title in {
        "free-intake": "Tell us about your organization.",
        "intake-question": "What does your organization need its board members to help accomplish?",
        "payment-return": "Your payment confirmation",
        "recovery": "Find your purchased resources.",
        "preview-access": "Open your Board Builder preview",
        "not-found": "We could not find this page.",
    }.items():
        pages[key] = (True, f'<section class="v2-card {"v2-question" if key == "intake-question" else ""}"><h1>{title}</h1><p>Read these instructions and share the information your organization has available.</p>{field}<div class="v2-actions">{button}</div></section>')
    for key, title in {"application": "Board application form", "fundraising-form": "Your fundraising ideas", "strategic-form": "Your strategic planning ideas", "recommitment-form": "Your board recommitment response"}.items():
        pages[key] = (True, f'<div class="v2-action-page"><header class="v2-form-brand"><p class="v2-eyebrow">Synthetic Education Trust</p><h1>{title}</h1><p>Share your own ideas. You can indicate uncertainty when you do not know an answer.</p></header><form class="v2-card"><h2>Your contribution</h2><div class="v2-grid"><label>Your name<input value="Synthetic Participant"></label><label>Your email address<input type="email" value="participant@example.test"></label></div>{field}<div class="v2-actions">{button}</div></form></div>')
    pages["product-index"] = (False, '<section class="v2-intro"><h1>Practical tools for the work your board needs to do.</h1><p>Choose the process your organization needs.</p></section><div class="v2-product-grid">' + "".join(f'<article class="v2-card"><h2>{escape(p["name"])}</h2><p>{escape(p["outcome"])}</p><a class="v2-button" href="#">Learn the process</a></article>' for p in products.values()) + '</div>')
    pages["marketplace"] = (False, '<section class="v2-intro"><h1>Board opportunities in this private preview</h1><p>Review a board opportunity and complete its application form.</p></section><div class="v2-product-grid"><article class="v2-card"><h2>Synthetic Education Trust</h2><p>This synthetic opportunity is for layout verification only.</p><a class="v2-button" href="#">Review the opportunity and apply</a></article></div>')
    return pages


async def check_layout(page, label):
    """Also usable against the actual built app by v2_browser_harness.py."""
    issues = await page.evaluate("""() => {
      const problems = [];
      const visible = el => el.getBoundingClientRect().width > 0 && el.getBoundingClientRect().height > 0;
      if (document.documentElement.scrollWidth > innerWidth + 1) problems.push('horizontal overflow');
      const main = document.querySelector('.v2-main');
      if (main) {
        const r = main.getBoundingClientRect();
        if (Math.abs(r.x + r.width / 2 - innerWidth / 2) > 2) problems.push('main column is off-center');
      }
      for (const el of document.querySelectorAll('.v2-app')) {
        if (parseFloat(getComputedStyle(el).fontSize) < 16) problems.push('body text below 16px');
      }
      for (const el of document.querySelectorAll('.v2-app label, .v2-app input:not([type=checkbox]):not([type=radio]), .v2-app textarea, .v2-app select')) {
        if (visible(el) && parseFloat(getComputedStyle(el).fontSize) < 16) problems.push('small form text');
      }
      for (const el of document.querySelectorAll('.v2-hero-copy h1, .v2-intro h1, .v2-action-page header h1, .v2-main-narrow > .v2-card > h1')) {
        if (visible(el) && getComputedStyle(el).textAlign !== 'center') problems.push('page title is not centered');
      }
      for (const el of document.querySelectorAll('.v2-app .v2-button, .v2-app .v2-btn')) {
        if (visible(el) && el.getBoundingClientRect().height < 44) problems.push('small action target');
      }
      for (const el of document.querySelectorAll('.v2-document-text, .v2-steps p, .v2-next-steps article p')) {
        if (visible(el) && getComputedStyle(el).textAlign !== 'left') problems.push('long copy is not left-aligned');
      }
      return problems;
    }""")
    assert not issues, f"{label}: {issues}"


async def check(artifacts):
    artifacts.mkdir(parents=True, exist_ok=True)
    # Original global CSS included so the revised styles are checked in context.
    css = "\n".join((ROOT / p).read_text() for p in ["frontend/src/App.css", "frontend/src/funnels/guided-products.css", "frontend/src/v2/v2.css", "frontend/src/v2/actions.css"])
    css = "html{font-size:16px} body{margin:0}" + css
    results = []
    async with async_playwright() as driver:
        executable = os.environ.get("NBB_V2_BROWSER_EXECUTABLE") or ("/usr/bin/chromium" if Path("/usr/bin/chromium").exists() else None)
        browser = await driver.chromium.launch(executable_path=executable, args=["--no-sandbox"])
        for width in (320, 390, 768, 1440):
            page = await browser.new_page(viewport={"width": width, "height": 1000})
            for key, (narrow, body) in fixtures().items():
                markup = f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>{css}</style></head><body><div class="v2-app"><header class="v2-header"><a class="v2-brand" href="#"><span class="v2-brand-mark">BB</span><span>Nonprofit Board Builder<small>Practical tools for your board</small></span></a><a class="v2-recovery-link" href="#">Recover my resources</a></header><main class="v2-main {"v2-main-narrow" if narrow else ""}">{body}</main><footer class="v2-footer"><p>Nonprofit Board Builder</p><span>Private testing version</span></footer></div></body></html>'
                await page.set_content(markup)
                await check_layout(page, f"{width}px {key}")
                if width in (390, 1440) and key in {"recruit-education", "recruit-offer", "resource-editor", "fundraising-form"}:
                    await page.screenshot(path=str(artifacts / f"{width}-{key}.png"), full_page=True)
                results.append(f"PASS {width}px {key}")
            await page.close()
        await browser.close()
    (artifacts / "results.json").write_text(json.dumps({"scope": "CSS layout fixtures, not React end-to-end tests", "results": results}, indent=2))
    print(f"PASS {len(results)} Chromium CSS layout checks across 320, 390, 768 and 1440px.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", default="/tmp/nbb-v2-layout-results")
    asyncio.run(check(Path(parser.parse_args().artifacts)))
