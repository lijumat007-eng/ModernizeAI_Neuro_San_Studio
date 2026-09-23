# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
GraphStore: persists a KnowledgeGraphEngine so it survives a restart and
several projects can coexist. Kept behind an ABC so the backend can be
swapped for an embedded Kuzu store later without touching any caller - Kuzu
currently has no Windows wheel for this project's Python version (3.14), so
`SqliteGraphStore` is the default today. Nodes/edges are stored relationally
(not as one JSON blob) so a future backend swap, or direct SQL inspection,
doesn't require deserializing the whole graph first.
"""

import json
import os
import sqlite3
from abc import ABC, abstractmethod
from contextlib import closing
from typing import Any, Optional

from coded_tools.modernize.graph.graph_engine import KnowledgeGraphEngine


class GraphStore(ABC):
    @abstractmethod
    def exists(self, project_name: str) -> bool: ...

    @abstractmethod
    def save(self, project_name: str, kg: KnowledgeGraphEngine) -> None: ...

    @abstractmethod
    def load(self, project_name: str) -> KnowledgeGraphEngine: ...

    @abstractmethod
    def delete(self, project_name: str) -> None: ...


class SqliteGraphStore(GraphStore):
    """One SQLite file per project, at `<root_dir>/<project_name>/graph.sqlite3`."""

    def __init__(self, root_dir: str = "projects"):
        self.root_dir = root_dir

    def _db_path(self, project_name: str) -> str:
        return os.path.join(self.root_dir, project_name, "graph.sqlite3")

    def exists(self, project_name: str) -> bool:
        return os.path.exists(self._db_path(project_name))

    def _connect(self, project_name: str) -> sqlite3.Connection:
        path = self._db_path(project_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                properties TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                properties TEXT NOT NULL,
                PRIMARY KEY (source_id, target_id, edge_type)
            )
        """)
        return conn

    def save(self, project_name: str, kg: KnowledgeGraphEngine) -> None:
        with closing(self._connect(project_name)) as conn:
            with conn:
                conn.execute("DELETE FROM nodes")
                conn.execute("DELETE FROM edges")
                for node_id, attrs in kg.graph.nodes(data=True):
                    conn.execute(
                        "INSERT INTO nodes (node_id, node_type, properties) VALUES (?, ?, ?)",
                        (node_id, attrs.get("node_type", ""), json.dumps(attrs)),
                    )
                for u, v, key, attrs in kg.graph.edges(keys=True, data=True):
                    conn.execute(
                        "INSERT INTO edges (source_id, target_id, edge_type, properties) VALUES (?, ?, ?, ?)",
                        (u, v, key, json.dumps(attrs)),
                    )

    def load(self, project_name: str) -> KnowledgeGraphEngine:
        kg = KnowledgeGraphEngine()
        if not self.exists(project_name):
            return kg
        with closing(self._connect(project_name)) as conn:
            for node_id, node_type, properties in conn.execute("SELECT node_id, node_type, properties FROM nodes"):
                attrs = json.loads(properties)
                kg.graph.add_node(node_id, **attrs)
            for source_id, target_id, edge_type, properties in conn.execute(
                "SELECT source_id, target_id, edge_type, properties FROM edges"
            ):
                attrs = json.loads(properties)
                kg.graph.add_edge(source_id, target_id, key=edge_type, **attrs)
        return kg

    def delete(self, project_name: str) -> None:
        path = self._db_path(project_name)
        if os.path.exists(path):
            os.remove(path)


_DEFAULT_STORE: Optional[GraphStore] = None


def get_default_store() -> GraphStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = SqliteGraphStore()
    return _DEFAULT_STORE
