import os
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

be = dotenv_values("/app/backend/.env")
fe = dotenv_values("/app/frontend/.env")
BASE = fe["REACT_APP_BACKEND_URL"].rstrip("/")
db = MongoClient(be["MONGO_URL"])[be["DB_NAME"]]

for email, ents in [("stage1b.tester@example.com", ["recruitment_self_guided"])]:
    if not db.members.find_one({"email": email}):
        r = requests.post(f"{BASE}/api/members/register", json={
            "first_name": "Stage", "last_name": "Tester", "email": email,
            "password": "TestPass123!", "confirm_password": "TestPass123!"})
        print(email, r.status_code, r.text[:200])
    db.members.update_one({"email": email}, {"$set": {"entitlements": ents}})
    print(email, db.members.find_one({"email": email}, {"_id": 0, "entitlements": 1, "user_id": 1}))

print("stage1:", db.members.find_one({"email": "stage1.tester@example.com"}, {"_id": 0, "entitlements": 1, "user_id": 1}))
