"""DynamoDB repository tests against mocked AWS (moto)."""

from decimal import Decimal

import boto3
import pytest
from moto import mock_aws

from app.repository import DynamoDBCategoryRepository, DynamoDBProductRepository
from app.seed_data import SEED_CATEGORIES, SEED_PRODUCTS

REGION = "us-east-1"
TABLE = "products-test"
CATEGORIES_TABLE = "categories-test"


@pytest.fixture
def dynamodb_table(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name=REGION)
        table = ddb.create_table(
            TableName=TABLE,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        table.wait_until_exists()
        with table.batch_writer() as batch:
            for product in SEED_PRODUCTS:
                batch.put_item(Item=product.model_dump())
        yield TABLE


def test_list_returns_all_seed_products(dynamodb_table):
    repo = DynamoDBProductRepository(TABLE, region_name=REGION)
    products = repo.list_products()
    assert len(products) == len(SEED_PRODUCTS)


def test_get_returns_typed_product_with_decimal_price(dynamodb_table):
    repo = DynamoDBProductRepository(TABLE, region_name=REGION)
    product = repo.get_product("cpu-ryzen-9800x3d")
    assert product is not None
    assert product.name == "Ryzen 7 9800X3D"
    assert product.price == Decimal("479.00")
    assert isinstance(product.stock, int)


def test_get_unknown_returns_none(dynamodb_table):
    repo = DynamoDBProductRepository(TABLE, region_name=REGION)
    assert repo.get_product("nope") is None


@pytest.fixture
def dynamodb_categories_table(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name=REGION)
        table = ddb.create_table(
            TableName=CATEGORIES_TABLE,
            KeySchema=[{"AttributeName": "slug", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "slug", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        table.wait_until_exists()
        with table.batch_writer() as batch:
            for category in SEED_CATEGORIES:
                batch.put_item(Item=category.model_dump())
        yield CATEGORIES_TABLE


def test_list_returns_all_seed_categories(dynamodb_categories_table):
    repo = DynamoDBCategoryRepository(CATEGORIES_TABLE, region_name=REGION)
    assert len(repo.list_categories()) == len(SEED_CATEGORIES)


def test_get_returns_typed_category(dynamodb_categories_table):
    repo = DynamoDBCategoryRepository(CATEGORIES_TABLE, region_name=REGION)
    category = repo.get_category("processors")
    assert category is not None
    assert category.name == "Processors"
    assert isinstance(category.sort_order, int)


def test_get_unknown_category_returns_none(dynamodb_categories_table):
    repo = DynamoDBCategoryRepository(CATEGORIES_TABLE, region_name=REGION)
    assert repo.get_category("nope") is None
