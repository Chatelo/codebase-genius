# Codebase Genius backend entry (JacLang)
# Sample AI-powered walker using by llm exposed via jac serve

import from byllm.llm { Model }
import from agents.DocGenie { docgen_summarize }
import from agents.Supervisor { build_overview }
import from agents.CodeAnalyzer { ccg_get_callers, ccg_get_callees, ccg_get_subclasses, ccg_get_dependencies }

import from graph.builders { build_repo_graph, collect_stats_from_repo, doc_collect }
import from utils.diagram_gen { make_call_graph_mermaid, make_class_hierarchy_mermaid, make_module_graph_mermaid }
import from utils.output { save_results_to_disk }
import from utils.cache { get_cache }


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
    has use_cache: bool = True;
    has include_diagrams: bool = False;
    has diagram_filter_tests: bool = False;
    has diagram_max_edges_call: int = 400;
    has diagram_max_edges_class: int = 400;
    has diagram_max_edges_module: int = 400;
    has exclude_dirs: list = [];
    has save_locally: bool = True;
    has outputs_dir: str = "outputs";
    has job_id: str = "";


    has return_full_data: bool = True;

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
        cache = get_cache();
        step_total = 7;
        if self.include_diagrams { step_total = 8; }
        # Initial progress
        if self.job_id != "" {
            try { cache.set("progress", self.repo_url, {"percent": 5, "stage": "start", "message": "Starting analysis", "step_index": 0, "step_total": step_total}, job_id=self.job_id); } except Exception as e { }
        }
        # Validate input
        if self.repo_url == "" {
            report {
                "status": "error",
                "error_type": "ValidationError",
                "message": "repo_url is required",
                "status_code": 400
            };
        }

        # Build an overview via Supervisor helpers (stub unless depth=="deep")
        overview = build_overview(self.repo_url, self.depth, self.exclude_dirs, self.exclude_globs, self.include_exts, self.include_globs, self.include_paths, self.max_files, self.max_file_size_bytes, self.top_n, self.use_cache, self.job_id);
        file_tree = overview["file_tree"];
        stats = overview["stats"];
        entities = {};
        if "entities" in overview { entities = overview["entities"]; }
        plan = {};
        scheduler = {};
        if "plan" in overview { plan = overview["plan"]; }
        if "scheduler" in overview { scheduler = overview["scheduler"]; }

        if self.job_id != "" {
            try { cache.set("progress", self.repo_url, {"percent": 60, "stage": "overview", "message": "Repository analyzed", "step_index": 3, "step_total": step_total}, job_id=self.job_id); } except Exception as e { }
        }
        # Fatal: repo clone/access errors  stop early with clear message
        if ("error" in overview) {
            err_msg = overview["error"];
            if ("Failed to clone repository" in err_msg) or ("GitPython is not available" in err_msg) or ("Git is not available" in err_msg) or ("Invalid GitHub URL" in err_msg) or ("Repository not found at" in err_msg) or ("Network timeout while cloning" in err_msg) {
                if self.job_id != "" {
                    try { cache.set("progress", self.repo_url, {"percent": 15, "stage": "clone", "message": err_msg}, job_id=self.job_id); } except Exception as e { }
                }
                report {
                    "status": "error",
                    "error_type": "RepoAccessError",
                    "message": err_msg,
                    "repo_url": self.repo_url,
                    "job_id": self.job_id,
                    "status_code": 400
                };
            }
        }



        # Build the Code Context Graph (CCG) from files + entities
        graph_error = "";
        try {
            _repo_node = build_repo_graph(here, self.repo_url, file_tree, entities);
        } except Exception as e {
            # Non-fatal: proceed even if graph build fails
            _repo_node = None;
            graph_error = str(e);
            print(f"[generate_docs] Graph build error: {graph_error}");
        }

        if self.job_id != "" {
            prog = {"percent": 75, "stage": "graph", "message": "Code graph built", "step_index": 4, "step_total": step_total};
            if _repo_node == None {
                prog["percent"] = 65;
                prog["message"] = f"Graph build failed: {graph_error}";
            }
            try { cache.set("progress", self.repo_url, prog, job_id=self.job_id); } except Exception as e { }
        }

            # NOTE: EdgeBuilder pass removed; build_repo_graph creates typed edges directly


        # Extract README summary if available
        readme_summary = "";
        if "readme_summary" in overview { readme_summary = overview["readme_summary"]; }

        # Prepare richer extra context for the LLM
        langs = "{}";
        if "languages" in stats { langs = str(stats["languages"]); }
        tdirs = "{}";
        if "top_dirs_code" in stats { tdirs = str(stats["top_dirs_code"]); }
        t_code = 0;
        if "tests_code_files" in stats { t_code = stats["tests_code_files"]; }
        e_code = 0;
        if "examples_code_files" in stats { e_code = stats["examples_code_files"]; }

        # Include README summary if available
        readme_context = "";
        if readme_summary != "" { readme_context = f" README: {readme_summary}"; }

        extra_context = f"Files={stats['files']}, Code={stats['code_files']}, Python={stats['python_files']}, Docs={stats['docs']}, Tests={stats['tests_files']}(code={t_code}), Examples={stats['examples_files']}(code={e_code}), Languages={langs}, TopDirsByCode={tdirs}, TopN={self.top_n}. Diagrams={self.include_diagrams}.{readme_context}";

        # Briefly include plan/scheduler hints for LLM if available (non-intrusive)
        ep_summary = "";
        try {
            eps = [];
            if "entry_points" in plan { eps = plan["entry_points"]; }
            # show up to 5 entry points
            i = 0;
            for ep in eps {
                if i >= 5 { break; }
                p = "";
                try { p = ep.get("path", ""); } except Exception as e { p = ""; }
                if p != "" { if ep_summary != "" { ep_summary += ", "; } ep_summary += p; i += 1; }
            }
        } except Exception as e { ep_summary = ""; }

        sched_summary = "";
        try {
            iters = [];
            if "iterations" in scheduler { iters = scheduler["iterations"]; }
            # take first 2 iterations, up to 5 files each
            j = 0;
            for it in iters {
                if j >= 2 { break; }
                sel = [];
                try { sel = it.get("selected", []); } except Exception as e { sel = []; }
                k = 0; sel_str = "";
                for f in sel {
                    if k >= 5 { break; }
                    if sel_str != "" { sel_str += ", "; }
                    sel_str += f; k += 1;
                }
                if sel_str != "" {
                    if sched_summary != "" { sched_summary += " | "; }
                    sched_summary += sel_str;
                }
                j += 1;
            }
        } except Exception as e { sched_summary = ""; }

        if ep_summary != "" { extra_context += f" EntryPoints=[{ep_summary}]"; }
        if sched_summary != "" { extra_context += f" SchedulerBatches=[{sched_summary}]"; }

        # CCG citations: callers/callees/subclasses/dependencies (kept concise)
        ccg_context = ""; ccg_mermaid = "";
        try {
            if _repo_node != None {
                # Top functions by fan-in
                fin = {}; fout = {};
                try {
                    for rel in _repo_node.ccg_calls {
                        callee = None; caller = None;
                        if "callee" in rel { callee = rel["callee"]; }
                        if "caller" in rel { caller = rel["caller"]; }
                        if callee != None {
                            n = callee.name; if n not in fin { fin[n] = 0; } fin[n] += 1;
                        }
                        if caller != None {
                            n2 = caller.name; if n2 not in fout { fout[n2] = 0; } fout[n2] += 1;
                        }
                    }
                } except Exception as e { }

                # Rank functions by fan-in (desc)
                ranked_funcs = [];
                for k in fin {
                    entry = {"name": k, "count": fin[k]};
                    ins = False; i = 0;
                    while i < len(ranked_funcs) {
                        if entry["count"] > ranked_funcs[i]["count"] { ranked_funcs.insert(i, entry); ins = True; break; }
                        i += 1;
                    }
                    if not ins { ranked_funcs.append(entry); }
                }

                # Build callers/callees summary for top 3 functions
                funcs_summary = ""; i = 0; mm_done = False;
                for rf in ranked_funcs {
                    if i >= 3 { break; }
                    fn = rf["name"];
                    callers = []; callees = [];
                    try { callers = ccg_get_callers(_repo_node, fn); } except Exception as e { callers = []; }
                    try { callees = ccg_get_callees(_repo_node, fn); } except Exception as e { callees = []; }
                    # Dedup and take up to 3 names
                    c_names = []; j = 0;
                    for c in callers { if ("name" in c) {
                        nm = c["name"]; dup = False; t = 0; while t < len(c_names) { if c_names[t] == nm { dup = True; break; } t += 1; }
                        if not dup { c_names.append(nm); }
                    } }
                    cal_names = []; j2 = 0;
                    for c2 in callees { if ("name" in c2) {
                        nm2 = c2["name"]; dup2 = False; u = 0; while u < len(cal_names) { if cal_names[u] == nm2 { dup2 = True; break; } u += 1; }
                        if not dup2 { cal_names.append(nm2); }
                    } }
                    # Trim to 3
                    c_str = ""; a = 0; for nm3 in c_names { if a >= 3 { break; } if c_str != "" { c_str += ", "; } c_str += nm3; a += 1; }
                    cal_str = ""; b = 0; for nm4 in cal_names { if b >= 3 { break; } if cal_str != "" { cal_str += ", "; } cal_str += nm4; b += 1; }
                    if funcs_summary != "" { funcs_summary += " | "; }
                    funcs_summary += f"{fn}: callers=[{c_str}], callees=[{cal_str}]";

                    # Micro-mermaid for the first function only
                    if not mm_done {
                        mm_edges = "";
                        # callers -> fn
                        a2 = 0; for nm5 in c_names { if a2 >= 3 { break; } if mm_edges != "" { mm_edges += " "; } mm_edges += f"{nm5}-->{fn};"; a2 += 1; }
                        # fn -> callees
                        b2 = 0; for nm6 in cal_names { if b2 >= 3 { break; } if mm_edges != "" { mm_edges += " "; } mm_edges += f"{fn}-->{nm6};"; b2 += 1; }
                        if mm_edges != "" { ccg_mermaid = f"```mermaid graph LR; {mm_edges}```"; }
                        mm_done = True;
                    }
                    i += 1;
                }

                # Classes: pick top 3 by subclass count
                classes_all = [];
                try {
                    if ("files" in entities) {
                        for f in entities["files"] { if ("classes" in f) { for cn in f["classes"] {
                            # Dedup class names
                            is_dup = False; z = 0; while z < len(classes_all) { if classes_all[z] == cn { is_dup = True; break; } z += 1; }
                            if not is_dup { classes_all.append(cn); }
                        } } }
                    }
                } except Exception as e { classes_all = []; }
                cls_counts = [];
                for cn2 in classes_all {
                    subs = []; try { subs = ccg_get_subclasses(_repo_node, cn2); } except Exception as e { subs = []; }
                    cnt = 0; for s in subs { cnt += 1; }
                    entry2 = {"name": cn2, "count": cnt};
                    ins2 = False; y = 0; while y < len(cls_counts) {
                        if entry2["count"] > cls_counts[y]["count"] { cls_counts.insert(y, entry2); ins2 = True; break; }
                        y += 1;
                    }
                    if not ins2 { cls_counts.append(entry2); }
                }
                classes_summary = ""; k2 = 0;
                for cc in cls_counts {
                    if k2 >= 2 { break; }
                    cn3 = cc["name"]; subs2 = []; try { subs2 = ccg_get_subclasses(_repo_node, cn3); } except Exception as e { subs2 = []; }
                    s_str = ""; w = 0; for s in subs2 { if ("name" in s) { if w >= 3 { break; } if s_str != "" { s_str += ", "; } s_str += s["name"]; w += 1; } }
                    if classes_summary != "" { classes_summary += " | "; }
                    classes_summary += f"{cn3}: subclasses=[{s_str}]";
                    k2 += 1;
                }

                # Modules: derive from entities and list deps
                mods_all = [];
                try {
                    if ("files" in entities) {
                        for f in entities["files"] { if ("module" in f) {
                            mn = f["module"]; if mn != "" {
                                dupm = False; q = 0; while q < len(mods_all) { if mods_all[q] == mn { dupm = True; break; } q += 1; }
                                if not dupm { mods_all.append(mn); }
                            }
                        } }
                    }
                } except Exception as e { mods_all = []; }
                # Rank by number of dependencies (outgoing imports)
                mod_counts = [];
                for mn2 in mods_all {
                    deps = []; try { deps = ccg_get_dependencies(_repo_node, mn2); } except Exception as e { deps = []; }
                    mc = 0; for d in deps { mc += 1; }
                    entry3 = {"name": mn2, "count": mc};
                    ins3 = False; r = 0; while r < len(mod_counts) {
                        if entry3["count"] > mod_counts[r]["count"] { mod_counts.insert(r, entry3); ins3 = True; break; }
                        r += 1;
                    }
                    if not ins3 { mod_counts.append(entry3); }
                }
                mods_summary = ""; k3 = 0;
                for md in mod_counts {
                    if k3 >= 2 { break; }
                    mn3 = md["name"]; deps2 = []; try { deps2 = ccg_get_dependencies(_repo_node, mn3); } except Exception as e { deps2 = []; }
                    d_str = ""; v = 0; for d in deps2 { if ("name" in d) { if v >= 3 { break; } if d_str != "" { d_str += ", "; } d_str += d["name"]; v += 1; } }
                    if mods_summary != "" { mods_summary += " | "; }
                    mods_summary += f"{mn3}: imports=[{d_str}]";
                    k3 += 1;
                }

                # Combine
                ccg_parts = [];
                if funcs_summary != "" { ccg_parts.append(f"Funcs: {funcs_summary}"); }
                if classes_summary != "" { ccg_parts.append(f"Classes: {classes_summary}"); }
                if mods_summary != "" { ccg_parts.append(f"Modules: {mods_summary}"); }
                if len(ccg_parts) > 0 { ccg_context = " ".join(ccg_parts); }
            }
        } except Exception as e { ccg_context = ""; ccg_mermaid = ""; }

        if ccg_context != "" { extra_context += f" CCGRels={{ {ccg_context} }}"; }
        if ccg_mermaid != "" { extra_context += f" CCGDiagram={ccg_mermaid}"; }


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


        # Generate documentation overview (stub or LLM)
        doc_overview = "";
        if self.use_llm {
            prompt = f"Generate high-level documentation for repo: {self.repo_url}. Depth: {self.depth}. " + extra_context + f" TopFilesByLines: [{top_files_str}]. API: {api_surface}.";
            doc_overview = docgen_summarize(self.repo_url, self.depth, prompt);
        } else {
            doc_overview = f"[Overview] Documentation for {self.repo_url} (depth={self.depth}, diagrams={self.include_diagrams})";
        }
        if self.job_id != "" {
            try { cache.set("progress", self.repo_url, {"percent": 85, "stage": "docs", "message": "Documentation overview generated", "step_index": 5, "step_total": step_total}, job_id=self.job_id); } except Exception as e { }
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
                diagrams["call_graph"] = make_call_graph_mermaid(entities, self.diagram_max_edges_call, self.diagram_filter_tests);
                diagrams["class_hierarchy"] = make_class_hierarchy_mermaid(entities, self.diagram_max_edges_class, self.diagram_filter_tests);
                diagrams["module_graph"] = make_module_graph_mermaid(entities, self.diagram_max_edges_module, self.diagram_filter_tests);
            } except Exception as e { diagrams = {}; }
            if self.job_id != "" {
                try { cache.set("progress", self.repo_url, {"percent": 95, "stage": "diagrams", "message": "Diagrams generated", "step_index": 6, "step_total": step_total}, job_id=self.job_id); } except Exception as e { }
            }
        } else {
            if self.job_id != "" {
                try { cache.set("progress", self.repo_url, {"percent": 90, "stage": "docs", "message": "Documentation ready", "step_index": 5, "step_total": step_total}, job_id=self.job_id); } except Exception as e { }
            }

        }

        # Compose structured Markdown documentation with required sections
        title_md = "# Documentation for " + self.repo_url + "\n\n";
        overview_md = "## Project Overview\n\n";
        ov_text = doc_overview;
        if ov_text == "" { ov_text = "No overview generated."; }
        overview_md += ov_text + "\n\n";

        # Installation and Usage from README (best-effort)
        inst_txt = ""; use_txt = "";
        try {
            if ("readme" in overview) {
                rd = overview["readme"];
                if ("sections" in rd) {
                    for sec in rd["sections"] {
                        t = ""; try { t = sec["title"].lower(); } except Exception as e { t = ""; }
                        if (inst_txt == "") and ("install" in t) { try { inst_txt = sec["content"]; } except Exception as e { inst_txt = ""; } }
                        if (use_txt == "") and (("usage" in t) or ("use" in t) or ("run" in t) or ("quick start" in t)) { try { use_txt = sec["content"]; } except Exception as e { use_txt = ""; } }
                    }
                }
            }
        } except Exception as e { inst_txt = inst_txt; use_txt = use_txt; }
        inst_md = "## Installation\n\n" + (inst_txt if (inst_txt != "") else "Refer to the repository README for installation instructions.") + "\n\n";
        use_md = "## Usage\n\n" + (use_txt if (use_txt != "") else "Refer to the repository README for usage examples.") + "\n\n";

        # API Reference summary (from earlier surface + counts)
        api_md = "## API Reference (summary)\n\n";
        if api_surface != "" { api_md += api_surface + "\n"; }
        try { api_md += f"CCG counts — calls: {ccg['calls']}, inherits: {ccg['inherits']}, imports: {ccg['imports']}\n"; } except Exception as e { }
        if top_files_str != "" { api_md += f"Top files by lines: {top_files_str}\n"; }
        api_md += "\n";

        # Diagrams (embed Mermaid when available)
        diagrams_md = "## Diagrams\n\n";
        if self.include_diagrams {
            try {
                if ("call_graph" in diagrams) { diagrams_md += f"```mermaid\n{diagrams['call_graph']}\n```\n\n"; }
                if ("class_hierarchy" in diagrams) { diagrams_md += f"```mermaid\n{diagrams['class_hierarchy']}\n```\n\n"; }
                if ("module_graph" in diagrams) { diagrams_md += f"```mermaid\n{diagrams['module_graph']}\n```\n\n"; }
            } except Exception as e { diagrams_md += "Diagrams not available.\n\n"; }
        } else {
            diagrams_md += "Diagrams disabled for this run.\n\n";
        }

        # Citations from CCG summaries
        cites_md = "## Citations (CCG)\n\n";
        if ccg_context != "" { cites_md += ccg_context + "\n\n"; }
        if ccg_mermaid != "" { cites_md += ccg_mermaid + "\n\n"; }

        # Final document
        doc = title_md + overview_md + inst_md + use_md + api_md + diagrams_md + cites_md;

        # Save to disk if enabled
        saved_paths = {};
        if self.save_locally {
            try {
                saved_paths = save_results_to_disk(self.repo_url, doc, diagrams, stats, self.outputs_dir);
            } except Exception as e { saved_paths = {}; }
        }
        if self.job_id != "" {
            try { cache.set("progress", self.repo_url, {"percent": 100, "stage": "done", "message": "Completed", "step_index": step_total, "step_total": step_total}, job_id=self.job_id); } except Exception as e { }
        }


        # Optionally reduce response payload
        rtree = file_tree;
        rentities = entities;
        if not self.return_full_data {
            rtree = [];
            rentities = {"files": []};
        }

        # Collect errors to include in response (non-breaking addition)
        errors_obj = {};
        try { if "errors" in entities { errors_obj["entities"] = entities["errors"]; } } except Exception as e { }
        try { if "error" in overview { errors_obj["overview"] = overview["error"]; } } except Exception as e { }
        if graph_error != "" { errors_obj["graph"] = graph_error; }


        report {
            "status": "success",
            "repo_url": self.repo_url,
            "job_id": self.job_id,
            "depth": self.depth,
            "include_diagrams": self.include_diagrams,
            "file_tree": rtree,
            "stats": stats,
            "entities": rentities,
            "plan": plan,
            "scheduler": scheduler,
            "ccg": ccg,
            "documentation": doc,
            "diagrams": diagrams,
            "saved": saved_paths,
            "errors": errors_obj
        };
    }
}



