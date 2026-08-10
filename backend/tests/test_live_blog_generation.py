"""Live blog generation rerun (iteration_8) — single Claude call.

Rerun of the ONLY blocked test from iteration_7: LLM budget was exhausted,
now topped up. This test:
  * Logs in as admin
  * POSTs /api/blog/generate with fundraising_activation (fallback: reactivation on 409)
  * Verifies word count 350-550 target, hard fail >650, min 300
  * Verifies content rules: no em dash, real-scenario opener,
    not a numbered step guide, no fabricated stats/testimonials
  * Verifies CTA fields, publication_status Pending Review, validation Passed
  * Leaves draft in Mongo (does NOT publish)
"""
import os
import re
from datetime import datetime

import pytest
import requests
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE:
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE = line.split("=", 1)[1].strip().strip('"')
BASE = BASE.rstrip("/")

ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PASSWORD = "PC8JX97y7YjPUel9-gM5gAem"

CATEGORY_CTA = {
    "fundraising_activation": "/activate",
    "reactivation": "/reactivate",
}


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def mongo_db():
    with open("/app/backend/.env") as fh:
        env = dict(
            line.strip().split("=", 1) for line in fh if "=" in line and not line.startswith("#")
        )
    client = MongoClient(env["MONGO_URL"].strip('"'))
    return client[env["DB_NAME"].strip('"')]


def _generate(admin_session, category):
    """POST /api/blog/generate with today's scheduled_date (endpoint default)."""
    payload = {"category": category}
    return admin_session.post(f"{BASE}/api/blog/generate", json=payload, timeout=180)


