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
    st.markdown(f"#### {title}")
    if not isinstance(diagram, str) or not diagram.strip():
        st.info("No diagram available.")
        return
    components.html(
        f"""
        <div>
          <div class=\"mermaid\">
{diagram}
          </div>
        </div>
        <script src=\"https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js\"></script>
        <script>
          if (window.mermaid) {{
            mermaid.initialize({{ startOnLoad: true, securityLevel: 'loose' }});
            mermaid.contentLoaded();
          }} else {{
            document.addEventListener('DOMContentLoaded', function () {{
              mermaid.initialize({{ startOnLoad: true, securityLevel: 'loose' }});
            }});
          }}
        </script>
        """,
        height=height,
    )

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
            include_diagrams = st.checkbox("Include Diagrams", key="include_diagrams", help="Generate Mermaid diagrams (call graph, class hierarchy, module graph)")

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
                status_box.info(f"{icon} {percent}% • {label} — {animated}")

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
            status_box.success(consolidated)
        else:
            # Show error in the status box to avoid contradictory messages
            status_box.error(f"❌ {result.get('message', 'Failed to generate documentation')}")

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

            # Create tabs for different views (added 📈 Diagrams and ⚠️ Errors)
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📖 Documentation", "📊 Statistics", "📈 Diagrams", "🌲 File Tree", "🔧 Raw Data", "⚠️ Errors"])

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
                st.markdown(documentation)

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
