#* Graph builder walkers for Codebase Genius.
# These walkers construct the Code Context Graph by creating nodes and edges.
*#

import from graph.nodes { Repository, Directory, CodeFile, Function, Class, Module }
import from graph.edges { Contains, Defines, Calls, Inherits, Imports }
import from utils.repo { clone_or_open_repo }
import from utils.fs_map { scan_repo_tree }
import from utils.ts_analyze { extract_entities }

#* Build a repository graph from file data with relationships in one pass.
# This function creates all nodes and typed edges directly, eliminating the need
# for a separate EdgeBuilder walker pass.
*#
def build_repo_graph(
    root_node: any,
    repo_url: str,
    files: list,
    entities: dict,
    build_typed_edges: bool = True
) -> any {
    # Create Repository node (instantiate first; then attach to root if possible)
    repo_node = Repository(url=repo_url);
    try { root_node ++> repo_node; } except Exception as e { }

    # Repo name from URL
    url_parts = repo_url.rstrip('/').split('/');
    repo_node.name = (url_parts[-1] if len(url_parts) > 0 else "");

    # Defensive defaults for inputs
    if files == None { files = []; }
    if entities == None { entities = {"files": []}; }

    # Track nodes
    dir_nodes = {};              # path -> Directory
    file_nodes = {};             # path -> CodeFile
    func_by_file = {};           # path -> {name: Function}
    func_global = {};            # name -> Function (first seen)
    cls_global = {};             # name -> Class (first seen)
    mod_global = {};             # module_name -> Module
    mod_of_file = {};            # path -> Module

    # Create Directory, CodeFile, Module nodes
    for f in files {
        fpath = ""; lang = ""; sz = 0; ln = 0;
        if "path" in f { fpath = f["path"]; }
        if "language" in f { lang = f["language"]; }
        if "size" in f { sz = f["size"]; }
        if "lines" in f { ln = f["lines"]; }

        # Build directory hierarchy
        parts = fpath.split('/');
        parent = repo_node;
        if len(parts) > 1 {
            accum = ""; i = 0;
            while i < len(parts) - 1 {
                if accum != "" { accum += "/"; }
                accum += parts[i];
                if accum not in dir_nodes {
                    d = Directory(path=accum, name=parts[i]);
                    parent ++> d;
                    dir_nodes[accum] = d;
                    parent = d;
                } else { parent = dir_nodes[accum]; }
                i += 1;
            }
        }

        # CodeFile
        cf = CodeFile(path=fpath, language=lang, size=sz, lines=ln);
        parent ++> cf;
        file_nodes[fpath] = cf;
        func_by_file[fpath] = {};

        lp = fpath.lower();
        if ("test" in lp) or ("spec" in lp) { cf.is_test = True; }
        if ("example" in lp) or ("demo" in lp) { cf.is_example = True; }
        if (lang == "markdown") or (lang == "rst") or (".md" in lp) or (".rst" in lp) { cf.is_doc = True; }

        # Module (derive from path by replacing '/' with '.')
        mod_name = fpath.replace('/', '.');
        mnode = None;
        if mod_name in mod_global { mnode = mod_global[mod_name]; }
        else {
            mnode = Module(name=mod_name, import_path=mod_name, is_external=False);
            repo_node ++> mnode;
            mod_global[mod_name] = mnode;
        }
        mod_of_file[fpath] = mnode;
    }

    # Add Function/Class nodes and build maps
    if "files" in entities {
        for fe in entities["files"] {
            # Map absolute to relative file path
            rel = "";
            if "file" in fe {
                ap = fe["file"];
                for k in file_nodes { if k in ap { rel = k; break; } }
            }
            if rel == "" or (rel not in file_nodes) { continue; }
            cf = file_nodes[rel];

            if "functions" in fe {
                for fn in fe["functions"] {
                    fn_node = Function(name=fn);
                    cf ++> fn_node;
                    func_by_file[rel][fn] = fn_node;
                    if fn not in func_global { func_global[fn] = fn_node; }
                }
            }
            if "classes" in fe {
                for cn in fe["classes"] {
                    c_node = Class(name=cn);
                    cf ++> c_node;
                    if cn not in cls_global { cls_global[cn] = c_node; }
                }
            }
        }
    }

    # Create relationship edges (Calls, Inherits, Imports)
    # Build typed edges directly if requested, otherwise use default edges
    edge_stats = {"calls": 0, "inherits": 0, "imports": 0};

    if "files" in entities {
        for fe2 in entities["files"] {
            rel = ""; mod_src = None;
            if "file" in fe2 {
                ap = fe2["file"];
                for k in file_nodes { if k in ap { rel = k; break; } }
            }
            if rel == "" { continue; }
            if rel in mod_of_file { mod_src = mod_of_file[rel]; }

            # Calls
            if ("calls" in fe2) and (rel in func_by_file) {
                for c in fe2["calls"] {
                    caller = None; callee = None;
                    if ("caller" in c) and (c["caller"] in func_by_file[rel]) { caller = func_by_file[rel][c["caller"]]; }
                    if ("callee" in c) {
                        if c["callee"] in func_global { callee = func_global[c["callee"]]; }
                        else {
                            if c["callee"] in cls_global { callee = cls_global[c["callee"]]; }
                        }
                    }
                    if caller != None and callee != None {
                        ln = 0; ctype = "direct";
                        if "line" in c { ln = c["line"]; }

                        if build_typed_edges {
                            # Create typed edge directly
                            try {
                                caller +>: Calls(line_number=ln, call_type=ctype) :+> callee;
                                edge_stats["calls"] += 1;
                            } except Exception as e {
                                # Fallback to default edge if typed edge fails
                                print(f"[build_repo_graph] Calls edge failed for {caller} -> {callee}: {str(e)}; falling back to default edge");
                                caller ++> callee;
                            }
                        } else {
                            # Use default edge and cache for later
                            caller ++> callee;
                            repo_node.ccg_calls.append({"caller": caller, "callee": callee, "line": ln, "type": ctype});
                        }
                    }
                }
            }

            # Inherits
            if "inherits" in fe2 {
                for inh in fe2["inherits"] {
                    if ("class" in inh) and ("base" in inh) {
                        sub = None; base = None;
                        if inh["class"] in cls_global { sub = cls_global[inh["class"]]; }
                        if inh["base"] in cls_global { base = cls_global[inh["base"]]; }
                        if sub != None and base != None {
                            itype = "extends";

                            if build_typed_edges {
                                # Create typed edge directly
                                try {
                                    sub +>: Inherits(inheritance_type=itype) :+> base;
                                    edge_stats["inherits"] += 1;
                                } except Exception as e {
                                    # Fallback to default edge if typed edge fails
                                    print(f"[build_repo_graph] Inherits edge failed for {sub} -> {base}: {str(e)}; falling back to default edge");
                                    sub ++> base;
                                }
                            } else {
                                # Use default edge and cache for later
                                sub ++> base;
                                repo_node.ccg_inherits.append({"sub": sub, "base": base, "type": itype});
                            }
                        }
                    }
                }
            }

            # Imports
            if (mod_src != None) and ("imports" in fe2) {
                for imp in fe2["imports"] {
                    tgt_name = ""; if "module" in imp { tgt_name = imp["module"]; }
                    if tgt_name == "" { continue; }
                    tgt = None;
                    if tgt_name in mod_global { tgt = mod_global[tgt_name]; }
                    else {
                        tgt = Module(name=tgt_name, import_path=tgt_name, is_external=True);
                        repo_node ++> tgt;
                        mod_global[tgt_name] = tgt;
                    }

                    al = ""; itype = "import";
                    if "alias" in imp { al = imp["alias"]; }
                    if "import_type" in imp { itype = imp["import_type"]; }

                    if build_typed_edges {
                        # Create typed edge directly
                        try {
                            mod_src +>: Imports(import_type=itype, alias=al) :+> tgt;
                            edge_stats["imports"] += 1;
                        } except Exception as e {
                            # Fallback to default edge if typed edge fails
                            print(f"[build_repo_graph] Imports edge failed for {mod_src} -> {tgt}: {str(e)}; falling back to default edge");
                            mod_src ++> tgt;
                        }
                    } else {
                        # Use default edge and cache for later
                        mod_src ++> tgt;
                        repo_node.ccg_imports.append({"src": mod_src, "dst": tgt, "alias": al, "import_type": itype});
                    }
                }
            }
        }
    }

    # Store edge statistics on the repository node
    if build_typed_edges {
        repo_node.ccg_stats = edge_stats;
        try { repo_node.file_tree = files; } except Exception as e { }
    }

    return repo_node;
}

