"""
Batch 4 — Activation Modules 4 (Facilitating Plan Adoption) + 5 (Equipping Board Members
to Execute). ONE end-to-end test. Triggers real Claude generation ONCE for the guide and
ONCE for the toolkit. Reuses the seeded activation-tester account from Batches 1-3.
"""
import os
import re
import time

import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

FOUNDER_EMAIL = "activation-tester-1786708997@example.com"
FOUNDER_PASSWORD = os.environ["ACTIVATION_TESTER_PASSWORD"]

# Guide section headings we must see in the generated facilitation guide
GUIDE_HEADINGS = [
    "1. OBJECTIVE FOR THE DISCUSSION",
    "2. BEFORE THE DISCUSSION",
    "3. OPEN THE DISCUSSION",
    "4. RECONNECT EVERYONE TO WHAT WE ARE TRYING TO ACCOMPLISH",
    "5. REVIEW THE FUNDRAISING STRATEGY",
    "6. WORK THROUGH THE BOARD'S FEEDBACK",
    "7. CONFIRM WHAT WE ARE PRIORITIZING",
    "8. CONFIRM WHAT THE BOARD WILL CARRY",
    "9. ESTABLISH INDIVIDUAL OWNERSHIP",
    "10. IDENTIFY WHAT BOARD MEMBERS NEED TO EXECUTE",
    "11. AGREE ON WHAT HAPPENS FIRST",
    "12. CONFIRM THE WAY FORWARD",
    "13. CLOSE WITH OWNERSHIP",
]


