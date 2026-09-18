"""Regression coverage for the teaching-first game and narration revision."""
import copy
import asyncio

import pytest
from fastapi import HTTPException

from game_finetune_routes import DecisionsPayload, create_finetune_router
from game_night_routes import SectionSave, clean_list, create_game_night_router
from game_response_quality import (
    is_meaningful_game_response,
    original_idea_text,
    response_input_hash,
    response_texts,
)
from voice_content import STATIC_NARRATIONS, TEXTS
from voice_script_state import SOURCE_REVISION, recording_status, resolve_script


def _matches(record, query):
    for key, expected in query.items():
        actual = record.get(key)
        if isinstance(expected, dict) and "$ne" in expected:
            if actual == expected["$ne"]:
                return False
        elif actual != expected:
            return False
    return True


def _set_dotted(record, key, value):
    target = record
    parts = key.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = copy.deepcopy(value)


class FakeCursor:
    def __init__(self, records):
        self.records = records

    async def to_list(self, _limit):
        return copy.deepcopy(self.records)

    def sort(self, *_args):
        return self


class FakeCollection:
    def __init__(self, records=None):
        self.records = copy.deepcopy(records or [])
        self.last_update = None

    async def find_one(self, query, _projection=None):
        return next((copy.deepcopy(row) for row in self.records if _matches(row, query)), None)

    def find(self, query, _projection=None):
        return FakeCursor([row for row in self.records if _matches(row, query)])

    async def count_documents(self, query):
        return sum(1 for row in self.records if _matches(row, query))

    async def update_one(self, query, update, upsert=False):
        self.last_update = copy.deepcopy(update)
        row = next((item for item in self.records if _matches(item, query)), None)
        if row is None and upsert:
            row = copy.deepcopy(query)
            self.records.append(row)
        if row is not None:
            for key, value in (update.get("$setOnInsert") or {}).items():
                if key not in row:
                    _set_dotted(row, key, value)
            for key, value in (update.get("$set") or {}).items():
                _set_dotted(row, key, value)
        return None


class FakeDB:
    def __init__(self, member, response):
        self.game_board_members = FakeCollection([member])
        self.game_section_responses = FakeCollection([response])
        self.game_profiles = FakeCollection([{"user_id": member["user_id"], "organization": {}}])
        self.game_nights = FakeCollection()
        self.game_situations = FakeCollection()
        self.members = FakeCollection()
        self.marketing_settings = FakeCollection()


def _endpoint(router, path, method):
    return next(route.endpoint for route in router.routes if route.path == path and method in route.methods)


def test_one_answer_is_not_duplicated_and_long_answer_is_preserved():
    long_answer = "Local employers " + ("with aligned community goals " * 220)
    response = {"final_response": [long_answer], "extras": {"second_response": long_answer}}
    assert response_texts(response) == [long_answer.strip()]
    assert original_idea_text(response) == long_answer.strip()
    assert len(clean_list([long_answer], max_chars=6000)[0]) > 600


def test_short_idea_passes_while_repeated_nonanswers_fail():
    assert is_meaningful_game_response("CSR")
    assert is_meaningful_game_response("Local banks")
    assert not is_meaningful_game_response("yes", "no", "okay", "continue")
    assert not is_meaningful_game_response("I don't know")


def test_invalid_cached_refinement_is_rejected_before_cache_is_returned():
    response = {
        "board_member_id": "m1", "section_id": 1,
        "final_response": ["Yes"], "extras": {"second_response": "Yes"},
    }
    response["fine_tuning"] = {
        "input_hash": response_input_hash(response),
        "proposals": [{"entry_id": "main", "original": "Yes", "refined": "Invented idea"}],
    }
    db = FakeDB({"token": "t1", "member_id": "m1", "user_id": "u1"}, response)
    endpoint = _endpoint(create_finetune_router(db), "/api/game/play/{token}/fine-tune/{section_id}", "POST")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(endpoint("t1", 1))
    assert exc.value.status_code == 422


def test_keep_original_saves_the_exact_participant_words():
    exact = "Local employers whose staff use our family services."
    response = {
        "board_member_id": "m1", "section_id": 1,
        "final_response": [exact], "extras": {"second_response": exact},
    }
    response["fine_tuning"] = {
        "input_hash": response_input_hash(response),
        "proposals": [{"entry_id": "main", "original": exact, "refined": "Improved text",
                       "original_is_verbatim": True}],
        "structured": [{"entry_id": "e0", "original": "AI summary", "refined": "Improved entry"}],
        "completed": False,
    }
    db = FakeDB({"token": "t1", "member_id": "m1", "user_id": "u1"}, response)
    endpoint = _endpoint(
        create_finetune_router(db),
        "/api/game/play/{token}/fine-tune/{section_id}/decisions",
        "POST",
    )
    result = asyncio.run(endpoint(
        "t1", 1,
        DecisionsPayload(entries=[{"entry_id": "main", "decision": "keep_original", "text": ""}]),
    ))
    assert result["approved_entries"][0]["text"] == exact
    assert result["approved_entries"][0]["chosen_text"] == exact
    assert len(result["approved_entries"]) == 1


def test_changed_answer_invalidates_refinement_and_preserves_locked_legacy_first_answer():
    response = {
        "board_member_id": "m1", "user_id": "u1", "section_id": 1,
        "first_move_locked": True, "first_response": ["Legacy first answer"],
        "final_response": ["Old current answer"], "extras": {"second_response": "Old current answer"},
        "fine_tuning": {"completed": True}, "approved_entries": [{"text": "Old"}],
        "approved_display": "Old", "completed": True,
    }
    member = {"token": "t1", "member_id": "m1", "user_id": "u1", "total_sections": 10}
    db = FakeDB(member, response)
    endpoint = _endpoint(
        create_game_night_router(db),
        "/api/game/play/{token}/section/{section_id}/complete",
        "POST",
    )
    asyncio.run(endpoint(
        "t1", 1,
        SectionSave(
            first_response=["Attempted overwrite"],
            final_response=["New useful answer"],
            extras={"second_response": "New useful answer"},
            first_move_locked=True,
        ),
    ))
    saved = asyncio.run(db.game_section_responses.find_one({"board_member_id": "m1", "section_id": 1}))
    assert saved["first_response"] == ["Legacy first answer"]
    assert saved["fine_tuning"] == {}
    assert saved["approved_entries"] == []
    assert saved["approved_display"] == ""


def test_teaching_clips_merge_the_retired_opening_and_are_active():
    active_ids = {item["narration_id"] for item in STATIC_NARRATIONS}
    assert not active_ids.intersection({"a1_intro", "a2_intro", "a3_intro", "a4_intro"})
    assert "Let's start with the most important question" in TEXTS["a1_deeper"]
    assert "where do we find them" in TEXTS["a2_deeper"]
    assert "Now let's talk about attraction" in TEXTS["a3_deeper"]
    assert "actual fundraising process" in TEXTS["a4_deeper"]


def test_revised_teaching_script_requires_audio_regeneration():
    script = resolve_script(
        TEXTS["a1_deeper"],
        {"text": "Old first-question teaching", "script_version": 1},
        force_revision=True,
    )
    assert script["source_revision"] == SOURCE_REVISION
    assert script["script_version"] >= 2
    assert recording_status({"status": "ready", "script_version": 1}, script) == "needs_regeneration"
    current_audio = {
        "status": "ready", "script_version": script["script_version"],
        "source_revision": script["source_revision"], "script_hash": script["script_hash"],
    }
    assert recording_status(current_audio, script) == "ready"
