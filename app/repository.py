"""Data access layer for products.

`ProductRepository` is the interface the API depends on. The factory picks the
DynamoDB implementation when a table is configured, and otherwise falls back to
the in-memory one so the app runs with zero AWS setup.
"""

from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import get_settings
from app.models import Category, Order, Product
from app.seed_data import SEED_CATEGORIES, SEED_PRODUCTS


class ProductRepository(ABC):
    @abstractmethod
    def list_products(self) -> list[Product]:
        ...

    @abstractmethod
    def get_product(self, product_id: str) -> Product | None:
        ...


class InMemoryProductRepository(ProductRepository):
    def __init__(self, products: list[Product] | None = None) -> None:
        seed = products if products is not None else SEED_PRODUCTS
        self._products = {p.id: p for p in seed}

    def list_products(self) -> list[Product]:
        return list(self._products.values())

    def get_product(self, product_id: str) -> Product | None:
        return self._products.get(product_id)


class DynamoDBProductRepository(ProductRepository):
    def __init__(
        self,
        table_name: str,
        *,
        region_name: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        # Imported lazily so the in-memory path never pays the boto3 import cost.
        import boto3

        resource = boto3.resource(
            "dynamodb", region_name=region_name, endpoint_url=endpoint_url
        )
        self._table = resource.Table(table_name)

    def list_products(self) -> list[Product]:
        items: list[dict] = []
        kwargs: dict = {}
        while True:
            response = self._table.scan(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key
        return [Product(**item) for item in items]

    def get_product(self, product_id: str) -> Product | None:
        response = self._table.get_item(Key={"id": product_id})
        item = response.get("Item")
        return Product(**item) if item else None


@lru_cache
def get_product_repository() -> ProductRepository:
    """Return the repository implementation. Cached so it's a singleton."""
    settings = get_settings()
    if settings.products_table:
        return DynamoDBProductRepository(
            settings.products_table,
            region_name=settings.aws_region,
            endpoint_url=settings.dynamodb_endpoint_url,
        )
    return InMemoryProductRepository()


class CategoryRepository(ABC):
    @abstractmethod
    def list_categories(self) -> list[Category]:
        ...

    @abstractmethod
    def get_category(self, slug: str) -> Category | None:
        ...


class InMemoryCategoryRepository(CategoryRepository):
    def __init__(self, categories: list[Category] | None = None) -> None:
        seed = categories if categories is not None else SEED_CATEGORIES
        self._categories = {c.slug: c for c in seed}

    def list_categories(self) -> list[Category]:
        return list(self._categories.values())

    def get_category(self, slug: str) -> Category | None:
        return self._categories.get(slug)


class DynamoDBCategoryRepository(CategoryRepository):
    def __init__(
        self,
        table_name: str,
        *,
        region_name: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        # Imported lazily so the in-memory path never pays the boto3 import cost.
        import boto3

        resource = boto3.resource(
            "dynamodb", region_name=region_name, endpoint_url=endpoint_url
        )
        self._table = resource.Table(table_name)

    def list_categories(self) -> list[Category]:
        items: list[dict] = []
        kwargs: dict = {}
        while True:
            response = self._table.scan(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key
        return [Category(**item) for item in items]

    def get_category(self, slug: str) -> Category | None:
        response = self._table.get_item(Key={"slug": slug})
        item = response.get("Item")
        return Category(**item) if item else None


@lru_cache
def get_category_repository() -> CategoryRepository:
    """Return the repository implementation. Cached so it's a singleton."""
    settings = get_settings()
    if settings.categories_table:
        return DynamoDBCategoryRepository(
            settings.categories_table,
            region_name=settings.aws_region,
            endpoint_url=settings.dynamodb_endpoint_url,
        )
    return InMemoryCategoryRepository()


class OrderRepository(ABC):
    @abstractmethod
    def add_order(self, order: Order) -> None:
        ...

    @abstractmethod
    def list_orders(self) -> list[Order]:
        ...


class InMemoryOrderRepository(OrderRepository):
    def __init__(self, orders: list[Order] | None = None) -> None:
        self._orders: dict[str, Order] = {o.id: o for o in (orders or [])}

    def add_order(self, order: Order) -> None:
        self._orders[order.id] = order

    def list_orders(self) -> list[Order]:
        return list(self._orders.values())


class DynamoDBOrderRepository(OrderRepository):
    def __init__(
        self,
        table_name: str,
        *,
        region_name: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        # Imported lazily so the in-memory path never pays the boto3 import cost.
        import boto3

        resource = boto3.resource(
            "dynamodb", region_name=region_name, endpoint_url=endpoint_url
        )
        self._table = resource.Table(table_name)

    def add_order(self, order: Order) -> None:
        # model_dump keeps Decimals as Decimal (DynamoDB rejects float), so the
        # money fields store cleanly without a float round-trip.
        self._table.put_item(Item=order.model_dump())

    def list_orders(self) -> list[Order]:
        items: list[dict] = []
        kwargs: dict = {}
        while True:
            response = self._table.scan(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key
        return [Order(**item) for item in items]


@lru_cache
def get_order_repository() -> OrderRepository:
    """Return the repository implementation. Cached so it's a singleton."""
    settings = get_settings()
    if settings.orders_table:
        return DynamoDBOrderRepository(
            settings.orders_table,
            region_name=settings.aws_region,
            endpoint_url=settings.dynamodb_endpoint_url,
        )
    return InMemoryOrderRepository()
