"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Product
from app.repository import InMemoryProductRepository, get_product_repository


@pytest.fixture
def sample_products() -> list[Product]:
    return [
        Product(id="gpu-a", name="Card A", brand="X", category="GPU", price="100.00", stock=2,
                image_key="products/gpu-a/main.webp"),
        Product(id="cpu-b", name="Chip B", brand="Y", category="CPU", price="49.99", stock=0),  # no image
    ]


@pytest.fixture
def client(sample_products: list[Product]) -> TestClient:
    """TestClient with the repository overridden to a known in-memory set.

    Using dependency_overrides keeps API tests deterministic and independent of
    seed_data.py, and bypasses the cached factory.
    """
    repo = InMemoryProductRepository(sample_products)
    app.dependency_overrides[get_product_repository] = lambda: repo
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
