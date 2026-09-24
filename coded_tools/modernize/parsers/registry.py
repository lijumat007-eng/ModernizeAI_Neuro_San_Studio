# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
ParserRegistry: maps a file extension (with light content sniffing for
ambiguous ones like `.h`) to the LanguageParser that should handle it.
Central place that knows which languages are currently wired in, so
RawMemory.ingest_directory and the pipeline don't hardcode extension lists.
"""

import re
from typing import Dict
from typing import List
from typing import Optional

from coded_tools.modernize.parsers.base import LanguageParser
from coded_tools.modernize.parsers.ir import ParseDiagnostic
from coded_tools.modernize.parsers.ir import ParseResult

# A `.h` file is ambiguous between C and C++. These tokens only appear in
# valid C++ (none is legal C), so any hit means "parse this as C++".
_CPP_ONLY_HINTS = re.compile(r"\bclass\s+\w+|\bnamespace\s+\w+|\btemplate\s*<|\bpublic\s*:|\bprivate\s*:|::\w|\bstd::")


class ParserRegistry:
    """Dispatches a (file_path, content) pair to the right LanguageParser."""

    def __init__(self):
        self._by_extension: Dict[str, LanguageParser] = {}
        self._c_parser: Optional[LanguageParser] = None
        self._cpp_parser: Optional[LanguageParser] = None
        self._register_defaults()

    def _register_defaults(self) -> None:
        # Imported lazily so a missing optional dependency (e.g. tree-sitter not
        # installed in a minimal environment) only breaks the languages that need
        # it, not the whole registry.
        try:
            from coded_tools.modernize.parsers.lang.java import JavaParser

            self.register(JavaParser())
        except ImportError:
            pass

        try:
            from coded_tools.modernize.parsers.lang.cpp import CParser
            from coded_tools.modernize.parsers.lang.cpp import CppParser

            self._c_parser = CParser()
            self._cpp_parser = CppParser()
            self.register(self._c_parser)
            self.register(self._cpp_parser)
        except ImportError:
            pass

        try:
            from coded_tools.modernize.parsers.lang.sql import SqlParser

            self.register(SqlParser())
        except ImportError:
            pass

    def register(self, parser: LanguageParser) -> None:
        for ext in parser.extensions:
            self._by_extension[ext.lower()] = parser

    def supported_extensions(self) -> List[str]:
        exts = set(self._by_extension.keys())
        exts.add(".h")  # handled via content sniffing, not a direct extension mapping
        return sorted(exts)

    def parser_for(self, file_path: str, content: str = "") -> Optional[LanguageParser]:
        ext = self._extension_of(file_path)
        if ext == ".h" and self._c_parser is not None:
            return self._cpp_parser if _CPP_ONLY_HINTS.search(content) else self._c_parser
        return self._by_extension.get(ext)

    @staticmethod
    def _extension_of(file_path: str) -> str:
        clean = file_path.replace("\\", "/")
        if "." not in clean.rsplit("/", 1)[-1]:
            return ""
        return "." + clean.rsplit(".", 1)[-1].lower()

    def parse_file(self, file_path: str, content: str) -> Optional[ParseResult]:
        parser = self.parser_for(file_path, content)
        if parser is None:
            return None
        try:
            return parser.parse(file_path, content)
        except Exception as exc:  # noqa: BLE001 - one bad file must not abort the repo scan
            result = ParseResult(
                file_path=file_path.replace("\\", "/"), language=getattr(parser, "language", "unknown")
            )
            result.diagnostics.append(
                ParseDiagnostic(
                    file_path=file_path,
                    severity="ERROR",
                    message=f"Parser raised an unhandled exception: {exc}",
                )
            )
            result.parse_coverage = 0.0
            return result


_DEFAULT_REGISTRY: Optional[ParserRegistry] = None


def get_default_registry() -> ParserRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = ParserRegistry()
    return _DEFAULT_REGISTRY
