from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.temporal.intervals import ensure_utc


class VectorRetrievalResult(BaseModel):
    memory_id: str
    content: str
    similarity: float
    rank: int
    confidence: float = 1.0
    importance: float = 0.5


class VectorRetriever:
    """Performs dense vector similarity search over pgvector embeddings."""

    @classmethod
    async def retrieve(
        cls,
        session: AsyncSession,
        tenant_id: str,
        query_vector: list[float],
        top_k: int = 10,
        valid_at: datetime | None = None,
        recorded_at: datetime | None = None,
    ) -> list[VectorRetrievalResult]:
        now = datetime.now(timezone.utc)
        vt_cond = ""
        tt_cond = ""
        params: dict = {
            "tenant_id": tenant_id,
            "qvec": str(query_vector),
            "top_k": top_k,
            "now": now,
        }

        if valid_at is not None:
            params["vt"] = ensure_utc(valid_at)
            vt_cond = "AND m.valid_from <= :vt AND m.valid_to > :vt"

        if recorded_at is not None:
            params["tt"] = ensure_utc(recorded_at)
            tt_cond = "AND m.recorded_from <= :tt AND m.recorded_to > :tt"
        else:
            tt_cond = "AND m.recorded_from <= :now AND m.recorded_to > :now"

        sql = f"""
        SELECT 
            m.id AS memory_id,
            m.normalized_content AS content,
            m.confidence AS confidence,
            m.importance AS importance,
            1 - (e.embedding <=> CAST(:qvec AS vector)) AS similarity
        FROM memory_embeddings e
        JOIN memories m ON m.id = e.memory_id
        WHERE e.tenant_id = :tenant_id
          AND m.is_active = true
          {vt_cond}
          {tt_cond}
        ORDER BY e.embedding <=> CAST(:qvec AS vector) ASC
        LIMIT :top_k;
        """

        result = await session.execute(text(sql), params)
        rows = result.mappings().all()

        results = []
        for idx, row in enumerate(rows):
            sim = float(row["similarity"])
            results.append(
                VectorRetrievalResult(
                    memory_id=row["memory_id"],
                    content=row["content"],
                    similarity=max(0.0, sim),
                    rank=idx + 1,
                    confidence=float(row.get("confidence") or 1.0),
                    importance=float(row.get("importance") or 0.5),
                )
            )
        return results
