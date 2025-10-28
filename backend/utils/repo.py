import os
import re
import hashlib
import shutil
import subprocess
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


def _git_available() -> bool:
    return shutil.which("git") is not None


def _cleanup_partial_dir(target: Path) -> None:
    try:
        if target.exists():
            # Remove partially created directory to allow retry
            shutil.rmtree(target)
    except Exception:
        pass


def _clone_via_cli(repo_url: str, target: Path, timeout_s: int) -> None:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"  # avoid interactive prompts
    target.parent.mkdir(parents=True, exist_ok=True)

    # Prefer modern partial+shallow clone to minimize data transfer
    cmd = [
        "git", "clone",
        "--depth=1",
        "--no-tags",
        "--filter=blob:none",
        "--single-branch",
        "--progress",
        "--", repo_url, str(target)
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_s, env=env)
        return
    except subprocess.TimeoutExpired as e:
        _cleanup_partial_dir(target)
        raise RuntimeError(f"Network timeout while cloning {repo_url} (>{timeout_s}s). Please try again or use a smaller depth.")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr or ""
        # Fallback: older git may not support filter=blob:none
        if "filter=blob:none" in stderr or "unknown option" in stderr:
            try:
                cmd_fb = [
                    "git", "clone", "--depth=1", "--no-tags", "--single-branch", "--", repo_url, str(target)
                ]
                subprocess.run(cmd_fb, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_s, env=env)
                return
            except subprocess.TimeoutExpired:
                _cleanup_partial_dir(target)
                raise RuntimeError(f"Network timeout while cloning {repo_url} (>{timeout_s}s). Please try again or use a smaller depth.")
            except subprocess.CalledProcessError as e2:
                _cleanup_partial_dir(target)
                msg2 = e2.stderr or str(e2)
                if ("Not Found" in msg2) or ("repository not found" in msg2.lower()):
                    raise RuntimeError(
                        f"Repository not found at {repo_url}. Ensure the URL includes both owner and repo (e.g., https://github.com/owner/repo) and is public or accessible."
                    )
                raise RuntimeError(f"Failed to clone repository: {repo_url}. {msg2}")
        else:
            _cleanup_partial_dir(target)
            if ("Not Found" in stderr) or ("repository not found" in stderr.lower()):
                raise RuntimeError(
                    f"Repository not found at {repo_url}. Ensure the URL includes both owner and repo (e.g., https://github.com/owner/repo) and is public or accessible."
                )
            raise RuntimeError(f"Failed to clone repository: {repo_url}. {stderr}")


def clone_or_open_repo(repo_url: str) -> str:
    """
    Clone a remote repo if needed, or open a local path.

    - If repo_url points to an existing local directory, just return it.
    - Else, clone into a cache directory under backend/.cache/repos/<slug>.
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

    # Choose timeout; allow override via env
    timeout_s = int(os.environ.get("CBG_GIT_TIMEOUT", "300"))  # default 5 minutes

    # Prefer git CLI for shallow/filtered clones; fallback to GitPython
    if _git_available():
        _clone_via_cli(repo_url, target, timeout_s)
        return str(target.resolve())

    if Repo is None:
        raise RuntimeError(
            "Git is not available and GitPython is not installed. Please install deps or ensure git is on PATH."
        )

    # Fallback: GitPython clone (may be slower, no filtering)
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

