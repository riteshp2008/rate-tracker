# Rate-Tracker Makefile

.PHONY: help build up down logs test migrate seed-db clean shell lint

PROJECT_NAME := rate_tracker
DOCKER_COMPOSE := docker-compose

help:
	@echo "Available commands:"
	@echo "  make build           - Build Docker images"
	@echo "  make up              - Start all services (docker-compose up)"
	@echo "  make down            - Stop all services"
	@echo "  make logs            - Tail all service logs"
	@echo "  make logs-django     - Tail Django logs"
	@echo "  make logs-celery     - Tail Celery worker logs"
	@echo "  make migrate         - Run Django migrations"
	@echo "  make seed-db         - Seed database from parquet file"
	@echo "  make test            - Run all tests (pytest)"
	@echo "  make test-watch      - Run tests in watch mode"
	@echo "  make lint            - Run linters"
	@echo "  make shell           - Django shell"
	@echo "  make clean           - Clean up Docker containers and volumes"
	@echo "  make createsuperuser - Create Django superuser"

build:
	$(DOCKER_COMPOSE) build

up:
	$(DOCKER_COMPOSE) up -d
	@echo "Services starting... Check logs with: make logs"

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

logs-django:
	$(DOCKER_COMPOSE) logs -f django

logs-celery:
	$(DOCKER_COMPOSE) logs -f celery_worker

migrate:
	$(DOCKER_COMPOSE) exec django python manage.py migrate

seed-db:
	$(DOCKER_COMPOSE) exec django python manage.py seed_data

test:
	$(DOCKER_COMPOSE) exec django pytest -v

test-watch:
	$(DOCKER_COMPOSE) exec django pytest -v --looponfail

lint:
	$(DOCKER_COMPOSE) exec django flake8 rates_app --max-line-length=120
	$(DOCKER_COMPOSE) exec django black --check rates_app

shell:
	$(DOCKER_COMPOSE) exec django python manage.py shell

createsuperuser:
	$(DOCKER_COMPOSE) exec django python manage.py createsuperuser

clean:
	$(DOCKER_COMPOSE) down -v
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '.pytest_cache' -delete

# Health check
ps:
	$(DOCKER_COMPOSE) ps
