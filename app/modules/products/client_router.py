from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.products.service import ProductService
from app.modules.products.repository import ProductRepository

router = APIRouter(prefix="/products", tags=["ClientProducts"])


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    repo = ProductRepository(db)
    return ProductService(repo)


@router.get("", response_class=HTMLResponse)
def list_client_products(
    request: Request, service: ProductService = Depends(get_product_service)
):
    """
    Symmetry C: Router for end clients to consume products dynamically.
    If you ever use HTMX to load the product grid in the index, this is the ideal endpoint.
    """
    products = service.list_products(only_active=True)




    if not products:
        html_content = "<p>No hay productos activos disponibles.</p>"
    else:
        html_content = "<p>Hay productos disponibles.</p>"
    return HTMLResponse(content=html_content)
