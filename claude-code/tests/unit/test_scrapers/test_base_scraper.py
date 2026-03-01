"""Tests for the considerate scraping base class."""

from unittest.mock import patch, MagicMock
from scrapers.common.base_scraper import BaseScraper, ScrapeConfig, ScrapeResult
from typing import Any


class ConcreteScraper(BaseScraper):
    """Minimal concrete implementation for testing."""

    @property
    def provider_name(self) -> str:
        return "test-provider"

    @property
    def base_url(self) -> str:
        return "https://example.com"

    def scrape_catalog(self, **kwargs: Any) -> ScrapeResult:
        return ScrapeResult(provider=self.provider_name, url=self.base_url)


class TestScrapeConfig:
    def test_default_config(self) -> None:
        config = ScrapeConfig()
        assert config.min_delay_seconds == 2.0
        assert config.max_delay_seconds == 5.0
        assert config.max_retries == 3
        assert config.respect_robots_txt is True

    def test_custom_config(self) -> None:
        config = ScrapeConfig(min_delay_seconds=1.0, max_retries=5)
        assert config.min_delay_seconds == 1.0
        assert config.max_retries == 5


class TestBaseScraper:
    def test_instantiation(self) -> None:
        scraper = ConcreteScraper()
        assert scraper.provider_name == "test-provider"
        assert scraper.base_url == "https://example.com"

    def test_url_resolution(self) -> None:
        scraper = ConcreteScraper()
        assert scraper._resolve_url("/wines") == "https://example.com/wines"
        assert (
            scraper._resolve_url("/wines?page=2")
            == "https://example.com/wines?page=2"
        )

    def test_scrape_result_defaults(self) -> None:
        result = ScrapeResult(provider="test", url="https://example.com")
        assert result.records_found == 0
        assert result.records_failed == 0
        assert result.raw_data == []
        assert result.errors == []

    @patch("scrapers.common.base_scraper.time.sleep")
    def test_rate_limiting_calls_sleep(self, mock_sleep: MagicMock) -> None:
        config = ScrapeConfig(min_delay_seconds=1.0, max_delay_seconds=1.0)
        scraper = ConcreteScraper(config=config)
        scraper._request_count = 1  # simulate a prior request
        scraper._rate_limit()
        mock_sleep.assert_called_once()
        # With min==max==1.0, sleep should be called with 1.0
        args = mock_sleep.call_args[0]
        assert 0.99 <= args[0] <= 1.01

    def test_close(self) -> None:
        scraper = ConcreteScraper()
        scraper.close()  # should not raise
