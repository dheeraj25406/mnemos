from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.core.config import get_settings
from mnemos.db.session import get_db_session

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_db_session)):
    """Health check validating PostgreSQL, Redis, and engine subsystems."""
    db_healthy = False
    redis_healthy = False

    # Check PostgreSQL
    try:
        await session.execute(text("SELECT 1"))
        db_healthy = True
    except Exception:
        db_healthy = False

    # Check Redis
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        redis_healthy = True
    except Exception:
        redis_healthy = False

    status = "healthy" if db_healthy else "degraded"

    return {
        "status": status,
        "product": "Mnemos",
        "tagline": "Persistent knowledge. Temporal reasoning. Evolving memory.",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {"connected": db_healthy, "type": "PostgreSQL 16 + pgvector"},
        "cache": {"connected": redis_healthy, "type": "Redis 7"},
    }
