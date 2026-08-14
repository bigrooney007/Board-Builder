"""
Batch 5 — Activation My Fundraising Board dashboard + Fundraising Portfolio.
End-to-end. Reuses activation-tester state left by Batch 4 (adopted+finalized,
toolkit Approved, Alice=Responsibility Agreed, Carol=Follow-Up Needed).
Never triggers real email sends (uses preview endpoints only).
Triggers ONE real Claude portfolio generation.
"""
import os
import re
import time
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
FOUNDER_EMAIL = "activation-tester-1786708997@example.com"
FOUNDER_PASSWORD = os.environ["ACTIVATION_TESTER_PASSWORD"]


def _login(session, email, password):
    r = session.post(f"{BASE_URL}/api/members/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"


def test_myboard_and_fundraising_portfolio_end_to_end():
    s = requests.Session()
    _login(s, FOUNDER_EMAIL, FOUNDER_PASSWORD)

    # --- 1) My Fundraising Board loads with correct members + counts + adopted strategy + toolkit
    r = s.get(f"{BASE_URL}/api/activation/my-board")
    assert r.status_code == 200, r.text
    board = r.json()
    assert board["ready"] is True, board  # adopted + toolkit Approved
    assert board["plan_status"] == "Adopted With Changes"
    assert board["adopted_strategy"], "adopted strategy missing on my-board"
    assert board["toolkit_text"], "approved toolkit missing on my-board"
    assert board["counts"]["participating"] == 2
    assert board["counts"]["responsibility_agreed"] == 1
    assert board["counts"]["follow_up_needed"] == 1
    members = board["members"]
    alice = next(m for m in members if m["name"].endswith("Alice"))
    carol = next(m for m in members if m["name"].endswith("Carol"))
    assert alice["responsibility_status"] == "Responsibility Agreed"
    assert alice["agreed_responsibility"], "Alice's agreed responsibility should show"
    assert carol["responsibility_status"] == "Follow-Up Needed"
    assert carol["agreed_responsibility"] == ""

    # --- 2) Portfolio generation BLOCKED for Follow-Up Needed member (no invented responsibility)
    r = s.post(f"{BASE_URL}/api/activation/members/{carol['participant_id']}/portfolio/generate")
    assert r.status_code == 409, f"expected 409 for Follow-Up Needed, got {r.status_code} {r.text}"

    # --- 3) Generate ONE portfolio for Alice (or reuse existing draft/approved)
    r = s.get(f"{BASE_URL}/api/activation/members/{alice['participant_id']}/portfolio")
    assert r.status_code == 200
    cur = r.json()
    if cur.get("fp_status") in {"NONE", "", None, "Failed"}:
        gen = s.post(f"{BASE_URL}/api/activation/members/{alice['participant_id']}/portfolio/generate")
        assert gen.status_code == 200, gen.text
        assert gen.json()["status"] == "Generating"
        deadline = time.time() + 180
        last = None
        while time.time() < deadline:
            last = s.get(f"{BASE_URL}/api/activation/members/{alice['participant_id']}/portfolio").json()
            if last.get("fp_status") not in {"Generating"}:
                break
            time.sleep(4)
        assert last and last["fp_status"] == "Draft", last
    cur = s.get(f"{BASE_URL}/api/activation/members/{alice['participant_id']}/portfolio").json()
    fp_text = cur.get("fp_text") or cur.get("fp_approved_text")
    assert fp_text, "portfolio text empty"

    # --- 4) Content assertions on portfolio
    up = fp_text.upper()
    # Uses Alice's exact agreed responsibility
    assert "corporate sponsorship" in fp_text.lower(), "portfolio must use Alice's agreed responsibility"
    # Uses org name (not another member's org)
    assert "Activation Test Nonprofit" in fp_text
    # Uses Alice's name — not Carol's
    assert "Alice" in fp_text
    assert "Carol" not in fp_text, "portfolio must not mention other member"
    # No AI mention, no invented donors/dollar amounts
    assert not re.search(r"\bAI\b", fp_text), "portfolio mentions AI"
    lc = fp_text.lower()
    for bad in ["$100,000", "$50,000 grant", "gates foundation", "goldman sachs"]:
        assert bad not in lc, f"portfolio invented {bad}"
    # Contains fundraising-specific structural language
    has_section = any(k in up for k in ["FUNDRAISING PORTFOLIO", "YOUR ROLE", "YOUR RESPONSIBILITY", "TOOLS", "WHERE YOU FIT"])
    assert has_section, "portfolio missing expected structural sections"

    # --- 5) Edit -> Save -> Approve
    marker = "TEST_BATCH5_FP_MARKER"
    edited = fp_text + f"\n\n{marker}\n"
    r = s.put(f"{BASE_URL}/api/activation/members/{alice['participant_id']}/portfolio", json={"text": edited})
    assert r.status_code == 200 and r.json()["status"] == "Draft"
    cur = s.get(f"{BASE_URL}/api/activation/members/{alice['participant_id']}/portfolio").json()
    assert marker in (cur.get("fp_text") or ""), "edit did not persist"

    r = s.post(f"{BASE_URL}/api/activation/members/{alice['participant_id']}/portfolio/approve")
    assert r.status_code == 200 and r.json()["status"] == "Approved"
    cur = s.get(f"{BASE_URL}/api/activation/members/{alice['participant_id']}/portfolio").json()
    assert cur["fp_status"] == "Approved"

    # --- 6) View online / PDF
    pdf = s.get(f"{BASE_URL}/api/activation/members/{alice['participant_id']}/portfolio/pdf")
    assert pdf.status_code == 200
    assert pdf.headers.get("content-type", "").startswith("application/pdf")
    assert len(pdf.content) > 1000

    # --- 7) Email preview WITHOUT sending (also source-of-truth for share token in UI)
    prev = s.get(f"{BASE_URL}/api/activation/members/{alice['participant_id']}/portfolio/email-preview")
    assert prev.status_code == 200
    prev_data = prev.json()
    assert prev_data["to_email"] == alice["email"]
    assert "Fundraising Portfolio" in prev_data["subject"]
    assert "Activation Test Nonprofit" in prev_data["subject"]
    assert "/fundraising-portfolio/" in prev_data["form_link"], "secure link auto-inserted"
    share_token = prev_data["form_link"].rsplit("/", 1)[-1]
    assert share_token, "share token must be present in form_link"
    assert "[VIEW MY FUNDRAISING PORTFOLIO]" in prev_data["body"]

    # --- 8) Public portfolio link WORKS without login (fresh session)
    fresh = requests.Session()
    r = fresh.get(f"{BASE_URL}/api/fundraising-portfolio/{share_token}")
    assert r.status_code == 200, r.text
    pub = r.json()
    assert pub["member_name"] == alice["name"]
    assert pub["organization_name"] == "Activation Test Nonprofit"
    assert pub["issued_by"], "issuer must be present"
    assert marker in pub["text"], "public text must reflect approved (marker) text"

    # Public PDF
    r = fresh.get(f"{BASE_URL}/api/fundraising-portfolio/{share_token}/pdf")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")

    # Invalid token 404
    r = fresh.get(f"{BASE_URL}/api/fundraising-portfolio/not-a-real-token")
    assert r.status_code == 404

    # --- 9) Portfolio email-preview blocked BEFORE approval for Carol (never approved)
    r = s.get(f"{BASE_URL}/api/activation/members/{carol['participant_id']}/portfolio/email-preview")
    assert r.status_code == 409

    # --- 10) My-board counts updated to reflect approved portfolio
    board2 = s.get(f"{BASE_URL}/api/activation/my-board").json()
    assert board2["counts"]["portfolios_approved"] >= 1

    # --- 11) Non-authenticated founder endpoints protected
    fresh2 = requests.Session()
    r = fresh2.get(f"{BASE_URL}/api/activation/my-board")
    assert r.status_code in (401, 403), f"my-board must require auth, got {r.status_code}"
    r = fresh2.post(f"{BASE_URL}/api/activation/members/{alice['participant_id']}/portfolio/generate")
    assert r.status_code in (401, 403)


# ---------- Accountability + Nurture CONFIGURATION INSPECTION ONLY (no sends) ----------
def test_activation_accountability_config():
    """Read code — do NOT trigger sends."""
    import sys
    sys.path.insert(0, "/app/backend")
    import importlib
    aa = importlib.import_module("activation_accountability")
    # Reuses shared accountability engine
    assert aa.PURCHASE_SOURCE == "direct_diy_board_activation_497"
    assert aa.PRODUCT == "activation_self_guided"
    # progress-aware activation_stage
    src = open("/app/backend/activation_accountability.py").read()
    assert "activation_stage" in src
    assert "completed_modules" in src
    assert "toolkit" in src and "adoption" in src and "portfolios_approved" in src
    # DWM excluded: enrolls only PURCHASE_SOURCE (direct_diy_board_activation_497). Confirm no
    # reference to direct_board_activation_project_2497 in accountability enrollment.
    assert "direct_board_activation_project_2497" not in src
    # STAGE_EMAILS has expected stages
    for stage in ["get_started", "start_planning", "board_input", "build_strategy", "board_review",
                  "facilitate_adoption", "equip_board", "complete_board", "completed"]:
        assert stage in aa.STAGE_EMAILS, f"missing stage {stage}"
    # Uses shared engine (imports from accountability_service)
    assert "from accountability_service import" in src


def test_activation_nurture_config():
    """Nurture must remain OFF; 3 templates rotating; Tuesday; purchase-stop covers both
    activation purchase sources; board_transformation not auto-enrolled."""
    # ACTIVATION_LEAD_NURTURE_ENABLED must be false
    env = open("/app/backend/.env").read()
    assert re.search(r'ACTIVATION_LEAD_NURTURE_ENABLED\s*=\s*"?false"?', env), \
        "ACTIVATION_LEAD_NURTURE_ENABLED must be false"

    import sys
    sys.path.insert(0, "/app/backend")
    import importlib
    ms = importlib.import_module("marketing_service")
    tpls = ms.NURTURE_TEMPLATES["fundraising_activation"]
    assert len(tpls) == 3, f"fundraising_activation must have exactly 3 templates, got {len(tpls)}"
    # Rotation targets:
    # 1: about-rooney; 2: /activate-your-board-yourself ($497); 3: /board-activation-proposal ($2,497)
    urls = [t["url"] for t in tpls]
    ctas = [t["cta"] for t in tpls]
    assert urls[0] == "/about-rooney"
    assert urls[1] == "/activate-your-board-yourself"
    assert urls[2] == "/board-activation-proposal"
    assert "$497" in ctas[1]
    assert "$2,497" in ctas[2]

    # Weekly Tuesday 7am ET via the shared nurture engine
    src = open("/app/backend/marketing_service.py").read()
    assert 'LEAD_NURTURE_DAY", "Tuesday"' in src
    assert "run_weekly_nurture" in src

    # Purchase-stop covers BOTH activation purchase sources
    assert "ACTIVATION_PURCHASE_SOURCES" in src
    assert ms.ACTIVATION_PURCHASE_SOURCES == {"direct_diy_board_activation_497",
                                              "direct_board_activation_project_2497"}
    assert "stop_activation_nurture" in src

    # board_transformation is NOT in NURTURE_TEMPLATES => sync_lead_nurture guard skips it
    assert "board_transformation" not in ms.NURTURE_TEMPLATES
    # sync_lead_nurture returns early if source not in NURTURE_TEMPLATES
    assert 'if source not in NURTURE_TEMPLATES' in src

    # enabled_nurture_sources reflects env: fundraising_activation should NOT be enabled
    enabled = ms.enabled_nurture_sources()
    assert "fundraising_activation" not in enabled, f"activation nurture must be OFF, enabled={enabled}"
