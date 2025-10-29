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



# --- Markdown sanitation helpers ---

def _normalize_text(s: str) -> str:
    """Normalize LLM/raw text to renderable markdown.
    - Decode JSON-escaped strings if possible
    - Convert literal \n/\r\n to real newlines
    - Replace \t with 4 spaces
    - Collapse excessive blank lines
    - Trim trailing whitespace per line
    """
    if not s:
        return ""
    t = str(s)
    # Try JSON decode if it looks like a quoted JSON string
    try:
        if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
            t = json.loads(t)
    except Exception:
        pass
    # Normalize common escapes
    t = t.replace("\\r\\n", "\n")
    t = t.replace("\\n", "\n")
    t = t.replace("\\t", "    ")
    # Collapse 3+ newlines
    t = re.sub(r"\n{3,}", "\n\n", t)
    # Trim trailing spaces
    t = "\n".join([ln.rstrip() for ln in t.splitlines()])
    return t.strip()


def _strip_md_headings(s: str) -> str:
    """Remove markdown heading lines (#, ##, ### ...) from text."""
    if not s:
        return ""
    return "\n".join([ln for ln in str(s).splitlines() if not ln.lstrip().startswith('#')]).strip()


def _dedupe_blocks(md: str) -> str:
    """Remove duplicate paragraphs/blocks while preserving order."""
    if not md:
        return ""
    seen = set()
    out = []
    for block in [b.strip() for b in str(md).split("\n\n") if b.strip()]:
        if block not in seen:
            seen.add(block)
            out.append(block)
    return "\n\n".join(out)

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
    entities: Optional[Dict] = None,
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
    ov_text = _normalize_text(doc_overview or "")
    ov_text = _strip_md_headings(ov_text)
    ov_text = _dedupe_blocks(ov_text)
    if not ov_text:
        ov_text = "No overview generated."
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
    # Normalize and clean extracted README sections
    inst_txt = _dedupe_blocks(_strip_md_headings(_normalize_text(inst_txt)))
    use_txt = _dedupe_blocks(_strip_md_headings(_normalize_text(use_txt)))

    inst_md = "## Installation\n\n" + (inst_txt or "Refer to the repository README for installation instructions.") + "\n\n"
    use_md = "## Usage\n\n" + (use_txt or "Refer to the repository README for usage examples.") + "\n\n"

    # API Reference (formatted)
    api_md = "## API Reference (summary)\n\n"
    # Parse classes from api_surface if present
    classes_list = []
    funcs_total_num = 0
    try:
        if api_surface and "Classes:" in api_surface:
            s = api_surface
            lb = s.find("[")
            rb = s.find("]", lb + 1)
            if lb != -1 and rb != -1:
                cls_blob = s[lb + 1:rb].strip()
                if cls_blob:
                    for item in cls_blob.split(","):
                        nm = item.strip()
                        if nm:
                            classes_list.append(nm)
            # parse total functions
            if "Total functions:" in s:
                try:
                    funcs_total_num = int(s.split("Total functions:")[-1].strip())
                except Exception:
                    funcs_total_num = 0
    except Exception:
        pass
    if classes_list:
        api_md += "- Classes (top selection):\n" + "\n".join([f"  - {c}" for c in classes_list]) + "\n"
    if funcs_total_num:
        api_md += f"- Total functions: {funcs_total_num}\n"
    # CCG counts
    if ccg_counts:
        calls = ccg_counts.get("calls", 0)
        inh = ccg_counts.get("inherits", 0)
        imps = ccg_counts.get("imports", 0)
        api_md += "- CCG counts:\n"
        api_md += f"  - calls: {calls}\n"
        api_md += f"  - inherits: {inh}\n"
        api_md += f"  - imports: {imps}\n"
    # Top files list formatting
    if top_files_str:
        items = [it.strip() for it in top_files_str.split(",") if it.strip()]
        if items:
            api_md += "- Top files by lines:\n" + "\n".join([f"  - {it}" for it in items]) + "\n"
    api_md += "\n"

    # Detailed API (inferred) using entities if available
    if entities and isinstance(entities, dict):
        try:
            details_added = 0
            lines_buf = []
            for fe in entities.get("files", []):
                mod = fe.get("module") or fe.get("file", "")
                fds = fe.get("functions_detail", [])
                cds = fe.get("classes_detail", [])
                if not fds and not cds:
                    continue
                if mod:
                    lines_buf.append(f"- Module: {mod}")
                for cd in cds:
                    name = str(cd.get("name", ""))
                    d = str(cd.get("doc", "")).strip()
                    first = d.split("\n")[0] if d else ""
                    lines_buf.append(f"  - Class: {name}" + (f" — {first}" if first else ""))
                    details_added += 1
                    if details_added >= 20:
                        break
                if details_added >= 20:
                    break
                for fd in fds:
                    name = str(fd.get("name",""))
                    params = fd.get("params", [])
                    params_str = ", ".join(params) if isinstance(params, list) else str(params)
                    d = str(fd.get("doc","")).strip()
                    first = d.split("\n")[0] if d else ""
                    lines_buf.append(f"  - Function: {name}({params_str})" + (f" — {first}" if first else ""))
                    details_added += 1
                    if details_added >= 20:
                        break
                if details_added >= 20:
                    break
            if lines_buf:
                api_md += "### Detailed API (inferred)\n" + "\n".join(lines_buf) + "\n\n"
        except Exception:
            pass

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

    # Citations (format ccg_context into bullets if it's a compact string)
    cites_md = "## Citations (CCG)\n\n"
    ctx = _normalize_text(ccg_context or "")
    if ctx:
        # If context already contains bullets, use as-is
        if "\n- " in ctx or ctx.strip().startswith("-"):
            cites_md += ctx + "\n\n"
        else:
            cites_md += ctx + "\n\n"
    elif not ccg_mermaid:
        cites_md += "No citations available.\n\n"
    if ccg_mermaid:
        cites_md += ccg_mermaid + "\n\n"

    return title_md + overview_md + inst_md + use_md + api_md + diagrams_md + cites_md


