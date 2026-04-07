from fastapi import FastAPI, HTTPException
from coinmarketcap import CryptoScraper

app = FastAPI(
    title="CoinMarketCap Scraper Service",
    description="Internal scraping service - fallback for price data when CoinGecko API is unavailable.",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    """Health check endpoint to verify scraper service is running."""
    return {"status": "ok"}

@app.get("/scrape")
def scrape_prices():
    """
    Scrape cryptocurrency data from CoinMarketCap as a fallback method.
    
    Returns:
        list : list of dicts with keys Name, Symbol, Price,
        MarketCap, Volume24h, Change24h, Date
    """
    scraper = None
    
    try:
        scraper = CryptoScraper("https://coinmarketcap.com/")
        scraper.load_page()
        data = scraper.extract_crypto_data()
        return data.to_dict(orient="records")
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scraping failed: {str(e)}"
        )
        
    finally:
        if scraper:
            scraper.close()