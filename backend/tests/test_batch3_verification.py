"""Batch 3 correction verification.

Covers:
- Strategy intake persistence (Board Recruitment Details fields).
- GET /api/workspace/strategy-pdf (reportlab) using seeded structured strategy.
- Public opportunity view: intro_sentences composition, no legacy fields.
- POST /api/workspace/applications/{id}/decision (move_forward / do_not_move_forward)
  including idempotency, agreement-approval gating, no emails sent.
- GET/POST /api/public/sign/{token}: typed + drawn methods, drawn requires signature_image,
  immutability of the signed snapshot, second-sign 409, cross-token isolation.
- App SPA route /app/recruitment/self-guided/results returns 200 HTML.

Seeds data directly in Mongo — no live Claude, no emails to real recipients.
"""
import os
import secrets
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://portfolio-dashboard-67.preview.emergentagent.com"
API = f"{BASE_URL}/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

STRATEGY_STRUCTURED = {
    "executive_summary": "We are recruiting three professionals through our personal network and a limited public LinkedIn presence. Recruitment begins immediately.",
    "roles": [{"role_name": "Fundraising Leader", "person_sought": "A development professional with major-donor experience."},
              {"role_name": "Governance Expert", "person_sought": "An attorney or seasoned nonprofit director."}],
    "channels": [{"channel": "Personal Network", "approach": "Reach out to five known professionals within the first week."},
                 {"channel": "Public Outreach", "approach": "Post the LinkedIn job listing and share the opportunity in one professional association."}],
    "selection_criteria": ["Mission alignment", "Board-role relevant skills", "Willingness and capacity to serve"],
}


@pytest.fixture(scope="session")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="session")
def seeded(db):
    """Create a fresh $497 test member with confirmed profile + published opportunity + seeded strategy material.
    Cleans up after the session."""
    email = f"rooney+batch3-{uuid.uuid4().hex[:8]}@nonprofitboardbuilder.com"
    password = os.environ["TEST_ACCOUNT_PASSWORD"]
    session = requests.Session()
    resp = session.post(f"{API}/members/register", json={
        "first_name": "Batch3", "last_name": "Tester",
        "email": email, "password": password, "confirm_password": password,
    })
    assert resp.status_code == 201, resp.text
    member = resp.json()["member"]
    user_id = member["user_id"]
    token = resp.json()["token"]

    db.members.update_one({"user_id": user_id}, {"$addToSet": {"entitlements": "recruitment_self_guided"}})
    ts = datetime.now(timezone.utc).isoformat()
    db.recruitment_profiles.update_one({"user_id": user_id}, {"$set": {
        "user_id": user_id,
        "data": {"organization_name": "Batch3 Test Nonprofit", "mission": "empower young people through mentorship", "board_kind": "Board of Directors"},
        "confirmed": True, "recruitment_profile_confirmed": True, "confirmed_at": ts, "updated_at": ts, "created_at": ts,
    }}, upsert=True)

    # Seed recruitment_strategy material
    material_id = uuid.uuid4().hex
    db.generated_materials.insert_one({
        "material_id": material_id, "user_id": user_id, "type": "recruitment_strategy", "application_id": "",
        "status": "Approved", "current_version": 1,
        "versions": [{"version": 1, "structured": STRATEGY_STRUCTURED,
                      "display_text": "BOARD RECRUITMENT STRATEGY\n\nEXECUTIVE SUMMARY\n" + STRATEGY_STRUCTURED["executive_summary"],
                      "source": "test-seed", "input_context_summary": "seed", "created_at": ts}],
        "created_at": ts, "updated_at": ts,
    })

    # Create + publish an opportunity for public view test
    opp_id = uuid.uuid4().hex
    slug = f"batch3-nonprofit-{uuid.uuid4().hex[:6]}"
    db.opportunities.insert_one({
        "opportunity_id": opp_id, "user_id": user_id, "slug": slug,
        "organization_name": "Batch3 Test Nonprofit", "status": "Published",
        "custom_questions": [], "application_saved": True, "email_content": {}, "broadcast_initiated": True,
        "broadcast_id": "test", "broadcast_status": "Initiated", "broadcast_mode": "test",
        "created_at": ts, "updated_at": ts, "published_at": ts,
    })
    # Seed a board_opportunity material (Approved)
    db.generated_materials.insert_one({
        "material_id": uuid.uuid4().hex, "user_id": user_id, "type": "board_opportunity", "application_id": "",
        "status": "Approved", "current_version": 1,
        "versions": [{"version": 1, "structured": {"title": "Board Opportunity", "introduction": "intro", "how_to_apply": f"Apply at {BASE_URL}/board-opportunities/{slug}/apply"},
                      "display_text": "BOARD OPPORTUNITY", "source": "seed", "input_context_summary": "seed", "created_at": ts}],
        "created_at": ts, "updated_at": ts,
    })

    # Seed an applicant + application in Applied status
    application_id = uuid.uuid4().hex
    db.opportunity_applications.insert_one({
        "application_id": application_id, "opportunity_id": opp_id, "owner_user_id": user_id,
        "source": "Public Application", "applicant_email": "rooney+batch3-applicant@nonprofitboardbuilder.com",
        "profile_snapshot": {"full_name": "Test Applicant", "email": "rooney+batch3-applicant@nonprofitboardbuilder.com", "profession": "Attorney", "employer": "Law Firm"},
        "answers": {}, "status": "Applied", "interview_completed": True,
        "references": [], "background_check": {"status": "Not started"}, "emails_sent": {},
        "created_at": ts, "updated_at": ts,
    })

    ctx = {
        "email": email, "password": password, "token": token, "user_id": user_id,
        "material_id": material_id, "opp_id": opp_id, "slug": slug, "application_id": application_id,
        "auth_headers": {"Authorization": f"Bearer {token}"},
    }
    yield ctx

    # Cleanup
    db.members.delete_one({"user_id": user_id})
    db.recruitment_profiles.delete_many({"user_id": user_id})
    db.generated_materials.delete_many({"user_id": user_id})
    db.opportunities.delete_many({"user_id": user_id})
    db.opportunity_applications.delete_many({"owner_user_id": user_id})
    db.signature_requests.delete_many({"owner_user_id": user_id})
    db.reference_processes.delete_many({"owner_user_id": user_id})
    db.board_profile_links.delete_many({"user_id": user_id})


