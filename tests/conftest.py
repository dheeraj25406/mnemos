import pytest_asyncio
from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from mnemos.core.config import get_settings
from mnemos.db.models import Tenant, APIKey
from mnemos.core.security import hash_api_key

settings = get_settings()

test_engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,
    echo=False,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a fresh transactional async database session per test."""
    async with TestingSessionLocal() as session:
        # Ensure default test tenant exists
        t = await session.get(Tenant, "tenant_test")
        if not t:
            tenant = Tenant(
                id="tenant_test",
                name="Test Tenant",
                config={},
            )
            session.add(tenant)
            key = APIKey(
                id="key_test_1",
                tenant_id="tenant_test",
                key_hash=hash_api_key("mnk_test_secret_key_12345"),
                key_prefix="mnk_test_sec",
                name="test_key",
                rate_limit=1000,
            )
            session.add(key)
            await session.commit()

        yield session
        await session.rollback()