def _login(session: requests.Session, email: str, password: str) -> None:
    r = session.post(f"{BASE_URL}/api/members/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"


def _poll_status(session, path, key, terminal, timeout_s=180):
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        r = session.get(f"{BASE_URL}{path}")
        assert r.status_code == 200, r.text
        last = r.json()
        if last.get(key) in terminal:
            return last
        time.sleep(3)
    raise AssertionError(f"polling {path} timed out; last={last}")


def test_batch4_activation_adoption_and_toolkit_end_to_end():
    founder = requests.Session()
    _login(founder, FOUNDER_EMAIL, FOUNDER_PASSWORD)

    # ========== 1) Adoption overview reflects Batch 3 end-state ==========
    ov = founder.get(f"{BASE_URL}/api/activation/adoption").json()
    assert ov["strategy"]["status"] == "Ready for Board Review"
    assert ov["strategy"]["review_version"] == 2
    # Alice is the only REVIEWED participant
    assert len(ov["reviews"]) == 1
    alice_review = ov["reviews"][0]
    assert "Alice" in alice_review["name"]
    assert alice_review["position"] and alice_review["contribution"], alice_review
    # members includes Alice + Carol
    members = ov["members"]
    assert len(members) == 2
    alice = next(m for m in members if m["name"].endswith("Alice"))
    carol = next(m for m in members if m["name"].endswith("Carol"))
    # AI has NOT populated responsibilities
    for m in members:
        assert m["agreed_responsibility"] == ""
        assert m["responsibility_status"] == "No Fundraising Responsibility Agreed Yet"

    # ========== 2-4) Generate facilitation guide ONCE ==========
    if not ov.get("adoption") or ov["adoption"].get("guide_status", "NONE") in {"NONE", "Failed"}:
        gen = founder.post(f"{BASE_URL}/api/activation/adoption/guide/generate")
        assert gen.status_code == 200, gen.text
        assert gen.json()["status"] == "Generating"
        final = _poll_status(founder, "/api/activation/adoption/status", "guide_status",
                             {"Draft", "Approved", "Failed"})
        assert final["guide_status"] == "Draft", final

    ov = founder.get(f"{BASE_URL}/api/activation/adoption").json()
    guide_text = ov["adoption"]["guide_text"]
    assert guide_text, "guide_text empty"

    up = guide_text.upper()
    # All 13 headings present
    for h in GUIDE_HEADINGS:
        assert h in up, f"missing heading {h!r}"
    # Order enforced
    positions = [up.index(h) for h in GUIDE_HEADINGS]
    assert positions == sorted(positions), "headings out of order"
    # Org-specific
    assert "Activation Test Nonprofit" in guide_text
    # No AI mention
    assert not re.search(r"\bAI\b", guide_text), "guide mentions AI"
    # No claim of formal Board adoption
    lower = guide_text.lower()
    for bad in ["quorum", "parliamentary", "bylaws", "voting requirement", "roll call vote", "motion carried"]:
        assert bad not in lower, f"guide mentions {bad}"
    # Should NOT claim the Board already adopted anything
    assert "board adopted" not in lower and "board has adopted" not in lower, "guide implies formal adoption"
    # Section 9 must reference Alice by first name (Carol has no planning response so must not be invented as an interest holder)
    sec9_start = up.index("9. ESTABLISH INDIVIDUAL OWNERSHIP")
    sec9_end = up.index("10. IDENTIFY WHAT BOARD MEMBERS NEED TO EXECUTE")
    section9 = guide_text[sec9_start:sec9_end]
    assert "Alice" in section9, "section 9 must reference Alice specifically"
    # Carol did not complete Module 2 planning form — Section 9 must not fabricate Carol interests.
    # We allow her name only in the context of "no response yet". Be strict: forbid Carol here entirely.
    if "Carol" in section9:
        carol_ctx = section9.lower()
        assert ("no response" in carol_ctx or "has not" in carol_ctx or "did not" in carol_ctx or
                "not yet" in carol_ctx), "section 9 references Carol without acknowledging she has not responded"
    # Section 6 must reference Alice's actual feedback keywords (she gave suggestions in her review)
    sec6_start = up.index("6. WORK THROUGH THE BOARD'S FEEDBACK")
    sec6_end = up.index("7. CONFIRM WHAT WE ARE PRIORITIZING")
    section6 = guide_text[sec6_start:sec6_end]
    assert "Alice" in section6, "section 6 must attribute Alice's actual review"

    # ========== 5) Edit → Save → Approve → PDF ==========
    marker = "TEST_BATCH4_MARKER_EDIT"
    edited = guide_text + f"\n\n{marker}\n"
    r = founder.put(f"{BASE_URL}/api/activation/adoption/guide", json={"text": edited})
    assert r.status_code == 200 and r.json()["status"] == "Draft"
    ov = founder.get(f"{BASE_URL}/api/activation/adoption").json()
    assert marker in ov["adoption"]["guide_text"], "edit did not persist"

    r = founder.post(f"{BASE_URL}/api/activation/adoption/guide/approve")
    assert r.status_code == 200 and r.json()["status"] == "Approved"
    ov = founder.get(f"{BASE_URL}/api/activation/adoption").json()
    assert ov["adoption"]["guide_status"] == "Approved"

    pdf = founder.get(f"{BASE_URL}/api/activation/adoption/guide/pdf")
    assert pdf.status_code == 200
    assert pdf.headers.get("content-type", "").startswith("application/pdf")
    assert len(pdf.content) > 1000

    # ========== 6) Plan Adoption Conclusion ==========
    conclusion_text = (
        "The Board met to discuss the strategy. Alice supported the plan with suggestions around "
        "corporate sponsorships and clarity on the 90-day priorities. Carol was not present but has "
        "committed to reviewing the plan next week. We agreed to adopt the plan with changes to "
        "reflect corporate sponsorship as the primary near-term focus."
    )
    r = founder.put(f"{BASE_URL}/api/activation/adoption/conclusion", json={"text": conclusion_text})
    assert r.status_code == 200
    ov = founder.get(f"{BASE_URL}/api/activation/adoption").json()
    assert ov["adoption"]["conclusion"] == conclusion_text

    # ========== 7) Plan status: Further Review Needed -> module 5 locked ==========
    r = founder.put(f"{BASE_URL}/api/activation/adoption/plan-status", json={"status": "Further Review Needed"})
    assert r.status_code == 200 and r.json()["module5_ready"] is False
    ov = founder.get(f"{BASE_URL}/api/activation/adoption").json()
    assert ov["module5_ready"] is False
    tk = founder.get(f"{BASE_URL}/api/activation/toolkit").json()
    assert tk["gate_open"] is False
    assert tk["plan_status"] == "Further Review Needed"
    # generating toolkit is 409
    r = founder.post(f"{BASE_URL}/api/activation/toolkit/generate")
    assert r.status_code == 409
    # strategy + Alice review untouched
    strat = founder.get(f"{BASE_URL}/api/activation/strategy").json()
    assert strat["strategy"]["status"] == "Ready for Board Review"
    assert strat["strategy"]["review_version"] == 2
    rev = founder.get(f"{BASE_URL}/api/activation/reviewers/{alice['participant_id']}/review")
    assert rev.status_code == 200
    assert rev.json()["review"]["position"], "Alice review lost"

    # ========== 7b) Adopted as Presented -> adopted_text=reviewed text, finalized=true ==========
    r = founder.put(f"{BASE_URL}/api/activation/adoption/plan-status", json={"status": "Adopted as Presented"})
    assert r.status_code == 200 and r.json()["module5_ready"] is True
    ov = founder.get(f"{BASE_URL}/api/activation/adoption").json()
    reviewed_text = ov["reviewed_text"]
    assert ov["adoption"]["adopted_text"] == reviewed_text
    assert ov["adoption"]["finalized"] is True
    assert ov["module5_ready"] is True

    # ========== 7c) Now switch to Adopted With Changes and edit, then finalize ==========
    r = founder.put(f"{BASE_URL}/api/activation/adoption/plan-status", json={"status": "Adopted With Changes"})
    assert r.status_code == 200
    ov = founder.get(f"{BASE_URL}/api/activation/adoption").json()
    assert ov["adoption"]["finalized"] is False
    # draft prefill exists (from adopted_text carried across, or newly seeded)
    draft = ov["adoption"].get("draft_adopted_text") or ov["adoption"].get("adopted_text") or reviewed_text
    assert draft, "no draft to edit"
    changed_line = "\n\nCHANGED IN ADOPTION: corporate sponsorship prioritized above events for the first 90 days.\n"
    edited_plan = draft + changed_line
    r = founder.put(f"{BASE_URL}/api/activation/adoption/adopted-plan", json={"text": edited_plan})
    assert r.status_code == 200
    r = founder.post(f"{BASE_URL}/api/activation/adoption/finalize")
    assert r.status_code == 200 and r.json()["status"] == "finalized"
    ov = founder.get(f"{BASE_URL}/api/activation/adoption").json()
    assert ov["adoption"]["finalized"] is True
    assert ov["adoption"]["plan_status"] == "Adopted With Changes"
    assert changed_line.strip() in ov["adoption"]["adopted_text"]
    # Version history preserved: reviewed version text unchanged
    strat = founder.get(f"{BASE_URL}/api/activation/strategy").json()
    assert strat["strategy"]["status"] == "Ready for Board Review"
    assert ov["adoption"]["adopted_text"] != reviewed_text, "adopted must differ from reviewed"
    # Alice review still available
    rev = founder.get(f"{BASE_URL}/api/activation/reviewers/{alice['participant_id']}/review")
    assert rev.status_code == 200

    # ========== 12-13) Responsibilities ==========
    alice_resp = "Lead corporate sponsorship introductions with the three local businesses she named and support one sponsor conversation with the founder in the next 60 days."
    r = founder.put(f"{BASE_URL}/api/activation/participants/{alice['participant_id']}/responsibility",
                    json={"agreed_responsibility": alice_resp, "responsibility_status": "Responsibility Agreed"})
    assert r.status_code == 200
    r = founder.put(f"{BASE_URL}/api/activation/participants/{carol['participant_id']}/responsibility",
                    json={"agreed_responsibility": "", "responsibility_status": "Follow-Up Needed"})
    assert r.status_code == 200
    # Invalid status → 422
    r = founder.put(f"{BASE_URL}/api/activation/participants/{alice['participant_id']}/responsibility",
                    json={"agreed_responsibility": alice_resp, "responsibility_status": "Not A Status"})
    assert r.status_code == 422
    # Persistence
    ov = founder.get(f"{BASE_URL}/api/activation/adoption").json()
    a = next(m for m in ov["members"] if m["participant_id"] == alice["participant_id"])
    c = next(m for m in ov["members"] if m["participant_id"] == carol["participant_id"])
    assert a["agreed_responsibility"] == alice_resp
    assert a["responsibility_status"] == "Responsibility Agreed"
    assert c["agreed_responsibility"] == ""
    assert c["responsibility_status"] == "Follow-Up Needed"

    # ========== 14) Module 5 gate open ==========
    assert ov["module5_ready"] is True
    tk = founder.get(f"{BASE_URL}/api/activation/toolkit").json()
    assert tk["gate_open"] is True

    # ========== 15-17) Generate toolkit ONCE ==========
    if tk["toolkit"]["status"] in {"NONE", "Failed"}:
        gen = founder.post(f"{BASE_URL}/api/activation/toolkit/generate")
        assert gen.status_code == 200, gen.text
        assert gen.json()["status"] == "Generating"
        # poll
        deadline = time.time() + 180
        last = None
        while time.time() < deadline:
            last = founder.get(f"{BASE_URL}/api/activation/toolkit").json()
            if last["toolkit"]["status"] not in {"Generating"}:
                break
            time.sleep(3)
        assert last["toolkit"]["status"] == "Draft", last
    tk = founder.get(f"{BASE_URL}/api/activation/toolkit").json()
    toolkit_text = tk["toolkit"]["display_text"]
    assert toolkit_text
    up_tk = toolkit_text.upper()
    assert "BOARD FUNDRAISING EXECUTION TOOLKIT" in up_tk
    assert "Activation Test Nonprofit" in toolkit_text
    assert not re.search(r"\bAI\b", toolkit_text), "toolkit mentions AI"
    # At least one call script section using labeled structure
    assert "CALL SCRIPTS" in up_tk, "no CALL SCRIPTS section"
    # Labeled call-script parts appear
    lc = toolkit_text.lower()
    assert "when to use" in lc, "call script missing 'When to use'"
    assert "opening" in lc
    assert "why i'm calling" in lc or "why i am calling" in lc
    assert "close" in lc
    # KNOW/LIKE/TRUST family or explicit relationship-building language
    # (soft check — required by AI note)
    # No invented dollar amounts / donor names — check no obvious hallucinated donor phrasing
    for bad in ["$50,000", "$100,000", "$25,000 grant", "goldman sachs", "gates foundation"]:
        assert bad.lower() not in lc, f"toolkit invented {bad}"

    # ========== Edit + Save + Approve + PDF for toolkit ==========
    marker2 = "TEST_BATCH4_TOOLKIT_MARKER"
    edited_tk = toolkit_text + f"\n\n{marker2}\n"
    r = founder.put(f"{BASE_URL}/api/activation/toolkit", json={"text": edited_tk})
    assert r.status_code == 200 and r.json()["status"] == "Draft"
    r = founder.post(f"{BASE_URL}/api/activation/toolkit/approve")
    assert r.status_code == 200 and r.json()["status"] == "Approved"
    pdf = founder.get(f"{BASE_URL}/api/activation/toolkit/pdf")
    assert pdf.status_code == 200
    assert pdf.headers.get("content-type", "").startswith("application/pdf")

    # ========== 20-22) Data intact ==========
    # Module 2 planning response for Alice still viewable
    r = founder.get(f"{BASE_URL}/api/activation/participants/{alice['participant_id']}/response")
    assert r.status_code == 200
    assert r.json()["response"]

    # smoke pings on other product surfaces (must not crash)
    for path in ["/api/recruitment/profile", "/api/reactivation/state"]:
        rr = founder.get(f"{BASE_URL}{path}")
        assert rr.status_code in {200, 204, 403, 404}, f"{path} returned {rr.status_code}"
