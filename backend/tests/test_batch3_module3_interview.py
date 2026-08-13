"""Batch 3 verification — Module 3 (Select and Interview Your Applicants).

Coverage:
- External applicant endpoint (name required; CV optional at backend, required on FE)
- No auto interview_guide task on public application submission
- Generate: interview_invitation, before_interview_rejection, interview_guide,
  after_interview_thank_you (4 Claude calls) with schema/content guards
- send-material side effects (status transitions + emails_sent timestamps)
- Interview completion PATCH
- PATCH candidate_email persistence
- APPLICATION_STATUSES includes new statuses
- SENDABLE_TYPES gates the new sendable types

Budget: 4 Claude calls (invitation, rejection, guide, thank-you).
"""
import io
import json
import os
import time
import uuid

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
MONGO = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
DB = MONGO[os.environ.get("DB_NAME", "test_database")]

ORG_NAME = "Harbor Youth Alliance"
MISSION = (
    "Harbor Youth Alliance provides mentorship, job-readiness training, and college "
    "counseling to first-generation youth in coastal communities."
)
PROFILE_DATA = {
    "organization_name": ORG_NAME,
    "mission": MISSION,
    "board_kind": "Governing Board",
    "present_board": "4",
    "active_board": "3",
    "new_members_count": "3",
    "desired_board_skills": ["Fundraising", "Finance", "Marketing"],
    "current_board_strengths": "program experience",
    "priorities": "grow fundraising",
}
STRATEGY_INTAKE = {"meeting_frequency": "Monthly", "meeting_format": "Virtual",
                   "time_expectation": "4-6 hours per month"}


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture(scope="session")
def member():
    email = f"TEST_batch3_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    r = requests.post(f"{API}/members/register", json={
        "email": email, "password": password, "confirm_password": password,
        "first_name": "Batch3", "last_name": "Tester",
    })
    assert r.status_code in (200, 201), r.text
    token = r.json().get("token") or r.json().get("access_token")
    doc = DB.members.find_one({"email": email.lower()})
    user_id = doc["user_id"]
    DB.members.update_one({"user_id": user_id}, {"$set": {"entitlements": ["recruitment_self_guided"]}})
    DB.recruitment_profiles.update_one(
        {"user_id": user_id},
        {"$set": {"data": PROFILE_DATA.copy(), "strategy_intake": STRATEGY_INTAKE.copy(),
                  "confirmed": True, "recruitment_profile_confirmed": True,
                  "confirmed_at": _now(), "updated_at": _now()}},
        upsert=True)
    ctx = {"email": email, "password": password, "token": token, "user_id": user_id}
    print(f"\n[FIXTURE] Batch3 member: {email} / {password}")
    yield ctx
    # cleanup
    DB.members.delete_one({"user_id": user_id})
    DB.recruitment_profiles.delete_one({"user_id": user_id})
    DB.opportunities.delete_many({"user_id": user_id})
    DB.generated_materials.delete_many({"user_id": user_id})
    DB.opportunity_applications.delete_many({"owner_user_id": user_id})


@pytest.fixture(scope="session")
def other_member():
    email = f"TEST_batch3_other_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    r = requests.post(f"{API}/members/register", json={
        "email": email, "password": password, "confirm_password": password,
        "first_name": "Other", "last_name": "Member"})
    assert r.status_code in (200, 201), r.text
    token = r.json().get("token") or r.json().get("access_token")
    doc = DB.members.find_one({"email": email.lower()})
    DB.members.update_one({"user_id": doc["user_id"]}, {"$set": {"entitlements": ["recruitment_self_guided"]}})
    DB.recruitment_profiles.update_one(
        {"user_id": doc["user_id"]},
        {"$set": {"data": {"organization_name": "Other Org", "mission": "other mission",
                           "new_members_count": "2"}, "confirmed": True,
                  "recruitment_profile_confirmed": True}}, upsert=True)
    ctx = {"email": email, "token": token, "user_id": doc["user_id"]}
    yield ctx
    DB.members.delete_one({"user_id": doc["user_id"]})
    DB.recruitment_profiles.delete_one({"user_id": doc["user_id"]})
    DB.opportunities.delete_many({"user_id": doc["user_id"]})
    DB.opportunity_applications.delete_many({"owner_user_id": doc["user_id"]})


