import os
import sys
import io
import webbrowser
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add backend directory to Python sys.path
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

def main():
    print("=" * 65)
    print("  🧠 EXPLAIN MY CODEBASE — AI Architecture Visualizer & Copilot")
    print("=" * 65)
    print(f"📁 Project Root: {BASE_DIR}")
    print(f"📦 Backend Path: {BACKEND_DIR}")
    
    try:
        import uvicorn
        from app.config import HOST, PORT
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)

    url = f"http://{HOST}:{PORT}"
    print(f"🚀 Starting server at: {url}")
    print("Press Ctrl+C to stop the server.")
    print("=" * 65)

    # Try opening browser after 1.2 seconds
    try:
        import threading
        def open_browser():
            import time
            time.sleep(1.2)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()
    except Exception:
        pass

    # Start FastAPI with Uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True, app_dir=str(BACKEND_DIR))

if __name__ == "__main__":
    main()
