from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, Optional


_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_.\-]+")


def _sanitize_name(name: str) -> str:
    # Replace unsafe characters with underscores; collapse runs; strip
    name = _SANITIZE_RE.sub("_", name).strip("_-")
    return name or "repo"


def repo_name_from_url(repo_url: str) -> str:
    """Derive a filesystem-safe repository name from a URL/path.

    Examples:
    - https://github.com/org/project.git -> project
    - git@github.com:org/project.git -> project
    - /local/path/to/repo -> repo
    - org/project -> project
    """
    if not repo_url:
        return "repo"

    # Strip trailing .git
    base = repo_url.rstrip("/")
    if base.endswith(".git"):
        base = base[:-4]

    # Prefer last path segment
    if "/" in base:
        segment = base.split("/")[-1]
    elif ":" in base:  # scp-like syntax git@host:org/repo
        segment = base.split(":")[-1].split("/")[-1]
    else:
        segment = base

    return _sanitize_name(segment) or "repo"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_results_to_disk(
    repo_url: str,
    documentation: str,
    diagrams: Optional[Dict[str, str]] = None,
    stats: Optional[Dict] = None,
    outputs_dir: str = "outputs",
) -> Dict:
    """Save documentation, diagrams, and optional statistics to disk.

    Layout:
      outputs/<repo_name>/
        - <repo_name>_documentation.md
        - statistics.json (optional)
        - diagrams/
            - <repo_name>_call_graph.mmd (if present)
            - <repo_name>_class_hierarchy.mmd (if present)
            - <repo_name>_module_graph.mmd (if present)

    Returns a dict with saved paths.
    """
    repo_name = repo_name_from_url(repo_url)
    # Anchor outputs at the project root (two levels up from this file: backend/utils/ -> project root)
    root_dir = Path(__file__).resolve().parents[2]
    base_dir = root_dir / outputs_dir / repo_name
    ensure_dir(base_dir)

    saved = {"base_dir": str(base_dir)}

    # Save documentation
    doc_filename = f"{repo_name}_documentation.md"
    doc_path = base_dir / doc_filename
    with doc_path.open("w", encoding="utf-8") as f:
        f.write(documentation or "")
    saved["documentation_path"] = str(doc_path)

    # Save diagrams
    diagrams_paths: Dict[str, str] = {}
    if diagrams:
        diag_dir = base_dir / "diagrams"
        ensure_dir(diag_dir)
        mapping = {
            "call_graph": f"{repo_name}_call_graph.mmd",
            "class_hierarchy": f"{repo_name}_class_hierarchy.mmd",
            "module_graph": f"{repo_name}_module_graph.mmd",
        }
        for key, content in diagrams.items():
            if not content:
                continue
            fname = mapping.get(key, f"{repo_name}_{key}.mmd")
            p = diag_dir / fname
            with p.open("w", encoding="utf-8") as f:
                f.write(str(content))
            diagrams_paths[key] = str(p)
    if diagrams_paths:
        saved["diagrams_paths"] = diagrams_paths

    # Save statistics if provided
    if stats is not None:
        stats_path = base_dir / "statistics.json"
        try:
            with stats_path.open("w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            saved["statistics_path"] = str(stats_path)
        except Exception:
            # Fail soft on stats save
            pass

    return saved

