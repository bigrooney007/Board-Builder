"""$197 V2 checkout using existing Stripe infrastructure and transaction records."""
import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from v2_core import CURRENCY, PRICE_CENTS, PRODUCTS, ensure_paid, find_journey, new_id, now_iso, origin


def stripe_sdk():
    import stripe
    return stripe


def stripe_key():
    key = os.environ.get("NBB_V2_STRIPE_SECRET_KEY") or os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        raise HTTPException(503, "Payments need to be configured before checkout is available.")
    if os.environ.get("NBB_V2_PAYMENTS_TEST_ONLY", "false").lower() == "true" and not key.startswith(("sk_test_", "rk_test_")):
        raise HTTPException(503, "This preview accepts test payments only.")
    return key


def purchase_source(product):
    return "v2_" + product.replace("-", "_") + "_197"


async def checkout(db, journey):
    from v2_forms import complete_intake
    if not complete_intake(journey["product"], journey.get("answers") or {}):
        raise HTTPException(409, "Finish your introductory questions before purchasing.")
    if journey.get("state") == "paid":
        raise HTTPException(409, "You have already purchased this product. Open your resources.")
    key = stripe_key()
    # A pending checkout can be reopened, so a double-click cannot create two
    # independent charges for the same purchase attempt.
    old = await db.payment_transactions.find_one({"journey_id": journey["journey_id"], "journey_version": "v2",
                                                  "payment_status": "unpaid", "status": "open"}, {"_id": 0})
    if old and old.get("checkout_url") and old.get("expires_at", "") > now_iso():
        return {"checkout_url": old["checkout_url"], "session_id": old["session_id"]}
    attempt = journey.get("checkout_attempt") or new_id()
    await db.v2_journeys.update_one({"journey_id": journey["journey_id"], "checkout_attempt": {"$exists": False}},
                                   {"$set": {"checkout_attempt": attempt}})
    latest = await find_journey(db, journey["journey_id"])
    attempt = latest.get("checkout_attempt") or attempt
    metadata = {"journey_version": "v2", "journey_id": journey["journey_id"], "product": journey["product"],
                "purchase_source": purchase_source(journey["product"])}
    params = {"mode": "payment", "customer_email": journey["email"], "client_reference_id": journey["journey_id"],
              "line_items": [{"price_data": {"currency": CURRENCY, "unit_amount": PRICE_CENTS,
                 "product_data": {"name": PRODUCTS[journey["product"]] + " | Self-Guided V2"}}, "quantity": 1}],
              "metadata": metadata, "payment_intent_data": {"metadata": metadata},
              "success_url": f"{origin()}/v2/{journey['product']}/payment?journey_id={journey['journey_id']}&session_id={{CHECKOUT_SESSION_ID}}",
              "cancel_url": f"{origin()}/v2/{journey['product']}/offer?journey_id={journey['journey_id']}&checkout=cancelled"}
    try:
        session = stripe_sdk().checkout.Session.create(**params, api_key=key, idempotency_key="nbb-v2-checkout-" + attempt)
        session_id, url = session.get("id"), session.get("url")
        if not session_id or not url:
            raise RuntimeError("Incomplete checkout response")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "Checkout could not be opened. Please try again. No access has been activated.") from exc
    expires = session.get("expires_at")
    expiry = datetime.fromtimestamp(expires, timezone.utc).isoformat() if isinstance(expires, (float, int)) else (datetime.now(timezone.utc) + timedelta(hours=23)).isoformat()
    await db.payment_transactions.update_one({"session_id": session_id}, {"$setOnInsert": {
        "session_id": session_id, "journey_id": journey["journey_id"], "journey_version": "v2",
        "offer_source": "v2:" + journey["product"], "purchase_source": metadata["purchase_source"],
        "amount": PRICE_CENTS, "currency": CURRENCY, "product": journey["product"], "lead_email": journey["email"],
        "status": "open", "payment_status": "unpaid", "checkout_url": url, "expires_at": expiry,
        "created_at": now_iso(), "updated_at": now_iso()}}, upsert=True)
    return {"checkout_url": url, "session_id": session_id}


def validate_session(session, transaction):
    meta = session.get("metadata") or {}
    expected = {"journey_version": "v2", "journey_id": transaction["journey_id"], "product": transaction["product"],
                "purchase_source": transaction["purchase_source"]}
    if (session.get("id") != transaction["session_id"] or any(meta.get(k) != v for k, v in expected.items())
            or session.get("mode") != "payment" or session.get("currency") != CURRENCY
            or session.get("amount_total") != PRICE_CENTS
            or session.get("amount_subtotal", PRICE_CENTS) != PRICE_CENTS):
        raise HTTPException(403, "This payment does not match this product purchase.")
    if os.environ.get("NBB_V2_PAYMENTS_TEST_ONLY", "false").lower() == "true" and session.get("livemode", False):
        raise HTTPException(403, "A live payment cannot activate this test journey.")


