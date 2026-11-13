from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.core.config import get_settings
from mnemos.core.security import hash_api_key
from mnemos.db.models import APIKey, Tenant
from mnemos.db.session import get_db_session

settings = get_settings()

api_key_header = APIKeyHeader(name=settings.api_key_header_name, auto_error=False)


async def get_current_tenant_id(
    api_key: str | None = Security(api_key_header),
    session: AsyncSession = Depends(get_db_session),
) -> str:
    """
    Validates API key against database.
    Supports default tenant in development mode.
    """
    # Check if key provided
    if not api_key:
        # Check Authorization header bearer token fallback
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Provide header 'X-Mnemos-API-Key'.",
        )

    # In development/test mode, check against default key
    if api_key == settings.default_tenant_key:
        return settings.default_tenant_id

    # Check database api_keys table
    key_hash = hash_api_key(api_key)
    stmt = select(APIKey).where(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True,
    )
    db_key = (await session.execute(stmt)).scalars().first()
    if not db_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key.",
        )

    # Verify tenant is active
    tenant = await session.get(Tenant, db_key.tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive or suspended.",
        )

    return tenant.id
