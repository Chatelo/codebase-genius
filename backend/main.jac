# Codebase Genius backend entry (JacLang)
# Sample AI-powered walker using by llm exposed via jac serve

import from byllm.llm { Model }
import from agents.DocGenie { docgen_summarize }
import from agents.Supervisor { build_overview }
import from graph.builders { build_repo_graph, EdgeBuilder }
import from utils.diagram_gen { make_call_graph_mermaid, make_class_hierarchy_mermaid, make_module_graph_mermaid }

glob llm = Model(model_name="gpt-4o-mini");

# AI function (not a walker ability) powered by byLLM
#* Generate a friendly greeting for the given name. *#
def make_greeting(name: str) -> str by llm(method="Reason");

walker api_hello {
    has who: str = "Codebase Genius";
    has use_llm: bool = False;  # Toggle to call LLM or use fallback

    obj __specs__ {
        # Make this walker publicly callable via REST (no auth for smoke test)
        static has auth: bool = False;
        # static has methods: list = ["post"];  # default is POST
    }

    can process with `root entry {
        msg = "";
        if self.use_llm {
            msg = make_greeting(self.who);
        } else {
            msg = f"Hello, {self.who}!";
        }
        report {
            "status": "success",
            "message": msg
        };
    }
}


walker generate_docs {
    has repo_url: str = "";
    has depth: str = "standard";
    has use_llm: bool = False;
    has include_diagrams: bool = False;
    has exclude_dirs: list = [];

    #* Sensible defaults: filter out binaries/notebooks and focus on code+docs *#
    has exclude_globs: list = [
        "**/*.ipynb", "**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.gif", "**/*.svg",
        "**/*.ico", "**/*.pdf", "**/*.zip", "**/*.tar", "**/*.gz", "**/*.xz",
        "**/*.7z", "**/*.rar", "**/*.exe", "**/*.dll", "**/*.so", "**/*.dylib",
        "**/*.class", "**/*.jar", "**/*.min.js", "**/*.lock", "**/*.bin",
        "**/.DS_Store", "**/.coverage*", "**/*.map"
    ];
    has include_exts: list = [
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".rb",
        ".php", ".cs", ".cpp", ".c", ".h", ".jac", ".md", ".rst"
    ];
    has include_globs: list = [];
    has include_paths: list = [];
    has max_files: int = 0;
    has max_file_size_bytes: int = 0;
    has top_n: int = 10;

    obj __specs__ {
        static has auth: bool = False;
    }

    can process with `root entry {
        # Build an overview via Supervisor helpers (stub unless depth=="deep")
        overview = build_overview(self.repo_url, self.depth, self.exclude_dirs, self.exclude_globs, self.include_exts, self.include_globs, self.include_paths, self.max_files, self.max_file_size_bytes, self.top_n);
        file_tree = overview["file_tree"];
        stats = overview["stats"];
        entities = {};
        if "entities" in overview { entities = overview["entities"]; }

        # Build the Code Context Graph (CCG) from files + entities
        try {
            _repo_node = build_repo_graph(here, self.repo_url, file_tree, entities);
        } except Exception as e {
            # Non-fatal: proceed even if graph build fails
            _repo_node = None;
        }

            # Materialize typed edges via EdgeBuilder walker (non-fatal)
            if _repo_node != None {
                try { EdgeBuilder() spawn _repo_node; } except Exception as e { }
            }


        # Prepare richer extra context for the LLM
        langs = "{}";
        if "languages" in stats { langs = str(stats["languages"]); }
        tdirs = "{}";
        if "top_dirs_code" in stats { tdirs = str(stats["top_dirs_code"]); }
        t_code = 0;
        if "tests_code_files" in stats { t_code = stats["tests_code_files"]; }
        e_code = 0;
        if "examples_code_files" in stats { e_code = stats["examples_code_files"]; }
        extra_context = f"Files={stats['files']}, Code={stats['code_files']}, Python={stats['python_files']}, Docs={stats['docs']}, Tests={stats['tests_files']}(code={t_code}), Examples={stats['examples_files']}(code={e_code}), Languages={langs}, TopDirsByCode={tdirs}, TopN={self.top_n}. Diagrams={self.include_diagrams}.";

        # Build Top Files (by lines) summary
        top_files_str = "";
        if "top_files_by_lines" in stats {
            i = 0;
            for entry in stats["top_files_by_lines"] {
                if i >= self.top_n { break; }
                pth = ""; ln = 0;
                if "path" in entry { pth = entry["path"]; }
                if "lines" in entry { ln = entry["lines"]; }
                if top_files_str != "" { top_files_str += ", "; }
                top_files_str += f"{pth} ({ln} loc)";
                i += 1;
            }
        }

        # Build API surface summary (classes + total functions)
        api_surface = "";
        if ("files" in entities) {
            classes = [];
            funcs_total = 0;
            for f in entities["files"] {
                if ("classes" in f) {
                    for cname in f["classes"] {
                        # Dedup class names
                        is_dup = False; k = 0;
                        while k < len(classes) {
                            if classes[k] == cname { is_dup = True; break; }
                            k += 1;
                        }
                        if not is_dup { classes.append(cname); }
                    }
                }
                if ("functions" in f) {
                    funcs_total += len(f["functions"]);
                }
            }
            # Take top N class names
            cls_str = ""; j = 0;
            for cname in classes {
                if j >= self.top_n { break; }
                if cls_str != "" { cls_str += ", "; }
                cls_str += cname;
                j += 1;
            }
            api_surface = f"Classes: [{cls_str}]; Total functions: {funcs_total}";
        }


        # Generate documentation (stub or LLM)
        doc = "";
        if self.use_llm {
            prompt = f"Generate high-level documentation for repo: {self.repo_url}. Depth: {self.depth}. " + extra_context + f" TopFilesByLines: [{top_files_str}]. API: {api_surface}.";
            doc = docgen_summarize(self.repo_url, self.depth, prompt);
        } else {
            doc = f"[Stub] Documentation for {self.repo_url} (depth={self.depth}, diagrams={self.include_diagrams})";
        }

        ccg = {"calls": 0, "inherits": 0, "imports": 0};
        if _repo_node != None {
            # raw cache sizes
            ccg["calls"] = len(_repo_node.ccg_calls);
            ccg["inherits"] = len(_repo_node.ccg_inherits);
            ccg["imports"] = len(_repo_node.ccg_imports);
            # prefer precise counts from EdgeBuilder if present
            try {
                ccg_stats = _repo_node.ccg_stats;
                if ("calls" in ccg_stats) { ccg["calls"] = ccg_stats["calls"]; }
                if ("inherits" in ccg_stats) { ccg["inherits"] = ccg_stats["inherits"]; }
                if ("imports" in ccg_stats) { ccg["imports"] = ccg_stats["imports"]; }
            } except Exception as e { }
        }
        # Fallback: if graph-derived counts are 0, estimate from raw entities
        try {
            if (ccg["calls"] == 0) or (ccg["inherits"] == 0) or (ccg["imports"] == 0) {
                if ("files" in entities) {
                    calls_e = 0; inh_e = 0; imp_e = 0;
                    for f in entities["files"] {
                        if ("calls" in f) { calls_e += len(f["calls"]); }
                        if ("inherits" in f) { inh_e += len(f["inherits"]); }
                        if ("imports" in f) { imp_e += len(f["imports"]); }
                    }
                    if ccg["calls"] == 0 { ccg["calls"] = calls_e; }
                    if ccg["inherits"] == 0 { ccg["inherits"] = inh_e; }
                    if ccg["imports"] == 0 { ccg["imports"] = imp_e; }
                }
            }
        } except Exception as e { }


        # Optional Mermaid diagrams
        diagrams = {};
        if self.include_diagrams {
            try {
                diagrams["call_graph"] = make_call_graph_mermaid(entities);
                diagrams["class_hierarchy"] = make_class_hierarchy_mermaid(entities);
                diagrams["module_graph"] = make_module_graph_mermaid(entities);
            } except Exception as e { diagrams = {}; }
        }

        report {
            "status": "success",
            "repo_url": self.repo_url,
            "depth": self.depth,
            "include_diagrams": self.include_diagrams,
            "file_tree": file_tree,
            "stats": stats,
            "entities": entities,
            "ccg": ccg,
            "documentation": doc,
            "diagrams": diagrams
        };
    }
}


