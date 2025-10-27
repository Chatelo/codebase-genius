# Codebase Genius - Frontend

Streamlit-based web UI for the Codebase Genius documentation generator.

## Features

- 🎨 **Beautiful UI**: Clean, modern interface with gradient headers and responsive layout
- ⚙️ **Full Configuration**: Access all backend features through an intuitive sidebar
- 📊 **Rich Visualizations**: Interactive charts for statistics and file trees
- 📥 **Export**: Download generated documentation as Markdown
- 🔄 **Real-time Feedback**: Progress indicators and error handling
- 📱 **Responsive**: Works on desktop and mobile devices

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
uv sync
```

Or with pip:

```bash
pip install -r requirements.txt
```

### 2. Configure Backend URL

Edit `.streamlit/secrets.toml` to point to your backend:

```toml
BACKEND_URL = "http://localhost:8000"
```

### 3. Run the App

```bash
uv run streamlit run app.py
```

Or:

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### Basic Workflow

1. **Enter Repository URL**: Paste a GitHub repository URL in the sidebar
2. **Configure Settings**:
   - Choose analysis depth (deep/standard)
   - Enable/disable AI documentation
   - Set filtering options
3. **Generate**: Click "Generate Documentation"
4. **View Results**: Browse through tabs:
   - 📖 Documentation: AI-generated markdown docs
   - 📊 Statistics: File counts, languages, top directories
   - 🌲 File Tree: Organized file structure
   - 🔧 Raw Data: Full API response

### Configuration Options

#### AI Settings
- **Enable AI Documentation**: Use LLM to generate comprehensive docs
- **Include Diagrams**: Generate architecture diagrams (future feature)
- **Top N Items**: Number of top files/directories to track (3-20)

#### Filters
- **Include Paths**: Only scan specific directories (e.g., `src/`, `lib/`)
- **Include Extensions**: Only include specific file types (e.g., `.py`, `.js`)
- **Exclude Directories**: Skip directories (e.g., `build/`, `dist/`)

#### Performance
- **Max Files**: Limit total files scanned (0 = unlimited)
- **Max File Size**: Skip files larger than N MB (0 = unlimited)

### Example Repositories

Try these repositories to see Codebase Genius in action:

- **Small**: `https://github.com/karpathy/micrograd` (~4 files, educational ML library)
- **Medium**: `https://github.com/pallets/flask` (~100 files, web framework)
- **Large**: `https://github.com/fastapi/fastapi` (~200 files, API framework)

## UI Components

### Header
- Gradient title with emoji
- Subtitle describing the tool

### Sidebar
- Repository URL input
- Analysis depth selector
- AI settings toggles
- Expandable filter sections
- Performance controls
- Generate button

### Main Area
- Welcome screen with features and examples
- Results tabs:
  - **Documentation**: Rendered markdown with download button
  - **Statistics**: Metrics cards, language breakdown, top directories chart, top files list
  - **File Tree**: Expandable directory structure with file metadata
  - **Raw Data**: JSON view of full API response

### Styling
- Custom CSS for gradient headers
- Color-coded stat cards
- Success/error message boxes
- Responsive grid layouts

## Development

### Project Structure

```
frontend/
├── .streamlit/
│   ├── config.toml      # Streamlit theme and server config
│   └── secrets.toml     # Backend URL configuration
├── app.py               # Main Streamlit application
├── requirements.txt     # Python dependencies
├── pyproject.toml       # UV project configuration
└── README.md           # This file
```

### Key Functions

- `call_generate_docs(config)`: Makes API request to backend
- `format_file_size(size_bytes)`: Formats bytes to human-readable size
- `render_stats(stats)`: Displays statistics with metrics and charts
- `render_file_tree(file_tree)`: Shows expandable file tree
- `main()`: Main app entry point

### Customization

#### Change Theme Colors

Edit `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#667eea"  # Purple gradient
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f8f9fa"
textColor = "#262730"
```

#### Change Backend URL

Edit `.streamlit/secrets.toml`:

```toml
BACKEND_URL = "http://your-backend-host:port"
```

#### Modify Timeout

In `app.py`, adjust the timeout in `call_generate_docs()`:

```python
response = requests.post(
    f"{BACKEND_URL}/walker/generate_docs",
    json=config,
    timeout=300  # 5 minutes (adjust as needed)
)
```

## Troubleshooting

### "Could not connect to backend"

- Make sure the backend server is running: `cd backend && uv run jac serve main.jac --port 8000`
- Check that `BACKEND_URL` in `.streamlit/secrets.toml` matches your backend host/port
- Verify no firewall is blocking the connection

### "Request timed out"

- The repository might be too large
- Try using filters to reduce scope (include_paths, max_files)
- Increase timeout in `call_generate_docs()` function

### Missing Dependencies

```bash
cd frontend
uv sync
```

Or:

```bash
pip install -r requirements.txt
```

## Dependencies

- **streamlit** (1.39.0): Web UI framework
- **requests** (2.32.3): HTTP client for API calls

## License

Part of the Codebase Genius project.
