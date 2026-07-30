<div align="center">
  <img src="public/icons/icon.png" alt="CookieVale" width="200">
  <br/>
  <h1>CookieVale — Order Management System</h1>
  <p>A custom order management system for a boutique bakery.</p>
</div>

## Quick Start

1. **Clone & Setup:**

   ```bash
   git clone https://github.com/benlox44/cookievale.git
   cd cookievale
   ```

2. **Environment handling:**
   Set up your `.env` variables if overriding default Docker settings.

3. **Start the Application:**

   ```bash
   make up
   ```

4. **Open in Browser:**

   ```text
   http://localhost:8000
   ```

## Development Commands

We rely on a `Makefile` to encapsulate Docker operations.

| Command | Description |
| --- | --- |
| `make build` | Rebuild docker images. Only needed when `Dockerfile`, `requirements.txt`, or system dependencies change. |
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
| `make check-md` | Run markdownlint-cli2 on all `.md` files |
| `make css` | Compile `public/styles.css` with `--minify`. Required when changing `public/tailwind.css`, `tailwind.config.js`, or templates (new Tailwind classes). Run before `git push`. |

## Stack

- **Backend:** FastAPI (Async, Type-Safe)
- **Database:** PostgreSQL (with SQLAlchemy ORM & Alembic for migrations)
- **Data Validation:** Pydantic (DTOs / Schemas) & Python Dataclasses
- **Frontend:** HTMX + Alpine.js + Jinja2 Templates + TailwindCSS (Lightweight reactivity)

## Architecture

The app is built upon **Vertical Slices**.
Instead of grouping files by technical concern (e.g. all models together, all routers together), everything related to a specific business feature (e.g., `orders`, `products`, `auth`) lives in its respective folder inside `app/modules/`.

## Client & Admin Routes

- **Client:**
  - `GET /` — Landing page with products and order CTA.
  - `GET /orders/new` — Interactive client form to select products and place orders.
- **Admin:**
  - `GET /admin` — Admin panel homepage (redirects to login if unauthenticated).
  - `GET /admin/login` — Admin authentication page.
  - `GET /admin/orders` — Main dashboard with HTMX real-time updates and search.
  - `GET /admin/orders/new` — Admin order creation form.
  - `GET /admin/orders/{id}` — Detail view, editing, and status flow control.
  - `GET /admin/products` — Products management dashboard.
  - `GET /admin/products/new` — Product creation form.
  - `GET /admin/dates` — Delivery dates calendar and scheduling.
