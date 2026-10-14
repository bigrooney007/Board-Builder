"""Exercise actual admin authentication, drafts and public publication offline."""
from copy import deepcopy
import asyncio
import os
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
import sys

import httpx
from fastapi import FastAPI

from backend.tests.test_v2_journeys import TEST_ENV, ROOT
from tests.v2_fixture import Database
from tests.v2_test_providers import external_import_guards


class V2LandingContentTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        environment = patch.dict(os.environ, TEST_ENV)
        environment.start()
        self.addCleanup(environment.stop)
        guards = patch.dict(sys.modules, external_import_guards())
        guards.start()
        self.addCleanup(guards.stop)
        from v2_core import create_indexes, session_token
        from v2_routes import create_v2_router
        from v2_landing_content import DEFAULTS
        from auth_service import create_access_token
        self.defaults = DEFAULTS
        self.db = Database()
        await create_indexes(self.db)
        await self.db.users.insert_one({"user_id": "synthetic-admin", "email": "owner@example.test", "role": "admin"})
        app = FastAPI()
        app.include_router(create_v2_router(self.db))
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)
        self.client.cookies.set("admin_access_token", create_access_token("synthetic-admin", "owner@example.test"))
        self.public = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
        self.addAsyncCleanup(self.public.aclose)
        self.public.cookies.set("nbb_v2_preview", session_token("preview"))

    async def call(self, method, path, data=None, status=200, client=None):
        response = await (client or self.client).request(method, "/api/v2" + path, json=data)
        self.assertEqual(response.status_code, status, response.text)
        return response

    async def test_all_four_defaults_are_available_without_admin_draft_or_metadata(self):
        for product, content in self.defaults.items():
            response = await self.call("GET", "/landing-content/" + product, client=self.public)
            self.assertEqual(response.json(), {"product": product, "content": content})
            self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(await self.db.v2_landing_content.count_documents({}), 0)

    async def test_drafts_stay_private_and_each_page_can_be_published_and_updated_independently(self):
        for product, original in self.defaults.items():
            path = "/admin/landing-content/" + product
            initial = (await self.call("GET", path)).json()
            self.assertEqual(initial["revision"], 0)
            content = deepcopy(original)
            content["headline"] = "My own words for " + product
            content["intro"] = "A complete first paragraph.\n\nA second paragraph in my voice."
            saved = (await self.call("PUT", path, {"revision": 0, "content": content})).json()
            self.assertEqual(saved["draft"], content)
            self.assertEqual(saved["published"], original)
            public = (await self.call("GET", "/landing-content/" + product, client=self.public)).json()
            self.assertEqual(public["content"], original)
            published = (await self.call("POST", path + "/publish", {"revision": saved["revision"]})).json()
            self.assertEqual(published["published"], content)
            self.assertTrue(published["published_at"])
            public = (await self.call("GET", "/landing-content/" + product, client=self.public)).json()
            self.assertEqual(public["content"], content)
            revised = deepcopy(content)
            revised["headline"] = "An unpublished revision"
            saved = (await self.call("PUT", path, {"revision": published["revision"], "content": revised})).json()
            self.assertEqual(saved["published"], content)
            self.assertEqual((await self.call("GET", path)).json()["draft"], revised)
            self.assertEqual((await self.call("GET", "/landing-content/" + product, client=self.public)).json()["content"], content)
        records = await self.db.v2_landing_content.find({}).to_list(None)
        self.assertEqual(len(records), 4)
        self.assertTrue(all(row["published_by"] == "synthetic-admin" for row in records))
        self.assertEqual(await self.db.v2_journeys.count_documents({}), 0)
        self.assertEqual(await self.db.v2_email_outbox.count_documents({}), 0)

    async def test_non_admin_cannot_read_save_or_publish_drafts(self):
        path = "/admin/landing-content/recruit"
        for method, endpoint, payload in [("GET", path, None), ("PUT", path, {"revision": 0, "content": self.defaults["recruit"]}), ("POST", path + "/publish", {"revision": 0})]:
            await self.call(method, endpoint, payload, status=401, client=self.public)
        from v2_core import session_token
        self.public.cookies.set("nbb_v2_owner_fake-journey", session_token("owner", journey_id="fake-journey", email="leader@example.test"))
        await self.call("GET", path, status=401, client=self.public)
        self.assertEqual(await self.db.v2_landing_content.count_documents({}), 0)

    async def test_cross_site_admin_mutation_is_rejected(self):
        response = await self.client.put("/api/v2/admin/landing-content/recruit", json={"revision": 0, "content": self.defaults["recruit"]}, headers={"Origin": "https://unrelated.example.test"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(await self.db.v2_landing_content.count_documents({}), 0)

    async def test_stale_saves_and_publication_cannot_overwrite_another_session(self):
        path = "/admin/landing-content/recruit"
        saved = (await self.call("PUT", path, {"revision": 0, "content": self.defaults["recruit"]})).json()
        changed = deepcopy(saved["draft"])
        changed["headline"] = "The latest draft"
        newer = (await self.call("PUT", path, {"revision": saved["revision"], "content": changed})).json()
        await self.call("PUT", path, {"revision": saved["revision"], "content": self.defaults["recruit"]}, status=409)
        await self.call("POST", path + "/publish", {"revision": saved["revision"]}, status=409)
        self.assertEqual((await self.call("GET", path)).json(), newer)
        responses = await asyncio.gather(*[self.client.put("/api/v2" + path, json={"revision": newer["revision"], "content": changed}) for _ in range(2)])
        self.assertEqual(sorted(response.status_code for response in responses), [200, 409])

    async def test_validation_does_not_accept_product_prices_routes_or_malformed_content(self):
        path = "/admin/landing-content/recruit"
        bad_values = []
        for key, value in [("headline", " "), ("headline", "x" * 301), ("intro", "x" * 12001), ("teaching", []), ("teaching", [["Heading"]]), ("teaching", [["Heading", "Body"]] * 21), ("teaching", "not a list")]:
            content = deepcopy(self.defaults["recruit"])
            content[key] = value
            bad_values.append(content)
        content = deepcopy(self.defaults["recruit"])
        content["price"] = 1
        bad_values.append(content)
        for content in bad_values:
            await self.call("PUT", path, {"revision": 0, "content": content}, status=422)
        for number in (True, -1, "0", None):
            await self.call("PUT", path, {"revision": number, "content": self.defaults["recruit"]}, status=422)
        await self.call("GET", "/landing-content/unknown", status=404, client=self.public)
        await self.call("POST", path + "/publish", {"revision": 0}, status=409)
        self.assertEqual(await self.db.v2_landing_content.count_documents({}), 0)
