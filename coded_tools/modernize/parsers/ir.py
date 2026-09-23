# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Common Intermediate Representation (IR) for all language parsers.
Every LanguageParser (Java, C#, C/C++, SQL, COBOL, JCL) returns a ParseResult
built from these dataclasses, so the rest of the fabric (StructuralMemory,
GraphBuilder, RulesExtractor) only has to know one shape regardless of the
source language.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Symbol kinds shared across all languages. Not every language uses every kind
# (COBOL has no CLASS, Java has no PROGRAM), but the vocabulary is shared so
# downstream code does not need per-language branching.
SYMBOL_KINDS = {
    "CLASS", "INTERFACE", "STRUCT", "ENUM", "RECORD",
    "METHOD", "FUNCTION", "PARAGRAPH", "FIELD", "PROPERTY",
    "NAMESPACE", "PACKAGE", "PROGRAM", "COPYBOOK", "JOB", "JOBSTEP",
    "TABLE", "VIEW", "PROCEDURE", "TRIGGER", "COLUMN",
}

REFERENCE_KINDS = {
    "CALLS", "INSTANTIATES", "INHERITS", "IMPLEMENTS",
    "IMPORTS", "INCLUDES", "READS_FROM", "WRITES_TO", "EXECUTES", "PERFORMS",
}


@dataclass
class Symbol:
    """A named, line-addressable unit of code: a class, method, program, table, etc."""

    kind: str
    name: str
    qualified_name: str
    language: str
    file_path: str
    line_start: int
    line_end: int
    parent: Optional[str] = None  # qualified_name of enclosing symbol, if any
    modifiers: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)  # @Annotation / [Attribute]
    signature: str = ""
    return_type: str = ""
    base_types: List[str] = field(default_factory=list)  # extends/implements/inherits
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "language": self.language,
            "file_path": self.file_path.replace("\\", "/"),
            "line_start": self.line_start,
            "line_end": self.line_end,
            "parent": self.parent,
            "modifiers": self.modifiers,
            "annotations": self.annotations,
            "signature": self.signature,
            "return_type": self.return_type,
            "base_types": self.base_types,
            "properties": self.properties,
        }


@dataclass
class Reference:
    """A directed relationship from one symbol to another named target.

    `target_name` starts out as the raw name seen in source (e.g. "gateway.charge",
    receiver type "PaymentGateway"); the Linker resolves it to a qualified_name
    and records how confident that resolution is.
    """

    from_symbol: str  # qualified_name of the symbol containing this reference
    target_name: str  # raw name as seen in source, pre-resolution
    kind: str
    file_path: str
    line: int
    evidence: str = ""
    confidence: float = 1.0
    resolved_target: Optional[str] = None  # filled in by Linker
    external: bool = False  # true if Linker could not resolve it inside the repo

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_symbol": self.from_symbol,
            "target_name": self.target_name,
            "kind": self.kind,
            "file_path": self.file_path.replace("\\", "/"),
            "line": self.line,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "resolved_target": self.resolved_target,
            "external": self.external,
        }


@dataclass
class SqlAccess:
    """A SQL statement found either in a .sql/.ddl file or embedded in host code."""

    verb: str  # SELECT / INSERT / UPDATE / DELETE / CALL / MERGE
    tables: List[str]
    file_path: str
    line: int
    snippet: str
    owner_symbol: Optional[str] = None  # qualified_name of the enclosing method/procedure
    confidence: float = 1.0
    locking: bool = False  # true for a pessimistic lock, e.g. `SELECT ... FOR UPDATE`

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verb": self.verb,
            "tables": self.tables,
            "file_path": self.file_path.replace("\\", "/"),
            "line": self.line,
            "snippet": self.snippet,
            "owner_symbol": self.owner_symbol,
            "confidence": self.confidence,
            "locking": self.locking,
        }


@dataclass
class Endpoint:
    """A network-exposed operation: REST route, WCF/SOAP operation, CICS transaction."""

    route: str
    http_method: str
    owner_symbol: str  # qualified_name of the handling class/method
    file_path: str
    line: int
    protocol: str = "REST"  # REST / SOAP / WCF / CICS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route": self.route,
            "http_method": self.http_method,
            "owner_symbol": self.owner_symbol,
            "file_path": self.file_path.replace("\\", "/"),
            "line": self.line,
            "protocol": self.protocol,
        }


@dataclass
class ParseDiagnostic:
    """A non-fatal issue encountered while parsing a single file."""

    file_path: str
    severity: str  # INFO / WARNING / ERROR
    message: str
    line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path.replace("\\", "/"),
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
        }


@dataclass
class ParseResult:
    """Everything extracted from one source file."""

    file_path: str
    language: str
    symbols: List[Symbol] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)
    sql_accesses: List[SqlAccess] = field(default_factory=list)
    endpoints: List[Endpoint] = field(default_factory=list)
    diagnostics: List[ParseDiagnostic] = field(default_factory=list)
    parse_coverage: float = 1.0  # fraction of the file tree-sitter parsed without ERROR nodes
    parser_name: str = ""  # which parser produced this (for fallback tracking)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path.replace("\\", "/"),
            "language": self.language,
            "symbols": [s.to_dict() for s in self.symbols],
            "references": [r.to_dict() for r in self.references],
            "sql_accesses": [s.to_dict() for s in self.sql_accesses],
            "endpoints": [e.to_dict() for e in self.endpoints],
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "parse_coverage": self.parse_coverage,
            "parser_name": self.parser_name,
        }
