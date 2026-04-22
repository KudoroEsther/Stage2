"""
Seed script — inserts 2026 pre-enriched profiles from seed_data.json.

Data is already enriched (no external API calls needed).
Safe to re-run: skips names that already exist (idempotent).

Usage:
    python seed.py
    python seed.py /path/to/seed_data.json   # optional custom path
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
# import uuid
from uuid_utils import uuid7

from database import database, engine, metadata
from models import profiles


DEFAULT_SEED_FILE = "seed_data.json"


async def seed(seed_path: str):
    # Create tables if they don't exist
    metadata.create_all(engine)
    await database.connect()

    with open(seed_path, encoding="utf-8") as f:
        records = json.load(f)["profiles"]

    print(f"Loaded {len(records)} records from {seed_path}")

    # Fetch already-stored names to skip duplicates
    existing = {
        row["name"]
        for row in await database.fetch_all(profiles.select().with_only_columns(profiles.c.name))
    }
    print(f"{len(existing)} profiles already in DB — skipping those.")

    inserted = 0
    skipped  = 0

    for record in records:
        name = record["name"].strip().lower()

        if name in existing:
            skipped += 1
            continue

        data = {
            "id":                  str(uuid7()),
            "name":                name,
            "gender":              record["gender"],
            "gender_probability":  record["gender_probability"],
            "sample_size":         0,          # not present in seed file
            "age":                 record["age"],
            "age_group":           record["age_group"],
            "country_id":          record["country_id"],
            "country_name":        record.get("country_name", ""),
            "country_probability": record["country_probability"],
            "created_at":          datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        try:
            await database.execute(profiles.insert().values(**data))
            inserted += 1
        except Exception as e:
            print(f"  [SKIP] {name} — DB error: {e}")
            skipped += 1

    await database.disconnect()
    print(f"Done. Inserted: {inserted} | Skipped: {skipped}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SEED_FILE
    asyncio.run(seed(path))
