# PlaneTrack

Polls the [OpenSky Network](https://opensky-network.org) for live aircraft state vectors, runs them through a Bronze → Silver → Gold pipeline, and persists each layer as Parquet on Azure Data Lake Gen2. A FastAPI app exposes the processed data for querying.

## Stack

- **FastAPI** + uvicorn — API server
- **APScheduler** — background polling on a configurable interval
- **httpx** — async OpenSky client
- **pydantic-settings** — typed config from `.env`
- **pyarrow / pandas** — Parquet I/O
- **azure-storage-file-datalake** — ADLS Gen2

## Setup

```bash
# 1. Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync --dev

# 3. Configure
cp .env.example .env
# edit .env with your credentials

# 4. Run
uv run uvicorn app.main:app --reload
```

Swagger UI: http://localhost:8000/docs

## Configuration (`.env`)

Copy `.env.example` to `.env` and fill in your values. `.env` is gitignored.

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENSKY_CLIENT_ID` | yes | — | OpenSky OAuth2 client ID |
| `OPENSKY_CLIENT_SECRET` | yes | — | OpenSky OAuth2 client secret |
| `OPENSKY_BASE_URL` | no | `https://opensky-network.org/api` | API base URL |
| `OPENSKY_TOKEN_URL` | no | `https://opensky-network.org/api/auth/realms/opensky-network/protocol/openid-connect/token` | OAuth2 token endpoint |
| `AZURE_ACCOUNT_NAME` | yes | — | Storage account name |
| `AZURE_ACCOUNT_KEY` | yes | — | Storage account key |
| `ADLS_CONTAINER` | no | `planetrack` | Container name in ADLS Gen2 |
| `PIPELINE_INTERVAL_SECONDS` | no | `60` | How often to poll OpenSky (min 10) |
| `LOG_LEVEL` | no | `INFO` | Python logging level |

## API Routes

All routes are under `/api/v1`. Interactive docs at `/docs`.

### Aircraft — Silver layer

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/aircraft/` | All aircraft from the latest Silver snapshot |
| `GET` | `/api/v1/aircraft/{icao24}` | Single aircraft by ICAO24 hex address |

**`GET /api/v1/aircraft/`** — response is a list of:

```json
{
  "icao24": "3c6581",
  "callsign": "DLH123",
  "origin_country": "Germany",
  "time_position": "2024-11-14T12:00:00Z",
  "last_contact": "2024-11-14T12:00:01Z",
  "longitude": 13.404,
  "latitude": 52.520,
  "baro_altitude_m": 9144.0,
  "geo_altitude_m": 9200.0,
  "on_ground": false,
  "velocity_ms": 245.3,
  "true_track_deg": 270.0,
  "vertical_rate_ms": -0.5,
  "squawk": "1234",
  "ingested_at": "2024-11-14T12:00:02Z"
}
```

Returns `503` if no Silver data exists yet (run the pipeline first).
Returns `404` for unknown ICAO24.

### Stats — Gold layer

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/stats/` | Aggregated counts from the latest Gold snapshot |

**Response:**

```json
{
  "snapshot_time": "2024-11-14T12:00:00Z",
  "total_tracked": 9842,
  "total_airborne": 7321,
  "total_on_ground": 2521,
  "by_country": {
    "United States": 1823,
    "Germany": 412,
    "France": 389
  }
}
```

`by_country` counts airborne aircraft only, keyed by origin country.

Returns `503` if no Gold data exists yet.

### Pipeline

| Method | Path | Status | Description |
|---|---|---|---|
| `POST` | `/api/v1/pipeline/ingest` | `202` | Manually trigger a full pipeline run |

Runs synchronously and returns the resulting `FlightStats` object. Useful for backfilling or testing without waiting for the scheduler.

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check — returns `{"status": "ok"}` |

## Pipeline

Each run fetches all current aircraft states from OpenSky and writes three Parquet files to ADLS:

```
bronze/YYYY/MM/DD/HH/{epoch}.parquet   raw OpenSky response, all 17 fields
silver/YYYY/MM/DD/HH/{epoch}.parquet   cleaned: typed timestamps, stripped callsigns, nulls handled
gold/YYYY/MM/DD/HH/{epoch}.parquet     aggregated counts per snapshot
```

The scheduler fires every `PIPELINE_INTERVAL_SECONDS` (default 60s) starting at app startup. `POST /api/v1/pipeline/ingest` triggers an additional run on demand.

**Bronze → Silver transformations:**
- Unix epoch timestamps → `datetime` (UTC)
- Callsigns whitespace-stripped, empty string → `null`
- `on_ground: null` → `false`
- Records with no ICAO24 address are dropped
- `ingested_at` field added (wall-clock time of ingest)

**Silver → Gold aggregation:**
- `total_tracked` — all records in the Silver snapshot
- `total_airborne` / `total_on_ground` — split on `on_ground`
- `by_country` — airborne aircraft counted by `origin_country`

## Project Structure

```
app/
├── main.py                     # FastAPI app + APScheduler lifespan
├── config.py                   # Settings (pydantic-settings, reads .env)
├── api/v1/routes/
│   ├── __init__.py             # Assembles api_router
│   ├── aircraft.py             # GET /aircraft endpoints
│   ├── stats.py                # GET /stats endpoint
│   └── pipeline.py             # POST /pipeline/ingest endpoint
├── core/
│   └── dependencies.py         # SettingsDep type alias
├── models/
│   ├── bronze.py               # StateVector, BronzeSnapshot
│   ├── silver.py               # AircraftState
│   └── gold.py                 # FlightStats
├── services/
│   ├── opensky.py              # Async httpx client for OpenSky REST API
│   └── pipeline.py             # run_pipeline() + transformation logic
└── storage/
    └── adls.py                 # ADLSClient — Parquet read/write/list

tests/
├── conftest.py                 # Session env-var fixture (no .env needed for tests)
├── test_pipeline.py            # Unit tests for transformation functions
└── test_routes.py              # Integration tests (TestClient + mocked ADLS)
```

## Development

```bash
# Run tests
uv run pytest -v

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy app
```
