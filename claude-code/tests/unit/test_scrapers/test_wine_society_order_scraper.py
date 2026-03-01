"""Tests for WineSocietyOrderScraperSelenium and OrderDetail."""

from unittest.mock import patch, MagicMock, PropertyMock
from scrapers.wine_society.order_scraper import (
    WineSocietyOrderScraperSelenium,
    OrderDetail,
)


def test_order_detail_to_dict() -> None:
    od = OrderDetail(
        order_number="12345",
        order_date="2024-06-01",
        order_total="£100.00",
        url="https://example.com",
        pdf_path="/tmp/12345.pdf",
        receipts=["receipt.pdf"],
        wine_notes=["note.pdf"],
        wine_links=["https://example.com/wine1"],
    )
    d = od.to_dict()
    assert d["order_number"] == "12345"
    assert d["order_date"] == "2024-06-01"
    assert d["order_total"] == "£100.00"
    assert d["pdf_path"] == "/tmp/12345.pdf"
    assert d["receipts"] == ["receipt.pdf"]
    assert d["wine_notes"] == ["note.pdf"]
    assert d["wine_links"] == ["https://example.com/wine1"]


@patch("src.wine_soc_order_scraper_selenium.webdriver.Chrome")
def test_scraper_instantiation(mock_chrome: MagicMock) -> None:
    scraper = WineSocietyOrderScraperSelenium("user", "pass", "url")
    assert scraper.username == "user"
    assert scraper.password == "pass"
    assert scraper.start_url == "url"
    scraper.close()


@patch.object(WineSocietyOrderScraperSelenium, "save_order_page_as_pdf")
@patch.object(WineSocietyOrderScraperSelenium, "download_receipt_and_notes")
@patch.object(WineSocietyOrderScraperSelenium, "follow_wine_links")
@patch.object(WineSocietyOrderScraperSelenium, "driver", create=True)
def test_handle_order_detail_page_mocks(
    mock_driver: MagicMock,
    mock_follow: MagicMock,
    mock_download: MagicMock,
    mock_save: MagicMock,
) -> None:
    scraper = WineSocietyOrderScraperSelenium("user", "pass", "url")
    # Patch Selenium find_element and find_elements to return MagicMock with .text and .get_attribute
    fake_elem = MagicMock()
    fake_elem.text = "Order No: 12345"
    fake_elem.find_element.return_value.text = "2024-06-01"
    fake_elem.find_element().text = "2024-06-01"
    type(scraper.driver).find_element = MagicMock(return_value=fake_elem)
    type(scraper.driver).find_elements = MagicMock(return_value=[])
    with patch.object(
        type(scraper.driver), "current_url", new_callable=PropertyMock
    ) as mock_url:
        mock_url.return_value = "https://example.com/order/12345"
        result = scraper.handle_order_detail_page(output_dir="/tmp")
        assert isinstance(result, OrderDetail)
        assert result.order_number == "12345"
    scraper.close()