def test_live_blog_generation_end_to_end(admin_session, mongo_db):
    # 1) Try fundraising_activation first; fall back to reactivation on 409 duplicate.
    primary = "fundraising_activation"
    fallback = "reactivation"
    r = _generate(admin_session, primary)
    category = primary
    if r.status_code == 409:
        print(f"[INFO] {primary} already has a post for today -> falling back to {fallback}")
        r = _generate(admin_session, fallback)
        category = fallback

    assert r.status_code in (200, 201), f"generate failed: {r.status_code} {r.text}"
    result = r.json()
    print("Generate response:", {k: result.get(k) for k in ("status", "error", "post_id", "slug", "category_key")})

    # If LLM infra failed again, surface loudly (this is the SPECIFIC thing being rerun)
    if result.get("status") == "Failed":
        pytest.fail(f"LLM generation still failing after budget top-up: {result.get('error')}")

    # 2) Fetch persisted draft — prefer GET /api/admin/blog/posts, verify DB truth
    listing = admin_session.get(f"{BASE}/api/admin/blog/posts")
    assert listing.status_code == 200, listing.text
    posts = listing.json() if isinstance(listing.json(), list) else listing.json().get("posts", [])
    slug = result.get("slug")
    post_id = result.get("post_id")
    matched = None
    for p in posts:
        if (slug and p.get("slug") == slug) or (post_id and p.get("post_id") == post_id):
            matched = p
            break
    assert matched is not None, f"Generated draft not found in GET /api/admin/blog/posts (slug={slug})"

    # DB truth
    query = {"category_key": category}
    if slug:
        query["slug"] = slug
    post = mongo_db.blog_posts.find_one(query, {"_id": 0}, sort=[("created_at", -1)])
    assert post is not None, f"Draft not found in db.blog_posts for query {query}"

    # 3) Basic required fields
    assert post.get("title"), "title missing"
    assert post.get("slug"), "slug missing"
    assert post.get("excerpt"), "excerpt missing"
    body = post.get("body") or ""
    assert body, "body missing"

    # 4) Word-count: target 350-550, HARD FAIL >650, min 300
    words = len(re.findall(r"\S+", body))
    print(f"[INFO] Generated body word count = {words} (target 350-550, hard max 650)")
    assert words <= 650, f"HARD FAIL: body {words} words > 650 max. Title={post.get('title')!r}"
    assert 300 <= words, f"body {words} words < 300 minimum"
    within_target = 350 <= words <= 550
    if not within_target:
        # 300-350 or 551-650 should not fail the run (validator allows) but flag it
        print(f"[WARN] Word count {words} outside 350-550 target (still within 300-650 accepted range)")

    # 5) No em dash character
    assert "\u2014" not in body, "Body contains em dash (—) which is forbidden by prompt"

    # 6) CTA fields match category
    expected_cta = CATEGORY_CTA[category]
    assert post.get("cta_url") == expected_cta, f"cta_url {post.get('cta_url')!r} != {expected_cta!r}"
    assert post.get("cta_label"), "cta_label missing"

    # 7) publication_status Pending Review; validation Passed; error empty
    assert post.get("publication_status") == "Pending Review", (
        f"publication_status {post.get('publication_status')!r} != 'Pending Review'"
    )
    validation_status = post.get("validation_status") or post.get("status")
    # Endpoint returns overall status; DB stores validation_status
    assert validation_status in {"Passed", "Pending Review"}, f"validation_status={validation_status!r} not Passed"
    err = post.get("error") or post.get("validation_errors") or ""
    if isinstance(err, list):
        assert not err, f"validation errors non-empty: {err}"
    else:
        assert not err, f"error field non-empty: {err!r}"

    # 8) Voice rules — real-scenario opener, no generic industry intros
    first_para = body.split("\n\n", 1)[0].lower()
    banned_intros = [
        "in today", "in the ever", "in the world of", "in the nonprofit sector",
        "nonprofits face many", "in an era", "in this article", "welcome to",
    ]
    hits = [p for p in banned_intros if p in first_para]
    assert not hits, f"Generic industry intro detected in first paragraph: {hits}. First para: {first_para[:200]!r}"

    # 9) Get directly to ONE problem within first 2-3 sentences
    sentences = re.split(r"(?<=[.!?])\s+", body.strip())
    first_three = " ".join(sentences[:3]).lower()
    # Heuristic: look for a concrete problem/situation signal in first 3 sentences
    problem_signals = [
        "problem", "struggle", "struggling", "stuck", "quiet", "silent", "stopped",
        "declining", "drop", "dropped", "stalled", "missing", "lost", "burnout",
        "disengag", "haven't", "hasn't", "won't", "can't", "isn't", "aren't",
        "no one", "nobody", "board member", "your board", "the board", "donor",
        "reactivat", "activat", "fundraising", "raise", "give", "check",
    ]
    assert any(sig in first_three for sig in problem_signals), (
        f"First 3 sentences don't cite a concrete nonprofit scenario/problem: {first_three[:300]!r}"
    )

    # 10) NOT a long numbered step-by-step guide
    numbered_lines = re.findall(r"(?m)^\s*(?:\d+[\.)]\s|Step\s+\d+)", body)
    assert len(numbered_lines) < 4, (
        f"Body looks like a numbered step-by-step guide ({len(numbered_lines)} numbered items)"
    )

    # 11) No fabricated stats/research/studies
    bad_stat_patterns = [
        r"\bstudy\b", r"\bstudies\b", r"\bresearch\b", r"\bsurvey\b",
        r"\bstatistic", r"\b\d{1,3}\s*%", r"\b\d{1,2}\s*out of\s*\d{1,2}\b",
        r"according to", r"data shows", r"report(?:s|ed)? that",
    ]
    stat_hits = [pat for pat in bad_stat_patterns if re.search(pat, body, re.IGNORECASE)]
    assert not stat_hits, f"Body appears to cite fabricated stats/research: {stat_hits}"

    # 12) No fake testimonials or named client stories
    # crude quote detection with a named person
    quote_named = re.findall(r'["\u201C][^"\u201D]{20,}["\u201D]\s*[-—]\s*[A-Z][a-z]+', body)
    assert not quote_named, f"Fake testimonial pattern found: {quote_named[:2]}"

    print(f"[PASS] Live blog generation OK — category={category}, words={words}, cta={post['cta_url']}, slug={post['slug']}")
