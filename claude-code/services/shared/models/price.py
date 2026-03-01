"""
Bi-temporal wine price model -- the "Market Data" of the wine domain.

Implements bi-temporal modelling so we can answer:
- Business time: "What was the price on March 15?" (valid_from/valid_to)
- System time: "What did we KNOW at 3pm on March 16?" (known_from/known_to)

Finance analogy:
- WinePrice = Market data tick / EOD price
- provider_id = Data vendor (Bloomberg, Refinitiv, ICE)
- Bi-temporal = Standard for front-office data stores (Aladdin, Charles River)
- superseded_by = Price correction chain
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PriceType(str, Enum):
    RETAIL = "retail"
    SALE = "sale"
    CASE = "case"
    EN_PRIMEUR = "en_primeur"
    AUCTION = "auction"


class WinePrice(BaseModel):
    """
    A single price observation with full bi-temporal and lineage metadata.
    """

    wine_id: UUID
    provider_id: str = Field(max_length=50)

    price: Decimal = Field(ge=0, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    price_type: PriceType = PriceType.RETAIL
    case_size: Optional[int] = Field(default=None, description="Bottles per case")

    # Business time: when was this price valid in the real world?
    valid_from: date
    valid_to: date = Field(default=date(9999, 12, 31))

    # System time: when did our system learn about this price?
    known_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    known_to: datetime = Field(default=datetime(9999, 12, 31))

    # Lineage
    ingestion_id: UUID
    source_file: str = Field(description="S3 URI or file path of the raw source")
    source_file_hash: str = Field(description="SHA-256 of the raw file")
    source_row: Optional[int] = Field(
        default=None, description="Row number in the original file"
    )

    # Correction chain
    superseded_by: Optional[int] = Field(
        default=None, description="ID of the price record that replaced this one"
    )
