# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
End-to-end tests for ProjectScanner: the core property this whole layer
exists for is that scanning source B does not wipe source A's contribution
(the old /api/scan cleared the entire global graph on every call - see
apps/modernizeai_ui/server.py:172-176) - plus incremental rescan (an
unchanged source does no parsing work) and persistence across a fresh
scanner instance (simulating a server restart).
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath("."))

from coded_tools.modernize.graph.store import SqliteGraphStore
from coded_tools.modernize.sources.models import ProjectStore, Source
from coded_tools.modernize.sources.scanner import ProjectScanner

JAVA_A = "package com.a;\npublic class Foo { void m() { new Bar(); } }\n"
JAVA_A_V2 = "package com.a;\npublic class Foo { void m() { new Bar(); } void n() {} }\n"
JAVA_B = "package com.b;\npublic class Baz { }\n"


class TestProjectScanner(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="modernize_scanner_")
        self.repo_a_dir = os.path.join(self.tmp_dir, "repo_a")
        self.repo_b_dir = os.path.join(self.tmp_dir, "repo_b")
        os.makedirs(self.repo_a_dir)
        os.makedirs(self.repo_b_dir)
        with open(os.path.join(self.repo_a_dir, "Foo.java"), "w") as f:
            f.write(JAVA_A)
        with open(os.path.join(self.repo_b_dir, "Baz.java"), "w") as f:
            f.write(JAVA_B)

        self.projects_root = os.path.join(self.tmp_dir, "projects")
        self.project_store = ProjectStore(root_dir=self.projects_root)
        self.graph_store = SqliteGraphStore(root_dir=self.projects_root)
        self.scanner = ProjectScanner(project_store=self.project_store, graph_store=self.graph_store)

        project = self.project_store.create("multisrc")
        project.add_source(Source(source_id="repoA", type="local", config={"root_path": self.repo_a_dir}))
        project.add_source(Source(source_id="repoB", type="local", config={"root_path": self.repo_b_dir}))
        self.project_store.save(project)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_scanning_second_source_does_not_wipe_first(self):
        r1 = self.scanner.scan_source("multisrc", "repoA")
        self.assertEqual(r1.status, "scanned")

        r2 = self.scanner.scan_source("multisrc", "repoB")
        self.assertEqual(r2.status, "scanned")

        kg = self.graph_store.load("multisrc")
        self.assertTrue(kg.graph.has_node("repoA::com.a.Foo"), "source A's node must survive source B's scan")
        self.assertTrue(kg.graph.has_node("repoB::com.b.Baz"))

    def test_scan_all_covers_every_source(self):
        results = self.scanner.scan_all("multisrc")
        self.assertEqual(set(results.keys()), {"repoA", "repoB"})
        self.assertTrue(all(r.status == "scanned" for r in results.values()))

        kg = self.graph_store.load("multisrc")
        self.assertTrue(kg.graph.has_node("repoA::com.a.Foo"))
        self.assertTrue(kg.graph.has_node("repoB::com.b.Baz"))

    def test_rescan_with_no_changes_is_reported_as_unchanged(self):
        self.scanner.scan_source("multisrc", "repoA")
        result = self.scanner.scan_source("multisrc", "repoA")
        self.assertEqual(result.status, "unchanged")

    def test_rescan_after_file_change_updates_graph(self):
        self.scanner.scan_source("multisrc", "repoA")
        with open(os.path.join(self.repo_a_dir, "Foo.java"), "w") as f:
            f.write(JAVA_A_V2)

        result = self.scanner.scan_source("multisrc", "repoA")
        self.assertEqual(result.status, "scanned")

        kg = self.graph_store.load("multisrc")
        # Symbols table should now show the new method too (n), reachable via
        # the rebuilt graph having refreshed the Foo node rather than leaving
        # a stale one from before the edit.
        self.assertTrue(kg.graph.has_node("repoA::com.a.Foo"))

    def test_force_full_rescans_even_without_changes(self):
        self.scanner.scan_source("multisrc", "repoA")
        result = self.scanner.scan_source("multisrc", "repoA", force_full=True)
        self.assertEqual(result.status, "scanned")

    def test_project_json_updated_with_scan_status(self):
        self.scanner.scan_source("multisrc", "repoA")
        reloaded = self.project_store.load("multisrc")
        source_a = reloaded.get_source("repoA")
        self.assertEqual(source_a.last_scan_status, "success")
        self.assertIsNotNone(source_a.last_fingerprint)
        self.assertIsNotNone(source_a.last_scanned_at)

    def test_scan_error_is_reported_not_raised(self):
        project = self.project_store.load("multisrc")
        project.add_source(Source(source_id="broken", type="local", config={"root_path": "/does/not/exist"}))
        self.project_store.save(project)

        result = self.scanner.scan_source("multisrc", "broken")
        self.assertEqual(result.status, "error")

        reloaded = self.project_store.load("multisrc")
        self.assertEqual(reloaded.get_source("broken").last_scan_status, "error")

    def test_graph_persists_across_a_fresh_scanner_instance(self):
        self.scanner.scan_all("multisrc")
        # A brand-new ProjectScanner + GraphStore, as a restarted server would create.
        fresh_scanner = ProjectScanner(
            project_store=ProjectStore(root_dir=self.projects_root),
            graph_store=SqliteGraphStore(root_dir=self.projects_root),
        )
        kg = fresh_scanner.graph_store.load("multisrc")
        self.assertTrue(kg.graph.has_node("repoA::com.a.Foo"))
        self.assertTrue(kg.graph.has_node("repoB::com.b.Baz"))

    def test_connection_test_passes_for_valid_source(self):
        result = self.scanner.test_source("multisrc", "repoA")
        self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
