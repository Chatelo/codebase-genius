import os
import tempfile
import unittest
from pathlib import Path

from backend.utils.fs_map import scan_repo_tree, extract_readme, summarize_readme_sections


class TestFsMap(unittest.TestCase):
    def test_scan_repo_tree_basic(self):
        with tempfile.TemporaryDirectory() as tmpd:
            root = Path(tmpd)
            # Create files and directories
            (root / "a.py").write_text("print('hi')\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "README.md").write_text("# Title\nSome content\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "x.js").write_text("console.log('x')\n", encoding="utf-8")

            items = scan_repo_tree(str(root), compute_line_counts=False)
            paths = {it["path"] for it in items}

            # Should include a.py and docs/README.md, but not node_modules/x.js
            self.assertIn("a.py", paths)
            self.assertIn("docs/README.md", paths)
            self.assertNotIn("node_modules/x.js", paths)

            # Check classification
            a_meta = next(it for it in items if it["path"] == "a.py")
            self.assertEqual(a_meta["type"], "CodeFile")
            self.assertEqual(a_meta["language"], "python")

    def test_readme_extract_and_summarize(self):
        with tempfile.TemporaryDirectory() as tmpd:
            root = Path(tmpd)
            content = (
                "# Project\n\n"
                "Some intro.\n\n"
                "## Usage\n\nRun it like this.\n\n"
                "## API\nMethods overview.\n"
            )
            (root / "README.md").write_text(content, encoding="utf-8")

            rd = extract_readme(str(root))
            self.assertIsNotNone(rd)
            self.assertEqual(rd["path"], "README.md")
            self.assertGreater(len(rd.get("sections", [])), 0)

            summary = summarize_readme_sections(rd["sections"], max_sections=2)
            self.assertTrue(len(summary) > 0)


if __name__ == "__main__":
    unittest.main()

