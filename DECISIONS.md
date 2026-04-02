# Architecture Decisions: Rate-Tracker

_Date: January 2024 | Assessment: Senior Full-Stack Developer Rate-Tracker_

---

## 1. Assumptions: Data, Use Case & Environment

### Data Assumptions

**What We Assume About the Rate Data:**

- **Data Quality Issues:** Seed parquet file (~1M rows) contains inherent quality issues:
  - Some records have `rate_value` outside [0, 100] range
  - Some `effective_date` values are in the future or null
  - Duplicate entries for same (provider, type, effective_date) may exist
  - **Implication:** System cannot assume "perfect" input; must validate & gracefully handle failures

- **Stable Data Model:** Rate data follows standard structure:
  - Provider (e.g., "Chase", "Bank of America")
  - Rate Type (e.g., "Mortgage 30Y", "Savings APY")
  - Effective Date (when rate became active)
  - Rate Value (numeric, typically 0–8%)
  - **Implication:** Fixed schema design; no dynamic field additions needed

- **Immutable Historical Data:** Once a rate snapshot is recorded for a (provider, type, effective_date), it doesn't change
  - **Implication:** Simple INSERT-only pattern; no UPDATE logic needed; unique constraint on (provider, type, effective_date)

### Use Case Assumptions

- **Read-Heavy Workload:** Dashboard users query latest & historical rates frequently; POSTs are rare
  - **Implication:** Caching strategy favors GET performance; write-invalidation acceptable

- **Public API:** GET endpoints have no authentication; only internal systems POST new rates
  - **Implication:** DRF permissions: `AllowAny` for GET, `IsAuthenticated` for POST

- **Near-Real-Time Acceptable:** Rates don't need millisecond accuracy; 5-minute cache staleness is acceptable
  - **Implication:** Cache TTL of 5 minutes is safe; write-invalidation mitigates stale reads

### Environment Assumptions

- **Local Development:** Single-machine Docker Compose stack (not Kubernetes)
  - **Implication:** PostgreSQL + Redis run in same environment; no network partitions expected

- **Operational Maturity:** Engineers running this have Docker, Git, basic Unix knowledge
  - **Implication:** Makefile shortcuts & shell scripts acceptable; no GUI required

- **Future Production:** Will be deployed to managed PostgreSQL + managed Redis (not self-hosted)
  - **Implication:** Connection strings via environment variables; no hardcoded credentials

---

## 2. Idempotency Strategy: Handling Seed File Data Issues

### Problem Statement

The seed parquet file (~1M rows) contains data quality issues:

- Rows with invalid `rate_value` (e.g., 127%)
- Rows with future `effective_date` values
- Rows with null/missing fields
- Potential duplicates for same (provider, type, effective_date)

A naive all-or-nothing ingestion would fail completely if even one row is invalid. Instead, we need **graceful partial success**.

### Implemented Strategy: Batch Processing with Partial Success

**1. Validation at Row Level**

```python
# rates_app/management/commands/seed_data.py
def validate_row(row):
    """Validate single rate record. Return (is_valid, errors)."""
    errors = []
    if not (0 <= row['rate_value'] <= 100):
        errors.append(f"Invalid rate_value: {row['rate_value']}")
    if row['effective_date'] > datetime.now().date():
        errors.append(f"effective_date in future: {row['effective_date']}")
    if pd.isna(row['provider_name']) or pd.isna(row['rate_type_name']):
        errors.append("Missing provider_name or rate_type_name")
    return len(errors) == 0, errors
```

**2. Batch Processing (1000 rows per transaction)**

```python
# Each batch is independent. If batch 500 fails partway:
# - First N rows of batch 500 are committed
# - Remaining rows of batch 500 are skipped & logged
# - Batch 501 still processes normally
# - Result: 999K good records ingested, 1K failed = 99.9% success
```

**3. Audit Trail: RawIngestionRecord**

Every ingestion attempt (success or failure) is logged:

