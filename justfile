set windows-shell := ["cmd.exe", "/c"]
set dotenv-load := true
set dotenv-path := "versions.env"

dc := "docker compose"
python := if os() == "windows" { "python" } else { "python3" }

# List recipes
default:
    @just --list --unsorted

# Build Docker images
build:
    {{ dc }} build

# Start the stack
up:
    {{ dc }} up -d

# Stop the stack
down:
    {{ dc }} down

# Restart the web container
restart:
    {{ dc }} restart web

# Tail web logs
logs:
    {{ dc }} logs -f web

# Shell into the web container
shell:
    {{ dc }} exec web bash

# Apply Alembic migrations
migrate:
    {{ dc }} exec web alembic upgrade head

# Run host backup script (DB + .env + media)
backup:
    @{{ python }} backup.py

# Compile public/styles.css
css:
    {{ dc }} exec web tailwindcss -i public/tailwind.css -o public/styles.css --minify

# Verify public/styles.css is up to date
css-check:
    {{ dc }} exec web sh -c 'tailwindcss -i public/tailwind.css -o /tmp/styles.css --minify && cmp -s public/styles.css /tmp/styles.css || { echo "public/styles.css is stale. Run just css." >&2; exit 1; }'

# Format with ruff
format:
    {{ dc }} exec web ruff format .

# Verify formatting with ruff
format-check:
    {{ dc }} exec web ruff format --check .

# Lint with ruff
lint:
    {{ dc }} exec web ruff check .

# Type-check with mypy
typecheck:
    {{ dc }} exec web mypy app/

# Lint Markdown files
md-check:
    docker run --rm -v "${PWD}:/work" -w /work node:$NODE_VERSION-alpine npx markdownlint-cli2 "**/*.md"

# Run pre-commit hooks (EOF newline, trailing whitespace, LF, YAML)
pre-commit:
    {{ dc }} exec web sh -c 'git config --global --add safe.directory /app && pre-commit run --all-files'

# Run tests
test:
    {{ dc }} exec web pytest
