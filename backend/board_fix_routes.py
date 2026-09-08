"""Complete Board Fix: post-payment intake, master customer record, roadmap, admin journey view."""
import html
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone

import resend
import stripe
from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field

from ai_service import extract_cv_text
from auth_service import authenticate_admin
from board_fix_master import BOARD_FIX_SOURCE, get_master_record, master_prefill, synthetic_session
from course_content import ACTIVATION_MODULES, REACTIVATION_MODULES, SELF_GUIDED_MODULES
from member_auth import authenticate_member, create_member_token, hash_member_password, new_uuid, require_entitlement, set_member_cookie

PURCHASE_SOURCE = "board_fix_system_497"
DWM_PURCHASE_SOURCE = "board_fix_dwm_5497"
FBB_PURCHASE_SOURCE = "fundraising_board_builder_497"
PURCHASE_SOURCES = [PURCHASE_SOURCE, DWM_PURCHASE_SOURCE, FBB_PURCHASE_SOURCE]
CALENDLY_URL = "https://calendly.com/boardbuilder/recruitboard"

PATHWAYS = [
    ("recruitment", "Board Recruitment", "recruitment_self_guided", SELF_GUIDED_MODULES),
    ("reactivation", "Board Reactivation", "reactivation_self_guided", REACTIVATION_MODULES),
    ("activation", "Board Fundraising Activation", "activation_self_guided", ACTIVATION_MODULES),
]

INTAKE_COLLECTIONS = {
    "recruitment": "board_recruitment_intakes",
    "reactivation": "board_reactivation_intakes",
    "activation": "board_activation_intakes",
}

ADVISORY_OPTION = "Transition to an Advisory Board / Advisory Role"
STEP_OFF_OPTION = "Step Down From the Board"

JOURNEY_STAGES = [
    {"key": "orientation", "label": "Welcome to Board Fix"},
    {"key": "understand", "label": "Understand the Situation", "pathway": "reactivation", "modules": [3]},
    {"key": "identify", "label": "Identify the Board Members You Need", "pathway": "recruitment", "modules": [2]},
    {"key": "launch", "label": "Launch Your Recruitment Campaign", "pathway": "recruitment", "modules": [3]},
    {"key": "select", "label": "Select and Interview Your Applicants", "pathway": "recruitment", "modules": [4]},
    {"key": "references", "label": "Complete References and Background Checks", "pathway": "recruitment", "modules": [5]},
    {"key": "onboard", "label": "Onboard Your New Board Members", "pathway": "recruitment", "modules": [6]},
    {"key": "fundraising_planning", "label": "Build the Fundraising Plan With Your Board", "pathway": "activation", "modules": [2]},
    {"key": "create_strategy", "label": "Build Your Fundraising Strategy", "pathway": "activation", "modules": [3]},
    {"key": "adopt_strategy", "label": "Review and Adopt the Fundraising Strategy", "pathway": "activation", "modules": [4]},
    {"key": "execute_strategy", "label": "Equip Your Board to Execute", "pathway": "activation", "modules": [5]},
]

PREVIEW_ENTITLEMENTS = ["board_fix_system", "recruitment_self_guided", "reactivation_self_guided",
                        "activation_self_guided", "recruitment_selection_onboarding"]

INTAKE_STAGE_KEYS = {"fundraising_planning": "activation"}


class OrientationSelections(BaseModel):
    step_off: str = Field(pattern="^(Yes|No)$")
    advisory: str = Field(pattern="^(Yes|No)$")


class IntakeSubmit(BaseModel):
    session_id: str = ""
    data: dict
    contact_name: str = ""
    contact_email: str = ""
    origin_url: str = ""


