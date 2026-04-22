import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_postgres_connection():
    """
    Establishes a connection to the Postgres database using environment variables.
    
    Args:
        None
        
    Returns:
        connection: A psycopg2 connection object to the Postgres database.
    """
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )