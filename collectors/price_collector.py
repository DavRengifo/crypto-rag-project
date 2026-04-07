import os
import time
import redis
import requests
import pandas as pd
from datetime import datetime, UTC
from dotenv import load_dotenv

load_dotenv()

# List of CoinGecko token IDs to track
TRACKED_TOKENS = [
    "bitcoin", "ethereum", "solana", "binancecoin",
    "ripple", "cardano", "dogecoin", "polkadot"
]

class PriceCollector:
    """
    Collects cryptocurrency price data with automatic fallback.
    Primary source  : CoinGecko API (free, stable, complete)
    Fallback source : CoinMarketCap scraping (used only if API fails)
    """
    
    def __init__(self):
        """
        Initialize PriceCollector with Redis client and CoinGecko base URL.

        Args:
            None
        """
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        self.session = requests.Session()
        
        # Add CoinGecko API key to headers if available (Demo plan)
        coingecko_key = os.getenv("COINGECKO_API_KEY")
        if coingecko_key:
            self.session.headers.update({
                "x-cg-demo-api-key": coingecko_key
            })

    def fetch_from_coingecko(self, token_ids=None): 
        """
        Fetch price data from CoinGecko API for a list of tokens.

        Args:
            token_ids : list of CoinGecko token IDs (e.g. ['bitcoin', 'ethereum'])

        Returns:
            pd.DataFrame : price data with columns
                           Name, Symbol, Price, MarketCap, Volume24h, Change24h, Date
        """
        if token_ids is None:
            token_ids = TRACKED_TOKENS
            
        url = f"{self.coingecko_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ",".join(token_ids),
            "order": "market_cap_desc",
            "per_page": 250,
            "sparkline": False
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()  # raises exception if status != 200
        coins = response.json()

        data = []
        current_datetime = datetime.now(UTC)

        for coin in coins:
            data.append({
                'Name'      : coin['name'],
                'Symbol'    : coin['symbol'].upper(),
                'Price'     : coin['current_price'],
                'MarketCap' : coin['market_cap'],
                'Volume24h' : coin['total_volume'],
                'Change24h' : coin['price_change_percentage_24h'],
                'Date'      : current_datetime
            })

        return pd.DataFrame(data)

    def fetch_from_scraper(self): 
        """
        Fallback : fetch price data from CoinMarketCap scraping service.
        Calls the internal scraper microservice via HTTP.
        Called only if CoinGecko API is unavailable.

        Args:
            None

        Returns:
            pd.DataFrame : price data from CoinMarketCap scraper
        """
        scraper_url = os.getenv("SCRAPER_SERVICE_URL", "http://scraper:8001/scrape")
        response = requests.get(scraper_url, timeout=60)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data)

    def fetch_price_data(self):
        """
        Main fetch method with automatic fallback strategy.
        Tries CoinGecko first, falls back to scraping if API fails.

        Args:
            None

        Returns:
            pd.DataFrame : price data from best available source
        """
        try:
            data = self.fetch_from_coingecko()
            if not data.empty:
                print('Prices fetched successfully from CoinGecko API.')
                return data
        except Exception as e:
            print(f"CoinGecko failed: {e}, switching to scraper...")

        print('Fetching prices from CoinMarketCap scraper...')
        scraper_data = self.fetch_from_scraper()
        if not scraper_data.empty:
            print('Prices fetched successfully from CoinMarketCap scraper.')
            return scraper_data

        print('Both data sources failed.')
        return pd.DataFrame()

    def send_to_redis(self, data):
        """
        Serialize DataFrame to JSON and push it to the Redis queue.

        Args:
            data : pd.DataFrame containing price data to send

        Returns:
            None
        """
        if data.empty:
            print("No data to send to Redis.")
            return
        
        payload = data.to_json(orient="records")
        self.redis_client.rpush("prices_queue", payload)
        print(f"Sent {len(data)} rows to Redis queue.")

def main():
    """
    Main collector loop.
    Fetches prices every 5 minutes and sends them to Redis.

    Args:
        None
    """
    collector = PriceCollector()

    print("Starting PriceCollector...")
    
    while True:
        price_data = collector.fetch_price_data()
        collector.send_to_redis(price_data)
        time.sleep(300)  # Wait for 5 minutes before next fetch
            
if __name__ == "__main__":
    main()