# ---------------- Strategy intake persistence ----------------
def test_strategy_intake_persistence(seeded):
    headers = seeded["auth_headers"]
    intake = {
        "know_people": "No", "reach_channels": [], "referral_network": "Yes",
        "recruit_outside": "Yes", "public_channels": ["LinkedIn"],
        "meeting_frequency": "Monthly", "meeting_frequency_other": "",
        "board_term": "2 Years", "board_term_other": "",
        "max_board_size": "9", "max_board_size_unknown": False,
        "meeting_format": "Hybrid", "meeting_location": "Delaware",
        "time_expectation": "4-6 hours per month",
        "application_deadline": "Specific Date", "deadline_date": "2026-03-31",
    }
    r = requests.put(f"{API}/workspace/strategy-intake", json={"data": intake}, headers=headers)
    assert r.status_code == 200, r.text
    # Verify via GET /workspace/profile
    r = requests.get(f"{API}/workspace/profile", headers=headers)
    assert r.status_code == 200
    saved = r.json()["strategy_intake"]
    for k, v in intake.items():
        assert saved.get(k) == v, f"intake field {k} not persisted"


# ---------------- Strategy PDF ----------------
def test_strategy_pdf_download(seeded):
    r = requests.get(f"{API}/workspace/strategy-pdf", headers=seeded["auth_headers"])
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    body = r.content
    assert body[:4] == b"%PDF", "response is not a valid PDF"
    try:
        from pypdf import PdfReader
    except ImportError:
        pytest.skip("pypdf not installed")
    import io as _io
    reader = PdfReader(_io.BytesIO(body))
    assert len(reader.pages) >= 1
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    # Sections
    assert "Board Recruitment Strategy" in text
    assert "Executive Summary" in text
    assert "Recruitment Channels" in text or "RECRUITMENT CHANNELS" in text.upper()
    assert "Selection Criteria" in text or "SELECTION CRITERIA" in text.upper()
    assert "Recruitment Timeline" in text or "TIMELINE" in text.upper()
    assert "DAY 1" in text.upper()
    assert "WITHIN 48 HOURS" in text.upper()
    # STEP names (locked)
    for expected in ["BUILD YOUR RECRUITMENT STRATEGY", "LAUNCH YOUR RECRUITMENT CAMPAIGN", "INTERVIEW YOUR APPLICANTS",
                     "COMPLETE REFERENCES AND BACKGROUND CHECKS", "ONBOARD YOUR NEW BOARD MEMBERS"]:
        assert expected in text.upper(), f"missing locked step name: {expected}"
    # Footer with org
    assert "Batch3 Test Nonprofit" in text
    # No app route URLs (e.g., /app/recruitment). Allow apply URL if present since it's a real page.
    assert "/app/recruitment" not in text


