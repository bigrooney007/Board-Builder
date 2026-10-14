"""Confirmed V2 recruitment launch using the existing marketplace and network.

Only V2 opportunities are written. Preview announcements default to explicitly
configured test contacts already registered and opted in to board opportunities.
No provider calls happen here; the existing V2 outbox owns delivery and retries.
"""
import copy
import hashlib
import html
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from v2_core import digest, enabled, find_journey, journey_lock, now_iso, origin, preview_access, require_owner, validate_email
from v2_email import queue_email, retry_email
from v2_resource_content import RECRUITMENT_INVENTORY, organization_name

REQUIRED = tuple((key, title) for key, title, _, _ in RECRUITMENT_INVENTORY)
SUSPENDED = {"withdrawn", "paused", "unsubscribed", "opted out", "opted-out"}


def network_live():
    return os.environ.get("NBB_V2_NETWORK_LIVE_ENABLED", "false").lower() == "true"


def network_test_contacts():
    raw = os.environ.get("NBB_V2_NETWORK_TEST_EMAILS") or os.environ.get("NBB_V2_TEST_EMAILS", "")
    return {value.strip().lower() for value in raw.split(",") if value.strip()}


def opted_in(applicant):
    """Missing consent never becomes implied permission to receive announcements."""
    return (applicant.get("board_opportunity_consent") is True
            and str(applicant.get("status", "")).strip().lower() not in SUSPENDED
            and not any(applicant.get(key) for key in ("unsubscribed", "unsubscribed_at", "email_unsubscribed", "marketing_unsubscribed")))


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def approved_snapshot(resource):
    if not resource or resource.get("status") != "approved" or resource.get("approved_revision") != resource.get("revision"):
        return None
    approved = next((item for item in resource.get("approved_versions", []) if item.get("revision") == resource["revision"]), None)
    if not approved:
        return None
    return {key: copy.deepcopy(approved.get(key)) for key in ("revision", "title", "text", "structured", "branding", "branding_hash", "approved_at")}


async def current_preview(db, journey):
    resources = await db.v2_resources.find({"journey_id": journey["journey_id"], "key": {"$in": [key for key, _ in REQUIRED]}, "submission_id": ""}, {"_id": 0}).to_list(len(REQUIRED))
    by_key = {item["key"]: item for item in resources}
    snapshots, readiness, hash_rows = {}, [], []
    for key, title in REQUIRED:
        item = by_key.get(key) or {}
        selected = approved_snapshot(item)
        approved = bool(selected and selected.get("text"))
        if selected:
            snapshots[key] = selected
        readiness.append({"key": key, "title": title, "resource_id": item.get("resource_id", ""),
                          "approved": approved, "status": item.get("status", "missing"), "revision": item.get("revision", 0),
                          "approved_revision": item.get("approved_revision")})
        hash_rows.append({"key": key, "resource_id": item.get("resource_id", ""), "revision": item.get("revision", 0),
                          "approved_revision": item.get("approved_revision"), "text_hash": digest(item.get("text", "")),
                          "branding_hash": (selected or {}).get("branding_hash", "")})
    revision = stable_hash({"resources": hash_rows, "branding": journey.get("branding") or {}})
    preview = (snapshots.get("board_opportunity") or {}).get("text") or "Review and approve your Board Recruitment Announcement to see the campaign preview."
    return {"revision": revision, "resources": snapshots, "required_resources": readiness, "preview": preview,
            "branding": copy.deepcopy(journey.get("branding") or {}), "ready": all(item["approved"] for item in readiness)}


def _activity(key, title, status, detail, mode=""):
    return {"key": key, "title": title, "status": status, "detail": detail, **({"mode": mode} if mode else {})}


