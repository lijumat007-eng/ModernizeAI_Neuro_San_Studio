# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Tier 2: Structural Memory Engine.
Maintains deterministic symbol tables, AST hierarchies, and schema dictionaries.
"""

from typing import Any, Dict, List, Optional


class StructuralMemory:
    """
    Tier 2 Structural Memory storing parsed code AST symbols and relational schemas.
    """

    def __init__(self):
        self.classes: Dict[str, Dict[str, Any]] = {}
        self.tables: Dict[str, Dict[str, Any]] = {}
        self.procedures: Dict[str, Dict[str, Any]] = {}
        self.endpoints: Dict[str, Dict[str, Any]] = {}

        # Generic multi-language IR stores (coded_tools.modernize.parsers.ir),
        # populated by the parser pipeline for any language (Java, C#, SQL,
        # COBOL, C/C++, ...). The typed dict stores above are kept as a
        # Java/SQL-shaped convenience view for existing callers.
        self.symbols: Dict[str, Dict[str, Any]] = {}
        self.references: List[Dict[str, Any]] = []
        self.ir_endpoints: List[Dict[str, Any]] = []

    def register_class(
        self,
        class_name: str,
        package: str,
        file_path: str,
        start_line: int,
        end_line: int,
        methods: List[Dict[str, Any]],
        fields: List[Dict[str, Any]],
        imports: List[str],
    ):
        full_name = f"{package}.{class_name}" if package else class_name
        self.classes[full_name] = {
            "name": class_name,
            "package": package,
            "full_name": full_name,
            "file_path": file_path.replace("\\", "/"),
            "start_line": start_line,
            "end_line": end_line,
            "methods": methods,
            "fields": fields,
            "imports": imports,
        }

    def register_table(
        self,
        table_name: str,
        columns: List[Dict[str, Any]],
        primary_key: Optional[str],
        foreign_keys: List[Dict[str, Any]],
        file_path: str,
        start_line: int,
        end_line: int,
    ):
        clean_name = table_name.upper()
        self.tables[clean_name] = {
            "name": clean_name,
            "columns": columns,
            "primary_key": primary_key,
            "foreign_keys": foreign_keys,
            "file_path": file_path.replace("\\", "/"),
            "start_line": start_line,
            "end_line": end_line,
        }

    def register_procedure(
        self,
        proc_name: str,
        parameters: List[Dict[str, Any]],
        tables_read: List[str],
        tables_written: List[str],
        file_path: str,
        start_line: int,
        end_line: int,
    ):
        clean_name = proc_name.upper()
        self.procedures[clean_name] = {
            "name": clean_name,
            "parameters": parameters,
            "tables_read": [t.upper() for t in tables_read],
            "tables_written": [t.upper() for t in tables_written],
            "file_path": file_path.replace("\\", "/"),
            "start_line": start_line,
            "end_line": end_line,
        }

    def register_endpoint(
        self,
        route: str,
        http_method: str,
        service_class: str,
        method_name: str,
        file_path: str,
        start_line: int,
        end_line: int,
    ):
        key = f"{http_method.upper()} {route}"
        self.endpoints[key] = {
            "route": route,
            "method": http_method.upper(),
            "service_class": service_class,
            "handler": method_name,
            "file_path": file_path.replace("\\", "/"),
            "start_line": start_line,
            "end_line": end_line,
        }

    def register_symbol(self, symbol_dict: Dict[str, Any]) -> None:
        """Registers one IR Symbol (see parsers/ir.py) by its qualified_name."""
        self.symbols[symbol_dict["qualified_name"]] = symbol_dict

    def register_reference(self, reference_dict: Dict[str, Any]) -> None:
        """Records one IR Reference (see parsers/ir.py), post-linking."""
        self.references.append(reference_dict)

    def register_ir_endpoint(self, endpoint_dict: Dict[str, Any]) -> None:
        self.ir_endpoints.append(endpoint_dict)

    def get_symbol(self, qualified_name: str) -> Optional[Dict[str, Any]]:
        return self.symbols.get(qualified_name)

    def get_class(self, name: str) -> Optional[Dict[str, Any]]:
        if name in self.classes:
            return self.classes[name]
        for k, v in self.classes.items():
            if v["name"] == name:
                return v
        return None

    def get_table(self, name: str) -> Optional[Dict[str, Any]]:
        return self.tables.get(name.upper())

    def get_procedure(self, name: str) -> Optional[Dict[str, Any]]:
        return self.procedures.get(name.upper())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "classes": self.classes,
            "tables": self.tables,
            "procedures": self.procedures,
            "endpoints": self.endpoints,
            "symbols": self.symbols,
            "references": self.references,
            "ir_endpoints": self.ir_endpoints,
        }
