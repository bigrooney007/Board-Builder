"""Personalized recommendation email: ONE AI call per submitted lead. Deterministic prices/URLs/guarantee."""
import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

import resend
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)

GUARANTEE = "Your investment is protected by our 100% money-back guarantee."

OFFER_FACTS = {
    "reactivation": {
        "offer": "Board Reactivation",
        "url": "https://nonprofitboardbuilder.com/board-reactivation",
        "scope": "Rooney will work with them to determine who on their current Board is ready to step up, who may need to step down, and how to rebuild an active Board around the people who are ready to serve.",
        "options": "Option 1 — Become Your Organization's Board Builder (self-guided Complete Board Transformation system): Regular Price $997, Your 7-Day Discount Price $497. Option 2 — Work directly with Rooney on Board Reactivation: $2,997.",
    },
    "recruitment": {
        "offer": "Board Recruitment",
        "url": "https://nonprofitboardbuilder.com/board-recruitment",
        "scope": "Rooney will work with them to identify the Board Members their organization needs, launch the recruitment campaign, interview and select the right candidates, and move them through appointment and onboarding.",
        "options": "Option 1 — Become Your Organization's Board Builder (self-guided Complete Board Transformation system): Regular Price $997, Your 7-Day Discount Price $497. Option 2 — Work directly with Rooney on Board Recruitment: $3,997.",
    },
    "activation": {
        "offer": "Board Fundraising Activation",
        "url": "https://nonprofitboardbuilder.com/board-fundraising-activation",
        "scope": "Rooney will work with them and their Board to build the Fundraising Strategy, adopt it together, agree how each Board Member will participate, and equip the Board to begin executing the plan.",
        "options": "Option 1 — Become Your Organization's Board Builder (self-guided Complete Board Transformation system): Regular Price $997, Your 7-Day Discount Price $497. Option 2 — Work directly with Rooney on Board Fundraising Activation: $4,997.",
    },
    "complete_transformation": {
        "offer": "Complete Board Transformation",
        "url": "https://nonprofitboardbuilder.com/complete-board-transformation",
        "scope": "The process will reactivate the present Board, recruit the people the organization is missing, and activate the complete Board to raise money and work with the organization to build its fundraising system.",
        "options": "Option 1 — Become Your Organization's Board Builder (self-guided Complete Board Transformation system): Regular Price $997, Your 7-Day Discount Price $497. Option 2 — Work directly with Rooney on the Complete Board Transformation: $5,997.",
    },
}

PROMPT_RULES = (
    "You are writing ONE short recommendation email (250-450 words) as Rooney Akpesiri of Nonprofit Board Builder, "
    "responding personally to a nonprofit leader who just told us what is happening with their Board.\n"
    "Voice: direct, warm, experienced, confident, practical, personal. No emojis, no consultant jargon, no generic AI language, "
    "no exaggerated praise, no excessive bullets or headings, do not repeatedly say 'based on your responses'.\n"
    "HARD RULES:\n"
    "- Use ONLY the facts in the context. Never invent Board problems, motivations, finances, deadlines, scarcity or expiration dates.\n"
    "- Reflect their actual situation (their Board count and what they wrote) at its actual strength — never exaggerate.\n"
    "- The prescribed recommendation is FINAL. Sell ONLY the prescribed offer. No alternative service, no secondary recommendation, no cross-sell.\n"
    "- Include this exact sentence verbatim on its own line: 'Your investment is protected by our 100% money-back guarantee.'\n"
    "- Include the exact PAYMENT URL from the context after the line 'You can get started here:'. Never invent or alter URLs.\n"
    "- Present the commercial options exactly as supplied in the context (OFFER OPTIONS). Never change prices.\n"
    "- Structure: greeting with their first name (or 'Hello,' if none) -> brief thanks referencing their organization -> 1-2 short paragraphs "
    "reflecting what they told us -> a line stating: Based on what you've told us, my recommendation is [prescribed offer]. -> why it is the "
    "immediate priority -> what Rooney will work with them to accomplish (from OFFER SCOPE) -> the offer options -> guarantee line -> "
    "'You can get started here:' with the URL -> short closing tied to their stated Board problem -> sign 'Rooney Akpesiri' newline 'Nonprofit Board Builder'.\n"
    "- Subject: clearly communicate the recommendation, may use the organization name, no clickbait, no manufactured urgency.\n"
    "Respond with ONE JSON object only: {\"subject\": \"...\", \"body\": \"...\"} (body is plain text with newlines)."
)


