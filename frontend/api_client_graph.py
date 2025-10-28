from typing import Dict, Any
import os
import requests


DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _extract_report_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if isinstance(data, dict) and "reports" in data and data["reports"]:
            return data["reports"][0]
    except Exception:
        pass
    return data if isinstance(data, dict) else {}


def call_graph_stats(repo_url: str, depth: str = "deep", top_n: int = 10, backend_url: str | None = None) -> Dict[str, Any]:
    """Call the api_graph_stats walker and return its payload.

    Parameters
    - repo_url: Repository URL to analyze
    - depth: "deep" or "standard"
    - top_n: Number of top items to compute
    - backend_url: Optional override for backend base URL; defaults to env BACKEND_URL or localhost
    """
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


essage": f"graph_docs failed: {e}"}

