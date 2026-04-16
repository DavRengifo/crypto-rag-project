import os
import time
from playwright.sync_api import sync_playwright
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, UTC
from dotenv import load_dotenv


class CryptoScraper:
    """
    Playwright-based scraper for CoinMarketCap price data.
    Used as a fallback data source when the CoinGecko API is unavailable.

    Args:
        url : str — URL of the CoinMarketCap page to scrape.
    """
    def __init__(self, url):
        """
        Initialize CryptoScraper with Playwright instead of Selenium.
        Playwright manages its own browser binaries — no system Chrome needed.

        Args:
            url (str): The URL of the page to scrape.

        Returns:
            None
        """
        load_dotenv()
        
        self.url = url
        self.scraping_count = 0
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = self.browser.new_page()

    def load_page(self):
        """
        Load page and wait for the cryptocurrency table to be present.

        Returns:
            None
        """
        self.page.goto(self.url)
        self.page.wait_for_selector(".cmc-table", timeout=10000)
        time.sleep(1)

    def smooth_scroll(self):
        """
        Smoothly scroll the page to load all cryptocurrency data.

        Returns:
            None
        """
        for _ in range(5):
            self.page.evaluate("window.scrollBy(0, 400);")
            time.sleep(0.2)
            
        for _ in range(5):
            self.page.evaluate("window.scrollBy(0, -400);")
            time.sleep(0.2)

    def extract_crypto_data(self):
        """
        Extract cryptocurrency data from the CoinMarketCap table.

        Returns:
            pd.DataFrame : scraped data with columns
                        Name, Symbol, Price, MarketCap, Volume24h, Change24h, Date
        """
        self.smooth_scroll()
        soup = BeautifulSoup(self.page.content(), 'html.parser')
        
        crypto_div = soup.find('div', class_='sc-7e3c705d-2')        
        if not crypto_div:
            raise ValueError("Crypto table div not found.")

        table = crypto_div.find('table', class_='sc-7e3c705d-3')
        if not table:
            raise ValueError("Crypto table not found.")

        crypto_tbody = table.find('tbody')
        if not crypto_tbody:
            raise ValueError("Crypto data tbody not found.")

        data = []
        rows = crypto_tbody.find_all('tr')
        current_datetime = datetime.now(UTC)

        for row in rows:
            cols = row.find_all('td')
            
            # Ensure enough columns exist to read all fields
            if len(cols) >= 9:
                
                # Name and symbol
                name_element = cols[2].find('div', class_='sc-65e7f566-0')
                symbol_element = cols[2].find('p', class_='coin-item-symbol')
                symbol = symbol_element.text.strip() if symbol_element else ""
                name = name_element.find('p', class_='sc-65e7f566-0').text.strip() if name_element else ""
                
                # Price
                price_element = cols[3].find('div', class_='sc-b3fc6b7-0 dzgUIj')
                price = float(price_element.text.strip().replace('$', '').replace(',', '')) if price_element else 0
                
                # Market cap - None if absent (optional column)
                market_cap_element = cols[7].find('span', class_='sc-11478e5d-0 chpohi')
                market_cap = float(market_cap_element.text.strip().replace('$', '').replace(',', '')) if market_cap_element else None
                
                # Volume 24h - None if absent (optional column)
                volume_anchor = cols[8].find('a')
                volume_element = volume_anchor.find('p') if volume_anchor else None
                volume_24h = float(volume_element.text.strip().replace('$', '').replace(',', '')) if volume_element else None
                
                # Change 24h - None if absent (optional column)
                change_24h_element = cols[5].find('span')
                change_24h = None   
                
                if change_24h_element:
                    # Find child span that contains the icon and determine the sign
                    icon = change_24h_element.find('span')
                    sign = 1 if (icon and 'icon-Caret-up' in icon.get('class', [])) else -1
                    # Extract the percentage value and apply the sign
                    raw_text = change_24h_element.get_text(strip=True)
                    try:
                        change_24h = sign * float(raw_text.replace('%', '').replace(',', ''))
                    except ValueError:
                        change_24h = None
                
                if price > 0:
                    data.append({'Name': name,
                                 'Symbol': symbol,
                                 'Price': price,
                                 'MarketCap': market_cap,
                                 'Volume24h': volume_24h,
                                 'Change24h': change_24h,
                                 'Date': current_datetime
                                 })

        self.scraping_count += 1
        return pd.DataFrame(data)

    def close(self):
        """
        Close the browser and stop Playwright.

        Returns:
            None
        """
        self.page.close()
        self.browser.close()
        self.playwright.stop()