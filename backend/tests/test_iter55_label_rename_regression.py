"""Iteration 55 — regression after the package label rename to
'Selection, Interview, Reference Check & Onboarding' (ids/lookup keys unchanged).

Read-only except one throwaway stage-1-only member used to trigger the 403 message.
"""
import os
import uuid

import pytest
import requests
import stripe
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or backend_env["STRIPE_SECRET_KEY"]
MONGO_URL = os.environ.get("MONGO_URL") or backend_env["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME") or backend_env["DB_NAME"]

NEW_NAME = "Selection, Interview, Reference Check & Onboarding"
OLD_NAME = "Selection, Interview & Onboarding Package"


@pytest.fixture(scope="session")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def throwaway(api, db):
    """Stage-1-only throwaway member (recruitment_self_guided only)."""
    email = f"TEST_iter55_{uuid.uuid4().hex[:8]}@example.com"
    r = api.post(f"{BASE_URL}/api/members/register", json={
        "first_name": "Iter55", "last_name": "Tester", "email": email,
        "password": "TestPass123!", "confirm_password": "TestPass123!"})
    assert r.status_code == 201, r.text
    data = r.json()
    uid = data["member"]["user_id"]
    db.members.update_one({"user_id": uid}, {"$set": {"entitlements": ["recruitment_self_guided"]}})
    yield {"user_id": uid, "token": data["token"], "email": email}
    db.members.delete_many({"user_id": uid})
    db.course_progress.delete_many({"user_id": uid})


def auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# --- Rename verification: backend strings -------------------------------------
class TestRenameStrings:
    def test_stage2_progress_403_uses_new_package_name(self, api, throwaway):
        r = api.post(f"{BASE_URL}/api/courses/progress", headers=auth(throwaway["token"]),
                     json={"product": "recruitment_self_guided", "module_number": 4, "action": "viewed"})
        assert r.status_code == 403, r.text
        detail = r.json()["detail"]
        assert NEW_NAME in detail, detail
        assert OLD_NAME not in detail

    def test_selection_checkout_metadata_and_stripe_product_name(self, api, db):
        r = api.post(f"{BASE_URL}/api/payments/selection-onboarding-checkout",
                     json={"origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        session = stripe.checkout.Session.retrieve(sid, expand=["line_items.data.price.product"])
        assert session.amount_total == 29700
        assert session.metadata["purchase_source"] == "recruitment_selection_onboarding_297"
        assert session.metadata["offer"] == NEW_NAME
        product = session.line_items.data[0].price.product
        assert product.name == NEW_NAME, product.name
        assert product.metadata.get("emergent_product_id") == "recruitment_selection_onboarding_297"
        db.payment_transactions.delete_many({"session_id": sid})

    def test_stage1_only_member_still_locked_out_of_stage2(self, api, throwaway):
        course = api.get(f"{BASE_URL}/api/courses/recruitment/self-guided", headers=auth(throwaway["token"]))
        assert course.status_code == 200, course.text
        modules = course.json()["modules"]
        locked = {m["number"]: m.get("locked") for m in modules}
        # iter56: module 1 restored -> 6 modules
        assert [m["number"] for m in modules] == [1, 2, 3, 4, 5, 6]
        assert locked == {1: False, 2: False, 3: False, 4: True, 5: True, 6: True}
        assert api.get(f"{BASE_URL}/api/workspace/applications", headers=auth(throwaway["token"])).status_code == 403


# --- Journey spot-checks -------------------------------------------------------
class TestJourneySpotChecks:
    def test_diy_297_checkout(self, api, db):
        r = api.post(f"{BASE_URL}/api/payments/diy-checkout", json={"origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        session = stripe.checkout.Session.retrieve(sid)
        assert session.amount_total == 29700
        assert session.metadata["purchase_source"] == "recruitment_campaign_diy_297"
        assert session.success_url == f"{BASE_URL}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}"
        db.payment_transactions.delete_many({"session_id": sid})

    def test_dwy_1497_checkout(self, api, db):
        r = api.post(f"{BASE_URL}/api/payments/direct-project-checkout", json={"origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        session = stripe.checkout.Session.retrieve(sid)
        assert session.amount_total == 149700
        assert session.metadata["purchase_source"] == "direct_board_recruitment_project"
        assert session.success_url == f"{BASE_URL}/board-recruitment-intake?session_id={{CHECKOUT_SESSION_ID}}"
        db.payment_transactions.delete_many({"session_id": sid})

    def test_unpaid_intake_context_blocked(self, api):
        r = api.get(f"{BASE_URL}/api/board-recruitment-intake/context",
                    params={"session_id": "cs_test_bogus_iter55"})
        assert r.status_code in (402, 404), r.status_code

    def test_grandfathered_both_entitlement_count(self, db):
        count = db.members.count_documents({
            "entitlements": {"$all": ["recruitment_self_guided", "recruitment_selection_onboarding"]},
            "email": {"$not": {"$regex": "^(TEST_|verifyA)"}},
        })
        assert count >= 8, count


# --- Other-funnel read-only regression ----------------------------------------
class TestOtherFunnels:
    @pytest.mark.parametrize("path", ["/reactivate", "/activate"])
    def test_pages_load(self, api, path):
        r = api.get(f"{BASE_URL}{path}")
        assert r.status_code == 200

    def test_reactivation_project_checkout(self, api, db):
        r = api.post(f"{BASE_URL}/api/payments/reactivation-project-checkout", json={"origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        assert stripe.checkout.Session.retrieve(sid).amount_total == 549700
        db.payment_transactions.delete_many({"session_id": sid})
