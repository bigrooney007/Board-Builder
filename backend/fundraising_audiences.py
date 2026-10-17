"""Audience-specific data and decisions for the existing Fundraising Game."""
import copy
import hashlib
import json
from fastapi import HTTPException

VERSION = 6
CATEGORIES = ("individuals", "businesses", "grantmakers")
LABELS = {"individuals": "Individuals", "businesses": "Businesses", "grantmakers": "Grantmakers"}
FIELDS = ("who_why", "where", "attraction", "process", "ask", "amount")
INSTRUCTIONS = "We want to hear your ideas about the people, businesses and grantmakers who may have strong reasons to fund our mission. Share what you think, based on your own experience and understanding. You don't need to know every answer. Your ideas will be reviewed together during our fundraising strategy meeting."
PARTICIPATION = "How do you see yourself participating in helping our organization raise money and achieve its fundraising goal?"
PARTICIPATION_HELP = "Think about the relationships, skills, experience, time, introductions or fundraising activities you would be willing to contribute."
QUESTIONS = {
    "individuals": [
        ("What specific type of individual are you thinking about, and why do you believe they would have strong reasons to fund our mission?", "Think about people whose experiences, interests, values or circumstances may connect them to the work our organization does."),
        ("Where do you think our organization could find these individuals?", "Think about the communities, networks, organizations, events or other places where we might be able to reach them."),
        ("What do you think we could do to attract their attention and interest in our mission?", "Think about the messages, activities, relationships or opportunities that could make them interested in what our organization does."),
        ("How do you think we could build relationships with these individuals and raise money from them?", "Think about how we could approach them, develop their interest and invite them to support our work."),
        ("What specifically do you think we should ask these individuals to fund or support?", "Consider a program, project, organizational need or result that could give them a clear reason to contribute."),
        ("How much do you think we should ask these individuals to contribute?", "If you have an amount in mind, share it. You can also explain why you think that amount would be appropriate."),
    ],
    "businesses": [
        ("What specific type of business, and why would it have strong reasons to support our mission?", "Think about businesses whose interests, customers or community priorities connect to our mission."),
        ("Where could we find businesses like this?", "Consider networks, associations, places and people who could introduce us."),
        ("How could we attract their interest?", "Describe a relevant benefit, opportunity or evidence that would establish credibility."),
        ("How could we develop relationships and raise money from these businesses?", "Explain how we could approach them and build a relationship before asking for support."),
        ("What should we ask them to fund or support?", "Identify the program, project or organizational need they might support."),
        ("How much should we ask them to contribute?", "Share an amount and your reasoning, or say that you are unsure."),
    ],
    "grantmakers": [
        ("Which type of grantmaker, and why would its funding interests align with our mission?", "Describe the funding priorities that connect to our work."),
        ("Where could we identify and find these grantmakers?", "Consider funding sources, networks and directories you know."),
        ("How could we attract their interest or demonstrate that our organization fits their funding priorities?", "Describe relevant evidence, relationships or information."),
        ("How could we approach them and successfully pursue funding?", "Think about eligibility, relationships, applications and appropriate follow-up."),
        ("What program, project or organizational need should we seek funding for?", "Identify a purpose that fits both our mission and the grantmaker's priorities."),
        ("How much should we request?", "Share an estimate and your reasoning, or indicate what still needs to be confirmed."),
    ],
}


LAUNCH_VERSION = 7
PARTICIPATION_LAUNCH = "How do you see yourself participating and supporting your organization to reach this fundraising goal?"
LAUNCH_INSTRUCTIONS = "You can write or speak your answers freely. There are no perfect answers expected. We want your ideas about who should fund this mission and how the organization could raise money from them."

