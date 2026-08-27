import sys
import io
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add backend directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.ingester import scan_repository
from app.core.tree_builder import build_file_tree, extract_architecture_modules
from app.core.chunker import chunk_all_files
from app.core.vector_store import CodeVectorStore
from app.core.llm_service import llm_service

def test_full_pipeline():
    print("🧪 Running Explain My Codebase Verification Pipeline...")
    
    # 1. Test scanning current backend directory
    print("\n1. Testing Ingestion & File Scanning...")
    scan_data = scan_repository(BASE_DIR)
    assert scan_data["total_files"] > 0, "No files scanned"
    assert scan_data["total_loc"] > 0, "No LOC counted"
    print(f"   ✅ Scanned {scan_data['total_files']} files ({scan_data['total_loc']} total LOC)")
    print(f"   ✅ Detected languages: {[l['language'] for l in scan_data['languages']]}")

    # 2. Test tree builder & module classification
    print("\n2. Testing Tree Builder & Module Categorization...")
    tree = build_file_tree(scan_data["files"])
    assert tree["type"] == "directory", "Tree root is not a directory"
    modules = extract_architecture_modules(scan_data["files"])
    assert len(modules) > 0, "No architectural modules identified"
    print(f"   ✅ Generated tree hierarchy (Root: {tree['name']}, {tree['loc']} LOC)")
    for mod, files in modules.items():
        print(f"      - {mod}: {len(files)} files")

    # 3. Test code chunker
    print("\n3. Testing Code Chunker & AST Symbol Detection...")
    chunks = chunk_all_files(scan_data["files"])
    assert len(chunks) > 0, "No chunks produced"
    print(f"   ✅ Created {len(chunks)} code chunks with boundary tags")
    sample_chunk = chunks[0]
    print(f"   ✅ Sample chunk: {sample_chunk['preview']}")

    # 4. Test Hybrid Vector Store & Search
    print("\n4. Testing Hybrid Vector Store Indexing & Retrieval...")
    store = CodeVectorStore("test_repo")
    store.index_chunks(chunks)
    
    # Query for vector store / RAG / routes
    results = store.search("authentication or database routes", top_k=3)
    assert len(results) > 0, "No search results returned"
    print(f"   ✅ Search retrieved {len(results)} relevant chunks:")
    for r in results:
        print(f"      - [{r['file_path']}:{r['start_line']}-{r['end_line']}] (Score: {r['relevance_score']})")

    # 5. Test LLM Service & Architecture Synthesis
    print("\n5. Testing Architecture Overview & RAG Synthesis...")
    arch = llm_service.generate_architecture_overview(
        repo_name="TestCodebase",
        modules=modules,
        total_loc=scan_data["total_loc"],
        languages=scan_data["languages"]
    )
    assert "mermaid_diagram" in arch, "Mermaid diagram missing"
    print(f"   ✅ Architecture Title: {arch['title']}")
    print(f"   ✅ Mermaid Graph generated:\n{arch['mermaid_diagram'][:120]}...")

    # 6. Test Query Answering
    ans = llm_service.answer_query(
        query="Where does vector search happen?",
        retrieved_chunks=results,
        repo_name="ExplainMyCodebase",
        modules=modules
    )
    assert "answer" in ans, "Answer missing"
    assert len(ans["citations"]) > 0, "Citations missing"
    print(f"\n   ✅ Query Answering tested successfully (Provider: {ans['provider']})")
    print(f"   ✅ Citations count: {len(ans['citations'])}")

    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_full_pipeline()
