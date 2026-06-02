"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Category, Product
from app.repository import (
    InMemoryCategoryRepository,
    InMemoryProductRepository,
    get_category_repository,
    get_product_repository,
)


@pytest.fixture
def sample_categories() -> list[Category]:
    return [
        Category(slug="cpu", name="Processors", sort_order=1),
        Category(slug="gpu", name="Graphics Cards", sort_order=2),
    ]


@pytest.fixture
def sample_products() -> list[Product]:
    return [
        Product(id="gpu-a", name="Card A", brand="X", category="gpu", price="100.00", stock=2,
                image_key="products/gpu-a/main.webp"),
        Product(id="cpu-b", name="Chip B", brand="Y", category="cpu", price="49.99", stock=0),  # no image
    ]


@pytest.fixture
def client(sample_products: list[Product], sample_categories: list[Category]) -> TestClient:
    """TestClient with both repositories overridden to known in-memory sets.

    Using dependency_overrides keeps API tests deterministic and independent of
    seed_data.py, and bypasses the cached factories.
    """
    app.dependency_overrides[get_product_repository] = lambda: InMemoryProductRepository(sample_products)
    app.dependency_overrides[get_category_repository] = lambda: InMemoryCategoryRepository(sample_categories)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
