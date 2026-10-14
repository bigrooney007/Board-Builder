"""Administrator-written educational pages, independent of customer journeys."""
from copy import deepcopy
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response

from v2_core import csrf_guard, enabled, existing_admin, now_iso, preview_access
from v2_routes import body_json, text


DEFAULTS = json.loads(Path(__file__).with_name("v2_landing_defaults.json").read_text())
SHORT_FIELDS = {"eyebrow", "headline", "education_eyebrow", "education_heading",
                "service_heading", "closing_heading"}
LONG_FIELDS = {"intro", "hero_note", "outcome", "service_body", "closing_body"}


def validate_content(value):
    if not isinstance(value, dict) or set(value) != SHORT_FIELDS | LONG_FIELDS | {"teaching"}:
        raise HTTPException(422, "Please provide the educational page fields only.")
    cleaned = {key: text(value[key], key.replace("_", " "), 300 if key in SHORT_FIELDS else 12000)
               for key in SHORT_FIELDS | LONG_FIELDS}
    steps = value["teaching"]
    if not isinstance(steps, list) or not 1 <= len(steps) <= 20:
        raise HTTPException(422, "Include between one and twenty teaching steps.")
    cleaned["teaching"] = []
    for step in steps:
        if not isinstance(step, list) or len(step) != 2:
            raise HTTPException(422, "Each teaching step needs a heading and an explanation.")
        cleaned["teaching"].append([text(step[0], "a step heading", 300),
                                    text(step[1], "a step explanation", 12000)])
    return cleaned


def revision(value):
    number = value.get("revision")
    if not isinstance(number, int) or isinstance(number, bool) or number < 0:
        raise HTTPException(422, "Please reload the page before saving.")
    return number


def page_state(product, record):
    record = record or {}
    return {"product": product, "revision": record.get("revision", 0),
            "draft": deepcopy(record.get("draft") or DEFAULTS[product]),
            "published": deepcopy(record.get("published") or DEFAULTS[product]),
            "published_at": record.get("published_at"), "saved_at": record.get("saved_at")}


def create_landing_content_router(db):
    router = APIRouter(prefix="/api/v2", tags=["Educational page content"])

    def valid_product(product):
        if product not in DEFAULTS:
            raise HTTPException(404, "This educational page was not found.")

    async def admin(request):
        enabled()
        csrf_guard(request)
        user = await existing_admin(request, db)
        if not user:
            raise HTTPException(401, "Administrator access is required.")
        return user

    @router.get("/landing-content/{product}")
    async def public_content(product: str, request: Request, response: Response):
        await preview_access(request, db)
        valid_product(product)
        record = await db.v2_landing_content.find_one({"product": product}, {"published": 1, "published_at": 1, "_id": 0})
        response.headers["Cache-Control"] = "no-store"
        return {"product": product, "content": (record or {}).get("published") or deepcopy(DEFAULTS[product])}

    @router.get("/admin/landing-content/{product}")
    async def load_page(product: str, request: Request, response: Response):
        await admin(request)
        valid_product(product)
        response.headers["Cache-Control"] = "no-store"
        return page_state(product, await db.v2_landing_content.find_one({"product": product}, {"_id": 0}))

    @router.put("/admin/landing-content/{product}")
    async def save_draft(product: str, request: Request):
        user = await admin(request)
        valid_product(product)
        value = await body_json(request, 350000)
        number = revision(value)
        content = validate_content(value.get("content"))
        # Initialize once without overwriting either the draft or published text.
        await db.v2_landing_content.update_one({"product": product},
            {"$setOnInsert": {"product": product, "revision": 0}}, upsert=True)
        record = await db.v2_landing_content.find_one_and_update(
            {"product": product, "revision": number},
            {"$set": {"draft": content, "saved_at": now_iso(), "saved_by": user["user_id"]},
             "$inc": {"revision": 1}}, return_document=True)
        if not record:
            raise HTTPException(409, "This page changed in another session. Copy your unsaved text, then reload the saved page.")
        return page_state(product, record)

    @router.post("/admin/landing-content/{product}/publish")
    async def publish(product: str, request: Request):
        user = await admin(request)
        valid_product(product)
        value = await body_json(request, 2048)
        number = revision(value)
        current = await db.v2_landing_content.find_one({"product": product, "revision": number}, {"_id": 0})
        if not current or not current.get("draft"):
            raise HTTPException(409, "Save the current draft before publishing it.")
        record = await db.v2_landing_content.find_one_and_update(
            {"product": product, "revision": number},
            {"$set": {"published": deepcopy(current["draft"]), "published_at": now_iso(),
                      "published_by": user["user_id"]}, "$inc": {"revision": 1}}, return_document=True)
        if not record:
            raise HTTPException(409, "This draft changed in another session. Reload and review it before publishing.")
        return page_state(product, record)

    return router
