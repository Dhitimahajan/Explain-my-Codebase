import re
from typing import List, Dict, Any

# Regex patterns for detecting function and class boundaries across languages
SYMBOL_PATTERNS = [
    # Python
    (r"^(?:async\s+)?def\s+([a-zA-Z0-9_]+)\s*\(", "function"),
    (r"^class\s+([a-zA-Z0-9_]+)", "class"),
    # JavaScript / TypeScript
    (r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)", "function"),
    (r"^(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", "function"),
    (r"^(?:export\s+)?(?:default\s+)?class\s+([a-zA-Z0-9_]+)", "class"),
    (r"^(?:export\s+)?interface\s+([a-zA-Z0-9_]+)", "interface"),
    (r"^(?:export\s+)?type\s+([a-zA-Z0-9_]+)\s*=", "type"),
    # Go
    (r"^func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(", "function"),
    (r"^type\s+([a-zA-Z0-9_]+)\s+struct", "struct"),
    # Rust
    (r"^(?:pub\s+)?(?:async\s+)?fn\s+([a-zA-Z0-9_]+)", "function"),
    (r"^(?:pub\s+)?(?:struct|enum|trait)\s+([a-zA-Z0-9_]+)", "struct"),
    # Java / C# / C++
    (r"^(?:public|private|protected|static|final|native|synchronized|abstract|\s)+[\w<>\[\]]+\s+([a-zA-Z0-9_]+)\s*\(", "method"),
    (r"^(?:public|private|protected)?\s*(?:class|struct)\s+([a-zA-Z0-9_]+)", "class"),
    # API route handlers (Express, FastAPI, Flask, Gin)
    (r"@(app|router|api)\.(get|post|put|delete|patch|options|route)\s*\(\s*[\"']([^\"']+)[\"']", "route"),
    (r"(?:router|app)\.(get|post|put|delete|patch|use)\s*\(\s*[\"']([^\"']+)[\"']", "route"),
]


def detect_symbol(line: str) -> str:
    """Detects if a line defines a key class, function, or route."""
    stripped = line.strip()
    for pattern, kind in SYMBOL_PATTERNS:
        match = re.search(pattern, stripped)
        if match:
            if kind == "route":
                return f"Route: {match.group(0)}"
            return f"{kind.capitalize()}: {match.group(1)}"
    return ""


def chunk_code_file(
    file_info: Dict[str, Any],
    max_lines_per_chunk: int = 60,
    overlap_lines: int = 10
) -> List[Dict[str, Any]]:
    """
    Chunks code files intelligently preserving function/class context and line numbers.
    """
    content = file_info.get("content", "")
    lines = content.splitlines()
    total_lines = len(lines)
    file_path = file_info.get("path", "")
    language = file_info.get("language", "")

    if total_lines == 0:
        return []

    # If small file, return single chunk
    if total_lines <= max_lines_per_chunk + 15:
        return [{
            "chunk_id": f"{file_path}:1-{total_lines}",
            "file_path": file_path,
            "language": language,
            "start_line": 1,
            "end_line": total_lines,
            "symbol": detect_symbol(lines[0]) if lines else "",
            "content": content,
            "preview": f"File {file_path} (Lines 1-{total_lines})",
        }]

    chunks: List[Dict[str, Any]] = []
    current_start = 0

    while current_start < total_lines:
        current_end = min(current_start + max_lines_per_chunk, total_lines)

        # Try to find natural boundary if we're not at the very end
        if current_end < total_lines:
            lookahead_range = range(current_end, max(current_start + 20, current_end - 15), -1)
            for candidate_line in lookahead_range:
                if candidate_line < len(lines):
                    line_text = lines[candidate_line].strip()
                    if line_text == "" or line_text.startswith(("#", "//", "/*", "*/", "def ", "class ", "func ", "export ")):
                        current_end = candidate_line
                        break

        chunk_lines = lines[current_start:current_end]
        chunk_content = "\n".join(chunk_lines)

        # Detect primary symbols inside this chunk
        detected_symbols = []
        for line in chunk_lines:
            sym = detect_symbol(line)
            if sym and sym not in detected_symbols:
                detected_symbols.append(sym)

        primary_symbol = ", ".join(detected_symbols[:2]) if detected_symbols else "Module Code"

        start_line_1idx = current_start + 1
        end_line_1idx = current_end

        chunks.append({
            "chunk_id": f"{file_path}:{start_line_1idx}-{end_line_1idx}",
            "file_path": file_path,
            "language": language,
            "start_line": start_line_1idx,
            "end_line": end_line_1idx,
            "symbol": primary_symbol,
            "content": chunk_content,
            "preview": f"{file_path}:{start_line_1idx}-{end_line_1idx} ({primary_symbol})",
        })

        if current_end >= total_lines:
            break

        # Step forward with overlap
        current_start = max(current_start + 1, current_end - overlap_lines)

    return chunks


def chunk_all_files(code_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chunks all scanned repository code files."""
    all_chunks: List[Dict[str, Any]] = []
    for file in code_files:
        chunks = chunk_code_file(file)
        all_chunks.extend(chunks)
    return all_chunks
