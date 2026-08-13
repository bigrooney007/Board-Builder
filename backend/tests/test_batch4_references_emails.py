"""Batch 4 verification — Module 4 (Reference workflow + platform email quality).

Approach: this file talks to the RUNNING FastAPI backend over HTTP for end-to-end
behavior + verifies static content (subjects/prompts/opportunity_email_html) by
importing the modules directly. Real Resend calls target safe addresses
(delivered@resend.dev + OWNER_NOTIFICATION_EMAIL).

Coverage:
- REFEREE_QUESTIONS/RECOMMEND_QUESTION shape + candidate/org substitution
- POST /workspace/reference-process (idempotent create)
- POST /workspace/reference-process/{id}/send transitions status + subject construction
- POST /public/reference-form/{token}: saves 2 refs w/ status "Ready to Contact",
  NO auto sent_at, permission_confirmed required, founder notification triggered
- POST /public/referee-form/{token}: declaration + explanation validation,
  full submit sets Completed + response stored, both-complete -> process Completed
- GET /public/referee-form: exact 4 questions + candidate/org substitution + recommend options
- POST resend-referee returns Sent + sets DB status "Sent"
- Move Forward decision endpoint prepares reference process + signature stubs
- opportunity_email_html unit assertions
- Email audit: no user-facing [TEST MODE]/[Sandbox]/[Staging] labels
- Regression: 5 modules in course
"""
import os
import uuid

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
INTERNAL_API = os.environ.get("INTERNAL_BACKEND_URL", "http://127.0.0.1:8001") + "/api"
MONGO = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
DB = MONGO[os.environ.get("DB_NAME", "test_database")]

ORG_NAME = "Harbor Youth Alliance"
SAFE_EMAIL = "delivered@resend.dev"  # Resend accepts + drops
REFEREE_1_EMAIL = "delivered+ref1@resend.dev"
REFEREE_2_EMAIL = "delivered+ref2@resend.dev"


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def auth(t):
    return {"Authorization": f"Bearer {t}"}


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def member():
    email = f"TEST_batch4_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    r = requests.post(f"{API}/members/register", json={
        "email": email, "password": password, "confirm_password": password,
        "first_name": "Batch4", "last_name": "Tester",
    })
    assert r.status_code in (200, 201), r.text
    token = r.json().get("token") or r.json().get("access_token")
    doc = DB.members.find_one({"email": email.lower()})
    user_id = doc["user_id"]
    DB.members.update_one({"user_id": user_id}, {"$set": {"entitlements": ["recruitment_self_guided"]}})
    DB.recruitment_profiles.update_one(
        {"user_id": user_id},
        {"$set": {"data": {"organization_name": ORG_NAME, "mission": "Youth mentorship",
                           "board_kind": "Governing Board", "new_members_count": "3",
                           "desired_board_skills": ["Fundraising", "Finance"]},
                  "confirmed": True, "recruitment_profile_confirmed": True,
                  "confirmed_at": _now(), "updated_at": _now()}},
        upsert=True)
    DB.opportunities.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "organization_name": ORG_NAME,
                  "opportunity_id": f"opp-{uuid.uuid4().hex[:8]}",
                  "slug": "harbor-youth-alliance-b4", "status": "Draft",
                  "email_content": {"mission": "Youth mentorship and college readiness.",
                                     "candidate_needs": "Finance, Fundraising, Marketing",
                                     "commitment": "About 4-6 hours per month",
                                     "location": "Virtual", "deadline": "October 15"},
                  "created_at": _now(), "updated_at": _now()}}, upsert=True)
    ctx = {"email": email, "password": password, "token": token, "user_id": user_id}
    print(f"\n[FIXTURE] Batch4 member: {email} / {password}")
    yield ctx
    DB.members.delete_one({"user_id": user_id})
    DB.recruitment_profiles.delete_one({"user_id": user_id})
    DB.opportunities.delete_many({"user_id": user_id})
    DB.opportunity_applications.delete_many({"owner_user_id": user_id})
    DB.reference_processes.delete_many({"owner_user_id": user_id})
    DB.signature_requests.delete_many({"owner_user_id": user_id})
    DB.board_profile_links.delete_many({"user_id": user_id})


