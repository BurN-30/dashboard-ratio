#!/usr/bin/env python3
"""
Migration Script: V1 JSON Data -> V2 Database

Migrates historical tracker data from the old JSON-based system
to the new SQLAlchemy database.

Usage:
    python migrate_v1_data.py [--history-file PATH] [--stats-file PATH]

Default paths:
    - ../history.json
    - ../stats.json
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import argparse

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings
from app.db.database import engine, async_session
from app.db.models import Base, TrackerStats


def parse_timestamp(ts: int) -> datetime:
    """Convert Unix timestamp to datetime."""
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def normalize_tracker_name(name: str) -> str:
    """Normalize tracker names between V1 and V2."""
    # Map V1 names to V2 names if different
    name_map = {
        "Generation-Free": "Generation-Free",
        "TheOldSchool": "TheOldSchool",
        "Sharewood": "Sharewood",
        "Torr9": "Torr9",
        "Gemini": "Gemini",
    }
    return name_map.get(name, name)


def extract_stats(tracker_name: str, data: dict, timestamp: datetime) -> Optional[TrackerStats]:
    """
    Extract and normalize stats from V1 format to V2 TrackerStats model.

    V1 has slightly different field names between trackers.
    """
    try:
        # Common fields with fallbacks
        ratio_str = data.get("ratio", "0")

        # Handle ratio parsing
        try:
            ratio = float(ratio_str.replace(",", "."))
        except (ValueError, AttributeError):
            ratio = 0.0

        # Buffer field varies: "buffer" or "dl_capacity"
        buffer = data.get("buffer") or data.get("dl_capacity") or "0"

        # Upload/Download volumes
        vol_upload = data.get("vol_upload") or data.get("vol_upload_final") or "0"
        vol_download = data.get("vol_download") or "0"

        # Points bonus
        points_bonus = data.get("points_bonus") or data.get("points") or "0"

        # FL tokens
        fl_tokens = data.get("fl_tokens") or "0"

        # Seed/leech counts
        count_seed = data.get("count_seed") or "0"
        count_leech = data.get("count_leech") or "0"
        count_downloaded = data.get("count_downloaded") or data.get("count_download") or "0"

        # Seed time - various formats
        seed_time_total = (
            data.get("seed_time_total") or
            data.get("time_seed_total") or
            "0"
        )
        seed_time_avg = (
            data.get("seed_time_avg") or
            data.get("time_seed_avg") or
            "0"
        )

        # Warnings and H&R
        warnings_active = data.get("warnings_active") or "0"
        hit_and_run = data.get("hit_and_run") or "0"

        return TrackerStats(
            tracker_name=normalize_tracker_name(tracker_name),
            ratio=ratio,
            buffer=str(buffer),
            vol_upload=str(vol_upload),
            vol_download=str(vol_download),
            points_bonus=str(points_bonus),
            fl_tokens=str(fl_tokens),
            count_seed=str(count_seed),
            count_leech=str(count_leech),
            count_downloaded=str(count_downloaded),
            seed_time_total=str(seed_time_total),
            seed_time_avg=str(seed_time_avg),
            warnings_active=str(warnings_active),
            hit_and_run=str(hit_and_run),
            scraped_at=timestamp,
        )
    except Exception as e:
        print(f"  [WARN] Failed to parse {tracker_name}: {e}")
        return None


async def migrate_history(history_file: Path) -> int:
    """Migrate history.json to database."""
    if not history_file.exists():
        print(f"[ERROR] History file not found: {history_file}")
        return 0

    print(f"[INFO] Reading history from: {history_file}")

    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)

    print(f"[INFO] Found {len(history)} snapshots to migrate")

    migrated = 0
    async with async_session() as session:
        for i, snapshot in enumerate(history):
            timestamp_unix = snapshot.get("_timestamp")
            if not timestamp_unix:
                continue

            timestamp = parse_timestamp(timestamp_unix)

            for tracker_name, data in snapshot.items():
                if tracker_name.startswith("_"):
                    continue

                if not isinstance(data, dict):
                    continue

                stats = extract_stats(tracker_name, data, timestamp)
                if stats:
                    session.add(stats)
                    migrated += 1

            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(history)} snapshots...")

        await session.commit()

    return migrated


async def migrate_current_stats(stats_file: Path) -> int:
    """Migrate stats.json (current stats) to database."""
    if not stats_file.exists():
        print(f"[ERROR] Stats file not found: {stats_file}")
        return 0

    print(f"[INFO] Reading current stats from: {stats_file}")

    with open(stats_file, "r", encoding="utf-8") as f:
        stats = json.load(f)

    timestamp_unix = stats.get("_timestamp", int(datetime.now().timestamp()))
    timestamp = parse_timestamp(timestamp_unix)

    migrated = 0
    async with async_session() as session:
        for tracker_name, data in stats.items():
            if tracker_name.startswith("_"):
                continue

            if not isinstance(data, dict):
                continue

            stat = extract_stats(tracker_name, data, timestamp)
            if stat:
                session.add(stat)
                migrated += 1

        await session.commit()

    return migrated


async def main():
    parser = argparse.ArgumentParser(description="Migrate V1 data to V2 database")
    parser.add_argument(
        "--history-file",
        type=Path,
        default=Path(__file__).parent.parent.parent / "history.json",
        help="Path to history.json file"
    )
    parser.add_argument(
        "--stats-file",
        type=Path,
        default=Path(__file__).parent.parent.parent / "stats.json",
        help="Path to stats.json file"
    )
    parser.add_argument(
        "--skip-history",
        action="store_true",
        help="Skip migrating history (only migrate current stats)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Dashboard V1 -> V2 Data Migration")
    print("=" * 60)

    settings = get_settings()
    print(f"[INFO] Database: {settings.database_url[:50]}...")

    # Create tables if they don't exist
    print("[INFO] Ensuring database tables exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    total_migrated = 0

    # Migrate history
    if not args.skip_history:
        print("\n[STEP 1/2] Migrating history...")
        count = await migrate_history(args.history_file)
        print(f"  -> Migrated {count} historical records")
        total_migrated += count
    else:
        print("\n[STEP 1/2] Skipping history migration")

    # Migrate current stats
    print("\n[STEP 2/2] Migrating current stats...")
    count = await migrate_current_stats(args.stats_file)
    print(f"  -> Migrated {count} current stat records")
    total_migrated += count

    print("\n" + "=" * 60)
    print(f"Migration complete! Total records migrated: {total_migrated}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
