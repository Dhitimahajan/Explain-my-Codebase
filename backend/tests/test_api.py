import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.main import app
from app.api.routes_repo import REPO_CACHE

client = TestClient(app)

def test_root_route():
    """Verify root route returns 200 and serves HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Explain My Codebase" in response.text

def test_system_status():
    """Verify /api/status returns healthy and correct app name."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "Explain My Codebase"
    assert "ai_provider" in data

def test_samples_endpoint():
    """Verify /api/repo/samples returns curated repositories."""
    response = client.get("/api/repo/samples")
    assert response.status_code == 200
    samples = response.json().get("samples", [])
    assert len(samples) >= 3
    sample_keys = [s["key"] for s in samples]
    assert "fastapi-realworld" in sample_keys

def test_invalid_repo_url_rejected():
    """Verify invalid and malicious repository URLs are rejected."""
    # Test invalid scheme
    res1 = client.post("/api/repo/ingest", json={"repo_url": "ftp://malicious.com/repo"})
    assert res1.status_code in (400, 500)

    # Test SSRF attempt
    res2 = client.post("/api/repo/ingest", json={"repo_url": "http://169.254.169.254/secret"})
    assert res2.status_code in (400, 500)

def test_local_path_ingest_and_chat():
    """Verify complete ingestion and chat on local backend code."""
    res = client.post("/api/repo/ingest", json={"local_path": str(BASE_DIR)})
    assert res.status_code == 200
    data = res.json()
    repo_id = data["repo_id"]
    assert data["status"] == "success"
    assert data["total_files"] > 0
    assert "architecture" in data
    assert "file_tree" in data

    # Test file retrieval endpoint
    sample_file = list(REPO_CACHE[repo_id]["files_by_path"].keys())[0]
    file_res = client.get(f"/api/repo/{repo_id}/file?path={sample_file}")
    assert file_res.status_code == 200
    assert "content" in file_res.json()

    # Test path traversal prevention
    bad_res = client.get(f"/api/repo/{repo_id}/file?path=../../../../etc/passwd")
    assert bad_res.status_code == 404

    # Test AI Chat query endpoint
    chat_res = client.post("/api/chat/query", json={
        "repo_id": repo_id,
        "query": "Where are API routes defined?"
    })
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "answer" in chat_data
    assert len(chat_data["citations"]) > 0

if __name__ == "__main__":
    pytest.main(["-v", __file__])
