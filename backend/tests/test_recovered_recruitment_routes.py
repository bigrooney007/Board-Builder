"""Execute the existing scheduling and publication handlers against test Mongo.

Authentication, generated material readiness and outbound delivery are substituted;
the existing handler bodies and Mongo publication guard execute unchanged.
"""
import ast
import asyncio
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException


def handler(name, namespace):
    tree = ast.parse((Path(__file__).resolve().parents[1] / "workspace_routes.py").read_text())
    factory = next(n for n in tree.body if getattr(n, "name", "") == "create_workspace_router")
    node = next(n for n in factory.body if getattr(n, "name", "") == name)
    node.decorator_list = []
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, node], type_ignores=[])), "workspace_routes.py", "exec"), namespace)
    return namespace[name]


@unittest.skipUnless(os.environ.get("RECOVERY_ACCEPTANCE") == "1", "Requires isolated Mongo acceptance configuration")
class RecruitmentRoutes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        assert os.environ["MONGO_URL"].startswith("mongodb://127.0.0.1:")
        self.mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
        self.db = self.mongo.nbb_recovery_recruitment_tests
        for name in ("opportunities", "recruitment_profiles", "generated_materials"):
            await self.db[name].delete_many({})
        await self.db.opportunities.insert_one({"user_id": "test-owner", "organization_name": "Synthetic Organization", "status": "Draft"})
        self.flags = {key: True for key in ("profiles_approved", "scheduling_saved", "application_saved", "materials_generated", "materials_approved")}
        self.broadcasts = []
        async def member(*args): return {"user_id": "test-owner", "review_mode": True}
        async def profile(db, user): return await db.recruitment_profiles.find_one({"user_id": user}) or {}
        async def ensure(*args): return await self.db.opportunities.find_one({"user_id": "test-owner"}, {"_id": 0})
        async def readiness(*args): return dict(self.flags)
        async def material(*args): return {"current": {"structured": {"priority_roles": []}}}
        async def broadcast(*args, **kwargs):
            self.assertTrue(kwargs["force_test"])
            self.broadcasts.append(True)
            return {"broadcast_id": "synthetic", "mode": "test", "recipients": 0}
        async def no_delivery(*args): pass
        self.ns = dict(db=self.db, current_member=member, get_profile=profile, ensure_opportunity=ensure,
                       opportunity_readiness=readiness, get_current_material=material, HTTPException=HTTPException,
                       now_iso=lambda: datetime.now(timezone.utc).isoformat(), asyncio=asyncio, os=os,
                       SUPPORT_PREP_TYPES=["general_interview_invitation"], prepare_support_assets=no_delivery,
                       send_opportunity_broadcast=broadcast, send_campaign_launch_email=no_delivery)

    async def asyncTearDown(self):
        await asyncio.sleep(0)
        self.mongo.close()

    async def test_schedule_validates_saves_and_survives_reload_without_publication(self):
        save = handler("save_interview_scheduling", self.ns)
        read = handler("read_interview_scheduling", self.ns)
        for method, link, availability in [("link", "https://example.test/interview", ""), ("availability", "", "Tuesday 10 AM UTC")]:
            payload = SimpleNamespace(method=method, scheduling_link=link, availability=availability)
            result = await save(payload, None)
            self.assertEqual((await read(None))["scheduling"], result["scheduling"])
        with self.assertRaises(HTTPException):
            await save(SimpleNamespace(method="link", scheduling_link="invalid", availability=""), None)
        self.assertEqual((await self.db.opportunities.find_one({"user_id": "test-owner"}))["status"], "Draft")
        self.assertEqual(self.broadcasts, [])

    async def test_launch_requires_approvals_and_publishes_once(self):
        publish = handler("publish_opportunity", self.ns)
        request = SimpleNamespace(headers={"origin": "http://127.0.0.1:8765"})
        for key in self.flags:
            self.flags[key] = False
            with self.assertRaises(HTTPException) as denied:
                await publish(request)
            self.assertEqual(denied.exception.status_code, 409)
            self.flags[key] = True
        self.assertEqual(self.broadcasts, [])
        result = await publish(request)
        self.assertEqual(result["status"], "Published")
        self.assertEqual(len(self.broadcasts), 1)
        with self.assertRaises(HTTPException) as duplicate:
            await publish(request)
        self.assertEqual(duplicate.exception.status_code, 409)
        self.assertEqual(len(self.broadcasts), 1)
        self.assertEqual(await self.db.opportunities.count_documents({"user_id": "test-owner"}), 1)
