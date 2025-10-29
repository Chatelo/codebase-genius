import re
from pathlib import Path
from typing import Dict, List, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import os

# Optional tree-sitter support via tree_sitter_languages (if installed)
try:
    from tree_sitter_languages import get_parser  # type: ignore
except Exception:  # pragma: no cover
    get_parser = None

# Basic regexes (Python-focused fallback)
_FUNC_DEF_RE = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_CLASS_DEF_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(([^)]*)\))?\s*:")
_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_PY_IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z_][\w\.]*)(?:\s+as\s+([A-Za-z_][\w]*))?")
_PY_FROM_IMPORT_RE = re.compile(r"^\s*from\s+([A-Za-z_][\w\.]*)\s+import\s+([A-Za-z_\*,\s][\w\*,\s]*)")
_ESM_IMPORT_RE = re.compile(r"^\s*import\s+.+?from\s+['\"]([^'\"]+)['\"]")
_CJS_REQUIRE_RE = re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)")

_PY_KEYWORDS = {
    'def','class','return','import','from','lambda','if','elif','else','for','while','with','try','except','finally','yield','async','await','pass','break','continue'
}
_BUILTIN_FUNCS = {
    'print','len','range','list','dict','set','tuple','int','float','str','bool','sum','min','max','open','enumerate','zip','map','filter','any','all'
}


def _module_name_for(path: Path, language: str) -> str:
    # Derive a dotted module name for Python, or slash-based for others
    rel = path
    name = rel.as_posix()
    if language == 'python':
        if name.endswith('.py'):
            name = name[:-3]
        return name.replace('/', '.')
    # JS/TS: drop extension
    for ext in ('.ts', '.tsx', '.js', '.jsx'):
        if name.endswith(ext):
            name = name[: -len(ext)]
            break
    return name


