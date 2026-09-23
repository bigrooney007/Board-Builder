from datetime import datetime, timezone
import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth_service import authenticate_admin


FLOW_KEYS = {
    "main",
    "recruitment",
    "board-fundraising-game",
    "strategic-planning",
    "board-recommitment",
    "facilitated-game",
    "board-applicant-network",
}

EVENT_TYPES = {
    "page_view",
    "contact_entered",
    "video_started",
    "video_progress",
    "video_completed",
    "checkout_started",
    "dashboard_entered",
    "platform_completed",
    "platform_active",
}

VIDEO_DEFINITIONS = [
    {"key": "recruitment_demonstration", "name": "Board Recruitment Demonstration", "flow": "recruitment", "stage": "demonstration"},
    {"key": "recruitment_welcome", "name": "Board Recruitment Onboarding", "flow": "recruitment", "stage": "onboarding"},
    {"key": "game_homepage", "name": "Board Fundraising Game Demonstration", "flow": "board-fundraising-game", "stage": "demonstration"},
    {"key": "game_welcome", "name": "Board Fundraising Game Onboarding", "flow": "board-fundraising-game", "stage": "onboarding"},
    {"key": "strategic_planning_demonstration", "name": "Strategic Planning Demonstration", "flow": "strategic-planning", "stage": "demonstration"},
    {"key": "strategic_planning_welcome", "name": "Strategic Planning Onboarding", "flow": "strategic-planning", "stage": "onboarding"},
    {"key": "board_recommitment_demonstration", "name": "Board Recommitment Demonstration", "flow": "board-recommitment", "stage": "demonstration"},
    {"key": "board_recommitment_welcome", "name": "Board Recommitment Onboarding", "flow": "board-recommitment", "stage": "onboarding"},
]

STRATEGIC_PLANNING_SECTION_VIDEO_DEFINITIONS = [
    {"key": "organization", "name": "Tell Us About Your Organization"},
    {"key": "meeting", "name": "Set Your Strategic Planning Meeting"},
    {"key": "founder-form", "name": "Complete Your Own Strategic Planning Form"},
    {"key": "board-forms", "name": "Invite The Board And Collect Their Ideas"},
    {"key": "facilitation-guide", "name": "Prepare The Strategic Planning Session"},
    {"key": "live-session", "name": "Run The Strategic Planning Session"},
    {"key": "plan-execution", "name": "Review The Plan And Move Into Execution"},
]

RECOMMITMENT_SECTION_VIDEO_DEFINITIONS = [
    {"key": "questions", "name": "Answer The Four Recommitment Questions"},
    {"key": "forms", "name": "Prepare And Send The Recommitment Forms"},
    {"key": "responses", "name": "Understand Responses And Prepare The Conversation"},
    {"key": "decisions", "name": "Confirm Final Outcomes And Board Member Portfolios"},
]

RECRUITMENT_SECTION_VIDEO_DEFINITIONS = [
    {"key": "questions", "name": "Answer The Six Recruitment Questions"},
    {"key": "identify", "name": "Identify The Board Members You Need"},
    {"key": "materials", "name": "Build The Application And Campaign Materials"},
    {"key": "launch", "name": "Launch Your Recruitment Campaign"},
    {"key": "applicants", "name": "Review Applicants"},
    {"key": "interviews", "name": "Run Board Candidate Interviews"},
    {"key": "references", "name": "Complete Reference Checks"},
    {"key": "background", "name": "Complete Background Checks"},
    {"key": "onboarding-prep", "name": "Prepare Onboarding And Appointment Emails"},
    {"key": "onboarding-session", "name": "Facilitate The Onboarding Session"},
    {"key": "portfolios", "name": "Create Board Member Portfolios"},
]

HOME_PAGE_KEYS = {
    "main",
    "recruitment",
    "board-fundraising-game",
    "strategic-planning",
    "board-recommitment",
    "facilitated-game",
}

HOME_PATHS = {
    "main": "/",
    "recruitment": "/recruit",
    "board-fundraising-game": "/board-fundraising-game",
    "strategic-planning": "/strategic-planning",
    "board-recommitment": "/board-recommitment",
    "facilitated-game": "/organize-board-fundraising-game",
    "board-applicant-network": "/join-a-board",
}

PAYMENT_FLOW_SOURCES = {
    "recruitment": {
        "offer_source": {"recruitment"},
        "purchase_source": {"recruitment_497", "recruitment_self_guided_497"},
    },
    "board-fundraising-game": {
        "offer_source": {"board_fundraising_game"},
        "purchase_source": {"board_fundraising_game_497"},
    },
    "strategic-planning": {
        "offer_source": {"strategic_planning"},
        "purchase_source": {"strategic_planning_497"},
    },
    "board-recommitment": {
        "offer_source": {"board_recommitment"},
        "purchase_source": {"board_recommitment_497"},
    },
}


