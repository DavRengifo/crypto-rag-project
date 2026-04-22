import os
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
from db import get_postgres_connection

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL       = "gpt-5.4-mini"
TOP_K           = 5    # number of articles to retrieve for RAG
    
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
    try:
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
        
        cursor.execute(similar_news_search_query, (embedding_str, top_k))
        results = cursor.fetchall()
        
        cursor.close()
        
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
    
    finally:
        connection.close()

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

def get_summary(
    symbols:            list[str],
    prices_data:        list[dict],
    news_articles:      list[dict],
    price_histories:    dict[str, list[dict]],
    period:             str = "1y",
    previous_reports:   list[str] | None = None
) -> str:
    """
    Generate an AI-powered market report for one or multiple tokens.
    Uses price history, recent news, and previous reports for trend analysis.
    When previous reports exist, only recent data (24h) is needed.
    When no previous reports exist, full historical data (1Y) is used.

    Args:
        symbols          : list of token symbols (e.g. ['BTC', 'ETH'])
        prices_data      : list of current price dicts
        news_articles    : list of recent news dicts
        price_histories  : dict of historical price points indexed by symbol
                           e.g. {"BTC": [{price_usd: ..., scraped_at: ...}, ...]}
        period           : analysis period for trend calculation (default: 1y)
        previous_reports : list of previous report contents (max 2), or None

    Returns:
        str : generated markdown report
    """
    
    # Step 1 — Build price context with trend per token
    
    price_context = ""
    
    for p in prices_data:
        history = price_histories.get(p['symbol'], [])
        if history:
            oldest = history[0]['price_usd']
            newest = history[-1]['price_usd']
            trend_pct = ((newest - oldest) / oldest) * 100
            trend_str = f"{'▲' if trend_pct >= 0 else '▼'} {abs(trend_pct):.1f}% over {period}"
        else:
            trend_str = "no history available"
            
        price_context += f"""
            {p['symbol']} ({p['name']})
            Current price : ${p['price_usd']:,.2f}
            24h change    : {p['change_24h']:+.2f}%
            Market cap    : ${p['market_cap']:,.0f}
            Volume 24h    : ${p['volume_24h']:,.0f}
            Trend {period}  : {trend_str}
        """
    
    # Step 2 — Build news context
    
    news_context = "\n".join([
        f"- [{a['source']}] {a['title']}"
        for a in news_articles[:10]
    ])

    # Step 3 — Build previous reports context if available
    # Truncated to 800 chars each to control token cost
    previous_context = ""
    if previous_reports:
        summaries = "\n\n---\n\n".join(
            f"Report from {i + 1} day(s) ago:\n{r[:800]}"
            for i, r in enumerate(previous_reports)
        )
        previous_context = f"""
            PREVIOUS REPORTS (for continuity and trend comparison):
            {summaries}
        """
        
    # Step 4 — Build analysis instruction based on context availability
    # If previous reports exist, instruct the LLM to compare and update
    # If not, instruct a full baseline analysis
    if previous_reports:
        instruction = f"""
            You have access to previous daily reports above.
            Focus on what has CHANGED since the last report.
            Compare current prices and news to the previous context.
            Highlight new developments, trend reversals, or confirmations.
        """
    else:
        instruction = f"""
            This is the first report — no previous context exists.
            Provide a comprehensive baseline analysis covering the full {period} period.
            Be thorough. This report will serve as the reference for all future reports.
        """
    
    # Step 5 — Determine report scope
    is_general = len(symbols) > 3
    scope = "the overall crypto market" if is_general else ", ".join(symbols)
    
    # Step 6 — Build single unified prompt
    prompt = f"""
        You are a professional cryptocurrency market analyst.
        Generate a structured daily report for {scope}.

        {previous_context}

        CURRENT PRICE DATA:
        {price_context}

        RECENT NEWS:
        {news_context}

        {instruction}

        Write a structured report including:
        1. Executive Summary (2-3 sentences)
        2. Price Analysis (trend, key levels, momentum)
        3. News Impact (how news affected prices)
        4. What Changed Since Last Report (skip this section if no previous reports)
        5. Beginner Insight (simple explanation of what is happening)
        6. Expert Insight (technical and macro perspective)
        7. Outlook (short-term expectation based on data)
        8. Risk Disclaimer

        Be factual, cite news sources, use the actual price numbers provided.
        Format in clean markdown.
    """     
        
    # Step 7 — Generate report via LLM
    
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role"   : "system",
                "content": "You are a professional crypto analyst. Always base your analysis strictly on provided data."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()  