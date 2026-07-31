# CookieVale — Agent Guide

FastAPI + HTMX + Alpine.js + TailwindCSS + PostgreSQL bakery order management system.
Everything runs inside Docker. Never run Python commands locally — use `make` targets.

## Commands

- `make up` / `make down` — start/stop stack
- `make build` — rebuild images
- `make lint` — ruff check (inside container)
- `make format` — ruff format (inside container)
- `make migrate` — `alembic upgrade head` (inside container)
- `make reset-db` — drop volume, recreate, run all migrations. **Development only**: refuses to run if `docker-compose.override.yml` is missing (i.e. on production checkouts).
- `make shell` — bash into the web container
- `make backup` — run `backup.py` inside the web container (requires the stack to be up). Exports the database and syncs media files to `$BACKUP_DEST` via the `CONTAINER_BACKUP_PATH` mount.
- `make css` — compile `public/styles.css` with `--minify`. Required every time you change `public/tailwind.css`, `tailwind.config.js`, or templates (new Tailwind classes). Must be run before `git push`.
- `make build` — rebuild Docker images. Only needed when `Dockerfile`, `requirements.txt`, or system dependencies change. Not needed for template/CSS/Python-only changes (volumes sync automatically, uvicorn `--reload` picks up Python changes).
- `make check-md` — run markdownlint-cli2 on all `.md` files
- No test suite exists currently

## Architecture — Vertical Slicing

Modules live in `app/modules/<context>/`. Each module has a fixed internal layout:

| File | Role |
| --- | --- |
| `domain.py` | Pure dataclasses + enums. No infra imports. |
| `models.py` | SQLAlchemy ORM models. |
| `repository.py` | `Protocol` interface + SQLAlchemy implementation. |
| `schemas.py` | Pydantic request/response DTOs. |
| `service.py` | Business logic. Operates on domain objects via Protocol repos. Never returns HTML. |
| `admin_router.py` / `client_router.py` | FastAPI routers. Return Jinja2 `TemplateResponse` for HTMX. |

Modules: `orders`, `products`, `auth`, `scheduling`.

Shared infra in `app/core/`: `database.py`, `dependencies.py`, `security.py`, `templates.py`, `telegram.py`.

New routers must be registered in `app/main.py` via `app.include_router()`.

## Migrations (Alembic)

- Migration scripts in `migrations/versions/`.
- **Critical**: new ORM models must be imported in `migrations/env.py` or autogenerate won't detect them.
- Generate: `alembic revision --autogenerate -m "description"` (inside container).
- Apply: `make migrate`.

## Conventions

- **Language**: Backend code (Python vars, functions, classes, comments) in English. Frontend templates (HTML/UI text) in Spanish.
- **Typing**: Strict type hints mandatory on all functions (`->`, `:`). When fixing mypy/linter errors, never relax the config strictness (e.g. `disallow_untyped_defs`, `warn_return_any`). Fix the code, not the rules.
- **Env vars**: Use `os.environ["KEY"]` (fail-fast), never `os.getenv("KEY", "default")`.
- **Versions**: `versions.env` is the single source of truth for Python/PostgreSQL/Tailwind/Node versions. Never hardcode a version anywhere else (workflows, Dockerfile, docker-compose, configs). Documented exceptions only: the literal fallbacks in `Dockerfile`/`docker-compose.yml` (so standalone `docker build`/`docker compose` keep working) and `python_version` in `pyproject.toml` (kept in sync with the comment there).
- **Comments**: Explain WHY, not WHAT. Only comment complex business logic or edge cases.
- **HTMX**: Return HTML partials, not JSON. Use `TemplateResponse` with templates in `templates/partials/`.
- **Domain layer**: Pure `dataclass` or Pydantic models, enums, value objects. No infra dependencies.

## Quirks

- `docker-compose.override.yml` is gitignored — provides dev `--reload` flag via uvicorn and a `tailwind` service that watches templates and recompiles CSS automatically.
- Versions (Python, PostgreSQL, Tailwind, Node) have a single source of truth: `versions.env`. The Makefile `include`s it, the Dockerfile reads it at build time, and every CI workflow sources it (see the "Load versions" step in each job). When bumping a version, edit `versions.env` only (literal fallbacks in `Dockerfile`/`docker-compose.yml` exist solely so standalone `docker build`/`docker compose` keep working).
- TailwindCSS: CSS is compiled locally via the standalone CLI (`tailwindcss`). Source config in `tailwind.config.js`, input in `public/tailwind.css` (also contains `@layer components` with custom shared classes like `.cv-input`, `.cv-btn`), output in `public/styles.css`. Run `make css` before pushing to keep the compiled CSS up to date.
- Media files: host volume `MEDIA_ROOT` mounted as `CONTAINER_MEDIA_PATH` in container. Photos written to `/media/orders/<id>/`.
- Auth is HMAC-based cookie sessions (no JWT or third-party auth library).
- PostgreSQL connection uses synchronous SQLAlchemy (not async).
- `alembic.ini` uses `render_as_batch=True` for SQLite compatibility (even though this project uses Postgres).
- Backup script: single `backup.py` (Python stdlib only), run via `make backup` inside the web container. Reads env vars fail-fast via `os.environ["KEY"]` (injected by compose `env_file`/`environment`); no fallbacks. Dumps the DB with `pg_dump -h db` (password via `PGPASSWORD`), writes to `CONTAINER_BACKUP_PATH` (`/app_backup`, mounted from `$BACKUP_DEST`), and syncs media from `CONTAINER_MEDIA_PATH`. Database dump is compressed with `gzip` and integrity-verified. Keeps last 7 timestamped backups.
