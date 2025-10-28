# 🧠 Codebase Genius

**AI-Powered Repository Documentation Generator**

Automatically analyze any GitHub repository and generate comprehensive, high-quality documentation using advanced AI and code analysis techniques.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![JacLang](https://img.shields.io/badge/jaclang-0.8.10-purple.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.39.0-red.svg)

---

## ✨ Features

### 🔍 Deep Code Analysis
- **Repository Cloning**: Automatically clone and cache GitHub repositories
- **File Tree Scanning**: Intelligent directory traversal with configurable filters
- **Code Entity Extraction**: Parse functions, classes, and modules using tree-sitter
- **Multi-Language Support**: Python, JavaScript, TypeScript, Java, Go, Rust, and more

### 🤖 AI-Powered Documentation
- **LLM Integration**: Generate comprehensive documentation using OpenAI GPT models
- **Context-Aware**: Enriched prompts with repository statistics and API surface
- **Structured Output**: Well-formatted markdown with sections for overview, structure, API, and more

### 📊 Rich Statistics
- File counts (total, code, tests, docs, examples)
- Language breakdown
- Top directories by code files
- Top files by size and lines of code
- Test coverage indicators

### 🎯 Advanced Filtering
- **Include Paths**: Focus on specific directories (e.g., `src/`, `lib/`)
- **Include Extensions**: Only analyze certain file types (e.g., `.py`, `.js`)
- **Include Globs**: Positive pattern matching
- **Exclude Directories**: Skip build artifacts, caches, etc.
- **Exclude Globs**: Filter out binaries, images, notebooks

### ⚡ Performance Controls
- **Max Files**: Limit total files scanned
- **Max File Size**: Skip large files
- **Fast Line Counting**: Efficient LOC computation with capped reads
- **Repository Caching**: Avoid redundant cloning

### 🎨 Beautiful Web UI
- **Streamlit Interface**: Modern, responsive web application
- **Interactive Visualizations**: Charts, metrics, expandable file trees
- **Real-time Feedback**: Progress indicators and error handling
- **Export**: Download documentation as Markdown

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone https://github.com/Chatelo/codebase-genius.git
cd codebase-genius

# Set up backend
cd backend
uv sync
export OPENAI_API_KEY="your-api-key-here"
#You may use Geminias they have generous free tier
uv run jac serve main.jac --port 8000

# In a new terminal, set up frontend
cd frontend
uv sync
uv run streamlit run app.py
```

The UI will open at `http://localhost:8501`

---

## 📖 Usage

### Web UI

1. Open `http://localhost:8501` in your browser
2. Enter a GitHub repository URL (e.g., `https://github.com/karpathy/micrograd`)
3. Configure settings in the sidebar:
   - Analysis depth: **deep** (full analysis) or **standard** (stub)
   - Enable AI documentation
   - Set filters and performance limits
4. Click **🚀 Generate Documentation**
5. View results in tabs:
   - 📖 **Documentation**: AI-generated markdown
   - 📊 **Statistics**: Metrics and charts
   - 🌲 **File Tree**: Repository structure
   - 🔧 **Raw Data**: Full API response
6. Download documentation using the **⬇️ Download** button

### API

```python
import requests

response = requests.post("http://localhost:8000/walker/generate_docs", json={
    "repo_url": "https://github.com/karpathy/micrograd",
    "depth": "deep",
    "use_llm": True,
    "include_paths": ["micrograd/", "test/"],
    "top_n": 10
})

result = response.json()["reports"][0]
print(result["documentation"])
```

---

---

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

### cURL examples
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


## 🏗️ Architecture

### Tech Stack

**Backend (JacLang)**
- **JacLang**: Object-Spatial Programming language for graph-based architecture
- **byLLM**: LLM integration framework
- **GitPython**: Repository cloning
- **tree-sitter**: Code parsing
- **FastAPI/Uvicorn**: REST API server (via jac-cloud)

**Frontend (Streamlit)**
- **Streamlit**: Web UI framework
- **Requests**: HTTP client for API calls

### System Design

```
┌──────────────────────────────────────────────────────────┐
│                   Streamlit Frontend                      │
│  • Repository URL input                                   │
│  • Configuration sidebar (filters, LLM, performance)      │
│  • Results visualization (tabs, charts, file tree)        │
│  • Export functionality                                   │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTP POST /walker/generate_docs
                     ▼
┌──────────────────────────────────────────────────────────┐
│                    JacLang Backend                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Supervisor (Orchestration)                        │  │
│  └────────────────────────────────────────────────────┘  │
│           │                    │                          │
│           ▼                    ▼                          │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │   RepoMapper    │  │  CodeAnalyzer   │               │
│  │ • Clone repo    │  │ • Extract       │               │
│  │ • Scan files    │  │   entities      │               │
│  │ • Build tree    │  │ • Compute stats │               │
│  └─────────────────┘  └─────────────────┘               │
│           │                    │                          │
│           └────────┬───────────┘                          │
│                    ▼                                      │
│           ┌─────────────────┐                            │
│           │    DocGenie     │                            │
│           │ • LLM prompts   │                            │
│           │ • Generate docs │                            │
│           └─────────────────┘                            │
└──────────────────────────────────────────────────────────┘
```

### Graph Architecture (Future)

Codebase Genius is designed with a graph-first architecture:

**Nodes**: Repository, Directory, CodeFile, Function, Class, Module
**Edges**: Contains, Defines, Calls, Inherits, Imports, References

This enables advanced features like:
- Call graph analysis
- Dependency tracking
- Impact analysis
- Code navigation

See `backend/graph/` for node/edge definitions and builders.

---

## 📁 Project Structure

```
codebase-genius/
├── backend/                 # JacLang backend
│   ├── agents/             # Specialized walkers
│   │   ├── Supervisor.jac  # Orchestration
│   │   ├── RepoMapper.jac  # Repository mapping
│   │   ├── CodeAnalyzer.jac # Statistics
│   │   └── DocGenie.jac    # LLM documentation
│   ├── graph/              # Graph architecture
│   │   ├── nodes.jac       # Node definitions
│   │   ├── edges.jac       # Edge definitions
│   │   └── builders.jac    # Graph construction
│   ├── utils/              # Python helpers
│   │   ├── repo.py         # Git operations
│   │   ├── fs_map.py       # File scanning
│   │   └── ts_analyze.py   # Code parsing
│   ├── main.jac            # API entry point
│   └── README.md           # Backend docs
├── frontend/               # Streamlit UI
│   ├── .streamlit/         # Streamlit config
│   ├── app.py              # Main UI
│   └── README.md           # Frontend docs
└── README.md               # This file
```

---

## 🎯 Example Output

### Input
```
Repository: https://github.com/karpathy/micrograd
Filters: include_paths=["micrograd/", "test/"]
LLM: Enabled
```

### Output Statistics
```
Files: 4
Code Files: 4 (Python: 4)
Tests: 1
Top Files: engine.py (94 loc), test_engine.py (67 loc), nn.py (60 loc)
API: Classes [Value, Module, Neuron, Layer, MLP], Functions: 35
```

### Generated Documentation (excerpt)
```markdown
# Micrograd Documentation Summary

## Overview
Micrograd is a minimalistic library for automatic differentiation...

## API Overview
### Classes
- **Value**: Represents a scalar value and its gradient
- **Module**: Base class for all neural network modules
- **Neuron**: Represents a single neuron
- **Layer**: Represents a layer of neurons
- **MLP**: Multi-layer perceptron

### Functions
Total Functions: 35 functions defined across the codebase
...
```

---

## 🛠️ Configuration

### Backend Configuration

Edit `backend/.streamlit/secrets.toml` (if using Streamlit secrets) or set environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export BACKEND_PORT=8000
```

### Frontend Configuration

Edit `frontend/.streamlit/secrets.toml`:

```toml
BACKEND_URL = "http://localhost:8000"
```

Edit `frontend/.streamlit/config.toml` for theme customization:

```toml
[theme]
primaryColor = "#667eea"
backgroundColor = "#ffffff"
```

---

## 📊 Sample Outputs

See real examples of Codebase Genius in action:

- **[outputs/codebase-genius/](outputs/codebase-genius/)** — Analysis of this project (Codebase Genius)
  - `codebase-genius_documentation.md` — AI-generated comprehensive documentation
  - `diagrams/` — Mermaid diagrams (call graph, class hierarchy, module dependencies)
  - `statistics.json` — Repository metrics and analytics

- **[outputs/micrograd/](outputs/micrograd/)** — Analysis of [karpathy/micrograd](https://github.com/karpathy/micrograd)
  - `micrograd_documentation.md` — AI-generated documentation
  - `statistics.json` — Repository metrics


## 📄 License

MIT License - see LICENSE file for details

---


