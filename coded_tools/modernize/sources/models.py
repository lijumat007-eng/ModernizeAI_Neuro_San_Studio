# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Project & Source model: a Project groups many Sources (Git repos, DBs, SSH
hosts, wikis, local folders); each Source is scanned independently and its
documents are merged into one Knowledge Fabric.

Persisted as plain JSON under `projects/<name>/project.json`. Never contains
a secret: `credential_ref` is only the *name* of an environment variable (or
variable prefix), resolved at connect time by `sources/base.py`.
"""

import dataclasses
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

_PROJECTS_ROOT_DEFAULT = "projects"
_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _validate_name(name: str, what: str) -> None:
    if not name or not _NAME_RE.match(name):
        raise ValueError(f"Invalid {what} '{name}': use only letters, digits, '.', '_', '-'.")


@dataclasses.dataclass
class Source:
    """One ingestible source within a Project."""

    source_id: str
    type: str  # "local" | "git" | "s3" | "database" | "ssh" | "confluence"
    config: Dict[str, Any] = dataclasses.field(default_factory=dict)
    credential_ref: Optional[str] = None  # env var NAME (or prefix); never a secret value
    db_alias: Optional[str] = None  # canonical alias used to unify cross-source table/procedure identity
    last_fingerprint: Optional[str] = None
    last_scanned_at: Optional[float] = None
    last_scan_status: Optional[str] = None  # "success" | "error" | None (never scanned)
    last_scan_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Source":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclasses.dataclass
class Project:
    """A named collection of Sources whose documents are merged into one fabric."""

    name: str
    sources: List[Source] = dataclasses.field(default_factory=list)
    created_at: float = dataclasses.field(default_factory=time.time)
    llm_assist_enabled: bool = False  # per-project switch for the optional AI layer

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "sources": [s.to_dict() for s in self.sources],
            "created_at": self.created_at,
            "llm_assist_enabled": self.llm_assist_enabled,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Project":
        return cls(
            name=d["name"],
            sources=[Source.from_dict(s) for s in d.get("sources", [])],
            created_at=d.get("created_at", time.time()),
            llm_assist_enabled=d.get("llm_assist_enabled", False),
        )

    def get_source(self, source_id: str) -> Optional[Source]:
        return next((s for s in self.sources if s.source_id == source_id), None)

    def add_source(self, source: Source) -> None:
        if self.get_source(source.source_id):
            raise ValueError(f"Source '{source.source_id}' already exists in project '{self.name}'.")
        _validate_name(source.source_id, "source_id")
        self.sources.append(source)

    def remove_source(self, source_id: str) -> bool:
        before = len(self.sources)
        self.sources = [s for s in self.sources if s.source_id != source_id]
        return len(self.sources) != before


class ProjectStore:
    """Reads and writes Project JSON files under a root directory (default: `projects/`)."""

    def __init__(self, root_dir: str = _PROJECTS_ROOT_DEFAULT):
        self.root_dir = root_dir

    def _project_path(self, name: str) -> str:
        _validate_name(name, "project name")
        return os.path.join(self.root_dir, name, "project.json")

    def project_dir(self, name: str) -> str:
        _validate_name(name, "project name")
        return os.path.join(self.root_dir, name)

    def exists(self, name: str) -> bool:
        return os.path.exists(self._project_path(name))

    def list_projects(self) -> List[str]:
        if not os.path.isdir(self.root_dir):
            return []
        return sorted(
            d for d in os.listdir(self.root_dir)
            if os.path.exists(os.path.join(self.root_dir, d, "project.json"))
        )

    def load(self, name: str) -> Project:
        path = self._project_path(name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Project '{name}' not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            return Project.from_dict(json.load(f))

    def save(self, project: Project) -> None:
        path = self._project_path(project.name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(project.to_dict(), f, indent=2)
        os.replace(tmp_path, path)

    def create(self, name: str) -> Project:
        if self.exists(name):
            raise ValueError(f"Project '{name}' already exists.")
        project = Project(name=name)
        self.save(project)
        return project

    def delete(self, name: str) -> None:
        import shutil

        d = self.project_dir(name)
        if os.path.exists(d):
            shutil.rmtree(d)
