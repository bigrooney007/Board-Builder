import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from funnel_models import FunnelLeadCreate, FunnelLeadResponse, LeadResultResponse, OFFER_SOURCES
from funnel_service import build_result, create_lead_id, send_owner_lead_email, validate_answers


def create_funnel_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/funnel-leads")

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
        return FunnelLeadResponse(**lead)

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