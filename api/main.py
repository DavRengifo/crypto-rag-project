from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
from rag import ask, get_summary
from db import get_postgres_connection
import os
import requests
from datetime import datetime, timedelta, timezone
import hashlib
import json as json_module
import redis

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

# Redis client for report caching
# Avoids duplicate LLM calls for identical symbol sets within 1 hour
redis_client = redis.Redis(
    host           = os.getenv("REDIS_HOST", "redis"),
    port           = int(os.getenv("REDIS_PORT", 6379)),
    decode_responses= True
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
    
class ReportRequest(BaseModel):
    """Request model for on-demand report generation."""
    symbols: list[str]
    period : str = "30d"

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
    try:
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

        return [
            PriceHistoryPoint(
                price_usd  = row[0],
                scraped_at = row[1].isoformat()
            )
            for row in rows
        ]
    finally:
        connection.close()


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
    try:
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
        
    finally:
        connection.close()
    
@app.get("/prices/{symbol}/history", response_model=list[PriceHistoryPoint])
def get_price_history(symbol: str, period: str = "24h"):
    """
    Return the price history for a specific token over a given period.
    Short periods (24h, 7d) use local database — no cache needed.
    Long periods (30d, 1y, 5y) use CoinGecko API — cached 1 hour.
    
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
        # CoinGecko call — cache 1 hour to respect rate limits
        cache_key = f"history:{symbol.upper()}:{period}"
        cached    = redis_client.get(cache_key)
        if cached:
            return json_module.loads(cached)
        
        result = fetch_history_from_coingecko(symbol, period)
        redis_client.setex(
            cache_key,
            3600,
            json_module.dumps([r.model_dump() for r in result])
        )
        
        return result

@app.get("/prices/top-movers", response_model=list[PriceData])
def get_top_movers():
    """
    Return all tokens ordered by 24h price change (best to worst).
    Used to display gainers and losers sections.
    Cached in Redis for 60 seconds — prices update every 5 minutes.
    
    Returns:
        list[PriceData] : tokens sorted by change_24h descending.
    """
    cached = redis_client.get("prices:top_movers")
    if cached:
        return json_module.loads(cached)
    
    rows = []
    connection = get_postgres_connection()
    try:
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
        
    finally:
        connection.close()
    
    result = [
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
                    
    # Serialize via model_dump() — PriceData is not JSON-serializable directly
    redis_client.setex(
        "prices:top_movers",
        60,
        json_module.dumps([r.model_dump() for r in result])
    )

    return result

@app.get("/stats")
def get_stats():
    """
    Return API statistics.
    
    Returns:
        dict: counts of tokens, price snapshots, news articles, embeddings.
    """
    connection = get_postgres_connection()
    try:
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
        
        return {
            "total_tokens"          : row[0],
            "total_price_snapshots" : row[1],
            "total_news_articles"   : row[2],
            "total_embeddings"      : row[3]
        }
        
    finally:
        connection.close()

@app.get("/news", response_model=list[NewsItem])
def get_news(symbol:  Optional[str] = None):
    """
    Return the 20 most recent news articles, ordered by published date.
    Optionally filter by token symbol.
    
    Args:
        symbol (str, optional) : filter by token symbol (e.g. 'BTC')
    
    Returns:
        list[NewsItem] : List of news articles with title, source, url, and published date.
    """
    connection = get_postgres_connection()
    try:
        cursor = connection.cursor()
        
        if symbol:
            query = """
            SELECT n.title, n.source, n.url, n.published_at
            FROM news n
            JOIN tokens t ON t.id = n.token_id
            WHERE t.symbol = %s
            ORDER BY n.published_at DESC
            LIMIT 20
            """
            cursor.execute(query, (symbol.upper(),))
        else:
            query = """
            SELECT title, source, url, published_at
            FROM news
            ORDER BY published_at DESC
            LIMIT 20
            """
            cursor.execute(query)
            
        rows = cursor.fetchall()
        cursor.close()
        
        return [
            NewsItem(
                title        =row[0],
                source       =row[1],
                url          =row[2],
                published_at =row[3].isoformat() if row[3] else None
            )
            for row in rows
        ] 
    
    finally:
        connection.close()

@app.get("/health")
def health_check():
    """
    Health check endpoint.
    Returns API status, used by Docker and monitoring tools to verify the API is running.
    """
    return {"status": "ok"}

@app.get("/reports/market/latest")
def get_market_report():
    """
    Return the latest auto-generated general market report.
    Cached in Redis for 1 hour — market report is generated once per day.

    Returns:
        dict : report content and generation timestamp
    """
    cached = redis_client.get("market_report:latest")
    if cached:
        return json_module.loads(cached)
    
    row = None 
    connection = get_postgres_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT content, generated_at
            FROM reports
            WHERE report_type = 'market'
            ORDER BY generated_at DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        cursor.close()
    finally:
        connection.close()

    if not row:
        raise HTTPException(status_code=404, detail="No market report available yet")

    result = {"content": row[0], "generated_at": str(row[1])}

    redis_client.setex("market_report:latest", 3600, json_module.dumps(result))

    return result

# @app.get("/reports/favorites/latest")
# def get_favorites_report():
#     """
#     Return the latest auto-generated favorites report (V2 with auth).

#     Returns:
#         dict : report content and generation timestamp
#     """
#     connection = get_postgres_connection()
#     try:
#         cursor = connection.cursor()
#         cursor.execute("""
#             SELECT content, generated_at
#             FROM reports
#             WHERE report_type = 'favorites'
#             ORDER BY generated_at DESC
#             LIMIT 1
#         """)
#         row = cursor.fetchone()
#         cursor.close()
#     finally:
#         connection.close()

#     if not row:
#         raise HTTPException(status_code=404, detail="No favorites report available yet")
#     return {"content": row[0], "generated_at": row[1]}

@app.post("/reports/generate")
def generate_report(request: ReportRequest):
    """
    Generate an on-demand report for one or multiple tokens.
    Also used internally by report_generator for the daily market report.
    Results are cached in Redis for 1 hour to handle concurrent identical requests.
    
    Strategy:
    - Per-symbol price history: 24h local Postgres if recent report exists (<48h),
      1 year CoinGecko if first report for that symbol or last report is older than 48h.
    - News: 24h if recent reports exist globally, 30 days for first report.
    - Previous reports: up to 2 most recent reports with overlapping symbols,
      injected as LLM context for continuity and trend comparison.

    Args:
        request (ReportRequest) : symbols list and analysis period

    Returns:
        dict : symbols, period, and generated markdown report content
    """
    symbols = sorted([s.upper() for s in request.symbols]) # sort for consistent cache key
            
    # Check Redis cache — return immediately if identical request was made recently
    cache_key = f"report:{hashlib.md5(json_module.dumps(symbols).encode()).hexdigest()}"
    cached = redis_client.get(cache_key)
    if cached:
        print(f"Cache hit for report {symbols}", flush=True)
        return json_module.loads(cached)
    
    connection = get_postgres_connection()
    try:
        cursor = connection.cursor()

        # Step 1 — Fetch latest price per token
        cursor.execute("""
            SELECT DISTINCT ON (t.symbol)
                t.symbol,
                t.name,
                p.price_usd,
                p.change_24h,
                p.market_cap,
                p.volume_24h
            FROM tokens t
            JOIN price_snapshots p ON p.token_id = t.id
            WHERE t.symbol = ANY(%s)
            ORDER BY t.symbol, p.scraped_at DESC
        """, (symbols,))
        
        prices_data = [
            {
                "symbol"    : r[0],
                "name"      : r[1],
                "price_usd" : float(r[2]),
                "change_24h": float(r[3] or 0),
                "market_cap": float(r[4] or 0),
                "volume_24h": float(r[5] or 0)
            }
            for r in cursor.fetchall()
        ]

        if not prices_data:
            raise HTTPException(
                status_code=404,
                detail=f"No price data found for {symbols}"
            )

        # Step 2 — Global check: do any recent reports exist for these symbols?
        # Used to decide news interval (Step 4) and actual_period for get_summary
        # && = at least one symbol in common
        # A report older than 48h is treated as missing (daily report should refresh)
        cursor.execute("""
            SELECT COUNT(*) FROM reports
            WHERE report_type IN ('custom', 'market')
                AND symbols && %s::text[]
                AND generated_at >= NOW() - INTERVAL '48 hours'
        """, (symbols,))
        
        report_count = cursor.fetchone()[0]
        has_recent_report = report_count > 0
        actual_period   = "24h" if has_recent_report else "1y"
        
        # Step 3 — Price history per symbol individually
        # Each symbol is checked independently:
        # → recent report for this symbol (<48h) → 24h local Postgres data
        # → no recent report for this symbol     → 1 year CoinGecko API
        # This handles A+B+C+D where only A+B+C have recent reports:
        # A, B, C → 24h local | D → 1 year CoinGecko
        price_histories: dict[str, list[dict]] = {}
        
        for sym in symbols:
            cursor.execute("""
                SELECT COUNT(*) FROM reports
                WHERE report_type IN ('custom', 'market')
                AND symbols && ARRAY[%s]::text[]
                AND generated_at >= NOW() - INTERVAL '48 hours'
            """, (sym,))
            sym_has_recent_report = cursor.fetchone()[0] > 0
            
            if sym_has_recent_report:
                # Recent report exists — local 24h data is sufficient and granular
                cursor.execute("""
                    SELECT 
                        p.price_usd,
                        p.scraped_at
                    FROM price_snapshots p
                    JOIN tokens t ON t.id = p.token_id
                    WHERE t.symbol = %s
                        AND p.scraped_at >= NOW() - INTERVAL '24 hours'
                    ORDER BY p.scraped_at ASC
                """, (sym,))

                price_histories[sym] = [
                    {
                        "price_usd": float(r[0]),
                        "scraped_at": r[1].isoformat()
                    }
                    for r in cursor.fetchall()  
                ]
                
            else:
                # No recent report — fetch 1 year from CoinGecko as baseline
                coingecko_id = SYMBOL_TO_ID.get(sym)
                if not coingecko_id:
                    continue
                
                url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart"
                params = {"vs_currency": "usd", "days": 365, "interval": "daily"}
                headers = {}
                if os.getenv("COINGECKO_API_KEY"):
                    headers["x-cg-demo-api-key"] = os.getenv("COINGECKO_API_KEY")
                    
                resp = requests.get(url, params=params, headers=headers, timeout=10)
                if resp.ok:
                    price_histories[sym] = [
                        {
                            "price_usd" : point[1],
                            "scraped_at": datetime.fromtimestamp(
                                point[0] / 1000, tz=timezone.utc
                            ).isoformat()
                        }
                        for point in resp.json().get("prices", [])
                    ]
                    
        # Step 4 — Fetch recent news for the requested tokens
        # 24h if recent reports exist (daily update), 30 days for first report
        news_interval = "24 hours" if has_recent_report else "30 days"
        cursor.execute("""
            SELECT 
                n.title,
                n.source,
                n.published_at
            FROM news n
            JOIN tokens t ON t.id = n.token_id
            WHERE t.symbol = ANY(%s)
              AND n.published_at >= NOW() - INTERVAL %s
            ORDER BY n.published_at DESC
            LIMIT 20
        """, (symbols, news_interval))
        news_articles = [
            {
                "title": r[0],
                "source": r[1],
                "published_at": str(r[2])    
            }
            for r in cursor.fetchall()
        ]

        # Step 5 — Fetch up to 2 previous reports for LLM context and continuity
        # Uses && (intersection) so partial symbol overlap is accepted as context
        # e.g. a BTC+ETH report is useful context for a BTC+ETH+SOL request
        # ORDER BY generated_at DESC → most recent first (most relevant)
        cursor.execute("""
            SELECT content FROM reports
            WHERE report_type IN ('custom', 'market')
                AND symbols && %s::text[]
            ORDER BY generated_at DESC
            LIMIT 2
        """, (symbols,))
        previous_reports = [row[0] for row in cursor.fetchall()] or None

        cursor.close()
    finally:
        connection.close()

    # Step 6 — Generate report via LLM
    content = get_summary(
        symbols          = symbols,
        prices_data      = prices_data,
        news_articles    = news_articles,
        price_histories  = price_histories,
        period           = actual_period,
        previous_reports = previous_reports
    )

    # Step 7 — Persist report in DB
    # token_id is NULL for multi-token reports — no single token ownership
    # report_generator will UPDATE report_type to 'market' for daily reports
    connection = get_postgres_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO reports (report_type, content, generated_at, symbols)
            VALUES ('custom', %s, NOW(), %s)
        """, (content, symbols))
        connection.commit()
        cursor.close()
    finally:
        connection.close()

    result = {
        "symbols": symbols,
        "period" : actual_period,
        "content": content
    }
    
    # Store in Redis cache — expires after 1 hour
    redis_client.setex(cache_key, 3600, json_module.dumps(result))
    
    return result

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