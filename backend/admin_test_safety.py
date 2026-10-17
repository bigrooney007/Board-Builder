"""Request-scoped email capture for the existing isolated admin client tests.

Real customers always use the original email transport. Context variables also
follow background tasks spawned by a test request, without affecting other users.
"""
import contextvars
import hashlib
from datetime import datetime, timezone
from fastapi import HTTPException

_scope = contextvars.ContextVar("nbb_admin_client_test", default=None)


def bind_test_scope(db, record):
    ident = str(record.get("user_id") or record.get("claimed_by_user_id") or record.get("project_id") or record.get("session_id") or "")
    if record.get("internal_dashboard_preview") or record.get("internal_preview") or ident.startswith("admin-dashboard-preview-"):
        _scope.set((db, ident))


def prevent_test_checkout(request, member):
    if (member.get("internal_dashboard_preview") or member.get("internal_client_test")) and "checkout" in request.url.path and not request.url.path.endswith(("/guided-checkout", "/game-checkout")):
        raise HTTPException(409, "This isolated admin test already has access. Real checkout is disabled for test accounts.")


def install_email_capture(app, db):
    import resend
    if not getattr(resend.Emails, "_nbb_test_capture", False):
        original_async = resend.Emails.send_async
        original_sync = resend.Emails.send

        def capture(params):
            scope = _scope.get()
            recipients = params.get("to") or []
            if isinstance(recipients, str): recipients = [recipients]
            synthetic = any(str(x).endswith(".internal") for x in recipients)
            return scope or ((db, "synthetic-recipient") if synthetic else None)

        async def send_async(params, *args, **kwargs):
            scope = capture(params)
            if not scope: return await original_async(params, *args, **kwargs)
            database, user = scope
            now = datetime.now(timezone.utc).isoformat()
            event = {"user_id": user, "status": "captured", "provider_delivery": False, "message": params, "created_at": now}
            result = await database.admin_test_email_events.insert_one(event)
            return {"id": "admin-test-captured-" + str(result.inserted_id), "test_capture": True}

        def send(params, *args, **kwargs):
            if not capture(params): return original_sync(params, *args, **kwargs)
            # Synchronous callers have no await point. Never dispatch test mail.
            return {"id": "admin-test-captured-" + hashlib.sha256(repr(params).encode()).hexdigest(), "test_capture": True}

        resend.Emails.send_async = staticmethod(send_async)
        resend.Emails.send = staticmethod(send)
        resend.Emails._nbb_test_capture = True

    @app.middleware("http")
    async def isolated_test_context(request, call_next):
        token = _scope.set(None)
        try: return await call_next(request)
        finally: _scope.reset(token)
