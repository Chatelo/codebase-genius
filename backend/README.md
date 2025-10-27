# Codebase Genius Backend (JacLang)

This backend is implemented in JacLang with AI-powered walkers (by llm).

Current status (Step 1):
- Scaffolded structure: `agents/`, `utils/`, `prompts/`
- Initialized `main.jac` with a sample walker: `api_hello`

Directory layout:
- `main.jac` — backend entry and sample AI walker
- `agents/` — Supervisor, RepoMapper, CodeAnalyzer, DocGenie (skeletons)
- `prompts/` — prompt templates for AI abilities
- `utils/` — Python/Jac helpers (installed via uv as needed)

Next steps:
- Wire REST API endpoints (e.g., POST /walker/generate_docs) to walkers
- Implement RepoMapper, CodeAnalyzer, and DocGenie logic

Note: Use uv for Python dependencies from this directory:
- Install/sync: `uv sync`
- Run tools: `uv run <command>`