async def network_result(db, journey):
    campaign = journey.get("campaign") or {}
    revision = (journey.get("campaign_snapshot") or {}).get("revision")
    stored = (campaign.get("activities") or {}).get("network")
    if not revision or campaign.get("network_recipients") is None:
        return stored or _activity("network", "Applicant network announcement", "not_started", "No applicant network announcement has been requested.")
    contacts = campaign.get("network_recipients") or []
    mode = campaign.get("network_mode", "test")
    if not contacts:
        return stored or _activity("network", "Applicant network announcement", "skipped", "There are no eligible opted-in contacts for this preview.", mode)
    records = await db.v2_email_outbox.find({"journey_id": journey["journey_id"], "purpose": "board-opportunity", "campaign_revision": revision},
                                          {"_id": 0, "status": 1}).to_list(6000)
    counts = {}
    for record in records:
        status = record.get("status", "pending")
        counts[status] = counts.get(status, 0) + 1
    skipped = len(campaign.get("network_skipped") or [])
    sent = counts.get("sent", 0)
    pending = counts.get("pending", 0) + counts.get("sending", 0)
    failed = counts.get("failed", 0) + counts.get("blocked", 0) + counts.get("needs_review", 0)
    cancelled = counts.get("cancelled", 0) + counts.get("suppressed", 0)
    missing = max(0, len(contacts) - len(records) - skipped)
    if failed or missing:
        status = "partial" if sent or pending else "failed"
    elif pending:
        status = "pending"
    elif sent:
        status = "sent"
    else:
        status = "skipped"
    detail = f"{sent} announcement(s) confirmed sent; {pending} queued or awaiting confirmation; {failed + missing} need attention; {skipped + cancelled} skipped or cancelled."
    return _activity("network", "Applicant network announcement", status, detail, mode)


async def campaign_view(db, journey):
    current = await current_preview(db, journey)
    campaign = journey.get("campaign") or {}
    status = journey.get("campaign_status") or campaign.get("status") or "not_launched"
    activities = copy.deepcopy(campaign.get("activities") or {})
    if status == "active":
        activities["application"] = _activity("application", "Board application form", "active", "The confirmed application form is accepting submissions.")
    elif status in {"paused", "closed"}:
        activities["application"] = _activity("application", "Board application form", status, "The form is not accepting new applications. Existing submissions are retained.")
    activities["network"] = await network_result(db, journey)
    snapshot = journey.get("campaign_snapshot") or {}
    # The displayed launched opportunity is the exact frozen approved version.
    preview = (snapshot.get("resources", {}).get("board_opportunity") or {}).get("text") if status == "active" else current["preview"]
    return {"journey_id": journey["journey_id"], "status": status, "revision": current["revision"],
            "published_revision": snapshot.get("revision"), "preview": preview or current["preview"],
            "required_resources": current["required_resources"], "activities": list(activities.values()),
            "application_link": f"{origin()}/v2/forms/{journey['form_token']}",
            "marketplace_link": f"{origin()}/v2/marketplace" if (activities.get("marketplace") or {}).get("status") == "published" else ""}


async def _record_activity(db, jid, revision, key, value):
    await db.v2_journeys.update_one({"journey_id": jid, "campaign_snapshot.revision": revision},
                                  {"$set": {f"campaign.activities.{key}": value, "updated_at": now_iso()}})


async def publish_marketplace(db, journey):
    jid = journey["journey_id"]
    snapshot = journey["campaign_snapshot"]
    revision = snapshot["revision"]
    opportunity = snapshot["resources"]["board_opportunity"]
    # Existing unique user_id/slug/opportunity_id indexes provide deduplication.
    slug = "v2-" + re.sub(r"[^a-z0-9-]", "", jid.lower())
    brand = opportunity.get("branding") or snapshot.get("branding") or {}
    document = {"user_id": "v2:" + jid, "opportunity_id": "v2:" + jid, "slug": slug,
                "organization_name": brand.get("organization_name") or organization_name(journey),
                "status": "V2Published", "source": "v2", "journey_version": "v2", "journey_id": jid,
                "campaign_revision": revision, "summary": opportunity["text"], "branding": brand,
                "approved_opportunity": opportunity, "custom_questions": snapshot["resources"]["application_questions"].get("structured", {}).get("custom_questions", []),
                "application_path": f"/v2/forms/{journey['form_token']}", "application_saved": True,
                "published_at": journey.get("campaign", {}).get("launched_at") or now_iso(), "updated_at": now_iso()}
    await db.opportunities.update_one({"user_id": "v2:" + jid}, {"$set": document, "$setOnInsert": {"created_at": now_iso()}}, upsert=True)
    await _record_activity(db, jid, revision, "marketplace", _activity("marketplace", "Board Applicant Marketplace", "published", "The approved opportunity is published in the isolated V2 marketplace."))


