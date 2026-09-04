import os
import secrets
import asyncio

import resend

from recommendation_email_service import linkify, send_recommendation_email
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from funnel_models import FunnelLeadCreate, FunnelLeadResponse, LeadResultResponse, OFFER_SOURCES
from funnel_service import build_result, create_lead_id, send_owner_lead_email, validate_answers


def create_funnel_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/funnel-leads")

    class LeadMagnetPayload(BaseModel):
        name: str = Field(min_length=1, max_length=120)
        email: str = Field(min_length=3, max_length=200)
        origin_url: str = ""

    @router.post("/lead-magnet", status_code=201)
    async def lead_magnet(payload: LeadMagnetPayload):
        """Homepage lead magnet: save Name + Email, email the Three Mistakes video link. ZERO AI."""
        email = payload.email.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise HTTPException(status_code=422, detail="Enter a valid email address")
        name = payload.name.strip()
        now = datetime.now(timezone.utc)
        existing = await db.funnel_leads.find_one({"email": email, "offer_source": "board_fix"}, {"_id": 0, "lead_id": 1, "result_token": 1})
        if existing:
            token = existing["result_token"]
            await db.funnel_leads.update_one({"lead_id": existing["lead_id"]}, {"$set": {"name": name, "updated_at": now.isoformat()}})
        else:
            token = secrets.token_urlsafe(32)
            await db.funnel_leads.insert_one({
                "lead_id": create_lead_id(now), "result_token": token, "offer_source": "board_fix",
                "name": name, "email": email, "organization": "", "answers": {},
                "lead_source": "homepage_lead_magnet",
                "created_at": now.isoformat(), "updated_at": now.isoformat(),
                "owner_email_status": "Pending", "selected_tier": "",
            })
        origin = payload.origin_url.rstrip("/") if payload.origin_url.startswith("http") else "https://nonprofitboardbuilder.com"
        link = f"{origin}/offer/board-fix?t={token}"
        first = name.split(" ")[0] if name else "there"
        body = (
            f"Hi {first},\n\n"
            "Here is the Board training I promised you.\n\n"
            "In this video, I will show you the three mistakes nonprofit founders and executive directors make with their Board "
            "that can limit their organization's ability to raise money and grow, and what to do differently.\n\n"
            f"{link}\n\n"
            "Rooney Akpesiri\nNonprofit Board Builder")
        status = "Sent"
        try:
            resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
            paragraphs = "".join(
                f"<p style='margin:0 0 14px 0;'>{'<br/>'.join(linkify(line) for line in block.split(chr(10)))}</p>"
                for block in body.split("\n\n"))
            resend.Emails.send({
                "from": os.environ["NONPROFIT_SENDER"].strip('"'), "to": [email],
                "reply_to": [os.environ["ADMIN_EMAIL"].strip('"')],
                "subject": "Your Board Training: The 3 Mistakes",
                "html": f"<div style='font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;color:#1a1a1a;'>{paragraphs}</div>",
                "text": body,
            })
        except Exception:
            status = "Failed"
        await db.funnel_leads.update_one({"result_token": token}, {"$set": {"lead_magnet_email_status": status}})
        return {"token": token, "redirect_url": f"/offer/board-fix?t={token}"}

    QUALIFY_TIMELINES = {"As soon as possible", "Within 30 days", "Within 60 days", "Within 90 days", "I am not sure yet"}

    class QualifyPayload(BaseModel):
        token: str = ""
        priority: str
        board_count: str = ""
        timeline: str = ""

    @router.post("/qualify")
    async def qualify(payload: QualifyPayload):
        """Deterministic two-way routing: recruitment or fundraising_activation. ZERO AI."""
        if payload.priority not in {"recruitment", "fundraising_activation"}:
            raise HTTPException(status_code=422, detail="Choose what your Board needs most right now")
        if payload.timeline and payload.timeline not in QUALIFY_TIMELINES:
            raise HTTPException(status_code=422, detail="Choose one of the timeline options")
        route = "/board-recruitment" if payload.priority == "recruitment" else "/board-fundraising-activation"
        if payload.token:
            now = datetime.now(timezone.utc)
            await db.funnel_leads.update_one({"result_token": payload.token}, {"$set": {
                "qualifier_priority": payload.priority,
                "qualifier_board_count": str(payload.board_count)[:20],
                "qualifier_timeline": payload.timeline,
                "recommendation": payload.priority,
                "recommended_pathway": payload.priority,
                "updated_at": now.isoformat(),
            }})
            lead = await db.funnel_leads.find_one({"result_token": payload.token}, {"_id": 0, "email": 1, "reco_nurture": 1})
            if lead and lead.get("email"):
                state = lead.get("reco_nurture") or {}
                if state.get("sequence") != payload.priority or state.get("status") not in {"active", "completed"}:
                    await db.funnel_leads.update_one({"result_token": payload.token}, {"$set": {"reco_nurture": {
                        "sequence": payload.priority, "next_email": 1, "status": "active",
                        "first_scheduled_at": (now + timedelta(hours=24)).isoformat(),
                        "next_send_at": (now + timedelta(hours=24)).isoformat(),
                        "last_sent_at": "",
                    }}})
        return {"recommendation": payload.priority, "route": route}

    @router.get("/unsubscribe/{token}")
    async def reco_unsubscribe(token: str):
        lead = await db.funnel_leads.find_one({"result_token": token}, {"_id": 0, "email": 1})
        if not lead:
            raise HTTPException(status_code=404, detail="Unknown link")
        now = datetime.now(timezone.utc).isoformat()
        await db.funnel_leads.update_one({"result_token": token}, {"$set": {
            "reco_nurture.status": "stopped", "reco_nurture.stopped_reason": "unsubscribed", "reco_nurture.updated_at": now}})
        await db.nurture_contacts.update_one(
            {"email": (lead.get("email") or "").lower()},
            {"$set": {"nurture_status": "unsubscribed", "updated_at": now}}, upsert=True)
        return HTMLResponse("<div style='font-family:Arial,Helvetica,sans-serif;padding:48px;text-align:center;'><h2>You have been unsubscribed.</h2><p>You will not receive further emails from this sequence.</p></div>")

    @router.post("/{offer_source}", response_model=FunnelLeadResponse, status_code=201)
    async def create_lead(offer_source: str, payload: FunnelLeadCreate):
        if offer_source not in OFFER_SOURCES:
            raise HTTPException(status_code=404, detail="Offer not found")
        try:
            validate_answers(offer_source, payload.answers)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        now = datetime.now(timezone.utc)
        lead = payload.model_dump(mode="json")
        lead.update({
            "lead_id": create_lead_id(now), "result_token": secrets.token_urlsafe(32),
            "offer_source": offer_source, "created_at": now.isoformat(), "updated_at": now.isoformat(),
            "owner_email_status": "Pending", "selected_tier": "",
        })
        if offer_source == "recruitment":
            lead["support_preference"] = str(payload.answers.get("support_preference", ""))
        await db.funnel_leads.insert_one(lead.copy())
        try:
            email_id = await send_owner_lead_email(lead)
            lead.update({"owner_email_status": "Sent", "owner_email_id": email_id, "owner_email_error": ""})
        except Exception as exc:
            lead.update({"owner_email_status": "Failed", "owner_email_error": str(exc)[:500]})
        await db.funnel_leads.update_one({"lead_id": lead["lead_id"]}, {"$set": {
            "owner_email_status": lead["owner_email_status"],
            "owner_email_id": lead.get("owner_email_id", ""),
            "owner_email_error": lead.get("owner_email_error", ""),
        }})
        try:
            from marketing_service import sync_lead_nurture
            await sync_lead_nurture(db, lead)
        except Exception:
            pass
        return FunnelLeadResponse(**lead)

    class ProductSelection(BaseModel):
        result_token: str = Field(min_length=1)
        product: str

        @field_validator("product")
        @classmethod
        def valid_product(cls, value: str) -> str:
            if value not in {"recruit", "reactivate", "activate"}:
                raise ValueError("Unknown product")
            return value

    DIAGNOSTIC_OPTIONS = {
        "has_board": {"Yes", "No"},
        "active_participation": {"Yes", "No", "Some are, some are not", ""},
        "right_people": {"Yes", "No", "Not sure", ""},
        "fundraising_working": {"Yes", "No", "Only a little", ""},
    }

    class DiagnosticPayload(BaseModel):
        result_token: str = ""
        has_board: str
        active_participation: str = ""
        right_people: str = ""
        fundraising_working: str = ""
        name: str = ""
        email: str = ""
        organization: str = ""
        board_count: str = ""
        board_situation: str = ""

    def diagnose(payload: "DiagnosticPayload") -> str:
        if payload.has_board == "No":
            return "recruitment"
        flags = []
        if payload.active_participation in {"No", "Some are, some are not"}:
            flags.append("reactivation")
        if payload.right_people == "No":
            flags.append("recruitment")
        if payload.fundraising_working in {"No", "Only a little"}:
            flags.append("activation")
        if len(flags) >= 2:
            return "complete_transformation"
        return flags[0] if flags else "activation"

    @router.post("/board-fix/diagnostic")
    async def board_fix_diagnostic(payload: DiagnosticPayload):
        for key, allowed in DIAGNOSTIC_OPTIONS.items():
            if getattr(payload, key) not in allowed:
                raise HTTPException(status_code=422, detail="Please answer using the options provided")
        if payload.has_board == "Yes" and not (payload.active_participation and payload.right_people and payload.fundraising_working):
            raise HTTPException(status_code=422, detail="Please answer all four questions")
        recommended = diagnose(payload)
        now = datetime.now(timezone.utc).isoformat()
        answers = {key: getattr(payload, key) for key in DIAGNOSTIC_OPTIONS}
        token = payload.result_token
        contact = {}
        if payload.name.strip():
            contact["name"] = payload.name.strip()
        if payload.email.strip():
            contact["email"] = payload.email.strip().lower()
        if payload.organization.strip():
            contact["organization"] = payload.organization.strip()
        if payload.board_count.strip():
            contact["board_count"] = payload.board_count.strip()
        if payload.board_situation.strip():
            contact["board_situation"] = payload.board_situation.strip()[:5000]
        if token:
            await db.funnel_leads.update_one(
                {"result_token": token, "offer_source": "board_fix"},
                {"$set": {"diagnostic_answers": answers, "recommended_pathway": recommended,
                          "diagnosed_at": now, **contact}})
        elif contact.get("email"):
            token = secrets.token_urlsafe(32)
            await db.funnel_leads.insert_one({
                "lead_id": create_lead_id(now), "result_token": token, "offer_source": "board_fix",
                **contact, "diagnostic_answers": answers, "recommended_pathway": recommended,
                "diagnosed_at": now, "created_at": now, "updated_at": now})
        if token and contact.get("email"):
            claimed = await db.funnel_leads.update_one(
                {"result_token": token, "recommendation_email_status": {"$exists": False}},
                {"$set": {"recommendation_email_status": "queued", "recommendation_email_queued_at": now}})
            if claimed.modified_count == 1:
                asyncio.create_task(send_recommendation_email(db, token))
        return {"recommended_pathway": recommended, "result_token": token}

    @router.post("/board-transformation/select")
    async def select_transformation_product(payload: ProductSelection):
        result = await db.funnel_leads.update_one(
            {"result_token": payload.result_token, "offer_source": "board_transformation"},
            {"$set": {"selected_product": payload.product, "updated_at": datetime.now(timezone.utc).isoformat()}})
        if not result.matched_count:
            raise HTTPException(status_code=404, detail="Result not found")
        return {"status": "ok"}

    @router.get("/result/{result_token}", response_model=LeadResultResponse)
    async def get_result(result_token: str):
        lead = await db.funnel_leads.find_one({"result_token": result_token}, {"_id": 0})
        if not lead:
            raise HTTPException(status_code=404, detail="Result not found")
        return LeadResultResponse(
            lead_id=lead["lead_id"], offer_source=lead["offer_source"], name=lead["name"],
            organization=lead["organization"], answers=lead["answers"],
            result=build_result(lead["offer_source"], lead["answers"]),
        )

    return router