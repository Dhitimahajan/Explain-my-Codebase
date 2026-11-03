import io
import os
import re
import stat
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import requests

from app.config import REPOS_DIR, MAX_REPO_SIZE_MB

# Extensions recognized by language category
LANGUAGE_MAP = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".sql": "SQL",
    ".graphql": "GraphQL",
    ".gql": "GraphQL",
    ".prisma": "Prisma Schema",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".sh": "Shell Script",
    ".dockerfile": "Dockerfile",
}

# Directories to skip completely for high speed and security
IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", "out", ".next", ".nuxt", "__pycache__",
    ".venv", "venv", "env", ".pytest_cache", ".idea", ".vscode", "target",
    "bin", "obj", "vendor", ".turbo", ".husky", ".cargo", "coverage", ".cache",
    "docs", "documentation", "site", "fixtures", "tests/fixtures", "test_data",
    "testdata", "datasets", "tmp", "temp", "third_party", "pods", "site-packages"
}

IGNORED_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "pipfile.lock", "cargo.lock", "go.sum", "composer.lock"
}

IGNORED_EXTENSIONS = {
    ".min.js", ".min.css", ".map", ".png", ".jpg", ".jpeg", ".gif",
    ".svg", ".ico", ".webp", ".pdf", ".zip", ".tar", ".gz", ".exe",
    ".dll", ".so", ".dylib", ".woff", ".woff2", ".ttf", ".eot",
    ".mp4", ".mp3", ".mov", ".avi", ".pyc", ".pyo", ".pyd", ".class",
    ".jar", ".war", ".lock", ".csv", ".tsv", ".parquet", ".db", ".sqlite"
}

MAX_FILES_TO_SCAN = 300
MAX_FILE_SIZE_KB = 250  # Source code files are almost always < 250KB


