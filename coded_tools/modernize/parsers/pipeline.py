# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
parse_repository(): the single entry point that turns everything sitting in
Tier 1 Raw Memory into linked IR and loads it into Tier 2 Structural Memory.
Replaces the old pattern of every CodedTool calling JavaParser/DdlParser
directly and re-implementing ingestion/registration itself.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from coded_tools.modernize.parsers.ir import ParseResult
from coded_tools.modernize.parsers.linker import Linker
from coded_tools.modernize.parsers.registry import ParserRegistry, get_default_registry


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

    for path, rec in fabric.raw._files.items():
        report.files_seen += 1
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
        for ref in result.references:
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
