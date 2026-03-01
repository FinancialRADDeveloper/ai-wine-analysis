"""
Base scraper with considerate scraping practices built in.

Demonstrates AI-assisted web scraping that respects:
- robots.txt directives
- Rate limiting with randomised jitter
- Structured logging with correlation IDs
- Retry with exponential backoff
- Clean separation between scraping and data transformation
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

logger = logging.getLogger(__name__)


@dataclass
class ScrapeConfig:
    """Configuration for considerate scraping behaviour."""

    min_delay_seconds: float = 2.0
    max_delay_seconds: float = 5.0
    max_retries: int = 3
    backoff_factor: float = 2.0
    respect_robots_txt: bool = True
    user_agent: str = (
        "SommelierBot/1.0 (+https://github.com/yourusername/ai-wine-analysis; "
        "educational project; respects robots.txt)"
    )
    timeout_seconds: int = 30


@dataclass
class ScrapeResult:
    """Result of a scraping run with full provenance metadata."""

    provider: str
    url: str
    scrape_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    records_found: int = 0
    records_failed: int = 0
    raw_data: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class BaseScraper(ABC):
    """
    Abstract base class for all wine retailer scrapers.

    Provides considerate scraping infrastructure:
    - robots.txt checking
    - Rate limiting with random jitter
    - Request retry with exponential backoff
    - Structured result collection with provenance

    Subclasses implement the provider-specific logic.
    """

    def __init__(self, config: ScrapeConfig | None = None) -> None:
        self.config = config or ScrapeConfig()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.config.user_agent})
        self._robot_parser: RobotFileParser | None = None
        self._request_count = 0

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider (e.g. 'wine-society')."""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL of the retailer website."""
        ...

    @abstractmethod
    def scrape_catalog(self, **kwargs: Any) -> ScrapeResult:
        """
        Scrape the product catalog. Provider-specific implementation.
        Returns a ScrapeResult with raw records.
        """
        ...

    def _check_robots_txt(self, url: str) -> bool:
        """Check if the URL is allowed by robots.txt."""
        if not self.config.respect_robots_txt:
            return True

        if self._robot_parser is None:
            parsed = urlparse(self.base_url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            self._robot_parser = RobotFileParser()
            self._robot_parser.set_url(robots_url)
            try:
                self._robot_parser.read()
                logger.info(
                    "Loaded robots.txt",
                    extra={"provider": self.provider_name, "url": robots_url},
                )
            except Exception as e:
                logger.warning(
                    "Failed to load robots.txt, proceeding with caution",
                    extra={"provider": self.provider_name, "error": str(e)},
                )
                return True

        allowed = self._robot_parser.can_fetch(self.config.user_agent, url)
        if not allowed:
            logger.warning(
                "URL disallowed by robots.txt",
                extra={"provider": self.provider_name, "url": url},
            )
        return allowed

    def _rate_limit(self) -> None:
        """Apply randomised delay between requests (jitter prevents detection)."""
        delay = random.uniform(
            self.config.min_delay_seconds, self.config.max_delay_seconds
        )
        logger.debug(
            "Rate limiting",
            extra={
                "provider": self.provider_name,
                "delay_seconds": round(delay, 2),
                "request_number": self._request_count,
            },
        )
        time.sleep(delay)

    def _fetch(self, url: str, **kwargs: Any) -> requests.Response:
        """
        Fetch a URL with retry, backoff, rate limiting, and robots.txt checking.
        """
        if not self._check_robots_txt(url):
            raise PermissionError(f"URL disallowed by robots.txt: {url}")

        if self._request_count > 0:
            self._rate_limit()

        last_exception: Exception | None = None
        for attempt in range(self.config.max_retries):
            try:
                response = self._session.get(
                    url, timeout=self.config.timeout_seconds, **kwargs
                )
                response.raise_for_status()
                self._request_count += 1
                logger.info(
                    "Fetched URL",
                    extra={
                        "provider": self.provider_name,
                        "url": url,
                        "status": response.status_code,
                        "attempt": attempt + 1,
                    },
                )
                return response
            except requests.RequestException as e:
                last_exception = e
                wait = self.config.backoff_factor ** attempt
                logger.warning(
                    "Request failed, retrying",
                    extra={
                        "provider": self.provider_name,
                        "url": url,
                        "attempt": attempt + 1,
                        "wait_seconds": wait,
                        "error": str(e),
                    },
                )
                time.sleep(wait)

        raise ConnectionError(
            f"Failed to fetch {url} after {self.config.max_retries} attempts: "
            f"{last_exception}"
        )

    def _resolve_url(self, path: str) -> str:
        """Resolve a relative path against the base URL."""
        return urljoin(self.base_url, path)

    def close(self) -> None:
        """Clean up the HTTP session."""
        self._session.close()
        logger.info(
            "Scraper closed",
            extra={
                "provider": self.provider_name,
                "total_requests": self._request_count,
            },
        )
