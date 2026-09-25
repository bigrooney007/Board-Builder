import html
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import resend
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from member_auth import authenticate_member, hash_member_password, new_uuid, require_entitlement
from platform_communications import notify_homepage_lead, public_origin

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
    desired_outcomes: str = ""
    board_support_needed: str = ""

class GuidedInitialize(BaseModel):
    session_id: str = Field(min_length=1)

class GuidedAccessEmail(BaseModel):
    session_id: str = Field(min_length=1)
    product: str
    origin_url: str = Field(min_length=1)

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
            {"$set": {"user_id": member["user_id"], "answers": answers,
                      "desired_outcomes": payload.desired_outcomes.strip(),
                      "board_support_needed": payload.board_support_needed.strip(),
                      "result": report, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return {"result": report}

    @router.post("/board-recommitment/initialize")
    async def initialize_board_recommitment(payload: GuidedInitialize, request: Request):
        """Create the paid Recommitment workspace without a second intake form."""
        tx = await db.payment_transactions.find_one(
            {"session_id": payload.session_id, "payment_status": "paid", "purchase_source": "board_recommitment_497"},
            {"_id": 0},
        )
        if not tx:
            raise HTTPException(402, "Paid Board Recommitment access could not be confirmed")
        lead = await db.guided_product_leads.find_one({"token": tx.get("guided_lead_token", "")}, {"_id": 0}) or {}
        member = await authenticate_member(request, db)
        if member.get("email", "").lower() != str(lead.get("email", "")).lower() and not member.get("internal_admin_entitlement"):
            raise HTTPException(401, "Log in with the email used for this Board Recommitment purchase")
        now = datetime.now(timezone.utc).isoformat()
        await db.members.update_one(
            {"user_id": member["user_id"]},
            {"$addToSet": {"entitlements": "reactivation_self_guided"}, "$set": {"updated_at": now}},
        )
        payment_contact = {"email": tx.get("payment_email") or lead.get("email", ""), "phone": tx.get("payment_phone", "")}
        await db.guided_product_intakes.update_one(
            {"session_id": payload.session_id},
            {"$set": {"session_id": payload.session_id, "product": "board-recommitment",
                      "payment_contact": payment_contact, "updated_at": now},
             "$setOnInsert": {"answers": {}, "created_at": now}},
            upsert=True,
        )
        await db.board_reactivation_intakes.update_one(
            {"guided_session_id": payload.session_id},
            {"$set": {"user_id": member["user_id"], "session_id": payload.session_id,
                      "guided_session_id": payload.session_id,
                      "payment_contact": payment_contact, "submitted_at": now},
             "$setOnInsert": {
                 "organization_name": lead.get("organization", ""),
                 "founder_title": "",
                 "mission": "",
                 "organization_goals": "",
             }},
            upsert=True,
        )
        return {"saved": True, "dashboard_url": f"/board-recommitment/dashboard?session_id={payload.session_id}"}
    @router.post("/lead")
    async def create_lead(payload: GuidedLead):
        if payload.product not in {"strategic-planning","board-recommitment"}:
            raise HTTPException(400,"Unknown guided product")
        token=secrets.token_urlsafe(24); now=datetime.now(timezone.utc).isoformat()
        doc={"token":token,**payload.model_dump(mode="json"),"email":str(payload.email).lower(),"created_at":now,"updated_at":now,
             "followup_status":"active","followup_step":0,"next_followup_at":now,"converted_at":""}
        await db.guided_product_leads.insert_one(doc.copy())
        try:
            root=public_origin(payload.origin_url or "")
            pathway=payload.product
            next_url=f"{root}/{payload.product}/video?token={token}"
            await notify_homepage_lead(
                db,
                pathway=pathway,
                source_id=token,
                name=payload.name,
                email=str(payload.email).lower(),
                organization=payload.organization,
                continue_url=next_url,
                details={"board_count": str(payload.board_count)},
            )
        except Exception:
            pass
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
        lead=await db.guided_product_leads.find_one({"token":tx.get("guided_lead_token","")},{"_id":0}) or {}
        authenticated=await authenticate_member(request,db)
        if authenticated.get("email","").lower()!=str(lead.get("email","")).lower() and not authenticated.get("internal_admin_entitlement"):
            raise HTTPException(401,f"Log in with the email used for this {payload.product.replace('-', ' ').title()} purchase before continuing")
        now=datetime.now(timezone.utc).isoformat()
        entitlement="strategic_planning_497" if payload.product=="strategic-planning" else "reactivation_self_guided"
        await db.members.update_one({"user_id":authenticated["user_id"]},{"$addToSet":{"entitlements":entitlement},"$set":{"updated_at":now}})
        payment_contact={"email":tx.get("payment_email") or lead.get("email", ""),"phone":tx.get("payment_phone", "")}
        await db.guided_product_intakes.update_one({"session_id":payload.session_id},{"$set":{"session_id":payload.session_id,"product":payload.product,"answers":payload.answers,"payment_contact":payment_contact,"updated_at":now},"$setOnInsert":{"created_at":now}},upsert=True)
        if payload.product=="board-recommitment":
            await db.board_reactivation_intakes.update_one({"guided_session_id":payload.session_id},{"$set":{"user_id":authenticated["user_id"],"session_id":payload.session_id,"organization_name":lead.get("organization",""),"founder_title":"","mission":payload.answers.get("mission",""),"organization_goals":payload.answers.get("goals",""),"guided_session_id":payload.session_id,"guided_answers":payload.answers,"payment_contact":payment_contact,"submitted_at":now}},upsert=True)
        elif payload.product=="strategic-planning":
            lead=await db.guided_product_leads.find_one({"token":tx.get("guided_lead_token","")},{"_id":0}) or {}
            existing=await db.sp_projects.find_one({"guided_session_id":payload.session_id},{"_id":0})
            if not existing:
                project_id=secrets.token_hex(16)
                await db.sp_projects.insert_one({"project_id":project_id,"guided_session_id":payload.session_id,"owner_user_id":authenticated["user_id"],"organization_name":lead.get("organization") or "Organization","founder_name":lead.get("name") or "Organization Leader","founder_email":lead.get("email") or "","founder_title":"","mission":payload.answers.get("mission",""),"status":"Active","generic_form_token":secrets.token_urlsafe(32),"created_at":now})
            else:
                await db.sp_projects.update_one({"project_id":existing["project_id"]},{"$set":{"owner_user_id":authenticated["user_id"],"organization_name":lead.get("organization") or existing.get("organization_name") or "Organization","founder_name":lead.get("name") or existing.get("founder_name") or "Organization Leader","founder_email":lead.get("email") or existing.get("founder_email") or "","mission":payload.answers.get("mission",existing.get("mission","")),"updated_at":now}})
            project=existing or await db.sp_projects.find_one({"guided_session_id":payload.session_id},{"_id":0})
            participant_id=secrets.token_hex(16)
            await db.sp_participants.update_one({"project_id":project["project_id"],"email":str(lead.get("email") or "").lower()},{"$setOnInsert":{"participant_id":participant_id,"project_id":project["project_id"],"name":lead.get("name") or "Organization Leader","email":str(lead.get("email") or "").lower(),"role":"Lead User","status":"INVITED","form_token":secrets.token_urlsafe(32),"review_status":"NOT SENT","review_token":secrets.token_urlsafe(32),"created_at":now}},upsert=True)
        return {"saved":True,"dashboard_url":f"/{payload.product}/dashboard?session_id={payload.session_id}"}

    @router.get("/dashboard")
    async def dashboard(session_id: str, product: str, request: Request):
        tx=await db.payment_transactions.find_one({"session_id":session_id},{"_id":0})
        expected={"strategic-planning":"strategic_planning_497","board-recommitment":"board_recommitment_497"}.get(product)
        if not tx or tx.get("payment_status")!="paid" or tx.get("purchase_source")!=expected:
            raise HTTPException(402,"Paid access could not be confirmed")
        lead=await db.guided_product_leads.find_one({"token":tx.get("guided_lead_token","")},{"_id":0}) or {}
        member=await authenticate_member(request,db)
        if member.get("email","").lower()!=str(lead.get("email","")).lower() and not member.get("internal_admin_entitlement"):
            raise HTTPException(401,"This dashboard belongs to a different account")
        intake=await db.guided_product_intakes.find_one({"session_id":session_id},{"_id":0})
        return {"product":product,"intake":intake or {}}

    @router.post("/access-email")
    async def send_guided_access_email(payload: GuidedAccessEmail):
        expected = {"strategic-planning": "strategic_planning_497", "board-recommitment": "board_recommitment_497"}.get(payload.product)
        parsed = urlparse(payload.origin_url)
        if not expected or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(400, "Invalid product access request")
        tx = await db.payment_transactions.find_one(
            {"session_id": payload.session_id, "payment_status": "paid", "purchase_source": expected}, {"_id": 0}
        )
        if not tx:
            raise HTTPException(402, "Paid access could not be confirmed")
        if tx.get("access_email_sent_at"):
            return {"sent": True}
        lead = await db.guided_product_leads.find_one({"token": tx.get("guided_lead_token", "")}, {"_id": 0}) or {}
        email = str(tx.get("payment_email") or lead.get("email") or "").strip().lower()
        if "@" not in email:
            raise HTTPException(409, "The payment does not contain a usable email address")
        member = await db.members.find_one({"email": email}, {"_id": 0})
        now = datetime.now(timezone.utc)
        if not member:
            names = str(lead.get("name") or "Organization Leader").split(None, 1)
            member = {"user_id": new_uuid(), "email": email, "first_name": names[0],
                      "last_name": names[1] if len(names) > 1 else "",
                      "password_hash": hash_member_password(secrets.token_urlsafe(48)), "entitlements": [],
                      "lead_ids": [], "stripe_customer_id": "", "account_status": "guided_guest",
                      "created_at": now.isoformat(), "updated_at": now.isoformat()}
            await db.members.insert_one(member.copy())
        entitlement = "strategic_planning_497" if payload.product == "strategic-planning" else "reactivation_self_guided"
        await db.members.update_one(
            {"user_id": member["user_id"]},
            {"$addToSet": {"entitlements": entitlement}, "$set": {"updated_at": now.isoformat()}},
        )
        token = secrets.token_urlsafe(32)
        await db.password_resets.insert_one({"token": token, "user_id": member["user_id"], "email": email,
            "expires_at": (now + timedelta(hours=48)).isoformat(), "used": False, "created_at": now.isoformat()})
        root = payload.origin_url.rstrip("/")
        dashboard_path = "/strategic-planning/dashboard" if payload.product == "strategic-planning" else "/board-recommitment/dashboard"
        dashboard_link = f"{root}{dashboard_path}?session_id={payload.session_id}"
        login_link = f"{root}/login?next={dashboard_path}%3Fsession_id%3D{payload.session_id}"
        setup_link = f"{root}/reset-password/{token}"
        product_name = "Strategic Planning" if payload.product == "strategic-planning" else "Board Recommitment"
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        await resend.Emails.send_async({"from": os.environ["NONPROFIT_SENDER"], "to": [email],
            "subject": f"Save This Email: Your {product_name} Login And Dashboard",
            "html": ("<div style='max-width:600px;margin:auto;font-family:Arial,sans-serif;color:#111827;line-height:1.65'>"
                     f"<h2>Your {html.escape(product_name)} workspace is ready</h2>"
                     f"<p>Hello {html.escape(member.get('first_name',''))},</p>"
                     "<p>Save this email so you can return to your work at any time.</p>"
                     f"<p><strong>Account email:</strong> {html.escape(email)}</p>"
                     f"<p><a href='{setup_link}'>Create or reset my password</a></p>"
                     f"<p><a href='{login_link}'>Log in to Nonprofit Board Builder</a></p>"
                     f"<p><a href='{dashboard_link}'>Open my {html.escape(product_name)} dashboard</a></p>"
                     f"<p>If you ever forget your password, use <a href='{root}/forgot-password'>Forgot Password</a> on the login page.</p>"
                     "<p>Rooney Akpesiri<br/>Nonprofit Board Builder</p></div>")})
        await db.payment_transactions.update_one({"session_id": payload.session_id}, {"$set": {"access_email_sent_at": now.isoformat(), "access_email_sent_to": email}})
        return {"sent": True}
    return router