def configuration(version=VERSION):
    result = {"workflow_version": version, "categories": list(CATEGORIES), "labels": LABELS,
            "opening_questions": {"individuals":"Do you know a specific type of individual who would have strong reasons to fund our organization's mission?", "businesses":"Do you know a specific type of business that would have strong reasons to support our organization's mission?", "grantmakers":"Do you know a specific type of grantmaker that would have strong reasons to fund our mission?"},
            "another_questions": {"individuals":"Do you know another type of individual who could have strong reasons to fund our mission?", "businesses":"Do you know another type of business that could have strong reasons to support our mission?", "grantmakers":"Do you know another type of grantmaker that could fund our mission?"},
            "instructions": INSTRUCTIONS, "participation_question": PARTICIPATION, "participation_help": PARTICIPATION_HELP,
            "questions": {cat: [{"key": field, "prompt": text, "help": helper} for field, (text, helper) in zip(FIELDS, QUESTIONS[cat])] for cat in CATEGORIES}}
    if version == LAUNCH_VERSION:
        result.update(instructions=LAUNCH_INSTRUCTIONS, participation_question=PARTICIPATION_LAUNCH)
        result["categories"].append("other")
        result["labels"]={**LABELS,"other":"Other Funding Audiences"}
        result["opening_questions"]["other"]="Is there another type of funding audience you would like to recommend?"
        result["another_questions"]["other"]="Would you like to recommend another funding audience?"
        result["questions"]["other"]=[dict(q) for q in result["questions"]["individuals"][:5]]
        result["questions"]["other"][0].update(prompt="Who should fund the mission, and why?",help="Describe this audience and why it has a strong reason to support the mission.")
        result["questions"]["other"][1].update(prompt="Where could your organization find this audience?",help="Share the places, communities or networks you know.")
        result["questions"]["other"][2].update(prompt="How could your organization attract this audience?",help="Explain how you would build interest and credibility.")
        result["questions"]["other"][3].update(prompt="How could your organization raise money from this audience?",help="Describe the approach you recommend, or say where you are unsure.")
        result["questions"]["other"][4].update(prompt="What should we ask for, and how much?",help="Explain the request and recommended amount, or indicate uncertainty.")
        for cat in CATEGORIES:
            result["questions"][cat] = result["questions"][cat][:5]
            result["questions"][cat][4].update(prompt="What should we ask for, and how much?", help="Explain what this audience should support, the amount you recommend, and why. If you are unsure, say so.")
    return result


def clean_response(payload, *, submitting=False, version=None):
    version = version or payload.get("workflow_version") or VERSION
    if version not in (VERSION, LAUNCH_VERSION): raise HTTPException(422, "Unsupported questionnaire version")
    required_fields = FIELDS[:5] if version == LAUNCH_VERSION else FIELDS
    if not isinstance(payload, dict) or len(json.dumps(payload)) > 1_000_000:
        raise HTTPException(422, "Please keep your contribution within the form's storage capacity")
    if not isinstance(payload.get("audiences") or {},dict) or not isinstance(payload.get("category_status") or {},dict):
        raise HTTPException(422,"Use the separate audience and category fields")
    audiences = {}; seen = set()
    categories=(*CATEGORIES,"other") if version==LAUNCH_VERSION else CATEGORIES
    for cat in categories:
        bucket = (payload.get("audiences") or {}).get(cat, [])
        if not isinstance(bucket, list): raise HTTPException(422, "Each audience must be saved separately")
        audiences[cat] = []
        for raw in bucket:
            if not isinstance(raw, dict): raise HTTPException(422, "Enter a valid audience")
            item = {key: str(raw.get(key) or "").strip()[:12000] for key in FIELDS}
            ident = str(raw.get("id") or "").strip()
            if not ident or ident in seen or len(ident) > 100: raise HTTPException(422, "Each audience needs its own unique identifier")
            seen.add(ident); item["id"] = ident
            if submitting and any(not item[key] for key in required_fields):
                raise HTTPException(422, "Complete each audience's answers, or say where you are unsure")
            audiences[cat].append(item)
    participation = str(payload.get("involvement") or "").strip()[:12000]
    if submitting and not participation: raise HTTPException(422, "Tell us how you would like to participate")
    progress = payload.get("progress") or {}
    if not isinstance(progress, dict): raise HTTPException(422, "Invalid progress")
    if progress.get("phase", "welcome") not in {"welcome","gate","answer","participation","review"}: raise HTTPException(422,"Invalid questionnaire step")
    if any(not isinstance(progress.get(key,0),int) or not 0 <= progress.get(key,0) <= limit for key,limit in (("category",3 if version == LAUNCH_VERSION else 2),("question",4 if version == LAUNCH_VERSION else 5),("audience_index",100000))): raise HTTPException(422,"Invalid questionnaire progress")
    if submitting and not all((payload.get("category_status") or {}).get(cat) == "complete" for cat in CATEGORIES):
        raise HTTPException(422, "Finish or skip each funding category")
    return {"workflow_version": version, "game_version": version, "audiences": audiences, "involvement": participation,
            "progress": {k: progress[k] for k in ("category", "audience_index", "question", "phase") if k in progress},
            "category_status": {cat: (payload.get("category_status") or {}).get(cat, "complete" if cat=="other" else "") for cat in categories}}


