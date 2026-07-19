from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.core.dependencies import get_product_service
from app.modules.products.service import ProductService

router = APIRouter(prefix="/products", tags=["ClientProducts"])


@router.get("", response_class=HTMLResponse)
def list_client_products(
    request: Request, service: ProductService = Depends(get_product_service)
):
    products = service.list_products(only_active=True)

    if not products:
        html_content = "<p>No hay productos activos disponibles.</p>"
    else:
        html_content = "<p>Hay productos disponibles.</p>"
    return HTMLResponse(content=html_content)
