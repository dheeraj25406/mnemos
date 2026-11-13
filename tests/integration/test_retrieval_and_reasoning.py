from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.evolution.resolver import EvolutionManager
from mnemos.ingestion.pipeline import IngestionPipeline, IngestionItem
from mnemos.ingestion.resolver import EntityResolver
from mnemos.retrieval.hybrid import HybridRetrievalEngine, HybridRetrievalRequest
from mnemos.temporal.reasoning import TemporalReasoningEngine


@pytest.mark.asyncio
async def test_hybrid_retrieval_and_temporal_reasoning(db_session: AsyncSession):
    tenant_id = "tenant_test"

    # Ingest memories with distinct temporal anchors and content
    item1 = IngestionItem(
        content="David Chen founded NeuralFlow in Austin in 2021-03-01",
        memory_type="observation",
        valid_from=datetime(2021, 3, 1, tzinfo=timezone.utc),
    )
    item2 = IngestionItem(
        content="David Chen relocated to San Francisco and works at DeepBrain in 2024-02-15",
        memory_type="observation",
        valid_from=datetime(2024, 2, 15, tzinfo=timezone.utc),
    )
    await IngestionPipeline.ingest(db_session, tenant_id, item1)
    await IngestionPipeline.ingest(db_session, tenant_id, item2)

    # 1. Search for current knowledge about David Chen in 2024
    req_2024 = HybridRetrievalRequest(
        query="Where does David Chen work?",
        valid_at=datetime(2024, 5, 1, tzinfo=timezone.utc),
        top_k=5,
    )
    resp_2024 = await HybridRetrievalEngine.search(db_session, tenant_id, req_2024)
    assert resp_2024.total_found >= 1
    top_content = resp_2024.memories[0].content
    assert "DeepBrain" in top_content or "NeuralFlow" in top_content

    # 2. Timeline comparison for David Chen between 2021 and 2024
    diff = await TemporalReasoningEngine.compare_timeline(
        session=db_session,
        tenant_id=tenant_id,
        subject_name="David Chen",
        t1=datetime(2021, 6, 1, tzinfo=timezone.utc),
        t2=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    assert diff.subject_name == "David Chen"
    assert len(diff.changes) >= 1

    # 3. Knowledge acquisition time
    acq = await TemporalReasoningEngine.get_knowledge_acquisition_time(
        session=db_session,
        tenant_id=tenant_id,
        subject_name="David Chen",
        predicate="created",
    )
    assert acq is not None
    assert acq["subject"] == "David Chen"
    assert "first_recorded_at" in acq
