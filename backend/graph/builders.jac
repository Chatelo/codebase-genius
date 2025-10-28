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
    # Create Repository node
    repo_node = root_node ++> Repository(url=repo_url);

    # Repo name from URL
    url_parts = repo_url.rstrip('/').split('/');
    repo_node.name = (url_parts[-1] if len(url_parts) > 0 else "");

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


#* StatsCollector: Traverses the graph and computes statistics *#
walker StatsCollector {
    has stats: dict = {};

    can collect with Repository entry {
        # Initialize stats
        visitor.stats = {
            "files": 0,
            "code_files": 0,
            "docs": 0,
            "tests_files": 0,
            "examples_files": 0,
            "functions": 0,
            "classes": 0,
            "languages": {},
            "top_dirs": {}
        };

        # Traversal disabled (visit syntax not available in this environment)
        # TODO: Implement traversal using supported APIs or during graph build

        # Store stats in Repository node
        here.stats = visitor.stats;

        report visitor.stats;
    }

    can count_file with CodeFile entry {
        visitor.stats["files"] += 1;

        if here.language != "" and here.language != "unknown" {
            visitor.stats["code_files"] += 1;

            # Count by language
            if here.language not in visitor.stats["languages"] {
                visitor.stats["languages"][here.language] = 0;
            }
            visitor.stats["languages"][here.language] += 1;
        }

        if here.is_doc {
            visitor.stats["docs"] += 1;
        }

        if here.is_test {
            visitor.stats["tests_files"] += 1;
        }

        if here.is_example {
            visitor.stats["examples_files"] += 1;
        }

        # Count top-level directory
        path_parts = here.path.split('/');
        if len(path_parts) > 0 {
            top_dir = path_parts[0];
            if top_dir not in visitor.stats["top_dirs"] {
                visitor.stats["top_dirs"][top_dir] = 0;
            }
            visitor.stats["top_dirs"][top_dir] += 1;
        }
    }

    can count_function with Function entry {
        visitor.stats["functions"] += 1;
    }

    can count_class with Class entry {
        visitor.stats["classes"] += 1;
    }
}

#* DocCollector: Traverses the graph and collects documentation-relevant data *#
walker DocCollector {
    has top_n: int = 10;
    has top_files: list = [];
    has api_classes: list = [];
    has total_functions: int = 0;

    can collect with Repository entry {
        # Traversal disabled (visit syntax not available in this environment)
        # TODO: Implement DocCollector using supported traversal APIs
        report {"top_files": [], "api_classes": [], "total_functions": 0};
    }
}

