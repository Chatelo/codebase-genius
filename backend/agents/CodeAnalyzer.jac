# Analyzes code semantics (skeleton)

"""Compute basic stats from a file_tree list.
Returns dict with counts: files, jac_files, docs, plus code_files, python_files, languages and doc_kinds breakdowns.
"""
def basic_stats(file_tree: list, top_n: int = 10) -> dict {
    total = 0; jac_files = 0; docs = 0; code_files = 0; python_files = 0;
    languages = {}; doc_kinds = {}; top_dirs = {}; tests_files = 0; examples_files = 0;
    top_dirs_code = {}; tests_code_files = 0; examples_code_files = 0;
    top_size = []; top_lines = [];
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
                inserted = False;
                i = 0;
                while i < len(top_size) {
                    if sz > top_size[i]["size"] {
                        top_size.insert(i, {"path": p, "size": sz});
                        inserted = True;
                        break;
                    }
                    i += 1;
                }
                if not inserted { top_size.append({"path": p, "size": sz}); }
                if len(top_size) > top_n { top_size.pop(); }
            }
            # Track top N by lines for code files if provided
            if ("lines" in item) {
                ln = item["lines"];
                inserted2 = False;
                j = 0;
                while j < len(top_lines) {
                    if ln > top_lines[j]["lines"] {
                        top_lines.insert(j, {"path": p, "lines": ln});
                        inserted2 = True;
                        break;
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
    };
}

walker CodeAnalyzer {
    can analyze with `root entry {
        # Placeholder: would analyze CodeFile content and populate graph entities
        report {"ok": true};
    }
}