@pytest.fixture(scope="session")
def opportunity(member):
    r = requests.get(f"{API}/workspace/opportunity", headers=auth(member["token"]))
    assert r.status_code == 200, r.text
    opp = r.json()["opportunity"]
    # Mark as Published directly to allow the public apply route (avoids 5 Claude calls)
    DB.opportunities.update_one({"user_id": member["user_id"]},
                                {"$set": {"status": "Published", "broadcast_initiated": True,
                                          "broadcast_status": "Initiated", "published_at": _now()}})
    return DB.opportunities.find_one({"user_id": member["user_id"]}, {"_id": 0})


HOSTED_ANSWERS = {
    "full_name": "Maria Alvarez", "email": "maria.alvarez+batch3@example.com",
    "phone": "555-0100", "city": "Boston", "state_region": "MA", "country": "USA",
    "profession": "Development Director", "employer": "Coastal Nonprofit Coalition",
    "linkedin": "https://linkedin.com/in/maria-alvarez",
    "board_experience": "Served two years on the finance committee of a youth arts nonprofit.",
    "why_interested": "Harbor Youth Alliance's mission around mentorship and college readiness aligns with the work I have been doing for a decade.",
    "skills_experience": "Major-donor fundraising, grant writing, event strategy, and campaign leadership.",
    "fundraising_support": "Individual giving events, board give/get, and major-donor cultivation.",
    "relationships": "Corporate partners, family foundations, and local independent schools.",
    "monthly_time": "6-8 hours per month",
    "attend_meetings": "Yes", "accept_responsibility": "Yes",
    "causes": "Youth mentorship and educational equity.",
}


@pytest.fixture(scope="session")
def hosted_application(member, opportunity):
    """Submit a public application to create a hosted applicant. Verifies no auto guide."""
    slug = opportunity["slug"]
    # Minimal valid PDF that includes candidate CV text (public apply requires PDF/DOC/DOCX)
    cv_text = (
        "Maria Alvarez - Development Director - Coastal Nonprofit Coalition. "
        "Email: maria.alvarez+batch3@example.com. Ten years leading development teams "
        "and building major-donor programs at youth-serving nonprofits. Board finance "
        "committee 2018-2020. Skills: fundraising strategy, grant writing, campaign leadership."
    )
    from reportlab.pdfgen import canvas as _canvas
    _buf = io.BytesIO()
    c = _canvas.Canvas(_buf)
    y = 800
    for line in [cv_text[i:i+90] for i in range(0, len(cv_text), 90)]:
        c.drawString(50, y, line)
        y -= 15
    c.save()
    cv_content = _buf.getvalue()
    files = {"cv": ("maria_cv.pdf", cv_content, "application/pdf")}
    data = {"payload": json.dumps(HOSTED_ANSWERS)}
    INTERNAL = os.environ.get("INTERNAL_BACKEND_URL", "http://127.0.0.1:8001")
    r = requests.post(f"{INTERNAL}/api/public/board-opportunities/{slug}/apply", data=data, files=files, timeout=120)
    assert r.status_code == 201, r.text
    application_id = r.json()["application_id"]
    # brief wait in case there were any background tasks (there shouldn't be, per spec)
    time.sleep(2)
    return DB.opportunity_applications.find_one({"application_id": application_id}, {"_id": 0})


@pytest.fixture(scope="session")
def external_application(member):
    """Add external applicant via workspace endpoint. CV text contains an email."""
    cv_content = (
        "Jordan Rivera\nAttorney at Rivera Law Group\n"
        "Contact: jordan.rivera+batch3@example.com\n"
        "Governance experience with three nonprofits. Interest in youth education."
    ).encode()
    r = requests.post(f"{API}/workspace/applications/external",
                      headers=auth(member["token"]),
                      data={"name": "Jordan Rivera"},
                      files={"cv": ("jordan_cv.txt", cv_content, "text/plain")}, timeout=30)
    assert r.status_code == 201, r.text
    application_id = r.json()["application_id"]
    return DB.opportunity_applications.find_one({"application_id": application_id}, {"_id": 0})


# ---------- External applicant behavior ----------
class TestExternalApplicant:
    def test_external_requires_name(self, member):
        r = requests.post(f"{API}/workspace/applications/external",
                          headers=auth(member["token"]),
                          data={}, files={})
        assert r.status_code == 422, r.text

    def test_external_created_appears_in_list(self, member, external_application):
        r = requests.get(f"{API}/workspace/applications", headers=auth(member["token"]))
        assert r.status_code == 200
        applications = r.json()["applications"]
        found = [a for a in applications if a["application_id"] == external_application["application_id"]]
        assert found, "external applicant not in /applications list"
        app = found[0]
        assert app["source"] == "LinkedIn / External"
        assert app["profile_snapshot"]["full_name"] == "Jordan Rivera"

    def test_external_no_duplicate_records(self, member, external_application):
        cnt = DB.opportunity_applications.count_documents({
            "owner_user_id": member["user_id"],
            "profile_snapshot.full_name": "Jordan Rivera"})
        assert cnt == 1


