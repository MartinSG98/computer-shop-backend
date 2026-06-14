"""Admin auth guard, metrics aggregation, and admin endpoints."""

from decimal import Decimal

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.auth import _groups_from_claims, require_admin
from app.main import app
from app.metrics import compute_overview
from app.models import Order, OrderLineItem
from app.repository import InMemoryOrderRepository, get_order_repository


def _order(order_id: str, day: str, lines: list[tuple[str, str, str, str, int]]) -> Order:
    """Build an order. Each line is (product_id, name, category, unit_price, qty)."""
    items = [
        OrderLineItem(
            product_id=pid,
            name=name,
            category=cat,
            unit_price=Decimal(price),
            quantity=qty,
            line_total=Decimal(price) * qty,
        )
        for pid, name, cat, price, qty in lines
    ]
    total = sum((i.line_total for i in items), Decimal("0"))
    return Order(id=order_id, username="user-normal", created_at=f"{day}T10:00:00+00:00",
                 total=total, items=items)


SAMPLE_ORDERS = [
    _order("ord_1", "2026-06-10", [("gpu-a", "Card A", "gpu", "100.00", 2)]),
    _order("ord_2", "2026-06-11", [("gpu-a", "Card A", "gpu", "100.00", 1),
                                   ("cpu-b", "Chip B", "cpu", "50.00", 1)]),
]


# --- auth guard ---------------------------------------------------------------

def _request_with_groups(groups: str) -> Request:
    event = {"requestContext": {"authorizer": {"jwt": {"claims": {"cognito:groups": groups}}}}}
    return Request({"type": "http", "aws.event": event})


def test_groups_parsed_from_bracketed_string():
    assert _groups_from_claims({"cognito:groups": "[admins manager]"}) == {"admins", "manager"}


def test_groups_empty_when_claim_absent():
    assert _groups_from_claims({}) == set()


def test_require_admin_noop_without_gateway_event():
    # No aws.event in scope (local/dev/tests): guard does nothing.
    assert require_admin(Request({"type": "http"})) is None


def test_require_admin_allows_admin_group():
    assert require_admin(_request_with_groups("[admins]")) is None


def test_require_admin_rejects_non_admin():
    with pytest.raises(HTTPException) as exc:
        require_admin(_request_with_groups("[shoppers]"))
    assert exc.value.status_code == 403


# --- metrics ------------------------------------------------------------------

def test_compute_overview_aggregates():
    overview = compute_overview(SAMPLE_ORDERS)

    assert overview.summary.order_count == 2
    assert overview.summary.total_revenue == Decimal("350.00")  # 200 + 150
    assert overview.summary.units_sold == 4
    assert overview.summary.average_order_value == Decimal("175.00")

    # Two distinct days, sorted ascending.
    assert [d.date for d in overview.sales_over_time] == ["2026-06-10", "2026-06-11"]

    # gpu-a leads on units (3 vs 1).
    assert overview.top_products[0].product_id == "gpu-a"
    assert overview.top_products[0].units == 3
    assert overview.top_products[0].revenue == Decimal("300.00")

    categories = {c.category: c for c in overview.sales_by_category}
    assert categories["gpu"].units == 3
    assert categories["cpu"].revenue == Decimal("50.00")


def test_compute_overview_empty():
    overview = compute_overview([])
    assert overview.summary.order_count == 0
    assert overview.summary.total_revenue == Decimal("0")
    assert overview.summary.average_order_value == Decimal("0.00")
    assert overview.sales_over_time == []
    assert overview.top_products == []


# --- endpoints ----------------------------------------------------------------

@pytest.fixture
def client() -> TestClient:
    repo = InMemoryOrderRepository(SAMPLE_ORDERS)
    app.dependency_overrides[get_order_repository] = lambda: repo
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_admin_overview_endpoint(client):
    body = client.get("/admin/overview").json()
    assert body["summary"]["order_count"] == 2
    assert body["summary"]["total_revenue"] == "350.00"
    assert body["top_products"][0]["product_id"] == "gpu-a"


def test_admin_orders_endpoint_most_recent_first(client):
    body = client.get("/admin/orders").json()
    assert [o["id"] for o in body] == ["ord_2", "ord_1"]
