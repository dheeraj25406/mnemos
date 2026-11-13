import pytest_asyncio
from collections.abc import AsyncGenerator
from sqlalchemy import select, text
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
        # Ensure default test tenants exist
        for tid, tname, tkey in [
            ("tenant_test", "Test Tenant", "mnk_test_secret_key_12345"),
            (settings.default_tenant_id, "Default Tenant", settings.default_tenant_key),
        ]:
            t = await session.get(Tenant, tid)
            if not t:
                tenant = Tenant(
                    id=tid,
                    name=tname,
                    config={},
                )
                session.add(tenant)
                # Check if key hash already exists
                kh = hash_api_key(tkey)
                existing_key = (
                    await session.execute(
                        select(APIKey).where(APIKey.key_hash == kh)
                    )
                ).scalars().first()
                if not existing_key:
                    key = APIKey(
                        id=f"key_{tid}_root",
                        tenant_id=tid,
                        key_hash=kh,
                        key_prefix=tkey[:12],
                        name="test_key",
                        rate_limit=1000,
                    )
                    session.add(key)
        await session.commit()

        yield session
        await session.rollback()
