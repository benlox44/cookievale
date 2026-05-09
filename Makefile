is .PHONY: up down build shell logs restart lint format reset-db backup

DC := docker-compose
APP := web

up:
	$(DC) up -d

down:
	$(DC) down

build:
	$(DC) build

shell:
	$(DC) exec -it $(APP) bash

logs:
	$(DC) logs -f $(APP)

restart:
	$(DC) restart $(APP)

lint:
	$(DC) exec $(APP) ruff check .

format:
	$(DC) exec $(APP) ruff format .

reset-db:
	@echo "Resetting database..."
	$(DC) down -v
	$(DC) up -d
	@echo "Waiting for database to be ready..."
	@sleep 5
	$(DC) exec $(APP) alembic upgrade head
	@echo "Database reset complete."

backup:
	@cmd /c "backup.bat"
