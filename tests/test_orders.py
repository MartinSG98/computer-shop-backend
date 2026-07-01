"""Checkout endpoint tests via TestClient."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Product
from app.repository import (
    InMemoryOrderRepository,
    InMemoryProductRepository,
    get_order_repository,
    get_product_repository,
)


@pytest.fixture
def order_repo() -> InMemoryOrderRepository:
    return InMemoryOrderRepository()


@pytest.fixture
def client(order_repo: InMemoryOrderRepository) -> TestClient:
    """TestClient with the product catalog and a fresh order store overridden,
    so checkout is deterministic and the stored order can be inspected."""
    products = [
        Product(id="gpu-a", name="Card A", brand="X", category="gpu", price="100.00", stock=5),
        Product(id="cpu-b", name="Chip B", brand="Y", category="cpu", price="49.99", stock=5),
    ]
    app.dependency_overrides[get_product_repository] = lambda: InMemoryProductRepository(products)
    app.dependency_overrides[get_order_repository] = lambda: order_repo
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_order_computes_total_server_side(client, order_repo):
    response = client.post(
        "/orders",
        json={
            "username": "user-normal",
            "items": [
                {"product_id": "gpu-a", "quantity": 2},
                {"product_id": "cpu-b", "quantity": 1},
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()

    # 100.00*2 + 49.99*1, computed from the catalog, serialized as a string.
    assert body["total"] == "249.99"
    assert body["currency"] == "USD"
    assert body["username"] == "user-normal"
    assert body["id"].startswith("ord_")
    assert body["created_at"]

    # Line items carry a snapshot of name/category/price.
    gpu_line = next(i for i in body["items"] if i["product_id"] == "gpu-a")
    assert gpu_line["name"] == "Card A"
    assert gpu_line["category"] == "gpu"
    assert gpu_line["unit_price"] == "100.00"
    assert gpu_line["line_total"] == "200.00"

    # The order was actually persisted.
    assert len(order_repo.list_orders()) == 1


def test_create_order_without_username_is_allowed(client):
    response = client.post("/orders", json={"items": [{"product_id": "cpu-b", "quantity": 1}]})
    assert response.status_code == 200
    assert response.json()["username"] is None


def test_unknown_product_returns_404(client, order_repo):
    response = client.post(
        "/orders",
        json={"items": [{"product_id": "does-not-exist", "quantity": 1}]},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found: does-not-exist"
    # A failed checkout stores nothing.
    assert order_repo.list_orders() == []


def test_empty_items_rejected(client):
    response = client.post("/orders", json={"items": []})
    assert response.status_code == 422


def test_zero_quantity_rejected(client):
    response = client.post("/orders", json={"items": [{"product_id": "gpu-a", "quantity": 0}]})
    assert response.status_code == 422