walker api_get_progress {
    has repo_url: str = "";
    has job_id: str = "";

    obj __specs__ { static has auth: bool = False; }

    can process with `root entry {
        cache = get_cache();
        prog = {};
        try {
            if (self.repo_url != "") and (self.job_id != "") {
                p = cache.get("progress", self.repo_url, job_id=self.job_id);
                if p != None { prog = p; }
            }
        } except Exception as e { }
        report {
            "status": "success",
            "repo_url": self.repo_url,
            "job_id": self.job_id,
            "progress": prog
        };
    }
}


# CCG query endpoints
walker api_ccg_callers {
    has repo_url: str = "";
    has func_name: str = "";
    has depth: str = "deep";

    obj __specs__ { static has auth: bool = False; }

    can process with `root entry {
        if (self.repo_url == "") or (self.func_name == "") {
            report {"status": "error", "message": "repo_url and func_name are required", "status_code": 400};
        }
        ov = build_overview(self.repo_url, self.depth);
        ents = {}; if "entities" in ov { ents = ov["entities"]; }
        ft = []; if "file_tree" in ov { ft = ov["file_tree"]; }
        _repo_node = None; gerr = "";
        try { _repo_node = build_repo_graph(here, self.repo_url, ft, ents); } except Exception as e { _repo_node = None; gerr = str(e); }
        res = []; err = gerr;
        if _repo_node != None {
            try { res = ccg_get_callers(_repo_node, self.func_name); } except Exception as e { err = str(e); res = []; }
        }
        report {"status": "success", "repo_url": self.repo_url, "func_name": self.func_name, "results": res, "error": err};
    }
}

