# Rate-Tracker

A full-stack application for tracking and visualizing interest rates across different financial institutions. Built with Django, PostgreSQL, Redis, and NextJS.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### Setup (2 minutes)

```bash
git clone <repo-url>
cd rate-tracker
docker-compose up -d
```

Visit the dashboard at `http://localhost:3000`

**Services:**
- Dashboard: http://localhost:3000
- API: http://localhost:8000/api/rates/latest/
- Admin: http://localhost:8000/admin/ (admin/admin)

### Load Sample Data

To populate the database with ~1M rate records:

```bash
docker-compose exec django python manage.py seed_data --batch-size 10000
```

## API Endpoints

- **GET** `/api/rates/latest` - Most recent rates per provider
- **GET** `/api/rates/history` - Historical rates for a provider and type
- **GET** `/api/rates/providers` - List all providers
- **GET** `/api/rates/types` - List all rate types
- **POST** `/api/rates/ingest` - Add new rates (requires authentication)

## Testing

```bash
docker-compose exec django pytest -v
```

## Troubleshooting

**Services not responding:**
```bash
docker-compose logs django
docker-compose ps
```

**Clean rebuild:**
```bash
docker-compose down -v
docker-compose up -d --build
```

## Project Structure

```
rate-tracker/
├── rate_tracker/          # Django project config
├── rates_app/             # Main Django app
│   ├── models.py          # Database models
│   ├── views.py           # API views
│   ├── tasks.py           # Celery tasks
│   └── management/
│       └── seed_data.py   # Data loading script
├── frontend/              # NextJS dashboard
├── docker-compose.yml     # Services configuration
└── data/                  # Seed data
    └── rates_seed.parquet
```

## Features

- **Real-time Dashboard** - View latest interest rates across providers
- **Historical Analysis** - Track rate changes over time
- **REST API** - Full API for rate data access
- **Data Ingestion** - Automated batch loading from Parquet files
- **Caching** - Redis-backed caching for performance
- **Task Scheduling** - Celery Beat for scheduled jobs
- **Admin Interface** - Django admin for data management

## Development

### Run tests
```bash
docker-compose exec django pytest -v
```

### Access Django shell
```bash
docker-compose exec django python manage.py shell
```

### View logs
```bash
docker-compose logs -f django
docker-compose logs -f celery_worker
```

## Deployment

For production deployment:

1. Use managed PostgreSQL and Redis services
2. Set environment variables for production
3. Generate a new Django SECRET_KEY
4. Deploy Docker images to a container platform (Kubernetes, ECS, etc.)
