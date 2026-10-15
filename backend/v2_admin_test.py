"""Admin-only paid journey testing using the real V2 routers and separate storage.

No production payment, AI, email or applicant-network provider is called. Only
administrator authentication reads the existing users collection.
"""
from collections import OrderedDict
import hashlib
import html
import json
import re
import secrets

from fastapi import APIRouter, FastAPI, HTTPException, Request, Response

from v2_core import PRODUCTS, csrf_guard, enabled, existing_admin, new_id, now_iso, origin
from v2_form_content import INTAKE_FIELDS


class AdminTestDatabase:
    def __init__(self, source, user_id):
        self.source = source
        self.prefix = "v2_admintest_" + hashlib.sha256(user_id.encode()).hexdigest()[:16] + "_"

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self.source, "users" if name == "users" else self.prefix + name)


def is_admin_test(db):
    return isinstance(db, AdminTestDatabase)


def form_token(db, product):
    token = secrets.token_urlsafe(32)
    return f"admin-test-{product}--{token}" if is_admin_test(db) else token


def sample_generation(generation_type, context):
    """Clearly labeled, schema-shaped examples rendered by existing generators."""
    from ai_service import GENERATION_TYPES
    source, _ = json.JSONDecoder().raw_decode(context.split("VERIFIED V2 CONTEXT:\n", 1)[1])
    org = source["organization_name"]
    submission = source.get("submission") or {}
    answers = submission.get("answers") or {}
    statement = answers.get("decision_reason") or answers.get("participation_barriers") or answers.get("why_interested") or ""
    sentence = f"SAMPLE FOR ADMIN TESTING. {org} helps young people develop skills through community learning."
    if submission:
        sentence = f"SAMPLE FOR ADMIN TESTING. {submission['name']} said: {statement or 'I would like to discuss my contribution.'}"
    if source.get("approved_board_member_profiles"):
        sentence += " Approved roles: " + source["approved_board_member_profiles"]["text"][:2000]

    def fill(schema):
        if isinstance(schema, dict):
            return {key: fill(value) for key, value in schema.items()}
        if isinstance(schema, list):
            return [fill(schema[0])] if schema else []
        return sentence

    result = fill(GENERATION_TYPES[generation_type]["schema"])
    if generation_type == "social_posts":
        result["posts"] = [{"platform": platform, "post_text": sentence + " Apply here: [APPLICATION LINK]"} for platform in ("LinkedIn", "Facebook", "Instagram")]
    if generation_type == "application_questions":
        result["custom_questions"] = [{"id": f"custom_{i}", "label": f"How could you support our community learning work? Example question {i}.", "type": "textarea"} for i in range(1, 6)]
    if generation_type == "recruitment_assessment_profiles":
        result["priority_roles"] = [{"role_name": "Community learning and governance", "why_this_person_is_important": sentence, "how_this_person_can_support": "Help the sample organization strengthen its learning programs and board governance."}]
    if generation_type in {"interview_invitation", "before_interview_rejection"}:
        result["subject"] = "Sample interview invitation" if generation_type == "interview_invitation" else "Sample application response"
        result["body"] = f"Dear {submission['name']},\n\nThank you for considering {org}. This is an administrator test communication and will not be sent."
    return result


def sample_answers(product):
    answers = {key: "Our sample organization supports community learning and practical opportunities for young people." for key in INTAKE_FIELDS[product]}
    answers.update({"mission": "Help young people build skills and confidence through community learning."})
    if product == "strategic-planning":
        answers["program_details"] = [{"name": "Community learning", "description": "Weekly mentoring and learning sessions.", "present_work": "Volunteer-led sessions."}]
        answers["budget"] = "No financial commitment has been approved in this sample."
    if product == "board-recommitment":
        answers["need_by"] = "2030-12-31"
    return answers