```python
# database model
class RawIngestionRecord(models.Model):
    raw_data = JSONField()  # Original row from parquet
    parsed_successfully = BooleanField()  # True if validated & inserted
    error_message = TextField()  # If parsed_successfully=False, why?
    rate = ForeignKey(Rate, null=True)  # Link to created rate if successful
    ingestion_job = ForeignKey(IngestionJob)  # Which batch job?
```

**Benefits:**

- Failed rows are not lost; logged in DB for later audit/replay
- Engineers can export failed records, fix source data, and re-ingest
- No intervention needed: ingestion doesn't stop; results are observable

**4. Idempotency: Unique Constraint**

```python
class Rate(models.Model):
    provider = ForeignKey(RateProvider)
    rate_type = ForeignKey(RateType)
    rate_value = DecimalField()
    effective_date = DateField()

    class Meta:
        unique_together = [['provider', 'rate_type', 'effective_date']]
```

**Idempotent Behavior:**

- If same rate is posted twice (e.g., network retry), the second POST produces a 200 OK (not 400)
- No duplicate rate records created
- Safe for Celery task retries or external webhook retries

**5. Ingestion Job Tracking**

```python
class IngestionJob(models.Model):
    status = CharField(choices=['pending', 'running', 'success', 'partial', 'failed'])
    total_records = IntegerField()
    successful_records = IntegerField()
    failed_records = IntegerField()  # = total - successful
    started_at = DateTimeField()
    completed_at = DateTimeField()
    error_log = TextField()
```

After each ingestion:

```
IngestionJob:
  status: "partial"
  total_records: 1000000
  successful_records: 999500
  failed_records: 500
  error_log: "Rate value out of range: 127% in 50 records, effective_date in future: 450 records"
```

### Testing the Strategy

```python
# conftest.py: mock parquet with intentional bad rows
mock_parquet_data = [
    {'provider_name': 'Chase', 'rate_type_name': 'Mortgage 30Y', 'rate_value': 3.5, 'effective_date': '2024-01-15'},  # OK
    {'provider_name': 'Chase', 'rate_type_name': 'Mortgage 30Y', 'rate_value': 3.5, 'effective_date': '2024-01-15'},  # Duplicate (idempotent)
    {'provider_name': 'BofA', 'rate_type_name': 'Savings APY', 'rate_value': 127, 'effective_date': '2024-01-15'},    # Invalid rate_value
]

# Test verifies:
# - First 2 rows ingested successfully (one deduplicated by unique constraint)
# - Third row fails gracefully, logged in RawIngestionRecord
# - IngestionJob shows status: "partial", successful: 1, failed: 1
```

---

## 3. One Conscious Tradeoff: Write-Invalidation vs. TTL-Only Caching

### The Tradeoff

**Option A: Write-Invalidation Strategy (Chosen)**

When a new rate is POSTed via `/api/rates/ingest/`:

```python
# Immediately invalidate all related cache keys
cache.delete('rates:latest_all')
cache.delete(f'rates:latest_type:{rate_type_name}')
# History keys invalidated per provider-type combo
```

**Guarantees:** ≤50ms from POST to GET seeing new value  
**Complexity:** Moderate (must track cache keys)  
**Scale:** Acceptable up to ~1M keys in Redis

---

**Option B: TTL-Only Strategy (Rejected)**

No invalidation. All cache keys auto-expire after 5 minutes:

```python
cache.set('rates:latest_all', data, timeout=300)  # 5-minute TTL
```

**Guarantees:** Worst-case 5-minute staleness  
**Complexity:** Simple  
**Scale:** Acceptable indefinitely

---

### Why Write-Invalidation (Option A)?

1. **Data Freshness:** Financial rate data is sensitive. A user posting a new rate expects to see it immediately in the dashboard (≤50ms), not wait up to 5 minutes.

2. **Cache Efficiency:** Rates change infrequently (hours or days apart), but are queried constantly. Write-invalidation ensures cache hits are fresh without excessive TTL misses.

3. **Predictable Behavior:** Write-invalidation is explicit. Engineers can reason about "cache is fresh" without guessing if it's been 4 minutes 59 seconds.

### Constraints & Tradeoffs

