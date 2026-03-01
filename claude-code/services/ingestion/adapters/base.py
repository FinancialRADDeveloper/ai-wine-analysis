"""
Provider Adapter base class -- the Strategy pattern for data ingestion.

Each wine retailer delivers data in a different format. This abstract base
class defines the contract that every adapter must implement:
  1. detect()    -- Can this adapter handle the given file?
  2. parse()     -- Parse raw bytes into provider-specific records
  3. normalize() -- Transform provider records to canonical Wine/WinePrice

Finance analogy:
- This is how Bloomberg DLIB, Refinitiv Datascope, and ICE feed handlers work
- Each vendor adapter encapsulates parsing and normalisation logic
- Adding a new vendor = one new file, zero changes elsewhere
"""

from abc import ABC, abstractmethod
from typing import Any, Type

from services.shared.models.provider import ProviderRawRecord
from services.shared.models.wine import Wine
from services.shared.models.price import WinePrice


class ProviderAdapter(ABC):
    """Abstract base class for all provider adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider."""
        ...

    @abstractmethod
    def detect(self, filename: str, metadata: dict[str, Any]) -> bool:
        """
        Can this adapter handle the given file?
        Returns True if the filename/metadata matches this provider's format.
        """
        ...

    @abstractmethod
    def parse(self, raw_bytes: bytes) -> list[ProviderRawRecord]:
        """
        Parse raw file bytes into provider-specific records.
        This is the first stage: raw bytes -> structured (but provider-specific) data.
        """
        ...

    @abstractmethod
    def normalize_wine(self, raw: ProviderRawRecord) -> Wine:
        """
        Transform a provider-specific record into the canonical Wine schema.
        This is entity resolution + field mapping.
        """
        ...

    @abstractmethod
    def normalize_price(self, raw: ProviderRawRecord) -> WinePrice | None:
        """
        Extract price information from a provider record.
        Returns None if the record doesn't contain price data.
        """
        ...


# Adapter registry -- populated by each adapter module
ADAPTER_REGISTRY: dict[str, Type[ProviderAdapter]] = {}


def register_adapter(adapter_class: Type[ProviderAdapter]) -> Type[ProviderAdapter]:
    """Decorator to register an adapter in the global registry."""
    instance = adapter_class()
    ADAPTER_REGISTRY[instance.provider_name] = adapter_class
    return adapter_class


def get_adapter_for_file(
    filename: str, metadata: dict[str, Any] | None = None
) -> ProviderAdapter | None:
    """Find the right adapter for a given file by trying each registered adapter."""
    metadata = metadata or {}
    for adapter_class in ADAPTER_REGISTRY.values():
        adapter = adapter_class()
        if adapter.detect(filename, metadata):
            return adapter
    return None
