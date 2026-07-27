import logging
import re

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.dependencies import get_product_service
from app.core.security import get_current_admin
from app.core.templates import templates
from app.modules.products.schemas import (
    ProductCreate,
    ProductReorderRequest,
    ProductUpdate,
)
from app.modules.products.service import ProductService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/products", tags=["AdminProducts"])

MEDIA_URL_PATTERN = re.compile(r"^/media/products/\d+/[a-f0-9]+\.\w+$")


def _validate_existing_images(urls: list[str]) -> list[str]:
    return [url for url in urls if MEDIA_URL_PATTERN.match(url)]


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
    price: int = Form(...),
    description: str = Form(...),
    is_active: bool = Form(False),
    photos: list[UploadFile] | None = File(None),
    service: ProductService = Depends(get_product_service),
    admin: str = Depends(get_current_admin),
):
    if photos is None:
        photos = []
    dto = ProductCreate(
        name=name, price=price, description=description, is_active=is_active
    )
    service.create_product(dto, photos)
    return RedirectResponse(
        url="/admin/products", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/reorder")
def reorder_products(
    request: ProductReorderRequest,
    service: ProductService = Depends(get_product_service),
    admin: str = Depends(get_current_admin),
):
    service.reorder_products(request.ordered_ids)
    return {"status": "success"}


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
    price: int = Form(...),
    description: str = Form(...),
    is_active: bool = Form(False),
    existing_images: list[str] = Form([]),
    photos: list[UploadFile] | None = File(None),
    service: ProductService = Depends(get_product_service),
    admin: str = Depends(get_current_admin),
):
    validated_images = _validate_existing_images(existing_images)
    dto = ProductUpdate(
        name=name, price=price, description=description, is_active=is_active
    )
    service.update_product(product_id, dto, validated_images, photos)
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
    except Exception as e:
        logger.error("Failed to delete product %d: %s", product_id, e)
    return RedirectResponse(
        url="/admin/products", status_code=status.HTTP_303_SEE_OTHER
    )