walker api_ccg_callees {
    has repo_url: str = "";
    has func_name: str = "";
    has depth: str = "deep";

    obj __specs__ { static has auth: bool = False; }

    can process with `root entry {
        if (self.repo_url == "") or (self.func_name == "") {
            report {"status": "error", "message": "repo_url and func_name are required", "status_code": 400};
        }
        ov = build_overview(self.repo_url, self.depth);
        ents = {}; if "entities" in ov { ents = ov["entities"]; }
        ft = []; if "file_tree" in ov { ft = ov["file_tree"]; }
        _repo_node = None; gerr = "";
        try { _repo_node = build_repo_graph(here, self.repo_url, ft, ents); } except Exception as e { _repo_node = None; gerr = str(e); }
        res = []; err = gerr;
        if _repo_node != None {
            try { res = ccg_get_callees(_repo_node, self.func_name); } except Exception as e { err = str(e); res = []; }
        }
        report {"status": "success", "repo_url": self.repo_url, "func_name": self.func_name, "results": res, "error": err};
    }
}


walker api_ccg_subclasses {
    has repo_url: str = "";
    has class_name: str = "";
    has depth: str = "deep";

    obj __specs__ { static has auth: bool = False; }

    can process with `root entry {
        if (self.repo_url == "") or (self.class_name == "") {
            report {"status": "error", "message": "repo_url and class_name are required", "status_code": 400};
        }
        ov = build_overview(self.repo_url, self.depth);
        ents = {}; if "entities" in ov { ents = ov["entities"]; }
        ft = []; if "file_tree" in ov { ft = ov["file_tree"]; }
        _repo_node = None; gerr = "";
        try { _repo_node = build_repo_graph(here, self.repo_url, ft, ents); } except Exception as e { _repo_node = None; gerr = str(e); }
        res = []; err = gerr;
        if _repo_node != None {
            try { res = ccg_get_subclasses(_repo_node, self.class_name); } except Exception as e { err = str(e); res = []; }
        }
        report {"status": "success", "repo_url": self.repo_url, "class_name": self.class_name, "results": res, "error": err};
    }
}

