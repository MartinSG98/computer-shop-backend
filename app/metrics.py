"""Sales aggregation for the admin dashboard.

Pure functions over a list of orders, so the metrics are unit-testable without
DynamoDB or HTTP. At demo scale the dashboard scans the whole orders table and
aggregates here, which avoids paying for a secondary index (see the infra
module's "Cost posture").
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from app.models import (
    AdminOverview,
    Order,
    SalesByCategory,
    SalesByDay,
    SalesSummary,
    TopProduct,
)

_CENTS = Decimal("0.01")


def compute_overview(orders: list[Order], *, top_n: int = 10) -> AdminOverview:
    total_revenue = Decimal("0")
    units_sold = 0

    day_revenue: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    day_orders: dict[str, int] = defaultdict(int)

    product_units: dict[str, int] = defaultdict(int)
    product_revenue: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    product_name: dict[str, str] = {}

    category_units: dict[str, int] = defaultdict(int)
    category_revenue: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for order in orders:
        total_revenue += order.total
        day = order.created_at[:10]  # YYYY-MM-DD
        day_revenue[day] += order.total
        day_orders[day] += 1
        for item in order.items:
            units_sold += item.quantity
            product_units[item.product_id] += item.quantity
            product_revenue[item.product_id] += item.line_total
            product_name[item.product_id] = item.name
            category_units[item.category] += item.quantity
            category_revenue[item.category] += item.line_total

    order_count = len(orders)
    average = (
        (total_revenue / order_count).quantize(_CENTS, rounding=ROUND_HALF_UP)
        if order_count
        else Decimal("0.00")
    )

    summary = SalesSummary(
        order_count=order_count,
        total_revenue=total_revenue,
        average_order_value=average,
        units_sold=units_sold,
    )

    sales_over_time = [
        SalesByDay(date=day, revenue=day_revenue[day], orders=day_orders[day])
        for day in sorted(day_revenue)
    ]

    top_products = sorted(
        (
            TopProduct(
                product_id=pid,
                name=product_name[pid],
                units=product_units[pid],
                revenue=product_revenue[pid],
            )
            for pid in product_units
        ),
        key=lambda p: (p.units, p.revenue),
        reverse=True,
    )[:top_n]

    sales_by_category = sorted(
        (
            SalesByCategory(
                category=category,
                units=category_units[category],
                revenue=category_revenue[category],
            )
            for category in category_units
        ),
        key=lambda c: c.revenue,
        reverse=True,
    )

    return AdminOverview(
        summary=summary,
        sales_over_time=sales_over_time,
        top_products=top_products,
        sales_by_category=sales_by_category,
    )
