from typing import Dict, List, Tuple

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


def make_call_graph_mermaid(entities: Dict) -> str:
    """Build a Mermaid flowchart for the function call graph.
    Collapses duplicate edges and prefixes names with module for clarity.
    """
    func_module, class_module = _build_maps(entities)
    lines: List[str] = ["flowchart LR"]
    edges = set()
    max_edges = 400

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
            edge = f"  \"{src}\" --> \"{dst}\""
            if edge not in edges:
                lines.append(edge)
                edges.add(edge)
                if len(edges) >= max_edges:
                    break
        if len(edges) >= max_edges:
            break

    return "\n".join(lines)


def make_class_hierarchy_mermaid(entities: Dict) -> str:
    """Build a Mermaid diagram for class inheritance."""
    lines: List[str] = ["flowchart TB"]
    edges = set()
    max_edges = 400

    for f in entities.get("files", []):
        for inh in f.get("inherits", []):
            sub = inh.get("class")
            base = inh.get("base")
            if not sub or not base:
                continue
            edge = f"  \"{sub}\" -->|extends| \"{base}\""
            if edge not in edges:
                lines.append(edge)
                edges.add(edge)
                if len(edges) >= max_edges:
                    break
        if len(edges) >= max_edges:
            break

    return "\n".join(lines)


def make_module_graph_mermaid(entities: Dict) -> str:
    """Build a Mermaid diagram for module imports."""
    lines: List[str] = ["flowchart LR"]
    edges = set()
    max_edges = 400

    for f in entities.get("files", []):
        mod_src = f.get("module", "")
        if not mod_src:
            continue
        for imp in f.get("imports", []):
            tgt = imp.get("module", "")
            if not tgt:
                continue
            edge = f"  \"{mod_src}\" --> \"{tgt}\""
            if edge not in edges:
                lines.append(edge)
                edges.add(edge)
                if len(edges) >= max_edges:
                    break
        if len(edges) >= max_edges:
            break

    return "\n".join(lines)

