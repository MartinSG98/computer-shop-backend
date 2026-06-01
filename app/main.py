"""Computer Shop API entry point."""

from fastapi import Depends, FastAPI, HTTPException

from app.models import Product
from app.repository import ProductRepository, get_product_repository

app = FastAPI(
    title="Computer Shop API",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/products", response_model=list[Product], tags=["products"])
def list_products(
    repo: ProductRepository = Depends(get_product_repository),
) -> list[Product]:
    return repo.list_products()


@app.get("/products/{product_id}", response_model=Product, tags=["products"])
def get_product(
    product_id: str,
    repo: ProductRepository = Depends(get_product_repository),
) -> Product:
    product = repo.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
