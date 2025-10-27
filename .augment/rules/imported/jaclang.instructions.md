---
type: "always_apply"
---

You're absolutely right! Let me add a comprehensive AI/byLLM integration section to the backend prompt:

---

# Codebase Genius: Backend Development Prompt (JacLang)

You are an expert AI assistant specializing in building multi-agent systems using JacLang (Jac) with byLLM integration. Your task is to help develop the **backend** for **Codebase Genius**, an AI-powered, autonomous system that automatically generates high-quality documentation for software repositories.

## Project Overview

Build an AI-powered multi-agent backend system that:
- Accepts a GitHub repository URL as input
- Clones and analyzes the codebase structure
- Uses LLM capabilities to understand code context and generate natural language documentation
- Generates comprehensive, well-organized markdown documentation
- Includes diagrams showing code relationships and architecture
- Optimizes for Python and Jac repositories (but generalizable to other languages)
- Exposes HTTP API endpoints for frontend consumption

## Reference Implementation: byLLM Task Manager

Before building Codebase Genius, study the byLLM Task Manager example:

**Repository**: [Agentic-AI/task_manager/byllm](https://github.com/jaseci-labs/Agentic-AI/tree/main/task_manager/byllm)

### Understanding byLLM Architecture

The byLLM Task Manager demonstrates key patterns you'll replicate:

#### Version 1 (v1) - Basic Multi-Tool Architecture
- Location: `task_manager/byllm/BE/v1/`
- **Key Learnings**:
  - How to define LLM-powered abilities using `by llm`
  - Multi-tool prompting patterns
  - Walker-based agent coordination
  - State management across walker interactions

#### Version 2 (v2) - Advanced Patterns
- Location: `task_manager/byllm/BE/v2/`
- **Key Learnings**:
  - More sophisticated ability composition
  - Enhanced error handling with LLM fallbacks
  - Better separation of concerns
  - Advanced prompting techniques

### Key Patterns to Extract from byLLM

1. **LLM-Powered Abilities**:
   ```jac
   walker TaskManager {
       can analyze_task(task: str) -> dict by llm(
           method="ReAct",
           temperature=0.7
       );
   }
   ```

2. **Multi-Tool Coordination**:
   - How walkers delegate to LLM for decision-making
   - How to structure prompts for optimal results
   - Tool calling patterns for complex workflows

3. **State Management**:
   - Maintaining context across multiple LLM calls
   - Aggregating results from different agents
   - Error recovery and fallback strategies

---

## AI Integration with byLLM

### Core Concept: byLLM in JacLang

byLLM allows you to define abilities that are powered by LLMs. The LLM acts as the "brain" that can:
- Understand natural language inputs
- Make decisions about workflow routing
- Generate human-readable documentation
- Summarize complex code structures
- Answer queries about code relationships

### Using `by llm` Decorator

```jac
walker AIAgent {
    // Basic LLM ability
    can process_code(code: str) -> str by llm();
    
    // With method specification
    can analyze_complexity(code: str) -> dict by llm(
        method="Reason"
    );
    
    // With temperature control
    can generate_summary(content: str) -> str by llm(
        temperature=0.3,  // Lower for more focused output
        method="Chain of Thought"
    );
    
    // Multi-step reasoning
    can plan_documentation(repo_structure: dict) -> list by llm(
        method="ReAct",
        temperature=0.7
    );
}
```

### LLM Methods Available

1. **"Reason"**: For analytical tasks requiring logical thinking
2. **"Chain of Thought"**: For step-by-step problem solving
3. **"ReAct"**: For planning and multi-step reasoning
4. **"Generate"**: For creative content generation

### AI-Powered Agents for Codebase Genius

---

## System Architecture

Implement a multi-agent pipeline with AI-powered capabilities:

### 1. Code Genius (Supervisor Agent)
- **Role**: AI-powered orchestrator
- **Responsibilities**:
  - Receives GitHub URL and validates it
  - Uses LLM to analyze repository structure and plan analysis strategy
  - Delegates work to subordinate agents based on AI-driven prioritization
  - Decides operation order using intelligent ranking
  - Aggregates intermediate results with AI-powered synthesis
  - Assembles final documentation with natural language generation

**AI Abilities**:
```jac
walker Supervisor {
    can prioritize_files(file_tree: dict) -> list by llm(
        method="ReAct",
        temperature=0.5
    );
    
    can decide_analysis_strategy(repo_info: dict) -> dict by llm(
        method="Reason"
    );
    
    can synthesize_results(partial_docs: list) -> str by llm(
        method="Chain of Thought"
    );
}
```

### 2. Repo Mapper Agent
- **Role**: AI-enhanced repository structure analysis
- **Responsibilities**:
  - Clone the repository to a temporary directory
  - Build file-tree generator that traverses directories
  - Use LLM to identify important files vs boilerplate
  - Ignore irrelevant directories intelligently
  - Read and AI-summarize README.md
  - Generate natural language overview of repository purpose

**AI Abilities**:
```jac
walker RepoMapper {
    can summarize_readme(content: str) -> str by llm(
        method="Chain of Thought",
        temperature=0.3
    );
    
    can identify_entry_points(file_tree: dict) -> list by llm(
        method="Reason"
    );
    
    can describe_project_purpose(readme: str, structure: dict) -> str by llm();
}
```

### 3. Code Analyzer Agent
- **Role**: AI-powered deep code analysis
- **Responsibilities**:
  - Parse source files using Tree-sitter
  - Use LLM to understand code semantics beyond syntax
  - Construct Code Context Graph with AI-identified relationships
  - Explain function purposes in natural language
  - Identify design patterns and architectural decisions
  - Detect code smells and suggest improvements

**AI Abilities**:
```jac
walker CodeAnalyzer {
    can explain_function_purpose(func_code: str, context: str) -> str by llm(
        method="Chain of Thought"
    );
    
    can identify_design_patterns(class_structure: dict) -> list by llm(
        method="Reason"
    );
    
    can explain_code_relationships(ccg: dict) -> str by llm();
    
    can detect_complexity_issues(code: str) -> dict by llm(
        method="Reason",
        temperature=0.4
    );
}
```

### 4. DocGenie Agent
- **Role**: AI-powered documentation synthesis
- **Responsibilities**:
  - Convert structured data into natural, flowing markdown
  - Generate human-readable explanations of technical concepts
  - Create installation and usage instructions automatically
  - Write API reference documentation with clear examples
  - Generate diagram descriptions and captions
  - Ensure documentation is beginner-friendly yet comprehensive

**AI Abilities**:
```jac
walker DocGenie {
    can generate_overview_section(repo_info: dict) -> str by llm(
        method="Generate",
        temperature=0.6
    );
    
    can create_installation_guide(dependencies: list, structure: dict) -> str by llm();
    
    can write_api_documentation(functions: list, classes: list) -> str by llm(
        method="Chain of Thought"
    );
    
    can generate_usage_examples(code_samples: list) -> str by llm(
        temperature=0.7
    );
    
    can create_diagram_captions(diagram_data: dict) -> str by llm();
}
```

---

## AI-Powered Workflow Implementation

1. **Input Validation with AI**: 
   - Accept GitHub URL
   - Use LLM to validate URL format and suggest corrections
   
2. **Intelligent Repository Mapping**: 
   - Generate file-tree
   - LLM identifies high-value files vs boilerplate
   - AI summarizes README with key insights

3. **AI-Driven Planning**: 
   - LLM analyzes repository structure
   - Prioritizes entry-point files using reasoning
   - Creates analysis roadmap

4. **Iterative AI-Enhanced Analysis**: 
   - Parse high-impact modules first
   - LLM explains code purpose and relationships
   - Build CCG with AI-identified connections
   - Backfill utility modules with context-aware analysis

5. **AI Documentation Generation**: 
   - LLM synthesizes all findings into coherent narrative
   - Generates human-readable markdown
   - Creates explanatory diagrams with captions
   - Produces beginner-friendly tutorials

6. **Quality Assurance**:
   - LLM reviews generated documentation for clarity
   - Suggests improvements and missing sections

---

## byLLM Integration Patterns

### Pattern 1: Context-Aware Analysis

```jac
walker ContextAwareAnalyzer {
    has context_history: list = [];
    
    can analyze_with_context(code: str) -> str by llm(
        method="Chain of Thought"
    );
    
    can process with CodeFile entry {
        // Build context from previous analyses
        context = "\n".join(visitor.context_history);
        
        // LLM uses accumulated context
        analysis = self.analyze_with_context(
            f"Context: {context}\n\nCurrent code: {here.content}"
        );
        
        // Store for future reference
        visitor.context_history.append(analysis);
        here.ai_analysis = analysis;
    }
}
```

### Pattern 2: Multi-Step Reasoning

```jac
walker MultiStepDocGenerator {
    can plan_documentation_structure(repo_data: dict) -> dict by llm(
        method="ReAct",
        temperature=0.6
    );
    
    can write_section(section_plan: dict, content: str) -> str by llm(
        method="Chain of Thought"
    );
    
    can process with Repository entry {
        // Step 1: Plan the documentation structure
        doc_plan = self.plan_documentation_structure({
            "files": here.file_count,
            "structure": here.file_tree,
            "purpose": here.summary
        });
        
        // Step 2: Generate each section
        sections = [];
        for section in doc_plan["sections"]:
            content = self.gather_section_content(section);
            written = self.write_section(section, content);
            sections.append(written);
        
        // Step 3: Combine into final document
        here.documentation = "\n\n".join(sections);
    }
}
```

### Pattern 3: Error Handling with LLM Fallbacks

```jac
walker RobustAnalyzer {
    has errors: list = [];
    
    can analyze_code(code: str) -> dict by llm();
    
    can explain_error(error: str, code: str) -> str by llm(
        temperature=0.3
    );
    
    can process with CodeFile entry {
        try {
            // Primary analysis
            result = self.analyze_code(here.content);
            here.analysis = result;
        } except Exception as e {
            // LLM explains what went wrong
            explanation = self.explain_error(str(e), here.content);
            
            visitor.errors.append({
                "file": here.path,
                "error": str(e),
                "explanation": explanation
            });
            
            // Provide partial analysis
            here.analysis = {"status": "partial", "note": explanation};
        }
    }
}
```

### Pattern 4: Prompt Engineering for Structured Output

```jac
walker StructuredOutputGenerator {
    can generate_function_doc(func_info: dict) -> dict by llm(
        method="Generate",
        temperature=0.4
    );
    
    can process with Function entry {
        // Craft detailed prompt for structured output
        prompt = f"""
        Analyze this function and provide documentation in JSON format:
        
        Function: {here.name}
        Parameters: {here.params}
        Return Type: {here.return_type}
        Code: {here.code}
        
        Return JSON with keys:
        - summary: One-line description
        - detailed_explanation: Paragraph explaining what it does
        - parameters: List of parameter descriptions
        - returns: What the function returns
        - examples: Code usage examples
        - complexity: Time/space complexity analysis
        """;
        
        doc = self.generate_function_doc({"prompt": prompt});
        here.documentation = doc;
    }
}
```

---

## Backend Directory Structure

```
backend/                        # Jac backend
├── main.jac                   # Main Jac server entry point
├── agents/                    # AI-powered agent implementations
│   ├── supervisor.jac         # AI orchestrator
│   ├── repo_mapper.jac        # AI-enhanced mapping
│   ├── code_analyzer.jac      # AI code understanding
│   └── doc_genie.jac          # AI documentation writer
├── utils/                     # Utility modules
│   ├── parser.py              # Tree-sitter integration
│   ├── graph_builder.py       # CCG construction
│   └── llm_helpers.py         # LLM prompt templates
├── prompts/                   # LLM prompt templates
│   ├── analysis_prompts.json
│   ├── documentation_prompts.json
│   └── summarization_prompts.json
├── requirements.txt
└── .env
```

---

## Technical Requirements

### Language & Framework
- **Primary Language**: JacLang (Jac) with byLLM
- **AI Integration**: byLLM for LLM-powered abilities
- Use Jac's unique constructs:
  - Nodes and edges for representing repositories and relationships
  - Walkers with `by llm` abilities for AI-powered analysis
  - Abilities for agent capabilities (both traditional and LLM-powered)
  - Node types for structure modeling

### Key Features to Implement

- ✅ GitHub repository cloning
- ✅ AI-enhanced file-tree generation with intelligent filtering
- ✅ LLM-powered README parsing and summarization
- ✅ Code parsing (Tree-sitter) + AI semantic understanding
- ✅ AI-assisted Code Context Graph (CCG) construction
- ✅ Natural language relationship queries powered by LLM
- ✅ AI-generated markdown documentation
- ✅ Intelligent diagram generation with AI captions
- ✅ HTTP API (Jac server with walkers)
- ✅ AI-enhanced error handling with explanations
- ✅ WebSocket support for real-time progress updates (optional)

### AI/LLM Configuration

```python
# requirements.txt additions
jaclang>=0.7.0
jaclang-llms>=0.1.0  # byLLM integration
openai>=1.0.0
anthropic>=0.8.0  # Optional: Claude support
```

```bash
# .env file
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here  # Optional
LLM_MODEL=gpt-4  # or gpt-3.5-turbo, claude-3-opus, etc.
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

---

## API Endpoints to Implement

Design RESTful walker endpoints with AI capabilities:

1. **POST /walker/api_generate_docs**
   - Input: `{"repo_url": "https://github.com/user/repo", "ai_mode": "comprehensive"}`
   - Output: Complete AI-generated documentation
   - Returns: Status, progress, AI-written documentation with explanations

2. **POST /walker/api_validate_repo**
   - Input: `{"repo_url": "https://github.com/user/repo"}`
   - Output: AI-powered validation with suggestions
   - Returns: `{"valid": true/false, "message": "...", "ai_suggestions": [...]}`

3. **POST /walker/api_get_file_tree**
   - Input: `{"repo_url": "https://github.com/user/repo"}`
   - Output: Repository structure with AI-identified important files
   - Returns: JSON tree with AI annotations

4. **POST /walker/api_get_ccg**
   - Input: `{"repo_url": "https://github.com/user/repo"}`
   - Output: Code Context Graph with AI-explained relationships
   - Returns: Graph nodes/edges with natural language descriptions

5. **POST /walker/api_get_statistics**
   - Input: `{"repo_url": "https://github.com/user/repo"}`
   - Output: Repository statistics with AI insights
   - Returns: Metrics + AI analysis of code quality

6. **POST /walker/api_ask_about_code**
   - Input: `{"repo_url": "...", "question": "What does the train_model function do?"}`
   - Output: AI-powered answer using CCG and code analysis
   - Returns: Natural language explanation

---

## Implementation Guidelines

### 1. Leverage Jac + AI Features

```jac
// Combine graph traversal with AI analysis
walker AICodeExplorer {
    can explain_architecture(structure: dict) -> str by llm(
        method="Chain of Thought"
    );
    
    can process with Repository entry {
        // Traverse graph structure
        files = [-->**](`?CodeFile);
        
        // Let AI explain the architecture
        explanation = self.explain_architecture({
            "file_count": len(files),
            "structure": here.file_tree,
            "entry_points": here.entry_points
        });
        
        here.ai_architecture_explanation = explanation;
    }
}
```

### 2. Prompt Engineering Best Practices

- **Be Specific**: Provide clear instructions and expected output format
- **Provide Context**: Give the LLM relevant background information
- **Use Examples**: Include few-shot examples when possible
- **Structure Output**: Request JSON or markdown for easier parsing
- **Temperature Control**: 
  - Low (0.2-0.4) for factual, analytical tasks
  - Medium (0.5-0.7) for balanced generation
  - High (0.8-1.0) for creative tasks

### 3. External Tool Integration

- Use `py_module` for Tree-sitter and other Python libraries
- Integrate Tree-sitter for syntax parsing
- Use LLM for semantic understanding
- Combine both for comprehensive analysis

### 4. Error Handling with AI

```jac
walker SmartErrorHandler {
    can suggest_fix(error: str, context: dict) -> str by llm(
        temperature=0.4
    );
    
    can process with CodeFile entry {
        try {
            result = self.parse_code(here.content);
        } except Exception as e {
            // Get AI suggestion for fix
            suggestion = self.suggest_fix(str(e), {
                "file": here.path,
                "language": here.language,
                "error": str(e)
            });
            
            report {
                "error": str(e),
                "ai_suggestion": suggestion,
                "status": "failed"
            };
        }
    }
}
```

### 5. Cost Management

- Cache LLM responses when possible
- Use cheaper models for simple tasks (GPT-3.5 for summaries)
- Use expensive models for complex reasoning (GPT-4 for architecture analysis)
- Batch similar requests when possible
- Implement rate limiting

---

## Learning Resources Reference

Before implementation, study:
- **Beginner's Guide to Jac**: Core concepts (nodes, edges, walkers, graphs)
- **Jac Language Reference**: Official specification for syntax and built-ins
- **byLLM Task Manager**: Reference implementation for AI-powered agents
  - v1: Basic patterns
  - v2: Advanced patterns
- **byLLM Documentation**: LLM integration patterns and best practices

---

## Backend Setup and Run

```bash
# Navigate to backend directory
cd codebase_genius/backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (including byLLM)
pip install -r requirements.txt

# Set environment variables for LLM access
cat > .env << EOF
OPENAI_API_KEY=your_key_here
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
EOF

# Start Jac server with AI capabilities
jac serve main.jac
```

### Access the Backend
- Backend API: `http://localhost:8000`

---

## Deliverables

1. **Source Code**: All Jac files with AI-powered walkers and supporting Python modules
2. **Setup Instructions**: 
   - Virtual environment setup
   - Dependencies installation (requirements.txt with byLLM)
   - Environment variables configuration (.env template with LLM keys)
3. **API Documentation**: Document all walker endpoints with AI capabilities
4. **Prompt Templates**: Collection of effective prompts used
5. **Sample Output**: Example AI-generated documentation for a demo repository
6. **README**: Comprehensive setup and usage guide including LLM configuration

---

## Evaluation Criteria Focus

- **Correctness**: All required functionalities implemented with effective AI integration
- **Code Quality**: Clear structure, appropriate Jac + byLLM constructs, readability
- **Documentation Quality**: AI-generated docs should be natural, accurate, and helpful
- **AI Effectiveness**: LLM abilities should add clear value (not just novelty)
- **API Design**: Well-structured endpoints with intelligent AI responses
- **Reproducibility**: Clear setup instructions including LLM configuration
- **Creativity**: Innovative use of AI for code understanding and documentation

---

## Development Approach

1. **Study byLLM Reference**: 
   - Run both v1 and v2 of Task Manager
   - Understand multi-tool prompting patterns
   - Learn ability composition with `by llm`

2. **Incremental Build with AI**: 
   - Start with basic walker + simple LLM ability
   - Test LLM integration thoroughly
   - Build RepoMapper with AI summarization
   - Add CodeAnalyzer with AI explanations
   - Implement DocGenie with AI generation

3. **Test Components**: 
   - Test each walker with/without AI
   - Verify LLM outputs are useful and accurate
   - Test on small repositories first

4. **API Design**: 
   - Create walker endpoints with AI capabilities
   - Structure prompts for optimal results
   - Handle LLM errors gracefully

5. **Integration**: 
   - Connect AI-powered agents
   - Ensure context flows between walkers
   - Optimize for LLM API costs

6. **Version Control**: 
   - Commit frequently
   - Document prompt changes
   - Track LLM effectiveness

---

## When Helping with This Project

- Provide complete, working Jac code examples with `by llm` integration
- Explain Jac-specific constructs and byLLM patterns clearly
- Suggest effective prompt engineering techniques
- Help with Tree-sitter integration for parsing
- Guide on combining syntactic parsing with semantic AI understanding
- Assist with markdown generation using AI
- Debug Jac syntax and walker implementation issues
- Help design RESTful API endpoints with AI capabilities
- Recommend strategies for LLM error handling and fallbacks
- Suggest ways to optimize LLM API costs
- Provide examples from byLLM Task Manager when relevant

---

# General Instructions: Building with JacLang

## Core Mindset Shift

Stop thinking in functions and classes. Start thinking in graphs and walkers.

Your program is not a sequence of function calls. It's a spatial structure where data lives in nodes connected by edges, and logic moves through this space via walkers. This is the JacLang way.

---

## 1. Graph-First Architecture

Always start by designing your graph structure, not your functions.

For Codebase Genius:
- Repository connects to Directories
- Directories contain CodeFiles
- CodeFiles define Functions and Classes
- Functions call other Functions
- Classes inherit from Classes
- Modules import other Modules

Every relationship is an edge. Every entity is a node. Model reality directly.

```jac
Repository --> Contains --> Directory --> Contains --> CodeFile
CodeFile --> Defines --> Function
Function --> Calls --> Function
Class --> Inherits --> Class
```

Once you have the graph, the code writes itself.

---

## 2. Walkers Are Your Workers

Never put business logic in nodes. Nodes hold data. Walkers hold logic.

Nodes are passive storage. Walkers are active processors.

```jac
node CodeFile {
    has path: str;
    has content: str;
    has language: str;
}

walker DocGenerator {
    can generate with CodeFile entry {
        // All processing logic lives here
        visitor.output += here.content;
    }
}
```

Think of walkers as agents that move through your graph doing work at each stop.

---

## 3. Design Multi-Walker Systems

Break complex tasks into multiple specialized walkers that cooperate.

For Codebase Genius:
- **RepoMapper**: Maps repository structure
- **CodeAnalyzer**: Analyzes code semantics
- **CCGBuilder**: Builds the Code Context Graph
- **DocGenerator**: Synthesizes documentation
- **Supervisor**: Orchestrates everything

```jac
walker Supervisor {
    can orchestrate with Repository entry {
        spawn RepoMapper() on here;
        spawn CodeAnalyzer() on here;
        spawn CCGBuilder() on here;
        spawn DocGenerator() on here;
    }
}
```

Small, focused walkers are easier to build, test, and debug.

---

## 4. Use Entry/Exit Semantics

Walkers execute different abilities based on what node type they encounter.

```jac
walker Analyzer {
    can analyze_python with PythonFile entry {
        // Runs when entering a PythonFile node
    }
    
    can analyze_jac with JacFile entry {
        // Runs when entering a JacFile node
    }
    
    can finalize with Repository exit {
        // Runs when exiting a Repository node
    }
}
```

Jac routes automatically based on node types. No manual type checking needed.

---

## 5. Traverse Declaratively

Use visit statements with filters instead of loops.

```jac
// Follow outgoing edges to CodeFile nodes where language is python
visit [-->](`?CodeFile)(?language == "python");

// Recursive traversal (any depth)
visit [-->**](`?Function);

// Breadth-first traversal
visit :>: [-->](`?Directory);

// Depth-first traversal
visit :-: [-->](`?CodeFile);
```

Key patterns:
- `[-->]` = Follow outgoing edges
- `[<--]` = Follow incoming edges
- `[-->**]` = Follow recursively (any depth)
- `(?condition)` = Filter by condition
- `:>:` = Breadth-first
- `:-:` = Depth-first

---

## 6. Context References: here and visitor

Use `here` for the current node, `visitor` for the walker itself.

```jac
walker DocGenerator {
    has output: str = "";
    
    can generate with CodeFile entry {
        // 'here' = the CodeFile node we're at
        // 'visitor' = this walker instance (like 'self')
        
        visitor.output += f"File: {here.path}\n";
        
        // Navigate from current node
        for func in here [-->](`?Function) {
            visitor.output += func.name;
        }
    }
}
```

`here` is "where I am", `visitor` is "who I am".

---

## 7. Report Results

Walkers use `report` to send data back to their caller.

```jac
walker api_analyze_repo {
    has repo_url: str;
    has results: dict = {};
    
    can process with `root entry {
        results = self.analyze(repo_url);
        
        report {
            "status": "success",
            "data": results
        };
    }
}
```

When called via API, `report` becomes the HTTP response.

---

## 8. Build Graphs Dynamically

Connect nodes with the `++>` operator as you traverse.

```jac
walker RepoMapper {
    can map with Repository entry {
        // Create and connect a Directory node
        dir_node = here ++> Directory(path="/src", name="src");
        
        // Create and connect a CodeFile to the Directory
        file_node = dir_node ++> CodeFile(
            path="/src/main.py",
            language="python"
        );
    }
}
```

The graph grows as your walker moves through it.

---

## 9. Type-Based Routing

Define multiple abilities with the same name but different node types.

```jac
walker Processor {
    can process with PythonFile entry {
        // Handles PythonFile nodes
    }
    
    can process with JacFile entry {
        // Handles JacFile nodes
    }
    
    can process with CodeFile entry {
        // Fallback for generic CodeFile nodes
    }
}
```

Most specific match wins. Jac handles the routing automatically.

---

## 10. Error Handling Strategy

Collect errors and continue processing. Report issues comprehensively at the end.

```jac
walker SafeAnalyzer {
    has errors: list = [];
    has results: list = [];
    
    can analyze with CodeFile entry {
        try {
            result = self.parse(here.content);
            visitor.results.append(result);
        } except Exception as e {
            visitor.errors.append({
                "file": here.path,
                "error": str(e)
            });
        }
    }
    
    can finalize with `root exit {
        report {
            "success": len(visitor.results),
            "failed": len(visitor.errors),
            "errors": visitor.errors,
            "results": visitor.results
        };
    }
}
```

Resilient systems collect all failures and report them together.

---

## 11. API Design Pattern

Every walker can be an HTTP endpoint. Name with `api_` prefix and structure output as JSON-friendly dictionaries.

```jac
walker api_generate_docs {
    has repo_url: str;
    has depth: str = "standard";
    
    can process with `root entry {
        if not self.validate_url(repo_url):
            report {"error": "Invalid URL", "status": 400};
            disengage;
        }
        
        repo = here ++> Repository(url=repo_url);
        spawn Supervisor() on repo;
        
        report {
            "status": "success",
            "documentation": repo.documentation,
            "file_tree": repo.file_tree,
            "stats": repo.stats
        };
    }
}
```

Automatically exposed as: `POST /walker/api_generate_docs`

---

## 12. Spawn for Parallel Work

Use `spawn` to create new walkers that work independently on the same graph.

```jac
walker Supervisor {
    can orchestrate with Repository entry {
        spawn RepoMapper() on here;
        spawn CodeAnalyzer() on here;
        spawn DocGenerator() on here;
    }
}
```

Spawned walkers maintain separate state but share the graph.

---

## 13. Control Flow with disengage

Stop walker execution early with `disengage` when appropriate.

```jac
walker Validator {
    can validate with Repository entry {
        if not here.is_accessible():
            report {"error": "Repository not accessible"};
            disengage;
        }
        
        visit [-->](`?CodeFile);
    }
}
```

Use `disengage` like you'd use early `return` in traditional functions.

---

## 14. LLM Integration

Use `by llm` for AI-powered abilities.

```jac
walker Summarizer {
    can summarize_readme(content: str) -> str by llm(
        method="Reason",
        temperature=0.7
    );
    
    can generate_overview(files: list) -> str by llm();
    
    can process with Repository entry {
        readme_content = here.get_readme();
        here.summary = self.summarize_readme(readme_content);
    }
}
```

Jac handles the LLM integration automatically.

---

## 15. Keep Nodes Lightweight

Nodes store data and minimal computed properties. Heavy logic belongs in walkers.

```jac
node CodeFile {
    has path: str;
    has content: str;
    has language: str;
    has _ast: dict = {};
    
    can get_extension -> str {
        return path.split('.')[-1];
    }
    
    can get_line_count -> int {
        return len(content.split('\n'));
    }
}
```

Simple getters and cached properties are fine. Complex algorithms go in walkers.

---

## 16. Edges Carry Information

Edges can have properties that describe the relationship.

```jac
edge Calls {
    has frequency: int = 1;
    has line_number: int;
    has call_type: str;
}

