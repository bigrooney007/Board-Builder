import os
import secrets
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

    @router.get("/direct-recruitment/config")
    async def direct_recruitment_config():
        url = os.environ.get("DIRECT_RECRUITMENT_VIDEO_URL", "").strip().strip('"')
        return {"video_url": url}

    @router.get("/direct-reactivation/config")
    async def direct_reactivation_config():
        url = os.environ.get("DIRECT_REACTIVATION_VIDEO_URL", "").strip().strip('"')
        return {"video_url": url}

    @router.get("/direct-activation/config")
    async def direct_activation_config():
        url = os.environ.get("DIRECT_ACTIVATION_VIDEO_URL", "").strip().strip('"')
        return {"video_url": url}

    @router.get("/shared/{token}")
    async def shared_resource(token: str):
        link = await db.share_links.find_one({"share_token": token}, {"_id": 0})
        if not link:
            raise HTTPException(status_code=404, detail="This shared resource is not available")
        material = await db.generated_materials.find_one({"material_id": link["material_id"]}, {"_id": 0})
        if not material:
            raise HTTPException(status_code=404, detail="This shared resource is not available")
        current = next((v for v in material["versions"] if v["version"] == material["current_version"]), None)
        profile = await db.recruitment_profiles.find_one({"user_id": material["user_id"]}, {"_id": 0, "branding": 1})
        branding = (profile or {}).get("branding", {})
        org = (await db.opportunities.find_one({"user_id": material["user_id"]}, {"_id": 0, "organization_name": 1}) or {}).get("organization_name", "")
        return {"title": material["title"], "display_text": current["display_text"] if current else "",
                "organization_name": org, "logo_data": branding.get("logo_data", ""),
                "primary_color": branding.get("primary_color", ""), "secondary_color": branding.get("secondary_color", ""),
                "design_spec": material.get("design_spec", {})}

    @router.get("/board-profile/{token}")
    async def board_profile_meta(token: str):
        record = await db.board_profile_forms.find_one({"share_token": token}, {"_id": 0})
        if record:
            return {"organization_name": record["organization_name"], "prefill": {}}
        link = await db.board_profile_links.find_one({"token": token}, {"_id": 0})
        if not link:
            raise HTTPException(status_code=404, detail="This form is not available")
        org = await db.opportunities.find_one({"user_id": link["user_id"]}, {"_id": 0, "organization_name": 1})
        prefill = link.get("prefill", {})
        return {"organization_name": (org or {}).get("organization_name", ""),
                "prefill": {"full_name": prefill.get("full_name", ""), "email": prefill.get("email", ""),
                            "professional_title": prefill.get("professional_title", ""), "employer": prefill.get("employer", ""),
                            "linkedin": prefill.get("linkedin", ""), "location": prefill.get("location", "")}}

    @router.post("/board-profile/{token}", status_code=201)
    async def board_profile_submit(token: str, payload: dict):
        record = await db.board_profile_forms.find_one({"share_token": token}, {"_id": 0})
        link = None
        if not record:
            link = await db.board_profile_links.find_one({"token": token}, {"_id": 0})
            if not link:
                raise HTTPException(status_code=404, detail="This form is not available")
        user_id = record["user_id"] if record else link["user_id"]
        allowed = ["full_name", "preferred_name", "email", "phone", "location", "professional_title", "employer", "bio", "linkedin", "skills", "professional_experience", "board_experience", "fundraising_strengths", "relationships", "committees_of_interest", "availability", "areas_to_support", "time_commitment", "why_joined"]
        data = {key: str(payload.get(key, ""))[:4000] for key in allowed}
        if not data["full_name"].strip() or not data["email"].strip():
            raise HTTPException(status_code=422, detail="Full name and email are required")
        await db.board_profile_responses.insert_one({
            "response_id": secrets.token_hex(8), "user_id": user_id, "share_token": token,
            "application_id": (link or {}).get("application_id", ""),
            "data": data, "submitted_at": datetime.now(timezone.utc).isoformat(),
        })
        if link:
            await db.board_profile_links.update_one({"token": token}, {"$set": {"status": "Completed", "completed_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "submitted"}

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
