"""Phase 3 opportunity emails: network broadcast (safe test mode), receipts, signature emails."""
import html
import logging
import os
import secrets
from datetime import datetime, timezone

import resend

logger = logging.getLogger(__name__)


def _wrap(title: str, body_html: str) -> str:
    return f"<div style='max-width:640px;margin:auto;font-family:Arial,sans-serif;color:#111;line-height:1.6;'><h2 style='color:#083d2a;'>{html.escape(title)}</h2>{body_html}<p style='color:#667;font-size:12px;margin-top:28px;'>Nonprofit Board Builder — {html.escape(os.environ.get('POSTAL_ADDRESS', ''))}</p></div>"


async def _send(sender_env: str, to: str, subject: str, html_body: str) -> str:
    resend.api_key = os.environ["RESEND_API_KEY"]
    response = await resend.Emails.send_async({"from": os.environ[sender_env], "to": [to], "subject": subject, "html": html_body})
    return response.get("id") if isinstance(response, dict) else getattr(response, "id", "")


def opportunity_email_html(opportunity: dict, org_name: str, apply_url: str, view_url: str, first_name_merge: str = "there") -> str:
    content = opportunity.get("email_content", {})
    needs = [n.strip() for n in (content.get("candidate_needs") or "").split(",") if n.strip()]
    needs_html = "".join(f"<li>{html.escape(n)}</li>" for n in needs[:10])
    practical_bits = [b for b in [content.get("commitment", ""), content.get("location", "")] if b]
    practical = f"<p>{html.escape(' · '.join(practical_bits))}</p>" if practical_bits else ""
    deadline = f"<p><strong>Application deadline:</strong> {html.escape(content['deadline'])}</p>" if content.get("deadline") else ""
    body = (
        f"<p>Dear {first_name_merge},</p>"
        f"<p>I'm currently supporting <strong>{html.escape(org_name)}</strong> as they intentionally build their board, and I wanted to bring this opportunity to you because you have expressed interest in serving on a nonprofit board.</p>"
        f"<p><strong>{html.escape(org_name)}</strong> — {html.escape(content.get('mission', ''))}</p>"
        + (f"<h3>We're seeking professionals with experience in areas such as:</h3><ul>{needs_html}</ul>" if needs_html
           else f"<p>They are seeking professionals whose experience and relationships can help move the mission forward.</p>")
        + "<p>This is an active board leadership opportunity for professionals who want to contribute strategically, strengthen the organization through their expertise and relationships, support fundraising and partnerships, and help guide the organization's growth — meaningful contribution, not simply attending meetings.</p>"
        + practical + deadline
        + "<p>The recruitment process includes an application, interview and onboarding process designed to help both you and the organization determine whether the opportunity is a good fit.</p>"
        + "<p>If serving on a mission-driven board aligns with your interests and experience, I encourage you to apply.</p>"
        f"<p><a href='{apply_url}' style='display:inline-block;background:#087e5b;color:#fff;padding:13px 22px;border-radius:6px;text-decoration:none;font-weight:bold;'>Apply Here</a></p>"
        f"<p><a href='{view_url}'>View the Board Opportunity</a></p>"
        "<p>If you have questions about the opportunity or the recruitment process, you are welcome to reach out.</p>"
        "<p>Rooney Akpesiri<br/>The Nonprofit Board Builder</p>"
    )
    return _wrap(f"Board Leadership Opportunity | {org_name}", body)


