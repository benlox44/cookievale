# CookieVale — Agent Guide

FastAPI + HTMX + Alpine.js + TailwindCSS + PostgreSQL bakery order management system.
Everything runs inside Docker. Use `just` recipes (`just --list`) instead of running tools on the host.

## Architecture — Vertical Slicing

Modules live in `app/modules/{orders,products,scheduling,auth}/`, with shared infrastructure in `app/core/`.

| File | Role |
| --- | --- |
| `domain.py` | Pure dataclasses and enums (no infrastructure imports). |
| `models.py` | SQLAlchemy ORM models. |
| `repository.py` | `Protocol` interface + SQLAlchemy implementation. |
| `schemas.py` | Pydantic DTOs. |
| `service.py` | Business logic operating on domain objects via repository protocols. |
| `admin_router.py` / `client_router.py` / `router.py` | FastAPI routers returning Jinja2 `TemplateResponse` or redirects. |

Register new routers in `app/main.py`, and import new ORM models in `migrations/env.py` so Alembic autogenerate detects them.

## Conventions & Quirks

- **Language**: Code, identifiers, and comments in English; user-facing UI/error strings in Spanish.
- **Typing**: `mypy --strict` is enforced on `app/`. Never weaken type-checking rules to silence errors.
- **Configuration**: Fail-fast via `os.environ["KEY"]` in `app/core/config.py` (no defaults). `DATABASE_URL` is composed in `docker-compose.yml` from `POSTGRES_*`.
- **Single source of versions**: `versions.env` defines `PYTHON_VERSION`, `POSTGRES_VERSION`, `TAILWIND_VERSION`, and `NODE_VERSION` for `just`, Docker builds, CI, and deploy.
- **Comments**: Only document non-obvious *why* decisions or security constraints.
- **Templates & Frontend**: Templates live in `templates/{admin,client,components}/`. Frontend JS/CSS libraries are vendored in `public/vendor/` (no CDNs). Run `just css` after changing Tailwind classes or `public/tailwind.css`.
- **Line endings & hygiene**: LF everywhere (`.gitattributes`). Run `just pre-commit` before committing.
- **Orders & slots**: `order_items.product_name` snapshots the product name at order time. Each order holds an `availability_slots` row (enforced by unique index `uq_orders_availability_slot_active`); deleting an order or moving it to another date also removes its previous slot.
- **Dev overrides**: `docker-compose.override.yml` (gitignored) enables uvicorn `--reload` and a `tailwind --watch` container.
