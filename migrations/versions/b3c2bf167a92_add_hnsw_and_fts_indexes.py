"""add_hnsw_and_fts_indexes

Revision ID: b3c2bf167a92
Revises: 314a296bf5c2
Create Date: 2026-11-13 08:46:57.670399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision: str = 'b3c2bf167a92'
down_revision: Union[str, None] = '314a296bf5c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # HNSW index for high performance approximate nearest neighbor cosine search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_memory_embeddings_vector_hnsw "
        "ON memory_embeddings USING hnsw (embedding vector_cosine_ops);"
    )
    # Full-Text Search GIN index on normalized_content for lexical BM25/tsquery search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_memories_fts "
        "ON memories USING gin(to_tsvector('english', normalized_content));"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_memories_fts;")
    op.execute("DROP INDEX IF EXISTS ix_memory_embeddings_vector_hnsw;")
