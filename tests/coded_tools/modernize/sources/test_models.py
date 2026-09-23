# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""Tests for Project/Source persistence: round-trip, no-secret guarantee, validation."""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath("."))

from coded_tools.modernize.sources.models import Project, ProjectStore, Source


class TestProjectModel(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="modernize_projects_")
        self.store = ProjectStore(root_dir=self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_create_and_load_round_trip(self):
        project = self.store.create("claimcore")
        project.add_source(Source(source_id="repo1", type="git", config={"url": "https://x/y.git"}, credential_ref="GITHUB_TOKEN"))
        self.store.save(project)

        reloaded = self.store.load("claimcore")
        self.assertEqual(reloaded.name, "claimcore")
        self.assertEqual(len(reloaded.sources), 1)
        self.assertEqual(reloaded.sources[0].type, "git")
        self.assertEqual(reloaded.sources[0].credential_ref, "GITHUB_TOKEN")

    def test_credential_ref_is_a_name_never_a_secret_value(self):
        project = self.store.create("secure_proj")
        project.add_source(Source(
            source_id="db1", type="database", config={"host": "db.internal"}, credential_ref="ORACLE_PROD",
        ))
        self.store.save(project)

        with open(self.store._project_path("secure_proj"), encoding="utf-8") as f:
            raw_text = f.read()
        self.assertIn("ORACLE_PROD", raw_text)  # the reference name is fine to store
        # No plausible secret-shaped value should ever appear - this project only
        # ever held a reference name, so this is really asserting the field
        # itself round-trips as a bare name, not a "user:pass@" shape.
        self.assertNotIn("@", raw_text)
        self.assertNotIn("://", raw_text.split('"config"')[0])

    def test_duplicate_source_id_rejected(self):
        project = Project(name="p")
        project.add_source(Source(source_id="s1", type="local", config={}))
        with self.assertRaises(ValueError):
            project.add_source(Source(source_id="s1", type="git", config={}))

    def test_remove_source(self):
        project = Project(name="p")
        project.add_source(Source(source_id="s1", type="local", config={}))
        self.assertTrue(project.remove_source("s1"))
        self.assertFalse(project.remove_source("s1"))
        self.assertEqual(project.sources, [])

    def test_invalid_project_name_rejected(self):
        with self.assertRaises(ValueError):
            self.store.create("../escape")

    def test_list_projects(self):
        self.store.create("alpha")
        self.store.create("beta")
        self.assertEqual(self.store.list_projects(), ["alpha", "beta"])

    def test_double_create_rejected(self):
        self.store.create("dup")
        with self.assertRaises(ValueError):
            self.store.create("dup")

    def test_delete_project(self):
        self.store.create("temp_proj")
        self.assertTrue(self.store.exists("temp_proj"))
        self.store.delete("temp_proj")
        self.assertFalse(self.store.exists("temp_proj"))

    def test_save_is_atomic_no_tmp_file_left_behind(self):
        project = self.store.create("atomic_proj")
        self.store.save(project)
        path = self.store._project_path("atomic_proj")
        self.assertTrue(os.path.exists(path))
        self.assertFalse(os.path.exists(path + ".tmp"))
        with open(path, encoding="utf-8") as f:
            json.load(f)  # must be valid JSON, not partially written


if __name__ == "__main__":
    unittest.main()
