from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.templates import templates
from app.core.security import ADMIN_PASSWORD, create_admin_token, get_current_admin

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/admin", tags=["Auth"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def get_admin_panel(request: Request):
    try:
        admin = get_current_admin(request)
        return templates.TemplateResponse(
            request=request, name="admin/panel.html", context={"admin_user": admin}
        )
    except Exception:
        return RedirectResponse(
            url="/admin/login", status_code=status.HTTP_303_SEE_OTHER
        )


@router.get("/login", response_class=HTMLResponse)
def get_login(request: Request):
    return templates.TemplateResponse(request=request, name="admin/login.html")


@router.post("/login")
@limiter.limit("5/minute")
def post_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        token = create_admin_token()

        response = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="admin_session",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=8 * 60 * 60,
        )
        return response

    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={"error": "Contraseña incorrecta. Intenta de nuevo."},
    )


@router.post("/logout")
def post_logout():
    response = RedirectResponse(
        url="/admin/login", status_code=status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie("admin_session")
    return response