async def _choose_network_contacts(db, journey):
    live, allowlist = network_live(), network_test_contacts()
    mode = "live" if live else "test"
    if not live and not allowlist:
        return [], mode, _activity("network", "Applicant network announcement", "not_configured", "No test contacts are configured. No announcement was sent to the live applicant network.", mode)
    if live and not all(os.environ.get(key) for key in ("RESEND_API_KEY", "BOARD_APPLICANT_SENDER")):
        return [], mode, _activity("network", "Applicant network announcement", "not_configured", "The applicant network sender is not configured. No live announcement was queued.", mode)
    query = {"board_opportunity_consent": True}
    if not live:
        query["email"] = {"$in": sorted(allowlist)}
    rows = await db.board_applicants.find(query, {"_id": 0}).to_list(5000)
    chosen, emails = [], set()
    for applicant in rows:
        if not opted_in(applicant) or not applicant.get("applicant_id"):
            continue
        try:
            email = validate_email(applicant.get("email"))
        except HTTPException:
            continue
        if email in emails or (not live and email not in allowlist):
            continue
        if live and not applicant.get("resend_contact_id"):
            # Live provider-side unsubscribe verification requires the existing
            # registered contact. No contact is created to make a send possible.
            continue
        emails.add(email)
        chosen.append({"applicant_id": applicant["applicant_id"], "email": email, "contact_id": applicant.get("resend_contact_id", "")})
    if not chosen:
        return [], mode, _activity("network", "Applicant network announcement", "skipped", "No registered, opted-in contacts are eligible for this announcement. No applicant contacts have been created.", mode)
    return chosen, mode, _activity("network", "Applicant network announcement", "pending", f"Preparing announcements for {len(chosen)} registered, opted-in contact(s).", mode)


