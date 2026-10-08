"""Offline API checks for offer video replacement and saved walkthroughs."""
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
        return copy.deepcopy(self.document) if query["key"] == self.document.get("key") else None

    async def update_one(self, query, update, upsert=False):
        inserted = not self.document
        if inserted:
            if not upsert:
                return
            self.document = {"key": query["key"]}
        elif any(
            self.document.get(key) == value["$ne"] if isinstance(value, dict)
            else self.document.get(key) != value
            for key, value in query.items()
        ):
            return
        values = dict(update.get("$setOnInsert", {})) if inserted else {}
        values.update(update.get("$set", {}))
        for key, value in values.items():
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
        self.app = FastAPI()
        self.app.include_router(routes.create_clean_platform_router(self.db))
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")

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

    async def test_startup_replaces_all_four_old_offer_videos_and_keeps_existing_onboarding(self):
        expected = {
            "recruitment_upgrade": "rOkPAcYRhxE",
            "game_homepage": "iHr6ddUsp9Y",
            "strategic_planning_demonstration": "00zyPIRIAjA",
            "board_recommitment_demonstration": "jCaxd7eQWqk",
        }
        onboarding = {
            "recruitment_welcome": "Onboard0001",
            "game_welcome": "Onboard0002",
            "strategic_planning_welcome": "Onboard0003",
            "board_recommitment_welcome": "Onboard0004",
        }
        self.db.marketing_settings.document["videos"] = {
            **{key: "https://youtu.be/AbCdEf12345" for key in expected},
            **{key: f"https://youtu.be/{video}" for key, video in onboarding.items()},
            "game_dashboard": "https://youtu.be/ZyXwVu54321",
            "board_recruitment_offer": "https://youtu.be/AbCdEf12345",
        }
        await self.app.router.startup()
        response = await self.client.get("/api/platform/videos")
        videos = {row["key"]: row for row in response.json()["videos"]}
        for key, video in {**expected, **onboarding, "game_dashboard": "ZyXwVu54321"}.items():
            self.assertEqual(videos[key]["youtube_id"], video)
        self.assertEqual(self.db.marketing_settings.document["videos"]["board_recruitment_offer"], "https://youtu.be/AbCdEf12345")

    async def test_later_admin_video_changes_and_clears_survive_restart(self):
        await self.app.router.startup()
        for key, url in [("recruitment_upgrade", "https://youtu.be/AbCdEf12345"), ("game_homepage", "")]:
            response = await self.client.put(f"/api/admin/platform/videos/{key}", json={"url": url}, headers={"x-test-admin": "yes"})
            self.assertEqual(response.status_code, 200)
        await self.app.router.startup()
        videos = {row["key"]: row for row in (await self.client.get("/api/platform/videos")).json()["videos"]}
        self.assertEqual(videos["recruitment_upgrade"]["youtube_id"], "AbCdEf12345")
        self.assertEqual(videos["game_homepage"]["url"], "")

    async def test_fresh_settings_have_new_offer_videos_and_matching_onboarding_defaults(self):
        self.db.marketing_settings.document = {}
        await self.app.router.startup()
        videos = {row["key"]: row for row in (await self.client.get("/api/platform/videos")).json()["videos"]}
        for key, video in {
            "recruitment_upgrade": "rOkPAcYRhxE",
            "game_homepage": "iHr6ddUsp9Y",
            "strategic_planning_demonstration": "00zyPIRIAjA",
            "board_recommitment_demonstration": "jCaxd7eQWqk",
            "recruitment_welcome": "PPn-5LpOoZQ",
            "game_welcome": "LZBbDChNQDs",
            "strategic_planning_welcome": "iRMokrM8mR8",
            "board_recommitment_welcome": "5cR1l4qdldg",
        }.items():
            self.assertEqual(videos[key]["youtube_id"], video)
        # Dedicated walkthroughs remain unset so the frontend uses onboarding.
        self.assertEqual(videos["game_dashboard"]["youtube_id"], "")


if __name__ == "__main__":
    unittest.main()
