"""Offline HTTP regressions for setup order and Mongo-indexed Admin test launches.

Run with unittest. External authentication and delivery are substituted; the real
route factories, validation and seeders run against an indexed in-memory store.
"""
import ast
import asyncio
import copy
import hashlib
import html
import json
import logging
import os
import re
import secrets
import sys
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
from fastapi import APIRouter, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from pymongo.errors import DuplicateKeyError

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from game_content import EDITABLE_FIELDS, merged_sections
from game_content_v3 import GAME_V3
from game_response_quality import is_meaningful_game_response, response_input_hash, response_texts


def field_value(row, key):
    for part in key.split("."):
        if not isinstance(row, dict) or part not in row:
            return None
        row = row[part]
    return row


def matches(row, query):
    for key, expected in query.items():
        actual = field_value(row, key)
        if isinstance(expected, dict):
            if "$ne" in expected and actual == expected["$ne"]:
                return False
            if "$in" in expected and actual not in expected["$in"]:
                return False
            if "$exists" in expected and (actual is not None) != expected["$exists"]:
                return False
        elif actual != expected:
            return False
    return True


def set_field(row, key, value):
    parts = key.split(".")
    for part in parts[:-1]:
        row = row.setdefault(part, {})
    row[parts[-1]] = copy.deepcopy(value)


class Cursor:
    def __init__(self, rows):
        self.rows = copy.deepcopy(rows)

    def sort(self, key, direction=1):
        keys = key if isinstance(key, list) else [(key, direction)]
        for field, order in reversed(keys):
            self.rows.sort(key=lambda row: str(field_value(row, field) or ""), reverse=order < 0)
        return self

    async def to_list(self, length):
        return self.rows[:length]


class IndexedCollection:
    def __init__(self):
        self.rows = []
        self.unique_indexes = []

    def validate(self, candidate, original=None):
        for fields in self.unique_indexes:
            value = tuple(field_value(candidate, field) for field in fields)
            # Mongo's non-sparse unique indexes also index missing fields as null.
            if any(row is not original and tuple(field_value(row, field) for field in fields) == value
                   for row in self.rows):
                raise DuplicateKeyError(f"Duplicate indexed values for {fields}")

    async def find_one(self, query, *args, **kwargs):
        return copy.deepcopy(next((row for row in self.rows if matches(row, query)), None))

    def find(self, query, *args, **kwargs):
        return Cursor([row for row in self.rows if matches(row, query)])

    async def count_documents(self, query):
        return sum(matches(row, query) for row in self.rows)

    async def insert_one(self, row):
        self.validate(row)
        self.rows.append(copy.deepcopy(row))
        return SimpleNamespace(inserted_id=len(self.rows))

    async def delete_many(self, query):
        self.rows = [row for row in self.rows if not matches(row, query)]

    async def update_one(self, query, update, upsert=False):
        all_paths = [path for operation in update.values() for path in operation]
        if len(set(all_paths)) != len(all_paths):
            raise AssertionError("Conflicting Mongo update paths")
        original = next((row for row in self.rows if matches(row, query)), None)
        if original is None and not upsert:
            return SimpleNamespace(matched_count=0, modified_count=0)
        candidate = copy.deepcopy(original) if original is not None else {
            key: copy.deepcopy(value) for key, value in query.items() if not isinstance(value, dict)}
        if original is None:
            for key, value in update.get("$setOnInsert", {}).items():
                set_field(candidate, key, value)
        for key, value in update.get("$set", {}).items():
            set_field(candidate, key, value)
        for key, value in update.get("$addToSet", {}).items():
            items = copy.deepcopy(field_value(candidate, key) or [])
            for item in value.get("$each", []) if isinstance(value, dict) else [value]:
                if item not in items:
                    items.append(item)
            set_field(candidate, key, items)
        self.validate(candidate, original)
        if original is None:
            self.rows.append(candidate)
        else:
            original.clear()
            original.update(candidate)
        return SimpleNamespace(matched_count=int(original is not None), modified_count=1)


