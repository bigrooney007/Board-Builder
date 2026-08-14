"""Crash-safe, idempotent remap of Recruitment from five modules to six.

New Module 1 "Recruiting Board Members the Right Way" is training-only (no video record).
Old modules 1-5 become new modules 2-6. Progress, videos and generated materials move with
their modules. Self-heals any half-migrated state left by a crashed earlier attempt:
temporary-offset leftovers (module_number 200+), stale pre-restructure module-6 video
records, and re-shifted progress docs (reconstructed from legacy_module_number).
Runs at startup, guarded by the migrations collection.
"""
import logging
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from five_step_migration import FIVE_STEP_VIDEOS, RETIRED_MODULE_NUMBER

logger = logging.getLogger(__name__)

MIGRATION_KEY = "six_module_recruitment_v1"
PRODUCTS = ["recruitment_basic", "recruitment_self_guided"]
TEMP_OFFSET = 200
LEGACY_TO_SIX = {1: 2, 2: RETIRED_MODULE_NUMBER, 3: 3, 4: 4, 5: 5, 6: 6}
SIX_MODULE_VIDEOS = {old + 1: url for old, url in FIVE_STEP_VIDEOS.items()}
MATERIAL_TYPE_GUARD = {"$not": {"$regex": "^(reactivation_|activation_)"}}


def _progress_target(doc: dict) -> int:
    number = doc["module_number"]
    if number == RETIRED_MODULE_NUMBER:
        return RETIRED_MODULE_NUMBER
    legacy = doc.get("legacy_module_number")
    if legacy in LEGACY_TO_SIX:
        return LEGACY_TO_SIX[legacy]
    if number > TEMP_OFFSET:
        return min(number - TEMP_OFFSET + 1, 6)
    if doc.get("migrated_six_module_at"):
        return min(max(number, 2), 6)
    if 1 <= number <= 5:
        return number + 1
    return number


async def _migrate_progress(db, product: str, now: str) -> int:
    moved = 0
    async for doc in db.course_progress.find({"product": product, "six_module_done": {"$ne": True}}):
        target = _progress_target(doc)
        try:
            await db.course_progress.update_one(
                {"_id": doc["_id"]},
                {"$set": {"module_number": target, "six_module_done": True, "migrated_six_module_at": now}})
        except DuplicateKeyError:
            existing_filter = {"user_id": doc["user_id"], "product": product, "module_number": target}
            merge = {"six_module_done": True}
            if doc.get("completed"):
                merge["completed"] = True
            if doc.get("viewed"):
                merge["viewed"] = True
            await db.course_progress.update_one(existing_filter, {"$set": merge})
            await db.course_progress.delete_one({"_id": doc["_id"]})
        moved += 1
    return moved


async def _rebuild_videos(db, product: str, now: str) -> None:
    await db.course_videos.delete_many({"product": product, "module_number": {"$ne": RETIRED_MODULE_NUMBER}})
    for number, url in SIX_MODULE_VIDEOS.items():
        await db.course_videos.update_one(
            {"product": product, "module_number": number},
            {"$set": {"youtube_url": url, "migrated_six_module_at": now}},
            upsert=True)


async def _migrate_materials(db, now: str) -> int:
    moved = 0
    for old in range(5, 0, -1):
        stamp = {"$set": {"module": old + 1, "six_module_done": True, "migrated_six_module_at": now}}
        leftover = await db.generated_materials.update_many(
            {"module": TEMP_OFFSET + old, "type": MATERIAL_TYPE_GUARD}, stamp)
        fresh = await db.generated_materials.update_many(
            {"module": old, "six_module_done": {"$ne": True}, "type": MATERIAL_TYPE_GUARD}, stamp)
        moved += leftover.modified_count + fresh.modified_count
    return moved


async def run_six_module_migration(db) -> None:
    guard = await db.migrations.find_one({"key": MIGRATION_KEY})
    if guard and guard.get("status", "completed") == "completed":
        return
    now = datetime.now(timezone.utc).isoformat()
    await db.migrations.update_one(
        {"key": MIGRATION_KEY},
        {"$set": {"status": "running"}, "$setOnInsert": {"key": MIGRATION_KEY, "started_at": now}},
        upsert=True)
    moved_progress = 0
    for product in PRODUCTS:
        moved_progress += await _migrate_progress(db, product, now)
        await _rebuild_videos(db, product, now)
    moved_materials = await _migrate_materials(db, now)
    await db.migrations.update_one(
        {"key": MIGRATION_KEY},
        {"$set": {"status": "completed", "ran_at": now,
                  "progress_moved": moved_progress, "materials_moved": moved_materials}})
    logger.info("Six-module recruitment migration complete: %s progress, %s materials",
                moved_progress, moved_materials)
