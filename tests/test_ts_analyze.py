import os
import tempfile
import unittest
from pathlib import Path

from backend.utils.ts_analyze import extract_entities


SAMPLE_PY = """
import math
from os import path

class Base:
    pass

class Child(Base):
    def m(self):
        return 1


def a():
    b()
    c()


def b():
    return 2


def c():
    return 3
"""


class TestTsAnalyze(unittest.TestCase):
    def test_extract_entities_python(self):
        with tempfile.TemporaryDirectory() as tmpd:
            p = Path(tmpd) / "foo.py"
            p.write_text(SAMPLE_PY, encoding="utf-8")

            file_tree = [
                {"type": "CodeFile", "path": "foo.py", "language": "python"}
            ]

            res = extract_entities(tmpd, file_tree, parallel=False)
            self.assertIn("files", res)
            self.assertEqual(len(res["files"]), 1)
            fe = res["files"][0]

            # Module name and language
            self.assertEqual(fe.get("module"), "foo")
            self.assertEqual(fe.get("language"), "python")

            # Functions and classes
            self.assertTrue({"a", "b", "c"}.issubset(set(fe.get("functions", []))))
            self.assertTrue({"Base", "Child"}.issubset(set(fe.get("classes", []))))

            # Imports captured
            imps = fe.get("imports", [])
            self.assertGreaterEqual(len(imps), 2)

            # Calls captured: a -> b, c
            calls = fe.get("calls", [])
            callers = [c.get("caller") for c in calls]
            callees = [c.get("callee") for c in calls]
            self.assertIn("a", callers)
            self.assertIn("b", callees)
            self.assertIn("c", callees)


if __name__ == "__main__":
    unittest.main()

