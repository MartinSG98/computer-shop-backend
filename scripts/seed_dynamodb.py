"""Create the DynamoDB tables if missing and load the seed data.

Usage (PowerShell):
    $env:PRODUCTS_TABLE = "computer-shop-products"
    $env:CATEGORIES_TABLE = "computer-shop-categories"   # optional
    python -m scripts.seed_dynamodb

Honors AWS_REGION and DYNAMODB_ENDPOINT_URL (the latter for DynamoDB Local).
The categories table is only seeded when CATEGORIES_TABLE is set.
"""

import os

import boto3


def _ensure_table(ddb, table_name: str, key_attr: str):
    """Return the table, creating it (free-tier provisioned 5/5) if missing."""
    if table_name in (t.name for t in ddb.tables.all()):
        return ddb.Table(table_name)
    # Provisioned 5/5 keeps the table inside the DynamoDB always-free tier
    # (25 RCU + 25 WCU per account). Switch to BillingMode="PAY_PER_REQUEST"
    # for spiky traffic at the cost of leaving the free tier.
    table = ddb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": key_attr, "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": key_attr, "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table.wait_until_exists()
    return table


def _load(table, items) -> None:
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item.model_dump())


def main() -> None:
    ddb = boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION"),
        endpoint_url=os.getenv("DYNAMODB_ENDPOINT_URL"),
    )

    from app.seed_data import SEED_CATEGORIES, SEED_PRODUCTS

    products_table_name = os.environ["PRODUCTS_TABLE"]
    products_table = _ensure_table(ddb, products_table_name, "id")
    _load(products_table, SEED_PRODUCTS)
    print(f"Loaded {len(SEED_PRODUCTS)} products into {products_table_name}")

    categories_table_name = os.getenv("CATEGORIES_TABLE")
    if categories_table_name:
        categories_table = _ensure_table(ddb, categories_table_name, "slug")
        _load(categories_table, SEED_CATEGORIES)
        print(f"Loaded {len(SEED_CATEGORIES)} categories into {categories_table_name}")


if __name__ == "__main__":
    main()
