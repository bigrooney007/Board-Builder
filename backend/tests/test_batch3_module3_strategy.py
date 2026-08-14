"""
Batch 3 — Activation Module 3: Fundraising Strategy Plan (Build → Review → Track)
Single focused end-to-end test. Triggers the real Claude generation ONCE.
"""
import os
import time
import re
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

FOUNDER_EMAIL = "activation-tester-1786708997@example.com"
FOUNDER_PASSWORD = os.environ["ACTIVATION_TESTER_PASSWORD"]
NO_ENT_EMAIL = "module-tester@example.com"
NO_ENT_PASSWORD = os.environ["MODULE_TESTER_PASSWORD"]


def _login(session, email, password):
    r = session.post(f"{BASE_URL}/api/members/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"


def _get_reviewer_by_email(session, email):
    ov = session.get(f"{BASE_URL}/api/activation/strategy").json()
    for r in ov["reviewers"]:
        if r["email"] == email:
            return r
    raise AssertionError(f"reviewer with email {email} not found")


def test_batch3_module3_strategy_end_to_end():
    founder = requests.Session()
    _login(founder, FOUNDER_EMAIL, FOUNDER_PASSWORD)

    # ---------- (0) Tenant isolation ----------
    unauth = requests.get(f"{BASE_URL}/api/activation/strategy")
    assert unauth.status_code == 401
    other = requests.Session()
    _login(other, NO_ENT_EMAIL, NO_ENT_PASSWORD)
    r = other.get(f"{BASE_URL}/api/activation/strategy")
    assert r.status_code == 403

    # ---------- (1) Overview: planning counts reflect Alice COMPLETED, Carol SENT ----------
    ov = founder.get(f"{BASE_URL}/api/activation/strategy").json()
    assert ov["planning"] == {"invited": 2, "received": 1, "waiting": 1, "included": 1}, ov["planning"]
    assert ov["strategy"]["status"] in {"NONE", "Draft", "Ready for Board Review"}
    assert len(ov["reviewers"]) == 2

    alice = _get_reviewer_by_email(founder, "delivered@resend.dev")
    carol = _get_reviewer_by_email(founder, "bounced@resend.dev")
    alice_id = alice["participant_id"]
    carol_id = carol["participant_id"]

    # ---------- (5b) Sending review BEFORE approval → 409 ----------
    # first attempt (regardless of current strategy state): if strategy already NONE/Draft, we expect 409
    if ov["strategy"]["status"] != "Ready for Board Review":
        r = founder.post(f"{BASE_URL}/api/activation/reviewers/{alice_id}/send", json={"type": "initial"})
        assert r.status_code == 409, f"send-before-approve expected 409 got {r.status_code}"

    # ---------- (2) Generate strategy ONCE ----------
    if ov["strategy"]["status"] == "NONE":
        gen = founder.post(f"{BASE_URL}/api/activation/strategy/generate")
        assert gen.status_code == 200
        assert gen.json()["status"] == "Generating"
        # poll
        for _ in range(60):
            time.sleep(3)
            s = founder.get(f"{BASE_URL}/api/activation/strategy/status").json()
            if s["status"] != "Generating":
                break
        assert s["status"] == "Draft", f"generation did not finish, last={s}"

    ov = founder.get(f"{BASE_URL}/api/activation/strategy").json()
    strategy_text = ov["strategy"]["display_text"]
    assert strategy_text, "strategy display_text empty"

    # ---------- (3+4) Inspect generated strategy ----------
    required_headings = [
        "FUNDRAISING STRATEGY PLAN",
        "EXECUTIVE SUMMARY",
        "1. FUNDRAISING GOAL",
        "2. WHAT WE ARE RAISING MONEY FOR",
        "3. WHO WE SHOULD BUILD RELATIONSHIPS WITH",
        "4. PRIORITY FUNDRAISING OPPORTUNITIES",
        "5. WHAT WE NEED PEOPLE TO UNDERSTAND ABOUT THE MISSION",
        "6. HOW WE WILL BUILD FUNDRAISING RELATIONSHIPS",
        "7. RELATIONSHIPS ALREADY AROUND THE BOARD",
        "8. HOW THE BOARD CAN PARTICIPATE",
        "9. FOUNDER AND STAFF RESPONSIBILITIES",
        "10. WHAT WE NEED TO EXECUTE",
        "11. THE NEXT 90 DAYS",
        "12. 12-MONTH FUNDRAISING DIRECTION",
        "13. HOW WE WILL KNOW THE PLAN IS MOVING",
        "14. ITEMS FOR BOARD REVIEW",
        "15. NEXT STEP: REVIEW AND ADOPT THE PLAN",
    ]
    last_idx = -1
    for h in required_headings:
        idx = strategy_text.find(h)
        assert idx > last_idx, f"missing/out-of-order heading: {h}"
        last_idx = idx

    # Real org name + $500,000
    assert "Activation Test Nonprofit" in strategy_text
    # $500,000 goal from intake (could be formatted variants)
    assert re.search(r"\$?\s*500[,.]?000", strategy_text), "goal amount $500,000 missing"
    # No 'AI' or placeholders (word-boundary AI check)
    assert not re.search(r"\bAI\b", strategy_text), "strategy mentions AI"
    assert "[PLACEHOLDER]" not in strategy_text and "[ORGANIZATION]" not in strategy_text
    # Section 6 must reference the KNOW/LIKE/TRUST framework
    sect6 = strategy_text[strategy_text.find("6. HOW WE WILL BUILD FUNDRAISING RELATIONSHIPS"):strategy_text.find("7. RELATIONSHIPS")]
    for kw in ["KNOW", "LIKE", "TRUST", "ASK", "FOLLOW UP", "STEWARD"]:
        assert kw.lower() in sect6.lower(), f"section 6 missing framework keyword {kw}"
    # No mis-attribution: 'Carol' must not appear anywhere (only Alice completed)
    assert "Carol" not in strategy_text, "Carol's name appears though she did not complete"

    # ---------- (5) EDIT + SAVE + APPROVE ----------
    marker = "\n\n[BATCH3-TEST-MARKER-DO-NOT-KEEP]"
    edited = strategy_text + marker
    r = founder.put(f"{BASE_URL}/api/activation/strategy", json={"display_text": edited})
    assert r.status_code == 200 and r.json()["status"] == "Draft"
    st = founder.get(f"{BASE_URL}/api/activation/strategy/status").json()
    assert st["status"] == "Draft" and marker in st["display_text"]

    # send before approve → 409 while status is Draft
    r = founder.post(f"{BASE_URL}/api/activation/reviewers/{alice_id}/send", json={"type": "initial"})
    assert r.status_code == 409

    ap = founder.post(f"{BASE_URL}/api/activation/strategy/approve-review")
    assert ap.status_code == 200 and ap.json()["status"] == "Ready for Board Review"
    v_after_marker = ap.json()["review_version"]
    assert v_after_marker >= 1

    # ---------- (6) Send review to Alice ----------
    pv = founder.get(f"{BASE_URL}/api/activation/reviewers/{alice_id}/email-preview", params={"type": "initial"}).json()
    assert pv["subject"] == "Please Review Our Fundraising Strategy Plan | Activation Test Nonprofit"
    assert "Thank you for contributing your ideas" in pv["body"]
    assert "developed the Fundraising Strategy Plan for Board review" in pv["body"]
    assert pv["form_link"].startswith("http") and "/strategy-review/" in pv["form_link"]
    alice_token = pv["form_link"].rsplit("/", 1)[-1]

    send = founder.post(f"{BASE_URL}/api/activation/reviewers/{alice_id}/send", json={"type": "initial"})
    assert send.status_code == 200
    alice_after_send = _get_reviewer_by_email(founder, "delivered@resend.dev")
    assert alice_after_send["review_status"] == "SENT"
    assert alice_after_send["last_review_sent_at"]
    assert alice_after_send["review_version"] == v_after_marker

    # ---------- (7-9) Public strategy-review page ----------
    pub_unauth = requests.Session()  # no cookies at all
    pub = pub_unauth.get(f"{BASE_URL}/api/strategy-review/{alice_token}")
    assert pub.status_code == 200
    pub_data = pub.json()
    assert pub_data["organization_name"] == "Activation Test Nonprofit"
    assert pub_data["submitted"] is False
    # Frozen version served must contain marker (was approved with marker)
    assert marker in pub_data["strategy_text"]
    assert pub_data["options"] == [
        "I support the plan as written",
        "I support the overall direction but have suggestions",
        "I have issues I believe we should discuss before adopting the plan",
    ]

    # invalid token → 404
    bad = requests.get(f"{BASE_URL}/api/strategy-review/not-a-real-token-xyz-123")
    assert bad.status_code == 404

    # Option 2/3 require discussion_points → 422
    r = pub_unauth.post(f"{BASE_URL}/api/strategy-review/{alice_token}", json={
        "position": "I support the overall direction but have suggestions",
        "discussion_points": "",
        "contribution": "I can help with donor outreach.",
        "support_needs": "",
    })
    assert r.status_code == 422

    # Missing contribution → 422 (min_length=1)
    r = pub_unauth.post(f"{BASE_URL}/api/strategy-review/{alice_token}", json={
        "position": "I support the plan as written",
        "discussion_points": "",
        "contribution": "",
        "support_needs": "",
    })
    assert r.status_code == 422

    # Invalid position → 422
    r = pub_unauth.post(f"{BASE_URL}/api/strategy-review/{alice_token}", json={
        "position": "made up option",
        "contribution": "x",
    })
    assert r.status_code == 422

    # Valid submission (option 2, realistic supportive-with-suggestions)
    review_payload = {
        "position": "I support the overall direction but have suggestions",
        "discussion_points": "I'd like the Board to discuss timing on approaching local businesses and whether we lead with sponsorships or major individual gifts first.",
        "contribution": "I can personally introduce us to two business owners I know from the Chamber, and I'm willing to help draft the sponsorship one-pager.",
        "support_needs": "A short case-for-support document and talking points I can use in initial conversations.",
    }
    submit = pub_unauth.post(f"{BASE_URL}/api/strategy-review/{alice_token}", json=review_payload)
    assert submit.status_code == 201, submit.text

    # Resubmit → 409
    dup = pub_unauth.post(f"{BASE_URL}/api/strategy-review/{alice_token}", json=review_payload)
    assert dup.status_code == 409

    # ---------- (10) Founder view: VIEW REVIEW returns verbatim data ----------
    view = founder.get(f"{BASE_URL}/api/activation/reviewers/{alice_id}/review").json()
    assert view["review"]["position"] == review_payload["position"]
    assert view["review"]["discussion_points"] == review_payload["discussion_points"]
    assert view["review"]["contribution"] == review_payload["contribution"]
    assert view["review"]["support_needs"] == review_payload["support_needs"]
    assert view["review_version"] == v_after_marker

    # reviewer row shows REVIEWED
    alice_row = _get_reviewer_by_email(founder, "delivered@resend.dev")
    assert alice_row["review_status"] == "REVIEWED"
    assert alice_row["review_position"] == review_payload["position"]

    # ---------- (11) Reminder to Carol ----------
    # Reminder on NOT SENT → 409
    r = founder.post(f"{BASE_URL}/api/activation/reviewers/{carol_id}/send", json={"type": "reminder"})
    assert r.status_code == 409

    # Send Carol her initial review first
    cpv = founder.get(f"{BASE_URL}/api/activation/reviewers/{carol_id}/email-preview", params={"type": "initial"}).json()
    carol_token_1 = cpv["form_link"].rsplit("/", 1)[-1]
    r = founder.post(f"{BASE_URL}/api/activation/reviewers/{carol_id}/send", json={"type": "initial"})
    assert r.status_code == 200

    # Reminder preview: subject + same token
    rpv = founder.get(f"{BASE_URL}/api/activation/reviewers/{carol_id}/email-preview", params={"type": "reminder"}).json()
    assert rpv["subject"] == "Reminder: Please Review Our Fundraising Strategy Plan"
    carol_token_2 = rpv["form_link"].rsplit("/", 1)[-1]
    assert carol_token_1 == carol_token_2, "reminder token must match initial token"

    rr = founder.post(f"{BASE_URL}/api/activation/reviewers/{carol_id}/send", json={"type": "reminder"})
    assert rr.status_code == 200
    carol_after = _get_reviewer_by_email(founder, "bounced@resend.dev")
    assert carol_after["review_status"] == "SENT"
    assert carol_after["last_review_reminder_at"]

    # Reminder to Alice (REVIEWED) → 409
    r = founder.post(f"{BASE_URL}/api/activation/reviewers/{alice_id}/send", json={"type": "reminder"})
    assert r.status_code == 409

    # ---------- (12) Review progress counts ----------
    ov = founder.get(f"{BASE_URL}/api/activation/strategy").json()
    assert ov["review_progress"] == {"invited": 2, "received": 1, "waiting": 1}, ov["review_progress"]
    assert ov["strategy"]["status"] == "Ready for Board Review"

    # ---------- (14) Version safety: re-edit removing marker + re-approve creates v2 ----------
    cleaned = ov["strategy"]["display_text"].replace(marker, "")
    r = founder.put(f"{BASE_URL}/api/activation/strategy", json={"display_text": cleaned})
    assert r.status_code == 200
    ap2 = founder.post(f"{BASE_URL}/api/activation/strategy/approve-review")
    assert ap2.status_code == 200
    v_new = ap2.json()["review_version"]
    assert v_new == v_after_marker + 1

    # Alice's public page should still show frozen text WITH marker (her original version)
    pub_after = requests.get(f"{BASE_URL}/api/strategy-review/{alice_token}").json()
    assert marker in pub_after["strategy_text"], "Alice's frozen version must still contain the marker (version pinning broken)"
    assert pub_after["submitted"] is True

    # Alice's reviewer row keeps her original review_version pinned
    alice_final = _get_reviewer_by_email(founder, "delivered@resend.dev")
    assert alice_final["review_version"] == v_after_marker

    # Founder-facing strategy no longer contains the marker (cleaned)
    ov_final = founder.get(f"{BASE_URL}/api/activation/strategy").json()
    assert marker not in ov_final["strategy"]["display_text"]

    # Module 2 data still intact — Alice's original planning response viewable
    pdata = founder.get(f"{BASE_URL}/api/activation/participants/{alice_id}/response").json()
    assert pdata.get("response"), "Alice's Module 2 response was lost"

    # Nothing marked 'Adopted'
    assert ov_final["strategy"]["status"] == "Ready for Board Review"
