from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.templates import templates
from app.core.security import ADMIN_PASSWORD, create_admin_token

router = APIRouter(prefix="/admin", tags=["Auth"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def get_admin_panel(request: Request):
    from app.core.security import get_current_admin

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
def post_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        token = create_admin_token()
        # Ensure we use an HTTP 303 Redirect so the browser redirects via GET
        response = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="admin_session", value=token, httponly=True, samesite="lax"
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
