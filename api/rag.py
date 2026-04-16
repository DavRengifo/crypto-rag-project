import os
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL       = "gpt-5.4-mini"
TOP_K           = 5    # number of articles to retrieve for RAG

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
    
def embed_question(question):
    """
    Generate an embedding vector for the input question using OpenAI's API.
    
    Args:
        question (str): The user's question to be embedded.

    Returns:
        list: The embedding vector for the input question of dimension 1536,
        returns None if generation fails.
    """ 
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=question
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding failed: {e}")
        return None

def search_similar_news(question_embedding, top_k=TOP_K):
    """
    Search for news articles semantically similar to the question.
    Uses pgvector's cosine similarity operator (<=>) on embeddings_news table.
    
    Args:
        question_embedding (list): The embedding vector of the user's question.
        top_k (int): The number of top similar articles to retrieve.
        
    Returns:
        list: A list of dicts representing news articles,
        each with keys: title, content, url, source, published_at.
    """
    connection = get_postgres_connection()
    cursor = connection.cursor()

    similar_news_search_query = """
    SELECT 
        n.title, 
        n.content, 
        n.url, 
        n.source, 
        n.published_at,
        e.embedding <=> %s::vector AS distance
    FROM embeddings_news e
    JOIN news n ON n.id = e.news_id
    ORDER BY distance
    LIMIT %s
    """
    
    # Convert embedding into string format pgvector
    embedding_str = "[" + ",".join(map(str, question_embedding)) + "]"
    
    cursor.execute(similar_news_search_query, (embedding_str, TOP_K))
    results = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    articles = []
    for row in results:
        articles.append({
            "title"         : row[0],
            "content"       : row[1],
            "url"           : row[2],
            "source"        : row[3],
            "published_at"  : row[4],
            "distance"      : row[5]
        })
    return articles

def build_context(articles):
    """
    Build a context string from the retrieved news articles to inject into the LLM prompt.
    
    Args:
        articles (list): list of article dicts with keys: title, content, url, source, published_at.
    
    Returns:
        str: A formatted string containing the context from the news articles.
    """
    context = ""
    for i, article in enumerate(articles):
        context += f"""
        Article {i + 1} — {article['source']} ({article['published_at']})
        Title: {article['title']}
        Content: {article.get('content') or 'No content available.'}
        """
    return context

def generate_answer(question, articles):
    """
    Generate a natural language answer using retrieved articles as context.
    Sends question + context to GPT-5.4-mini and returns the response.

    Args:
        question : str  — original user question
        articles : list — retrieved articles from search_similar_news()

    Returns:
        str : generated answer from the LLM
    """
    context = build_context(articles)
    
    prompt = f"""
        You are a cryptocurrency market analyst.
        Answer the following question based ONLY on the provided news articles.
        If the articles do not contain enough information, say so clearly.
        
        NEWS CONTEXT:
        {context}
        
        QUESTION:
        {question}

        Provide a clear, concise answer in 3-5 sentences.
    """
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system",
             "content": "You are a helpful cryptocurrency market analyst. Answer only based on the provided context."},
            {"role": "user",
             "content": prompt}
        ],
        temperature=0.3, # lower temperature for more factual answers
    )
    return response.choices[0].message.content.strip()

def ask(question):
    """
    Main RAG pipeline. Embeds the question, retrieves relevant articles, and generates an answer.
    
    Args:
        question (str): The user's question in natural language.
        
    Returns:
        dict: answer and sources used
    """
    # Step 1: Embed the question
    question_embedding = embed_question(question)
    if not question_embedding:
        return {"answer": "Sorry, I couldn't process your question.", "sources": []}
    
    # Step 2: Retrieve similar news articles using the question embedding
    articles = search_similar_news(question_embedding)
    if not articles:
        return {"answer": "Sorry, I couldn't find relevant news articles to answer your question.", "sources": []}
    
    # Step 3: Generate an answer
    answer = generate_answer(question, articles)
    if not answer:
        return {"answer": "Sorry, I couldn't generate an answer based on the retrieved articles.", "sources": articles}

    return {"answer": answer,
            "sources": [
                {
                    "title"        : a["title"],
                    "source"      : a["source"],
                    "published_at" : str(a["published_at"]),
                    "distance"     : round(a.get("distance", 0), 4)
                }
                for a in articles
            ]}