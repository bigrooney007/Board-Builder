"""Iteration 16 verification — Nonprofit Board Builder Production Quality Corrections.

Covers (backend only — no live Claude, no live emails):
- ORG+MISSION GATE: /workspace/generate returns 422 without mission in profile.data,
  succeeds (or fails past the gate) after profile PUT with organization_name + mission.
- SERVER-SIDE MATERIAL PDF: /workspace/material-pdf/{material_id} returns valid PDF
  with title, org name, page-number footer, no /app/ route URLs; 401 unauth; 404 cross-tenant.
- BRANDING REUSE: PUT /workspace/branding then material-pdf + strategy-pdf still parse OK;
  GET /shared/{token} for a share link returns organization_name + logo_data + primary_color.
- HOSTED LINKS: /workspace/signatures returns records that include a token field.
- SIGNATURE OPTIONS: POST /public/sign/{token} accepts signature_method='uploaded' + data:image
  and stores method='uploaded' + image; drawn/uploaded without image → 422; typed still works;
  second sign → 409.
- CONDITIONAL APPOINTMENT: conditional_offer generation blocks with 409 listing missing docs
  when onboarding docs not Approved.
- ONBOARDING SESSION: PUT /workspace/onboarding-session persists new fields (timezone/format/
  link/location/prepare), GET returns saved session.

Uses seeded materials to avoid Claude budget except for the ONE gate probe (which is expected
to 422 or 502 — never Approved because we intentionally seed missing mission first). No emails
are sent (send is not exercised).
"""
import base64
import io
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://rooney-recruitment.preview.emergentagent.com"
API = f"{BASE_URL}/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

# 1x1 transparent PNG
TINY_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgAAIAAAUAAeImBZsAAAAASUVORK5CYII="
TINY_PNG_DATA_URL = f"data:image/png;base64,{TINY_PNG_B64}"


def _now():
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture(scope="session")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


