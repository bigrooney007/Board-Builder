"""The compact, protected V2 entry, recovery and support endpoints."""
import base64
import copy
import io
import json
import math
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from v2_core import (
    CALENDLY_URL, CURRENCY, PRICE_CENTS, PRODUCTS, cookie_options, csrf_guard,
    decode_session, digest, enabled, existing_admin, existing_member, find_journey,
    journey_lock, new_id, now_iso, origin, preview_access, public_journey,
    require_owner, secret, session_token, set_owner_cookie, validate_email,
)


async def body_json(request, limit=1_600_000):
    body = await request.body()
    if len(body) > limit:
        raise HTTPException(413, "This submission is too large.")
    try:
        value = json.loads(body)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, "Please provide a valid form submission.") from exc
    if not isinstance(value, dict):
        raise HTTPException(422, "Please provide a valid form submission.")
    return value


def text(value, label, maximum=300, required=True):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise HTTPException(422, "Please enter " + label + ".")
    return value.strip()


async def rate_limit(db, request, action, identifier="", limit=8):
    address = request.client.host if request.client else "unknown"
    key = digest(action + ":" + address + ":" + identifier)
    now = datetime.now(timezone.utc)
    row = await db.v2_rate_limits.find_one({"key": key}, {"_id": 0})
    if row and row.get("until", "") > now.isoformat() and row.get("count", 0) >= limit:
        raise HTTPException(429, "Please wait a little before trying this action again.")
    if not row or row.get("until", "") <= now.isoformat():
        await db.v2_rate_limits.update_one({"key": key}, {"$set": {"count": 1, "until": (now + timedelta(minutes=15)).isoformat()}}, upsert=True)
    else:
        await db.v2_rate_limits.update_one({"key": key}, {"$inc": {"count": 1}})


def clean_branding(value, organization):
    if not isinstance(value, dict):
        raise HTTPException(422, "Please confirm your organization's branding.")
    name = text(value.get("organization_name") or organization, "your organization name")
    result = {"organization_name": name, "logo_data": "", "primary_color": "", "secondary_color": ""}
    for key in ("primary_color", "secondary_color"):
        color = str(value.get(key) or "").strip()
        if color and not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise HTTPException(422, "Choose a six-digit hexadecimal brand color.")
        result[key] = color.lower()
    logo = value.get("logo_data") or ""
    if logo:
        if not isinstance(logo, str) or len(logo) > 1_500_000 or not re.match(r"^data:image/(png|jpeg|webp);base64,", logo):
            raise HTTPException(422, "Use a PNG, JPEG or WebP logo smaller than 1 MB.")
        try:
            from PIL import Image
            raw = base64.b64decode(logo.split(",", 1)[1], validate=True)
            if len(raw) > 1_048_576:
                raise ValueError("Too large")
            with Image.open(io.BytesIO(raw)) as image:
                if image.width * image.height > 16_000_000 or image.format not in {"PNG", "JPEG", "WEBP"}:
                    raise ValueError("Unsupported image")
                image.load()
                image.thumbnail((1200, 1200))
                image = image.convert("RGBA")
                output = io.BytesIO()
                image.save(output, format="PNG")
            if output.tell() > 1_500_000:
                raise ValueError("Too large")
            result["logo_data"] = "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()
        except Exception as exc:
            raise HTTPException(422, "This logo could not be read. Use a small PNG, JPEG or WebP image.") from exc
    return result


def replace_organization(value, previous, current):
    if isinstance(value, str):
        return re.sub(r"(?<!\w)" + re.escape(previous) + r"(?!\w)", lambda _: current, value) if previous else value
    if isinstance(value, list):
        return [replace_organization(item, previous, current) for item in value]
    if isinstance(value, dict):
        return {key: replace_organization(item, previous, current) for key, item in value.items()}
    return value


async def existing_intake(db, member, product):
    """Reuse only authenticated customer-owned intake, never an email lookup alone."""
    if not member:
        return {}
    user_id, email = member.get("user_id"), str(member.get("email", "")).lower()
    if product == "recruit":
        for name in ("recruitment_free_assessments", "recruit_free_assessments", "free_recruitment_assessments"):
            row = await getattr(db, name).find_one({"member_user_id": user_id}, {"_id": 0}, sort=[("updated_at", -1)])
            if row:
                return copy.deepcopy(row.get("answers") or {})
    elif product in {"strategic-planning", "board-recommitment"}:
        row = await db.guided_product_leads.find_one({"product": product, "email": email}, {"_id": 0}, sort=[("updated_at", -1)])
        if row:
            return copy.deepcopy(row.get("prepayment_answers") or {})
    else:
        row = await db.game_free_answers.find_one({"user_id": user_id}, {"_id": 0})
        if row:
            return copy.deepcopy(row.get("answers") or {})
    return {}


def create_v2_router(db):
    router = APIRouter(prefix="/api/v2", tags=["Simplified V2 preview"])

    @router.get("/access")
    async def access(request: Request):
        await preview_access(request, db)
        return {"enabled": True, "allowed": True}

    @router.post("/preview-access")
    async def enter_preview(request: Request, response: Response):
        enabled()
        csrf_guard(request)
        await rate_limit(db, request, "preview-key", limit=8)
        value = await body_json(request, 2048)
        configured = __import__("os").environ.get("NBB_V2_PREVIEW_KEY", "")
        supplied = value.get("key")
        if len(configured) < 16 or not isinstance(supplied, str) or not secrets.compare_digest(supplied, configured):
            raise HTTPException(403, "This preview access key is not valid.")
        response.set_cookie("nbb_v2_preview", session_token("preview"), **cookie_options())
        return {"enabled": True, "allowed": True}

    @router.get("/catalog")
    async def catalog(request: Request):
        await preview_access(request, db)
        return {"products": [{"product": key, "title": value, "amount": PRICE_CENTS, "currency": CURRENCY} for key, value in PRODUCTS.items()],
                "calendly_url": CALENDLY_URL, "journey_version": "v2"}

    @router.post("/journeys")
    async def create_journey(request: Request):
        await preview_access(request, db)
        csrf_guard(request)
        await rate_limit(db, request, "new-journey", limit=30)
        value = await body_json(request, 25000)
        product = value.get("product")
        if product not in PRODUCTS:
            raise HTTPException(422, "Choose one of the four board services.")
        name = text(value.get("name"), "your name", 200)
        email = validate_email(value.get("email"))
        organization = text(value.get("organization"), "your organization name")
        count = str(value.get("desired_count") or "not_sure")
        if product == "recruit" and count != "not_sure" and (not count.isdigit() or not 1 <= int(count) <= 50):
            raise HTTPException(422, "Choose a number of board members from 1 to 50, or choose I'm not sure yet.")
        board_count = value.get("board_count") or 0
        if not isinstance(board_count, int) or isinstance(board_count, bool) or board_count < 0 or board_count > 200:
            raise HTTPException(422, "Enter a valid number of board members.")
        if product in {"strategic-planning", "board-recommitment"} and board_count < 1:
            raise HTTPException(422, "Enter the number of board members who will participate.")
        goal = value.get("goal_amount") or 0
        if not isinstance(goal, (int, float)) or isinstance(goal, bool) or not math.isfinite(goal) or goal < 0 or goal > 1_000_000_000:
            raise HTTPException(422, "Enter a valid fundraising goal.")
        if product == "board-fundraising-game" and goal <= 0:
            raise HTTPException(422, "Enter your fundraising goal.")
        member = await existing_member(request, db)
        if member and str(member.get("email", "")).lower() != email:
            member = None
        from v2_forms import validate_intake
        saved = validate_intake(product, await existing_intake(db, member, product))
        draft = secrets.token_urlsafe(32)
        journey = {"journey_id": new_id(), "journey_version": "v2", "product": product,
            "name": name, "email": email, "organization": organization, "desired_count": count,
            "board_count": board_count, "goal_amount": goal, "answers": saved,
            "branding": {"organization_name": organization, "logo_data": "", "primary_color": "", "secondary_color": ""},
            "state": "free", "draft_digest": digest(draft), "form_token": secrets.token_urlsafe(32),
            "group_token": secrets.token_urlsafe(32), "meeting": {}, "decision_version": 0,
            "campaign_status": "draft", "created_at": now_iso(), "updated_at": now_iso()}
        if member:
            journey["member_user_id"] = member["user_id"]
        await db.v2_journeys.insert_one(journey.copy())
        return {"journey_id": journey["journey_id"], "draft_token": draft}

    @router.get("/journeys/{jid}")
    async def journey(jid: str, request: Request):
        return public_journey(await require_owner(request, db, jid, paid=False))

    @router.put("/journeys/{jid}/answers")
    async def save_answers(jid: str, request: Request):
        journey = await require_owner(request, db, jid, paid=False)
        if journey["state"] == "paid":
            raise HTTPException(409, "Your introductory answers have been saved with this purchase. Edit the generated resources instead.")
        from v2_forms import validate_intake, complete_intake
        value = await body_json(request, 250000)
        answers = {**journey.get("answers", {}), **validate_intake(journey["product"], value.get("answers"))}
        await db.v2_journeys.update_one({"journey_id": jid, "state": "free"}, {"$set": {"answers": answers, "updated_at": now_iso()}})
        return {"saved": True, "complete": complete_intake(journey["product"], answers)}

    @router.put("/journeys/{jid}/branding")
    async def branding(jid: str, request: Request):
        journey = await require_owner(request, db, jid)
        value = await body_json(request)
        brand = clean_branding(value.get("branding", value), journey["organization"])
        async with journey_lock(db, jid):
            journey = await find_journey(db, jid)
            if brand != journey.get("branding"):
                if await db.v2_resources.find_one({"journey_id": jid, "status": "approved"}):
                    raise HTTPException(409, "Approved resources retain the organization details you confirmed. Their saved branding cannot be changed.")
                old_name = (journey.get("branding") or {}).get("organization_name") or journey["organization"]
                await db.v2_journeys.update_one({"journey_id": jid}, {"$set": {"branding": brand, "organization": brand["organization_name"],
                                                                                 "branding_confirmed": True, "updated_at": now_iso()}})
                resources = await db.v2_resources.find({"journey_id": jid}, {"_id": 0}).to_list(500)
                for resource in resources:
                    updates = {"approved_revision": None, "updated_at": now_iso()}
                    if resource["status"] == "approved":
                        updates["status"] = "ready"
                    if old_name != brand["organization_name"]:
                        updates["text"] = replace_organization(resource.get("text", ""), old_name, brand["organization_name"])
                        updates["structured"] = replace_organization(resource.get("structured") or {}, old_name, brand["organization_name"])
                    await db.v2_resources.update_one({"resource_id": resource["resource_id"], "revision": resource["revision"]},
                                                     {"$set": updates, "$inc": {"revision": 1}})
            else:
                await db.v2_journeys.update_one({"journey_id": jid}, {"$set": {"branding_confirmed": True}})
        return {"branding": brand, "saved": True}

    @router.post("/journeys/{jid}/setup")
    async def complete_paid_setup(jid: str, request: Request):
        journey = await require_owner(request, db, jid)
        value = await body_json(request)
        from v2_journey_flow import GROUP_PRODUCTS, validate_meeting
        meeting = validate_meeting(value.get("meeting")) if journey["product"] in GROUP_PRODUCTS else None
        await branding(jid, request)
        updates = {"setup_complete": True, "setup_initialization_status": "pending", "updated_at": now_iso()}
        if meeting is not None:
            updates["meeting"] = meeting
        await db.v2_journeys.update_one({"journey_id": jid}, {"$set": updates})
        journey = await find_journey(db, jid)
        from v2_forms import initialize_forms
        from v2_resources import initialize_resources
        try:
            await initialize_forms(db, journey)
            await initialize_resources(db, journey)
        except Exception as exc:
            await db.v2_journeys.update_one({"journey_id": jid}, {"$set": {"setup_complete": False, "setup_initialization_status": "failed", "generation_status": "waiting_setup", "technical_issue": "Your payment and organization details are saved. Resource preparation needs a retry."}})
            raise HTTPException(503, "Your payment and details are saved. Please retry preparing your resources.") from exc
        await db.v2_journeys.update_one({"journey_id": jid}, {"$set": {"setup_initialization_status": "complete", "technical_issue": ""}})
        return {"saved": True, "journey": public_journey(await find_journey(db, jid)), "next": f"/v2/resources/{jid}"}

    @router.post("/journeys/{jid}/checkout")
    async def purchase(jid: str, request: Request):
        journey = await require_owner(request, db, jid, paid=False)
        from v2_payments import checkout
        return await checkout(db, journey)

    @router.get("/journeys/{jid}/payment")
    async def payment(jid: str, request: Request, response: Response, session_id: str):
        await require_owner(request, db, jid, paid=False)
        from v2_payments import verify_payment
        result = await verify_payment(db, jid, session_id)
        if result["payment_status"] == "paid":
            set_owner_cookie(response, await find_journey(db, jid))
        return result

    @router.post("/access-link")
    async def exchange_link(request: Request, response: Response):
        enabled()
        csrf_guard(request)
        value = await body_json(request, 2048)
        supplied = value.get("token")
        if not isinstance(supplied, str) or not 32 <= len(supplied) <= 200:
            raise HTTPException(401, "This secure link is no longer available. Recover your resource access.")
        row = await db.v2_access_links.find_one({"token_digest": digest(supplied), "expires_at": {"$gt": now_iso()}}, {"_id": 0})
        if not row:
            raise HTTPException(401, "This secure link is no longer available. Recover your resource access.")
        if row.get("consumed_at"):
            await require_owner(request, db, row["journey_id"])
        else:
            consumed = await db.v2_access_links.update_one({"token_digest": row["token_digest"], "consumed_at": {"$exists": False}, "expires_at": {"$gt": now_iso()}},
                                                          {"$set": {"consumed_at": now_iso()}})
            if not consumed.modified_count:
                raise HTTPException(409, "This link has just been opened. Please try again from your email.")
        journey = await find_journey(db, row["journey_id"])
        if journey.get("state") != "paid":
            raise HTTPException(403, "This product has not been purchased.")
        set_owner_cookie(response, journey)
        return {"journey_id": row["journey_id"], "next": row["action_path"]}

    @router.post("/recover")
    async def recover(request: Request):
        enabled()
        csrf_guard(request)
        value = await body_json(request, 2048)
        email = validate_email(value.get("email"))
        await rate_limit(db, request, "recover-address", identifier=digest(email), limit=3)
        await rate_limit(db, request, "recover-source", limit=15)
        from v2_email import queue_email
        journeys = await db.v2_journeys.find({"email": email, "state": "paid"}, {"_id": 0}).to_list(50)
        window = int(datetime.now(timezone.utc).timestamp() // 900)
        for journey in journeys:
            await queue_email(db, f"recover:{journey['journey_id']}:{window}", email, "Your Secure Board Builder Resource Link",
                              "Use this secure link to return to the resources you purchased. Your approved documents remain available and you can open the next action directly from future emails.",
                              journey_id=journey["journey_id"], action_path="/v2/resources/" + journey["journey_id"])
        return {"sent": True, "message": "If this address has purchased resources, we will email secure access links."}

    @router.get("/journeys/{jid}/emails")
    async def email_status(jid: str, request: Request):
        await require_owner(request, db, jid)
        rows = await db.v2_email_outbox.find({"journey_id": jid}, {"_id": 0, "payload": 0, "provider_key": 0}).sort("created_at", -1).to_list(250)
        return {"emails": rows}

    @router.post("/journeys/{jid}/emails/{event_id}/retry")
    async def email_retry(jid: str, event_id: str, request: Request):
        await require_owner(request, db, jid)
        from v2_email import retry_email
        record = await retry_email(db, event_id, journey_id=jid)
        return {key: record.get(key) for key in ("event_id", "status", "attempts", "error")}

    @router.get("/admin/overview")
    async def admin_overview(request: Request):
        enabled()
        if not await existing_admin(request, db):
            raise HTTPException(401, "Administrator access is required.")
        journeys = await db.v2_journeys.find({}, {"_id": 0, "draft_digest": 0, "form_token": 0, "group_token": 0}).sort("created_at", -1).to_list(250)
        rows = []
        for journey in journeys:
            jid = journey["journey_id"]
            resources = await db.v2_resources.find({"journey_id": jid}, {"_id": 0, "text": 0, "structured": 0, "approved_versions": 0}).to_list(250)
            payment = await db.payment_transactions.find_one({"journey_id": jid, "journey_version": "v2"}, {"_id": 0, "checkout_url": 0}, sort=[("created_at", -1)])
            rows.append({**public_journey(journey), "customer": journey["name"], "organization": journey["organization"],
                         "payment_status": (payment or {}).get("payment_status", "not_purchased"), "payment": payment,
                         "resources": resources, "response_count": await db.v2_submissions.count_documents({"journey_id": jid})})
        emails = await db.v2_email_outbox.find({}, {"_id": 0, "payload": 0, "provider_key": 0}).sort("created_at", -1).to_list(500)
        issues = [{"journey_id": row["journey_id"], "message": row["technical_issue"]} for row in rows if row.get("technical_issue")]
        return {"journeys": rows, "emails": emails, "issues": issues}

    @router.post("/admin/emails/{event_id}/retry")
    async def admin_retry(event_id: str, request: Request):
        enabled()
        csrf_guard(request)
        if not await existing_admin(request, db):
            raise HTTPException(401, "Administrator access is required.")
        from v2_email import retry_email
        record = await retry_email(db, event_id)
        return {key: record.get(key) for key in ("event_id", "status", "attempts", "error")}

    from v2_resources import create_v2_resource_router
    from v2_forms import create_v2_form_router
    from v2_campaigns import create_v2_campaign_router
    from v2_landing_content import create_landing_content_router
    # Subrouters already own the /api/v2 prefix.
    combined = APIRouter()
    combined.include_router(router)
    combined.include_router(create_landing_content_router(db))
    combined.include_router(create_v2_resource_router(db))
    combined.include_router(create_v2_form_router(db))
    combined.include_router(create_v2_campaign_router(db))
    return combined
