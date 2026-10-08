# CookieVale — Agent Guide

FastAPI + HTMX + Alpine.js + TailwindCSS + PostgreSQL bakery order management system.
Everything runs inside Docker. Never run Python commands locally — use `just` recipes.

## Commands

- `just up` / `just down` — start/stop stack
- `just build` — rebuild images
- `just lint` — ruff check (inside container)
- `just format` — ruff format (inside container)
- `just migrate` — `alembic upgrade head` (inside container)
- `just reset-db` — drop volume, recreate, run all migrations. **Development only**: refuses to run if `docker-compose.override.yml` is missing (i.e. on production checkouts).
- `just shell` — bash into the web container
- `just backup` — run `backup.py` on the host (requires the stack to be up). Exports the database via `docker compose exec` and syncs media files directly to `BACKUP_DEST` (supports local paths and SMB/network shares). Fails with a clear message when unavailable.
- `just css` — compile `public/styles.css` with `--minify`. Required every time you change `public/tailwind.css`, `tailwind.config.js`, or templates (new Tailwind classes). Must be run before `git push`.
- `just build` — rebuild Docker images. Only needed when `Dockerfile`, `requirements.txt`, or system dependencies change. Not needed for template/CSS/Python-only changes (volumes sync automatically, uvicorn `--reload` picks up Python changes).
- `just check-md` — run markdownlint-cli2 on all `.md` files
- `just check` — run everything the CI checks locally (ruff lint, ruff format check, mypy, compiled-CSS diff, markdown lint). Use before pushing instead of waiting for the pipeline.
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
- Apply: `just migrate`.

## Conventions

- **Language**: Backend code (Python vars, functions, classes, comments) in English. Frontend templates (HTML/UI text) in Spanish.
- **Typing**: Strict type hints mandatory on all functions (`->`, `:`). When fixing mypy/linter errors, never relax the config strictness (e.g. `disallow_untyped_defs`, `warn_return_any`). Fix the code, not the rules.
- **Env vars**: Use `os.environ["KEY"]` (fail-fast), never `os.getenv("KEY", "default")`.
- **Versions**: `versions.env` is the single source of truth for Python/PostgreSQL/Tailwind/Node versions. Never hardcode a version anywhere else (workflows, Dockerfile, docker-compose, configs). Documented exceptions only: the literal fallbacks in `Dockerfile`/`docker-compose.yml` (so standalone `docker build`/`docker compose` keep working) and `python_version` in `pyproject.toml` (kept in sync with the comment there).
- **Comments**: Explain WHY, not WHAT. Only comment complex business logic or edge cases.
- **HTMX**: Return HTML partials, not JSON. Use `TemplateResponse` with templates in `templates/partials/`.
- **Domain layer**: Pure `dataclass` or Pydantic models, enums, value objects. No infra dependencies.
- **Line endings**: LF everywhere. `.gitattributes` pins `versions.env`, `.env.example`, `Makefile`, `Dockerfile` and `docker-compose.yml` to LF. Never create or edit `.env` with CRLF; copy it from `.env.example`.

## Quirks

- `docker-compose.override.yml` is gitignored — provides dev `--reload` flag via uvicorn and a `tailwind` service that watches templates and recompiles CSS automatically.
- Deploy over SSH: the `deploy` job sets `$env:DOCKER_CONFIG` to a clean `{"auths":{}}` so registry pulls never depend on the host credential helper (all images are public).
- Versions (Python, PostgreSQL, Tailwind, Node) have a single source of truth: `versions.env`. The Makefile `include`s it, the Dockerfile reads it at build time, and every CI workflow sources it (see the "Load versions" step in each job). When bumping a version, edit `versions.env` only (literal fallbacks in `Dockerfile`/`docker-compose.yml` exist solely so standalone `docker build`/`docker compose` keep working).
- TailwindCSS: CSS is compiled locally via the standalone CLI (`tailwindcss`). Source config in `tailwind.config.js`, input in `public/tailwind.css` (also contains `@layer components` with custom shared classes like `.cv-input`, `.cv-btn`), output in `public/styles.css`. Run `make css` before pushing to keep the compiled CSS up to date.
- Frontend libs (htmx, Alpine, sort, Cropper) are vendored under `public/vendor/` — never reference CDNs.
- Orders: `order_items.product_name` stores the product name at order time (renaming/deleting a product must not rewrite history), each order holds one `availability_slots` slot, and a unique index (`uq_orders_availability_slot_active`) enforces one order per slot. Deleting an order frees its slot; there is no rejected status.
- Media files: host volume `MEDIA_ROOT` mounted as `CONTAINER_MEDIA_PATH` in container. Photos written to `/media/orders/<id>/`.
- Auth is HMAC-based cookie sessions (no JWT or third-party auth library).
- PostgreSQL connection uses synchronous SQLAlchemy (not async).
- Migrations use standard Alembic operations (`op.add_column`, `op.drop_column`, `op.create_index`, ...). This project runs Postgres, which supports native `ALTER TABLE`, so the SQLite-oriented `op.batch_alter_table` pattern is deliberately not used (and `render_as_batch=True` is not set in `env.py`/`alembic.ini`).
- Backup script: single `backup.py` (Python stdlib only), run via `make backup` on the host. Reads config from `.env` (and environment overrides). Dumps the DB with `docker compose exec -T db pg_dump` (password via `PGPASSWORD`), writes directly to `BACKUP_DEST` (supporting local folders and SMB/network shares), and syncs media from `MEDIA_ROOT`. Also copies `.env` into the backup. Database dump is compressed with `gzip` and integrity-verified. Keeps last 7 timestamped backups. Verifies the destination is accessible and writable, exiting with a clear error otherwise.
