# Maps repository structure into a graph (skeleton)

"""Return a tiny, static file tree for smoke testing and docs generation.
Each entry is a dict with keys: path, type, language.
"""
def sample_file_tree() -> list {
    return [
        {"path": "backend/main.jac", "type": "CodeFile", "language": "jac"},
        {"path": "backend/agents/Supervisor.jac", "type": "CodeFile", "language": "jac"},
        {"path": "backend/agents/RepoMapper.jac", "type": "CodeFile", "language": "jac"},
        {"path": "backend/agents/CodeAnalyzer.jac", "type": "CodeFile", "language": "jac"},
        {"path": "backend/agents/DocGenie.jac", "type": "CodeFile", "language": "jac"},
        {"path": "backend/prompts/docgen.md", "type": "Doc", "language": "md"},
    ];
}

walker RepoMapper {
    has repo_url: str = "";

    can map with `root entry {
        # Placeholder: real mapping will populate nodes/edges
        report {"file_tree": sample_file_tree()};
    }
}
