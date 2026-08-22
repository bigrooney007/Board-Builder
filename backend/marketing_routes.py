"""Phase 4 routes: public blog + admin-triggered test generation/sends. No admin dashboard."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from auth_service import authenticate_admin
from board_content_topics import BOARD_CONTENT_TOPICS
from marketing_service import CATEGORIES, run_weekly_nurture, create_scheduled_blog_post, generate_linkedin_snippet, next_topic_for, now_tz, regenerate_blog_post, slugify_title

PUBLIC_FIELDS = {"_id": 0, "blog_post_id": 1, "title": 1, "slug": 1, "category": 1, "category_key": 1, "excerpt": 1, "published_at": 1, "cta_label": 1, "cta_button": 1, "cta_url": 1}


class BlogGenerate(BaseModel):
    category: str
    scheduled_date: Optional[str] = ""
    publish_now: bool = False

    @field_validator("category")
    @classmethod
    def valid_category(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError("Unknown category")
        return value


class NurtureTestSend(BaseModel):
    test_email: Optional[str] = ""


class BlogEdit(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    excerpt: str = ""
    body: str = Field(min_length=50)


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

    @router.get("/admin/blog/topics")
    async def admin_topic_schedule(request: Request):
        await authenticate_admin(request, db)
        schedule = []
        day_names = {0: "Monday", 2: "Wednesday", 4: "Friday", 5: "Saturday"}
        for key, config in CATEGORIES.items():
            published_posts = await db.blog_posts.find(
                {"category_key": key, "topic_number": {"$gte": 1}, "publication_status": "Published"},
                {"_id": 0, "topic_number": 1, "topic_title": 1, "published_at": 1, "slug": 1}).sort("published_at", 1).to_list(200)
            latest = {}
            for post in published_posts:
                latest[post["topic_number"]] = post
            upcoming = await next_topic_for(db, key)
            topics = []
            for number, title in enumerate(BOARD_CONTENT_TOPICS[key], start=1):
                record = latest.get(number)
                topics.append({
                    "topic_number": number, "topic_title": title,
                    "publication_status": "Published" if record else ("Next" if number == upcoming["topic_number"] else "Unpublished"),
                    "published_at": (record or {}).get("published_at", ""),
                    "slug": (record or {}).get("slug", ""),
                })
            schedule.append({
                "category_key": key, "category": config["name"],
                "publish_day": day_names.get(config["day"], ""), "cta_url": config["cta_url"],
                "published_count": upcoming["published_in_category"],
                "next_topic_number": upcoming["topic_number"], "next_topic_title": upcoming["topic_title"],
                "topics": topics,
            })
        return {"schedule": schedule}

    @router.get("/admin/blog/posts")
    async def admin_list_posts(request: Request):
        await authenticate_admin(request, db)
        posts = await db.blog_posts.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
        return {"posts": posts, "categories": [{"key": key, "name": config["name"]} for key, config in CATEGORIES.items()]}

    @router.patch("/admin/blog/posts/{blog_post_id}")
    async def admin_edit_post(blog_post_id: str, payload: BlogEdit, request: Request):
        await authenticate_admin(request, db)
        post = await db.blog_posts.find_one({"blog_post_id": blog_post_id}, {"_id": 0})
        if not post:
            raise HTTPException(status_code=404, detail="Blog post not found")
        update = {"title": payload.title.strip(), "excerpt": payload.excerpt.strip(), "body": payload.body.strip(), "edited_at": now_tz().isoformat()}
        if post["publication_status"] != "Published":
            new_slug = slugify_title(update["title"])
            conflict = await db.blog_posts.find_one({"slug": new_slug, "blog_post_id": {"$ne": blog_post_id}}, {"_id": 1})
            if conflict:
                raise HTTPException(status_code=409, detail="Another post already uses this title. Choose a different title.")
            update["slug"] = new_slug
        await db.blog_posts.update_one({"blog_post_id": blog_post_id}, {"$set": update})
        post.update(update)
        return {"post": post}

    @router.post("/admin/blog/posts/{blog_post_id}/approve")
    async def admin_approve_post(blog_post_id: str, request: Request):
        await authenticate_admin(request, db)
        post = await db.blog_posts.find_one({"blog_post_id": blog_post_id}, {"_id": 0})
        if not post:
            raise HTTPException(status_code=404, detail="Blog post not found")
        if post["publication_status"] == "Published":
            raise HTTPException(status_code=409, detail="This article is already published")
        if not post.get("title") or not post.get("body"):
            raise HTTPException(status_code=400, detail="This draft has no content to publish. Regenerate it first.")
        update = {"publication_status": "Published", "published_at": now_tz().isoformat(), "approved_at": now_tz().isoformat(), "error": ""}
        await db.blog_posts.update_one({"blog_post_id": blog_post_id}, {"$set": update})
        try:
            snippet = await generate_linkedin_snippet(db, {**post, **update})
            update["linkedin_snippet"] = snippet
        except Exception:
            pass
        return {"post": {**post, **update}}

    @router.post("/admin/blog/posts/{blog_post_id}/linkedin-snippet")
    async def admin_generate_snippet(blog_post_id: str, request: Request):
        await authenticate_admin(request, db)
        post = await db.blog_posts.find_one({"blog_post_id": blog_post_id}, {"_id": 0})
        if not post:
            raise HTTPException(status_code=404, detail="Blog post not found")
        if post["publication_status"] != "Published":
            raise HTTPException(status_code=409, detail="LinkedIn posts are created for published articles only")
        try:
            snippet = await generate_linkedin_snippet(db, post)
        except Exception:
            raise HTTPException(status_code=502, detail="Could not generate the LinkedIn post. Please try again.")
        return {"post": {**post, "linkedin_snippet": snippet}, "snippet": snippet}

    @router.post("/admin/blog/posts/{blog_post_id}/reject")
    async def admin_reject_post(blog_post_id: str, request: Request):
        await authenticate_admin(request, db)
        post = await db.blog_posts.find_one({"blog_post_id": blog_post_id}, {"_id": 0})
        if not post:
            raise HTTPException(status_code=404, detail="Blog post not found")
        if post["publication_status"] == "Published":
            raise HTTPException(status_code=409, detail="Published articles cannot be rejected")
        update = {"publication_status": "Rejected", "rejected_at": now_tz().isoformat()}
        await db.blog_posts.update_one({"blog_post_id": blog_post_id}, {"$set": update})
        return {"post": {**post, **update}}

    @router.post("/admin/blog/posts/{blog_post_id}/regenerate")
    async def admin_regenerate_post(blog_post_id: str, request: Request):
        await authenticate_admin(request, db)
        post = await db.blog_posts.find_one({"blog_post_id": blog_post_id}, {"_id": 0})
        if not post:
            raise HTTPException(status_code=404, detail="Blog post not found")
        if post["publication_status"] == "Published":
            raise HTTPException(status_code=409, detail="Published articles cannot be regenerated")
        result = await regenerate_blog_post(db, post)
        fresh = await db.blog_posts.find_one({"blog_post_id": blog_post_id}, {"_id": 0})
        return {**result, "post": fresh}

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
