import logging
from urllib.parse import quote

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
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import get_product_service
from app.core.security import require_admin
from app.core.templates import templates
from app.modules.products.schemas import (
    ProductCreate,
    ProductReorderRequest,
    ProductUpdate,
)
from app.modules.products.service import ProductService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/products",
    tags=["AdminProducts"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_class=HTMLResponse)
def list_products(
    request: Request,
    service: ProductService = Depends(get_product_service),
) -> HTMLResponse:
    products = service.list_products()
    return templates.TemplateResponse(
        request=request,
        name="admin/products_dashboard.html",
        context={"products": products},
    )


@router.get("/new", response_class=HTMLResponse)
def new_product_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="admin/product_form.html")


@router.post("")
def create_product(
    name: str = Form(...),
    price: int = Form(...),
    description: str = Form(...),
    is_active: bool = Form(False),
    photos: list[UploadFile] | None = File(None),
    service: ProductService = Depends(get_product_service),
) -> RedirectResponse:
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
) -> dict[str, str]:
    service.reorder_products(request.ordered_ids)
    return {"status": "success"}


@router.get("/{product_id}", response_class=HTMLResponse)
def edit_product_form(
    product_id: int,
    request: Request,
    service: ProductService = Depends(get_product_service),
) -> HTMLResponse:
    product = service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse(
        request=request,
        name="admin/product_form.html",
        context={"product": product},
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
) -> RedirectResponse:
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
) -> RedirectResponse:
    try:
        service.delete_product(product_id)
    except (ValueError, IntegrityError) as e:
        logger.warning("Delete blocked for product %d: %s", product_id, e)
        return RedirectResponse(
            url=f"/admin/products?error={quote(str(e))}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(
        url="/admin/products", status_code=status.HTTP_303_SEE_OTHER
    )
