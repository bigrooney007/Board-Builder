import asyncio
import html
import os
from datetime import datetime, timezone

import resend
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

CALENDLY_URL = "https://calendly.com/boardbuilder/recruitboard"
READY_OPTIONS = {
    "Yes, we are ready to organize the Board Fundraising Game.",
    "I am ready, but I need to confirm with my board.",
    "We are interested, but we need to discuss it as a board first.",
}

class FacilitatedGameApplication(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    organization_name: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=150)
    position: str = Field(min_length=1, max_length=150)
    email: EmailStr
    board_members: int = Field(ge=1, le=500)
    mission: str = Field(min_length=1, max_length=3000)
    website: str = Field(min_length=1, max_length=500)
    readiness: str

    @field_validator("readiness")
    @classmethod
    def valid_readiness(cls, value: str) -> str:
        if value not in READY_OPTIONS:
            raise ValueError("Please select one of the readiness options")
        return value

def create_facilitated_game_application_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/facilitated-game-application")

    @router.post("")
    async def submit_application(payload: FacilitatedGameApplication):
        now = datetime.now(timezone.utc).isoformat()
        doc = payload.model_dump(mode="json")
        doc["email"] = str(payload.email).lower()
        doc.update({"submitted_at": now, "status": "New Application", "service": "Facilitated Board Fundraising Game", "price": "$3,497"})
        result = await db.facilitated_game_applications.insert_one(doc.copy())
        doc["application_id"] = str(result.inserted_id)

        api_key = os.environ.get("RESEND_API_KEY")
        sender = os.environ.get("SENDER_EMAIL") or os.environ.get("NONPROFIT_SENDER")
        owner = os.environ.get("OWNER_NOTIFICATION_EMAIL") or os.environ.get("OWNER_EMAIL")
        if api_key and sender and owner:
            resend.api_key = api_key
            safe = lambda value: html.escape(str(value or "Not provided"))
            body = f"""<div style="font-family:Arial,sans-serif;max-width:700px;margin:auto;line-height:1.55">
            <h1>New Board Fundraising Game Application</h1>
            <p><strong>Organization:</strong> {safe(doc["organization_name"])}<br>
            <strong>Name:</strong> {safe(doc["name"])}<br><strong>Position:</strong> {safe(doc["position"])}<br>
            <strong>Email:</strong> {safe(doc["email"])}<br><strong>Board members:</strong> {safe(doc["board_members"])}<br>
            <strong>Website:</strong> {safe(doc["website"])}</p>
            <p><strong>Mission</strong><br>{safe(doc["mission"])}</p>
            <p><strong>Readiness</strong><br>{safe(doc["readiness"])}</p></div>"""
            try:
                await asyncio.to_thread(resend.Emails.send, {
                    "from": sender, "to": [owner],
                    "subject": f'Board Fundraising Game Application — {doc["organization_name"]}',
                    "html": body,
                })
                await db.facilitated_game_applications.update_one({"_id": result.inserted_id}, {"$set": {"owner_notification": "Sent"}})
            except Exception as exc:
                await db.facilitated_game_applications.update_one({"_id": result.inserted_id}, {"$set": {"owner_notification": "Failed", "owner_notification_error": str(exc)[:500]}})

        return {"status": "submitted", "booking_url": CALENDLY_URL}

    return router
