import json
import os
import time
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
import redis

class CryptoScraper:
    def __init__(self, url):
        load_dotenv()
        self.url = url
        self.scraping_count = 0
        self.symbols = set()
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        print(os.getenv("HEADLESS_BOOL"))
        if os.getenv("HEADLESS_BOOL") == "True":
            options.add_argument('--headless')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()

    def load_page(self):
        self.driver.get(self.url)
        self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
        self.driver.execute_script("document.body.style.zoom='25%'")
        time.sleep(1)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cmc-table"))
        )

    def smooth_scroll(self):
        for _ in range(5):
            self.driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(0.2)
        for _ in range(5):
            self.driver.execute_script("window.scrollBy(0, -400);")
            time.sleep(0.2)

    def extract_crypto_data(self):
        """
        Extract cryptocurrency data from the CoinMarketCap table.

        Returns:
            pd.DataFrame : scraped data with columns
                        Name, Symbol, Price, MarketCap, Volume24h, Change24h, Date
        """
        self.smooth_scroll()
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
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
                    self.symbols.add((symbol, name))

        self.scraping_count += 1
        return pd.DataFrame(data)

    def fetch_historical_data(self):
        API_KEY = os.getenv("CRYPTO_TOKEN")
        BASE_URL = 'https://min-api.cryptocompare.com/data/'
        headers = {
            'authorization': f'Apikey {API_KEY}',
        }

        historical_data = []
        for symbol, name in self.symbols:
            print(f"Fetching historical data for {name} ({symbol})")
            endpoint = 'v2/histohour'
            params = {
                'fsym': symbol,
                'tsym': 'USD',
                'limit': 24 * 60,
            }
            url = f"{BASE_URL}{endpoint}"
            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            if 'Data' in data and 'Data' in data['Data']:
                df = pd.DataFrame(data['Data']['Data'])
                df['Date'] = pd.to_datetime(df['time'], unit='s')
                df['Name'] = name
                df['Symbol'] = symbol
                df['Price'] = df['close']  # Use 'close' column as price
                df['MarketCap'] = None
                df['Volume24h'] = None
                df['Change24h'] = None
                historical_data.append(df[['Name', 'Symbol', 'Price', 'MarketCap', 'Volume24h', 'Change24h', 'Date']])

        return pd.concat(historical_data, ignore_index=True) if historical_data else pd.DataFrame()

    def combine_and_save_data(self, new_scrape_data, historical_data):
        # Vérifie si le dossier 'data' existe, sinon le crée
        if not os.path.exists("scrapping/data"):
            os.makedirs("scrapping/data")

        combined_data = pd.concat([new_scrape_data, historical_data], ignore_index=True)
        dataframe_json = combined_data.to_json(orient="records")
        self.redis_client.rpush("crypto_data_queue", dataframe_json)
        # Charger les données existantes si le fichier combiné existe déjà
        if os.path.exists("scrapping/data/combined_data.parquet"):
            existing_data = pd.read_parquet("scrapping/data/combined_data.parquet")
            combined_data = pd.concat([existing_data, combined_data], ignore_index=True)

        # Sauvegarder en .parquet et .csv avec les colonnes spécifiées
        combined_data.to_parquet("scrapping/data/combined_data.parquet", index=False)
        combined_data.to_csv("scrapping/data/combined_data.csv", index=False)
        print("Data saved and updated in combined_data.parquet and combined_data.csv")

    def close(self):
        self.driver.quit()

# Utilisation
scraper = CryptoScraper("https://coinmarketcap.com/")
scraper.load_page()

try:
    while True:
        # Extraire les nouvelles données de scraping
        new_scrape_data = scraper.extract_crypto_data()

        # Enregistrer les données dans le fichier combiné
        if scraper.scraping_count == 5:
            historical_data = scraper.fetch_historical_data()
            scraper.combine_and_save_data(new_scrape_data, historical_data)
        elif scraper.scraping_count > 5: 
            # Incrémentation du fichier combiné avec seulement le scraping en attendant l'historique
            scraper.combine_and_save_data(new_scrape_data, pd.DataFrame())
        else:
            pass
        time.sleep(5)

except KeyboardInterrupt:
    print("Stopping the scraper.")
finally:
    scraper.close()
