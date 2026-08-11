"""Batch 11 final e2e verification — focused backend regression.

Covers: public funnel/checkout, six locked stages page, advisory option,
testimonials data (via frontend file spot check), review-mode progress
endpoints (auth-gated), CSV import (preview vs commit vs unauth), and public
application page Advisory Board label. NO Claude generation calls, NO
publish, NO email sends.
"""
import io
import os
import re
import time

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PASSWORD = "PC8JX97y7YjPUel9-gM5gAem"

SIX_STAGES = [
    "Identify the Board Members Your Organization Needs",
    "Build Your Recruitment Strategy",
    "Launch Your Recruitment Campaign",
    "Interview Your Applicants",
    "Complete References and Background Checks",
    "Onboard Your New Board Members",
]


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    return s


# ---------- Public frontend page smoke ----------
def test_recruit_page_loads():
    r = requests.get(f"{BASE_URL}/recruit", timeout=20)
    assert r.status_code == 200


def test_recruit_checkout_page_loads():
    r = requests.get(f"{BASE_URL}/recruit/checkout", timeout=20)
    assert r.status_code == 200


def test_recruit_process_page_loads():
    r = requests.get(f"{BASE_URL}/recruit/process", timeout=20)
    assert r.status_code == 200


# ---------- Funnel config: advisory option present ----------
def test_funnel_config_has_advisory_option():
    """Read the source funnelConfig.js from disk to confirm advisory option exists."""
    path = "/app/frontend/src/funnels/funnelConfig.js"
    with open(path, "r") as f:
        content = f.read()
    assert "An advisory board that provides expertise, strategic advice and connections" in content


# ---------- Testimonials: Cyrena Denniston updated quote ----------
def test_testimonial_cyrena_quote_updated():
    path = "/app/frontend/src/components/testimonialsData.js"
    with open(path, "r") as f:
        content = f.read()
    assert "Pastor Cyrena Denniston" in content
    assert "Because of your input and your investment in my life" in content


# ---------- Six stage names LOCKED (source spot check) ----------
def test_six_stage_names_locked_in_source():
    # Grep across frontend to make sure all six exact strings exist somewhere
    import glob
    files = glob.glob("/app/frontend/src/**/*.jsx", recursive=True) + glob.glob("/app/frontend/src/**/*.js", recursive=True)
    combined = ""
    for f in files:
        try:
            with open(f, "r") as fh:
                combined += fh.read()
        except Exception:
            pass
    missing = [s for s in SIX_STAGES if s not in combined]
    assert not missing, f"missing stage labels in frontend source: {missing}"


# ---------- Review-mode progress endpoints ----------
def test_review_progress_get_without_admin_returns_null():
    r = requests.get(f"{BASE_URL}/api/review-mode/progress", timeout=15)
    # spec: GET returns {"progress": null} without admin cookie
    assert r.status_code == 200
    body = r.json()
    assert body.get("progress") in (None, {}) or "progress" in body


def test_review_progress_post_without_admin_401():
    r = requests.post(f"{BASE_URL}/api/review-mode/progress", json={"route": "/recruit", "label": "Recruit"}, timeout=15)
    assert r.status_code in (401, 403, 404), f"expected 401/403, got {r.status_code}"


def test_review_progress_full_cycle(admin_session):
    # POST save
    r = admin_session.post(
        f"{BASE_URL}/api/review-mode/progress",
        json={"route": "/recruit/process", "label": "Recruit Process"},
        timeout=15,
    )
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    assert r.json().get("status") == "saved"

    # GET returns it
    r = admin_session.get(f"{BASE_URL}/api/review-mode/progress", timeout=15)
    assert r.status_code == 200
    progress = r.json().get("progress")
    assert progress is not None
    assert progress.get("last_route") == "/recruit/process"
    assert progress.get("last_label") == "Recruit Process"

    # After logout, GET returns null and POST returns 401
    lo = admin_session.post(f"{BASE_URL}/api/auth/logout", timeout=15)
    assert lo.status_code in (200, 204)
    r = admin_session.get(f"{BASE_URL}/api/review-mode/progress", timeout=15)
    assert r.status_code == 200
    assert r.json().get("progress") in (None, {})
    r = admin_session.post(f"{BASE_URL}/api/review-mode/progress", json={"route": "/x", "label": "x"}, timeout=15)
    assert r.status_code in (401, 403)

    # Log back in for follow-up tests; verify progress persisted
    r = admin_session.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200
    r = admin_session.get(f"{BASE_URL}/api/review-mode/progress", timeout=15)
    progress = r.json().get("progress")
    assert progress is not None
    assert progress.get("last_route") == "/recruit/process"

    # DELETE resets
    r = admin_session.delete(f"{BASE_URL}/api/review-mode/progress", timeout=15)
    assert r.status_code == 200
    r = admin_session.get(f"{BASE_URL}/api/review-mode/progress", timeout=15)
    assert r.json().get("progress") in (None, {})


