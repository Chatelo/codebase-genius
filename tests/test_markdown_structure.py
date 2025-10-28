import unittest

from backend.utils.output import build_structured_markdown


class TestMarkdownStructure(unittest.TestCase):
    def _fake_overview(self):
        return {
            "readme": {
                "sections": [
                    {"title": "Installation", "content": "pip install example"},
                    {"title": "Usage", "content": "python -m example run"},
                ]
            }
        }

    def test_build_structured_markdown_with_diagrams(self):
        repo_url = "https://github.com/foo/bar"
        overview = self._fake_overview()
        api_surface = "Classes: Foo, Bar\nTotal functions: 3"
        ccg_counts = {"calls": 1, "inherits": 2, "imports": 3}
        top_files_str = "foo.py(10), bar.py(8)"
        diagrams = {
            "call_graph": "flowchart LR\nA-->B",
            "class_hierarchy": "flowchart TB\nC-->D",
            "module_graph": "flowchart LR\nE-->F",
        }
        ccg_context = "- fn foo called by bar"
        ccg_mermaid = ""
        include_diagrams = True
        doc_overview = "This is a test overview"

        doc = build_structured_markdown(
            repo_url=repo_url,
            overview=overview,
            api_surface=api_surface,
            ccg_counts=ccg_counts,
            top_files_str=top_files_str,
            diagrams=diagrams,
            ccg_context=ccg_context,
            ccg_mermaid=ccg_mermaid,
            include_diagrams=include_diagrams,
            doc_overview=doc_overview,
        )

        # Required headings
        for heading in [
            "# Documentation for",
            "## Project Overview",
            "## Installation",
            "## Usage",
            "## API Reference",
            "## Diagrams",
            "## Citations",
        ]:
            self.assertIn(heading, doc)

        # Mermaid blocks embedded
        self.assertIn("```mermaid", doc)
        # API counts line present
        self.assertIn("CCG counts", doc)
        # Installation/Usage content pulled from README
        self.assertIn("pip install example", doc)
        self.assertIn("python -m example run", doc)

    def test_build_structured_markdown_without_diagrams(self):
        repo_url = "local-repo"
        overview = self._fake_overview()
        doc = build_structured_markdown(
            repo_url=repo_url,
            overview=overview,
            include_diagrams=False,
            diagrams={"call_graph": "flowchart LR\nA-->B"},
        )
        # Diagrams disabled notice is present and no mermaid fences
        self.assertIn("Diagrams disabled for this run.", doc)
        self.assertNotIn("```mermaid", doc)


if __name__ == "__main__":
    unittest.main()

