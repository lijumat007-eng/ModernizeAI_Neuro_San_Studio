# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
HTTP-level tests for the multi-source Project API added to
apps/modernizeai_ui/server.py. Swaps the module's global project_store/
graph_store/project_scanner to point at a temp directory for the duration of
each test, so this never touches the real `projects/` folder next to the
running app.
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("apps/modernizeai_ui"))

from fastapi.testclient import TestClient

import server  # apps/modernizeai_ui/server.py
from coded_tools.modernize.graph.store import SqliteGraphStore
from coded_tools.modernize.sources.models import ProjectStore
from coded_tools.modernize.sources.scanner import ProjectScanner


class TestProjectApi(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="modernize_api_")
        self._orig_project_store = server.project_store
        self._orig_graph_store = server.graph_store
        self._orig_scanner = server.project_scanner

        server.project_store = ProjectStore(root_dir=self.tmp_dir)
        server.graph_store = SqliteGraphStore(root_dir=self.tmp_dir)
        server.project_scanner = ProjectScanner(project_store=server.project_store, graph_store=server.graph_store)

        self.client = TestClient(server.app)

        self.repo_dir = os.path.join(self.tmp_dir, "repo")
        os.makedirs(self.repo_dir)
        with open(os.path.join(self.repo_dir, "Foo.java"), "w") as f:
            f.write("package com.a;\npublic class Foo {}\n")

    def tearDown(self):
        server.project_store = self._orig_project_store
        server.graph_store = self._orig_graph_store
        server.project_scanner = self._orig_scanner
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_create_and_list_project(self):
        res = self.client.post("/api/projects", json={"name": "demo"})
        self.assertEqual(res.status_code, 200)
        res = self.client.get("/api/projects")
        self.assertIn("demo", res.json()["projects"])

    def test_duplicate_project_rejected_with_409(self):
        self.client.post("/api/projects", json={"name": "demo"})
        res = self.client.post("/api/projects", json={"name": "demo"})
        self.assertEqual(res.status_code, 409)

    def test_get_nonexistent_project_returns_404(self):
        res = self.client.get("/api/projects/nope")
        self.assertEqual(res.status_code, 404)

    def test_add_source_and_scan_it(self):
        self.client.post("/api/projects", json={"name": "demo"})
        res = self.client.post("/api/projects/demo/sources", json={
            "source_id": "repoA", "type": "local", "config": {"root_path": self.repo_dir},
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["sources"]), 1)

        res = self.client.post("/api/projects/demo/sources/repoA/scan")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "scanned")

        res = self.client.get("/api/projects/demo/graph")
        self.assertGreater(res.json()["total_nodes"], 0)

    def test_scanning_two_sources_does_not_wipe_first_via_http(self):
        second_repo = os.path.join(self.tmp_dir, "repo2")
        os.makedirs(second_repo)
        with open(os.path.join(second_repo, "Bar.java"), "w") as f:
            f.write("package com.b;\npublic class Bar {}\n")

        self.client.post("/api/projects", json={"name": "demo"})
        self.client.post("/api/projects/demo/sources", json={
            "source_id": "repoA", "type": "local", "config": {"root_path": self.repo_dir},
        })
        self.client.post("/api/projects/demo/sources", json={
            "source_id": "repoB", "type": "local", "config": {"root_path": second_repo},
        })

        self.client.post("/api/projects/demo/sources/repoA/scan")
        self.client.post("/api/projects/demo/sources/repoB/scan")

        export = self.client.get("/api/projects/demo/graph/export").json()
        node_ids = {n["id"] for n in export["nodes"]}
        self.assertIn("repoA::com.a.Foo", node_ids)
        self.assertIn("repoB::com.b.Bar", node_ids)

    def test_scan_all_endpoint(self):
        self.client.post("/api/projects", json={"name": "demo"})
        self.client.post("/api/projects/demo/sources", json={
            "source_id": "repoA", "type": "local", "config": {"root_path": self.repo_dir},
        })
        res = self.client.post("/api/projects/demo/scan")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["repoA"]["status"], "scanned")

    def test_test_source_endpoint(self):
        self.client.post("/api/projects", json={"name": "demo"})
        self.client.post("/api/projects/demo/sources", json={
            "source_id": "repoA", "type": "local", "config": {"root_path": self.repo_dir},
        })
        res = self.client.post("/api/projects/demo/sources/repoA/test")
        self.assertTrue(res.json()["ok"])

    def test_remove_source(self):
        self.client.post("/api/projects", json={"name": "demo"})
        self.client.post("/api/projects/demo/sources", json={
            "source_id": "repoA", "type": "local", "config": {"root_path": self.repo_dir},
        })
        res = self.client.delete("/api/projects/demo/sources/repoA")
        self.assertEqual(res.json()["sources"], [])

    def test_delete_project_removes_its_graph_too(self):
        self.client.post("/api/projects", json={"name": "demo"})
        self.client.post("/api/projects/demo/sources", json={
            "source_id": "repoA", "type": "local", "config": {"root_path": self.repo_dir},
        })
        self.client.post("/api/projects/demo/sources/repoA/scan")
        self.assertTrue(server.graph_store.exists("demo"))

        res = self.client.delete("/api/projects/demo")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(server.project_store.exists("demo"))
        self.assertFalse(server.graph_store.exists("demo"))

    def test_source_types_endpoint_lists_local_git_s3(self):
        res = self.client.get("/api/source_types")
        types = res.json()["types"]
        self.assertIn("local", types)
        self.assertIn("git", types)
        self.assertIn("s3", types)


if __name__ == "__main__":
    unittest.main()