def _remove_readonly(func, path, excinfo):
    """Windows-safe error handler for read-only files."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def safe_delete_tree(path: Path):
    """Safely deletes a directory tree even if it contains read-only files."""
    if path.exists():
        try:
            shutil.rmtree(path, onerror=_remove_readonly)
        except Exception:
            try:
                shutil.rmtree(path, ignore_errors=True)
            except Exception:
                pass


def sanitize_repo_name(url_or_name: str) -> str:
    """Creates a filesystem-safe folder name from a repo URL or name."""
    clean = url_or_name.strip().rstrip("/")
    clean = re.sub(r"https?://github\.com/", "", clean)
    clean = re.sub(r"\.git$", "", clean)
    clean = re.sub(r"[^a-zA-Z0-9_\-]", "_", clean)
    return clean or "unknown_repo"


def parse_github_url(repo_url: str) -> Tuple[str, str, str]:
    """
    Validates and normalizes GitHub repository URLs.
    Returns: (normalized_url, owner, repo)
    """
    raw = repo_url.strip()
    if raw.startswith("-"):
        raise ValueError("Invalid repository URL format.")

    # Allow shorthand 'owner/repo'
    if re.match(r"^[a-zA-Z0-9_\-\.]+\/[a-zA-Z0-9_\-\.]+$", raw):
        owner, repo = raw.split("/", 1)
        repo = re.sub(r"\.git$", "", repo)
        return f"https://github.com/{owner}/{repo}", owner, repo

    parsed = re.match(r"^https?:\/\/(?:www\.)?github\.com\/([a-zA-Z0-9_\-\.]+)\/([a-zA-Z0-9_\-\.]+?)(?:\.git|\/)?$", raw)
    if not parsed:
        raise ValueError("Please provide a valid public GitHub URL (e.g. https://github.com/owner/repository).")

    owner, repo = parsed.group(1), parsed.group(2)
    return f"https://github.com/{owner}/{repo}", owner, repo


def validate_github_url(repo_url: str) -> str:
    """Convenience helper returning just the validated GitHub URL."""
    url, _, _ = parse_github_url(repo_url)
    return url


def download_github_zip(owner: str, repo: str, target_dir: Path) -> Path:
    """
    Downloads repository source code as a ZIP archive without requiring a Git executable.
    Compatible with Vercel serverless functions, Docker, and local machines.
    """
    download_urls = [
        f"https://github.com/{owner}/{repo}/archive/HEAD.zip",
        f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/main",
        f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/master",
    ]

    headers = {
        "User-Agent": "ExplainMyCodebase/1.0",
        "Accept": "application/vnd.github.v3+json, application/zip, */*",
    }
    github_token = os.getenv("GITHUB_TOKEN", "").strip()
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    session = requests.Session()
    response = None
    last_error = None

    for url in download_urls:
        try:
            resp = session.get(url, headers=headers, stream=True, timeout=25, allow_redirects=True)
            if resp.status_code == 200:
                response = resp
                break
            elif resp.status_code == 404:
                last_error = f"Repository '{owner}/{repo}' not found on GitHub. Please check that the URL is correct and the repository is public."
            elif resp.status_code == 403:
                last_error = "GitHub access was rate-limited or forbidden. Please wait a few minutes or provide a GITHUB_TOKEN."
            else:
                last_error = f"GitHub returned HTTP status {resp.status_code} while fetching archive."
        except requests.exceptions.Timeout:
            last_error = f"Connection to GitHub timed out while downloading '{owner}/{repo}'."
        except requests.exceptions.RequestException as e:
            last_error = f"Network error connecting to GitHub: {str(e)}"

    if response is None:
        raise ValueError(last_error or f"Failed to download repository '{owner}/{repo}'.")

    # Read stream with size limit check
    max_bytes = MAX_REPO_SIZE_MB * 1024 * 1024
    total_bytes = 0
    buffer = io.BytesIO()

    try:
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise ValueError(f"Repository exceeds the maximum allowed size limit of {MAX_REPO_SIZE_MB}MB.")
                buffer.write(chunk)
    finally:
        response.close()

    buffer.seek(0)

    # Safely extract ZIP archive
    try:
        zf = zipfile.ZipFile(buffer)
    except zipfile.BadZipFile:
        raise ValueError(f"Failed to unpack repository archive for '{owner}/{repo}'. The archive may be corrupted or invalid.")

    # Guard against zip-bomb decompression attacks
    uncompressed_size = sum(m.file_size for m in zf.infolist())
    if uncompressed_size > max_bytes * 4:
        raise ValueError("Security check failed: uncompressed repository contents exceed safe storage limit.")

    top_dir = None
    for name in zf.namelist():
        parts = name.split("/")
        if parts[0]:
            top_dir = parts[0] + "/"
            break

    target_dir_resolved = target_dir.resolve()

    # Extract all files safely
    for member in zf.infolist():
        rel_path = member.filename
        if top_dir and rel_path.startswith(top_dir):
            rel_path = rel_path[len(top_dir):]

        if not rel_path or rel_path.endswith("/"):
            continue

        # Prevent Path Traversal (Zip Slip vulnerability)
        out_file = (target_dir / rel_path).resolve()
        if not str(out_file).startswith(str(target_dir_resolved)):
            raise ValueError(f"Security error: ZIP archive contains illegal traversal path '{member.filename}'.")

        out_file.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member) as src, open(out_file, "wb") as dst:
            shutil.copyfileobj(src, dst)

    return target_dir


def clone_github_repo(repo_url: str) -> Path:
    """
    Ingests a GitHub repository.
    Uses pure-Python HTTPS archive streaming first (100% Vercel & serverless compatible without Git).
    Falls back to shallow git clone only if git executable is locally installed.
    """
    clean_url, owner, repo = parse_github_url(repo_url)
    repo_id = sanitize_repo_name(clean_url)
    target_dir = REPOS_DIR / repo_id

    # If already cloned/downloaded recently and has files, return cached target
    if target_dir.exists() and any(target_dir.iterdir()):
        return target_dir

    safe_delete_tree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Primary method: Zero-dependency HTTPS Archive Download (Works on Vercel)
    try:
        return download_github_zip(owner, repo, target_dir)
    except Exception as zip_err:
        # 2. Secondary fallback: Git CLI (only if git executable actually exists locally)
        git_path = shutil.which("git")
        if git_path:
            try:
                safe_delete_tree(target_dir)
                target_dir.mkdir(parents=True, exist_ok=True)
                git_url = f"{clean_url}.git"
                git_env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
                cmd = ["git", "clone", "--depth", "1", "--single-branch", "--no-tags", git_url, str(target_dir)]
                res = subprocess.run(cmd, capture_output=True, text=True, env=git_env, timeout=30)
                if res.returncode == 0:
                    return target_dir
            except Exception:
                pass

        # If both fail or git is not present, raise the clear zip_err
        safe_delete_tree(target_dir)
        raise ValueError(str(zip_err))


def scan_repository(repo_path: Path) -> Dict[str, Any]:
    """
    Scans repository directory quickly, prioritizing source code files.
    """
    code_files: List[Dict[str, Any]] = []
    language_counts: Dict[str, int] = {}
    total_loc = 0

    for root, dirs, files in os.walk(repo_path):
        # In-place filter ignored directories
        dirs[:] = [
            d for d in dirs 
            if d.lower() not in IGNORED_DIRS and not d.startswith(".")
        ]

        for file_name in files:
            if len(code_files) >= MAX_FILES_TO_SCAN:
                break

            lower_name = file_name.lower()
            if lower_name in IGNORED_FILES or (file_name.startswith(".") and file_name not in (".env.example", ".dockerignore", ".gitignore")):
                continue

            # Check ignored extensions
            if any(lower_name.endswith(ext) for ext in IGNORED_EXTENSIONS):
                continue

            full_path = Path(root) / file_name
            try:
                file_size_kb = full_path.stat().st_size / 1024
                if file_size_kb > MAX_FILE_SIZE_KB:
                    continue  # skip massive files

                # Detect extension / language
                ext = full_path.suffix.lower()
                if lower_name == "dockerfile":
                    ext = ".dockerfile"
                elif lower_name == "makefile":
                    ext = ".sh"
                elif lower_name.startswith("readme"):
                    ext = ".md"
                elif lower_name in ("license", "licence"):
                    ext = ".txt"

                language = LANGUAGE_MAP.get(ext, "Other")
                if language == "Other" and ext not in (".md", ".txt", ".env"):
                    continue

                rel_path = full_path.relative_to(repo_path).as_posix()

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue

                lines = content.splitlines()
                loc = len(lines)
                total_loc += loc

                language_counts[language] = language_counts.get(language, 0) + loc

                code_files.append({
                    "path": rel_path,
                    "name": file_name,
                    "language": language,
                    "extension": ext,
                    "loc": loc,
                    "size_kb": round(file_size_kb, 2),
                    "content": content,
                })
            except Exception:
                continue

        if len(code_files) >= MAX_FILES_TO_SCAN:
            break

    # Sort files alphabetically by path
    code_files.sort(key=lambda x: x["path"])

    # Calculate language percentages
    lang_distribution = []
    if total_loc > 0:
        for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
            pct = round((count / total_loc) * 100, 1)
            if pct > 0:
                lang_distribution.append({"language": lang, "loc": count, "percentage": pct})

    return {
        "repo_name": repo_path.name,
        "repo_path": str(repo_path),
        "total_files": len(code_files),
        "total_loc": total_loc,
        "languages": lang_distribution,
        "files": code_files,
    }
