<div align="center">
  <img src="public/icons/icon.png" alt="CookieVale" width="200">
  <br/>
  <h1>CookieVale — Order Management System</h1>
  <p>A custom order management system for a boutique bakery.</p>
</div>

## Quick Start

**Prerequisites**: Docker with Compose v2+ and [`just`](https://github.com/casey/just). Everything runs inside Docker.

1. **Configure environment:**

   ```bash
   cp .env.example .env
   ```

   Fill in every value in `.env` (the app is fail-fast and refuses to start if any variable is missing).

2. **Start the stack:**

   ```bash
   just up
   ```

   Open `http://localhost:8000` (Swagger UI is available at `/docs` when `DEBUG=True`).

## Commands

Run `just` to list all available recipes:

| Command | Description |
| --- | --- |
| `just build` | Build Docker images |
| `just up` / `just down` | Start or stop the stack |
| `just restart` | Restart the web container |
| `just logs` | Tail web container logs |
| `just shell` | Open a bash shell in the web container |
| `just migrate` | Apply pending Alembic migrations |
| `just backup` | Export DB dump, `.env`, and media to `BACKUP_DEST` (keeps last 7) |
| `just css` | Compile `public/styles.css` with Tailwind (`--minify`) |
| `just css-check` | Verify `public/styles.css` matches Tailwind output |
| `just format` / `just format-check` | Format or verify formatting with Ruff |
| `just lint` | Lint Python code with Ruff |
| `just typecheck` | Type-check `app/` with mypy |
| `just md-check` | Lint Markdown files with markdownlint-cli2 |
| `just pre-commit` | Run pre-commit hooks (EOF newline, trailing whitespace, LF, YAML) |
| `just test` | Run pytest suite |

## Stack & Architecture

- **Backend:** FastAPI, SQLAlchemy 2.0 (sync), PostgreSQL, Alembic, Pydantic
- **Frontend:** Jinja2, HTMX, Alpine.js, TailwindCSS (vendored assets in `public/vendor/`)
- **Architecture:** Vertical slices under `app/modules/{orders,products,scheduling,auth}` with shared infrastructure in `app/core/`.
