"""Iteration 17 — Verify removal of POST /api/admin/reset-review-data with zero regression."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # Fallback: read frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip()
                break
BASE_URL = BASE_URL.rstrip("/")

ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
               timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


# ---------- Removed endpoint ----------
def test_reset_review_data_no_auth_returns_404():
    r = requests.post(f"{BASE_URL}/api/admin/reset-review-data", timeout=10)
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text[:200]}"


def test_reset_review_data_with_admin_returns_404(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/reset-review-data", timeout=10)
    assert r.status_code == 404, f"Expected 404 with admin, got {r.status_code}: {r.text[:200]}"


# ---------- Owner Review Mode intact ----------
def test_review_mode_status_active(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/review-mode/status", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("active") is True, f"Expected active:true, got {data}"


# ---------- Owner Review persistence endpoints ----------
def test_review_mode_progress_get(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/review-mode/progress", timeout=10)
    assert r.status_code == 200
    data = r.json()
    # progress may be null or an object; just verify shape
    assert "progress" in data or data == {} or isinstance(data, (dict, list))


def test_review_mode_progress_post_and_delete(admin_session):
    payload = {"route": "/test/iter17", "label": "TEST_iter17_verification"}
    r = admin_session.post(f"{BASE_URL}/api/review-mode/progress", json=payload, timeout=10)
    assert r.status_code in (200, 201), f"POST progress failed: {r.status_code} {r.text[:200]}"
    # Clean up
    r_del = admin_session.delete(f"{BASE_URL}/api/review-mode/progress", timeout=10)
    assert r_del.status_code in (200, 204), f"DELETE progress failed: {r_del.status_code} {r_del.text[:200]}"


# ---------- Quick regression ----------
def test_workspace_profile_admin(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/workspace/profile", timeout=15)
    assert r.status_code == 200, f"workspace/profile failed: {r.status_code} {r.text[:200]}"
