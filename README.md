# CookieVale - Order Management System

A custom order management system for a boutique bakery. Built with FastAPI, HTMX, TailwindCSS, Alpine.js, and PostgreSQL using a Vertical Slicing and Domain-Driven Design (DDD) approach.

## Quick Start

1. **Clone & Setup:**
   ```bash
   git clone <repo-url>
   cd cookievale
   ```

2. **Environment handling:**
   *Set up your `.env` variables if overriding default docker settings.*

3. **Start the Application:**
    ```bash
    make up
    ```

4. **Open in Browser:**
    ```
    http://localhost:8000
    ```

## Development Commands

We rely on a `Makefile` to encapsulate Docker operations.

| Command | Description |
|---------|-------------|
| `make build` | Rebuild docker images |
| `make up` | Spin up the entire stack in the background |
| `make down` | Tear down the stack |
| `make restart` | Restart the web container |
| `make logs` | Attach to the backend logs |
| `make shell` | Open a continuous bash session inside the web container |
| `make lint` | Run Ruff to check code quality |
| `make format` | Run Ruff to auto-format code |
| `make migrate` | Apply all pending Alembic migrations (`alembic upgrade head`) |
| `make reset-db` | Drop the database volume, recreate it, and apply all migrations |
| `make backup` | Dump the database and sync media to `BACKUP_DEST` (see `.env`) |
| `make css` | Compile `public/styles.css` with `--minify` (run before git push) |

## Stack

- **Backend:** FastAPI (Async, Type-Safe)
- **Database:** PostgreSQL (with SQLAlchemy ORM & Alembic for migrations)
- **Data Validation:** Pydantic (DTOs / Schemas) & Python Dataclasses
- **Frontend:** HTMX + Alpine.js + Jinja2 Templates + TailwindCSS (Lightweight reactivity)

## Architecture

The app is built upon **Vertical Slices**.
Instead of grouping files by technical concern (e.g. all models together, all routers together), everything related to a specific business feature (e.g., `orders`, `products`, `auth`) lives in its respective folder inside `app/modules/`.

## Client & Admin Routes

*   **Client:**
    *   `GET /orders/new` - Interactive client form to select products and place orders.
*   **Admin:**
    *   `GET /admin/login` - Admin authentication page.
    *   `GET /admin/products` - Products management dashboard.
    *   `GET /admin/orders` - Main dashboard with HTMX real-time updates and search.
    *   `GET /admin/orders/{id}` - Detail view, editing, and status flow control.