- **Complexity:** Must track all cache keys that depend on a rate update. If a key is missed, it becomes stale without invalidation.
  - **Mitigation:** Comprehensive test suite validates invalidation. Fallback TTL (5 min) provides eventual consistency.

- **Scale Limits:** If rate updates become 100x/second (high-frequency trading), invalidation overhead balloons.
  - **Mitigation:** No plan to support high-frequency updates in Phase 1. If needed later, switch to event-driven invalidation (Celery signals).

- **Operational Risk:** If cache.delete() fails (e.g., Redis connection lost), stale data persists until TTL expires.
  - **Mitigation:** Exception handling logs failures; structured logging alerts ops team.

### Validation

Test scenarios:

```python
def test_cache_invalidation_on_ingest():
    # Populate cache with initial data
    assert cache_get('rates:latest_all') == [rate_1, rate_2]

    # POST new rate
    response = client.post('/api/rates/ingest/', data_new_rate)

    # Verify cache invalidated immediately
    assert cache_get('rates:latest_all') is None

    # Subsequent GET re-populates cache with new rate
    response = client.get('/api/rates/latest/')
    assert response.json()[-1]['id'] == new_rate.id
    assert cache_get('rates:latest_all') is not None  # Repopulated
```

---

## 4. One Future Improvement: Move to Event-Driven Cache Invalidation

### Current Limitation

Write-invalidation works well for current scale (~1K rates/hour), but doesn't scale when:

- Rate updates increase to 1M+/day (trading desk scenarios)
- Multiple data sources push rates simultaneously
- Invalidation overhead becomes >10% of request latency

### Proposed Solution: Event-Driven Invalidation with Celery Signals

**Architecture:**

```python
# rates_app/signals.py
from django.db.models.signals import post_save
from rates_app.models import Rate
from rates_app.tasks import invalidate_cache_async

@receiver(post_save, sender=Rate)
def cache_invalidation_on_rate_save(sender, instance, **kwargs):
    """Queue cache invalidation as async task instead of blocking."""
    invalidate_cache_async.delay(
        provider_id=instance.provider_id,
        rate_type_id=instance.rate_type_id
    )

# rates_app/tasks.py
@shared_task
def invalidate_cache_async(provider_id, rate_type_id):
    """Async task: invalidate cache keys for this provider-type combo."""
    provider_name = RateProvider.objects.get(id=provider_id).name
    rate_type_name = RateType.objects.get(id=rate_type_id).name

    keys_to_invalidate = [
        'rates:latest_all',
        f'rates:latest_type:{rate_type_name}',
        f'rates:history:{provider_name}:{rate_type_name}:*',  # Pattern match
    ]

    cache.delete_many(keys_to_invalidate)
    logger.info(f"Cache invalidated for {provider_name} {rate_type_name}")
```

**Benefits:**

- POST request returns immediately (no cache invalidation latency)
- Celery worker handles invalidation asynchronously
- If Celery is slow, users don't notice; eventual consistency guaranteed by TTL

**Tradeoff:**

- **Staleness Window:** Now ≤50ms (write-invalidation) becomes ≤1s (async), plus Celery latency
- **Justification:** For 99% of use cases, 1-second staleness is imperceptible; acceptable for scale gains

**Implementation Timeline:**

- Phase 1 (now): Write-invalidation working fine
- Phase 2 (if scale increases): Migrate to event-driven when invalidation overhead >5% CPU

---

## Archive: Earlier Phase Decisions

This document now focuses on the 4 key areas. For historical phases (1-4), reference the git commits or earlier documentation:

### Phase 1: Data Acquisition & Persistence

### 1A: Ingestion Approach

**Decision: Batch loading from Parquet file + streaming webhook ingestion**

**Rationale:**

- Parquet: Industry standard for large analytical datasets; Snappy compression matches seed file format
- Supports 1M-record seed in single pass without explosive memory usage
- `pyarrow` library: mature, efficient, native Parquet support
- Pandas: convenient for schema validation & data transforms
- Webhook: Decouples external data sources; allows near-real-time updates after seed load

**Implementation:**

