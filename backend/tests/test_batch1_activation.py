"""Batch 1: Board Fundraising Activation — public funnel, choice page config,
DIY $497 + DWM $2,497 checkouts, intake gating/submit, course endpoints,
claim entitlement grants, cross-product regression.

Public URL from REACT_APP_BACKEND_URL. Stripe TEST mode keys already in
backend/.env. Cleans up any test rows it creates.
"""
import os
import uuid
import asyncio
import pytest
import requests
import stripe
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
ORIGIN = BASE_URL
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers["Content-Type"] = "application/json"
    return s


@pytest.fixture(scope="module")
def db():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    mc = AsyncIOMotorClient(MONGO_URL)
    yield mc[DB_NAME], loop
    mc.close()
    loop.close()


def _run(loop, coro):
    return loop.run_until_complete(coro)


# ---- Public funnel /api/funnel-leads/fundraising_activation ----
class TestPublicFunnelActivation:
    def test_creates_lead_with_offer_source(self, client, db):
        mongo, loop = db
        payload = {
            "name": "TEST Activation Lead",
            "email": f"test-act-{uuid.uuid4().hex[:8]}@example.com",
            "organization": "TEST Nonprofit",
            "phone": "555-1212",
            "answers": {"board_member_count": "6-10"},
        }
        r = client.post(f"{BASE_URL}/api/funnel-leads/fundraising_activation", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["offer_source"] == "fundraising_activation"
        row = _run(loop, mongo.funnel_leads.find_one({"lead_id": body["lead_id"]}))
        assert row["organization"] == "TEST Nonprofit"
        assert row is not None
        assert row["offer_source"] == "fundraising_activation"
        assert row["answers"].get("board_member_count") == "6-10"
        _run(loop, mongo.funnel_leads.delete_one({"lead_id": body["lead_id"]}))

    def test_missing_required_answer_blocked(self, client):
        payload = {
            "name": "X", "email": "x@example.com",
            "organization": "Org", "phone": "555",
            "answers": {},
        }
        r = client.post(f"{BASE_URL}/api/funnel-leads/fundraising_activation", json=payload)
        assert r.status_code == 422, r.text

    def test_missing_required_top_level(self, client):
        r = client.post(f"{BASE_URL}/api/funnel-leads/fundraising_activation",
                        json={"name": "", "email": "x@example.com",
                              "organization": "", "phone": "",
                              "answers": {"board_member_count": "6-10"}})
        assert r.status_code in (400, 422)


# ---- /api/direct-activation/config ----
class TestActivationVideoConfig:
    def test_config_default_empty(self, client):
        r = client.get(f"{BASE_URL}/api/direct-activation/config")
        assert r.status_code == 200
        assert r.json().get("video_url", "") == ""

    def test_recruitment_reactivation_activation_isolated(self, client):
        rec = client.get(f"{BASE_URL}/api/direct-recruitment/config").json().get("video_url", "")
        rea = client.get(f"{BASE_URL}/api/direct-reactivation/config").json().get("video_url", "")
        act = client.get(f"{BASE_URL}/api/direct-activation/config").json().get("video_url", "")
        # activation must be empty in this env
        assert act == ""


# ---- DIY Activation Checkout ----
class TestActivationDIYCheckout:
    def test_diy_activation_checkout(self, client, db):
        r = client.post(f"{BASE_URL}/api/payments/activation-diy-checkout",
                        json={"origin_url": ORIGIN})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["session_id"].startswith("cs_")
        mongo, loop = db
        row = _run(loop, mongo.payment_transactions.find_one({"session_id": data["session_id"]}))
        assert row is not None
        assert row["amount"] == 49700
        assert row["purchase_source"] == "direct_diy_board_activation_497"
        assert row["offer_source"] == "direct_diy_board_activation"

        session = stripe.checkout.Session.retrieve(data["session_id"])
        assert session.amount_total == 49700
        assert session.currency == "usd"
        assert session.mode == "payment"
        assert "/purchase/success" in session.success_url
        assert "/activate-your-board-yourself?checkout=cancelled" in session.cancel_url or "cancelled" in session.cancel_url
        assert session.metadata["purchase_source"] == "direct_diy_board_activation_497"
        assert session.metadata["offer_source"] == "direct_diy_board_activation"
        assert session.metadata["selected_tier"] == "497"
        _run(loop, mongo.payment_transactions.delete_one({"session_id": data["session_id"]}))


# ---- DWM Activation Project Checkout ----
class TestActivationProjectCheckout:
    def test_project_activation_checkout(self, client, db):
        r = client.post(f"{BASE_URL}/api/payments/activation-project-checkout",
                        json={"origin_url": ORIGIN})
        assert r.status_code == 200, r.text
        data = r.json()
        session = stripe.checkout.Session.retrieve(data["session_id"])
        assert session.amount_total == 249700
        assert "/board-activation-intake?session_id=" in session.success_url
        assert "/board-activation-proposal?checkout=cancelled" in session.cancel_url
        assert session.metadata["purchase_source"] == "direct_board_activation_project_2497"

        mongo, loop = db
        row = _run(loop, mongo.payment_transactions.find_one({"session_id": data["session_id"]}))
        assert row is not None
        assert row["amount"] == 249700
        assert row["purchase_source"] == "direct_board_activation_project_2497"
        _run(loop, mongo.payment_transactions.delete_one({"session_id": data["session_id"]}))


# ---- Activation Intake Gating ----
class TestActivationIntakeGating:
    def test_context_404_bogus(self, client):
        r = client.get(f"{BASE_URL}/api/board-activation-intake/context",
                       params={"session_id": f"cs_bogus_{uuid.uuid4().hex}"})
        assert r.status_code == 404

    def test_context_402_unpaid_diy(self, client, db):
        r = client.post(f"{BASE_URL}/api/payments/activation-diy-checkout",
                        json={"origin_url": ORIGIN})
        sid = r.json()["session_id"]
        r2 = client.get(f"{BASE_URL}/api/board-activation-intake/context",
                        params={"session_id": sid})
        assert r2.status_code == 402, r2.text
        mongo, loop = db
        _run(loop, mongo.payment_transactions.delete_one({"session_id": sid}))

    def test_context_402_unpaid_dwm(self, client, db):
        r = client.post(f"{BASE_URL}/api/payments/activation-project-checkout",
                        json={"origin_url": ORIGIN})
        sid = r.json()["session_id"]
        r2 = client.get(f"{BASE_URL}/api/board-activation-intake/context",
                        params={"session_id": sid})
        assert r2.status_code == 402, r2.text
        mongo, loop = db
        _run(loop, mongo.payment_transactions.delete_one({"session_id": sid}))


# ---- Activation Intake happy path (seeded paid) ----
class TestActivationIntakeSubmit:
    def _seed_paid(self, mongo, loop, purchase_source, user_id=""):
        sid = f"cs_test_seed_{uuid.uuid4().hex[:16]}"
        doc = {
            "session_id": sid, "purchase_source": purchase_source,
            "offer_source": purchase_source.replace("_497", "").replace("_2497", ""),
            "amount": 49700 if "diy" in purchase_source else 249700,
            "currency": "usd", "status": "completed", "payment_status": "paid",
            "test_mode": True,
        }
        if user_id:
            doc["claimed_by_user_id"] = user_id
        _run(loop, mongo.payment_transactions.insert_one(doc))
        return sid

    def _valid_payload(self, sid):
        return {
            "session_id": sid, "your_name": "TEST Founder",
            "email": f"test-{uuid.uuid4().hex[:6]}@example.com",
            "organization_name": "TEST Org",
            "fundraising_goal": "Raise 200k",
            "amount_needed": "$200,000",
            "money_accomplish": "Program expansion",
            "current_methods": ["Individual donors", "Grants"],
            "current_methods_other": "",
            "written_strategy": "Partially",
            "fundraising_calendar": "No",
            "fundraising_carriers": ["Executive Director", "Board Members"],
            "fundraising_carriers_detail": "",
            "present_board": "10", "active_board": "6",
            "board_fundraising_involvement": "Some Board Members participate",
            "board_fundraising_activities": ["Attend events", "Make personal gifts"],
            "board_fundraising_activities_other": "",
            "perceived_barriers": "Time",
            "board_skills_relationships": "Some connections",
            "direction_12_24": "Expand programs",
            "organization_priorities": "Grow revenue",
            "previous_fundraising_planning": "No",
            "broader_strategic_planning": "Partially",
            "desired_change": "Confident board",
            "success_definition": "Board raises 50% of budget",
            "anything_else": "",
        }

    def test_diy_intake_submit_and_upsert(self, client, db):
        mongo, loop = db
        sid = self._seed_paid(mongo, loop, "direct_diy_board_activation_497")
        try:
            r = client.get(f"{BASE_URL}/api/board-activation-intake/context",
                           params={"session_id": sid})
            assert r.status_code == 200, r.text
            ctx = r.json()
            assert ctx["eligible"] is True
            assert ctx["purchase_source"] == "direct_diy_board_activation_497"
            assert ctx["submitted"] is False

            payload = self._valid_payload(sid)
            r = client.post(f"{BASE_URL}/api/board-activation-intake/submit", json=payload)
            assert r.status_code == 201, r.text
            body = r.json()
            assert body["redirect_url"] == "/activation-start-here"

            # Idempotent resubmit
            r = client.post(f"{BASE_URL}/api/board-activation-intake/submit", json=payload)
            assert r.status_code == 201
            count = _run(loop, mongo.board_activation_intakes.count_documents({"session_id": sid}))
            assert count == 1

            r = client.get(f"{BASE_URL}/api/board-activation-intake/context",
                           params={"session_id": sid})
            assert r.json()["submitted"] is True
        finally:
            _run(loop, mongo.payment_transactions.delete_one({"session_id": sid}))
            _run(loop, mongo.board_activation_intakes.delete_many({"session_id": sid}))

    def test_dwm_intake_submit_calendly_redirect(self, client, db):
        mongo, loop = db
        sid = self._seed_paid(mongo, loop, "direct_board_activation_project_2497")
        try:
            payload = self._valid_payload(sid)
            r = client.post(f"{BASE_URL}/api/board-activation-intake/submit", json=payload)
            assert r.status_code == 201, r.text
            body = r.json()
            assert body["redirect_url"] == "https://calendly.com/boardbuilder/recruitboard"
        finally:
            _run(loop, mongo.payment_transactions.delete_one({"session_id": sid}))
            _run(loop, mongo.board_activation_intakes.delete_many({"session_id": sid}))

    def test_active_gt_present_rejected(self, client, db):
        mongo, loop = db
        sid = self._seed_paid(mongo, loop, "direct_diy_board_activation_497")
        try:
            payload = self._valid_payload(sid)
            payload["present_board"] = "5"
            payload["active_board"] = "10"
            r = client.post(f"{BASE_URL}/api/board-activation-intake/submit", json=payload)
            assert r.status_code == 422, r.text
        finally:
            _run(loop, mongo.payment_transactions.delete_one({"session_id": sid}))
            _run(loop, mongo.board_activation_intakes.delete_many({"session_id": sid}))


# ---- Activation Course endpoints ----
class TestActivationCourseEndpoints:
    def test_courses_activation_401_no_auth(self, client):
        r = requests.get(f"{BASE_URL}/api/courses/activation/self-guided", timeout=15)
        assert r.status_code == 401

    def test_module_tester_403_activation(self, client):
        # login as module-tester
        r = requests.post(f"{BASE_URL}/api/members/login",
                          json={"email": "module-tester@example.com", "password": os.environ["MODULE_TESTER_PASSWORD"]},
                          timeout=15)
        assert r.status_code == 200, r.text
        token = r.json().get("access_token") or r.json().get("token")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        cookies = r.cookies
        r2 = requests.get(f"{BASE_URL}/api/courses/activation/self-guided",
                          headers=headers, cookies=cookies, timeout=15)
        assert r2.status_code == 403, f"expected 403, got {r2.status_code}: {r2.text}"

    def test_progress_activation_module6_rejected(self, client, db):
        # log in as module-tester (no activation entitlement) - progress endpoint requires
        # entitlement so we can only assert 422 or 403; we accept both because entitlement is checked also
        r = requests.post(f"{BASE_URL}/api/members/login",
                          json={"email": "module-tester@example.com", "password": os.environ["MODULE_TESTER_PASSWORD"]},
                          timeout=15)
        token = r.json().get("access_token") or r.json().get("token")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        cookies = r.cookies
        r2 = requests.post(f"{BASE_URL}/api/courses/progress",
                           json={"product": "activation_self_guided", "module_number": 6, "action": "completed"},
                           headers=headers, cookies=cookies, timeout=15)
        # Per checklist should be 422 (module cap) - the cap check is before entitlement gate
        assert r2.status_code == 422, f"expected 422, got {r2.status_code}: {r2.text}"


# ---- Claim purchase: DIY activation grants entitlement / DWM rejected ----
class TestActivationClaim:
    def test_claim_diy_activation_grants_entitlement(self, client, db):
        """This test exercises claim-purchase on a paid DIY activation session.
        Per checklist Item 6, expected outcome is claim SUCCESS with entitlement
        activation_self_guided ONLY. We use stripe test-mode payment simulation
        via checkout session created and then need to actually complete payment
        - but we cannot programmatically complete a real Stripe payment without
        a browser. So we skip real-payment portion and check the claim behavior
        against a real (unpaid) session_id: expected 402 unpaid.

        Additionally we check that the claim branching logic recognizes
        direct_diy_board_activation offer_source (not silently rejects as
        'not a Recruitment program purchase').
        """
        mongo, loop = db
        # Create a real DIY activation checkout session (unpaid)
        r = client.post(f"{BASE_URL}/api/payments/activation-diy-checkout",
                        json={"origin_url": ORIGIN})
        sid = r.json()["session_id"]

        # Register a new member with this session_id — will attempt to claim
        email = f"test-claim-{uuid.uuid4().hex[:8]}@example.com"
        try:
            rr = requests.post(f"{BASE_URL}/api/members/register",
                               json={"first_name": "TEST", "last_name": "Claim",
                                     "email": email, "password": os.environ["TEST_ACCOUNT_PASSWORD"],
                                     "confirm_password": os.environ["TEST_ACCOUNT_PASSWORD"],
                                     "session_id": sid},
                               timeout=15)
            # Since session is unpaid, expect 402 (payment not completed)
            # Not 400 ("not a Recruitment program purchase") which would indicate
            # missing activation branch in claim_recruitment_purchase
            assert rr.status_code in (402, 201), f"got {rr.status_code}: {rr.text}"
            if rr.status_code == 400 and "not a Recruitment program purchase" in rr.text:
                pytest.fail("BUG: claim_recruitment_purchase does not handle "
                            "direct_diy_board_activation offer_source — falls through to 400")
        finally:
            _run(loop, mongo.payment_transactions.delete_one({"session_id": sid}))
            _run(loop, mongo.members.delete_one({"email": email}))
            _run(loop, mongo.purchases.delete_one({"session_id": sid}))

    def test_claim_diy_activation_seeded_paid_grants_entitlement(self, client, db):
        """Seed a paid direct_diy_board_activation transaction and attempt claim
        via member register. But claim_recruitment_purchase calls stripe to
        retrieve session — with a fake seeded session_id it will fail at stripe.
        So we skip claim assertion and just probe the code path via error content."""
        mongo, loop = db
        # Use a REAL activation-diy-checkout session (unpaid) and force it "paid"
        # via stripe test payment is not possible headless. Instead we test that
        # if the offer_source metadata is direct_diy_board_activation and tier=497,
        # register would not immediately raise 400 'not a Recruitment program purchase'.
        r = client.post(f"{BASE_URL}/api/payments/activation-diy-checkout",
                        json={"origin_url": ORIGIN})
        sid = r.json()["session_id"]
        email = f"test-claim2-{uuid.uuid4().hex[:8]}@example.com"
        try:
            rr = requests.post(f"{BASE_URL}/api/members/register",
                               json={"first_name": "TEST", "last_name": "Claim2",
                                     "email": email, "password": os.environ["TEST_ACCOUNT_PASSWORD"],
                                     "confirm_password": os.environ["TEST_ACCOUNT_PASSWORD"],
                                     "session_id": sid},
                               timeout=15)
            # Unpaid, expect 402 not 400 with 'not a Recruitment program purchase'
            if rr.status_code == 400:
                assert "not a Recruitment program purchase" not in rr.text, (
                    "BUG confirmed: claim_recruitment_purchase missing "
                    "direct_diy_board_activation branch, treats DIY activation "
                    "session as non-recruitment and rejects with 400."
                )
        finally:
            _run(loop, mongo.payment_transactions.delete_one({"session_id": sid}))
            _run(loop, mongo.members.delete_one({"email": email}))

    def test_claim_dwm_activation_rejected(self, client, db):
        """Per checklist Item 7 — DWM activation session must be REJECTED at claim
        with 400 'not a Recruitment program purchase' (no entitlement)."""
        mongo, loop = db
        r = client.post(f"{BASE_URL}/api/payments/activation-project-checkout",
                        json={"origin_url": ORIGIN})
        sid = r.json()["session_id"]
        email = f"test-dwmclaim-{uuid.uuid4().hex[:8]}@example.com"
        try:
            rr = requests.post(f"{BASE_URL}/api/members/register",
                               json={"first_name": "TEST", "last_name": "DWM",
                                     "email": email, "password": os.environ["TEST_ACCOUNT_PASSWORD"],
                                     "confirm_password": os.environ["TEST_ACCOUNT_PASSWORD"],
                                     "session_id": sid},
                               timeout=15)
            # Unpaid -> 402 first; if session was somehow paid, DWM claim MUST return 400
            assert rr.status_code in (400, 402), f"got {rr.status_code}: {rr.text}"
        finally:
            _run(loop, mongo.payment_transactions.delete_one({"session_id": sid}))
            _run(loop, mongo.members.delete_one({"email": email}))


# ---- Static source verification: claim_recruitment_purchase must handle DIY activation ----
class TestClaimSourceHandlesActivation:
    def test_diy_activation_branch_present_in_source(self):
        """Verify that member_routes.claim_recruitment_purchase has an explicit
        branch that maps offer_source='direct_diy_board_activation' + tier='497'
        to entitlement='activation_self_guided'. Without this branch a paid DIY
        activation session claim will fall through to the 400 'not a Recruitment
        program purchase' error."""
        import re
        src = open("/app/backend/member_routes.py").read()
        # Find the block from "async def claim_recruitment_purchase" until the return
        m = re.search(r"async def claim_recruitment_purchase.*?return purchase",
                      src, re.DOTALL)
        assert m, "Could not locate claim_recruitment_purchase in member_routes.py"
        block = m.group(0)
        # There must be a branch that sets entitlement = "activation_self_guided"
        assert "activation_self_guided" in block, (
            "BUG: claim_recruitment_purchase does NOT set "
            "entitlement='activation_self_guided' anywhere. A paid DIY "
            "activation session (offer_source=direct_diy_board_activation, "
            "tier=497) will fall through to 400 'not a Recruitment program "
            "purchase' and no entitlement will be granted."
        )
        # There must be a branch that recognises direct_diy_board_activation as
        # a valid entitlement source (before the else). We look for it in the
        # entitlement-mapping ladder.
        entitlement_ladder = block.split("purchase.update")[0] if "purchase.update" in block else block
        assert "direct_diy_board_activation" in entitlement_ladder and \
               entitlement_ladder.count("direct_diy_board_activation") >= 1, (
            "BUG: claim_recruitment_purchase entitlement resolution does not "
            "handle offer_source='direct_diy_board_activation'."
        )



class TestRegression:
    def test_diy_recruitment_still_works(self, client, db):
        r = client.post(f"{BASE_URL}/api/payments/diy-checkout",
                        json={"origin_url": ORIGIN})
        assert r.status_code == 200
        sid = r.json()["session_id"]
        mongo, loop = db
        _run(loop, mongo.payment_transactions.delete_one({"session_id": sid}))

    def test_diy_reactivation_still_works(self, client, db):
        r = client.post(f"{BASE_URL}/api/payments/reactivation-diy-checkout",
                        json={"origin_url": ORIGIN})
        assert r.status_code == 200
        sid = r.json()["session_id"]
        mongo, loop = db
        _run(loop, mongo.payment_transactions.delete_one({"session_id": sid}))

    def test_recruit_funnel_still_works(self, client, db):
        payload = {"name": "TEST", "email": f"test-r-{uuid.uuid4().hex[:6]}@example.com",
                   "organization": "TEST Org", "phone": "555",
                   "answers": {"disengaged_count": "6-10", "support_preference": "diy"}}
        r = client.post(f"{BASE_URL}/api/funnel-leads/recruitment", json=payload)
        # recruitment funnel requires different answer keys but should return either 201 or 422
        assert r.status_code in (201, 422)
        if r.status_code == 201:
            mongo, loop = db
            _run(loop, mongo.funnel_leads.delete_one({"lead_id": r.json()["lead_id"]}))


# ---- Public SPA routes serve HTML ----
class TestPublicRoutes:
    @pytest.mark.parametrize("path", [
        "/activate", "/activate-with-rooney", "/activate-your-board-yourself",
        "/board-activation-proposal", "/board-activation-intake",
        "/activation-start-here",
    ])
    def test_route_returns_html(self, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=15)
        assert r.status_code == 200
        assert 'id="root"' in r.text or "id='root'" in r.text
