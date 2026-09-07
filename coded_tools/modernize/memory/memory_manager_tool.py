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
from coded_tools.modernize.parsers.ddl_parser import DdlParser
from coded_tools.modernize.parsers.java_parser import JavaParser


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

    def _ensure_ingested(self, fabric: MemoryFabric, repo_path: str):
        """Ensures that repository artifacts are ingested into raw and semantic memory."""
        if len(fabric.raw._files) == 0:
            target = repo_path if repo_path and os.path.exists(repo_path) else "data/insurance_claims_app"
            if os.path.exists(target):
                records = fabric.raw.ingest_directory(target)
                for rec in records:
                    if rec.rel_path.endswith((".md", ".txt")):
                        content = rec.get_lines(1, rec.line_count)
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

    def _ensure_structural(self, fabric: MemoryFabric):
        """Ensures that deterministic AST symbols and tables are populated in structural memory."""
        if len(fabric.structural.classes) == 0:
            for p, rec in fabric.raw._files.items():
                if p.endswith(".java"):
                    parsed = JavaParser.parse_file(p, rec.get_lines(1, rec.line_count))
                    fabric.structural.register_class(
                        class_name=parsed["class_name"],
                        package=parsed["package"],
                        file_path=parsed["file_path"],
                        start_line=parsed["start_line"],
                        end_line=parsed["end_line"],
                        methods=parsed["methods"],
                        fields=parsed["fields"],
                        imports=parsed["imports"],
                    )
                elif p.endswith((".ddl", ".sql")):
                    content = rec.get_lines(1, rec.line_count)
                    ddl_res = DdlParser.parse_ddl(p, content)
                    for t in ddl_res.get("tables", []):
                        fabric.structural.register_table(
                            table_name=t.get("table_name", t.get("name", "UNKNOWN")),
                            columns=t["columns"],
                            primary_key=t["primary_key"],
                            foreign_keys=t["foreign_keys"],
                            file_path=t["file_path"],
                            start_line=t["start_line"],
                            end_line=t["end_line"],
                        )
                    sp_res = DdlParser.parse_stored_procedure(p, content)
                    for sp in sp_res.get("procedures", []):
                        fabric.structural.register_procedure(
                            proc_name=sp.get("procedure_name", sp.get("name", "UNKNOWN")),
                            parameters=sp["parameters"],
                            tables_read=sp["tables_read"],
                            tables_written=sp["tables_written"],
                            file_path=sp["file_path"],
                            start_line=sp["start_line"],
                            end_line=sp["end_line"],
                        )

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        fabric = get_memory_fabric(sly_data)
        action = args.get("action", "status")
        repo_path = args.get("repo_path") or "data/insurance_claims_app"

        # Auto-ingest if memory is currently empty
        self._ensure_ingested(fabric, repo_path)

        if action == "ingest_repo":
            records = fabric.raw.ingest_directory(repo_path if os.path.exists(repo_path) else "data/insurance_claims_app")
            # Ingest docs into semantic memory
            for rec in records:
                if rec.rel_path.endswith((".md", ".txt")):
                    content = rec.get_lines(1, rec.line_count)
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
            self._ensure_structural(fabric)
            return {
                "status": "success",
                "action": "ingest_repo",
                "files_ingested": len(records),
                "semantic_chunks": len(fabric.semantic.chunks),
                "files": [r.rel_path for r in records],
            }

        elif action in ("get_raw", "raw", "list_files", "get_files", "files"):
            raw_files = [r.rel_path for r in fabric.raw._files.values()]
            java_files = [f for f in raw_files if f.endswith(".java")]
            sql_files = [f for f in raw_files if f.endswith((".sql", ".ddl"))]
            doc_files = [f for f in raw_files if f.endswith((".md", ".txt"))]
            return {
                "status": "success",
                "action": action,
                "total_files_count": len(raw_files),
                "java_files_count": len(java_files),
                "java_files": java_files,
                "sql_files_count": len(sql_files),
                "sql_files": sql_files,
                "doc_files_count": len(doc_files),
                "doc_files": doc_files,
                "all_files": raw_files,
                "message": (
                    f"Raw memory contains {len(raw_files)} files ({len(java_files)} Java files: {', '.join(java_files)})."
                    if java_files
                    else f"Raw memory contains {len(raw_files)} files, no Java files found."
                ),
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
            snippet = fabric.raw.get_evidence(rel_path, start_line, end_line) if rel_path else None
            return {
                "status": "success" if snippet is not None else "not_found",
                "rel_path": rel_path,
                "start_line": start_line,
                "end_line": end_line,
                "snippet": snippet,
                "available_files": [r.rel_path for r in fabric.raw._files.values()],
            }

        elif action == "get_structural":
            self._ensure_structural(fabric)
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
            self._ensure_structural(fabric)
            raw_files = list(fabric.raw._files.keys())
            java_files = [f for f in raw_files if f.endswith(".java")]
            return {
                "raw_files_count": len(raw_files),
                "java_files_count": len(java_files),
                "java_files": java_files,
                "structural_classes": len(fabric.structural.classes),
                "structural_tables": len(fabric.structural.tables),
                "structural_procedures": len(fabric.structural.procedures),
                "semantic_chunks": len(fabric.semantic.chunks),
                "procedural_recipes": len(fabric.procedural.recipes),
                "transformation_metrics": len(fabric.transformation.metrics),
            }

        return {
            "error": f"Unknown memory action: {action}",
            "available_actions": ["ingest_repo", "get_raw", "list_files", "get_evidence", "get_structural", "semantic_search", "get_transformation", "status"],
            "raw_files_count": len(fabric.raw._files),
            "java_files_count": len([f for f in fabric.raw._files if f.endswith('.java')]),
            "java_files": [f for f in fabric.raw._files if f.endswith('.java')],
        }

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        return self.invoke(args, sly_data)
