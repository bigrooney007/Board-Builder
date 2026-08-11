"""
Backend regression tests for the Recruitment Funnel upgrade + Owner Review Mode.

Covers:
  - GET /api/review-mode/status  (logged-out=false, admin cookie + env flag => true)
  - GET /api/recruitment-guarantee  (fallback text, no fabricated refund terms)
  - POST /api/terms-agreements  (records for valid lead; 404 for invalid lead)
  - POST /api/funnel-leads/recruitment  (support_preference=guided saves, owner email Sent)
  - GET /api/courses/recruitment/self-guided
      * 401 for public (no cookie)
      * 200 with admin cookie via review_mode_member fallback (6 canonical modules)
      * 200 for member with recruitment_self_guided entitlement
  - POST /api/payments/checkout
      * public => 403 when RECRUITMENT_497_LIVE=false
      * with admin cookie + internal_test=true => returns Stripe checkout_url
      * DOES NOT complete payment
  - /api/funnel-leads reactivation + fundraising_activation still work (regression)

All test data uses TEST_-prefixed names/emails and is cleaned up after run.
"""
import os
import re
import time
import uuid

import pytest
import requests
from pymongo import MongoClient

def _read_frontend_env(key: str) -> str:
    path = "/app/frontend/.env"
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                if line.strip().startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env("REACT_APP_BACKEND_URL")).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not configured"
ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PASSWORD = "PC8JX97y7YjPUel9-gM5gAem"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

CANONICAL_MODULE_TITLES = [
    "Identify the Board Members Your Organization Needs",
    "Build Your Recruitment Strategy",
    "Launch Your Recruitment Campaign",
    "Interview Your Applicants",
    "Complete References and Background Checks",
    "Onboard Your New Board Members",
]

# Track created lead_ids for cleanup
CREATED_LEAD_IDS = []
CREATED_MEMBER_EMAILS = []


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    # Cleanup
    if CREATED_LEAD_IDS:
        client[DB_NAME].funnel_leads.delete_many({"lead_id": {"$in": CREATED_LEAD_IDS}})
        client[DB_NAME].terms_agreements.delete_many({"lead_id": {"$in": CREATED_LEAD_IDS}})
        client[DB_NAME].payment_transactions.delete_many({"lead_id": {"$in": CREATED_LEAD_IDS}})
    if CREATED_MEMBER_EMAILS:
        client[DB_NAME].members.delete_many({"email": {"$in": [e.lower() for e in CREATED_MEMBER_EMAILS]}})
    client.close()


@pytest.fixture(scope="module")
def public_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


# -------------------- Review Mode --------------------

