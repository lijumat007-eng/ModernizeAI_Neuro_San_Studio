# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Deterministic Java AST & Regex Parser.
Extracts classes, methods, imports, inter-service calls, and embedded SQL queries.
"""

import os
import re
from typing import Any, Dict, List, Optional


class JavaParser:
    """
    Deterministic parser for legacy Java source code files.
    """

    @staticmethod
    def parse_file(file_path: str, content: str) -> Dict[str, Any]:
        lines = content.splitlines()
        rel_path = file_path.replace("\\", "/")

        # 1. Package
        package_match = re.search(r"^\s*package\s+([a-zA-Z0-9_.]+);", content, re.MULTILINE)
        package = package_match.group(1) if package_match else ""

        # 2. Imports
        imports = re.findall(r"^\s*import\s+([a-zA-Z0-9_.*]+);", content, re.MULTILINE)

        # 3. Class name and line range
        class_match = re.search(
            r"^\s*(?:public\s+|abstract\s+|final\s+)*class\s+([A-Za-z0-9_]+)",
            content,
            re.MULTILINE,
        )
        class_name = class_match.group(1) if class_match else os.path.basename(file_path).replace(".java", "")
        
        class_start = 1
        if class_match:
            class_start = content[: class_match.start()].count("\n") + 1
        class_end = len(lines)

        # 4. Fields
        fields = []
        field_pattern = re.compile(
            r"^\s*(?:private|protected|public)?\s+(?:static\s+|final\s+)*([A-Za-z0-9_<>]+)\s+([A-Za-z0-9_]+)\s*(?:=.*?)?;",
            re.MULTILINE,
        )
        for m in field_pattern.finditer(content):
            f_type, f_name = m.groups()
            line_no = content[: m.start()].count("\n") + 1
            if f_name not in ("class", "return"):
                fields.append({
                    "name": f_name,
                    "type": f_type,
                    "line": line_no,
                })

        # 5. Methods
        methods = []
        method_pattern = re.compile(
            r"^\s*(?:public|protected|private)?\s*(?:static\s+|final\s+)*([A-Za-z0-9_<>]+)\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*(?:throws\s+[A-Za-z0-9_,\s]+)?\s*\{",
            re.MULTILINE,
        )
        for m in method_pattern.finditer(content):
            ret_type, m_name, params = m.groups()
            line_no = content[: m.start()].count("\n") + 1
            if m_name not in ("if", "while", "switch", "for", "catch"):
                methods.append({
                    "name": m_name,
                    "return_type": ret_type,
                    "parameters": params.strip(),
                    "line": line_no,
                })

        # 6. Embedded SQL detection
        sql_statements = []
        sql_pattern = re.compile(
            r'"\s*(SELECT|INSERT|UPDATE|DELETE|\{call)\s+([^"]+)"',
            re.IGNORECASE | re.DOTALL,
        )
        for m in sql_pattern.finditer(content):
            verb = m.group(1).upper()
            full_sql = m.group(0).strip('"')
            line_no = content[: m.start()].count("\n") + 1
            
            # Extract target table name
            table_match = re.search(r"(?:FROM|INTO|UPDATE|call)\s+([A-Za-z0-9_]+)", full_sql, re.IGNORECASE)
            table_name = table_match.group(1).upper() if table_match else "UNKNOWN"

            sql_statements.append({
                "verb": verb,
                "table": table_name,
                "sql": full_sql.replace("\n", " ").strip(),
                "line": line_no,
            })

        # 7. Inter-service calls and instantiation
        service_calls = []
        instantiation_pattern = re.compile(r"new\s+([A-Za-z0-9_]+ValidationService|[A-Za-z0-9_]+Service)\s*\(", re.MULTILINE)
        for m in instantiation_pattern.finditer(content):
            called_service = m.group(1)
            line_no = content[: m.start()].count("\n") + 1
            service_calls.append({
                "target_service": called_service,
                "call_type": "INSTANTIATION",
                "line": line_no,
            })

        method_call_pattern = re.compile(r"([A-Za-z0-9_]+Service)\.([A-Za-z0-9_]+)\(", re.MULTILINE)
        for m in method_call_pattern.finditer(content):
            target_srv, method = m.groups()
            line_no = content[: m.start()].count("\n") + 1
            service_calls.append({
                "target_service": target_srv,
                "target_method": method,
                "call_type": "INVOCATION",
                "line": line_no,
            })

        return {
            "class_name": class_name,
            "package": package,
            "file_path": rel_path,
            "start_line": class_start,
            "end_line": class_end,
            "imports": imports,
            "fields": fields,
            "methods": methods,
            "sql_statements": sql_statements,
            "service_calls": service_calls,
        }
