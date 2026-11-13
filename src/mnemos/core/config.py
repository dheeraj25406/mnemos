from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationInfo, field_validator
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

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_async_db_url(cls, v: str | None) -> str:
        if not v:
            return "postgresql+asyncpg://mnemos:mnemos_dev_secret@localhost:5432/mnemos"
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://") and not v.startswith("postgresql+"):
            return "postgresql+asyncpg://" + v[len("postgresql://") :]
        return v

    @field_validator("sync_database_url", mode="before")
    @classmethod
    def assemble_sync_db_url(cls, v: str | None, info: ValidationInfo) -> str:
        if not v:
            db_url = info.data.get("database_url", "")
            if isinstance(db_url, str):
                if db_url.startswith("postgresql+asyncpg://"):
                    return "postgresql+psycopg://" + db_url[len("postgresql+asyncpg://") :]
                elif db_url.startswith("postgresql://"):
                    return "postgresql+psycopg://" + db_url[len("postgresql://") :]
            return "postgresql+psycopg://mnemos:mnemos_dev_secret@localhost:5432/mnemos"
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://") and not v.startswith("postgresql+"):
            return "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

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
