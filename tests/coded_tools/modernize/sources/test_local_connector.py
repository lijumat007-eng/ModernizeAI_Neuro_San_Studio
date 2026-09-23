# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""Tests for LocalConnector: extension filtering, excludes, fingerprint stability."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath("."))

from coded_tools.modernize.sources.local import LocalConnector


class TestLocalConnector(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="modernize_local_src_")
        os.makedirs(os.path.join(self.tmp_dir, "src"))
        os.makedirs(os.path.join(self.tmp_dir, "node_modules", "pkg"))
        with open(os.path.join(self.tmp_dir, "src", "Foo.java"), "w") as f:
            f.write("class Foo {}")
        with open(os.path.join(self.tmp_dir, "src", "notes.md"), "w") as f:
            f.write("# notes")
        with open(os.path.join(self.tmp_dir, "src", "image.png"), "wb") as f:
            f.write(b"\x89PNG\r\n")
        with open(os.path.join(self.tmp_dir, "node_modules", "pkg", "Ignored.java"), "w") as f:
            f.write("class Ignored {}")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_fetches_supported_extensions_only(self):
        connector = LocalConnector("s1", {"root_path": self.tmp_dir})
        docs, _fp = connector.fetch()
        paths = {d.path for d in docs}
        self.assertIn("src/Foo.java", paths)
        self.assertIn("src/notes.md", paths)
        self.assertNotIn("src/image.png", paths)

    def test_excludes_default_directories(self):
        connector = LocalConnector("s1", {"root_path": self.tmp_dir})
        docs, _fp = connector.fetch()
        paths = {d.path for d in docs}
        self.assertFalse(any("node_modules" in p for p in paths))

    def test_doc_kind_assigned_to_markdown(self):
        connector = LocalConnector("s1", {"root_path": self.tmp_dir})
        docs, _fp = connector.fetch()
        notes = next(d for d in docs if d.path == "src/notes.md")
        self.assertEqual(notes.kind, "doc")
        java = next(d for d in docs if d.path == "src/Foo.java")
        self.assertEqual(java.kind, "file")

    def test_fingerprint_stable_when_unchanged(self):
        connector = LocalConnector("s1", {"root_path": self.tmp_dir})
        _docs1, fp1 = connector.fetch()
        _docs2, fp2 = connector.fetch()
        self.assertEqual(fp1, fp2)

    def test_fingerprint_changes_on_edit(self):
        connector = LocalConnector("s1", {"root_path": self.tmp_dir})
        _docs1, fp1 = connector.fetch()
        with open(os.path.join(self.tmp_dir, "src", "Foo.java"), "w") as f:
            f.write("class Foo { void m() {} }")
        _docs2, fp2 = connector.fetch()
        self.assertNotEqual(fp1, fp2)

    def test_include_globs_narrow_selection(self):
        connector = LocalConnector("s1", {"root_path": self.tmp_dir, "include_globs": ["*.md"]})
        docs, _fp = connector.fetch()
        paths = {d.path for d in docs}
        self.assertEqual(paths, {"src/notes.md"})

    def test_test_connection_reports_missing_directory(self):
        connector = LocalConnector("s1", {"root_path": os.path.join(self.tmp_dir, "nope")})
        result = connector.test_connection()
        self.assertFalse(result.ok)

    def test_test_connection_succeeds_for_real_directory(self):
        connector = LocalConnector("s1", {"root_path": self.tmp_dir})
        result = connector.test_connection()
        self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
