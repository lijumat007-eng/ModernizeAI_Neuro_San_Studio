# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Tests for GitConnector against a real local repository (file:// URL, no
network). Covers cloning, incremental fetch (unchanged fingerprint skips
work), and picking up a new commit on re-scan.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath("."))

from coded_tools.modernize.sources.git import GitConnector, _inject_token


def _run(cmd, cwd):
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
    if res.returncode != 0:
        raise RuntimeError(f"{cmd} failed: {res.stderr}")
    return res


class TestGitConnector(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="modernize_git_")
        self.origin_dir = os.path.join(self.tmp_dir, "origin")
        os.makedirs(self.origin_dir)
        _run(["git", "init", "-b", "main"], cwd=self.origin_dir)
        _run(["git", "config", "user.email", "test@example.com"], cwd=self.origin_dir)
        _run(["git", "config", "user.name", "Test"], cwd=self.origin_dir)
        with open(os.path.join(self.origin_dir, "App.java"), "w") as f:
            f.write("class App {}")
        _run(["git", "add", "."], cwd=self.origin_dir)
        _run(["git", "commit", "-m", "initial"], cwd=self.origin_dir)

        self.workspace_root = os.path.join(self.tmp_dir, "_workspaces")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _connector(self) -> GitConnector:
        return GitConnector("repo1", {
            "url": self.origin_dir, "branch": "main", "workspace_root": self.workspace_root,
        })

    def test_clones_and_fetches_files(self):
        connector = self._connector()
        docs, sha = connector.fetch()
        paths = {d.path for d in docs}
        self.assertIn("App.java", paths)
        self.assertEqual(len(sha), 40)  # a real git SHA

    def test_rescan_with_same_fingerprint_returns_no_documents(self):
        connector = self._connector()
        _docs1, sha1 = connector.fetch()
        docs2, sha2 = connector.fetch(since_fingerprint=sha1)
        self.assertEqual(sha1, sha2)
        self.assertEqual(docs2, [])

    def test_rescan_after_new_commit_picks_up_change(self):
        connector = self._connector()
        _docs1, sha1 = connector.fetch()

        with open(os.path.join(self.origin_dir, "Second.java"), "w") as f:
            f.write("class Second {}")
        _run(["git", "add", "."], cwd=self.origin_dir)
        _run(["git", "commit", "-m", "second"], cwd=self.origin_dir)

        docs2, sha2 = connector.fetch(since_fingerprint=sha1)
        self.assertNotEqual(sha1, sha2)
        paths = {d.path for d in docs2}
        self.assertIn("Second.java", paths)
        self.assertIn("App.java", paths)  # full snapshot, not a diff

    def test_test_connection_succeeds_for_reachable_repo(self):
        result = self._connector().test_connection()
        self.assertTrue(result.ok)

    def test_test_connection_fails_for_unreachable_url(self):
        connector = GitConnector("repo1", {
            "url": os.path.join(self.tmp_dir, "does_not_exist"), "workspace_root": self.workspace_root,
        })
        result = connector.test_connection()
        self.assertFalse(result.ok)


class TestTokenInjection(unittest.TestCase):

    def test_https_token_injected(self):
        url = _inject_token("https://github.com/org/repo.git", "SECRETTOKEN")
        self.assertIn("oauth2:SECRETTOKEN@", url)

    def test_no_token_leaves_url_unchanged(self):
        url = _inject_token("https://github.com/org/repo.git", None)
        self.assertEqual(url, "https://github.com/org/repo.git")

    def test_ssh_url_left_untouched(self):
        url = _inject_token("git@github.com:org/repo.git", "SECRETTOKEN")
        self.assertEqual(url, "git@github.com:org/repo.git")

    def test_url_with_existing_credentials_not_double_injected(self):
        url = _inject_token("https://user:pass@github.com/org/repo.git", "SECRETTOKEN")
        self.assertNotIn("oauth2:", url)


if __name__ == "__main__":
    unittest.main()
