"""Admin service-delivery routes: DWM client directory + operator workspaces."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

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
}


def create_admin_service_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/admin")

    async def intake_for(session_id: str, collection: str) -> dict:
        return await db[collection].find_one({"session_id": session_id}, {"_id": 0}) or {}

    @router.get("/dwm-clients")
    async def dwm_clients(request: Request):
        await authenticate_admin(request, db)
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
                "purchase_date": tx.get("created_at", ""),
                "founder_name": intake.get("your_name", "") or intake.get("full_name", ""),
                "founder_email": intake.get("your_email", "") or intake.get("email", "") or tx.get("email", ""),
                "organization_name": intake.get("organization_name", ""),
                "intake_status": "Completed" if intake else "Not Completed",
                "workspace_status": "Open" if workspace else "Not Started",
                "workspace_user_id": (workspace or {}).get("user_id", ""),
                "entry_route": meta["entry_route"],
            })
        return {"clients": clients}

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
