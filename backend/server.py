import asyncio
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
from resend_service import send_automation_error
from automation_service import automation_loop
from accountability_service import accountability_loop
from funnel_routes import create_funnel_router
from payment_routes import create_payment_router, create_stripe_webhook_router
from member_routes import create_member_router
from course_routes import create_course_router
from workspace_routes import create_workspace_router
from public_opportunity_routes import create_public_opportunity_router
from marketing_routes import create_marketing_router
from review_routes import create_review_router
from reference_routes import create_reference_router
from marketing_service import marketing_loop


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Nonprofit Board Builder")
api_router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)
automation_task = None


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
    execution_preference: str = Field(min_length=1)
    additional_information: Optional[str] = ""
    confirmation_accepted: bool


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
    document["email"] = str(payload.email).lower()
    document.update(
        {
            "assessment_number": assessment_number,
            "submitted_at": now.isoformat(),
            "status": "New Board Assessment",
            "owner_email_status": "Pending",
            "resend_contact_id": "",
            "resend_sync_status": "Pending" if payload.country == "United States" else "Not Applicable — United Kingdom",
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

    if payload.country == "United States":
        existing_contact = await db.nonprofit_contacts.find_one({"email": document["email"]}, {"_id": 0})
        contact = {
            "name": document["name"], "email": document["email"], "phone": document["phone"],
            "organization_name": document["organization_name"], "country": document["country"],
            "city": document["city"], "state_region": document["state_region"],
            "created_at": existing_contact["created_at"] if existing_contact else now.isoformat(),
            "latest_assessment_at": now.isoformat(), "latest_assessment_number": assessment_number,
            "present_board_size": document["current_board_size"],
            "active_board_members": document["active_board_members"],
            "inactive_board_members": document["inactive_board_members"],
            "recruitment_need": document["new_board_members_needed"],
            "fundraising_need": ", ".join(document["areas_carried_alone"]),
            "execution_preference": document["execution_preference"],
            "resend_contact_id": existing_contact.get("resend_contact_id", "") if existing_contact else "",
            "resend_sync_status": "Pending",
        }
        await db.nonprofit_contacts.update_one({"email": document["email"]}, {"$set": contact}, upsert=True)
        try:
            contact_id = await sync_nonprofit_leader(contact)
            await db.board_assessments.update_one(
                {"assessment_number": assessment_number},
                {"$set": {
                    "resend_sync_status": "Synced", "resend_contact_id": contact_id, "resend_sync_error": "",
                }},
            )
            await db.nonprofit_contacts.update_one(
                {"email": document["email"]},
                {"$set": {"resend_sync_status": "Synced", "resend_contact_id": contact_id, "resend_sync_error": ""}},
            )
        except Exception as exc:
            logger.error("Nonprofit leader Resend sync failed for %s: %s", assessment_number, exc)
            await db.board_assessments.update_one(
                {"assessment_number": assessment_number},
                {"$set": {"resend_sync_status": "Failed", "resend_sync_error": str(exc)[:500]}},
            )
            await db.nonprofit_contacts.update_one(
                {"email": document["email"]}, {"$set": {"resend_sync_status": "Failed", "resend_sync_error": str(exc)[:500]}}
            )
            await send_automation_error(
                db, failure_key=f"nonprofit-sync:{assessment_number}",
                process="Nonprofit leader Resend contact sync", contact_email=document["email"],
                error=str(exc), submission_saved=True, owner_notification_sent=email_sent,
                corrective_action="Review the Resend API key, Nonprofit Leaders Segment and Board Building Opportunities Topic, then update the contact in Resend.",
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
app.include_router(create_funnel_router(db))
app.include_router(create_payment_router(db))
app.include_router(create_stripe_webhook_router(db))
app.include_router(create_member_router(db))
app.include_router(create_course_router(db))
app.include_router(create_workspace_router(db))
from refinement_routes import create_refinement_router
app.include_router(create_refinement_router(db))
from board_intake_routes import create_board_intake_router
app.include_router(create_board_intake_router(db))
from reactivation_intake_routes import create_reactivation_intake_router
app.include_router(create_reactivation_intake_router(db))
from activation_intake_routes import create_activation_intake_router
app.include_router(create_activation_intake_router(db))
from activation_planning_routes import create_activation_planning_router
app.include_router(create_activation_planning_router(db))
from activation_delivery import create_activation_delivery_router
app.include_router(create_activation_delivery_router(db))
from reactivation_routes import create_reactivation_router
app.include_router(create_reactivation_router(db))
from admin_service_routes import create_admin_service_router
app.include_router(create_admin_service_router(db))
from funnel_stats_routes import create_funnel_stats_router
app.include_router(create_funnel_stats_router(db))
from board_fix_routes import create_board_fix_router
app.include_router(create_board_fix_router(db))
from strategic_planning_routes import create_strategic_planning_router
app.include_router(create_strategic_planning_router(db))
from reactivation_plan_routes import create_reactivation_plan_router
app.include_router(create_reactivation_plan_router(db))
app.include_router(create_public_opportunity_router(db))
app.include_router(create_marketing_router(db))
app.include_router(create_review_router(db))
app.include_router(create_reference_router(db))
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
    global automation_task
    await db.board_applicants.create_index("email", unique=True)
    await db.board_applicants.create_index("applicant_id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier", unique=True)
    await db.nonprofit_contacts.create_index("email", unique=True)
    await db.weekly_sales_emails.create_index(
        [("audience", 1), ("campaign_theme", 1), ("scheduled_week", 1)], unique=True
    )
    await db.automation_errors.create_index("failure_key", unique=True)
    await db.funnel_leads.create_index("lead_id", unique=True)
    await db.funnel_leads.create_index("result_token", unique=True)
    await db.funnel_leads.create_index([("offer_source", 1), ("created_at", -1)])
    await db.payment_transactions.create_index("session_id", unique=True)
    await db.members.create_index("email", unique=True)
    await db.members.create_index("user_id", unique=True)
    await db.purchases.create_index("session_id", unique=True)
    await db.password_resets.create_index("token", unique=True)
    await db.course_progress.create_index(
        [("user_id", 1), ("product", 1), ("module_number", 1)], unique=True
    )
    await db.course_videos.create_index([("product", 1), ("module_number", 1)], unique=True)
    from five_step_migration import run_five_step_migration
    await run_five_step_migration(db)
    from six_module_migration import run_six_module_migration
    await run_six_module_migration(db)
    await db.support_requests.create_index("support_request_id", unique=True)
    await db.recruitment_profiles.create_index("user_id", unique=True)
    await db.generated_materials.create_index("material_id", unique=True)
    await db.generated_materials.create_index([("user_id", 1), ("type", 1), ("application_id", 1)], unique=True)
    await db.opportunities.create_index("opportunity_id", unique=True)
    await db.opportunities.create_index("slug", unique=True)
    await db.opportunities.create_index("user_id", unique=True)
    await db.opportunity_applications.create_index("application_id", unique=True)
    await db.opportunity_applications.create_index([("opportunity_id", 1), ("applicant_email", 1)], unique=True)
    await db.apply_tokens.create_index("token", unique=True)
    await db.signature_requests.create_index("request_id", unique=True)
    await db.signature_requests.create_index("token", unique=True)
    await db.blog_posts.create_index([("category_key", 1), ("scheduled_date", 1)], unique=True)
    await db.blog_posts.create_index("slug")
    await db.nurture_sends.create_index([("segment", 1), ("scheduled_week", 1)], unique=True)
    await db.nurture_contacts.create_index("email", unique=True)
    await db.rooney_engagements.create_index("purchase_id", unique=True)
    await db.rooney_engagements.create_index("engagement_id", unique=True)
    await db.rooney_engagements.create_index("user_id")
    await db.board_reactivation_intakes.create_index("session_id", unique=True)
    await db.board_activation_intakes.create_index("session_id", unique=True)
    await db.activation_participants.create_index("form_token", unique=True)
    await db.activation_participants.create_index([("user_id", 1), ("email", 1)])
    await db.activation_planning_forms.create_index("user_id", unique=True)
    await db.activation_strategies.create_index("user_id", unique=True)
    await db.activation_adoptions.create_index("user_id", unique=True)
    await db.activation_toolkits.create_index("user_id", unique=True)
    await db.reactivation_board_members.create_index("form_token", unique=True)
    await db.reactivation_board_members.create_index([("user_id", 1), ("email", 1)])
    await db.reactivation_engagements.create_index("purchase_id", unique=True)
    await seed_admin(db)
    automation_task = asyncio.create_task(automation_loop(db))
    app.state.marketing_task = asyncio.create_task(marketing_loop(db))
    app.state.accountability_task = asyncio.create_task(accountability_loop(db))
    from reactivation_accountability import reactivation_accountability_loop
    app.state.reactivation_accountability_task = asyncio.create_task(reactivation_accountability_loop(db))
    from activation_accountability import activation_accountability_loop
    app.state.activation_accountability_task = asyncio.create_task(activation_accountability_loop(db))
    from checkout_recovery import checkout_recovery_loop
    app.state.checkout_recovery_task = asyncio.create_task(checkout_recovery_loop(db))


@app.on_event("shutdown")
async def shutdown_db_client():
    if automation_task:
        automation_task.cancel()
    client.close()