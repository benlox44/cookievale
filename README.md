<div align="center">
  <img src="public/icons/icon.png" alt="CookieVale" width="200">
  <br/>
  <h1>CookieVale — Order Management System</h1>
  <p>A custom order management system for a boutique bakery.</p>
</div>

## Quick Start

**Prerequisites**: Docker with the Compose plugin (v2+) installed and running. This project runs entirely inside Docker — Python, Node, Tailwind and PostgreSQL are never installed on your machine.

1. **Clone the repo:**

   ```bash
   git clone https://github.com/benlox44/cookievale.git
   cd cookievale
   ```

2. **Create your environment file:**

   ```bash
   cp .env.example .env
   ```

   Then fill in **every** value: the PostgreSQL credentials, `SECRET_KEY`, `ADMIN_PASSWORD`, `BASE_URL`, `MEDIA_ROOT`, `BACKUP_DEST` and the Telegram bot token. The app is fail-fast: if any variable is missing it will refuse to start, so don't skip any.

3. **Start the stack:**

   ```bash
   make up
   ```

   The first run builds the Docker image, which can take a few minutes. In development the Tailwind watcher and uvicorn `--reload` run automatically.

4. **Open in your browser:**

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
| `make reset-db` | Drop the database volume, recreate it, and apply all migrations. **Development only**: refuses to run when `docker-compose.override.yml` is missing (i.e. on production checkouts). |
| `make backup` | Run `backup.py` in a throwaway web container that mounts `BACKUP_DEST` only for the backup. The app never depends on it. Fails with a clear message if unavailable. |
| `make check-md` | Run markdownlint-cli2 on all `.md` files |
| `make css` | Compile `public/styles.css` with `--minify`. Required when changing `public/tailwind.css`, `tailwind.config.js`, or templates (new Tailwind classes). Run before `git push`. |
| `make check` | Run every check the CI runs locally: ruff lint, ruff format check, mypy, compiled-CSS diff and markdown lint. |

## Stack

- **Backend:** FastAPI (Async, Type-Safe)
- **Database:** PostgreSQL (with SQLAlchemy ORM & Alembic for migrations)
- **Data Validation:** Pydantic (DTOs / Schemas) & Python Dataclasses
- **Frontend:** HTMX + Alpine.js + Jinja2 Templates + TailwindCSS (Lightweight reactivity)

## Architecture

The app is built upon **Vertical Slices**.
Instead of grouping files by technical concern (e.g. all models together, all routers together), everything related to a specific business feature (e.g., `orders`, `products`, `auth`) lives in its respective folder inside `app/modules/`.

## Routes

### Client

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Landing page with products and order CTA. |
| `GET` | `/products` | Client products listing. |
| `GET` | `/orders/new` | Interactive client form to select products and place orders. |
| `POST` | `/orders` | Submit a new order. |

### Auth

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/admin/login` | Admin authentication page. |
| `POST` | `/admin/login` | Authenticate with `ADMIN_PASSWORD` (HMAC cookie session). |
| `POST` | `/admin/logout` | End the admin session. |
| `GET` | `/admin` | Admin panel homepage (redirects to login if unauthenticated). |

### Orders (admin)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/admin/orders` | Main dashboard with HTMX real-time updates and search. |
| `GET` | `/admin/orders/new` | Admin order creation form. |
| `POST` | `/admin/orders` | Create an order. |
| `GET` | `/admin/orders/{order_id}` | Order detail view. |
| `POST` | `/admin/orders/{order_id}` | Update an order. |
| `POST` | `/admin/orders/{order_id}/status` | Advance or change order status. |
| `POST` | `/admin/orders/{order_id}/delete` | Delete an order. |

### Products (admin)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/admin/products` | Products management dashboard. |
| `GET` | `/admin/products/new` | Product creation form. |
| `POST` | `/admin/products` | Create a product. |
| `POST` | `/admin/products/reorder` | Reorder the products list. |
| `GET` | `/admin/products/{product_id}` | Product detail/edit form. |
| `POST` | `/admin/products/{product_id}` | Update a product. |
| `POST` | `/admin/products/{product_id}/delete` | Delete a product. |

### Delivery dates (admin)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/admin/dates` | Delivery dates calendar and scheduling. |
| `POST` | `/admin/dates` | Create or update a delivery date. |
| `DELETE` | `/admin/dates/{date_id}` | Delete a delivery date. |

### System

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check (JSON): app and database connectivity status. |

### Static files

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/public/*` | Compiled CSS, favicons, icons and background images. |
| `GET` | `/media/*` | Uploaded order media. |
