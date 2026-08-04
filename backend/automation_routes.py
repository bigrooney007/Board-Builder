from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from automation_service import record_action


class TrackedActionRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)


def create_automation_router(db) -> APIRouter:
    router = APIRouter(prefix="/api/tracked-actions")

    @router.post("/{action_type}")
    async def track_action(action_type: str, payload: TrackedActionRequest):
        if action_type not in {"board-transformation-ready", "available-to-serve"}:
            raise HTTPException(status_code=404, detail="Tracked action not found")
        result = await record_action(db, action_type, payload.token)
        if not result:
            raise HTTPException(status_code=404, detail="This secure action link is invalid or expired")
        return result

    return router