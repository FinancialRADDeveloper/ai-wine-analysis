"""
Data lineage model -- provenance tracking for every record.

Every piece of data carries metadata about where it came from,
when it was ingested, and what code processed it. This enables
full auditability and reproducibility.

Finance analogy:
- This is the "audit trail" that regulators and compliance require
- Answers: "Where did this price come from? When? What processed it?"
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DataLineage(BaseModel):
    """Provenance metadata attached to every ingested record."""

    ingestion_id: UUID = Field(default_factory=uuid4)
    source_file: str = Field(description="S3 URI or local path of the raw file")
    source_file_hash: str = Field(description="SHA-256 hash of the raw file")
    source_row: int = Field(description="Row/record number in the original file")
    provider: str = Field(description="Provider identifier (e.g. 'wine-society')")
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pipeline_version: str = Field(
        default="unknown", description="Git SHA of the processing code"
    )
    adapter_version: str = Field(
        default="1.0", description="Version of the provider adapter used"
    )