def _naive_extract_python(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    functions: List[str] = []
    classes: List[str] = []
    inherits: List[Dict[str, Any]] = []
    imports: List[Dict[str, Any]] = []
    calls: List[Dict[str, Any]] = []


    # Capture richer details for API docs
    functions_detail: List[Dict[str, Any]] = []
    classes_detail: List[Dict[str, Any]] = []

    def _peek_docstring(start_idx: int) -> str:
        """Return a triple-quoted docstring starting at or after start_idx (1-based)."""
        j = start_idx
        n = len(lines)
        while 1 <= j <= n:
            ln = lines[j - 1]
            if ln.strip() == "":
                j += 1
                continue
            s = ln.lstrip()
            if s.startswith('"""') or s.startswith("'''"):
                q = '"""' if s.startswith('"""') else "'''"
                body = s[len(q):]
                if q in body:
                    return body.split(q)[0].strip()
                # multi-line docstring
                k = j + 1
                parts = [body]
                while 1 <= k <= n:
                    ln2 = lines[k - 1]
                    if q in ln2:
                        parts.append(ln2.split(q)[0])
                        break
                    parts.append(ln2)
                    k += 1
                return "\n".join(parts).strip()
            # first non-empty is not a docstring
            break
        return ""

    # Track current function by indentation
    current_func = None
    current_indent = 0

    for idx, line in enumerate(lines, start=1):
        m_cls = _CLASS_DEF_RE.match(line)
        if m_cls:
            cls_name = m_cls.group(1)
            classes.append(cls_name)
            bases_raw = (m_cls.group(2) or '').strip()
            if bases_raw:
                for base in [b.strip().split('.')[-1] for b in bases_raw.split(',') if b.strip()]:
                    inherits.append({"class": cls_name, "base": base, "line": idx})
            # Capture class docstring if present
            try:
                cdoc = _peek_docstring(idx + 1)
            except Exception:
                cdoc = ""
            classes_detail.append({"name": cls_name, "doc": cdoc})
            # Reset current func when encountering class at same indent level
            # (We do not track class context for methods here)

        m_fun = _FUNC_DEF_RE.match(line)
        if m_fun:
            fname = m_fun.group(1)
            functions.append(fname)
            # Parse params
            params: List[str] = []
            try:
                after = line.split(fname, 1)[1]
                pseg = after[after.find("(")+1:]
                pseg = pseg.split(")")[0]
                for token in [t.strip() for t in pseg.split(",") if t.strip()]:
                    nm = token
                    if ":" in nm:
                        nm = nm.split(":", 1)[0].strip()
                    if "=" in nm:
                        nm = nm.split("=", 1)[0].strip()
                    nm = nm.lstrip("*")
                    nm = nm.lstrip("*")
                    if nm:
                        params.append(nm)
            except Exception:
                params = []
            m_ret = re.search(r"->\s*([^:]+)", line)
            returns = m_ret.group(1).strip() if m_ret else ""
            # Docstring
            try:
                fdoc = _peek_docstring(idx + 1)
            except Exception:
                fdoc = ""
            functions_detail.append({"name": fname, "params": params, "returns": returns, "doc": fdoc})
            current_func = fname
            current_indent = len(line) - len(line.lstrip(' '))
            continue

        # Imports
        m_imp = _PY_IMPORT_RE.match(line)
        if m_imp:
            imports.append({
                "module": m_imp.group(1),
                "alias": m_imp.group(2) or "",
                "import_type": "import",
                "line": idx,
            })
        m_from = _PY_FROM_IMPORT_RE.match(line)
        if m_from:
            mods = [s.strip() for s in (m_from.group(2) or '').split(',') if s.strip()]
            if not mods:
                mods = ["*"]
            for mod in mods:
                imports.append({
                    "module": f"{m_from.group(1)}.{mod}" if mod not in {"*"} else m_from.group(1),
                    "alias": "",
                    "import_type": "from_import",
                    "line": idx,
                })

        # Calls (very naive): find foo( and filter obvious non-calls
        for call in _CALL_RE.findall(line):
            if call in _PY_KEYWORDS or call in _BUILTIN_FUNCS:
                continue
            calls.append({
                "caller": current_func or "",
                "callee": call,
                "line": idx,
            })

        # crude dedent detection: reset current_func when line indentation <= current_indent and line starts with def/class
        if current_func and (line.strip().startswith('def ') or line.strip().startswith('class ')):
            indent = len(line) - len(line.lstrip(' '))
            if indent <= current_indent:
                current_func = None

    return {
        "functions": functions,
        "classes": classes,
        "inherits": inherits,
        "imports": imports,
        "calls": calls,
        "functions_detail": functions_detail,
        "classes_detail": classes_detail,
    }


def _naive_extract_generic(path: Path, language: str) -> Dict[str, Any]:
    # Fallback: read and return minimal info using simple regexes for class/function-like patterns
    text = path.read_text(encoding="utf-8", errors="ignore")
    functions = []
    classes = []
    # Extremely naive heuristics
    if language in {"javascript", "typescript", "tsx", "jsx"}:
        # function foo(  |  const foo = () =>  | class Foo
        functions += re.findall(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", text)
        functions += re.findall(r"\bconst\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\([^)]*\)\s*=>", text)
        classes += re.findall(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b", text)
        imports: List[Dict[str, Any]] = []
        calls: List[Dict[str, Any]] = []
        inherits: List[Dict[str, Any]] = []
        for idx, line in enumerate(text.splitlines(), start=1):
            m1 = _ESM_IMPORT_RE.match(line)
            if m1:
                imports.append({"module": m1.group(1), "alias": "", "import_type": "esm", "line": idx})
            for m2 in _CJS_REQUIRE_RE.findall(line):
                imports.append({"module": m2, "alias": "", "import_type": "cjs", "line": idx})
            for call in _CALL_RE.findall(line):
                calls.append({"caller": "", "callee": call, "line": idx})
        return {"functions": functions, "classes": classes, "inherits": inherits, "imports": imports, "calls": calls}
    else:
        # default minimal
        functions = re.findall(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", text)
        classes = re.findall(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b", text)
        return {"functions": functions, "classes": classes, "inherits": [], "imports": [], "calls": []}


def _ts_extract(path: Path, language: str) -> Dict[str, Any]:
    # If a tree-sitter parser is available, attempt to use it for improved accuracy.
    # Be defensive: tree-sitter parsers are version-dependent and may throw parsing
    # errors on some codebases. If parsing fails, return a structured warning and
    # fall back to a naive extractor.
    # Also avoid attempting heavy parsing on very large files.
    max_ts_bytes = int(os.environ.get("CBG_TS_MAX_BYTES", str(200 * 1024)))
    try:
        size = path.stat().st_size
    except Exception:
        size = 0

    if size > max_ts_bytes:
        # Skip heavy parsing for very large TS/JS files; fall back to naive extractor
        return {"_parse_warning": f"Skipped tree-sitter parse due to file size > {max_ts_bytes} bytes"} | _naive_extract(path, language)

    if get_parser is None:
        # No tree-sitter available; use naive fallback
        return _naive_extract(path, language)

    # Try to invoke parser; guard against parser exceptions
    parser_info = None
    try:
        # Some tree-sitter bindings accept language name variations; prefer explicit request
        parser = get_parser(language)
        parser_info = getattr(parser, "__name__", str(parser))
        # If parser exposes parse() or other APIs, attempt extraction (best-effort)
        # NOTE: tree-sitter extraction implementation is out of scope here; keep defensive
        try:
            # Attempt a lightweight parse call if available
            tree = parser.parse(path.read_bytes()) if hasattr(parser, "parse") else None
            # Not attempting full AST traversal here - use naive extractor as safe fallback
            return _naive_extract(path, language)
        except Exception as e:
            # Fall back to naive extractor with warning
            return {"_parse_warning": f"Tree-sitter parse failed: {e}. Using naive fallback."} | _naive_extract(path, language)
    except Exception as e:
        # Parser resolution failed; include hint about pinning parser versions
        ver_hint = os.environ.get("CBG_TS_PARSER_VERSION", "unspecified")
        return {"_parse_warning": f"TS parser unavailable or failed ({e}). Consider installing a pinned parser (CBG_TS_PARSER_VERSION={ver_hint})."} | _naive_extract(path, language)


def _naive_extract(path: Path, language: str) -> Dict[str, Any]:
    if language == 'python':
        return _naive_extract_python(path)
    return _naive_extract_generic(path, language)


def _process_single_file(args: tuple) -> Dict[str, Any]:
    """
    Process a single file for entity extraction.

    Returns a dict:
      - {"__ok__": True, "data": <entity_dict>} on success
      - {"__error__": {"file": <path>, "error": <str>}} on failure
      - None for non-CodeFile items or missing files
    """
    repo_root, item = args
    root = Path(repo_root).resolve()

    if item.get("type") != "CodeFile":
        return None

    language = item.get("language", "")
    rel_path = item.get("path")
    file_path = (root / rel_path).resolve()

    if not file_path.exists():
        return {"__error__": {"file": str(file_path), "error": "File does not exist"}}

    try:
        data = _ts_extract(file_path, language) if get_parser is not None else _naive_extract(file_path, language)
        # Attach derived module name and file
        data["file"] = str(file_path)
        data["module"] = _module_name_for(Path(rel_path), language)
        data["language"] = language
        return {"__ok__": True, "data": data}
    except Exception as e:
        # Return structured error for failed parses
        return {"__error__": {"file": str(file_path), "error": str(e)}}


def extract_entities(repo_root: str, file_tree: List[Dict], parallel: bool = True, max_workers: int = None) -> Dict:
    """
    Extract entities from all code files in the file tree.

    Args:
        repo_root: Root directory of the repository
        file_tree: List of file metadata dictionaries
        parallel: Whether to use parallel processing (default: True)
        max_workers: Maximum number of worker processes (default: CPU count)

    Returns:
        Dictionary with "files" key containing list of extracted entities
    """
    # Filter to only code files
    code_files = [item for item in file_tree if item.get("type") == "CodeFile"]

    if not code_files:
        return {"files": []}

    # Determine if we should use parallel processing
    # Only use parallel for larger file sets (overhead not worth it for small sets)
    use_parallel = parallel and len(code_files) > 10

    if not use_parallel:
        # Sequential processing for small file sets
        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        for item in code_files:
            out = _process_single_file((repo_root, item))
            if not out:
                continue
            if isinstance(out, dict) and out.get("__ok__"):
                results.append(out["data"])
            elif isinstance(out, dict) and "__error__" in out:
                errors.append(out["__error__"])
        return {"files": results, "errors": errors}

    # Parallel processing for larger file sets
    if max_workers is None:
        # Use CPU count, but cap at 8 to avoid excessive overhead
        max_workers = min(multiprocessing.cpu_count(), 8)

    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    # Prepare arguments for parallel processing
    args_list = [(repo_root, item) for item in code_files]

    # Use ProcessPoolExecutor for CPU-bound parsing work
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_single_file, args): args for args in args_list}

        for future in as_completed(futures):
            try:
                out = future.result()
                if not out:
                    continue
                if isinstance(out, dict) and out.get("__ok__"):
                    results.append(out["data"])
                elif isinstance(out, dict) and "__error__" in out:
                    errors.append(out["__error__"])
            except Exception as e:
                # Record unexpected worker failure
                args = futures.get(future)
                fitem = args[1] if args else {}
                fpath = fitem.get("path", "")
                errors.append({"file": fpath, "error": str(e)})

    return {"files": results, "errors": errors}
