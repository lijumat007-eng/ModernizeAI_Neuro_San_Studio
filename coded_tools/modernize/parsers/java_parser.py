# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Backward-compatible shim over the real tree-sitter Java parser
(coded_tools.modernize.parsers.lang.java.JavaParser).

Existing callers (RulesExtractor, KnowledgeGraphTool, MemoryManagerTool, the
test suite) call `JavaParser.parse_file(path, content)` and expect a single
flat dict describing "the" class in the file. The new parser is IR-based and
handles multiple/nested top-level types per file, so this shim picks the
first top-level type as "the class" (matching the old regex parser's
behavior) and flattens the IR back into the legacy shape.

New code should prefer `coded_tools.modernize.parsers.pipeline.parse_repository`
and the richer IR directly; this module exists only to avoid a breaking
rewrite of every call site in one step.
"""

import os
from typing import Any, Dict

from coded_tools.modernize.parsers.lang.java import JavaParser as _TreeSitterJavaParser

_PARSER = _TreeSitterJavaParser()


class JavaParser:
    """Legacy-shaped facade over the tree-sitter-backed Java parser."""

    @staticmethod
    def parse_file(file_path: str, content: str) -> Dict[str, Any]:
        result = _PARSER.parse(file_path, content)
        rel_path = file_path.replace("\\", "/")

        top_level = [s for s in result.symbols if s.parent is None and s.kind in ("CLASS", "INTERFACE", "ENUM", "RECORD")]
        package = top_level[0].qualified_name.rsplit("." + top_level[0].name, 1)[0] if top_level and "." in top_level[0].qualified_name else ""
        main_class = top_level[0] if top_level else None
        class_name = main_class.name if main_class else os.path.basename(file_path).replace(".java", "")
        class_qname = main_class.qualified_name if main_class else class_name

        imports = [r.target_name for r in result.references if r.kind == "IMPORTS"]

        fields = [
            {"name": s.name, "type": s.return_type, "line": s.line_start}
            for s in result.symbols
            if s.kind == "FIELD" and s.parent == class_qname
        ]
        methods = [
            {
                "name": s.name,
                "return_type": s.return_type,
                "parameters": s.signature.split("(", 1)[-1].rstrip(")") if s.signature else "",
                "line": s.line_start,
            }
            for s in result.symbols
            if s.kind == "METHOD" and s.parent == class_qname
        ]
        sql_statements = [
            {
                "verb": sql.verb,
                "table": sql.tables[0] if sql.tables else "UNKNOWN",
                "tables": sql.tables,
                "sql": sql.snippet,
                "line": sql.line,
            }
            for sql in result.sql_accesses
        ]
        service_calls = [
            {
                "target_service": ref.target_name,
                "call_type": "INSTANTIATION" if ref.kind == "INSTANTIATES" else "INVOCATION",
                "line": ref.line,
            }
            for ref in result.references
            if ref.kind in ("CALLS", "INSTANTIATES")
        ]

        return {
            "class_name": class_name,
            "package": package,
            "file_path": rel_path,
            "start_line": main_class.line_start if main_class else 1,
            "end_line": main_class.line_end if main_class else len(content.splitlines()),
            "imports": imports,
            "fields": fields,
            "methods": methods,
            "sql_statements": sql_statements,
            "service_calls": service_calls,
            "parse_coverage": result.parse_coverage,
            "diagnostics": [d.to_dict() for d in result.diagnostics],
        }
