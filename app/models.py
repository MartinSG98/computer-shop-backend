"""Domain models for the Computer Shop API."""

from decimal import Decimal

from pydantic import BaseModel, Field


def _image_url(image_key: str | None, cdn_base_url: str | None) -> str | None:
    if image_key and cdn_base_url:
        return f"{cdn_base_url.rstrip('/')}/{image_key.lstrip('/')}"
    return None


class CompatAttributes(BaseModel):
    """Typed, build-relevant facts that drive the PC configurator's compatibility
    engine. Flat and all-optional: each product fills only the fields relevant to
    its category (peripherals leave it unset). Human-readable display still uses
    `specs`; this is the machine-comparable counterpart.
    """

    # Processors (socket also on motherboards; tdp_w also on graphics cards)
    socket: str | None = None
    tdp_w: int | None = None
    has_igpu: bool | None = None

    # CPU coolers
    sockets: list[str] | None = None
    cooler_type: str | None = None  # "air" | "aio"
    height_mm: int | None = None  # air coolers
    radiator_mm: int | None = None  # AIO coolers
    tdp_rating_w: int | None = None  # cooling capacity, compared to CPU tdp_w

    # Motherboards (form_factor also reused by power supplies: "ATX" | "SFX")
    form_factor: str | None = None
    memory_type: str | None = None  # also on memory: "DDR5"
    memory_slots: int | None = None
    memory_max_gb: int | None = None
    m2_slots: int | None = None

    # Memory
    modules: int | None = None  # sticks in the kit
    capacity_gb: int | None = None
    speed_mts: int | None = None

    # Graphics cards
    length_mm: int | None = None
    recommended_psu_w: int | None = None

    # Storage
    storage_form_factor: str | None = None  # "M.2" | "2.5" | "3.5"
    interface: str | None = None  # "NVMe" | "SATA"

    # Power supplies
    wattage_w: int | None = None

    # Cases
    form_factors: list[str] | None = None  # board form factors the case accepts
    max_gpu_length_mm: int | None = None
    max_cooler_height_mm: int | None = None
    max_radiator_mm: int | None = None
    psu_form_factors: list[str] | None = None

    # Relative positioning tier (1 = entry .. 4 = flagship), for balance/overkill
    # advice. Set on processors, graphics cards and motherboards only.
    tier: int | None = None


class ProductBase(BaseModel):
    id: str
    name: str
    brand: str
    category: str  # category slug, references Category.slug
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = "USD"
    stock: int = Field(ge=0)
    description: str = ""
    specs: dict[str, str] = Field(default_factory=dict)
    attributes: CompatAttributes | None = None


class Product(ProductBase):
    """Stored representation (the DynamoDB item shape). Holds the S3 object key."""

    image_key: str | None = None


class ProductOut(ProductBase):
    """API response shape. Exposes a full image URL instead of the raw key."""

    image_url: str | None = None

    @classmethod
    def from_product(cls, product: Product, cdn_base_url: str | None) -> "ProductOut":
        return cls(
            **product.model_dump(exclude={"image_key"}),
            image_url=_image_url(product.image_key, cdn_base_url),
        )


class CategoryBase(BaseModel):
    slug: str
    name: str
    description: str = ""
    sort_order: int = 0


class Category(CategoryBase):
    """Stored representation. Holds the optional S3 object key for a nav icon."""

    image_key: str | None = None


class CategoryOut(CategoryBase):
    """API response shape. Exposes a full image URL instead of the raw key."""

    image_url: str | None = None

    @classmethod
    def from_category(cls, category: Category, cdn_base_url: str | None) -> "CategoryOut":
        return cls(
            **category.model_dump(exclude={"image_key"}),
            image_url=_image_url(category.image_key, cdn_base_url),
        )


class OrderItemIn(BaseModel):
    """One requested checkout line: a product and how many. The price, name, and
    category are resolved server-side from the catalog, never trusted from the
    client."""

    product_id: str
    quantity: int = Field(ge=1, le=100)


class OrderCreate(BaseModel):
    """Checkout request body.

    `username` is supplied by the frontend from its signed-in context. It is not
    server-verified (checkout is a public route), so treat it as a best-effort
    label, not an authorization fact.
    """

    items: list[OrderItemIn] = Field(min_length=1, max_length=50)
    username: str | None = None


class OrderLineItem(BaseModel):
    """A line within a stored order. Name, category, and price are snapshotted at
    purchase time so historical orders and the sales metrics don't shift when the
    catalog is later re-priced or re-categorised."""

    product_id: str
    name: str
    category: str
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    quantity: int = Field(ge=1)
    line_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class Order(BaseModel):
    """Stored representation (the DynamoDB item shape) and the API response shape;
    an order has no client-hidden fields, so one model serves both."""

    id: str
    username: str | None = None
    created_at: str  # ISO 8601, UTC
    currency: str = "USD"
    total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    items: list[OrderLineItem]


class ChatRequest(BaseModel):
    """One customer message to the support agent.

    The length cap bounds the Bedrock token spend per request; the session id
    minimum is an AgentCore requirement (>= 33 chars), enforced here so bad ids
    fail fast as a 422 instead of deep inside the invoke call.
    """

    message: str = Field(min_length=1, max_length=500)
    session_id: str = Field(min_length=33, max_length=100)


class ChatOut(BaseModel):
    """API response shape: the agent's reply text."""

    reply: str
