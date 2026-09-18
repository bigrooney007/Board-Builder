"""Version helpers that keep changed narration scripts and recordings in sync."""
import hashlib

SOURCE_REVISION = "teaching-first-2026-09-18"


def script_hash(text: str) -> str:
    return hashlib.sha256(str(text or "").strip().encode("utf-8")).hexdigest()


def resolve_script(default_text: str, stored: dict, force_revision: bool = False) -> dict:
    """Adopt revised defaults while preserving deliberate admin edits (version 2+)."""
    stored = stored or {}
    stored_text = str(stored.get("text") or "").strip()
    stored_version = max(1, int(stored.get("script_version") or 1))
    stored_revision = str(stored.get("source_revision") or "")
    if stored_text and (stored_revision == SOURCE_REVISION or stored_version > 1):
        text = stored_text
        version = stored_version
    else:
        text = str(default_text or "").strip()
        version = max(2, stored_version + 1) if force_revision and stored_revision != SOURCE_REVISION else stored_version
    return {
        "text": text,
        "script_version": version,
        "source_revision": SOURCE_REVISION,
        "script_hash": script_hash(text),
    }


def recording_status(audio: dict, script: dict) -> str:
    if not audio or audio.get("status") != "ready":
        return "missing"
    if int(audio.get("script_version") or 0) != int(script.get("script_version") or 0):
        return "needs_regeneration"
    if audio.get("source_revision") and audio.get("source_revision") != script.get("source_revision"):
        return "needs_regeneration"
    if audio.get("script_hash") and audio.get("script_hash") != script.get("script_hash"):
        return "needs_regeneration"
    return "ready"