async def queue_network(db, journey):
    jid, snapshot = journey["journey_id"], journey["campaign_snapshot"]
    revision, campaign = snapshot["revision"], journey.get("campaign") or {}
    contacts = campaign.get("network_recipients")
    if contacts is None:
        contacts, mode, initial = await _choose_network_contacts(db, journey)
        await db.v2_journeys.update_one({"journey_id": jid, "campaign_snapshot.revision": revision},
                                      {"$set": {"campaign.network_recipients": contacts, "campaign.network_mode": mode,
                                                "campaign.network_skipped": [], "campaign.activities.network": initial}})
        if not contacts:
            return
    else:
        mode = campaign.get("network_mode", "test")
    skipped = set(campaign.get("network_skipped") or [])
    opportunity = snapshot["resources"]["board_opportunity"]
    for contact in contacts:
        current_journey = await find_journey(db, jid)
        if current_journey.get("campaign_status") != "active" or current_journey.get("campaign_snapshot", {}).get("revision") != revision:
            return
        applicant = await db.board_applicants.find_one({"applicant_id": contact["applicant_id"], "email": contact["email"]}, {"_id": 0})
        if not applicant or not opted_in(applicant) or (mode == "test" and contact["email"] not in network_test_contacts()) or (mode == "live" and not network_live()):
            skipped.add(contact["applicant_id"])
            continue
        key = f"campaign-network:{jid}:{revision}:{contact['applicant_id']}"
        existing = await db.v2_email_outbox.find_one({"event_key": key}, {"_id": 0})
        if existing and existing.get("status") != "assembling":
            if existing.get("status") in {"failed", "blocked"}:
                await retry_email(db, existing["event_id"], jid)
            continue
        token = secrets.token_urlsafe(32)
        unsubscribe_url = f"{origin()}/api/v2/network/unsubscribe/{token}"
        text = opportunity["text"]
        announcement = await queue_email(db, key, contact["email"], f"Board opportunity with {organization_name(journey)}",
                                         "You registered to receive nonprofit board opportunities. This organization has approved its recruitment opportunity and is accepting applications.\n\n" + text,
                                         journey_id=jid, action_path=f"/v2/forms/{journey['form_token']}",
                                         metadata={"purpose": "board-opportunity", "network_applicant_id": contact["applicant_id"],
                                                   "network_mode": mode, "campaign_revision": revision,
                                                   "sender_env": "BOARD_APPLICANT_SENDER", "unsubscribe_digest": digest(token)}, ready=False)
        # The outbox remains in assembling state until purpose, unsubscribe
        # safeguards and the complete payload are persisted together.
        payload = copy.deepcopy(announcement["payload"])
        payload["html"] += "<p style='font-size:13px'><a href='" + html.escape(unsubscribe_url, quote=True) + "'>Unsubscribe from Board Applicant Network opportunities</a></p>"
        payload["headers"] = {"List-Unsubscribe": "<" + unsubscribe_url + ">", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}
        await db.v2_email_outbox.update_one({"event_id": announcement["event_id"]},
                                          {"$set": {"purpose": "board-opportunity", "network_applicant_id": contact["applicant_id"],
                                                    "network_contact_id": contact.get("contact_id", ""), "network_mode": mode,
                                                    "campaign_revision": revision, "sender_env": "BOARD_APPLICANT_SENDER",
                                                    "unsubscribe_digest": digest(token), "payload": payload, "status": "pending"}})
    await db.v2_journeys.update_one({"journey_id": jid, "campaign_snapshot.revision": revision}, {"$set": {"campaign.network_skipped": sorted(skipped)}})
    current = await find_journey(db, jid)
    await _record_activity(db, jid, revision, "network", await network_result(db, current))


async def finish_launch(db, journey):
    """Recoverable activity lease keeps provider-free DB work outside owner locks."""
    jid, revision = journey["journey_id"], journey["campaign_snapshot"]["revision"]
    token = secrets.token_urlsafe(24)
    claim = await db.v2_journeys.update_one({"journey_id": jid, "campaign_snapshot.revision": revision, "campaign_status": "active",
                                           "$or": [{"campaign_activity_lease_until": {"$exists": False}}, {"campaign_activity_lease_until": {"$lte": now_iso()}}]},
                                          {"$set": {"campaign_activity_lease": token, "campaign_activity_lease_until": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()}})
    if not claim.modified_count:
        return
    try:
        try:
            await publish_marketplace(db, journey)
        except Exception:
            await _record_activity(db, jid, revision, "marketplace", _activity("marketplace", "Board Applicant Marketplace", "failed", "The opportunity could not be published. Your application form remains available. Retry this activity safely."))
        try:
            await queue_network(db, journey)
        except Exception:
            await _record_activity(db, jid, revision, "network", _activity("network", "Applicant network announcement", "partial", "Some announcements could not be queued. Retry safely to complete the remaining eligible contacts.", "live" if network_live() else "test"))
        current = await find_journey(db, jid)
        view = await campaign_view(db, current)
        summary = "\n".join(activity["title"] + ": " + activity["status"] + ". " + activity["detail"] for activity in view["activities"])
        try:
            await queue_email(db, f"campaign-launch:{jid}:{revision}", journey["email"], "Your Board Recruitment Campaign Launch Results",
                              "You confirmed your recruitment campaign launch. Here are the recorded results:\n\n" + summary + "\n\nUse the secure link to review current delivery results, retry any unfinished activity, or pause or close applications. Share your application link and approved promotional materials through your own networks.",
                              journey_id=jid, action_path=f"/v2/campaign/{jid}")
        except Exception:
            await _record_activity(db, jid, revision, "confirmation", _activity("confirmation", "Campaign launch confirmation email", "failed", "The launch results are saved here, but the confirmation email could not be queued. Retry to request it again."))
    finally:
        await db.v2_journeys.update_one({"journey_id": jid, "campaign_activity_lease": token},
                                      {"$unset": {"campaign_activity_lease": "", "campaign_activity_lease_until": ""}})


