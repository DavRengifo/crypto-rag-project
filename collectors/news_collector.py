import os
import time
import redis
import requests
import json
from dotenv import load_dotenv
from bs4 import BeautifulSoup


load_dotenv()

class NewsCollector:
    """
    Collects cryptocurrency news with content extraction.
    Primary source  : CryptoPanic API (discovery)
    Content source  : BeautifulSoup (full article text from URL)
    """

    def __init__(self):
        """
        Initialize NewsCollector with Redis client and API configuration.

        Args:
            None
        """
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )
        self.cryptopanic_url = "https://cryptopanic.com/api/v1/posts/"
        self.api_key = os.getenv("CRYPTOPANIC_API_KEY")
        self.session = requests.Session()

    def fetch_news(self, symbol=None):
        """
        Fetch latest news from CryptoPanic API.

        Args:
            symbol : token symbol to filter news (e.g. 'BTC'), None for all news

        Returns:
            list : list of dicts with keys title, url, source, published_at, symbol
        """
        params = {
            "auth_token": self.api_key,
            "public": "true",
            "kind": "news",
        }
        if symbol:
            params["currencies"] = symbol

        response = self.session.get(self.cryptopanic_url, params=params)
        response.raise_for_status()
        posts = response.json().get("results", [])
        if not posts:
            return []

        news = []
        for post in posts:
            news.append({
                "title"         : post["title"],
                "url"           : post["url"],
                "source"        : post["source"]["title"],
                "published_at"  : post["published_at"],
                "symbol"        : post["currencies"][0]["code"] if post.get("currencies") else None
            })
        return news
    
    def fetch_article_content(self, url):
        """
        Fetch full article content from URL using BeautifulSoup.
        Tries multiple common HTML structures for compatibility
        across different news sources.
        
        Args:
            url : URL of the news article
            
        Returns:
            str : full text content of the article, or None if extraction fails
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Try common article containers in order of reliability
            for selector in [
                soup.find("article"),
                soup.find("div", class_="article-body"),
                soup.find("div", class_="post-content"),
                soup.find("main"),
            ]:
                if selector:
                    return selector.get_text(strip=True)
                
            return None  # Return None if no content found
        except Exception as e:
            print(f"Content extraction failed for {url}: {e}")
            return None
        
    def fetch(self):
        """
        Fetch news and enrich each article with full content.
        
        Args:
            None
        Returns:
            list : list of enriched article dicts
        """
        news = self.fetch_news()
        articles = []
        
        for article in news:
            content = self.fetch_article_content(article["url"])
            articles.append({
                "title"             : article["title"],
                "url"               : article["url"],
                "source"            : article["source"],
                "published_at"      : article["published_at"],
                "symbol"            : article["symbol"],
                "content"           : content
            })
        return articles
    
    def send_to_redis(self, articles):
        """
        Serialize articles list to JSON and push to Redis news queue

        Args:
            articles : list of article dicts to send
        Returns:
            None
        """
        if not articles:
            print("No articles to send to Redis.")
            return

        payload = json.dumps(articles, default=str)  # Serialize with default=str to handle datetime
        self.redis_client.rpush("news_queue", payload)
        print(f"Sent {len(articles)} articles to Redis news queue.")
        
def main():
    """
    Main collector loop.
    Fetches news every 15 minutes and sends them to Redis.
    
    Args:
        None
    """
    collector = NewsCollector()
    print("Starting NewsCollector...")
    
    while True:
        articles = collector.fetch()
        collector.send_to_redis(articles)
        time.sleep(900)  # Wait for 15 minutes before next fetch
        
if __name__ == "__main__":
    main()