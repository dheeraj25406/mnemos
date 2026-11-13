from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from mnemos.core.config import get_settings
from mnemos.db.base import Base

settings = get_settings()

# Async Engine for FastAPI runtime & async services
async_engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.db_echo,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync Engine for Alembic migrations & sync CLI tasks
sync_engine = create_engine(
    settings.sync_database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.db_echo,
    future=True,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an isolated async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Ensure vector extensions and initialize database tables and default tenant."""
    async with async_engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector";'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm";'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "btree_gist";'))
        await conn.run_sync(Base.metadata.create_all)
        # Ensure HNSW vector index and FTS GIN index exist
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_memory_embeddings_vector_hnsw "
            "ON memory_embeddings USING hnsw (embedding vector_cosine_ops);"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_memories_fts "
            "ON memories USING gin(to_tsvector('english', normalized_content));"
        ))

    from mnemos.core.security import hash_api_key
    from mnemos.db.models import APIKey, Tenant

    async with AsyncSessionLocal() as session:
        t = await session.get(Tenant, settings.default_tenant_id)
        if not t:
            tenant = Tenant(
                id=settings.default_tenant_id,
                name="Default Tenant",
                config={},
            )
            session.add(tenant)
            key = APIKey(
                id="key_default_root",
                tenant_id=settings.default_tenant_id,
                key_hash=hash_api_key(settings.default_tenant_key),
                key_prefix=settings.default_tenant_key[:12],
                name="default_key",
                rate_limit=1000,
            )
            session.add(key)
            await session.commit()
