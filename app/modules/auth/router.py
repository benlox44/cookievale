import hmac

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.core.config import ADMIN_PASSWORD
from app.core.rate_limit import limiter
from app.core.security import SESSION_TTL_SECONDS, create_admin_token, require_admin
from app.core.templates import templates

router = APIRouter(prefix="/admin", tags=["Auth"])


@router.get("", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def get_admin_panel(request: Request) -> Response:
    return templates.TemplateResponse(request=request, name="admin/panel.html")


@router.get("/login", response_class=HTMLResponse)
def get_login(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="admin/login.html")


@router.post("/login")
@limiter.limit("5/hour")
def post_login(request: Request, password: str = Form(...)) -> Response:
    if hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode()):
        token = create_admin_token()

        response = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="admin_session",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=SESSION_TTL_SECONDS,
        )
        return response

    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={"error": "Contraseña incorrecta. Intenta de nuevo."},
    )


@router.post("/logout")
def post_logout() -> RedirectResponse:
    response = RedirectResponse(
        url="/admin/login", status_code=status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie("admin_session")
    return response
