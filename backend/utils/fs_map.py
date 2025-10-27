import os
from pathlib import Path
from typing import Dict, List

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


def _classify(path: Path) -> Dict:
    ext = path.suffix.lower()
    if ext in _CODE_EXTS:
        return {"path": str(path), "type": "CodeFile", "language": _CODE_EXTS[ext]}
    if ext in _DOC_EXTS:
        return {"path": str(path), "type": "Doc", "language": _DOC_EXTS[ext]}
    return {"path": str(path), "type": "Other", "language": ext.lstrip(".")}


def scan_repo_tree(root_path: str) -> List[Dict]:
    root = Path(root_path).resolve()
    out: List[Dict] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            p = Path(dirpath) / fname
            rel = p.relative_to(root)
            meta = _classify(rel)
            out.append(meta)
    return out

