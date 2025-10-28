# Codebase Genius – Design Decisions & Report

## Overview
This document summarizes key architectural decisions, constraints, and validation for the Code Context Graph (CCG) features and the overall system.

## Architecture Highlights
- Multi‑agent backend in JacLang: Supervisor, RepoMapper, CodeAnalyzer, DocGenie.
- Graph‑first design (Repository/Directory/CodeFile/Function/Class/Module; edges: Contains, Defines, Calls, Inherits, Imports).
- Clean agent boundaries: Supervisor orchestrates; RepoMapper maps repo; CodeAnalyzer builds stats/CCG; DocGenie handles LLM prompts.
- Public CCG walkers: callers, callees, subclasses, dependencies, overview.
- Streamlit frontend with dedicated “CCG Explorer” tab, stateful caching, and micro‑Mermaid diagrams.

## Key Decisions
- Robust error handling: endpoints never crash; return `status=error` or include non‑fatal `error` strings in payloads.
- Stateless server responses; caching occurs only in Streamlit session state for UI responsiveness.
- Minimal JSON schemas for results to keep payloads compact (results accept either `{name}` objects or strings).
- Overview precomputes counts and top‑N lists for fast at‑a‑glance insights.
- Download/copy affordances throughout the UI for portability.

## Backend Endpoints (CCG)
- POST /walker/api_ccg_overview – repo overview (counts + top‑N)
- POST /walker/api_ccg_callers – functions that call the given function
- POST /walker/api_ccg_callees – functions called by the given function
- POST /walker/api_ccg_subclasses – classes inheriting from the given class
- POST /walker/api_ccg_dependencies – module imports/dependencies

OpenAPI spec: docs/openapi/ccg.openapi.yaml
Postman collection: docs/postman/ccg.postman_collection.json

## Frontend – CCG Explorer
- Overview panel auto‑loads and shows counts and top‑N tables.
- Function Callers/Callees: inputs + results + micro‑Mermaid diagrams.
- Subclasses/Dependencies: inputs + results tables.
- Caching with composite keys to avoid redundant calls; graceful error messages.

## Testing & CI
- Unit tests for utilities: fs_map, ts_analyze (regex fallback), diagram_gen (Mermaid builders).
- GitHub Actions: run unit tests on push/PR.
- Future: optional e2e smoke tests for walkers with local server or mocked requests.

## Constraints & Trade‑offs
- Cross‑language entity extraction is heuristic and may miss edge cases; UI exposes raw lists for transparency.
- Mermaid diagrams favor clarity over completeness (limited max nodes in micro‑views).
- No persistent server‑side cache to avoid memory growth; relies on on‑demand computation and frontend caching.

## Next Work (Proposed)
- E2E smoke tests with a local jac serve harness or request mocking.
- Additional graph traversals (impact analysis, reference queries).
- Performance tuning (parallel parsing, incremental graph builds).
- Optional OpenAPI integration into the app (schema‑driven clients).

