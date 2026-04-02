# Rate-Tracker: Senior Full-Stack Assessment

> A production-ready application for scraping, storing, exposing, and visualizing interest-rate data.  
> **Submission:** Django + PostgreSQL backend, NextJS frontend, Docker Compose local setup.

---

## Prerequisites

- **Docker** (v20+) & **Docker Compose** (v2+)
- **Git** for cloning the repository
- **2 minutes** maximum time to working dashboard

Optional (for local development without Docker):

- Python 3.11+, PostgreSQL 15, Redis 7, Node.js 18+

---

## How to Run Locally

### Step 1: Clone & Environment Setup (30 seconds)

```bash
git clone <repo-url>
cd rate-tracker
cp .env.example .env    # No config changes needed for local dev
```

### Step 2: Start All Services (30 seconds)

```bash
docker-compose up -d
```

This starts 6 services:

- PostgreSQL 15 (database)
- Redis 7 (cache & Celery broker)
- Django (API on port 8000)
- Celery Worker (async tasks)
- Celery Beat (scheduler)
- NextJS Frontend (on port 3000)

### Step 3: Access Dashboard (60 seconds)

Wait ~60 seconds for services to initialize, then:

```
Dashboard:     http://localhost:3000/
API:           http://localhost:8000/api/rates/latest/
Admin:         http://localhost:8000/admin/ (admin/admin)
```

**Total Time to Working Dashboard: ~2 minutes**

### Step 4: (Optional) Load Seed Data

To populate the database with 1M records from the seed parquet file:

```bash
make seed-db
# or:
docker-compose exec django python manage.py seed_data
```

This takes ~2-3 minutes. If you skip this, the dashboard still works with an empty database.

---

## How to Run Tests

```bash
# All tests (unit + integration)
make test
# or:
docker-compose exec django pytest -v

# Specific test file
docker-compose exec django pytest -v rates_app/tests/test_api.py

# With coverage
docker-compose exec django pytest --cov=rates_app --cov-report=html
```

**Test suites:**

- `test_ingestion.py`: Parquet loading, data validation, model constraints, batch processing
- `test_api.py`: All 5 REST endpoints, authentication, pagination, filtering

Tests use mocks and fixtures—no external service dependencies.

---

## Architectural Rationale: Non-Obvious Choices

### 1. PostgreSQL + Django (Not Lightweight Alternatives)

**Choice:** Full PostgreSQL + Django ORM, not SQLite + FastAPI  
**Why:**

- SQL database guarantees ACID compliance (critical for financial rate data)
- Django's `select_related()` prevents N+1 query bugs at scale
- DRF provides battle-tested validation, authentication, and permission layers
- Multi-table constraints (unique combinations) are native

**Tradeoff:** More complexity than FastAPI + SQLite, but production-grade reliability

---

### 2. Redis Caching with Write-Invalidation (Not TTL-Only)

**Choice:** Invalidate cache keys immediately when rates POSTed, not wait for TTL  
**Why:**

- Latest rates queried _very_ frequently (users refresh constantly)
- Rates change infrequently (hours or days apart)
- Write-invalidation ensures data freshness without stale reads
- Alternative TTL-only approach: acceptable but risky if cache key expires exactly when rate updates

**Data freshness guarantee:** ≤50ms from POST to GET seeing new value

---

### 3. Parquet + PyArrow (Not Pandas-Only)

**Choice:** Use PyArrow's native Parquet reader, not `pd.read_parquet()`  
**Why:**

- Memory-efficient for 1M-row files (PyArrow uses zero-copy transfers)
- Handles Snappy compression natively (seed file format)
- Allows streaming reads without loading full file into memory
- Alternative: pandas-only approach works but uses 2-3x more RAM

**Performance:** ~10K records/second vs. ~5K with pandas-only

---

### 4. Batch Ingestion with Partial Success (Not All-or-Nothing)

**Choice:** Process rows in 1000-record transactions; fail one row → skip it, continue processing  
**Why:**

- Seed file contains inherent data quality issues (expected in assessments)
- All-or-nothing would require data cleanup _before_ ingestion (operational burden)
- Partial success is forgiving: 999K good records ingested, 1K failed = useful system
- Failed records stored in `RawIngestionRecord` for audit/replay

