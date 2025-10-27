# 🧠 Codebase Genius

**AI-Powered Repository Documentation Generator**

Automatically analyze any GitHub repository and generate comprehensive, high-quality documentation using advanced AI and code analysis techniques.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
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
git clone <your-repo-url>
cd codebase-genius

# Set up backend
cd backend
uv sync
export OPENAI_API_KEY="your-api-key-here"
uv run jac serve main.jac --port 8000

# In a new terminal, set up frontend
cd frontend
uv sync
uv run streamlit run app.py
```

The UI will open at `http://localhost:8501`

**👉 See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions**

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
├── QUICKSTART.md           # Quick start guide
├── PROGRESS.md             # Implementation progress
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

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)**: Get started in 5 minutes
- **[PROGRESS.md](PROGRESS.md)**: Implementation progress and roadmap
- **[backend/README.md](backend/README.md)**: Backend API documentation
- **[frontend/README.md](frontend/README.md)**: Frontend UI documentation

---

## 🗺️ Roadmap

### ✅ Completed
- Deep repository analysis with filtering
- AI-powered documentation generation
- Rich statistics and visualizations
- Streamlit web UI
- Graph architecture foundation

### 🚧 In Progress
- Graph traversal walkers
- Enhanced entity extraction with tree-sitter

### 📋 Planned
- Diagram generation (Mermaid)
- Call graph analysis
- Incremental updates
- Multi-repository analysis
- Code search and navigation

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- **JacLang**: Object-Spatial Programming language
- **Streamlit**: Beautiful web UI framework
- **OpenAI**: GPT models for documentation generation
- **tree-sitter**: Universal code parser

---

**Built with ❤️ using JacLang and Streamlit**

