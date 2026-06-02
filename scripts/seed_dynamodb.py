"""Create the products table if missing and load the seed assortment.

Usage (PowerShell):
    $env:PRODUCTS_TABLE = "computer-shop-products"
    python -m scripts.seed_dynamodb

Honors AWS_REGION and DYNAMODB_ENDPOINT_URL (the latter for DynamoDB Local).
"""

import os

import boto3


def main() -> None:
    table_name = os.environ["PRODUCTS_TABLE"]
    ddb = boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION"),
        endpoint_url=os.getenv("DYNAMODB_ENDPOINT_URL"),
    )

    if table_name not in (t.name for t in ddb.tables.all()):
        # Provisioned 5/5 keeps the table inside the DynamoDB always-free tier
        # (25 RCU + 25 WCU per account). Switch to BillingMode="PAY_PER_REQUEST"
        # for spiky traffic at the cost of leaving the free tier.
        table = ddb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        table.wait_until_exists()
    else:
        table = ddb.Table(table_name)

    from app.seed_data import SEED_PRODUCTS

    with table.batch_writer() as batch:
        for product in SEED_PRODUCTS:
            batch.put_item(Item=product.model_dump())

    print(f"Loaded {len(SEED_PRODUCTS)} products into {table_name}")


if __name__ == "__main__":
    main()
