# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Tier 1: Raw Memory Engine.
Manages ingested source code and documents with SHA-256 integrity and line-offset indexing.

Source-qualified since the multi-source fabric: a record optionally carries
`source_id` (which Source it came from), `source_type`, and `uri` (a
clickable link back to the Git blob, DB object, or wiki page). When a record
has a `source_id`, its storage key becomes `"<source_id>::<rel_path>"` so two
sources with a same-named file (or a live DB and a repo that mirrors it)
never collide. Every pre-existing single-source caller (`ingest_file`,
`ingest_directory` with no `source_id`) is unaffected: its records still key
by bare `rel_path`, exactly as before.
"""

import hashlib
import os
from typing import Any
from typing import Dict
from typing import List
from typing import Optional


class RawFileRecord:
    """Represents an ingested raw file with hash and line tracking."""

    def __init__(
        self,
        rel_path: str,
        abs_path: str,
        content: str,
        source_id: str = "",
        source_type: str = "",
        uri: str = "",
    ):
        self.rel_path: str = rel_path.replace("\\", "/")
        self.abs_path: str = abs_path.replace("\\", "/")
        self.source_id: str = source_id
        self.source_type: str = source_type
        self.uri: str = uri
        self.sha256: str = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.lines: List[str] = content.splitlines()
        self.line_count: int = len(self.lines)
        self.byte_size: int = len(content.encode("utf-8"))

    @property
    def key(self) -> str:
        """Storage key in RawMemory._files: source-qualified when a source_id is set."""
        return f"{self.source_id}::{self.rel_path}" if self.source_id else self.rel_path

    def get_lines(self, start_line: int, end_line: int) -> str:
        """
        Returns line snippet (1-indexed, inclusive).
        """
        if start_line < 1:
            start_line = 1
        if end_line > self.line_count:
            end_line = self.line_count
        return "\n".join(self.lines[start_line - 1 : end_line])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rel_path": self.rel_path,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "uri": self.uri,
            "sha256": self.sha256,
            "line_count": self.line_count,
            "byte_size": self.byte_size,
        }


class RawMemory:
    """
    Tier 1 Raw Memory Catalog maintaining complete provenance.
    """

    def __init__(self):
        self._files: Dict[str, RawFileRecord] = {}

    def ingest_file(
        self,
        rel_path: str,
        abs_path: str,
        content: str,
        source_id: str = "",
        source_type: str = "",
        uri: str = "",
    ) -> RawFileRecord:
        record = RawFileRecord(rel_path, abs_path, content, source_id=source_id, source_type=source_type, uri=uri)
        self._files[record.key] = record
        return record

    def ingest_document(self, source_id: str, source_type: str, doc: "Any") -> RawFileRecord:
        """Ingests one `sources.base.SourceDocument` under a source-qualified key.
        Used by the multi-source project scanner; `ingest_file`/`ingest_directory`
        remain the single-source entry points used by every existing tool."""
        return self.ingest_file(
            rel_path=doc.path,
            abs_path=doc.uri or doc.path,
            content=doc.content,
            source_id=source_id,
            source_type=source_type,
            uri=doc.uri,
        )

    def ingest_directory(self, root_dir: str, extensions: Optional[List[str]] = None) -> List[RawFileRecord]:
        """Ingests all matching files from a directory (single-source, unqualified keys)."""
        if extensions is None:
            extensions = [".java", ".sql", ".ddl", ".md", ".txt", ".json", ".xml", ".properties"]

        ingested = []
        root_abs = os.path.abspath(root_dir)
        for root, _, files in os.walk(root_abs):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, root_abs)
                    try:
                        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                        record = self.ingest_file(rel_path, abs_path, content)
                        ingested.append(record)
                    except Exception as e:
                        print(f"Failed to read {abs_path}: {e}")
        return ingested

    def get(self, rel_path: str, source_id: str = "") -> Optional[RawFileRecord]:
        norm = rel_path.replace("\\", "/")
        key = f"{source_id}::{norm}" if source_id else norm
        found = self._files.get(key)
        if found is not None or source_id:
            return found
        # No source_id given and no exact bare-key match: fall back to a
        # suffix match across source-qualified keys, so callers that only
        # know a bare path (existing single-source tools, provenance lookups
        # by basename) still work once records carry a source prefix.
        for k, rec in self._files.items():
            if k == norm or k.endswith("::" + norm):
                return rec
        return None

    def get_evidence(self, rel_path: str, start_line: int, end_line: int) -> Optional[str]:
        record = self.get(rel_path)
        if record:
            return record.get_lines(start_line, end_line)
        return None

    def list_files(self) -> List[Dict[str, Any]]:
        return [rec.to_dict() for rec in self._files.values()]

    def to_dict(self) -> Dict[str, Any]:
        return {key: rec.to_dict() for key, rec in self._files.items()}
