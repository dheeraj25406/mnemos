import os
from typing import Any

from mcp.server.mcpserver import MCPServer

from mnemos.client import AsyncMnemos

mcp_server = MCPServer("mnemos")

_client: AsyncMnemos | None = None


def get_client() -> AsyncMnemos:
    global _client
    if _client is None:
        base_url = os.getenv("MNEMOS_API_URL", "http://localhost:8088")
        api_key = os.getenv("MNEMOS_API_KEY", "mnk_test_secret_key_12345")
        _client = AsyncMnemos(base_url=base_url, api_key=api_key)
    return _client


@mcp_server.tool()
async def add_memory(
    content: str,
    user_id: str | None = None,
    memory_type: str = "observation",
    valid_from: str | None = None,
    importance: float = 0.5,
) -> dict[str, Any]:
    """
    Ingest a new memory item into Mnemos.
    Extracts entities, structured facts, bitemporal coordinates, and vector embeddings.
    """
    client = get_client()
    return await client.add(
        content=content,
        user_id=user_id,
        memory_type=memory_type,
        valid_from=valid_from,
        importance=importance,
    )


@mcp_server.tool()
async def search_memory(
    query: str,
    valid_at: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Search memories using hybrid vector similarity, lexical keyword matching,
    temporal knowledge graph expansion, and bitemporal valid time filtering.
    """
    client = get_client()
    result = await client.search(
        query=query,
        valid_at=valid_at,
        top_k=top_k,
    )
    return result.model_dump()


@mcp_server.tool()
async def query_history(entity: str) -> list[dict[str, Any]]:
    """
    Query the historical facts and memories associated with a given entity name.
    """
    client = get_client()
    return await client.get_history(entity=entity)


@mcp_server.tool()
async def compare_timeline(
    subject: str,
    t1: str,
    t2: str,
) -> dict[str, Any]:
    """
    Compare facts and states for a subject between two dates (t1 and t2)
    to determine exactly what evolved, changed, or remained invariant.
    """
    client = get_client()
    diff = await client.compare_timeline(subject=subject, t1=t1, t2=t2)
    return diff.model_dump()


@mcp_server.tool()
async def traverse_graph(
    seed_entity_id: str,
    max_depth: int = 2,
    valid_at: str | None = None,
) -> dict[str, Any]:
    """
    Traverse the temporal knowledge graph starting at seed_entity_id
    up to max_depth hops, filtering edges by validity at valid_at.
    """
    client = get_client()
    return await client.traverse_graph(
        seed_entity_id=seed_entity_id,
        max_depth=max_depth,
        valid_at=valid_at,
    )


@mcp_server.tool()
async def delete_memory(memory_id: str) -> dict[str, Any]:
    """
    Purge a memory unit with complete cascade deletion of embeddings and derived facts.
    """
    client = get_client()
    success = await client.delete(memory_id=memory_id)
    return {"status": "deleted" if success else "failed", "memory_id": memory_id}


def main():
    mcp_server.run()


if __name__ == "__main__":
    main()
