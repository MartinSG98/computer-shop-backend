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


def test_image_url_built_from_cdn_base(client, monkeypatch):
    monkeypatch.setenv("CDN_BASE_URL", "https://cdn.example.com")
    body = client.get("/products/gpu-a").json()
    assert body["image_url"] == "https://cdn.example.com/products/gpu-a/main.webp"
    assert "image_key" not in body  # storage detail is not exposed by the API


def test_image_url_null_when_cdn_not_configured(client, monkeypatch):
    monkeypatch.delenv("CDN_BASE_URL", raising=False)
    body = client.get("/products/gpu-a").json()
    assert body["image_url"] is None


def test_image_url_null_when_product_has_no_image(client, monkeypatch):
    monkeypatch.setenv("CDN_BASE_URL", "https://cdn.example.com")
    body = client.get("/products/cpu-b").json()  # cpu-b has no image_key
    assert body["image_url"] is None
