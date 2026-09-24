# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Base classes shared by every language-specific parser:
- LanguageParser: the interface the ParserRegistry dispatches to.
- TreeSitterParser: shared plumbing for the tree-sitter-backed parsers
  (Java, C#, C, C++) - node text extraction, 1-based line spans, and
  ERROR/MISSING node counting so callers get an honest coverage score
  instead of a silent guess.
"""

from abc import ABC
from abc import abstractmethod
from typing import List

from coded_tools.modernize.parsers.ir import ParseDiagnostic
from coded_tools.modernize.parsers.ir import ParseResult


class LanguageParser(ABC):
    """Interface every language parser implements."""

    language: str = ""
    extensions: List[str] = []

    @abstractmethod
    def parse(self, file_path: str, content: str) -> ParseResult:
        """Parses one file's content and returns its IR."""
        raise NotImplementedError


class TreeSitterParser(LanguageParser):
    """
    Shared helper for tree-sitter-backed parsers.
    Subclasses provide `ts_language_name` and implement `_extract(root, source, file_path)`.
    """

    ts_language_name: str = ""

    def __init__(self):
        self._parser = None

    def _get_parser(self):
        if self._parser is None:
            from tree_sitter_language_pack import get_parser

            self._parser = get_parser(self.ts_language_name)
        return self._parser

    def parse(self, file_path: str, content: str) -> ParseResult:
        source_bytes = content.encode("utf-8", errors="replace")
        parser = self._get_parser()
        tree = parser.parse(source_bytes)
        root = tree.root_node

        result = ParseResult(
            file_path=file_path.replace("\\", "/"),
            language=self.language,
            parser_name=f"tree_sitter_{self.language}",
        )

        error_count, node_count = self._count_errors(root)
        result.parse_coverage = round(1.0 - (error_count / max(1, node_count)), 4)
        if error_count > 0:
            result.diagnostics.append(
                ParseDiagnostic(
                    file_path=file_path,
                    severity="WARNING" if result.parse_coverage > 0.9 else "ERROR",
                    message=f"{error_count} syntax error node(s) encountered during parse; "
                    f"coverage={result.parse_coverage}",
                )
            )

        try:
            self._extract(root, source_bytes, file_path.replace("\\", "/"), result)
        except Exception as exc:  # noqa: BLE001 - a parser bug must not crash the pipeline
            result.diagnostics.append(
                ParseDiagnostic(
                    file_path=file_path,
                    severity="ERROR",
                    message=f"Extraction failed after tree-sitter parse: {exc}",
                )
            )

        return result

    @staticmethod
    def _count_errors(node) -> "tuple[int, int]":
        """Walks the tree once, counting ERROR/MISSING nodes and total nodes."""
        error_count = 0
        node_count = 0
        stack = [node]
        while stack:
            n = stack.pop()
            node_count += 1
            if n.type == "ERROR" or n.is_missing:
                error_count += 1
            stack.extend(n.children)
        return error_count, node_count

    @staticmethod
    def text(node, source_bytes: bytes) -> str:
        if node is None:
            return ""
        return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    @staticmethod
    def line_start(node) -> int:
        return node.start_point[0] + 1

    @staticmethod
    def line_end(node) -> int:
        return node.end_point[0] + 1

    @staticmethod
    def find_child_by_field(node, field_name: str):
        return node.child_by_field_name(field_name)

    @staticmethod
    def find_children_by_type(node, type_name: str) -> list:
        return [c for c in node.children if c.type == type_name]

    @staticmethod
    def walk(node):
        """Depth-first generator over every descendant node, including `node` itself."""
        stack = [node]
        while stack:
            n = stack.pop()
            yield n
            stack.extend(reversed(n.children))

    def _extract(self, root, source_bytes: bytes, file_path: str, result: ParseResult) -> None:
        raise NotImplementedError
