.PHONY: up down build shell logs restart lint format migrate reset-db backup css check-md check

include versions.env
export PYTHON_VERSION POSTGRES_VERSION TAILWIND_VERSION NODE_VERSION

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

migrate:
	$(DC) exec $(APP) alembic upgrade head

reset-db:
	@echo "WARNING: this will DELETE all data in the database."
	@test -f docker-compose.override.yml || (echo "ERROR: reset-db is disabled: docker-compose.override.yml not found. This target only runs in development. Aborting." && exit 1)
	@echo "Resetting database..."
	$(DC) down -v
	$(DC) up -d db
	@echo "Waiting for database to be ready..."
	@until $(DC) exec -T db sh -c 'pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' >/dev/null 2>&1; do sleep 1; done
	$(DC) up -d
	$(DC) exec $(APP) alembic upgrade head
	@echo "Database reset complete."

backup:
	$(DC) exec -T $(APP) python backup.py

css:
	$(DC) exec $(APP) tailwindcss -i public/tailwind.css -o public/styles.css --minify

check-md:
	docker run --rm -v "$${PWD}:/work" -w /work node:${NODE_VERSION}-alpine npx markdownlint-cli2 "**/*.md"