class LaunchRequest(BaseModel):
    confirmed: bool = False
    expected_revision: str = Field(min_length=1, max_length=64)


class CampaignStatusRequest(BaseModel):
    status: str


def create_v2_campaign_router(db):
    router = APIRouter(prefix="/api/v2", tags=["NBB V2 recruitment campaign"])

    async def recruitment_owner(request, jid):
        journey = await require_owner(request, db, jid)
        if journey["product"] != "recruit":
            raise HTTPException(422, "Only Board Recruitment has a recruitment campaign.")
        return journey

    @router.get("/marketplace")
    async def marketplace(request: Request):
        await preview_access(request, db)
        rows = await db.opportunities.find({"status": "V2Published", "source": "v2", "journey_version": "v2"}, {"_id": 0}).sort("published_at", -1).to_list(200)
        opportunities = []
        for row in rows:
            journey = await db.v2_journeys.find_one({"journey_id": row.get("journey_id"), "state": "paid", "campaign_status": "active",
                                                   "campaign_snapshot.revision": row.get("campaign_revision")}, {"_id": 0})
            if not journey:
                continue
            opportunities.append({key: row.get(key) for key in ("slug", "organization_name", "summary", "application_path", "branding")})
        return {"opportunities": opportunities}

    @router.get("/journeys/{jid}/campaign")
    async def campaign(jid: str, request: Request):
        return await campaign_view(db, await recruitment_owner(request, jid))

    @router.post("/journeys/{jid}/campaign/launch")
    async def launch(jid: str, payload: LaunchRequest, request: Request):
        await recruitment_owner(request, jid)
        if not payload.confirmed:
            raise HTTPException(422, "Confirm the approved campaign preview before launching.")
        async with journey_lock(db, jid):
            journey = await find_journey(db, jid)
            if journey.get("campaign_status") == "closed":
                raise HTTPException(409, "This campaign is closed. Its resources and applications remain available.")
            preview = await current_preview(db, journey)
            if payload.expected_revision != preview["revision"]:
                raise HTTPException(409, "Your campaign materials changed. Review the new preview before confirming launch.")
            if not preview["ready"]:
                raise HTTPException(409, "Approve the current announcement, application form, job post and LinkedIn post before launching.")
            current_snapshot = journey.get("campaign_snapshot") or {}
            if journey.get("campaign_status") == "active" and current_snapshot.get("revision") != preview["revision"]:
                raise HTTPException(409, "Pause the existing campaign before confirming changed recruitment materials.")
            if current_snapshot.get("revision") != preview["revision"] or not current_snapshot:
                snapshot = {"revision": preview["revision"], "resources": preview["resources"], "branding": preview["branding"], "confirmed_at": now_iso()}
                campaign_data = {"status": "active", "launched_at": now_iso(), "activities": {
                    "application": _activity("application", "Board application form", "active", "Your explicitly approved form is accepting applications."),
                    "marketplace": _activity("marketplace", "Board Applicant Marketplace", "pending", "Marketplace publication is being prepared."),
                    "network": _activity("network", "Applicant network announcement", "pending", "Permitted announcements are being prepared.", "live" if network_live() else "test"),
                }}
                await db.v2_journeys.update_one({"journey_id": jid}, {"$set": {"campaign_snapshot": snapshot, "campaign_status": "active", "campaign": campaign_data, "updated_at": now_iso()}})
            else:
                await db.v2_journeys.update_one({"journey_id": jid}, {"$set": {"campaign_status": "active", "campaign.status": "active", "updated_at": now_iso()}})
            journey = await find_journey(db, jid)
        await finish_launch(db, journey)
        return await campaign_view(db, await find_journey(db, jid))

    @router.post("/journeys/{jid}/campaign/retry")
    async def retry(jid: str, request: Request):
        journey = await recruitment_owner(request, jid)
        if not journey.get("campaign_snapshot") or journey.get("campaign_status") != "active":
            raise HTTPException(409, "Launch an active campaign before retrying its unfinished activities.")
        await finish_launch(db, journey)
        return await campaign_view(db, await find_journey(db, jid))

    @router.post("/journeys/{jid}/campaign/status")
    async def status(jid: str, payload: CampaignStatusRequest, request: Request):
        await recruitment_owner(request, jid)
        if payload.status not in {"active", "paused", "closed"}:
            raise HTTPException(422, "Choose active, paused or closed.")
        async with journey_lock(db, jid):
            journey = await find_journey(db, jid)
            if not journey.get("campaign_snapshot"):
                raise HTTPException(409, "Confirm your campaign launch before managing its availability.")
            if journey.get("campaign_status") == "closed" and payload.status != "closed":
                raise HTTPException(409, "This campaign is closed. Existing applications remain available.")
            await db.v2_journeys.update_one({"journey_id": jid}, {"$set": {"campaign_status": payload.status, "campaign.status": payload.status, "updated_at": now_iso()}})
            await db.opportunities.update_one({"user_id": "v2:" + jid}, {"$set": {"status": "V2Published" if payload.status == "active" else "V2Paused" if payload.status == "paused" else "V2Closed", "updated_at": now_iso()}})
            if payload.status != "active":
                await db.v2_email_outbox.update_many({"journey_id": jid, "purpose": "board-opportunity", "status": {"$in": ["pending", "failed", "blocked"]}},
                                                    {"$set": {"status": "cancelled", "error": "The organization paused or closed the campaign.", "updated_at": now_iso()}})
        # Resuming never queues a second announcement or adopts draft edits.
        return await campaign_view(db, await find_journey(db, jid))

    @router.get("/network/unsubscribe/{token}", response_class=HTMLResponse)
    @router.post("/network/unsubscribe/{token}", response_class=HTMLResponse)
    async def unsubscribe(token: str, request: Request):
        enabled()
        record = await db.v2_email_outbox.find_one({"unsubscribe_digest": digest(token), "purpose": "board-opportunity"}, {"_id": 0})
        if not record:
            raise HTTPException(404, "This unsubscribe link is not available.")
        if request.method == "GET":
            return HTMLResponse("<!doctype html><html><head><meta name='robots' content='noindex'><meta name='viewport' content='width=device-width, initial-scale=1'></head><body style='font-family:Arial,sans-serif;max-width:42rem;margin:4rem auto;padding:1rem'><h1>Board opportunity email preferences</h1><p>Confirm if you no longer want Board Applicant Network opportunity announcements.</p><form method='post'><button type='submit'>Unsubscribe from board opportunities</button></form></body></html>",
                                headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})
        await db.board_applicants.update_one({"applicant_id": record["network_applicant_id"], "email": record["to"]},
                                            {"$set": {"board_opportunity_consent": False, "unsubscribed_at": now_iso()}})
        await db.v2_email_outbox.update_many({"purpose": "board-opportunity", "to": record["to"], "status": {"$in": ["pending", "failed", "blocked"]}},
                                            {"$set": {"status": "suppressed", "error": "The applicant unsubscribed from board opportunities.", "updated_at": now_iso()}})
        return HTMLResponse("<!doctype html><html><head><meta name='robots' content='noindex'><meta name='viewport' content='width=device-width, initial-scale=1'></head><body style='font-family:Arial,sans-serif;max-width:42rem;margin:4rem auto;padding:1rem'><h1>You have unsubscribed from board opportunities.</h1><p>You will no longer receive Board Applicant Network opportunity announcements. Your existing applications are retained.</p></body></html>",
                            headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})

    return router
