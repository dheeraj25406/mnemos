from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    app_name: str = "Mnemos"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_v1_prefix: str = "/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["*"]

    # Security & Multi-tenancy
    api_key_header_name: str = "X-Mnemos-API-Key"
    default_tenant_id: str = "tenant_default"
    default_tenant_key: str = "mnk_test_secret_key_12345"
    rate_limit_per_minute: int = 600

    # PostgreSQL Database
    database_url: str = Field(
        default="postgresql+asyncpg://mnemos:mnemos_dev_secret@localhost:5432/mnemos"
    )
    sync_database_url: str = Field(
        default="postgresql+psycopg://mnemos:mnemos_dev_secret@localhost:5432/mnemos"
    )
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300

    # Embeddings
    embedding_provider: Literal["fastembed", "mock", "openai"] = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    # Graph Traversal
    default_max_graph_depth: int = 3
    max_graph_nodes: int = 200

    # Consolidation
    consolidation_similarity_threshold: float = 0.85
    consolidation_batch_size: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
