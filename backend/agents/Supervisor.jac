# Orchestrator walker (minimal -> real-ready)

import from agents.RepoMapper { sample_file_tree, map_scan, get_readme_info, ensure_repo }
import from agents.CodeAnalyzer { basic_stats, analyze_files }

import from utils.repo { is_repo_cached }
import from utils.cache { get_cache }

# --- Entry-point prioritization helpers ---
# Heuristics to identify and score likely repo entry-points (Python/JS/TS/Jac)

def _is_test_path(p: str) -> bool {
    lp = p.lower();
    if ("/tests/" in lp) or ("/test/" in lp) or lp.startswith("tests/") or lp.startswith("test/") { return True; }
    if ("/spec/" in lp) or lp.startswith("spec/") or ("/specs/" in lp) or lp.startswith("specs/") { return True; }
    return False;
}

# Return a simple depth (number of components - 1)
def _path_depth(p: str) -> int {
    parts = p.split("/");
    return (len(parts) - 1);
}

# Extract filename only

def _basename(p: str) -> str {
    parts = p.split("/");
    if len(parts) == 0 { return p; }
    return parts[len(parts) - 1];
}

# Scoring by filename patterns and shallow depth; higher = more likely entry-point

def _score_entry_point(path: str) -> int {
    lp = path.lower();
    bn = _basename(lp);
    score = 0;

    # Hard negative for tests/specs
    if _is_test_path(lp) { return 0; }

    # Strong Python signals
    if bn == "__main__.py" { score += 120; }
    if bn == "main.py" { score += 110; }
    if bn == "app.py" { score += 100; }
    if bn == "run.py" or bn == "server.py" or bn == "manage.py" { score += 95; }
    if bn == "wsgi.py" or bn == "asgi.py" or bn == "cli.py" or bn == "api.py" { score += 90; }

    # JS/TS front/back entry files
    if bn == "index.js" or bn == "index.ts" or bn == "index.tsx" or bn == "index.jsx" { score += 95; }
    if bn == "app.js" or bn == "app.ts" or bn == "app.tsx" { score += 90; }
    if bn == "server.js" or bn == "server.ts" { score += 90; }
    if bn == "main.js" or bn == "main.ts" { score += 88; }

    # Jac
    if bn == "main.jac" or bn == "app.jac" { score += 95; }

    # Location bonuses
    d = _path_depth(lp);
    if d == 0 { score += 15; }            # repo root
    if d == 1 { score += 8; }             # shallow
    if (lp.startswith("src/")) { score += 8; }
    if ("/bin/" in lp) { score += 6; }

    return score;
}


# Local helpers to keep ordering declarative and reusable
# Primary desc, optional secondary desc for tie-breaks
def __insort_desc(lst: list, entry: dict, key: str) -> None {
    inserted = False; i = 0;
    while i < len(lst) {
        cur = 0; try { if (key in lst[i]) { cur = lst[i][key]; } } except Exception as e { cur = 0; }
        if entry.get(key, 0) > cur { lst.insert(i, entry); inserted = True; break; }
        i += 1;
    }
    if not inserted { lst.append(entry); }
}

def __insort_desc2(lst: list, entry: dict, key1: str, key2: str) -> None {
    inserted = False; i = 0;
    while i < len(lst) {
        a1 = entry.get(key1, 0); b1 = 0; try { if (key1 in lst[i]) { b1 = lst[i][key1]; } } except Exception as e { b1 = 0; }
        if a1 > b1 {
            lst.insert(i, entry); inserted = True; break;
        } elif a1 == b1 {
            a2 = entry.get(key2, 0); b2 = 0; try { if (key2 in lst[i]) { b2 = lst[i][key2]; } } except Exception as e { b2 = 0; }
            if a2 > b2 { lst.insert(i, entry); inserted = True; break; }
        }
        i += 1;
    }
    if not inserted { lst.append(entry); }
}

