# Codebase Genius backend entry (JacLang)
# Sample AI-powered walker using by llm exposed via jac serve

import from byllm.llm { Model }
import from agents.DocGenie { docgen_summarize }
import from agents.Supervisor { build_overview }


glob llm = Model(model_name="gpt-4o-mini");

# AI function (not a walker ability) powered by byLLM
"""Generate a friendly greeting for the given name."""
def make_greeting(name: str) -> str by llm(method="Reason");

walker api_hello {
    has who: str = "Codebase Genius";
    has use_llm: bool = False;  # Toggle to call LLM or use fallback

    obj __specs__ {
        # Make this walker publicly callable via REST (no auth for smoke test)
        static has auth: bool = False;
        # static has methods: list = ["post"];  # default is POST
    }

    can process with `root entry {
        msg = "";
        if self.use_llm {
            msg = make_greeting(self.who);
        } else {
            msg = f"Hello, {self.who}!";
        }
        report {
            "status": "success",
            "message": msg
        };
    }
}


walker generate_docs {
    has repo_url: str = "";
    has depth: str = "standard";
    has use_llm: bool = False;
    has include_diagrams: bool = False;
    has exclude_dirs: list = [];

    obj __specs__ {
        static has auth: bool = False;
    }

    can process with `root entry {
        # Build an overview via Supervisor helpers (stub unless depth=="deep")
        overview = build_overview(self.repo_url, self.depth, self.exclude_dirs);
        file_tree = overview["file_tree"];
        stats = overview["stats"];
        entities = {};
        if "entities" in overview { entities = overview["entities"]; }

        # Prepare extra context for the LLM
        extra_context = f"Files={stats['files']}, Jac={stats['jac_files']}, Docs={stats['docs']}. Diagrams={self.include_diagrams}.";

        # Generate documentation (stub or LLM)
        doc = "";
        if self.use_llm {
            prompt = f"Generate high-level documentation for repo: {self.repo_url}. Depth: {self.depth}. " + extra_context;
            doc = docgen_summarize(self.repo_url, self.depth, prompt);
        } else {
            doc = f"[Stub] Documentation for {self.repo_url} (depth={self.depth}, diagrams={self.include_diagrams})";
        }

        report {
            "status": "success",
            "repo_url": self.repo_url,
            "depth": self.depth,
            "include_diagrams": self.include_diagrams,
            "file_tree": file_tree,
            "stats": stats,
            "entities": entities,
            "documentation": doc
        };
    }
}


