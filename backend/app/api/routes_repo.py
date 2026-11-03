import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import REPOS_DIR
from app.core.ingester import clone_github_repo, scan_repository, sanitize_repo_name
from app.core.tree_builder import build_file_tree, extract_architecture_modules
from app.core.chunker import chunk_all_files
from app.core.vector_store import get_or_create_vector_store
from app.core.llm_service import llm_service

router = APIRouter(prefix="/api/repo", tags=["Repository"])

# In-memory session cache for processed repositories
REPO_CACHE: Dict[str, Dict[str, Any]] = {}


class IngestRequest(BaseModel):
    repo_url: Optional[str] = Field(None, description="Public GitHub repository URL")
    local_path: Optional[str] = Field(None, description="Local folder path on machine")
    sample_key: Optional[str] = Field(None, description="Sample repository key")


# Curated sample repositories for quick 1-click testing
SAMPLE_REPOS = [
    {
        "key": "fastapi-realworld",
        "name": "FastAPI RealWorld Example App",
        "url": "https://github.com/nsidnev/fastapi-realworld-example-app",
        "description": "Clean architecture backend with JWT Auth, SQLAlchemy, CRUD routers, and Pydantic models.",
        "tags": ["Python", "FastAPI", "SQLAlchemy", "JWT Auth", "PostgreSQL"],
    },
    {
        "key": "express-auth-api",
        "name": "Node.js Express Authentication API",
        "url": "https://github.com/cornflourblue/node-mongo-signup-verification-api",
        "description": "Express + MongoDB API with Email Verification, JWT authentication, and Role-based authorization.",
        "tags": ["Node.js", "Express", "MongoDB", "Auth", "JWT"],
    },
    {
        "key": "golang-gin-realworld",
        "name": "Go Gin RealWorld Example App",
        "url": "https://github.com/gothinkster/golang-gin-realworld-example-app",
        "description": "Exemplary Go backend API with Gin, GORM, JWT Auth, and clean architecture.",
        "tags": ["Go", "Gin", "GORM", "JWT", "REST API"],
    },
]


@router.get("/samples")
async def get_sample_repositories():
    """Returns a list of curated sample repositories for testing."""
    return {"samples": SAMPLE_REPOS}


@router.post("/ingest")
async def ingest_repository(payload: IngestRequest):
    """
    Ingests, filters, indexes a GitHub repo or local path,
    and returns its architecture overview, file tree, and metrics.
    """
    repo_path: Optional[Path] = None
    repo_id: str = ""
    source_url: str = ""

    try:
        if payload.sample_key:
            sample = next((s for s in SAMPLE_REPOS if s["key"] == payload.sample_key), None)
            if not sample:
                raise HTTPException(status_code=404, detail="Sample repository not found")
            source_url = sample["url"]
            repo_path = clone_github_repo(source_url)
            repo_id = sanitize_repo_name(source_url)
        elif payload.repo_url:
            source_url = payload.repo_url.strip()
            # If user pasted sample key into url input
            sample = next((s for s in SAMPLE_REPOS if s["key"] == source_url or s["url"] == source_url), None)
            if sample:
                source_url = sample["url"]
            repo_path = clone_github_repo(source_url)
            repo_id = sanitize_repo_name(source_url)
        elif payload.local_path:
            local = Path(payload.local_path)
            if not local.exists() or not local.is_dir():
                raise HTTPException(status_code=400, detail=f"Local path '{payload.local_path}' does not exist.")
            repo_path = local
            repo_id = sanitize_repo_name(local.name)
            source_url = str(local)
        else:
            raise HTTPException(status_code=400, detail="Please provide a repo_url, sample_key, or local_path.")

        # 1. Scan and filter files
        scan_data = scan_repository(repo_path)

        if scan_data["total_files"] == 0:
            raise HTTPException(status_code=400, detail="No readable code files found in the specified repository.")

        # 2. Build hierarchical file tree & module categorization
        file_tree = build_file_tree(scan_data["files"])
        modules = extract_architecture_modules(scan_data["files"])

        # 3. Chunk files & index in Vector Store
        chunks = chunk_all_files(scan_data["files"])
        vector_store = get_or_create_vector_store(repo_id)
        vector_store.index_chunks(chunks)

        # 4. Generate high-level architecture overview & Mermaid diagram
        arch_overview = llm_service.generate_architecture_overview(
            repo_name=scan_data["repo_name"],
            modules=modules,
            total_loc=scan_data["total_loc"],
            languages=scan_data["languages"],
        )

        # 5. Generate starter questions
        suggested_questions = llm_service.suggest_questions(modules)

        # Cache repository metadata
        REPO_CACHE[repo_id] = {
            "repo_id": repo_id,
            "repo_name": scan_data["repo_name"],
            "source_url": source_url,
            "scan_data": scan_data,
            "file_tree": file_tree,
            "modules": modules,
            "architecture": arch_overview,
            "suggested_questions": suggested_questions,
            "total_chunks": len(chunks),
            "files_by_path": {f["path"]: f for f in scan_data["files"]},
        }

        return {
            "status": "success",
            "repo_id": repo_id,
            "repo_name": scan_data["repo_name"],
            "source_url": source_url,
            "total_files": scan_data["total_files"],
            "total_loc": scan_data["total_loc"],
            "total_chunks": len(chunks),
            "languages": scan_data["languages"],
            "architecture": arch_overview,
            "file_tree": file_tree,
            "module_summary": {k: len(v) for k, v in modules.items()},
            "suggested_questions": suggested_questions,
            "ai_provider": llm_service.active_provider,
        }

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process repository: {str(e)}")


@router.get("/{repo_id}/tree")
async def get_repo_tree(repo_id: str):
    """Returns the file tree for an ingested repository."""
    if repo_id not in REPO_CACHE:
        raise HTTPException(status_code=404, detail="Repository not found or not yet ingested.")
    return {
        "repo_id": repo_id,
        "file_tree": REPO_CACHE[repo_id]["file_tree"],
        "modules": {k: len(v) for k, v in REPO_CACHE[repo_id]["modules"].items()},
    }


@router.get("/{repo_id}/architecture")
async def get_repo_architecture(repo_id: str):
    """Returns the architecture overview and Mermaid diagram."""
    if repo_id not in REPO_CACHE:
        raise HTTPException(status_code=404, detail="Repository not found or not yet ingested.")
    return REPO_CACHE[repo_id]["architecture"]


@router.get("/{repo_id}/file")
async def get_file_content(repo_id: str, path: str = Query(..., description="Relative file path")):
    """Returns file content for the in-app code viewer with traversal prevention."""
    if repo_id not in REPO_CACHE:
        raise HTTPException(status_code=404, detail="Repository not found.")
    
    normalized_path = path.replace("\\", "/").strip("/")
    if ".." in normalized_path.split("/") or normalized_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid file path.")

    file_map = REPO_CACHE[repo_id]["files_by_path"]
    
    if normalized_path not in file_map:
        raise HTTPException(status_code=404, detail=f"File '{path}' not found in repository index.")

    file_info = file_map[normalized_path]
    return {
        "path": file_info["path"],
        "name": file_info["name"],
        "language": file_info["language"],
        "loc": file_info["loc"],
        "size_kb": file_info["size_kb"],
        "content": file_info["content"],
    }
