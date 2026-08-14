"""Backend tests for the /board-recruitment-proposal direct project checkout flow."""
import os
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # Read frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def db():
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def test_payment_config_unchanged(api):
    r = api.get(f"{BASE_URL}/api/payments/config")
    assert r.status_code == 200
    d = r.json()
    assert d["recruit_with_rooney_997_live"] is False
    assert d["stripe_mode"] == "test"


def test_direct_project_checkout_creates_session(api, db):
    r = api.post(f"{BASE_URL}/api/payments/direct-project-checkout",
                 json={"origin_url": "https://example.com"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "checkout_url" in data and "session_id" in data
    assert data["checkout_url"].startswith("https://")
    session_id = data["session_id"]

    # Verify Stripe session
    import stripe
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    session = stripe.checkout.Session.retrieve(session_id)
    assert session.amount_total == 199700
    assert session.currency == "usd"
    assert session.mode == "payment"
    assert session.metadata.get("purchase_source") == "direct_board_recruitment_project"
    assert session.metadata.get("offer") == "Board Recruitment Project"
    assert "/board-recruitment-intake" in session.success_url
    assert "board-recruitment-proposal?checkout=cancelled" in session.cancel_url
    # Ensure it's one-time (not recurring)
    line_items = stripe.checkout.Session.list_line_items(session_id, limit=1)
    price = line_items.data[0].price
    assert price.recurring is None
    assert price.unit_amount == 199700

    # Verify DB transaction row
    async def check_db():
        row = await db.payment_transactions.find_one({"session_id": session_id})
        assert row is not None
        assert row["amount"] == 199700
        assert row["offer_source"] == "direct_board_recruitment_project"
        assert row["purchase_source"] == "direct_board_recruitment_project"
        assert row["status"] == "initiated"
        assert row["payment_status"] == "pending"
    asyncio.get_event_loop().run_until_complete(check_db())

    # cleanup
    async def cleanup():
        await db.payment_transactions.delete_one({"session_id": session_id})
    asyncio.get_event_loop().run_until_complete(cleanup())


def test_direct_project_checkout_invalid_origin(api):
    r = api.post(f"{BASE_URL}/api/payments/direct-project-checkout",
                 json={"origin_url": "notaurl"})
    assert r.status_code == 400


def test_status_missing_session(api):
    r = api.get(f"{BASE_URL}/api/payments/status/cs_test_nonexistent_xyz")
    assert r.status_code == 404


def test_status_idempotent_for_pending(api, db):
    # create a session then poll status twice; row count must stay at 1
    r = api.post(f"{BASE_URL}/api/payments/direct-project-checkout",
                 json={"origin_url": "https://example.com"})
    session_id = r.json()["session_id"]
    a = api.get(f"{BASE_URL}/api/payments/status/{session_id}")
    b = api.get(f"{BASE_URL}/api/payments/status/{session_id}")
    assert a.status_code == 200 and b.status_code == 200
    assert a.json()["payment_status"] in ("pending", "paid")

    async def count():
        return await db.payment_transactions.count_documents({"session_id": session_id})
    assert asyncio.get_event_loop().run_until_complete(count()) == 1
    async def cleanup():
        await db.payment_transactions.delete_one({"session_id": session_id})
    asyncio.get_event_loop().run_until_complete(cleanup())


def test_claim_purchase_rejects_direct_project(api, db):
    """A direct-project session cannot be claimed as a Recruitment program purchase."""
    # Register a member
    import uuid
    email = f"test_brp_{uuid.uuid4().hex[:8]}@example.com"
    reg = api.post(f"{BASE_URL}/api/members/register",
                   json={"email": email, "password": os.environ["TEST_ACCOUNT_PASSWORD"], "confirm_password": os.environ["TEST_ACCOUNT_PASSWORD"],
                         "first_name": "BRP", "last_name": "Tester", "organization": "Test Org"})
    if reg.status_code not in (200, 201):
        pytest.skip(f"member register unavailable: {reg.status_code} {reg.text[:120]}")
    token = reg.json().get("token") or reg.json().get("access_token")
    if not token:
        pytest.skip("no token from register")

    # Create a direct-project session (unpaid)
    ck = api.post(f"{BASE_URL}/api/payments/direct-project-checkout",
                  json={"origin_url": "https://example.com"})
    session_id = ck.json()["session_id"]

    # Attempt claim
    r = api.post(f"{BASE_URL}/api/members/claim-purchase",
                 json={"session_id": session_id},
                 headers={"Authorization": f"Bearer {token}"})
    # Expect 400 (not a Recruitment program purchase) or 402 (unpaid)
    assert r.status_code in (400, 402), r.text

    # cleanup
    async def cleanup():
        await db.payment_transactions.delete_one({"session_id": session_id})
        await db.members.delete_one({"email": email})
    asyncio.get_event_loop().run_until_complete(cleanup())


def test_recruit_with_rooney_still_gated(api):
    r = api.post(f"{BASE_URL}/api/payments/rooney-checkout",
                 json={"origin_url": "https://example.com"})
    assert r.status_code == 403
    assert "not open" in r.text.lower()


def test_existing_pages_still_load(api):
    # Regression: SPA index served for these routes
    for path in ["/", "/recruit", "/recruit/process", "/recruit-with-rooney", "/reactivate", "/activate"]:
        r = api.get(f"{BASE_URL}{path}")
        assert r.status_code == 200, f"{path} -> {r.status_code}"
