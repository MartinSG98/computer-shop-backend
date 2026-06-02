"""Environment-driven configuration."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    products_table: str | None
    categories_table: str | None
    aws_region: str | None
    dynamodb_endpoint_url: str | None
    cdn_base_url: str | None


def get_settings() -> Settings:
    return Settings(
        products_table=os.getenv("PRODUCTS_TABLE"),
        categories_table=os.getenv("CATEGORIES_TABLE"),
        aws_region=os.getenv("AWS_REGION"),
        dynamodb_endpoint_url=os.getenv("DYNAMODB_ENDPOINT_URL"),
        cdn_base_url=os.getenv("CDN_BASE_URL"),
    )
