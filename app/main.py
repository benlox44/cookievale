import logging
import os
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import engine
from app.core.templates import templates
from app.modules.auth.router import router as auth_router
from app.modules.orders.admin_router import router as admin_router
from app.modules.orders.client_router import router as client_router
from app.modules.products.admin_router import router as products_admin_router
from app.modules.products.client_router import router as products_client_router
from app.modules.scheduling.admin_router import router as scheduling_admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="CookieVale API")

DEBUG = os.environ.get("DEBUG", "").lower() == "true"


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

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Demasiados intentos. Intenta de nuevo en un minuto."},
    )


app.mount("/public", StaticFiles(directory="public"), name="public")
app.mount(
    "/media", StaticFiles(directory=os.environ["CONTAINER_MEDIA_PATH"]), name="media"
)


@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def unauthorized_exception_handler(
    request: Request, exc: HTTPException
) -> RedirectResponse:
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


app.include_router(client_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(products_admin_router)
app.include_router(products_client_router)
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
