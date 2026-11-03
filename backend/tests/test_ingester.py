import sys
import shutil
import tempfile
from pathlib import Path
import pytest

# Ensure backend directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.ingester import (
    validate_github_url,
    parse_github_url,
    sanitize_repo_name,
    download_github_zip,
    clone_github_repo,
    scan_repository,
)


def test_url_validation_and_parsing():
    """Verify various GitHub URL formats and rejection of malicious inputs."""
    # Standard HTTPS
    url, owner, repo = parse_github_url("https://github.com/fastapi/fastapi")
    assert url == "https://github.com/fastapi/fastapi"
    assert owner == "fastapi"
    assert repo == "fastapi"

    # With .git
    url, owner, repo = parse_github_url("https://github.com/octocat/Hello-World.git")
    assert url == "https://github.com/octocat/Hello-World"
    assert owner == "octocat"
    assert repo == "Hello-World"

    # Shorthand owner/repo
    url, owner, repo = parse_github_url("octocat/Spoon-Knife")
    assert url == "https://github.com/octocat/Spoon-Knife"
    assert owner == "octocat"
    assert repo == "Spoon-Knife"

    # Trailing slash
    url, owner, repo = parse_github_url("https://github.com/octocat/Hello-World/")
    assert url == "https://github.com/octocat/Hello-World"

    # Invalid URLs must raise ValueError
    with pytest.raises(ValueError):
        parse_github_url("https://gitlab.com/user/repo")

    with pytest.raises(ValueError):
        parse_github_url("--upload-pack=evil")

    with pytest.raises(ValueError):
        parse_github_url("http://169.254.169.254/latest/meta-data")


def test_sanitize_repo_name():
    """Verify filesystem-safe repo directory naming."""
    assert sanitize_repo_name("https://github.com/user/repo-name.git") == "user_repo-name"
    assert sanitize_repo_name("octocat/Hello-World") == "octocat_Hello-World"
    assert sanitize_repo_name("../../etc/passwd") == "______etc_passwd"


def test_real_github_zip_download_no_git():
    """Verify real public GitHub repo download and extraction without Git binary."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "test_repo"
        target.mkdir()

        # Ingest public repo octocat/Hello-World via HTTPS archive
        result_dir = download_github_zip("octocat", "Hello-World", target)
        assert result_dir.exists()
        files = list(result_dir.iterdir())
        assert len(files) > 0
        names = [f.name for f in files]
        assert "README" in names

        # Test scanning downloaded files
        scan = scan_repository(result_dir)
        assert scan["total_files"] >= 1


def test_nonexistent_github_repo():
    """Verify clear error message when repository does not exist."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "nonexistent"
        target.mkdir()

        with pytest.raises(ValueError) as excinfo:
            download_github_zip("dhitimahajan_nonexistent_123456", "fake-repo-9999", target)
        assert "not found" in str(excinfo.value).lower() or "failed" in str(excinfo.value).lower()


def test_clone_github_repo_wrapper():
    """Verify clone_github_repo wrapper works end-to-end with real GitHub repo."""
    repo_path = clone_github_repo("https://github.com/octocat/Hello-World")
    assert repo_path.exists()
    assert (repo_path / "README").exists()
