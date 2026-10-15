"""Canonical 24-month questions shared by intake, member forms and discussion."""
import copy
import hashlib
import json
import re
from pathlib import Path

VERSION = "strategic-24-months-15"
QUESTIONS = json.loads(Path(__file__).with_name("strategic_questions.json").read_text())
KEYS = tuple(q["key"] for q in QUESTIONS)
WELCOME = "Welcome to your Strategic Planning Session.\n\nOver the next 24 months, your organisation has an opportunity to achieve important goals and strengthen the impact of its work.\n\nEveryone has already contributed their ideas about what the organisation should achieve and how to make it happen.\n\nIn this session, you will review those ideas together, discuss them, and agree on the direction your organisation wants to take.\n\nFor each question, we will display everyone's contributions. Your facilitator will guide the conversation, and together you will select the ideas you want to adopt.\n\nAt the end, you will review everything you have agreed on before the system uses those decisions to develop your organisation's strategic plan."


def current(answers):
    return any(key in (answers or {}) for key in KEYS)


def complete(answers):
    return all(str((answers or {}).get(key) or "").strip() for key in KEYS)


def form_content():
    return {"questionnaire_version": VERSION,
            "introduction": "Share your own ideas about what your organisation should achieve in the next 24 months. You do not need to review anyone else's answers. Your ideas will be discussed together during the board meeting.",
            "sections": [{"key": q["key"], "title": q["title"], "subtitle": q["help"],
                          "questions": [{"id": q["key"], "prompt": q["prompt"], "help": q["help"], "type": "long", "options": [], "required": True}]}
                         for q in QUESTIONS]}


def session_sections(people, saved):
    sections = []
    for q in QUESTIONS:
        ideas = []
        for person in people:
            raw = str((person.get("response") or {}).get(q["key"]) or "").strip()
            if not raw:
                continue
            # Split only explicit paragraphs/list lines; never invent a paraphrase.
            chunks = [s.strip(" \t-*•") for s in re.split(r"\n\s*\n|\n(?=\s*[-*•]\s)", raw) if s.strip()]
            for index, chunk in enumerate(chunks):
                ideas.append({"idea_id": f"{person['participant_id']}:{q['key']}:{index}",
                              "participant_id": person["participant_id"], "participant_name": person.get("name", "Board Member"),
                              "question_id": q["key"], "question": q["prompt"], "idea": chunk, "source_response": raw})
        ideas.extend(copy.deepcopy((saved.get("discussion_ideas") or {}).get(q["key"], [])))
        selected = (saved.get("decisions") or {}).get(q["key"], [])
        sections.append({"key": q["key"], "title": q["prompt"], "subtitle": q["help"], "ideas": ideas,
                         "selected_idea_ids": [i for i in selected if i in {x["idea_id"] for x in ideas}],
                         "decision_mode": "selected_ideas", "allow_keep_current_mission": False,
                         "recommendations": [], "is_action_planning": q["key"] == KEYS[12],
                         "is_role_planning": q["key"] == KEYS[-1], "current_context": ""})
    return sections


def adopted_areas(sections, decisions):
    out = []
    for section in sections:
        ids = decisions.get(section["key"], [])
        if not isinstance(ids, list) or any(i not in {x["idea_id"] for x in section["ideas"]} for i in ids):
            raise ValueError("Only visible, explicitly selected ideas can be adopted")
        selected = [i for i in section["ideas"] if i["idea_id"] in ids]
        out.append({"area_key": section["key"], "area": section["title"], "subtitle": section["subtitle"],
                    "agreed_ideas": [{"participant_id": i["participant_id"], "participant_name": i["participant_name"], "text": i["idea"]} for i in selected],
                    "direction": "\n\n".join(i["idea"] for i in selected), "decision_mode": "selected_ideas", "status": "READY FOR PLAN"})
    return out


def decision_revision(areas):
    return hashlib.sha256(json.dumps(areas, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def approved_context(areas, mission=""):
    return json.dumps({"existing_mission_background_only": mission, "planning_period_months": 24,
                       "explicitly_adopted_decisions": areas}, ensure_ascii=False)


async def stored_mission(db, user_id, organization_name):
    """Reuse a supplied mission only when it belongs to this customer's organization."""
    if not user_id or not organization_name: return ""
    profile = await db.recruitment_profiles.find_one({"user_id":user_id},{"_id":0}) or {}
    data = profile.get("data") or {}
    if str(data.get("organization_name") or "").strip().casefold() != str(organization_name).strip().casefold(): return ""
    return str(data.get("mission") or "")
