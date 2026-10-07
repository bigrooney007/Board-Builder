"""Offline API checks for independently saved dashboard walkthroughs."""
import copy
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI, HTTPException


class Settings:
    def __init__(self):
        self.document = {"key": "flow_videos", "videos": {"game_homepage": "https://youtu.be/rsf_QZfEId8"}}

    async def find_one(self, query, projection=None):
        return copy.deepcopy(self.document) if query["key"] == self.document["key"] else None

    async def update_one(self, query, update, upsert=False):
        for key, value in update.get("$set", {}).items():
            parts = key.split(".")
            target = self.document
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = value


async def authenticate(request, db):
    if request.headers.get("x-test-admin") != "yes":
        raise HTTPException(401, "Admin required")


with patch.dict(sys.modules, {"auth_service": types.SimpleNamespace(authenticate_admin=authenticate)}):
    spec = importlib.util.spec_from_file_location("walkthrough_test_routes", Path(__file__).resolve().parents[1] / "clean_platform_routes.py")
    routes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(routes)


class DashboardWalkthroughVideos(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = types.SimpleNamespace(marketing_settings=Settings())
        app = FastAPI()
        app.include_router(routes.create_clean_platform_router(self.db))
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_admin_saves_replaces_and_clears_each_walkthrough_without_changing_offer_video(self):
        headers = {"x-test-admin": "yes"}
        keys = ["recruitment_dashboard", "game_dashboard", "strategic_planning_dashboard", "board_recommitment_dashboard"]
        for key in keys:
            for value in ["https://youtu.be/AbCdEf12345", "https://www.youtube.com/watch?v=ZyXwVu54321", ""]:
                response = await self.client.put(f"/api/admin/platform/videos/{key}", json={"url": value}, headers=headers)
                self.assertEqual(response.status_code, 200, response.text)
                public = await self.client.get("/api/platform/videos")
                video = next(row for row in public.json()["videos"] if row["key"] == key)
                self.assertEqual(video["stage"], "dashboard")
                self.assertEqual(video["url"], value)
                self.assertEqual(video["youtube_id"], "" if not value else routes.youtube_id(value))
                self.assertEqual(next(row for row in public.json()["videos"] if row["key"] == "game_homepage")["youtube_id"], "rsf_QZfEId8")

    async def test_only_admin_can_change_walkthroughs_and_unknown_keys_are_rejected(self):
        response = await self.client.put("/api/admin/platform/videos/game_dashboard", json={"url": "AbCdEf12345"})
        self.assertEqual(response.status_code, 401)
        response = await self.client.put("/api/admin/platform/videos/unknown_dashboard", json={"url": "AbCdEf12345"}, headers={"x-test-admin": "yes"})
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("game_dashboard", self.db.marketing_settings.document["videos"])


if __name__ == "__main__":
    unittest.main()
