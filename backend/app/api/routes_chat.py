from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.routes_repo import REPO_CACHE
from app.core.vector_store import get_or_create_vector_store
from app.core.llm_service import llm_service

router = APIRouter(prefix="/api/chat", tags=["Copilot & Chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatQueryRequest(BaseModel):
    repo_id: str
    query: str
    history: Optional[List[ChatMessage]] = Field(default_factory=list)


class FlowExplanationRequest(BaseModel):
    repo_id: str
    topic: str


@router.post("/query")
async def chat_with_codebase(payload: ChatQueryRequest):
    """
    RAG-powered conversational endpoint for codebase queries.
    Retrieves relevant code chunks and synthesizes an architectural explanation.
    """
    repo_id = payload.repo_id
    if repo_id not in REPO_CACHE:
        raise HTTPException(status_code=404, detail="Repository not found. Please ingest the repository first.")

    repo_data = REPO_CACHE[repo_id]
    vector_store = get_or_create_vector_store(repo_id)

    # 1. Retrieve most relevant code chunks
    retrieved_chunks = vector_store.search(payload.query, top_k=7)

    # 2. Synthesize answer with Claude 3.5 or Heuristic engine
    result = llm_service.answer_query(
        query=payload.query,
        retrieved_chunks=retrieved_chunks,
        repo_name=repo_data["repo_name"],
        modules=repo_data["modules"],
    )

    return {
        "repo_id": repo_id,
        "query": payload.query,
        "answer": result["answer"],
        "citations": result["citations"],
        "provider": result.get("provider", llm_service.active_provider),
        "retrieved_chunks": [
            {
                "chunk_id": c["chunk_id"],
                "file_path": c["file_path"],
                "start_line": c["start_line"],
                "end_line": c["end_line"],
                "symbol": c.get("symbol", ""),
                "score": c.get("relevance_score", 0),
            }
            for c in retrieved_chunks
        ],
    }


@router.post("/explain-flow")
async def explain_codebase_flow(payload: FlowExplanationRequest):
    """
    Generates a dedicated step-by-step trace and sequence diagram for a specific flow.
    """
    repo_id = payload.repo_id
    if repo_id not in REPO_CACHE:
        raise HTTPException(status_code=404, detail="Repository not found.")

    repo_data = REPO_CACHE[repo_id]
    vector_store = get_or_create_vector_store(repo_id)

    # Query with flow focus
    expanded_query = f"trace flow sequence lifecycle for: {payload.topic}"
    retrieved = vector_store.search(expanded_query, top_k=8)

    result = llm_service.answer_query(
        query=f"Explain the complete execution and data flow for: {payload.topic}. Include entry points, middleware, controllers, services, and database queries.",
        retrieved_chunks=retrieved,
        repo_name=repo_data["repo_name"],
        modules=repo_data["modules"],
    )

    return {
        "repo_id": repo_id,
        "topic": payload.topic,
        "flow_explanation": result["answer"],
        "citations": result["citations"],
        "provider": result.get("provider", llm_service.active_provider),
    }