async def create_apply_token(db, applicant_id: str, opportunity_id: str) -> str:
    token = secrets.token_urlsafe(32)
    await db.apply_tokens.insert_one({
        "token": token, "applicant_id": applicant_id, "opportunity_id": opportunity_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return token


async def send_opportunity_broadcast(db, opportunity: dict, org_name: str, origin: str, force_test: bool = False) -> dict:
    """Idempotent network announcement. Live=false or force_test (Owner Review Mode) -> owner test email only. Never emails the live Segment in test mode."""
    live = os.environ.get("BOARD_APPLICANT_OPPORTUNITY_EMAILS_LIVE", "false").lower() == "true" and not force_test
    slug = opportunity["slug"]
    view_url = f"{origin}/board-opportunities/{slug}/apply"
    subject = f"Board Leadership Opportunity | {org_name}"

    if not live:
        test_email = os.environ.get("OWNER_TEST_EMAIL") or os.environ["OWNER_NOTIFICATION_EMAIL"]
        sample_applicant = await db.board_applicants.find_one({"email": test_email.lower()}, {"_id": 0}) or {}
        token = await create_apply_token(db, sample_applicant.get("applicant_id", "owner-preview"), opportunity["opportunity_id"])
        apply_url = f"{origin}/apply/{token}"
        email_id = await _send("BOARD_APPLICANT_SENDER", test_email, f"[Owner Preview] {subject}",
                               opportunity_email_html(opportunity, org_name, apply_url, view_url, sample_applicant.get("first_name") or "there"))
        return {"mode": "test", "broadcast_id": email_id or f"test-{secrets.token_hex(4)}", "recipients": 1}

    # LIVE mode: personalized tokens + one Resend Broadcast to the existing Board Applicants Segment/Topic
    resend.api_key = os.environ["RESEND_API_KEY"]
    eligible = await db.board_applicants.find(
        {"board_opportunity_consent": {"$ne": False}, "status": {"$nin": ["Withdrawn", "Paused"]}, "resend_contact_id": {"$ne": ""}},
        {"_id": 0, "applicant_id": 1, "email": 1, "resend_contact_id": 1},
    ).to_list(5000)
    for applicant in eligible:
        token = await create_apply_token(db, applicant["applicant_id"], opportunity["opportunity_id"])
        try:
            await resend.Contacts.update_async({
                "id": applicant["resend_contact_id"],
                "properties": {"current_opportunity_apply_url": f"{origin}/apply/{token}"},
            })
        except Exception as exc:
            logger.error("Contact property update failed for %s: %s", applicant["email"], exc)
    broadcast = await resend.Broadcasts.create_async({
        "segment_id": os.environ["RESEND_BOARD_APPLICANTS_SEGMENT_ID"],
        "topic_id": os.environ["RESEND_BOARD_OPPORTUNITIES_TOPIC_ID"],
        "from": os.environ["BOARD_APPLICANT_SENDER"],
        "subject": subject,
        "html": opportunity_email_html(opportunity, org_name, "{{{current_opportunity_apply_url}}}", view_url, "{{{FIRST_NAME|there}}}"),
    })
    broadcast_id = broadcast.get("id") if isinstance(broadcast, dict) else getattr(broadcast, "id", "")
    try:
        await resend.Broadcasts.send_async({"broadcast_id": broadcast_id})
    except Exception:
        await resend.Broadcasts.send_async(broadcast_id)
    return {"mode": "live", "broadcast_id": broadcast_id, "recipients": len(eligible)}


async def send_application_receipt(email: str, name: str, org_name: str) -> str:
    body = (
        f"<p>Hello {html.escape(name)},</p>"
        f"<p>Your board application has been received by <strong>{html.escape(org_name)}</strong>.</p>"
        f"<p>Completing an application does not guarantee an interview or board appointment. You will be contacted if next steps are required.</p>"
    )
    return await _send("BOARD_APPLICANT_SENDER", email, f"Your Board Application Has Been Received — {org_name}", _wrap("Application Received", body))


async def send_signature_request(email: str, name: str, org_name: str, agreement_title: str, sign_url: str) -> str:
    body = (
        f"<p>Hello {html.escape(name)},</p>"
        f"<p><strong>{html.escape(org_name)}</strong> has sent you the <strong>{html.escape(agreement_title)}</strong> to review and sign.</p>"
        f"<p><a href='{sign_url}' style='display:inline-block;background:#087e5b;color:#fff;padding:13px 22px;border-radius:6px;text-decoration:none;font-weight:bold;'>Review and Sign the Agreement</a></p>"
        f"<p>Please review the complete agreement before signing.</p>"
    )
    return await _send("BOARD_APPLICANT_SENDER", email, f"Signature Requested — {agreement_title} — {org_name}", _wrap("Signature Requested", body))


async def send_signature_confirmations(signer_email: str, signer_name: str, owner_email: str, org_name: str, agreement_title: str) -> None:
    body = f"<p>The <strong>{html.escape(agreement_title)}</strong> for <strong>{html.escape(org_name)}</strong> has been signed by {html.escape(signer_name)}.</p><p>A copy of the signed agreement is stored in the Board Builder workspace.</p>"
    await _send("BOARD_APPLICANT_SENDER", signer_email, f"Signed — {agreement_title} — {org_name}", _wrap("Agreement Signed", body))
    await _send("NONPROFIT_SENDER", owner_email, f"Agreement Signed — {agreement_title} — {org_name}", _wrap("Agreement Signed", body))
