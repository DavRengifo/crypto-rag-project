from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add root directory to path
from api.rag import ask

app = FastAPI(
    title="Crypto RAG API",
    description="API for Retrieval-Augmented Generation (RAG) on cryptocurrency news and prices.",
    version="1.0.0"
)

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