async def activate_journey(db, journey_id):
    journey = await find_journey(db, journey_id)
    ensure_paid(journey)
    if journey.get("activation_status") == "complete":
        return journey
    # Seed operations are individually idempotent and can recover after an
    # interrupted webhook or a missing generator configuration.
    from v2_email import queue_email
    try:
        await queue_email(db, "welcome:" + journey_id, journey["email"], "Your " + PRODUCTS[journey["product"]] + " Resources",
            "Your payment is confirmed. Confirm your organization details next. For meeting-based services, set your next board meeting date and time before inviting participants. For recruitment, review and approve your board member profiles before we prepare the recruitment pack. Your saved resources will remain available in one secure collection.",
            journey_id=journey_id, action_path="/v2/setup/" + journey_id)
        await db.v2_journeys.update_one({"journey_id": journey_id},
            {"$set": {"activation_status": "complete", "generation_status": "waiting_setup", "technical_issue": "", "updated_at": now_iso()}})
    except Exception:
        await db.v2_journeys.update_one({"journey_id": journey_id},
            {"$set": {"activation_status": "failed", "technical_issue": "Payment was saved, but resource preparation needs a retry.", "updated_at": now_iso()}})
        raise HTTPException(503, "Your payment is saved. Resource preparation is being retried; please reopen this link shortly.")
    return await find_journey(db, journey_id)


async def record_verified_payment(db, transaction, session):
    validate_session(session, transaction)
    if session.get("payment_status") != "paid":
        return {"payment_status": session.get("payment_status", "unpaid"), "journey_id": transaction["journey_id"], "state": "free"}
    now = now_iso()
    await db.payment_transactions.update_one({"session_id": transaction["session_id"], "journey_version": "v2"},
        {"$set": {"status": "completed", "payment_status": "paid", "payment_email": (session.get("customer_details") or {}).get("email", ""),
                  "stripe_payment_intent_id": session.get("payment_intent", ""), "updated_at": now}})
    await db.v2_purchases.update_one({"session_id": transaction["session_id"]}, {"$setOnInsert": {
        "purchase_id": new_id(), "session_id": transaction["session_id"], "journey_id": transaction["journey_id"],
        "product": transaction["product"], "journey_version": "v2", "amount": PRICE_CENTS,
        "currency": CURRENCY, "payment_status": "paid", "created_at": now}}, upsert=True)
    await db.v2_journeys.update_one({"journey_id": transaction["journey_id"]},
        {"$set": {"state": "paid", "paid_at": now, "purchase_session_id": transaction["session_id"], "updated_at": now}})
    journey = await activate_journey(db, transaction["journey_id"])
    return {"payment_status": "paid", "journey_id": journey["journey_id"], "state": journey["state"]}


async def verify_payment(db, journey_id, session_id):
    transaction = await db.payment_transactions.find_one({"session_id": session_id, "journey_id": journey_id,
                                                         "journey_version": "v2"}, {"_id": 0})
    if not transaction:
        raise HTTPException(404, "This checkout does not belong to your product.")
    try:
        session = stripe_sdk().checkout.Session.retrieve(session_id, api_key=stripe_key())
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "Payment confirmation is temporarily unavailable. Please try again.") from exc
    return await record_verified_payment(db, transaction, session)


async def handle_v2_event(db, event):
    """Called only after the existing webhook validates Stripe's signature."""
    session = (event.get("data") or {}).get("object") or {}
    if (session.get("metadata") or {}).get("journey_version") != "v2":
        return False
    from v2_core import enabled
    enabled()
    transaction = await db.payment_transactions.find_one({"session_id": session.get("id"), "journey_version": "v2"}, {"_id": 0})
    if not transaction:
        raise HTTPException(409, "The V2 checkout record is not available yet. Retry the event.")
    event_type = event.get("type")
    if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        await record_verified_payment(db, transaction, session)
    elif event_type in {"checkout.session.async_payment_failed", "checkout.session.expired"}:
        status = "failed" if event_type.endswith("failed") else "expired"
        await db.payment_transactions.update_one({"session_id": transaction["session_id"], "payment_status": {"$ne": "paid"}},
            {"$set": {"status": status, "payment_status": status, "updated_at": now_iso()}})
        await db.v2_journeys.update_one({"journey_id": transaction["journey_id"], "state": {"$ne": "paid"}},
                                       {"$unset": {"checkout_attempt": ""}})
    return True