# ---------- No auto interview_guide on submission ----------
class TestNoAutoInterviewGuide:
    def test_hosted_application_has_no_generated_guide(self, member, hosted_application):
        # interview_guide subdoc should be Pending (never triggered)
        assert hosted_application.get("interview_guide", {}).get("status") == "Pending"
        # No generated_materials entry of type interview_guide for this application
        mat = DB.generated_materials.find_one({
            "user_id": member["user_id"], "type": "interview_guide",
            "application_id": hosted_application["application_id"]})
        assert mat is None, "auto interview_guide material was created — auto AI task should be removed"

    def test_hosted_application_status_applied(self, hosted_application):
        assert hosted_application["status"] == "Applied"


# ---------- APPLICATION_STATUSES contains new values ----------
class TestApplicationStatuses:
    def test_new_statuses_present(self, member):
        r = requests.get(f"{API}/workspace/applications", headers=auth(member["token"]))
        assert r.status_code == 200
        statuses = r.json()["statuses"]
        assert "Interview Invited" in statuses
        assert "Not Moving to Interview" in statuses


# ---------- Interview Invitation (1 Claude call) ----------
@pytest.fixture(scope="session")
def invitation_material(member, hosted_application):
    INTERNAL = os.environ.get("INTERNAL_BACKEND_URL", "http://127.0.0.1:8001")
    r = requests.post(f"{INTERNAL}/api/workspace/generate", headers=auth(member["token"]),
                      json={"type": "interview_invitation",
                            "application_id": hosted_application["application_id"]}, timeout=300)
    assert r.status_code == 200, r.text[:500]
    return r.json()


class TestInterviewInvitation:
    def test_subject_and_body(self, invitation_material):
        current = next(v for v in invitation_material["versions"]
                       if v["version"] == invitation_material["current_version"])
        structured = current["structured"] or {}
        subject = structured.get("subject", "")
        body = structured.get("body", "")
        assert "Interview Invitation" in subject, f"subject={subject!r}"
        assert "Board Member Application" in subject
        assert ORG_NAME in subject, f"subject missing org: {subject!r}"
        assert "Maria" in body, "invitation should address candidate by first name"
        # No unresolved placeholders / scheduling stubs
        for forbidden in ["[Calendly Link]", "[Scheduling Link]", "TBD",
                          "[APPLICANT NAME]", "[Organization Name]"]:
            assert forbidden not in body, f"body still contains {forbidden!r}"
        # Should not claim selection to the board
        low = body.lower()
        assert "selected for the board" not in low
        assert "welcome to the board" not in low
        assert "conditional appointment" not in low

    def test_send_transitions_status(self, member, hosted_application, invitation_material):
        r = requests.post(f"{API}/workspace/send-material", headers=auth(member["token"]),
                          json={"type": "interview_invitation",
                                "application_id": hosted_application["application_id"]}, timeout=60)
        # Resend infra may fail (502) in preview — accept both
        assert r.status_code in (200, 502), r.text
        if r.status_code == 200:
            app = DB.opportunity_applications.find_one({"application_id": hosted_application["application_id"]})
            assert app["status"] == "Interview Invited", f"status={app['status']}"
            assert app.get("emails_sent", {}).get("interview_invitation"), "timestamp not recorded"


# ---------- Before-Interview Rejection (1 Claude call, on external applicant) ----------
@pytest.fixture(scope="session")
def rejection_material(member, external_application):
    # Persist an email for the external applicant via PATCH candidate_email (extracted from CV in real flow;
    # here we exercise the PATCH endpoint explicitly).
    r0 = requests.patch(f"{API}/workspace/applications/{external_application['application_id']}",
                       headers=auth(member["token"]),
                       json={"candidate_email": "jordan.rivera+batch3@example.com"})
    assert r0.status_code == 200, r0.text
    assert r0.json()["applicant_email"] == "jordan.rivera+batch3@example.com"

    r = requests.post(f"{os.environ.get('INTERNAL_BACKEND_URL', 'http://127.0.0.1:8001')}/api/workspace/generate", headers=auth(member["token"]),
                      json={"type": "before_interview_rejection",
                            "application_id": external_application["application_id"]}, timeout=300)
    assert r.status_code == 200, r.text
    return r.json()


