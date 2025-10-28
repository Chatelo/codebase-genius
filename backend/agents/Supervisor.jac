# Orchestrator walker (minimal -> real-ready)

import from agents.RepoMapper { RepoMapper, sample_file_tree }
import from agents.CodeAnalyzer { CodeAnalyzer, basic_stats }
import from agents.DocGenie { DocGenie }
import from utils.repo { clone_or_open_repo }
import from utils.fs_map { scan_repo_tree, extract_readme, summarize_readme_sections }
import from utils.ts_analyze { extract_entities }
import from utils.cache { get_cache }

#* Build an overview by coordinating RepoMapper/CodeAnalyzer.
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
                # Cache hit - return cached data
                cached_result["from_cache"] = True;
                return cached_result;
            }
        }

        try {
            repo_path = clone_or_open_repo(repo_url);
            # Progress: repo cloned/opened
            if job_id != "" {
                try { cache.set("progress", repo_url, {"percent": 10, "stage": "clone", "message": "Repository ready"}, job_id=job_id); } except Exception as e { }
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
                files = scan_repo_tree(
                    repo_path,
                    exclude_dirs,
                    exclude_globs,
                    include_exts,
                    include_globs,
                    include_paths,
                    max_files,
                    max_file_size_bytes,
                    True,
                    524288,
                );
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
                # Progress: starting entity extraction
                if job_id != "" {
                    try { cache.set("progress", repo_url, {"percent": 35, "stage": "parse", "message": "Extracting entities"}, job_id=job_id); } except Exception as e { }
                }
                entities = extract_entities(repo_path, files);
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

            # Extract README if available
            readme_data = extract_readme(repo_path);
            readme_summary = "";
            if readme_data != None {
                sections = readme_data.get("sections", []);
                readme_summary = summarize_readme_sections(sections, 5);
            }

            result = {
                "repo_url": repo_url,
                "depth": depth,
                "repo_path": repo_path,
                "file_tree": files,
                "stats": stats,
                "entities": entities,
                "readme": readme_data,
                "readme_summary": readme_summary,
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
            return {"file_tree": files, "stats": stats, "repo_url": repo_url, "depth": depth, "error": str(e), "from_cache": False};
        }
    }

    # Stub path
    files = sample_file_tree();
    stats = basic_stats(files, top_n);
    return {"file_tree": files, "stats": stats, "repo_url": repo_url, "depth": depth, "from_cache": False};
}

walker Supervisor {
    has repo_url: str = "";
    has depth: str = "standard";

    can orchestrate with `root entry {
        overview = build_overview(self.repo_url, self.depth, [], [], [], [], 0, 0, 10);
        report overview;
    }
}
