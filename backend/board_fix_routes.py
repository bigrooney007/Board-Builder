"""Complete Board Fix: post-payment intake, master customer record, roadmap prefill, admin journey view."""
import os
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth_service import authenticate_admin
from course_content import ACTIVATION_MODULES, REACTIVATION_MODULES, SELF_GUIDED_MODULES
from member_auth import authenticate_member

PURCHASE_SOURCE = "board_fix_system_497"

PATHWAYS = [
    ("recruitment", "Board Recruitment", "recruitment_self_guided", SELF_GUIDED_MODULES),
    ("reactivation", "Board Reactivation", "reactivation_self_guided", REACTIVATION_MODULES),
    ("activation", "Board Fundraising Activation", "activation_self_guided", ACTIVATION_MODULES),
]


class IntakeSubmit(BaseModel):
    session_id: str = Field(min_length=1)
    data: dict


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_board_fix_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    async def verify_session(session_id: str):
        txn = await db.payment_transactions.find_one({"session_id": session_id, "purchase_source": PURCHASE_SOURCE}, {"_id": 0})
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
    async def intake_context(session_id: str = ""):
        txn = await verify_session(session_id)
        if not txn:
            return {"eligible": False}
        existing = await db.board_fix_intakes.find_one({"session_id": session_id}, {"_id": 0})
        return {"eligible": True, "lead_name": txn.get("lead_name", ""), "lead_organization": txn.get("lead_organization", ""),
                "submitted": bool(existing and existing.get("submitted_at")), "data": (existing or {}).get("data", {})}

    @router.post("/board-fix-intake/submit")
    async def intake_submit(payload: IntakeSubmit):
        txn = await verify_session(payload.session_id)
        if not txn:
            raise HTTPException(status_code=403, detail="A completed Complete Board Fix purchase is required")
        purchase = await db.purchases.find_one({"session_id": payload.session_id}, {"_id": 0, "user_id": 1})
        user_id = (purchase or {}).get("user_id", "")
        await db.board_fix_intakes.update_one(
            {"session_id": payload.session_id},
            {"$set": {"data": payload.data, "user_id": user_id, "lead_email": txn.get("lead_email", ""),
                      "submitted_at": now_iso(), "updated_at": now_iso()},
             "$setOnInsert": {"created_at": now_iso()}}, upsert=True)
        if user_id:
            seed = {}
            data = payload.data
            mapping = {
                "organization_name": data.get("organization_name", ""), "website": data.get("website", ""),
                "mission": data.get("mission", ""), "priorities": data.get("strategic_priorities", ""),
                "present_board": data.get("board_size", ""),
            }
            profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data": 1}) or {}
            existing_data = profile.get("data", {})
            for key, value in mapping.items():
                if value and not existing_data.get(key):
                    seed[f"data.{key}"] = value
            if seed:
                seed["updated_at"] = now_iso()
                await db.recruitment_profiles.update_one({"user_id": user_id}, {"$set": seed, "$setOnInsert": {"created_at": now_iso()}}, upsert=True)
        return {"status": "submitted", "redirect_url": "/board-fix-roadmap"}

    @router.get("/board-fix/master-intake")
    async def master_intake(request: Request):
        member = await authenticate_member(request, db)
        intake = await db.board_fix_intakes.find_one({"user_id": member["user_id"]}, {"_id": 0})
        if not intake:
            intake = await db.board_fix_intakes.find_one({"lead_email": member["email"]}, {"_id": 0})
        return {"data": (intake or {}).get("data", {}), "submitted_at": (intake or {}).get("submitted_at", "")}

    async def pathway_progress(user_id: str):
        pathways = []
        for key, label, product, modules in PATHWAYS:
            records = {r["module_number"]: r for r in await db.course_progress.find({"user_id": user_id, "product": product}, {"_id": 0}).to_list(20)}
            completed = [m["title"] for m in modules if records.get(m["number"], {}).get("completed")]
            current = next((m["title"] for m in modules if not records.get(m["number"], {}).get("completed")), "")
            started = any(r.get("viewed") or r.get("completed") for r in records.values())
            pathways.append({"key": key, "label": label, "started": started,
                             "completed_steps": completed, "current_step": current if started else "",
                             "done": bool(completed) and not current,
                             "percent": round(len(completed) / len(modules) * 100)})
        return pathways

    @router.get("/admin/board-fix/customers")
    async def admin_customers(request: Request):
        await authenticate_admin(request, db)
        leads = await db.funnel_leads.find({"offer_source": "board_fix"}, {"_id": 0}).sort("created_at", -1).to_list(300)
        txns = await db.payment_transactions.find({"offer_source": "board_fix_system"}, {"_id": 0}).to_list(300)
        intakes = await db.board_fix_intakes.find({}, {"_id": 0}).to_list(300)
        purchases = await db.purchases.find({"purchase_source": PURCHASE_SOURCE}, {"_id": 0}).to_list(300)
        customers = {}

        def record(email):
            email = (email or "").lower()
            if not email:
                return None
            return customers.setdefault(email, {"email": email, "name": "", "organization": "", "form": None, "paid": False,
                                                "payment": None, "intake": None, "member_user_id": "", "pathways": [],
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
        for intake in intakes:
            email = intake.get("lead_email") or user_emails.get(intake.get("user_id", ""), "")
            row = record(email)
            if row is not None:
                row["intake"] = {"submitted_at": intake.get("submitted_at", ""), "data": intake.get("data", {})}
                row["member_user_id"] = row["member_user_id"] or intake.get("user_id", "")
                row["last_activity"] = max(row["last_activity"], intake.get("updated_at", ""))
        overview = {"form_submitted": 0, "paid": 0, "intake_completed": 0, "onboarding": 0,
                    "recruitment": 0, "reactivation": 0, "activation": 0, "completed": 0}
        for row in customers.values():
            if row["member_user_id"]:
                row["pathways"] = await pathway_progress(row["member_user_id"])
            started = [p for p in row["pathways"] if p["started"]]
            if row["form"]:
                overview["form_submitted"] += 1
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
            elif row["form"]:
                row["status"] = "Form Submitted"
        rows = sorted(customers.values(), key=lambda r: r["last_activity"], reverse=True)
        return {"customers": rows, "overview": overview}

    return router
