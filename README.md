# Profile Intelligence Service

A demographic intelligence API that enriches names with gender, age, and nationality data, stores 2026+ profiles, and exposes a queryable engine with filtering, sorting, pagination, and natural language search.

---

## Tech Stack

- **FastAPI** — web framework
- **PostgreSQL** — database
- **SQLAlchemy** — schema definition and table creation
- **databases** — async query execution
- **httpx** — concurrent calls to external enrichment APIs
- **uuid-utils** — UUID v7 ID generation

---

## External Enrichment APIs

| API | Data Extracted |
|---|---|
| [Genderize](https://api.genderize.io) | gender, gender_probability, sample_size |
| [Agify](https://api.agify.io) | age → age_group |
| [Nationalize](https://api.nationalize.io) | country_id, country_name, country_probability |

No API keys required.

---

## Database Schema

| Field | Type | Notes |
|---|---|---|
| id | UUID v7 | Primary key |
| name | VARCHAR (unique) | Lowercased on insert |
| gender | VARCHAR | `male` or `female` |
| gender_probability | FLOAT | Confidence score |
| sample_size | INT | From Genderize (`count`) |
| age | INT | Exact age |
| age_group | VARCHAR | `child`, `teenager`, `adult`, `senior` |
| country_id | VARCHAR(2) | ISO code e.g. `NG`, `KE` |
| country_name | VARCHAR | Full country name |
| country_probability | FLOAT | Confidence score |
| created_at | VARCHAR | UTC ISO 8601 timestamp |

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/profiles` | Create and enrich a new profile |
| `GET` | `/api/profiles` | List profiles with filters, sorting, pagination |
| `GET` | `/api/profiles/search` | Natural language query search |
| `GET` | `/api/profiles/{id}` | Get a single profile by ID |
| `DELETE` | `/api/profiles/{id}` | Delete a profile |

---

### POST /api/profiles

```json
// Request
{ "name": "amara" }

// 201 Created
{
  "status": "success",
  "data": {
    "id": "uuid-v7",
    "name": "amara",
    "gender": "female",
    "gender_probability": 0.94,
    "sample_size": 3120,
    "age": 28,
    "age_group": "adult",
    "country_id": "NG",
    "country_name": "Nigeria",
    "country_probability": 0.72,
    "created_at": "2026-04-22T10:00:00Z"
  }
}
```

Submitting the same name again returns the existing record with `"message": "Profile already exists"`.

---

### GET /api/profiles — Filters, Sorting & Pagination

All parameters are optional and combinable.

**Filter params:**

| Param | Example |
|---|---|
| `gender` | `male` / `female` |
| `age_group` | `child` / `teenager` / `adult` / `senior` |
| `country_id` | `NG`, `KE`, `GH` |
| `min_age` | `25` |
| `max_age` | `45` |
| `min_gender_probability` | `0.80` |
| `min_country_probability` | `0.50` |

**Sort params:** `sort_by=age|created_at|gender_probability` + `order=asc|desc`

**Pagination:** `page=1&limit=10` (max limit: 50)

```
/api/profiles?gender=male&country_id=NG&min_age=25&sort_by=age&order=desc&page=1&limit=10
```

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 84,
  "data": [ { "..." } ]
}
```

---

### GET /api/profiles/search — Natural Language Query

Rule-based only. No AI or LLMs.

```
/api/profiles/search?q=young males from nigeria&page=1&limit=10
```

**Example mappings:**

| Query | Interpreted As |
|---|---|
| `young males` | `gender=male`, `min_age=16`, `max_age=24` |
| `females above 30` | `gender=female`, `min_age=30` |
| `people from angola` | `country_id=AO` |
| `adult males from kenya` | `gender=male`, `age_group=adult`, `country_id=KE` |
| `teenagers above 17` | `age_group=teenager`, `min_age=17` |

Uninterpretable queries return:
```json
{ "status": "error", "message": "Unable to interpret query" }
```

---

## Age Groups

| Age Range | Group |
|---|---|
| 0–12 | child |
| 13–19 | teenager |
| 20–59 | adult |
| 60+ | senior |

> `young` is a query-time alias for ages 16–24. It is not a stored age group.

---

## Local Setup

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
pip install -r requirements.txt
```

Create a `.env` file:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/profiles_db
```

Run the server:
```bash
uvicorn main:app --reload
```

Seed the database:
```bash
python seed.py                        # looks for seed_data.json in the same folder
python seed.py /path/to/seed_data.json  # or pass a custom path
```

The app auto-creates the `profiles` table on startup — no migrations needed.

---

## Deployment (Railway)

1. Push all files (including `seed_data.json`) to GitHub
2. Create a Railway project → **Deploy from GitHub repo**
3. Add a **PostgreSQL** service from the Railway dashboard
4. In your app service → **Variables** tab → link `DATABASE_URL` from the Postgres service
5. Railway uses the `Procfile` to start the server:
   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
6. After deploy, open a Railway shell and run `python seed.py` to load the 2026 profiles

---

## Error Responses

All errors follow this structure:
```json
{ "status": "error", "message": "<error message>" }
```

| Status | Reason |
|---|---|
| 400 | Missing or empty parameter |
| 422 | Invalid parameter type |
| 404 | Profile not found |
| 502 | External enrichment API returned invalid data |
