---
type: "agent_requested"
description: "Example description"
---

# Codebase Genius: Frontend Development Prompt (Streamlit)

You are an expert AI assistant specializing in building interactive web applications using Streamlit. Your task is to help develop the **frontend UI** for **Codebase Genius**, an AI-powered system that automatically generates high-quality documentation for software repositories.

## Project Overview

Build an interactive Streamlit interface that:
- Provides user-friendly input for GitHub repository URLs
- Communicates with the Jac backend via HTTP API
- Displays real-time progress during documentation generation
- Visualizes repository structure and code relationships
- Presents generated documentation in an organized, readable format
- Allows users to download documentation and diagrams
- Manages session history for quick access to previous analyses

## Frontend UI Structure

### Main Interface Features

1. **Input Section**:
   - Text input field for GitHub repository URL
   - Validation indicator (✓ valid URL / ✗ invalid)
   - "Generate Documentation" button
   - Optional settings (e.g., language preference, analysis depth)

2. **Progress Tracking**:
   - Real-time progress indicators showing:
     - Repository cloning status
     - File-tree mapping progress
     - Code analysis stage (with file count)
     - Documentation generation status
   - Progress bars for each major stage
   - Status messages and logs in an expandable section

3. **Results Display**:
   - Tabs or sections for:
     - **Generated Documentation**: Rendered markdown preview
     - **Repository Structure**: Interactive file tree view
     - **Code Context Graph**: Visual diagram (using Plotly, Graphviz, or similar)
     - **Statistics**: Metrics (file count, function count, class count, etc.)
   - Download buttons for:
     - Complete markdown documentation
     - Diagrams (PNG/SVG format)
     - JSON export of CCG

4. **History/Session Management**:
   - Sidebar showing previously analyzed repositories
   - Session persistence (using Streamlit session state)
   - Quick re-generate or view cached results
   - Clear history option

5. **Interactive Features**:
   - Search within generated documentation
   - Filter file tree by file type or directory
   - Zoom/pan controls for diagrams
   - Click on nodes in CCG to see code snippets
   - Collapsible sections for long documentation

## Streamlit-Backend Communication

Implement communication between Streamlit frontend and Jac backend:

```python
# Example Streamlit code structure
import streamlit as st
import requests
import json

# Configure Jac backend endpoint
JAC_BACKEND_URL = "http://localhost:8000"

def call_jac_walker(walker_name, data):
    """Send request to Jac server walker endpoint"""
    response = requests.post(
        f"{JAC_BACKEND_URL}/walker/{walker_name}",
        json=data
    )
    return response.json()

# Streamlit UI components
st.title("🧠 Codebase Genius")
st.subheader("AI-Powered Code Documentation Generator")

repo_url = st.text_input("Enter GitHub Repository URL:")

if st.button("Generate Documentation"):
    with st.spinner("Analyzing repository..."):
        # Call Jac backend walker
        result = call_jac_walker("generate_docs", {"repo_url": repo_url})
        
        # Display results
        if result["status"] == "success":
            st.success("Documentation generated successfully!")
            st.markdown(result["documentation"])
        else:
            st.error(f"Error: {result['message']}")
```

## UI Layout Recommendations

```python
# Recommended Streamlit layout structure

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    analysis_depth = st.selectbox("Analysis Depth", ["Quick", "Standard", "Deep"])
    include_diagrams = st.checkbox("Include Diagrams", value=True)
    language_filter = st.multiselect("Languages", ["Python", "Jac", "JavaScript", "All"])
    
    st.divider()
    
    st.header("📋 Recent Analyses")
    # Display history from session state
    if "history" in st.session_state:
        for repo in st.session_state.history[-5:]:
            if st.button(repo["name"], key=repo["id"]):
                # Load cached results
                load_cached_results(repo["id"])

# Main content area
tab1, tab2, tab3, tab4 = st.tabs([
    "📄 Documentation", 
    "🗂️ Repository Structure", 
    "🕸️ Code Graph", 
    "📊 Statistics"
])

with tab1:
    # Display generated markdown
    st.markdown(documentation_content)
    st.download_button("Download Documentation", data=doc_content, file_name="docs.md")

with tab2:
    # Interactive file tree
    display_file_tree(repo_structure)

with tab3:
    # Interactive code context graph
    display_ccg_diagram(ccg_data)

with tab4:
    # Show metrics and statistics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Files", file_count)
    col2.metric("Functions", function_count)
    col3.metric("Classes", class_count)
```

## Streamlit Features to Utilize

1. **Progress Indicators**:
   ```python
   progress_bar = st.progress(0)
   status_text = st.empty()
   
   for i, step in enumerate(analysis_steps):
       status_text.text(f"Processing: {step}")
       progress_bar.progress((i + 1) / len(analysis_steps))
   ```

2. **Real-time Updates**:
   ```python
   # Use st.empty() for dynamic updates
   status_placeholder = st.empty()
   
   # Update as backend processes
   status_placeholder.info("Cloning repository...")
   # ... later ...
   status_placeholder.success("Analysis complete!")
   ```

3. **Interactive Visualizations**:
   ```python
   import plotly.graph_objects as go
   
   # Create interactive code graph
   fig = go.Figure(data=[go.Scatter(...)])
   st.plotly_chart(fig, use_container_width=True)
   ```

4. **Expanders for Details**:
   ```python
   with st.expander("View Analysis Logs"):
       st.code(analysis_logs)
   
   with st.expander("Advanced Settings"):
       max_depth = st.slider("Max Directory Depth", 1, 10, 5)
   ```

## Frontend Directory Structure

```
frontend/                       # Streamlit UI
├── app.py                     # Main Streamlit application
├── components/                # UI components
│   ├── file_tree.py
│   ├── graph_viewer.py
│   └── doc_viewer.py
├── utils/                     # Frontend utilities
│   └── api_client.py
└── requirements.txt
```

