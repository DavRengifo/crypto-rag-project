from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
from rag import ask, get_postgres_connection
import os
import requests
from datetime import datetime, timedelta, timezone

# Constants

PERIOD_MAP = {
    "24h": timedelta(hours=24),
    "7d" : timedelta(days=7),
    "30d": timedelta(days=30),
    "1y" : timedelta(days=365),
    "5y" : timedelta(days=1825),
}

# Mapping from token symbol to CoinGecko ID
SYMBOL_TO_ID = {
    "BTC" : "bitcoin",
    "ETH" : "ethereum",
    "SOL" : "solana",
    "BNB" : "binancecoin",
    "XRP" : "ripple",
    "DOGE": "dogecoin",
    "ADA" : "cardano",
    "DOT" : "polkadot",
}

# App

app = FastAPI(
    title="Crypto RAG API",
    description="API for Retrieval-Augmented Generation (RAG) on cryptocurrency news and prices.",
    version="1.0.0"
)

# Pydantic models

class QuestionRequest(BaseModel):
    """
        Request model for the /ask endpoint.
    """
    question: str

class AnswerResponse(BaseModel):
    """
        Response model for the /ask endpoint.
    """
    answer: str
    sources: list[dict[str, Any]]
    
class PriceData(BaseModel):
    """Response model for a single token price."""
    symbol      : str
    name        : str
    price_usd   : float
    market_cap  : Optional[float]
    volume_24h  : Optional[float]
    change_24h  : Optional[float]
    scraped_at  : Optional[str]
    
class PriceHistoryPoint(BaseModel):
    """Single price data point for historical chart."""
    price_usd  : float
    scraped_at : str

class NewsItem(BaseModel):
    """Response model for a single news article."""
    title        : str
    source       : str
    url          : Optional[str]
    published_at : Optional[str]

# Helper functions

def fetch_history_from_postgres(symbol: str, period: str) -> list[PriceHistoryPoint]:
    """
    Fetch price history from local Postgres database.
    Used for short periods (24h, 7d) where local data is fresh and granular.

    Args:
        symbol : token symbol (e.g. 'BTC')
        period : time period key from PERIOD_MAP

    Returns:
        list[PriceHistoryPoint] : price data points ordered by time
    """
    since = datetime.now(timezone.utc) - PERIOD_MAP[period]
    connection = get_postgres_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT p.price_usd, p.scraped_at
        FROM price_snapshots p
        JOIN tokens t ON t.id = p.token_id
        WHERE t.symbol = %s
          AND p.scraped_at >= %s
        ORDER BY p.scraped_at ASC
    """, (symbol.upper(), since))
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    return [
        PriceHistoryPoint(
            price_usd  = row[0],
            scraped_at = row[1].isoformat()
        )
        for row in rows
    ]


def fetch_history_from_coingecko(symbol: str, period: str) -> list[PriceHistoryPoint]:
    """
    Fetch historical price data from CoinGecko API.
    Used for long periods (30d, 1y, 5y) not available in local database.

    Args:
        symbol : token symbol (e.g. 'BTC')
        period : time period — '30d', '1y', '5y'

    Returns:
        list[PriceHistoryPoint] : price data points ordered by time
    """
    DAYS_MAP = {"30d": 30, "1y": 365, "5y": 1825}

    coingecko_id = SYMBOL_TO_ID.get(symbol.upper())
    if not coingecko_id:
        raise HTTPException(
            status_code=404,
            detail=f"Token {symbol} not supported for historical data"
        )

    days = DAYS_MAP[period]
    url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days"       : days,
        "interval"   : "daily"
    }

    headers = {}
    coingecko_key = os.getenv("COINGECKO_API_KEY")
    if coingecko_key:
        headers["x-cg-demo-api-key"] = coingecko_key

    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()

    return [
        PriceHistoryPoint(
            price_usd  = point[1],
            scraped_at = datetime.fromtimestamp(
                point[0] / 1000, tz=timezone.utc
            ).isoformat()
        )
        for point in data["prices"]
    ]


# Endpoints

@app.get("/prices", response_model=list[PriceData])
def get_prices():
    """
    Return the latest price for each tracked token.
    Uses DISTINCT ON to return only the most recent snapshot per token.
    
    Returns:
        list[PriceData] : List of latest price data for all tokens.
    """
    connection = get_postgres_connection()
    cursor = connection.cursor()
    
    query = """
    SELECT DISTINCT ON (token_id) 
        t.symbol,
        t.name,
        p.price_usd,
        p.market_cap,
        p.volume_24h,
        p.change_24h,
        p.scraped_at
    FROM price_snapshots p
    JOIN tokens t ON t.id = p.token_id
    ORDER BY token_id, scraped_at DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    
    return [
        PriceData(
            symbol      =row[0],
            name        =row[1],
            price_usd   =row[2],
            market_cap  =row[3],
            volume_24h  =row[4],
            change_24h  =row[5],
            scraped_at  =row[6].isoformat() if row[6] else None
        )
        for row in rows
    ]
    
