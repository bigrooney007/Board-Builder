"""One-time, non-destructive migration from the six-module Recruitment journey to the five-step journey.

Old → New mapping:
  1 (Identify)            → 1
  2 (Recruitment Strategy) → retired (module_number 99, data preserved)
  3 (Launch Campaign)     → 2
  4 (Interview)           → 3 (Select and Interview Your Applicants)
  5 (References)          → 4
  6 (Onboard)             → 5

Runs at startup, guarded by the migrations collection, and is idempotent at the document level.
"""
import logging
from datetime import datetime, timezone

from ai_service import GENERATION_TYPES

logger = logging.getLogger(__name__)

MIGRATION_KEY = "five_step_recruitment_v1"
PRODUCTS = ["recruitment_basic", "recruitment_self_guided"]
RETIRED_MODULE_NUMBER = 99
PROGRESS_MAP = [(2, RETIRED_MODULE_NUMBER), (3, 2), (4, 3), (5, 4), (6, 5)]
FIVE_STEP_VIDEOS = {
    1: "https://youtu.be/Crzh5tPpQYo",
    2: "https://youtu.be/E4S16dkgKSY",
    3: "https://youtu.be/WxGpi3hHEO8",
    4: "https://youtu.be/-gbn1_sl9h8",
    5: "https://youtu.be/fdjjsiEnfWc",
}
RETIRED_STRATEGY_VIDEO_ID = "671KaVEJFbg"


async def run_five_step_migration(db):
    if await db.migrations.find_one({"key": MIGRATION_KEY}):
        return
    now = datetime.now(timezone.utc).isoformat()

    migrated_progress = 0
    for old, new in PROGRESS_MAP:
        extra = {"retired_strategy": True} if new == RETIRED_MODULE_NUMBER else {}
        result = await db.course_progress.update_many(
            {"product": {"$in": PRODUCTS}, "module_number": old, "five_step_migrated": {"$ne": True}},
            {"$set": {"module_number": new, "legacy_module_number": old, "five_step_migrated": True, **extra}},
        )
        migrated_progress += result.modified_count
    await db.course_progress.update_many(
        {"product": {"$in": PRODUCTS}, "module_number": 1, "five_step_migrated": {"$ne": True}},
        {"$set": {"legacy_module_number": 1, "five_step_migrated": True}},
    )

    for product in PRODUCTS:
        old_strategy = await db.course_videos.find_one({"product": product, "module_number": 2}, {"_id": 0})
        if old_strategy and RETIRED_STRATEGY_VIDEO_ID in (old_strategy.get("youtube_url") or ""):
            await db.course_videos.update_one(
                {"product": product, "module_number": RETIRED_MODULE_NUMBER},
                {"$set": {"youtube_url": old_strategy["youtube_url"], "retired_strategy": True, "updated_at": now}},
                upsert=True,
            )
        for number, url in FIVE_STEP_VIDEOS.items():
            await db.course_videos.update_one(
                {"product": product, "module_number": number},
                {"$set": {"youtube_url": url, "updated_at": now}},
                upsert=True,
            )

    remapped_materials = 0
    for generation_type, meta in GENERATION_TYPES.items():
        result = await db.generated_materials.update_many(
            {"type": generation_type, "module": {"$ne": meta["module"]}},
            {"$set": {"module": meta["module"]}},
        )
        remapped_materials += result.modified_count

    await db.migrations.insert_one({"key": MIGRATION_KEY, "ran_at": now,
                                    "progress_records_migrated": migrated_progress,
                                    "materials_remapped": remapped_materials})
    logger.info("Five-step recruitment migration complete: %s progress records, %s materials remapped",
                migrated_progress, remapped_materials)