## Technical Requirements

### Language & Framework
- **Frontend**: Streamlit (Python)
- **Communication**: HTTP REST API calls to Jac backend

### Key Features to Implement

- ✅ URL input and validation
- ✅ Real-time progress tracking
- ✅ Markdown preview with syntax highlighting
- ✅ Interactive file tree visualization
- ✅ Code Context Graph visualization (interactive diagram)
- ✅ Statistics dashboard
- ✅ Download functionality (markdown, diagrams, JSON)
- ✅ Session history management
- ✅ Search and filter capabilities
- ✅ Responsive design for different screen sizes
- ✅ Error handling and user feedback

### Backend API Endpoints to Call

Your frontend should communicate with these backend endpoints:

1. **POST /walker/generate_docs**
   - Purpose: Trigger complete documentation generation
   - Input: `{"repo_url": "..."}`
   - Expected response: Documentation data and status

2. **POST /walker/validate_repo**
   - Purpose: Validate repository URL before processing
   - Input: `{"repo_url": "..."}`
   - Expected response: `{"valid": true/false, "message": "..."}`

3. **POST /walker/get_file_tree**
   - Purpose: Retrieve repository structure
   - Input: `{"repo_url": "..."}`
   - Expected response: JSON tree structure

4. **POST /walker/get_ccg**
   - Purpose: Get Code Context Graph data
   - Input: `{"repo_url": "..."}`
   - Expected response: Graph nodes and edges

5. **POST /walker/get_statistics**
   - Purpose: Fetch repository statistics
   - Input: `{"repo_url": "..."}`
   - Expected response: Metrics (file count, function count, etc.)

### Implementation Guidelines

1. **Streamlit Best Practices**:
   - Use `st.session_state` for maintaining state across interactions
   - Implement caching with `@st.cache_data` for expensive operations
   - Use `st.empty()` for dynamic updates during processing
   - Organize UI with tabs, columns, and expanders
   - Add loading spinners and progress bars for better UX

2. **Backend Communication**:
   - Create a dedicated `api_client.py` module for all backend calls
   - Handle HTTP errors and timeouts gracefully
   - Display user-friendly error messages
   - Implement retry logic for failed requests
   - Add request timeout handling

3. **State Management**:
   - Store analysis history in `st.session_state`
   - Cache expensive visualizations
   - Persist user preferences (settings)
   - Handle session cleanup appropriately

4. **Error Handling**:
   - Validate user inputs before sending to backend
   - Display clear error messages from backend
   - Provide helpful suggestions for common errors
   - Log errors for debugging (use st.expander for logs)

5. **Code Organization**:
   - Modular UI components in separate files
   - Reusable functions for common operations
   - Clear separation of concerns (UI vs logic)
   - Comment code thoroughly

6. **UI/UX Considerations**:
   - Responsive layout for different screen sizes
   - Intuitive navigation and clear labels
   - Consistent color scheme and styling
   - Loading indicators for all async operations
   - Helpful tooltips and documentation

## Learning Resources Reference

Before implementation, study:
- **Streamlit Documentation**: UI components and best practices
- **Streamlit API Reference**: Available widgets and functions

## Frontend Setup and Run

```bash
# Open terminal, navigate to frontend directory
cd codebase_genius/frontend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run app.py
```

### Access the Frontend
- Frontend UI: `http://localhost:8501`

## Required Dependencies (requirements.txt)

```txt
streamlit>=1.28.0
requests>=2.31.0
plotly>=5.17.0
pandas>=2.1.0
graphviz>=0.20.1
pillow>=10.0.0
```

## Deliverables

1. **Frontend Source Code**: Streamlit application with all UI components
2. **Setup Instructions**: 
   - Virtual environment setup
   - Dependencies installation (requirements.txt)
   - Configuration (backend URL)
3. **Component Documentation**: Explain each UI component's purpose
4. **Screenshots/Video**: Demonstration of UI functionality
5. **README**: Comprehensive setup and usage guide for frontend

## Evaluation Criteria Focus

- **UI/UX Quality**: Intuitive interface, responsive design, good user experience
- **Code Quality**: Clean structure, modular components, readability
- **Integration**: Seamless communication with Jac backend
- **Error Handling**: Graceful handling of errors with user-friendly messages
- **Reproducibility**: Clear setup instructions
- **Creativity**: Innovative UI features, advanced visualizations

## Development Approach

1. **Study Reference**: Start by understanding the byLLM Task Manager Streamlit frontend
2. **Basic Layout**: Create main app structure with input and output sections
3. **Backend Integration**: Implement API client for backend communication
4. **Progress Tracking**: Add real-time progress indicators
5. **Visualizations**: Implement file tree and code graph viewers
6. **Polish**: Refine UX, add error handling, improve performance
7. **Testing**: Test with various repositories and edge cases

## Running the Complete System

1. Start the Jac backend server (see backend instructions)
2. Start the Streamlit frontend (see setup instructions above)
3. Access UI at `http://localhost:8501`
4. Backend API available at `http://localhost:8000`

## When Helping with This Project

- Provide complete, working Streamlit code examples
- Suggest appropriate Streamlit components for specific UI needs
- Help with state management in Streamlit
- Assist with visualization libraries (Plotly, Graphviz, etc.)
- Guide on API client implementation and error handling
- Recommend best practices for responsive design
- Help debug Streamlit-specific issues
- Suggest UX improvements and interactive features

---

**Remember**: This frontend should provide an excellent user experience with intuitive navigation, real-time feedback, and beautiful visualizations. Focus on creating a polished, professional interface that makes complex code analysis accessible to all users.