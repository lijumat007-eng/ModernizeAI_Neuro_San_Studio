# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
CodedTools for Intel Agents:
- CodeIntelTool (Java/SQL AST parser)
- DatabaseIntelTool (DDL and Stored Procedure parser)
- DocIntelTool (Markdown and SME document chunker)
"""

import os
from typing import Any, Dict, List
from neuro_san.interfaces.coded_tool import CodedTool

from coded_tools.modernize.memory.memory_manager_tool import get_memory_fabric
from coded_tools.modernize.parsers.ddl_parser import DdlParser
from coded_tools.modernize.parsers.doc_parser import DocParser
from coded_tools.modernize.parsers.java_parser import JavaParser


class CodeIntelTool(CodedTool):
    """Parses legacy Java and SQL source files deterministically."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        fabric = get_memory_fabric(sly_data)
        file_path = args.get("file_path", "")
        repo_path = args.get("repo_path", "data/insurance_claims_app")

        # Ingest if memory is empty
        if len(fabric.raw._files) == 0:
            fabric.raw.ingest_directory(repo_path)

        parsed_classes = []
        if file_path:
            rec = fabric.raw.get(file_path)
            if rec:
                parsed = JavaParser.parse_file(rec.rel_path, rec.get_lines(1, rec.line_count))
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
                parsed_classes.append(parsed)
        else:
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
                    parsed_classes.append(parsed)

        return {
            "status": "success",
            "agent": "code_intel",
            "parsed_classes_count": len(parsed_classes),
            "classes": parsed_classes,
        }

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        return self.invoke(args, sly_data)


class DatabaseIntelTool(CodedTool):
    """Parses database DDL schemas and stored procedures deterministically."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        fabric = get_memory_fabric(sly_data)
        repo_path = args.get("repo_path", "data/insurance_claims_app")

        if len(fabric.raw._files) == 0:
            fabric.raw.ingest_directory(repo_path)

        parsed_tables = []
        parsed_procedures = []

        for p, rec in fabric.raw._files.items():
            if p.endswith(".ddl") or p.endswith(".sql"):
                content = rec.get_lines(1, rec.line_count)
                if "CREATE TABLE" in content.upper():
                    ddl = DdlParser.parse_ddl(p, content)
                    for t in ddl["tables"]:
                        fabric.structural.register_table(
                            table_name=t["table_name"],
                            columns=t["columns"],
                            primary_key=t["primary_key"],
                            foreign_keys=t["foreign_keys"],
                            file_path=t["file_path"],
                            start_line=t["start_line"],
                            end_line=t["end_line"],
                        )
                        parsed_tables.append(t)
                if "PROCEDURE" in content.upper():
                    sp = DdlParser.parse_stored_procedure(p, content)
                    for proc in sp["procedures"]:
                        fabric.structural.register_procedure(
                            proc_name=proc["procedure_name"],
                            parameters=proc["parameters"],
                            tables_read=proc["tables_read"],
                            tables_written=proc["tables_written"],
                            file_path=proc["file_path"],
                            start_line=proc["start_line"],
                            end_line=proc["end_line"],
                        )
                        parsed_procedures.append(proc)

        return {
            "status": "success",
            "agent": "database_intel",
            "tables_count": len(parsed_tables),
            "procedures_count": len(parsed_procedures),
            "tables": parsed_tables,
            "procedures": parsed_procedures,
        }

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        return self.invoke(args, sly_data)


class DocIntelTool(CodedTool):
    """Parses documentation and SME notes into structured semantic chunks."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        fabric = get_memory_fabric(sly_data)
        repo_path = args.get("repo_path", "data/insurance_claims_app")

        if len(fabric.raw._files) == 0:
            fabric.raw.ingest_directory(repo_path)

        parsed_docs = []
        for p, rec in fabric.raw._files.items():
            if p.endswith((".md", ".txt")):
                content = rec.get_lines(1, rec.line_count)
                doc_info = DocParser.parse_document(p, content)
                parsed_docs.append(doc_info)

        return {
            "status": "success",
            "agent": "doc_intel",
            "docs_count": len(parsed_docs),
            "documents": parsed_docs,
        }

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        return self.invoke(args, sly_data)
