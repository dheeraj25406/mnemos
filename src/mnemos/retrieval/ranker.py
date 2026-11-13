from typing import Any

from pydantic import BaseModel, Field


class RankedMemory(BaseModel):
    memory_id: str
    content: str
    final_score: float
    rrf_score: float = 0.0
    vector_score: float = 0.0
    keyword_score: float = 0.0
    graph_proximity: float = 0.0
    temporal_relevance: float = 1.0
    importance: float = 0.5
    confidence: float = 1.0
    explanation: dict[str, Any] = Field(default_factory=dict)


class FusionRanker:
    """
    Combines ranked results using Reciprocal Rank Fusion (RRF)
    and multi-factor contextual re-ranking.
    """

    @classmethod
    def rrf_fuse(
        cls,
        vector_ranked: list[dict[str, Any]],   # [{"memory_id": ..., "content": ..., "rank": 1, "score": ...}]
        keyword_ranked: list[dict[str, Any]],  # [{"memory_id": ..., "content": ..., "rank": 1, "score": ...}]
        graph_ranked: list[dict[str, Any]],    # [{"memory_id": ..., "content": ..., "rank": 1, "hops": 1}]
        k: int = 60,
        w_vec: float = 1.0,
        w_kw: float = 0.8,
        w_graph: float = 0.6,
    ) -> list[RankedMemory]:
        """Performs Reciprocal Rank Fusion across retrieval channels."""
        all_memories: dict[str, dict[str, Any]] = {}

        # 1. Accumulate vector rank
        for item in vector_ranked:
            mid = item["memory_id"]
            all_memories.setdefault(mid, {
                "memory_id": mid,
                "content": item["content"],
                "rrf_score": 0.0,
                "vector_score": item.get("score", 0.0),
                "keyword_score": 0.0,
                "graph_proximity": 0.0,
                "importance": item.get("importance", 0.5),
                "confidence": item.get("confidence", 1.0),
            })
            all_memories[mid]["rrf_score"] += w_vec / (k + item["rank"])

        # 2. Accumulate keyword rank
        for item in keyword_ranked:
            mid = item["memory_id"]
            all_memories.setdefault(mid, {
                "memory_id": mid,
                "content": item["content"],
                "rrf_score": 0.0,
                "vector_score": 0.0,
                "keyword_score": item.get("score", 0.0),
                "graph_proximity": 0.0,
                "importance": item.get("importance", 0.5),
                "confidence": item.get("confidence", 1.0),
            })
            all_memories[mid]["rrf_score"] += w_kw / (k + item["rank"])
            all_memories[mid]["keyword_score"] = item.get("score", 0.0)

        # 3. Accumulate graph rank
        for item in graph_ranked:
            mid = item["memory_id"]
            hops = item.get("hops", 1)
            prox = 1.0 / (1.0 + hops)
            all_memories.setdefault(mid, {
                "memory_id": mid,
                "content": item["content"],
                "rrf_score": 0.0,
                "vector_score": 0.0,
                "keyword_score": 0.0,
                "graph_proximity": prox,
                "importance": item.get("importance", 0.5),
                "confidence": item.get("confidence", 1.0),
            })
            all_memories[mid]["rrf_score"] += w_graph / (k + item["rank"])
            all_memories[mid]["graph_proximity"] = max(all_memories[mid]["graph_proximity"], prox)

        results: list[RankedMemory] = []
        for mid, data in all_memories.items():
            # Final multi-factor formula:
            # final_score = rrf_score * (0.8 + 0.2 * confidence) * (0.8 + 0.2 * importance)
            conf = data.get("confidence", 1.0)
            imp = data.get("importance", 0.5)
            rrf = data["rrf_score"]
            final = rrf * (0.7 + 0.3 * conf) * (0.8 + 0.2 * imp)

            explanation = {
                "rrf_score": round(rrf, 5),
                "vector_score": round(data["vector_score"], 4),
                "keyword_score": round(data["keyword_score"], 4),
                "graph_proximity": round(data["graph_proximity"], 4),
                "confidence": conf,
                "importance": imp,
            }

            results.append(
                RankedMemory(
                    memory_id=mid,
                    content=data["content"],
                    final_score=round(final, 5),
                    rrf_score=round(rrf, 5),
                    vector_score=data["vector_score"],
                    keyword_score=data["keyword_score"],
                    graph_proximity=data["graph_proximity"],
                    importance=imp,
                    confidence=conf,
                    explanation=explanation,
                )
            )

        results.sort(key=lambda x: x.final_score, reverse=True)
        return results
