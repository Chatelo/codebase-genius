# Orchestrator walker (minimal -> real-ready)

import from agents.RepoMapper { RepoMapper, sample_file_tree }
import from agents.CodeAnalyzer { CodeAnalyzer, basic_stats }
import from agents.DocGenie { DocGenie }
import from utils.repo { clone_or_open_repo }
import from utils.fs_map { scan_repo_tree }
import from utils.ts_analyze { extract_entities }

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
) -> dict {
    if depth == "deep" {
        try {
            repo_path = clone_or_open_repo(repo_url);
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
            stats = basic_stats(files, top_n);
            entities = extract_entities(repo_path, files);
            return {
                "repo_url": repo_url,
                "depth": depth,
                "repo_path": repo_path,
                "file_tree": files,
                "stats": stats,
                "entities": entities,
            };
        } except Exception as e {
            # Fall back to stub on error
            files = sample_file_tree();
            stats = basic_stats(files, top_n);
            return {"file_tree": files, "stats": stats, "repo_url": repo_url, "depth": depth, "error": str(e)};
        }
    }

    # Stub path
    files = sample_file_tree();
    stats = basic_stats(files, top_n);
    return {"file_tree": files, "stats": stats, "repo_url": repo_url, "depth": depth};
}

walker Supervisor {
    has repo_url: str = "";
    has depth: str = "standard";

    can orchestrate with `root entry {
        overview = build_overview(self.repo_url, self.depth, [], [], [], [], 0, 0, 10);
        report overview;
    }
}
