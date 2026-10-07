import asyncio
import io
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import stripe
from docx import Document
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, EmailStr, Field
from pypdf import PdfReader

from autofundraiser_ai import CRITERIA, analyze_source, build_diagnosis, build_final_strategy
from autofundraiser_email import (
    send_contribution_notification,
    send_contributor_invite,
    send_payment_email,
    send_resume_email,
)

logger = logging.getLogger(__name__)

DEFAULT_HOMEPAGE = {
    "headline": "How Does Your Organization Currently Raise Money?",
    "problem_statement": "The number one reason nonprofits struggle to raise money is because of their fundraising strategy and approach.",
    "supporting_text": "Show Auto Fundraiser how your organization currently fundraises. Describe your approach or attach the strategy or plan you already use.",
    "composer_placeholder": "Describe your current fundraising strategy or approach…",
    "no_strategy_label": "I don't have a fundraising strategy",
    "cta": "REVIEW MY FUNDRAISING APPROACH",
    "result_offer_heading": "Build Your Organization's Fundraising Strategy",
    "result_offer_text": "Auto Fundraiser will guide you through building the missing parts into one clear fundraising strategy your organization can execute.",
    "price": "$497",
    "price_cents": 49700,
}

CLARIFICATION_COPY = {
    "WHO": "I can't identify a clearly defined fundraising audience in what you shared. Do you know exactly who your organization's ideal funders are?",
    "WHERE": "I can see who you are trying to raise money from, but I can't clearly see where you consistently find them. Do you know where to find your ideal funders?",
    "ATTRACT": "I can't clearly identify how your organization consistently gets the attention of your ideal funders before asking for money. Do you know how you will attract them and build their interest?",
    "RAISE": "I can't clearly identify a defined process for moving your ideal funders from first contact to giving. Do you have a fundraising process for that journey?",
    "ASK": "I can't clearly identify what you will ask your ideal funders to fund and how much you will ask for. Do you already know the ask and amount?",
    "SYSTEM": "I can see parts of the strategy, but I can't clearly identify the recurring system that will drive it. Do you already have a system for executing the strategy consistently?",
}

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def token() -> str:
    return secrets.token_urlsafe(24)

def _frontend_url() -> str:
    return (os.environ.get("AUTO_FUNDRAISER_FRONTEND_URL") or os.environ.get("FRONTEND_URL") or "").rstrip("/")

