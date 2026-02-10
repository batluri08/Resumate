.PHONY: help docker-build docker-up docker-down docker-logs docker-shell docker-db docker-clean docker-rebuild test

help:
	@echo "RestlessResume Docker Commands"
	@echo "=============================="
	@echo "make docker-build    - Build Docker image"
	@echo "make docker-up       - Start all services"
	@echo "make docker-down     - Stop all services"
	@echo "make docker-logs     - View application logs"
	@echo "make docker-shell    - Access app bash shell"
	@echo "make docker-db       - Connect to PostgreSQL"
	@echo "make docker-clean    - Remove containers and volumes"
	@echo "make docker-rebuild  - Rebuild and restart all services"
	@echo "make docker-status   - Show container status"
	@echo "make docker-backup   - Backup database"
	@echo "make test            - Run tests in container"

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f app

docker-logs-db:
	docker-compose logs -f postgres

docker-shell:
	docker-compose exec app bash

docker-db:
	docker-compose exec postgres psql -U ${DB_USER:-resumeuser} -d ${DB_NAME:-restless_resume}

docker-clean:
	docker-compose down -v
	docker system prune -f

docker-rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

docker-status:
	docker-compose ps

docker-backup:
	@mkdir -p backups
	docker-compose exec -T postgres pg_dump -U ${DB_USER:-resumeuser} ${DB_NAME:-restless_resume} > backups/backup-$$(date +%Y%m%d-%H%M%S).sql
	@echo "Database backed up to backups/backup-$$(date +%Y%m%d-%H%M%S).sql"

docker-restore:
	@read -p "Enter backup file path: " backup_file; \
	docker-compose exec -T postgres psql -U ${DB_USER:-resumeuser} ${DB_NAME:-restless_resume} < $$backup_file
	@echo "Database restored"

prod-up:
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f app

dev-up:
	docker-compose up -d

dev-down:
	docker-compose down

test:
	docker-compose exec app python -m pytest tests/ -v

lint:
	docker-compose exec app python -m pylint app/

format:
	docker-compose exec app python -m black app/
	docker-compose exec app python -m isort app/

install-dev-deps:
	pip install pytest pytest-cov pylint black isort

.DEFAULT_GOAL := help
