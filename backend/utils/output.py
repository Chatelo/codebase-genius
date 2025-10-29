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
    """Compose a deterministic Markdown document aligned to mk-format template.

    Required compatibility (preserved):
    - Keep legacy headings: "# Documentation for", "## Project Overview",
      "## Installation", "## Usage", "## API Reference (summary)",
      "## Diagrams", "## Citations (CCG)" so existing tests remain green.
    - Preserve normalization/dedup and Detailed API (inferred) section.
    - Enrich to follow mk-format.md ordering and style by adding: badges,
      Table of Contents, Key Features, Quick Start, Project Structure,
      Core Architecture, Code Context Graph section, Development, Testing,
      Contributing, Project Statistics, Additional Resources, Acknowledgments.
    """
    # --- derive helpful context from provided overview/stats ---
    stats = {}
    if overview and isinstance(overview, dict):
        try:
            stats = overview.get("stats", {}) or {}
        except Exception:
            stats = {}
    repo_name = repo_name_from_url(repo_url)
    # Primary language heuristic
    primary_language = "unknown"
    try:
        langs = stats.get("languages") or {}
        if isinstance(langs, dict) and langs:
            # choose max by lines/files if available, key by count otherwise
            def _lang_metric(v):
                if isinstance(v, dict):
                    return v.get("lines", 0) or v.get("files", 0) or 0
                return int(v) if isinstance(v, (int, float)) else 0
            primary_language = max(langs.items(), key=lambda kv: _lang_metric(kv[1]))[0]
    except Exception:
        pass
    license_name = (overview or {}).get("license") or stats.get("license") or "unknown"
    last_commit = stats.get("last_commit_date") or stats.get("last_commit") or "unknown"
    # Title and badges (template-inspired)
    title_md = f"# Documentation for {repo_url}\n\n"
    badges_md = (
        f"[![Language](https://img.shields.io/badge/language-{_sanitize_name(primary_language)}-blue)]()\n"
        f"[![License](https://img.shields.io/badge/license-{_sanitize_name(str(license_name))}-green)]()\n"
        f"[![Last Commit](https://img.shields.io/badge/last_commit-{_sanitize_name(str(last_commit))}-orange)]()\n\n"
    )

    # Table of Contents — mirrors mk-format.md ordering
    toc_md = (
        "## 📋 Table of Contents\n\n"
        "- [Overview](#project-overview)\n"
        "- [Key Features](#key-features)\n"
        "- [Installation](#installation)\n"
        "- [Usage](#usage)\n"
        "- [Getting Started](#getting-started)\n"
        "- [Project Structure](#project-structure)\n"
        "- [Core Architecture](#core-architecture)\n"
        "- [API Reference](#api-reference-summary)\n"
        "- [Code Context Graph](#code-context-graph)\n"
        "- [Usage Examples](#usage-examples)\n"
        "- [Configuration](#configuration)\n"
        "- [Development](#development)\n"
        "- [Testing](#testing)\n"
        "- [Contributing](#contributing)\n"
        "- [Project Statistics](#project-statistics)\n"
        "- [Additional Resources](#additional-resources)\n"
        "- [Acknowledgments](#acknowledgments)\n\n"
    )

    # Overview
    ov_text = _normalize_text(doc_overview or "")
    ov_text = _strip_md_headings(ov_text)
    ov_text = _dedupe_blocks(ov_text)
    if not ov_text:
        ov_text = "No overview generated."
    overview_md = "## Project Overview\n\n" + ov_text + "\n\n"

    # Key Features (best-effort auto-synthesis)
    feats = []
    try:
        total_files = stats.get("files")
        code_files = stats.get("code_files")
        tests_files = stats.get("tests_files")
        if total_files is not None:
            feats.append(f"Processes repository with {total_files} files")
        if code_files is not None:
            feats.append(f"Understands code across {code_files} source files")
        if primary_language and primary_language != "unknown":
            feats.append(f"Language-aware analysis (primary: {primary_language})")
        if include_diagrams:
            feats.append("Generates Mermaid diagrams for call/class/module relations")
        if tests_files:
            feats.append(f"Identifies tests: {tests_files} test files detected")
    except Exception:
        pass
    if not feats:
        feats = [
            "Automated repository overview",
            "Inferred API surface with classes and functions",
            "Optional diagrams for relationships",
        ]
    key_features_md = "## ✨ Key Features\n\n" + "\n".join([f"- **{f}**" for f in feats]) + "\n\n"

    # Installation / Usage (extract from README sections if available)
    # Helpers: balance stray fenced code blocks and identify typical run lines
    def _balance_fences(text: str) -> str:
        try:
            if text and text.count("```") % 2 == 1:
                return text.rstrip() + "\n```\n"
        except Exception:
            pass
        return text

    RUN_PATTERNS = (
        "jac serve", "python -m", "npm run", "npm start", "pnpm", "yarn",
        "uv run", "pytest", "streamlit run", "docker run", "poetry run",
    )

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
                if not use_txt and ("usage" in title or "use" in title or "run" in title or "quick start" in title or "getting started" in title):
                    use_txt = content
    except Exception:
        pass
    # Normalize and clean extracted README sections
    inst_txt = _dedupe_blocks(_strip_md_headings(_normalize_text(inst_txt)))
    use_txt = _dedupe_blocks(_strip_md_headings(_normalize_text(use_txt)))

    # Keep Installation strictly setup/dependencies: filter out typical run commands
    if inst_txt:
        try:
            filtered_lines = []
            for ln in inst_txt.splitlines():
                if any(pat in ln for pat in RUN_PATTERNS):
                    continue
                filtered_lines.append(ln)
            inst_txt = "\n".join(filtered_lines)
        except Exception:
            pass

    # Balance fences to avoid leaking blocks into subsequent sections
    inst_txt = _balance_fences(inst_txt)
    use_txt = _balance_fences(use_txt)

    inst_md = "## Installation\n\n" + (inst_txt or "Refer to the repository README for installation instructions.") + "\n\n"
    # Getting Started focuses on running/using after setup; when README provides usage, move it here
    if use_txt:
        getting_started_body = use_txt
        usage_body = "See Getting Started for basic run. Refer to the repository README for advanced usage."
    else:
        getting_started_body = "> After installation, refer to the repository README for a minimal working example."
        usage_body = "Refer to the repository README for usage examples."

    getting_started_md = (
        "## 🚀 Getting Started\n\n" + getting_started_body + "\n\n"
    )
    use_md = "## Usage\n\n" + usage_body + "\n\n"

    # Project Structure (render exactly like Tree tab logic)
    proj_struct_md = "## 📁 Project Structure\n\n"
    file_tree = (overview or {}).get("file_tree") if isinstance(overview, dict) else None
    try:
        # Build a nested tree structure from a flat list of file paths
        def _build_nested(ft_list):
            root = {"dirs": {}, "files": []}
            for f in (ft_list or []):
                try:
                    path = str(f.get("path", ""))
                except Exception:
                    path = ""
                parts = [p for p in path.split("/") if p]
                if not parts:
                    continue
                node = root
                for d in parts[:-1]:
                    node = node["dirs"].setdefault(d, {"dirs": {}, "files": []})
                node["files"].append(parts[-1])
            return root

        def _file_kind(name: str) -> str:
            lower = name.lower()
            if lower.endswith(".py"): return "py"
            if lower.endswith((".js", ".jsx", ".ts", ".tsx")): return "js"
            if lower.endswith((".md", ".rst")): return "md"
            if lower.endswith((".json", ".yml", ".yaml", ".toml")): return "conf"
            if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")): return "img"
            return "other"

        def _file_icon(name: str) -> str:
            k = _file_kind(name)
            return {"py": "🐍", "js": "🧩", "md": "📘", "conf": "🧾", "img": "🖼️"}.get(k, "📄")

        def _build_lines(node, prefix: str = "", depth: int = 0, max_depth: int = 3):
            lines = []
            dirs = sorted(node.get("dirs", {}).items(), key=lambda x: x[0])
            files = sorted(node.get("files", []))
            total = len(dirs) + len(files)

            # Directories
            for idx, (dname, dnode) in enumerate(dirs):
                last = (idx == total - 1) and (len(files) == 0)
                branch = "└──" if last else "├──"
                lines.append(f"{prefix}{branch} 📁 {dname}/")
                next_prefix = prefix + ("    " if last else "│   ")
                if depth + 1 < max_depth:
                    lines.extend(_build_lines(dnode, next_prefix, depth + 1, max_depth))

            # Files
            for j, fname in enumerate(files):
                last = (j + len(dirs) == total - 1)
                branch = "└──" if last else "├──"
                icon = _file_icon(fname)
                lines.append(f"{prefix}{branch} {icon} {fname}")
            return lines

        if isinstance(file_tree, list) and file_tree:
            nested = _build_nested(file_tree)
            header = "📁 Repository Root/"
            lines = [header]
            lines.extend(_build_lines(nested, "", 0, 3))
            proj_struct_md += "```\n" + "\n".join(lines) + "\n```\n\n"
        else:
            proj_struct_md += "Structure not available.\n\n"
    except Exception:
        proj_struct_md += "Structure not available.\n\n"

    # Core Architecture (generic explanation tuned to CCG and walkers)
    core_arch_md = (
        "## 🏗️ Core Architecture\n\n"
        "This project is documented via a graph-first analysis: files, classes, functions, and modules are modeled as nodes; calls, imports, and inheritance are edges.\n\n"
        "Walkers traverse the graph to derive insights and optionally generate diagrams.\n\n"
    )

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

    # Code Context Graph wrapper (template-aligned) + legacy Diagrams section
    ccg_wrapper_md = "## 🕸️ Code Context Graph\n\n"
    diagrams_md = "## Diagrams\n\n"

    def _is_empty_mermaid(s: str) -> bool:
        try:
            t = (s or "").strip()
            # Consider empty if no edges/arrows or only header line
            if ("-->" not in t) and ("---" not in t) and ("-.->" not in t) and ("--x" not in t):
                # Also ignore trivial single-line like 'flowchart LR'
                return len([ln for ln in t.splitlines() if ln.strip()]) <= 1
            return False
        except Exception:
            return False

    if include_diagrams:
        try:
            if diagrams and isinstance(diagrams, dict):
                # As sub-sections under Code Context Graph (primary home for diagrams)
                if diagrams.get("call_graph"):
                    cc = diagrams["call_graph"]
                    ccg_wrapper_md += "### Call Graph\n\n"
                    if _is_empty_mermaid(cc):
                        ccg_wrapper_md += "No call graph data available.\n\n"
                    else:
                        ccg_wrapper_md += f"```mermaid\n{cc}\n```\n\n"
                if diagrams.get("class_hierarchy"):
                    ch = diagrams["class_hierarchy"]
                    ccg_wrapper_md += "### Class Hierarchy\n\n"
                    if _is_empty_mermaid(ch):
                        ccg_wrapper_md += "No class hierarchy data available.\n\n"
                    else:
                        ccg_wrapper_md += f"```mermaid\n{ch}\n```\n\n"
                if diagrams.get("module_graph"):
                    mg = diagrams["module_graph"]
                    ccg_wrapper_md += "### Module Dependencies\n\n"
                    if _is_empty_mermaid(mg):
                        ccg_wrapper_md += "No module dependency data available.\n\n"
                    else:
                        ccg_wrapper_md += f"```mermaid\n{mg}\n```\n\n"

                # Avoid duplicating diagrams; keep Diagrams section as a pointer
                diagrams_md += "See Code Context Graph section above for diagrams.\n\n"
        except Exception:
            diagrams_md += "Diagrams not available.\n\n"
    else:
        diagrams_md += "Diagrams disabled for this run.\n\n"
        # If no diagrams and no ccg mermaid/context, provide a guiding note
        try:
            if not (diagrams and any(diagrams.get(k) for k in ("call_graph","class_hierarchy","module_graph"))) and not ccg_mermaid and not _normalize_text(ccg_context):
                ccg_wrapper_md += "Diagrams are disabled. See Citations below for summarized relationships.\n\n"
        except Exception:
            pass

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
    # Additional template sections (lightweight placeholders to match style)
    usage_examples_md = "## 💡 Usage Examples\n\n" \
        "+ See README for examples relevant to this repository.\n\n"

    configuration_md = "## ⚙️ Configuration\n\n" \
        "+ Refer to the repository for configuration files and environment variables.\n\n"

    development_md = "## 🛠️ Development\n\n" \
        "This section is repository-specific. Use the project's preferred tooling for linting, formatting, and testing.\n\n"

    testing_md = "## 🧪 Testing\n\n" \
        "Run the repository's test suite as described in its README.\n\n"

    contributing_md = "## 🤝 Contributing\n\n" \
        "Follow the repository's contribution guidelines if available.\n\n"

    # Project statistics (best-effort table)
    proj_stats_md = "## 📊 Project Statistics\n\n"
    try:
        total_files = stats.get("files")
        code_files = stats.get("code_files")
        docs_files = stats.get("docs")
        tests_files = stats.get("tests_files")
        lines = ["| Metric | Value |", "|--------|-------|"]
        if total_files is not None:
            lines.append(f"| Total Files | {total_files} |")
        if code_files is not None:
            lines.append(f"| Code Files | {code_files} |")
        if docs_files is not None:
            lines.append(f"| Docs Files | {docs_files} |")
        if tests_files is not None:
            lines.append(f"| Test Files | {tests_files} |")
        if lines and len(lines) > 2:
            proj_stats_md += "\n".join(lines) + "\n\n"
    except Exception:
        pass

    resources_md = "## 📚 Additional Resources\n\n" \
        "+ Issues and discussions can be found on the repository.\n\n"

    # License section when available
    license_md = ""
    if str(license_name).lower() != "unknown":
        license_md = f"## License\n\nThis project is licensed under **{license_name}**. See the repository's LICENSE for details.\n\n"

    acknowledgments_md = "## 🙏 Acknowledgments\n\nGenerated by Codebase Genius.\n\n"

    # Compose final document respecting template-like ordering while preserving legacy headings
    parts = [
        title_md,
        badges_md,
        toc_md,
        overview_md,
        key_features_md,
        inst_md,
        use_md,
    getting_started_md,
        proj_struct_md,
        core_arch_md,
        api_md,
        ccg_wrapper_md,
        diagrams_md,
        cites_md,
        usage_examples_md,
        configuration_md,
        development_md,
        testing_md,
        contributing_md,
        proj_stats_md,
        resources_md,
        license_md,
        acknowledgments_md,
    ]

    return "".join(parts)


