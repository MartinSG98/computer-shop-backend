"""Domain models for the Computer Shop API."""

from decimal import Decimal

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str
    name: str
    brand: str
    category: str
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = "USD"
    stock: int = Field(ge=0)
    description: str = ""
    image_url: str | None = None
    specs: dict[str, str] = Field(default_factory=dict)