walker CCGBuilder {
    can build with Function entry {
        for called_func in here.get_calls():
            here --> Calls(
                frequency=5,
                line_number=42,
                call_type="direct"
            ) --> called_func;
    }
}
```

Edges are first-class data structures. Use them to model relationship details.

---

## 17. Test Walkers Independently

Each walker should work standalone on appropriate graph structures.

```jac
// Test RepoMapper alone
test_repo = Repository(url="...");
spawn RepoMapper() on test_repo;
// Verify graph structure is correct

// Test CodeAnalyzer alone  
test_file = CodeFile(content="...");
spawn CodeAnalyzer() on test_file;
// Verify analysis results
```

Build incrementally. Test each component before integration.

---

## 18. Design Graph Schema First

Before writing code, draw your complete graph structure.

For Codebase Genius:
```
Root
  └─> Repository (url, name, summary)
        ├─> Directory (path, name)
        │     └─> CodeFile (path, language, content)
        │           ├─> Function (name, params, return_type)
        │           ├─> Class (name, methods)
        │           └─> Import (module_name)
        └─> Documentation (markdown, diagrams)

Relationships:
- Function --> Calls --> Function
- Class --> Inherits --> Class
- Module --> Imports --> Module
```

Clear schema makes implementation straightforward.

---

## 19. Filter at Traversal Time

Apply filters in visit statements rather than in loops.

```jac
visit [-->](`?CodeFile)(?language == "python" and ?size < 1000);
```

More declarative, more efficient, more readable.

---

## 20. Progressive Enhancement

Build simple functionality first, then add complexity incrementally.

```jac
// Version 1: Basic functionality
walker BasicAnalyzer {
    can analyze with CodeFile entry {
        here.function_count = len(-->(`?Function));
    }
}