# ---------------- Public opportunity view ----------------
def test_public_opportunity_view_intro_sentences(seeded):
    r = requests.get(f"{API}/public/board-opportunities/{seeded['slug']}")
    assert r.status_code == 200, r.text
    data = r.json()
    intro = data.get("intro_sentences") or []
    assert isinstance(intro, list) and 2 <= len(intro) <= 4
    joined = " ".join(intro)
    assert "Batch3 Test Nonprofit" in joined
    assert "Board of Directors" in joined
    assert "empower young people through mentorship" in joined
    assert "Complete the application below" in joined
    # Absence checks (should not leak legacy fields into intro)
    assert "The Board Opportunity" not in joined
    assert "[Organization Name]" not in joined
    assert "Information to Add" not in joined


# ---------------- Candidate decision endpoint ----------------
def test_decision_do_not_move_forward(seeded, db):
    r = requests.post(f"{API}/workspace/applications/{seeded['application_id']}/decision",
                      json={"decision": "do_not_move_forward"}, headers=seeded["auth_headers"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "Not Moving Forward"
    app = db.opportunity_applications.find_one({"application_id": seeded["application_id"]})
    assert app["status"] == "Not Moving Forward"
    # No emails sent
    assert not (app.get("emails_sent") or {})


def test_decision_move_forward_idempotent_and_agreement_gating(seeded, db):
    # Reset status so we can test move_forward
    db.opportunity_applications.update_one({"application_id": seeded["application_id"]}, {"$set": {"status": "Applied"}})
    db.signature_requests.delete_many({"application_id": seeded["application_id"]})
    db.reference_processes.delete_many({"application_id": seeded["application_id"]})
    db.board_profile_links.delete_many({"application_id": seeded["application_id"]})

    r = requests.post(f"{API}/workspace/applications/{seeded['application_id']}/decision",
                      json={"decision": "move_forward"}, headers=seeded["auth_headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "Moving Forward"
    prepared = body.get("prepared", {})
    assert prepared.get("reference_form") == "Ready"
    assert prepared.get("board_member_profile") == "Ready"
    # No agreements approved -> should be "Agreement not approved yet"
    for at in ["board_member_agreement", "confidentiality_agreement", "conflict_of_interest_agreement"]:
        assert prepared.get(at) == "Agreement not approved yet", f"{at}: {prepared.get(at)}"

    # Reference process created
    assert db.reference_processes.count_documents({"application_id": seeded["application_id"]}) == 1
    # Board profile link created
    assert db.board_profile_links.count_documents({"application_id": seeded["application_id"]}) == 1
    # No signature_requests yet
    assert db.signature_requests.count_documents({"application_id": seeded["application_id"]}) == 0

    # Approve one agreement, retry - should create ONE signature_request only
    ts = datetime.now(timezone.utc).isoformat()
    db.generated_materials.insert_one({
        "material_id": uuid.uuid4().hex, "user_id": seeded["user_id"], "type": "board_member_agreement", "application_id": "",
        "status": "Approved", "current_version": 1,
        "versions": [{"version": 1, "structured": {"title": "Agreement", "sections": []},
                      "display_text": "BOARD MEMBER AGREEMENT\n\nTerms follow.", "source": "seed", "input_context_summary": "seed", "created_at": ts}],
        "created_at": ts, "updated_at": ts,
    })
    r2 = requests.post(f"{API}/workspace/applications/{seeded['application_id']}/decision",
                       json={"decision": "move_forward"}, headers=seeded["auth_headers"])
    assert r2.status_code == 200
    assert r2.json()["prepared"].get("board_member_agreement") == "Ready for Signature"
    # Idempotent: only one signature_request for this agreement
    assert db.signature_requests.count_documents({"application_id": seeded["application_id"], "agreement_type": "board_member_agreement"}) == 1
    # Idempotent: only one reference process, one profile link
    assert db.reference_processes.count_documents({"application_id": seeded["application_id"]}) == 1
    assert db.board_profile_links.count_documents({"application_id": seeded["application_id"]}) == 1

    # No duplicate applicant
    assert db.opportunity_applications.count_documents({"application_id": seeded["application_id"]}) == 1


def test_decision_bad_payload(seeded):
    r = requests.post(f"{API}/workspace/applications/{seeded['application_id']}/decision",
                      json={"decision": "maybe"}, headers=seeded["auth_headers"])
    assert r.status_code == 422


# ---------------- Public signature flow ----------------
@pytest.fixture(scope="module")
def signature_token(seeded, db):
    """Ensure a signature_request exists for the seeded application (from prior test seeded agreement)."""
    ts = datetime.now(timezone.utc).isoformat()
    # Ensure at least one signature request seeded (independent of ordering)
    material = db.generated_materials.find_one({"user_id": seeded["user_id"], "type": "board_member_agreement"})
    if not material:
        material_id = uuid.uuid4().hex
        db.generated_materials.insert_one({
            "material_id": material_id, "user_id": seeded["user_id"], "type": "board_member_agreement",
            "application_id": "", "status": "Approved", "current_version": 1,
            "versions": [{"version": 1, "structured": {}, "display_text": "AGREEMENT", "source": "seed", "input_context_summary": "seed", "created_at": ts}],
            "created_at": ts, "updated_at": ts,
        })
        material = db.generated_materials.find_one({"user_id": seeded["user_id"], "type": "board_member_agreement"})
    existing = db.signature_requests.find_one({"application_id": seeded["application_id"], "agreement_type": "board_member_agreement"})
    if not existing:
        token = secrets.token_urlsafe(24)
        db.signature_requests.insert_one({
            "request_id": uuid.uuid4().hex, "token": token, "owner_user_id": seeded["user_id"],
            "application_id": seeded["application_id"], "agreement_type": "board_member_agreement",
            "agreement_title": "Board Member Agreement", "material_id": material["material_id"],
            "agreement_version": 1, "document_snapshot": "ORIGINAL AGREEMENT SNAPSHOT VERSION 1",
            "organization_name": "Batch3 Test Nonprofit",
            "board_member_name": "Test Applicant", "board_member_email": "rooney+batch3-applicant@nonprofitboardbuilder.com",
            "status": "Ready for Signature", "created_at": ts, "updated_at": ts,
        })
    else:
        token = existing["token"]
        # Ensure it's not already Signed from a prior run
        db.signature_requests.update_one({"token": token},
            {"$set": {"status": "Ready for Signature", "document_snapshot": "ORIGINAL AGREEMENT SNAPSHOT VERSION 1"},
             "$unset": {"signed": ""}})
    return token


def test_sign_get_returns_branded_record(signature_token):
    r = requests.get(f"{API}/public/sign/{signature_token}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["organization_name"] == "Batch3 Test Nonprofit"
    assert data["agreement_title"] == "Board Member Agreement"
    assert data["document"].startswith("ORIGINAL AGREEMENT SNAPSHOT")
    assert data["status"] == "Ready for Signature"
    assert data["signed"] is False


def test_sign_drawn_requires_signature_image(signature_token):
    r = requests.post(f"{API}/public/sign/{signature_token}", json={
        "agreed": True, "typed_signature": "Test Signer",
        "email": "signer@example.com", "date": "2026-01-15",
        "signature_method": "drawn", "signature_image": "",
    })
    assert r.status_code == 422, r.text
    assert "signature" in r.text.lower() or "draw" in r.text.lower()


def test_sign_typed_and_immutability(signature_token, seeded, db):
    r = requests.post(f"{API}/public/sign/{signature_token}", json={
        "agreed": True, "typed_signature": "Test Signer",
        "email": "signer@example.com", "date": "2026-01-15",
        "signature_method": "typed",
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "Signed"
    # Second attempt -> 409
    r2 = requests.post(f"{API}/public/sign/{signature_token}", json={
        "agreed": True, "typed_signature": "Second", "email": "second@example.com", "date": "2026-01-16", "signature_method": "typed",
    })
    assert r2.status_code == 409
    # GET returns signed_record
    r3 = requests.get(f"{API}/public/sign/{signature_token}")
    assert r3.status_code == 200
    rec = r3.json().get("signed_record")
    assert rec and rec.get("name") == "Test Signer" and rec.get("method") == "typed"
    # Immutability: edit the source agreement material -> signed document_snapshot unchanged
    material = db.generated_materials.find_one({"user_id": seeded["user_id"], "type": "board_member_agreement"})
    edit_headers = seeded["auth_headers"]
    r4 = requests.put(f"{API}/workspace/materials/{material['material_id']}",
                      json={"display_text": "COMPLETELY DIFFERENT AGREEMENT TEXT"}, headers=edit_headers)
    assert r4.status_code == 200
    signed_req = db.signature_requests.find_one({"token": signature_token})
    assert signed_req["document_snapshot"].startswith("ORIGINAL AGREEMENT SNAPSHOT"), "document_snapshot must not change after signing"


def test_sign_cross_token_isolation():
    r = requests.get(f"{API}/public/sign/{secrets.token_urlsafe(24)}")
    assert r.status_code == 404


# ---------------- SPA route ----------------
def test_results_route_serves_html():
    r = requests.get(f"{BASE_URL}/app/recruitment/self-guided/results")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    # SPA — should contain a React app anchor
    assert "<div" in r.text.lower()
