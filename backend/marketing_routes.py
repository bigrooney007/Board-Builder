"""Phase 4 routes: public blog + admin-triggered test generation/sends. No admin dashboard."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from auth_service import authenticate_admin
from marketing_service import CATEGORIES, run_weekly_nurture, create_scheduled_blog_post, now_tz

PUBLIC_FIELDS = {"_id": 0, "blog_post_id": 1, "title": 1, "slug": 1, "category": 1, "category_key": 1, "excerpt": 1, "published_at": 1, "cta_label": 1, "cta_button": 1, "cta_url": 1}


class BlogGenerate(BaseModel):
    category: str
    scheduled_date: Optional[str] = ""
    publish_now: bool = True

    @field_validator("category")
    @classmethod
    def valid_category(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError("Unknown category")
        return value


class NurtureTestSend(BaseModel):
    test_email: Optional[str] = ""


def create_marketing_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/blog/posts")
    async def list_posts(category: str = "", limit: int = 50):
        query = {"publication_status": "Published"}
        if category and category in CATEGORIES:
            query["category_key"] = category
        posts = await db.blog_posts.find(query, PUBLIC_FIELDS).sort("published_at", -1).to_list(min(limit, 100))
        return {"posts": posts, "categories": [{"key": key, "name": config["name"]} for key, config in CATEGORIES.items()]}

    @router.get("/blog/posts/{slug}")
    async def get_post(slug: str):
        post = await db.blog_posts.find_one({"slug": slug, "publication_status": "Published"}, {"_id": 0, "error": 0})
        if not post:
            raise HTTPException(status_code=404, detail="Article not found")
        return post

    @router.post("/blog/generate", status_code=201)
    async def generate_post(payload: BlogGenerate, request: Request):
        await authenticate_admin(request, db)
        scheduled_date = payload.scheduled_date or now_tz().strftime("%Y-%m-%d")
        result = await create_scheduled_blog_post(db, payload.category, scheduled_date, publish_now=payload.publish_now)
        if result.get("skipped"):
            raise HTTPException(status_code=409, detail=result["reason"])
        return result

    @router.post("/nurture/test-send")
    async def nurture_test(payload: NurtureTestSend, request: Request):
        await authenticate_admin(request, db)
        origin = request.headers.get("origin") or "https://nonprofitboardbuilder.com"
        return await run_weekly_nurture(db, origin, test_only=True, test_email=payload.test_email or "")

    @router.get("/nurture/status")
    async def nurture_status(request: Request):
        await authenticate_admin(request, db)
        import os
        rotation = await db.nurture_rotation.find({}, {"_id": 0}).to_list(10)
        sends = await db.nurture_sends.find({}, {"_id": 0}).sort("created_at", -1).to_list(20)
        contacts = await db.nurture_contacts.find({}, {"_id": 0}).sort("updated_at", -1).to_list(50)
        return {"rotation": rotation, "sends": sends, "contacts": contacts,
                "blog_automation_enabled": os.environ.get("BLOG_AUTOMATION_ENABLED", "false"),
                "lead_nurture_enabled": os.environ.get("LEAD_NURTURE_ENABLED", "false")}

    return router
