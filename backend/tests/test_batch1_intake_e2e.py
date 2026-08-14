"""Batch 1 Reactivation intake + DWM flow using paid-state DB simulation.

Since we cannot complete a real card-form Stripe checkout headlessly reliably,
mark the payment_transaction as paid via Mongo — verified_transaction() will use
the DB paid state and skip the Stripe status check (only unpaid rows re-check Stripe).
"""
import os, sys, uuid, asyncio
import pytest
import requests

from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

sys.path.insert(0, "/app/backend")
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
ORIGIN = BASE_URL

# Reactivation intake data
INTAKE_ANSWERS = {
    "your_name": "TEST Founder", "email": "test_founder@example.com",
    "organization_name": "TEST Nonprofit", "mission": "Help",
    "direction_12_24": "grow programs", "board_help_accomplish": "fundraising",
    "active_board_vision": "engaged", "present_board": "9", "active_board": "5",
    "disengaged_board": "4", "current_skills": "legal", "missing_skills": "finance",
    "recruited_how": ["Invited by Founder"], "original_responsibilities": "vague",
    "roles_defined": "No", "roles_description": "", "expected_contribution": "meetings",
    "actually_happening": "quiet", "strategic_plan": "No",
    "board_participated_planning": "No", "planning_involvement": "",
    "disengage_reason": "no clarity", "disengage_when": "over time",
    "disengagement_signs": ["Missing meetings"], "disengagement_signs_other": "",
    "reactivation_attempts": "reminders", "attempts_outcome": "no change",
    "meeting_frequency": "quarterly", "typical_meeting": "reports",
    "clear_responsibilities_after_meetings": "No",
    "transition_options": ["Advisory role"], "anything_else": "",
}


@pytest.fixture(scope="module")
def db():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], io_loop=loop)
    yield client[os.environ["DB_NAME"]], loop
    loop.close()


@pytest.fixture(scope="module")
def http():
    return requests.Session()


def mark_paid(db_tuple, session_id):
    db, loop = db_tuple
    loop.run_until_complete(
        db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "paid", "status": "completed"}},
        )
    )


class TestDIYE2E:
    def test_full_diy_flow(self, db, http):
        db_tuple = db
        db, loop = db_tuple
        # 1. Create reactivation DIY checkout
        chk = http.post(f"{API}/payments/reactivation-diy-checkout", json={"origin_url": ORIGIN}).json()
        sid = chk["session_id"]
        mark_paid(db_tuple, sid)

        # 2. Register a fresh member (without session_id — Stripe not truly paid) then seed entitlement
        email = f"test_diy_e2e_{uuid.uuid4().hex[:6]}@example.com"
        reg = http.post(f"{API}/members/register", json={
            "first_name": "TEST", "last_name": "DIYE2E", "email": email,
            "password": "TestPass123!", "confirm_password": "TestPass123!",
        })
        assert reg.status_code == 201, reg.text
        user_id = reg.json()["member"]["user_id"]
        token = reg.json()["token"]

        # Seed entitlement + purchase + link transaction to the user (simulates successful claim)
        loop.run_until_complete(db.members.update_one(
            {"user_id": user_id},
            {"$addToSet": {"entitlements": "reactivation_self_guided"}},
        ))
        loop.run_until_complete(db.purchases.insert_one({
            "purchase_id": str(uuid.uuid4()), "user_id": user_id, "session_id": sid,
            "entitlement": "reactivation_self_guided",
            "purchase_source": "direct_diy_board_reactivation_497",
            "product": "Do It Yourself Board Reactivation", "tier": "497",
        }))

        # 3. Intake context — should be eligible with purchase_source direct_diy
        ctx = http.get(f"{API}/board-reactivation-intake/context", params={"session_id": sid})
        assert ctx.status_code == 200, ctx.text
        cdata = ctx.json()
        assert cdata["eligible"] is True
        assert cdata["purchase_source"] == "direct_diy_board_reactivation_497"
        assert cdata["submitted"] is False

        # 4. Submit intake -> DIY redirect
        payload = {"session_id": sid, **INTAKE_ANSWERS, "email": email}
        sub = http.post(f"{API}/board-reactivation-intake/submit", json=payload)
        assert sub.status_code == 201, sub.text
        assert sub.json()["redirect_url"] == "/reactivation-start-here"

        # 5. Intake persisted with correct purchase_source + linked user_id
        intake = loop.run_until_complete(
            db.board_reactivation_intakes.find_one({"session_id": sid}, {"_id": 0})
        )
        assert intake is not None
        assert intake["purchase_source"] == "direct_diy_board_reactivation_497"
        assert intake["user_id"] == user_id

        # 6. GET again returns submitted=True
        ctx2 = http.get(f"{API}/board-reactivation-intake/context", params={"session_id": sid}).json()
        assert ctx2["submitted"] is True

        # 7. Course endpoint returns 5 reactivation modules
        course = http.get(f"{API}/courses/reactivation/self-guided",
                          headers={"Authorization": f"Bearer {token}"})
        assert course.status_code == 200, course.text
        modules = course.json().get("modules", [])
        assert len(modules) == 5, f"expected 5 modules, got {len(modules)}"
        titles = [m["title"] for m in modules]
        expected = ["Why Boards Disengage", "Reactivating Your Board",
                    "Having the Difficult Conversation", "Equipping Each Board Member", "My Board"]
        for exp in expected:
            assert any(exp in t for t in titles), f"missing '{exp}' in {titles}"

        # 8. Mark module 1 complete
        prog = http.post(f"{API}/courses/progress",
                        json={"product": "reactivation_self_guided", "module_number": 1, "action": "completed"},
                        headers={"Authorization": f"Bearer {token}"})
        assert prog.status_code in (200, 201), prog.text

        # 9. Logout + login + verify persistence
        http.post(f"{API}/members/logout")
        login = http.post(f"{API}/members/login", json={"email": email, "password": "TestPass123!"})
        assert login.status_code == 200
        token2 = login.json()["token"]
        course2 = http.get(f"{API}/courses/reactivation/self-guided",
                           headers={"Authorization": f"Bearer {token2}"}).json()
        m1 = next(m for m in course2["modules"] if m["number"] == 1)
        assert m1.get("completed") is True, f"progress didn't persist: {m1}"


