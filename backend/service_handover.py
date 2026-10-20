"""Expiring, revocable dashboard handover for prepared paid service projects.

Uses the existing service customer and workspace, rather than copying project data.
The emailed capability is exchanged explicitly for an HttpOnly operator session.
"""
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from consultation_routes import no_cache, origin
from guided_service_defaults import PACKAGES

COOKIE = "guided_operator_session"
STATES = {"rooney_preparing", "ready_for_handover", "organization_operating", "rooney_facilitating", "completed"}


def stamp():
    return datetime.now(timezone.utc)


async def operator_record(db, request, service=None):
    token = request.cookies.get(COOKIE, "")
    try:
        claim = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"], audience="guided-service-operator")
    except (jwt.InvalidTokenError, KeyError) as exc:
        raise HTTPException(401, "Open your personal dashboard invitation to continue.") from exc
    if service and service != claim.get("service"):
        raise HTTPException(403, "This access belongs to another service.")
    row = await db.guided_service_customers.find_one({"customer_id": claim.get("sub"), "service": claim.get("service"), "payment_status": "paid", "purchased_package": "self-facilitated", "operator_status": {"$in": ["organization_operating", "completed"]}, "operator_session_version": claim.get("version")}, {"_id": 0})
    if not row or row["service"] not in PACKAGES:
        raise HTTPException(403, "Your dashboard access is unavailable. Request a new invitation from Rooney.")
    return row


async def operator_for_workspace(db, request, workspace_id, service):
    row = await operator_record(db, request, service)
    if row["workspace_user_id"] != workspace_id:
        raise HTTPException(403, "This project belongs to another organization.")
    return row


def create_handover_router(db):
    from guided_services import admin_record, digest, now, settings, render, context, send_message
    router = APIRouter(prefix="/api", dependencies=[Depends(no_cache)])

    @router.post("/admin/services/{service}/customers/{ident}/handover")
    async def prepare(service: str, ident: str, payload: dict, request: Request):
        row = await admin_record(db, service, ident, request, True)
        if service not in PACKAGES or row.get("purchased_package") != "self-facilitated":
            raise HTTPException(403, "Dashboard handover is included with the self-facilitation package.")
        if not row.get("branding_saved_at") or payload.get("prepared_confirmed") is not True:
            raise HTTPException(409, "Save branding and confirm the project and invitations are prepared before handover.")
        # Reusing an unexpired invitation makes double-clicks and email retries safe.
        existing = row.get("handover") or {}
        if existing.get("expires_at", "") > now() and not existing.get("accepted_at"):
            token = existing["token"]
        else:
            token = secrets.token_urlsafe(32)
            existing = {"token": token, "token_hash": digest(token), "expires_at": (stamp()+timedelta(hours=48)).isoformat(), "created_at": now()}
            await db.guided_service_customers.update_one({"customer_id": ident}, {"$set": {"handover": existing, "operator_status": "ready_for_handover"}})
        config, _, _ = await settings(db, service)
        link = origin()+f"/services/{service}/handover/"+token
        delivery = await send_message(db, row, "guided-handover-"+digest(token)[:20], render(config["handover_email"], context(row)), link)
        return {"url": link, "expires_at": existing["expires_at"], "delivery": delivery, "operator_status": "ready_for_handover"}

    async def invitation(service, token):
        if service not in PACKAGES or not 40 <= len(token) <= 100:
            raise HTTPException(404, "This dashboard invitation was not found.")
        row = await db.guided_service_customers.find_one({"service": service, "handover.token_hash": digest(token), "payment_status": "paid", "purchased_package": "self-facilitated"}, {"_id": 0})
        if not row or (row.get("handover") or {}).get("expires_at", "") <= now():
            raise HTTPException(410, "This invitation has expired. Ask Rooney for a new dashboard invitation. Your paid project is still saved.")
        return row

    @router.get("/services/{service}/handover/{token}")
    async def inspect(service: str, token: str):
        row = await invitation(service, token)
        config, _, _ = await settings(db, service)
        return {"organization": row["organization"], "copy": config["customer_copy"], "accepted": bool(row["handover"].get("accepted_at"))}

    @router.post("/services/{service}/handover/{token}")
    async def accept(service: str, token: str, payload: dict):
        row = await invitation(service, token)
        if payload.get("confirmed") is not True:
            raise HTTPException(422, "Confirm that you are accepting control of your organization's prepared dashboard.")
        version = row.get("operator_session_version") or secrets.token_urlsafe(24)
        await db.guided_service_customers.update_one({"customer_id": row["customer_id"], "handover.token_hash": digest(token)}, {"$set": {"operator_status": "organization_operating", "handover.accepted_at": now(), "operator_session_version": version}})
        claim = {"sub": row["customer_id"], "service": service, "version": version, "aud": "guided-service-operator", "iat": stamp(), "exp": stamp()+timedelta(hours=8)}
        jwt_token = jwt.encode(claim, os.environ["JWT_SECRET"], algorithm="HS256")
        response = JSONResponse({"url": f"/services/{service}/dashboard/"+row["customer_id"]})
        response.set_cookie(COOKIE, jwt_token, httponly=True, secure=True, samesite="lax", path="/api", max_age=8*3600)
        return response

    @router.post("/admin/services/{service}/customers/{ident}/revoke-handover")
    async def revoke(service: str, ident: str, request: Request):
        await admin_record(db, service, ident, request, True)
        await db.guided_service_customers.update_one({"customer_id": ident}, {"$set": {"operator_status": "rooney_preparing", "operator_session_version": secrets.token_urlsafe(24)}, "$unset": {"handover": ""}})
        return {"status": "revoked"}

    @router.get("/services/{service}/operator/{ident}")
    async def dashboard(service: str, ident: str, request: Request):
        row = await operator_record(db, request, service)
        if row["customer_id"] != ident:
            raise HTTPException(403, "This dashboard belongs to another organization.")
        from guided_services import public_record
        config, _, _ = await settings(db, service)
        return {"customer": public_record(row), "copy": config["customer_copy"]}

    @router.post("/services/{service}/operator/{ident}/support", status_code=201)
    async def support(service: str, ident: str, payload: dict, request: Request):
        row = await operator_record(db, request, service)
        if row["customer_id"] != ident:raise HTTPException(403, "This dashboard belongs to another organization.")
        message = str(payload.get("message", "")).strip()
        if not 5 <= len(message) <= 10000:raise HTTPException(422, "Describe where you need help.")
        request_id=secrets.token_urlsafe(24)
        await db.help_requests.insert_one({"request_id": request_id, "user_id": row["workspace_user_id"], "guided_customer_id": ident, "service": service, "customer_email": row["email"], "message": message, "status": "open", "created_at": now()})
        from workflow_delivery import deliver_once
        result=await deliver_once(db,row["workspace_user_id"],"guided-help-"+request_id,os.environ.get("OWNER_NOTIFICATION_EMAIL","rooney@nonprofitboardbuilder.com"),"A Customer Has Requested Help",f"{row['organization']} needs help with {service}. Open the customer workspace to review the request.",origin()+"/admin/services/"+service)
        return {"status":"saved","notification_status":result["status"]}
    return router
