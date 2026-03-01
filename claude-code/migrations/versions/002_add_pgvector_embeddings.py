"""Add pgvector embedding column and HNSW index for semantic search.

Revision ID: 002
Create Date: 2025-02-27
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add embedding column (1536 dimensions = text-embedding-3-small)
    op.execute(
        "ALTER TABLE wines ADD COLUMN embedding vector(1536)"
    )

    # HNSW index for approximate nearest neighbour search
    # m=16 and ef_construction=64 are good defaults for ~100K records
    op.execute(
        "CREATE INDEX ix_wines_embedding_hnsw ON wines "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_wines_embedding_hnsw")
    op.execute("ALTER TABLE wines DROP COLUMN IF EXISTS embedding")
