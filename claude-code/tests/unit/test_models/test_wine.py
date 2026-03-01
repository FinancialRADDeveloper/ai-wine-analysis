"""Tests for the canonical Wine model and related schemas."""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from services.shared.models.wine import (
    Wine,
    WineType,
    GrapeVariety,
    FlavorProfile,
)
from services.shared.models.price import WinePrice, PriceType
from services.shared.models.provider import (
    WineSocietyRawRecord,
    BerryBrosRawRecord,
    MajesticRawRecord,
)
from services.shared.models.lineage import DataLineage


class TestWineModel:
    """Test the canonical Wine schema."""

    def test_create_minimal_wine(self) -> None:
        wine = Wine(
            canonical_name="Chateau Margaux 2015",
            producer="Chateau Margaux",
            region="Bordeaux",
            country="FR",
            wine_type=WineType.RED,
        )
        assert wine.canonical_name == "Chateau Margaux 2015"
        assert wine.country == "FR"
        assert wine.bottle_size_ml == 750  # default

    def test_create_full_wine(self) -> None:
        wine = Wine(
            canonical_name="Penfolds Grange 2018",
            producer="Penfolds",
            region="South Australia",
            sub_region="Barossa Valley",
            country="AU",
            wine_type=WineType.RED,
            grape_varieties=[
                GrapeVariety(grape="Shiraz", percentage=Decimal("96.0")),
                GrapeVariety(grape="Cabernet Sauvignon", percentage=Decimal("4.0")),
            ],
            vintage=2018,
            abv=Decimal("14.5"),
            organic=False,
            flavor_profile=FlavorProfile(
                fruit=9, oak=8, tannin=8, acidity=6, body=9, sweetness=1
            ),
        )
        assert len(wine.grape_varieties) == 2
        assert wine.vintage == 2018
        assert wine.flavor_profile is not None
        assert wine.flavor_profile.fruit == 9

    def test_country_must_be_two_chars(self) -> None:
        with pytest.raises(ValidationError):
            Wine(
                canonical_name="Test",
                producer="Test",
                region="Test",
                country="France",  # should be "FR"
                wine_type=WineType.RED,
            )

    def test_vintage_range_validation(self) -> None:
        with pytest.raises(ValidationError):
            Wine(
                canonical_name="Test",
                producer="Test",
                region="Test",
                country="FR",
                wine_type=WineType.RED,
                vintage=1800,  # too old
            )

    def test_flavor_profile_range(self) -> None:
        with pytest.raises(ValidationError):
            FlavorProfile(fruit=11)  # max is 10


class TestWinePriceModel:
    """Test the bi-temporal price model."""

    def test_create_price(self) -> None:
        from datetime import date

        price = WinePrice(
            wine_id=uuid4(),
            provider_id="wine-society",
            price=Decimal("12.50"),
            currency="GBP",
            price_type=PriceType.RETAIL,
            valid_from=date(2025, 1, 1),
            ingestion_id=uuid4(),
            source_file="s3://sommelier-landing/wine-society/catalog_2025.csv",
            source_file_hash="abc123",
        )
        assert price.price == Decimal("12.50")
        assert price.currency == "GBP"
        assert str(price.valid_to) == "9999-12-31"  # default

    def test_currency_must_be_three_uppercase_chars(self) -> None:
        from datetime import date

        with pytest.raises(ValidationError):
            WinePrice(
                wine_id=uuid4(),
                provider_id="bbr",
                price=Decimal("25.00"),
                currency="gbp",  # lowercase
                valid_from=date(2025, 1, 1),
                ingestion_id=uuid4(),
                source_file="test",
                source_file_hash="test",
            )


class TestProviderRawRecords:
    """Test provider-specific raw record types."""

    def test_wine_society_record(self) -> None:
        record = WineSocietyRawRecord(
            product_name="Exhibition Gruner Veltliner 2023",
            product_code="AA12345",
            region_code="AA",
        )
        assert record.source == "wine-society"
        assert record.region_code == "AA"

    def test_berry_bros_record(self) -> None:
        record = BerryBrosRawRecord(
            wine_name="BBR Claret 2019",
            price_gbp=Decimal("18.50"),
            region="Bordeaux",
            vintage=2019,
        )
        assert record.source == "bbr"

    def test_majestic_record(self) -> None:
        record = MajesticRawRecord(
            wine_name="Definition Malbec 2022",
            price_gbp=Decimal("9.99"),
            mix_six_price=Decimal("7.99"),
            country="AR",
        )
        assert record.source == "majestic"
        assert record.mix_six_price == Decimal("7.99")


class TestDataLineage:
    """Test lineage / provenance model."""

    def test_create_lineage(self) -> None:
        lineage = DataLineage(
            source_file="s3://sommelier-landing/wine-society/2025-01-15.csv",
            source_file_hash="sha256:abcdef1234567890",
            source_row=42,
            provider="wine-society",
            pipeline_version="abc1234",
        )
        assert lineage.provider == "wine-society"
        assert lineage.source_row == 42
        assert lineage.ingestion_id is not None  # auto-generated UUID
