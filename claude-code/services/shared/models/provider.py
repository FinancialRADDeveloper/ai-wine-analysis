"""
Provider-specific raw record types.

Each provider delivers data in a different format. These models capture
the raw shape of the data BEFORE normalisation, using Pydantic discriminated
unions so we can validate and route records by provider.

Finance analogy:
- Each class = a vendor-specific feed format (Bloomberg FTP vs Refinitiv CSV)
- The Union type = the feed handler's input type
"""

from datetime import date
from decimal import Decimal
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class WineSocietyRawRecord(BaseModel):
    """Raw record from Wine Society CSV export or scraped data."""

    source: Literal["wine-society"] = "wine-society"
    product_name: str
    product_code: str
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    drink_date: Optional[str] = None
    region_code: Optional[str] = Field(
        default=None, description="2-letter prefix from product code"
    )


class BerryBrosRawRecord(BaseModel):
    """Raw record from Berry Bros & Rudd catalog scrape."""

    source: Literal["bbr"] = "bbr"
    wine_name: str
    price_gbp: Optional[Decimal] = None
    region: Optional[str] = None
    sub_region: Optional[str] = None
    grape_variety: Optional[str] = None
    vintage: Optional[int] = None
    abv: Optional[Decimal] = None
    product_url: Optional[str] = None


class MajesticRawRecord(BaseModel):
    """Raw record from Majestic Wine catalog scrape."""

    source: Literal["majestic"] = "majestic"
    wine_name: str
    price_gbp: Optional[Decimal] = None
    mix_six_price: Optional[Decimal] = Field(
        default=None, description="Majestic's mix-six discount price"
    )
    region: Optional[str] = None
    country: Optional[str] = None
    grape_variety: Optional[str] = None
    vintage: Optional[int] = None
    abv: Optional[Decimal] = None
    tasting_notes: Optional[str] = None
    food_match: Optional[str] = None
    customer_rating: Optional[Decimal] = None
    product_url: Optional[str] = None


# Discriminated union -- Pydantic resolves to the correct type based on "source" field
ProviderRawRecord = Union[
    WineSocietyRawRecord,
    BerryBrosRawRecord,
    MajesticRawRecord,
]
