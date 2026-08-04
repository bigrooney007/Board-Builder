import csv
import io
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from applicant_models import ApplicantAdminUpdate, ApplicantResponse, AdminLogin, BoardApplicantCreate
from auth_service import ACCESS_MINUTES, authenticate_admin, create_access_token, verify_password
from resend_service import send_applicant_confirmation, send_automation_error, sync_board_applicant


ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx"}
ALLOWED_RESUME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
}
MAX_RESUME_BYTES = 8 * 1024 * 1024


def create_applicant_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")
    resume_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="applicant_resumes")

    async def current_admin(request: Request):
        return await authenticate_admin(request, db)

    def applicant_number(now: datetime) -> str:
        return f"NBB-A-{now.strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"

    async def store_resume(resume: UploadFile, applicant_id: str) -> dict:
        extension = os.path.splitext(resume.filename or "")[1].lower()
        if extension not in ALLOWED_RESUME_EXTENSIONS or resume.content_type not in ALLOWED_RESUME_TYPES:
            raise HTTPException(status_code=400, detail="Résumé must be a PDF, DOC, or DOCX file.")
        content = await resume.read(MAX_RESUME_BYTES + 1)
        if len(content) > MAX_RESUME_BYTES:
            raise HTTPException(status_code=400, detail="Résumé must be 8 MB or smaller.")
        file_id = await resume_bucket.upload_from_stream(
            resume.filename,
            content,
            metadata={"applicant_id": applicant_id, "content_type": resume.content_type},
        )
        return {
            "resume_file_id": str(file_id),
            "resume_filename": resume.filename,
            "resume_content_type": resume.content_type,
        }

    @router.post("/applicants", response_model=ApplicantResponse, status_code=201)
    async def save_applicant(payload: str = Form(...), resume: Optional[UploadFile] = File(None)):
        try:
            profile_input = BoardApplicantCreate.model_validate(json.loads(payload))
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        normalized_email = str(profile_input.email).lower()
        existing = await db.board_applicants.find_one({"email": normalized_email}, {"_id": 0})
        created = existing is None
        applicant_id = existing["applicant_id"] if existing else applicant_number(now)

        document = profile_input.model_dump(mode="json")
        document["email"] = normalized_email
        document.update({
            "applicant_id": applicant_id,
            "consent_at": now_iso,
            "source_page": "/join-a-board",
            "created_at": existing["created_at"] if existing else now_iso,
            "updated_at": now_iso,
            "status": existing.get("status", "New Applicant") if existing else "New Applicant",
            "resend_contact_id": existing.get("resend_contact_id", "") if existing else "",
            "resend_segment_status": "Pending",
            "confirmation_email_status": "Pending",
            "internal_notes": existing.get("internal_notes", "") if existing else "",
        })

        if resume and resume.filename:
            resume_data = await store_resume(resume, applicant_id)
            old_file_id = existing.get("resume_file_id") if existing else None
            document.update(resume_data)
            if old_file_id:
                try:
                    await resume_bucket.delete(ObjectId(old_file_id))
                except Exception:
                    pass
        elif existing:
            for key in ("resume_file_id", "resume_filename", "resume_content_type"):
                if key in existing:
                    document[key] = existing[key]

        await db.board_applicants.update_one(
            {"email": normalized_email}, {"$set": document}, upsert=True,
        )

        try:
            contact_id = await sync_board_applicant(document)
            document["resend_contact_id"] = contact_id
            document["resend_segment_status"] = "Synced"
            document["resend_sync_error"] = ""
        except Exception as exc:
            document["resend_segment_status"] = "Failed"
            document["resend_sync_error"] = str(exc)[:500]
            await send_automation_error(
                db, failure_key=f"applicant-sync:{applicant_id}:{now_iso}", automation="Board applicant Resend contact sync",
                contact_or_report_type="board applicant", error=str(exc), submission_saved=True,
                email_sent=False, corrective_action="Review the Resend API key, Board Applicants segment and applicant updates Topic, then sync this applicant contact again.",
            )

        try:
            email_id = await send_applicant_confirmation(document)
            document["confirmation_email_status"] = "Sent"
            document["confirmation_email_id"] = email_id
            document["confirmation_email_error"] = ""
        except Exception as exc:
            document["confirmation_email_status"] = "Failed"
            document["confirmation_email_error"] = str(exc)[:500]

        await db.board_applicants.update_one(
            {"email": normalized_email},
            {"$set": {key: value for key, value in document.items() if key.startswith("resend_") or key.startswith("confirmation_")}},
        )
        return ApplicantResponse(
            applicant_id=applicant_id,
            first_name=document["first_name"],
            last_name=document["last_name"],
            email=normalized_email,
            country=document["country"],
            created=created,
            resend_sync_status=document["resend_segment_status"],
            confirmation_email_status=document["confirmation_email_status"],
        )

    @router.post("/auth/login")
    async def admin_login(credentials: AdminLogin, request: Request, response: Response):
        email = str(credentials.email).lower()
        identifier = email
        attempt = await db.login_attempts.find_one({"identifier": identifier}, {"_id": 0})
        if attempt and attempt.get("locked_until"):
            locked_until = datetime.fromisoformat(attempt["locked_until"])
            if locked_until > datetime.now(timezone.utc):
                raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 15 minutes.")
        user = await db.users.find_one({"email": email, "role": "admin"})
        if not user or not verify_password(credentials.password, user["password_hash"]):
            failures = (attempt or {}).get("failures", 0) + 1
            update = {"failures": failures, "updated_at": datetime.now(timezone.utc).isoformat()}
            if failures >= 5:
                update["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
            await db.login_attempts.update_one({"identifier": identifier}, {"$set": update}, upsert=True)
            raise HTTPException(status_code=401, detail="Invalid administrator email or password")
        await db.login_attempts.delete_one({"identifier": identifier})
        token = create_access_token(user["user_id"], user["email"])
        response.set_cookie(
            "admin_access_token", token, httponly=True, secure=True,
            samesite="none", max_age=ACCESS_MINUTES * 60, path="/",
        )
        return {"email": user["email"], "role": "admin"}

    @router.get("/auth/me")
    async def admin_me(admin=Depends(current_admin)):
        return admin

    @router.post("/auth/logout")
    async def admin_logout(response: Response):
        response.delete_cookie("admin_access_token", path="/", secure=True, samesite="none")
        return {"message": "Logged out"}

    @router.get("/admin/applicants")
    async def list_applicants(
        search: str = "", country: str = "", state_region: str = "", cause: str = "",
        skill: str = "", board_type: str = "", fundraising: str = "", availability: str = "",
        admin=Depends(current_admin),
    ):
        filters = {}
        if search:
            filters["$or"] = [
                {"first_name": {"$regex": search, "$options": "i"}},
                {"last_name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
            ]
        for key, value in (("country", country), ("state_region", state_region), ("causes", cause), ("skills", skill), ("board_types", board_type), ("fundraising_activities", fundraising), ("availability", availability)):
            if value:
                filters[key] = value
        applicants = await db.board_applicants.find(filters, {"_id": 0}).sort("created_at", -1).to_list(2000)
        return applicants

    @router.get("/admin/applicants/{applicant_id}")
    async def get_applicant(applicant_id: str, admin=Depends(current_admin)):
        applicant = await db.board_applicants.find_one({"applicant_id": applicant_id}, {"_id": 0})
        if not applicant:
            raise HTTPException(status_code=404, detail="Applicant not found")
        return applicant

    @router.patch("/admin/applicants/{applicant_id}")
    async def update_applicant(applicant_id: str, payload: ApplicantAdminUpdate, admin=Depends(current_admin)):
        updates = {key: value for key, value in payload.model_dump().items() if value is not None}
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await db.board_applicants.update_one({"applicant_id": applicant_id}, {"$set": updates})
        if not result.matched_count:
            raise HTTPException(status_code=404, detail="Applicant not found")
        return await db.board_applicants.find_one({"applicant_id": applicant_id}, {"_id": 0})

    @router.post("/admin/applicants/{applicant_id}/retry-resend")
    async def retry_resend(applicant_id: str, admin=Depends(current_admin)):
        applicant = await db.board_applicants.find_one({"applicant_id": applicant_id}, {"_id": 0})
        if not applicant:
            raise HTTPException(status_code=404, detail="Applicant not found")
        try:
            contact_id = await sync_board_applicant(applicant)
            await db.board_applicants.update_one(
                {"applicant_id": applicant_id},
                {"$set": {"resend_contact_id": contact_id, "resend_segment_status": "Synced", "resend_sync_error": ""}},
            )
            return {"status": "Synced", "contact_id": contact_id}
        except Exception as exc:
            await db.board_applicants.update_one(
                {"applicant_id": applicant_id},
                {"$set": {"resend_segment_status": "Failed", "resend_sync_error": str(exc)[:500]}},
            )
            raise HTTPException(status_code=502, detail="Resend sync failed") from exc

    @router.get("/admin/applicants/{applicant_id}/resume")
    async def download_resume(applicant_id: str, admin=Depends(current_admin)):
        applicant = await db.board_applicants.find_one({"applicant_id": applicant_id}, {"_id": 0})
        if not applicant or not applicant.get("resume_file_id"):
            raise HTTPException(status_code=404, detail="Résumé not found")
        stream = await resume_bucket.open_download_stream(ObjectId(applicant["resume_file_id"]))
        content = await stream.read()
        headers = {"Content-Disposition": f'attachment; filename="{applicant["resume_filename"]}"'}
        return StreamingResponse(io.BytesIO(content), media_type=applicant["resume_content_type"], headers=headers)

    @router.get("/admin/applicants-export.csv")
    async def export_applicants(ids: str = Query(""), admin=Depends(current_admin)):
        selected_ids = [item for item in ids.split(",") if item]
        filters = {"applicant_id": {"$in": selected_ids}} if selected_ids else {}
        applicants = await db.board_applicants.find(filters, {"_id": 0}).sort("created_at", -1).to_list(5000)
        output = io.StringIO()
        fields = ["applicant_id", "first_name", "last_name", "email", "phone", "country", "city", "state_region", "job_title", "professional_field", "skills", "causes", "board_types", "availability", "status", "resend_segment_status", "created_at"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for applicant in applicants:
            row = {field: applicant.get(field, "") for field in fields}
            for field in ("skills", "causes", "board_types"):
                row[field] = " | ".join(row[field]) if isinstance(row[field], list) else row[field]
            writer.writerow(row)
        return Response(
            output.getvalue(), media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=board-applicants.csv"},
        )

    @router.get("/admin/nonprofit-contacts")
    async def nonprofit_contacts(admin=Depends(current_admin)):
        contacts = await db.board_assessments.find(
            {"email_permission": True},
            {"_id": 0, "name": 1, "email": 1, "phone": 1, "organization_name": 1, "country": 1, "submitted_at": 1, "email_permission_at": 1, "resend_sync_status": 1},
        ).sort("submitted_at", -1).to_list(2000)
        return contacts

    return router