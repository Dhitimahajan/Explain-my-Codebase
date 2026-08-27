import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APP_DIR = Path(__file__).resolve().parent

# Load .env from project root if it exists
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Storage paths
REPOS_DIR = BASE_DIR / "data" / "repos"
REPOS_DIR.mkdir(parents=True, exist_ok=True)

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Server Settings
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

# Constraints
MAX_REPO_SIZE_MB = int(os.getenv("MAX_REPO_SIZE_MB", "100"))
MAX_FILE_SIZE_KB = 500  # Skip individual files > 500KB (likely minified or bundles)
MAX_CHUNKS_PER_QUERY = 10
