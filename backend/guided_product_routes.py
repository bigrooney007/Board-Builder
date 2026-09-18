import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

class GuidedLead(BaseModel):
    product: str
    name: str = Field(min_length=1)
    email: EmailStr
    organization: str = ""
    board_count: int = Field(ge=1, le=200)

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
        doc={"token":token,**payload.model_dump(mode="json"),"email":str(payload.email).lower(),"created_at":now,"updated_at":now}
        await db.guided_product_leads.insert_one(doc.copy())
        return {"token":token}

    @router.get("/context/{token}")
    async def context(token: str):
        doc=await db.guided_product_leads.find_one({"token":token},{"_id":0})
        if not doc: raise HTTPException(404,"Journey not found")
        return doc

    @router.post("/intake")
    async def save_intake(payload: GuidedIntake):
        tx=await db.payment_transactions.find_one({"session_id":payload.session_id},{"_id":0})
        expected={"strategic-planning":"strategic_planning_497","board-recommitment":"board_recommitment_497"}.get(payload.product)
        if not tx or tx.get("payment_status")!="paid" or tx.get("purchase_source")!=expected:
            raise HTTPException(402,"Paid access could not be confirmed")
        now=datetime.now(timezone.utc).isoformat()
        await db.guided_product_intakes.update_one({"session_id":payload.session_id},{"$set":{"session_id":payload.session_id,"product":payload.product,"answers":payload.answers,"updated_at":now},"$setOnInsert":{"created_at":now}},upsert=True)
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
