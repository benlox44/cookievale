set windows-shell := ["cmd.exe", "/c"]
set dotenv-load := true
set dotenv-filename := "versions.env"

export PYTHON_VERSION := env('PYTHON_VERSION', '3.11')
export POSTGRES_VERSION := env('POSTGRES_VERSION', '15')
export TAILWIND_VERSION := env('TAILWIND_VERSION', '3.4.17')
export NODE_VERSION := env('NODE_VERSION', '20')

dc := "docker-compose"
app := "web"
python := if os() == "windows" { "python" } else { "python3" }

# List available recipes
default:
    @just --list

# Start the entire stack in the background
up:
    {{ dc }} up -d

# Stop and remove containers
down:
    {{ dc }} down

# Build docker images
build:
    {{ dc }} build

# Open a bash shell inside the web container
shell:
    {{ dc }} exec -it {{ app }} bash

# Follow backend logs
logs:
    {{ dc }} logs -f {{ app }}

# Restart the web container
restart:
    {{ dc }} restart {{ app }}

# Run Ruff linter inside the container
lint:
    {{ dc }} exec {{ app }} ruff check .

# Format code with Ruff inside the container
format:
    {{ dc }} exec {{ app }} ruff format .

# Apply database migrations
migrate:
    {{ dc }} exec {{ app }} alembic upgrade head

# Reset database (development only)
reset-db:
    @echo "WARNING: this will DELETE all data in the database."
    @test -f docker-compose.override.yml || (echo "ERROR: reset-db is disabled: docker-compose.override.yml not found. This target only runs in development. Aborting." && exit 1)
    @echo "Resetting database..."
    {{ dc }} down -v
    {{ dc }} up -d db
    @echo "Waiting for database to be ready..."
    @until {{ dc }} exec -T db sh -c 'pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' >/dev/null 2>&1; do sleep 1; done
    {{ dc }} up -d
    {{ dc }} exec {{ app }} alembic upgrade head
    @echo "Database reset complete."

# Run local backup script
backup:
    @{{ python }} backup.py

# Compile Tailwind CSS
css:
    {{ dc }} exec {{ app }} tailwindcss -i public/tailwind.css -o public/styles.css --minify

# Run pytest inside the container
test:
    {{ dc }} exec {{ app }} pip install -q -r requirements-dev.txt
    {{ dc }} exec {{ app }} pytest

# Check markdown files with markdownlint-cli2
check-md:
    docker run --rm -v "${PWD}:/work" -w /work node:{{ NODE_VERSION }}-alpine npx markdownlint-cli2 "**/*.md"

# Run all checks (ruff, mypy, pytest, css diff, markdownlint)
check:
    {{ dc }} exec {{ app }} ruff check .
    {{ dc }} exec {{ app }} ruff format --check .
    {{ dc }} exec {{ app }} mypy app/
    {{ dc }} exec {{ app }} pip install -q -r requirements-dev.txt
    {{ dc }} exec {{ app }} pytest
    @echo "Verifying compiled CSS matches the committed file..."
    {{ dc }} exec {{ app }} sh -c 'tailwindcss -i public/tailwind.css -o /tmp/styles.css --minify && cmp -s public/styles.css /tmp/styles.css || { echo "public/styles.css is stale. Run just css and commit."; exit 1; }'
    @echo "Checking markdown..."
    docker run --rm -v "${PWD}:/work" -w /work node:{{ NODE_VERSION }}-alpine npx markdownlint-cli2 "**/*.md"
    @echo "All checks passed."
