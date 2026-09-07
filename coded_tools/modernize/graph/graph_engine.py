# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Knowledge Graph Engine: Schema-enforced NetworkX MultiDiGraph manager.
Maintains nodes, edges, and strict 80/20 evidence metadata.
"""

import json
import os
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx


class KnowledgeGraphEngine:
    """
    Schema-enforced Property Graph engine backed by NetworkX MultiDiGraph.
    """

    NODE_TYPES = {
        "Application",
        "Service",
        "Module",
        "APIEndpoint",
        "DatabaseTable",
        "Column",
        "StoredProcedure",
        "BusinessRule",
        "RequirementDocument",
        "SMEInsight",
        "Risk",
    }

    EDGE_TYPES = {
        "CALLS",
        "DEPENDS_ON",
        "READS_FROM",
        "WRITES_TO",
        "IMPLEMENTS_RULE",
        "DEFINED_IN",
        "IMPACTS",
        "VALIDATES",
    }

    def __init__(self):
        self.graph = nx.MultiDiGraph()

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        source_file: str = "",
        line_start: int = 1,
        line_end: int = 1,
        confidence: float = 1.0,
        extractor: str = "deterministic",
        evidence_snippet: str = "",
    ) -> str:
        """Adds a node with schema validation and evidence metadata."""
        if node_type not in self.NODE_TYPES:
            raise ValueError(f"Invalid node_type: {node_type}. Must be in {self.NODE_TYPES}")

        props = properties or {}
        props.update({
            "node_type": node_type,
            "label": label or node_id,
            "source_file": source_file.replace("\\", "/"),
            "line_start": line_start,
            "line_end": line_end,
            "confidence": confidence,
            "extractor": extractor,
            "evidence_snippet": evidence_snippet,
        })
        self.graph.add_node(node_id, **props)
        return node_id

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None,
        source_file: str = "",
        line_start: int = 1,
        line_end: int = 1,
        confidence: float = 1.0,
        extractor: str = "deterministic",
        evidence_snippet: str = "",
    ):
        """Adds a directed edge with schema validation and evidence metadata."""
        if edge_type not in self.EDGE_TYPES:
            raise ValueError(f"Invalid edge_type: {edge_type}. Must be in {self.EDGE_TYPES}")

        if not self.graph.has_node(source_id):
            raise KeyError(f"Source node '{source_id}' does not exist in graph.")
        if not self.graph.has_node(target_id):
            raise KeyError(f"Target node '{target_id}' does not exist in graph.")

        props = properties or {}
        props.update({
            "edge_type": edge_type,
            "source_file": source_file.replace("\\", "/"),
            "line_start": line_start,
            "line_end": line_end,
            "confidence": confidence,
            "extractor": extractor,
            "evidence_snippet": evidence_snippet,
        })
        self.graph.add_edge(source_id, target_id, key=edge_type, **props)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        if self.graph.has_node(node_id):
            return dict(self.graph.nodes[node_id])
        return None

    def get_neighbors(self, node_id: str, direction: str = "both") -> List[Dict[str, Any]]:
        """Returns neighboring nodes and connected edges."""
        if not self.graph.has_node(node_id):
            return []

        neighbors = []
        if direction in ("out", "both"):
            for _, target, key, data in self.graph.out_edges(node_id, keys=True, data=True):
                neighbors.append({
                    "direction": "out",
                    "edge_type": key,
                    "target_id": target,
                    "target_data": dict(self.graph.nodes[target]),
                    "edge_data": data,
                })
        if direction in ("in", "both"):
            for source, _, key, data in self.graph.in_edges(node_id, keys=True, data=True):
                neighbors.append({
                    "direction": "in",
                    "edge_type": key,
                    "source_id": source,
                    "source_data": dict(self.graph.nodes[source]),
                    "edge_data": data,
                })
        return neighbors

    def to_json_dict(self) -> Dict[str, Any]:
        """Serializes the graph into a standard JSON structure."""
        nodes = []
        for n_id, attrs in self.graph.nodes(data=True):
            node_data = {"id": n_id}
            node_data.update(attrs)
            nodes.append(node_data)

        edges = []
        for u, v, k, attrs in self.graph.edges(keys=True, data=True):
            edge_data = {"source": u, "target": v, "key": k}
            edge_data.update(attrs)
            edges.append(edge_data)

        return {
            "summary": {
                "total_nodes": self.graph.number_of_nodes(),
                "total_edges": self.graph.number_of_edges(),
            },
            "nodes": nodes,
            "edges": edges,
        }

    def export_json(self, output_path: str):
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_json_dict(), f, indent=2)

    def export_graphml(self, output_path: str):
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        # Create a copy with stringified dictionary properties for GraphML compatibility
        g_copy = nx.MultiDiGraph()
        for n, d in self.graph.nodes(data=True):
            clean_d = {k: (str(v) if isinstance(v, (dict, list)) else v) for k, v in d.items()}
            g_copy.add_node(n, **clean_d)
        for u, v, k, d in self.graph.edges(keys=True, data=True):
            clean_d = {k_: (str(v_) if isinstance(v_, (dict, list)) else v_) for k_, v_ in d.items()}
            g_copy.add_edge(u, v, key=k, **clean_d)
        nx.write_graphml(g_copy, output_path)

    def load_json(self, input_path: str):
        """Loads a graph from a previously exported JSON file."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Knowledge graph JSON file not found at {input_path}")
        
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.graph.clear()
        
        for n in data.get("nodes", []):
            n_copy = n.copy()
            node_id = n_copy.pop("id")
            self.graph.add_node(node_id, **n_copy)
            
        for e in data.get("edges", []):
            e_copy = e.copy()
            u = e_copy.pop("source")
            v = e_copy.pop("target")
            k = e_copy.pop("key", None)
            self.graph.add_edge(u, v, key=k, **e_copy)

