# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Shared SQL-in-host-language extraction. Used by every host-language parser
(Java, C#, C/C++, COBOL) to turn a raw SQL string found in source code into
a SqlAccess record with real table names, via sqlglot rather than regex
guessing. Falls back to a regex table match only if sqlglot cannot parse the
fragment (common with `?`/`:param` placeholders it doesn't expect).
"""

import re
from typing import List, Optional

import sqlglot
from sqlglot import exp

from coded_tools.modernize.parsers.ir import SqlAccess

_SQL_VERB_RE = re.compile(
    r"^\s*(SELECT|INSERT|UPDATE|DELETE|MERGE|CALL|EXEC|\{\s*call)\b", re.IGNORECASE
)
_FALLBACK_TABLE_RE = re.compile(
    r"(?:FROM|INTO|UPDATE|CALL|JOIN)\s+([A-Za-z0-9_\.]+)", re.IGNORECASE
)


def looks_like_sql(text: str) -> bool:
    """Cheap pre-filter so we don't run sqlglot on every string literal in a repo."""
    return bool(_SQL_VERB_RE.match(text.strip()))


def sql_verb(sql_text: str) -> str:
    m = _SQL_VERB_RE.match(sql_text.strip())
    if not m:
        return "UNKNOWN"
    return m.group(1).upper().lstrip("{").strip()


def extract_tables(sql_text: str, dialect: Optional[str] = None) -> List[str]:
    """Best-effort table name extraction: real SQL parse first, regex fallback second."""
    try:
        parsed = sqlglot.parse_one(sql_text, read=dialect, error_level=sqlglot.ErrorLevel.IGNORE)
    except Exception:
        parsed = None

    if parsed is not None:
        tables = sorted({t.name.upper() for t in parsed.find_all(exp.Table) if t.name})
        if tables:
            return tables

    m = _FALLBACK_TABLE_RE.search(sql_text)
    return [m.group(1).upper()] if m else []


def build_sql_access(
    sql_text: str,
    file_path: str,
    line: int,
    owner_symbol: Optional[str] = None,
    dialect: Optional[str] = None,
    confidence: float = 1.0,
) -> SqlAccess:
    verb = sql_verb(sql_text)
    tables = extract_tables(sql_text, dialect=dialect)
    return SqlAccess(
        verb=verb,
        tables=tables,
        file_path=file_path,
        line=line,
        snippet=" ".join(sql_text.split())[:300],
        owner_symbol=owner_symbol,
        confidence=confidence if tables else min(confidence, 0.5),
    )


def join_string_concat(
    node,
    source_bytes: bytes,
    string_literal_types=("string_literal",),
    container_types=("binary_expression", "concatenated_string"),
) -> Optional[str]:
    """
    Walks a concatenation tree of string literals and non-literal expressions
    (variables, method calls) and joins the literal parts, substituting a `?`
    placeholder for anything that isn't a literal string. Returns None if the
    tree contains no string literal at all (not a SQL candidate).

    Handles two concatenation styles across the supported host languages:
      - `left + right` operator concatenation (Java, C#): `binary_expression`
      - adjacent-literal concatenation (C/C++): `concatenated_string`, e.g.
        `"SELECT * FROM " "ORDERS"` with no operator at all.

    This is what lets `"SELECT * FROM " + tableVar + " WHERE id = ?"` resolve
    to a real SQL statement instead of being missed entirely by a
    single-string-literal regex.
    """
    parts: List[str] = []
    found_literal = [False]

    def strip_quotes(raw: str) -> str:
        if len(raw) >= 2 and raw[0] in "\"'" and raw[-1] == raw[0]:
            return raw[1:-1]
        return raw

    def visit(n):
        if n.type in string_literal_types:
            found_literal[0] = True
            raw = source_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="replace")
            parts.append(strip_quotes(raw))
        elif n.type == "binary_expression":
            left = n.child_by_field_name("left")
            right = n.child_by_field_name("right")
            if left is not None:
                visit(left)
            if right is not None:
                visit(right)
        elif n.type == "concatenated_string":
            for c in n.children:
                if c.type in string_literal_types:
                    visit(c)
        else:
            parts.append("?")

    visit(node)
    if not found_literal[0]:
        return None
    return "".join(parts)
