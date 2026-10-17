"""Disposable integration/browser server using real routes and Mongo, fake providers."""
import os
import sys
import types
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
assert os.environ.get("RECOVERY_ACCEPTANCE") == "1"
assert os.environ["MONGO_URL"].startswith("mongodb://127.0.0.1:")
# Only the external AI transport is substituted. All product handlers run normally.
chat = types.ModuleType("emergentintegrations.llm.chat")
class ForbiddenProvider:
    def __init__(self, *args, **kwargs): raise AssertionError("An integration test attempted a real AI provider call")
chat.LlmChat = ForbiddenProvider; chat.UserMessage = lambda **kwargs: kwargs
for name in ("emergentintegrations", "emergentintegrations.llm"):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules[chat.__name__] = chat
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
from auth_service import create_access_token, authenticate_admin
from member_auth import create_member_token
from clean_platform_routes import create_clean_platform_router
from game_routes import create_game_router
from game_night_routes import create_game_night_router
from group_game_routes import create_group_game_router
from game_meeting_routes import create_game_meeting_router
from guided_product_routes import create_guided_product_router
from strategic_planning_routes import create_strategic_planning_router, create_guided_strategic_planning_router
from admin_dashboard_preview_routes import create_admin_dashboard_preview_router
from payment_routes import create_payment_router
from board_fix_routes import create_board_fix_router
from public_opportunity_routes import create_public_opportunity_router
from admin_test_safety import install_email_capture
from fundraising_launch import create_fundraising_launch_router
from portfolio_routes import create_portfolio_router
from member_routes import create_member_router
import strategic_planning_routes as sp
mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = mongo["nbb_current_workflow_acceptance"]
def build_app(database):
    app = FastAPI()
    install_email_capture(app, database)
    @app.get("/api/auth/me")
    async def admin_identity(request: Request):
        return await authenticate_admin(request, database)
    for factory in (create_clean_platform_router, create_game_router, create_game_night_router, create_group_game_router, create_game_meeting_router,
                    create_guided_product_router, create_strategic_planning_router, create_guided_strategic_planning_router, create_admin_dashboard_preview_router,
                    create_payment_router, create_member_router, create_board_fix_router, create_public_opportunity_router, create_fundraising_launch_router, create_portfolio_router):
        app.include_router(factory(database))
    return app

app = build_app(db)

AI_CONTEXTS = []
async def fake_generation(kind, context, instructions=""):
    AI_CONTEXTS.append({"kind": kind, "context": context, "instructions": instructions})
    return {"sections": [{"heading": "Agreed 24-Month Direction", "content": "The group will deliver the explicitly adopted priorities. Costs and dates not supplied require confirmation."}]}
sp.generate_structured = fake_generation

@app.on_event("startup")
async def seed():
    for name in await db.list_collection_names(): await db[name].delete_many({})
    await db.users.insert_one({"user_id":"acceptance-admin","email":"admin@example.test","role":"admin"})

@app.get("/__test/session")
async def session(variant: str = ""):
    identity = "acceptance-admin" + ("-" + variant if variant in {"1440","390"} else "")
    email = identity + "@example.test"
    if not variant: email = "admin@example.test"
    await db.users.update_one({"user_id":identity},{"$setOnInsert":{"user_id":identity,"email":email,"role":"admin"}},upsert=True)
    return {"token":create_access_token(identity,email)}

@app.get("/__test/ai-contexts")
async def ai_contexts(): return AI_CONTEXTS

@app.get("/__test/member/{user_id}")
async def member(user_id:str):
    record=await db.members.find_one({"user_id":user_id},{"_id":0})
    return {"token": create_member_token(user_id,record["email"])}

@app.get("/{path:path}")
async def frontend(path:str):
    build=ROOT / "frontend/build";candidate=(build/path).resolve()
    return FileResponse(candidate if candidate.is_relative_to(build.resolve()) and candidate.is_file() else build/"index.html")