def create_admin_test_router(source_db):
    router = APIRouter(prefix="/api/v2/admin", tags=["Admin paid journey tests"])
    apps = OrderedDict()

    async def environment(request):
        enabled()
        csrf_guard(request)
        user = await existing_admin(request, source_db)
        if not user:
            raise HTTPException(401, "Sign in to your administrator dashboard to open these test journeys.")
        key = user["user_id"]
        if key not in apps:
            from v2_core import create_indexes
            from v2_routes import create_v2_router
            db = AdminTestDatabase(source_db, key)
            await create_indexes(db)
            app = FastAPI()
            app.include_router(create_v2_router(db, include_admin_tests=False))
            apps[key] = (db, app)
            if len(apps) > 32:
                apps.popitem(last=False)
        apps.move_to_end(key)
        return apps[key]

    @router.get("/test-journeys/{product}")
    async def current(product: str, request: Request):
        db, _ = await environment(request)
        if product not in PRODUCTS:
            raise HTTPException(404, "Choose one of the four products.")
        row = await db.v2_journeys.find_one({"product": product}, {"_id": 0}, sort=[("created_at", -1)])
        return {"journey": row, "test_mode": True}

    @router.post("/test-journeys/{product}")
    async def start(product: str, request: Request):
        db, _ = await environment(request)
        if product not in PRODUCTS:
            raise HTTPException(404, "Choose one of the four products.")
        jid = f"admin-test-{product}--{new_id()}"
        stamp = now_iso()
        row = {"journey_id": jid, "journey_version": "v2", "product": product,
               "name": "Sample Executive Director", "email": "leader@example.test", "organization": "Sample Community Learning Charity",
               "answers": sample_answers(product), "desired_count": "2", "board_count": 5, "goal_amount": 50000,
               "state": "paid", "admin_test": True, "payment_status": "admin_test_no_payment",
               "branding": {"organization_name": "Sample Community Learning Charity", "logo_data": "", "primary_color": "", "secondary_color": ""},
               "form_token": form_token(db, product), "group_token": form_token(db, product),
               "meeting": {}, "decision_version": 0, "campaign_status": "draft",
               "setup_complete": False, "generation_status": "waiting_setup", "created_at": stamp, "updated_at": stamp}
        await db.v2_journeys.insert_one(row.copy())
        return {"journey": row, "next": f"/v2/setup/{jid}", "test_mode": True}

    @router.get("/test-journeys/{product}/inbox")
    async def inbox(product: str, request: Request):
        db, _ = await environment(request)
        if product not in PRODUCTS:
            raise HTTPException(404, "Choose one of the four products.")
        journeys = await db.v2_journeys.find({"product": product}, {"journey_id": 1, "_id": 0}).to_list(100)
        records = await db.v2_email_outbox.find({"journey_id": {"$in": [row["journey_id"] for row in journeys]}}, {"_id": 0}).sort("created_at", -1).to_list(100)
        return {"test_mode": True, "emails": [{"event_id": row["event_id"], "to": row["to"], "subject": row["subject"],
            "status": "captured_not_sent", "text": row.get("test_body") or html.unescape(re.sub(r"<[^>]*>", " ", row["payload"]["html"])),
            "action_path": row.get("test_action_path", ""), "resource_id": row.get("resource_id"), "journey_id": row["journey_id"]} for row in records]}

    @router.api_route("/test-api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def customer_api(path: str, request: Request):
        db, app = await environment(request)
        # Only paid customer actions. Checkout, access recovery and admin tools
        # cannot be reached through this adapter.
        if (not path.startswith(("journeys/", "forms/", "meeting/")) and path != "marketplace") or re.search(r"(?:^|/)(?:checkout|payment)(?:/|$)", path) or ".." in path or "\\" in path:
            raise HTTPException(403, "This action is not available in administrator testing.")
        scope = dict(request.scope)
        scope.update(path="/api/v2/" + path, raw_path=("/api/v2/" + path).encode(), root_path="")
        messages = []

        async def capture(message):
            messages.append(message)

        await app(scope, request.receive, capture)
        # There is no background worker in this isolated test environment.
        # Complete only its sample preparation, using the same profile gates.
        from v2_resources import generate_pending_resources
        for row in await db.v2_journeys.find({"setup_complete": True}, {"_id": 0}).to_list(100):
            await generate_pending_resources(db, row)
        start = next(message for message in messages if message["type"] == "http.response.start")
        body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
        response = Response(body, status_code=start["status"])
        response.raw_headers = start["headers"]
        return response

    return router
