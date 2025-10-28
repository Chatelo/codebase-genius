import os
import re
import hashlib
from pathlib import Path
from typing import Optional

try:
    from git import Repo  # type: ignore
except Exception:  # pragma: no cover
    Repo = None  # Allows code import without GitPython installed


def _slugify(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip())
    return text.strip("-")


def _cache_dir() -> Path:
    base = Path(__file__).resolve().parent.parent / ".cache" / "repos"
    base.mkdir(parents=True, exist_ok=True)
    return base


def clone_or_open_repo(repo_url: str) -> str:
    """
    Clone a remote repo if needed, or open a local path.

    - If repo_url points to an existing local directory, just return it.
    - Else, clone into a cache directory under backend/.cache/repos/<slug>.
    - Requires GitPython at runtime for cloning; if unavailable, raises RuntimeError.
    """
    p = Path(repo_url)
    if p.exists() and p.is_dir():
        return str(p.resolve())

    # Validate common remote URL mistakes (GitHub org URL without repo)
    url = repo_url.strip()
    if url.startswith("http://") or url.startswith("https://"):
        gh_org_only = re.match(r"^https?://github\.com/[^/]+/?$", url.rstrip('/'))
        if gh_org_only:
            raise RuntimeError(
                "Invalid GitHub URL: points to a user/org, not a repository. "
                "Use https://github.com/<owner>/<repo>"
            )

    # Remote URL path
    slug = _slugify(repo_url)
    hashed = hashlib.sha1(repo_url.encode()).hexdigest()[:10]
    target = _cache_dir() / f"{slug}-{hashed}"

    if target.exists():
        # Repo already cloned
        return str(target.resolve())

    if Repo is None:
        raise RuntimeError(
            "GitPython is not available. Please install deps with: uv sync"
        )

    # Clone with basic error handling
    try:
        Repo.clone_from(repo_url, str(target))
    except Exception as e:
        msg = str(e)
        if ("Not Found" in msg) or ("repository not found" in msg.lower()):
            raise RuntimeError(
                f"Repository not found at {repo_url}. Ensure the URL includes both owner and repo (e.g., https://github.com/owner/repo) and is public or accessible."
            )
        raise RuntimeError(f"Failed to clone repository: {repo_url}. {msg}")
    return str(target.resolve())

