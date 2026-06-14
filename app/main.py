"""Computer Shop API entry point."""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.agent_client import invoke_support_agent
from app.auth import require_admin
from app.config import Settings, get_settings
from app.metrics import compute_overview
from app.models import (
    AdminOverview,
    CategoryOut,
    ChatOut,
    ChatRequest,
    Order,
    OrderCreate,
    OrderLineItem,
    ProductOut,
)
from app.repository import (
    CategoryRepository,
    OrderRepository,
    ProductRepository,
    get_category_repository,
    get_order_repository,
    get_product_repository,
)

app = FastAPI(
    title="Computer Shop API",
    version="0.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/categories", response_model=list[CategoryOut], tags=["categories"])
def list_categories(
    repo: CategoryRepository = Depends(get_category_repository),
    settings: Settings = Depends(get_settings),
) -> list[CategoryOut]:
    categories = sorted(repo.list_categories(), key=lambda c: (c.sort_order, c.name))
    return [CategoryOut.from_category(c, settings.cdn_base_url) for c in categories]


@app.get("/products", response_model=list[ProductOut], tags=["products"])
def list_products(
    category: str | None = Query(default=None, description="Filter by category slug"),
    repo: ProductRepository = Depends(get_product_repository),
    category_repo: CategoryRepository = Depends(get_category_repository),
    settings: Settings = Depends(get_settings),
) -> list[ProductOut]:
    if category is not None and category_repo.get_category(category) is None:
        raise HTTPException(status_code=404, detail="Category not found")
    products = repo.list_products()
    if category is not None:
        products = [p for p in products if p.category == category]
    return [ProductOut.from_product(p, settings.cdn_base_url) for p in products]


@app.get("/products/{product_id}", response_model=ProductOut, tags=["products"])
def get_product(
    product_id: str,
    repo: ProductRepository = Depends(get_product_repository),
    settings: Settings = Depends(get_settings),
) -> ProductOut:
    product = repo.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOut.from_product(product, settings.cdn_base_url)


@app.post("/orders", response_model=Order, tags=["orders"])
def create_order(
    request: OrderCreate,
    repo: ProductRepository = Depends(get_product_repository),
    orders: OrderRepository = Depends(get_order_repository),
) -> Order:
    """Place an order. Prices, names, and categories are taken from the catalog
    server-side, so the client only chooses products and quantities, never the
    amount charged. `username` is the frontend's best-effort label (see
    OrderCreate); this route is public, so it is not an authorization fact.
    """
    line_items: list[OrderLineItem] = []
    total = Decimal("0")
    currency = "USD"
    for item in request.items:
        product = repo.get_product(item.product_id)
        if product is None:
            raise HTTPException(
                status_code=404, detail=f"Product not found: {item.product_id}"
            )
        line_total = product.price * item.quantity
        total += line_total
        currency = product.currency
        line_items.append(
            OrderLineItem(
                product_id=product.id,
                name=product.name,
                category=product.category,
                unit_price=product.price,
                quantity=item.quantity,
                line_total=line_total,
            )
        )

    order = Order(
        id=f"ord_{uuid.uuid4().hex[:12]}",
        username=request.username,
        created_at=datetime.now(timezone.utc).isoformat(),
        currency=currency,
        total=total,
        items=line_items,
    )
    orders.add_order(order)
    return order


@app.get(
    "/admin/overview",
    response_model=AdminOverview,
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
def admin_overview(
    orders: OrderRepository = Depends(get_order_repository),
) -> AdminOverview:
    """Dashboard metrics: KPIs, sales over time, top products, sales by category.
    Computed from a single scan of the orders table."""
    return compute_overview(orders.list_orders())


@app.get(
    "/admin/orders",
    response_model=list[Order],
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
def admin_orders(
    orders: OrderRepository = Depends(get_order_repository),
) -> list[Order]:
    """Recent orders, most recent first."""
    return sorted(orders.list_orders(), key=lambda o: o.created_at, reverse=True)


@app.post("/chat", response_model=ChatOut, tags=["chat"])
def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> ChatOut:
    if settings.agent_runtime_arn is None:
        raise HTTPException(status_code=503, detail="Chat is not configured")
    try:
        reply = invoke_support_agent(
            agent_runtime_arn=settings.agent_runtime_arn,
            region_name=settings.aws_region,
            session_id=request.session_id,
            message=request.message,
        )
    except Exception:
        # Whatever went wrong upstream, the customer gets one stable message.
        # Details (which may include ARNs) belong in the logs, not the response.
        logging.getLogger(__name__).exception("Support agent invocation failed")
        raise HTTPException(status_code=502, detail="Support agent unavailable")
    return ChatOut(reply=reply)
