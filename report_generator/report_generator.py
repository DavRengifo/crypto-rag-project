import os
import time
import schedule
import requests
import psycopg2
from datetime import datetime, timezone
import hashlib, json
import redis
from dotenv import load_dotenv

load_dotenv()

# All tracked symbols — single source of truth for this service
# Duplicated from main.py intentionally (no shared module to avoid Docker complexity)
SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "DOT": "polkadot",
}

ALL_SYMBOLS = sorted((SYMBOL_TO_ID.keys()))

def get_postgres_connection():
    """
    Establish a connection to the PostgreSQL database.
    Duplicated from api/db.py — intentional, avoids Docker shared volume complexity.
    
    Args:
        None

    Returns:
        psycopg2 connection object
    """
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

def wait_for_api() -> bool:
    """
    Wait for the API service to be ready and have price data.
    Retries up to 20 times with 10 second intervals.

    Args:
        None

    Returns:
        bool : True if API is ready with data, False if timeout
    """
    for attempt in range(20):
        try:
            response = requests.get("http://api:8000/prices", timeout=5)
            if response.ok and len(response.json()) > 0:
                print("API is ready with price data.", flush=True)
                return True
            print(f"API ready but no price data yet... attempt {attempt + 1}/20", flush=True)
        except Exception as e:
            print(f"Waiting for API... attempt {attempt + 1}/20 ({e})", flush=True)
        time.sleep(10)

    print("API not ready after 20 attempts. Skipping startup report.", flush=True)
    return False

def market_report_exists_today() -> bool:
    """
    Check whether a market report has already been generated today.
    Prevents duplicate generation if the service restarts during the day.
    Uses 23h instead of 24h to avoid false positives near midnight.

    Args:
        None

    Returns:
        bool : True if a market report exists from the last 23 hours
    """
    connection = get_postgres_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM reports
            WHERE report_type = 'market'
              AND generated_at >= NOW() - INTERVAL '23 hours'
        """)
        count = cursor.fetchone()[0]
        cursor.close()
        return count > 0
    finally:
        connection.close()

def generate_daily_market_report():
    """
    Generate and store the daily general market report.
    Calls POST /reports/generate on the internal API service for all tracked symbols.
    The API saves the report as 'custom' — this function then relabels it as 'market'.
    Cache is invalidated before the call to ensure a fresh report is always generated.
    
    Args:
        None
        
    Returns:
        None
    """
    print(f"[{datetime.now()}]) Generating daily market report...", flush=True)
    
    try:
        #Invalidate Redis cache for ALL_SYMBOLS before generating
        # Without this, the API returns a cached report instead of inserting a new one
        # which would prevent the UPDATE from finding a fresh 'custom' report
        redis_client = redis.Redis(
            host           = os.getenv("REDIS_HOST", "redis"),
            port           = int(os.getenv("REDIS_PORT", 6379)),
            decode_responses= True
        )
        cache_key = f"report:{hashlib.md5(json.dumps(sorted(ALL_SYMBOLS)).encode()).hexdigest()}"
        redis_client.delete(cache_key)
        print(f"Cache invalidated for ALL_SYMBOLS.", flush=True)
        
        # Call the internal API with all tracked symbols
        # The API service handles all data fetching and LLM generation
        response = requests.post(
            "http://api:8000/reports/generate",
            json={"symbols": ALL_SYMBOLS, "period": "1y"},
            timeout=180 
        )
        response.raise_for_status()
        
        # Relabel the fresh 'custom' report as 'market'
        connection = get_postgres_connection()
        try:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE reports
                SET report_type = 'market'
                WHERE report_type = 'custom'
                    AND symbols = %s::text[]
                    AND generated_at >= NOW() - INTERVAL '5 minutes'
            """, (ALL_SYMBOLS,))
            updated = cursor.rowcount
            connection.commit()
            cursor.close()
        finally:
            connection.close()
            
        if updated == 0:
            print(f"[{datetime.now(timezone.utc)}] WARNING: UPDATE found no report to relabel.", flush=True)
        else:
            print(f"[{datetime.now(timezone.utc)}] Market report generated successfully.", flush=True)
        
    except Exception as e:
        print(f"[{datetime.now()}] Failed to generate market report: {e}", flush=True)
        
def main():
    """
    Main loop for the report generator service.
    Waits for Postgres to be ready before starting.
    Generates a market report immediately on startup if none exists today.
    Schedules daily generation at 08:00 UTC.
    
    Args:
        None
    """
    print("Report generator started.", flush=True)
    
    # Wait for Postgres to be ready — it may not be accepting connections yet
    # even though the container has started
    for attempt in range(10):
        try:
            conn = get_postgres_connection()
            conn.close()
            print("Postgres is ready.", flush=True)
            break
        except Exception as e:
            print(f"Waiting for Postgres... attempt {attempt + 1}/10 ({e})", flush=True)
            time.sleep(5)
    else:
        print("Could not connect to Postgres after 10 attempts. Exiting.", flush=True)
        return
    
    # Step 2 — Wait for API and price data
    # Collectors need time to fetch first prices before a report can be generated
    # Generate immediately on startup if no report exists in the last 23h    
    if not wait_for_api():
        print("Skipping startup report — will retry at 08:00 UTC.", flush=True)
    elif not market_report_exists_today():
        print("No market report found for today - generating now.", flush=True)
        generate_daily_market_report()   
    else:  
        print("Market report already exists for today — skipping startup generation.", flush=True)
        
    # Schedule daily at 8:00 UTC
    schedule.every().day.at("08:00").do(generate_daily_market_report)
    
    # Main loop — wakes up every 60 seconds to check if 08:00 has passed
    while True:
        schedule.run_pending()
        time.sleep(60)
        
if __name__ == "__main__":
    main()