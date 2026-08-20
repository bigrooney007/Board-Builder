"""Iteration 50: canonical videos, DWY $5,497 pricing, conditional_offer gating removal."""
import os
import re
import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
base = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base.rstrip("/")
API = f"{BASE_URL}/api"
STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY") or backend_env.get("STRIPE_SECRET_KEY")

EXPECTED = {
    "recruitment": ["MADZN-LqAvA", "ZDudgx9O1Vg", "tESJV4jJVWs", "w4-kn3tayRQ", "0G9NC6A7vTE", "T_JBGaSBX6M"],
    "reactivation": ["2wdW11ZInFQ", "FekXiaQAF8g", "DHXzONsqlcA", "NKN08iH8-FQ", "cursn2RtzzQ"],
    "activation": ["kcQqxpFALLA", "UmiZJS6Ygr8", "uNH70p8xQMI", "zshP-kDiGAM", "ngP-VDBVEHs"],
}

ACCOUNTS = {
    "recruitment": ("module-tester@example.com", "ModuleTest123!"),
    "reactivation": ("test_ui_batch2_6ca82f@example.com", "UITest123!"),
    "activation": ("activation-tester-1786708997@example.com", "ActTest123!"),
}


def member_session(product):
    email, password = ACCOUNTS[product]
    s = requests.Session()
    r = s.post(f"{API}/members/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code != 200:
        r = s.post(f"{API}/auth/member/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"member login failed for {product}: {r.status_code} {r.text[:300]}"
    token = r.json().get("access_token") or r.json().get("token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# ---------- VIDEOS backend ----------
@pytest.mark.parametrize("product", ["recruitment", "reactivation", "activation"])
def test_canonical_videos(product):
    s = member_session(product)
    r = s.get(f"{API}/courses/{product}/self-guided", timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    modules = r.json().get("modules", [])
    assert len(modules) >= len(EXPECTED[product])
    for index, expected_id in enumerate(EXPECTED[product]):
        url = modules[index].get("youtube_url", "")
        assert url == f"https://youtu.be/{expected_id}", f"{product} module {index+1}: got {url}"


# ---------- PRICING backend ----------
def stripe_amount(session_url_or_id):
    session_id = session_url_or_id
    match = re.search(r"(cs_[A-Za-z0-9_]+)", session_url_or_id)
    if match:
        session_id = match.group(1)
    r = requests.get(f"https://api.stripe.com/v1/checkout/sessions/{session_id}",
                     auth=(STRIPE_KEY, ""), timeout=30)
    assert r.status_code == 200, f"stripe retrieve failed: {r.text[:300]}"
    return r.json()["amount_total"]


@pytest.mark.parametrize("endpoint,expected", [
    ("direct-project-checkout", 549700),
    ("reactivation-project-checkout", 549700),
    ("activation-project-checkout", 549700),
    ("diy-checkout", 49700),
    ("reactivation-diy-checkout", 49700),
    ("activation-diy-checkout", 49700),
])
def test_checkout_amounts(endpoint, expected):
    r = requests.post(f"{API}/payments/{endpoint}", json={"origin_url": BASE_URL}, timeout=60)
    assert r.status_code == 200, f"{endpoint}: {r.status_code} {r.text[:300]}"
    data = r.json()
    assert data.get("checkout_url", "").startswith("https://"), data
    session_ref = data.get("session_id") or data["checkout_url"]
    assert stripe_amount(session_ref) == expected, f"{endpoint} amount mismatch"


# ---------- conditional_offer gating ----------
def test_conditional_offer_gating_removed_in_code():
    src = open("/app/backend/workspace_routes.py").read()
    marker = 'if payload.type == "conditional_offer":'
    assert marker in src
    block = src[src.index(marker):src.index(marker) + 3000]
    assert "409" not in block, "409 gating still present in conditional_offer block"


# ---------- NEXT STEP completion persistence ----------
def test_next_step_completion_persists():
    s = member_session("recruitment")
    r = s.post(f"{API}/courses/progress",
               json={"product": "recruitment_self_guided", "module_number": 1, "action": "completed"}, timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    course = s.get(f"{API}/courses/recruitment/self-guided", timeout=30).json()
    module1 = next(m for m in course["modules"] if m["number"] == 1)
    assert module1["completed"] is True, module1
    assert course["modules_completed"] >= 1
