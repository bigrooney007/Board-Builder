"""Iteration 47: verify checkout endpoints + payment status for text-based offer pages."""
import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://deploy-ready-326.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ORIGIN = BASE_URL

CHECKOUT_ENDPOINTS = [
    "diy-checkout",
    "direct-project-checkout",
    "reactivation-diy-checkout",
    "reactivation-project-checkout",
    "activation-diy-checkout",
    "activation-project-checkout",
]


def _post_checkout(endpoint):
    r = requests.post(f"{API}/payments/{endpoint}", json={"origin_url": ORIGIN}, timeout=30)
    return r


def test_all_checkout_endpoints_return_stripe_session():
    failures = []
    for ep in CHECKOUT_ENDPOINTS:
        r = _post_checkout(ep)
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:200]}
        if r.status_code != 200:
            failures.append((ep, r.status_code, body))
            continue
        checkout_url = body.get("checkout_url", "")
        session_id = body.get("session_id", "")
        if "stripe.com" not in checkout_url:
            failures.append((ep, "no stripe url", body))
        if not session_id:
            failures.append((ep, "no session_id", body))
        print(f"OK {ep}: {session_id[:20]}... url_ok={('stripe.com' in checkout_url)}")
    assert not failures, f"Checkout failures: {failures}"


def test_payment_status_fake_id_returns_404():
    r = requests.get(f"{API}/payments/status/cs_fake_iter47_nonexistent", timeout=15)
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text[:200]}"


def test_homepage_and_login_reachable():
    for path in ["/", "/login", "/offer/recruitment", "/offer/reactivation", "/offer/activation"]:
        r = requests.get(f"{BASE_URL}{path}", timeout=15)
        assert r.status_code == 200, f"{path} -> {r.status_code}"


def test_board_transformation_result_invalid_token_endpoint():
    # verify backend token lookup exists and returns 404 for bogus token
    r = requests.get(f"{API}/funnel-leads/board-transformation/result/BOGUS_TOKEN_XYZ", timeout=15)
    # accept 404 or 400 - just want a clean error, not 500
    assert r.status_code in (400, 404), f"Unexpected status {r.status_code}: {r.text[:200]}"
