import os
import re
from pathlib import Path
from typing import Dict, List, Optional

_CODE_EXTS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "jsx",
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
    ".jac": "jaclang",
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


DEFAULT_MAX_LINECOUNT_BYTES = 524288  # 512 KB cap for quick line counting


def _count_lines_fast(path: Path, max_bytes: int) -> int:
    """Count newline characters by reading up to max_bytes from file.
    Falls back to 0 on error.
    """
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes)
        return data.count(b"\n")
    except Exception:
        return 0


def scan_repo_tree(
    root_path: str,
    exclude_dirs: Optional[List[str]] = None,
    exclude_globs: Optional[List[str]] = None,
    include_exts: Optional[List[str]] = None,
    include_globs: Optional[List[str]] = None,
    include_paths: Optional[List[str]] = None,
    max_files: Optional[int] = None,
    max_file_size_bytes: Optional[int] = None,
    compute_line_counts: bool = True,
    max_line_count_bytes: Optional[int] = DEFAULT_MAX_LINECOUNT_BYTES,
) -> List[Dict]:
    root = Path(root_path).resolve()
    out: List[Dict] = []
    final_excludes = set(EXCLUDE_DIRS)
    if exclude_dirs:
        final_excludes.update(exclude_dirs)

    # Normalize include_exts to lowercase with leading dots
    include_exts_norm = None
    if include_exts:
        include_exts_norm = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in include_exts}

    # Normalize include_paths to posix prefixes
    include_paths_norm = None
    if include_paths:
        include_paths_norm = [p if p.endswith("/") else f"{p}/" for p in (s.replace("\\", "/") for s in include_paths)]

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Exclude common non-source directories (by directory name)
        dirnames[:] = [d for d in dirnames if d not in final_excludes]
        for fname in filenames:
            p = Path(dirpath) / fname
            try:
                rel = p.relative_to(root)
            except Exception:
                rel = Path(fname)
            rel_posix = rel.as_posix()

            # Include by path prefixes if requested (keep only those under prefix)
            if include_paths_norm is not None:
                if not any(rel_posix.startswith(prefix) or rel_posix == prefix.rstrip("/") for prefix in include_paths_norm):
                    continue

            # Include by glob patterns (must match at least one if provided)
            if include_globs:
                matched = False
                for pat in include_globs:
                    try:
                        if rel.match(pat):
                            matched = True
                            break
                    except Exception:
                        pass
                if not matched:
                    continue

            # Filter by extension if requested
            if include_exts_norm is not None:
                if rel.suffix.lower() not in include_exts_norm:
                    continue

            # Exclude by glob patterns against path relative to root
            if exclude_globs:
                excluded = False
                for pat in exclude_globs:
                    try:
                        if rel.match(pat):
                            excluded = True
                            break
                    except Exception:
                        # If pattern invalid, ignore it
                        pass
                if excluded:
                    continue

            # Stat size (skip files over limit if configured)
            try:
                size = p.stat().st_size
            except Exception as e:
                print(f"[scan_repo_tree] Could not stat size for {rel}: {e}")
                size = 0
            if max_file_size_bytes and size > max_file_size_bytes:
                continue

            meta = _classify(rel)
            meta["size"] = int(size)

            # Optionally compute approximate line count for code files only
            if compute_line_counts and meta.get("type") == "CodeFile":
                try:
                    mb = max_line_count_bytes or DEFAULT_MAX_LINECOUNT_BYTES
                    meta["lines"] = int(_count_lines_fast(p, int(mb)))
                except Exception as e:
                    print(f"[scan_repo_tree] Could not count lines for {rel}: {e}")
                    meta["lines"] = 0

            out.append(meta)

            if max_files and len(out) >= max_files:
                return out
    return out


def extract_readme(root_path: str) -> Optional[Dict]:
    """
    Extract README.md (or similar) from repository root.

    Returns a dict with:
        - path: relative path to README
        - content: full text content
        - sections: list of markdown sections
        - size: file size in bytes
        - lines: number of lines
    """
    readme_names = ["README.md", "README.rst", "README.txt", "README", "Readme.md"]

    for name in readme_names:
        readme_path = Path(root_path) / name
        if readme_path.exists() and readme_path.is_file():
            try:
                content = readme_path.read_text(encoding="utf-8", errors="ignore")
                sections = _extract_markdown_sections(content)

                return {
                    "path": name,
                    "content": content,
                    "sections": sections,
                    "size": readme_path.stat().st_size,
                    "lines": len(content.splitlines())
                }
            except Exception as e:
                print(f"[extract_readme] Failed reading {name}: {e}")
                continue

    return None


def _extract_markdown_sections(content: str) -> List[Dict]:
    """
    Extract markdown sections (headings and their content).

    Returns a list of dicts with:
        - level: heading level (1-6)
        - title: heading text
        - content: section content (text after heading until next heading)
    """
    sections = []
    lines = content.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]

        # Match markdown headings: # Title, ## Title, etc.
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()

            # Collect content until next heading
            content_lines = []
            i += 1
            while i < len(lines):
                if re.match(r'^#{1,6}\s+', lines[i]):
                    break
                content_lines.append(lines[i])
                i += 1

            sections.append({
                "level": level,
                "title": title,
                "content": "\n".join(content_lines).strip()
            })
        else:
            i += 1

    return sections


def summarize_readme_sections(sections: List[Dict], max_sections: int = 5) -> str:
    """
    Create a concise summary of README sections.

    Takes the top N sections and creates a brief overview.
    """
    if not sections:
        return ""

    # Take top-level sections (level 1 and 2)
    top_sections = [s for s in sections if s["level"] <= 2][:max_sections]

    if not top_sections:
        top_sections = sections[:max_sections]

    summary_parts = []
    for section in top_sections:
        title = section["title"]
        content = section["content"]

        # Take first 200 chars of content
        if content:
            preview = content[:200].replace("\n", " ").strip()
            if len(content) > 200:
                preview += "..."
            summary_parts.append(f"{title}: {preview}")
        else:
            summary_parts.append(title)

    return " | ".join(summary_parts)

