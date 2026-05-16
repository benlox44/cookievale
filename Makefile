.PHONY: up down build shell logs restart lint format migrate reset-db backup

DC := docker-compose
APP := web

ifeq ($(OS),Windows_NT)
    SLEEP := timeout /t 5 /nobreak > NUL
else
    SLEEP := sleep 5
endif

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

migrate:
	$(DC) exec $(APP) alembic upgrade head

reset-db:
	@echo "Resetting database..."
	$(DC) down -v
	$(DC) up -d
	@echo "Waiting for database to be ready..."
	@$(SLEEP)
	$(DC) exec $(APP) alembic upgrade head
	@echo "Database reset complete."

backup:
	@cmd /c "backup.bat"
