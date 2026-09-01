"""Iteration 59 — Verify admin 'Test Complete Board Transformation' preview-access auto-provisioning fix.

Scope (narrow, per product owner): only POST /api/admin/board-fix/preview-access,
GET /api/board-fix-intake/context (session-less member mode), POST /api/members/login,
and GET /api/admin/board-fix/customers. NO intake submit, NO AI, NO emails, NO Stripe.
"""
import os

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"].lower()
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
MODULE_TESTER_EMAIL = "module-tester@example.com"
MODULE_TESTER_PASSWORD = os.environ["MODULE_TESTER_PASSWORD"]

MEMBER_COOKIE = "member_access_token"

state = {}


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


@pytest.fixture(scope="module")
def admin_session():
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login",
                            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=45)
    if response.status_code != 200:
        pytest.fail(f"Admin login failed {response.status_code}: {response.text[:300]}")
    assert "admin_access_token" in response.cookies.get_dict(), \
        f"admin_access_token cookie missing; got {response.cookies.get_dict()}"
    return session


# --- module: board_fix_routes.admin_preview_access ---
class TestPreviewAccess:

    def test_01_preview_access_returns_intake_url_and_member_cookie(self, admin_session):
        response = admin_session.post(f"{BASE_URL}/api/admin/board-fix/preview-access", timeout=60)
        assert response.status_code == 200, f"{response.status_code}: {response.text[:400]}"
        body = response.json()
        assert body["intake_url"] == "/board-fix-intake"
        assert body["member_email"] == ADMIN_EMAIL
        set_cookie = response.headers.get("set-cookie", "")
        assert MEMBER_COOKIE in set_cookie, f"member cookie not set: {set_cookie}"
        lowered = set_cookie.lower()
        assert "httponly" in lowered and "secure" in lowered and "samesite=none" in lowered, set_cookie
        token = admin_session.cookies.get(MEMBER_COOKIE)
        assert token, "member_access_token not stored in session cookie jar"
        state["member_token"] = token

    def test_02_member_record_provisioned_with_entitlements(self, mongo_db):
        member = mongo_db.members.find_one({"email": ADMIN_EMAIL})
        assert member, "db.members record for admin email was not created"
        entitlements = member.get("entitlements", [])
        for ent in ["board_fix_system", "recruitment_self_guided", "reactivation_self_guided",
                    "activation_self_guided", "recruitment_selection_onboarding"]:
            assert ent in entitlements, f"missing entitlement {ent} in {entitlements}"
        assert member.get("internal_admin_entitlement") is True
        assert str(member.get("password_hash", "")).startswith("$2b$"), \
            f"password_hash not bcrypt $2b$: {str(member.get('password_hash'))[:10]}"
        admin_user = mongo_db.users.find_one({"email": ADMIN_EMAIL})
        assert admin_user and member["password_hash"] == admin_user["password_hash"], \
            "member password_hash was not copied from db.users"
        state["member_user_id"] = member["user_id"]

    def test_03_journey_marked_internal_preview(self, mongo_db):
        journey = mongo_db.board_fix_journeys.find_one({"user_id": state["member_user_id"]})
        assert journey, "board_fix_journeys doc missing for preview member"
        assert journey.get("internal_preview") is True
        assert journey.get("email") == ADMIN_EMAIL

    # --- module: member_routes.member_login (shared bcrypt hash / one identity) ---
    def test_04_member_login_with_admin_credentials(self):
        response = requests.post(f"{BASE_URL}/api/members/login",
                                 json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=45)
        assert response.status_code == 200, f"{response.status_code}: {response.text[:400]}"
        data = response.json()
        assert data.get("email", "").lower() == ADMIN_EMAIL or data.get("member", {}).get("email", "").lower() == ADMIN_EMAIL, data
        assert MEMBER_COOKIE in response.headers.get("set-cookie", "")

    # --- module: board_fix_routes.intake_context (session-less member mode) ---
    def test_05_intake_context_sessionless_with_preview_cookie(self):
        response = requests.get(f"{BASE_URL}/api/board-fix-intake/context",
                                cookies={MEMBER_COOKIE: state["member_token"]}, timeout=45)
        assert response.status_code == 200, f"{response.status_code}: {response.text[:400]}"
        body = response.json()
        assert body.get("eligible") is True, body
        assert body.get("submitted") is False, body

    def test_06_preview_access_is_idempotent(self, admin_session, mongo_db):
        before = mongo_db.members.count_documents({"email": ADMIN_EMAIL})
        response = admin_session.post(f"{BASE_URL}/api/admin/board-fix/preview-access", timeout=60)
        assert response.status_code == 200, f"{response.status_code}: {response.text[:400]}"
        assert response.json()["intake_url"] == "/board-fix-intake"
        after = mongo_db.members.count_documents({"email": ADMIN_EMAIL})
        assert after == before == 1, f"duplicate member records: before={before} after={after}"
        member = mongo_db.members.find_one({"email": ADMIN_EMAIL})
        assert member["user_id"] == state["member_user_id"], "member user_id changed on second call"
        assert len(member["entitlements"]) == len(set(member["entitlements"])), \
            f"duplicate entitlements: {member['entitlements']}"

    # --- security gates ---
    def test_07_intake_context_no_auth_no_session_returns_401(self):
        response = requests.get(f"{BASE_URL}/api/board-fix-intake/context", timeout=45)
        assert response.status_code == 401, f"expected 401, got {response.status_code}: {response.text[:300]}"

    def test_08_preview_access_without_admin_auth_returns_401(self):
        response = requests.post(f"{BASE_URL}/api/admin/board-fix/preview-access", timeout=45)
        assert response.status_code == 401, f"expected 401, got {response.status_code}: {response.text[:300]}"

    def test_09_member_without_board_fix_entitlement_gets_403(self):
        login = requests.post(f"{BASE_URL}/api/members/login",
                              json={"email": MODULE_TESTER_EMAIL, "password": MODULE_TESTER_PASSWORD}, timeout=45)
        assert login.status_code == 200, f"module tester login failed {login.status_code}: {login.text[:300]}"
        token = login.cookies.get(MEMBER_COOKIE)
        assert token, "member cookie missing on module tester login"
        response = requests.get(f"{BASE_URL}/api/board-fix-intake/context",
                                cookies={MEMBER_COOKIE: token}, timeout=45)
        assert response.status_code == 403, f"expected 403, got {response.status_code}: {response.text[:300]}"

    # --- regression: existing admin endpoint + preview exclusion ---
    def test_10_admin_customers_still_works_and_excludes_preview_member(self, admin_session):
        response = admin_session.get(f"{BASE_URL}/api/admin/board-fix/customers", timeout=60)
        assert response.status_code == 200, f"{response.status_code}: {response.text[:400]}"
        payload = response.json()
        rows = payload if isinstance(payload, list) else payload.get("customers", [])
        assert isinstance(rows, list)
        preview_rows = [r for r in rows if (r.get("email") or "").lower() == ADMIN_EMAIL and r.get("intake")]
        assert not preview_rows, f"preview member surfaced as customer with intake: {preview_rows}"
