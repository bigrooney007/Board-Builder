"""Admin service-delivery routes: DWM client directory + operator workspaces."""
import logging
import os
import uuid
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from auth_service import authenticate_admin

logger = logging.getLogger(__name__)

DWM_OFFERS = {
    "direct_board_recruitment_project": {
        "product": "recruitment", "offer": "Board Recruitment Project ($1,997)",
        "entitlement": "recruitment_self_guided", "intake_collection": "board_recruitment_intakes",
        "entry_route": "/app/recruitment/self-guided/module/1",
    },
    "direct_board_reactivation_project": {
        "product": "reactivation", "offer": "Board Reactivation Project ($1,997)",
        "entitlement": "reactivation_self_guided", "intake_collection": "board_reactivation_intakes",
        "entry_route": "/app/reactivation/self-guided/module/1",
    },
    "direct_board_activation_project_2497": {
        "product": "activation", "offer": "Board Activation Project ($2,497)",
        "entitlement": "activation_self_guided", "intake_collection": "board_activation_intakes",
        "entry_route": "/app/activation/self-guided/module/1",
    },
    "board_reactivation_dfy": {
        "product": "reactivation", "offer": "Board Reactivation — Done For You ($997)",
        "entitlement": "reactivation_self_guided", "intake_collection": "board_reactivation_intakes",
        "entry_route": "/app/reactivation/self-guided/module/1",
    },
    "board_recruitment_dfy": {
        "product": "recruitment", "offer": "Board Recruitment — Done For You ($997)",
        "entitlement": "recruitment_self_guided", "intake_collection": "board_recruitment_intakes",
        "entry_route": "/app/recruitment/self-guided/module/1",
    },
    "board_fundraising_activation_dfy": {
        "product": "activation", "offer": "Board Fundraising Activation — Done For You ($997)",
        "entitlement": "activation_self_guided", "intake_collection": "board_activation_intakes",
        "entry_route": "/app/activation/self-guided/module/1",
    },
    "recruitment_campaign_launch_697": {
        "product": "recruitment", "engagement_type": "recruitment_campaign_launch",
        "offer": "Recruitment Campaign Launch ($697)",
        "entitlement": "recruitment_self_guided", "intake_collection": "board_recruitment_intakes",
        "entry_route": "/app/recruitment/self-guided/module/2",
    },
    "activate_my_board_with_rooney_2997": {
        "product": "activation", "offer": "Activate My Board With Rooney ($2,997)",
        "entitlement": "activation_self_guided", "intake_collection": "board_activation_intakes",
        "entry_route": "/app/activation/self-guided/module/1",
    },
}

ENGAGEMENT_STATUSES = {"Active", "Paused", "Completed"}
MEETING_STATUSES = {"Not Booked", "Booking Link Sent", "Booked"}


