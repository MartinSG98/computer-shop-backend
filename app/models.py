"""Domain models for the Computer Shop API."""

from decimal import Decimal

from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    id: str
    name: str
    brand: str
    category: str
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = "USD"
    stock: int = Field(ge=0)
    description: str = ""
    specs: dict[str, str] = Field(default_factory=dict)


class Product(ProductBase):
    """Stored representation (the DynamoDB item shape). Holds the S3 object key."""

    image_key: str | None = None


class ProductOut(ProductBase):
    """API response shape. Exposes a full image URL instead of the raw key."""

    image_url: str | None = None

    @classmethod
    def from_product(cls, product: Product, cdn_base_url: str | None) -> "ProductOut":
        image_url = None
        if product.image_key and cdn_base_url:
            image_url = f"{cdn_base_url.rstrip('/')}/{product.image_key.lstrip('/')}"
        return cls(**product.model_dump(exclude={"image_key"}), image_url=image_url)
