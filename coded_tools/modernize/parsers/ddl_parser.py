# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Deterministic SQL DDL & Stored Procedure Parser.
Extracts tables, columns, primary/foreign keys, and stored procedure data lineage.
"""

import re
from typing import Any, Dict, List, Optional


class DdlParser:
    """
    Deterministic parser for database schemas and stored procedures.
    """

    @staticmethod
    def parse_ddl(file_path: str, content: str) -> Dict[str, Any]:
        tables = []
        rel_path = file_path.replace("\\", "/")

        # Table block extraction
        table_blocks = re.finditer(
            r"CREATE\s+TABLE\s+([A-Za-z0-9_]+)\s*\((.*?)\);",
            content,
            re.IGNORECASE | re.DOTALL,
        )

        for block in table_blocks:
            tbl_name = block.group(1).upper()
            body = block.group(2)
            start_line = content[: block.start()].count("\n") + 1
            end_line = content[: block.end()].count("\n") + 1

            columns = []
            pk_col = None
            fks = []

            # Parse lines in table definition
            lines = [l.strip().rstrip(",") for l in body.splitlines() if l.strip()]
            for l in lines:
                # Foreign key check
                fk_match = re.search(
                    r"CONSTRAINT\s+([A-Za-z0-9_]+)\s+FOREIGN\s+KEY\s*\(([A-Za-z0-9_]+)\)\s+REFERENCES\s+([A-Za-z0-9_]+)\s*\(([A-Za-z0-9_]+)\)",
                    l,
                    re.IGNORECASE,
                )
                if fk_match:
                    fks.append({
                        "constraint_name": fk_match.group(1),
                        "column": fk_match.group(2).lower(),
                        "target_table": fk_match.group(3).upper(),
                        "target_column": fk_match.group(4).lower(),
                    })
                    continue

                # Primary key inline or constraint
                if "PRIMARY KEY" in l.upper():
                    parts = l.split()
                    if len(parts) >= 2:
                        col_name = parts[0].lower()
                        pk_col = col_name
                        columns.append({
                            "name": col_name,
                            "type": parts[1].upper(),
                            "is_primary": True,
                        })
                    continue

                # Standard column
                col_parts = l.split()
                if len(col_parts) >= 2 and not col_parts[0].upper().startswith(("CONSTRAINT", "PRIMARY", "UNIQUE", "CHECK")):
                    columns.append({
                        "name": col_parts[0].lower(),
                        "type": col_parts[1].upper(),
                        "is_primary": False,
                    })

            tables.append({
                "table_name": tbl_name,
                "columns": columns,
                "primary_key": pk_col,
                "foreign_keys": fks,
                "file_path": rel_path,
                "start_line": start_line,
                "end_line": end_line,
            })

        return {"tables": tables}

    @staticmethod
    def parse_stored_procedure(file_path: str, content: str) -> Dict[str, Any]:
        procedures = []
        rel_path = file_path.replace("\\", "/")

        proc_pattern = re.compile(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+([A-Za-z0-9_]+)\s*\((.*?)\)\s*(?:LANGUAGE\s+[A-Za-z0-9_]+\s*)?AS\s*\$\$(.*?)\$\$;",
            re.IGNORECASE | re.DOTALL,
        )

        for match in proc_pattern.finditer(content):
            proc_name = match.group(1).upper()
            params_raw = match.group(2)
            body = match.group(3)
            start_line = content[: match.start()].count("\n") + 1
            end_line = content[: match.end()].count("\n") + 1

            # Extract parameters
            params = []
            for p in params_raw.split(","):
                p_str = p.strip()
                if p_str:
                    parts = p_str.split()
                    params.append({
                        "name": parts[0],
                        "mode": parts[1] if len(parts) > 1 else "IN",
                        "type": parts[2] if len(parts) > 2 else "VARCHAR",
                    })

            # Detect read tables (FROM ...)
            reads = set()
            for r in re.finditer(r"FROM\s+([A-Za-z0-9_]+)", body, re.IGNORECASE):
                reads.add(r.group(1).upper())

            # Detect written tables (UPDATE ... / INSERT INTO ... / DELETE FROM ...)
            writes = set()
            for w in re.finditer(r"UPDATE\s+([A-Za-z0-9_]+)", body, re.IGNORECASE):
                writes.add(w.group(1).upper())
            for w in re.finditer(r"INSERT\s+INTO\s+([A-Za-z0-9_]+)", body, re.IGNORECASE):
                writes.add(w.group(1).upper())
            for w in re.finditer(r"DELETE\s+FROM\s+([A-Za-z0-9_]+)", body, re.IGNORECASE):
                writes.add(w.group(1).upper())

            procedures.append({
                "procedure_name": proc_name,
                "parameters": params,
                "tables_read": list(reads),
                "tables_written": list(writes),
                "file_path": rel_path,
                "start_line": start_line,
                "end_line": end_line,
            })

        return {"procedures": procedures}
