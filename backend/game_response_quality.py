"""Shared response validation and exact-answer helpers for the guided game."""
import hashlib
import re
import unicodedata

NON_ANSWERS = {
    "yes", "no", "ok", "okay", "none", "nothing", "not sure", "i don't know",
    "i dont know", "n/a", "na", "nil", "skip", "continue",
}
NON_ANSWER_TOKENS = {
    "yes", "no", "ok", "okay", "none", "nothing", "not", "sure", "i", "don't",
    "dont", "know", "n", "a", "na", "nil", "skip", "continue",
}


def _flatten(values):
    for value in values:
        if isinstance(value, (list, tuple, set)):
            yield from _flatten(value)
        elif value is not None and str(value).strip():
            yield str(value).strip()


def _normalized(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    text = re.sub(r"[^\w'’]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def is_meaningful_game_response(*values) -> bool:
    """Reject blanks and confirmations without rejecting concise, usable ideas such as CSR."""
    text = " ".join(_flatten(values))
    normalized = _normalized(text)
    if not normalized or normalized in NON_ANSWERS:
        return False
    tokens = normalized.replace("’", "'").split()
    if not tokens or all(token in NON_ANSWER_TOKENS for token in tokens):
        return False
    return sum(character.isalpha() for character in normalized) >= 3


def response_texts(response: dict) -> list[str]:
    """Return the player's one current answer once, even when legacy fields duplicate it."""
    response = response or {}
    extras = response.get("extras") if isinstance(response.get("extras"), dict) else {}
    candidates = [extras.get("second_response")]
    candidates.extend(response.get("final_response") or [])
    current = []
    seen = set()
    for text in _flatten(candidates):
        key = _normalized(text)
        if key and key not in seen:
            current.append(text)
            seen.add(key)
    if current:
        return current
    return list(_flatten(response.get("first_response") or []))


def original_idea_text(response: dict) -> str:
    """Return exactly what the participant entered, with no AI rewriting."""
    return "\n\n".join(response_texts(response)).strip()


def response_input_hash(response: dict) -> str:
    return hashlib.sha256(original_idea_text(response).encode("utf-8")).hexdigest()