def build_context(lead: dict) -> str:
    facts = OFFER_FACTS[lead["recommended_pathway"]]
    answers = lead.get("diagnostic_answers", {})
    return (
        f"PROSPECT NAME: {lead.get('name', '')}\n"
        f"ORGANIZATION: {lead.get('organization', '')}\n"
        f"NUMBER OF BOARD MEMBERS THEY SAID THEY HAVE: {lead.get('board_count', '')}\n"
        f"WHAT'S HAPPENING WITH THEIR BOARD (their own words): {lead.get('board_situation', '')}\n"
        f"FOUR DIAGNOSTIC ANSWERS: {json.dumps(answers)}\n"
        f"PRESCRIBED RECOMMENDATION (FINAL): {facts['offer']}\n"
        f"OFFER SCOPE: {facts['scope']}\n"
        f"OFFER OPTIONS (fixed, present exactly): {facts['options']}\n"
        f"PAYMENT URL (use exactly): {facts['url']}\n"
        f"REQUIRED GUARANTEE SENTENCE (verbatim): {GUARANTEE}"
    )


async def generate_recommendation_email(lead: dict) -> dict:
    """Exactly one AI call. Returns {subject, body} with deterministic guarantee/URL enforcement."""
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    chat = LlmChat(api_key=api_key, session_id=f"nbb-rec-email-{uuid.uuid4()}",
                   system_message="You write personal, factual emails for Nonprofit Board Builder. You never invent facts.").with_model("anthropic", model)
    raw = await chat.send_message(UserMessage(text=f"{PROMPT_RULES}\n\nCONTEXT (the only information you may use):\n{build_context(lead)}"))
    text = re.sub(r"^```(?:json)?|```$", "", str(raw).strip(), flags=re.MULTILINE).strip()
    parsed = json.loads(text[text.index("{"):text.rindex("}") + 1])
    subject = str(parsed.get("subject", "")).strip()
    body = str(parsed.get("body", "")).strip()
    facts = OFFER_FACTS[lead["recommended_pathway"]]
    if GUARANTEE not in body:
        body += f"\n\n{GUARANTEE}"
    if facts["url"] not in body:
        body += f"\n\nYou can get started here:\n{facts['url']}"
    if not subject:
        subject = f"Your Board Recommendation | {lead.get('organization', 'Your Organization')}"
    return {"subject": subject, "body": body}


def deliver_email(to_email: str, subject: str, body: str):
    resend.api_key = os.environ["RESEND_API_KEY"].strip('"')
    html = "".join(f"<p style='margin:0 0 14px 0;'>{line}</p>" for line in body.split("\n\n"))
    resend.Emails.send({
        "from": os.environ["NONPROFIT_SENDER"].strip('"'),
        "to": [to_email],
        "reply_to": [os.environ["ADMIN_EMAIL"].strip('"')],
        "subject": subject,
        "html": f"<div style='font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;color:#1a1a1a;'>{html.replace(chr(10), '<br/>')}</div>",
        "text": body,
    })


async def send_recommendation_email(db, result_token: str):
    """Background task. Idempotency is claimed by the caller before scheduling."""
    lead = await db.funnel_leads.find_one({"result_token": result_token}, {"_id": 0})
    if not lead or not lead.get("email") or lead.get("recommended_pathway") not in OFFER_FACTS:
        return
    now = datetime.now(timezone.utc).isoformat()
    try:
        email = await generate_recommendation_email(lead)
    except Exception as exc:
        logger.exception("Recommendation email generation failed for lead %s", lead.get("lead_id"))
        await db.funnel_leads.update_one({"result_token": result_token},
            {"$set": {"recommendation_email_status": "generation_failed", "recommendation_email_error": str(exc)[:500]}})
        return
    await db.funnel_leads.update_one({"result_token": result_token},
        {"$set": {"recommendation_email_status": "generated", "recommendation_email_type": lead["recommended_pathway"],
                  "generated_subject": email["subject"], "generated_body": email["body"], "generated_at": now}})
    try:
        await asyncio.to_thread(deliver_email, lead["email"], email["subject"], email["body"])
        await db.funnel_leads.update_one({"result_token": result_token},
            {"$set": {"recommendation_email_status": "sent", "recommendation_email_sent_at": datetime.now(timezone.utc).isoformat()}})
    except Exception as exc:
        logger.exception("Recommendation email delivery failed for lead %s", lead.get("lead_id"))
        await db.funnel_leads.update_one({"result_token": result_token},
            {"$set": {"recommendation_email_status": "send_failed", "recommendation_email_error": str(exc)[:500]}})