class IndexedDb:
    def __init__(self):
        self.collections = {}
        # Load the production unique index definitions rather than omitting them.
        for node in ast.walk(ast.parse((BACKEND / "server.py").read_text())):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            target = node.func.value
            if node.func.attr != "create_index" or not isinstance(target, ast.Attribute):
                continue
            if not isinstance(target.value, ast.Name) or target.value.id != "db":
                continue
            if not any(arg.arg == "unique" and isinstance(arg.value, ast.Constant) and arg.value.value is True
                       for arg in node.keywords):
                continue
            try:
                index = ast.literal_eval(node.args[0])
            except (ValueError, TypeError):
                continue
            fields = [index] if isinstance(index, str) else [item[0] for item in index]
            getattr(self, target.attr).unique_indexes.append(fields)

    def __getattr__(self, name):
        return self.collections.setdefault(name, IndexedCollection())

    def __getitem__(self, name):
        return getattr(self, name)


async def authenticate_admin(request, db):
    return {"user_id": "test-admin", "email": "admin@example.org"}


async def authenticate_member(request, db):
    token = request.headers.get("authorization", "").removeprefix("Bearer ") or request.cookies.get("member_session", "")
    member = await db.members.find_one({"user_id": token.removeprefix("test:")})
    if not token.startswith("test:") or not member:
        raise HTTPException(401, "Member session required")
    return member


def require_entitlement(member, entitlements):
    if not set(member.get("entitlements", [])) & entitlements:
        raise HTTPException(403, "Purchase required")


async def offline_delivery(*args, **kwargs):
    return {"id": "offline-delivery"}


