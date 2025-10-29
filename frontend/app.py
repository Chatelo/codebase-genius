import streamlit as st
import requests
import json
from typing import Dict, Any, List
import streamlit.components.v1 as components
import time
import threading
import uuid



# Page configuration
st.set_page_config(
    page_title="Codebase Genius",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Backend API configuration
BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

def call_generate_docs(config: Dict[str, Any]) -> Dict[str, Any]:
    """Call the backend API to generate documentation."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/walker/generate_docs",
            json=config,
            timeout=600  # 10 minute timeout for large repos
        )
        response.raise_for_status()
        result = response.json()
        # Extract the first report from the response
        if "reports" in result and len(result["reports"]) > 0:
            return result["reports"][0]
        return result
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timed out. The repository might be too large."}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": f"Could not connect to backend at {BACKEND_URL}. Make sure the server is running."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"API request failed: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

def call_get_progress(repo_url: str, job_id: str) -> Dict[str, Any]:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/walker/api_get_progress",
            json={"repo_url": repo_url, "job_id": job_id},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "reports" in data and data["reports"]:
            return data["reports"][0]
        return data
    except Exception:
        return {"status": "error"}


# --- CCG API clients ---

def _extract_report_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if isinstance(data, dict) and "reports" in data and data["reports"]:
            return data["reports"][0]
    except Exception:
        pass
    return data if isinstance(data, dict) else {}


def call_ccg_overview(repo_url: str, depth: str = "deep", top_n: int = 5) -> Dict[str, Any]:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/walker/api_ccg_overview",
            json={"repo_url": repo_url, "depth": depth, "top_n": top_n},
            timeout=120,
        )
        resp.raise_for_status()
        return _extract_report_payload(resp.json())
    except Exception as e:
        return {"status": "error", "message": f"ccg_overview failed: {e}"}


def call_ccg_callers(repo_url: str, func_name: str, depth: str = "deep") -> Dict[str, Any]:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/walker/api_ccg_callers",
            json={"repo_url": repo_url, "func_name": func_name, "depth": depth},
            timeout=120,
        )
        resp.raise_for_status()
        return _extract_report_payload(resp.json())
    except Exception as e:
        return {"status": "error", "message": f"ccg_callers failed: {e}"}


def call_ccg_callees(repo_url: str, func_name: str, depth: str = "deep") -> Dict[str, Any]:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/walker/api_ccg_callees",
            json={"repo_url": repo_url, "func_name": func_name, "depth": depth},
            timeout=120,
        )
        resp.raise_for_status()
        return _extract_report_payload(resp.json())
    except Exception as e:
        return {"status": "error", "message": f"ccg_callees failed: {e}"}


def call_ccg_subclasses(repo_url: str, class_name: str, depth: str = "deep") -> Dict[str, Any]:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/walker/api_ccg_subclasses",
            json={"repo_url": repo_url, "class_name": class_name, "depth": depth},
            timeout=120,
        )
        resp.raise_for_status()
        return _extract_report_payload(resp.json())
    except Exception as e:
        return {"status": "error", "message": f"ccg_subclasses failed: {e}"}


def call_ccg_dependencies(repo_url: str, module_name: str, depth: str = "deep") -> Dict[str, Any]:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/walker/api_ccg_dependencies",
            json={"repo_url": repo_url, "module_name": module_name, "depth": depth},
            timeout=120,
        )
        resp.raise_for_status()
        return _extract_report_payload(resp.json())
    except Exception as e:
        return {"status": "error", "message": f"ccg_dependencies failed: {e}"}


# --- Graph Walker API clients ---
from api_client_graph import call_graph_stats, call_graph_docs


def build_micro_mermaid_function(func_name: str, callers: List[Dict[str, Any]], callees: List[Dict[str, Any]], max_nodes: int = 5) -> str:
    """Build a tiny, safe Mermaid graph around a function with callers/callees.

    Uses bracketed labels and sanitized ids so that Mermaid reliably renders.
    """
    try:
        def safe_id(label: str) -> str:
            s = str(label)
            out = []
            for ch in s:
                out.append(ch if ch.isalnum() else "_")
            ident = "".join(out).strip("_") or "n"
            if ident[0].isdigit():
                ident = f"n_{ident}"
            return ident

        c_names: List[str] = []
        for c in callers:
            nm = c.get("name") if isinstance(c, dict) else None
            if nm and nm not in c_names:
                c_names.append(nm)
            if len(c_names) >= max_nodes:
                break
        d_names: List[str] = []
        for c in callees:
            nm = c.get("name") if isinstance(c, dict) else None
            if nm and nm not in d_names:
                d_names.append(nm)
            if len(d_names) >= max_nodes:
                break

        center_id = safe_id(func_name)
        parts: List[str] = ["flowchart LR"]
        # Define center node implicitly via first edge
        for nm in c_names:
            left_id = safe_id(nm)
            parts.append(f"  {left_id}[\"{nm}\"] --> {center_id}[\"{func_name}\"]")
        for nm in d_names:
            right_id = safe_id(nm)
            parts.append(f"  {center_id}[\"{func_name}\"] --> {right_id}[\"{nm}\"]")
        if len(parts) <= 1:
            return ""
        return "\n".join(parts)
    except Exception:
        return ""

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

# Stage icons and animated activity (lightweight; no backend cost)
STAGE_LABELS = {
    "start": ("🚀", "starting"),
    "clone": ("⬇️", "cloning"),
    "scan": ("🧭", "scanning"),
    "parse": ("🧠", "parsing"),
    "stats": ("🧮", "statistics"),
    "graph": ("🧱", "graph"),
    "docs": ("📝", "docs"),
    "diagrams": ("📈", "diagrams"),
    "done": ("✅", "done"),
    "error": ("❌", "error"),
}
SPINNER_FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

def animated_status(stage: str, base_message: str, job_id: str) -> str:
    key = f"anim_{job_id}"
    cnt = st.session_state.get(key, 0)
    st.session_state[key] = cnt + 1
    frame = SPINNER_FRAMES[cnt % len(SPINNER_FRAMES)]
    # Keep it real: prefer backend message; just add a light spinner
    if stage == "error":
        return base_message or "An error occurred"
    if base_message:
        return f"{base_message} {frame}"
    # Fallback phrasing when backend omitted message
    fallback = {
        "start": "Preparing workspace",
        "clone": "Cloning repository",
        "scan": "Scanning repository structure",
        "parse": "Extracting entities",
        "stats": "Aggregating statistics",
        "graph": "Building code graph",
        "docs": "Generating documentation",
        "diagrams": "Rendering diagrams",
    }.get(stage, "Working")
    return f"{fallback} {frame}"


# Small helper: detect cached hints and format a tiny chip (no raw HTML)
def _has_cached_hint(text: str) -> bool:
    try:
        return isinstance(text, str) and ("cached" in text.lower())
    except Exception:
        return False


def _add_cached_chip(msg: str) -> str:
    # Keep it subtle and HTML-free per UI preference
    return f"{msg} • 🟢 Cached"

def render_stats(stats: Dict[str, Any]):
    """Render statistics in a nice grid layout."""
    st.subheader("📊 Repository Statistics")

    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Files", stats.get("files", 0))
    with col2:
        st.metric("Code Files", stats.get("code_files", 0))
    with col3:
        st.metric("Test Files", stats.get("tests_files", 0))
    with col4:
        st.metric("Doc Files", stats.get("docs", 0))

    # Language breakdown
    if "languages" in stats and stats["languages"]:
        st.subheader("💻 Languages")
        lang_cols = st.columns(min(len(stats["languages"]), 5))
        for idx, (lang, count) in enumerate(stats["languages"].items()):
            with lang_cols[idx % 5]:
                st.metric(lang.capitalize(), count)

    # Top directories
    if "top_dirs_code" in stats and stats["top_dirs_code"]:
        st.subheader("📁 Top Directories (by code files)")
        top_dirs = sorted(stats["top_dirs_code"].items(), key=lambda x: x[1], reverse=True)[:10]
        dir_data = {"Directory": [d[0] for d in top_dirs], "Files": [d[1] for d in top_dirs]}
        st.bar_chart(dir_data, x="Directory", y="Files", horizontal=True)

    # Top files by lines
    if "top_files_by_lines" in stats and stats["top_files_by_lines"]:
        st.subheader("📄 Top Files (by lines of code)")
        top_files = stats["top_files_by_lines"][:10]
        for idx, file_info in enumerate(top_files, 1):
            path = file_info.get("path", "unknown")
            lines = file_info.get("lines", 0)
            st.text(f"{idx}. {path} ({lines:,} lines)")

def render_file_tree(file_tree: List[Dict[str, Any]]):
    """Render file tree similar to the `tree` command, with connectors and colors."""
    st.subheader("🌲 File Tree")

    if not file_tree:
        st.info("No files found.")
        return

    # Build a nested tree structure
    root: Dict[str, Any] = {"dirs": {}, "files": []}
    for f in file_tree:
        path = f.get("path", "")
        parts = [p for p in path.split("/") if p]
        if not parts:
            continue
        node = root
        for d in parts[:-1]:
            node = node["dirs"].setdefault(d, {"dirs": {}, "files": []})
        node["files"].append(parts[-1])

    # Icon/kind by extension
    def file_kind(name: str) -> str:
        lower = name.lower()
        if lower.endswith(".py"): return "py"
        if lower.endswith((".js", ".jsx", ".ts", ".tsx")): return "js"
        if lower.endswith((".md", ".rst")): return "md"
        if lower.endswith((".json", ".yml", ".yaml", ".toml")): return "conf"
        if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")): return "img"
        return "other"

    def file_icon(name: str) -> str:
        k = file_kind(name)
        return {"py": "🐍", "js": "🧩", "md": "📘", "conf": "🧾", "img": "🖼️"}.get(k, "📄")

    # Produce ASCII tree lines with connectors and depth limit
    def build_lines(node: Dict[str, Any], prefix: str = "", depth: int = 0, max_depth: int = 3) -> List[str]:
        lines: List[str] = []
        dirs = sorted(node["dirs"].items(), key=lambda x: x[0])
        files = sorted(node["files"])  # type: ignore
        total = len(dirs) + len(files)

        # Directories
        for idx, (dname, dnode) in enumerate(dirs):
            last = (idx == total - 1) and (len(files) == 0)
            branch = "└──" if last else "├──"
            lines.append(f"{prefix}{branch} <span class=\"dir\"><span class=\"ico\">📁</span> {dname}/</span>")
            next_prefix = prefix + ("    " if last else "│   ")
            if depth + 1 < max_depth:
                lines.extend(build_lines(dnode, next_prefix, depth + 1, max_depth))

        # Files
        for j, fname in enumerate(files):
            last = (j + len(dirs) == total - 1)
            branch = "└──" if last else "├──"
            kind = file_kind(fname)
            icon = file_icon(fname)
            lines.append(f"{prefix}{branch} <span class=\"file lang-{kind}\"><span class=\"ico\">{icon}</span> {fname}</span>")
        return lines

    # Root header line + content
    lines = ["<span class=\"dir\"><span class=\"ico\">📁</span> Repository Root/</span>"]
    lines.extend(build_lines(root, "", 0, 3))

    # Render inside a small iframe to avoid showing raw HTML in Streamlit
    html_doc = f"""
    <html>
      <head>
        <meta charset='utf-8'/>
        <style>
          body {{ margin: 0; }}
          .tree-pre {{
            background:#fafafa; border:1px solid #eee; border-radius:8px;
            padding:12px 14px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco,
            Consolas, 'Liberation Mono', monospace; font-size: 13px; line-height: 1.5;
            white-space: pre; overflow: auto;
          }}
          .tree-pre .ico {{ display:inline-block; width: 1.2rem; text-align:center; }}
          .tree-pre .dir {{ color:#2563eb; font-weight:600; }}
          .tree-pre .file.lang-py  {{ color:#fbbf24; }}
          .tree-pre .file.lang-js  {{ color:#f59e0b; }}
          .tree-pre .file.lang-md  {{ color:#3b82f6; }}
          .tree-pre .file.lang-conf{{ color:#6b7280; }}
          .tree-pre .file.lang-img {{ color:#8b5cf6; }}
        </style>
      </head>
      <body>
        <pre class='tree-pre'>{'\n'.join(lines)}</pre>
      </body>
    </html>
    """
    height = min(700, 28 * (len(lines) + 2))
    components.html(html_doc, height=height, scrolling=True)

# Mermaid rendering helper (no extra package; embeds mermaid.js)
def render_mermaid_diagram(title: str, diagram: str, height: int = 500):
        """Render a Mermaid diagram inside Streamlit using an isolated HTML snippet.

        Improvements:
        - HTML-escape special characters in diagram source to avoid HTML parsing issues
        - Unique container scoping so multiple diagrams never conflict
        - Robust loader: try ESM first, then fall back to UMD build if ESM import fails
        - Looser security level to allow long labels and special chars in nodes
        """
        st.markdown(f"#### {title}")
        if not isinstance(diagram, str) or not diagram.strip():
                st.info("No diagram available.")
                return

        from html import escape as _html_escape

        container_id = f"mmd-{uuid.uuid4().hex}"
        # Escape only &,<,> leaving quotes as-is to keep Mermaid labels intact
        safe_diagram = _html_escape(diagram, quote=False)
        html = f"""
        <div id="{container_id}" style="width:100%;">
            <style>
                /* Ensure visible overflow for large diagrams and monospace font for consistency */
                #{container_id} .mermaid {{
                    display:block; width:100%; overflow:auto; font-family: ui-monospace, monospace;
                }}
            </style>
            <pre class="mermaid">{safe_diagram}</pre>
        </div>
        <script type="module">
            const scopeSel = '#{container_id} .mermaid';
            async function esmRender() {{
                const mermaid = (await import('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs')).default;
                mermaid.initialize({{ startOnLoad: false, securityLevel: 'loose' }});
                await mermaid.run({{ querySelector: scopeSel, suppressErrors: true }});
                return true;
            }}
            (async () => {{
                try {{
                    await esmRender();
                }} catch (e) {{
                    console.warn('ESM mermaid failed, falling back to UMD', e);
                    // Fallback to UMD build
                    function loadScript(src) {{
                        return new Promise((resolve, reject) => {{
                            const s = document.createElement('script');
                            s.src = src; s.async = true; s.onload = resolve; s.onerror = reject;
                            document.head.appendChild(s);
                        }});
                    }}
                    try {{
                        await loadScript('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js');
                    }} catch (e2) {{
                        try {{ await loadScript('https://unpkg.com/mermaid@11/dist/mermaid.min.js'); }} catch (e3) {{ console.error('UMD load failed', e2, e3); }}
                    }}
                    try {{
                        if (window.mermaid) {{
                            window.mermaid.initialize({{ startOnLoad: false, securityLevel: 'loose' }});
                            // UMD exposes contentLoaded to render existing elements
                            if (typeof window.mermaid.run === 'function') {{
                                await window.mermaid.run({{ querySelector: scopeSel, suppressErrors: true }});
                            }} else if (typeof window.mermaid.contentLoaded === 'function') {{
                                window.mermaid.contentLoaded();
                            }}
                        }} else {{
                            console.error('Mermaid UMD not available after load');
                        }}
                    }} catch (e4) {{ console.error('Mermaid UMD render failed', e4); }}
                }}
            }})();
        </script>
        """

        components.html(html, height=height)


def render_markdown_with_mermaid(documentation: str):
        """Render markdown that may contain ```mermaid fenced blocks.

        For each mermaid fenced block we render it using components.html (so the
        Mermaid library can run), and for other markdown we use st.markdown.
        Uses the same robust loader and HTML-escaping as render_mermaid_diagram.
        """
        import re
        from html import escape as _html_escape

        if not documentation:
                return

        # Pattern captures content inside ```mermaid\n ... ``` (non-greedy)
        pat = re.compile(r"```mermaid\n(.*?)\n```", re.S)
        last = 0
        for m in pat.finditer(documentation):
                pre = documentation[last:m.start()]
                if pre.strip():
                        st.markdown(pre)
                mmd = m.group(1) or ""
                container_id = f"mmd-{uuid.uuid4().hex}"
                safe_mmd = _html_escape(mmd, quote=False)
                html = f"""
                <div id=\"{container_id}\" style=\"width:100%;\">
                    <pre class=\"mermaid\">{safe_mmd}</pre>
                </div>
                <script type=\"module\">
                    const scopeSel = '#{container_id} .mermaid';
                    async function esmRender() {{
                        const mermaid = (await import('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs')).default;
                        mermaid.initialize({{ startOnLoad: false, securityLevel: 'loose' }});
                        await mermaid.run({{ querySelector: scopeSel, suppressErrors: true }});
                        return true;
                    }}
                    (async () => {{
                        try {{
                            await esmRender();
                        }} catch (e) {{
                            console.warn('ESM mermaid failed, falling back to UMD', e);
                            function loadScript(src) {{
                                return new Promise((resolve, reject) => {{
                                    const s = document.createElement('script');
                                    s.src = src; s.async = true; s.onload = resolve; s.onerror = reject;
                                    document.head.appendChild(s);
                                }});
                            }}
                            try {{
                                await loadScript('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js');
                            }} catch (e2) {{
                                try {{ await loadScript('https://unpkg.com/mermaid@11/dist/mermaid.min.js'); }} catch (e3) {{ console.error('UMD load failed', e2, e3); }}
                            }}
                            try {{
                                if (window.mermaid) {{
                                    window.mermaid.initialize({{ startOnLoad: false, securityLevel: 'loose' }});
                                    if (typeof window.mermaid.run === 'function') {{
                                        await window.mermaid.run({{ querySelector: scopeSel, suppressErrors: true }});
                                    }} else if (typeof window.mermaid.contentLoaded === 'function') {{
                                        window.mermaid.contentLoaded();
                                    }}
                                }} else {{
                                    console.error('Mermaid UMD not available after load');
                                }}
                            }} catch (e4) {{ console.error('Mermaid UMD render failed', e4); }}
                        }}
                    }})();
                </script>
                """
                components.html(html, height=420)
                last = m.end()

        tail = documentation[last:]
        if tail.strip():
                st.markdown(tail)

# Copy-to-clipboard helper for .mmd strings
def copy_mmd_button(label: str, mmd: str, key: str):
    try:
        esc = json.dumps(mmd if isinstance(mmd, str) else str(mmd))
    except Exception:
        esc = json.dumps("")
    components.html(
        f"""
        <button id=\"btn-{key}\" style=\"margin: 0.25rem 0;\">{label}</button>
        <script>
        const txt_{key.replace('-', '_')} = {esc};
        const el_{key.replace('-', '_')} = document.getElementById('btn-{key}');
        if (el_{key.replace('-', '_')}) {{
            el_{key.replace('-', '_')}.addEventListener('click', async () => {{
                try {{
                    await navigator.clipboard.writeText(txt_{key.replace('-', '_')});
                    alert('Copied to clipboard');
                }} catch (e) {{
                    alert('Copy failed: ' + e);
                }}
            }});
        }}
        </script>
        """,
        height=45,
    )


def main():
    # Header
    st.markdown('<h1 class="main-header">🧠 Codebase Genius</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Repository Documentation Generator</p>', unsafe_allow_html=True)

    # Main input section in a form: pressing Enter submits and triggers generation
    with st.form("generate_form", clear_on_submit=False):
        repo_url = st.text_input(
            "Repository URL",
            placeholder="https://github.com/username/repo",
            help="Enter a GitHub repository URL",
            key="repo_url_main",
        )
        generate_button = st.form_submit_button("🚀 Generate Documentation", type="primary")


    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Initialize session state for diagram controls
        if "include_diagrams" not in st.session_state:
            st.session_state.include_diagrams = False
        if "diagram_filter_tests" not in st.session_state:
            st.session_state.diagram_filter_tests = True
        if "diagram_max_edges_call" not in st.session_state:
            st.session_state.diagram_max_edges_call = 400
        if "diagram_max_edges_class" not in st.session_state:
            st.session_state.diagram_max_edges_class = 400
        if "diagram_max_edges_module" not in st.session_state:
            st.session_state.diagram_max_edges_module = 400

        # Essentials
        depth = st.selectbox(
            "Analysis Depth",
            options=["deep", "standard"],
            index=0,
            help="Deep mode clones and analyzes the full repository"
        )
        use_llm = st.checkbox("Enable AI", value=True, help="Use LLM to generate comprehensive documentation")

        include_diagrams = st.checkbox(
            "Include Diagrams",
            key="include_diagrams",
            help="Generate Mermaid diagrams (call graph, class hierarchy, module graph)"
        )

        # Response size
        return_full_data = st.checkbox(
            "Full response",
            value=True,
            help="Include complete file tree and entities in the response. Disable for very large repos.",
        )


        # Advanced (hidden by default)
        with st.expander("Advanced Settings", expanded=False):
            st.caption("Diagrams")
            diagram_filter_tests = st.checkbox("Filter test modules/classes/functions in diagrams", key="diagram_filter_tests")

            col1, col2, col3 = st.columns(3)
            with col1:
                diagram_max_edges_call = st.number_input("Max Edges: Call Graph", min_value=50, max_value=2000, step=50, key="diagram_max_edges_call")
            with col2:
                diagram_max_edges_class = st.number_input("Max Edges: Class Hierarchy", min_value=50, max_value=2000, step=50, key="diagram_max_edges_class")
            with col3:
                diagram_max_edges_module = st.number_input("Max Edges: Module Graph", min_value=50, max_value=2000, step=50, key="diagram_max_edges_module")

            st.caption("Metrics")
            top_n = st.slider("Top N Items", min_value=3, max_value=20, value=10, help="Number of top items to track")

            st.caption("Filters")
            include_paths_text = st.text_area(
                "Include Paths (one per line)",
                placeholder="src/\nlib/\napp/",
                help="Only scan files in these directories",
            )
            include_paths = [p.strip() for p in include_paths_text.split("\n") if p.strip()]

            use_default_exts = st.checkbox("Use default extensions", value=True)
            if not use_default_exts:
                include_exts_text = st.text_area(
                    "Include Extensions (one per line)",
                    placeholder=".py\n.js\n.ts",
                    help="Only include files with these extensions",
                )
                include_exts = [e.strip() for e in include_exts_text.split("\n") if e.strip()]
            else:
                include_exts = []

            exclude_dirs_text = st.text_area(
                "Exclude Directories (one per line)",
                placeholder="build/\ndist/\n.cache/",
                help="Skip these directories",
            )
            exclude_dirs = [d.strip() for d in exclude_dirs_text.split("\n") if d.strip()]

            st.caption("Performance")
            max_files = st.number_input("Max Files", min_value=0, value=0, help="0 = unlimited")
            max_file_size_mb = st.number_input("Max File Size (MB)", min_value=0, value=0, help="0 = unlimited")
            max_file_size_bytes = max_file_size_mb * 1024 * 1024 if max_file_size_mb > 0 else 0
    # Main content area
    if generate_button:
        if not repo_url:
            st.error("Please enter a repository URL")
            return

        # Build configuration
        job_id = str(uuid.uuid4())
        config = {
            "repo_url": repo_url,
            "depth": depth,
            "use_llm": use_llm,
            "include_diagrams": include_diagrams,
            "top_n": top_n,
            "exclude_dirs": exclude_dirs,
            "include_exts": include_exts,
            "include_paths": include_paths,
            "max_files": max_files,
            "max_file_size_bytes": max_file_size_bytes,
            "diagram_filter_tests": diagram_filter_tests,
            "diagram_max_edges_call": diagram_max_edges_call,
            "diagram_max_edges_class": diagram_max_edges_class,
            "diagram_max_edges_module": diagram_max_edges_module,
            "return_full_data": return_full_data,
            "job_id": job_id,
        }

        # Show configuration
        with st.expander("📋 Request Configuration"):
            st.json(config)

        # Start request in background and poll progress
        result_container: Dict[str, Any] = {"result": None}
        def _run():
            result_container["result"] = call_generate_docs(config)
        t = threading.Thread(target=_run, daemon=True)
        t.start()

        progress_bar = st.progress(0)
        status_box = st.empty()
        activity_box = st.empty()
        last_stage = ""
        st.session_state[f"log_{job_id}"] = []

        # Reset animation counter for this job
        st.session_state[f"anim_{job_id}"] = 0

        # Reset cached chip flag for this job
        st.session_state[f"cached_seen_{job_id}"] = False


        # Poll progress until the background thread finishes
        last_percent = 0
        while t.is_alive():
            prog_resp = call_get_progress(repo_url, job_id)
            if isinstance(prog_resp, dict):
                prog = prog_resp.get("progress") or {}
                raw_percent = int(prog.get("percent", last_percent))
                stage = prog.get("stage", "start")
                message = prog.get("message", "Working...")

                # If backend reports completion, finalize once and break; final message shown after join
                if (raw_percent >= 100) or (stage == "done"):
                    progress_bar.progress(100)
                    break

                percent = max(min(raw_percent, 99), last_percent)
                progress_bar.progress(percent)
                icon, label = STAGE_LABELS.get(stage, ("⏳", stage))
                animated = animated_status(stage, message, job_id)
                cached_key = f"cached_seen_{job_id}"
                hit_now = _has_cached_hint(message)
                if hit_now:
                    st.session_state[cached_key] = True
                is_cached = hit_now or st.session_state.get(cached_key, False)
                status_text = f"{icon} {percent}% • {label} — {animated}"
                if is_cached:
                    status_text = _add_cached_chip(status_text)
                status_box.info(status_text)

                # Update lightweight activity log (last 5 events) after clamping percent
                if (stage != last_stage) or (percent > last_percent):
                    label_for_log = STAGE_LABELS.get(stage, ("", stage))[1]
                    line = f"{percent}% • {label_for_log} — {message}"
                    log_key = f"log_{job_id}"
                    hist = st.session_state.get(log_key, [])
                    hist.append(line)
                    st.session_state[log_key] = hist[-5:]
                    activity_box.caption("  ·  ".join(st.session_state[log_key]))
                    last_stage = stage

                last_percent = percent
            time.sleep(1.0)

        # Join thread and fetch final result (be patient after 100%/done)
        progress_bar.progress(100)
        # Wait up to 30s for the background request to deliver the result
        deadline = time.time() + 30
        while result_container.get("result") is None and t.is_alive() and time.time() < deadline:
            status_box.info("⏳ 100% • done — Finalizing results…")
            t.join(timeout=0.5)
        # Final attempt to join without blocking
        t.join(timeout=0)
        result = result_container.get("result") or {"status": "error", "message": "Failed to get result"}
        if result.get("status") == "success":
            consolidated = "✅ 100% • done — Completed · Success! Documentation generated successfully."
            cached_key = f"cached_seen_{job_id}"
            was_from_cache = bool(result.get("from_cache")) if isinstance(result, dict) else False
            final_is_cached = was_from_cache or st.session_state.get(cached_key, False)
            if final_is_cached:
                consolidated = _add_cached_chip(consolidated)
            status_box.success(consolidated)
        else:
            # Show error in the status box to avoid contradictory messages
            err_line = f"❌ {result.get('message', 'Failed to generate documentation')}"
            cached_key = f"cached_seen_{job_id}"
            was_from_cache = bool(result.get("from_cache")) if isinstance(result, dict) else False
            final_is_cached = was_from_cache or st.session_state.get(cached_key, False)
            if final_is_cached:
                err_line = _add_cached_chip(err_line)
            status_box.error(err_line)

        # Display results
        if result.get("status") == "error":
            st.markdown(f'<div class="error-box">❌ <strong>Error:</strong> {result.get("message", "Unknown error")}</div>', unsafe_allow_html=True)
        elif result.get("status") == "success":
            # Saved paths (concise message)
            saved = result.get("saved", {})
            if isinstance(saved, dict) and saved:
                base_dir = saved.get("base_dir")
                if not base_dir:
                    # Derive a common directory from one of the file paths
                    base_candidate = saved.get("documentation_path") or saved.get("statistics_path")
                    if base_candidate:
                        import os as _os
                        base_dir = _os.path.dirname(base_candidate)
                if base_dir:
                    st.info(f"Documentations and statistics saved to {base_dir}")


                # Persist repo/depth for CCG Explorer and init CCG cache
                st.session_state["last_repo_url"] = repo_url
                st.session_state["last_depth"] = depth
                st.session_state["last_top_n"] = top_n
                if "ccg_cache" not in st.session_state:
                    st.session_state.ccg_cache = {}

            # Create tabs for different views (added 📈 Diagrams and ⚠️ Errors)
            tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📖 Documentation", "📊 Statistics", "📈 Diagrams", "🌲 File Tree", "🔧 Raw Data", "⚠️ Errors", "🧭 CCG Explorer"])

            with tab1:

                with st.expander("📈 Diagrams Preview", expanded=False):
                    diags = result.get("diagrams", {})
                    if not diags:
                        st.info("No diagrams found. Enable 'Include Diagrams' and re-run.")
                    else:
                        if diags.get("call_graph"):
                            render_mermaid_diagram("Call Graph", diags["call_graph"], height=450)
                            copy_mmd_button("📋 Copy Call Graph (.mmd)", diags["call_graph"], key="call-preview")
                        if diags.get("class_hierarchy"):
                            render_mermaid_diagram("Class Hierarchy", diags["class_hierarchy"], height=450)
                            copy_mmd_button("📋 Copy Class Hierarchy (.mmd)", diags["class_hierarchy"], key="class-preview")
                        if diags.get("module_graph"):
                            render_mermaid_diagram("Module Graph", diags["module_graph"], height=400)
                            copy_mmd_button("📋 Copy Module Graph (.mmd)", diags["module_graph"], key="module-preview")


                st.subheader("Generated Documentation")
                documentation = result.get("documentation", "No documentation generated.")
                # Render documentation but process any mermaid fenced blocks so
                # diagrams appear rendered instead of raw code blocks.
                render_markdown_with_mermaid(documentation)

                # Download button
                st.download_button(
                    label="⬇️ Download Documentation (Markdown)",
                    data=documentation,
                    file_name=f"{repo_url.split('/')[-1]}_documentation.md",
                    mime="text/markdown"
                )

            with tab2:
                if "stats" in result:
                    render_stats(result["stats"])
                else:
                    st.info("No statistics available.")


            with tab3:
                st.subheader("Mermaid Diagrams")
                diags = result.get("diagrams", {})
                if not diags:
                    st.info("No diagrams found in response. Enable 'Include Diagrams' in the sidebar and re-run.")
                else:
                    if diags.get("call_graph"):
                        render_mermaid_diagram("Call Graph", diags["call_graph"], height=600)
                        st.download_button(
                            label="\u2B07\uFE0F Download Call Graph (.mmd)",
                            data=diags["call_graph"],
                            file_name="call_graph.mmd",
                            mime="text/plain",
                        )
                        copy_mmd_button("📋 Copy Call Graph (.mmd)", diags["call_graph"], key="call-diag")

                    if diags.get("class_hierarchy"):
                        render_mermaid_diagram("Class Hierarchy", diags["class_hierarchy"], height=600)
                        st.download_button(
                            label="\u2B07\uFE0F Download Class Hierarchy (.mmd)",
                            data=diags["class_hierarchy"],
                            file_name="class_hierarchy.mmd",
                            mime="text/plain",
                        )
                        copy_mmd_button("📋 Copy Class Hierarchy (.mmd)", diags["class_hierarchy"], key="class-diag")

                    if diags.get("module_graph"):
                        render_mermaid_diagram("Module Graph", diags["module_graph"], height=500)
                        st.download_button(
                            label="\u2B07\uFE0F Download Module Graph (.mmd)",
                            data=diags["module_graph"],
                            file_name="module_graph.mmd",
                            mime="text/plain",
                        )
                        copy_mmd_button("📋 Copy Module Graph (.mmd)", diags["module_graph"], key="module-diag")


            with tab4:
                if "file_tree" in result:
                    if not result.get("file_tree") and not return_full_data:
                        st.info("File tree not included in response (Include full response payload disabled). Enable in sidebar to view.")
                    else:
                        render_file_tree(result["file_tree"])
                else:
                    st.info("No file tree available.")

            with tab5:
                st.subheader("Raw API Response")
                st.json(result)

            with tab6:
                ents = result.get("entities") or {}
                errs = []
                if isinstance(ents, dict):
                    errs = ents.get("errors") or []
                errs_obj = result.get("errors") if isinstance(result.get("errors"), dict) else {}
                ov_err = errs_obj.get("overview") if isinstance(errs_obj, dict) else None
                graph_err = errs_obj.get("graph") if isinstance(errs_obj, dict) else None
                total = len(errs) + (1 if ov_err else 0) + (1 if graph_err else 0)
                st.subheader(f"Errors ({total})")
                if ov_err:
                    st.error(f"Overview error: {ov_err}")
                if graph_err:
                    st.error(f"Graph build error: {graph_err}")
                if errs:
                    for i, e in enumerate(errs[:200], 1):
                        st.write(f"{i}. {e.get('file', 'unknown')}: {e.get('error', '')}")
                if total == 0:
                    st.info("No errors were recorded.")


            with tab7:
                st.subheader("🧭 CCG Explorer")
                lr = st.session_state.get("last_repo_url")
                ld = st.session_state.get("last_depth")
                tn = st.session_state.get("last_top_n", 5)
                if not lr or not ld:
                    st.info("Run an analysis first to enable the CCG Explorer.")
                else:
                    st.caption(f"Target: {lr} • Depth: {ld}")

                    # Overview panel
                    with st.expander("📌 CCG Overview", expanded=True):
                        refresh = st.button("🔄 Refresh Overview", key="ccg_refresh_overview")
                        k = f"overview::{lr}::{ld}::{tn}"
                        if refresh:
                            st.session_state.ccg_cache.pop(k, None)
                        data_ov = st.session_state.ccg_cache.get(k)
                        if data_ov is None:
                            with st.spinner("Loading overview..."):
                                data_ov = call_ccg_overview(lr, ld, tn)
                                st.session_state.ccg_cache[k] = data_ov
                        if data_ov.get("status") != "success":
                            st.error(data_ov.get("message", "Failed to load overview"))
                        else:
                            ov = data_ov.get("overview") or {}
                            counts = ov.get("counts") or {}
                            ca, cb, cc = st.columns(3)
                            ca.metric("🔁 Calls", counts.get("calls", 0))
                            cb.metric("🧬 Inherits", counts.get("inherits", 0))
                            cc.metric("📦 Imports", counts.get("imports", 0))
                            top = ov.get("top") or {}
                            t1, t2, t3 = st.columns(3)
                            def _tab(items):
                                rows = []
                                items = items or []
                                for it in items[:tn]:
                                    if isinstance(it, dict):
                                        nm = it.get("name", ""); ct = it.get("count")
                                    else:
                                        nm = str(it); ct = None
                                    rows.append({"Name": nm, "Count": ct})
                                st.table(rows)
                            with t1:
                                st.caption("Top Functions (fan-in)"); _tab(top.get("functions") or [])
                            with t2:
                                st.caption("Top Classes (subclasses)"); _tab(top.get("classes") or [])
                            with t3:
                                st.caption("Top Modules (deps)"); _tab(top.get("modules") or [])
                            st.download_button(
                                label="⬇️ Download Overview (JSON)",
                                data=json.dumps(ov, indent=2),
                                file_name="ccg_overview.json",
                                mime="application/json",
                            )


                    # Graph Stats (Walker)
                    with st.expander("📊 Graph Stats (Walker)", expanded=False):
                        gk = f"gstats::{lr}::{ld}::{tn}"
                        refresh_stats = st.button("🔄 Refresh Graph Stats", key="ccg_refresh_gstats")
                        if refresh_stats:
                            st.session_state.ccg_cache.pop(gk, None)
                        cache_hit = gk in st.session_state.ccg_cache
                        data_st = st.session_state.ccg_cache.get(gk)
                        if data_st is None:
                            with st.spinner("Computing graph stats…"):
                                data_st = call_graph_stats(lr, ld, tn)
                                st.session_state.ccg_cache[gk] = data_st
                        if data_st.get("status") != "success":
                            st.error(data_st.get("message", "Failed to compute graph stats"))
                        else:
                            msg = "Graph stats ready"
                            if cache_hit:
                                msg = _add_cached_chip(msg)
                            st.success(msg)
                            stats_payload = data_st.get("stats") or {}
                            # Reuse the existing stats renderer if payload aligns
                            try:
                                render_stats(stats_payload)
                            except Exception:
                                st.json(stats_payload)
                            col_a, col_b = st.columns([1, 1])
                            with col_a:
                                st.download_button("⬇️ Download Graph Stats (JSON)", data=json.dumps(stats_payload, indent=2), file_name="graph_stats.json", mime="application/json")
                            with col_b:
                                show_gstats_json = st.checkbox("Show raw JSON", key="gstats_show_json")
                                if show_gstats_json:
                                    st.code(json.dumps(stats_payload, indent=2), language="json")

                    # Graph Docs (Walker)
                    with st.expander("📝 Graph Docs (Walker)", expanded=False):
                        gkd = f"gdocs::{lr}::{ld}::{tn}"
                        refresh_docs = st.button("🔄 Refresh Graph Docs", key="ccg_refresh_gdocs")
                        if refresh_docs:
                            st.session_state.ccg_cache.pop(gkd, None)
                        cache_hit = gkd in st.session_state.ccg_cache
                        data_doc = st.session_state.ccg_cache.get(gkd)
                        if data_doc is None:
                            with st.spinner("Collecting documentation aggregates…"):
                                data_doc = call_graph_docs(lr, ld, tn)
                                st.session_state.ccg_cache[gkd] = data_doc
                        if data_doc.get("status") != "success":
                            st.error(data_doc.get("message", "Failed to collect doc aggregates"))
                        else:
                            msg = "Graph docs ready"
                            if cache_hit:
                                msg = _add_cached_chip(msg)
                            st.success(msg)
                            doc_payload = data_doc.get("docs") or {}
                            c1, c2, c3 = st.columns([1, 1, 2])
                            with c1:
                                st.metric("Total Functions", doc_payload.get("total_functions", 0))
                            with c2:
                                st.metric("API Classes", len(doc_payload.get("api_classes", [])))
                            # Top files table with server ranking toggle + extra fields + sorting
                            server_lines = list(doc_payload.get("top_files", []))
                            server_size = list(doc_payload.get("top_files_by_size", []))
                            any_rows = server_lines or server_size
                            if any_rows:
                                rank_choice = st.radio("Rank by", options=["Lines", "Size"], index=0, horizontal=True, key="gdocs_rank_by")
                                use_size = (rank_choice == "Size") and len(server_size) > 0
                                top_files_all = server_size if use_size else server_lines

                                # Determine available sort keys; prefer numeric (lines/size) then path
                                possible = []
                                for k in ["lines", "size", "path"]:
                                    if any(isinstance(it, dict) and (k in it) for it in top_files_all):
                                        possible.append(k)
                                if not possible:
                                    # Fallback: any keys from first item
                                    possible = list(top_files_all[0].keys())

                                csort1, csort2 = st.columns([3, 1])
                                with csort1:
                                    default_key = "size" if use_size and ("size" in possible) else ("lines" if "lines" in possible else possible[0])
                                    default_idx = possible.index(default_key)
                                    sort_by = st.selectbox("Sort by", options=possible, index=default_idx, key="gdocs_sort_key")
                                with csort2:
                                    asc = st.checkbox("Ascending", value=False, key="gdocs_sort_asc")

                                # Column selector
                                # Gather all available keys across rows (keep order stable)
                                available = []
                                for it in top_files_all:
                                    if isinstance(it, dict):
                                        for k in it.keys():
                                            if k not in available:
                                                available.append(k)
                                preferred = [k for k in ["path", "lines", "size", "language"] if k in available]
                                rest = [k for k in available if k not in preferred]
                                default_cols = preferred + rest
                                selected_cols = st.multiselect("Columns", options=available, default=default_cols, key="gdocs_cols")

                                def _sv(d, k):
                                    v = d.get(k)
                                    if isinstance(v, (int, float)): return v
                                    if isinstance(v, str): return v.lower()
                                    return 0 if k in ["lines", "size"] else ""

                                sorted_tf = sorted(top_files_all, key=lambda d: _sv(d, sort_by), reverse=not asc)[:tn]
                                cap_rank = "size" if use_size else "lines"
                                st.caption(f"Top Files (from walker) — ranked by {cap_rank} • sorted by {sort_by}{' ↑' if asc else ' ↓'}")
                                # Filter to selected columns and preserve order
                                filtered = [ {k: row.get(k) for k in selected_cols} for row in sorted_tf ]
                                st.table(filtered)
                            if doc_payload.get("api_classes"):
                                st.caption("API Classes")
                                st.table([{ "Class": c } for c in doc_payload.get("api_classes", [])[:tn]])
                            col_a, col_b = st.columns([1, 1])
                            with col_a:
                                st.download_button("⬇️ Download Graph Docs (JSON)", data=json.dumps(doc_payload, indent=2), file_name="graph_docs.json", mime="application/json")
                            with col_b:
                                show_gdocs_json = st.checkbox("Show raw JSON", key="gdocs_show_json")
                                if show_gdocs_json:
                                    st.code(json.dumps(doc_payload, indent=2), language="json")

                    # Function Callers
                    with st.expander("🧰 Function Callers", expanded=False):
                        with st.form("form_ccg_callers"):
                            fn = st.text_input("Function name", value=st.session_state.get("ccg_fn_callers", ""), key="ccg_fn_callers_input")
                            ok = st.form_submit_button("🔎 Query Callers")
                        if ok:
                            st.session_state["ccg_fn_callers"] = fn
                            if not fn.strip():
                                st.warning("Please enter a function name.")
                            else:
                                ckey = f"callers::{lr}::{ld}::{fn}"
                                data_c = st.session_state.ccg_cache.get(ckey)
                                if data_c is None:
                                    with st.spinner("Fetching callers..."):
                                        data_c = call_ccg_callers(lr, fn, ld)
                                        st.session_state.ccg_cache[ckey] = data_c
                                if data_c.get("status") != "success":
                                    st.error(data_c.get("message", "Failed to fetch callers"))
                                else:
                                    callers = data_c.get("results") or []
                                    st.success(f"Found {len(callers)} callers for {fn}")
                                    rows = [{"Name": (c.get("name") if isinstance(c, dict) else str(c))} for c in callers]
                                    st.dataframe(rows, use_container_width=True)
                                    # also fetch callees to draw a richer micro-diagram
                                    dkey = f"callees::{lr}::{ld}::{fn}"
                                    data_d = st.session_state.ccg_cache.get(dkey)
                                    if data_d is None or data_d.get("status") != "success":
                                        try:
                                            data_d = call_ccg_callees(lr, fn, ld)
                                            st.session_state.ccg_cache[dkey] = data_d
                                        except Exception:
                                            data_d = {"results": []}
                                    callees = data_d.get("results") or []
                                    mmd = build_micro_mermaid_function(fn, callers, callees)
                                    if mmd:
                                        render_mermaid_diagram(f"Callers/Callees for {fn}", mmd, height=320)
                                        copy_mmd_button("📋 Copy Diagram (.mmd)", mmd, key=f"copy-callers-{fn}")
                                    st.download_button("⬇️ Download (JSON)", data=json.dumps(callers, indent=2), file_name=f"callers_{fn}.json", mime="application/json")

                    # Function Callees
                    with st.expander("🧰 Function Callees", expanded=False):
                        with st.form("form_ccg_callees"):
                            fn2 = st.text_input("Function name", value=st.session_state.get("ccg_fn_callees", ""), key="ccg_fn_callees_input")
                            ok2 = st.form_submit_button("🔎 Query Callees")
                        if ok2:
                            st.session_state["ccg_fn_callees"] = fn2
                            if not fn2.strip():
                                st.warning("Please enter a function name.")
                            else:
                                dkey2 = f"callees::{lr}::{ld}::{fn2}"
                                data_d2 = st.session_state.ccg_cache.get(dkey2)
                                if data_d2 is None:
                                    with st.spinner("Fetching callees..."):
                                        data_d2 = call_ccg_callees(lr, fn2, ld)
                                        st.session_state.ccg_cache[dkey2] = data_d2
                                if data_d2.get("status") != "success":
                                    st.error(data_d2.get("message", "Failed to fetch callees"))
                                else:
                                    callees2 = data_d2.get("results") or []
                                    st.success(f"Found {len(callees2)} callees for {fn2}")
                                    rows2 = [{"Name": (c.get("name") if isinstance(c, dict) else str(c))} for c in callees2]
                                    st.dataframe(rows2, use_container_width=True)
                                    ckey2 = f"callers::{lr}::{ld}::{fn2}"
                                    data_c2 = st.session_state.ccg_cache.get(ckey2)
                                    if data_c2 is None or data_c2.get("status") != "success":
                                        try:
                                            data_c2 = call_ccg_callers(lr, fn2, ld)
                                            st.session_state.ccg_cache[ckey2] = data_c2
                                        except Exception:
                                            data_c2 = {"results": []}
                                    callers2 = data_c2.get("results") or []
                                    mmd2 = build_micro_mermaid_function(fn2, callers2, callees2)
                                    if mmd2:
                                        render_mermaid_diagram(f"Callers/Callees for {fn2}", mmd2, height=320)
                                        copy_mmd_button("📋 Copy Diagram (.mmd)", mmd2, key=f"copy-callees-{fn2}")
                                    st.download_button("⬇️ Download (JSON)", data=json.dumps(callees2, indent=2), file_name=f"callees_{fn2}.json", mime="application/json")

                    # Class Subclasses
                    with st.expander("🏷️ Class Subclasses", expanded=False):
                        with st.form("form_ccg_subclasses"):
                            cn = st.text_input("Class name", value=st.session_state.get("ccg_class_name", ""), key="ccg_class_name_input")
                            ok3 = st.form_submit_button("🔎 Query Subclasses")
                        if ok3:
                            st.session_state["ccg_class_name"] = cn
                            if not cn.strip():
                                st.warning("Please enter a class name.")
                            else:
                                skey = f"subclasses::{lr}::{ld}::{cn}"
                                data_s = st.session_state.ccg_cache.get(skey)
                                if data_s is None:
                                    with st.spinner("Fetching subclasses..."):
                                        data_s = call_ccg_subclasses(lr, cn, ld)
                                        st.session_state.ccg_cache[skey] = data_s
                                if data_s.get("status") != "success":
                                    st.error(data_s.get("message", "Failed to fetch subclasses"))
                                else:
                                    subs = data_s.get("results") or []
                                    st.success(f"Found {len(subs)} subclasses for {cn}")
                                    rows3 = [{"Name": (s.get("name") if isinstance(s, dict) else str(s))} for s in subs]
                                    st.dataframe(rows3, use_container_width=True)
                                    st.download_button("⬇️ Download (JSON)", data=json.dumps(subs, indent=2), file_name=f"subclasses_{cn}.json", mime="application/json")

                    # Module Dependencies
                    with st.expander("📦 Module Dependencies", expanded=False):
                        with st.form("form_ccg_dependencies"):
                            mn = st.text_input("Module name", value=st.session_state.get("ccg_module_name", ""), key="ccg_module_name_input")
                            ok4 = st.form_submit_button("🔎 Query Dependencies")
                        if ok4:
                            st.session_state["ccg_module_name"] = mn
                            if not mn.strip():
                                st.warning("Please enter a module name.")
                            else:
                                mkey = f"dependencies::{lr}::{ld}::{mn}"
                                data_m = st.session_state.ccg_cache.get(mkey)
                                if data_m is None:
                                    with st.spinner("Fetching dependencies..."):
                                        data_m = call_ccg_dependencies(lr, mn, ld)
                                        st.session_state.ccg_cache[mkey] = data_m
                                if data_m.get("status") != "success":
                                    st.error(data_m.get("message", "Failed to fetch dependencies"))
                                else:
                                    deps = data_m.get("results") or []
                                    st.success(f"Found {len(deps)} dependencies for {mn}")
                                    rows4 = [{"Name": (d.get("name") if isinstance(d, dict) else str(d))} for d in deps]
                                    st.dataframe(rows4, use_container_width=True)
                                    st.download_button("⬇️ Download (JSON)", data=json.dumps(deps, indent=2), file_name=f"dependencies_{mn}.json", mime="application/json")

        else:

            st.warning("Unexpected response format from API")
            st.json(result)
    else:
        # Welcome screen
        st.info("👈 Configure your analysis settings in the sidebar and click 'Generate Documentation' to get started!")

        st.markdown("""
        ### Features

        - 🔍 **Deep Repository Analysis**: Clone and analyze entire codebases
        - 🤖 **AI-Powered Documentation**: Generate comprehensive docs using LLM
        - 📊 **Rich Statistics**: File counts, language breakdown, top directories
        - 🎯 **Advanced Filtering**: Include/exclude paths, extensions, and directories
        - ⚡ **Performance Controls**: Limit files and file sizes for faster analysis
        - 📥 **Export**: Download documentation as Markdown

        ### Example Repo

        - `https://github.com/karpathy/micrograd` - Small educational ML library
        """)

if __name__ == "__main__":
    main()
