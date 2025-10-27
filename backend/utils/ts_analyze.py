import re
from pathlib import Path
from typing import Dict, List

# Optional tree-sitter support via tree_sitter_languages (if installed)
try:
    from tree_sitter_languages import get_parser  # type: ignore
except Exception:  # pragma: no cover
    get_parser = None


_FUNC_RE = re.compile(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_CLASS_RE = re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b")


def _naive_extract(path: Path, language: str) -> Dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    funcs = _FUNC_RE.findall(text)
    classes = _CLASS_RE.findall(text)
    return {"file": str(path), "language": language, "functions": funcs, "classes": classes}


def _ts_extract(path: Path, language: str) -> Dict:
    # Minimal tree-sitter example: if parser exists for language, build tree
    # For brevity, we still return naive results; extend here for real TS queries
    return _naive_extract(path, language)


def extract_entities(repo_root: str, file_tree: List[Dict]) -> Dict:
    root = Path(repo_root).resolve()
    results: List[Dict] = []
    for item in file_tree:
        if item.get("type") != "CodeFile":
            continue
        language = item.get("language", "")
        rel_path = item.get("path")
        file_path = (root / rel_path).resolve()
        if not file_path.exists():
            continue
        if get_parser is not None:
            results.append(_ts_extract(file_path, language))
        else:
            results.append(_naive_extract(file_path, language))
    return {"files": results}

