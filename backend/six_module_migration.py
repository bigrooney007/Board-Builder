"""One-time, non-destructive remap of Recruitment from five modules to six.

New Module 1 "Recruiting Board Members the Right Way" is training-only (no video record created).
Old modules 1-5 become new modules 2-6. Videos, progress and generated materials move with their modules.
Uses a two-pass temporary-offset shift so unique indexes on (product, module_number) never collide.
Runs at startup, guarded by the migrations collection.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MIGRATION_KEY = "six_module_recruitment_v1"
PRODUCTS = ["recruitment_basic", "recruitment_self_guided"]
TEMP_OFFSET = 200


async def run_six_module_migration(db) -> None:
    if await db.migrations.find_one({"key": MIGRATION_KEY}):
        return
    now = datetime.now(timezone.utc).isoformat()
    moved_progress = moved_videos = moved_materials = 0
    for product in PRODUCTS:
        for collection, counter in ((db.course_progress, "progress"), (db.course_videos, "videos")):
            for old in range(1, 6):
                result = await collection.update_many(
                    {"product": product, "module_number": old},
                    {"$set": {"module_number": TEMP_OFFSET + old, "migrated_six_module_at": now}})
                if counter == "progress":
                    moved_progress += result.modified_count
                else:
                    moved_videos += result.modified_count
            for old in range(1, 6):
                await collection.update_many(
                    {"product": product, "module_number": TEMP_OFFSET + old},
                    {"$set": {"module_number": old + 1}})
    for old in range(1, 6):
        result = await db.generated_materials.update_many(
            {"module": old, "type": {"$not": {"$regex": "^reactivation_"}}},
            {"$set": {"module": TEMP_OFFSET + old, "migrated_six_module_at": now}})
        moved_materials += result.modified_count
    for old in range(1, 6):
        await db.generated_materials.update_many(
            {"module": TEMP_OFFSET + old, "type": {"$not": {"$regex": "^reactivation_"}}},
            {"$set": {"module": old + 1}})
    await db.migrations.insert_one({"key": MIGRATION_KEY, "ran_at": now,
                                    "progress_moved": moved_progress, "videos_moved": moved_videos,
                                    "materials_moved": moved_materials})
    logger.info("Six-module recruitment migration complete: %s progress, %s videos, %s materials",
                moved_progress, moved_videos, moved_materials)
