"""Real route/auth/Mongo persistence checks. Requires disposable local Mongo."""
import os
import sys
import unittest
from pathlib import Path

import httpx
from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from auth_service import create_access_token
from clean_platform_routes import create_clean_platform_router

KEYS = ["recruitment", "board-fundraising-game", "strategic-planning", "board-recommitment"]


@unittest.skipUnless(os.environ.get("RECOVERY_ACCEPTANCE") == "1", "Requires isolated Mongo acceptance configuration")
class RecoveredContentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        assert os.environ["MONGO_URL"].startswith("mongodb://127.0.0.1:")
        self.mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
        self.db = self.mongo.nbb_recovery_content_tests
        await self.db.marketing_settings.delete_many({})
        await self.db.users.replace_one({"user_id": "test-admin"}, {
            "user_id": "test-admin", "email": "admin@example.test", "role": "admin"
        }, upsert=True)
        app = FastAPI()
        app.include_router(create_clean_platform_router(self.db))
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.headers = {"Authorization": "Bearer " + create_access_token("test-admin", "admin@example.test")}

    async def asyncTearDown(self):
        await self.client.aclose()
        self.mongo.close()

    async def test_all_eight_pages_save_persist_and_remain_independent(self):
        for key in KEYS + ["offer-" + k for k in KEYS]:
            content = {"heading": "My exact words " + key, "steps": ["One", "Two"], "content_version": "older-version"}
            response = await self.client.put(f"/api/admin/platform/homepages/{key}", headers=self.headers, json={"content": content})
            self.assertEqual(response.status_code, 200, response.text)
            saved = await self.db.marketing_settings.find_one({"key": "clean_homepage_content"})
            self.assertEqual(saved["pages"][key], content)
        # Recreate the application to verify the content is not held in route memory.
        app = FastAPI()
        app.include_router(create_clean_platform_router(self.db))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as restarted:
            for key in KEYS + ["offer-" + k for k in KEYS]:
                response = await restarted.get(f"/api/platform/homepages/{key}")
                self.assertEqual(response.json()["content"]["heading"], "My exact words " + key)

    async def test_admin_authorization_and_unknown_keys(self):
        for key in KEYS + ["offer-" + k for k in KEYS]:
            denied = await self.client.put(f"/api/admin/platform/homepages/{key}", json={"content": {"heading": "Unauthorized"}})
            self.assertEqual(denied.status_code, 401)
        denied = await self.client.put("/api/admin/platform/homepages/recruitment", headers={"Authorization": "Bearer invalid"}, json={"content": {}})
        self.assertEqual(denied.status_code, 401)
        unknown = await self.client.put("/api/admin/platform/homepages/not-a-page", headers=self.headers, json={"content": {}})
        self.assertEqual(unknown.status_code, 404)
        self.assertIsNone(await self.db.marketing_settings.find_one({"key": "clean_homepage_content"}))
