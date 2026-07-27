# CookieVale — Agent Guide

FastAPI + HTMX + Alpine.js + TailwindCSS + PostgreSQL bakery order management system.
Everything runs inside Docker. Never run Python commands locally — use `make` targets.

## Commands

- `make up` / `make down` — start/stop stack
- `make build` — rebuild images
- `make lint` — ruff check (inside container)
- `make format` — ruff format (inside container)
- `make migrate` — `alembic upgrade head` (inside container)
- `make reset-db` — drop volume, recreate, run all migrations
- `make shell` — bash into the web container
- `make backup` — export database + sync media files to `$BACKUP_DEST` (see `.env`)
- `make css` — compile `public/styles.css` with `--minify` (run before git push)
- No test suite exists currently

## Architecture — Vertical Slicing

Modules live in `app/modules/<context>/`. Each module has a fixed internal layout:

| File | Role |
|---|---|
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
- **Typing**: Strict type hints mandatory on all functions (`->`, `:`).
- **Env vars**: Use `os.environ["KEY"]` (fail-fast), never `os.getenv("KEY", "default")`.
- **Comments**: Explain WHY, not WHAT. Only comment complex business logic or edge cases.
- **HTMX**: Return HTML partials, not JSON. Use `TemplateResponse` with templates in `templates/partials/`.
- **Domain layer**: Pure `dataclass` or Pydantic models, enums, value objects. No infra dependencies.

## Quirks

- `docker-compose.override.yml` is gitignored — provides dev `--reload` flag via uvicorn and a `tailwind` service that watches templates and recompiles CSS automatically.
- TailwindCSS: CSS is compiled locally via the standalone CLI (`tailwindcss`). Source config in `tailwind.config.js`, input in `public/tailwind.css`, output in `public/styles.css`. Run `make css` before pushing to keep the compiled CSS up to date.
- Media files: host volume `MEDIA_ROOT` mounted as `CONTAINER_MEDIA_PATH` in container. Photos written to `/media/orders/<id>/`.
- Auth is HMAC-based cookie sessions (no JWT or third-party auth library).
- PostgreSQL connection uses synchronous SQLAlchemy (not async).
- `alembic.ini` uses `render_as_batch=True` for SQLite compatibility (even though this project uses Postgres).
- Backup script: single `backup.py` (Python stdlib only) with custom `.env` parser to handle special characters in `SECRET_KEY`. Database dump is compressed with `gzip` and integrity-verified. Keeps last 7 timestamped backups. Works identically on Windows and Linux.
