# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
MemoryManagerTool: CodedTool interface for Neuro SAN Studio.
Exposes the 5-tier memory fabric (Raw, Structural, Semantic, Procedural, Transformation).
"""

import json
import os
from typing import Any, Dict, List, Optional, Union
from neuro_san.interfaces.coded_tool import CodedTool

from coded_tools.modernize.memory.procedural_memory import ProceduralMemory
from coded_tools.modernize.memory.raw_memory import RawMemory
from coded_tools.modernize.memory.semantic_memory import SemanticMemory
from coded_tools.modernize.memory.structural_memory import StructuralMemory
from coded_tools.modernize.memory.transformation_memory import TransformationMemory


class MemoryFabric:
    """Unified container for all 5 tiers of the Knowledge Fabric."""

    def __init__(self):
        self.raw = RawMemory()
        self.structural = StructuralMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        self.transformation = TransformationMemory()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw.to_dict(),
            "structural": self.structural.to_dict(),
            "semantic": self.semantic.to_dict(),
            "procedural": self.procedural.to_dict(),
            "transformation": self.transformation.to_dict(),
        }


# Global memory instance for shared local access across agent calls
_GLOBAL_MEMORY = MemoryFabric()


def get_memory_fabric(sly_data: Optional[Dict[str, Any]] = None) -> MemoryFabric:
    global _GLOBAL_MEMORY
    if sly_data is not None and "memory_fabric" in sly_data:
        return sly_data["memory_fabric"]
    if sly_data is not None:
        sly_data["memory_fabric"] = _GLOBAL_MEMORY
    return _GLOBAL_MEMORY


class MemoryManagerTool(CodedTool):
    """
    CodedTool that provides multi-tier memory operations to the Memory Manager Agent.
    """

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        fabric = get_memory_fabric(sly_data)
        action = args.get("action", "status")

        if action == "ingest_repo":
            repo_path = args.get("repo_path", "data/insurance_claims_app")
            records = fabric.raw.ingest_directory(repo_path)
            # Ingest docs into semantic memory
            for rec in records:
                if rec.rel_path.endswith((".md", ".txt")):
                    content = rec.get_lines(1, rec.line_count)
                    # Break into sections
                    sections = content.split("\n\n")
                    curr_line = 1
                    for sec in sections:
                        sec_str = sec.strip()
                        if sec_str:
                            l_count = len(sec.splitlines())
                            fabric.semantic.add_chunk(
                                content=sec_str,
                                source_file=rec.rel_path,
                                start_line=curr_line,
                                end_line=curr_line + l_count,
                                chunk_type="doc",
                            )
                        curr_line += max(1, len(sec.splitlines()) + 1)
            fabric.semantic.build_index()
            return {
                "status": "success",
                "action": "ingest_repo",
                "files_ingested": len(records),
                "semantic_chunks": len(fabric.semantic.chunks),
                "files": [r.rel_path for r in records],
            }

        elif action == "semantic_search":
            query = args.get("query", "")
            top_k = int(args.get("top_k", 5))
            results = fabric.semantic.search(query, top_k=top_k)
            return {
                "status": "success",
                "action": "semantic_search",
                "query": query,
                "matches": results,
            }

        elif action == "get_evidence":
            rel_path = args.get("rel_path", "")
            start_line = int(args.get("start_line", 1))
            end_line = int(args.get("end_line", 10))
            snippet = fabric.raw.get_evidence(rel_path, start_line, end_line)
            return {
                "status": "success" if snippet is not None else "not_found",
                "rel_path": rel_path,
                "start_line": start_line,
                "end_line": end_line,
                "snippet": snippet,
            }

        elif action == "get_structural":
            category = args.get("category", "all")
            if category == "classes":
                return fabric.structural.classes
            elif category == "tables":
                return fabric.structural.tables
            elif category == "procedures":
                return fabric.structural.procedures
            return fabric.structural.to_dict()

        elif action == "get_transformation":
            component = args.get("component")
            if component:
                return fabric.transformation.get_component_scorecard(component) or {"error": "Not found"}
            return fabric.transformation.to_dict()

        elif action == "status":
            return {
                "raw_files_count": len(fabric.raw._files),
                "structural_classes": len(fabric.structural.classes),
                "structural_tables": len(fabric.structural.tables),
                "structural_procedures": len(fabric.structural.procedures),
                "semantic_chunks": len(fabric.semantic.chunks),
                "procedural_recipes": len(fabric.procedural.recipes),
                "transformation_metrics": len(fabric.transformation.metrics),
            }

        return {"error": f"Unknown memory action: {action}"}

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        return self.invoke(args, sly_data)
