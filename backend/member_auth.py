import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, Request

JWT_ALGORITHM = "HS256"
MEMBER_SESSION_HOURS = 24 * 7
MEMBER_COOKIE = "member_access_token"


def hash_member_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_member_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_member_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "member",
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(hours=MEMBER_SESSION_HOURS),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def set_member_cookie(response, token: str) -> None:
    response.set_cookie(
        MEMBER_COOKIE, token, httponly=True, secure=True, samesite="none",
        path="/", max_age=MEMBER_SESSION_HOURS * 3600,
    )


def clear_member_cookie(response) -> None:
    response.delete_cookie(MEMBER_COOKIE, path="/", secure=True, samesite="none")


async def review_mode_member(request: Request, db):
    """Owner Review Mode: synthetic member view for the authenticated admin only."""
    if os.environ.get("OWNER_RECRUITMENT_REVIEW_MODE", "false").lower() != "true":
        return None
    from auth_service import authenticate_admin
    try:
        admin = await authenticate_admin(request, db)
    except HTTPException:
        return None
    return {
        "user_id": "owner-review-admin", "email": admin["email"],
        "first_name": "Owner", "last_name": "Review",
        "entitlements": ["recruitment_basic", "recruitment_self_guided", "recruitment_selection_onboarding", "reactivation_self_guided", "activation_self_guided"],
        "lead_ids": [], "review_mode": True,
    }


async def operator_member(request: Request, db):
    """Admin operating a DWM client workspace: admin auth + X-Operate-As header targeting an operator workspace tenant only."""
    target = request.headers.get("X-Operate-As", "").strip()
    if not target:
        return None
    from auth_service import authenticate_admin
    try:
        await authenticate_admin(request, db)
    except HTTPException:
        return None
    member = await db.members.find_one(
        {"user_id": target, "operator_workspace": True}, {"_id": 0, "password_hash": 0})
    if not member:
        return None
    return {**member, "operator_mode": True}


async def authenticate_member(request: Request, db) -> dict:
    try:
        token = request.cookies.get(MEMBER_COOKIE)
        if not token:
            header = request.headers.get("Authorization", "")
            if header.startswith("Bearer "):
                token = header[7:]
        if not token:
            raise HTTPException(status_code=401, detail="Please log in to access your Board Builder account")
        try:
            payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(status_code=401, detail="Your session has expired. Please log in again.") from exc
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail="Invalid session. Please log in again.") from exc
        if payload.get("type") != "access" or payload.get("role") != "member":
            raise HTTPException(status_code=403, detail="Member access required")
        member = await db.members.find_one(
            {"user_id": payload.get("sub"), "email": payload.get("email")},
            {"_id": 0, "password_hash": 0},
        )
        if not member:
            raise HTTPException(status_code=401, detail="Account not found. Please log in again.")
        return member
    except HTTPException:
        reviewer = await review_mode_member(request, db)
        if reviewer:
            return reviewer
        raise


def require_entitlement(member: dict, allowed: set) -> None:
    entitlements = set(member.get("entitlements", []))
    if not entitlements.intersection(allowed):
        raise HTTPException(status_code=403, detail="Your account does not include access to this program")


def new_uuid() -> str:
    return str(uuid.uuid4())
