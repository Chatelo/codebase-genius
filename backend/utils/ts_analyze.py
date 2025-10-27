import re
from pathlib import Path
from typing import Dict, List, Any

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
            # Reset current func when encountering class at same indent level
            # (We do not track class context for methods here)

        m_fun = _FUNC_DEF_RE.match(line)
        if m_fun:
            fname = m_fun.group(1)
            functions.append(fname)
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
    # Placeholder: if TS parser available, route to language-specific extraction
    # For now, defer to naive language handlers
    return _naive_extract(path, language)


def _naive_extract(path: Path, language: str) -> Dict[str, Any]:
    if language == 'python':
        return _naive_extract_python(path)
    return _naive_extract_generic(path, language)


def extract_entities(repo_root: str, file_tree: List[Dict]) -> Dict:
    root = Path(repo_root).resolve()
    results: List[Dict[str, Any]] = []
    for item in file_tree:
        if item.get("type") != "CodeFile":
            continue
        language = item.get("language", "")
        rel_path = item.get("path")
        file_path = (root / rel_path).resolve()
        if not file_path.exists():
            continue
        data = _ts_extract(file_path, language) if get_parser is not None else _naive_extract(file_path, language)
        # Attach derived module name and file
        data["file"] = str(file_path)
        data["module"] = _module_name_for(Path(rel_path), language)
        data["language"] = language
        results.append(data)
    return {"files": results}
