"""Local-only acceptance server. Uses a disposable Mongo database, never .env."""
import ast
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from auth_service import create_access_token
from clean_platform_routes import create_clean_platform_router

assert os.environ.get("RECOVERY_ACCEPTANCE") == "1", "Acceptance server requires explicit test configuration"
assert os.environ["MONGO_URL"].startswith("mongodb://127.0.0.1:"), "Only local test Mongo is permitted"
mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = mongo["nbb_recovery_acceptance"]
app = FastAPI()
app.include_router(create_clean_platform_router(db))


@app.on_event("startup")
async def seed():
    await db.users.replace_one({"user_id": "acceptance-admin"}, {
        "user_id": "acceptance-admin", "email": "admin@example.test", "role": "admin"
    }, upsert=True)


@app.get("/__test/session")
async def session():
    return {"token": create_access_token("acceptance-admin", "admin@example.test")}


@app.get("/api/game/content")
async def game_content():
    tree = ast.parse((ROOT / "backend/game_routes.py").read_text())
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "DEFAULT_CONTENT" for t in n.targets))
    return {"content": ast.literal_eval(node.value)}


@app.get("/{path:path}")
async def frontend(path: str):
    build = ROOT / "frontend/build"
    candidate = (build / path).resolve()
    if candidate.is_relative_to(build.resolve()) and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(build / "index.html")
