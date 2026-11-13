from datetime import datetime
from typing import Any

import httpx

from mnemos.client.models import SearchResult, TimelineDiff


class Mnemos:
    """Official Synchronous Python SDK for Mnemos Temporal Memory Infrastructure."""

    def __init__(
        self,
        base_url: str = "http://localhost:8088",
        api_key: str = "mnk_test_secret_key_12345",
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-Mnemos-API-Key": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def add(
        self,
        content: str,
        user_id: str | None = None,
        memory_type: str = "observation",
        valid_from: datetime | str | None = None,
        valid_to: datetime | str | None = None,
        confidence: float = 1.0,
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ingest memory with entity resolution and bitemporal coordinates."""
        meta = metadata.copy() if metadata else {}
        if user_id:
            meta["user_id"] = user_id

        vf_str = valid_from.isoformat() if isinstance(valid_from, datetime) else valid_from
        vt_str = valid_to.isoformat() if isinstance(valid_to, datetime) else valid_to

        payload = {
            "content": content,
            "memory_type": memory_type,
            "source": user_id or "sdk-agent",
            "confidence": confidence,
            "importance": importance,
            "valid_from": vf_str,
            "valid_to": vt_str,
            "metadata": meta,
        }

        resp = self._client.post("/v1/memories", json=payload)
        resp.raise_for_status()
        return resp.json()

    def search(
        self,
        query: str,
        user_id: str | None = None,
        top_k: int = 10,
        valid_at: datetime | str | None = None,
        recorded_at: datetime | str | None = None,
        enable_vector: bool = True,
        enable_keyword: bool = True,
        enable_graph: bool = True,
    ) -> SearchResult:
        """Execute hybrid search combining vector, lexical, graph, and temporal constraints."""
        va_str = valid_at.isoformat() if isinstance(valid_at, datetime) else valid_at
        ra_str = recorded_at.isoformat() if isinstance(recorded_at, datetime) else recorded_at

        payload = {
            "query": query,
            "top_k": top_k,
            "valid_at": va_str,
            "recorded_at": ra_str,
            "enable_vector": enable_vector,
            "enable_keyword": enable_keyword,
            "enable_graph": enable_graph,
        }

        resp = self._client.post("/v1/memories/search", json=payload)
        resp.raise_for_status()
        return SearchResult(**resp.json())

    def get_history(self, entity: str) -> list[dict[str, Any]]:
        """Retrieve historical memories and facts associated with an entity."""
        resp = self._client.get("/v1/memories", params={"limit": 50})
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [it for it in items if entity.lower() in it["content"].lower()]

    def compare_timeline(
        self,
        subject: str,
        t1: datetime | str,
        t2: datetime | str,
    ) -> TimelineDiff:
        """Compare what changed for a subject between date t1 and date t2."""
        t1_str = t1.isoformat() if isinstance(t1, datetime) else t1
        t2_str = t2.isoformat() if isinstance(t2, datetime) else t2

        resp = self._client.get(
            "/v1/temporal/timeline-diff",
            params={"subject": subject, "t1": t1_str, "t2": t2_str},
        )
        resp.raise_for_status()
        return TimelineDiff(**resp.json())

    def traverse_graph(
        self,
        seed_entity_id: str,
        max_depth: int = 2,
        valid_at: datetime | str | None = None,
    ) -> dict[str, Any]:
        """Traverse knowledge graph around a seed entity."""
        va_str = valid_at.isoformat() if isinstance(valid_at, datetime) else valid_at
        resp = self._client.get(
            "/v1/graph/subgraph",
            params={"seed_entity_id": seed_entity_id, "max_depth": max_depth, "valid_at": va_str},
        )
        resp.raise_for_status()
        return resp.json()

    def delete(self, memory_id: str) -> bool:
        """Cascade purge memory."""
        resp = self._client.delete(f"/v1/memories/{memory_id}")
        return resp.status_code == 200

    def close(self) -> None:
        """Close HTTP connection pool."""
        self._client.close()
