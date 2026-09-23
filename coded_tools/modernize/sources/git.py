# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
GitConnector: shallow-clones (or fetches) one repository into a workspace
directory and hands its tracked files to LocalConnector-style ingestion.
Supports a token for private repos (GitHub/GitLab/Bitbucket/Azure DevOps all
accept `https://<token>@host/...` or `https://oauth2:<token>@host/...`), and
is incremental: re-scanning only re-clones/pulls when the branch's HEAD SHA
has moved, otherwise reuses the existing checkout.
"""

import os
import re
import shutil
import stat
import subprocess
from typing import List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

from coded_tools.modernize.sources.base import (
    ConnectionTestResult,
    SourceConnector,
    SourceDocument,
    resolve_secret,
)
from coded_tools.modernize.sources.local import LocalConnector

_GIT_TIMEOUT_SECONDS = 180


def _inject_token(url: str, token: Optional[str]) -> str:
    if not token or "@" in urlsplit(url).netloc:
        return url  # already has embedded credentials, or nothing to inject
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return url  # SSH URLs use keys, not tokens - left untouched
    netloc = f"oauth2:{token}@{parts.netloc}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _force_remove_dir(path: str) -> None:
    if not os.path.exists(path):
        return

    def on_rm_error(func, p, _exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass

    shutil.rmtree(path, onerror=on_rm_error)


def _run_git(args: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args, capture_output=True, text=True, timeout=_GIT_TIMEOUT_SECONDS, cwd=cwd,
    )


class GitConnector(SourceConnector):
    """
    config:
        url: str (required) - clone URL (https or ssh)
        branch: str (optional, default "main")
        workspace_root: str (optional, default "data/_workspaces")
        include_globs / exclude_globs: passed through to LocalConnector for the checkout
    credential_ref: env var NAME holding a personal access token (https URLs only)
    """

    type_name = "git"

    def _workspace_dir(self) -> str:
        url = self.config.get("url", "")
        # Split on both separators: a "url" can be a Windows local path or a
        # UNC-style remote as well as an actual URL, and re-joining a
        # colon-containing component (e.g. a bare "C:") into a directory name
        # is illegal on Windows (WinError 123), not just cosmetically wrong.
        repo_name = re.split(r"[\\/]", url.rstrip("\\/"))[-1].removesuffix(".git") or self.source_id
        repo_name = re.sub(r'[<>:"|?*]', "_", repo_name)
        workspace_root = self.config.get("workspace_root", "data/_workspaces")
        return os.path.join(workspace_root, f"{self.source_id}__{repo_name}")

    def test_connection(self) -> ConnectionTestResult:
        url = self.config.get("url")
        if not url:
            return ConnectionTestResult(ok=False, message="'url' is required for a git source.")
        try:
            token = resolve_secret(self.credential_ref)
        except Exception as e:  # CredentialError
            return ConnectionTestResult(ok=False, message=str(e))
        auth_url = _inject_token(url, token)
        try:
            res = _run_git(["ls-remote", "--heads", auth_url])
        except (subprocess.TimeoutExpired, OSError) as e:
            return ConnectionTestResult(ok=False, message=f"git error: {e}")
        if res.returncode != 0:
            return ConnectionTestResult(ok=False, message=_redact(res.stderr.strip() or "git ls-remote failed", token))
        branch_count = len([l for l in res.stdout.splitlines() if l.strip()])
        return ConnectionTestResult(ok=True, message=f"Reachable ({branch_count} branch ref(s) found).")

    def fetch(self, since_fingerprint: Optional[str] = None) -> Tuple[List[SourceDocument], str]:
        url = self.config.get("url")
        if not url:
            raise ValueError(f"Source '{self.source_id}': 'url' is required for a git source.")
        branch = self.config.get("branch", "main")
        token = resolve_secret(self.credential_ref)
        auth_url = _inject_token(url, token)
        workspace = self._workspace_dir()

        try:
            head_sha = self._sync_checkout(auth_url, branch, workspace)
        except (subprocess.TimeoutExpired, OSError) as e:
            raise RuntimeError(f"git sync failed for source '{self.source_id}': {_redact(str(e), token)}") from e

        if since_fingerprint is not None and since_fingerprint == head_sha:
            return [], head_sha  # nothing changed since the last scan

        local = LocalConnector(
            self.source_id,
            {**self.config, "root_path": workspace, "exclude_globs": [".git"] + list(self.config.get("exclude_globs", []))},
        )
        documents, _local_fingerprint = local.fetch()
        for doc in documents:
            doc.uri = self._blob_url(url, branch, doc.path)
            doc.metadata["git_sha"] = head_sha
        return documents, head_sha

    def _sync_checkout(self, auth_url: str, branch: str, workspace: str) -> str:
        os.makedirs(os.path.dirname(workspace) or ".", exist_ok=True)
        if os.path.isdir(os.path.join(workspace, ".git")):
            res = _run_git(["fetch", "--depth", "1", "origin", branch], cwd=workspace)
            if res.returncode == 0:
                _run_git(["checkout", "FETCH_HEAD"], cwd=workspace)
            else:
                # Remote/branch may have changed shape; fall back to a clean re-clone.
                _force_remove_dir(workspace)

        if not os.path.isdir(os.path.join(workspace, ".git")):
            cmd = ["clone", "--depth", "1"]
            if branch and branch not in ("main", "master"):
                cmd += ["-b", branch]
            cmd += [auth_url, workspace]
            res = _run_git(cmd)
            if res.returncode != 0:
                # Retry without an explicit branch (covers repos whose default branch differs).
                res = _run_git(["clone", "--depth", "1", auth_url, workspace])
                if res.returncode != 0:
                    raise RuntimeError(f"git clone failed: {res.stderr.strip()}")

        sha_res = _run_git(["rev-parse", "HEAD"], cwd=workspace)
        return sha_res.stdout.strip() if sha_res.returncode == 0 else "unknown"

    @staticmethod
    def _blob_url(url: str, branch: str, rel_path: str) -> str:
        clean = url.removesuffix(".git")
        if "github.com" in clean or "gitlab.com" in clean:
            return f"{clean}/blob/{branch}/{rel_path}"
        return f"{clean}#{rel_path}"


def _redact(message: str, token: Optional[str]) -> str:
    if token:
        message = message.replace(token, "***")
    return message
