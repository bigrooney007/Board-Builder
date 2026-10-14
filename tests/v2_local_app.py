"""Local-only acceptance app: real V2 routers, synthetic data, fake providers.

    python tests/v2_local_app.py --port 8765

This never imports backend/server.py, loads .env, connects to MongoDB, creates a
real Stripe charge or sends a real email. It serves the actual frontend build
when available. Test helper routes exist only in this process-local fixture app.
"""

import argparse
import asyncio
from contextlib import asynccontextmanager, suppress
import html
import os
from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from tests.v2_fixture import Database
from tests.v2_test_providers import external_import_guards, FakeStripe, FakeEmailTransport, FakeStructuredAI


def create_fixture_app(port=8765, frontend_dir=None):
    local_origin = f"http://127.0.0.1:{port}"
    os.environ.update({
        "NBB_V2_ENABLED": "true", "NBB_V2_ORIGIN": local_origin,
        "NBB_V2_PREVIEW_KEY": "synthetic-preview-only-key",
        "NBB_V2_SESSION_SECRET": "synthetic-session-secret-at-least-32-characters",
        "JWT_SECRET": "synthetic-original-jwt-secret-at-least-32-characters",
        "NBB_V2_STRIPE_SECRET_KEY": "sk_test_synthetic_never_use_network",
        "NBB_V2_PAYMENTS_TEST_ONLY": "true", "NBB_V2_NETWORK_LIVE_ENABLED": "false",
        "NBB_V2_EMAIL_TEST_MODE": "true",
        "NBB_V2_TEST_EMAILS": "leader@example.test,candidate@example.test,board@example.test,opted-in@example.test",
        "RESEND_API_KEY": "", "MONGO_URL": "", "ANTHROPIC_API_KEY": "",
        "BOARD_APPLICANT_SENDER": "Board Builder <network@example.test>", "NONPROFIT_SENDER": "Board Builder <resources@example.test>",
        "OPENAI_API_KEY": "", "EMERGENT_LLM_KEY": "",
    })
    sys.modules.update(external_import_guards())
    import ai_service
    import v2_core
    import v2_email
    import v2_forms
    import v2_payments
    import v2_resources
    import v2_routes

    db, stripe, transport, ai = Database(), FakeStripe(), FakeEmailTransport(), FakeStructuredAI()
    original_create = stripe.create

    def local_checkout(**params):
        session = original_create(**params)
        session["url"] = local_origin + "/test/checkout/" + session["id"]
        stripe.sessions[session["id"]]["url"] = session["url"]
        return session

    stripe.checkout.Session.create = local_checkout
    v2_payments.stripe_sdk = lambda: stripe
    v2_email.send_provider = transport
    ai_service.generate_structured = ai
    build = Path(frontend_dir or ROOT / "frontend/build").resolve()

    @asynccontextmanager
    async def lifespan(app):
        await v2_core.create_indexes(db)
        worker = asyncio.create_task(v2_email.run_v2_jobs(db))
        yield
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker

    app = FastAPI(lifespan=lifespan)
    v2_core.install_v2_response_headers(app)
    app.state.fixture_db, app.state.fake_stripe = db, stripe
    app.state.fake_transport, app.state.fake_ai = transport, ai
    app.include_router(v2_routes.create_v2_router(db))

    @app.get("/test/health")
    async def health():
        return {"fixture": True, "providers": "synthetic", "frontend_build": (build / "index.html").exists()}

    @app.get("/test/checkout/{session_id}", response_class=HTMLResponse)
    async def checkout_page(session_id: str):
        if session_id not in stripe.sessions:
            raise HTTPException(404, "Unknown synthetic checkout")
        safe_id = html.escape(session_id, quote=True)
        return f"<html><body><h1>Synthetic test checkout</h1><p>No real payment will be charged.</p><form method='post' action='/test/checkout/{safe_id}'><button>Pay $197 in this synthetic test</button></form></body></html>"

    @app.post("/test/checkout/{session_id}")
    async def pay(session_id: str):
        if session_id not in stripe.sessions:
            raise HTTPException(404, "Unknown synthetic checkout")
        stripe.pay(session_id)
        call = next(call for call in stripe.calls if call["client_reference_id"] == stripe.sessions[session_id]["client_reference_id"])
        return RedirectResponse(call["success_url"].replace("{CHECKOUT_SESSION_ID}", session_id), status_code=303)

    @app.get("/test/emails")
    async def emails():
        return {"emails": await db.v2_email_outbox.find({}, {"_id": 0}).to_list(None)}

    @app.get("/test/state")
    async def state():
        return {"journeys": await db.v2_journeys.find({}, {"_id": 0}).to_list(None),
                "resources": await db.v2_resources.find({}, {"_id": 0}).to_list(None),
                "submissions": await db.v2_submissions.find({}, {"_id": 0}).to_list(None)}

    @app.get("/{page_path:path}")
    async def frontend(page_path: str):
        if page_path.startswith("api/"):
            raise HTTPException(404, "Unknown API route")
        requested = (build / page_path).resolve()
        if not requested.is_relative_to(build):
            raise HTTPException(404)
        if requested.is_file():
            return FileResponse(requested)
        if not (build / "index.html").is_file():
            raise HTTPException(503, "The actual frontend build is missing. Build frontend before running browser acceptance.")
        headers = {"X-Robots-Tag": "noindex, nofollow, noarchive", "Cache-Control": "no-store"} if page_path.startswith("v2") else {}
        return FileResponse(build / "index.html", headers=headers)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--frontend-dir")
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(create_fixture_app(args.port, args.frontend_dir), host="127.0.0.1", port=args.port)
