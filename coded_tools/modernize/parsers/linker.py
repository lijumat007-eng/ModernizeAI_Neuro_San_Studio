# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Linker: cross-file symbol resolution over the IR produced by every
LanguageParser. A single file's parser only ever sees simple names
("PaymentGateway", not "com.acme.gateway.PaymentGateway"); the Linker turns
those into resolved, repo-wide qualified names wherever it safely can, and
otherwise records an honest confidence instead of guessing.

Resolution rules, in order:
  1. The reference's file has an import/using/include statement that ends
     with the simple name, and a symbol exists at that exact qualified name
     -> confidence 1.0.
  2. Exactly one symbol anywhere in the repo has this simple name
     -> confidence 0.8 (a same-name-different-package clash cannot occur
     because it would have matched more than one candidate).
  3. More than one symbol shares the simple name (ambiguous) -> the first
     candidate is kept as a best guess, confidence 0.5, so the edge still
     shows up in the graph rather than disappearing.
  4. No candidate anywhere -> external (framework/library class, or a type
     genuinely outside the scanned repo), confidence unchanged, `external=True`.
"""

from typing import Dict, List

from coded_tools.modernize.parsers.ir import ParseResult, Symbol

# Symbol kinds that can be the *target* of a CALLS/INSTANTIATES/INHERITS/IMPLEMENTS
# reference. Fields, methods, and parameters are never link targets themselves.
_LINKABLE_KINDS = {"CLASS", "INTERFACE", "STRUCT", "ENUM", "RECORD", "PROGRAM", "TABLE", "PROCEDURE"}


class Linker:
    def link(self, parse_results: List[ParseResult]) -> None:
        symbol_by_qname: Dict[str, Symbol] = {}
        simple_name_index: Dict[str, List[str]] = {}
        imports_by_file: Dict[str, List[str]] = {}

        for result in parse_results:
            for symbol in result.symbols:
                if symbol.kind not in _LINKABLE_KINDS:
                    continue
                symbol_by_qname[symbol.qualified_name] = symbol
                simple = symbol.qualified_name.rsplit(".", 1)[-1]
                simple_name_index.setdefault(simple, [])
                if symbol.qualified_name not in simple_name_index[simple]:
                    simple_name_index[simple].append(symbol.qualified_name)

            for ref in result.references:
                if ref.kind == "IMPORTS":
                    imports_by_file.setdefault(ref.file_path, []).append(ref.target_name)

        for result in parse_results:
            for ref in result.references:
                if ref.kind == "IMPORTS":
                    continue
                self._resolve(ref, symbol_by_qname, simple_name_index, imports_by_file)

    @staticmethod
    def _resolve(ref, symbol_by_qname, simple_name_index, imports_by_file) -> None:
        simple = ref.target_name.rsplit(".", 1)[-1]

        for imp in imports_by_file.get(ref.file_path, []):
            if imp == ref.target_name or imp.endswith("." + simple):
                if imp in symbol_by_qname:
                    ref.resolved_target = imp
                    ref.confidence = 1.0
                    ref.external = False
                    return

        candidates = simple_name_index.get(simple, [])
        if len(candidates) == 1:
            ref.resolved_target = candidates[0]
            ref.confidence = 0.8
            ref.external = False
        elif len(candidates) > 1:
            ref.resolved_target = candidates[0]
            ref.confidence = 0.5
            ref.external = False
        else:
            ref.resolved_target = None
            ref.external = True
