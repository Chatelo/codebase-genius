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


def build_structured_markdown(
    repo_url: str,
    overview: Optional[Dict] = None,
    api_surface: str = "",
    ccg_counts: Optional[Dict[str, int]] = None,
    top_files_str: str = "",
    diagrams: Optional[Dict[str, str]] = None,
    ccg_context: str = "",
    ccg_mermaid: str = "",
    include_diagrams: bool = False,
    doc_overview: str = "",
) -> str:
    """Compose a deterministic Markdown document with required sections.

    Sections produced:
      - # Documentation for <repo_url>
      - ## Project Overview
      - ## Installation
      - ## Usage
      - ## API Reference (summary)
      - ## Diagrams (mermaid blocks if enabled and present)
      - ## Citations (CCG)
    """
    title_md = f"# Documentation for {repo_url}\n\n"

    # Overview
    ov_text = (doc_overview or "").strip() or "No overview generated."
    overview_md = "## Project Overview\n\n" + ov_text + "\n\n"

    # Installation / Usage (extract from README sections if available)
    inst_txt = ""; use_txt = ""
    try:
        if overview and isinstance(overview, dict):
            rd = overview.get("readme") or {}
            sections = rd.get("sections") or []
            for sec in sections:
                title = str(sec.get("title", "")).lower()
                content = str(sec.get("content", ""))
                if not inst_txt and ("install" in title):
                    inst_txt = content
                if not use_txt and ("usage" in title or "use" in title or "run" in title or "quick start" in title):
                    use_txt = content
    except Exception:
        pass
    inst_md = "## Installation\n\n" + (inst_txt or "Refer to the repository README for installation instructions.") + "\n\n"
    use_md = "## Usage\n\n" + (use_txt or "Refer to the repository README for usage examples.") + "\n\n"

    # API Reference
    api_md = "## API Reference (summary)\n\n"
    if api_surface:
        api_md += api_surface + "\n"
    if ccg_counts:
        calls = ccg_counts.get("calls", 0)
        inh = ccg_counts.get("inherits", 0)
        imps = ccg_counts.get("imports", 0)
        api_md += f"CCG counts — calls: {calls}, inherits: {inh}, imports: {imps}\n"
    if top_files_str:
        api_md += f"Top files by lines: {top_files_str}\n"
    api_md += "\n"

    # Diagrams
    diagrams_md = "## Diagrams\n\n"
    if include_diagrams:
        try:
            if diagrams and isinstance(diagrams, dict):
                if diagrams.get("call_graph"):
                    diagrams_md += f"```mermaid\n{diagrams['call_graph']}\n```\n\n"
                if diagrams.get("class_hierarchy"):
                    diagrams_md += f"```mermaid\n{diagrams['class_hierarchy']}\n```\n\n"
                if diagrams.get("module_graph"):
                    diagrams_md += f"```mermaid\n{diagrams['module_graph']}\n```\n\n"
        except Exception:
            diagrams_md += "Diagrams not available.\n\n"
    else:
        diagrams_md += "Diagrams disabled for this run.\n\n"

    # Citations
    cites_md = "## Citations (CCG)\n\n"
    if ccg_context:
        cites_md += ccg_context + "\n\n"
    if ccg_mermaid:
        cites_md += ccg_mermaid + "\n\n"

    return title_md + overview_md + inst_md + use_md + api_md + diagrams_md + cites_md


