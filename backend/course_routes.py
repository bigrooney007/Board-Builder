import html
import os
from datetime import datetime, timezone
from typing import Optional

import resend
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from auth_service import authenticate_admin
from course_content import BASIC_MODULES, PRODUCT_KEYS, SELF_GUIDED_MODULES, SUPPORT_TYPES
from member_auth import authenticate_member, new_uuid, require_entitlement


class ProgressRequest(BaseModel):
    product: str
    module_number: int = Field(ge=1, le=6)
    action: str

    @field_validator("product")
    @classmethod
    def valid_product(cls, value: str) -> str:
        if value not in PRODUCT_KEYS:
            raise ValueError("Unknown product")
        return value

    @field_validator("action")
    @classmethod
    def valid_action(cls, value: str) -> str:
        if value not in {"viewed", "completed", "uncompleted"}:
            raise ValueError("Unknown action")
        return value


class SupportRequestCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    product: str
    module_number: int = Field(ge=1, le=6)
    support_type: str
    message: str = Field(min_length=1)

    @field_validator("product")
    @classmethod
    def valid_product(cls, value: str) -> str:
        if value not in PRODUCT_KEYS:
            raise ValueError("Unknown product")
        return value

    @field_validator("support_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        if value not in SUPPORT_TYPES:
            raise ValueError("Unknown support type")
        return value


class VideoConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    product: str
    module_number: int = Field(ge=1, le=6)
    youtube_url: Optional[str] = ""

    @field_validator("product")
    @classmethod
    def valid_product(cls, value: str) -> str:
        if value not in PRODUCT_KEYS:
            raise ValueError("Unknown product")
        return value


async def merged_course(db, member, product: str, modules: list) -> dict:
    videos = {v["module_number"]: v.get("youtube_url", "") for v in await db.course_videos.find({"product": product}, {"_id": 0}).to_list(20)}
    progress = {p["module_number"]: p for p in await db.course_progress.find({"user_id": member["user_id"], "product": product}, {"_id": 0}).to_list(20)}
    output = []
    for module in modules:
        record = progress.get(module["number"], {})
        item = dict(module)
        item["youtube_url"] = videos.get(module["number"], "")
        item["viewed"] = bool(record.get("viewed"))
        item["completed"] = bool(record.get("completed"))
        item["completed_at"] = record.get("completed_at", "")
        output.append(item)
    completed = sum(1 for item in output if item["completed"])
    return {
        "product": product, "modules": output,
        "modules_completed": completed,
        "percent_complete": round(completed / len(modules) * 100),
        "support_types": SUPPORT_TYPES,
    }


def create_course_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/courses/recruitment/basic")
    async def basic_course(request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {"recruitment_basic", "recruitment_self_guided"})
        return await merged_course(db, member, "recruitment_basic", BASIC_MODULES)

    @router.get("/courses/recruitment/self-guided")
    async def self_guided_course(request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {"recruitment_self_guided"})
        return await merged_course(db, member, "recruitment_self_guided", SELF_GUIDED_MODULES)

    @router.post("/courses/progress")
    async def track_progress(payload: ProgressRequest, request: Request):
        member = await authenticate_member(request, db)
        allowed = {"recruitment_basic", "recruitment_self_guided"} if payload.product == "recruitment_basic" else {"recruitment_self_guided"}
        require_entitlement(member, allowed)
        now = datetime.now(timezone.utc).isoformat()
        update = {"$set": {"last_visited_at": now, "updated_at": now},
                  "$setOnInsert": {"created_at": now}}
        if payload.action == "viewed":
            update["$set"]["viewed"] = True
        elif payload.action == "completed":
            update["$set"].update({"viewed": True, "completed": True, "completed_at": now})
        elif payload.action == "uncompleted":
            update["$set"].update({"completed": False, "completed_at": ""})
        await db.course_progress.update_one(
            {"user_id": member["user_id"], "product": payload.product, "module_number": payload.module_number},
            update, upsert=True,
        )
        records = await db.course_progress.find({"user_id": member["user_id"], "product": payload.product}, {"_id": 0}).to_list(20)
        completed = sum(1 for record in records if record.get("completed"))
        return {"status": "ok", "modules_completed": completed, "percent_complete": round(completed / 6 * 100)}

    @router.post("/support-requests", status_code=201)
    async def create_support_request(payload: SupportRequestCreate, request: Request):
        member = await authenticate_member(request, db)
        allowed = {"recruitment_basic", "recruitment_self_guided"} if payload.product == "recruitment_basic" else {"recruitment_self_guided"}
        require_entitlement(member, allowed)
        organization = ""
        lead_ids = member.get("lead_ids", [])
        if lead_ids:
            lead = await db.funnel_leads.find_one({"lead_id": {"$in": lead_ids}}, {"_id": 0, "organization": 1})
            organization = (lead or {}).get("organization", "")
        tier = "$497" if payload.product == "recruitment_self_guided" else "$97"
        product_name = "Recruitment Self-Guided" if payload.product == "recruitment_self_guided" else "Recruitment Basic"
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "support_request_id": new_uuid(),
            "user_id": member["user_id"],
            "name": f"{member['first_name']} {member['last_name']}",
            "organization": organization,
            "email": member["email"],
            "tier": tier,
            "product": product_name,
            "module": payload.module_number,
            "support_type": payload.support_type,
            "message": payload.message,
            "created_at": now,
            "status": "New",
            "owner_email_status": "Pending",
        }
        await db.support_requests.insert_one(record.copy())
        try:
            resend.api_key = os.environ["RESEND_API_KEY"]
            rows = "".join(
                f"<tr><td style='padding:8px;border-bottom:1px solid #ddd;font-weight:bold;'>{html.escape(label)}</td><td style='padding:8px;border-bottom:1px solid #ddd;'>{html.escape(str(value))}</td></tr>"
                for label, value in [
                    ("Support Request ID", record["support_request_id"]), ("Name", record["name"]),
                    ("Organization", organization or "Not provided"), ("Email", record["email"]),
                    ("Tier", tier), ("Product", product_name), ("Module", payload.module_number),
                    ("Support type", payload.support_type), ("Message", payload.message),
                    ("Date and time", now), ("Status", "New"),
                ]
            )
            await resend.Emails.send_async({
                "from": os.environ["NONPROFIT_SENDER"], "to": [os.environ["OWNER_NOTIFICATION_EMAIL"]],
                "subject": f"New Board Builder Support Request — {organization or record['name']} — Module {payload.module_number}",
                "html": f"<div style='max-width:680px;margin:auto;font-family:Arial,sans-serif;color:#000;'><h2>New Board Builder Support Request</h2><table style='width:100%;border-collapse:collapse;'>{rows}</table></div>",
            })
            await db.support_requests.update_one({"support_request_id": record["support_request_id"]}, {"$set": {"owner_email_status": "Sent"}})
        except Exception as exc:
            await db.support_requests.update_one({"support_request_id": record["support_request_id"]}, {"$set": {"owner_email_status": "Failed", "owner_email_error": str(exc)[:400]}})
        return {"status": "received", "support_request_id": record["support_request_id"],
                "message": "Your request has been received. We will follow up with you by email."}

    @router.patch("/admin/course-videos")
    async def set_course_video(payload: VideoConfig, request: Request):
        await authenticate_admin(request, db)
        now = datetime.now(timezone.utc).isoformat()
        await db.course_videos.update_one(
            {"product": payload.product, "module_number": payload.module_number},
            {"$set": {"youtube_url": payload.youtube_url or "", "updated_at": now}}, upsert=True,
        )
        return {"status": "ok"}

    return router
