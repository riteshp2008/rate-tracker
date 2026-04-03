# Architecture Decisions: Rate-Tracker

## Key Assumptions

- **Data:** Parquet files may have quality issues; rates are immutable after insertion
- **Usage:** Read-heavy (dashboard); GET public, POST authenticated
- **Environment:** Docker Compose for development; managed PostgreSQL/Redis for production

## Data Ingestion

**Strategy:** Batch processing with partial success, audit trail via `RawIngestionRecord`, unique constraint ensures idempotency.

Process in 10K-record batches; skip invalid rows and log for replay. Supports 1M-row seed files. Result: graceful degradation instead of all-or-nothing failures.

## Caching

**Write-invalidation:** Delete cache keys immediately on POST so subsequent GETs see fresh data. 5-minute TTL fallback.

Trade-off: freshness vs. invalidation complexity. Acceptable for current scale (~1K posts/hour).

## Database

PostgreSQL (normalized 3NF):

- `rate_providers`, `rate_types`, `rates` (fact table)
- `raw_ingestion_records` (audit trail), `ingestion_jobs` (tracking)
- Indexes on (provider, type, -effective_date) for fast queries

## Task Scheduling

Celery + Redis. Celery Beat for hourly scheduling. More observable than cron; built-in job status tracking.

## API

**DRF (Django REST Framework)**

- `GET /api/rates/latest` — Most recent per provider (cached)
- `GET /api/rates/history` — Time-series (cached, paginated)
- `GET /api/rates/providers` — List providers
- `GET /api/rates/types` — List types
- `POST /api/rates/ingest` — Add rate (token auth, idempotent)

## Authentication

Token-based (DRF). GET public; POST requires valid token.

## Infrastructure

**Docker Compose:** PostgreSQL, Redis, Django (Gunicorn), Celery Worker, Celery Beat, NextJS.

**Configuration:** Environment variables via `.env` (not committed). Fail-fast for missing required vars.

**Logging:** Structured JSON to stdout (Docker) and rotating files.

## Testing

- Unit: Model constraints, serializer validation
- Integration: API endpoints, parquet loading
- Fixtures: Mock parquet with intentional bad rows

## Future Improvements

1. **Event-driven cache invalidation** (if scale increases)
   - Queue invalidation as async Celery task instead of blocking
   - Acceptable staleness: ≤1s vs. current ≤50ms

2. **High-frequency updates** (if rate posts 100x+/hour)
   - Current batch processing becomes bottleneck
   - Consider: streaming ingest or partitioned updates

3. **Production deployment**
   - Managed PostgreSQL (RDS, Azure, etc.)
   - Managed Redis (ElastiCache, etc.)
   - Generate production SECRET_KEY
   - Add CI/CD (GitHub Actions)
   - Logging aggregation (ELK, Datadog)
