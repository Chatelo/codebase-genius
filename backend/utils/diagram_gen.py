from typing import Dict, List, Tuple


def _sanitize_id(label: str) -> str:
    """Create a Mermaid-safe node id from an arbitrary label.

    Mermaid node IDs should avoid spaces and special characters. We map any
    non-alphanumeric to underscores and ensure the id doesn't start with a digit.
    """
    if not isinstance(label, str):
        label = str(label)
    # Replace non-alnum with underscore
    out = []
    for ch in label:
        if ch.isalnum():
            out.append(ch)
        else:
            out.append("_")
    ident = "".join(out).strip("_") or "n"
    if ident[0].isdigit():
        ident = f"n_{ident}"
    return ident


def _id_for(label: str, cache: Dict[str, str]) -> str:
    """Return a stable id for a given label using a cache."""
    if label in cache:
        return cache[label]
    ident = _sanitize_id(label)
    # Avoid collisions by appending a numeric suffix if needed
    if ident in cache.values():
        i = 2
        base = ident
        while f"{base}_{i}" in cache.values():
            i += 1
        ident = f"{base}_{i}"
    cache[label] = ident
    return ident

def _build_maps(entities: Dict) -> Tuple[Dict[str, str], Dict[str, str]]:
    func_module: Dict[str, str] = {}
    class_module: Dict[str, str] = {}
    for f in entities.get("files", []):
        mod = f.get("module", "")
        for fn in f.get("functions", []):
            func_module.setdefault(fn, mod)
        for cn in f.get("classes", []):
            class_module.setdefault(cn, mod)
    return func_module, class_module


def _label(mod: str, name: str) -> str:
    if mod:
        return f"{mod}.{name}"
    return name


def make_call_graph_mermaid(entities: Dict, max_edges: int = 400, filter_tests: bool = False) -> str:
    """Build a Mermaid flowchart for the function call graph.
    Collapses duplicate edges and prefixes names with module for clarity.
    """
    func_module, class_module = _build_maps(entities)
    lines: List[str] = ["flowchart LR"]
    edges = set()
    id_cache: Dict[str, str] = {}

    def is_test_label(label: str) -> bool:
        l = (label or "").lower()
        return "test" in l or "tests" in l

    for f in entities.get("files", []):
        mod = f.get("module", "")
        for c in f.get("calls", []):
            caller = c.get("caller") or ""
            callee = c.get("callee") or ""
            if not caller or not callee:
                continue
            src = _label(mod, caller)
            callee_mod = func_module.get(callee) or class_module.get(callee) or ""
            dst = _label(callee_mod, callee)
            if filter_tests and (is_test_label(src) or is_test_label(dst)):
                continue
            sid = _id_for(src, id_cache)
            did = _id_for(dst, id_cache)
            # Inline node definitions with labels to ensure valid Mermaid syntax
            edge = f"  {sid}[\"{src}\"] --> {did}[\"{dst}\"]"
            if edge not in edges:
                lines.append(edge)
                edges.add(edge)
                if len(edges) >= max_edges:
                    return "\n".join(lines)
    return "\n".join(lines)


def make_class_hierarchy_mermaid(entities: Dict, max_edges: int = 400, filter_tests: bool = False) -> str:
    """Build a Mermaid diagram for class inheritance."""
    lines: List[str] = ["flowchart TB"]
    edges = set()
    id_cache: Dict[str, str] = {}

    def is_test_label(label: str) -> bool:
        l = (label or "").lower()
        return "test" in l or "tests" in l

    for f in entities.get("files", []):
        for inh in f.get("inherits", []):
            sub = inh.get("class")
            base = inh.get("base")
            if not sub or not base:
                continue
            if filter_tests and (is_test_label(sub) or is_test_label(base)):
                continue
            sid = _id_for(sub, id_cache)
            bid = _id_for(base, id_cache)
            edge = f"  {sid}[\"{sub}\"] -->|extends| {bid}[\"{base}\"]"
            if edge not in edges:
                lines.append(edge)
                edges.add(edge)
                if len(edges) >= max_edges:
                    return "\n".join(lines)
    return "\n".join(lines)


def make_module_graph_mermaid(entities: Dict, max_edges: int = 400, filter_tests: bool = False) -> str:
    """Build a Mermaid diagram for module imports."""
    lines: List[str] = ["flowchart LR"]
    edges = set()
    id_cache: Dict[str, str] = {}

    def is_test_label(label: str) -> bool:
        l = (label or "").lower()
        return "test" in l or "tests" in l

    for f in entities.get("files", []):
        mod_src = f.get("module", "")
        if not mod_src:
            continue
        for imp in f.get("imports", []):
            tgt = imp.get("module", "")
            if not tgt:
                continue
            if filter_tests and (is_test_label(mod_src) or is_test_label(tgt)):
                continue
            sid = _id_for(mod_src, id_cache)
            did = _id_for(tgt, id_cache)
            edge = f"  {sid}[\"{mod_src}\"] --> {did}[\"{tgt}\"]"
            if edge not in edges:
                lines.append(edge)
                edges.add(edge)
                if len(edges) >= max_edges:
                    return "\n".join(lines)
    return "\n".join(lines)

