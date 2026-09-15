"""Voice Guided Individual Game backend.
Dual ElevenLabs environments: TEST voice (preview/approval) and LIVE voice (production customers).
Audio is NEVER generated automatically — only by explicit admin actions. All provider calls server-side.
Static narration: generate once per environment, stored in Mongo, replayed forever."""
import asyncio
import hashlib
import html
import os
import re
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from auth_service import authenticate_admin
from voice_content import DEFAULT_VOICE_SETTINGS, PERSONALIZED_POINTS, STATIC_NARRATIONS, TEXTS

STATIC_BY_ID = {item["narration_id"]: item for item in STATIC_NARRATIONS}
POINTS_BY_ID = {item["point_id"]: item for item in PERSONALIZED_POINTS}
ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
ENVIRONMENTS = ("test", "live")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_first_name(raw: str) -> str:
    name = re.sub(r"[^A-Za-z0-9 '\-]", "", html.unescape(str(raw or ""))).strip()
    return name.split(" ")[0][:40] if name else ""


def env_voice_id(environment: str) -> str:
    if environment == "live":
        return os.environ.get("ELEVENLABS_LIVE_VOICE_ID", "").strip()
    return (os.environ.get("ELEVENLABS_TEST_VOICE_ID", "").strip()
            or os.environ.get("ELEVENLABS_VOICE_ID", "").strip())


def mask(value: str) -> str:
    return f"…{value[-4:]}" if value else "not configured"


