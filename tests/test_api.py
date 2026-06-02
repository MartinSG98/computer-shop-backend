"""API-level tests via TestClient."""


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_products(client):
    response = client.get("/products")
    assert response.status_code == 200
    ids = [p["id"] for p in response.json()]
    assert ids == ["gpu-a", "cpu-b"]


def test_get_product_serializes_price_as_string(client):
    response = client.get("/products/cpu-b")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Chip B"
    assert body["price"] == "49.99"  # Decimal preserved as a string, not a float


def test_get_unknown_product_returns_404(client):
    response = client.get("/products/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"
