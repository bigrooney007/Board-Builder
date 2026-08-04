import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from email_service import send_owner_assessment_email
from applicant_routes import create_applicant_router
from auth_service import seed_admin
from resend_service import sync_nonprofit_leader


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Nonprofit Board Builder")
api_router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


class BoardAssessmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    email: EmailStr
    phone: str = Field(min_length=1)
    organization_name: str = Field(min_length=1)
    website: Optional[str] = ""
    mission: str = Field(min_length=1)
    city: str = Field(min_length=1)
    state_region: str = Field(min_length=1)
    country: str = Field(min_length=1)
    annual_budget: str = Field(min_length=1)
    most_important_board_result: str = Field(min_length=1)

    bylaws_board_size: str = Field(min_length=1)
    current_board_size: str = Field(min_length=1)
    active_board_members: str = Field(min_length=1)
    inactive_board_members: str = Field(min_length=1)
    present_board_condition: List[str] = Field(min_length=1)
    board_type: str = Field(min_length=1)
    commitment_conversations: str = Field(min_length=1)
    willing_to_allow_step_down: str = Field(min_length=1)
    bylaw_clarity: str = Field(min_length=1)

    new_board_members_needed: str = Field(min_length=1)
    recruitment_timeline: str = Field(min_length=1)
    areas_carried_alone: List[str] = Field(min_length=1)
    missing_skills_networks: str = Field(min_length=1)
    expected_new_member_benefit: str = Field(min_length=1)
    people_already_identified: str = Field(min_length=1)
    benefits_of_joining: str = Field(min_length=1)
    previous_recruitment_experience: str = Field(min_length=1)

    present_fundraising_involvement: str = Field(min_length=1)
    board_support_areas: List[str] = Field(min_length=1)
    written_fundraising_strategy: str = Field(min_length=1)
    individual_responsibilities: str = Field(min_length=1)
    board_participation_in_planning: str = Field(min_length=1)
    missing_fundraising_elements: List[str] = Field(min_length=1)
    desired_result: str = Field(min_length=1)
    support_required: str = Field(min_length=1)
    additional_information: Optional[str] = ""
    confirmation_accepted: bool
    marketing_consent: bool = False


class AssessmentResponse(BaseModel):
    assessment_number: str
    organization_name: str
    submitted_email: EmailStr
    submitted_at: str
    status: str
    email_sent: bool


def make_assessment_number(now: datetime) -> str:
    return f"NBB-{now.strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"


@api_router.get("/")
async def root():
    return {"message": "Nonprofit Board Builder API"}


@api_router.post("/assessments", response_model=AssessmentResponse, status_code=201)
async def create_assessment(payload: BoardAssessmentCreate):
    now = datetime.now(timezone.utc)
    assessment_number = make_assessment_number(now)
    document = payload.model_dump(mode="json")
    document.update(
        {
            "assessment_number": assessment_number,
            "submitted_at": now.isoformat(),
            "status": "New Board Assessment",
            "owner_email_status": "Pending",
            "marketing_consent_at": now.isoformat() if payload.marketing_consent else "",
            "marketing_resend_status": "Pending" if payload.marketing_consent else "Not Requested",
        }
    )

    await db.board_assessments.insert_one(document.copy())

    email_sent = False
    try:
        await send_owner_assessment_email(document)
        email_sent = True
        await db.board_assessments.update_one(
            {"assessment_number": assessment_number},
            {"$set": {"owner_email_status": "Sent"}},
        )
    except Exception as exc:
        logger.error("Owner email failed for %s: %s", assessment_number, exc)
        await db.board_assessments.update_one(
            {"assessment_number": assessment_number},
            {"$set": {"owner_email_status": "Failed", "owner_email_error": str(exc)[:500]}},
        )

    if payload.marketing_consent:
        try:
            contact_id = await sync_nonprofit_leader(document)
            await db.board_assessments.update_one(
                {"assessment_number": assessment_number},
                {"$set": {
                    "marketing_resend_status": "Synced",
                    "marketing_resend_contact_id": contact_id,
                    "marketing_resend_error": "",
                }},
            )
        except Exception as exc:
            logger.error("Nonprofit leader Resend sync failed for %s: %s", assessment_number, exc)
            await db.board_assessments.update_one(
                {"assessment_number": assessment_number},
                {"$set": {"marketing_resend_status": "Failed", "marketing_resend_error": str(exc)[:500]}},
            )

    return AssessmentResponse(
        assessment_number=assessment_number,
        organization_name=payload.organization_name,
        submitted_email=payload.email,
        submitted_at=now.isoformat(),
        status="New Board Assessment",
        email_sent=email_sent,
    )


app.include_router(api_router)
app.include_router(create_applicant_router(db))
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[] if os.environ.get("CORS_ORIGINS") == "*" else os.environ["CORS_ORIGINS"].split(","),
    allow_origin_regex=r"https?://.*" if os.environ.get("CORS_ORIGINS") == "*" else None,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@app.on_event("startup")
async def startup_tasks():
    await db.board_applicants.create_index("email", unique=True)
    await db.board_applicants.create_index("applicant_id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier", unique=True)
    await seed_admin(db)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()