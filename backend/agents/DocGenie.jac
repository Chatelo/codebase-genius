sem docgen.purpose is "Generates documentation using by llm (DocGenie)";

import from byllm.llm { Model }

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

    can process with `root entry {
        if self.use_llm {
            self.summary = docgen_summarize(self.repo_url, self.depth, "");
        } else {
            self.summary = f"Documentation stub for {self.repo_url} (depth: {self.depth})";
        }
        report {"summary": self.summary};
    }
}
