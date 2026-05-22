from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi import Request
from fastapi import HTTPException
from fastapi import status

from app.modules.orders.client_router import router as client_router
from app.modules.orders.admin_router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.products.admin_router import router as products_admin_router
from app.modules.products.client_router import router as products_client_router
from app.modules.scheduling.admin_router import router as scheduling_admin_router
from app.core.templates import templates

import os

app = FastAPI(title="CookieVale API")

app.mount("/public", StaticFiles(directory="public"), name="public")
app.mount(
    "/media", StaticFiles(directory=os.environ["CONTAINER_MEDIA_PATH"]), name="media"
)


# Exception handler to gracefully redirect HTMX and normal browser requests to login
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
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="client/index.html")
