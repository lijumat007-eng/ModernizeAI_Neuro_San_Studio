# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Tier 1: Raw Memory Engine.
Manages ingested source code and documents with SHA-256 integrity and line-offset indexing.
"""

import hashlib
import os
from typing import Dict, List, Optional, Tuple


class RawFileRecord:
    """Represents an ingested raw file with hash and line tracking."""

    def __init__(self, rel_path: str, abs_path: str, content: str):
        self.rel_path: str = rel_path.replace("\\", "/")
        self.abs_path: str = abs_path.replace("\\", "/")
        self.sha256: str = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.lines: List[str] = content.splitlines()
        self.line_count: int = len(self.lines)
        self.byte_size: int = len(content.encode("utf-8"))

    def get_lines(self, start_line: int, end_line: int) -> str:
        """
        Returns line snippet (1-indexed, inclusive).
        """
        if start_line < 1:
            start_line = 1
        if end_line > self.line_count:
            end_line = self.line_count
        return "\n".join(self.lines[start_line - 1 : end_line])

    def to_dict(self) -> Dict[str, any]:
        return {
            "rel_path": self.rel_path,
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

    def ingest_file(self, rel_path: str, abs_path: str, content: str) -> RawFileRecord:
        record = RawFileRecord(rel_path, abs_path, content)
        self._files[record.rel_path] = record
        return record

    def ingest_directory(self, root_dir: str, extensions: Optional[List[str]] = None) -> List[RawFileRecord]:
        """Ingests all matching files from a directory."""
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

    def get(self, rel_path: str) -> Optional[RawFileRecord]:
        norm = rel_path.replace("\\", "/")
        return self._files.get(norm)

    def get_evidence(self, rel_path: str, start_line: int, end_line: int) -> Optional[str]:
        record = self.get(rel_path)
        if record:
            return record.get_lines(start_line, end_line)
        return None

    def list_files(self) -> List[Dict[str, any]]:
        return [rec.to_dict() for rec in self._files.values()]

    def to_dict(self) -> Dict[str, any]:
        return {path: rec.to_dict() for path, rec in self._files.items()}