class TestBeforeInterviewRejection:
    def test_body_respectful_no_invented_reasons(self, rejection_material):
        current = next(v for v in rejection_material["versions"]
                       if v["version"] == rejection_material["current_version"])
        body = (current["structured"] or {}).get("body", "")
        assert body
        low = body.lower()
        for phrase in ["not qualified", "lack experience", "you are not a fit",
                       "not a good fit", "another candidate is better"]:
            assert phrase not in low, f"rejection body should not contain {phrase!r}"
        assert "Jordan" in body, "rejection should address by first name"

    def test_send_transitions_status(self, member, external_application, rejection_material):
        r = requests.post(f"{API}/workspace/send-material", headers=auth(member["token"]),
                          json={"type": "before_interview_rejection",
                                "application_id": external_application["application_id"]}, timeout=60)
        assert r.status_code in (200, 502), r.text
        # Whether email delivery succeeds or fails, per spec the status ONLY changes on successful send.
        if r.status_code == 200:
            app = DB.opportunity_applications.find_one({"application_id": external_application["application_id"]})
            assert app["status"] == "Not Moving to Interview"
            # Record still present
            assert app is not None

    def test_record_not_deleted(self, external_application):
        app = DB.opportunity_applications.find_one({"application_id": external_application["application_id"]})
        assert app is not None


# ---------- Interview Guide (1 Claude call) ----------
@pytest.fixture(scope="session")
def guide_material(member, hosted_application):
    # Interview-guide generation takes >60s and can hit the Cloudflare 502 timeout on the public URL.
    # Bypass by hitting the internal backend directly, then verify via public URL fetch.
    INTERNAL = os.environ.get("INTERNAL_BACKEND_URL", "http://127.0.0.1:8001")
    r = requests.post(f"{INTERNAL}/api/workspace/generate", headers=auth(member["token"]),
                      json={"type": "interview_guide",
                            "application_id": hosted_application["application_id"]}, timeout=300)
    assert r.status_code == 200, r.text[:500]
    return r.json()


class TestInterviewGuide:
    def test_schema_and_content(self, guide_material):
        current = next(v for v in guide_material["versions"]
                       if v["version"] == guide_material["current_version"])
        structured = current["structured"] or {}
        # required top-level keys
        for key in ["header", "purpose_of_the_interview", "candidate_snapshot",
                    "welcome_and_introductions", "introduce_the_organization",
                    "learn_about_this_candidate", "mission_alignment",
                    "contribution_to_the_board", "commitment_and_participation",
                    "collaboration_and_accountability", "candidate_questions", "closing"]:
            assert key in structured, f"missing key {key}"
        # 4-6 evaluation questions in purpose
        eq = structured["purpose_of_the_interview"].get("evaluation_questions", [])
        assert isinstance(eq, list) and 4 <= len(eq) <= 6, f"evaluation_questions len={len(eq)}"
        # question blocks have why_this_question_matters / listen_for
        for block_key in ["learn_about_this_candidate", "mission_alignment",
                          "contribution_to_the_board", "commitment_and_participation",
                          "collaboration_and_accountability"]:
            block = structured.get(block_key)
            assert isinstance(block, list) and block, f"{block_key} empty"
            for item in block:
                assert item.get("question"), f"{block_key} missing question"
                assert item.get("why_this_question_matters"), f"{block_key} missing why"
                assert isinstance(item.get("listen_for"), list) and item["listen_for"], f"{block_key} missing listen_for"
        # header candidate name
        header = structured.get("header", {})
        assert "Maria" in header.get("candidate", ""), f"header candidate={header.get('candidate')!r}"
        # display_text has no scoring language
        text = current["display_text"].lower()
        for forbidden in ["fit score", "pass/fail", "hire", "do not hire",
                          "recommended:", "not recommended"]:
            assert forbidden not in text, f"guide contains forbidden token: {forbidden!r}"

    def test_edit_and_approve(self, member, guide_material):
        material_id = guide_material["material_id"]
        edited = "MANUAL EDIT SENTINEL " + uuid.uuid4().hex[:6]
        r = requests.put(f"{API}/workspace/materials/{material_id}",
                         headers=auth(member["token"]),
                         json={"display_text": edited})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "Edited"
        r2 = requests.get(f"{API}/workspace/materials/{material_id}", headers=auth(member["token"]))
        cur = next(v for v in r2.json()["versions"] if v["version"] == r2.json()["current_version"])
        assert cur["display_text"] == edited
        r3 = requests.post(f"{API}/workspace/materials/{material_id}/approve",
                           headers=auth(member["token"]))
        assert r3.status_code == 200
        assert r3.json()["status"] == "Approved"


