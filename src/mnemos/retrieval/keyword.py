import re
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.temporal.intervals import ensure_utc


class KeywordRetrievalResult(BaseModel):
    memory_id: str
    content: str
    bm25_score: float
    rank: int
    confidence: float = 1.0
    importance: float = 0.5


class KeywordRetriever:
    """Performs full-text lexical search using PostgreSQL FTS and ts_rank_cd."""

    @classmethod
    async def retrieve(
        cls,
        session: AsyncSession,
        tenant_id: str,
        query: str,
        top_k: int = 10,
        valid_at: datetime | None = None,
        recorded_at: datetime | None = None,
    ) -> list[KeywordRetrievalResult]:
        clean_q = query.strip()
        if not clean_q:
            return []

        tokens = [t for t in re.findall(r"[a-zA-Z0-9]+", clean_q) if len(t) > 1]
        stop = {
            "what", "which", "who", "where", "when", "how", "why", "does", "did",
            "the", "and", "for", "with", "from", "that", "this", "was", "were",
            "are", "is", "a", "an", "in", "to", "of", "on", "at", "by", "as"
        }
        filtered = [t for t in tokens if t.lower() not in stop]
        terms = filtered if filtered else tokens
        or_terms = " | ".join(terms[:16]) if terms else ""

        now = datetime.now(timezone.utc)
        vt_cond = ""
        tt_cond = ""
        params: dict = {
            "tenant_id": tenant_id,
            "query": clean_q,
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

        if or_terms:
            params["or_terms"] = or_terms
            match_cond = """
            AND (
                to_tsvector('english', m.normalized_content) @@ to_tsquery('english', :or_terms)
                OR to_tsvector('english', m.normalized_content) @@ websearch_to_tsquery('english', :query)
            )
            """
            rank_expr = """
            (
                ts_rank_cd(to_tsvector('english', m.normalized_content), to_tsquery('english', :or_terms))
                + CASE WHEN to_tsvector('english', m.normalized_content) @@ websearch_to_tsquery('english', :query) THEN 1.0 ELSE 0.0 END
            )
            """
        else:
            match_cond = "AND to_tsvector('english', m.normalized_content) @@ websearch_to_tsquery('english', :query)"
            rank_expr = "ts_rank_cd(to_tsvector('english', m.normalized_content), websearch_to_tsquery('english', :query))"

        sql = f"""
        SELECT 
            m.id AS memory_id,
            m.normalized_content AS content,
            m.confidence AS confidence,
            m.importance AS importance,
            {rank_expr} AS score
        FROM memories m
        WHERE m.tenant_id = :tenant_id
          AND m.is_active = true
          {match_cond}
          {vt_cond}
          {tt_cond}
        ORDER BY score DESC
        LIMIT :top_k;
        """

        result = await session.execute(text(sql), params)
        rows = result.mappings().all()

        results = []
        for idx, row in enumerate(rows):
            results.append(
                KeywordRetrievalResult(
                    memory_id=row["memory_id"],
                    content=row["content"],
                    bm25_score=float(row["score"]),
                    rank=idx + 1,
                    confidence=float(row.get("confidence") or 1.0),
                    importance=float(row.get("importance") or 0.5),
                )
            )
        return results
