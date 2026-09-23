# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
parse_repository(): the single entry point that turns everything sitting in
Tier 1 Raw Memory into linked IR and loads it into Tier 2 Structural Memory.
Replaces the old pattern of every CodedTool calling JavaParser/DdlParser
directly and re-implementing ingestion/registration itself.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from coded_tools.modernize.parsers.ir import ParseResult, Reference
from coded_tools.modernize.parsers.linker import Linker
from coded_tools.modernize.parsers.registry import ParserRegistry, get_default_registry

_SQL_VERB_TO_EDGE_KIND = {
    "SELECT": "READS_FROM",
    "INSERT": "WRITES_TO",
    "UPDATE": "WRITES_TO",
    "DELETE": "WRITES_TO",
    "MERGE": "WRITES_TO",
    "CALL": "EXECUTES",
    "EXEC": "EXECUTES",
    "EXECUTE": "EXECUTES",
}


def _sql_accesses_to_references(result: ParseResult) -> List[Reference]:
    """Embedded SQL found inside host-language code (Java/C#/C/C++ string
    literals) only ever produces a SqlAccess, never a Reference - unlike a
    native .sql file's own procedure body, which the SQL parser already turns
    into References directly. This bridges the two so GraphBuilder sees table
    lineage the same way regardless of which language it came from."""
    derived = []
    for access in result.sql_accesses:
        edge_kind = _SQL_VERB_TO_EDGE_KIND.get(access.verb)
        if edge_kind is None or not access.owner_symbol:
            continue
        for table in access.tables:
            derived.append(Reference(
                from_symbol=access.owner_symbol, target_name=table, kind=edge_kind,
                file_path=access.file_path, line=access.line, evidence=access.snippet,
                confidence=access.confidence, resolved_target=table,  # a bare table name IS its own canonical id
            ))
    return derived


@dataclass
class ParseReport:
    """Summary of one parse_repository() run, for diagnostics and the benchmark script."""

    files_seen: int = 0
    files_parsed: int = 0
    files_unsupported: List[str] = field(default_factory=list)
    by_language: Dict[str, int] = field(default_factory=dict)
    total_symbols: int = 0
    total_references: int = 0
    resolved_references: int = 0
    external_references: int = 0
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    results: List[ParseResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "files_seen": self.files_seen,
            "files_parsed": self.files_parsed,
            "files_unsupported": self.files_unsupported,
            "by_language": self.by_language,
            "total_symbols": self.total_symbols,
            "total_references": self.total_references,
            "resolved_references": self.resolved_references,
            "external_references": self.external_references,
            "resolution_rate": round(self.resolved_references / self.total_references, 4)
            if self.total_references else 1.0,
            "diagnostics": self.diagnostics,
        }


def parse_repository(fabric, registry: ParserRegistry = None) -> ParseReport:
    """
    Parses every file in `fabric.raw` with the appropriate LanguageParser,
    links the results across files, and registers everything into
    `fabric.structural`. Returns a ParseReport summarizing the run.
    """
    registry = registry or get_default_registry()
    report = ParseReport()
    results: List[ParseResult] = []

    for rec in fabric.raw._files.values():
        report.files_seen += 1
        # Use the record's own clean rel_path, not the RawMemory dict key: a
        # source-qualified record's key is "<source_id>::<rel_path>" (see
        # raw_memory.py), and using that compound key as the file path would
        # leak into every Symbol/Reference's file_path/source_file provenance.
        path = rec.rel_path
        content = rec.get_lines(1, rec.line_count)
        result = registry.parse_file(path, content)
        if result is None:
            report.files_unsupported.append(path)
            continue

        report.files_parsed += 1
        report.by_language[result.language] = report.by_language.get(result.language, 0) + 1
        results.append(result)
        for diag in result.diagnostics:
            report.diagnostics.append(diag.to_dict())

    Linker().link(results)

    for result in results:
        for symbol in result.symbols:
            fabric.structural.register_symbol(symbol.to_dict())
        for endpoint in result.endpoints:
            fabric.structural.register_ir_endpoint(endpoint.to_dict())

        all_refs = list(result.references) + _sql_accesses_to_references(result)
        for ref in all_refs:
            fabric.structural.register_reference(ref.to_dict())
            if ref.kind == "IMPORTS":
                continue  # a statement of intent, not a resolvable link target
            report.total_references += 1
            if ref.resolved_target:
                report.resolved_references += 1
            if ref.external:
                report.external_references += 1
        report.total_symbols += len(result.symbols)

    report.results = results
    return report
