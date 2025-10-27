# Analyzes code semantics (skeleton)

"""Compute basic stats from a file_tree list.
Returns dict with counts: files, jac_files, docs, plus code_files, python_files, languages and doc_kinds breakdowns.
"""
def basic_stats(file_tree: list) -> dict {
    total = 0; jac_files = 0; docs = 0; code_files = 0; python_files = 0;
    languages = {}; doc_kinds = {}; top_dirs = {}; tests_files = 0; examples_files = 0;
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
        # Detect tests/examples buckets
        if has_path and ("/tests/" in p or p.startswith("tests/") or "/test/" in p or p.startswith("test/")) { tests_files += 1; }
        if has_path and ("/examples/" in p or p.startswith("examples/") or "/example/" in p or p.startswith("example/")) { examples_files += 1; }

        if ("type" in item) and item["type"] == "CodeFile" {
            code_files += 1;
            if ("language" in item) {
                lang = item["language"];
                if (lang == "jac") { jac_files += 1; }
                if (lang == "python") { python_files += 1; }
                if (lang not in languages) { languages[lang] = 0; }
                languages[lang] += 1;
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
        "top_dirs": top_dirs,
    };
}

walker CodeAnalyzer {
    can analyze with `root entry {
        # Placeholder: would analyze CodeFile content and populate graph entities
        report {"ok": true};
    }
}