class AnalyticsEvent(BaseModel):
    flow: str = Field(min_length=1, max_length=80)
    event: str = Field(min_length=1, max_length=80)
    page: str = Field(default="", max_length=300)
    video_key: str = Field(default="", max_length=120)
    visitor_id: str = Field(default="", max_length=160)
    progress: float = Field(default=0, ge=0, le=100)
    active_seconds: int = Field(default=0, ge=0, le=3600)
    metadata: dict = Field(default_factory=dict)


class VideoUpdate(BaseModel):
    url: str = Field(default="", max_length=1000)


class HomepageUpdate(BaseModel):
    content: dict = Field(default_factory=dict)


def youtube_id(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value
    patterns = [
        r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group(1)
    raise ValueError("Enter a YouTube URL or 11-character YouTube video ID.")


def create_clean_platform_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.post("/platform-analytics/event", status_code=201)
    async def record_event(payload: AnalyticsEvent):
        if payload.flow not in FLOW_KEYS:
            raise HTTPException(status_code=400, detail="Unknown platform flow")
        if payload.event not in EVENT_TYPES:
            raise HTTPException(status_code=400, detail="Unknown analytics event")
        document = payload.model_dump()
        document["recorded_at"] = datetime.now(timezone.utc).isoformat()
        document["metadata"] = {
            str(key)[:80]: str(value)[:500]
            for key, value in (document.get("metadata") or {}).items()
        }
        await db.platform_analytics.insert_one(document)
        return {"status": "recorded"}

    @router.get("/platform/videos")
    async def public_videos():
        doc = await db.marketing_settings.find_one({"key": "flow_videos"}, {"_id": 0}) or {}
        stored = doc.get("videos") or {}
        videos = []
        for item in VIDEO_DEFINITIONS:
            raw = stored.get(item["key"], "")
            try:
                video_id = youtube_id(raw)
            except ValueError:
                video_id = ""
            videos.append({**item, "url": raw, "youtube_id": video_id})
        return {"videos": videos}

    @router.get("/admin/platform/videos")
    async def admin_videos(request: Request):
        await authenticate_admin(request, db)
        return await public_videos()

    @router.get("/platform/strategic-planning-section-videos")
    async def strategic_planning_section_videos():
        doc = await db.marketing_settings.find_one({"key": "strategic_planning_section_videos"}, {"_id": 0}) or {}
        stored = doc.get("videos") or {}
        rows = []
        for item in STRATEGIC_PLANNING_SECTION_VIDEO_DEFINITIONS:
            raw = stored.get(item["key"], "")
            try:
                video_id = youtube_id(raw)
            except ValueError:
                video_id = ""
            rows.append({**item, "url": raw, "youtube_id": video_id})
        return {"videos": rows}

    @router.get("/admin/platform/strategic-planning-section-videos")
    async def admin_strategic_planning_section_videos(request: Request):
        await authenticate_admin(request, db)
        return await strategic_planning_section_videos()

    @router.put("/admin/platform/strategic-planning-section-videos/{key}")
    async def update_strategic_planning_section_video(key: str, payload: VideoUpdate, request: Request):
        await authenticate_admin(request, db)
        if key not in {item["key"] for item in STRATEGIC_PLANNING_SECTION_VIDEO_DEFINITIONS}:
            raise HTTPException(status_code=404, detail="Unknown Strategic Planning section video")
        raw = payload.url.strip()
        if raw:
            youtube_id(raw)
        await db.marketing_settings.update_one(
            {"key": "strategic_planning_section_videos"},
            {"$set": {f"videos.{key}": raw, "updated_at": datetime.now(timezone.utc).isoformat()},
             "$setOnInsert": {"key": "strategic_planning_section_videos"}},
            upsert=True,
        )
        return {"status": "saved", "key": key, "url": raw}

    @router.get("/platform/recommitment-section-videos")
    async def recommitment_section_videos():
        doc = await db.marketing_settings.find_one({"key": "recommitment_section_videos"}, {"_id": 0}) or {}
        stored = doc.get("videos") or {}
        rows = []
        for item in RECOMMITMENT_SECTION_VIDEO_DEFINITIONS:
            raw = stored.get(item["key"], "")
            try:
                video_id = youtube_id(raw)
            except ValueError:
                video_id = ""
            rows.append({**item, "url": raw, "youtube_id": video_id})
        return {"videos": rows}

    @router.get("/admin/platform/recommitment-section-videos")
    async def admin_recommitment_section_videos(request: Request):
        await authenticate_admin(request, db)
        return await recommitment_section_videos()

    @router.put("/admin/platform/recommitment-section-videos/{key}")
    async def update_recommitment_section_video(key: str, payload: VideoUpdate, request: Request):
        await authenticate_admin(request, db)
        if key not in {item["key"] for item in RECOMMITMENT_SECTION_VIDEO_DEFINITIONS}:
            raise HTTPException(status_code=404, detail="Unknown Recommitment section video")
        raw = payload.url.strip()
        if raw:
            youtube_id(raw)
        await db.marketing_settings.update_one(
            {"key": "recommitment_section_videos"},
            {"$set": {f"videos.{key}": raw, "updated_at": datetime.now(timezone.utc).isoformat()},
             "$setOnInsert": {"key": "recommitment_section_videos"}},
            upsert=True,
        )
        return {"status": "saved", "key": key, "url": raw}

    @router.get("/platform/recruitment-section-videos")
    async def recruitment_section_videos():
        doc = await db.marketing_settings.find_one({"key": "recruitment_section_videos"}, {"_id": 0}) or {}
        stored = doc.get("videos") or {}
        rows = []
        for item in RECRUITMENT_SECTION_VIDEO_DEFINITIONS:
            raw = stored.get(item["key"], "")
            try:
                video_id = youtube_id(raw)
            except ValueError:
                video_id = ""
            rows.append({**item, "url": raw, "youtube_id": video_id})
        return {"videos": rows}

    @router.get("/admin/platform/recruitment-section-videos")
    async def admin_recruitment_section_videos(request: Request):
        await authenticate_admin(request, db)
        return await recruitment_section_videos()

    @router.put("/admin/platform/recruitment-section-videos/{key}")
    async def update_recruitment_section_video(key: str, payload: VideoUpdate, request: Request):
        await authenticate_admin(request, db)
        if key not in {item["key"] for item in RECRUITMENT_SECTION_VIDEO_DEFINITIONS}:
            raise HTTPException(status_code=404, detail="Unknown Recruitment section video")
        raw = payload.url.strip()
        if raw:
            youtube_id(raw)
        await db.marketing_settings.update_one(
            {"key": "recruitment_section_videos"},
            {"$set": {f"videos.{key}": raw, "updated_at": datetime.now(timezone.utc).isoformat()},
             "$setOnInsert": {"key": "recruitment_section_videos"}},
            upsert=True,
        )
        return {"status": "saved", "key": key, "url": raw}

    @router.put("/admin/platform/videos/{key}")
    async def update_video(key: str, payload: VideoUpdate, request: Request):
        await authenticate_admin(request, db)
        if key not in {item["key"] for item in VIDEO_DEFINITIONS}:
            raise HTTPException(status_code=404, detail="Unknown platform video")
        raw = payload.url.strip()
        if raw:
            youtube_id(raw)
        await db.marketing_settings.update_one(
            {"key": "flow_videos"},
            {"$set": {f"videos.{key}": raw, "updated_at": datetime.now(timezone.utc).isoformat()},
             "$setOnInsert": {"key": "flow_videos"}},
            upsert=True,
        )
        return {"status": "saved", "key": key, "url": raw}

    @router.get("/platform/homepages/{page_key}")
    async def public_homepage(page_key: str):
        if page_key not in HOME_PAGE_KEYS:
            raise HTTPException(status_code=404, detail="Unknown home page")
        doc = await db.marketing_settings.find_one({"key": "clean_homepage_content"}, {"_id": 0}) or {}
        return {"page_key": page_key, "content": (doc.get("pages") or {}).get(page_key, {})}

    @router.get("/admin/platform/homepages")
    async def admin_homepages(request: Request):
        await authenticate_admin(request, db)
        doc = await db.marketing_settings.find_one({"key": "clean_homepage_content"}, {"_id": 0}) or {}
        pages = doc.get("pages") or {}
        return {"pages": [{"key": key, "content": pages.get(key, {})} for key in sorted(HOME_PAGE_KEYS)]}

    @router.put("/admin/platform/homepages/{page_key}")
    async def update_homepage(page_key: str, payload: HomepageUpdate, request: Request):
        await authenticate_admin(request, db)
        if page_key not in HOME_PAGE_KEYS:
            raise HTTPException(status_code=404, detail="Unknown home page")
        await db.marketing_settings.update_one(
            {"key": "clean_homepage_content"},
            {"$set": {f"pages.{page_key}": payload.content, "updated_at": datetime.now(timezone.utc).isoformat()},
             "$setOnInsert": {"key": "clean_homepage_content"}},
            upsert=True,
        )
        return {"status": "saved", "page_key": page_key}

    async def event_count(flow: str, event: str) -> int:
        return await db.platform_analytics.count_documents({"flow": flow, "event": event})

    async def unique_event_count(flow: str, event: str, page: str = "") -> int:
        query = {"flow": flow, "event": event}
        if page:
            query["page"] = page
        values = await db.platform_analytics.distinct("visitor_id", query)
        return len([value for value in values if value])

    async def homepage_visitors(flow: str) -> int:
        return await unique_event_count(flow, "page_view", HOME_PATHS.get(flow, ""))

    async def payment_counts(flow: str) -> dict:
        contract = PAYMENT_FLOW_SOURCES.get(flow)
        if not contract:
            return {"stripe_sessions": 0, "purchases": 0}
        source_match = {
            "$or": [
                {"offer_source": {"$in": list(contract["offer_source"])}},
                {"purchase_source": {"$in": list(contract["purchase_source"])}},
            ]
        }
        stripe_sessions = await db.payment_transactions.count_documents(source_match)
        purchases = await db.payment_transactions.count_documents(
            {"$and": [source_match, {"payment_status": "paid"}]}
        )
        return {"stripe_sessions": stripe_sessions, "purchases": purchases}

    @router.get("/admin/platform-analytics")
    async def platform_analytics(request: Request):
        await authenticate_admin(request, db)

        video_pipeline = [
            {"$match": {"event": {"$in": ["video_started", "video_progress", "video_completed"]}, "video_key": {"$ne": ""}}},
            {"$group": {
                "_id": {"visitor_id": "$visitor_id", "video_key": "$video_key", "flow": "$flow"},
                "max_progress": {"$max": "$progress"},
                "started": {"$max": {"$cond": [{"$eq": ["$event", "video_started"]}, 1, 0]}},
                "completed": {"$max": {"$cond": [{"$eq": ["$event", "video_completed"]}, 1, 0]}},
            }},
            {"$group": {
                "_id": {"video_key": "$_id.video_key", "flow": "$_id.flow"},
                "viewers": {"$sum": "$started"},
                "completed": {"$sum": "$completed"},
                "average_watch_rate": {"$avg": "$max_progress"},
            }},
            {"$sort": {"_id.flow": 1, "_id.video_key": 1}},
        ]
        video_rows = await db.platform_analytics.aggregate(video_pipeline).to_list(100)
        videos = [{
            "flow": row["_id"]["flow"],
            "video_key": row["_id"]["video_key"],
            "viewers": row.get("viewers", 0),
            "completed": row.get("completed", 0),
            "average_watch_rate": round(float(row.get("average_watch_rate") or 0), 1),
        } for row in video_rows]

        activity_pipeline = [
            {"$match": {"event": "platform_active", "active_seconds": {"$gt": 0}}},
            {"$group": {
                "_id": {"visitor_id": "$visitor_id", "flow": "$flow"},
                "seconds": {"$sum": "$active_seconds"},
            }},
            {"$group": {
                "_id": "$_id.flow",
                "average_seconds": {"$avg": "$seconds"},
                "users": {"$sum": 1},
            }},
        ]
        activity_rows = await db.platform_analytics.aggregate(activity_pipeline).to_list(50)
        activity = {
            row["_id"]: {
                "average_seconds": round(float(row.get("average_seconds") or 0), 1),
                "users": row.get("users", 0),
            }
            for row in activity_rows
        }

        flows = []
        for flow in ["main", "recruitment", "board-fundraising-game", "strategic-planning", "board-recommitment", "facilitated-game", "board-applicant-network"]:
            payments = await payment_counts(flow)
            flows.append({
                "flow": flow,
                "homepage_visitors": await homepage_visitors(flow),
                "page_views": await event_count(flow, "page_view"),
                "contacts_entered": await unique_event_count(flow, "contact_entered"),
                "checkout_started": await event_count(flow, "checkout_started"),
                "stripe_sessions": payments["stripe_sessions"],
                "purchases": payments["purchases"],
                "dashboard_entered": await unique_event_count(flow, "dashboard_entered"),
                "platform_completed": await unique_event_count(flow, "platform_completed"),
                "average_use_seconds": activity.get(flow, {}).get("average_seconds", 0),
                "active_users": activity.get(flow, {}).get("users", 0),
            })

        return {
            "flows": flows,
            "videos": videos,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    return router