def proposed_audiences(responses, members):
    people = {m["member_id"]: m for m in members}
    if any(r.get("workflow_version") == LAUNCH_VERSION for r in responses):
        responses = sorted(responses, key=lambda r: bool(people.get(r.get("board_member_id"), {}).get("is_primary")))
    proposals = []; statements = []
    categories=(*CATEGORIES,"other") if any(r.get("workflow_version")==LAUNCH_VERSION for r in responses) else CATEGORIES
    for cat in categories:
        for response in responses:
            member = people.get(response.get("board_member_id"))
            if not member: continue
            bucket = (response.get("audiences") or {}).get(cat) or []
            # Safe read adapter for older one-audience-per-category submissions.
            if not isinstance(bucket, list):
                legacy = bucket
                bucket = [{"id": "legacy-" + cat, "who_why": "\n".join(filter(None, [legacy.get("audience"), legacy.get("reason")])),
                           "where": legacy.get("where", ""), "attraction": legacy.get("attraction", ""),
                           "process": legacy.get("process", ""), "ask": legacy.get("funding_ask", ""), "amount": "Not separately supplied"}] if legacy.get("enabled") else []
            for item in bucket:
                proposals.append({"id": f"{member['member_id']}:{item['id']}", "category": cat,
                                  "member_id": member["member_id"], "contributor": member["full_name"], "strategy": copy.deepcopy(item)})
    for response in responses:
        member = people.get(response.get("board_member_id"))
        if member and response.get("involvement"):
            statements.append({"member_id": member["member_id"], "name": member["full_name"], "statement": response["involvement"]})
    if any(r.get("workflow_version") == LAUNCH_VERSION for r in responses):
        proposals.sort(key=lambda p: bool(people.get(p.get("member_id"), {}).get("is_primary")))
    return proposals, statements


def summary(review):
    audiences = []
    for proposal in review.get("proposals", []):
        decision = (review.get("decisions") or {}).get(proposal["id"], {})
        if decision.get("status") == "adopted":
            audiences.append({**copy.deepcopy(proposal), "strategy": copy.deepcopy(decision.get("strategy") or proposal["strategy"])})
    commitments = [copy.deepcopy(x) for x in review.get("commitments", []) if x.get("confirmed")]
    content = {"audiences": audiences, "commitments": commitments}
    content["revision"] = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    return content


def document_sections(agreed, profile):
    goal = profile.get("goal") or {}; organization = (profile.get("organization") or {}).get("name", "Your organization")
    purpose = str(goal.get("purpose") or "")
    goal_text = f"${goal['amount']:,}" if isinstance(goal.get("amount"), (int, float)) else "the fundraising goal supplied by the organization"
    sections = [{"key": "executive_summary", "title": "Executive Summary", "text": f"{organization} will pursue {len(agreed['audiences'])} approved funding audiences toward {goal_text}" + (f" for {purpose}" if purpose else "") + (f" by {goal['deadline']}" if goal.get("deadline") else "") + ". The approaches and confirmed contributions below record the group's decisions. They do not guarantee a particular fundraising result."}]
    labels = [("who_why", "Audience and why they may fund us"), ("where", "Where to find them"), ("attraction", "How to attract them"), ("process", "How to develop relationships and raise money"), ("ask", "What to ask for"), ("amount", "How much to ask")]
    if profile.get("workflow_version") == LAUNCH_VERSION:
        labels = [(k, label) for k, label in labels if k != "amount"]
        labels = [(k, "What to ask for and how much" if k == "ask" else label) for k, label in labels]
    categories=(*CATEGORIES,"other") if profile.get("workflow_version")==LAUNCH_VERSION else CATEGORIES
    for cat in categories:
        for index, proposal in enumerate(x for x in agreed["audiences"] if x["category"] == cat):
            sections.append({"key": f"audience_{cat}_{index}", "title": LABELS.get(cat,"Other Funding Audiences") + ": " + proposal["strategy"]["who_why"].split("\n")[0][:120],
                             "text": "\n\n".join(label + "\n" + str(proposal["strategy"].get(key) or "Requires confirmation") for key, label in labels)})
    sections.append({"key": "board_roles", "title": "How We Have Agreed to Participate in Fundraising",
                     "text": "\n\n".join(x["name"] + "\n" + x["contribution"] + ("\nSupporting approved audiences: " + "; ".join(p["strategy"]["who_why"] for p in agreed["audiences"] if p["id"] in x.get("audience_ids", [])) if x.get("audience_ids") else "") + ("\nNext step: " + x["next_action"] if x.get("next_action") else "") for x in agreed["commitments"]) or "No individual responsibilities were confirmed."})
    return sections


async def persist_draft(collection, query, value, initial):
    """An autosave or repeated submit cannot overwrite a completed contribution."""
    await collection.update_one(query, {"$setOnInsert": {**query, **initial, "completed": False}}, upsert=True)
    return await collection.update_one({**query, "completed": {"$ne": True}}, {"$set": value})