def _clean(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not doc:
        return {}
    out = dict(doc)
    out.pop("_id", None)
    return out

async def _extract_file(upload: Optional[UploadFile]) -> str:
    if not upload or not upload.filename:
        return ""
    raw = await upload.read()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(413, "Please upload a file smaller than 8MB.")
    name = upload.filename.lower()
    try:
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        if name.endswith(".docx"):
            doc = Document(io.BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs).strip()
        if name.endswith((".txt", ".md", ".csv")):
            return raw.decode("utf-8", errors="ignore").strip()
    except Exception as exc:
        logger.exception("Auto Fundraiser file extraction failed")
        raise HTTPException(400, "We could not read that file. Please paste the fundraising approach instead.") from exc
    raise HTTPException(400, "Upload a PDF, DOCX, TXT, MD or CSV file.")

def _first_no(clarifications: Dict[str, Any]) -> Optional[str]:
    for key, _ in CRITERIA:
        if clarifications.get(key, {}).get("knows") is False:
            return key
    return None

def _next_clarification(lead: Dict[str, Any]) -> Optional[Dict[str, str]]:
    clarifications = lead.get("clarifications") or {}
    if _first_no(clarifications):
        return None
    criteria = (lead.get("analysis") or {}).get("criteria") or {}
    for key, _description in CRITERIA:
        if criteria.get(key, {}).get("status") == "PRESENT":
            continue
        if key in clarifications:
            continue
        return {
            "criterion": key,
            "question": CLARIFICATION_COPY[key],
            "evidence": criteria.get(key, {}).get("evidence", ""),
        }
    return None

async def _ensure_diagnosis(db, lead: Dict[str, Any]) -> Dict[str, Any]:
    if lead.get("diagnosis"):
        return lead
    diagnosis = await build_diagnosis(lead)
    await db.autofundraiser_leads.update_one(
        {"lead_id": lead["lead_id"]},
        {"$set": {
            "diagnosis": diagnosis,
            "stage": "DIAGNOSIS_READY",
            "updated_at": utcnow(),
            "last_activity_at": utcnow(),
        }},
    )
    lead.update({"diagnosis": diagnosis, "stage": "DIAGNOSIS_READY"})
    return lead

def _lead_payload(lead: Dict[str, Any]) -> Dict[str, Any]:
    result = _clean(lead)
    result.pop("source_text", None)
    result.pop("checkout_session_id", None)
    result["analysis_pending"] = not bool(lead.get("analysis"))
    result["next_clarification"] = _next_clarification(lead) if lead.get("analysis") else None
    return result

class ClarificationBody(BaseModel):
    criterion: str
    knows: bool
    note: str = ""

class StrategyAnswerBody(BaseModel):
    question: int = Field(ge=1, le=5)
    answer: str = Field(min_length=1)

class ParticipationBody(BaseModel):
    answer: str = Field(min_length=1)

class RealityBody(BaseModel):
    answers: Dict[str, str]

class MeetingBody(BaseModel):
    date: str = ""
    time: str = ""
    timezone: str = ""
    notes: str = ""

class ContributorInviteBody(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    role: str = ""

class ContributorSubmissionBody(BaseModel):
    answers: Dict[str, str]
    participation: str = Field(min_length=1)

class AdoptionBody(BaseModel):
    adopted: Dict[str, List[str]]
    meeting_notes: str = ""

class HomepageBody(BaseModel):
    headline: str
    problem_statement: str
    supporting_text: str
    composer_placeholder: str
    no_strategy_label: str
    cta: str
    result_offer_heading: str
    result_offer_text: str
    price: str = "$497"
    price_cents: int = 49700

class ManualEmailBody(BaseModel):
    kind: str

def create_autofundraiser_router(db):
    router = APIRouter(prefix="/api/autofundraiser", tags=["Auto Fundraiser"])
    reminder_task = {"task": None}

    async def require_admin(x_auto_fundraiser_admin: str = Header(default="")):
        expected = os.environ.get("AUTO_FUNDRAISER_ADMIN_KEY") or os.environ.get("ADMIN_PASSWORD")
        if not expected or not secrets.compare_digest(x_auto_fundraiser_admin or "", expected):
            raise HTTPException(401, "Invalid Auto Fundraiser admin key.")
        return True

    async def get_lead(resume_token: str, paid_required: bool = False) -> Dict[str, Any]:
        lead = await db.autofundraiser_leads.find_one({"resume_token": resume_token})
        if not lead:
            raise HTTPException(404, "This Auto Fundraiser link is not available.")
        if paid_required and not lead.get("paid"):
            raise HTTPException(402, "Payment is required to build the fundraising strategy.")
        return lead

    @router.on_event("startup")
    async def startup():
        await db.autofundraiser_leads.create_index("lead_id", unique=True)
        await db.autofundraiser_leads.create_index("resume_token", unique=True)
        await db.autofundraiser_leads.create_index("email")
        await db.autofundraiser_leads.create_index([("paid", 1), ("stage", 1), ("last_activity_at", 1)])
        await db.autofundraiser_contributors.create_index("token", unique=True)
        await db.autofundraiser_contributors.create_index([("lead_id", 1), ("email", 1)], unique=True)

        async def reminder_loop():
            while True:
                try:
                    await asyncio.sleep(3600)
                    base = _frontend_url()
                    if not base:
                        continue
                    now = utcnow()
                    abandoned_before = now - timedelta(hours=6)
                    async for lead in db.autofundraiser_leads.find({
                        "paid": {"$ne": True},
                        "stage": {"$in": ["SOURCE_CAPTURED", "CLARIFYING"]},
                        "last_activity_at": {"$lte": abandoned_before},
                        "reminders.abandonment_sent_at": {"$exists": False},
                    }).limit(50):
                        ok = await send_resume_email(
                            lead.get("email", ""), lead.get("name", ""), lead.get("organization_name", ""),
                            f"{base}/auto-fundraiser/review/{lead['resume_token']}",
                        )
                        if ok:
                            await db.autofundraiser_leads.update_one(
                                {"lead_id": lead["lead_id"]},
                                {"$set": {"reminders.abandonment_sent_at": now}},
                            )
                    payment_before = now - timedelta(hours=18)
                    async for lead in db.autofundraiser_leads.find({
                        "paid": {"$ne": True},
                        "stage": {"$in": ["DIAGNOSIS_READY", "RESULT_VIEWED", "CHECKOUT_STARTED"]},
                        "last_activity_at": {"$lte": payment_before},
                        "reminders.payment_sent_at": {"$exists": False},
                    }).limit(50):
                        ok = await send_payment_email(
                            lead.get("email", ""), lead.get("name", ""), lead.get("organization_name", ""),
                            f"{base}/auto-fundraiser/result/{lead['resume_token']}",
                        )
                        if ok:
                            await db.autofundraiser_leads.update_one(
                                {"lead_id": lead["lead_id"]},
                                {"$set": {"reminders.payment_sent_at": now}},
                            )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Auto Fundraiser reminder loop failed")

        reminder_task["task"] = asyncio.create_task(reminder_loop())

    @router.on_event("shutdown")
    async def shutdown():
        if reminder_task["task"]:
            reminder_task["task"].cancel()

    @router.get("/homepage")
    async def homepage():
        stored = await db.autofundraiser_settings.find_one({"key": "homepage"})
        return {**DEFAULT_HOMEPAGE, **(_clean(stored).get("content") or {})}

    @router.post("/leads")
    async def create_lead(
        name: str = Form(...),
        email: EmailStr = Form(...),
        organization_name: str = Form(...),
        approach: str = Form(""),
        no_strategy: bool = Form(False),
        file: Optional[UploadFile] = File(default=None),
    ):
        file_text = await _extract_file(file)
        source = "\n\n".join(part for part in [approach.strip(), file_text] if part).strip()
        if not no_strategy and not source:
            raise HTTPException(400, "Describe your fundraising approach, attach your plan, or tell us you do not have a fundraising strategy.")

        lead_id = secrets.token_hex(12)
        resume_token = token()
        now = utcnow()
        lead = {
            "lead_id": lead_id,
            "resume_token": resume_token,
            "name": name.strip(),
            "email": str(email).lower(),
            "organization_name": organization_name.strip(),
            "source_type": "none" if no_strategy else ("upload" if file_text else "written"),
            "source_filename": file.filename if file and file.filename else "",
            "source_text": source,
            "no_strategy": no_strategy,
            "analysis": {},
            "clarifications": {},
            "diagnosis": None,
            "paid": False,
            "stage": "SOURCE_CAPTURED",
            "strategy_answers": {},
            "present_reality": {},
            "participation": "",
            "meeting": {},
            "adopted": {},
            "final_strategy": None,
            "created_at": now,
            "updated_at": now,
            "last_activity_at": now,
            "reminders": {},
        }

        # Capture the person before any AI work. If AI is temporarily unavailable,
        # the admin still sees the lead and the person keeps a resume path.
        await db.autofundraiser_leads.insert_one(dict(lead))

        try:
            if no_strategy:
                analysis = {
                    "summary": "The organization told Auto Fundraiser that it does not currently have a fundraising strategy.",
                    "criteria": {key: {"status": "MISSING", "evidence": "The organization said it does not have a fundraising strategy.", "confidence": 1.0} for key, _ in CRITERIA},
                }
            else:
                analysis = await analyze_source(source)
            lead["analysis"] = analysis
            await db.autofundraiser_leads.update_one(
                {"lead_id": lead_id},
                {"$set": {"analysis": analysis, "updated_at": utcnow(), "last_activity_at": utcnow()}},
            )

            if no_strategy:
                lead = await _ensure_diagnosis(db, lead)
            elif _next_clarification(lead):
                lead["stage"] = "CLARIFYING"
                await db.autofundraiser_leads.update_one(
                    {"lead_id": lead_id},
                    {"$set": {"stage": "CLARIFYING", "updated_at": utcnow(), "last_activity_at": utcnow()}},
                )
            else:
                diagnosis = await build_diagnosis(lead)
                lead["diagnosis"] = diagnosis
                lead["stage"] = "DIAGNOSIS_READY"
                await db.autofundraiser_leads.update_one(
                    {"lead_id": lead_id},
                    {"$set": {"diagnosis": diagnosis, "stage": "DIAGNOSIS_READY", "updated_at": utcnow(), "last_activity_at": utcnow()}},
                )
        except Exception as exc:
            logger.exception("Auto Fundraiser initial analysis failed")
            await db.autofundraiser_leads.update_one(
                {"lead_id": lead_id},
                {"$set": {"analysis_error": str(exc)[:500], "updated_at": utcnow()}},
            )
            lead["analysis_error"] = str(exc)[:500]
            return _lead_payload(lead)

        return _lead_payload(lead)

    @router.get("/leads/{resume_token}")
    async def read_lead(resume_token: str):
        lead = await get_lead(resume_token)
        if not lead.get("analysis"):
            try:
                if lead.get("no_strategy"):
                    analysis = {
                        "summary": "The organization told Auto Fundraiser that it does not currently have a fundraising strategy.",
                        "criteria": {key: {"status": "MISSING", "evidence": "The organization said it does not have a fundraising strategy.", "confidence": 1.0} for key, _ in CRITERIA},
                    }
                else:
                    analysis = await analyze_source(lead.get("source_text", ""))
                await db.autofundraiser_leads.update_one(
                    {"lead_id": lead["lead_id"]},
                    {"$set": {"analysis": analysis, "analysis_error": "", "updated_at": utcnow(), "last_activity_at": utcnow()}},
                )
                lead["analysis"] = analysis
            except Exception:
                logger.exception("Auto Fundraiser resume analysis failed")
                raise HTTPException(502, "Your review is saved, but Auto Fundraiser could not complete the analysis right now.")
        if not lead.get("diagnosis") and not _next_clarification(lead):
            lead = await _ensure_diagnosis(db, lead)
        return _lead_payload(lead)

    @router.post("/leads/{resume_token}/clarify")
    async def clarify(resume_token: str, body: ClarificationBody):
        lead = await get_lead(resume_token)
        criterion = body.criterion.upper()
        if criterion not in {key for key, _ in CRITERIA}:
            raise HTTPException(400, "Unknown clarification.")
        expected = _next_clarification(lead)
        if not expected or expected["criterion"] != criterion:
            raise HTTPException(409, "That is not the next clarification for this review.")
        clarification = {"knows": body.knows, "note": body.note.strip(), "answered_at": utcnow()}
        await db.autofundraiser_leads.update_one(
            {"lead_id": lead["lead_id"]},
            {"$set": {
                f"clarifications.{criterion}": clarification,
                "stage": "CLARIFYING",
                "updated_at": utcnow(),
                "last_activity_at": utcnow(),
            }},
        )
        lead.setdefault("clarifications", {})[criterion] = clarification
        if not body.knows or not _next_clarification(lead):
            lead = await _ensure_diagnosis(db, lead)
        return _lead_payload(lead)

    @router.post("/leads/{resume_token}/result-viewed")
    async def result_viewed(resume_token: str):
        lead = await get_lead(resume_token)
        await db.autofundraiser_leads.update_one(
            {"lead_id": lead["lead_id"]},
            {"$set": {"stage": "RESULT_VIEWED", "last_activity_at": utcnow(), "updated_at": utcnow()}},
        )
        return {"ok": True}

    @router.post("/leads/{resume_token}/checkout")
    async def checkout(resume_token: str, request: Request):
        lead = await get_lead(resume_token)
        if not lead.get("diagnosis"):
            raise HTTPException(409, "Complete your fundraising diagnosis before payment.")
        key = os.environ.get("STRIPE_SECRET_KEY")
        if not key:
            raise HTTPException(503, "Stripe is not configured yet.")
        stripe.api_key = key
        origin = _frontend_url() or (request.headers.get("origin") or "").rstrip("/") or str(request.base_url).rstrip("/")
        content = await homepage()
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                customer_email=lead["email"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(content.get("price_cents", 49700)),
                        "product_data": {
                            "name": "Auto Fundraiser Strategy Builder",
                            "description": "Build your organization's fundraising strategy with Auto Fundraiser.",
                        },
                    },
                    "quantity": 1,
                }],
                success_url=f"{origin}/auto-fundraiser/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{origin}/auto-fundraiser/result/{resume_token}",
                metadata={"product": "auto_fundraiser_strategy", "lead_id": lead["lead_id"], "resume_token": resume_token},
            )
        except Exception as exc:
            logger.exception("Auto Fundraiser Stripe checkout failed")
            raise HTTPException(502, "We could not start checkout. Please try again.") from exc
        await db.autofundraiser_leads.update_one(
            {"lead_id": lead["lead_id"]},
            {"$set": {"checkout_session_id": session.id, "stage": "CHECKOUT_STARTED", "last_activity_at": utcnow(), "updated_at": utcnow()}},
        )
        return {"checkout_url": session.url}

    async def mark_paid(session_id: str) -> Dict[str, Any]:
        lead = await db.autofundraiser_leads.find_one({"checkout_session_id": session_id})
        if not lead:
            raise HTTPException(404, "Payment session is not connected to an Auto Fundraiser review.")
        if not lead.get("paid"):
            await db.autofundraiser_leads.update_one(
                {"lead_id": lead["lead_id"]},
                {"$set": {"paid": True, "paid_at": utcnow(), "stage": "PAID", "updated_at": utcnow(), "last_activity_at": utcnow()}},
            )
            lead["paid"] = True
            lead["stage"] = "PAID"
        return lead

    @router.get("/checkout-status")
    async def checkout_status(session_id: str):
        key = os.environ.get("STRIPE_SECRET_KEY")
        if not key:
            raise HTTPException(503, "Stripe is not configured yet.")
        stripe.api_key = key
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except Exception as exc:
            raise HTTPException(400, "We could not verify this payment session.") from exc
        if session.payment_status != "paid":
            return {"paid": False}
        lead = await mark_paid(session_id)
        return {"paid": True, "resume_token": lead["resume_token"]}

    @router.post("/stripe-webhook")
    async def stripe_webhook(request: Request):
        secret = os.environ.get("AUTO_FUNDRAISER_STRIPE_WEBHOOK_SECRET")
        if not secret:
            raise HTTPException(503, "Auto Fundraiser webhook is not configured.")
        payload = await request.body()
        signature = request.headers.get("stripe-signature", "")
        try:
            event = stripe.Webhook.construct_event(payload, signature, secret)
        except Exception as exc:
            raise HTTPException(400, "Invalid Stripe webhook.") from exc
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            if session.get("metadata", {}).get("product") == "auto_fundraiser_strategy" and session.get("payment_status") == "paid":
                lead = await db.autofundraiser_leads.find_one({"lead_id": session.get("metadata", {}).get("lead_id")})
                if lead:
                    await db.autofundraiser_leads.update_one(
                        {"lead_id": lead["lead_id"]},
                        {"$set": {"checkout_session_id": session["id"], "paid": True, "paid_at": utcnow(), "stage": "PAID", "updated_at": utcnow(), "last_activity_at": utcnow()}},
                    )
        return {"received": True}

    @router.get("/strategy/{resume_token}")
    async def strategy_state(resume_token: str):
        lead = await get_lead(resume_token, paid_required=True)
        contributors = []
        async for contributor in db.autofundraiser_contributors.find({"lead_id": lead["lead_id"]}).sort("created_at", 1):
            contributors.append(_clean(contributor))
        result = _lead_payload(lead)
        result["contributors"] = contributors
        return result

    @router.put("/strategy/{resume_token}/answer")
    async def save_strategy_answer(resume_token: str, body: StrategyAnswerBody):
        lead = await get_lead(resume_token, paid_required=True)
        await db.autofundraiser_leads.update_one(
            {"lead_id": lead["lead_id"]},
            {"$set": {
                f"strategy_answers.{body.question}": body.answer.strip(),
                "stage": "STRATEGY_QUESTIONS",
                "updated_at": utcnow(),
                "last_activity_at": utcnow(),
            }},
        )
        return {"ok": True}

    @router.put("/strategy/{resume_token}/reality")
    async def save_reality(resume_token: str, body: RealityBody):
        lead = await get_lead(resume_token, paid_required=True)
        cleaned = {k: str(v).strip() for k, v in body.answers.items()}
        await db.autofundraiser_leads.update_one(
            {"lead_id": lead["lead_id"]},
            {"$set": {"present_reality": cleaned, "stage": "PRESENT_REALITY", "updated_at": utcnow(), "last_activity_at": utcnow()}},
        )
        return {"ok": True}

    @router.put("/strategy/{resume_token}/participation")
    async def save_participation(resume_token: str, body: ParticipationBody):
        lead = await get_lead(resume_token, paid_required=True)
        await db.autofundraiser_leads.update_one(
            {"lead_id": lead["lead_id"]},
            {"$set": {"participation": body.answer.strip(), "stage": "PLANNING", "updated_at": utcnow(), "last_activity_at": utcnow()}},
        )
        return {"ok": True}

    @router.put("/strategy/{resume_token}/meeting")
    async def save_meeting(resume_token: str, body: MeetingBody):
        lead = await get_lead(resume_token, paid_required=True)
        await db.autofundraiser_leads.update_one(
            {"lead_id": lead["lead_id"]},
            {"$set": {"meeting": body.model_dump(), "stage": "PLANNING", "updated_at": utcnow(), "last_activity_at": utcnow()}},
        )
        return {"ok": True}

    @router.post("/strategy/{resume_token}/contributors")
    async def invite_contributor(resume_token: str, body: ContributorInviteBody):
        lead = await get_lead(resume_token, paid_required=True)
        existing = await db.autofundraiser_contributors.find_one({"lead_id": lead["lead_id"], "email": str(body.email).lower()})
        if existing:
            contributor = existing
        else:
            contributor = {
                "token": token(),
                "lead_id": lead["lead_id"],
                "name": body.name.strip(),
                "email": str(body.email).lower(),
                "role": body.role.strip(),
                "answers": {},
                "participation": "",
                "completed": False,
                "created_at": utcnow(),
                "updated_at": utcnow(),
            }
            await db.autofundraiser_contributors.insert_one(dict(contributor))
        base = _frontend_url() or str(os.environ.get("PUBLIC_BASE_URL", "")).rstrip("/")
        if base:
            await send_contributor_invite(
                contributor["email"], contributor["name"], lead["organization_name"],
                f"{base}/auto-fundraiser/contribute/{contributor['token']}", lead.get("name", ""),
            )
        return _clean(contributor)

    @router.get("/contribute/{contributor_token}")
    async def contributor_state(contributor_token: str):
        contributor = await db.autofundraiser_contributors.find_one({"token": contributor_token})
        if not contributor:
            raise HTTPException(404, "This contribution link is not available.")
        lead = await db.autofundraiser_leads.find_one({"lead_id": contributor["lead_id"]})
        return {"contributor": _clean(contributor), "organization_name": (lead or {}).get("organization_name", "")}

    @router.post("/contribute/{contributor_token}")
    async def contributor_submit(contributor_token: str, body: ContributorSubmissionBody):
        contributor = await db.autofundraiser_contributors.find_one({"token": contributor_token})
        if not contributor:
            raise HTTPException(404, "This contribution link is not available.")
        lead = await db.autofundraiser_leads.find_one({"lead_id": contributor["lead_id"]})
        if not lead:
            raise HTTPException(404, "The organization planning record is not available.")
        await db.autofundraiser_contributors.update_one(
            {"token": contributor_token},
            {"$set": {
                "answers": {str(k): str(v).strip() for k, v in body.answers.items()},
                "participation": body.participation.strip(),
                "completed": True,
                "completed_at": utcnow(),
                "updated_at": utcnow(),
            }},
        )
        base = _frontend_url()
        if base:
            await send_contribution_notification(
                lead["email"], lead.get("name", ""), contributor.get("name", "A contributor"),
                lead.get("organization_name", ""), f"{base}/auto-fundraiser/strategy/{lead['resume_token']}",
            )
        return {"completed": True}

    @router.get("/meeting/{resume_token}")
    async def meeting_state(resume_token: str):
        lead = await get_lead(resume_token, paid_required=True)
        contributors = []
        async for contributor in db.autofundraiser_contributors.find({"lead_id": lead["lead_id"], "completed": True}).sort("created_at", 1):
            contributors.append(_clean(contributor))
        return {
            "organization_name": lead["organization_name"],
            "strategy_answers": lead.get("strategy_answers", {}),
            "participation": lead.get("participation", ""),
            "present_reality": lead.get("present_reality", {}),
            "meeting": lead.get("meeting", {}),
            "contributors": contributors,
            "adopted": lead.get("adopted", {}),
            "final_strategy": lead.get("final_strategy"),
        }

    @router.post("/meeting/{resume_token}/adopt")
    async def adopt(resume_token: str, body: AdoptionBody):
        lead = await get_lead(resume_token, paid_required=True)
        contributors = []
        async for contributor in db.autofundraiser_contributors.find({"lead_id": lead["lead_id"], "completed": True}):
            contributors.append(_clean(contributor))
        planning = {
            "organization_name": lead["organization_name"],
            "organizer_answers": lead.get("strategy_answers", {}),
            "present_reality": lead.get("present_reality", {}),
            "organizer_participation": lead.get("participation", ""),
            "contributors": contributors,
            "adopted_ideas": body.adopted,
            "meeting_notes": body.meeting_notes.strip(),
        }
        final_strategy = await build_final_strategy(planning)
        await db.autofundraiser_leads.update_one(
            {"lead_id": lead["lead_id"]},
            {"$set": {
                "adopted": body.adopted,
                "meeting_notes": body.meeting_notes.strip(),
                "final_strategy": final_strategy,
                "stage": "COMPLETE",
                "completed_at": utcnow(),
                "updated_at": utcnow(),
                "last_activity_at": utcnow(),
            }},
        )
        return {"final_strategy": final_strategy}

    @router.get("/admin/homepage", dependencies=[Depends(require_admin)])
    async def admin_homepage():
        return await homepage()

    @router.put("/admin/homepage", dependencies=[Depends(require_admin)])
    async def update_homepage(body: HomepageBody):
        content = body.model_dump()
        await db.autofundraiser_settings.update_one(
            {"key": "homepage"},
            {"$set": {"key": "homepage", "content": content, "updated_at": utcnow()}},
            upsert=True,
        )
        return content

    @router.get("/admin/leads", dependencies=[Depends(require_admin)])
    async def admin_leads():
        items = []
        async for lead in db.autofundraiser_leads.find({}).sort("created_at", -1).limit(500):
            item = _lead_payload(lead)
            item["contributor_count"] = await db.autofundraiser_contributors.count_documents({"lead_id": lead["lead_id"]})
            items.append(item)
        return {"items": items}

    @router.post("/admin/leads/{lead_id}/email", dependencies=[Depends(require_admin)])
    async def admin_email(lead_id: str, body: ManualEmailBody):
        lead = await db.autofundraiser_leads.find_one({"lead_id": lead_id})
        if not lead:
            raise HTTPException(404, "Lead not found.")
        base = _frontend_url()
        if not base:
            raise HTTPException(503, "AUTO_FUNDRAISER_FRONTEND_URL is not configured.")
        if body.kind == "resume":
            ok = await send_resume_email(lead["email"], lead.get("name", ""), lead.get("organization_name", ""), f"{base}/auto-fundraiser/review/{lead['resume_token']}")
        elif body.kind == "payment":
            ok = await send_payment_email(lead["email"], lead.get("name", ""), lead.get("organization_name", ""), f"{base}/auto-fundraiser/result/{lead['resume_token']}")
        else:
            raise HTTPException(400, "Email kind must be resume or payment.")
        return {"sent": ok}

    return router
