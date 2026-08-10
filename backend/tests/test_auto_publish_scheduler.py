"""Iteration 9 verification: scheduler auto-publish behavior.

Tests marketing_service.create_scheduled_blog_post behavior with the
publish_now toggle, validation-failure path (owner alert),
public /api/blog/posts gate, and confirms marketing_loop source uses
publish_now=True. claude_blog + send_owner_alert are monkeypatched --
NO live LLM/email calls made.
"""
import asyncio
import inspect
import os
import textwrap
import uuid

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

import marketing_service


def _load_backend_url():
    val = os.environ.get("REACT_APP_BACKEND_URL")
    if val:
        return val.rstrip("/")
    try:
        with open("/app/frontend/.env") as fh:
            for line in fh:
                if line.startswith("REACT_APP_BACKEND_URL"):
                    return line.split("=", 1)[1].strip().strip('"').rstrip("/")
    except FileNotFoundError:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not configured")


BASE_URL = _load_backend_url()
TEST_TAG = f"TEST-AUTOPUB-{uuid.uuid4().hex[:8]}"


def _get_db():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return client, client[os.environ["DB_NAME"]]


def _cleanup(db):
    async def _do():
        await db.blog_posts.delete_many({"scheduled_date": {"$regex": f"^{TEST_TAG}"}})
    asyncio.get_event_loop().run_until_complete(_do())


def _valid_article(title_suffix: str) -> dict:
    paragraph = (
        "Nonprofit boards often stall when responsibilities are unclear and no single person "
        "understands what is expected of them personally. The founder ends up carrying too much "
        "work while the board watches from the sidelines and never takes ownership of what actually "
        "moves the mission forward each quarter for the organization."
    )
    body = "\n\n".join([paragraph] * 7)
    while len(body.split()) < 340:
        body += "\n\n" + paragraph
    return {
        "title": f"Auto Publish Verification {title_suffix} {uuid.uuid4().hex[:6]}",
        "excerpt": "A short excerpt describing the article without any banned phrases.",
        "body": body,
    }


def _invalid_article(title_suffix: str) -> dict:
    return {
        "title": f"Invalid Article {title_suffix}",
        "excerpt": "Short excerpt.",
        "body": "This body is way too short \u2014 and also uses an em dash which is banned.",
    }


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def db(event_loop):
    client, database = _get_db()
    yield database
    event_loop.run_until_complete(
        database.blog_posts.delete_many({"scheduled_date": {"$regex": f"^{TEST_TAG}"}})
    )
    client.close()


# ---------- Behavior tests ----------

def test_publish_now_true_publishes_valid_article(db, event_loop, monkeypatch):
    calls = {"n": 0, "alerts": []}

    async def fake_claude(category_key, recent_titles, correction="", draft=None):
        calls["n"] += 1
        return _valid_article("published")

    async def fake_alert(subject, rows):
        calls["alerts"].append(subject)

    monkeypatch.setattr(marketing_service, "claude_blog", fake_claude)
    monkeypatch.setattr(marketing_service, "send_owner_alert", fake_alert)

    scheduled_date = f"{TEST_TAG}-pub"
    result = event_loop.run_until_complete(
        marketing_service.create_scheduled_blog_post(
            db, "recruitment", scheduled_date, publish_now=True
        )
    )
    assert result["status"] == "Published", result
    doc = event_loop.run_until_complete(
        db.blog_posts.find_one(
            {"category_key": "recruitment", "scheduled_date": scheduled_date}, {"_id": 0}
        )
    )
    assert doc["publication_status"] == "Published"
    assert doc.get("published_at"), "published_at must be set when publish_now=True"
    assert doc["slug"]
    assert calls["n"] == 1
    assert not calls["alerts"], "no owner alert expected on successful auto-publish"


def test_publish_now_false_creates_pending_review(db, event_loop, monkeypatch):
    alerts = []

    async def fake_claude(category_key, recent_titles, correction="", draft=None):
        return _valid_article("pending")

    async def fake_alert(subject, rows):
        alerts.append(subject)

    monkeypatch.setattr(marketing_service, "claude_blog", fake_claude)
    monkeypatch.setattr(marketing_service, "send_owner_alert", fake_alert)

    scheduled_date = f"{TEST_TAG}-pending"
    result = event_loop.run_until_complete(
        marketing_service.create_scheduled_blog_post(
            db, "reactivation", scheduled_date, publish_now=False
        )
    )
    assert result["status"] == "Pending Review", result
    doc = event_loop.run_until_complete(
        db.blog_posts.find_one(
            {"category_key": "reactivation", "scheduled_date": scheduled_date}, {"_id": 0}
        )
    )
    assert doc["publication_status"] == "Pending Review"
    assert not doc.get("published_at")
    assert any("Draft Ready" in s for s in alerts), alerts


def test_validation_fails_twice_no_publish_and_alerts_owner(db, event_loop, monkeypatch):
    calls = {"n": 0}
    alerts = []

    async def fake_claude(category_key, recent_titles, correction="", draft=None):
        calls["n"] += 1
        return _invalid_article(f"v{calls['n']}")

    async def fake_alert(subject, rows):
        alerts.append((subject, dict(rows)))

    monkeypatch.setattr(marketing_service, "claude_blog", fake_claude)
    monkeypatch.setattr(marketing_service, "send_owner_alert", fake_alert)

    scheduled_date = f"{TEST_TAG}-fail"
    result = event_loop.run_until_complete(
        marketing_service.create_scheduled_blog_post(
            db, "fundraising_activation", scheduled_date, publish_now=True
        )
    )
    assert result["status"] == "Validation Failed", result
    assert calls["n"] == 2, f"expected exactly 2 claude_blog calls (1 correction), got {calls['n']}"
    doc = event_loop.run_until_complete(
        db.blog_posts.find_one(
            {"category_key": "fundraising_activation", "scheduled_date": scheduled_date},
            {"_id": 0},
        )
    )
    assert doc["publication_status"] == "Validation Failed"
    assert not doc.get("published_at")
    assert alerts, "send_owner_alert must be invoked on validation failure"
    assert any("Failed Validation" in subj for subj, _ in alerts)


# ---------- Source-code checks ----------

def test_marketing_loop_uses_publish_now_true():
    src = textwrap.dedent(inspect.getsource(marketing_service.marketing_loop))
    assert "publish_now=True" in src, (
        "marketing_loop scheduled path must call create_scheduled_blog_post(..., publish_now=True)"
    )
    assert "CATEGORIES" in src and "weekday()" in src


def test_manual_generate_default_is_publish_now_false():
    import marketing_routes as mr
    src = inspect.getsource(mr.BlogGenerate)
    assert "publish_now: bool = False" in src, (
        "Manual POST /api/blog/generate must default publish_now=False (Pending Review)"
    )


# ---------- Public gate ----------

def test_public_blog_posts_only_returns_published():
    resp = requests.get(f"{BASE_URL}/api/blog/posts", timeout=15)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    posts = payload.get("posts", [])
    for p in posts:
        assert p.get("published_at"), f"Non-published post leaked to public listing: {p}"
        assert "publication_status" not in p, "publication_status must not leak to public"
