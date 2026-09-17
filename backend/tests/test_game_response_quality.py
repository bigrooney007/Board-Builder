"""Regression tests for Board Fundraising Game response quality guardrails."""

from game_night_routes import is_meaningful_game_response
from game_finetune_routes import SYSTEM_MESSAGE


def test_rejects_blank_and_confirmation_only_responses():
    assert not is_meaningful_game_response([], [], "")
    assert not is_meaningful_game_response("", "Yes;", "")
    assert not is_meaningful_game_response(["Not sure"], [], "")


def test_accepts_short_real_fundraising_ideas():
    assert is_meaningful_game_response("", "Major donors", "")
    assert is_meaningful_game_response(
        ["Local employers connected to the families we serve"],
        ["Invite them to meet program participants"],
        "",
    )


def test_finetune_prompt_forbids_strategy_invention_from_non_answers():
    assert "do not supply one from general fundraising knowledge" in SYSTEM_MESSAGE
    assert "Never turn blanks" in SYSTEM_MESSAGE