@app.get("/prices/{symbol}/history", response_model=list[PriceHistoryPoint])
def get_price_history(symbol: str, period: str = "24h"):
    """
    Return the price history for a specific token over a given period.
    Short periods (24h, 7d) use local database.
    Long periods (30d, 1y, 5y) use CoinGecko API.
    
    Args:
        symbol (str): token symbol (e.g. 'BTC')
        period (str): time period — '24h', '7d', '30d', '1y', '5y' (default: '24h')
        
    Returns:
        list[PriceHistoryPoint] : List of price and timestamp data points.
    """
    if period not in PERIOD_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Choose from: {list(PERIOD_MAP.keys())}"
        )
        
    if period in ["24h", "7d"]:
        return fetch_history_from_postgres(symbol, period)
    else:
        return fetch_history_from_coingecko(symbol, period)

@app.get("/prices/top-movers", response_model=list[PriceData])
def get_top_movers():
    """
    Return all tokens ordered by 24h price change (best to worst).
    Used to display gainers and losers sections.
    
    Returns:
        list[PriceData] : tokens sorted by change_24h descending.
    """
    connection = get_postgres_connection()
    cursor = connection.cursor()
    
    query = """
    -- Step 1 : last snapshot per token
    WITH latest AS (
        SELECT DISTINCT ON (token_id)
            t.symbol,
            t.name,
            p.price_usd,
            p.market_cap,
            p.volume_24h,
            p.change_24h,
            p.scraped_at
        FROM price_snapshots p
        JOIN tokens t ON t.id = p.token_id
        WHERE p.change_24h IS NOT NULL
        ORDER BY token_id, scraped_at DESC
    )
    -- Step 2 : order by variation
    SELECT * FROM latest
    ORDER BY change_24h DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    
    return [
        PriceData(
            symbol      =row[0],
            name        =row[1],
            price_usd   =row[2],
            market_cap  =row[3],
            volume_24h  =row[4],
            change_24h  =row[5],
            scraped_at  =row[6].isoformat() if row[6] else None
        )
        for row in rows
    ]

@app.get("/stats")
def get_stats():
    """
    Return API statistics.
    
    Returns:
        dict: counts of tokens, price snapshots, news articles, embeddings.
    """
    connection = get_postgres_connection()
    cursor = connection.cursor()
    
    query = """
    SELECT
        (SELECT COUNT(*) FROM tokens) AS tokens,
        (SELECT COUNT(*) FROM price_snapshots) AS prices,
        (SELECT COUNT(*) FROM news) AS news,
        (SELECT COUNT(*) FROM embeddings_news) AS embeddings
    """
    cursor.execute(query)
    row = cursor.fetchone()
    cursor.close()
    connection.close()
    
    return {
        "total_tokens"          : row[0],
        "total_price_snapshots" : row[1],
        "total_news_articles"   : row[2],
        "total_embeddings"      : row[3]
    }

@app.get("/news", response_model=list[NewsItem])
def get_news():
    """
    Return the 20 most recent news articles, ordered by published date.
    
    Returns:
        list[NewsItem] : List of news articles with title, source, url, and published date.
    """
    connection = get_postgres_connection()
    cursor = connection.cursor()
    
    query = """
    SELECT title, source, url, published_at
    FROM news
    ORDER BY published_at DESC
    LIMIT 20
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    
    return [
        NewsItem(
            title        =row[0],
            source       =row[1],
            url          =row[2],
            published_at =row[3].isoformat() if row[3] else None
        )
        for row in rows
    ]

@app.get("/health")
def health_check():
    """
    Health check endpoint.
    Returns API status, used by Docker and monitoring tools to verify the API is running.
    """
    return {"status": "ok"}

@app.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    """
    Main RAG endpoint for asking questions about cryptocurrency news and prices.
    Receives a question, retrieves relevant news articles,
    and returns an AI-generated answer along with sources.

    Args:
        request (QuestionRequest): Contains the user's question.
    
    Returns:
        AnswerResponse: Contains the generated answer and list of sources used.
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )
        
    result = ask(request.question)
    return AnswerResponse(
        answer=result["answer"],
        sources=result["sources"]
    )
  
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
  
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app" if DEBUG else app,
        host="0.0.0.0",
        port=8000,
        reload=DEBUG
    )