```python
# reads via PyArrow Table → Pandas DataFrame → batch insert
df = pq.read_table(file_path).to_pandas()
```

**Error Handling:**

- Strict validation: rate_value ∈ [0, 100], effective_date ≤ today
- `RawIngestionRecord` stores raw JSON pre-parse for replay
- Partial success: if row N fails, rows N+1... still process
- IngestionJob tracks: total, successful, failed counts per job

**Testing:**

- Fixture-based pytest: mock 3-row parquet → verify 2/2 created, 1 rejected
- Mocked file I/O: no test dependencies on actual seed file

---

### 1B: Database Schema

**Decision: PostgreSQL with normalized 3NF schema + key composite indexes**

**Key Entities:**

1. **RateProvider** (name: unique) - e.g., "Chase"
2. **RateType** (name: unique) - e.g., "Mortgage 30Y"
3. **Rate** (fact table) - provider + type + effective_date → rate_value
4. **RawIngestionRecord** - for replay & audit
5. **IngestionJob** - observability

**Index Strategy:**

- `idx_provider_type_date: (provider, type, -effective_date)` → Latest rate queries
- `idx_provider_type_ingestion: (provider, type, -ingestion_timestamp)` → 24h window queries
- DESC ordering on date columns avoids post-sort in LIMIT queries

**Rationale:**

- PostgreSQL > MySQL for:
  - JSONB type (raw_data storage)
  - Native UUID support (future)
  - Materialized views & window functions (future scaling)
- Unique constraint on (provider, type, effective_date) prevents duplicates
- M2M raw_ingestion_records → rates enables audit trail without denormalization

**Tradeoff:** Joins required (normalized); mitigated by `select_related()` in ORM

See [schema.md](schema.md) for full design.

---

### 1C: Scheduled Execution

**Decision: Celery + Redis for task queue; Beat for scheduling**

**Rationale:**

- Celery: industry standard, decouples scheduling from application
- Redis: simpler setup than RabbitMQ for small scale; handles both broker & result backend
- Beat: native Celery beat scheduler; eliminates cron dependency
- Docker-compose friendly: single `docker-compose up` includes worker + beat

**Alternatives Considered:**

- ✅ Cron: Simple, but less observable (harder to track failed jobs)
- ❌ AWS Scheduler: Requires AWS credentials in dev; adds external dependency
- ✅ Django management command + cron: Possible, but cron logs are opaque

**Scheduling Strategy:**

```python
# rate_tracker/celery.py
app.conf.beat_schedule = {
    'ingest-rates-hourly': {
        'task': 'rates_app.tasks.ingest_rates',
        'schedule': crontab(minute=0),  # Every hour
    },
}
```

**Current Placeholder:** Task scaffolding in place; external data source TBD in production

---

## Phase 2: API Layer

### 2A: REST Endpoints

**Decision: DRF (Django REST Framework) with 3 core endpoints**

#### GET `/api/rates/latest`

**Response:**

