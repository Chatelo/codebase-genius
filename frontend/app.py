import streamlit as st
import requests
import json
from typing import Dict, Any, List
import streamlit.components.v1 as components


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
            timeout=300  # 5 minute timeout for large repos
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

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

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
    """Render file tree in an expandable format."""
    st.subheader("🌲 File Tree")

    if not file_tree:
        st.info("No files found.")
        return

    # Group files by directory
    dirs = {}
    for file_info in file_tree:
        path = file_info.get("path", "")
        parts = path.split("/")
        if len(parts) > 1:
            dir_name = "/".join(parts[:-1])
            if dir_name not in dirs:
                dirs[dir_name] = []
            dirs[dir_name].append(file_info)
        else:
            if "." not in dirs:
                dirs["."] = []
            dirs["."].append(file_info)

    # Display grouped files
    for dir_name in sorted(dirs.keys()):
        with st.expander(f"📂 {dir_name} ({len(dirs[dir_name])} files)"):
            for file_info in sorted(dirs[dir_name], key=lambda x: x.get("path", "")):
                path = file_info.get("path", "unknown")
                lang = file_info.get("language", "unknown")
                size = file_info.get("size", 0)
                lines = file_info.get("lines", 0)

                file_name = path.split("/")[-1]
                st.text(f"📄 {file_name} | {lang} | {format_file_size(size)} | {lines:,} lines")

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
        key=f"copy-{key}"
    )


def main():
    # Header
    st.markdown('<h1 class="main-header">🧠 Codebase Genius</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Repository Documentation Generator</p>', unsafe_allow_html=True)

    # Main input section: move URL input and Generate button to main body
    repo_url = st.text_input(
        "Repository URL",
        placeholder="https://github.com/username/repo",
        help="Enter a GitHub repository URL",
        key="repo_url_main",
    )
    generate_button = st.button("🚀 Generate Documentation", type="primary")


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


        # Analysis depth
        depth = st.selectbox(
            "Analysis Depth",
            options=["deep", "standard"],
            index=0,
            help="Deep mode clones and analyzes the full repository"
        )

        # LLM settings
        st.subheader("🤖 AI Settings")
        use_llm = st.checkbox("Enable AI Documentation", value=True, help="Use LLM to generate comprehensive documentation")
        include_diagrams = st.checkbox("Include Diagrams", key="include_diagrams", help="Generate Mermaid diagrams (call graph, class hierarchy, module graph)")
        diagram_filter_tests = st.checkbox("Filter test modules/classes/functions in diagrams", key="diagram_filter_tests")
        col1, col2, col3 = st.columns(3)
        with col1:
            diagram_max_edges_call = st.number_input("Max Edges: Call Graph", min_value=50, max_value=2000, step=50, key="diagram_max_edges_call")
        with col2:
            diagram_max_edges_class = st.number_input("Max Edges: Class Hierarchy", min_value=50, max_value=2000, step=50, key="diagram_max_edges_class")
        with col3:
            diagram_max_edges_module = st.number_input("Max Edges: Module Graph", min_value=50, max_value=2000, step=50, key="diagram_max_edges_module")

        top_n = st.slider("Top N Items", min_value=3, max_value=20, value=10, help="Number of top items to track")

        # Filtering options
        st.subheader("🔍 Filters")

        with st.expander("Include Paths"):
            include_paths_text = st.text_area(
                "Path prefixes (one per line)",
                placeholder="src/\nlib/\napp/",
                help="Only scan files in these directories"
            )
            include_paths = [p.strip() for p in include_paths_text.split("\n") if p.strip()]

        with st.expander("Include Extensions"):
            use_default_exts = st.checkbox("Use default extensions", value=True)
            if not use_default_exts:
                include_exts_text = st.text_area(
                    "File extensions (one per line)",
                    placeholder=".py\n.js\n.ts",
                    help="Only include files with these extensions"
                )
                include_exts = [e.strip() for e in include_exts_text.split("\n") if e.strip()]
            else:
                include_exts = []

        with st.expander("Exclude Directories"):
            exclude_dirs_text = st.text_area(
                "Directory names (one per line)",
                placeholder="build/\ndist/\n.cache/",
                help="Skip these directories"
            )
            exclude_dirs = [d.strip() for d in exclude_dirs_text.split("\n") if d.strip()]

        # Performance limits
        st.subheader("⚡ Performance")
        max_files = st.number_input("Max Files", min_value=0, value=0, help="0 = unlimited")
        max_file_size_mb = st.number_input("Max File Size (MB)", min_value=0, value=0, help="0 = unlimited")
        max_file_size_bytes = max_file_size_mb * 1024 * 1024 if max_file_size_mb > 0 else 0

    # Main content area
    if generate_button:
        if not repo_url:
            st.error("Please enter a repository URL")
            return

        # Build configuration
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
            "diagram_max_edges_module": diagram_max_edges_module
        }

        # Show configuration
        with st.expander("📋 Request Configuration"):
            st.json(config)

        # Call API
        with st.spinner("🔄 Analyzing repository... This may take a few minutes for large repos."):
            result = call_generate_docs(config)


        # Display results
        if result.get("status") == "error":
            st.markdown(f'<div class="error-box">❌ <strong>Error:</strong> {result.get("message", "Unknown error")}</div>', unsafe_allow_html=True)
        elif result.get("status") == "success":
            st.markdown('<div class="success-box">✅ <strong>Success!</strong> Documentation generated successfully.</div>', unsafe_allow_html=True)

            # Create tabs for different views (added 📈 Diagrams)
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["📖 Documentation", "📊 Statistics", "📈 Diagrams", "🌲 File Tree", "🔧 Raw Data"])

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
                    render_file_tree(result["file_tree"])
                else:
                    st.info("No file tree available.")

            with tab5:
                st.subheader("Raw API Response")
                st.json(result)
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

        ### Example Repositories to Try

        - `https://github.com/karpathy/micrograd` - Small educational ML library
        - `https://github.com/pallets/flask` - Popular Python web framework


        - `https://github.com/fastapi/fastapi` - Modern Python API framework
        """)

if __name__ == "__main__":
    main()
