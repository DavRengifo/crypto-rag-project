import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client once at module level
# Avoids creating a new client on every funciton call
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Embedding model and dimension
EMBEDDING_MODEL     = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

def generate_embedding(text):
    """
    Generate an embedding vector for the given text using OpenAI's API.
    The embedding captures the semantic meaning of the text in a high-dimensional space,
    and is used for similarity search in pgvector.
    
    Args:
        text (str): The input text to embed (title + content).

    Returns:
        list: The embedding vector for the input text of dimension 1536,
        returns None if generation fails.
    """
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding failed: {e}")
        return None