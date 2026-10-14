"""Isolated access and records for the simplified Board Builder preview.

Existing members, purchases and product records are never given new entitlements
by this module. Paid email links exchange a scoped, expiring capability for an
HttpOnly cookie. Enabling V2 does not publish or redirect any original route.
"""
import hashlib
import os
import re
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, unquote

import jwt
from fastapi import HTTPException, Request

PRODUCTS = {
    "recruit": "Board Recruitment",
    "board-fundraising-game": "Board Fundraising Activation",
    "strategic-planning": "Strategic Planning",
    "board-recommitment": "Board Recommitment",
}
PRICE_CENTS = 19700
CURRENCY = "usd"
JOURNEY_VERSION = "v2"
CALENDLY_URL = "https://calendly.com/boardbuilder/recruitboard"
SESSION_DAYS = 7
LINK_DAYS = 14


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return str(uuid.uuid4())


def is_enabled():
    return os.environ.get("NBB_V2_ENABLED", "true").strip().lower() == "true"


def enabled():
    if not is_enabled():
        raise HTTPException(404, "This version is not available.")


def origin():
    value = (os.environ.get("NBB_V2_ORIGIN") or os.environ.get("PUBLIC_ORIGIN")
             or "https://nonprofitboardbuilder.com").rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise HTTPException(503, "The V2 site address needs to be configured.")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1", "testserver"}:
        raise HTTPException(503, "The V2 site requires a secure address.")
    return value


def digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def secret():
    value = os.environ.get("NBB_V2_SESSION_SECRET") or os.environ.get("JWT_SECRET", "")
    if len(value) < 32:
        raise HTTPException(503, "Secure V2 access is not configured.")
    return value


def validate_email(value):
    value = str(value or "").strip().lower()
    if len(value) > 254 or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value):
        raise HTTPException(422, "Enter a valid email address.")
    return value


def internal_path(path):
    # Never allow open redirects or old-workflow handoffs from a V2 email.
    if not isinstance(path, str) or not path.startswith("/v2/") or "\\" in path or any(ord(c) < 32 for c in path):
        raise HTTPException(422, "Choose a V2 action link.")
    parsed = urlparse(path)
    decoded = parsed.path
    for _ in range(5):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    if (parsed.netloc or parsed.scheme or parsed.fragment or "//" in decoded or "\\" in decoded
            or any(segment in {".", ".."} for segment in decoded.split("/"))
            or any(ord(c) < 32 for c in decoded) or not decoded.startswith("/v2/")):
        raise HTTPException(422, "Choose a V2 action link.")
    return path


def session_token(kind, **claims):
    return jwt.encode({"iss": "nbb-v2", "aud": "nbb-v2", "kind": kind, **claims,
                       "exp": datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)}, secret(), algorithm="HS256")


def decode_session(token, kind):
    if not token:
        return None
    try:
        value = jwt.decode(token, secret(), algorithms=["HS256"], audience="nbb-v2", issuer="nbb-v2")
        return value if value.get("kind") == kind else None
    except jwt.PyJWTError:
        return None


def cookie_options():
    return {"httponly": True, "secure": origin().startswith("https://"), "samesite": "lax",
            "path": "/api/v2", "max_age": SESSION_DAYS * 86400}


def set_owner_cookie(response, journey):
    response.set_cookie("nbb_v2_owner_" + journey["journey_id"],
                        session_token("owner", journey_id=journey["journey_id"], email=journey["email"]),
                        **cookie_options())


async def existing_member(request, db):
    try:
        from member_auth import authenticate_member
        return await authenticate_member(request, db)
    except (HTTPException, ImportError):
        return None


async def existing_admin(request, db):
    try:
        from auth_service import authenticate_admin
        return await authenticate_admin(request, db)
    except (HTTPException, ImportError):
        return None


async def preview_access(request, db):
    enabled()
    # Public education/intake access is independent of paid-resource permission.
    # An optional configured key still supports intentionally private instances.
    if not os.environ.get("NBB_V2_PREVIEW_KEY"):
        return True
    if decode_session(request.cookies.get("nbb_v2_preview"), "preview"):
        return True
    if await existing_admin(request, db):
        return True
    for name, value in request.cookies.items():
        if name.startswith("nbb_v2_owner_") and decode_session(value, "owner"):
            return True
    raise HTTPException(403, "Enter your preview access key to test this version.")


async def find_journey(db, journey_id):
    journey = await db.v2_journeys.find_one({"journey_id": journey_id}, {"_id": 0})
    if not journey:
        raise HTTPException(404, "This resource link is not available.")
    return journey


def ensure_paid(journey):
    if journey.get("state") != "paid":
        raise HTTPException(403, "This product has not been purchased.")


def csrf_guard(request):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    supplied = request.headers.get("origin", "").rstrip("/")
    if supplied and supplied != origin():
        raise HTTPException(403, "Open this action from your Board Builder link.")


