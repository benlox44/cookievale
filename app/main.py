import logging
import os

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

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

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Demasiados intentos. Intenta de nuevo en un minuto."},
    )


app.mount("/public", StaticFiles(directory="public"), name="public")
app.mount(
    "/media", StaticFiles(directory=os.environ["CONTAINER_MEDIA_PATH"]), name="media"
)


@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def unauthorized_exception_handler(request: Request, exc: HTTPException):
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


app.include_router(client_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(products_admin_router)
app.include_router(products_client_router)
app.include_router(scheduling_admin_router)


@app.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": "unavailable"},
        )


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="client/index.html")