# Build an entry-point prioritization plan from a file_tree
# Returns { "entry_points": [ {path, score}... ], "analysis_order": [paths...] }

def _prioritize_entry_points(file_tree: list, top_n: int = 10) -> dict {
    # Collect candidate code files with scores
    candidates = [];
    for item in file_tree {
        if ("type" in item) and (item["type"] == "CodeFile") {
            p = ""; ln = 0;
            if "path" in item { p = item["path"]; }
            if p == "" { continue; }
            s = _score_entry_point(p);
            if s > 0 {
                if "lines" in item { ln = item["lines"]; }
                candidates.append({"path": p, "score": s, "lines": ln});
            }
        }
    }

    # Sort candidates by score desc, then lines desc
    ranked = [];
    for c in candidates { __insort_desc2(ranked, c, "score", "lines"); }

    # Truncate to top N entry points
    entry_points = [];
    cnt = 0;
    for r in ranked {
        if cnt >= top_n { break; }
        entry_points.append({"path": r["path"], "score": r["score"]});
        cnt += 1;
    }

    # Build the overall analysis order: entry points first, then remaining code files by lines desc
    ep_set = {};
    for e in entry_points { ep_set[e["path"]] = True; }

    rest = [];
    for item2 in file_tree {
        if ("type" in item2) and (item2["type"] == "CodeFile") {
            p2 = item2.get("path", "");
            if p2 == "" { continue; }
            if p2 in ep_set { continue; }
            if _is_test_path(p2) { continue; }
            ln2 = 0; if "lines" in item2 { ln2 = item2["lines"]; }
            rest.append({"path": p2, "lines": ln2});
        }
    }
    # Sort rest by lines desc
    rest_sorted = [];
    for r2 in rest { __insort_desc(rest_sorted, r2, "lines"); }

    analysis_order = [];
    for e2 in entry_points { analysis_order.append(e2["path"]); }
    for r3 in rest_sorted { analysis_order.append(r3["path"]); }

    return {"entry_points": entry_points, "analysis_order": analysis_order};
}
# --- Iterative analysis scheduler (plan→analyze→evaluate) ---
# Uses entities (calls/imports) to rank files and propose iterative batches.

def _match_rel_path(file_tree: list, abs_path: str) -> str {
    # Find a file_tree path that appears as a substring of abs_path
    if abs_path == None { return ""; }
    ap = abs_path;
    best = ""; best_len = 0;
    for it in file_tree {
        if ("type" in it) and (it["type"] == "CodeFile") {
            rp = ""; if "path" in it { rp = it["path"]; }
            if rp != "" and (rp in ap) {
                if len(rp) > best_len { best = rp; best_len = len(rp); }
            }
        }
    }
    return best;
}

# Return scheduler result with iterations, coverage, and stop reason

