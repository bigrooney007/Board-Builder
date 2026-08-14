"""Batch 2 Reactivation — Board Member Profile & Recommitment System.

Covers: roster API + auth, add/import board members, dedupe/tenant isolation,
email preview + send (resend delivered@resend.dev), call script + notes,
public form context + submit (valid, invalid, dup, missing fields),
view response, admin overview, light regression.
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

ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PW = os.environ["ADMIN_PASSWORD"]
RECRUIT_EMAIL = "module-tester@example.com"
RECRUIT_PW = os.environ["MODULE_TESTER_PASSWORD"]


@pytest.fixture(scope="module")
def loop():
    lp = asyncio.new_event_loop()
    asyncio.set_event_loop(lp)
    yield lp
    lp.close()


@pytest.fixture(scope="module")
def db(loop):
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], io_loop=loop)
    return client[os.environ["DB_NAME"]]


def run(loop, coro):
    return loop.run_until_complete(coro)


@pytest.fixture(scope="module")
def founder(loop, db):
    """Reactivation member (founder) with intake + advisory permitted, NO support role option."""
    email = f"test_batch2_founder_{uuid.uuid4().hex[:6]}@example.com"
    reg = requests.post(f"{API}/members/register", json={
        "first_name": "TestBatch2", "last_name": "Founder", "email": email,
        "password": os.environ["TEST_ACCOUNT_PASSWORD"], "confirm_password": os.environ["TEST_ACCOUNT_PASSWORD"],
    })
    assert reg.status_code == 201, reg.text
    user_id = reg.json()["member"]["user_id"]
    token = reg.json()["token"]
    # Grant reactivation entitlement + purchase + intake
    run(loop, db.members.update_one(
        {"user_id": user_id},
        {"$addToSet": {"entitlements": "reactivation_self_guided"}},
    ))
    run(loop, db.purchases.insert_one({
        "purchase_id": str(uuid.uuid4()), "user_id": user_id,
        "session_id": f"seed_{uuid.uuid4().hex[:8]}",
        "entitlement": "reactivation_self_guided",
        "purchase_source": "direct_diy_board_reactivation_497",
        "product": "Do It Yourself Board Reactivation", "tier": "497",
    }))
    run(loop, db.board_reactivation_intakes.insert_one({
        "user_id": user_id, "session_id": f"seed_{uuid.uuid4().hex[:8]}",
        "organization_name": "TESTBatch2 Nonprofit",
        "founder_title": "Founder & CEO",
        "purchase_source": "direct_diy_board_reactivation_497",
        # Advisory allowed but NOT volunteer/support role
        "transition_options": ["Transition to an Advisory Board / Advisory Role"],
        "submitted_at": "2026-01-01T00:00:00+00:00",
    }))
    return {"email": email, "user_id": user_id, "token": token,
            "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="module")
def founder_b(loop, db):
    """Second reactivation user for tenant isolation checks."""
    email = f"test_batch2_founder_b_{uuid.uuid4().hex[:6]}@example.com"
    reg = requests.post(f"{API}/members/register", json={
        "first_name": "TestBatch2B", "last_name": "Other", "email": email,
        "password": os.environ["TEST_ACCOUNT_PASSWORD"], "confirm_password": os.environ["TEST_ACCOUNT_PASSWORD"],
    })
    user_id = reg.json()["member"]["user_id"]
    token = reg.json()["token"]
    run(loop, db.members.update_one({"user_id": user_id}, {"$addToSet": {"entitlements": "reactivation_self_guided"}}))
    run(loop, db.board_reactivation_intakes.insert_one({
        "user_id": user_id, "session_id": f"seed_{uuid.uuid4().hex[:8]}",
        "organization_name": "TESTBatch2 B Org", "founder_title": "ED",
        "purchase_source": "direct_diy_board_reactivation_497",
        "transition_options": [],
        "submitted_at": "2026-01-01T00:00:00+00:00",
    }))
    return {"user_id": user_id, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


# =========== AUTH GUARDS ===========

class TestAuthGuards:
    def test_roster_unauth_returns_401(self):
        r = requests.get(f"{API}/reactivation/roster")
        assert r.status_code == 401, r.text

    def test_roster_recruitment_only_returns_403(self):
        login = requests.post(f"{API}/members/login", json={"email": RECRUIT_EMAIL, "password": RECRUIT_PW})
        assert login.status_code == 200, login.text
        tok = login.json()["token"]
        r = requests.get(f"{API}/reactivation/roster", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 403, r.text

    def test_admin_overview_requires_admin(self, founder):
        r = requests.get(f"{API}/admin/reactivation/overview", headers=founder["headers"])
        # non-admin member — auth service should reject with 401 or 403
        assert r.status_code in (401, 403), r.text


# =========== ROSTER + ADD + IMPORT ===========

class TestRosterAndAdd:
    def test_roster_empty_initially(self, founder):
        r = requests.get(f"{API}/reactivation/roster", headers=founder["headers"])
        assert r.status_code == 200
        data = r.json()
        assert data["members"] == []
        assert data["progress"] == {"total": 0, "completed": 0, "waiting": 0}

    def test_add_board_member(self, founder):
        payload = {"name": "TEST Alice Board", "email": "delivered@resend.dev",
                   "phone": "555-1111", "role": "Board Member"}
        r = requests.post(f"{API}/reactivation/board-members", json=payload, headers=founder["headers"])
        assert r.status_code == 201, r.text
        assert r.json()["status"] == "created"
        founder["alice_id"] = r.json()["member"]["member_record_id"]
        assert r.json()["member"]["status"] == "NOT SENT"

    def test_add_board_member_dedupe(self, founder):
        payload = {"name": "TEST Alice Duplicate", "email": "delivered@resend.dev"}
        r = requests.post(f"{API}/reactivation/board-members", json=payload, headers=founder["headers"])
        assert r.status_code == 201
        assert r.json()["status"] == "exists"

    def test_add_missing_name_returns_422(self, founder):
        r = requests.post(f"{API}/reactivation/board-members",
                          json={"email": "someoneelse@example.com"}, headers=founder["headers"])
        assert r.status_code == 422

    def test_add_missing_email_returns_422(self, founder):
        r = requests.post(f"{API}/reactivation/board-members",
                          json={"name": "No Email"}, headers=founder["headers"])
        assert r.status_code == 422

    def test_roster_after_add(self, founder):
        r = requests.get(f"{API}/reactivation/roster", headers=founder["headers"]).json()
        assert r["progress"]["total"] == 1
        assert r["progress"]["waiting"] == 1
        assert r["members"][0]["email"] == "delivered@resend.dev"

    def test_import_from_recruitment(self, loop, db, founder):
        # Seed opportunity_application owned by founder + status Selected
        app_id = str(uuid.uuid4())
        run(loop, db.opportunity_applications.insert_one({
            "application_id": app_id, "owner_user_id": founder["user_id"],
            "opportunity_id": f"opp_{uuid.uuid4().hex[:8]}",
            "applicant_email": "test_import_target@example.com", "status": "Selected",
            "profile_snapshot": {"full_name": "TEST Bob Recruit", "phone": "555-2222"},
        }))
        # roster now shows this in existing_people
        r = requests.get(f"{API}/reactivation/roster", headers=founder["headers"]).json()
        emails = [p["email"] for p in r["existing_people"]]
        assert "test_import_target@example.com" in emails
        # import
        imp = requests.post(f"{API}/reactivation/board-members/import",
                            json={"application_id": app_id}, headers=founder["headers"])
        assert imp.status_code == 201, imp.text
        assert imp.json()["status"] == "created"
        founder["bob_id"] = imp.json()["member"]["member_record_id"]
        # Roster: bob is now in members, no longer in existing_people
        r2 = requests.get(f"{API}/reactivation/roster", headers=founder["headers"]).json()
        emails_now = [p["email"] for p in r2["existing_people"]]
        assert "test_import_target@example.com" not in emails_now
        # Re-import returns exists
        imp2 = requests.post(f"{API}/reactivation/board-members/import",
                             json={"application_id": app_id}, headers=founder["headers"])
        assert imp2.json()["status"] == "exists"


# =========== TENANT ISOLATION ===========

class TestTenantIsolation:
    def test_founder_b_cannot_see_a_members(self, founder, founder_b):
        r = requests.get(f"{API}/reactivation/roster", headers=founder_b["headers"]).json()
        emails = [m["email"] for m in r["members"]]
        assert "delivered@resend.dev" not in emails

    def test_founder_b_cannot_read_a_member_details(self, founder, founder_b):
        alice_id = founder["alice_id"]
        r = requests.get(f"{API}/reactivation/board-members/{alice_id}/email-preview",
                         headers=founder_b["headers"])
        assert r.status_code == 404

    def test_founder_b_cannot_send_form_for_a_member(self, founder, founder_b):
        alice_id = founder["alice_id"]
        r = requests.post(f"{API}/reactivation/board-members/{alice_id}/send",
                          json={"type": "initial"}, headers=founder_b["headers"])
        assert r.status_code == 404


# =========== EMAIL PREVIEW + SEND FLOW ===========

class TestSendFlow:
    def test_email_preview_initial(self, founder):
        alice_id = founder["alice_id"]
        r = requests.get(f"{API}/reactivation/board-members/{alice_id}/email-preview",
                         headers=founder["headers"])
        assert r.status_code == 200
        data = r.json()
        assert data["subject"] == "Board Recommitment & Profile | TESTBatch2 Nonprofit"
        assert "This is not about pressuring anyone to stay." in data["body"]
        assert "[Organization Name]" not in data["body"]
        assert "TEST" not in data["subject"].replace("TESTBatch2", "")  # substring check
        assert "localhost" not in data["form_link"]
        assert "/board-recommitment/" in data["form_link"]
        # bullet list present
        assert "- how you would like to continue contributing" in data["body"]

    def test_email_preview_reminder(self, founder):
        alice_id = founder["alice_id"]
        r = requests.get(f"{API}/reactivation/board-members/{alice_id}/email-preview",
                         params={"type": "reminder"}, headers=founder["headers"]).json()
        assert r["subject"] == "Reminder: Board Member Recommitment Form | TESTBatch2 Nonprofit"

    def test_send_initial_form(self, loop, db, founder):
        alice_id = founder["alice_id"]
        r = requests.post(f"{API}/reactivation/board-members/{alice_id}/send",
                          json={"type": "initial"}, headers=founder["headers"])
        # delivered@resend.dev is Resend-accepted test address; API should return 200
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "sent"
        # DB status transitioned to SENT
        rec = run(loop, db.reactivation_board_members.find_one({"member_record_id": alice_id}))
        assert rec["status"] == "SENT"
        assert rec["last_sent_at"]
        # Remember token for later
        founder["alice_token"] = rec["form_token"]

    def test_resend_keeps_same_token(self, loop, db, founder):
        alice_id = founder["alice_id"]
        before = founder["alice_token"]
        r = requests.post(f"{API}/reactivation/board-members/{alice_id}/send",
                          json={"type": "initial"}, headers=founder["headers"])
        assert r.status_code == 200
        rec = run(loop, db.reactivation_board_members.find_one({"member_record_id": alice_id}))
        assert rec["form_token"] == before

    def test_send_reminder_records_last_reminder_at(self, loop, db, founder):
        alice_id = founder["alice_id"]
        r = requests.post(f"{API}/reactivation/board-members/{alice_id}/send",
                          json={"type": "reminder"}, headers=founder["headers"])
        assert r.status_code == 200
        rec = run(loop, db.reactivation_board_members.find_one({"member_record_id": alice_id}))
        assert rec["last_reminder_at"]

    def test_call_script(self, founder):
        alice_id = founder["alice_id"]
        r = requests.get(f"{API}/reactivation/board-members/{alice_id}/call-script",
                         headers=founder["headers"])
        assert r.status_code == 200
        data = r.json()
        assert "TEST" in data["script"]  # first name of the seeded member ("TEST Alice Board")
        assert "TESTBatch2 Nonprofit" in data["script"]
        assert "dead weight" not in data["script"].lower()
        assert "step up or step down" not in data["script"].lower()

    def test_save_call_notes(self, loop, db, founder):
        alice_id = founder["alice_id"]
        r = requests.put(f"{API}/reactivation/board-members/{alice_id}/call-notes",
                         json={"notes": "TEST called Alice, will complete this week"},
                         headers=founder["headers"])
        assert r.status_code == 200
        rec = run(loop, db.reactivation_board_members.find_one({"member_record_id": alice_id}))
        assert rec["call_notes"] == "TEST called Alice, will complete this week"


# =========== PUBLIC FORM ===========

VALID_PAYLOAD = {
    "full_name": "TEST Alice Board", "preferred_name": "Ally",
    "email": "delivered@resend.dev", "phone": "555-1111",
    "city_state": "Denver, CO", "linkedin": "",
    "current_position": "Director of Ops", "employer": "TEST Co",
    "industry": "Nonprofit", "years_experience": "10",
    "expertise": ["Fundraising", "Strategic Planning"], "expertise_other": "",
    "networks": ["Business Leaders"],
    "why_joined": "Mission-aligned.", "how_recruited": "Invited by the Founder / Executive Director",
    "original_role_expectation": "Attend meetings and fundraise.",
    "role_clarity": "Somewhat Clear", "clarity_help": "",
    "board_experience": "Positive but limited engagement.",
    "participation_barriers": "Work travel.", "board_improvement": "More clarity on roles.",
    "strategic_clarity": "Somewhat Clear", "planning_participation": "Somewhat",
    "planning_involvement_desire": "",
    "recommitment": "Yes — I am ready to continue serving actively.",
    "advisory_openness": "",
    "contribution_interests": ["Fundraising", "Governance"],
    "fundraising_comfort": ["Making introductions to potential donors"],
    "ownership_areas": "Fundraising committee.",
    "leadership_interest": "Chair fundraising committee.",
    "support_needed": "Training on grant writing.",
    "monthly_availability": "5–8 hours", "meeting_participation": "Yes",
    "constraints": "", "meaningful_service": "Impact on students.",
    "anything_else": "", "confirmation": True,
}


class TestPublicForm:
    def test_public_context_valid_token(self, founder):
        token = founder["alice_token"]
        r = requests.get(f"{API}/board-recommitment/{token}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["organization_name"] == "TESTBatch2 Nonprofit"
        assert data["submitted"] is False
        assert data["allow_advisory"] is True
        assert data["allow_support_role"] is False  # not in transition_options
        assert data["recommitment_options"] == [
            "Yes — I am ready to continue serving actively.",
            "Yes — but I need greater clarity about my role and responsibilities.",
            "Yes — but my current time/capacity is limited and I need a role that reflects that.",
            "I am unsure and would like to discuss what continued Board service would involve.",
            "No — I am no longer able to continue serving actively in my current Board role.",
        ]
        assert data["prefill"]["email"] == "delivered@resend.dev"

    def test_public_context_invalid_token(self):
        r = requests.get(f"{API}/board-recommitment/invalidtoken12345")
        assert r.status_code == 404

    def test_submit_missing_confirmation_returns_422(self, founder):
        token = founder["alice_token"]
        payload = {**VALID_PAYLOAD, "confirmation": False}
        r = requests.post(f"{API}/board-recommitment/{token}", json=payload)
        assert r.status_code == 422, r.text

    def test_submit_invalid_recommitment_returns_422(self, founder):
        token = founder["alice_token"]
        payload = {**VALID_PAYLOAD, "recommitment": "Some other invalid string"}
        r = requests.post(f"{API}/board-recommitment/{token}", json=payload)
        assert r.status_code == 422, r.text

    def test_submit_valid(self, loop, db, founder):
        token = founder["alice_token"]
        r = requests.post(f"{API}/board-recommitment/{token}", json=VALID_PAYLOAD)
        assert r.status_code == 201, r.text
        assert r.json()["organization_name"] == "TESTBatch2 Nonprofit"
        rec = run(loop, db.reactivation_board_members.find_one({"member_record_id": founder["alice_id"]}))
        assert rec["status"] == "COMPLETED"
        assert rec["submitted_at"]
        assert rec["response"]["recommitment"] == VALID_PAYLOAD["recommitment"]

    def test_revisit_already_submitted(self, founder):
        token = founder["alice_token"]
        r = requests.get(f"{API}/board-recommitment/{token}").json()
        assert r["submitted"] is True

    def test_repost_returns_409(self, founder):
        token = founder["alice_token"]
        r = requests.post(f"{API}/board-recommitment/{token}", json=VALID_PAYLOAD)
        assert r.status_code == 409


# =========== VIEW RESPONSE (founder side) ===========

class TestViewResponse:
    def test_view_response_completed(self, founder):
        alice_id = founder["alice_id"]
        r = requests.get(f"{API}/reactivation/board-members/{alice_id}/response",
                         headers=founder["headers"])
        assert r.status_code == 200
        data = r.json()
        assert data["response"]["recommitment"] == "Yes — I am ready to continue serving actively."
        assert data["submitted_at"]

    def test_view_response_not_completed_404(self, founder):
        bob_id = founder["bob_id"]
        r = requests.get(f"{API}/reactivation/board-members/{bob_id}/response",
                         headers=founder["headers"])
        assert r.status_code == 404

    def test_roster_progress_reflects_completion(self, founder):
        r = requests.get(f"{API}/reactivation/roster", headers=founder["headers"]).json()
        assert r["progress"]["completed"] == 1
        assert r["progress"]["total"] == 2


# =========== ADMIN OVERVIEW ===========

class TestAdminOverview:
    def test_admin_overview_success(self, founder):
        s = requests.Session()
        login = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
        assert login.status_code == 200, login.text
        r = s.get(f"{API}/admin/reactivation/overview")
        assert r.status_code == 200, r.text
        rows = r.json()["customers"]
        assert any(row["user_id"] == founder["user_id"] for row in rows)
        row = next(row for row in rows if row["user_id"] == founder["user_id"])
        assert row["organization"] == "TESTBatch2 Nonprofit"
        assert row["board_members"] >= 2
        assert row["forms_sent"] >= 1
        assert row["forms_completed"] >= 1
        # No raw response content
        assert "response" not in row


# =========== REGRESSION (Batch 1) ===========

class TestBatch1Regression:
    def test_reactivate_short_lead(self):
        r = requests.post(f"{API}/funnel-leads/reactivation", json={
            "name": "TEST Regress", "email": f"test_regress_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "555-0000", "organization": "TEST Org",
            "answers": {"disengaged_count": "3"},
        })
        assert r.status_code in (200, 201), r.text

    def test_reactivation_diy_checkout(self):
        r = requests.post(f"{API}/payments/reactivation-diy-checkout",
                          json={"origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        assert r.json()["session_id"].startswith("cs_")

    def test_intake_context_bogus_session_404(self):
        r = requests.get(f"{API}/board-reactivation-intake/context",
                        params={"session_id": "cs_bogus_xxx"})
        assert r.status_code == 404

    def test_recruitment_workspace_endpoint_still_gated(self):
        # Recruitment endpoint should still be reachable (403 without correct entitlement is fine)
        r = requests.get(f"{API}/workspace/board-profile-link")
        assert r.status_code in (401, 403, 404), r.text
