# Orchestrator walker (skeleton)

import from agents.RepoMapper { RepoMapper }
import from agents.CodeAnalyzer { CodeAnalyzer }
import from agents.DocGenie { DocGenie }

walker Supervisor {
    can orchestrate with `root entry {
        # Spawn specialized walkers (skeletons); no-op until they are implemented
        spawn RepoMapper() on here;
        spawn CodeAnalyzer() on here;
        spawn DocGenie() on here;
    }
}
