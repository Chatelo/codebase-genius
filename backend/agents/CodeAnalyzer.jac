# Analyzes code semantics (skeleton)

import from graph.nodes { Repository, Function, Class, Module }

import from utils.ts_analyze { extract_entities }
import from graph.builders { compute_top_files }


#* CCG Query helpers operating on Repository.ccg_* caches (no traversal required) *#
def ccg_get_callers(repo: Repository, func_name: str) -> list {
    res = [];
    if repo == None { return res; }
    if "ccg_calls" in repo {
        for rel in repo.ccg_calls {
            callee = None; caller = None; ln = 0;
            if "callee" in rel { callee = rel["callee"]; }
            if "caller" in rel { caller = rel["caller"]; }
            if "line" in rel { ln = rel["line"]; }
            if callee != None and caller != None and (callee.name == func_name) {
                res.append({"name": caller.name, "line": ln});
            }
        }
    }
    return res;
}

def ccg_get_callees(repo: Repository, func_name: str) -> list {
    res = [];
    if repo == None { return res; }
    if "ccg_calls" in repo {
        for rel in repo.ccg_calls {
            callee = None; caller = None; ln = 0;
            if "callee" in rel { callee = rel["callee"]; }
            if "caller" in rel { caller = rel["caller"]; }
            if "line" in rel { ln = rel["line"]; }
            if callee != None and caller != None and (caller.name == func_name) {
                res.append({"name": callee.name, "line": ln});
            }
        }
    }
    return res;
}

def ccg_get_subclasses(repo: Repository, class_name: str) -> list {
    res = [];
    if repo == None { return res; }
    if "ccg_inherits" in repo {
        for rel in repo.ccg_inherits {
            sub = None; base = None; t = "extends";
            if "sub" in rel { sub = rel["sub"]; }
            if "base" in rel { base = rel["base"]; }
            if "type" in rel { t = rel["type"]; }
            if sub != None and base != None and (base.name == class_name) {
                res.append({"name": sub.name, "type": t});
            }
        }
    }
    return res;
}

def ccg_get_dependencies(repo: Repository, module_name: str) -> list {
    res = [];
    if repo == None { return res; }
    if "ccg_imports" in repo {
        for rel in repo.ccg_imports {
            src = None; dst = None; al = ""; it = "import";
            if "src" in rel { src = rel["src"]; }
            if "dst" in rel { dst = rel["dst"]; }
            if "alias" in rel { al = rel["alias"]; }
            if "import_type" in rel { it = rel["import_type"]; }
            if src != None and dst != None and (src.name == module_name) {
                res.append({"name": dst.name, "alias": al, "type": it});
            }
        }
    }
    return res;
}

# Wrapper for entity extraction to keep analysis in the CodeAnalyzer agent boundary
# items: list of file dicts from file_tree; returns {"functions": [...], "classes": [...], ...}
def analyze_files(repo_path: str, items: list, parallel: bool = True) -> dict {
    return extract_entities(repo_path, items, parallel);
}


# Small helper to maintain descending order by key
def __insort_desc(lst: list, entry: dict, key: str) -> None {
    inserted = False; i = 0;
    while i < len(lst) {
        cur = 0; try { if (key in lst[i]) { cur = lst[i][key]; } } except Exception as e { cur = 0; }
        if entry.get(key, 0) > cur { lst.insert(i, entry); inserted = True; break; }
        i += 1;
    }
    if not inserted { lst.append(entry); }
}

#* Compute basic stats from a file_tree list.
# Returns dict with counts: files, jac_files, docs, plus code_files, python_files, languages and doc_kinds breakdowns.
*#
def basic_stats(file_tree: list, top_n: int = 10) -> dict {
    total = 0; jac_files = 0; docs = 0; code_files = 0; python_files = 0;
    languages = {}; doc_kinds = {}; top_dirs = {}; tests_files = 0; examples_files = 0;
    top_dirs_code = {}; tests_code_files = 0; examples_code_files = 0;
    top_size = []; top_lines = [];
    for item in file_tree {
        total += 1;
        has_path = ("path" in item);
        p = "";
        if has_path { p = item["path"]; }
        # Count top-level directory distribution
        if has_path and ("/" in p) {
            top = p.split("/")[0];
            if (top not in top_dirs) { top_dirs[top] = 0; }
            top_dirs[top] += 1;
        }
        # Detect tests/examples buckets (all files)
        if has_path and ("/tests/" in p or p.startswith("tests/") or "/test/" in p or p.startswith("test/")) { tests_files += 1; }
        if has_path and ("/examples/" in p or p.startswith("examples/") or "/example/" in p or p.startswith("example/")) { examples_files += 1; }

        if ("type" in item) and item["type"] == "CodeFile" {
            code_files += 1;
            if has_path and ("/" in p) {
                top = p.split("/")[0];
                if (top not in top_dirs_code) { top_dirs_code[top] = 0; }
                top_dirs_code[top] += 1;
            }
            # Detect tests/examples buckets for code files only
            if has_path and ("/tests/" in p or p.startswith("tests/") or "/test/" in p or p.startswith("test/")) { tests_code_files += 1; }
            if has_path and ("/examples/" in p or p.startswith("examples/") or "/example/" in p or p.startswith("example/")) { examples_code_files += 1; }

            if ("language" in item) {
                lang = item["language"];
                if (lang == "jac") { jac_files += 1; }
                if (lang == "python") { python_files += 1; }
                if (lang not in languages) { languages[lang] = 0; }
                languages[lang] += 1;
            }
            # Track top N by size for code files
            if ("size" in item) {
                sz = item["size"];
                __insort_desc(top_size, {"path": p, "size": sz}, "size");
                if len(top_size) > top_n { top_size.pop(); }
            }
            # Track top N by lines for code files if provided
            if ("lines" in item) {
                ln = item["lines"];
                __insort_desc(top_lines, {"path": p, "lines": ln}, "lines");
                if len(top_lines) > top_n { top_lines.pop(); }
            }
        } elif ("type" in item) and item["type"] == "Doc" {
            docs += 1;
            if ("language" in item) {
                dlang = item["language"];
                if (dlang not in doc_kinds) { doc_kinds[dlang] = 0; }
                doc_kinds[dlang] += 1;
            }
        }
    }
    # Unify top-lists using centralized helper
    try {
        tmp = compute_top_files(file_tree, top_n);
        top_lines = tmp.get("by_lines", top_lines);
        top_size = tmp.get("by_size", top_size);
    } except Exception as e { }
    return {
        "files": total,
        "jac_files": jac_files,
        "docs": docs,
        "code_files": code_files,
        "python_files": python_files,
        "languages": languages,
        "doc_kinds": doc_kinds,
        "tests_files": tests_files,
        "examples_files": examples_files,
        "tests_code_files": tests_code_files,
        "examples_code_files": examples_code_files,
        "top_dirs": top_dirs,
        "top_dirs_code": top_dirs_code,
        "top_files_by_size": top_size,
        "top_files_by_lines": top_lines,
    };
}


# Walker wrapper to compute stats from a Repository's file_tree
walker FileTreeStats {
    has top_n: int = 10;
    can compute with Repository entry {
        ft = []; try { if ("file_tree" in here) { ft = here.file_tree; } } except Exception as e { ft = []; }
        res = basic_stats(ft, self.top_n);
        report res;
    }
}

walker CodeAnalyzer {
    can analyze with `root entry {
        # Placeholder: would analyze CodeFile content and populate graph entities
        report {"ok": true};
    }
}
