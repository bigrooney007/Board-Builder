import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth_service import authenticate_admin

GUARANTEE_FALLBACK = (
    "Complete the required Recruitment System and follow the published Recruitment Guarantee requirements. "
    "If you do not achieve the qualifying recruitment result, you may request a refund under the Recruitment Guarantee terms. "
    "The full Recruitment Guarantee terms will be published here."
)

TERMS_VERSION = "2026-06-recruitment-v1"


def review_mode_enabled() -> bool:
    return os.environ.get("OWNER_RECRUITMENT_REVIEW_MODE", "false").lower() == "true"


class TermsAgreement(BaseModel):
    lead_id: str = Field(min_length=1)
    terms_version: str = TERMS_VERSION


def create_review_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/review-mode/status")
    async def review_status(request: Request):
        if not review_mode_enabled():
            return {"active": False}
        try:
            await authenticate_admin(request, db)
            return {"active": True}
        except HTTPException:
            return {"active": False}

    @router.get("/recruitment-guarantee")
    async def recruitment_guarantee():
        terms = os.environ.get("RECRUITMENT_GUARANTEE_TERMS", "").strip()
        return {"terms": terms or GUARANTEE_FALLBACK, "configured": bool(terms)}

    @router.post("/terms-agreements", status_code=201)
    async def record_terms_agreement(payload: TermsAgreement):
        lead = await db.funnel_leads.find_one({"lead_id": payload.lead_id}, {"_id": 0, "email": 1})
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found. Please complete the recruitment form first.")
        await db.terms_agreements.insert_one({
            "lead_id": payload.lead_id,
            "email": lead["email"],
            "terms_version": payload.terms_version or TERMS_VERSION,
            "agreed_at": datetime.now(timezone.utc).isoformat(),
            "context": "recruitment_checkout",
        })
        return {"status": "recorded", "terms_version": payload.terms_version or TERMS_VERSION}

    return router
