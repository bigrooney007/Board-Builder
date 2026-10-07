import json
import os
import re
from typing import Any, Dict, List

from openai import AsyncOpenAI

CRITERIA = [
    ("WHO", "A clearly defined fundraising audience: the specific people, businesses, companies, foundations, grantmakers or other funders the organization intends to raise money from."),
    ("WHERE", "Where the organization can consistently find, reach or encounter those ideal funders."),
    ("ATTRACT", "How the organization will consistently get the attention of those funders and build interest in the mission before asking for money."),
    ("RAISE", "A defined process for moving funders from first contact or awareness through relationship-building to a financial contribution."),
    ("ASK", "What the organization will ask funders to fund and how much it intends to ask for."),
    ("SYSTEM", "The people, recurring activities, processes, technology, follow-up and accountability required to execute the fundraising strategy consistently."),
]

def _client():
    key = os.environ.get("OPENAI_API_KEY")
    return AsyncOpenAI(api_key=key) if key else None

def _model():
    return os.environ.get("AUTO_FUNDRAISER_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini"

def _json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text or "", re.S)
        if match:
            return json.loads(match.group(0))
        raise

def _heuristic(source: str) -> Dict[str, Any]:
    lower = (source or "").lower()
    checks = {
        "WHO": any(k in lower for k in ["donor", "funder", "foundation", "business", "company", "corporate", "individual giver", "grantmaker"]),
        "WHERE": any(k in lower for k in ["linkedin", "network", "association", "database", "directory", "community", "event", "referral", "prospect"]),
        "ATTRACT": any(k in lower for k in ["content", "newsletter", "social", "event", "relationship", "engage", "awareness", "story"]),
        "RAISE": any(k in lower for k in ["meeting", "cultivat", "follow up", "follow-up", "proposal", "ask", "solicit", "donation page"]),
        "ASK": any(k in lower for k in ["$", "£", "amount", "ask for", "sponsor", "fund ", "funding need"]),
        "SYSTEM": any(k in lower for k in ["weekly", "monthly", "crm", "track", "pipeline", "responsible", "owner", "calendar", "sequence"]),
    }
    return {
        "summary": (source or "").strip()[:900],
        "criteria": {
            key: {
                "status": "PRESENT" if value else "MISSING",
                "evidence": "The submitted material appears to address this area." if value else "I could not clearly identify this area in the submitted material.",
                "confidence": 0.55,
            }
            for key, value in checks.items()
        },
    }