logger = logging.getLogger(__name__)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_board_fix_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    async def verify_session(session_id: str):
        txn = await db.payment_transactions.find_one({"session_id": session_id, "purchase_source": {"$in": PURCHASE_SOURCES}}, {"_id": 0})
        if not txn:
            return None
        if txn.get("payment_status") != "paid":
            try:
                session = stripe.checkout.Session.retrieve(session_id)
                if session.payment_status == "paid":
                    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"payment_status": "paid", "status": "complete", "updated_at": now_iso()}})
                    txn["payment_status"] = "paid"
            except Exception:
                return None
        return txn if txn.get("payment_status") == "paid" else None

    @router.get("/board-fix-intake/context")
    async def intake_context(request: Request, session_id: str = ""):
        if not session_id:
            member = await authenticate_member(request, db)
            if member.get("review_mode"):
                raise HTTPException(status_code=401, detail="Please log in to your member account to open the Complete Board Fix intake")
            require_entitlement(member, {"board_fix_system"})
            existing = await db.board_fix_intakes.find_one({"user_id": member["user_id"]}, {"_id": 0})
            return {"eligible": True,
                    "lead_name": f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
                    "lead_organization": "",
                    "submitted": bool(existing and existing.get("submitted_at")),
                    "bylaws_filename": (existing or {}).get("bylaws_filename", ""),
                    "data": (existing or {}).get("data", {})}
        txn = await verify_session(session_id)
        if not txn:
            return {"eligible": False}
        existing = await db.board_fix_intakes.find_one({"session_id": session_id}, {"_id": 0})
        result = {"eligible": True, "lead_name": txn.get("lead_name", ""), "lead_organization": txn.get("lead_organization", ""),
                  "submitted": bool(existing and existing.get("submitted_at")),
                  "bylaws_filename": (existing or {}).get("bylaws_filename", ""),
                  "data": (existing or {}).get("data", {}),
                  "purchase_source": txn.get("purchase_source", "")}
        if txn.get("purchase_source") == FBB_PURCHASE_SOURCE:
            contact = {"name": txn.get("lead_name", ""), "email": txn.get("lead_email", "")}
            if not contact["email"]:
                try:
                    session = stripe.checkout.Session.retrieve(session_id)
                    details = getattr(session, "customer_details", None)
                    if details:
                        contact = {"name": details.get("name") or "", "email": details.get("email") or ""}
                except stripe.StripeError:
                    pass
            result["contact_prefill"] = contact
            result["account_linked"] = bool(txn.get("claimed_by_user_id"))
        return result

    @router.post("/board-fix-intake/submit")
    async def intake_submit(request: Request, payload: IntakeSubmit, response: Response):
        try:
            return await save_intake(request, payload, response)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Complete Board Fix intake save failed (mode=%s)", "session" if payload.session_id else "member")
            raise HTTPException(status_code=500, detail="We could not save your intake. Please try again.")

    async def send_login_details(email: str, first_name: str, temp_password: str, origin: str):
        resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
        login_link = f"{origin}/login"
        await resend.Emails.send_async({
            "from": os.environ["NONPROFIT_SENDER"], "to": [email],
            "subject": "Your Fundraising Board Builder Login Details",
            "html": (
                "<div style='max-width:560px;margin:auto;font-family:Arial,sans-serif;color:#000;line-height:1.6;'>"
                "<h2>Welcome to the Fundraising Board Builder</h2>"
                f"<p>Hi {html.escape(first_name)},</p>"
                "<p>Your customer account is ready. Use the details below to log in anytime:</p>"
                f"<p><strong>Login page:</strong> <a href='{login_link}'>{login_link}</a><br/>"
                f"<strong>Email:</strong> {html.escape(email)}<br/>"
                f"<strong>Temporary password:</strong> {html.escape(temp_password)}</p>"
                "<p>You can change your password anytime using the Forgot Password link on the login page.</p>"
                "<p>Rooney Akpesiri<br/>Nonprofit Board Builder</p></div>"),
        })

    async def ensure_fbb_account(payload: IntakeSubmit, response: Response):
        """Create or link the customer account for a Fundraising Board Builder purchase at intake submission."""
        email = payload.contact_email.strip().lower()
        name = payload.contact_name.strip()
        if not name or "@" not in email:
            raise HTTPException(status_code=422, detail="Enter your name and email so we can set up your customer account")
        from member_routes import claim_recruitment_purchase
        member = await db.members.find_one({"email": email})
        created = False
        temp_password = ""
        if not member:
            created = True
            temp_password = secrets.token_urlsafe(9)
            first, _, last = name.partition(" ")
            member = {
                "user_id": new_uuid(), "email": email,
                "first_name": first, "last_name": last.strip(),
                "password_hash": hash_member_password(temp_password),
                "entitlements": [], "lead_ids": [], "stripe_customer_id": "",
                "created_at": now_iso(), "updated_at": now_iso(),
            }
            await db.members.insert_one(member.copy())
        await claim_recruitment_purchase(db, member, payload.session_id)
        origin = payload.origin_url.rstrip("/") if payload.origin_url.startswith("http") else "https://nonprofitboardbuilder.com"
        if created:
            token = create_member_token(member["user_id"], email)
            set_member_cookie(response, token)
            try:
                await send_login_details(email, member["first_name"], temp_password, origin)
            except Exception:
                logger.exception("FBB login details email failed for %s", email)
        return ("created" if created else "existing"), member

    async def save_intake(request: Request, payload: IntakeSubmit, response: Response):
        is_fbb = False
        account_state = ""
        if not payload.session_id:
            member = await authenticate_member(request, db)
            if member.get("review_mode"):
                raise HTTPException(status_code=401, detail="Please log in to your member account to submit the Complete Board Fix intake")
            require_entitlement(member, {"board_fix_system"})
            user_id = member["user_id"]
            internal = bool(member.get("internal_admin_entitlement"))
            lead_email = member.get("email", "")
            is_dwm = False
            existing = await db.board_fix_intakes.find_one({"user_id": user_id}, {"_id": 0, "session_id": 1})
            storage_session = (existing or {}).get("session_id") or f"member-intake-{user_id}"
        else:
            txn = await verify_session(payload.session_id)
            if not txn:
                raise HTTPException(status_code=403, detail="A completed Complete Board Fix purchase is required")
            purchase = await db.purchases.find_one({"session_id": payload.session_id}, {"_id": 0, "user_id": 1})
            user_id = (purchase or {}).get("user_id", "")
            internal = False
            lead_email = txn.get("lead_email", "")
            is_dwm = txn.get("purchase_source") == DWM_PURCHASE_SOURCE
            is_fbb = txn.get("purchase_source") == FBB_PURCHASE_SOURCE
            storage_session = payload.session_id
            if is_fbb and not user_id:
                account_state, fbb_member = await ensure_fbb_account(payload, response)
                user_id = fbb_member["user_id"]
                lead_email = fbb_member["email"]
        if user_id:
            journey_set = {"experience": "do_it_with_me" if is_dwm else "self_guided"}
            if internal:
                journey_set["internal_preview"] = True
            await db.board_fix_journeys.update_one({"user_id": user_id}, {"$set": journey_set}, upsert=True)
        prior = await db.board_fix_intakes.find_one({"session_id": storage_session}, {"_id": 0, "submitted_at": 1})
        first_time = not (prior and prior.get("submitted_at"))
        await db.board_fix_intakes.update_one(
            {"session_id": storage_session},
            {"$set": {"data": payload.data, "user_id": user_id, "lead_email": lead_email,
                      "internal_preview": internal,
                      "submitted_at": now_iso(), "updated_at": now_iso()},
             "$setOnInsert": {"created_at": now_iso()}}, upsert=True)
        if user_id:
            seed = {}
            data = payload.data
            mapping = {
                "organization_name": data.get("organization_name", ""), "website": data.get("website", ""),
                "mission": data.get("mission", ""), "priorities": data.get("strategic_priorities", ""),
                "present_board": data.get("board_size", ""),
                "current_board_strengths": data.get("skills_represented", ""),
                "board_challenges": data.get("board_problems", ""),
            }
            profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data": 1}) or {}
            existing_data = profile.get("data", {})
            for key, value in mapping.items():
                if value and not existing_data.get(key):
                    seed[f"data.{key}"] = value
            if seed:
                seed["updated_at"] = now_iso()
                await db.recruitment_profiles.update_one({"user_id": user_id}, {"$set": seed, "$setOnInsert": {"created_at": now_iso()}}, upsert=True)
        if is_fbb:
            redirect = "/login?next=/app" if account_state == "existing" else "/app"
        elif is_dwm:
            redirect = CALENDLY_URL
        else:
            redirect = "/board-fix-orientation" if first_time else "/board-fix-roadmap"
        return {"status": "submitted", "redirect_url": redirect, "account_state": account_state}

    @router.post("/board-fix-intake/bylaws", status_code=201)
    async def upload_board_fix_bylaws(request: Request, session_id: str = Form(""), file: UploadFile = File(...)):
        """Optional bylaws document; stored against the intake. No AI/OCR runs — deterministic text extraction only."""
        if session_id:
            txn = await verify_session(session_id)
            if not txn:
                raise HTTPException(status_code=403, detail="A completed Complete Board Fix purchase is required")
            storage_session = session_id
        else:
            member = await authenticate_member(request, db)
            if member.get("review_mode"):
                raise HTTPException(status_code=401, detail="Please log in to your member account to upload your bylaws")
            require_entitlement(member, {"board_fix_system"})
            existing = await db.board_fix_intakes.find_one({"user_id": member["user_id"]}, {"_id": 0, "session_id": 1})
            if not existing:
                raise HTTPException(status_code=404, detail="Submit the intake form before uploading your bylaws")
            storage_session = existing["session_id"]
        name = file.filename or "bylaws"
        extension = os.path.splitext(name)[1].lower()
        if extension not in {".pdf", ".doc", ".docx"}:
            raise HTTPException(status_code=400, detail="Bylaws must be a PDF, DOC or DOCX file")
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Bylaws file is too large (10MB maximum)")
        intake = await db.board_fix_intakes.find_one({"session_id": storage_session}, {"_id": 0, "session_id": 1})
        if not intake:
            raise HTTPException(status_code=404, detail="Submit the intake form before uploading your bylaws")
        try:
            text = extract_cv_text(content, name)
        except Exception:
            logger.exception("Bylaws text extraction failed for %s", name)
            text = ""
        await db.board_fix_intakes.update_one(
            {"session_id": storage_session},
            {"$set": {"bylaws_filename": name, "bylaws_uploaded_at": now_iso(),
                      "data.bylaws_text": text[:120000], "updated_at": now_iso()}})
        return {"status": "uploaded", "filename": name}

    @router.get("/board-fix/master-intake")
    async def master_intake(request: Request):
        member = await authenticate_member(request, db)
        intake = await get_master_record(db, user_id=member["user_id"], email=member.get("email", ""))
        return {"data": (intake or {}).get("data", {}), "submitted_at": (intake or {}).get("submitted_at", "")}

    async def pathway_intake_status(user_id: str) -> dict:
        status = {}
        for key, collection in INTAKE_COLLECTIONS.items():
            doc = await db[collection].find_one(
                {"$or": [{"user_id": user_id}, {"session_id": synthetic_session(user_id)}],
                 "submitted_at": {"$exists": True}},
                {"_id": 0, "submitted_at": 1})
            status[key] = {"completed": bool(doc), "submitted_at": (doc or {}).get("submitted_at", "")}
        return status

    async def pathway_progress(user_id: str):
        pathways = []
        for key, label, product, modules in PATHWAYS:
            records = {r["module_number"]: r for r in await db.course_progress.find({"user_id": user_id, "product": product}, {"_id": 0}).to_list(20)}
            completed = [m["title"] for m in modules if records.get(m["number"], {}).get("completed")]
            remaining = [m["title"] for m in modules if not records.get(m["number"], {}).get("completed")]
            started = any(r.get("viewed") or r.get("completed") for r in records.values())
            pathways.append({"key": key, "label": label, "started": started,
                             "completed_steps": completed,
                             "module_states": [{"number": m["number"], "title": m["title"],
                                                "completed": bool(records.get(m["number"], {}).get("completed")),
                                                "viewed": bool(records.get(m["number"], {}).get("viewed"))} for m in modules],
                             "current_step": remaining[0] if remaining else "",
                             "next_step": remaining[1] if len(remaining) > 1 else "",
                             "done": bool(completed) and not remaining,
                             "percent": round(len(completed) / len(modules) * 100)})
        return pathways

    async def orientation_state(user_id: str) -> dict:
        journey = await db.board_fix_journeys.find_one({"user_id": user_id}, {"_id": 0}) or {}
        form = await db.reactivation_forms.find_one({"user_id": user_id}, {"_id": 0, "status": 1}) or {}
        return {
            "accessed": bool(journey.get("orientation_first_accessed_at")),
            "selections_saved": bool(journey.get("orientation_selections")),
            "selections": journey.get("orientation_selections", {}),
            "recommitment_form_status": form.get("status", "NONE"),
        }

    @router.get("/board-fix/orientation")
    async def get_orientation(request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {"board_fix_system"})
        now = now_iso()
        await db.board_fix_journeys.update_one(
            {"user_id": member["user_id"]},
            {"$set": {"orientation_last_accessed_at": now, "email": member.get("email", "")},
             "$min": {"orientation_first_accessed_at": now}}, upsert=True)
        return await orientation_state(member["user_id"])

    @router.post("/board-fix/orientation")
    async def save_orientation(payload: OrientationSelections, request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {"board_fix_system"})
        user_id = member["user_id"]
        now = now_iso()
        selections = {"step_off": payload.step_off, "advisory": payload.advisory, "saved_at": now}
        await db.board_fix_journeys.update_one(
            {"user_id": user_id},
            {"$set": {"orientation_selections": selections, "email": member.get("email", "")},
             "$min": {"orientation_first_accessed_at": now}}, upsert=True)
        transition_options = []
        if payload.advisory == "Yes":
            transition_options.append(ADVISORY_OPTION)
        if payload.step_off == "Yes":
            transition_options.append(STEP_OFF_OPTION)
        await db.board_reactivation_intakes.update_one(
            {"session_id": synthetic_session(user_id)},
            {"$set": {"transition_options": transition_options, "user_id": user_id, "updated_at": now},
             "$setOnInsert": {"created_at": now}}, upsert=True)
        return {"status": "saved", "transition_options": transition_options,
                "next_url": "/app/reactivation/self-guided/module/3"}

    async def ensure_recruitment_seed(user_id: str, member: dict) -> None:
        """BUF customers do not complete a second recruitment intake — seed it from the master intake."""
        existing_intake = await db.board_recruitment_intakes.find_one({"user_id": user_id}, {"_id": 0, "session_id": 1})
        if existing_intake:
            return
        master = await get_master_record(db, user_id=user_id, email=member.get("email", ""))
        if not master:
            return
        mapped = master_prefill("recruitment", master.get("data", {}) or {})
        if not mapped.get("organization_name"):
            return
        now = now_iso()
        contact_name = f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()
        await db.board_recruitment_intakes.update_one(
            {"session_id": synthetic_session(user_id)},
            {"$set": {**mapped, "session_id": synthetic_session(user_id), "user_id": user_id,
                      "your_name": contact_name, "email": member.get("email", ""),
                      "purchase_source": BOARD_FIX_SOURCE, "auto_seeded_from_master": True, "updated_at": now},
             "$setOnInsert": {"intake_id": str(uuid.uuid4()), "submitted_at": now}}, upsert=True)
        profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data": 1}) or {}
        merged = {**(profile.get("data", {}) or {})}
        for key, value in {
            "organization_name": mapped.get("organization_name", ""), "website": mapped.get("website", ""),
            "mission": mapped.get("mission", ""), "present_board": mapped.get("present_board", ""),
            "current_board_strengths": mapped.get("current_board_strengths", ""),
            "board_challenges": mapped.get("board_challenges", ""), "priorities": mapped.get("accomplish", ""),
            "specific_wants": mapped.get("specific_wants", ""),
            "contact_name": contact_name, "contact_email": member.get("email", ""),
        }.items():
            if value and not merged.get(key):
                merged[key] = value
        await db.recruitment_profiles.update_one(
            {"user_id": user_id},
            {"$set": {"data": merged, "updated_at": now}, "$setOnInsert": {"created_at": now}}, upsert=True)

    @router.get("/board-fix/roadmap")
    async def board_fix_roadmap(request: Request):
        member = await authenticate_member(request, db)
        require_entitlement(member, {"board_fix_system"})
        user_id = member["user_id"]
        now = now_iso()
        await db.board_fix_journeys.update_one(
            {"user_id": user_id},
            {"$set": {"roadmap_last_accessed_at": now, "email": member.get("email", "")},
             "$min": {"roadmap_first_accessed_at": now}}, upsert=True)
        master = await get_master_record(db, user_id=user_id, email=member.get("email", ""))
        if master:
            await ensure_recruitment_seed(user_id, member)
        intake_status = await pathway_intake_status(user_id)
        pathways = await pathway_progress(user_id)
        for pathway in pathways:
            status = intake_status[pathway["key"]]
            pathway["intake_completed"] = status["completed"]
            pathway["needs_intake"] = not status["completed"] and not pathway["started"]
        by_key = {p["key"]: p for p in pathways}
        orientation = await orientation_state(user_id)
        journey = []
        for stage in JOURNEY_STAGES:
            if stage["key"] == "orientation":
                journey.append({"key": "orientation", "label": stage["label"],
                                "done": orientation["selections_saved"] or orientation["recommitment_form_status"] != "NONE",
                                "started": orientation["accessed"], "current_step": "", "next_step": "",
                                "completed_steps": [], "percent": 100 if orientation["selections_saved"] else 0,
                                "needs_intake": False, "pathway": ""})
                continue
            pathway = by_key[stage["pathway"]]
            states = [m for m in pathway["module_states"] if not stage["modules"] or m["number"] in stage["modules"]]
            completed = [m for m in states if m["completed"]]
            remaining = [m for m in states if not m["completed"]]
            journey.append({
                "key": stage["key"], "label": stage["label"], "pathway": stage["pathway"],
                "done": bool(completed) and not remaining,
                "started": any(m["viewed"] or m["completed"] for m in states),
                "current_step": remaining[0]["title"] if remaining else "",
                "current_module": remaining[0]["number"] if remaining else states[-1]["number"],
                "next_step": remaining[1]["title"] if len(remaining) > 1 else "",
                "completed_steps": [m["title"] for m in completed],
                "percent": round(len(completed) / len(states) * 100) if states else 0,
                "needs_intake": pathway["needs_intake"] if INTAKE_STAGE_KEYS.get(stage["key"]) else False,
            })
        return {"master_intake_submitted": bool(master and master.get("submitted_at")),
                "orientation": orientation, "journey": journey, "pathways": pathways}

    async def pathway_resources(user_id: str) -> dict:
        materials = await db.generated_materials.find(
            {"user_id": user_id}, {"_id": 0, "type": 1, "title": 1, "status": 1, "updated_at": 1}).to_list(400)
        resources = {
            "recruitment": [{"title": m.get("title", m.get("type", "")), "status": m.get("status", ""), "updated_at": m.get("updated_at", "")}
                            for m in materials if not str(m.get("type", "")).startswith("reactivation_")],
            "reactivation": [{"title": m.get("title", m.get("type", "")), "status": m.get("status", ""), "updated_at": m.get("updated_at", "")}
                             for m in materials if str(m.get("type", "")).startswith("reactivation_")],
            "activation": [],
        }
        planning_form = await db.activation_planning_forms.find_one({"user_id": user_id}, {"_id": 0, "updated_at": 1})
        if planning_form:
            resources["activation"].append({"title": "Fundraising Planning Form", "status": "Created", "updated_at": planning_form.get("updated_at", "")})
        strategy = await db.activation_strategies.find_one({"user_id": user_id}, {"_id": 0, "status": 1, "updated_at": 1})
        if strategy:
            resources["activation"].append({"title": "Fundraising Strategy", "status": strategy.get("status", "Created"), "updated_at": strategy.get("updated_at", "")})
        toolkit = await db.activation_toolkits.find_one({"user_id": user_id}, {"_id": 0, "status": 1, "updated_at": 1})
        if toolkit:
            resources["activation"].append({"title": "Board Fundraising Toolkit", "status": toolkit.get("status", "Created"), "updated_at": toolkit.get("updated_at", "")})
        return resources

    async def pathway_status_lines(user_id: str) -> dict:
        opportunity = await db.opportunities.find_one({"user_id": user_id}, {"_id": 0, "status": 1, "published_at": 1})
        if opportunity and opportunity.get("status") == "Published":
            recruitment = f"Campaign published {str(opportunity.get('published_at', ''))[:10]}"
        elif opportunity:
            recruitment = f"Campaign {opportunity.get('status', 'Draft').lower()} — not launched"
        else:
            recruitment = "Campaign not created"
        roster = await db.reactivation_board_members.count_documents({"user_id": user_id})
        reactivation = f"{roster} board member{'s' if roster != 1 else ''} on the reactivation roster" if roster else "Reactivation roster not started"
        participants = await db.activation_participants.count_documents({"user_id": user_id})
        activation = f"{participants} board participant{'s' if participants != 1 else ''} engaged" if participants else "No board participants engaged yet"
        return {"recruitment": recruitment, "reactivation": reactivation, "activation": activation}

    def compute_next_action(row: dict) -> str:
        if not row["paid"]:
            if row["payment"]:
                return "Complete the checkout"
            if row["form"]:
                return "Visit the sales page and purchase"
            return "Submit the initial form"
        if not row["intake"]:
            return "Complete the master intake"
        if not row.get("roadmap_accessed_at"):
            return "Open the Board Fix roadmap"
        unfinished = [p for p in row["pathways"] if not p["done"]]
        if not unfinished:
            return "All pathways completed"
        active = next((p for p in unfinished if p["started"]), unfinished[0])
        if not active["started"] and not active.get("intake_completed"):
            return f"{active['label']}: complete the pathway intake"
        return f"{active['label']}: {active['current_step'] or 'Continue'}"

    async def board_fix_steps(user_id: str) -> dict:
        journey = await db.board_fix_journeys.find_one({"user_id": user_id}, {"_id": 0}) or {}
        form = await db.reactivation_forms.find_one({"user_id": user_id}, {"_id": 0, "status": 1, "approved_at": 1}) or {}
        roster_total = await db.reactivation_board_members.count_documents({"user_id": user_id})
        responses = await db.reactivation_board_members.count_documents({"user_id": user_id, "status": "COMPLETED"})
        interpretations = await db.generated_materials.count_documents(
            {"user_id": user_id, "type": "reactivation_response_analysis", "status": {"$nin": ["Failed"]}})
        summary = await db.generated_materials.find_one(
            {"user_id": user_id, "type": "reactivation_board_summary"}, {"_id": 0, "status": 1, "updated_at": 1})
        conversations = await db.generated_materials.count_documents(
            {"user_id": user_id, "type": "reactivation_conversation_script"})
        recruited = await db.opportunity_applications.count_documents(
            {"owner_user_id": user_id, "$or": [{"final_outcome": "Joined Board"}, {"status": "Selected"}]})
        return {
            "orientation_accessed_at": journey.get("orientation_first_accessed_at", ""),
            "orientation_selections": journey.get("orientation_selections", {}),
            "recommitment_form_status": form.get("status", "NONE"),
            "board_members_on_roster": roster_total,
            "responses_received": responses,
            "interpretations_generated": interpretations,
            "board_summary_status": (summary or {}).get("status", "NONE"),
            "conversation_scripts": conversations,
            "board_members_recruited": recruited,
        }

    @router.post("/admin/board-fix/preview-access")
    async def admin_preview_access(request: Request, response: Response):
        """Super-Admin-only: auto-provision the admin's member identity with the normal Complete entitlement (no Stripe)."""
        admin = await authenticate_admin(request, db)
        email = (admin.get("email") or "").lower()
        now = now_iso()
        member = await db.members.find_one({"email": email}, {"_id": 0, "user_id": 1})
        if member:
            user_id = member["user_id"]
        else:
            admin_user = await db.users.find_one({"email": email}, {"_id": 0, "password_hash": 1})
            if not admin_user or not admin_user.get("password_hash"):
                raise HTTPException(status_code=500, detail="Your admin account record could not be loaded to provision member access. Please try again.")
            user_id = str(uuid.uuid4())
            first_name = (email.split("@")[0] or "Member").split(".")[0].capitalize()
            await db.members.insert_one({
                "user_id": user_id, "email": email,
                "password_hash": admin_user["password_hash"],
                "first_name": first_name, "last_name": "",
                "entitlements": [], "lead_ids": [], "stripe_customer_id": "",
                "created_at": now, "updated_at": now,
            })
        await db.members.update_one(
            {"user_id": user_id},
            {"$addToSet": {"entitlements": {"$each": PREVIEW_ENTITLEMENTS}},
             "$set": {"internal_admin_entitlement": True, "updated_at": now}})
        await db.board_fix_journeys.update_one(
            {"user_id": user_id},
            {"$set": {"internal_preview": True, "email": email}}, upsert=True)
        set_member_cookie(response, create_member_token(user_id, email))
        return {"intake_url": "/board-fix-intake", "member_email": email}

    @router.post("/admin/board-fix/activation-preview-access")
    async def admin_activation_preview_access(request: Request, response: Response):
        """Super-Admin-only: provision the admin's member identity with ONLY the Fundraising Activation entitlement (no Stripe)."""
        admin = await authenticate_admin(request, db)
        email = (admin.get("email") or "").lower()
        now = now_iso()
        member = await db.members.find_one({"email": email}, {"_id": 0, "user_id": 1})
        if member:
            user_id = member["user_id"]
        else:
            admin_user = await db.users.find_one({"email": email}, {"_id": 0, "password_hash": 1})
            if not admin_user or not admin_user.get("password_hash"):
                raise HTTPException(status_code=500, detail="Your admin account record could not be loaded to provision member access. Please try again.")
            user_id = str(uuid.uuid4())
            first_name = (email.split("@")[0] or "Member").split(".")[0].capitalize()
            await db.members.insert_one({
                "user_id": user_id, "email": email,
                "password_hash": admin_user["password_hash"],
                "first_name": first_name, "last_name": "",
                "entitlements": [], "lead_ids": [], "stripe_customer_id": "",
                "created_at": now, "updated_at": now,
            })
        await db.members.update_one(
            {"user_id": user_id},
            {"$set": {"entitlements": ["activation_self_guided"], "internal_admin_entitlement": True, "updated_at": now}})
        set_member_cookie(response, create_member_token(user_id, email))
        return {"intake_url": "/board-activation-intake?bf=1", "member_email": email}

    @router.get("/admin/board-fix/customers")
    async def admin_customers(request: Request):
        await authenticate_admin(request, db)
        leads = await db.funnel_leads.find({"offer_source": "board_fix"}, {"_id": 0}).sort("created_at", -1).to_list(300)
        txns = await db.payment_transactions.find({"offer_source": "board_fix_system"}, {"_id": 0}).to_list(300)
        intakes = await db.board_fix_intakes.find({"internal_preview": {"$ne": True}}, {"_id": 0}).to_list(300)
        purchases = await db.purchases.find({"purchase_source": {"$in": PURCHASE_SOURCES}}, {"_id": 0}).to_list(300)
        journeys = {j["user_id"]: j for j in await db.board_fix_journeys.find({}, {"_id": 0}).to_list(300)}
        customers = {}

        def record(email):
            email = (email or "").lower()
            if not email:
                return None
            return customers.setdefault(email, {"email": email, "name": "", "organization": "", "form": None, "paid": False,
                                                "payment": None, "intake": None, "member_user_id": "", "pathways": [],
                                                "purchase": None, "roadmap_accessed_at": "", "next_action": "",
                                                "board_fix_steps": None,
                                                "status": "", "last_activity": ""})

        for lead in leads:
            row = record(lead.get("email"))
            if row is not None:
                row["name"] = row["name"] or lead.get("name", "")
                row["organization"] = row["organization"] or lead.get("organization", "")
                row["form"] = {"submitted_at": lead.get("created_at", ""), "answers": lead.get("answers", {})}
                row["last_activity"] = max(row["last_activity"], lead.get("created_at", ""))
        for txn in txns:
            row = record(txn.get("lead_email"))
            if row is not None:
                row["payment"] = {"session_id": txn.get("session_id", ""), "amount": txn.get("amount", 0),
                                  "payment_status": txn.get("payment_status", ""), "created_at": txn.get("created_at", "")}
                row["paid"] = row["paid"] or txn.get("payment_status") == "paid"
                row["last_activity"] = max(row["last_activity"], txn.get("updated_at", txn.get("created_at", "")))
        user_emails = {}
        for purchase in purchases:
            member = await db.members.find_one({"user_id": purchase.get("user_id", "")}, {"_id": 0, "email": 1, "first_name": 1, "last_name": 1})
            if member:
                user_emails[purchase["user_id"]] = member["email"]
                row = record(member["email"])
                if row is not None:
                    row["paid"] = True
                    row["member_user_id"] = purchase["user_id"]
                    row["name"] = row["name"] or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()
                    row["purchase"] = {"product": purchase.get("product", ""), "purchased_at": purchase.get("purchased_at", ""),
                                       "amount": purchase.get("amount", 0)}
        for intake in intakes:
            email = intake.get("lead_email") or user_emails.get(intake.get("user_id", ""), "")
            row = record(email)
            if row is not None:
                row["intake"] = {"submitted_at": intake.get("submitted_at", ""), "data": intake.get("data", {})}
                row["member_user_id"] = row["member_user_id"] or intake.get("user_id", "")
                row["last_activity"] = max(row["last_activity"], intake.get("updated_at", ""))
        overview = {"form_submitted": 0, "checkout_started": 0, "paid": 0, "intake_completed": 0, "onboarding": 0,
                    "recruitment": 0, "reactivation": 0, "activation": 0, "completed": 0}
        for row in customers.values():
            if row["member_user_id"]:
                row["pathways"] = await pathway_progress(row["member_user_id"])
                intake_status = await pathway_intake_status(row["member_user_id"])
                resources = await pathway_resources(row["member_user_id"])
                status_lines = await pathway_status_lines(row["member_user_id"])
                for pathway in row["pathways"]:
                    status = intake_status[pathway["key"]]
                    pathway["intake_completed"] = status["completed"]
                    pathway["intake_submitted_at"] = status["submitted_at"]
                    pathway["resources"] = resources[pathway["key"]]
                    pathway["status_line"] = status_lines[pathway["key"]]
                journey = journeys.get(row["member_user_id"], {})
                row["roadmap_accessed_at"] = journey.get("roadmap_first_accessed_at", "")
                row["experience"] = journey.get("experience", "")
                row["board_fix_steps"] = await board_fix_steps(row["member_user_id"])
            started = [p for p in row["pathways"] if p["started"]]
            if row["form"]:
                overview["form_submitted"] += 1
            if row["payment"]:
                overview["checkout_started"] += 1
            if row["paid"]:
                overview["paid"] += 1
            if row["intake"]:
                overview["intake_completed"] += 1
            if row["intake"] and not started:
                overview["onboarding"] += 1
            for pathway in started:
                overview[pathway["key"]] += 1
            if row["pathways"] and all(p["done"] for p in row["pathways"]):
                overview["completed"] += 1
                row["status"] = "Completed"
            elif started:
                active = started[-1]
                row["status"] = f"{active['label']} → {active['current_step'] or 'Completed'}"
            elif row["intake"]:
                row["status"] = "Onboarding"
            elif row["paid"]:
                row["status"] = "Paid — Intake Pending"
            elif row["payment"]:
                row["status"] = "Checkout Initiated"
            elif row["form"]:
                row["status"] = "Form Submitted"
            row["next_action"] = compute_next_action(row)
        rows = sorted(customers.values(), key=lambda r: r["last_activity"], reverse=True)
        homepage_visits = await db.funnel_page_views.count_documents({"page": "homepage"})
        video_views = await db.funnel_video_views.count_documents({"offer": "board-fix"})
        paid_txns = [t for t in txns if t.get("payment_status") == "paid"]
        purchases_homepage = sum(1 for t in paid_txns if t.get("lead_id"))
        purchases_direct = len(paid_txns) - purchases_homepage
        journey_started = await db.board_fix_journeys.count_documents(
            {"internal_preview": {"$ne": True},
             "$or": [{"roadmap_first_accessed_at": {"$exists": True, "$ne": ""}},
                     {"orientation_first_accessed_at": {"$exists": True, "$ne": ""}}]})
        funnel_report = {
            "homepage_visits": homepage_visits,
            "form_submits": len(leads),
            "video_views": video_views,
            "paid": overview["paid"],
            "journey_started": journey_started,
            "purchases_homepage_funnel": purchases_homepage,
            "purchases_direct_or_unattributed": purchases_direct,
        }
        return {"customers": rows, "overview": overview, "funnel_report": funnel_report}

    return router
