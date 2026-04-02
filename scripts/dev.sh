#!/bin/bash
# Scripts for common development tasks

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."

echo "Rate-Tracker Development Helper Script"
echo "======================================"

if [ -z "$1" ]; then
  echo "Usage: ./scripts/dev.sh [command]"
  echo ""
  echo "Commands:"
  echo "  setup              - Initial setup (build images, run migrations)"
  echo "  start              - Start all services"
  echo "  stop               - Stop all services"
  echo "  logs               - View all logs"
  echo "  test               - Run tests"
  echo "  seed               - Seed database"
  echo "  shell              - Open Django shell"
  echo "  psql               - Connect to PostgreSQL"
  echo "  redis-cli          - Connect to Redis"
  exit 1
fi

case "$1" in
  setup)
    echo "Setting up Rate-Tracker..."
    cd "$PROJECT_ROOT"
    docker-compose build
    docker-compose up -d
    echo "Waiting for services to be healthy..."
    sleep 10
    docker-compose exec -T django python manage.py migrate
    docker-compose exec -T django python manage.py check
    echo "✅ Setup complete! Run 'make up' or './scripts/dev.sh start'"
    ;;

  start)
    echo "Starting services..."
    cd "$PROJECT_ROOT"
    docker-compose up -d
    docker-compose ps
    ;;

  stop)
    echo "Stopping services..."
    cd "$PROJECT_ROOT"
    docker-compose down
    ;;

  logs)
    echo "Tailing logs..."
    cd "$PROJECT_ROOT"
    docker-compose logs -f
    ;;

  test)
    echo "Running tests..."
    cd "$PROJECT_ROOT"
    docker-compose exec -T django pytest -v --cov=rates_app
    ;;

  seed)
    echo "Seeding database..."
    cd "$PROJECT_ROOT"
    docker-compose exec -T django python manage.py seed_data
    ;;

  shell)
    echo "Opening Django shell..."
    cd "$PROJECT_ROOT"
    docker-compose exec django python manage.py shell
    ;;

  psql)
    echo "Connecting to PostgreSQL..."
    cd "$PROJECT_ROOT"
    docker-compose exec postgres psql -U postgres -d rate_tracker
    ;;

  redis-cli)
    echo "Connecting to Redis..."
    cd "$PROJECT_ROOT"
    docker-compose exec redis redis-cli
    ;;

  *)
    echo "Unknown command: $1"
    exit 1
    ;;
esac
