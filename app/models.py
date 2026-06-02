"""Domain models for the Computer Shop API."""

from decimal import Decimal

from pydantic import BaseModel, Field


def _image_url(image_key: str | None, cdn_base_url: str | None) -> str | None:
    if image_key and cdn_base_url:
        return f"{cdn_base_url.rstrip('/')}/{image_key.lstrip('/')}"
    return None


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
