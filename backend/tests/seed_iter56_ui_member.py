"""Seed a throwaway stage-1-only recruitment member for iteration 56 UI testing."""
import os
import sys

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env["REACT_APP_BACKEND_URL"]).rstrip("/")
client = MongoClient(backend_env["MONGO_URL"])
db = client[backend_env["DB_NAME"]]

EMAIL = "TEST_iter56_ui@example.com"
PASSWORD = "TestPass123!"

if sys.argv[1:] == ["cleanup"]:
    doc = db.members.find_one({"email": EMAIL})
    if doc:
        db.course_progress.delete_many({"user_id": doc["user_id"]})
        db.recruitment_profiles.delete_many({"user_id": doc["user_id"]})
        db.members.delete_many({"user_id": doc["user_id"]})
    print("cleaned", EMAIL)
    raise SystemExit(0)

db.members.delete_many({"email": EMAIL})
r = requests.post(f"{BASE_URL}/api/members/register", json={
    "first_name": "Iter56", "last_name": "UI", "email": EMAIL,
    "password": PASSWORD, "confirm_password": PASSWORD})
print(r.status_code, r.text[:200])
uid = r.json()["member"]["user_id"]
db.members.update_one({"user_id": uid}, {"$set": {"entitlements": ["recruitment_self_guided"]}})
print("seeded", EMAIL, uid, db.members.find_one({"user_id": uid}, {"_id": 0, "entitlements": 1}))
