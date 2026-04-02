# Database Schema Design

## Overview

The Rate-Tracker database schema is optimized for:

- **Fast historical rate lookups** for a provider + type combination
- **Efficient latest-rate queries** per provider
- **Audit trail** of all ingestion jobs
- **Replay capability** for failed parses

## Tables

### `rate_providers`

Stores financial institutions or data providers.

**Columns:**

- `id` (PK, BigAutoField)
- `name` (CharField, unique, indexed) - Provider name (e.g., "Chase Bank")
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)

**Indexes:**

- `UNIQUE(name)` - Enforce provider name uniqueness
- Implicit index on `id` (primary key)

**Rationale:** Normalized to prevent duplicate provider names and enable efficient lookups by name.

---

### `rate_types`

Catalogues financial rate types.

**Columns:**

- `id` (PK, BigAutoField)
- `name` (CharField, unique, indexed) - Rate type name (e.g., "Mortgage 30Y", "Savings APY")
- `description` (TextField, optional)
- `created_at` (DateTimeField)

**Indexes:**

- `UNIQUE(name)` - Enforce type uniqueness

**Rationale:** Allows filtering and reporting by rate type; minimal table, serves as dimension for rates.

---

### `rates` ⭐ (Primary fact table)

The core rates data with historical tracking.

**Columns:**

- `id` (PK, BigAutoField)
- `provider_id` (FK → rate_providers)
- `rate_type_id` (FK → rate_types)
- `rate_value` (DecimalField, 10,4) - e.g., 3.5000
- `effective_date` (DateField, indexed) - Date rate became active
- `ingestion_timestamp` (DateTimeField, indexed) - When data was ingested
- `created_at` (DateTimeField, indexed)
- `updated_at` (DateTimeField)

**Unique Constraint:**

- `UNIQUE(provider_id, rate_type_id, effective_date)` - Only one rate per provider/type/date combination

**Indexes:**

1. `idx_provider_type_date` ON `(provider_id, rate_type_id, -effective_date)` - **For query: "latest rate per provider"**
   - Enables fast retrieval of most recent rates for paginated queries
   - Composite index orders newest first for efficient LIMIT queries

2. `idx_provider_type_ingestion` ON `(provider_id, rate_type_id, -ingestion_timestamp)` - **For ingestion window queries**
   - Supports "all records ingested in 24-hour window"

3. `idx_effective_date` ON `(effective_date)` - **For time range reports**

4. `idx_ingestion_timestamp` ON `(ingestion_timestamp)` - **For replay & analytics**

**Rationale:**

- `effective_date` + `ingestion_timestamp` are separate to track when data actually took effect vs. when ingested (e.g., announced Friday, effective Monday)
- Composite indexes ordered DESC on date fields allow efficient descending queries without post-sort
- Unique constraint prevents duplicate historical overwrites

---

### `raw_ingestion_records`

Audit trail of all ingestion attempts (successful and failed).

**Columns:**

- `id` (PK, BigAutoField)
- `source` (CharField, indexed) - Origin ("seed_parquet", "webhook", "scheduler")
- `raw_data` (JSONField) - Original payload before parsing
- `parsed_successfully` (BooleanField, indexed) - Success flag
- `error_message` (TextField, optional) - If failed, why
- `related_rates` (M2M → rates) - Parsed rates from this record
- `ingestion_timestamp` (DateTimeField, indexed)
- `created_at` (DateTimeField)

**Indexes:**

1. `idx_source_ingestion` ON `(source, -ingestion_timestamp)` - For audit queries per source
2. `idx_parse_success` ON `(parsed_successfully, -ingestion_timestamp)` - For failure analysis

**Rationale:**

- Enables replaying failed ingestions by re-parsing `raw_data`
- JSONField stores original data for debugging (e.g., malformed fields)
- `related_rates` M2M allows tracing which parsed rates came from which raw record
- Separate from fact table reduces bloat

---

### `ingestion_jobs`

Tracks batch jobs (seed load, scheduled tasks, webhooks).

**Columns:**

- `id` (PK, BigAutoField)
- `job_id` (CharField, unique, indexed) - Idempotent ID (UUID or timestamp)
- `source` (CharField) - Origin ("seed_data_command", "scheduler", "webhook")
- `status` (CharField, indexed) - pending → running → success/failed/partial
- `total_records` (IntegerField)
- `successful_records` (IntegerField)
- `failed_records` (IntegerField)
- `error_message` (TextField, optional)
- `started_at` (DateTimeField)
- `completed_at` (DateTimeField, optional)

**Indexes:**

- `idx_job_status_date` ON `(status, -started_at)` - For job monitoring dashboards

**Rationale:**

- Observability: track what ingested, when, and why it failed
- Idempotent `job_id` prevents duplicate runs
- Enables alerting on failed jobs

---

## Query Optimization Examples

### Latest rate per provider

```sql
SELECT DISTINCT ON (provider_id) provider_id, rate_type_id, rate_value, effective_date
FROM rates
ORDER BY provider_id, effective_date DESC;
```

✅ Uses `idx_provider_type_date` (DESC on date field)

### Rate change over 30 days for Mortgage 30Y

```sql
SELECT provider_id, rate_value, effective_date
FROM rates
WHERE rate_type_id = 1 AND effective_date >= NOW()::date - '30 days'::interval
ORDER BY provider_id, effective_date DESC;
```

✅ Uses `idx_provider_type_date`

### All records ingested in 24-hour window

```sql
SELECT * FROM rates
WHERE ingestion_timestamp >= '2024-01-15 00:00:00'
  AND ingestion_timestamp < '2024-01-16 00:00:00'
ORDER BY ingestion_timestamp DESC;
```

✅ Uses `idx_ingestion_timestamp`

---

## Design Tradeoffs

### ✅ Normalized (3NF)

- Provider/Rate-Type are separate tables
- **Pro:** Single source of truth, easy bulk updates
- **Con:** Requires JOINs (negligible cost with proper indexes)

### ✅ Decimal(10,4) for rates

- **Pro:** Precision for financial data (4 decimal places = 0.0001%)
- **Con:** Slightly larger than float (but correctness > size)

### ✅ Separate effective_date and ingestion_timestamp

- **Pro:** Audit trail; handles delayed announcements
- **Con:** Two date fields can be confusing
- **Mitigation:** Comment in schema

### ✅ M2M raw_ingestion_records → rates

- **Pro:** Audit trail of which raw records produced which rates
- **Con:** Additional table
- **Mitigation:** Only populated on successful parse; nullable foreign keys allowed

### ❌ No partitioning (initially)

- Simple deployment first
- Can partition by `effective_date` or `ingestion_timestamp` later if table grows >10GB

### ❌ No materialized views (initially)

- Let application layer handle caching (Redis)
- Can add later if specific reports lag

---

## Scaling Considerations

1. **Table Growth:** At 1M seed records + 1000/day ongoing = ~40K/month
   - 1-year data = ~500K records
   - With indexes, expect ~2-3GB by year 1
   - At that point, may want table partitioning by month

2. **Index Size:** 4 indexes + primary key = ~5x raw data size
   - Acceptable tradeoff for query speed

3. **Connection Pool:** Use persistent connections (ATOMIC_REQUESTS = True)

4. **Read Replicas:** If read volume > 1000 QPS, add read replicas for analytics

---

## Implementation Notes

- PostgreSQL will maintain indexes automatically
- Django ORM generates efficient queries with `select_related()` and `prefetch_related()`
- Use `bulk_create()` or `bulk_update()` for batch operations to reduce ORM overhead
- Monitor slow queries with `SLOW_QUERY_THRESHOLD_MS` setting (default 200ms)
