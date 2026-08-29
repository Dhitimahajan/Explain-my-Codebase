import sys
import io
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.ingester import clone_github_repo, scan_repository
from app.core.tree_builder import build_file_tree, extract_architecture_modules
from app.core.chunker import chunk_all_files
from app.core.vector_store import get_or_create_vector_store
from app.core.llm_service import llm_service

def benchmark():
    url = "https://github.com/nsidnev/fastapi-realworld-example-app"
    print(f"🚀 Benchmarking ingestion speed for: {url}")
    
    t0 = time.time()
    repo_path = clone_github_repo(url)
    t_clone = time.time() - t0
    print(f"   ⏱️ Cloned in {t_clone:.2f} seconds")

    t1 = time.time()
    scan_data = scan_repository(repo_path)
    t_scan = time.time() - t1
    print(f"   ⏱️ Scanned {scan_data['total_files']} files ({scan_data['total_loc']} LOC) in {t_scan:.3f} seconds")

    t2 = time.time()
    tree = build_file_tree(scan_data["files"])
    modules = extract_architecture_modules(scan_data["files"])
    chunks = chunk_all_files(scan_data["files"])
    store = get_or_create_vector_store("fastapi-benchmark")
    store.index_chunks(chunks)
    t_index = time.time() - t2
    print(f"   ⏱️ Tree built, {len(chunks)} chunks created & indexed in {t_index:.3f} seconds")

    t3 = time.time()
    arch = llm_service.generate_architecture_overview(
        scan_data["repo_name"], modules, scan_data["total_loc"], scan_data["languages"]
    )
    t_arch = time.time() - t3
    print(f"   ⏱️ Architecture synthesized in {t_arch:.3f} seconds")

    total_time = time.time() - t0
    print(f"\n🎉 FULL PIPELINE COMPLETED IN {total_time:.2f} SECONDS TOTAL!")

if __name__ == "__main__":
    benchmark()
