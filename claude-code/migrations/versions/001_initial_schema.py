"""Initial schema: wines, wine_prices (bi-temporal), consumption_history, audit_log.

Revision ID: 001
Create Date: 2025-02-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # =========================================================================
    # wines -- the "Security Master"
    # =========================================================================
    op.create_table(
        "wines",
        sa.Column("wine_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_name", sa.String(500), nullable=False),
        sa.Column("producer", sa.String(200), nullable=False),
        sa.Column("region", sa.String(200), nullable=False),
        sa.Column("sub_region", sa.String(200), nullable=True),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column(
            "wine_type",
            sa.Enum(
                "red",
                "white",
                "rose",
                "sparkling",
                "fortified",
                "dessert",
                "orange",
                name="wine_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("grape_varieties", JSONB, server_default="[]"),
        sa.Column("vintage", sa.Integer, nullable=True),
        sa.Column("abv", sa.Numeric(4, 2), nullable=True),
        sa.Column("bottle_size_ml", sa.Integer, server_default="750"),
        sa.Column("closure_type", sa.String(50), nullable=True),
        sa.Column("organic", sa.Boolean, nullable=True),
        sa.Column("tasting_notes", sa.Text, nullable=True),
        sa.Column("flavor_profile", JSONB, nullable=True),
        sa.Column("source_providers", JSONB, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_wines_producer", "wines", ["producer"])
    op.create_index("ix_wines_region", "wines", ["region"])
    op.create_index("ix_wines_country", "wines", ["country"])
    op.create_index("ix_wines_vintage", "wines", ["vintage"])
    op.create_index("ix_wines_wine_type", "wines", ["wine_type"])

    # =========================================================================
    # wine_prices -- bi-temporal market data
    # =========================================================================
    op.create_table(
        "wine_prices",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "wine_id",
            UUID(as_uuid=True),
            sa.ForeignKey("wines.wine_id"),
            nullable=False,
        ),
        sa.Column("provider_id", sa.String(50), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "price_type",
            sa.Enum(
                "retail",
                "sale",
                "case",
                "en_primeur",
                "auction",
                name="price_type_enum",
            ),
            server_default="retail",
        ),
        sa.Column("case_size", sa.Integer, nullable=True),
        # Business time
        sa.Column("valid_from", sa.Date, nullable=False),
        sa.Column("valid_to", sa.Date, server_default="9999-12-31"),
        # System time
        sa.Column(
            "known_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "known_to",
            sa.DateTime(timezone=True),
            server_default="9999-12-31",
        ),
        # Lineage
        sa.Column("ingestion_id", UUID(as_uuid=True), nullable=False),
        sa.Column("source_file", sa.String(500), nullable=True),
        sa.Column("source_file_hash", sa.String(64), nullable=True),
        sa.Column("source_row", sa.Integer, nullable=True),
        sa.Column("superseded_by", sa.BigInteger, nullable=True),
    )

    op.create_index(
        "ix_wine_prices_lookup",
        "wine_prices",
        ["wine_id", "provider_id", "valid_from"],
    )
    op.create_index(
        "ix_wine_prices_provider", "wine_prices", ["provider_id"]
    )

    # =========================================================================
    # consumption_history -- personal trade/position history
    # =========================================================================
    op.create_table(
        "consumption_history",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "wine_id",
            UUID(as_uuid=True),
            sa.ForeignKey("wines.wine_id"),
            nullable=False,
        ),
        sa.Column("consumed_date", sa.Date, nullable=True),
        sa.Column("quantity", sa.Integer, server_default="1"),
        sa.Column("purchase_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("purchase_source", sa.String(100), nullable=True),
        sa.Column("occasion", sa.String(200), nullable=True),
        sa.Column("personal_rating", sa.Numeric(3, 1), nullable=True),
        sa.Column("personal_notes", sa.Text, nullable=True),
        sa.Column("would_buy_again", sa.Boolean, nullable=True),
        sa.Column("paired_with", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # =========================================================================
    # audit_log -- full provenance for every data change
    # =========================================================================
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("record_id", sa.String(100), nullable=False),
        sa.Column(
            "action",
            sa.Enum("INSERT", "UPDATE", "DELETE", name="audit_action_enum"),
            nullable=False,
        ),
        sa.Column("old_values", JSONB, nullable=True),
        sa.Column("new_values", JSONB, nullable=True),
        sa.Column("changed_by", sa.String(100), server_default="system"),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("ingestion_id", UUID(as_uuid=True), nullable=True),
    )

    op.create_index(
        "ix_audit_log_table_record",
        "audit_log",
        ["table_name", "record_id"],
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("consumption_history")
    op.drop_table("wine_prices")
    op.drop_table("wines")
    op.execute("DROP TYPE IF EXISTS audit_action_enum")
    op.execute("DROP TYPE IF EXISTS price_type_enum")
    op.execute("DROP TYPE IF EXISTS wine_type_enum")
    op.execute("DROP EXTENSION IF EXISTS vector")
