# CookieVale Architecture Rules & Copilot Instructions

## 1. Architectural Pattern (Vertical Slicing & DDD)
This project uses **Vertical Slicing** combined with **Domain-Driven Design (DDD)** concepts. Code that changes together stays together in `app/modules/<context>/`.
- **Domain**: Pure pure entities (`dataclass` or Pydantic models), Enums, Value Objects. No infrastructural dependencies.
- **Application (Services/Use Cases)**: Business logic algorithms. Operates on pure entities using abstract repository interfaces. Must never return HTML.
- **Infrastructure (Repositories)**: SQLAlchemy implementations of the abstract interfaces.
- **Presentation (Routers)**: FastAPI controllers. They handle HTMX requests, inject dependencies, call Application services, and return Jinja2 HTML partials/views.

## 2. HTMX & Frontend Philosophy
- Return HTML, not JSON (unless specifically defining a 3rd party API).
- Use `TemplateResponse` from Jinja2 to render partials located in `templates/partials/`.

## 3. Strict Coding Conventions
- **Language**: Backend code in English only (vars, functions, classes, comments, docs). Front-end templates (HTML/UI) MUST be in Spanish.
- **Typing**: Strict type hinting is mandatory (`->`, `:`).
- **Comments**: Explain the **WHY**, never the **WHAT**. Do not write comments explaining obvious code (e.g. `app = FastAPI()`). Only comment complex business logic or edge cases.

## 4. Environment & Dependencies
- **Fail Fast**: Never use fallbacks or defaults for critical environment variables (e.g. `os.getenv("URL", "default")`). Use `os.environ["URL"]` so the app crashes immediately if misconfigured.
- Do not run local python commands. Everything runs inside Docker.
- Use `make` commands.
