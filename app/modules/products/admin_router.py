from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form,
    UploadFile,
    File,
    HTTPException,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List

from app.core.templates import templates
from app.core.security import get_current_admin
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.modules.products.service import ProductService
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import ProductCreate, ProductUpdate

router = APIRouter(prefix="/admin/products", tags=["AdminProducts"])


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    repo = ProductRepository(db)
    return ProductService(repo)


@router.get("", response_class=HTMLResponse)
def list_products(
    request: Request,
    service: ProductService = Depends(get_product_service),
    admin: str = Depends(get_current_admin),
):
    products = service.list_products()
    return templates.TemplateResponse(
        request=request,
        name="admin/products_dashboard.html",
        context={"products": products, "admin_user": admin},
    )


@router.get("/new", response_class=HTMLResponse)
def new_product_form(request: Request, admin: str = Depends(get_current_admin)):
    return templates.TemplateResponse(
        request=request, name="admin/product_form.html", context={"admin_user": admin}
    )


@router.post("")
def create_product(
    name: str = Form(...),
    price: float = Form(...),
    description: str = Form(...),
    is_active: bool = Form(False),
    photos: List[UploadFile] = File(...),
    service: ProductService = Depends(get_product_service),
    admin: str = Depends(get_current_admin),
):
    dto = ProductCreate(
        name=name, price=price, description=description, is_active=is_active
    )
    service.create_product(dto, photos)
    return RedirectResponse(
        url="/admin/products", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/{product_id}", response_class=HTMLResponse)
def edit_product_form(
    product_id: int,
    request: Request,
    service: ProductService = Depends(get_product_service),
    admin: str = Depends(get_current_admin),
):
    product = service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse(
        request=request,
        name="admin/product_form.html",
        context={"product": product, "admin_user": admin},
    )


@router.post("/{product_id}")
def update_product(
    product_id: int,
    name: str = Form(...),
    price: float = Form(...),
    description: str = Form(...),
    is_active: bool = Form(False),
    existing_images: List[str] = Form([]),
    photos: List[UploadFile] = File(None),
    service: ProductService = Depends(get_product_service),
    admin: str = Depends(get_current_admin),
):
    dto = ProductUpdate(
        name=name, price=price, description=description, is_active=is_active
    )
    service.update_product(product_id, dto, existing_images, photos)
    return RedirectResponse(
        url="/admin/products", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{product_id}/delete")
def delete_product(
    product_id: int,
    request: Request,
    service: ProductService = Depends(get_product_service),
    admin: str = Depends(get_current_admin),
):
    try:
        service.delete_product(product_id)
    except BaseException:
        # If it fails due to foreign keys, redirect with an error param or whatever (just redirect for now)
        pass
    return RedirectResponse(
        url="/admin/products", status_code=status.HTTP_303_SEE_OTHER
    )