walker api_ccg_dependencies {
    has repo_url: str = "";
    has module_name: str = "";
    has depth: str = "deep";

    obj __specs__ { static has auth: bool = False; }

    can process with `root entry {
        if (self.repo_url == "") or (self.module_name == "") {
            report {"status": "error", "message": "repo_url and module_name are required", "status_code": 400};
        }
        ov = build_overview(self.repo_url, self.depth);
        ents = {}; if "entities" in ov { ents = ov["entities"]; }
        ft = []; if "file_tree" in ov { ft = ov["file_tree"]; }
        _repo_node = None; gerr = "";
        try { _repo_node = build_repo_graph(here, self.repo_url, ft, ents); } except Exception as e { _repo_node = None; gerr = str(e); }
        res = []; err = gerr;
        if _repo_node != None {
            try { res = ccg_get_dependencies(_repo_node, self.module_name); } except Exception as e { err = str(e); res = []; }
        }
        report {"status": "success", "repo_url": self.repo_url, "module_name": self.module_name, "results": res, "error": err};
    }
}


# Compact graph traversal: return counts and top-N over relationships
walker api_ccg_overview {
    has repo_url: str = "";
    has depth: str = "deep";
    has top_n: int = 5;

    obj __specs__ { static has auth: bool = False; }

    can process with `root entry {
        if self.repo_url == "" { report {"status": "error", "message": "repo_url is required", "status_code": 400}; }
        ov = build_overview(self.repo_url, self.depth);
        ents = {}; if "entities" in ov { ents = ov["entities"]; }
        ft = []; if "file_tree" in ov { ft = ov["file_tree"]; }
        _repo_node = None; gerr = "";
        try { _repo_node = build_repo_graph(here, self.repo_url, ft, ents); } except Exception as e { _repo_node = None; gerr = str(e); }
        out = {"counts": {"calls": 0, "inherits": 0, "imports": 0}, "top": {"functions": [], "classes": [], "modules": []}, "error": gerr};
        if _repo_node != None {
            # counts
            try {
                out["counts"]["calls"] = len(_repo_node.ccg_calls);
                out["counts"]["inherits"] = len(_repo_node.ccg_inherits);
                out["counts"]["imports"] = len(_repo_node.ccg_imports);
            } except Exception as e { }
            # top functions by fan-in
            fin = {};
            try { for rel in _repo_node.ccg_calls { if ("callee" in rel) and (rel["callee"] != None) {
                nm = rel["callee"].name; if nm not in fin { fin[nm] = 0; } fin[nm] += 1; } } } except Exception as e { fin = {}; }
            funcs = [];
            for k in fin { entry = {"name": k, "count": fin[k]}; ins = False; i = 0; while i < len(funcs) { if entry["count"] > funcs[i]["count"] { funcs.insert(i, entry); ins=True; break; } i += 1; } if not ins { funcs.append(entry); } }
            # top classes by subclasses
            classes_all = []; try { if ("files" in ents) { for f in ents["files"] { if ("classes" in f) { for cn in f["classes"] { dup=False; j=0; while j < len(classes_all) { if classes_all[j]==cn { dup=True; break; } j+=1; } if not dup { classes_all.append(cn); } } } } } } except Exception as e { classes_all = []; }
            cls_counts = []; for cn in classes_all { subs = []; try { subs = ccg_get_subclasses(_repo_node, cn); } except Exception as e { subs = []; } cnt=0; for s in subs { cnt += 1; } en = {"name": cn, "count": cnt}; ins2=False; y=0; while y < len(cls_counts) { if en["count"] > cls_counts[y]["count"] { cls_counts.insert(y, en); ins2=True; break; } y+=1; } if not ins2 { cls_counts.append(en); } }
            # top modules by dependencies
            mods_all = []; try { if ("files" in ents) { for f in ents["files"] { if ("module" in f) { mn=f["module"]; if mn!="" { dupm=False; q=0; while q < len(mods_all) { if mods_all[q]==mn { dupm=True; break; } q+=1; } if not dupm { mods_all.append(mn); } } } } } } except Exception as e { mods_all = []; }
            mod_counts = []; for mn in mods_all { deps=[]; try { deps = ccg_get_dependencies(_repo_node, mn); } except Exception as e { deps = []; } mc=0; for d in deps { mc+=1; } em = {"name": mn, "count": mc}; ins3=False; r=0; while r < len(mod_counts) { if em["count"] > mod_counts[r]["count"] { mod_counts.insert(r, em); ins3=True; break; } r+=1; } if not ins3 { mod_counts.append(em); } }
            # trim
            t = self.top_n; if t < 1 { t = 5; }
            out["top"]["functions"] = funcs[0:t];
            out["top"]["classes"] = cls_counts[0:t];
            out["top"]["modules"] = mod_counts[0:t];
        }
        report {"status": "success", "repo_url": self.repo_url, "overview": out};
    }
}

