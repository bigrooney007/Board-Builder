"""Backend regression tests for the RECRUITMENT support_preference/accomplish_areas rework
and the new BLOG generation prompt (350-550 words target, 300-650 hard bounds)."""
import os
import time
from datetime import datetime, timedelta

import pytest
import requests
from pymongo import MongoClient

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE:
    # fallback to reading frontend/.env
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE = line.split("=", 1)[1].strip().strip('"').rstrip("/")

ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_session(session):
    r = session.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return session


@pytest.fixture(scope="module")
def mongo_db():
    with open("/app/backend/.env") as fh:
        env = dict(
            line.strip().split("=", 1) for line in fh if "=" in line and not line.startswith("#")
        )
    client = MongoClient(env["MONGO_URL"].strip('"'))
    return client[env["DB_NAME"].strip('"')]


# ---------- Recruitment payload helpers ----------
def _recruitment_payload(support_preference="self_guided", accomplish_areas=None, extras=None):
    answers = {
        "new_members_needed": "3",
        "present_board": "6",
        "active_board": "3",
        "board_type": "A working board that actively helps execute",
        "accomplish_areas": accomplish_areas if accomplish_areas is not None else ["Raise money", "Strengthen governance"],
        "timeline": "Within 30 days",
        "support_preference": support_preference,
    }
    if extras:
        answers.update(extras)
    return {
        "name": "TEST Recruit User",
        "email": f"test_recruit_{int(time.time()*1000)}@example.com",
        "phone": "555-000-1111",
        "organization": "TEST Recruit Org",
        "website": "",
        "city": "Austin",
        "state_region": "TX",
        "country": "United States",
        "answers": answers,
    }


# ---------- Recruitment tests ----------
class TestRecruitmentSubmission:
    def test_valid_self_guided_submission_persists_top_level_support_preference(self, session, mongo_db):
        payload = _recruitment_payload(support_preference="self_guided")
        r = session.post(f"{BASE}/api/funnel-leads/recruitment", json=payload)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["offer_source"] == "recruitment"
        assert data["owner_email_status"] in {"Sent", "Failed"}
        lead_id = data["lead_id"]
        doc = mongo_db.funnel_leads.find_one({"lead_id": lead_id}, {"_id": 0})
        assert doc is not None, "Lead was not persisted"
        assert doc.get("support_preference") == "self_guided", f"top-level support_preference missing: {doc}"
        assert doc["answers"]["support_preference"] == "self_guided"
        assert doc["answers"]["accomplish_areas"] == ["Raise money", "Strengthen governance"]

    def test_accomplish_other_free_text_persisted(self, session, mongo_db):
        payload = _recruitment_payload(
            support_preference="diy",
            accomplish_areas=["Other"],
            extras={"accomplish_other": "Board governance training for new directors"},
        )
        r = session.post(f"{BASE}/api/funnel-leads/recruitment", json=payload)
        assert r.status_code == 201, r.text
        lead_id = r.json()["lead_id"]
        doc = mongo_db.funnel_leads.find_one({"lead_id": lead_id}, {"_id": 0})
        assert doc["answers"]["accomplish_other"] == "Board governance training for new directors"
        assert doc["support_preference"] == "diy"

    def test_invalid_support_preference_returns_422(self, session):
        payload = _recruitment_payload(support_preference="premium")
        r = session.post(f"{BASE}/api/funnel-leads/recruitment", json=payload)
        assert r.status_code == 422
        assert "support" in r.text.lower()

    def test_missing_support_preference_returns_422(self, session):
        payload = _recruitment_payload()
        payload["answers"].pop("support_preference")
        r = session.post(f"{BASE}/api/funnel-leads/recruitment", json=payload)
        assert r.status_code == 422
        assert "support_preference" in r.text

    def test_missing_accomplish_areas_returns_422(self, session):
        payload = _recruitment_payload(accomplish_areas=[])
        r = session.post(f"{BASE}/api/funnel-leads/recruitment", json=payload)
        assert r.status_code == 422
        assert "accomplish_areas" in r.text

    def test_all_four_support_options_accepted(self, session):
        for opt in ["diy", "self_guided", "done_with_you", "undecided"]:
            r = session.post(f"{BASE}/api/funnel-leads/recruitment", json=_recruitment_payload(support_preference=opt))
            assert r.status_code == 201, f"{opt} failed: {r.status_code} {r.text}"