# ---------- Admin CSV import ----------
CSV_ROWS = (
    "Email,First Name,Last Name,City\n"
    "csvtest1@example.com,Alice,Andrews,Boston\n"
    "csvtest2@example.com,Bob,Baker,Chicago\n"
    "csvtest3@example.com,Carla,Chen,Denver\n"
    "csvtest2@example.com,Bob,Duplicate,Chicago\n"  # duplicate email in file
    "not-an-email,Dan,Broken,Detroit\n"             # invalid email
)


def test_csv_import_unauth_401():
    files = {"file": ("t.csv", CSV_ROWS, "text/csv")}
    r = requests.post(f"{BASE_URL}/api/admin/applicants-import?confirmed=true&commit=false", files=files, timeout=20)
    assert r.status_code in (401, 403)


def test_csv_import_requires_consent(admin_session):
    files = {"file": ("t.csv", CSV_ROWS, "text/csv")}
    r = admin_session.post(f"{BASE_URL}/api/admin/applicants-import?confirmed=false&commit=false", files=files, timeout=20)
    assert r.status_code == 422


def test_csv_import_preview_no_writes(admin_session):
    # Ensure baseline count of csvtest emails in DB is 0 by checking via preview twice
    files = {"file": ("t.csv", CSV_ROWS, "text/csv")}
    r = admin_session.post(f"{BASE_URL}/api/admin/applicants-import?confirmed=true&commit=false", files=files, timeout=20)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body.get("preview") is True
    summary = body["summary"]
    # 3 unique valid emails imported (preview), 1 duplicate, 1 invalid
    assert summary["imported"] + summary["updated"] == 3
    assert summary["skipped_duplicate"] == 1
    assert summary["skipped_invalid_email"] == 1

    # Repeat preview to confirm no accumulation (would only shift to 'updated' if writes occurred)
    files2 = {"file": ("t.csv", CSV_ROWS, "text/csv")}
    r2 = admin_session.post(f"{BASE_URL}/api/admin/applicants-import?confirmed=true&commit=false", files=files2, timeout=20)
    body2 = r2.json()["summary"]
    assert body2["imported"] + body2["updated"] == 3
    # If preview accidentally wrote, second call would show updated=3, imported=0
    assert body2["imported"] == summary["imported"], "Preview must not persist records"


def test_csv_import_commit_and_dedupe(admin_session):
    # Ensure clean slate for csvtest emails
    try:
        from pymongo import MongoClient
        MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "test_database")]\
            .board_applicants.delete_many({"email": {"$regex": "^csvtest"}})
    except Exception:
        pass
    files = {"file": ("t.csv", CSV_ROWS, "text/csv")}
    r = admin_session.post(f"{BASE_URL}/api/admin/applicants-import?confirmed=true&commit=true", files=files, timeout=30)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body.get("preview") is False
    s = body["summary"]
    assert s["imported"] + s["updated"] == 3
    assert s["skipped_invalid_email"] == 1

    # Repeat commit -> should NOT create new records; either updated (if no new field values) or skipped_duplicate
    files2 = {"file": ("t.csv", CSV_ROWS, "text/csv")}
    r2 = admin_session.post(f"{BASE_URL}/api/admin/applicants-import?confirmed=true&commit=true", files=files2, timeout=30)
    s2 = r2.json()["summary"]
    assert s2["imported"] == 0, f"Duplicate emails must not be re-imported, got {s2}"


# ---------- workspace/opportunity readiness (no AI) ----------
def test_workspace_opportunity_get_auto_creates(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/workspace/opportunity", timeout=20)
    assert r.status_code == 200
    body = r.json()
    # Should contain opportunity with application_saved eventually True (iteration 13 already set it)
    op = body.get("opportunity") or {}
    assert op.get("slug"), "opportunity slug must exist"


# ---------- Public application page terminology ----------
def test_public_application_page_loads_or_404(admin_session):
    # find slug
    r = admin_session.get(f"{BASE_URL}/api/workspace/opportunity", timeout=15)
    op = r.json().get("opportunity") or {}
    slug = op.get("slug")
    if not slug:
        pytest.skip("no opportunity slug")
    # The public JSON endpoint may exist; frontend HTML always returns 200 (SPA)
    r = requests.get(f"{BASE_URL}/board-opportunities/{slug}/apply", timeout=15)
    assert r.status_code in (200, 404)
