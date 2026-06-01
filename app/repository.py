"""Data access layer for products.

`ProductRepository` is the interface the API depends on. Today the only
implementation is in-memory; a DynamoDB-backed one is added later behind the
same interface, so the API never changes when the store does.
"""

from abc import ABC, abstractmethod
from functools import lru_cache

from app.models import Product
from app.seed_data import SEED_PRODUCTS


class ProductRepository(ABC):
    @abstractmethod
    def list_products(self) -> list[Product]:
        ...

    @abstractmethod
    def get_product(self, product_id: str) -> Product | None:
        ...


class InMemoryProductRepository(ProductRepository):
    def __init__(self, products: list[Product] | None = None) -> None:
        seed = products if products is not None else SEED_PRODUCTS
        self._products = {p.id: p for p in seed}

    def list_products(self) -> list[Product]:
        return list(self._products.values())

    def get_product(self, product_id: str) -> Product | None:
        return self._products.get(product_id)


@lru_cache
def get_product_repository() -> ProductRepository:
    """Return the repository implementation. Cached so it's a singleton.

    Later this chooses DynamoDB vs in-memory based on environment.
    """
    return InMemoryProductRepository()
