import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from member_auth import authenticate_member, require_entitlement

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

class FounderAuditSubmission(BaseModel):
    answers: dict

def create_guided_product_router(db):
    router = APIRouter(prefix="/api/guided")
    audit_dimensions = {
        "co_leader": "Co-Leader", "co_facilitator": "Co-Facilitator", "co_architect": "Co-Architect",
        "co_mobilizer": "Co-Mobilizer", "co_evaluator": "Co-Evaluator", "co_reporter": "Co-Reporter",
    }

    @router.get("/founder-board-audit")
    async def founder_board_audit(request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {"reactivation_self_guided"})
        saved = await db.founder_board_audits.find_one({"user_id": member["user_id"]}, {"_id": 0}) or {}
        return {"audit": saved}

    @router.post("/founder-board-audit")
    async def save_founder_board_audit(payload: FounderAuditSubmission, request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {"reactivation_self_guided"})
        answers = {str(k): int(v) for k, v in payload.answers.items() if str(v).isdigit() and 1 <= int(v) <= 4}
        required = {f"{key}_{number}" for key in audit_dimensions for number in (1, 2)}
        if set(answers) != required:
            raise HTTPException(422, "Answer every audit question before seeing your result")
        dimensions = []
        for key, label in audit_dimensions.items():
            score = answers[f"{key}_1"] + answers[f"{key}_2"]
            level = "Embedded" if score >= 7 else "Developing" if score >= 5 else "Limited"
            dimensions.append({"key": key, "label": label, "score": score, "maximum": 8, "level": level})
        total = sum(row["score"] for row in dimensions)
        stage = "Board Partnership Is Embedded" if total >= 42 else "Board Partnership Is Developing" if total >= 30 else "The Board Is Being Underused"
        weakest = sorted(dimensions, key=lambda row: row["score"])[:2]
        report = {
            "score": total, "maximum": 48, "stage": stage, "dimensions": dimensions,
            "summary": "This audit measures how fully you involve the board as partners in leadership, facilitation, organizational design, resource mobilization, evaluation and reporting.",
            "priority": "Your immediate opportunity is to strengthen " + " and ".join(row["label"] for row in weakest) + ".",
        }
        now = datetime.now(timezone.utc).isoformat()
        await db.founder_board_audits.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"user_id": member["user_id"], "answers": answers, "result": report, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return {"result": report}
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
        if payload.product=="board-recommitment":
            # Verify identity before persisting any protected Recommitment intake data.
            lead=await db.guided_product_leads.find_one({"token":tx.get("guided_lead_token","")},{"_id":0})
            member=await db.members.find_one({"email":(lead or {}).get("email","")},{"_id":0})
            if not member: raise HTTPException(409,"Your Board Recommitment workspace session could not be linked")
            authenticated=await authenticate_member(request,db)
            if authenticated.get("user_id")!=member.get("user_id"): raise HTTPException(401,"Log in with the email used for this Board Recommitment purchase before continuing")
        lead=await db.guided_product_leads.find_one({"token":tx.get("guided_lead_token","")},{"_id":0}) or {}
        payment_contact={"email":tx.get("payment_email") or lead.get("email", ""),"phone":tx.get("payment_phone", "")}
        await db.guided_product_intakes.update_one({"session_id":payload.session_id},{"$set":{"session_id":payload.session_id,"product":payload.product,"answers":payload.answers,"payment_contact":payment_contact,"updated_at":now},"$setOnInsert":{"created_at":now}},upsert=True)
        if payload.product=="board-recommitment":
            lead=await db.guided_product_leads.find_one({"token":tx.get("guided_lead_token","")},{"_id":0})
            member=await db.members.find_one({"email":(lead or {}).get("email","")},{"_id":0})
            if not member:
                raise HTTPException(409,"Your Board Recommitment workspace session could not be linked")
            await db.members.update_one({"user_id":member["user_id"]},{"$addToSet":{"entitlements":"reactivation_self_guided"},"$set":{"updated_at":now}})
            await db.board_reactivation_intakes.update_one({"guided_session_id":payload.session_id},{"$set":{"user_id":member["user_id"],"organization_name":(lead or {}).get("organization",""),"founder_title":"","mission":payload.answers.get("mission",""),"organization_goals":payload.answers.get("goals",""),"guided_session_id":payload.session_id,"guided_answers":payload.answers,"payment_contact":payment_contact,"submitted_at":now}},upsert=True)
        elif payload.product=="strategic-planning":
            lead=await db.guided_product_leads.find_one({"token":tx.get("guided_lead_token","")},{"_id":0}) or {}
            existing=await db.sp_projects.find_one({"guided_session_id":payload.session_id},{"_id":0})
            if not existing:
                project_id=secrets.token_hex(16)
                await db.sp_projects.insert_one({"project_id":project_id,"guided_session_id":payload.session_id,"organization_name":lead.get("organization") or "Organization","founder_name":lead.get("name") or "Organization Leader","founder_email":lead.get("email") or "","founder_title":"","mission":payload.answers.get("mission",""),"status":"Active","generic_form_token":secrets.token_urlsafe(32),"created_at":now})
            project=existing or await db.sp_projects.find_one({"guided_session_id":payload.session_id},{"_id":0})
            participant_id=secrets.token_hex(16)
            await db.sp_participants.update_one({"project_id":project["project_id"],"email":str(lead.get("email") or "").lower()},{"$setOnInsert":{"participant_id":participant_id,"project_id":project["project_id"],"name":lead.get("name") or "Organization Leader","email":str(lead.get("email") or "").lower(),"role":"Lead User","status":"INVITED","form_token":secrets.token_urlsafe(32),"review_status":"NOT SENT","review_token":secrets.token_urlsafe(32),"created_at":now}},upsert=True)
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