def _iterative_scheduler(file_tree: list, entities: dict, plan: dict, max_iters: int = 3, batch_size: int = 20, coverage_target: float = 0.6) -> dict {
    # Index code files
    code_paths = [];
    lines_by_path = {};
    for it in file_tree {
        if ("type" in it) and (it["type"] == "CodeFile") {
            p = it.get("path", "");
            if p != "" { code_paths.append(p); lines_by_path[p] = it.get("lines", 0); }
        }
    }
    total = len(code_paths);
    if total == 0 { return {"iterations": [], "coverage": {"files_total": 0, "curve": [], "achieved": 0.0, "target": coverage_target, "selected_total": 0}, "stopped_reason": "no_code_files"}; }

    # Build entity indices
    func_to_files = {};         # name -> [rel_paths]
    module_to_file = {};        # module -> rel_path (first hit)

    if (entities != None) and ("files" in entities) {
        for fe in entities["files"] {
            rel = _match_rel_path(file_tree, fe.get("file", ""));
            if rel == "" { continue; }
            # Functions
            flist = fe.get("functions", []);
            for fn in flist {
                if fn not in func_to_files { func_to_files[fn] = []; }
                func_to_files[fn].append(rel);
            }
            # Module
            mod = fe.get("module", "");
            if mod != "" {
                if mod not in module_to_file { module_to_file[mod] = rel; }
            }
        }
    }

    # Initialize metrics per file
    metrics = {};  # path -> dict
    for pth in code_paths { metrics[pth] = {"in_calls": 0, "out_calls": 0, "in_imports": 0, "out_imports": 0, "score": 0}; }

    # Calls fan-in/out
    if (entities != None) and ("files" in entities) {
        for fe2 in entities["files"] {
            rel2 = _match_rel_path(file_tree, fe2.get("file", ""));
            if rel2 == "" { continue; }
            for c in fe2.get("calls", []) {
                metrics[rel2]["out_calls"] += 1;
                cal = c.get("callee", "");
                if cal != "" and (cal in func_to_files) {
                    for tgt in func_to_files[cal] {
                        if tgt != rel2 { metrics[tgt]["in_calls"] += 1; }
                    }
                }
            }
        }
    }

    # Imports in/out (module-level)
    if (entities != None) and ("files" in entities) {
        for fe3 in entities["files"] {
            rel3 = _match_rel_path(file_tree, fe3.get("file", ""));
            if rel3 == "" { continue; }
            for imp in fe3.get("imports", []) {
                tgt_mod = imp.get("module", "");
                if tgt_mod == "" { continue; }
                tgt_file = "";
                if tgt_mod in module_to_file { tgt_file = module_to_file[tgt_mod]; }
                else {
                    best_len = 0; best_file = "";
                    for mk in module_to_file {
                        if (tgt_mod.startswith(mk+".")) or (mk.startswith(tgt_mod+".")) or (mk == tgt_mod) {
                            if len(mk) > best_len { best_len = len(mk); best_file = module_to_file[mk]; }
                        }
                    }
                    tgt_file = best_file;
                }
                if tgt_file != "" and (tgt_file != rel3) {
                    metrics[rel3]["out_imports"] += 1;
                    metrics[tgt_file]["in_imports"] += 1;
                }
            }
        }
    }

    # Entry-point boost
    ep_set = {};
    try {
        if (plan != None) and ("entry_points" in plan) {
            for ep in plan["entry_points"] { if ("path" in ep) { ep_set[ep["path"]] = ep.get("score", 0); } }
        }
    } except Exception as e { }

    # Compute scores
    for p in code_paths {
        m = metrics[p];
        ep_bonus = 0;
        if p in ep_set { ep_bonus = 10; if ep_set[p] > 100 { ep_bonus = 15; } }
        m["score"] = (3*m["in_calls"]) + (2*m["in_imports"]) + (1*m["out_calls"]) + (1*m["out_imports"]) + ep_bonus;
        metrics[p] = m;
    }

    # Iterative batching
    selected = {}; ordered = [];
    coverage_curve = [];
    reason = "";
    it = 0;
    while it < max_iters {
        # Coverage
        cov = 0.0;
        try { cov = (1.0 * len(selected)) / (1.0 * total); } except Exception as e { cov = 0.0; }
        coverage_curve.append(cov);
        if cov >= coverage_target {
            reason = "coverage_target_met"; break;
        }
        # Build candidates
        cands = [];
        for p2 in code_paths { if p2 not in selected { cands.append(p2); } }
        if len(cands) == 0 { reason = "no_candidates"; break; }
        # Sort by score desc, tie by lines desc
        ranked = [];
        for p3 in cands {
            entry = {"path": p3, "score": metrics[p3]["score"], "lines": lines_by_path.get(p3, 0)};
            __insort_desc2(ranked, entry, "score", "lines");
        }
        # Pick batch
        batch = [];
        idx = 0;
        while idx < len(ranked) and idx < batch_size { batch.append(ranked[idx]["path"]); idx += 1; }
        # Apply
        for bp in batch { selected[bp] = True; }
        ordered.append({"index": it, "selected": batch});
        it += 1;
    }
    # Final coverage after loop
    cov_final = 0.0;
    try { cov_final = (1.0 * len(selected)) / (1.0 * total); } except Exception as e { cov_final = 0.0; }

    return {
        "config": {"max_iters": max_iters, "batch_size": batch_size, "coverage_target": coverage_target},
        "iterations": ordered,
        "coverage": {"files_total": total, "selected_total": len(selected), "curve": coverage_curve, "achieved": cov_final, "target": coverage_target},
        "stopped_reason": (reason if reason != "" else ("max_iters" if it >= max_iters else "done")),
    };
}


