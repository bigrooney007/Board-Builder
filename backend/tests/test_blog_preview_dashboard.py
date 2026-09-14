"""Backend tests for the Blog Preview Dashboard (admin blog moderation).

Focus: reject-pending, regenerate (Claude, slow), duplicate-title 409,
public-visibility gate for Pending/Rejected, approve->public, edit+slug update.
Uses live public preview URL and admin cookie login.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://fundraising-game.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


@pytest.fixture(scope="module")
def admin_client():
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login",
                        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert resp.status_code == 200, f"admin login failed: {resp.status_code} {resp.text}"
    return session


@pytest.fixture(scope="module")
def anon_client():
    return requests.Session()


# ---------- helpers ----------

def _list_admin_posts(client):
    r = client.get(f"{BASE_URL}/api/admin/blog/posts", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _first(posts, **filters):
    for post in posts:
        if all(post.get(k) == v for k, v in filters.items()):
            return post
    return None


# ---------- tests ----------

def test_admin_list_returns_categories_and_posts(admin_client):
    data = _list_admin_posts(admin_client)
    assert "posts" in data and "categories" in data
    keys = {c["key"] for c in data["categories"]}
    # sanity: known categories exist
    assert "reactivation" in keys or "fundraising_activation" in keys


def test_public_list_excludes_pending_and_rejected(admin_client, anon_client):
    admin_posts = _list_admin_posts(admin_client)["posts"]
    r = anon_client.get(f"{BASE_URL}/api/blog/posts", timeout=30)
    assert r.status_code == 200
    public_ids = {p["blog_post_id"] for p in r.json()["posts"]}
    for post in admin_posts:
        if post["publication_status"] in ("Pending Review", "Rejected", "Generating", "Failed", "Validation Failed"):
            assert post["blog_post_id"] not in public_ids, f"non-published post leaked publicly: {post['blog_post_id']}"


def test_generate_duplicate_category_same_day_returns_409(admin_client):
    # recruitment already has today post per instructions
    r = admin_client.post(f"{BASE_URL}/api/blog/generate",
                          json={"category": "recruitment", "publish_now": False},
                          timeout=120)
    assert r.status_code == 409, f"expected 409 duplicate guard, got {r.status_code} {r.text}"


def _find_or_create_pending_draft(admin_client, category="reactivation"):
    """Ensure we have a Pending Review draft to act on. Prefer existing to save Claude budget."""
    posts = _list_admin_posts(admin_client)["posts"]
    pending = _first(posts, publication_status="Pending Review", category_key=category)
    if pending:
        return pending, False
    # Generate new (slow: up to 90s)
    r = admin_client.post(f"{BASE_URL}/api/blog/generate",
                          json={"category": category, "publish_now": False},
                          timeout=180)
    if r.status_code == 409:
        # try fundraising_activation
        r = admin_client.post(f"{BASE_URL}/api/blog/generate",
                              json={"category": "fundraising_activation", "publish_now": False},
                              timeout=180)
    assert r.status_code in (200, 201), f"generate failed: {r.status_code} {r.text}"
    body = r.json()
    assert body.get("status") == "Pending Review", body
    time.sleep(1)
    posts = _list_admin_posts(admin_client)["posts"]
    pending = _first(posts, publication_status="Pending Review", slug=body.get("slug"))
    assert pending is not None
    return pending, True


def test_patch_edit_updates_slug_for_pending(admin_client):
    pending, _ = _find_or_create_pending_draft(admin_client)
    original_slug = pending["slug"]
    new_title = f"QA Edited Draft {uuid.uuid4().hex[:8]}"
    r = admin_client.patch(
        f"{BASE_URL}/api/admin/blog/posts/{pending['blog_post_id']}",
        json={"title": new_title, "excerpt": pending.get("excerpt", "QA excerpt"),
              "body": pending.get("body") or ("QA body content " * 20)},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    post = r.json()["post"]
    assert post["title"] == new_title
    assert post["slug"] != original_slug
    assert post["slug"].startswith("qa-edited-draft-")


def test_patch_duplicate_title_returns_409(admin_client):
    # get any published post title
    admin_posts = _list_admin_posts(admin_client)["posts"]
    published = _first(admin_posts, publication_status="Published")
    pending = _first(admin_posts, publication_status="Pending Review")
    if not (published and pending):
        pytest.skip("Need both a published post and a pending draft for duplicate-title test")
    r = admin_client.patch(
        f"{BASE_URL}/api/admin/blog/posts/{pending['blog_post_id']}",
        json={"title": published["title"], "excerpt": "dupe",
              "body": pending.get("body") or ("dupe body " * 20)},
        timeout=30,
    )
    assert r.status_code == 409, f"expected 409 duplicate title, got {r.status_code} {r.text}"


def test_reject_pending_and_public_invisible(admin_client, anon_client):
    pending, _ = _find_or_create_pending_draft(admin_client)
    pid = pending["blog_post_id"]
    slug = pending["slug"]
    r = admin_client.post(f"{BASE_URL}/api/admin/blog/posts/{pid}/reject", timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["post"]["publication_status"] == "Rejected"

    # public list must not include it
    pub = anon_client.get(f"{BASE_URL}/api/blog/posts", timeout=30).json()["posts"]
    assert pid not in {p["blog_post_id"] for p in pub}
    # slug detail 404
    detail = anon_client.get(f"{BASE_URL}/api/blog/posts/{slug}", timeout=30)
    assert detail.status_code == 404


def test_approve_already_published_returns_409(admin_client):
    admin_posts = _list_admin_posts(admin_client)["posts"]
    published = _first(admin_posts, publication_status="Published")
    assert published is not None, "expected at least one Published post"
    r = admin_client.post(
        f"{BASE_URL}/api/admin/blog/posts/{published['blog_post_id']}/approve",
        timeout=30,
    )
    assert r.status_code == 409, r.text


def test_regenerate_published_returns_409(admin_client):
    admin_posts = _list_admin_posts(admin_client)["posts"]
    published = _first(admin_posts, publication_status="Published")
    assert published is not None
    r = admin_client.post(
        f"{BASE_URL}/api/admin/blog/posts/{published['blog_post_id']}/regenerate",
        timeout=30,
    )
    assert r.status_code == 409, r.text


def test_reject_published_returns_409(admin_client):
    admin_posts = _list_admin_posts(admin_client)["posts"]
    published = _first(admin_posts, publication_status="Published")
    assert published is not None
    r = admin_client.post(
        f"{BASE_URL}/api/admin/blog/posts/{published['blog_post_id']}/reject",
        timeout=30,
    )
    assert r.status_code == 409, r.text


def test_regenerate_rejected_produces_new_pending(admin_client):
    """Regenerate on a Rejected draft returns to Pending Review with new content (slow: up to 90s)."""
    admin_posts = _list_admin_posts(admin_client)["posts"]
    rejected = _first(admin_posts, publication_status="Rejected")
    if not rejected:
        pytest.skip("No rejected draft available to regenerate; skipping to conserve Claude budget")
    pid = rejected["blog_post_id"]
    old_body = rejected.get("body", "")
    r = admin_client.post(f"{BASE_URL}/api/admin/blog/posts/{pid}/regenerate", timeout=180)
    assert r.status_code == 200, r.text
    post = r.json().get("post", {})
    assert post.get("publication_status") == "Pending Review", post
    assert post.get("body") and post["body"] != old_body


def test_public_article_detail_regression(anon_client):
    r = anon_client.get(f"{BASE_URL}/api/blog/posts", timeout=30)
    assert r.status_code == 200
    posts = r.json()["posts"]
    assert len(posts) >= 1
    slug = posts[0]["slug"]
    detail = anon_client.get(f"{BASE_URL}/api/blog/posts/{slug}", timeout=30)
    assert detail.status_code == 200
    assert detail.json().get("slug") == slug