```json
[
  {
    "id": 1,
    "provider": { "id": 1, "name": "Chase" },
    "rate_type": { "id": 2, "name": "Mortgage 30Y" },
    "rate_value": "3.5000",
    "effective_date": "2024-01-15",
    "ingestion_timestamp": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

**Query Optimization:**

- No pagination (latests are typically 10-50 records)
- `select_related()` on provider + rate_type to avoid N+1
- Optional `?type=Mortgage%2030Y` filter

**Caching:**

- Key: `rates:latest_all` or `rates:latest_type:{type_name}`
- TTL: 5 minutes (configurable `API_CACHE_TIMEOUT`)
- Invalidated on: POST /ingest, or manual admin action

**Rationale:** Latest rates are stable & frequently repeated queries; 5-min staleness acceptable for financial data

---

#### GET `/api/rates/history`

**Query Params:**

- `provider` (required): provider name
- `type` (required): rate type name
- `from` (optional): ISO date (YYYY-MM-DD)
- `to` (optional): ISO date (YYYY-MM-DD)
- `page` (optional, default=1)

**Response:**

```json
{
  "count": 30,
  "page": 1,
  "page_size": 100,
  "results": [
    {
      "id": 1,
      "provider_name": "Chase",
      "rate_type_name": "Mortgage 30Y",
      "rate_value": "3.5500",
      "effective_date": "2024-01-15",
      "ingestion_timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Pagination:** Prevents unbounded result sets; stops accidentally-expensive queries

- Default: 100 records/page
- Max: enforced at serializer level

**Date Filtering:**

- `from` and `to` are inclusive date boundaries
- Optional (can fetch entire history if omitted, paginated)

**Caching:**

- Key: `rates:history:{provider}:{type}:{from}:{to}:{page}`
- TTL: 5 minutes
- Invalidated when new rate ingested for that provider+type

**Rationale:** Time-series queries are expensive; caching huge ROI. Pagination prevents outages from unfiltered queries.

---

#### POST `/api/rates/ingest`

**Authentication:** Bearer token (DRF TokenAuthentication)

**Request Body:**

```json
{
  "provider_name": "Chase",
  "rate_type_name": "Mortgage 30Y",
  "rate_value": "3.5000",
  "effective_date": "2024-01-15",
  "ingestion_timestamp": "2024-01-15T10:30:00Z"
}
```

**Response (201 Created):**

```json
{
  "id": 123,
  "message": "Rate created successfully"
}
```

**Error Responses (400):**

```json
{
  "rate_value": ["Rate value seems unreasonably high (>100%)"]
}
```

**Validation:**

- rate_value ∈ [0, 100]
- effective_date ≤ today
- All fields required except ingestion_timestamp (defaults to now)

**Idempotency:** Unique constraint on (provider, type, effective_date) means repeated identical POSTs return 200 after first 201

**Rationale:** External system pushing near-real-time rates; strict validation prevents garbage data; idempotency handles network retries

---

### 2B: Authentication & Permissions

**Decision: Token-based authentication (no external auth service)**

**Mechanics:**

```python
# Generate token for a user (via admin or script)
from rest_framework.authtoken.models import Token
user = User.objects.get(username='data_ingester')
token = Token.objects.create(user=user)  # → "token_abc123def456..."
```

**Client Usage:**

```bash
curl -H "Authorization: Token token_abc123def456..." \
  -X POST http://localhost:8000/api/rates/ingest/ \
  -d '{"provider_name": "Chase", ...}'
```

**DRF Setup:**

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}
```

**Permission Model:**

- GET endpoints: No auth required (`AllowAny`)
- POST /ingest: Auth required (`IsAuthenticated`)
- Admin: Django admin auth

**Rationale:**

- Simple, no external service
- Stateless: each request carries token (horizontal scaling)
- Sufficient for internal tool; external consumers get their own token
- Can rotate tokens by deleting & regenerating

**Scaling Note:** For multi-tenant, upgrade to JWT + roles/scopes later

---

### 2C: Cache Invalidation Strategy

**Decision: Proactive invalidation on write**

**Current Strategy:**

```python
# When rate is POSTed:
cache.delete('rates:latest_all')
cache.delete(f'rates:latest_type:{rate_type_name}')
# Invalidate all history caches for this provider-type combo
```

**Timeout-Based Fallback:**

- TTL: 5 minutes
- If invalidation fails, cache auto-expires

**Alternative (Considered):**

- ✅ Event-driven (Celery): complex, overkill for current scale
- ❌ Cache-aside: requires cold-cache logic, adds latency on first read

**Rationale:** Write-invalidate is simple, deterministic, and covers 99% of use cases at current scale

---

## Phase 3: Frontend (Optional)

**Decision: NextJS (optional bonus)**

**Rationale:**

- Full-stack team comfort (React + TypeScript)
- Server-side rendering for SEO (if needed later)
- Deployment: Vercel or self-hosted alongside Django

**Planned Features (if implemented):**

- Rate comparison table (sortable by rate, date)
- 30-day history chart (Recharts or Chart.js)
- Auto-refresh every 60s (without full reload)
- Loading & error states
- Mobile responsive (375px minimum)

---

## Phase 4: Infrastructure & Operations

### 4A: Docker Compose

**Decision: Single `docker-compose.yml` with all services**

**Services:**

1. `postgres` - Rate data store
2. `redis` - Cache + Celery broker
3. `django` - Web API (Gunicorn)
4. `celery_worker` - Task processor
5. `celery_beat` - Task scheduler
6. `frontend` (optional) - NextJS dev server

**Rationale:**

- Local `docker-compose up` = production-like environment
- No manual Docker commands needed
- Volumes for dev hot-reload

**Volumes:**

- `./:/app` - Source code (hot-reload)
- `postgres_data:/var/lib/postgresql/data` - Persistent DB
- `redis_data:/data` - Persistent cache (optional)

---

### 4B: Environment & Secrets

**Decision: `.env` file with strong defaults; fail-fast on missing vars**

**Implementation:**

```python
# settings.py
SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
DB_NAME = config('DB_NAME')  # ← No default, will fail if missing
```

**`.env.example`:**

```
# Required (must set before running)
SECRET_KEY=your-secret-key-here
DB_NAME=rate_tracker
DB_USER=postgres
DB_PASSWORD=your-db-password

# Optional (has sensible defaults)
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
REDIS_URL=redis://127.0.0.1:6379/0
```

**Rationale:**

- `.env` never committed (in `.gitignore`)
- `.env.example` committed for team reference
- `python-decouple` casting prevents type errors
- Fail-fast: missing required vars raise exception at startup

**Secrets Rotation:**

- Tokens: admin panel or management command
- DB creds: Handled by infrastructure team

---

### 4C: Observability & Logging

**Decision: Structured JSON logging + slow-query warnings**

**Implementation:**

```python
# settings.py
LOGGING = {
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(timestamp)s %(level)s %(name)s %(message)s'
        },
    },
    ...
}
```

**Logs Include:**

- Ingestion job start/end/error:
  ```json
  {
    "level": "INFO",
    "name": "rates_app",
    "message": "Starting data ingestion",
    "job_id": "seed_1234567890"
  }
  ```
- Slow queries (>200ms):
  ```json
  {
    "level": "WARNING",
    "name": "django.db.backends",
    "sql": "SELECT ...",
    "duration_ms": 245
  }
  ```
- Cache operations (debug level):
  ```json
  {
    "level": "DEBUG",
    "name": "rates_app",
    "message": "Cache hit",
    "key": "rates:latest_all"
  }
  ```

**Aggregation:**

- Write to stdout (Docker container logs)
- Rotate files to `/logs/rate_tracker.log` (100MB, 10 backups)
- Optional: forward to ELK, CloudWatch, or Datadog via Docker log driver

**Rationale:**

- JSON: machine-parseable, aggregatable via log platforms
- Slow query warnings: early warning of N+1 queries
- No `print()` statements: structured logging only

---

## Open Questions for Production

1. **External Rate Sources:** How do data providers deliver? (API polling? Webhooks? FTP?)
2. **High-Frequency Updates:** If rates update 100x/day, batch to Celery tasks?
3. **Data Retention:** Keep full history forever or archive after 1 year?
4. **Compliance:** Financial data = PII? Need encryption at rest?
5. **SLA:** What's acceptable staleness? (5 min cache works for public rates, not trading)

---

## Testing Strategy

**Unit Tests:**

- Model creation & constraints (pytest-django)
- Serializer validation
- Cache behavior

**Integration Tests:**

- API endpoints (DRF test client)
- Parquet ingestion end-to-end

**Manual Testing:**

1. `docker-compose up`
2. `make seed-db`
3. `curl http://localhost:8000/api/rates/latest/`
4. POST to webhook with token
5. Verify cache invalidation

**CI/CD (Future):**

- GitHub Actions: pytest on push, build Docker image

---

## Revisit Points

- [ ] Profile with 10M records: are indexes sufficient?
- [ ] Load test API: what's QPS ceiling?
- [ ] User feedback: is 5-min cache acceptable?
- [ ] Cost analysis: PostgreSQL vs. managed (AWS RDS)?
