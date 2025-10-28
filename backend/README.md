# Codebase Genius Backend (JacLang)

This backend is implemented in JacLang with AI-powered walkers (by llm).

Current status:
- Production walkers: `generate_docs`, `api_ccg_overview`, `api_ccg_callers`, `api_ccg_callees`, `api_ccg_subclasses`, `api_ccg_dependencies`, `api_graph_stats`, `api_graph_docs`
- Agents implemented: Supervisor (orchestration), RepoMapper (repo mapping), CodeAnalyzer (stats + CCG), DocGenie (LLM docs)
- Robust validation and error handling; no global caches or leaks

Directory layout:
- `main.jac` — backend entry and API walkers
- `agents/` — Supervisor, RepoMapper, CodeAnalyzer, DocGenie
- `graph/` — nodes/edges/builders for graph construction
- `utils/` — Python/Jac helpers

Run (from backend/):
- Install/sync: `uv sync`
- Serve API: `uv run jac serve main.jac --port 8000`



---

## 🧭 CCG API (Code Context Graph)

Public Jac walkers returning code graph insights. Base URL (local): `http://localhost:8000`.

Endpoints
- POST `/walker/api_ccg_overview`
- POST `/walker/api_ccg_callers`
- POST `/walker/api_ccg_callees`
- POST `/walker/api_ccg_subclasses`
- POST `/walker/api_ccg_dependencies`

Notes
- `depth`: "deep" builds a fuller graph; "standard" is lighter.
- Success responses include an `error` string for non-fatal graph issues.
- Errors return `{ "status": "error", "message": str, "status_code": int? }`.

Overview request
```json
{
  "repo_url": "https://github.com/org/repo",
  "depth": "deep",
  "top_n": 5
}
```
Overview success response (shape)
```json
{
  "status": "success",
  "repo_url": "...",
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

Callers/Callees request
```json
{ "repo_url": "...", "func_name": "pkg.module.function", "depth": "deep" }
```
Callers/Callees success response (shape)
```json
{ "status": "success", "repo_url": "...", "func_name": "...", "results": [ { "name": "pkg.a.caller" }, "pkg.b.other" ], "error": "" }
```

Subclasses request/response
```json
{ "repo_url": "...", "class_name": "pkg.module.Base", "depth": "deep" }
{ "status": "success", "repo_url": "...", "class_name": "...", "results": [ { "name": "pkg.module.Child" } ], "error": "" }
```

Dependencies request/response
```json
{ "repo_url": "...", "module_name": "pkg.module", "depth": "deep" }
{ "status": "success", "repo_url": "...", "module_name": "...", "results": [ { "name": "pkg.other" } ], "error": "" }
```

cURL examples
```bash
curl -sX POST http://localhost:8000/walker/api_ccg_overview \
  -H 'Content-Type: application/json' \
  -d '{"repo_url":"https://github.com/org/repo","depth":"deep","top_n":5}' | jq

curl -sX POST http://localhost:8000/walker/api_ccg_callers \
  -H 'Content-Type: application/json' \
  -d '{"repo_url":"https://github.com/org/repo","func_name":"pkg.module.func","depth":"deep"}' | jq
```


---

## 🧭 Graph Traversal API (Stats + Docs)

Additional public walkers that operate over the built repository graph.

Endpoints
- POST `/walker/api_graph_stats`
- POST `/walker/api_graph_docs`

Notes
- `depth`: "deep" builds a fuller graph; "standard" is lighter.
- Success responses include an `error` string for non‑fatal graph issues.

Graph Stats request
```json
{ "repo_url": "https://github.com/org/repo", "depth": "deep", "top_n": 10 }
```
Graph Stats success response (shape)
```json
{ "status":"success", "repo_url":"...", "stats": { "files":0, "code_files":0, "docs":0, "tests_files":0, "examples_files":0, "languages":{}, "top_dirs":{}, "top_dirs_code":{}, "top_files_by_size":[{"path":"src/a.py","size":12345}], "top_files_by_lines":[{"path":"src/a.py","lines":420}], "ccg_counts":{"calls":0,"inherits":0,"imports":0} }, "error":"" }
```

Graph Docs request
```json
{ "repo_url": "https://github.com/org/repo", "depth": "deep", "top_n": 10 }
```
Graph Docs success response (shape)
```json
{ "status":"success", "repo_url":"...", "docs": { "top_files":[{"path":"src/a.py","lines":420}], "api_classes":["pkg.mod.Base"], "total_functions": 123 }, "error":"" }
```