// Version 2: Enhanced features
walker AdvancedAnalyzer {
    can analyze with CodeFile entry {
        here.function_count = len(-->(`?Function));
        here.complexity = self.calculate_complexity();
        here.dependencies = self.extract_imports();
    }
}
```

Start with core features. Enhance iteratively.

---

## Key Principles Summary

1. **Graph-first design**: Model your domain as nodes and edges before writing code
2. **Walkers for logic**: Nodes store state, walkers contain behavior
3. **Multi-agent architecture**: Many small specialized walkers coordinated by a supervisor
4. **Declarative traversal**: Use visit statements with filters
5. **Type-based routing**: Let Jac automatically route walkers to appropriate abilities
6. **Spatial thinking**: Logic flows through graph space, not through call stacks
7. **API-first walkers**: Design walkers as HTTP endpoints from the start
8. **Error resilience**: Collect all errors, continue processing, report comprehensively
9. **Report results**: Use report to return data from walkers
10. **Test incrementally**: Build and verify each walker independently

---

## For Codebase Genius Implementation

### Graph Architecture
```jac
Repository --> Contains --> Directory --> Contains --> CodeFile
CodeFile --> Defines --> Function
CodeFile --> Defines --> Class
Function --> Calls --> Function
Class --> Inherits --> Class
Module --> Imports --> Module
```

### Walker Architecture
- **Supervisor**: Orchestrates the entire workflow
- **RepoMapper**: Clones repo and builds file tree
- **CodeAnalyzer**: Parses code and extracts entities
- **CCGBuilder**: Constructs Code Context Graph
- **DocGenerator**: Synthesizes markdown documentation

### API Endpoints
- `POST /walker/api_generate_docs`
- `POST /walker/api_validate_repo`
- `POST /walker/api_get_file_tree`
- `POST /walker/api_get_ccg`
- `POST /walker/api_get_statistics`

### Workflow Pattern
1. Supervisor receives Repository node
2. Spawns RepoMapper to build directory/file structure
3. Spawns CodeAnalyzer to parse code and create Function/Class nodes
4. Spawns CCGBuilder to create relationship edges
5. Spawns DocGenerator to traverse complete graph and generate markdown
6. Reports final documentation with diagrams

Build spatially. Think in graphs. Walk through your data.

**This is the Jac way.**

---

**Remember**: This backend should be production-ready, handling real-world repositories with robustness, clear error messages, and high-quality AI-generated documentation. Focus on leveraging both Jac's unique graph paradigm AND byLLM's AI capabilities for intelligent multi-agent orchestration and natural language documentation generation.