@pytest.fixture(scope="session")
def application(member):
    app_id = f"app-b4-{uuid.uuid4().hex[:8]}"
    doc = {
        "application_id": app_id,
        "owner_user_id": member["user_id"],
        "opportunity_id": "opp-b4",
        "source": "Hosted Application",
        "status": "Interviewed",
        "interview_completed": True,
        "applicant_email": SAFE_EMAIL,
        "profile_snapshot": {"full_name": "Maria Alvarez", "email": SAFE_EMAIL},
        "cv_text": f"Maria Alvarez {SAFE_EMAIL}",
        "created_at": _now(), "updated_at": _now(),
    }
    DB.opportunity_applications.insert_one(doc.copy())
    yield doc


# ---------- 1. Move Forward decision endpoint ----------
class TestMoveForward:
    def test_move_forward_creates_reference_process(self, member, application):
        r = requests.post(f"{API}/workspace/applications/{application['application_id']}/decision",
                          headers=auth(member["token"]),
                          json={"decision": "move_forward"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "Moving Forward"
        assert body["prepared"]["reference_form"] == "Ready"
        assert body["prepared"]["board_member_profile"] == "Ready"
        proc = DB.reference_processes.find_one({"application_id": application["application_id"]})
        assert proc is not None
        assert proc["status"] == "Not Started"
        assert proc["candidate_email"] == SAFE_EMAIL


# ---------- 2. Reference process send to candidate ----------
class TestSendCandidateForm:
    def test_send_transitions_status(self, member, application):
        # idempotent-create process
        requests.post(f"{API}/workspace/reference-process",
                      headers=auth(member["token"]),
                      json={"application_id": application["application_id"]})
        r = requests.post(f"{API}/workspace/reference-process/{application['application_id']}/send",
                          headers=auth(member["token"]),
                          json={"application_id": application["application_id"],
                                "candidate_email": SAFE_EMAIL})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "Waiting for Candidate"
        proc = DB.reference_processes.find_one({"application_id": application["application_id"]})
        assert proc["status"] == "Waiting for Candidate"
        assert proc["candidate_sent_to"] == SAFE_EMAIL

    def test_subject_string_present_in_source(self):
        """Static: subject built exactly as 'Reference Information Needed | <org> Board Application'."""
        src = open("/app/backend/refinement_routes.py", encoding="utf-8").read()
        assert 'f"Reference Information Needed | {org} Board Application"' in src


# ---------- 3. Candidate submits references (no auto-email to referees) ----------
class TestCandidateSubmitsReferences:
    def test_permission_required(self, application):
        proc = DB.reference_processes.find_one({"application_id": application["application_id"]})
        r = requests.post(f"{API}/public/reference-form/{proc['candidate_token']}",
                          json={"references": [{"name": "R One", "email": "r1@example.com"},
                                               {"name": "R Two", "email": "r2@example.com"}]})
        assert r.status_code == 422
        assert "permission" in r.json()["detail"].lower()

    def test_two_references_required(self, application):
        proc = DB.reference_processes.find_one({"application_id": application["application_id"]})
        r = requests.post(f"{API}/public/reference-form/{proc['candidate_token']}",
                          json={"permission_confirmed": True,
                                "references": [{"name": "Only One", "email": "only@example.com"}]})
        assert r.status_code == 422

    def test_submit_saves_ready_to_contact_no_auto_email(self, member, application):
        proc = DB.reference_processes.find_one({"application_id": application["application_id"]})
        payload = {
            "permission_confirmed": True,
            "references": [
                {"name": "Priya Referee", "email": REFEREE_1_EMAIL,
                 "position": "CEO", "organization": "Ref Org 1",
                 "relationship": "Former manager", "duration": "5 years"},
                {"name": "Sam Referee", "email": REFEREE_2_EMAIL,
                 "position": "Director", "organization": "Ref Org 2",
                 "relationship": "Colleague", "duration": "3 years"},
            ],
        }
        r = requests.post(f"{API}/public/reference-form/{proc['candidate_token']}", json=payload)
        assert r.status_code == 201, r.text
        proc = DB.reference_processes.find_one({"application_id": application["application_id"]})
        assert proc["status"] == "References Submitted"
        assert len(proc["references"]) == 2
        for ref in proc["references"]:
            assert ref["status"] == "Ready to Contact", \
                f"Expected 'Ready to Contact', got {ref['status']}"
            # No auto sent_at
            assert not ref.get("sent_at"), \
                f"Referee should NOT be auto-emailed: found sent_at {ref.get('sent_at')}"
        appdoc = DB.opportunity_applications.find_one({"application_id": application["application_id"]})
        assert appdoc["reference_check_status"] == "References Submitted"

    def test_founder_notification_subject_static(self):
        src = open("/app/backend/refinement_routes.py", encoding="utf-8").read()
        assert 'f"References Submitted | {candidate}"' in src
        assert 'f"Reference Received | {candidate}"' in src


# ---------- 4. Resend referee endpoint (founder-triggered) ----------
class TestResendReferee:
    def test_resend_marks_sent(self, member, application):
        proc = DB.reference_processes.find_one({"application_id": application["application_id"]})
        ref_id = proc["references"][0]["reference_id"]
        r = requests.post(
            f"{API}/workspace/reference-process/{application['application_id']}/resend-referee/{ref_id}",
            headers=auth(member["token"]))
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "Sent"
        proc2 = DB.reference_processes.find_one({"application_id": application["application_id"]})
        ref = next(x for x in proc2["references"] if x["reference_id"] == ref_id)
        assert ref["status"] == "Sent"
        assert ref.get("sent_at")
        assert proc2["status"] == "In Progress"

    def test_referee_email_subject_static(self):
        src = open("/app/backend/refinement_routes.py", encoding="utf-8").read()
        assert 'f"Reference Request | {candidate} — {org} Board Application"' in src


# ---------- 5. Referee form GET (question shape) ----------
class TestRefereeFormShape:
    def test_get_returns_four_questions_plus_recommend(self, application):
        proc = DB.reference_processes.find_one({"application_id": application["application_id"]})
        token = proc["references"][0]["referee_token"]
        r = requests.get(f"{API}/public/referee-form/{token}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["candidate_name"] == "Maria Alvarez"
        assert body["organization_name"] == ORG_NAME
        assert isinstance(body["questions"], list)
        assert len(body["questions"]) == 4, f"expected 4 questions, got {len(body['questions'])}"
        ids = [q["id"] for q in body["questions"]]
        assert set(ids) == {"capacity", "reliability", "strengths", "teamwork"}
        for q in body["questions"]:
            assert "Maria Alvarez" in q["label"], f"candidate not substituted in: {q['label']}"
            assert "{candidate}" not in q["label"]
        assert "Maria Alvarez" in body["recommend_question"]
        assert ORG_NAME in body["recommend_question"]
        assert body["recommend_options"] == ["Yes", "No", "I would need more information to say"]


# ---------- 6. Referee submits — validation ----------
class TestRefereeSubmitValidation:
    @pytest.fixture(scope="class")
    def token(self, application):
        proc = DB.reference_processes.find_one({"application_id": application["application_id"]})
        # Use ref[0] which was already 'Sent' via resend — status Sent, not Completed
        return proc["references"][0]["referee_token"]

    def _payload(self):
        return {
            "capacity": "Worked with Maria 5+ years as her manager.",
            "reliability": "Highly reliable and professional.",
            "strengths": "Strategic thinking, fundraising leadership.",
            "teamwork": "Excellent collaborator.",
            "recommend": "Yes",
            "explanation": "She would be a strong contributor.",
            "declaration_confirmed": True,
        }

    def test_missing_declaration_returns_422(self, token):
        p = self._payload(); p["declaration_confirmed"] = False
        r = requests.post(f"{API}/public/referee-form/{token}", json=p)
        assert r.status_code == 422

    def test_missing_explanation_returns_422(self, token):
        p = self._payload(); p["explanation"] = ""
        r = requests.post(f"{API}/public/referee-form/{token}", json=p)
        assert r.status_code == 422

    def test_invalid_recommend_returns_422(self, token):
        p = self._payload(); p["recommend"] = "Maybe"
        r = requests.post(f"{API}/public/referee-form/{token}", json=p)
        assert r.status_code == 422

    def test_missing_question_answer_returns_422(self, token):
        p = self._payload(); p["capacity"] = ""
        r = requests.post(f"{API}/public/referee-form/{token}", json=p)
        assert r.status_code == 422


# ---------- 7. Referee submit success + both-complete → process Completed ----------
class TestRefereeSubmitSuccess:
    def test_both_referees_complete_sets_process_completed(self, member, application):
        proc = DB.reference_processes.find_one({"application_id": application["application_id"]})
        tokens = [r["referee_token"] for r in proc["references"]]
        base = {
            "capacity": "Worked with Maria 5+ years.",
            "reliability": "Reliable and professional.",
            "strengths": "Strong fundraising and strategy.",
            "teamwork": "Collaborative and thoughtful.",
            "recommend": "Yes",
            "explanation": "Strong candidate — recommend.",
            "declaration_confirmed": True,
        }
        r = requests.post(f"{API}/public/referee-form/{tokens[0]}", json=base)
        assert r.status_code == 201, r.text
        proc = DB.reference_processes.find_one({"application_id": application["application_id"]})
        completed = [x for x in proc["references"] if x["status"] == "Completed"]
        assert len(completed) == 1
        assert completed[0]["response"]["explanation"].startswith("Strong candidate")
        assert completed[0]["response"]["recommend"] == "Yes"
        assert completed[0]["response"]["capacity"].startswith("Worked with Maria")
        assert proc["status"] != "Completed"

        r = requests.post(f"{API}/public/referee-form/{tokens[1]}", json=base)
        assert r.status_code == 201, r.text
        proc = DB.reference_processes.find_one({"application_id": application["application_id"]})
        assert proc["status"] == "Completed"
        appdoc = DB.opportunity_applications.find_one({"application_id": application["application_id"]})
        assert appdoc["reference_check_status"] == "Completed"


# ---------- 8. opportunity_email_html unit ----------
class TestOpportunityEmailHtml:
    def test_html_content_and_subject(self):
        from opportunity_emails import opportunity_email_html
        opp = {"email_content": {
            "mission": "Youth mentorship and college readiness.",
            "candidate_needs": "Finance, Fundraising, Marketing",
            "commitment": "About 4-6 hours per month",
            "location": "Virtual",
            "deadline": "October 15",
        }}
        apply_url = "https://example.org/apply/xyz-token"
        view_url = "https://example.org/board-opportunities/harbor-youth-alliance/apply"
        html_doc = opportunity_email_html(opp, ORG_NAME, apply_url, view_url, "Alex")
        assert f"Board Leadership Opportunity | {ORG_NAME}" in html_doc
        assert "I&#x27;m currently supporting" in html_doc or "I'm currently supporting" in html_doc
        assert "Youth mentorship" in html_doc
        assert "<li>Finance</li>" in html_doc
        assert "<li>Fundraising</li>" in html_doc
        assert "Apply Here" in html_doc
        assert apply_url in html_doc
        assert "Rooney Akpesiri" in html_doc
        assert "The Nonprofit Board Builder" in html_doc
        assert "[TEST MODE]" not in html_doc
        assert "[Application Link]" not in html_doc
        assert "[APPLICATION LINK]" not in html_doc
        assert "Dear Alex," in html_doc

    def test_owner_preview_prefix_used_in_source(self):
        src = open("/app/backend/opportunity_emails.py", encoding="utf-8").read()
        assert '[Owner Preview]' in src
        assert '[TEST MODE]' not in src


# ---------- 9. Email audit ----------
class TestEmailAudit:
    def test_no_test_mode_labels_in_user_emails(self):
        import pathlib
        root = pathlib.Path("/app/backend")
        banned = ["[TEST MODE]", "[Sandbox]", "[Staging]"]
        exempt_files = {"marketing_service.py", "marketing_routes.py"}
        offenders = []
        for py in root.glob("*.py"):
            if py.name in exempt_files or py.name.startswith("test_"):
                continue
            try:
                text = py.read_text(encoding="utf-8")
            except Exception:
                continue
            for label in banned:
                if label in text:
                    offenders.append((py.name, label))
        assert not offenders, f"Found banned labels: {offenders}"


# ---------- 10. Regression: 5 modules ----------
class TestModuleRegression:
    def test_course_has_five_modules(self, member):
        r = requests.get(f"{API}/courses/recruitment/self-guided", headers=auth(member["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        modules = body.get("modules") or body.get("course", {}).get("modules") or []
        assert len(modules) == 5, f"expected 5 modules, got {len(modules)}"
