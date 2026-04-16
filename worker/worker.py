import redis
import psycopg2
from psycopg2.extras import execute_values # optimized insertion
import json
from io import StringIO
import time
import os
from dotenv import load_dotenv
import pandas as pd
from embedding import generate_embedding, EMBEDDING_MODEL

load_dotenv()

# Configuration of postgres connection using environment variables
def get_postgres_connection():
    """
    Establish a connection to the PostgreSQL database.
    Reads connection parameters from environment variables:
        POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
    
    Args:
        None
        
    Returns:
        psycopg2 connection object to the Postgres database
    """
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB")
    )
    
def none_if_nan(value):
    """
    Convert NaN pandas value to None for Postgres compatibility.
    
    Args:
        value : pandas Series value, potentially NaN
    
    Returns:
        None if value is NaN, otherwise the original value
    """
    return None if pd.isna(value) else value

def upsert_token(cursor, symbol, name):
    """
    Insert a token into the database if it does not already exist.
    If the symbol already exists, update the name.

    Args:
        cursor  : active psycopg2 cursor
        symbol  : token symbol (e.g. 'BTC')
        name    : full token name (e.g. 'Bitcoin')

    Returns:
        UUID : token id in the database (new or existing)
    """
    query = """
    INSERT INTO tokens (symbol, name, slug)
    VALUES (%s, %s, %s)
    ON CONFLICT (symbol) DO UPDATE SET name = EXCLUDED.name
    RETURNING id
    """
    cursor.execute(query, (symbol, name, symbol.lower()))
    return cursor.fetchone()[0]

# Task processing function
def process_price_task(task_data):
    """
    Process a task from the Redis queue.
    Deserializes the JSON data, then inserts tokens
    and price snapshots into the Postgres database.

    Args:
        task_data : JSON string received from Redis queue
        
    Returns:
        None
    """
    connection = None
    try:
        # Step 1 : deserialize JSON data BEFORE opening a connection
        # (avoids wasting a connection if the data is corrupted)
        df = pd.read_json(StringIO(task_data), orient="records")
        
        # Convert millisecond timestamps to Python datetime
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], unit="ms")
            
        # Step 2 : open connection only if data is valid
        connection = get_postgres_connection()
        cursor = connection.cursor()

        # SQL Query for price snapshots insertion
        query = """
        INSERT INTO price_snapshots (token_id, price_usd, market_cap, volume_24h, change_24h, scraped_at, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        # Step 3 : insert each row of the DataFrame
        for _, row in df.iterrows():
            
            # 3a. Insert or retrieve the token — returns its UUID
            token_id = upsert_token(cursor, row["Symbol"], row["Name"])

            # 3b. Insert the price snapshot linked to this token
            cursor.execute(query, (
                token_id, 
                row["Price"], 
                none_if_nan(row.get("MarketCap")), 
                none_if_nan(row.get("Volume24h")), 
                none_if_nan(row.get("Change24h")),
                row["Date"],
                "coinmarketcap"))

        # Step 4 : commit all insertions as a single transaction
        connection.commit()
        print(f"{len(df)} rows successfully inserted.")

    except json.JSONDecodeError as e:
        print(f"JSON deserialization error: {e}")
    except psycopg2.Error as e:
        print(f"Postgres error: {e}")
        if connection:
            connection.rollback()  # Cancel transaction
    except Exception as e:
        print(f"Unexpected error: {e}")
        if connection:
            connection.rollback()  # Cancel transaction
    finally:
         # Close the connection cleanly, even if an error occurred
        if connection and not connection.closed:
            cursor.close()
            connection.close()
            print("Postgres connection closed.")
            
def process_news_task(task_data):
    """
    Process a news task from the Redis queue.
    Deserializes the JSON articles, resolves token_id from symbol,
    then inserts news articles into the news table.

    Args:
        task_data : JSON string received from Redis news_queue
        
    Returns:
        None
    """
    connection = None
    try:
        #Step 1 : deserialize JSON data BEFORE opening a connection
        articles = json.loads(task_data)
        
        #Step 2 : open connection only if data is valid
        connection = get_postgres_connection()
        cursor = connection.cursor()
        
        # Step 3 : insert each article, resolving token_id from symbol
        for article in articles:
            
            # 3a. Resolve token_id from symbol
            # symbol can be None if no currency was tagged
            token_id = None
            query = """
               SELECT id FROM tokens WHERE symbol = %s
            """
            
            if article.get("symbol"):
                cursor.execute(query, (article["symbol"],))
                result = cursor.fetchone()
                token_id = result[0] if result else None
                
            # 3b. Insert article - ON CONFLICT DO NOTHING to avoid duplicates
            insert_query = """
            INSERT INTO news (token_id, title, content, url, source, published_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
            RETURNING id
            """
            cursor.execute(insert_query, (
                token_id,
                article["title"],
                article.get("content"),
                article["url"],
                article["source"],
                article["published_at"],
            ))
            
            # 3c. Generate and store embedding if article was inserted (not a duplicate)
            embedding_query = """
                INSERT INTO embeddings_news (news_id, embedding, model)
                VALUES (%s, %s, %s)
            """
            result = cursor.fetchone()
            if result:  # New article was inserted
                news_id= result[0]
                text_to_embed = f"{article['title']} {article.get('content', '')}"
                embedding = generate_embedding(text_to_embed)
                
                if embedding:
                    cursor.execute(embedding_query, (news_id, embedding, EMBEDDING_MODEL))
                    
        # Step 4 : commit all insertions as a single transaction
        connection.commit()
        print(f"{len(articles)} articles inserted.")
        
    except json.JSONDecodeError as e:
        print(f"JSON deserialization error: {e}")
    except psycopg2.Error as e:
        print(f"Postgres error: {e}")
        if connection:
            connection.rollback()  # Cancel transaction
    except Exception as e:
        print(f"Unexpected error: {e}")
        if connection:
            connection.rollback()  # Cancel transaction
    finally:
         # Close the connection cleanly, even if an error occurred
        if connection and not connection.closed:
            cursor.close()
            connection.close()
            print("Postgres connection closed.")
    

def main():
    """
    Main worker loop.
    Connects to Redis and listens for tasks on the crypto_data_queue.
    Calls process_task() for each received task.

    Args:
        None
        
    Returns:
        None    
    """
    # Connect to Redis using environment variables (with defaults for local testing)
    # Listen to "crypto_data_queue" for new tasks
    client = redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True
    )
    print("Worker is listening for tasks...")

    while True:
        # blpop = Task recuperation with blocking pop (waits for new tasks in the queue)
        # timeout=5 means it will wait up to 5 seconds for a new task before printing a waiting message
        task = client.blpop(["prices_queue", "news_queue"], timeout=5)

        if task:
            queue_name, task_data = task  # queue_name tells where the task came from (prices or news)

            if queue_name == "prices_queue":
                print("Price task received, processing...")
                process_price_task(task_data)
            
            elif queue_name == "news_queue":
                print("News task received, processing...")
                process_news_task(task_data)
            
        else:
            print("Waiting for new tasks...")
            time.sleep(1)

if __name__ == "__main__":
    main()