async def analyze_source(source: str) -> Dict[str, Any]:
    client = _client()
    if not client:
        return _heuristic(source)

    criteria_text = "\n".join(f"- {key}: {description}" for key, description in CRITERIA)
    prompt = f"""
You are Auto Fundraiser, a senior nonprofit fundraising strategist reviewing an organization's CURRENT fundraising strategy or approach.

This is a DIAGNOSTIC only. Do not build a strategy. Do not recommend ideal funders. Do not invent missing information.

Review the material against these six strategic elements:
{criteria_text}

For each element classify it as:
PRESENT = it is clearly answered in the material.
MISSING = it is not answered.
UNCLEAR = something is mentioned but it is too vague to know whether the organization actually has this part of the strategy.

Return JSON only:
{{
  "summary": "2-4 sentences describing what the organization currently appears to do, using only supplied information",
  "criteria": {{
    "WHO": {{"status":"PRESENT|MISSING|UNCLEAR","evidence":"brief evidence","confidence":0.0}},
    "WHERE": {{"status":"PRESENT|MISSING|UNCLEAR","evidence":"brief evidence","confidence":0.0}},
    "ATTRACT": {{"status":"PRESENT|MISSING|UNCLEAR","evidence":"brief evidence","confidence":0.0}},
    "RAISE": {{"status":"PRESENT|MISSING|UNCLEAR","evidence":"brief evidence","confidence":0.0}},
    "ASK": {{"status":"PRESENT|MISSING|UNCLEAR","evidence":"brief evidence","confidence":0.0}},
    "SYSTEM": {{"status":"PRESENT|MISSING|UNCLEAR","evidence":"brief evidence","confidence":0.0}}
  }}
}}

CURRENT FUNDRAISING MATERIAL:
{source[:18000]}
"""
    response = await client.chat.completions.create(
        model=_model(),
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return _json(response.choices[0].message.content)

async def build_diagnosis(lead: Dict[str, Any]) -> Dict[str, Any]:
    client = _client()
    analysis = lead.get("analysis") or {}
    clarifications = lead.get("clarifications") or {}
    if not client:
        first_gap = next((k for k, _ in CRITERIA if (analysis.get("criteria", {}).get(k, {}).get("status") != "PRESENT") or clarifications.get(k, {}).get("knows") is False), "SYSTEM")
        return {
            "headline": "Your Fundraising Approach Has A Strategic Gap",
            "what_you_told_us": analysis.get("summary") or "You shared how your organization currently approaches fundraising.",
            "what_we_found": f"The first strategic gap we can clearly identify is {first_gap}.",
            "why_it_matters": "The number one reason nonprofits struggle to raise money is because of their fundraising strategy and approach. When a critical part of the strategy is missing, fundraising becomes harder to repeat, improve and scale.",
            "biggest_gap": first_gap,
            "next_step": "Build a complete fundraising strategy before adding more fundraising activities.",
        }

    criteria_text = json.dumps(analysis.get("criteria", {}), indent=2)
    clar_text = json.dumps(clarifications, indent=2)
    prompt = f"""
You are Auto Fundraiser. Produce the final FREE fundraising diagnosis.

NON-NEGOTIABLE:
- This is a diagnosis, not a free fundraising plan.
- Do not tell the organization who its ideal funders should be.
- Do not create tactics they did not give us.
- Do not fill missing strategy gaps for them.
- Speak specifically from their material and clarification answers.
- The core product truth is exactly: "The number one reason nonprofits struggle to raise money is because of their fundraising strategy and approach."
- Explain the consequence of the FIRST meaningful gap in the sequence WHO -> WHERE -> ATTRACT -> RAISE -> ASK -> SYSTEM.
- If they explicitly said NO to an element, treat that as confirmed missing.
- If an element was PRESENT in the uploaded/written material, acknowledge it.
- Keep the result focused and persuasive without becoming long or overwhelming.

Return JSON only:
{{
  "headline": "specific diagnosis headline",
  "what_you_told_us": "2-4 sentences",
  "what_we_found": "2-4 sentences",
  "why_it_matters": "2-4 sentences",
  "biggest_gap": "WHO|WHERE|ATTRACT|RAISE|ASK|SYSTEM|NONE",
  "next_step": "1-2 sentences explaining that the next step is to build/strengthen the fundraising strategy"
}}

ORGANIZATION: {lead.get("organization_name","")}
SOURCE SUMMARY: {analysis.get("summary","")}
CRITERIA:
{criteria_text}
CLARIFICATIONS:
{clar_text}
"""
    response = await client.chat.completions.create(
        model=_model(),
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return _json(response.choices[0].message.content)

async def build_final_strategy(payload: Dict[str, Any]) -> Dict[str, Any]:
    client = _client()
    if not client:
        return {
            "title": f"{payload.get('organization_name','Organization')} Fundraising Strategy",
            "executive_summary": "This strategy brings together the organization's selected fundraising ideas, present reality and participation commitments.",
            "sections": payload,
        }

    prompt = f"""
You are Auto Fundraiser. Build the organization's FINAL fundraising strategy from the ideas the organization has deliberately selected during its planning meeting.

Use only:
1. the organizer's paid strategy answers,
2. present fundraising reality,
3. contributor responses,
4. ideas explicitly adopted in the group review,
5. participation commitments.

Do not invent named donors, businesses, grantmakers or relationships.
Make the strategy actionable and operational.
The strategy must clearly cover:
- ideal funding audience(s)
- where to find them
- how to attract them consistently
- what to ask them to fund and how much
- the step-by-step process for building relationships and raising money
- the system needed to drive the strategy consistently
- who will participate and how

Return JSON only:
{{
  "title":"...",
  "executive_summary":"...",
  "funding_audiences":[...],
  "where_to_find":[...],
  "attraction":[...],
  "ask":[...],
  "fundraising_process":[...],
  "operating_system":[...],
  "participation":[...],
  "first_30_days":[...]
}}

PLANNING DATA:
{json.dumps(payload, default=str)[:26000]}
"""
    response = await client.chat.completions.create(
        model=_model(),
        temperature=0.25,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return _json(response.choices[0].message.content)
