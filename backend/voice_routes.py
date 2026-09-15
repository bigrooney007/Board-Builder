"""Voice Guided Individual Game: audio asset storage/serving, ElevenLabs TTS (server-side only),
personalized first-name micro-clips with caching + generic fallback. Audio bytes stored in Mongo.
Static narration is generated ONCE by admin action — never during normal gameplay."""
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


def effective_text(narration_id: str, doc: dict) -> str:
    return (doc.get("text") or "").strip() or TEXTS.get(narration_id, "")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_first_name(raw: str) -> str:
    name = re.sub(r"[^A-Za-z0-9 '\-]", "", html.unescape(str(raw or ""))).strip()
    return name.split(" ")[0][:40] if name else ""


async def eleven_tts(text: str, voice_id: str) -> bytes:
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key or not voice_id:
        raise RuntimeError("voice provider not configured")
    async with httpx.AsyncClient(timeout=60) as client:
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


class PersonalPayload(BaseModel):
    point_id: str = Field(min_length=1)


def create_voice_router(db) -> APIRouter:
    router = APIRouter(prefix="/api")

    async def get_settings() -> dict:
        doc = await db.marketing_settings.find_one({"key": "game_voice_settings"}, {"_id": 0}) or {}
        stored = doc.get("settings") if isinstance(doc.get("settings"), dict) else {}
        merged = {**DEFAULT_VOICE_SETTINGS, **{k: v for k, v in stored.items() if k in DEFAULT_VOICE_SETTINGS}}
        merged["voice_id"] = merged.get("voice_id") or os.environ.get("ELEVENLABS_VOICE_ID", "")
        return merged

    async def asset_doc(narration_id: str) -> dict:
        return await db.game_voice_assets.find_one({"narration_id": narration_id}, {"_id": 0, "audio": 0}) or {}

    async def playing_member(token: str) -> dict:
        record = await db.game_board_members.find_one({"token": token, "removed": {"$ne": True}}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="This game link is not valid")
        return record

    # ---------- Public: settings + manifest + audio ----------

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
        assets = await db.game_voice_assets.find(
            {"status": "ready"}, {"_id": 0, "narration_id": 1, "version": 1}).to_list(300)
        ready = {row["narration_id"]: row.get("version", 1) for row in assets}
        return {
            "voice_enabled": bool(settings["voice_enabled"] and settings["narration_on"]),
            "read_type_enabled": bool(settings["read_type_enabled"]),
            "default_mode": settings["default_mode"],
            "browser_stt_on": bool(settings["browser_stt_on"]),
            "personalization_on": bool(settings["personalization_on"]),
            "first_name": clean_first_name(record.get("full_name", "")),
            "clips": {item["narration_id"]: {
                "ready": item["narration_id"] in ready,
                "url": f"/api/game/voice/audio/{item['narration_id']}?v={ready.get(item['narration_id'], 0)}",
            } for item in STATIC_NARRATIONS},
            "personal_points": [item["point_id"] for item in PERSONALIZED_POINTS],
        }

    @router.get("/game/voice/audio/{narration_id}")
    async def serve_static_audio(narration_id: str):
        if narration_id not in STATIC_BY_ID:
            raise HTTPException(status_code=404, detail="Unknown narration")
        doc = await db.game_voice_assets.find_one({"narration_id": narration_id, "status": "ready"}, {"_id": 0, "audio": 1})
        if not doc or not doc.get("audio"):
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

    # ---------- Public: personalized micro-clip (server-side TTS, cached, never blocks) ----------

    @router.post("/game/voice/personal/{token}")
    async def personal_clip(token: str, payload: PersonalPayload):
        record = await playing_member(token)
        point = POINTS_BY_ID.get(payload.point_id)
        if not point:
            raise HTTPException(status_code=404, detail="Unknown personalization point")
        settings = await get_settings()
        fallback = {"fallback_narration_id": point["fallback_id"], "url": ""}
        if not settings["voice_enabled"] or not settings["narration_on"] or not settings["personalization_on"]:
            return fallback
        first_name = clean_first_name(record.get("full_name", ""))
        template_doc = await db.game_voice_assets.find_one(
            {"narration_id": f"template_{point['point_id']}"}, {"_id": 0, "text": 1})
        template = ((template_doc or {}).get("text") or "").strip() or point.get("template", "")
        if not first_name or not template or "[FIRST NAME]" not in template:
            return fallback
        text = template.replace("[FIRST NAME]", first_name)
        voice_id = settings["voice_id"]
        cache_key = hashlib.sha256(f"{text}|{voice_id}|v1".encode()).hexdigest()
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
            "cache_key": cache_key, "voice_id": voice_id, "audio": audio, "created_at": now_iso()})
        await db.game_board_members.update_one(
            {"member_id": record["member_id"]}, {"$inc": {"personal_clips_generated": 1}})
        return {"url": f"/api/game/voice/audio/personal/{cache_key}", "fallback_narration_id": point["fallback_id"]}

    # ---------- Admin: settings + narration assets ----------

    @router.get("/admin/game/voice/settings")
    async def admin_settings(request: Request):
        await authenticate_admin(request, db)
        settings = await get_settings()
        settings["provider_key_configured"] = bool(os.environ.get("ELEVENLABS_API_KEY"))
        return {"settings": settings}

    @router.put("/admin/game/voice/settings")
    async def save_settings(payload: SettingsPayload, request: Request):
        await authenticate_admin(request, db)
        clean = {k: v for k, v in (payload.settings or {}).items() if k in DEFAULT_VOICE_SETTINGS}
        if "max_personal_clips" in clean:
            clean["max_personal_clips"] = max(0, min(10, int(clean["max_personal_clips"] or 0)))
        await db.marketing_settings.update_one(
            {"key": "game_voice_settings"},
            {"$set": {**{f"settings.{k}": v for k, v in clean.items()}, "updated_at": now_iso()}}, upsert=True)
        return {"settings": await get_settings()}

    @router.get("/admin/game/voice/assets")
    async def list_assets(request: Request):
        await authenticate_admin(request, db)
        rows = []
        for item in STATIC_NARRATIONS:
            doc = await asset_doc(item["narration_id"])
            text = effective_text(item["narration_id"], doc)
            status = doc.get("status", "")
            if status not in {"ready", "needs_regeneration"}:
                status = "not_generated" if text else "missing"
            rows.append({**item, "kind": "static", "text": text, "status": status,
                         "version": doc.get("version", 0), "generated_at": doc.get("generated_at", "")})
        for item in PERSONALIZED_POINTS:
            doc = await asset_doc(f"template_{item['point_id']}")
            text = ((doc.get("text") or "").strip()) or item.get("template", "")
            rows.append({"narration_id": f"template_{item['point_id']}", "game_step_id": item["game_step_id"],
                         "label": f"{item['label']} — personalized template (use [FIRST NAME])", "kind": "template",
                         "text": text, "status": "ready" if text else "missing",
                         "version": doc.get("version", 0), "generated_at": ""})
        return {"assets": rows}

    @router.put("/admin/game/voice/assets/{narration_id}")
    async def save_asset_text(narration_id: str, payload: AssetTextPayload, request: Request):
        await authenticate_admin(request, db)
        is_template = narration_id.startswith("template_") and narration_id[len("template_"):] in POINTS_BY_ID
        if narration_id not in STATIC_BY_ID and not is_template:
            raise HTTPException(status_code=404, detail="Unknown narration asset")
        existing = await asset_doc(narration_id)
        text = payload.text.strip()
        sets = {"text": text, "updated_at": now_iso()}
        if not is_template and text != existing.get("text", "") and existing.get("status") == "ready":
            sets["status"] = "needs_regeneration"
        await db.game_voice_assets.update_one(
            {"narration_id": narration_id},
            {"$set": sets, "$setOnInsert": {"narration_id": narration_id, "status": "missing" if not is_template else "ready",
                                            "version": 0, "created_at": now_iso()}},
            upsert=True)
        return {"asset": await asset_doc(narration_id)}

    @router.post("/admin/game/voice/assets/{narration_id}/generate")
    async def generate_asset(narration_id: str, request: Request):
        """Deliberate admin action: generate the static clip ONCE. Never called during gameplay."""
        await authenticate_admin(request, db)
        if narration_id not in STATIC_BY_ID:
            raise HTTPException(status_code=404, detail="Unknown narration asset")
        doc = await asset_doc(narration_id)
        text = effective_text(narration_id, doc)
        if not text:
            raise HTTPException(status_code=409, detail="Paste the approved script text for this clip first")
        if doc.get("status") == "ready":
            raise HTTPException(status_code=409, detail="This clip is already generated. Edit its text first if it must change.")
        settings = await get_settings()
        try:
            audio = await eleven_tts(text, settings["voice_id"])
        except Exception:
            raise HTTPException(status_code=502, detail="Audio generation failed. Check the ElevenLabs key and voice ID.")
        await db.game_voice_assets.update_one(
            {"narration_id": narration_id},
            {"$set": {"audio": audio, "status": "ready", "provider": "elevenlabs",
                      "voice_id": settings["voice_id"], "generated_at": now_iso()},
             "$inc": {"version": 1}})
        return {"status": "ready"}

    return router
