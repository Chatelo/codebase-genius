# API Documentation

## 🧭 CCG API (Code Context Graph)

These endpoints expose graph insights for functions, classes, and modules. All are public (auth=False) Jac walkers.

Base URL in local dev: `http://localhost:8000`.

- POST `/walker/api_ccg_overview`
- POST `/walker/api_ccg_callers`
- POST `/walker/api_ccg_callees`
- POST `/walker/api_ccg_subclasses`
- POST `/walker/api_ccg_dependencies`

Notes
- `depth`: "deep" builds a fuller graph; "standard" is lighter.
- On errors, endpoints return `{ "status": "error", "message": str, "status_code": int? }`.
- On success, endpoints include an `error` field inside the payload for non-fatal graph issues (string, may be empty).

### Overview
Request
```json
{
  "repo_url": "https://github.com/org/repo",
  "depth": "deep",
  "top_n": 5
}
```
Success response
```json
{
  "status": "success",
  "repo_url": "https://github.com/org/repo",
  "overview": {
    "counts": { "calls": 0, "inherits": 0, "imports": 0 },
    "top": {
      "functions": [{ "name": "pkg.mod.func", "count": 12 }],
      "classes":   [{ "name": "pkg.mod.Base", "count": 5  }],
      "modules":   [{ "name": "pkg.mod",      "count": 20 }]
    },
    "error": ""
  }
}
```
Error response
```json
{ "status": "error", "message": "repo_url is required", "status_code": 400 }
```

### Function Callers
Request
```json
{
  "repo_url": "https://github.com/org/repo",
  "func_name": "pkg.module.function",
  "depth": "deep"
}
```
Success response
```json
{
  "status": "success",
  "repo_url": "https://github.com/org/repo",
  "func_name": "pkg.module.function",
  "results": [ { "name": "pkg.a.calling_func" }, "pkg.b.other_caller" ],
  "error": ""
}
```

### Function Callees
Request/Response same shape as Callers, with `func_name` and `results` listing the functions called by the input function.

### Class Subclasses
Request
```json
{
  "repo_url": "https://github.com/org/repo",
  "class_name": "pkg.module.BaseClass",
  "depth": "deep"
}
```
Success response
```json
{
  "status": "success",
  "repo_url": "https://github.com/org/repo",
  "class_name": "pkg.module.BaseClass",
  "results": [ { "name": "pkg.module.Child" } ],
  "error": ""
}
```

### Module Dependencies
Request
```json
{
  "repo_url": "https://github.com/org/repo",
  "module_name": "pkg.module",
  "depth": "deep"
}
```
Success response
```json
{
  "status": "success",
  "repo_url": "https://github.com/org/repo",
  "module_name": "pkg.module",
  "results": [ { "name": "pkg.other" } ],
  "error": ""
}
```

### CURL examples
```bash
# Overview
curl -sX POST http://localhost:8000/walker/api_ccg_overview \
  -H 'Content-Type: application/json' \
  -d '{"repo_url":"https://github.com/org/repo","depth":"deep","top_n":5}' | jq

# Callers
curl -sX POST http://localhost:8000/walker/api_ccg_callers \
  -H 'Content-Type: application/json' \
  -d '{"repo_url":"https://github.com/org/repo","func_name":"pkg.module.func","depth":"deep"}' | jq
```

### Frontend integration
- The Streamlit UI includes a dedicated tab: "🧭 CCG Explorer".
- Provides: Overview metrics/top-N, Function Callers/Callees (with micro-mermaid diagrams), Class Subclasses, Module Dependencies.
- Results can be copied/downloaded from the UI.


## 🧭 Graph Traversal API (Stats + Docs)

Two additional public walkers expose graph-derived aggregates. Base URL: `http://localhost:8000`.

- POST `/walker/api_graph_stats` — compute repository stats via the built graph
- POST `/walker/api_graph_docs` — collect documentation-oriented aggregates

Notes
- `depth`: "deep" builds a fuller graph; "standard" is lighter.
- Success responses include an `error` string for non‑fatal graph issues.


Dev: CLI smoke test
- Run a quick check against a running backend:
  - `python scripts/smoke_graph.py --base-url http://localhost:8000 --repo-url https://github.com/org/repo`

### Graph Stats
Request
```json
{
  "repo_url": "https://github.com/org/repo",
  "depth": "deep",
  "top_n": 10
}
```
Success response (shape)
```json
{
  "status": "success",
  "repo_url": "...",
  "stats": {
    "files": 0,
    "code_files": 0,
    "docs": 0,
    "tests_files": 0,
    "examples_files": 0,
    "languages": { "python": 4 },
    "top_dirs": { "src": 12 },
    "top_dirs_code": { "src": 10 },
    "top_files_by_size": [{ "path": "src/a.py", "size": 12345 }],
    "top_files_by_lines": [{ "path": "src/a.py", "lines": 420 }],
    "ccg_counts": { "calls": 0, "inherits": 0, "imports": 0 }
  },
  "error": ""
}
```

### Graph Docs
Request
```json
{
  "repo_url": "https://github.com/org/repo",
  "depth": "deep",
  "top_n": 10
}
```
Success response (shape)
```json
{
  "status": "success",
  "repo_url": "...",
  "docs": {
    "top_files": [{ "path": "src/a.py", "lines": 420 }],
    "top_files_by_size": [{ "path": "src/a.py", "size": 12345 }],
    "api_classes": ["pkg.mod.Base", "pkg.mod.Service"],
    "total_functions": 123
  },
  "error": ""
}
```

### cURL examples
```bash
# Graph Stats
curl -sX POST http://localhost:8000/walker/api_graph_stats \
  -H 'Content-Type: application/json' \
  -d '{"repo_url":"https://github.com/org/repo","depth":"deep","top_n":10}' | jq

# Graph Docs
curl -sX POST http://localhost:8000/walker/api_graph_docs \
  -H 'Content-Type: application/json' \
  -d '{"repo_url":"https://github.com/org/repo","depth":"deep","top_n":10}' | jq
```