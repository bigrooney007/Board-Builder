"""Batch 2 — Activation Module 2 (Fundraising Planning) end-to-end verification.

Single sequential end-to-end scenario (loadscope pins to one worker) exercising:
- entitlement gating (403 for non-activation user)
- overview does not trigger AI generation
- participant add / duplicate / delete rules
- master form real Claude generation with polling
- edit + save + approve v1
- send-before-approval blocked
- deterministic initial + reminder email preview, token reuse
- send actual initial + reminder email via Resend
- public GET/POST /planning-form/{token}, prefill, submission, resubmit 409
- founder VIEW RESPONSE
- version safety: edit after approve → Draft, re-approve → v2, alice's v1 link keeps v1
- token isolation, invalid token 404
"""
import os
import time
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

FOUNDER_EMAIL = "activation-tester-1786708997@example.com"
FOUNDER_PASSWORD = os.environ["ACTIVATION_TESTER_PASSWORD"]
NO_ENT_EMAIL = "module-tester@example.com"
NO_ENT_PASSWORD = os.environ["MODULE_TESTER_PASSWORD"]

ALICE_EMAIL = "delivered@resend.dev"
BOB_EMAIL = "test-b2-bob@example.com"


def _login(session, email, password):
    r = session.post(f"{BASE_URL}/api/members/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()


def _get_participant_by_email(session, email):
    overview = session.get(f"{BASE_URL}/api/activation/planning").json()
    for p in overview["participants"]:
        if p["email"].lower() == email.lower():
            return p
    return None


def test_batch2_end_to_end():
    """Full sequential scenario. Any assertion failure short-circuits the flow."""
    founder = requests.Session()
    _login(founder, FOUNDER_EMAIL, FOUNDER_PASSWORD)

    other = requests.Session()
    _login(other, NO_ENT_EMAIL, NO_ENT_PASSWORD)

    # ---- Access control ----
    r = other.get(f"{BASE_URL}/api/activation/planning")
    assert r.status_code == 403, f"module-tester must be 403; got {r.status_code}"

    r = requests.get(f"{BASE_URL}/api/activation/planning")
    assert r.status_code == 401

    # ---- Overview + no-generation-on-load ----
    overview = founder.get(f"{BASE_URL}/api/activation/planning")
    assert overview.status_code == 200
    o = overview.json()
    assert o["has_intake"] is True
    assert set(o["progress"].keys()) >= {"invited", "received", "waiting", "selected"}

    before_status = founder.get(f"{BASE_URL}/api/activation/planning-form").json().get("status")
    founder.get(f"{BASE_URL}/api/activation/planning")
    after_status = founder.get(f"{BASE_URL}/api/activation/planning-form").json().get("status")
    # If it was NONE it should still be NONE (no auto-gen on page load); if already Draft/Approved it should not regress.
    assert (before_status == after_status) or (before_status in (None, "NONE") and after_status in (None, "NONE"))

    # ---- Clean up leftovers from previous runs so we start deterministic on Alice (NOT SENT) ----
    for email in (ALICE_EMAIL, BOB_EMAIL):
        existing = _get_participant_by_email(founder, email)
        if existing and existing["status"] == "NOT SENT":
            founder.delete(f"{BASE_URL}/api/activation/participants/{existing['participant_id']}")

    # ---- Add Alice ----
    r = founder.post(f"{BASE_URL}/api/activation/participants",
                     json={"name": "TEST Batch2 Alice", "email": ALICE_EMAIL, "phone": "555-1000", "role": "Board Chair"})
    assert r.status_code == 201
    body = r.json()
    if body["status"] == "exists":
        # existing = already SENT/COMPLETED from a prior run — use it
        alice = body["participant"]
    else:
        assert body["status"] == "created"
        alice = body["participant"]
    alice_id = alice["participant_id"]
    print(f"Alice id={alice_id} status={alice['status']}")

    # Duplicate add returns exists
    r2 = founder.post(f"{BASE_URL}/api/activation/participants",
                      json={"name": "TEST Batch2 Alice", "email": ALICE_EMAIL})
    assert r2.status_code in (200, 201)
    assert r2.json()["status"] == "exists"

    # ---- Add Bob ----
    existing_bob = _get_participant_by_email(founder, BOB_EMAIL)
    if existing_bob and existing_bob["status"] != "NOT SENT":
        pytest.fail("Leftover Bob is in non-NOT-SENT state; manual cleanup required")
    r = founder.post(f"{BASE_URL}/api/activation/participants",
                     json={"name": "TEST Batch2 Bob", "email": BOB_EMAIL, "role": "Treasurer"})
    assert r.status_code == 201
    bob_id = r.json()["participant"]["participant_id"]

    # Removing a NOT SENT participant works
    r = founder.post(f"{BASE_URL}/api/activation/participants",
                     json={"name": "TEST Batch2 Del", "email": "test-b2-del@example.com"})
    del_id = r.json()["participant"]["participant_id"]
    d = founder.delete(f"{BASE_URL}/api/activation/participants/{del_id}")
    assert d.status_code == 200 and d.json()["status"] == "removed"

    # ---- Form generation ----
    form_state = founder.get(f"{BASE_URL}/api/activation/planning-form").json()
    if form_state.get("status") not in ("Draft", "Approved"):
        gen = founder.post(f"{BASE_URL}/api/activation/planning-form/generate")
        assert gen.status_code == 200
        assert gen.json()["status"] in ("Generating", "Draft", "Approved")
        # Poll up to 120s
        deadline = time.time() + 120
        while time.time() < deadline:
            cur = founder.get(f"{BASE_URL}/api/activation/planning-form").json()
            if cur.get("status") in ("Draft", "Approved", "Failed"):
                form_state = cur
                break
            time.sleep(3)
    assert form_state["status"] in ("Draft", "Approved"), f"generation ended status={form_state.get('status')} err={form_state.get('generation_error')}"
    content = form_state["content"]
    assert content
    # 11 sections in exact order
    assert [s["key"] for s in content["sections"]] == [
        "goal", "audiences", "opportunities", "relationships", "attracting",
        "outreach", "involvement", "ownership", "support", "ninety", "additional",
    ]
    # 18 questions total
    assert sum(len(s["questions"]) for s in content["sections"]) == 18
    # No AI mention / placeholders in introduction
    intro_lower = content["introduction"].lower()
    assert "artificial intelligence" not in intro_lower
    assert "[placeholder]" not in intro_lower and "[organization" not in intro_lower
    # Fixed strings
    assert "combined with ideas from other Board Members" in content["confirmation_text"]
    assert "Selecting a type" in content["relationship_note"]
    # 90-day fixed prompt
    ninety_q = [q for s in content["sections"] if s["key"] == "ninety" for q in s["questions"]][0]
    assert "If we could accomplish three fundraising things in the next 90 days" in ninety_q["prompt"]

    # ---- Send before approval blocked (only if not already Approved) ----
    if form_state["status"] == "Draft" and alice["status"] == "NOT SENT":
        r = founder.post(f"{BASE_URL}/api/activation/participants/{alice_id}/send", json={"type": "initial"})
        assert r.status_code == 409

    # ---- Edit + save (keep Draft) ----
    cur = founder.get(f"{BASE_URL}/api/activation/planning-form").json()
    prompts = {q["id"]: q["prompt"] for s in cur["content"]["sections"] for q in s["questions"]}
    prompts["goal_important"] = "[TEST-EDITED PROMPT] What matters most about what we are trying to accomplish?"
    r = founder.put(f"{BASE_URL}/api/activation/planning-form", json={
        "introduction": cur["content"]["introduction"] + "\n\n[TEST-EDIT] founder edit marker.",
        "goal_context": cur["content"].get("goal_context", ""),
        "question_prompts": prompts,
    })
    assert r.status_code == 200 and r.json()["status"] == "Draft"
    again = founder.get(f"{BASE_URL}/api/activation/planning-form").json()
    assert "[TEST-EDIT]" in again["content"]["introduction"]
    assert again["edited_since_generation"] is True

    # ---- Approve → next version ----
    prev_version = again.get("approved_version", 0)
    ap = founder.post(f"{BASE_URL}/api/activation/planning-form/approve")
    assert ap.status_code == 200
    v_now = ap.json()["approved_version"]
    assert v_now == prev_version + 1
    print(f"Approved v{v_now}")

    # ---- Email preview (deterministic) ----
    p = founder.get(f"{BASE_URL}/api/activation/participants/{alice_id}/email-preview",
                    params={"type": "initial"}).json()
    assert p["subject"].startswith("Help Us Build Our Fundraising Plan | ")
    assert "Rather than creating the plan and bringing it to the Board after the fact" in p["body"]
    assert "/planning-form/" in p["form_link"]
    alice_link_initial = p["form_link"]

    # ---- Send initial (idempotent-ish; only if currently NOT SENT) ----
    alice_now = _get_participant_by_email(founder, ALICE_EMAIL)
    if alice_now["status"] == "NOT SENT":
        r = founder.post(f"{BASE_URL}/api/activation/participants/{alice_id}/send", json={"type": "initial"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "sent"
        alice_now = _get_participant_by_email(founder, ALICE_EMAIL)
        assert alice_now["status"] == "SENT"
        assert alice_now.get("last_sent_at")
        assert alice_now.get("form_version") == v_now
        alice_form_version = v_now
    else:
        alice_form_version = alice_now.get("form_version") or v_now

    # ---- Removing a SENT/COMPLETED participant is blocked ----
    r = founder.delete(f"{BASE_URL}/api/activation/participants/{alice_id}")
    assert r.status_code == 409

    # ---- Reminder preview reuses same token ----
    if alice_now["status"] == "SENT":
        rp = founder.get(f"{BASE_URL}/api/activation/participants/{alice_id}/email-preview",
                         params={"type": "reminder"}).json()
        assert rp["subject"] == "Reminder: Help Us Build Our Fundraising Plan"
        assert rp["form_link"] == alice_link_initial

        # Send reminder
        r = founder.post(f"{BASE_URL}/api/activation/participants/{alice_id}/send", json={"type": "reminder"})
        assert r.status_code == 200

    # ---- Reminder on NOT SENT (Bob) is blocked ----
    r = founder.post(f"{BASE_URL}/api/activation/participants/{bob_id}/send", json={"type": "reminder"})
    assert r.status_code == 409

    # ---- Call script + call notes ----
    cs = founder.get(f"{BASE_URL}/api/activation/participants/{alice_id}/call-script").json()
    assert cs["script"].startswith("Hi ")
    assert " from " in cs["script"].split("\n")[0]

    r = founder.put(f"{BASE_URL}/api/activation/participants/{alice_id}/call-notes",
                    json={"notes": "TEST batch2 notes"})
    assert r.status_code == 200
    cs2 = founder.get(f"{BASE_URL}/api/activation/participants/{alice_id}/call-script").json()
    assert cs2["call_notes"] == "TEST batch2 notes"

    # ---- Public: invalid token ----
    r = requests.get(f"{BASE_URL}/api/planning-form/not-a-real-token-xxxx")
    assert r.status_code == 404

    # ---- Public: get with token ----
    alice_token = alice_link_initial.rstrip("/").split("/")[-1]
    r = requests.get(f"{BASE_URL}/api/planning-form/{alice_token}")
    assert r.status_code == 200
    pf = r.json()
    if alice_now["status"] != "COMPLETED":
        assert pf["submitted"] is False
    assert pf["prefill"]["email"] == ALICE_EMAIL
    assert pf["organization_name"]
    assert len(pf["form"]["sections"]) == 11
    # Ensure NO founder intake / other participants leaked into the payload
    assert "founder_intake" not in pf
    assert "participants" not in pf

    # ---- Submit (only if not already completed) ----
    if not pf["submitted"]:
        payload = {
            "full_name": "TEST Batch2 Alice",
            "email": ALICE_EMAIL,
            "role": "Board Chair",
            "goal_important": "The clarity of what the funding will accomplish is what stands out most.",
            "goal_clarity": "Would love more detail on Y1 milestones.",
            "funding_audiences": ["Individuals", "Local Businesses"],
            "audiences_why": "They are close to the mission and have supported before.",
            "opportunities": ["Individual Giving", "Events"],
            "opportunity_priority": "Individual Giving because it is repeatable.",
            "network_categories": ["Business Owners", "Community Leaders"],
            "specific_relationships": "A few local business owners I can approach.",
            "why_support": "The outcomes matter and are measurable.",
            "talk_about": "Specific stories about program impact.",
            "outreach_methods": ["Personal Introductions", "One-to-One Meetings"],
            "outreach_add": "",
            "participation_activities": ["Making Introductions", "Thanking / Stewarding Donors"],
            "ownership": "I can own donor stewardship communications.",
            "support_needed": ["Talking Points", "Case for Support"],
            "ninety_day_priorities": "Refresh case for support; 10 introductions; steward top 20 donors.",
            "fundraising_idea": "A small breakfast with 8 potential supporters.",
            "final_thoughts": "Excited to help.",
            "confirmation": True,
        }
        r = requests.post(f"{BASE_URL}/api/planning-form/{alice_token}", json=payload)
        assert r.status_code == 201, r.text
        assert r.json()["status"] == "submitted"

    # ---- Resubmit blocked ----
    r = requests.post(f"{BASE_URL}/api/planning-form/{alice_token}",
                      json={"full_name": "x", "email": ALICE_EMAIL,
                            "goal_important": "x", "funding_audiences": ["Individuals"], "audiences_why": "x",
                            "opportunities": ["Events"], "opportunity_priority": "x",
                            "network_categories": ["Business Owners"], "why_support": "x", "talk_about": "x",
                            "outreach_methods": ["Email Outreach"], "participation_activities": ["Making Introductions"],
                            "ownership": "x", "support_needed": ["Training"],
                            "ninety_day_priorities": "x", "confirmation": True})
    assert r.status_code == 409

    # ---- Public GET shows submitted ----
    r = requests.get(f"{BASE_URL}/api/planning-form/{alice_token}").json()
    assert r["submitted"] is True

    # ---- Founder VIEW RESPONSE ----
    vr = founder.get(f"{BASE_URL}/api/activation/participants/{alice_id}/response").json()
    assert vr["response"]["goal_important"]
    assert vr["form_version"] == alice_form_version
    for banned in ("ai_summary", "score", "ranking", "ai_ranking", "ai_analysis"):
        assert banned not in vr["response"]

    # Overview reflects COMPLETED status + progress counts
    ov = founder.get(f"{BASE_URL}/api/activation/planning").json()
    alice_final = next(p for p in ov["participants"] if p["participant_id"] == alice_id)
    assert alice_final["status"] == "COMPLETED"
    assert alice_final.get("submitted_at")
    assert ov["progress"]["received"] >= 1
    assert ov["progress"]["invited"] >= 1

    # ---- Version safety: create a FRESH participant Carol, send under current version,
    #      then edit + reapprove — Carol's token must still serve the version she was sent under.
    carol_email = "bounced@resend.dev"
    # Delete leftover Carol if present and NOT SENT so we can freshly send under v_now
    existing_carol = _get_participant_by_email(founder, carol_email)
    if existing_carol and existing_carol["status"] == "NOT SENT":
        founder.delete(f"{BASE_URL}/api/activation/participants/{existing_carol['participant_id']}")
        existing_carol = None
    if existing_carol:
        # Carol carried over from a prior run — reuse her existing SENT state.
        # She was sent under an earlier version; that version's content is what her token must serve.
        carol_id = existing_carol["participant_id"]
        print(f"NOTE: leftover Carol id={carol_id} status={existing_carol['status']} form_version={existing_carol['form_version']} — reusing")
    else:
        r = founder.post(f"{BASE_URL}/api/activation/participants",
                         json={"name": "TEST Batch2 Carol", "email": carol_email, "role": "Board Member"})
        assert r.status_code == 201
        carol_id = r.json()["participant"]["participant_id"]
        r = founder.post(f"{BASE_URL}/api/activation/participants/{carol_id}/send", json={"type": "initial"})
        assert r.status_code == 200, r.text
    carol_after_send = _get_participant_by_email(founder, carol_email)
    carol_version = carol_after_send["form_version"]
    assert carol_version >= 1, f"Carol form_version={carol_version} not stamped"
    carol_preview = founder.get(f"{BASE_URL}/api/activation/participants/{carol_id}/email-preview").json()
    carol_token = carol_preview["form_link"].rstrip("/").split("/")[-1]
    # Snapshot Carol's frozen intro under v_now
    carol_intro_v1 = requests.get(f"{BASE_URL}/api/planning-form/{carol_token}").json()["form"]["introduction"]

    # Edit → Draft → Approve v_now+1 with a distinguishing marker
    cur = founder.get(f"{BASE_URL}/api/activation/planning-form").json()
    prompts = {q["id"]: q["prompt"] for s in cur["content"]["sections"] for q in s["questions"]}
    version_marker = f"[TEST-VSAFE-{int(time.time())}]"
    r = founder.put(f"{BASE_URL}/api/activation/planning-form", json={
        "introduction": cur["content"]["introduction"] + f"\n\n{version_marker}",
        "goal_context": cur["content"].get("goal_context", ""),
        "question_prompts": prompts,
    })
    assert r.status_code == 200 and r.json()["status"] == "Draft"
    ap2 = founder.post(f"{BASE_URL}/api/activation/planning-form/approve")
    assert ap2.status_code == 200
    new_v = ap2.json()["approved_version"]
    assert new_v == v_now + 1

    carol_intro_after = requests.get(f"{BASE_URL}/api/planning-form/{carol_token}").json()["form"]["introduction"]
    assert version_marker not in carol_intro_after, "Carol's v_now frozen link leaked new-version content"
    assert carol_intro_after == carol_intro_v1, "Carol's frozen content mutated after re-approval"

    # Carol was SENT so deletion should be blocked (409); leave her in place
    r = founder.delete(f"{BASE_URL}/api/activation/participants/{carol_id}")
    assert r.status_code == 409

    # ---- Cleanup Bob (leave Alice + form for Batch 3 handoff per spec) ----
    d = founder.delete(f"{BASE_URL}/api/activation/participants/{bob_id}")
    assert d.status_code == 200

    print("BATCH2_E2E_PASSED")
