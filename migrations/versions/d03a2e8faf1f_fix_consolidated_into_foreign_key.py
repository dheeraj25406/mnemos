"""fix_consolidated_into_foreign_key

Revision ID: d03a2e8faf1f
Revises: b3c2bf167a92
Create Date: 2026-11-13 08:58:31.839459

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision: str = 'd03a2e8faf1f'
down_revision: Union[str, None] = 'b3c2bf167a92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(op.f('fk_memories_consolidated_into_id_memories'), 'memories', type_='foreignkey')
    op.create_foreign_key(op.f('fk_memories_consolidated_into_id_memory_consolidations'), 'memories', 'memory_consolidations', ['consolidated_into_id'], ['id'], ondelete='SET NULL')
    # Ensure HNSW and FTS indexes are present
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_memory_embeddings_vector_hnsw "
        "ON memory_embeddings USING hnsw (embedding vector_cosine_ops);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_memories_fts "
        "ON memories USING gin(to_tsvector('english', normalized_content));"
    )


def downgrade() -> None:
    op.drop_constraint(op.f('fk_memories_consolidated_into_id_memory_consolidations'), 'memories', type_='foreignkey')
    op.create_foreign_key(op.f('fk_memories_consolidated_into_id_memories'), 'memories', 'memories', ['consolidated_into_id'], ['id'], ondelete='SET NULL')
