import os
import re
import stat
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from app.config import REPOS_DIR

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

# Directories to skip completely for high speed
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

MAX_FILES_TO_SCAN = 250
MAX_FILE_SIZE_KB = 150  # source code files are almost always < 150KB


def _remove_readonly(func, path, excinfo):
    """Windows-safe error handler for read-only git files."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def safe_delete_tree(path: Path):
    """Safely deletes a directory tree even if it contains read-only git files."""
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


def validate_github_url(repo_url: str) -> str:
    """Validates and normalizes GitHub repository URLs safely."""
    raw = repo_url.strip()
    if raw.startswith("-"):
        raise ValueError("Invalid repository URL format.")
    
    # Allow shorthand 'owner/repo'
    if re.match(r"^[a-zA-Z0-9_\-\.]+\/[a-zA-Z0-9_\-\.]+$", raw):
        return f"https://github.com/{raw}"

    parsed = re.match(r"^https?:\/\/(?:www\.)?github\.com\/([a-zA-Z0-9_\-\.]+)\/([a-zA-Z0-9_\-\.]+?)(?:\.git|\/)?$", raw)
    if not parsed:
        raise ValueError("Please provide a valid public GitHub URL (e.g., https://github.com/owner/repository).")

    owner, repo = parsed.group(1), parsed.group(2)
    return f"https://github.com/{owner}/{repo}"


def clone_github_repo(repo_url: str) -> Path:
    """Clones a GitHub repository shallowly and quickly (--depth 1, --no-tags)."""
    clean_url = validate_github_url(repo_url)

    repo_id = sanitize_repo_name(clean_url)
    target_dir = REPOS_DIR / repo_id

    # If already cloned recently and has files, return immediately
    if target_dir.exists() and any(target_dir.iterdir()):
        return target_dir

    safe_delete_tree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    git_url = f"{clean_url}.git" if not clean_url.endswith(".git") else clean_url
    git_env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    cmd = [
        "git", "clone",
        "--depth", "1",
        "--single-branch",
        "--no-tags",
        git_url,
        str(target_dir)
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, env=git_env, timeout=30)
        if res.returncode != 0:
            if git_url != clean_url:
                cmd2 = ["git", "clone", "--depth", "1", "--single-branch", "--no-tags", clean_url, str(target_dir)]
                res2 = subprocess.run(cmd2, capture_output=True, text=True, env=git_env, timeout=30)
                if res2.returncode != 0:
                    raise RuntimeError(f"Git clone failed: {res2.stderr or res.stderr}")
            else:
                raise RuntimeError(f"Git clone failed: {res.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Git clone timed out after 30 seconds. Please check the repository URL or connection.")

    return target_dir


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
