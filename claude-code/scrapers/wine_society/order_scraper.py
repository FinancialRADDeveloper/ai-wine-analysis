"""
Selenium-based scraper for Wine Society order history and details.
"""

import os
import time
import base64
import logging
from dataclasses import dataclass, asdict
from typing import Optional, List, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from glob import glob

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("wine_soc_scraper")


@dataclass
class OrderDetail:
    order_number: Optional[str]
    order_date: Optional[str]
    order_total: Optional[str]
    url: str
    pdf_path: Optional[str]
    receipts: List[str]
    wine_notes: List[str]
    wine_links: List[str]
    download_dir: str = "Data"

    def to_dict(self) -> dict:
        return asdict(self)


class WineSocietyOrderScraperSelenium:
    def __init__(self, username: str, password: str, start_url: str) -> None:
        self.username = username
        self.password = password
        self.start_url = start_url
        self.download_dir = OrderDetail.download_dir
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": os.path.abspath(self.download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,
            },
        )
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

    def login(self) -> None:
        """
        Log in to the Wine Society website using Selenium, then navigate to the order
        history page.
        """
        self.driver.get(self.start_url)
        # Wait for login form
        self.wait.until(
            EC.presence_of_element_located((By.NAME, "SubmissionModel.Username"))
        )
        email_input = self.driver.find_element(By.NAME, "SubmissionModel.Username")
        password_input = self.driver.find_element(By.NAME, "SubmissionModel.Password")
        email_input.clear()
        email_input.send_keys(self.username)
        password_input.clear()
        password_input.send_keys(self.password)
        password_input.send_keys(Keys.RETURN)
        # After login, navigate directly to the order history page
        order_history_url = (
            "https://www.thewinesociety.com/my-account/order-history/?page=1&months=19"
            "&epmonths=6&isEnPrimeur=False"
        )
        self.driver.get(order_history_url)
        # Try to click the "Accept All Cookies" button if it exists
        try:
            accept_cookies_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            accept_cookies_btn.click()
            log.info("Accepted cookies.")
        except Exception:
            log.warning("No 'Accept All Cookies' button found or could not click it.")
        # Wait for the order history page to load (look for 'View' buttons)
        self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//a[normalize-space(text())='View'] | "
                    "//button[normalize-space(text())='View']",
                )
            )
        )

    def get_order_view_buttons(self) -> list[Any]:
        """
        Find all 'View' buttons on the order history page.
        Returns a list of WebElement objects.
        """
        return self.driver.find_elements(
            By.XPATH, "//a[normalize-space(text())='View' and contains(@class, 'btn')]"
        )

    def save_order_page_as_pdf(self, output_path: str) -> None:
        """
        Save the current order detail page as a PDF using Chrome's print-to-PDF feature.
        Requires Chrome to be started with --headless=new and --disable-gpu for PDF output.
        """
        try:
            pdf = self.driver.execute_cdp_cmd(
                "Page.printToPDF", {"printBackground": True}
            )
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(pdf["data"]))
            log.info(f"Saved PDF to {output_path}")
        except Exception as e:
            log.error(f"Error saving PDF: {e}")

    def extract_order_num_from_receipt_url(self, receipt_url: str) -> str:

        # example receipt_url
        # https://www.thewinesociety.com/CustomFileDownload/DownloadInvoice?orderNumber=TWSWEB-13480088

        # we want the order_num as the numeric part of the last part of the URL
        # i.e. orderNumber=TWSWEB-13480088 -> 13480088

        match = re.search(r"orderNumber=TWSWEB-(\d+)", receipt_url)
        order_num = match.group(1) if match else ""

        if order_num == "":
            log.error(
                f"Unable to scrape order number from the following URL: {receipt_url}"
            )

        return order_num

    def download_receipt_pdf(self, receipt_url: str, sleep_time: int = 5) -> None:
        """
        Download the receipt PDF from the given URL and save it to Data/receipts.
        The filename will be based on the order number in the URL.
        """
        try:
            self.driver.get(receipt_url)

            log.info(
                "Waiting for download to initiate and complete... (this might take a few seconds)"
            )
            time.sleep(sleep_time)

            # Assume download_dir is set elsewhere in the class or as a constant
            download_dir = getattr(self, "download_dir", "Data/downloads")
            receipts_dir = os.path.join("Data", "receipts")
            os.makedirs(receipts_dir, exist_ok=True)

            # Extract the filename from the URL
            order_number = self.extract_order_num_from_receipt_url(receipt_url)

            # Try to match a file in the download_dir with the format TWSWEB-<order_number>*.pdf
            pattern = os.path.join(download_dir, f"TWSWEB-{order_number}*.pdf")
            matching_files = glob(pattern)
            if matching_files:
                # Use the most recent file (by modification time)
                matching_files.sort(key=os.path.getmtime, reverse=True)
                filename = os.path.basename(matching_files[0])
            else:
                filename = None

            if filename:
                src_path = os.path.join(download_dir, filename)
                # Make a unique name in receipts_dir to avoid clashing with wine notes
                dest_path = os.path.join(receipts_dir, f"receipt_{order_number}.pdf")

                if os.path.exists(src_path):
                    try:
                        os.rename(src_path, dest_path)
                        log.info(f"Moved receipt PDF to {dest_path}")
                    except Exception as e:
                        log.error(f"Error moving receipt PDF: {e}")
                else:
                    log.warning(f"Receipt PDF not found at {src_path}")

        except Exception as e:
            log.error(f"Error downloading receipt: {e}")

    def download_wine_notes_pdf(self, wine_notes_url: str, sleep_time: int = 5) -> None:
        """
        Download the wine notes PDF from the given URL and save it to Data/receipts.
        The filename will be based on the order number in the URL.
        """
        try:
            self.driver.get(wine_notes_url)

            log.info(
                "Waiting for download to initiate and complete... (this might take a few seconds)"
            )
            time.sleep(sleep_time)

            # Assume download_dir is set elsewhere in the class or as a constant
            download_dir = getattr(self, "download_dir", "Data/downloads")
            wine_notes_dir = os.path.join("Data", "wine_notes")
            os.makedirs(wine_notes_dir, exist_ok=True)

            # Extract the filename from the URL
            order_number = self.extract_order_num_from_receipt_url(wine_notes_url)

            # Try to match a file in the download_dir with the format TWSWEB-<order_number>*.pdf
            pattern = os.path.join(download_dir, f"TWSWEB-{order_number}*.pdf")
            matching_files = glob(pattern)
            if matching_files:
                # Use the most recent file (by modification time)
                matching_files.sort(key=os.path.getmtime, reverse=True)
                filename = os.path.basename(matching_files[0])
            else:
                filename = None

            if filename:
                src_path = os.path.join(download_dir, filename)
                dest_path = os.path.join(
                    wine_notes_dir, f"wine_notes_{order_number}.pdf"
                )

                if os.path.exists(src_path):
                    try:
                        os.rename(src_path, dest_path)
                        log.info(f"Moved Wine Notes PDF to {dest_path}")
                    except Exception as e:
                        log.error(f"Error moving Wine Notes PDF: {e}")
                else:
                    log.warning(f"Wine Notes PDF not found at {src_path}")

        except Exception as e:
            log.error(f"Error downloading Wine Notes: {e}")

    def download_wine_notes_from_order_page(self, sleep_time: int = 5) -> Optional[str]:
        """
        Find the 'Download wine notes' button in the toolbar, extract the download URL,
        and trigger the download via Selenium.
        Returns the download URL if found and triggered, else None.
        """
        try:
            toolbar_div = self.driver.find_element(
                By.XPATH,
                "//div[contains(@class, 'order-toolbar__group--pull-right') "
                "and contains(@class, 'order-toolbar__actions')]",
            )
            # Find all button elements within the div
            buttons = toolbar_div.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                onclick = button.get_attribute("onclick")
                if onclick and "DownloadWineNotesPdf" in onclick:
                    # Extract the URL from the onclick attribute
                    match = re.search(
                        r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick
                    )
                    if match:
                        url_part = match.group(1)
                        # If the URL is relative, prepend the base URL
                        if url_part.startswith("/"):
                            base_url = (
                                self.driver.current_url.split("/")[0]
                                + "//"
                                + self.driver.current_url.split("/")[2]
                            )
                            full_url = base_url + url_part
                        else:
                            full_url = url_part
                        log.info(f"Triggering download of wine notes from: {full_url}")
                        self.driver.get(full_url)
                        time.sleep(sleep_time)

                        # log a warning if the receipt links are not found
                        if not full_url:
                            log.warning(
                                "No wine notes  link found on the order detail page."
                            )
                        else:
                            # download the receipt pdfs
                            self.download_wine_notes_pdf(full_url)
            return None
        except Exception as e:
            log.error(f"Error downloading wine notes from toolbar: {e}")
            return None

    def follow_wine_links(self) -> None:
        """
        Find and follow each available wine link on the order detail page.
        Opens each wine link in a new tab and prints the URL (can be extended to scrape details).
        """
        try:
            wine_links = self.driver.find_elements(
                By.XPATH, "//a[contains(@href, '/product/')]"
            )
            for link in wine_links:
                href = link.get_attribute("href")
                if href:
                    self.driver.execute_script(f"window.open('{href}', '_blank');")
                    log.info(f"Opened wine link: {href}")
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(1)
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
        except Exception as e:
            log.error(f"Error following wine links: {e}")

    def extract_order_number_from_element(self, order_number_elem) -> str | None:
        order_number = order_number_elem.text
        log.info(f"Order number text found: {order_number}")
        for prefix in [
            "Order No:",
            "Order number:",
            "Order #:",
            "Order no:",
            "OrderNo:",
            "OrderNumber:",
        ]:
            if order_number.startswith(prefix):
                log.info(f"Stripping off Order No: {prefix} from {order_number}")
                order_number = order_number[len(prefix) :].strip()  # noqa: E203
                break
        return order_number

    def extract_order_date_from_h3(self, order_date_h3) -> str | None:
        try:
            order_date_div = order_date_h3.find_element(By.XPATH, "./parent::div")
            order_date_p = order_date_div.find_element(By.TAG_NAME, "p")
            return order_date_p.text.strip()
        except Exception as e:
            log.error(f"Error extracting order date from h3: {e}")
            return None

    def extract_order_total_from_div(self, order_total_div) -> str | None:
        try:
            order_total_p = order_total_div.find_element(By.TAG_NAME, "p")
            return order_total_p.text.strip()
        except Exception as e:
            log.error(f"Error extracting order total from div: {e}")
            return None

    def download_receipt_pdfs_from_page(self) -> list[str]:
        """
        Find all receipt download buttons on the page, extract their URLs, and trigger downloads.
        Returns a list of the receipt URLs found.
        """
        receipt_links = []
        try:
            # Find the button with the correct class and text for "Download receipt"
            receipt_buttons = self.driver.find_elements(
                By.XPATH,
                (
                    "//div[contains(@class,'order-toolbar__row')]//button[contains(@class,'btn') "
                    "and contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), "
                    "'download receipt')]"
                ),
            )

            for btn in receipt_buttons:
                onclick = btn.get_attribute("onclick")
                if onclick and "location.href=" in onclick:
                    # Extract the URL from the onclick attribute
                    url_part = onclick.split("location.href=")[1].strip().strip("'\";")
                    # If the URL is relative, prepend the base URL
                    if url_part.startswith("/"):
                        base_url = (
                            self.driver.current_url.split("/")[0]
                            + "//"
                            + self.driver.current_url.split("/")[2]
                        )
                        full_url = base_url + url_part
                    else:
                        full_url = url_part
                    receipt_links.append(full_url)

            # log a warning if the receipt links are not found
            if not receipt_links:
                log.warning("No receipt link found on the order detail page.")
            else:
                # download the receipt pdfs
                for link in receipt_links:
                    self.download_receipt_pdf(link)
        except Exception as e:
            log.error(f"Error downloading receipt or notes: {e}")

        return receipt_links

    def handle_order_detail_page(
        self, output_dir: str = r"Data/order_details"
    ) -> Optional[OrderDetail]:
        """
        Extract order number, order date, and order total from the order detail page.
        Save the page as PDF, download receipts and wine notes, and follow wine links.
        Returns an OrderDetail dataclass instance for MongoDB storage.
        """
        # Click the "Accept All Cookies" button if it exists
        try:
            accept_btn = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
            if accept_btn.is_displayed() and accept_btn.is_enabled():
                accept_btn.click()
                time.sleep(1)
        except Exception:
            pass

        try:
            self.wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//*[contains(text(), 'Order No') or contains(text(), 'Order number') "
                        "or contains(text(), 'Order #') or contains(text(), 'Order no') "
                        "or contains(text(), 'OrderNo') or contains(text(), 'OrderNumber')]",
                    )
                )
            )
            # Extract order number
            try:
                order_number_elem = self.driver.find_element(
                    By.XPATH,
                    "//*[contains(text(), 'Order No') or contains(text(), 'Order number') "
                    "or contains(text(), 'Order #') or contains(text(), 'Order no') "
                    "or contains(text(), 'OrderNo') or contains(text(), 'OrderNumber')]",
                )
                order_number = self.extract_order_number_from_element(order_number_elem)
            except Exception:
                order_number = None
                log.error("Order Number could not be found on the order detail page.")

            # Extract order date
            try:
                order_date_h3 = self.driver.find_element(
                    By.XPATH,
                    "//h3[contains(@class, 'order-toolbar__text-column-title') "
                    "and contains(normalize-space(), 'Date placed')]",
                )
                order_date = self.extract_order_date_from_h3(order_date_h3)
            except Exception:
                order_date = None
                log.error("Order Date could not be found on the order detail page.")
            # Extract order total
            try:
                order_total_div = self.driver.find_element(
                    By.XPATH,
                    "//div[contains(@class, 'order-toolbar__text-column')][.//h3[contains(@class, "
                    "'order-toolbar__text-column-title') and contains(normalize-space(), 'Order total')]]",
                )
                order_total = self.extract_order_total_from_div(order_total_div)
            except Exception:
                order_total = None
                log.error("Order Total could not be found on the order detail page.")
            # 1. Save the page as PDF
            pdf_path = os.path.join(
                output_dir, f"{order_number or 'unknown_order'}.pdf"
            )
            self.save_order_page_as_pdf(pdf_path)

            # 2. Download receipt (collect links)
            receipt_links = self.download_receipt_pdfs_from_page()

            # 3. Download wine notes using the new function
            wine_notes_links: List[str] = []
            try:
                wine_notes_url = self.download_wine_notes_from_order_page()
                if wine_notes_url:
                    wine_notes_links.append(wine_notes_url)
            except Exception as e:
                log.error(f"Error downloading wine notes: {e}")

            log.info(f"Order Number: {order_number}")
            log.info(f"Order Date: {order_date}")
            log.info(f"Order Total: {order_total}")
            log.info(f"PDF Path: {pdf_path}")
            log.info(f"Receipts: {receipt_links}")
            log.info(f"Wine Notes: {wine_notes_links}")

            return OrderDetail(
                order_number=order_number,
                order_date=order_date,
                order_total=order_total,
                url=self.driver.current_url,
                pdf_path=pdf_path,
                receipts=receipt_links,
                wine_notes=wine_notes_links,
                wine_links=wine_notes_links,
            )
        except Exception as e:
            log.error(f"Error extracting order details: {e}")
            return None

    def scrape_all_orders(self) -> List[OrderDetail]:
        """
        Main method to scrape all orders using Selenium.
        Opens each order detail page in a new tab, scrapes, closes, and returns to main tab.
        """
        orders: List[OrderDetail] = []
        view_links = self.get_order_view_buttons()
        log.info(f"Found {len(view_links)} orders.")
        # Collect all hrefs first
        hrefs = []
        for link in view_links:
            href = link.get_attribute("href")
            if href:
                hrefs.append(href)
        main_window = self.driver.current_window_handle
        for href in hrefs:
            # Open order detail in a new tab
            self.driver.execute_script(f"window.open('{href}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            order_data = self.handle_order_detail_page()
            if order_data:
                orders.append(order_data)
            self.driver.switch_to.window(main_window)
        return orders

    def close(self) -> None:
        self.driver.quit()


def main() -> None:
    import os
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
    try:
        username = os.getenv("WINE_SOCIETY_EMAIL")
        password = os.getenv("WINE_SOCIETY_PASSWORD")
        if not username or not password:
            raise ValueError(
                "WINE_SOCIETY_EMAIL and/or WINE_SOCIETY_PASSWORD not set in .env file."
            )
    except Exception as e:
        log.error(f"Error loading credentials: {e}")
        raise
    start_url = (
        "https://www.thewinesociety.com/my-account/order-history/?page=1&months=19"
        "&epmonths=6&isEnPrimeur=False"
    )
    scraper = WineSocietyOrderScraperSelenium(username, password, start_url)
    try:
        scraper.login()
        orders = scraper.scrape_all_orders()
        for order in orders:
            log.info(order)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
