"""Public articles and the original admin's blog workstation."""
from datetime import date, datetime, timedelta
from html import escape
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool
from auth_service import authenticate_admin
from blog_content import BLOG_CATEGORIES
from blog_media import ORIGIN, cover_png, image_version, present_post
from blog_service import (CATEGORIES, blog_settings, claim_regeneration, generate_linkedin_snippet,
    generate_reserved_blog_post, next_topic_for, now_tz, reserve_blog_post, slugify_title, topic_usage)
from marketing_service import run_weekly_nurture


class BlogGenerate(BaseModel):
    category: str
    scheduled_date: Optional[date] = None
    topic_id: str = ""
    publish_now: bool = False

    @field_validator("category")
    @classmethod
    def valid_category(cls, value):
        if value not in BLOG_CATEGORIES:
            raise ValueError("Choose one of the five current blog topics.")
        return value

    @field_validator("scheduled_date", mode="before")
    @classmethod
    def blank_date(cls, value):
        return value or None


class NurtureTestSend(BaseModel):
    test_email: Optional[str] = ""


class BlogEdit(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    excerpt: str = Field(min_length=10, max_length=200)
    body: str = Field(min_length=50, max_length=20000)
    graphic_headline: str = Field(default="", max_length=85)
    graphic_subtitle: str = Field(default="", max_length=110)

    @field_validator("title", "excerpt", "body", "graphic_headline", "graphic_subtitle", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class BlogSettings(BaseModel):
    enabled: bool
    time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    timezone: str

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Use a valid timezone, such as Europe/London or America/New_York.")
        return value


def create_marketing_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def find_post(post_id):
        post = await db.blog_posts.find_one({"blog_post_id": post_id}, {"_id": 0})
        if not post:
            raise HTTPException(status_code=404, detail="Blog post not found")
        return post

    @router.get("/blog/posts")
    async def list_posts(category: str = "", limit: int = Query(default=50, ge=1, le=100)):
        query = {"publication_status": "Published"}
        if category:
            if category not in CATEGORIES:
                raise HTTPException(status_code=400, detail="Unknown blog topic")
            query["category_key"] = category
        posts = await db.blog_posts.find(query, {"_id": 0, "body": 0}).sort("published_at", -1).to_list(limit)
        return {"posts": [present_post(p, public=True) for p in posts],
                "categories": [{"key": key, "name": config["name"]} for key, config in BLOG_CATEGORIES.items()]}

    @router.get("/blog/posts/{slug}")
    async def get_post(slug: str):
        post = await db.blog_posts.find_one({"slug": slug, "publication_status": "Published"}, {"_id": 0})
        if not post:
            raise HTTPException(status_code=404, detail="Article not found")
        return present_post(post, public=True)

    @router.get("/blog/images/{slug}.png")
    async def public_image(slug: str, request: Request):
        post = await db.blog_posts.find_one({"slug": slug, "publication_status": "Published"}, {"_id": 0})
        if not post:
            raise HTTPException(status_code=404, detail="Article not found")
        etag = '"' + image_version(post) + '"'
        headers = {"ETag": etag, "Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"}
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        return Response(await run_in_threadpool(cover_png, post), media_type="image/png", headers=headers)

    @router.get("/blog/sitemap.xml")
    async def blog_sitemap():
        posts = await db.blog_posts.find({"publication_status": "Published", "slug": {"$ne": ""}}, {"_id": 0, "slug": 1, "edited_at": 1, "published_at": 1}).sort("published_at", -1).to_list(49000)
        urls = [f"<url><loc>{ORIGIN}/blog</loc></url>"]
        for post in posts:
            updated = post.get("edited_at") or post.get("published_at")
            lastmod = f"<lastmod>{escape(updated)}</lastmod>" if updated else ""
            urls.append(f"<url><loc>{ORIGIN}/blog/{escape(post['slug'])}</loc>{lastmod}</url>")
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(urls) + "</urlset>"
        return Response(xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=300"})

    @router.post("/blog/generate", status_code=202)
    async def generate_post(payload: BlogGenerate, request: Request, background_tasks: BackgroundTasks):
        await authenticate_admin(request, db)
        if payload.publish_now:
            raise HTTPException(status_code=400, detail="Generate the draft, then use Publish after reviewing it.")
        settings = await blog_settings(db)
        scheduled_date = str(payload.scheduled_date or datetime.now(ZoneInfo(settings["timezone"])).date())
        try:
            post, created = await reserve_blog_post(db, payload.category, scheduled_date, payload.topic_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if created:
            background_tasks.add_task(generate_reserved_blog_post, db, post)
        return {"status": post["publication_status"], "reused": not created, "post": present_post(post)}

    @router.get("/admin/blog/topics")
    async def admin_topic_schedule(request: Request):
        await authenticate_admin(request, db)
        settings = await blog_settings(db)
        today = datetime.now(ZoneInfo(settings["timezone"])).date()
        schedule = []
        for key, config in BLOG_CATEGORIES.items():
            next_topic = await next_topic_for(db, key)
            usage = await topic_usage(db, key)
            schedule.append({"category_key": key, "category": config["name"], "publish_day": config["publish_day"],
                "cta_url": config["cta_url"], "audience": config["audience"], "mechanism": config["mechanism"],
                "scheduled_date": str(today + timedelta(days=(config["day"] - today.weekday()) % 7)),
                "next_topic_id": next_topic["topic_id"], "topics": [{**angle, "drafts_and_posts": usage[angle["topic_id"]]} for angle in config["angles"]]})
        return {"schedule": schedule, "settings": settings}

    @router.put("/admin/blog/settings")
    async def save_settings(payload: BlogSettings, request: Request):
        await authenticate_admin(request, db)
        await db.marketing_settings.update_one({"key": "blog_weekday_drafts"}, {"$set": payload.model_dump()}, upsert=True)
        return {"settings": await blog_settings(db)}

    @router.get("/admin/blog/posts")
    async def admin_list_posts(request: Request, limit: int = Query(default=100, ge=1, le=100), skip: int = Query(default=0, ge=0)):
        await authenticate_admin(request, db)
        posts = await db.blog_posts.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).to_list(limit)
        return {"posts": [present_post(p) for p in posts], "has_more": len(posts) == limit}

    @router.get("/admin/blog/posts/{blog_post_id}")
    async def admin_get_post(blog_post_id: str, request: Request):
        await authenticate_admin(request, db)
        return {"post": present_post(await find_post(blog_post_id))}

    @router.get("/admin/blog/posts/{blog_post_id}/image")
    async def admin_image(blog_post_id: str, request: Request):
        await authenticate_admin(request, db)
        return Response(await run_in_threadpool(cover_png, await find_post(blog_post_id)), media_type="image/png", headers={"Cache-Control": "private, no-store"})

    @router.patch("/admin/blog/posts/{blog_post_id}")
    async def admin_edit_post(blog_post_id: str, payload: BlogEdit, request: Request):
        await authenticate_admin(request, db)
        post = await find_post(blog_post_id)
        if post["publication_status"] == "Generating":
            raise HTTPException(status_code=409, detail="Wait for generation to finish before editing this draft.")
        update = {**payload.model_dump(), "edited_at": now_tz().isoformat(), "error": "", "linkedin_snippet": ""}
        if post["publication_status"] != "Published":
            update.update({"slug": f"{slugify_title(payload.title) or 'board-insight'}-{blog_post_id[:8]}", "publication_status": "Pending Review"})
        try:
            await run_in_threadpool(cover_png, {**post, **update})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        result = await db.blog_posts.update_one({"blog_post_id": blog_post_id, "publication_status": post["publication_status"]}, {"$set": update})
        if not result.matched_count:
            raise HTTPException(status_code=409, detail="This article changed. Refresh before saving.")
        return {"post": present_post({**post, **update})}

    @router.post("/admin/blog/posts/{blog_post_id}/approve")
    async def admin_approve_post(blog_post_id: str, request: Request):
        await authenticate_admin(request, db)
        post = await find_post(blog_post_id)
        if post["publication_status"] != "Pending Review":
            raise HTTPException(status_code=409, detail="Save or generate a draft ready for review before publishing.")
        if not all(post.get(key, "").strip() for key in ["title", "excerpt", "body", "slug"]):
            raise HTTPException(status_code=400, detail="The title, description and article must be complete before publishing.")
        await run_in_threadpool(cover_png, post)
        stamp = now_tz().isoformat()
        update = {"publication_status": "Published", "published_at": stamp, "approved_at": stamp, "error": ""}
        result = await db.blog_posts.update_one({"blog_post_id": blog_post_id, "publication_status": "Pending Review"}, {"$set": update})
        if not result.modified_count:
            raise HTTPException(status_code=409, detail="This draft changed. Refresh it before publishing.")
        return {"post": present_post({**post, **update})}

    @router.post("/admin/blog/posts/{blog_post_id}/linkedin-snippet")
    async def admin_generate_snippet(blog_post_id: str, request: Request):
        await authenticate_admin(request, db)
        post = await find_post(blog_post_id)
        if post["publication_status"] != "Published":
            raise HTTPException(status_code=409, detail="Publish the article before creating its share text.")
        try:
            snippet = post.get("linkedin_snippet") or await generate_linkedin_snippet(db, post)
        except Exception:
            raise HTTPException(status_code=502, detail="Could not generate share text. Please try again.")
        return {"post": present_post({**post, "linkedin_snippet": snippet}), "snippet": snippet}

    @router.post("/admin/blog/posts/{blog_post_id}/reject")
    async def admin_reject_post(blog_post_id: str, request: Request):
        await authenticate_admin(request, db)
        post = await find_post(blog_post_id)
        if post["publication_status"] in ["Published", "Generating"]:
            raise HTTPException(status_code=409, detail="This article cannot be archived in its current state.")
        update = {"publication_status": "Rejected", "rejected_at": now_tz().isoformat()}
        await db.blog_posts.update_one({"blog_post_id": blog_post_id, "publication_status": post["publication_status"]}, {"$set": update})
        return {"post": present_post({**post, **update})}

    @router.post("/admin/blog/posts/{blog_post_id}/regenerate", status_code=202)
    async def admin_regenerate_post(blog_post_id: str, request: Request, background_tasks: BackgroundTasks):
        await authenticate_admin(request, db)
        claimed = await claim_regeneration(db, await find_post(blog_post_id))
        if not claimed:
            raise HTTPException(status_code=409, detail="This article is already generating or published.")
        background_tasks.add_task(generate_reserved_blog_post, db, claimed)
        return {"status": "Generating", "post": present_post(claimed)}

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
                "lead_nurture_enabled": os.environ.get("LEAD_NURTURE_ENABLED", "false"),
                "recruitment_lead_nurture_enabled": os.environ.get("RECRUITMENT_LEAD_NURTURE_ENABLED", "false")}

    return router
