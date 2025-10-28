from typing import Dict, Any
import os
try:
    import requests as _requests
except Exception:
    class _RequestsStub:
        # Provide attribute so tests can patch graph_api.requests.post without the real dependency
        post = None
    requests = _RequestsStub()
else:
    requests = _requests

DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _extract_report_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if isinstance(data, dict) and "reports" in data and data["reports"]:
            return data["reports"][0]
    except Exception:
        pass
    return data if isinstance(data, dict) else {}


def call_graph_stats(repo_url: str, depth: str = "deep", top_n: int = 10, backend_url: str | None = None) -> Dict[str, Any]:
    base = backend_url or DEFAULT_BACKEND_URL
    try:
        resp = requests.post(
            f"{base}/walker/api_graph_stats",
            json={"repo_url": repo_url, "depth": depth, "top_n": top_n},
            timeout=120,
        )
        resp.raise_for_status()
        return _extract_report_payload(resp.json())
    except Exception as e:
        return {"status": "error", "message": f"graph_stats failed: {e}"}


def call_graph_docs(repo_url: str, depth: str = "deep", top_n: int = 10, backend_url: str | None = None) -> Dict[str, Any]:
    base = backend_url or DEFAULT_BACKEND_URL
    try:
        resp = requests.post(
            f"{base}/walker/api_graph_docs",
            json={"repo_url": repo_url, "depth": depth, "top_n": top_n},
            timeout=120,
        )
        resp.raise_for_status()
        return _extract_report_payload(resp.json())
    except Exception as e:
        return {"status": "error", "message": f"graph_docs failed: {e}"}

