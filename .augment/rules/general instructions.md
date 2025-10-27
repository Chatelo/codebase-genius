---
type: "always_apply"
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
Got it — here’s the concise instruction to add:

---

### 🧩 Package Management

Always use **`uv`** as the Python package manager for creating environments, installing dependencies, and running Python-related commands.


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