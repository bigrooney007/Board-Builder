"""Backend tests for the new Board Fundraising Game feature (game_routes.py + payment integration + regression)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://fundraising-game.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "rooney@nonprofitboardbuilder.com"
ADMIN_PW = "PC8JX97y7YjPUel9-gM5gAem"
EXISTING_MEMBER_EMAIL = "module-tester@example.com"
EXISTING_MEMBER_PW = "ModuleTest123!"

TS = int(time.time())


# ---------- helpers ----------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def game_member():
    """Register a new member for game tests."""
    email = f"game-tester-{TS}@example.com"
    pw = "GameTest123!"
    s = requests.Session()
    r = s.post(f"{API}/members/register", json={
        "email": email, "password": pw, "confirm_password": pw,
        "first_name": "Game", "last_name": "Tester"
    })
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    token = r.json().get("access_token") or r.json().get("token") or ""
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return {"session": s, "email": email, "password": pw, "user_id": r.json().get("user_id") or r.json().get("member", {}).get("user_id")}


# ---------- game content ----------
class TestGameContent:
    def test_public_content_defaults(self):
        r = requests.get(f"{API}/game/content")
        assert r.status_code == 200
        c = r.json()["content"]
        assert c["headline"]
        assert len(c["stages"]) == 3
        assert len(c["benefits"]) == 9
        assert len(c["faqs"]) == 5
        assert c["price_display"] == "$497"

    def test_admin_update_content_requires_auth(self):
        r = requests.put(f"{API}/admin/game/content", json={"headline": "hi"})
        assert r.status_code == 401

    def test_admin_update_content_and_restore(self, admin_session):
        r = requests.get(f"{API}/game/content")
        original = r.json()["content"]["headline"]

        new_headline = "TEST_ Headline changed by pytest"
        r = admin_session.put(f"{API}/admin/game/content",
                              json={"headline": new_headline, "unknown_key_ignored": "xxx"})
        assert r.status_code == 200
        assert r.json()["content"]["headline"] == new_headline
        # unknown keys ignored
        assert "unknown_key_ignored" not in r.json()["content"]

        # public GET reflects it
        pub = requests.get(f"{API}/game/content").json()["content"]
        assert pub["headline"] == new_headline

        # restore
        r = admin_session.put(f"{API}/admin/game/content", json={"headline": original})
        assert r.status_code == 200
        assert requests.get(f"{API}/game/content").json()["content"]["headline"] == original


# ---------- flow videos ----------
class TestFlowVideos:
    def test_flow_videos_contains_game_keys(self):
        r = requests.get(f"{API}/flow-videos")
        assert r.status_code == 200
        videos = r.json().get("videos", [])
        keys = {v["key"] for v in videos} if isinstance(videos, list) else set(videos.keys())
        assert "game_homepage" in keys
        assert "game_welcome" in keys

    def test_admin_update_game_welcome_and_restore(self, admin_session):
        videos = requests.get(f"{API}/flow-videos").json()["videos"]
        original = next((v.get("url", "") for v in videos if v["key"] == "game_welcome"), "") if isinstance(videos, list) else videos.get("game_welcome", "")
        r = admin_session.put(f"{API}/admin/flow-videos/game_welcome",
                              json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
        assert r.status_code == 200, r.text
        after = requests.get(f"{API}/flow-videos").json()["videos"]
        got = next((v.get("url", "") for v in after if v["key"] == "game_welcome"), "") if isinstance(after, list) else after.get("game_welcome", "")
        assert "dQw4w9WgXcQ" in got
        # restore
        r = admin_session.put(f"{API}/admin/flow-videos/game_welcome", json={"url": original})
        assert r.status_code == 200


# ---------- profile ----------
class TestGameProfile:
    def test_save_and_get_profile(self, game_member):
        s = game_member["session"]
        r = s.put(f"{API}/game/profile", json={
            "organization": {"name": "TEST_ Org", "website": "https://ex.com"},
            "goal": {"amount": "750000", "deadline": "2026-12-31", "purpose": "Expand programs"},
            "primary_user": {"full_name": "Game Tester"},
        })
        assert r.status_code == 200, r.text
        r = s.get(f"{API}/game/profile")
        assert r.status_code == 200
        data = r.json()
        assert data["unlocked"] is False
        p = data["profile"]
        assert p["organization"]["name"] == "TEST_ Org"
        assert p["goal"]["amount"] == 750000
        assert p["goal"]["purpose"] == "Expand programs"
        assert p["primary_user"]["full_name"] == "Game Tester"
        assert p["profile_completed"] is True


# ---------- situation + dashboard entitlement gate ----------
class TestSituationEntitlement:
    def test_situation_get_forbidden_without_entitlement(self, game_member):
        r = game_member["session"].get(f"{API}/game/situation")
        assert r.status_code == 403

    def test_situation_put_forbidden_without_entitlement(self, game_member):
        r = game_member["session"].put(f"{API}/game/situation", json={"sections": {}, "current_step": 0})
        assert r.status_code == 403

    def test_dashboard_forbidden_without_entitlement(self, game_member):
        r = game_member["session"].get(f"{API}/game/dashboard")
        assert r.status_code == 403


class TestSituationWithEntitlement:
    @pytest.fixture(scope="class")
    def entitled(self, game_member):
        # grant entitlement directly via Mongo
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        async def grant():
            client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            db = client[os.environ.get("DB_NAME", "test_database")]
            await db.members.update_one({"email": game_member["email"]},
                                        {"$addToSet": {"entitlements": "board_fundraising_game"}})
            client.close()
        asyncio.get_event_loop().run_until_complete(grant())
        return game_member

    def test_situation_save_partial_and_resume(self, entitled):
        s = entitled["session"]
        r = s.put(f"{API}/game/situation",
                  json={"sections": {"financial": {"annual_budget": "500000"}}, "current_step": 2})
        assert r.status_code == 200
        r = s.get(f"{API}/game/situation")
        assert r.status_code == 200
        data = r.json()
        assert data["current_step"] == 2
        assert data["sections"]["financial"]["annual_budget"] == "500000"

    def test_situation_complete(self, entitled):
        s = entitled["session"]
        r = s.post(f"{API}/game/situation/complete")
        assert r.status_code == 200
        # GET profile → situation_completed True
        r = s.get(f"{API}/game/profile")
        assert r.json()["profile"].get("situation_completed") is True

    def test_dashboard_with_entitlement(self, entitled):
        s = entitled["session"]
        r = s.get(f"{API}/game/dashboard")
        assert r.status_code == 200
        d = r.json()
        assert "first_name" in d
        assert "goal" in d
        assert "status" in d
        assert isinstance(d.get("areas"), list)
        assert len(d["areas"]) == 7
        assert all(a["locked"] for a in d["areas"])


# ---------- stripe game-checkout ----------
class TestGameCheckout:
    def test_game_checkout_creates_session(self, game_member):
        s = game_member["session"]
        r = s.post(f"{API}/payments/game-checkout", json={"origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "checkout_url" in data
        assert "checkout.stripe.com" in data["checkout_url"] or "stripe.com" in data["checkout_url"]
        assert data["session_id"].startswith("cs_")

        # verify DB row via admin-side (indirect check: this endpoint doesn't expose, so trust returned session_id)
        # we could verify via mongo — skip to keep tests simple.


# ---------- google session negative test ----------
class TestGoogleSessionNegative:
    def test_invalid_session_returns_401(self):
        r = requests.post(f"{API}/members/google/session", json={"session_id": "invalid-xyz-not-real"})
        assert r.status_code == 401


# ---------- regression: existing member login + dashboard ----------
class TestRegressionExistingMember:
    def test_existing_member_login(self):
        r = requests.post(f"{API}/members/login",
                          json={"email": EXISTING_MEMBER_EMAIL, "password": EXISTING_MEMBER_PW})
        assert r.status_code == 200, r.text
        token = r.json().get("access_token") or r.json().get("token")
        assert token
        h = {"Authorization": f"Bearer {token}"}
        r = requests.get(f"{API}/members/dashboard", headers=h)
        assert r.status_code == 200

    def test_support_request_regression(self):
        # module-tester without game entitlement -> support with product board_fundraising_game should 403
        r = requests.post(f"{API}/members/login",
                          json={"email": EXISTING_MEMBER_EMAIL, "password": EXISTING_MEMBER_PW})
        token = r.json().get("access_token") or r.json().get("token")
        h = {"Authorization": f"Bearer {token}"}
        r = requests.post(f"{API}/support-requests", headers=h, json={
            "product": "board_fundraising_game",
            "support_type": "I need help using the platform",
            "module_number": 1,
            "message": "TEST_ regression - should be denied"
        })
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text}"


# ---------- admin game customers ----------
class TestAdminGameCustomers:
    def test_customers_list(self, admin_session):
        r = admin_session.get(f"{API}/admin/game/customers")
        assert r.status_code == 200
        assert "customers" in r.json()
        assert isinstance(r.json()["customers"], list)
