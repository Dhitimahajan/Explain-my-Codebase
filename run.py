import os
import sys
import io
import socket
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

def get_local_ip():
    """Gets the laptop's local WiFi/network IP address for mobile access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

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

    local_ip = get_local_ip()
    local_url = f"http://127.0.0.1:{PORT}"
    mobile_url = f"http://{local_ip}:{PORT}"

    print("=" * 65)
    print(f"💻 LOCAL BROWSER LINK:  {local_url}")
    print(f"📱 NETWORK / MOBILE:   {mobile_url}")
    print("   (Ensure your devices are connected to the same Wi-Fi network)")
    print("=" * 65)
    print("Press Ctrl+C to stop the server.\n")

    # Try opening browser after 1.2 seconds on laptop
    try:
        import threading
        def open_browser():
            import time
            time.sleep(1.2)
            webbrowser.open(local_url)
        threading.Thread(target=open_browser, daemon=True).start()
    except Exception:
        pass

    # Start FastAPI with Uvicorn on 0.0.0.0 so network can access it
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True, app_dir=str(BACKEND_DIR))

if __name__ == "__main__":
    main()