class TestReviewMode:
    def test_status_public_returns_false(self, public_client):
        r = public_client.get(f"{BASE_URL}/api/review-mode/status")
        assert r.status_code == 200
        assert r.json() == {"active": False}

    def test_status_admin_returns_true(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/review-mode/status")
        assert r.status_code == 200
        assert r.json() == {"active": True}


# -------------------- Recruitment Guarantee --------------------

class TestRecruitmentGuarantee:
    def test_returns_fallback_when_env_empty(self, public_client):
        r = public_client.get(f"{BASE_URL}/api/recruitment-guarantee")
        assert r.status_code == 200
        data = r.json()
        assert "terms" in data
        assert "configured" in data
        assert data["configured"] is False  # env is empty per constraints
        terms = data["terms"].lower()
        # Must not contain fabricated refund windows/conditions
        forbidden_patterns = [
            r"\d+\s*(day|week|month)s?\s+(money.?back|refund)",
            r"within\s+\d+\s*(day|week|month)",
            r"\d+%\s+refund",
            r"90-day",
            r"30-day",
        ]
        for pat in forbidden_patterns:
            assert not re.search(pat, terms), f"Fallback text contains fabricated refund window: '{pat}'"


# -------------------- Terms Agreements --------------------

class TestTermsAgreements:
    def test_invalid_lead_returns_404(self, public_client):
        r = public_client.post(
            f"{BASE_URL}/api/terms-agreements",
            json={"lead_id": f"NONEXISTENT_{uuid.uuid4().hex}", "terms_version": "2026-06-recruitment-v1"},
        )
        assert r.status_code == 404


# -------------------- Recruitment Lead Submission --------------------

class TestRecruitmentLeadSubmission:
    def test_submit_recruitment_lead_with_guided(self, public_client, db):
        unique = uuid.uuid4().hex[:8]
        payload = {
            "name": f"TEST_Rooney {unique}",
            "email": f"TEST_recruit_{unique}@example.com",
            "phone": "+1-555-0100",
            "organization": f"TEST_Org {unique}",
            "website": "https://example.com",
            "city": "Middletown",
            "state_region": "DE",
            "country": "United States",
            "answers": {
                "new_members_needed": "3",
                "present_board": "5",
                "active_board": "4",
                "board_type": "governance",
                "accomplish_areas": ["fundraising", "governance"],
                "timeline": "3_months",
                "support_preference": "guided",
            },
        }
        r = public_client.post(f"{BASE_URL}/api/funnel-leads/recruitment", json=payload)
        assert r.status_code == 201, f"Body: {r.text}"
        body = r.json()
        assert body["offer_source"] == "recruitment"
        assert body["owner_email_status"] == "Sent"
        lead_id = body["lead_id"]
        CREATED_LEAD_IDS.append(lead_id)

        # Verify persistence with correct support_preference
        lead = db.funnel_leads.find_one({"lead_id": lead_id}, {"_id": 0})
        assert lead is not None
        assert lead["support_preference"] == "guided"
        assert lead["offer_source"] == "recruitment"
        assert lead["email"] == payload["email"]

    def test_terms_agreement_records_for_valid_lead(self, public_client, db):
        assert CREATED_LEAD_IDS, "prior lead-creation test must run first"
        lead_id = CREATED_LEAD_IDS[0]
        r = public_client.post(
            f"{BASE_URL}/api/terms-agreements",
            json={"lead_id": lead_id, "terms_version": "2026-06-recruitment-v1"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "recorded"
        # verify persistence
        rec = db.terms_agreements.find_one({"lead_id": lead_id}, {"_id": 0})
        assert rec is not None
        assert rec["terms_version"] == "2026-06-recruitment-v1"
        assert rec["email"].startswith("TEST_recruit_")
        assert rec["context"] == "recruitment_checkout"

    def test_submit_missing_support_preference_fails(self, public_client):
        payload = {
            "name": f"TEST_MissingSupport",
            "email": f"TEST_missing_{uuid.uuid4().hex[:8]}@example.com",
            "phone": "+1-555-0101",
            "organization": "TEST_Org",
            "city": "Middletown", "state_region": "DE", "country": "United States",
            "answers": {
                "new_members_needed": "3", "present_board": "5", "active_board": "4",
                "board_type": "governance", "accomplish_areas": ["fundraising"],
                "timeline": "3_months",
            },
        }
        r = public_client.post(f"{BASE_URL}/api/funnel-leads/recruitment", json=payload)
        assert r.status_code == 422


# -------------------- Self-Guided Course Access --------------------

class TestSelfGuidedCourse:
    def test_public_returns_401(self, public_client):
        r = public_client.get(f"{BASE_URL}/api/courses/recruitment/self-guided")
        assert r.status_code == 401

    def test_admin_cookie_returns_course_with_6_canonical_modules(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/courses/recruitment/self-guided")
        assert r.status_code == 200, f"Body: {r.text}"
        data = r.json()
        # Extract modules regardless of exact key
        modules = data.get("modules") or data.get("stages") or []
        assert len(modules) == 6, f"Expected 6 modules, got {len(modules)}: {modules}"
        titles = [m.get("title") or m.get("name") for m in modules]
        assert titles == CANONICAL_MODULE_TITLES, (
            f"Module titles deviate.\nExpected: {CANONICAL_MODULE_TITLES}\nActual:   {titles}"
        )


# -------------------- Payments Checkout --------------------

class TestPaymentsCheckout:
    def test_public_checkout_blocked_when_flag_false(self, public_client):
        assert CREATED_LEAD_IDS, "prior lead-creation test must run first"
        lead_id = CREATED_LEAD_IDS[0]
        r = public_client.post(
            f"{BASE_URL}/api/payments/checkout",
            json={"lead_id": lead_id, "tier": "497", "origin_url": BASE_URL, "internal_test": False},
        )
        assert r.status_code == 403

    def test_admin_internal_test_returns_stripe_url(self, admin_client):
        assert CREATED_LEAD_IDS, "prior lead-creation test must run first"
        lead_id = CREATED_LEAD_IDS[0]
        r = admin_client.post(
            f"{BASE_URL}/api/payments/checkout",
            json={"lead_id": lead_id, "tier": "497", "origin_url": BASE_URL, "internal_test": True},
        )
        assert r.status_code == 200, f"Body: {r.text}"
        body = r.json()
        assert "checkout_url" in body
        assert body["checkout_url"].startswith("https://")
        assert "stripe.com" in body["checkout_url"] or "checkout.stripe" in body["checkout_url"]
        # Ensure it's Stripe TEST mode session -- session_id starts with cs_test_
        assert body.get("session_id", "").startswith("cs_test_"), f"Expected TEST mode session, got: {body.get('session_id')}"


# -------------------- Regression: Reactivation + Activation Funnels --------------------

class TestReactivationRegression:
    def test_submit_reactivation_lead(self, public_client, db):
        unique = uuid.uuid4().hex[:8]
        payload = {
            "name": f"TEST_React {unique}",
            "email": f"TEST_react_{unique}@example.com",
            "phone": "+1-555-0200",
            "organization": f"TEST_Org {unique}",
            "city": "Middletown", "state_region": "DE", "country": "United States",
            "answers": {
                "present_board": "7", "active_board": "3",
                "inactive_situations": ["not_attending"],
                "recommitment_conversations": "no",
                "strategic_planning": "no",
                "priorities": ["governance"],
                "desired_changes": "More engagement",
            },
        }
        r = public_client.post(f"{BASE_URL}/api/funnel-leads/reactivation", json=payload)
        assert r.status_code == 201, f"Body: {r.text}"
        body = r.json()
        assert body["offer_source"] == "reactivation"
        CREATED_LEAD_IDS.append(body["lead_id"])


class TestFundraisingActivationRegression:
    def test_submit_activation_lead(self, public_client, db):
        unique = uuid.uuid4().hex[:8]
        payload = {
            "name": f"TEST_Fund {unique}",
            "email": f"TEST_fund_{unique}@example.com",
            "phone": "+1-555-0300",
            "organization": f"TEST_Org {unique}",
            "city": "Middletown", "state_region": "DE", "country": "United States",
            "answers": {
                "present_board": "6", "active_board": "5",
                "fundraising_involvement": "some",
                "strategic_planning": "yes",
                "fundraising_strategy": "no",
                "individual_responsibilities": "no",
                "fundraising_need": "grow",
                "fundraising_areas": ["individual_giving"],
            },
        }
        r = public_client.post(f"{BASE_URL}/api/funnel-leads/fundraising_activation", json=payload)
        assert r.status_code == 201, f"Body: {r.text}"
        body = r.json()
        assert body["offer_source"] == "fundraising_activation"
        CREATED_LEAD_IDS.append(body["lead_id"])


# -------------------- Regression: Paid Member Access --------------------

class TestPaidMemberAccess:
    """Seed a member with recruitment_self_guided entitlement directly in Mongo; verify member auth still loads the course."""

    def test_member_with_entitlement_can_load_course(self, db):
        # Try to register a member via API
        unique = uuid.uuid4().hex[:8]
        email = f"TEST_member_{unique}@example.com"
        password = "TestPass!2026"
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        r = s.post(
            f"{BASE_URL}/api/members/register",
            json={
                "email": email, "password": password, "confirm_password": password,
                "first_name": "TEST", "last_name": f"Member{unique}",
            },
        )
        if r.status_code not in (200, 201):
            pytest.skip(f"Member register endpoint not available or failed: {r.status_code} {r.text[:200]}")
        CREATED_MEMBER_EMAILS.append(email)

        # Grant entitlement directly (email stored lowercase)
        result = db.members.update_one({"email": email.lower()}, {"$set": {"entitlements": ["recruitment_self_guided"]}})
        assert result.matched_count == 1, f"Failed to find member with email {email.lower()}"

        # If register did NOT set cookie, login
        r2 = s.get(f"{BASE_URL}/api/courses/recruitment/self-guided")
        if r2.status_code == 401:
            # Try login
            lg = s.post(f"{BASE_URL}/api/members/login", json={"email": email, "password": password})
            if lg.status_code != 200:
                pytest.skip(f"Member login not available: {lg.status_code}")
            r2 = s.get(f"{BASE_URL}/api/courses/recruitment/self-guided")

        assert r2.status_code == 200, f"Member with entitlement was blocked: {r2.status_code} {r2.text[:200]}"
        data = r2.json()
        modules = data.get("modules") or data.get("stages") or []
        assert len(modules) == 6
