import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from member_auth import authenticate_member

class GuidedLead(BaseModel):
    product: str
    name: str = Field(min_length=1)
    email: EmailStr
    organization: str = ""
    board_count: int = Field(ge=1, le=200)
    origin_url: Optional[str] = ""

class GuidedIntake(BaseModel):
    session_id: str = Field(min_length=1)
    product: str
    answers: dict

def create_guided_product_router(db):
    router = APIRouter(prefix="/api/guided")
    @router.post("/lead")
    async def create_lead(payload: GuidedLead):
        if payload.product not in {"strategic-planning","board-recommitment"}:
            raise HTTPException(400,"Unknown guided product")
        token=secrets.token_urlsafe(24); now=datetime.now(timezone.utc).isoformat()
        doc={"token":token,**payload.model_dump(mode="json"),"email":str(payload.email).lower(),"created_at":now,"updated_at":now,
             "followup_status":"active","followup_step":0,"next_followup_at":now,"converted_at":""}
        await db.guided_product_leads.insert_one(doc.copy())
        return {"token":token}

    @router.get("/context/{token}")
    async def context(token: str):
        doc=await db.guided_product_leads.find_one({"token":token},{"_id":0})
        if not doc: raise HTTPException(404,"Journey not found")
        return doc

    @router.post("/intake")
    async def save_intake(payload: GuidedIntake, request: Request):
        tx=await db.payment_transactions.find_one({"session_id":payload.session_id},{"_id":0})
        expected={"strategic-planning":"strategic_planning_497","board-recommitment":"board_recommitment_497"}.get(payload.product)
        if not tx or tx.get("payment_status")!="paid" or tx.get("purchase_source")!=expected:
            raise HTTPException(402,"Paid access could not be confirmed")
        now=datetime.now(timezone.utc).isoformat()
        await db.guided_product_intakes.update_one({"session_id":payload.session_id},{"$set":{"session_id":payload.session_id,"product":payload.product,"answers":payload.answers,"updated_at":now},"$setOnInsert":{"created_at":now}},upsert=True)
        if payload.product=="board-recommitment":
            lead=await db.guided_product_leads.find_one({"token":tx.get("guided_lead_token","")},{"_id":0})
            member=await db.members.find_one({"email":(lead or {}).get("email","")},{"_id":0})
            if not member:
                raise HTTPException(409,"Your Board Recommitment workspace session could not be linked")
            authenticated = await authenticate_member(request, db)
            if authenticated.get("user_id") != member.get("user_id"):
                raise HTTPException(401,"Log in with the email used for this Board Recommitment purchase before continuing")
            await db.members.update_one({"user_id":member["user_id"]},{"$addToSet":{"entitlements":"reactivation_self_guided"},"$set":{"updated_at":now}})
            await db.board_reactivation_intakes.update_one({"guided_session_id":payload.session_id},{"$set":{"user_id":member["user_id"],"organization_name":(lead or {}).get("organization",""),"founder_title":"","mission":payload.answers.get("mission",""),"organization_goals":payload.answers.get("goals",""),"guided_session_id":payload.session_id,"guided_answers":payload.answers,"submitted_at":now}},upsert=True)
        elif payload.product=="strategic-planning":
            lead=await db.guided_product_leads.find_one({"token":tx.get("guided_lead_token","")},{"_id":0}) or {}
            existing=await db.sp_projects.find_one({"guided_session_id":payload.session_id},{"_id":0})
            if not existing:
                project_id=secrets.token_hex(16)
                await db.sp_projects.insert_one({"project_id":project_id,"guided_session_id":payload.session_id,"organization_name":lead.get("organization") or "Organization","founder_name":lead.get("name") or "Organization Leader","founder_email":lead.get("email") or "","founder_title":"","mission":payload.answers.get("mission",""),"status":"Active","generic_form_token":secrets.token_urlsafe(32),"created_at":now})
            project=existing or await db.sp_projects.find_one({"guided_session_id":payload.session_id},{"_id":0})
            participant_id=secrets.token_hex(16)
            await db.sp_participants.update_one({"project_id":project["project_id"],"email":str(lead.get("email") or "").lower()},{"$setOnInsert":{"participant_id":participant_id,"project_id":project["project_id"],"name":lead.get("name") or "Organization Leader","email":str(lead.get("email") or "").lower(),"role":"Lead User","status":"INVITED","created_at":now}},upsert=True)
        return {"saved":True,"dashboard_url":f"/{payload.product}/dashboard?session_id={payload.session_id}"}

    @router.get("/dashboard")
    async def dashboard(session_id: str, product: str):
        tx=await db.payment_transactions.find_one({"session_id":session_id},{"_id":0})
        expected={"strategic-planning":"strategic_planning_497","board-recommitment":"board_recommitment_497"}.get(product)
        if not tx or tx.get("payment_status")!="paid" or tx.get("purchase_source")!=expected:
            raise HTTPException(402,"Paid access could not be confirmed")
        intake=await db.guided_product_intakes.find_one({"session_id":session_id},{"_id":0})
        return {"product":product,"intake":intake or {}}
    return router
