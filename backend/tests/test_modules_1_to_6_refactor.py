"""Regression tests for Modules 1-6 refactor (iteration 13).

Zero AI generation calls are made; zero publish/email endpoints are exercised.
Uses owner admin cookie (OWNER_RECRUITMENT_REVIEW_MODE=true) to hit the workspace
endpoints as user_id 'owner-review-admin'.
"""
import os
import time
import inspect

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PASSWORD = "PC8JX97y7YjPUel9-gM5gAem"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    return s


# ---- unauthenticated regression ----
def test_unauth_workspace_applications_401():
    r = requests.get(f"{BASE_URL}/api/workspace/applications", timeout=15)
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


# ---- Module 3: application/generate endpoint (no AI, no email) ----
def test_generate_standard_application_and_readiness(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/workspace/opportunity/application/generate", timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    data = r.json()
    assert data.get("status") == "generated"
    assert isinstance(data.get("core_questions"), list) and len(data["core_questions"]) > 0
    assert data.get("opportunity", {}).get("application_saved") is True

    # readiness reflects application_saved=True
    r2 = admin_session.get(f"{BASE_URL}/api/workspace/opportunity", timeout=20)
    assert r2.status_code == 200
    body = r2.json()
    assert body.get("readiness", {}).get("application_saved") is True
    assert isinstance(body.get("core_questions"), list) and len(body["core_questions"]) > 0


# ---- Module 4: external applicant now name-only (email/etc. optional) ----
def test_external_applicant_name_only(admin_session):
    files = {"name": (None, "TEST_ExternalCandidate_Modules")}  # only name
    r = admin_session.post(f"{BASE_URL}/api/workspace/applications/external", files=files, timeout=30)
    assert r.status_code == 201, f"{r.status_code} {r.text[:200]}"
    app_id = r.json().get("application_id")
    assert app_id

    # Verify appears in listing with source 'LinkedIn / External'
    listing = admin_session.get(f"{BASE_URL}/api/workspace/applications", timeout=20)
    assert listing.status_code == 200
    apps = listing.json().get("applications", [])
    match = next((a for a in apps if a.get("application_id") == app_id), None)
    assert match is not None, "created external applicant not in list"
    assert match.get("source") == "LinkedIn / External"
    snap = match.get("profile_snapshot", {}) or {}
    assert snap.get("full_name") == "TEST_ExternalCandidate_Modules"

    # Cleanup: set status to allow deletion; use PATCH then DELETE if delete route exists
    # Attempt DELETE endpoint (may not exist) — if unsupported we simply leave the TEST_ record.
    admin_session.delete(f"{BASE_URL}/api/workspace/applications/{app_id}", timeout=15)


def test_external_applicant_missing_name_422(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/workspace/applications/external", files={}, timeout=15)
    assert r.status_code in (422, 400), f"expected 422/400 without name, got {r.status_code}"


# ---- ai_service registry: module reassignments ----
def test_generation_registry_module_assignments():
    import sys
    sys.path.insert(0, "/app/backend")
    from ai_service import GENERATION_TYPES  # type: ignore

    # Module 5 reassignments
    assert GENERATION_TYPES["conditional_offer"]["module"] == 5
    assert GENERATION_TYPES["after_interview_rejection"]["module"] == 5
    for t in ("organization_overview", "board_manual", "board_member_agreement",
              "confidentiality_agreement", "conflict_of_interest_agreement"):
        assert GENERATION_TYPES[t]["module"] == 5
        # org-level (not per-application)
        assert GENERATION_TYPES[t].get("per_application", False) is False, f"{t} should be org-level"

    # Module 6 first board meeting invitation exists
    assert "first_board_meeting_invitation" in GENERATION_TYPES
    assert GENERATION_TYPES["first_board_meeting_invitation"]["module"] == 6
    assert GENERATION_TYPES["first_board_meeting_invitation"].get("per_application", False) is False


# ---- External applicant endpoint signature: name required, email optional ----
def test_external_applicant_signature_name_only_required():
    import sys
    sys.path.insert(0, "/app/backend")
    import workspace_routes  # type: ignore
    src = inspect.getsource(workspace_routes)
    # Signature: name: str = Form(...) required; email default ""
    assert 'name: str = Form(...)' in src
    assert 'email: str = Form("")' in src


# ---- publish endpoint must NOT be called; just verify it exists as POST (do NOT hit it) ----
def test_publish_endpoint_exists_but_not_called():
    # HEAD/OPTIONS to confirm route without triggering broadcast
    r = requests.options(f"{BASE_URL}/api/workspace/opportunity/publish", timeout=10)
    assert r.status_code in (200, 204, 405), f"unexpected {r.status_code}"
