import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from app.config import DEBUG, HOST, PORT
from app.api.routes_repo import router as repo_router, REPO_CACHE
from app.api.routes_chat import router as chat_router
from app.core.llm_service import llm_service

app = FastAPI(
    title="database_finder_bydhiti API",
    description="AI-Powered GitHub Repository Visualizer & Architecture Copilot by Dhiti",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(repo_router)
app.include_router(chat_router)


@app.get("/api/status")
async def get_system_status():
    """Returns the current system health and AI provider configuration."""
    return {
        "status": "healthy",
        "app_name": "database_finder_bydhiti",
        "ai_provider": llm_service.active_provider,
        "is_configured": llm_service.is_configured,
        "cached_repos_count": len(REPO_CACHE),
        "cached_repos": list(REPO_CACHE.keys()),
    }


# Static directory
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def serve_root():
        return RedirectResponse(url="/database_finder_bydhiti")

    @app.get("/database_finder_bydhiti")
    async def serve_custom_endpoint():
        return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting database_finder_bydhiti server on http://{HOST}:{PORT}/database_finder_bydhiti")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=DEBUG)
