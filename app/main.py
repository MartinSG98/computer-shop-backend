"""Computer Shop API entry point."""

from fastapi import Depends, FastAPI, HTTPException

from app.config import Settings, get_settings
from app.models import CategoryOut, ProductOut
from app.repository import (
    CategoryRepository,
    ProductRepository,
    get_category_repository,
    get_product_repository,
)

app = FastAPI(
    title="Computer Shop API",
    version="0.3.0",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/categories", response_model=list[CategoryOut], tags=["categories"])
def list_categories(
    repo: CategoryRepository = Depends(get_category_repository),
    settings: Settings = Depends(get_settings),
) -> list[CategoryOut]:
    categories = sorted(repo.list_categories(), key=lambda c: (c.sort_order, c.name))
    return [CategoryOut.from_category(c, settings.cdn_base_url) for c in categories]


@app.get("/products", response_model=list[ProductOut], tags=["products"])
def list_products(
    repo: ProductRepository = Depends(get_product_repository),
    settings: Settings = Depends(get_settings),
) -> list[ProductOut]:
    return [ProductOut.from_product(p, settings.cdn_base_url) for p in repo.list_products()]


@app.get("/products/{product_id}", response_model=ProductOut, tags=["products"])
def get_product(
    product_id: str,
    repo: ProductRepository = Depends(get_product_repository),
    settings: Settings = Depends(get_settings),
) -> ProductOut:
    product = repo.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOut.from_product(product, settings.cdn_base_url)
