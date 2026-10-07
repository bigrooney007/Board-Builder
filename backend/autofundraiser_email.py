import asyncio
import logging
import os
from typing import Optional

import resend

logger = logging.getLogger(__name__)

def _from_email() -> Optional[str]:
    return (
        os.environ.get("AUTO_FUNDRAISER_FROM_EMAIL")
        or os.environ.get("RESEND_FROM_EMAIL")
        or os.environ.get("EMAIL_FROM")
    )

async def _send(to: str, subject: str, html: str) -> bool:
    key = os.environ.get("RESEND_API_KEY")
    sender = _from_email()
    if not key or not sender or not to:
        logger.info("Auto Fundraiser email skipped because email configuration is incomplete.")
        return False
    resend.api_key = key
    try:
        await asyncio.to_thread(
            resend.Emails.send,
            {"from": sender, "to": [to], "subject": subject, "html": html},
        )
        return True
    except Exception:
        logger.exception("Auto Fundraiser email failed")
        return False

def _button(url: str, label: str) -> str:
    return f"""
    <p style="margin:28px 0">
      <a href="{url}" style="background:#0b6f61;color:#fff;text-decoration:none;padding:14px 22px;border-radius:10px;font-weight:700;display:inline-block">{label}</a>
    </p>
    """

async def send_resume_email(email: str, name: str, organization: str, resume_url: str) -> bool:
    first = (name or "there").split()[0]
    return await _send(
        email,
        "Continue your Auto Fundraiser review",
        f"""
        <div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;color:#12213a;line-height:1.6">
          <h2>Hi {first}, your fundraising review is waiting.</h2>
          <p>You started showing Auto Fundraiser how {organization or "your organization"} currently raises money, but the review was not completed.</p>
          <p>You can return to the exact point you stopped and finish the diagnosis.</p>
          {_button(resume_url, "CONTINUE MY FUNDRAISING REVIEW")}
        </div>
        """,
    )

async def send_payment_email(email: str, name: str, organization: str, result_url: str) -> bool:
    first = (name or "there").split()[0]
    return await _send(
        email,
        "Your fundraising strategy diagnosis is ready",
        f"""
        <div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;color:#12213a;line-height:1.6">
          <h2>Hi {first}, you already know where the gap is.</h2>
          <p>Auto Fundraiser reviewed the fundraising approach you shared for {organization or "your organization"} and identified the strategic gap that needs to be addressed.</p>
          <p>The next step is to build the fundraising strategy that closes that gap and gives your organization a clear system to execute.</p>
          {_button(result_url, "RETURN TO MY DIAGNOSIS")}
        </div>
        """,
    )

async def send_contributor_invite(email: str, name: str, organization: str, invite_url: str, inviter: str) -> bool:
    first = (name or "there").split()[0]
    return await _send(
        email,
        f"{organization}: contribute to the fundraising strategy",
        f"""
        <div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;color:#12213a;line-height:1.6">
          <h2>Hi {first}, {inviter or organization} invited you to contribute.</h2>
          <p>{organization} is building its fundraising strategy with Auto Fundraiser. Your ideas will be brought into the planning meeting for the organization to review and decide what should be adopted.</p>
          <p>You will answer five fundraising questions and tell the organization how you would be comfortable supporting fundraising.</p>
          {_button(invite_url, "CONTRIBUTE MY IDEAS")}
        </div>
        """,
    )

async def send_contribution_notification(email: str, leader_name: str, contributor_name: str, organization: str, planning_url: str) -> bool:
    first = (leader_name or "there").split()[0]
    return await _send(
        email,
        f"{contributor_name} contributed to your fundraising strategy",
        f"""
        <div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;color:#12213a;line-height:1.6">
          <h2>Hi {first}, {contributor_name} has completed the planning form.</h2>
          <p>Their ideas for {organization} are now saved and will be available in your group fundraising planning review.</p>
          {_button(planning_url, "VIEW MY FUNDRAISING PLANNING")}
        </div>
        """,
    )
