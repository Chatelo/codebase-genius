# 🧠 Codebase Genius

**AI-Powered Repository Documentation Generator**

Automatically analyze any GitHub repository and generate comprehensive, high-quality documentation using advanced AI and code analysis techniques.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![JacLang](https://img.shields.io/badge/jaclang-0.8.10-purple.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.39.0-red.svg)

## ✨ Features

- 🔍 **Smart Analysis** — Parses files, classes, and functions using Tree-sitter
- 🤖 **AI Documentation** — GPT-powered summaries with repository context
- 📊 **Code Statistics** — File counts, language breakdowns, and LOC
- 🎨 **Interactive UI** — Streamlit dashboard with charts and file explorer
- ⚙️ **Filters & Limits** — Control scan depth, include/exclude paths, size limits
- 🧭 **Graph APIs** — Explore function calls, subclasses, and dependencies
---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
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
# You may use Gemini as they have generous free tier
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
   - 🔧 **Raw Data**: Full API response
6. Download documentation using the **⬇️ Download** button

---

## 🧭 APIs

Codebase Genius provides several APIs for programmatic access to repository analysis and graph traversal. See [API.md](API.md) for complete documentation.

### CCG API (Code Context Graph)
Explore function calls, class hierarchies, and module dependencies through graph-based endpoints:
- `POST /walker/api_ccg_overview` - Repository overview with top entities
- `POST /walker/api_ccg_callers` - Functions calling a specific function
- `POST /walker/api_ccg_callees` - Functions called by a specific function
- `POST /walker/api_ccg_subclasses` - Subclasses of a specific class
- `POST /walker/api_ccg_dependencies` - Modules imported by a specific module

### Graph Traversal API
Aggregate statistics and documentation from the built graph:
- `POST /walker/api_graph_stats` - Repository statistics and metrics
- `POST /walker/api_graph_docs` - Documentation-oriented aggregates

Base URL: `http://localhost:8000` (local development)


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
│   ├── prompts/            # LLM prompt templates
│   ├── utils/              # Python helpers
│   │   ├── repo.py         # Git operations
│   │   ├── fs_map.py       # File scanning
│   │   ├── ts_analyze.py   # Code parsing
│   │   └── output.py       # Result formatting
│   ├── main.jac            # API entry point
│   └── pyproject.toml      # Backend dependencies
├── frontend/               # Streamlit UI
│   ├── .streamlit/         # Streamlit config
│   ├── app.py              # Main UI
│   ├── api_client_graph.py # API client
│   └── pyproject.toml      # Frontend dependencies
├── docs/                   # OpenAPI specs
├── outputs/                # Generated documentation examples
├── tests/                  # Test suite
├── API.md                  # API documentation
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

### Environment Variables
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### Frontend Settings
Edit `frontend/.streamlit/config.toml` for theme customization.

---

## 📊 Sample Outputs

See real examples in the `outputs/` directory:

- **[outputs/codebase-genius/](outputs/codebase-genius/)** — Analysis of this project
- **[outputs/micrograd/](outputs/micrograd/)** — Analysis of [karpathy/micrograd](https://github.com/karpathy/micrograd)
- **[outputs/rust_counter_mcp/](outputs/rust_counter_mcp/)** — Analysis of a Rust project
- **[outputs/vite/](outputs/vite/)** — Analysis of a JavaScript project

Each contains AI-generated documentation, statistics, and Mermaid diagrams.


## 📄 License

MIT License - see LICENSE file for details

---