def create_admin_service_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/admin")

    async def intake_for(session_id: str, collection: str) -> dict:
        return await db[collection].find_one({"session_id": session_id}, {"_id": 0}) or {}

    @router.get("/dwm-clients")
    async def dwm_clients(request: Request):
        await authenticate_admin(request, db)
        pending = await db.payment_transactions.find(
            {"purchase_source": {"$in": list(DWM_OFFERS.keys())}, "payment_status": {"$ne": "paid"}},
            {"_id": 0, "session_id": 1}).sort("created_at", -1).to_list(15)
        if pending:
            stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
            for row in pending:
                try:
                    session = stripe.checkout.Session.retrieve(row["session_id"])
                    if session.payment_status == "paid" or session.status == "complete":
                        await db.payment_transactions.update_one(
                            {"session_id": row["session_id"], "payment_status": {"$ne": "paid"}},
                            {"$set": {"payment_status": "paid", "status": "completed", "updated_at": datetime.now(timezone.utc).isoformat()}})
                except Exception:
                    continue
        transactions = await db.payment_transactions.find(
            {"purchase_source": {"$in": list(DWM_OFFERS.keys())}, "payment_status": "paid"},
            {"_id": 0}).sort("created_at", -1).to_list(500)
        clients = []
        for tx in transactions:
            meta = DWM_OFFERS[tx["purchase_source"]]
            session_id = tx.get("session_id", "")
            intake = await intake_for(session_id, meta["intake_collection"])
            workspace = await db.members.find_one(
                {"operator_workspace": True, "workspace_session_id": session_id},
                {"_id": 0, "user_id": 1, "organization_name": 1})
            clients.append({
                "session_id": session_id,
                "product": meta["product"],
                "offer": meta["offer"],
                "engagement_type": meta.get("engagement_type", meta["product"]),
                "purchase_date": tx.get("created_at", ""),
                "founder_name": intake.get("your_name", "") or intake.get("full_name", "") or tx.get("lead_name", ""),
                "founder_email": intake.get("your_email", "") or intake.get("email", "") or tx.get("email", "") or tx.get("lead_email", ""),
                "organization_name": intake.get("organization_name", "") or tx.get("lead_organization", ""),
                "intake_status": "Completed" if intake else "Not Started",
                "engagement_status": tx.get("dfy_engagement_status", "Active"),
                "first_meeting": tx.get("dfy_first_meeting", "Not Booked"),
                "current_step": tx.get("dfy_current_step", ""),
                "workspace_status": "Open" if workspace else "Not Started",
                "workspace_user_id": (workspace or {}).get("user_id", ""),
                "entry_route": meta["entry_route"],
            })
        return {"clients": clients}

    @router.get("/dwm-clients/{session_id}/intake")
    async def dwm_client_intake(session_id: str, request: Request):
        await authenticate_admin(request, db)
        tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0, "purchase_source": 1})
        if not tx or tx.get("purchase_source") not in DWM_OFFERS:
            raise HTTPException(status_code=404, detail="Client not found")
        meta = DWM_OFFERS[tx["purchase_source"]]
        intake = await db[meta["intake_collection"]].find_one({"session_id": session_id}, {"_id": 0})
        if not intake:
            raise HTTPException(status_code=404, detail="This client has not completed their intake yet")
        return {"offer": meta["offer"], "intake_collection": meta["intake_collection"], "intake": intake}

    class ClientStatusUpdate(BaseModel):
        engagement_status: str = ""
        first_meeting: str = ""
        current_step: Optional[str] = None

    @router.patch("/dwm-clients/{session_id}")
    async def update_client_status(session_id: str, payload: ClientStatusUpdate, request: Request):
        await authenticate_admin(request, db)
        updates = {}
        if payload.engagement_status:
            if payload.engagement_status not in ENGAGEMENT_STATUSES:
                raise HTTPException(status_code=422, detail="Unknown engagement status")
            updates["dfy_engagement_status"] = payload.engagement_status
        if payload.first_meeting:
            if payload.first_meeting not in MEETING_STATUSES:
                raise HTTPException(status_code=422, detail="Unknown meeting status")
            updates["dfy_first_meeting"] = payload.first_meeting
        if payload.current_step is not None:
            updates["dfy_current_step"] = payload.current_step[:200]
        if not updates:
            return {"status": "ok"}
        result = await db.payment_transactions.update_one(
            {"session_id": session_id, "purchase_source": {"$in": list(DWM_OFFERS.keys())}}, {"$set": updates})
        if not result.matched_count:
            raise HTTPException(status_code=404, detail="Client not found")
        return {"status": "ok"}

    @router.post("/dwm-clients/{session_id}/workspace")
    async def open_workspace(session_id: str, request: Request):
        await authenticate_admin(request, db)
        tx = await db.payment_transactions.find_one(
            {"session_id": session_id, "purchase_source": {"$in": list(DWM_OFFERS.keys())}, "payment_status": "paid"},
            {"_id": 0})
        if not tx:
            raise HTTPException(status_code=404, detail="No verified Do-With-You purchase found for this client")
        meta = DWM_OFFERS[tx["purchase_source"]]
        existing = await db.members.find_one(
            {"operator_workspace": True, "workspace_session_id": session_id}, {"_id": 0, "password_hash": 0})
        if existing:
            return {"status": "exists", "workspace": _workspace_view(existing, meta)}
        intake = await intake_for(session_id, meta["intake_collection"])
        now = datetime.now(timezone.utc).isoformat()
        user_id = f"dwm-{uuid.uuid4()}"
        founder_name = (intake.get("your_name", "") or intake.get("full_name", "") or "Client Founder").strip()
        parts = founder_name.split(" ", 1)
        member = {
            "user_id": user_id,
            "email": f"dwm+{session_id[-24:].lower()}@nonprofitboardbuilder.internal",
            "first_name": parts[0], "last_name": parts[1] if len(parts) > 1 else "",
            "password_hash": "!operator-workspace-no-login",
            "entitlements": [meta["entitlement"]],
            "operator_workspace": True,
            "workspace_session_id": session_id,
            "workspace_product": meta["product"],
            "organization_name": intake.get("organization_name", ""),
            "client_founder_email": intake.get("your_email", "") or intake.get("email", ""),
            "purchase_source": tx["purchase_source"],
            "created_at": now,
        }
        await db.members.insert_one({**member})
        if intake:
            await db[meta["intake_collection"]].update_one(
                {"session_id": session_id}, {"$set": {"user_id": user_id}})
        member.pop("password_hash", None)
        return {"status": "created", "workspace": _workspace_view(member, meta)}

    def _workspace_view(member: dict, meta: dict) -> dict:
        return {
            "user_id": member["user_id"],
            "organization_name": member.get("organization_name", ""),
            "product": meta["product"],
            "entry_route": meta["entry_route"],
        }

    return router