async def require_owner(request, db, journey_id, paid=True):
    enabled()
    csrf_guard(request)
    journey = await find_journey(db, journey_id)
    owner = decode_session(request.cookies.get("nbb_v2_owner_" + journey_id), "owner")
    allowed = bool(owner and owner.get("journey_id") == journey_id and owner.get("email") == journey["email"])
    if not allowed:
        member = await existing_member(request, db)
        allowed = bool(member and str(member.get("email", "")).lower() == journey["email"])
    if not allowed:
        allowed = bool(await existing_admin(request, db))
    if not allowed and not paid:
        draft = request.headers.get("X-V2-Draft", "")
        expected = journey.get("draft_digest", "")
        allowed = bool(draft and expected and secrets.compare_digest(digest(draft), expected))
    if not allowed:
        raise HTTPException(401, "Use the secure link in your email, or recover your resource access.")
    if paid:
        ensure_paid(journey)
    return journey


def public_journey(journey):
    return {key: value for key, value in journey.items() if key not in {
        "_id", "draft_digest", "mutation_lease", "mutation_lease_until", "payment_activation_lease", "generation_lease",
    }}


def install_v2_response_headers(app):
    """Apply only to V2 responses, including errors and disabled preview routes."""
    @app.middleware("http")
    async def v2_headers(request, call_next):
        response = await call_next(request)
        if request.url.path == "/api/v2" or request.url.path.startswith("/api/v2/"):
            response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response


@asynccontextmanager
async def journey_lock(db, journey_id):
    """Short Mongo-backed mutation lease, shared by approval and group decisions.

    No provider calls occur inside this lock. A lost process's lease expires so a
    customer can retry. Compare-and-set checks additionally protect revisions.
    """
    token = secrets.token_urlsafe(24)
    until = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
    claimed = await db.v2_journeys.update_one(
        {"journey_id": journey_id, "$or": [{"mutation_lease_until": {"$exists": False}},
                                          {"mutation_lease_until": {"$lte": now_iso()}}]},
        {"$set": {"mutation_lease": token, "mutation_lease_until": until}},
    )
    if not claimed.modified_count:
        raise HTTPException(409, "Another change is being saved. Please try again.")
    try:
        yield
    finally:
        await db.v2_journeys.update_one({"journey_id": journey_id, "mutation_lease": token},
                                      {"$unset": {"mutation_lease": "", "mutation_lease_until": ""}})


async def touch_decisions(db, journey_id):
    await db.v2_journeys.update_one({"journey_id": journey_id},
                                  {"$inc": {"decision_version": 1}, "$set": {"updated_at": now_iso()}})
    await db.v2_resources.update_many({"journey_id": journey_id, "key": {"$in": ["final_strategy", "final_plan"]}},
                                     {"$set": {"status": "ready", "approved_revision": None, "decisions_changed": True,
                                               "updated_at": now_iso()}})


async def issue_owner_link(db, journey_id, path):
    path = internal_path(path)
    journey = await find_journey(db, journey_id)
    ensure_paid(journey)
    token = secrets.token_urlsafe(32)
    await db.v2_access_links.insert_one({"link_id": new_id(), "token_digest": digest(token),
                                        "journey_id": journey_id, "action_path": path,
                                        "expires_at": (datetime.now(timezone.utc) + timedelta(days=LINK_DAYS)).isoformat(),
                                        "created_at": now_iso()})
    separator = "&" if "?" in path else "?"
    return origin() + path + separator + "access=" + token


async def create_indexes(db):
    definitions = {
        "v2_journeys": [("journey_id", True), ("form_token", True)],
        "v2_resources": [("resource_id", True), ([("journey_id", 1), ("key", 1), ("submission_id", 1)], True)],
        "v2_purchases": [("session_id", True)],
        "v2_access_links": [("token_digest", True)],
        "v2_submissions": [("submission_id", True), ([("journey_id", 1), ("participant_id", 1)], True)],
        "v2_invitations": [("invitation_id", True), ("form_token", True), ([("journey_id", 1), ("email", 1)], True)],
        "v2_email_outbox": [("event_key", True), ("event_id", True)],
        "v2_public_drafts": [("draft_token", True)],
        "v2_decisions": [("decision_id", True)],
    }
    for name, entries in definitions.items():
        for keys, unique in entries:
            await getattr(db, name).create_index(keys, unique=unique)
    await db.v2_access_links.create_index("expires_at")
    await db.v2_public_drafts.create_index([("journey_id", 1), ("submit_digest", 1)], unique=True,
                                         partialFilterExpression={"submit_digest": {"$type": "string"}})
    await db.v2_email_outbox.create_index([("status", 1), ("next_attempt_at", 1)])
    await db.v2_rate_limits.create_index("key", unique=True)