#* Build an overview by coordinating mapping and analysis helpers.
# If depth == "deep", perform real mapping and analysis. Otherwise, return stubbed data.
*#
def build_overview(
    repo_url: str,
    depth: str = "standard",
    exclude_dirs: list = [],
    exclude_globs: list = [],
    include_exts: list = [],
    include_globs: list = [],
    include_paths: list = [],
    max_files: int = 0,
    max_file_size_bytes: int = 0,
    top_n: int = 10,
    use_cache: bool = True,
    job_id: str = "",
) -> dict {
    if depth == "deep" {
        # Initialize cache
        cache = get_cache();
        # Try to get from cache first (keyed by analysis parameters)
        if use_cache {
            cached_result = cache.get(
                "overview",
                repo_url,
                exclude_dirs=exclude_dirs,
                exclude_globs=exclude_globs,
                include_exts=include_exts,
                include_globs=include_globs,
                include_paths=include_paths,
                max_files=max_files,
                max_file_size_bytes=max_file_size_bytes,
                top_n=top_n
            );
            if cached_result != None {
                # Cache hit - progress note for clarity in UI (cheap; file write only)
                if job_id != "" {
                    try { cache.set("progress", repo_url, {"percent": 10, "stage": "clone", "message": "Re-using cached repo artefacts"}, job_id=job_id); } except Exception as e { }
                }
                cached_result["from_cache"] = True;
                return cached_result;
            }
        }

        try {
            was_cached = False;
            try { was_cached = is_repo_cached(repo_url); } except Exception as e { was_cached = False; }
            # Progress: cloning/preparation start (write before blocking clone)
            if job_id != "" {
                try {
                    msg0 = "Cloning repository (shallow)";
                    if was_cached { msg0 = "Preparing repository"; }
                    cache.set("progress", repo_url, {"percent": 5, "stage": "clone", "message": msg0}, job_id=job_id);
                } except Exception as e { }
            }
            repo_path = ensure_repo(repo_url);
            # Progress: repo ready; indicate cache reuse if applicable
            if job_id != "" {
                try {
                    msg1 = "Repository ready";
                    if was_cached { msg1 = "Re-using cached repo artefacts"; }
                    cache.set("progress", repo_url, {"percent": 10, "stage": "clone", "message": msg1}, job_id=job_id);
                } except Exception as e { }
            }

            # Check cache for file_tree
            files = None;
            if use_cache {
                files = cache.get(
                    "file_tree",
                    repo_url,
                    exclude_dirs=exclude_dirs,
                    exclude_globs=exclude_globs,
                    include_exts=include_exts,
                    include_globs=include_globs,
                    include_paths=include_paths,
                    max_files=max_files,
                    max_file_size_bytes=max_file_size_bytes
                );
            }

            if files == None {
                mapping = map_scan(
                    repo_url,
                    exclude_dirs,
                    exclude_globs,
                    include_exts,
                    include_globs,
                    include_paths,
                    max_files,
                    max_file_size_bytes
                );
                repo_path = mapping.get("repo_path", "");
                files = mapping.get("file_tree", []);
                # Cache file_tree
                if use_cache {
                    cache.set(
                        "file_tree",
                        repo_url,
                        files,
                        exclude_dirs=exclude_dirs,
                        exclude_globs=exclude_globs,
                        include_exts=include_exts,
                        include_globs=include_globs,
                        include_paths=include_paths,
                        max_files=max_files,
                        max_file_size_bytes=max_file_size_bytes
                    );
                }
            }
            # Progress: file tree ready
            if job_id != "" {
                try { cache.set("progress", repo_url, {"percent": 30, "stage": "scan", "message": "File tree scanned"}, job_id=job_id); } except Exception as e { }
            }


            # Entry-point prioritization plan
            plan = _prioritize_entry_points(files, top_n);
            ep_count = 0;
            try { ep_count = len(plan["entry_points"]); } except Exception as e { ep_count = 0; }
            if job_id != "" {
                try { cache.set("progress", repo_url, {"percent": 33, "stage": "plan", "message": f"Prioritized entry points ({ep_count})"}, job_id=job_id); } except Exception as e { }
            }

            # Check cache for entities
            entities = None;
            if use_cache {
                entities = cache.get(
                    "entities",
                    repo_url,
                    exclude_dirs=exclude_dirs,
                    exclude_globs=exclude_globs,
                    include_exts=include_exts,
                    include_globs=include_globs,
                    include_paths=include_paths,
                    max_files=max_files,
                    max_file_size_bytes=max_file_size_bytes
                );
            }

            if entities == None {
                # Progress: starting entity extraction (entry points first)
                if job_id != "" {
                    try { cache.set("progress", repo_url, {"percent": 35, "stage": "parse", "message": "Extracting entities (entry points first)"}, job_id=job_id); } except Exception as e { }
                }

                # Determine prioritized vs. rest sets
                pri_paths = [];
                if "entry_points" in plan {
                    for ep in plan["entry_points"] { if "path" in ep { pri_paths.append(ep["path"]); } }
                }

                code_items = [];
                for it in files { if ("type" in it) and (it["type"] == "CodeFile") { code_items.append(it); } }

                pri_items = [];
                rest_items = [];
                if len(pri_paths) > 0 {
                    pri_set = {};
                    for pp in pri_paths { pri_set[pp] = True; }
                    for it2 in code_items {
                        pth2 = ""; if "path" in it2 { pth2 = it2["path"]; }
                        if (pth2 != "") and (pth2 in pri_set) { pri_items.append(it2); }
                        else { rest_items.append(it2); }
                    }
                } else {
                    rest_items = code_items;
                }

                # Extract entities: entry points first, then the rest
                ent_acc_files = [];
                ent_acc_errors = [];
                if (len(pri_items) > 0) and (len(rest_items) > 0) {
                    ent1 = analyze_files(repo_path, pri_items, False);
                    if ("files" in ent1) { for a in ent1["files"] { ent_acc_files.append(a); } }
                    if ("errors" in ent1) { for e1 in ent1["errors"] { ent_acc_errors.append(e1); } }
                    if job_id != "" {
                        try { cache.set("progress", repo_url, {"percent": 45, "stage": "parse", "message": f"Entry points analyzed ({len(pri_items)})"}, job_id=job_id); } except Exception as e { }
                    }
                    ent2 = analyze_files(repo_path, rest_items);
                    if ("files" in ent2) { for b in ent2["files"] { ent_acc_files.append(b); } }
                    if ("errors" in ent2) { for e2 in ent2["errors"] { ent_acc_errors.append(e2); } }
                    entities = {"files": ent_acc_files, "errors": ent_acc_errors};
                } else {
                    # Single-pass extraction
                    entities = analyze_files(repo_path, files);
                }

                # Cache entities
                if use_cache {
                    cache.set(
                        "entities",
                        repo_url,
                        entities,
                        exclude_dirs=exclude_dirs,
                        exclude_globs=exclude_globs,
                        include_exts=include_exts,
                        include_globs=include_globs,
                        include_paths=include_paths,
                        max_files=max_files,
                        max_file_size_bytes=max_file_size_bytes
                    );
                }
                # Progress: entities extracted
                if job_id != "" {
                    try { cache.set("progress", repo_url, {"percent": 55, "stage": "parse", "message": "Entities extracted"}, job_id=job_id); } except Exception as e { }
                }
            } else {
                # Progress: entities loaded from cache
                if job_id != "" {
                    try { cache.set("progress", repo_url, {"percent": 50, "stage": "parse", "message": "Entities loaded from cache"}, job_id=job_id); } except Exception as e { }
                }
            }

            # Progress: computing stats
            if job_id != "" {
                try { cache.set("progress", repo_url, {"percent": 58, "stage": "stats", "message": "Computing repository stats"}, job_id=job_id); } except Exception as e { }
            }

            # Compute stats (fast, no need to cache separately)
            stats = basic_stats(files, top_n);

            # Progress: scheduling next modules
            if job_id != "" {
                try { cache.set("progress", repo_url, {"percent": 60, "stage": "schedule", "message": "Ranking next modules"}, job_id=job_id); } except Exception as e { }
            }

            # Build iterative scheduler plan
            sch_max_iters = 5;
            try { if depth == "shallow" { sch_max_iters = 3; } } except Exception as e { }
            sch_batch = (top_n if (top_n > 0) else 20);
            scheduler = _iterative_scheduler(files, entities, plan, sch_max_iters, sch_batch, 0.6);

            # Extract README if available via RepoMapper
            readme_data = None; readme_summary = "";
            try {
                ri = get_readme_info(repo_path, 5);
                if "readme" in ri { readme_data = ri["readme"]; }
                if "readme_summary" in ri { readme_summary = ri["readme_summary"]; }
            } except Exception as e { readme_data = None; readme_summary = ""; }

            result = {
                "repo_url": repo_url,
                "depth": depth,
                "repo_path": repo_path,
                "file_tree": files,
                "stats": stats,
                "entities": entities,
                "readme": readme_data,
                "readme_summary": readme_summary,
                "plan": plan,
                "scheduler": scheduler,
                "from_cache": False,
            };

            # Cache the complete overview
            if use_cache {
                cache.set(
                    "overview",
                    repo_url,
                    result,
                    exclude_dirs=exclude_dirs,
                    exclude_globs=exclude_globs,
                    include_exts=include_exts,
                    include_globs=include_globs,
                    include_paths=include_paths,
                    max_files=max_files,
                    max_file_size_bytes=max_file_size_bytes,
                    top_n=top_n
                );
            }

            return result;
        } except Exception as e {
            # Report error progress
            if job_id != "" {
                try { cache.set("progress", repo_url, {"percent": 40, "stage": "error", "message": str(e)}, job_id=job_id); } except Exception as _e { }
            }
            # Fall back to stub on error
            files = sample_file_tree();
            stats = basic_stats(files, top_n);
            plan = _prioritize_entry_points(files, top_n);
            scheduler = _iterative_scheduler(files, {"files": []}, plan, 2, (top_n if (top_n > 0) else 10), 0.5);
            return {"file_tree": files, "stats": stats, "repo_url": repo_url, "depth": depth, "plan": plan, "scheduler": scheduler, "error": str(e), "from_cache": False};
        }
    }

    # Stub path
    files = sample_file_tree();
    stats = basic_stats(files, top_n);
    plan = _prioritize_entry_points(files, top_n);
    scheduler = _iterative_scheduler(files, {"files": []}, plan, 2, (top_n if (top_n > 0) else 10), 0.5);
    return {"file_tree": files, "stats": stats, "repo_url": repo_url, "depth": depth, "plan": plan, "scheduler": scheduler, "from_cache": False};
}

walker Supervisor {
    has repo_url: str = "";
    has depth: str = "standard";

    can orchestrate with `root entry {
        overview = build_overview(self.repo_url, self.depth, [], [], [], [], 0, 0, 10);
        report overview;
    }
}
