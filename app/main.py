import logging
from collections.abc import Awaitable, Callable
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.config import CONTAINER_MEDIA_PATH, DEBUG, TRUSTED_PROXY_HOSTS
from app.core.database import engine
from app.core.rate_limit import limiter
from app.core.templates import templates
from app.modules.auth.router import router as auth_router
from app.modules.orders.admin_router import router as admin_router
from app.modules.orders.client_router import router as client_router
from app.modules.products.admin_router import router as products_admin_router
from app.modules.scheduling.admin_router import router as scheduling_admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="CookieVale API")


class HttpsRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not DEBUG:
            proto = request.headers.get("x-forwarded-proto", "")
            if proto and proto != "https":
                url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(url), status_code=301)
        return await call_next(request)


app.add_middleware(HttpsRedirectMiddleware)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=TRUSTED_PROXY_HOSTS)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={
            "error": "Contraseña incorrecta. Intenta de nuevo.",
            "rate_limited": True,
        },
    )


app.mount("/public", StaticFiles(directory="public"), name="public")
app.mount("/media", StaticFiles(directory=CONTAINER_MEDIA_PATH), name="media")


@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def unauthorized_exception_handler(
    request: Request, exc: HTTPException
) -> RedirectResponse:
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


def _validation_error_response(request: Request, exc: Exception) -> Response:
    is_json = (request.headers.get("content-type") or "").startswith("application/json")
    if request.url.path.startswith("/admin") and not is_json:
        message = "Datos inválidos en el formulario. Revisa los campos."
        referer = request.headers.get("referer") or "/admin"
        base = referer.split("?")[0]
        return RedirectResponse(
            url=f"{base}?error={quote(message)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    errors: list[object] = getattr(exc, "errors", list)()
    return JSONResponse(status_code=422, content={"detail": errors})


app.add_exception_handler(RequestValidationError, _validation_error_response)
app.add_exception_handler(ValidationError, _validation_error_response)


app.include_router(client_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(products_admin_router)
app.include_router(scheduling_admin_router)


@app.get("/health", response_model=None)
def health_check() -> dict[str, str] | JSONResponse:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": "unavailable"},
        )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="client/index.html")