#* EdgeBuilder: materializes typed edges (Calls, Inherits, Imports) from cached CCG relations *#
walker EdgeBuilder {
    has created: dict = {"calls": 0, "inherits": 0, "imports": 0};

    can materialize with Repository entry {
        # Calls
        for rel in here.ccg_calls {
            caller = None; callee = None; ln = 0; ctype = "direct";
            if "caller" in rel { caller = rel["caller"]; }
            if "callee" in rel { callee = rel["callee"]; }
            if "line" in rel { ln = rel["line"]; }
            if "type" in rel { ctype = rel["type"]; }
            if caller != None and callee != None {
                caller +>: Calls(line_number=ln, call_type=ctype) :+> callee;
                visitor.created["calls"] += 1;
            }
        }

        # Inherits
        for rel in here.ccg_inherits {
            sub = None; base = None; itype = "extends";
            if "sub" in rel { sub = rel["sub"]; }
            if "base" in rel { base = rel["base"]; }
            if "type" in rel { itype = rel["type"]; }
            if sub != None and base != None {
                sub +>: Inherits(inheritance_type=itype) :+> base;
                visitor.created["inherits"] += 1;
            }
        }

        # Imports
        for rel in here.ccg_imports {
            src = None; dst = None; al = ""; itype = "import";
            if "src" in rel { src = rel["src"]; }
            if "dst" in rel { dst = rel["dst"]; }
            if "alias" in rel { al = rel["alias"]; }
            if "import_type" in rel { itype = rel["import_type"]; }
            if src != None and dst != None {
                src +>: Imports(import_type=itype, alias=al) :+> dst;
                visitor.created["imports"] += 1;
            }
        }

        # Persist counts on the repo for later reporting
        here.ccg_stats = visitor.created;
        report visitor.created;
    }
}

