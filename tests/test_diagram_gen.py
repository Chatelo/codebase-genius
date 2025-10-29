import unittest

from backend.utils.diagram_gen import (
    make_call_graph_mermaid,
    make_class_hierarchy_mermaid,
    make_module_graph_mermaid,
)


class TestDiagramGen(unittest.TestCase):
    def test_mermaid_builders(self):
        entities = {
            "files": [
                {
                    "module": "pkg.mod",
                    "functions": ["a", "b"],
                    "classes": ["Base", "Child"],
                    "imports": [{"module": "other.mod"}],
                    "calls": [
                        {"caller": "a", "callee": "b"},
                    ],
                    "inherits": [
                        {"class": "Child", "base": "Base"}
                    ],
                },
                {
                    "module": "other.mod",
                    "functions": ["x"],
                    "classes": [],
                    "imports": [],
                    "calls": [],
                    "inherits": [],
                },
            ]
        }

        cg = make_call_graph_mermaid(entities)
        self.assertIn("flowchart LR", cg)
        # New syntax uses bracketed labels with sanitized ids
        self.assertIn('["pkg.mod.a"]', cg)
        self.assertIn('["pkg.mod.b"]', cg)
        self.assertIn('-->', cg)

        ch = make_class_hierarchy_mermaid(entities)
        self.assertIn("flowchart TB", ch)
        self.assertIn('["Child"]', ch)
        self.assertIn('["Base"]', ch)
        self.assertIn('-->|extends|', ch)

        mg = make_module_graph_mermaid(entities)
        self.assertIn("flowchart LR", mg)
        self.assertIn('["pkg.mod"]', mg)
        self.assertIn('["other.mod"]', mg)
        self.assertIn('-->', mg)


if __name__ == "__main__":
    unittest.main()