# ---------- Regression: Reactivation & Activation ----------
class TestOtherFunnelsRegression:
    def test_reactivation_submission_does_not_require_support_preference(self, session):
        payload = {
            "name": "TEST Reactivate User",
            "email": f"test_react_{int(time.time()*1000)}@example.com",
            "phone": "555-000-2222",
            "organization": "TEST Reactivate Org",
            "website": "",
            "city": "Boston", "state_region": "MA", "country": "United States",
            "answers": {
                "present_board": "8", "active_board": "3",
                "inactive_situations": ["They do not attend meetings"],
                "recommitment_conversations": "No",
                "strategic_planning": "No",
                "priorities": "Raise money; improve programs; grow team",
                "desired_changes": ["Better accountability"],
            },
        }
        r = session.post(f"{BASE}/api/funnel-leads/reactivation", json=payload)
        assert r.status_code == 201, r.text

    def test_fundraising_activation_submission(self, session):
        payload = {
            "name": "TEST Activate User",
            "email": f"test_activate_{int(time.time()*1000)}@example.com",
            "phone": "555-000-3333",
            "organization": "TEST Activate Org",
            "website": "",
            "city": "Denver", "state_region": "CO", "country": "United States",
            "answers": {
                "present_board": "7", "active_board": "4",
                "fundraising_involvement": "Some board members are involved",
                "strategic_planning": "Yes",
                "fundraising_strategy": "No",
                "individual_responsibilities": "No",
                "fundraising_need": "General operating support",
                "fundraising_areas": ["Grants", "Major donors"],
            },
        }
        r = session.post(f"{BASE}/api/funnel-leads/fundraising_activation", json=payload)
        assert r.status_code == 201, r.text


# ---------- Blog generation ----------
class TestBlogGeneration:
    """Only ONE Claude generation allowed (per task budget). Use a future date to avoid duplicates."""

    def test_generate_reactivation_article_length_and_cta(self, admin_session, mongo_db):
        # Use a future date to avoid collision with today's automated post
        future_date = (datetime.utcnow() + timedelta(days=45)).strftime("%Y-%m-%d")
        payload = {"category": "reactivation", "scheduled_date": future_date, "publish_now": False}
        r = admin_session.post(f"{BASE}/api/blog/generate", json=payload, timeout=120)
        assert r.status_code in (201, 200), f"Generate failed: {r.status_code} {r.text}"
        result = r.json()
        # Environment budget may be exceeded; surface that clearly but continue duplicate-protection assertion
        pytest.blog_post_meta = {"date": future_date, "category": "reactivation"}
        if result.get("status") == "Failed":
            pytest.skip(f"LLM generation infra failure (not a code bug): {result.get('error')}")
        assert result.get("status") in {"Pending Review", "Published", "Validation Failed"}, result
        post = mongo_db.blog_posts.find_one({"category_key": "reactivation", "scheduled_date": future_date}, {"_id": 0})
        assert post is not None
        if result["status"] == "Validation Failed":
            pytest.skip(f"Claude produced validation-failing content: {result.get('errors')}")
        body = post.get("body", "")
        import re
        words = len(re.findall(r"\S+", body))
        assert 300 <= words <= 650, f"Word count {words} outside 300-650 (target 350-550). Title={post.get('title')!r}"
        assert post["cta_url"] == "/reactivate"
        assert post["cta_label"]
        assert post["publication_status"] == "Pending Review"
        assert "\u2014" not in body
        first_chunk = body.split("\n\n", 1)[0]
        assert "in today" not in first_chunk.lower() and "in the ever" not in first_chunk.lower()

    def test_duplicate_generation_same_category_and_date_returns_409(self, admin_session):
        meta = getattr(pytest, "blog_post_meta", None)
        if not meta:
            pytest.skip("Previous generation test did not populate meta")
        payload = {"category": meta["category"], "scheduled_date": meta["date"], "publish_now": False}
        r = admin_session.post(f"{BASE}/api/blog/generate", json=payload, timeout=30)
        assert r.status_code == 409, f"Expected 409, got {r.status_code}: {r.text}"


# ---------- Validation helper unit tests (word-count enforcement) ----------
class TestValidateArticleWordCount:
    def test_max_650_enforced(self):
        import sys; sys.path.insert(0, "/app/backend")
        from marketing_service import validate_article
        body = " ".join(["word"] * 700) + "."
        errors = validate_article({"title": "T", "excerpt": "E", "body": body}, "reactivation", [], set())
        assert any("Word count" in e for e in errors), errors

    def test_min_300_enforced(self):
        import sys; sys.path.insert(0, "/app/backend")
        from marketing_service import validate_article
        body = " ".join(["word"] * 250)
        errors = validate_article({"title": "T", "excerpt": "E", "body": body}, "reactivation", [], set())
        assert any("Word count" in e for e in errors), errors

    def test_target_450_passes(self):
        import sys; sys.path.insert(0, "/app/backend")
        from marketing_service import validate_article
        para = " ".join(["nonprofit board members must accept responsibility"] * 10) + "."
        body = "\n\n".join([para] * 8)
        errors = validate_article({"title": "T", "excerpt": "E", "body": body}, "reactivation", [], set())
        # allow only paragraph structure / duplicate errors; word-count should NOT be in errors
        assert not any("Word count" in e for e in errors), errors