# ---------- Interview Completion ----------
class TestInterviewCompletion:
    def test_patch_interview_completed(self, member, hosted_application):
        r = requests.patch(f"{API}/workspace/applications/{hosted_application['application_id']}",
                           headers=auth(member["token"]),
                           json={"interview_completed": True})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["interview_completed"] is True
        assert body.get("interview_completed_at")


# ---------- After-Interview Thank-You (1 Claude call) ----------
@pytest.fixture(scope="session")
def thankyou_material(member, hosted_application):
    # Must be after interview completion PATCH — TestInterviewCompletion runs first (module order).
    # ensure interview_completed set:
    DB.opportunity_applications.update_one({"application_id": hosted_application["application_id"]},
                                           {"$set": {"interview_completed": True,
                                                     "interview_completed_at": _now()}})
    r = requests.post(f"{os.environ.get('INTERNAL_BACKEND_URL', 'http://127.0.0.1:8001')}/api/workspace/generate", headers=auth(member["token"]),
                      json={"type": "after_interview_thank_you",
                            "application_id": hosted_application["application_id"]}, timeout=300)
    assert r.status_code == 200, r.text
    return r.json()


class TestAfterInterviewThankYou:
    def test_decision_neutral(self, thankyou_material):
        current = next(v for v in thankyou_material["versions"]
                       if v["version"] == thankyou_material["current_version"])
        structured = current["structured"] or {}
        body = structured.get("body", "")
        assert body
        low = body.lower()
        for forbidden in ["unfortunately", "we have decided", "congratulations",
                          "welcome to the board", "conditional appointment"]:
            assert forbidden not in low, f"thank-you body contains {forbidden!r}"
        assert "Maria" in body, "thank-you should address by first name"

    def test_send_does_not_change_status(self, member, hosted_application, thankyou_material):
        # Set status to a post-interview state before sending
        DB.opportunity_applications.update_one(
            {"application_id": hosted_application["application_id"]},
            {"$set": {"status": "Interview Invited", "interview_completed": True}})
        r = requests.post(f"{API}/workspace/send-material", headers=auth(member["token"]),
                          json={"type": "after_interview_thank_you",
                                "application_id": hosted_application["application_id"]}, timeout=60)
        assert r.status_code in (200, 502), r.text
        if r.status_code == 200:
            app = DB.opportunity_applications.find_one({"application_id": hosted_application["application_id"]})
            # After-Interview Thank-You must not change status away from post-interview state
            assert app["status"] == "Interview Invited", f"status changed to {app['status']}"
            assert app.get("emails_sent", {}).get("after_interview_thank_you")


# ---------- SENDABLE_TYPES coverage ----------
class TestSendableTypes:
    def test_unknown_sendable_type_422(self, member, hosted_application):
        r = requests.post(f"{API}/workspace/send-material", headers=auth(member["token"]),
                          json={"type": "not_a_sendable_type",
                                "application_id": hosted_application["application_id"]})
        assert r.status_code == 422

    def test_sendable_missing_email_422(self, member):
        # Create a fresh external applicant with NO email, try to send interview_invitation
        r = requests.post(f"{API}/workspace/applications/external",
                          headers=auth(member["token"]),
                          data={"name": "No Email Applicant"},
                          files={"cv": ("cv.txt", b"no email in this cv", "text/plain")})
        assert r.status_code == 201
        aid = r.json()["application_id"]
        # Try to send without an email set
        # (Need a saved material — 422 for missing email is checked before material lookup)
        r2 = requests.post(f"{API}/workspace/send-material", headers=auth(member["token"]),
                           json={"type": "interview_invitation", "application_id": aid})
        assert r2.status_code == 422
        assert "email" in r2.text.lower()
        DB.opportunity_applications.delete_one({"application_id": aid})


# ---------- Tenant isolation ----------
class TestTenantIsolation:
    def test_other_member_sees_no_applications(self, other_member, hosted_application):
        r = requests.get(f"{API}/workspace/applications", headers=auth(other_member["token"]))
        assert r.status_code == 200
        for a in r.json()["applications"]:
            assert a["owner_user_id"] == other_member["user_id"]

    def test_other_member_cannot_read_application(self, other_member, hosted_application):
        r = requests.get(f"{API}/workspace/applications/{hosted_application['application_id']}",
                         headers=auth(other_member["token"]))
        assert r.status_code == 404


# ---------- Regression: Modules unchanged ----------
class TestRegression:
    def test_courses_still_5_modules(self, member):
        r = requests.get(f"{API}/courses/recruitment/self-guided", headers=auth(member["token"]))
        assert r.status_code == 200
        assert len(r.json()["modules"]) == 5