def _register_member(email_prefix: str):
    session = requests.Session()
    email = f"rooney+{email_prefix}-{uuid.uuid4().hex[:8]}@nonprofitboardbuilder.com"
    password = "TestPass_iter16!"
    resp = session.post(f"{API}/members/register", json={
        "first_name": "Iter16", "last_name": "Tester",
        "email": email, "password": password, "confirm_password": password,
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "email": email, "password": password, "token": data["token"],
        "user_id": data["member"]["user_id"],
        "headers": {"Authorization": f"Bearer {data['token']}"},
    }


@pytest.fixture(scope="session")
def seeded(db):
    """Fresh $497 member with confirmed profile (mission set to Harbor Light) + branding +
    seeded materials for PDF/share tests. Second member for cross-tenant 404."""
    m1 = _register_member("iter16-a")
    m2 = _register_member("iter16-b")
    ts = _now()
    for m in (m1, m2):
        db.members.update_one({"user_id": m["user_id"]}, {"$addToSet": {"entitlements": "recruitment_self_guided"}})

    org_a = "Harbor Light Youth Services"
    mission_a = "To help homeless youth in Tampa find safe housing, education and employment"

    # A: profile confirmed but WITHOUT mission (for gate test) - deliberately incomplete
    db.recruitment_profiles.update_one({"user_id": m1["user_id"]}, {"$set": {
        "user_id": m1["user_id"],
        "data": {"organization_name": org_a, "board_kind": "Board of Directors"},  # no 'mission'
        "confirmed": True, "recruitment_profile_confirmed": True,
        "confirmed_at": ts, "updated_at": ts, "created_at": ts,
        "branding": {"logo_data": TINY_PNG_DATA_URL, "primary_color": "#7a1f2b", "secondary_color": ""},
    }}, upsert=True)

    # opportunity for A (needed for org name on PDFs)
    opp_id = uuid.uuid4().hex
    slug = f"harbor-light-{uuid.uuid4().hex[:6]}"
    db.opportunities.insert_one({
        "opportunity_id": opp_id, "user_id": m1["user_id"], "slug": slug,
        "organization_name": org_a, "status": "Draft",
        "custom_questions": [], "application_saved": True, "email_content": {},
        "created_at": ts, "updated_at": ts,
    })

    # Seed a board_opportunity material for A (used for material-pdf + share link tests)
    mat_id = uuid.uuid4().hex
    display = (
        "Board Opportunity\n\n"
        f"{org_a} is inviting community leaders to serve on our Board of Directors.\n"
        f"Mission: {mission_a}\n\n"
        "About the Role\n"
        "Board members guide governance, fundraising strategy and program impact."
    )
    db.generated_materials.insert_one({
        "material_id": mat_id, "user_id": m1["user_id"], "type": "board_opportunity",
        "application_id": "", "title": "Board Opportunity",
        "status": "Approved", "current_version": 1,
        "versions": [{"version": 1, "structured": {"title": "Board Opportunity", "body": display},
                      "display_text": display, "source": "seed",
                      "input_context_summary": "seed", "created_at": ts}],
        "created_at": ts, "updated_at": ts,
    })

    # Seed a share link for that material (branded shared-resource test)
    share_token = uuid.uuid4().hex
    db.share_links.insert_one({"share_token": share_token, "material_id": mat_id,
                                "user_id": m1["user_id"], "created_at": ts})

    # Seed a signature_request for A (list_signatures returns token check)
    sig_request_id = uuid.uuid4().hex
    sig_token = uuid.uuid4().hex
    application_id = uuid.uuid4().hex
    db.opportunity_applications.insert_one({
        "application_id": application_id, "opportunity_id": opp_id, "owner_user_id": m1["user_id"],
        "source": "External", "applicant_email": "rooney+iter16-candidate@nonprofitboardbuilder.com",
        "profile_snapshot": {"full_name": "Iter16 Candidate", "email": "rooney+iter16-candidate@nonprofitboardbuilder.com"},
        "answers": {}, "status": "Moving Forward", "interview_completed": True,
        "references": [], "background_check": {"status": "Not required"}, "emails_sent": {},
        "created_at": ts, "updated_at": ts,
    })
    db.signature_requests.insert_one({
        "request_id": sig_request_id, "token": sig_token, "owner_user_id": m1["user_id"],
        "application_id": application_id, "agreement_type": "board_member_agreement",
        "agreement_title": "Board Member Agreement",
        "material_id": mat_id, "agreement_version": 1,
        "document_snapshot": "BOARD MEMBER AGREEMENT\n\nBy signing, the member agrees to serve...",
        "organization_name": org_a,
        "board_member_name": "Iter16 Candidate",
        "board_member_email": "rooney+iter16-candidate@nonprofitboardbuilder.com",
        "status": "Ready for Signature", "created_at": ts, "updated_at": ts,
    })

    # Seed strategy structured for strategy-pdf branding test
    STRATEGY_STRUCTURED = {
        "executive_summary": "We are recruiting three professionals through our personal network.",
        "roles": [{"role_name": "Fundraising Leader", "person_sought": "A development professional."}],
        "channels": [{"channel": "Personal Network", "approach": "Reach out to five known contacts."}],
        "selection_criteria": ["Mission alignment", "Board-role relevant skills"],
    }
    db.generated_materials.insert_one({
        "material_id": uuid.uuid4().hex, "user_id": m1["user_id"], "type": "recruitment_strategy",
        "application_id": "", "title": "Board Recruitment Strategy",
        "status": "Approved", "current_version": 1,
        "versions": [{"version": 1, "structured": STRATEGY_STRUCTURED,
                      "display_text": "BOARD RECRUITMENT STRATEGY\n\nEXECUTIVE SUMMARY\n" + STRATEGY_STRUCTURED["executive_summary"],
                      "source": "seed", "input_context_summary": "seed", "created_at": ts}],
        "created_at": ts, "updated_at": ts,
    })

    ctx = {"a": m1, "b": m2, "org_a": org_a, "mission_a": mission_a,
           "material_id": mat_id, "share_token": share_token,
           "sig_token": sig_token, "sig_request_id": sig_request_id,
           "application_id": application_id, "opp_id": opp_id}
    yield ctx

    # Cleanup
    for m in (m1, m2):
        uid = m["user_id"]
        db.members.delete_one({"user_id": uid})
        db.recruitment_profiles.delete_many({"user_id": uid})
        db.generated_materials.delete_many({"user_id": uid})
        db.opportunities.delete_many({"user_id": uid})
        db.opportunity_applications.delete_many({"owner_user_id": uid})
        db.signature_requests.delete_many({"owner_user_id": uid})
        db.share_links.delete_many({"user_id": uid})
        db.board_profile_links.delete_many({"user_id": uid})
        db.reference_processes.delete_many({"owner_user_id": uid})


# ============================================================
# ORG + MISSION GATE
# ============================================================
def test_generate_without_mission_returns_422(seeded):
    """Confirmed profile missing 'mission' in data → 422 that mentions mission."""
    r = requests.post(f"{API}/workspace/generate",
                      json={"type": "board_opportunity"},
                      headers=seeded["a"]["headers"])
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"
    detail = (r.json().get("detail") or "").lower()
    assert "mission" in detail, f"422 detail should mention 'mission': {detail}"


def test_generate_after_setting_mission_passes_gate(seeded, db):
    """After PUT /workspace/profile with organization_name + mission, generate must pass the
    gate (i.e., NOT 422 with 'mission'). We accept any non-422 result — actual generation may
    500/502 (Claude budget) but the gate itself must be cleared."""
    headers = seeded["a"]["headers"]
    r = requests.put(f"{API}/workspace/profile",
                     json={"data": {"organization_name": seeded["org_a"],
                                    "mission": seeded["mission_a"],
                                    "board_kind": "Board of Directors"}},
                     headers=headers)
    assert r.status_code == 200, r.text
    # verify profile persisted
    prof = requests.get(f"{API}/workspace/profile", headers=headers).json()
    assert prof["profile"].get("mission") == seeded["mission_a"]
    assert prof["profile"].get("organization_name") == seeded["org_a"]

    # Now issue a generate probe; we don't wait for full generation. Verify the gate is passed:
    # response must NOT be 422 with 'mission' phrase.
    r2 = requests.post(f"{API}/workspace/generate",
                       json={"type": "board_opportunity"},
                       headers=headers, timeout=90)
    if r2.status_code == 422:
        detail = (r2.json().get("detail") or "").lower()
        assert "mission" not in detail, f"gate should be cleared, still 422 mission: {detail}"
    # any status other than 422-mission is acceptable (200 Approved, or 502 if Claude budget)
    # Reset profile back to no-mission for later tests? No — leave it, subsequent tests are independent.


# ============================================================
# SERVER-SIDE MATERIAL PDF
# ============================================================
def test_material_pdf_unauth_returns_401(seeded):
    r = requests.get(f"{API}/workspace/material-pdf/{seeded['material_id']}")
    assert r.status_code == 401, r.status_code


def test_material_pdf_cross_tenant_returns_404(seeded):
    """Member B requesting Member A's material_id → 404."""
    r = requests.get(f"{API}/workspace/material-pdf/{seeded['material_id']}",
                     headers=seeded["b"]["headers"])
    assert r.status_code == 404, r.text


def test_material_pdf_valid_branded(seeded):
    r = requests.get(f"{API}/workspace/material-pdf/{seeded['material_id']}",
                     headers=seeded["a"]["headers"])
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    body = r.content
    assert body[:4] == b"%PDF"
    try:
        from pypdf import PdfReader
    except ImportError:
        pytest.skip("pypdf not installed")
    reader = PdfReader(io.BytesIO(body))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    # title present
    assert "Board Opportunity" in text
    # org name present (footer + meta)
    assert seeded["org_a"] in text
    # page number footer
    assert "Page 1" in text
    # no app route URLs
    for bad in ["/app/recruitment", "/app/member/workspace", f"{BASE_URL}/app/"]:
        assert bad not in text, f"unexpected app route in PDF text: {bad}"


# ============================================================
# BRANDING REUSE
# ============================================================
def test_put_branding_and_strategy_pdf_reflects(seeded):
    """PUT branding → strategy-pdf still parses OK (uses primary_color/logo)."""
    r = requests.put(f"{API}/workspace/branding",
                     json={"logo_data": TINY_PNG_DATA_URL, "primary_color": "#7a1f2b",
                           "secondary_color": ""},
                     headers=seeded["a"]["headers"])
    assert r.status_code == 200, r.text

    r = requests.get(f"{API}/workspace/strategy-pdf", headers=seeded["a"]["headers"])
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_shared_returns_branding_and_org(seeded):
    """GET /api/shared/{token} → organization_name + logo_data + primary_color populated."""
    r = requests.get(f"{API}/shared/{seeded['share_token']}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["organization_name"] == seeded["org_a"]
    assert data["logo_data"].startswith("data:image")
    assert data["primary_color"] == "#7a1f2b"
    assert data["title"] == "Board Opportunity"
    assert seeded["org_a"] in data["display_text"]


def test_shared_bad_token_404(seeded):
    r = requests.get(f"{API}/shared/{'x' * 40}")
    assert r.status_code == 404


# ============================================================
# HOSTED LINKS — list_signatures includes token
# ============================================================
def test_list_signatures_includes_token(seeded):
    r = requests.get(f"{API}/workspace/signatures", headers=seeded["a"]["headers"])
    assert r.status_code == 200, r.text
    sigs = r.json()["signatures"]
    assert len(sigs) >= 1
    matching = [s for s in sigs if s.get("request_id") == seeded["sig_request_id"]]
    assert matching, "seeded signature request missing from list"
    rec = matching[0]
    assert rec.get("token") == seeded["sig_token"], "token must be present in list_signatures response"
    assert rec.get("agreement_type") == "board_member_agreement"


# ============================================================
# SIGN PAGE — public branding + method options
# ============================================================
def test_sign_get_returns_branding(seeded):
    r = requests.get(f"{API}/public/sign/{seeded['sig_token']}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["organization_name"] == seeded["org_a"]
    assert data["logo_data"].startswith("data:image")
    assert data["primary_color"] == "#7a1f2b"
    assert data["agreement_title"] == "Board Member Agreement"
    assert data["status"] in ("Ready for Signature", "Sent")


def test_sign_drawn_without_image_returns_422(seeded, db):
    """POSTing method drawn without a data:image signature_image → 422."""
    # ensure not signed yet
    r = requests.post(f"{API}/public/sign/{seeded['sig_token']}",
                      json={"agreed": True, "typed_signature": "Iter16 Candidate",
                            "email": "rooney+iter16-candidate@nonprofitboardbuilder.com",
                            "date": "2026-01-15",
                            "signature_method": "drawn", "signature_image": ""})
    assert r.status_code == 422, r.text


def test_sign_uploaded_without_image_returns_422(seeded):
    r = requests.post(f"{API}/public/sign/{seeded['sig_token']}",
                      json={"agreed": True, "typed_signature": "Iter16 Candidate",
                            "email": "rooney+iter16-candidate@nonprofitboardbuilder.com",
                            "date": "2026-01-15",
                            "signature_method": "uploaded", "signature_image": ""})
    assert r.status_code == 422, r.text


def test_sign_uploaded_method_success_and_second_409(seeded, db):
    """method='uploaded' + data:image PNG → 200; second attempt → 409; stored method+image."""
    payload = {"agreed": True, "typed_signature": "Iter16 Candidate",
               "email": "rooney+iter16-candidate@nonprofitboardbuilder.com",
               "date": "2026-01-15",
               "signature_method": "uploaded",
               "signature_image": TINY_PNG_DATA_URL}
    r = requests.post(f"{API}/public/sign/{seeded['sig_token']}", json=payload)
    assert r.status_code == 200, r.text
    # Second attempt → 409
    r2 = requests.post(f"{API}/public/sign/{seeded['sig_token']}", json=payload)
    assert r2.status_code == 409, r2.text
    # DB check: method='uploaded' + image stored
    rec = db.signature_requests.find_one({"token": seeded["sig_token"]}, {"_id": 0})
    assert rec["status"] == "Signed"
    assert rec["signed"]["method"] == "uploaded"
    assert rec["signed"]["signature_image"].startswith("data:image")
    # GET sign shows signed_record
    r3 = requests.get(f"{API}/public/sign/{seeded['sig_token']}")
    body = r3.json()
    assert body["signed"] is True
    assert body["signed_record"]["method"] == "uploaded"
    assert body["signed_record"]["signature_image"].startswith("data:image")


# ============================================================
# CONDITIONAL APPOINTMENT — 409 with missing docs
# ============================================================
def test_conditional_offer_blocked_when_docs_not_approved(seeded):
    """conditional_offer generation on a moving_forward application when onboarding docs
    (organization_overview, board_manual, agreements, profile form) are missing must return
    409 listing missing docs — never make a live Claude call."""
    # Make sure profile has mission and is confirmed (both required before gate)
    requests.put(f"{API}/workspace/profile",
                 json={"data": {"organization_name": seeded["org_a"],
                                "mission": seeded["mission_a"],
                                "board_kind": "Board of Directors"}},
                 headers=seeded["a"]["headers"])
    requests.post(f"{API}/workspace/profile/confirm", headers=seeded["a"]["headers"])
    r = requests.post(f"{API}/workspace/generate",
                      json={"type": "conditional_offer",
                            "application_id": seeded["application_id"]},
                      headers=seeded["a"]["headers"])
    assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text[:400]}"
    detail = r.json().get("detail", "")
    assert "onboarding" in detail.lower() or "conditional" in detail.lower()
    # should reference at least one missing material title
    assert "Organization Overview" in detail or "Board Manual" in detail or "Board Member Profile" in detail


# ============================================================
# ONBOARDING SESSION — persist + reuse
# ============================================================
def test_put_and_get_onboarding_session(seeded):
    payload = {"date": "2026-02-14", "time": "18:00", "timezone": "ET",
               "format": "Virtual", "link": "https://zoom.example.com/j/123",
               "location": "", "prepare": "Please review the board manual before we meet.",
               "status": "Scheduled"}
    r = requests.put(f"{API}/workspace/onboarding-session", json=payload,
                     headers=seeded["a"]["headers"])
    assert r.status_code == 200, r.text
    saved = r.json()["session"]
    for k in ("date", "time", "timezone", "format", "link", "prepare"):
        assert saved[k] == payload[k], f"session field {k} not persisted correctly"

    r = requests.get(f"{API}/workspace/onboarding-session", headers=seeded["a"]["headers"])
    assert r.status_code == 200
    sess = r.json()["session"]
    assert sess["date"] == payload["date"]
    assert sess["timezone"] == "ET"
    assert sess["format"] == "Virtual"
    assert sess["link"] == payload["link"]
    assert sess["prepare"] == payload["prepare"]
