# Codebase Genius backend entry (JacLang)
# Sample AI-powered walker using by llm exposed via jac serve

import from byllm.llm { Model }
import from agents.DocGenie { docgen_summarize }


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

walker generate_docs {
    has repo_url: str = "";
    has depth: str = "standard";
    has use_llm: bool = False;
    has include_diagrams: bool = False;

    obj __specs__ {
        static has auth: bool = False;
    }

    can process with `root entry {
        result = "";
        if self.use_llm {
            prompt = f"Generate high-level documentation for repo: {self.repo_url}. Depth: {self.depth}. Include diagrams: {self.include_diagrams}.";
            result = docgen_summarize(self.repo_url, self.depth, prompt);
        } else {
            result = f"[Stub] Documentation for {self.repo_url} (depth={self.depth}, diagrams={self.include_diagrams})";
        }
        report {
            "status": "success",
            "repo_url": self.repo_url,
            "depth": self.depth,
            "include_diagrams": self.include_diagrams,
            "documentation": result
        };
    }
}

}
