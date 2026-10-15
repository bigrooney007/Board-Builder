"""Synthetic, prefilled inputs and responses for the isolated admin journeys."""
import base64
from datetime import datetime, timedelta, timezone
import io
import json
import secrets

from v2_core import now_iso


async def dispatch(app, scope, path, method=None, payload=None, receive=None):
    forwarded = dict(scope)
    forwarded.update(path="/api/v2/" + path, raw_path=("/api/v2/" + path).encode(), root_path="")
    if method:
        forwarded.update(method=method, query_string=b"")
        body = json.dumps(payload or {}).encode()
        forwarded["headers"] = [(key, value) for key, value in scope.get("headers", []) if key.lower() not in {b"content-type", b"content-length"}]
        forwarded["headers"] += [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
        received = False

        async def receive_body():
            nonlocal received
            if received:
                return {"type": "http.disconnect"}
            received = True
            return {"type": "http.request", "body": body, "more_body": False}

        receive = receive_body
    messages = []

    async def capture(message):
        messages.append(message)

    await app(forwarded, receive, capture)
    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return start["status"], start["headers"], body


def response_answers(context, name, email, index=0):
    product = context["product"]
    answers = {"full_name": name, "email": email}
    if product == "board-fundraising-game":
        types = {"individuals": "Local professionals who care about young people", "businesses": "Local employers", "grantmakers": "Youth development foundations"}
        answers.update(audiences=[{"audience_id": f"sample-{index}-{category}", "category": category, "funder": audience,
            "why": "Their interests align with skills, education and opportunities for young people.",
            "where": "Professional associations and community networks." if index == 0 else "Existing employer, volunteer and education partner introductions.",
            "attract": "Share verified program outcomes and invite them to a learning session.",
            "relationship": "Arrange an introduction, listen to their interests, and agree a suitable request for support.",
            "ask": "Support the community learning and mentoring sessions.",
            "amount": "Discuss a suitable amount based on their interest and the verified program budget."} for category, audience in types.items()],
            participation="I am willing to introduce our organization to community and employer contacts.",
            _v2_flow={"mode": "review", "categoryIndex": 2, "step": 0, "audienceId": "", "returnToReview": False, "editReturn": None})
    elif product == "board-recommitment":
        from v2_form_content import RECOMMIT_ACTIVE, RECOMMIT_ADVISORY, RECOMMIT_STEP_DOWN
        answers.update(recommitment=[RECOMMIT_ACTIVE, RECOMMIT_ADVISORY, RECOMMIT_STEP_DOWN][index % 3],
            why_joined="I joined to help young people access meaningful learning opportunities.",
            expertise=["Education", "Community Engagement"], participation_barriers="I need meeting dates early so I can plan my time.",
            contribution_interests=["Fundraising / Resource Development"], ownership_area="Community introductions and mentoring partnerships.",
            leadership_interest="I would like to discuss this", leadership_area="Community partnerships",
            strengths_resources="Experience in education and community relationships.", monthly_availability="2–4 hours",
            experience_improvement="Share meeting papers and clear expectations in advance.",
            decision_reason=["I would like to discuss a practical contribution before confirming my next steps.", "Advisory service would fit the time I can offer.", "My work commitments mean I need to step down from active service."][index % 3],
            anything_else="Please discuss expectations and availability with me.")
    else:
        for question in context.get("questions", []):
            answers[question["id"]] = "Yes" if question.get("type") == "yes_no" else "Strengthen our community learning work, review the results together, and agree the resources needed before making commitments."
        answers.update(full_name=name, email=email, location="Sample City", profession="Education and community adviser",
                       why_interested="I would like to contribute my education, governance and community partnership experience.")
    return answers


async def prepare_responses(db, app, scope, journey):
    if journey.get("test_responses_prepared") or not journey.get("setup_complete"):
        return
    if journey["product"] == "recruit" and journey.get("campaign_status") != "active":
        return
    jid = journey["journey_id"]
    lease = secrets.token_urlsafe(16)
    claimed = await db.v2_journeys.update_one({"journey_id": jid, "test_responses_prepared": {"$ne": True},
        "$or": [{"test_seed_until": {"$exists": False}}, {"test_seed_until": {"$lte": now_iso()}}]},
        {"$set": {"test_seed_lease": lease, "test_seed_until": (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()}})
    if not claimed.modified_count:
        return

    async def call(path, method="GET", payload=None):
        status, _, body = await dispatch(app, scope, path, method, payload)
        if status != 200:
            raise RuntimeError(f"Sample fixture preparation failed for {path}: {status}")
        return json.loads(body)

    try:
        for index, name in enumerate(("Sample Alex Morgan", "Sample Jordan Lee", "Sample Taylor Quinn")):
            email = f"sample-member-{index + 1}@example.test"
            token = journey["form_token"]
            if journey["product"] != "recruit":
                person = await call(f"journeys/{jid}/invitations", "POST", {"name": name, "email": email, "send": False})
                token = person["form_token"]
            context = await call(f"forms/{token}")
            response = await call(f"forms/{token}/submit", "POST", {"name": name, "email": email,
                "answers": response_answers(context, name, email, index), "idempotency_key": f"prefilled-sample-{index}"})
            if journey["product"] == "recruit":
                from reportlab.pdfgen import canvas
                data = io.BytesIO()
                pdf = canvas.Canvas(data)
                pdf.drawString(60, 780, "SYNTHETIC SAMPLE CV: " + name)
                pdf.drawString(60, 750, "Education, governance and community partnership experience.")
                pdf.drawString(60, 720, "Created only for the administrator test. This is not a real applicant.")
                pdf.save()
                await db.v2_submissions.update_one({"submission_id": response["submission_id"]}, {"$set": {"cv": {
                    "filename": "sample-board-candidate-cv.pdf", "mime": "application/pdf", "text": "Synthetic education and governance experience.",
                    "content_base64": base64.b64encode(data.getvalue()).decode()}}})
        if journey["product"] != "recruit":
            await call(f"journeys/{jid}/invitations", "POST", {"name": "Sample Invitee Ready to Send", "email": "sample-invitee@example.test", "send": False})
        await db.v2_journeys.update_one({"journey_id": jid}, {"$set": {"test_responses_prepared": True}})
    finally:
        await db.v2_journeys.update_one({"journey_id": jid, "test_seed_lease": lease}, {"$unset": {"test_seed_lease": "", "test_seed_until": ""}})