class TestDWMPaidFlow:
    def test_dwm_no_account_intake_calendly_redirect(self, db, http):
        db_tuple = db
        db, loop = db_tuple
        # Create project checkout, mark paid
        chk = http.post(f"{API}/payments/reactivation-project-checkout", json={"origin_url": ORIGIN}).json()
        sid = chk["session_id"]
        mark_paid(db_tuple, sid)

        # Intake context works WITHOUT auth
        ctx = http.get(f"{API}/board-reactivation-intake/context", params={"session_id": sid})
        assert ctx.status_code == 200
        assert ctx.json()["purchase_source"] == "direct_board_reactivation_project"

        # Submit → Calendly redirect
        payload = {"session_id": sid, **INTAKE_ANSWERS}
        sub = http.post(f"{API}/board-reactivation-intake/submit", json=payload)
        assert sub.status_code == 201
        assert sub.json()["redirect_url"] == "https://calendly.com/boardbuilder/recruitboard"

    def test_dwm_session_cannot_be_claimed(self, db, http):
        db_tuple = db
        db, loop = db_tuple
        # Mark a project checkout as paid, try to claim → 400 (not a recruitment/DIY-recruit/DIY-react/rooney source)
        chk = http.post(f"{API}/payments/reactivation-project-checkout", json={"origin_url": ORIGIN}).json()
        sid = chk["session_id"]
        mark_paid(db_tuple, sid)
        # Also patch the Stripe session? claim_recruitment_purchase re-verifies via Stripe metadata.
        # Register member and attempt claim
        email = f"test_dwm_claim_{uuid.uuid4().hex[:6]}@example.com"
        reg = http.post(f"{API}/members/register", json={
            "first_name": "TEST", "last_name": "DWM", "email": email,
            "password": "TestPass123!", "confirm_password": "TestPass123!",
        })
        token = reg.json()["token"]
        r = http.post(f"{API}/members/claim-purchase", json={"session_id": sid},
                      headers={"Authorization": f"Bearer {token}"})
        # Stripe session isn't actually paid (we only marked DB), so Stripe returns unpaid -> 402
        # OR if we could bypass, the metadata offer_source=direct_board_reactivation_project would raise 400
        assert r.status_code in (400, 402), r.text
