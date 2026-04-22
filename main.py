# Importing libaries
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal
import httpx
import asyncio
import sqlalchemy

from database import database, engine, metadata
from models import profiles
from schemas import ProfileRequest
from nlp import parse_query
import uuid
# from uuid6 import uuid7


# Country name search / look up

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
    "PH": "Philippines", "VN": "Vietnam", "TR": "Turkey", "IR": "Iran",
    "TH": "Thailand", "MM": "Myanmar", "KR": "South Korea", "CO": "Colombia",
    "ES": "Spain", "UA": "Ukraine", "AR": "Argentina", "PL": "Poland",
    "CA": "Canada", "AU": "Australia", "IT": "Italy", "MX": "Mexico",
    "JP": "Japan", "RU": "Russia",
}


#App lifecycle 
@asynccontextmanager
async def lifespan(app: FastAPI):
    metadata.create_all(engine)
    await database.connect()
    yield
    await database.disconnect()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Error handlind and validation

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    errors = exc.errors()
    first = errors[0] if errors else {}
    msg = first.get("msg", "Invalid input").replace("Value error, ", "")
    status_code = 400 if "empty" in msg or "missing" in msg.lower() else 422
    return JSONResponse(
        status_code=status_code,
        content={"status": "error", "message": msg},
    )


# Helpers 

def get_age_group(age: int) -> str:
    if age <= 12:   return "child"
    if age <= 19:   return "teenager"
    if age <= 59:   return "adult"
    return "senior"


def error_502(api_name: str):
    return JSONResponse(
        status_code=502,
        content={"status": "502", "message": f"{api_name} returned an invalid response"},
    )


def apply_filters(query, gender, age_group, country_id, min_age, max_age,
                  min_gender_probability, min_country_probability):
    """Apply all supported filters to a SQLAlchemy select query."""
    if gender:
        query = query.where(profiles.c.gender == gender.lower())
    if age_group:
        query = query.where(profiles.c.age_group == age_group.lower())
    if country_id:
        query = query.where(profiles.c.country_id == country_id.upper())
    if min_age is not None:
        query = query.where(profiles.c.age >= min_age)
    if max_age is not None:
        query = query.where(profiles.c.age <= max_age)
    if min_gender_probability is not None:
        query = query.where(profiles.c.gender_probability >= min_gender_probability)
    if min_country_probability is not None:
        query = query.where(profiles.c.country_probability >= min_country_probability)
    return query


def apply_sorting(query, sort_by, order):
    """Apply sorting to a query."""
    SORTABLE = {
        "age":                profiles.c.age,
        "created_at":         profiles.c.created_at,
        "gender_probability": profiles.c.gender_probability,
    }
    col = SORTABLE.get(sort_by)
    if col is not None:
        query = query.order_by(col.desc() if order == "desc" else col.asc())
    return query


def paginate(query, page: int, limit: int):
    """Apply OFFSET/LIMIT pagination."""
    offset = (page - 1) * limit
    return query.offset(offset).limit(limit)


def profile_dict(row) -> dict:
    return dict(row)


#Routes

