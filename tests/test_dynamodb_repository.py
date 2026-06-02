"""DynamoDBProductRepository tests against mocked AWS (moto)."""

from decimal import Decimal

import boto3
import pytest
from moto import mock_aws

from app.repository import DynamoDBProductRepository
from app.seed_data import SEED_PRODUCTS

REGION = "us-east-1"
TABLE = "products-test"


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
    product = repo.get_product("cpu-ryzen-7800x3d")
    assert product is not None
    assert product.name == "Ryzen 7 7800X3D"
    assert product.price == Decimal("349.00")
    assert isinstance(product.stock, int)


def test_get_unknown_returns_none(dynamodb_table):
    repo = DynamoDBProductRepository(TABLE, region_name=REGION)
    assert repo.get_product("nope") is None