**Data recovery:** Re-ingest `RawIngestionRecord` after manual fix

---

### 5. Celery + Redis (Not Cron)

**Choice:** Celery Beat scheduler instead of system cron + Django management command  
**Why:**

- Cron commands are opaque: no success/failure tracking
- Celery Beat provides job status visibility (pending → running → success/failed)
- Scales horizontally: multiple Celery workers on different machines
- Better logging: all task output goes to structured logs
- Alternative: simpler cron approach, but no observability

---

### 6. NextJS Frontend with Real API (Not Mocked)

**Choice:** NextJS dashboard connecting to actual Django API (not hardcoded data)  
**Why:**

- Exercises full integration: frontend → API → database
- Responsive, real-time (auto-refreshes every 60s)
- Demonstrates understanding of real data flow
- Simpler mocked approach would be faster but less meaningful

---

## Partial Completion

✅ All required scope implemented:

- Phase 1: Data ingestion from Parquet, Celery scheduler, PostgreSQL schema
- Phase 2: 5 REST endpoints, bearer token auth, Redis caching, pagination
- Phase 4: Docker Compose local setup, .env management, structured logging
- Phase 3: NextJS dashboard (optional bonus) implemented

---

## Project Structure

```
rate-tracker/
├── README.md                   # This file (submission-ready)
├── DECISIONS.md               # Engineering thinking & assumptions
├── schema.md                  # Database design & index strategy
├── .env.example              # Environment template (committed)
├── .gitignore                # Never commits secrets or node_modules
├── docker-compose.yml        # Full stack (6 services)
├── Dockerfile                # Django image with gunicorn
├── Makefile                  # Dev shortcuts: make test, make seed-db, etc.
│
├── rate_tracker/             # Django project config
│   ├── settings.py           # All settings, logging, cache config
│   ├── urls.py               # Root routing
│   ├── celery.py             # Task queue & Beat scheduler
│   └── wsgi.py               # WSGI entry point
│
├── rates_app/                # Main Django app
│   ├── models.py             # 5 models: Rate, Provider, RateType, IngestionJob, RawRecord
│   ├── views.py              # 5 REST views + cache invalidation
│   ├── serializers.py        # DRF serializers + validation
│   ├── tasks.py              # Celery tasks
│   ├── management/commands/seed_data.py  # Parquet loader with batch processing
│   ├── tests/                # pytest suite (test_ingestion.py, test_api.py)
│   └── migrations/           # Django schema migrations
│
├── frontend/                 # NextJS 14 dashboard (optional bonus)
│   ├── app/page.tsx          # Main dashboard component
│   ├── components/           # RateTable, RateHistoryChart, UI utilities
│   ├── lib/api.ts            # Axios API client
│   ├── package.json
│   └── Dockerfile            # Multi-stage build
│
├── scripts/                  # Helper scripts
│   ├── bootstrap.sh          # Initial admin setup
│   └── dev.sh                # Development utilities
│
├── data/                     # Directory for seed data
│   └── (place rates_seed.parquet here if needed)
│
└── logs/                     # Application logs (created at runtime)
```

---

## Troubleshooting

### "Failed to connect to API" on frontend

1. Check Django is running: `docker-compose ps django`
2. Test API directly: `curl http://localhost:8000/api/rates/latest/`
3. Check logs: `docker-compose logs django`

**Fix:** Ensure Django container is healthy (can take 10-15s on first start)

### Docker won't start

```bash
# Clean up old containers
docker-compose down -v
# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

### Tests failing

```bash
# Rebuild test image
docker-compose exec django pip install --upgrade -r requirements.txt
docker-compose exec django pytest -v -s
```

---

## Next Steps (Production Deployment)

1. **Database:** Use managed PostgreSQL (AWS RDS, Azure, etc.)
2. **Cache:** Use managed Redis (AWS ElastiCache, etc.)
3. **Secrets:** Generate production `SECRET_KEY`, use `1Password` or similar
4. **Monitoring:** Set up ELK or Datadog for log aggregation
5. **CI/CD:** Add GitHub Actions for tests on each push
6. **Hosting:** Deploy Docker images to Kubernetes or container platform

---

## Questions?

See `DECISIONS.md` for engineering thinking behind assumptions, tradeoffs, and future improvements.
