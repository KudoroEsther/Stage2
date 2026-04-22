"""
Seed script — populates the profiles table with 2026 records.
Safe to re-run: skips names that already exist.

Usage:
    python seed.py <path_to_csv>

The CSV must have a 'name' column. The script calls the three
enrichment APIs for each name and inserts the result.
"""

import asyncio
import csv
import sys
from datetime import datetime, timezone

import httpx
# from uuid_extensions import uuid7str
import uuid

from database import database, engine, metadata
from models import profiles


COUNTRY_NAMES = {
    "NG": "Nigeria", "GH": "Ghana", "KE": "Kenya", "ZA": "South Africa",
    "ET": "Ethiopia", "TZ": "Tanzania", "UG": "Uganda", "AO": "Angola",
    "CM": "Cameroon", "SN": "Senegal", "CI": "Ivory Coast", "ML": "Mali",
    "ZM": "Zambia", "ZW": "Zimbabwe", "MZ": "Mozambique", "MG": "Madagascar",
    "BJ": "Benin", "TG": "Togo", "NE": "Niger", "BF": "Burkina Faso",
    "GN": "Guinea", "RW": "Rwanda", "SO": "Somalia", "SD": "Sudan",
    "TD": "Chad", "CG": "Congo", "CD": "DR Congo", "GA": "Gabon",
    "LR": "Liberia", "SL": "Sierra Leone", "MW": "Malawi", "BW": "Botswana",
    "NA": "Namibia", "LS": "Lesotho", "SZ": "Eswatini", "MU": "Mauritius",
    "CV": "Cape Verde", "GM": "Gambia", "GW": "Guinea-Bissau", "KM": "Comoros",
    "ER": "Eritrea", "DJ": "Djibouti", "LY": "Libya", "DZ": "Algeria",
    "MA": "Morocco", "TN": "Tunisia", "EG": "Egypt", "US": "United States",
    "GB": "United Kingdom", "FR": "France", "DE": "Germany", "BR": "Brazil",
    "IN": "India", "CN": "China", "PK": "Pakistan", "ID": "Indonesia",
    "NG": "Nigeria", "PH": "Philippines", "VN": "Vietnam", "TR": "Turkey",
    "IR": "Iran", "TH": "Thailand", "MM": "Myanmar", "KR": "South Korea",
    "CO": "Colombia", "ES": "Spain", "UA": "Ukraine", "AR": "Argentina",
    "DZ": "Algeria", "PL": "Poland", "CA": "Canada", "AU": "Australia",
    "IT": "Italy", "MX": "Mexico", "JP": "Japan", "RU": "Russia",
}


def get_age_group(age: int) -> str:
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"


async def fetch_profile_data(client: httpx.AsyncClient, name: str) -> dict | None:
    """Call all 3 APIs concurrently and return enriched data, or None on failure."""
    try:
        g_res, a_res, n_res = await asyncio.gather(
            client.get(f"https://api.genderize.io?name={name}"),
            client.get(f"https://api.agify.io?name={name}"),
            client.get(f"https://api.nationalize.io?name={name}"),
        )
        genderize   = g_res.json()
        agify       = a_res.json()
        nationalize = n_res.json()
    except Exception as e:
        print(f"  [SKIP] {name} — API error: {e}")
        return None

    if not genderize.get("gender") or genderize.get("count", 0) == 0:
        print(f"  [SKIP] {name} — Genderize invalid")
        return None
    if agify.get("age") is None:
        print(f"  [SKIP] {name} — Agify invalid")
        return None
    countries = nationalize.get("country", [])
    if not countries:
        print(f"  [SKIP] {name} — Nationalize invalid")
        return None

    top = max(countries, key=lambda c: c["probability"])
    age = agify["age"]
    country_id = top["country_id"]

    return {
        "id":                  str(uuid.uuid7()),
        "name":                name,
        "gender":              genderize["gender"],
        "gender_probability":  genderize["probability"],
        "sample_size":         genderize["count"],
        "age":                 age,
        "age_group":           get_age_group(age),
        "country_id":          country_id,
        "country_name":        COUNTRY_NAMES.get(country_id, country_id),
        "country_probability": top["probability"],
        "created_at":          datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


async def seed(csv_path: str):
    metadata.create_all(engine)
    await database.connect()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        names = [row["name"].strip().lower() for row in reader if row.get("name")]

    print(f"Found {len(names)} names in CSV.")

    # Fetch already-stored names to skip duplicates
    existing = {row["name"] for row in await database.fetch_all(profiles.select())}
    to_insert = [n for n in names if n not in existing]
    print(f"Inserting {len(to_insert)} new profiles ({len(existing)} already exist).")

    async with httpx.AsyncClient(timeout=15) as client:
        for i, name in enumerate(to_insert, 1):
            print(f"[{i}/{len(to_insert)}] Processing: {name}")
            data = await fetch_profile_data(client, name)
            if data:
                try:
                    await database.execute(profiles.insert().values(**data))
                    print(f"  [OK] {name}")
                except Exception as e:
                    print(f"  [SKIP] {name} — DB error: {e}")
            # Small delay to avoid rate-limiting the free APIs
            await asyncio.sleep(0.3)

    await database.disconnect()
    print("Seeding complete.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python seed.py <path_to_csv>")
        sys.exit(1)
    asyncio.run(seed(sys.argv[1]))
