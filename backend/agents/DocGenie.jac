sem docgen.purpose is "Generates documentation using by llm (DocGenie)";

import from byllm.llm { Model }
import from utils.cache { get_cache }

glob llm = Model(model_name="gpt-4o-mini");

sem docgen.summarize is "High-level repository overview; inputs: repo_url, depth [fast|standard|deep], extra_context; returns concise markdown";
sem docgen.llm.method is "Reason (temp=0.3)";
def docgen_summarize(repo_url: str, depth: str = "standard", extra_context: str = "") -> str by llm(
    method="Reason",
    temperature=0.3
);

# Optional walker wrapper, can be used independently if needed
walker DocGenie {
    has repo_url: str = "";
    has depth: str = "standard";
    has use_llm: bool = False;
    has summary: str = "";
    has cache_enabled: bool = True;
    has llm_seed: int = 0;

    can process with `root entry {
        if self.use_llm {
            # Attempt to use a simple file-based cache for LLM outputs to reduce cost and rate-limit impact.
            cache = None;
            try { cache = get_cache(); } except Exception { cache = None; }
            cache_key_params = {"depth": self.depth, "extra": ""};
            cached = None;
            try {
                if cache != None {
                    cached = cache.get("llm_summary", self.repo_url, depth=self.depth, extra_context="");
                }
            } except Exception { cached = None; }

            # Force refresh disabled by default; CI/runner can control caching via cache invalidation if needed
            force_refresh = false;
            if cached != None and not force_refresh {
                try { self.summary = cached["summary"]; } except Exception { self.summary = cached; }
            } else {
                # Deterministic seed support (best-effort). Some LLM integrations accept a seed.
                self.llm_seed = 0;
                try {
                    # Call the by-llm function; guard in case of rate limits or other errors
                    self.summary = docgen_summarize(self.repo_url, self.depth, "");
                } except Exception as e {
                    # Graceful fallback on LLM failure
                    self.summary = f"[LLM error] Could not generate summary: {e}. Using stub.";
                }

                # Store in cache if available
                try {
                    if cache != None {
                        cache.set("llm_summary", self.repo_url, {"summary": self.summary}, depth=self.depth, extra_context="");
                    }
                } except Exception { }
            }
        } else {
            self.summary = f"Documentation stub for {self.repo_url} (depth: {self.depth})";
        }
        report {"summary": self.summary};
    }
}
