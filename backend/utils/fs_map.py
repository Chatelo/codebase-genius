import os
from pathlib import Path
from typing import Dict, List, Optional

_CODE_EXTS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c-header",
    ".jac": "jac",
}

_DOC_EXTS = {".md": "md", ".rst": "rst"}

# Common directories to exclude from scanning (non-source, caches, VCS, envs)
EXCLUDE_DIRS = {
    ".git",
    ".github",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".cache",
    "node_modules",
    ".venv",
    "venv",
    ".tox",
    "dist",
    "build",
    "site-packages",
    ".idea",
    ".vscode",
    ".eggs",
    ".svn",
    ".hg",
    "coverage",
    "htmlcov",
    "target",
}



def _classify(path: Path) -> Dict:
    ext = path.suffix.lower()
    if ext in _CODE_EXTS:
        return {"path": str(path), "type": "CodeFile", "language": _CODE_EXTS[ext]}
    if ext in _DOC_EXTS:
        return {"path": str(path), "type": "Doc", "language": _DOC_EXTS[ext]}
    return {"path": str(path), "type": "Other", "language": ext.lstrip(".")}


def scan_repo_tree(root_path: str, exclude_dirs: Optional[List[str]] = None) -> List[Dict]:
    root = Path(root_path).resolve()
    out: List[Dict] = []
    final_excludes = set(EXCLUDE_DIRS)
    if exclude_dirs:
        final_excludes.update(exclude_dirs)
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Exclude common non-source directories (by directory name)
        dirnames[:] = [d for d in dirnames if d not in final_excludes]
        for fname in filenames:
            p = Path(dirpath) / fname
            rel = p.relative_to(root)
            meta = _classify(rel)
            out.append(meta)
    return out

