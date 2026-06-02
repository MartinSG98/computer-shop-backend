"""Environment-driven configuration."""

import os
from dataclasses import dataclass

# Local Vite dev server origins, used when CORS_ALLOW_ORIGINS is not set.
_DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


@dataclass(frozen=True)
class Settings:
    products_table: str | None
    categories_table: str | None
    aws_region: str | None
    dynamodb_endpoint_url: str | None
    cdn_base_url: str | None
    cors_allow_origins: list[str]


def _parse_origins(value: str | None) -> list[str]:
    if not value:
        return list(_DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def get_settings() -> Settings:
    return Settings(
        products_table=os.getenv("PRODUCTS_TABLE"),
        categories_table=os.getenv("CATEGORIES_TABLE"),
        aws_region=os.getenv("AWS_REGION"),
        dynamodb_endpoint_url=os.getenv("DYNAMODB_ENDPOINT_URL"),
        cdn_base_url=os.getenv("CDN_BASE_URL"),
        cors_allow_origins=_parse_origins(os.getenv("CORS_ALLOW_ORIGINS")),
    )