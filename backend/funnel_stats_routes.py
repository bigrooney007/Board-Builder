"""Public video-view counter + admin funnel numbers board."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth_service import authenticate_admin

VALID_VIDEO_OFFERS = {"recruitment", "reactivation", "activation", "board-fix"}

FUNNELS = [
    {
        "key": "recruitment", "label": "Board Recruitment",
        "lead_sources": ["recruitment"], "video_offer": "recruitment",
        "diy_sources": ["direct_diy_board_recruitment"],
        "dwy_sources": ["direct_board_recruitment_project"],
        "other_sources": ["recruitment", "recruit_with_rooney", "recruitment_selection_onboarding"],
    },
    {
        "key": "reactivation", "label": "Board Reactivation",
        "lead_sources": ["reactivation"], "video_offer": "reactivation",
        "diy_sources": ["direct_diy_board_reactivation"],
        "dwy_sources": ["direct_board_reactivation_project"],
        "other_sources": ["reactivation"],
    },
    {
        "key": "activation", "label": "Fundraising Activation",
        "lead_sources": ["fundraising_activation"], "video_offer": "activation",
        "diy_sources": ["direct_diy_board_activation"],
        "dwy_sources": ["direct_board_activation_project"],
        "other_sources": ["fundraising_activation"],
    },
    {
        "key": "board_fix", "label": "Complete Board Fix",
        "lead_sources": ["board_fix"], "video_offer": "board-fix",
        "diy_sources": ["board_fix_system"],
        "dwy_sources": [],
        "other_sources": [],
    },
]


class VideoViewPayload(BaseModel):
    offer: str = Field(min_length=1)


VALID_PAGES = {"homepage", "board_transformation_form"}


class PageViewPayload(BaseModel):
    page: str = Field(min_length=1)


def create_funnel_stats_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.post("/funnel-metrics/video-view", status_code=201)
    async def record_video_view(payload: VideoViewPayload):
        if payload.offer not in VALID_VIDEO_OFFERS:
            raise HTTPException(status_code=400, detail="Unknown offer")
        await db.funnel_video_views.insert_one({
            "offer": payload.offer,
            "viewed_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"status": "recorded"}

    @router.post("/funnel-metrics/page-view", status_code=201)
    async def record_page_view(payload: PageViewPayload):
        if payload.page not in VALID_PAGES:
            raise HTTPException(status_code=400, detail="Unknown page")
        await db.funnel_page_views.insert_one({
            "page": payload.page,
            "viewed_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"status": "recorded"}

    async def paid_stats(sources: list) -> dict:
        pipeline = [
            {"$match": {"payment_status": "paid", "offer_source": {"$in": sources}}},
            {"$group": {"_id": None, "count": {"$sum": 1}, "revenue": {"$sum": "$amount"}}},
        ]
        rows = await db.payment_transactions.aggregate(pipeline).to_list(1)
        if not rows:
            return {"count": 0, "revenue": 0}
        return {"count": rows[0]["count"], "revenue": rows[0].get("revenue") or 0}

    @router.get("/admin/funnel-stats")
    async def funnel_stats(request: Request):
        await authenticate_admin(request, db)
        funnels = []
        totals = {"form_submits": 0, "video_views": 0, "checkouts": 0, "purchases": 0, "revenue_cents": 0}
        for funnel in FUNNELS:
            form_submits = await db.funnel_leads.count_documents({"offer_source": {"$in": funnel["lead_sources"]}})
            video_views = await db.funnel_video_views.count_documents({"offer": funnel["video_offer"]})
            all_sources = funnel["diy_sources"] + funnel["dwy_sources"] + funnel["other_sources"]
            checkouts = await db.payment_transactions.count_documents({"offer_source": {"$in": all_sources}}) if all_sources else 0
            diy = await paid_stats(funnel["diy_sources"])
            dwy = await paid_stats(funnel["dwy_sources"])
            other = await paid_stats(funnel["other_sources"])
            purchases = diy["count"] + dwy["count"] + other["count"]
            revenue = diy["revenue"] + dwy["revenue"] + other["revenue"]
            funnels.append({
                "key": funnel["key"], "label": funnel["label"],
                "form_submits": form_submits, "video_views": video_views, "checkouts": checkouts,
                "purchases_diy": diy["count"], "purchases_dwy": dwy["count"],
                "purchases_other": other["count"], "purchases": purchases,
                "revenue_cents": revenue,
            })
            totals["form_submits"] += form_submits
            totals["video_views"] += video_views
            totals["checkouts"] += checkouts
            totals["purchases"] += purchases
            totals["revenue_cents"] += revenue
        return {"funnels": funnels, "totals": totals,
                "generated_at": datetime.now(timezone.utc).isoformat()}

    return router
