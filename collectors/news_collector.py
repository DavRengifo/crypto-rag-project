import os
import time
import redis
import requests
import json
import feedparser
from dotenv import load_dotenv
from bs4 import BeautifulSoup


load_dotenv()

# RSS feeds for crypto news — replaces CryptoPanic API (discontinued April 2026)
RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
]

class NewsCollector:
    """
    Collects cryptocurrency news with content extraction.
    Primary source  : RSS feed (CoinDesk, CoinTelegraph, Decrypt)
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
        self.session = requests.Session()

    def fetch_news(self, symbol=None):
        """
        Fetch latest news from RSS feeds.
        Replaces CryptoPanic API (discontinued free plan April 2026).

        Args:
            symbol : token symbol to filter news (e.g. 'BTC'), None for all news

        Returns:
            list : list of dicts with keys title, url, source, published_at, symbol
        """
        news = []

        for feed_url in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    
                    # Filter by symbol if provided
                    if symbol and symbol.upper() not in title.upper():
                        continue 

                    news.append({
                        "title"         : title,
                        "url"           : entry.get("link", ""),
                        "source"        : feed.feed.get("title", feed_url),
                        "published_at"  : entry.get("published", ""),
                        "symbol"       : symbol
                    })
            except Exception as e:
                print(f"RSS feed failed for {feed_url}: {e}")

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