def route_module(filename, extras=None):
    # Execute the actual definitions, replacing only imports of external services.
    namespace = {
        "__name__": "offline_" + filename.removesuffix(".py"),
        "asyncio": asyncio, "json": json, "uuid": uuid,
        "hashlib": hashlib, "html": html, "logging": logging, "os": os,
        "re": re, "secrets": secrets, "datetime": datetime, "timedelta": timedelta,
        "timezone": timezone, "APIRouter": APIRouter, "HTTPException": HTTPException,
        "Request": Request, "Response": Response, "BaseModel": BaseModel,
        "EmailStr": EmailStr, "Field": Field, "authenticate_admin": authenticate_admin,
        "authenticate_member": authenticate_member, "require_entitlement": require_entitlement,
        "new_uuid": lambda: str(uuid.uuid4()), "merged_sections": merged_sections,
        "EDITABLE_FIELDS": EDITABLE_FIELDS, "GAME_V3": GAME_V3,
        "is_meaningful_game_response": is_meaningful_game_response,
        "response_input_hash": response_input_hash, "response_texts": response_texts,
        "create_member_token": lambda user_id, email: "test:" + user_id,
        "set_member_cookie": lambda response, token: response.set_cookie("member_session", token),
        "email_html": lambda *args: "Offline notification",
        "resend": SimpleNamespace(Emails=SimpleNamespace(send_async=offline_delivery)),
    }
    namespace.update(extras or {})
    tree = ast.parse((BACKEND / filename).read_text())
    definitions = [node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
    exec(compile(ast.Module(body=definitions, type_ignores=[]), filename, "exec"), namespace)
    return namespace


class SetupRoutes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = IndexedDb()
        self.app = FastAPI()
        game = route_module("game_routes.py")
        night = route_module("game_night_routes.py", {
            "present_reality_is_complete": game["present_reality_is_complete"],
            "situation_is_complete": game["situation_is_complete"],
        })
        admin = route_module("admin_dashboard_preview_routes.py")
        strategy_tree = ast.parse((BACKEND / "strategy_routes.py").read_text())
        constants = {}
        for node in strategy_tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {"OUTPUT_SCHEMA", "CORE_STRATEGY_KEYS"}:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
        meeting = route_module("meeting_review_routes.py", {
            "OUTPUT_SCHEMA": constants["OUTPUT_SCHEMA"], "EDITABLE_SECTION_KEYS": constants["CORE_STRATEGY_KEYS"],
        })
        for namespace, factory in ((game, "create_game_router"), (night, "create_game_night_router"),
                                   (admin, "create_admin_dashboard_preview_router"), (meeting, "create_meeting_review_router")):
            self.app.include_router(namespace[factory](self.db))
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def fresh_game(self):
        launch = await self.client.post("/api/admin/dashboard-preview/fresh/board-fundraising-game")
        self.assertEqual(launch.status_code, 200, launch.text)
        self.client.headers["Authorization"] = "Bearer " + launch.json()["token"]
        self.user_id = launch.json()["token"].removeprefix("test:")
        self_play = await self.client.post("/api/game/self-play")
        self.assertEqual(self_play.status_code, 201, self_play.text)
        return self_play.json()["token"]

    async def save_reality(self, missing=None, no_funders=False):
        reality = {"setup_version": "present_funders_v3", "reviewed": "yes"}
        for group, prefix in (("individuals", "individual_donor"), ("businesses", "business"), ("grantors", "grantor")):
            reality[group + "_status"] = "none" if no_funders else "current"
            if not no_funders:
                for field in ("profile", "where", "process", "support"):
                    reality[f"current_{prefix}_{field}"] = f"Provided {prefix} {field} answer"
        if missing:
            reality.pop(missing)
        result = await self.client.put("/api/game/situation", json={"sections": {"current_reality": reality}, "current_step": 3})
        self.assertEqual(result.status_code, 200, result.text)

    async def test_participation_saves_before_meeting_then_invitations_unlock(self):
        token = await self.fresh_game()
        endpoint = f"/api/game/play/{token}/ideas/complete"
        involvement = {"involvement": "I will introduce prospects and follow up."}
        early = await self.client.post(endpoint, json=involvement)
        self.assertEqual(early.status_code, 409)
        await self.save_reality(missing="current_business_support")
        self.assertEqual((await self.client.post(endpoint, json=involvement)).status_code, 409)
        await self.save_reality()
        self.assertIsNone(await self.db.game_nights.find_one({"user_id": self.user_id}))
        for _ in range(2):
            result = await self.client.post(endpoint, json=involvement)
            self.assertEqual(result.status_code, 200, result.text)
        response = await self.db.game_audience_responses.find_one({"user_id": self.user_id})
        self.assertEqual(response["involvement"], involvement["involvement"])
        self.assertTrue(response["completed"])
        invitee = {"full_name": "A Board Member", "email": "board@example.org"}
        self.assertEqual((await self.client.post("/api/game/board-members", json=invitee)).status_code, 409)
        self.assertEqual((await self.client.post("/api/game/situation/complete")).status_code, 409)
        meeting = await self.client.put("/api/game/night", json={"meeting_date": "2026-10-20", "start_time": "12:00", "funding_deadline": "2026-12-31"})
        self.assertEqual(meeting.status_code, 200, meeting.text)
        complete = await self.client.post("/api/game/situation/complete")
        self.assertEqual(complete.status_code, 200, complete.text)
        dashboard = await self.client.get("/api/game/dashboard")
        self.assertEqual(dashboard.status_code, 200, dashboard.text)
        self.assertEqual(dashboard.json()["status"], "set_up_board")
        self.assertEqual(dashboard.json()["goal"]["deadline"], "2026-12-31")
        added = await self.client.post("/api/game/board-members", json=invitee)
        self.assertEqual(added.status_code, 201, added.text)
        board_record = await self.db.game_board_members.find_one({"member_id": added.json()["board_member"]["member_id"]})
        self.assertEqual(board_record["game_version"], 5)
        situation = await self.db.game_situations.find_one({"user_id": self.user_id})
        self.assertTrue(situation["completed"])
        self.assertNotIn("team", situation["sections"])
        self.assertNotIn("technology", situation["sections"])
        self.assertNotIn("materials", situation["sections"])

    async def test_none_categories_skip_and_meeting_cannot_complete_before_participation(self):
        token = await self.fresh_game()
        await self.save_reality(no_funders=True)
        result = await self.client.put("/api/game/night", json={"meeting_date": "2026-10-20", "start_time": "12:00", "funding_deadline": "2026-12-31"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual((await self.client.post("/api/game/situation/complete")).status_code, 409)
        completed = await self.client.post(f"/api/game/play/{token}/ideas/complete", json={"involvement": "I will make introductions."})
        self.assertEqual(completed.status_code, 200, completed.text)
        self.assertEqual((await self.client.post("/api/game/situation/complete")).status_code, 200)

    async def test_invited_member_only_needs_five_answers_and_participation(self):
        await self.db.game_board_members.insert_one({"member_id": "board", "token": "board-link", "user_id": "lead", "is_primary": False, "game_version": 5, "full_name": "Board Member"})
        endpoint = "/api/game/play/board-link/ideas"
        self.assertEqual((await self.client.post(endpoint + "/complete", json={"involvement": "Introduce prospects"})).status_code, 409)
        for question in range(1, 6):
            result = await self.client.put(endpoint + f"/answer/{question}", json={"answer": f"My original answer {question}"})
            self.assertEqual(result.status_code, 200, result.text)
        result = await self.client.post(endpoint + "/complete", json={"involvement": "Introduce prospects"})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual((await self.client.get(endpoint)).json()["next_question"], 6)
        self.assertFalse(self.db.game_situations.rows)
        self.assertFalse(self.db.game_nights.rows)

    async def test_repeated_fresh_recruitment_launches_with_existing_missing_token(self):
        await self.db.funnel_leads.insert_one({"lead_id": "existing-lead-without-result-token"})
        with self.assertRaises(DuplicateKeyError):
            await self.db.funnel_leads.insert_one({"lead_id": "old-fresh-test-without-result-token"})
        tokens = []
        for _ in range(3):
            response = await self.client.post("/api/admin/dashboard-preview/fresh/recruitment")
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertIn("/purchase/success?session_id=", body["start_url"])
            self.assertEqual(response.cookies["member_session"], body["token"])
            user_id = body["token"].removeprefix("test:")
            lead = await self.db.funnel_leads.find_one({"member_user_id": user_id})
            assessment = await self.db.recruitment_free_assessments.find_one({"member_user_id": user_id})
            self.assertEqual(lead["result_token"], assessment["token"])
            self.assertEqual(assessment["state"]["generation_status"], "not_started")
            tokens.append(lead["result_token"])
        self.assertEqual(len(set(tokens)), 3)

    async def test_shared_final_review_only_includes_actual_execution_agreements(self):
        await self.fresh_game()
        await self.db.game_strategies.insert_one({"strategy_id": "final", "user_id": self.user_id,
            "schema_version": 4, "mode": "final", "data": {"execution_agreements": []}})
        await self.db.meeting_review_sessions.insert_one({"review_id": "review", "user_id": self.user_id,
            "group_session_id": "group", "final_strategy_id": "final", "status": "final_strategy_created"})
        await self.db.group_game_sessions.insert_one({"session_id": "group", "user_id": self.user_id, "token": "group-link"})
        endpoint = "/api/game/meeting-review/final-review"
        self.assertEqual((await self.client.post(endpoint, json={"action": "start"})).status_code, 200)
        absent = await self.client.post(endpoint, json={"action": "section", "index": 7})
        self.assertEqual(absent.status_code, 422)
        await self.db.game_strategies.update_one({"strategy_id": "final"}, {"$set": {
            "data.execution_agreements": ["Alex agreed to prepare the employer introduction email."]}})
        selected = await self.client.post(endpoint, json={"action": "section", "index": 7})
        self.assertEqual(selected.status_code, 200, selected.text)
        shared = await self.client.get("/api/game/group/play/group-link/review-state")
        self.assertEqual(shared.status_code, 200, shared.text)
        self.assertEqual(shared.json()["total_sections"], 8)
        self.assertEqual(shared.json()["section"]["key"], "execution_agreements")
        self.assertEqual(shared.json()["section"]["data"], ["Alex agreed to prepare the employer introduction email."])

    async def test_all_four_admin_launchers_repeat_with_production_indexes(self):
        products = ("recruitment", "board-fundraising-game", "strategic-planning", "board-recommitment")
        identities = set()
        for _ in range(2):
            for product in products:
                fresh = await self.client.post(f"/api/admin/dashboard-preview/fresh/{product}")
                self.assertEqual(fresh.status_code, 200, fresh.text)
                token = fresh.json()["token"]
                self.assertNotIn(token, identities)
                identities.add(token)
                self.assertEqual(fresh.cookies["member_session"], token)
                session_id = fresh.json()["start_url"].split("session_id=", 1)[1]
                transaction = await self.db.payment_transactions.find_one({"session_id": session_id})
                self.assertEqual(transaction["amount"], 0)
                self.assertTrue(transaction["internal_preview"])
                loaded = await self.client.post(f"/api/admin/dashboard-preview/{product}")
                self.assertEqual(loaded.status_code, 200, loaded.text)
                self.assertEqual(loaded.cookies["member_session"], loaded.json()["token"])
        self.assertTrue(all(row["internal_preview"] for row in self.db.payment_transactions.rows))


if __name__ == "__main__":
    unittest.main()