@app.post("/api/profiles")
async def create_profile(payload: ProfileRequest):
    name = payload.name

    # Idempotency check
    existing = await database.fetch_one(profiles.select().where(profiles.c.name == name))
    if existing:
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Profile already exists",
                "data": profile_dict(existing),
            },
        )

    # Call all 3 external APIs concurrently
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            g_res, a_res, n_res = await asyncio.gather(
                client.get(f"https://api.genderize.io?name={name}"),
                client.get(f"https://api.agify.io?name={name}"),
                client.get(f"https://api.nationalize.io?name={name}"),
            )
            genderize   = g_res.json()
            agify       = a_res.json()
            nationalize = n_res.json()
        except Exception:
            return JSONResponse(
                status_code=502,
                content={"status": "error", "message": "Upstream service failure"},
            )

    if not genderize.get("gender") or genderize.get("count", 0) == 0:
        return error_502("Genderize")
    if agify.get("age") is None:
        return error_502("Agify")
    countries = nationalize.get("country", [])
    if not countries:
        return error_502("Nationalize")

    top     = max(countries, key=lambda c: c["probability"])
    age     = agify["age"]
    cid     = top["country_id"]

    data = {
        "id":                  str(uuid.uuid7()),
        "name":                name,
        "gender":              genderize["gender"],
        "gender_probability":  genderize["probability"],
        "sample_size":         genderize["count"],
        "age":                 age,
        "age_group":           get_age_group(age),
        "country_id":          cid,
        "country_name":        COUNTRY_NAMES.get(cid, cid),
        "country_probability": top["probability"],
        "created_at":          datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    await database.execute(profiles.insert().values(**data))
    return JSONResponse(status_code=201, content={"status": "success", "data": data})


@app.get("/api/profiles/search")
async def search_profiles(
    q:     str | None = Query(default=None),
    page:  int        = Query(default=1,  ge=1),
    limit: int        = Query(default=10, ge=1, le=50),
):
    """Natural language search endpoint."""
    if not q or not q.strip():
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing or empty query"},
        )

    filters = parse_query(q)
    if filters is None:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Unable to interpret query"},
        )

    base_query = profiles.select()
    base_query = apply_filters(
        base_query,
        gender=filters.get("gender"),
        age_group=filters.get("age_group"),
        country_id=filters.get("country_id"),
        min_age=filters.get("min_age"),
        max_age=filters.get("max_age"),
        min_gender_probability=None,
        min_country_probability=None,
    )

    # Count total matching records
    count_query = sqlalchemy.select(sqlalchemy.func.count()).select_from(
        base_query.alias("sub")
    )
    total = await database.fetch_val(count_query)

    # Fetch paginated results
    paged_query = paginate(base_query, page, limit)
    rows = await database.fetch_all(paged_query)

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "page":   page,
            "limit":  limit,
            "total":  total,
            "data":   [profile_dict(r) for r in rows],
        },
    )


@app.get("/api/profiles")
async def list_profiles(
    gender:                  str | None = Query(default=None),
    age_group:               str | None = Query(default=None),
    country_id:              str | None = Query(default=None),
    min_age:                 int | None = Query(default=None),
    max_age:                 int | None = Query(default=None),
    min_gender_probability:  float | None = Query(default=None),
    min_country_probability: float | None = Query(default=None),
    sort_by: str | None = Query(default=None, pattern="^(age|created_at|gender_probability)$"),
    order:   str        = Query(default="asc", pattern="^(asc|desc)$"),
    page:    int        = Query(default=1,  ge=1),
    limit:   int        = Query(default=10, ge=1, le=50),
):
    base_query = profiles.select()
    base_query = apply_filters(
        base_query, gender, age_group, country_id,
        min_age, max_age, min_gender_probability, min_country_probability,
    )
    base_query = apply_sorting(base_query, sort_by, order)

    # Count total matching records
    count_query = sqlalchemy.select(sqlalchemy.func.count()).select_from(
        base_query.alias("sub")
    )
    total = await database.fetch_val(count_query)

    # Fetch paginated results
    paged_query = paginate(base_query, page, limit)
    rows = await database.fetch_all(paged_query)

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "page":   page,
            "limit":  limit,
            "total":  total,
            "data":   [profile_dict(r) for r in rows],
        },
    )


@app.get("/api/profiles/{id}")
async def get_profile(id: str):
    row = await database.fetch_one(profiles.select().where(profiles.c.id == id))
    if not row:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Profile not found"},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "success", "data": profile_dict(row)},
    )


@app.delete("/api/profiles/{id}")
async def delete_profile(id: str):
    row = await database.fetch_one(profiles.select().where(profiles.c.id == id))
    if not row:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Profile not found"},
        )
    await database.execute(profiles.delete().where(profiles.c.id == id))
    return Response(status_code=204)