# Utility function: compute stats from a Repository node (no traversal needed)
# Returns a dict similar to agents.CodeAnalyzer.basic_stats, plus CCG counts if available
# top_n controls truncation for top files lists

def collect_stats_from_repo(repo: Repository, top_n: int = 10) -> dict {
    if repo == None { return {}; }
    files = [];
    try { if "file_tree" in repo { files = repo.file_tree; } } except Exception as e { files = []; }

    total = 0; jac_files = 0; docs = 0; code_files = 0; python_files = 0;
    languages = {}; doc_kinds = {}; top_dirs = {}; tests_files = 0; examples_files = 0;
    top_dirs_code = {}; tests_code_files = 0; examples_code_files = 0;
    top_size = []; top_lines = [];

    for item in files {
        total += 1;
        has_path = ("path" in item);
        p = ""; if has_path { p = item["path"]; }
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
                inserted = False; i = 0;
                while i < len(top_size) {
                    if sz > top_size[i]["size"] {
                        top_size.insert(i, {"path": p, "size": sz});
                        inserted = True; break;
                    }
                    i += 1;
                }
                if not inserted { top_size.append({"path": p, "size": sz}); }
                if len(top_size) > top_n { top_size.pop(); }
            }
            # Track top N by lines for code files if provided
            if ("lines" in item) {
                ln = item["lines"];
                inserted2 = False; j = 0;
                while j < len(top_lines) {
                    if ln > top_lines[j]["lines"] {
                        top_lines.insert(j, {"path": p, "lines": ln});
                        inserted2 = True; break;
                    }
                    j += 1;
                }
                if not inserted2 { top_lines.append({"path": p, "lines": ln}); }
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

    # Prefer precise counts if present
    ccg_calls = 0; ccg_inherits = 0; ccg_imports = 0;
    try {
        if ("ccg_stats" in repo) {
            if ("calls" in repo.ccg_stats) { ccg_calls = repo.ccg_stats["calls"]; }
            if ("inherits" in repo.ccg_stats) { ccg_inherits = repo.ccg_stats["inherits"]; }
            if ("imports" in repo.ccg_stats) { ccg_imports = repo.ccg_stats["imports"]; }
        } else {
            if ("ccg_calls" in repo) { ccg_calls = len(repo.ccg_calls); }
            if ("ccg_inherits" in repo) { ccg_inherits = len(repo.ccg_inherits); }
            if ("ccg_imports" in repo) { ccg_imports = len(repo.ccg_imports); }
        }
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
        "ccg_counts": {"calls": ccg_calls, "inherits": ccg_inherits, "imports": ccg_imports}
    };
}

# Utility function: collect doc-relevant data from repo + entities
# Returns {"top_files": [...], "api_classes": [...], "total_functions": int}

def doc_collect(repo: Repository, entities: dict, top_n: int = 10) -> dict {
    if repo == None { return {"top_files": [], "api_classes": [], "total_functions": 0}; }
    files = [];
    try { if "file_tree" in repo { files = repo.file_tree; } } except Exception as e { files = []; }

    # Top files by lines and size, include optional metadata (size, language) when available
    top_lines = [];
    top_size = [];
    for item in files {
        if ("type" in item) and item["type"] == "CodeFile" {
            p = item.get("path", ""); ln = item.get("lines", 0); sz = item.get("size", 0);
            entry = {"path": p, "lines": ln};
            try { if ("size" in item) { entry["size"] = item["size"]; } } except Exception as e { }
            try { if ("language" in item) { entry["language"] = item["language"]; } } except Exception as e { }
            # Insert by lines
            inserted = False; i = 0;
            while i < len(top_lines) {
                if ln > top_lines[i]["lines"] { top_lines.insert(i, entry); inserted = True; break; }
                i += 1;
            }
            if not inserted { top_lines.append(entry); }
            if len(top_lines) > top_n { top_lines.pop(); }
            # Insert by size
            inserted2 = False; j = 0;
            while j < len(top_size) {
                cur = 0; try { if ("size" in top_size[j]) { cur = top_size[j]["size"]; } } except Exception as e { cur = 0; }
                if sz > cur { top_size.insert(j, entry); inserted2 = True; break; }
                j += 1;
            }
            if not inserted2 { top_size.append(entry); }
            if len(top_size) > top_n { top_size.pop(); }
        }
    }

    # API classes + total functions from entities
    api_classes = [];
    total_functions = 0;
    try {
        if (entities != None) and ("files" in entities) {
            # Dedup class names
            seen = {};
            for fe in entities["files"] {
                for cn in fe.get("classes", []) {
                    if cn not in seen { api_classes.append(cn); seen[cn] = True; }
                }
                total_functions += len(fe.get("functions", []));
            }
        }
    } except Exception as e { api_classes = api_classes; total_functions = total_functions; }

    return {"top_files": top_lines, "top_files_by_size": top_size, "api_classes": api_classes[0:top_n], "total_functions": total_functions};
}


#* StatsCollector: Traverses the graph and computes statistics *#
walker StatsCollector {
    has stats: dict = {};

    can collect with Repository entry {
        # Compute stats using repository.file_tree and CCG caches
        visitor.stats = collect_stats_from_repo(here, 10);
        # Persist on repo node for reuse
        try { here.stats = visitor.stats; } except Exception as e { }
        report visitor.stats;
    }
}

#* DocCollector: Traverses the graph and collects documentation-relevant data *#
walker DocCollector {
    has top_n: int = 10;
    has top_files: list = [];
    has top_files_by_size: list = [];
    has api_classes: list = [];
    has total_functions: int = 0;

    can collect with Repository entry {
        # Compute documentation-relevant aggregates from repo + entities snapshot
        ents = {};
        try { if ("entities" in here) { ents = here.entities; } } except Exception as e { ents = {}; }
        # Note: entities are not stored on repo by default; callers can pass via endpoint
        visitor.top_files = [];
        visitor.api_classes = [];
        visitor.total_functions = 0;
        res = doc_collect(here, ents, visitor.top_n);
        try {
            if ("top_files" in res) { visitor.top_files = res["top_files"]; }
            if ("top_files_by_size" in res) { visitor.top_files_by_size = res["top_files_by_size"]; }
            if ("api_classes" in res) { visitor.api_classes = res["api_classes"]; }
            if ("total_functions" in res) { visitor.total_functions = res["total_functions"]; }
        } except Exception as e { }
        report {"top_files": visitor.top_files, "top_files_by_size": visitor.top_files_by_size, "api_classes": visitor.api_classes, "total_functions": visitor.total_functions};
    }
}

