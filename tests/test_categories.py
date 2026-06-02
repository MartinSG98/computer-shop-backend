"""Category endpoint, product filtering, and seed-integrity tests."""

from app.seed_data import SEED_CATEGORIES, SEED_PRODUCTS


def test_list_categories_sorted_by_sort_order(client):
    body = client.get("/categories").json()
    assert [c["slug"] for c in body] == ["cpu", "gpu"]  # sort_order 1, then 2


def test_categories_do_not_expose_raw_image_key(client):
    body = client.get("/categories").json()
    assert "image_key" not in body[0]
    assert "image_url" in body[0]


def test_filter_products_by_category(client):
    body = client.get("/products?category=gpu").json()
    assert [p["id"] for p in body] == ["gpu-a"]


def test_filter_unknown_category_returns_404(client):
    response = client.get("/products?category=does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_no_category_filter_returns_all(client):
    body = client.get("/products").json()
    assert len(body) == 2


def test_every_seed_product_has_a_valid_category():
    """Referential integrity: every product's category slug exists in the taxonomy."""
    slugs = {c.slug for c in SEED_CATEGORIES}
    orphans = [p.id for p in SEED_PRODUCTS if p.category not in slugs]
    assert orphans == []