async def eleven_tts(text: str, voice_id: str) -> bytes:
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key or not voice_id:
        raise RuntimeError("voice provider not configured")
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            ELEVEN_URL.format(voice_id=voice_id),
            headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
            json={"text": text, "model_id": "eleven_multilingual_v2",
                  "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}})
        if response.status_code != 200:
            raise RuntimeError(f"tts failed {response.status_code}")
        return response.content


class SettingsPayload(BaseModel):
    settings: dict = Field(default_factory=dict)


class AssetTextPayload(BaseModel):
    text: str = Field(default="", max_length=8000)


class GeneratePayload(BaseModel):
    environment: str = Field(min_length=1)
    force: bool = False


class PersonalPayload(BaseModel):
    point_id: str = Field(min_length=1)


def create_voice_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")
    bulk_lock = {"running": False}

    async def get_settings() -> dict:
        doc = await db.marketing_settings.find_one({"key": "game_voice_settings"}, {"_id": 0}) or {}
        stored = doc.get("settings") if isinstance(doc.get("settings"), dict) else {}
        allowed = {**DEFAULT_VOICE_SETTINGS, "voice_environment": "test"}
        merged = {**allowed, **{k: v for k, v in stored.items() if k in allowed}}
        if merged["voice_environment"] not in ENVIRONMENTS:
            merged["voice_environment"] = "test"
        return merged

    async def text_doc(narration_id: str) -> dict:
        doc = await db.game_voice_assets.find_one({"narration_id": narration_id}, {"_id": 0, "audio": 0}) or {}
        default_text = TEXTS.get(narration_id, "")
        if not default_text and narration_id.startswith("template_"):
            point = POINTS_BY_ID.get(narration_id[len("template_"):]) or {}
            default_text = point.get("template", "")
        return {"text": (doc.get("text") or "").strip() or default_text,
                "script_version": int(doc.get("script_version") or 1)}

    async def audio_doc(narration_id: str, environment: str, include_audio: bool = False) -> dict:
        projection = {"_id": 0} if include_audio else {"_id": 0, "audio": 0}
        return await db.game_voice_audio.find_one(
            {"narration_id": narration_id, "environment": environment}, projection) or {}

    def audio_status(audio: dict, script_version: int) -> str:
        if not audio or audio.get("status") != "ready":
            return "missing"
        if int(audio.get("script_version") or 0) != script_version:
            return "needs_regeneration"
        return "ready"

    async def playing_member(token: str) -> dict:
        record = await db.game_board_members.find_one({"token": token, "removed": {"$ne": True}}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This game link is not valid")
        return record

    async def generate_static(narration_id: str, environment: str) -> None:
        script = await text_doc(narration_id)
        if not script["text"]:
            raise HTTPException(status_code=409, detail="No script text exists for this clip")
        voice_id = env_voice_id(environment)
        audio = await eleven_tts(script["text"], voice_id)
        await db.game_voice_audio.update_one(
            {"narration_id": narration_id, "environment": environment},
            {"$set": {"audio": audio, "status": "ready", "provider": "elevenlabs", "voice_id": voice_id,
                      "script_version": script["script_version"], "generated_at": now_iso()},
             "$inc": {"version": 1},
             "$setOnInsert": {"created_at": now_iso()}},
            upsert=True)

    # ---------- Public (players) ----------

    @router.get("/game/voice/settings")
    async def public_settings():
        settings = await get_settings()
        return {"settings": {key: settings[key] for key in
                             ("voice_enabled", "read_type_enabled", "default_mode", "narration_on",
                              "personalization_on", "browser_stt_on")}}

    @router.get("/game/voice/manifest/{token}")
    async def voice_manifest(token: str):
        record = await playing_member(token)
        settings = await get_settings()
        environment = settings["voice_environment"]
        rows = await db.game_voice_audio.find(
            {"environment": environment, "status": "ready"},
            {"_id": 0, "narration_id": 1, "version": 1}).to_list(300)
        ready = {row["narration_id"]: row.get("version", 1) for row in rows}
        return {
            "voice_enabled": bool(settings["voice_enabled"] and settings["narration_on"]),
            "read_type_enabled": bool(settings["read_type_enabled"]),
            "default_mode": settings["default_mode"],
            "browser_stt_on": bool(settings["browser_stt_on"]),
            "personalization_on": bool(settings["personalization_on"]),
            "first_name": clean_first_name(record.get("full_name", "")),
            "clips": {item["narration_id"]: {
                "ready": item["narration_id"] in ready,
                "url": f"/api/game/voice/audio/{item['narration_id']}?v={environment[:1]}{ready.get(item['narration_id'], 0)}",
            } for item in STATIC_NARRATIONS},
            "personal_points": [item["point_id"] for item in PERSONALIZED_POINTS],
        }

    @router.get("/game/voice/audio/{narration_id}")
    async def serve_static_audio(narration_id: str):
        if narration_id not in STATIC_BY_ID:
            raise HTTPException(status_code=404, detail="Unknown narration")
        settings = await get_settings()
        doc = await audio_doc(narration_id, settings["voice_environment"], include_audio=True)
        if doc.get("status") != "ready" or not doc.get("audio"):
            raise HTTPException(status_code=404, detail="Narration audio not available")
        return Response(content=bytes(doc["audio"]), media_type="audio/mpeg",
                        headers={"Cache-Control": "public, max-age=86400"})

    @router.get("/game/voice/audio/personal/{cache_key}")
    async def serve_personal_audio(cache_key: str):
        doc = await db.game_voice_personal_cache.find_one({"cache_key": cache_key}, {"_id": 0, "audio": 1})
        if not doc or not doc.get("audio"):
            raise HTTPException(status_code=404, detail="Clip not available")
        return Response(content=bytes(doc["audio"]), media_type="audio/mpeg",
                        headers={"Cache-Control": "public, max-age=86400"})

    @router.post("/game/voice/personal/{token}")
    async def personal_clip(token: str, payload: PersonalPayload):
        record = await playing_member(token)
        point = POINTS_BY_ID.get(payload.point_id)
        if not point:
            raise HTTPException(status_code=404, detail="Unknown personalization point")
        fallback = {"fallback_narration_id": point["fallback_id"], "url": ""}
        settings = await get_settings()
        if not settings["voice_enabled"] or not settings["narration_on"] or not settings["personalization_on"]:
            return fallback
        first_name = clean_first_name(record.get("full_name", ""))
        template = (await text_doc(f"template_{point['point_id']}"))["text"]
        if not first_name or not template or "[FIRST NAME]" not in template:
            return fallback
        environment = settings["voice_environment"]
        voice_id = env_voice_id(environment)
        text = template.replace("[FIRST NAME]", first_name)
        cache_key = hashlib.sha256(f"{text}|{environment}|{voice_id}|v1".encode()).hexdigest()
        cached = await db.game_voice_personal_cache.find_one({"cache_key": cache_key}, {"_id": 0, "cache_key": 1})
        if cached:
            return {"url": f"/api/game/voice/audio/personal/{cache_key}", "fallback_narration_id": point["fallback_id"]}
        used = int(record.get("personal_clips_generated") or 0)
        if used >= int(settings.get("max_personal_clips") or 5):
            return fallback
        try:
            audio = await eleven_tts(text, voice_id)
        except Exception:
            return fallback
        await db.game_voice_personal_cache.insert_one({
            "cache_key": cache_key, "environment": environment, "voice_id": voice_id,
            "audio": audio, "created_at": now_iso()})
        await db.game_board_members.update_one(
            {"member_id": record["member_id"]}, {"$inc": {"personal_clips_generated": 1}})
        return {"url": f"/api/game/voice/audio/personal/{cache_key}", "fallback_narration_id": point["fallback_id"]}

    # ---------- Admin ----------

    @router.get("/admin/game/voice/settings")
    async def admin_settings(request: Request):
        await authenticate_admin(request, db)
        settings = await get_settings()
        settings["provider_key_configured"] = bool(os.environ.get("ELEVENLABS_API_KEY", "").strip())
        settings["test_voice_ref"] = mask(env_voice_id("test"))
        settings["live_voice_ref"] = mask(env_voice_id("live"))
        return {"settings": settings}

    @router.put("/admin/game/voice/settings")
    async def save_settings(payload: SettingsPayload, request: Request):
        await authenticate_admin(request, db)
        allowed = set(DEFAULT_VOICE_SETTINGS) | {"voice_environment"}
        clean = {k: v for k, v in (payload.settings or {}).items() if k in allowed and k != "voice_id"}
        if "max_personal_clips" in clean:
            clean["max_personal_clips"] = max(0, min(10, int(clean["max_personal_clips"] or 0)))
        if clean.get("voice_environment") not in (None, "test", "live"):
            clean.pop("voice_environment", None)
        await db.marketing_settings.update_one(
            {"key": "game_voice_settings"},
            {"$set": {**{f"settings.{k}": v for k, v in clean.items()}, "updated_at": now_iso()}}, upsert=True)
        return await admin_settings(request)

    @router.get("/admin/game/voice/assets")
    async def list_assets(request: Request):
        await authenticate_admin(request, db)
        rows = []
        for item in STATIC_NARRATIONS:
            script = await text_doc(item["narration_id"])
            entry = {**item, "kind": "static", "text": script["text"], "script_version": script["script_version"]}
            for environment in ENVIRONMENTS:
                audio = await audio_doc(item["narration_id"], environment)
                entry[environment] = {
                    "status": audio_status(audio, script["script_version"]) if script["text"] else "missing",
                    "version": audio.get("version", 0),
                    "generated_at": audio.get("generated_at", ""),
                    "voice_ref": mask(audio.get("voice_id", "")) if audio else "",
                }
            rows.append(entry)
        for item in PERSONALIZED_POINTS:
            script = await text_doc(f"template_{item['point_id']}")
            rows.append({"narration_id": f"template_{item['point_id']}", "game_step_id": item["game_step_id"],
                         "label": f"{item['label']} — personalized template (use [FIRST NAME])", "kind": "template",
                         "text": script["text"], "script_version": script["script_version"],
                         "test": {"status": "ready" if script["text"] else "missing"},
                         "live": {"status": "ready" if script["text"] else "missing"}})
        missing_live = [row["narration_id"] for row in rows
                        if row["kind"] == "static" and row["live"]["status"] == "missing" and row["text"]]
        bulk = await db.marketing_settings.find_one({"key": "game_voice_bulk"}, {"_id": 0}) or {}
        return {"assets": rows, "missing_live": missing_live,
                "bulk": {"running": bool(bulk_lock["running"]), "done": bulk.get("done", 0),
                         "total": bulk.get("total", 0), "failed": bulk.get("failed", [])}}

    @router.put("/admin/game/voice/assets/{narration_id}")
    async def save_asset_text(narration_id: str, payload: AssetTextPayload, request: Request):
        await authenticate_admin(request, db)
        is_template = narration_id.startswith("template_") and narration_id[len("template_"):] in POINTS_BY_ID
        if narration_id not in STATIC_BY_ID and not is_template:
            raise HTTPException(status_code=404, detail="Unknown narration asset")
        current = await text_doc(narration_id)
        text = payload.text.strip()
        updates = {"text": text, "updated_at": now_iso()}
        if text != current["text"]:
            updates["script_version"] = current["script_version"] + 1
        await db.game_voice_assets.update_one(
            {"narration_id": narration_id},
            {"$set": updates, "$setOnInsert": {"narration_id": narration_id, "created_at": now_iso()}},
            upsert=True)
        return {"status": "saved"}

    @router.post("/admin/game/voice/assets/{narration_id}/generate")
    async def generate_asset(narration_id: str, payload: GeneratePayload, request: Request):
        """Explicit admin action only. Live READY clips require force (confirmed regeneration)."""
        await authenticate_admin(request, db)
        if narration_id not in STATIC_BY_ID:
            raise HTTPException(status_code=404, detail="Unknown narration asset")
        if payload.environment not in ENVIRONMENTS:
            raise HTTPException(status_code=422, detail="Environment must be test or live")
        script = await text_doc(narration_id)
        existing = await audio_doc(narration_id, payload.environment)
        if (payload.environment == "live" and not payload.force
                and audio_status(existing, script["script_version"]) == "ready"):
            raise HTTPException(status_code=409, detail="This production clip is already generated. Use Regenerate Clip to replace it.")
        try:
            await generate_static(narration_id, payload.environment)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=502, detail="Audio generation failed. Check the ElevenLabs key and voice ID.")
        return {"status": "ready", "environment": payload.environment}

    @router.post("/admin/game/voice/generate-missing-live")
    async def generate_missing_live(request: Request):
        """Explicit, confirmed admin action: generate ONLY missing LIVE static clips. Skips READY clips."""
        await authenticate_admin(request, db)
        if bulk_lock["running"]:
            raise HTTPException(status_code=409, detail="A generation job is already running")
        missing = []
        for item in STATIC_NARRATIONS:
            script = await text_doc(item["narration_id"])
            if not script["text"]:
                continue
            audio = await audio_doc(item["narration_id"], "live")
            if not audio or audio.get("status") != "ready":
                missing.append(item["narration_id"])
        if not missing:
            return {"started": False, "total": 0}
        bulk_lock["running"] = True
        await db.marketing_settings.update_one(
            {"key": "game_voice_bulk"},
            {"$set": {"total": len(missing), "done": 0, "failed": [], "started_at": now_iso()}}, upsert=True)

        async def run_job(ids):
            try:
                for narration_id in ids:
                    try:
                        await generate_static(narration_id, "live")
                    except Exception:
                        await db.marketing_settings.update_one(
                            {"key": "game_voice_bulk"}, {"$push": {"failed": narration_id}})
                    await db.marketing_settings.update_one(
                        {"key": "game_voice_bulk"}, {"$inc": {"done": 1}})
            finally:
                bulk_lock["running"] = False

        asyncio.create_task(run_job(missing))
        return {"started": True, "total": len(missing)}

    return router
