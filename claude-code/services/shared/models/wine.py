"""
Canonical Wine schema -- the "Security Master" of the wine domain.

Every wine from every provider gets normalised to this format.
This is the single source of truth for what a bottle of wine IS.

Finance analogy:
- Wine = Security/Instrument
- wine_id = ISIN / CUSIP
- producer = Issuer
- region = Sector / Geography
- grape_varieties = Asset class breakdown
- vintage = Issue date / Tenor
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WineType(str, Enum):
    RED = "red"
    WHITE = "white"
    ROSE = "rose"
    SPARKLING = "sparkling"
    FORTIFIED = "fortified"
    DESSERT = "dessert"
    ORANGE = "orange"


class GrapeVariety(BaseModel):
    """A grape variety and its percentage in the blend."""

    grape: str
    percentage: Optional[Decimal] = Field(
        default=None, ge=0, le=100, decimal_places=1
    )


class FlavorProfile(BaseModel):
    """Normalised flavor profile scores (0-10 scale)."""

    fruit: Optional[int] = Field(default=None, ge=0, le=10)
    oak: Optional[int] = Field(default=None, ge=0, le=10)
    tannin: Optional[int] = Field(default=None, ge=0, le=10)
    acidity: Optional[int] = Field(default=None, ge=0, le=10)
    body: Optional[int] = Field(default=None, ge=0, le=10)
    sweetness: Optional[int] = Field(default=None, ge=0, le=10)


class Wine(BaseModel):
    """
    Canonical wine representation.

    This is the normalised "instrument" that all provider data maps to.
    The wine_id is a deterministic UUID derived from the identifying attributes
    (producer + region + primary grape + vintage), analogous to how an ISIN
    uniquely identifies a security.
    """

    wine_id: UUID = Field(default_factory=uuid4)
    canonical_name: str = Field(max_length=500)
    producer: str = Field(max_length=200)
    region: str = Field(max_length=200)
    sub_region: Optional[str] = Field(default=None, max_length=200)
    country: str = Field(min_length=2, max_length=2, description="ISO 3166-1 alpha-2")
    wine_type: WineType
    grape_varieties: list[GrapeVariety] = Field(default_factory=list)
    vintage: Optional[int] = Field(default=None, ge=1900, le=2030)
    abv: Optional[Decimal] = Field(default=None, ge=0, le=100, decimal_places=1)
    bottle_size_ml: int = Field(default=750)
    closure_type: Optional[str] = Field(default=None, max_length=50)
    organic: Optional[bool] = None

    # Tasting profile
    tasting_notes: Optional[str] = None
    flavor_profile: Optional[FlavorProfile] = None

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_providers: list[str] = Field(
        default_factory=list,
        description="Which providers have contributed data for this wine",
    )