# Graph traversal API: Stats from graph and document-oriented aggregates
walker api_graph_stats {
    has repo_url: str = "";
    has depth: str = "deep";
    has top_n: int = 10;

    obj __specs__ { static has auth: bool = False; }

    can process with `root entry {
        if self.repo_url == "" { report {"status": "error", "message": "repo_url is required", "status_code": 400}; }
        ov = build_overview(self.repo_url, self.depth);
        ents = {}; if "entities" in ov { ents = ov["entities"]; }
        ft = []; if "file_tree" in ov { ft = ov["file_tree"]; }
        _repo_node = None; gerr = "";
        try { _repo_node = build_repo_graph(here, self.repo_url, ft, ents); } except Exception as e { _repo_node = None; gerr = str(e); }
        st = {}; err = gerr;
        if _repo_node != None {
            try { st = collect_stats_from_repo(_repo_node, self.top_n); } except Exception as e { err = str(e); st = {}; }
        }
        report {"status": "success", "repo_url": self.repo_url, "stats": st, "error": err};
    }
}

walker api_graph_docs {
    has repo_url: str = "";
    has depth: str = "deep";
    has top_n: int = 10;

    obj __specs__ { static has auth: bool = False; }

    can process with `root entry {
        if self.repo_url == "" { report {"status": "error", "message": "repo_url is required", "status_code": 400}; }
        ov = build_overview(self.repo_url, self.depth);
        ents = {}; if "entities" in ov { ents = ov["entities"]; }
        ft = []; if "file_tree" in ov { ft = ov["file_tree"]; }
        _repo_node = None; gerr = "";
        try { _repo_node = build_repo_graph(here, self.repo_url, ft, ents); } except Exception as e { _repo_node = None; gerr = str(e); }
        docd = {"top_files": [], "top_files_by_size": [], "api_classes": [], "total_functions": 0}; err = gerr;
        if _repo_node != None {
            try { docd = doc_collect(_repo_node, ents, self.top_n); } except Exception as e { err = str(e); docd = {"top_files": [], "top_files_by_size": [], "api_classes": [], "total_functions": 0}; }
        }
        report {"status": "success", "repo_url": self.repo_url, "docs": docd, "error": err};
    }
}

