# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Backward-compatible shim over the real SQL/PL-SQL parser
(coded_tools.modernize.parsers.lang.sql.SqlParser).

Existing callers (RulesExtractor, KnowledgeGraphTool, MemoryManagerTool, the
test suite) call `DdlParser.parse_ddl(path, content)` and
`DdlParser.parse_stored_procedure(path, content)` and expect the old flat
dict shapes. The new parser is IR-based, dialect-aware (Oracle/T-SQL/Postgres/
ANSI), and understands procedure/function/trigger/package bodies, so this
shim flattens its output back into the legacy shape.

New code should prefer `coded_tools.modernize.parsers.pipeline.parse_repository`
and the richer IR directly; this module exists only to avoid a breaking
rewrite of every call site in one step.
"""

import re
from typing import Any
from typing import Dict
from typing import List

from coded_tools.modernize.parsers.lang.sql import SqlParser as _SqlParser

_PARSER = _SqlParser()
_FK_EVIDENCE_RE = re.compile(r"FOREIGN\s+KEY\s*\(([^)]*)\)\s*REFERENCES\s+\S+\s*\(([^)]*)\)", re.IGNORECASE)


class DdlParser:
    """Legacy-shaped facade over the tree-and-sqlglot-backed SQL parser."""

    @staticmethod
    def parse_ddl(file_path: str, content: str) -> Dict[str, Any]:
        result = _PARSER.parse(file_path, content)

        table_symbols = [s for s in result.symbols if s.kind == "TABLE" and not s.properties.get("is_index")]
        column_symbols = [s for s in result.symbols if s.kind == "COLUMN"]
        fk_refs = [r for r in result.references if r.kind == "READS_FROM" and "FOREIGN KEY" in r.evidence.upper()]

        tables = []
        for t in table_symbols:
            pk = t.properties.get("primary_key")
            columns = [
                {"name": c.name, "type": c.return_type, "is_primary": c.name == pk}
                for c in column_symbols
                if c.parent == t.qualified_name
            ]
            foreign_keys = []
            for ref in fk_refs:
                if ref.from_symbol != t.qualified_name:
                    continue
                m = _FK_EVIDENCE_RE.search(ref.evidence)
                foreign_keys.append(
                    {
                        "constraint_name": "",
                        "column": m.group(1).strip().lower() if m else "",
                        "target_table": ref.target_name,
                        "target_column": m.group(2).strip().lower() if m else "",
                    }
                )
            tables.append(
                {
                    "table_name": t.qualified_name,
                    "columns": columns,
                    "primary_key": pk,
                    "foreign_keys": foreign_keys,
                    "file_path": t.file_path,
                    "start_line": t.line_start,
                    "end_line": t.line_end,
                }
            )

        return {"tables": tables}

    @staticmethod
    def parse_stored_procedure(file_path: str, content: str) -> Dict[str, Any]:
        result = _PARSER.parse(file_path, content)

        proc_symbols = [s for s in result.symbols if s.kind == "PROCEDURE" and not s.properties.get("package")]
        procedures = []
        for s in proc_symbols:
            reads = sorted(
                {
                    r.target_name
                    for r in result.references
                    if r.from_symbol == s.qualified_name and r.kind == "READS_FROM"
                }
            )
            writes = sorted(
                {
                    r.target_name
                    for r in result.references
                    if r.from_symbol == s.qualified_name and r.kind == "WRITES_TO"
                }
            )
            param_names = _param_names_from_signature(s.signature)
            procedures.append(
                {
                    "procedure_name": s.name,
                    "parameters": [{"name": p, "mode": "IN", "type": "VARCHAR"} for p in param_names],
                    "tables_read": reads,
                    "tables_written": writes,
                    "file_path": s.file_path,
                    "start_line": s.line_start,
                    "end_line": s.line_end,
                }
            )

        return {"procedures": procedures}


def _param_names_from_signature(signature: str) -> List[str]:
    m = re.search(r"\((.*)\)", signature)
    if not m or not m.group(1).strip():
        return []
    return [p.strip() for p in m.group(1).split(",") if p.strip()]
