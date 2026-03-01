"""
Application configuration -- environment-aware settings.

Uses Pydantic Settings for type-safe config loaded from environment
variables or .env files. No hardcoded secrets anywhere.

Finance analogy:
- This is the "configuration management" layer
- Each environment (dev/staging/prod) has its own config
- Secrets come from env vars (in prod, from AWS Secrets Manager)
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""

    # Environment
    environment: Literal["dev", "staging", "prod"] = "dev"

    # Database
    database_url: str = "postgresql://sommelier:sommelier_dev@localhost:5432/sommelier"

    # AWS (LocalStack in dev)
    aws_endpoint_url: str | None = "http://localhost:4566"
    aws_region: str = "eu-west-2"
    s3_landing_bucket: str = "sommelier-landing"

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    # Wine Society credentials (for scraping)
    wine_society_email: str = ""
    wine_society_password: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
