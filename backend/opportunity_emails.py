"""Board Applicant Network announcements, receipts and signature emails."""
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
           else "<p>They are seeking professionals whose experience and relationships can help move the mission forward.</p>")
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
    """Real campaigns send to the applicant topic; only explicit owner review sends a preview."""
    slug = opportunity["slug"]
    view_url = f"{origin}/board-opportunities/{slug}/apply"
    subject = f"Board Leadership Opportunity | {org_name}"

    if force_test:
        test_email = os.environ.get("OWNER_TEST_EMAIL") or os.environ["OWNER_NOTIFICATION_EMAIL"]
        sample_applicant = await db.board_applicants.find_one({"email": test_email.lower()}, {"_id": 0}) or {}
        token = await create_apply_token(db, sample_applicant.get("applicant_id", "owner-preview"), opportunity["opportunity_id"])
        apply_url = f"{origin}/apply/{token}"
        email_id = await _send("BOARD_APPLICANT_SENDER", test_email, f"[Owner Preview] {subject}",
                               opportunity_email_html(opportunity, org_name, apply_url, view_url, sample_applicant.get("first_name") or "there"))
        return {"mode": "test", "broadcast_id": email_id or f"test-{secrets.token_hex(4)}", "recipients": 1}

    # A published real campaign must never silently fall back to an owner preview.
    for key in ("RESEND_API_KEY", "RESEND_BOARD_APPLICANTS_SEGMENT_ID", "RESEND_BOARD_OPPORTUNITIES_TOPIC_ID", "BOARD_APPLICANT_SENDER"):
        if not os.environ.get(key):
            raise RuntimeError(f"Applicant Network broadcast is not configured: {key}")
    # Personalized tokens + one Resend Broadcast to the existing applicant Segment/Topic.
    resend.api_key = os.environ["RESEND_API_KEY"]
    eligible = await db.board_applicants.find(
        {"board_opportunity_consent": {"$ne": False}, "status": {"$nin": ["Withdrawn", "Paused"]}, "resend_contact_id": {"$type": "string", "$ne": ""}},
        {"_id": 0, "applicant_id": 1, "email": 1, "resend_contact_id": 1},
    ).to_list(5000)
    for applicant in eligible:
        token = await create_apply_token(db, applicant["applicant_id"], opportunity["opportunity_id"])
        await resend.Contacts.update_async({
            "id": applicant["resend_contact_id"],
            "properties": {"current_opportunity_apply_url": f"{origin}/apply/{token}"},
        })
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


async def send_campaign_launch_email(db, opportunity: dict, member: dict, origin: str) -> None:
    """Send the owner a practical launch pack after the marketplace listing is live."""
    from dashboard_return import send_dashboard_return
    try:
        await send_dashboard_return(db, member, "recruitment", origin)
    except Exception:
        logger.exception("Private dashboard return email failed for %s", opportunity["opportunity_id"])
    user_id = opportunity["user_id"]
    materials = await db.generated_materials.find(
        {"user_id": user_id, "type": {"$in": ["recruitment_emails", "social_posts", "board_recruitment_job_post"]},
         "application_id": "", "status": "Approved"},
        {"_id": 0, "type": 1, "versions": 1, "current_version": 1},
    ).to_list(10)
    extracts = []
    for material in materials:
        current = next((v for v in material.get("versions", []) if v.get("version") == material.get("current_version")), {})
        extracts.append((material["type"].replace("_", " ").title(), current.get("display_text", "")[:4500]))
    apply_url = f"{origin.rstrip('/')}/board-opportunities/{opportunity['slug']}/apply"
    dashboard_url = f"{origin.rstrip('/')}/app/board-recruitment"
    network_status = opportunity.get("broadcast_status")
    if network_status == "Failed":
        network_message = "The Applicant Network announcement needs a retry. Open your dashboard to retry the distribution."
    elif opportunity.get("broadcast_mode") == "test":
        network_message = "An internal preview of the Applicant Network announcement was sent to the program owner."
    else:
        network_message = "The Applicant Network announcement has been initiated."
    body = (
        f"<p>Hello {html.escape(member.get('first_name') or 'there')},</p>"
        f"<p>Your Board recruitment campaign for <strong>{html.escape(opportunity['organization_name'])}</strong> is live. "
        f"Your opportunity is available to applicants in the Board Applicant Marketplace. {html.escape(network_message)}</p>"
        f"<p><a href='{html.escape(apply_url, quote=True)}'>View and share your Board Application</a> · "
        f"<a href='{html.escape(dashboard_url, quote=True)}'>Open your approved campaign materials</a></p>"
        "<p>Post your approved job post on LinkedIn and professional opportunity sites. Share the social copy on your organization's pages, "
        "send the outreach email to your contacts, and ask trusted people to forward the referral message. Use the same application link in every channel. "
        "The dashboard also has the short launch video for guidance.</p>"
        + "".join(f"<h3>{html.escape(title)}</h3><pre style='white-space:pre-wrap;font-family:Arial,sans-serif'>"
                  f"{html.escape(copy)}</pre>" for title, copy in extracts if copy)
        + "<p>You can review each new applicant and prepare interview, check, offer and onboarding resources in your dashboard.</p>"
    )
    try:
        email_id = await _send("NONPROFIT_SENDER", member["email"],
                               f"Your Board Recruitment Campaign Is Live | {opportunity['organization_name']}",
                               _wrap("Your Campaign Is Live", body))
        await db.opportunities.update_one({"opportunity_id": opportunity["opportunity_id"]},
            {"$set": {"launch_email_status": "Sent", "launch_email_id": email_id, "launch_email_at": datetime.now(timezone.utc).isoformat()}})
    except Exception as exc:
        logger.exception("Campaign launch email failed for %s", opportunity["opportunity_id"])
        await db.opportunities.update_one({"opportunity_id": opportunity["opportunity_id"]},
            {"$set": {"launch_email_status": "Failed", "launch_email_error": str(exc)[:300]}})


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
