# Maps repository structure into a graph (skeleton)


import from utils.repo { clone_or_open_repo }
import from utils.fs_map { scan_repo_tree, extract_readme, summarize_readme_sections }

#* Return a tiny, static file tree for smoke testing and docs generation.
# Each entry is a dict with keys: path, type, language.
*#
def sample_file_tree() -> list {
    return [
        {"path": "backend/main.jac", "type": "CodeFile", "language": "jac"},
        {"path": "backend/agents/Supervisor.jac", "type": "CodeFile", "language": "jac"},
        {"path": "backend/agents/RepoMapper.jac", "type": "CodeFile", "language": "jac"},
        {"path": "backend/agents/CodeAnalyzer.jac", "type": "CodeFile", "language": "jac"},
        {"path": "backend/agents/DocGenie.jac", "type": "CodeFile", "language": "jac"},
    ];
}


# Ensure local repo path (clone or open if cached)
def ensure_repo(repo_url: str) -> str { return clone_or_open_repo(repo_url); }

# Map: clone/open repo and scan file tree with filters
# Returns {"repo_path": str, "file_tree": list}
def map_scan(
    repo_url: str,
    exclude_dirs: list = [],
    exclude_globs: list = [],
    include_exts: list = [],
    include_globs: list = [],
    include_paths: list = [],
    max_files: int = 0,
    max_file_size_bytes: int = 0,
) -> dict {
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
    return {"repo_path": repo_path, "file_tree": files};
}

# Stream-aware variant: useful for very large repositories. Callers can set
# `streaming=True` to keep memory bounded; this will return the full list
# (for backwards compatibility) but will also accept an `on_batch` python
# callback (not exposed in Jac) via env-driven behavior. We ensure symlinks
# are not followed by default.
def map_scan_stream(
    repo_url: str,
    exclude_dirs: list = [],
    exclude_globs: list = [],
    include_exts: list = [],
    include_globs: list = [],
    include_paths: list = [],
    max_files: int = 0,
    max_file_size_bytes: int = 0,
    streaming: bool = False,
) -> dict {
    repo_path = clone_or_open_repo(repo_url);
    # Respect environment-driven streaming flag; default to False to keep backward compatibility
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
        False,  # follow_symlinks
    );
    return {"repo_path": repo_path, "file_tree": files};
}

# README info with summarized sections
# Returns {"readme": dict or None, "readme_summary": str}
def get_readme_info(repo_path: str, max_sections: int = 5) -> dict {
    rd = extract_readme(repo_path);
    if rd == None { return {"readme": None, "readme_summary": ""}; }
    sections = rd.get("sections", []);
    summ = "";
    try { summ = summarize_readme_sections(sections, max_sections); } except Exception as e { summ = ""; }
    return {"readme": rd, "readme_summary": summ};
}

walker RepoMapper {
    has repo_url: str = "";

    can map with `root entry {
        # Placeholder: real mapping will populate nodes/edges
        report {"file_tree": sample_file_tree()};
    }
}
