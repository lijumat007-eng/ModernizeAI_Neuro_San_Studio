# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
LocalConnector: reads a server-side directory tree. Replaces the old
browser-folder-picker flow (apps/modernizeai_ui/static/app.js), which never
actually uploaded anything and only worked if the folder already happened to
sit under `data/`.
"""

import fnmatch
import hashlib
import os
from typing import List
from typing import Optional
from typing import Tuple

from coded_tools.modernize.parsers.registry import get_default_registry
from coded_tools.modernize.sources.base import ConnectionTestResult
from coded_tools.modernize.sources.base import SourceConnector
from coded_tools.modernize.sources.base import SourceDocument

_DEFAULT_EXCLUDES = (
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "bin",
    "obj",
    "target",
    "build",
    "dist",
    ".idea",
    ".vscode",
)
_DOC_EXTENSIONS = (".md", ".txt", ".rst")
_MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB: skip binaries/generated blobs that slipped past the extension filter


class LocalConnector(SourceConnector):
    """
    config:
        root_path: str (required) - absolute or CWD-relative directory to scan
        include_globs: list[str] (optional) - only these glob patterns, if given
        exclude_globs: list[str] (optional) - in addition to _DEFAULT_EXCLUDES
    """

    type_name = "local"

    def _root(self) -> str:
        root = self.config.get("root_path")
        if not root:
            raise ValueError(f"Source '{self.source_id}': 'root_path' is required for a local source.")
        return os.path.abspath(root)

    def test_connection(self) -> ConnectionTestResult:
        try:
            root = self._root()
        except ValueError as e:
            return ConnectionTestResult(ok=False, message=str(e))
        if not os.path.isdir(root):
            return ConnectionTestResult(ok=False, message=f"Directory does not exist: {root}")
        if not os.access(root, os.R_OK):
            return ConnectionTestResult(ok=False, message=f"Directory is not readable: {root}")
        return ConnectionTestResult(ok=True, message=f"Found directory: {root}")

    def _extensions(self) -> set:
        exts = set(get_default_registry().supported_extensions())
        exts.update(_DOC_EXTENSIONS)
        return exts

    def _is_excluded(self, dirname: str) -> bool:
        excludes = set(_DEFAULT_EXCLUDES) | set(self.config.get("exclude_globs", []))
        return dirname in excludes or any(fnmatch.fnmatch(dirname, pat) for pat in excludes)

    def fetch(self, since_fingerprint: Optional[str] = None) -> Tuple[List[SourceDocument], str]:
        root = self._root()
        if not os.path.isdir(root):
            # os.walk() on a missing path silently yields nothing rather than
            # raising, which would otherwise make a typo'd or deleted
            # root_path look like a real, empty, successfully-scanned source.
            raise FileNotFoundError(f"Source '{self.source_id}': directory does not exist: {root}")
        extensions = self._extensions()
        include_globs = self.config.get("include_globs") or None

        documents: List[SourceDocument] = []
        fingerprint_parts: List[str] = []

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not self._is_excluded(d)]
            for filename in sorted(filenames):
                ext = os.path.splitext(filename)[1].lower()
                if ext not in extensions:
                    continue
                abs_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(abs_path, root).replace("\\", "/")
                if include_globs and not any(fnmatch.fnmatch(rel_path, g) for g in include_globs):
                    continue
                try:
                    stat = os.stat(abs_path)
                except OSError:
                    continue
                if stat.st_size > _MAX_FILE_BYTES:
                    continue
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except OSError:
                    continue

                documents.append(
                    SourceDocument(
                        path=rel_path,
                        content=content,
                        kind="doc" if ext in _DOC_EXTENSIONS else "file",
                        uri=f"file://{abs_path.replace(os.sep, '/')}",
                        metadata={"mtime": stat.st_mtime, "size": stat.st_size},
                    )
                )
                fingerprint_parts.append(f"{rel_path}:{stat.st_mtime}:{stat.st_size}")

        fingerprint = hashlib.sha256("\n".join(sorted(fingerprint_parts)).encode("utf-8")).hexdigest()
        return documents, fingerprint
