# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
SQL / PL-SQL parser covering Oracle, T-SQL, Postgres and generic ANSI DDL.

sqlglot parses standard DDL (CREATE TABLE/INDEX/VIEW, ALTER TABLE) exactly,
so that part of this module just walks its expression tree. Procedural
bodies (CREATE PROCEDURE/FUNCTION/TRIGGER/PACKAGE) are a different problem:
sqlglot has no grammar for PL/SQL or T-SQL control flow (IF/DECLARE/LOOP),
and its Oracle dialect cannot even parse a plain `IS ... BEGIN ... END;`
procedure header at all. So this parser finds procedural blocks itself with
a depth-aware BEGIN/END (and Postgres `$$...$$`) scanner, then treats each
statement *inside* the body as its own small SQL fragment and hands each one
to sqlglot individually for table lineage - the same approach the old
DdlParser took with regex, but with a real parser doing the per-statement
work instead of an ad hoc "FROM <word>" guess.
"""

import re
from typing import Dict, List, Optional, Tuple

import sqlglot
from sqlglot import exp

from coded_tools.modernize.parsers import embedded_sql
from coded_tools.modernize.parsers.base import LanguageParser
from coded_tools.modernize.parsers.ir import ParseDiagnostic, ParseResult, Reference, Symbol, SqlAccess

# --------------------------------------------------------------------------- #
# Dialect sniffing
# --------------------------------------------------------------------------- #

_DIALECT_HINTS = (
    (re.compile(r"\bVARCHAR2\b|\bNUMBER\s*\(|:=|\bDBMS_\w+"), "oracle"),
    (re.compile(r"@\w+\s+(VARCHAR|INT|NVARCHAR|DECIMAL|BIGINT)\b|\bGO\s*$", re.MULTILINE), "tsql"),
    (re.compile(r"\bLANGUAGE\s+plpgsql\b|\$\$|\$\w*\$"), "postgres"),
)


def sniff_dialect(content: str) -> str:
    for pattern, dialect in _DIALECT_HINTS:
        if pattern.search(content, re.IGNORECASE):
            return dialect
    return "postgres"  # sqlglot's most ANSI-forgiving common dialect


# --------------------------------------------------------------------------- #
# Character-level helpers: string/comment masking and statement splitting.
# Shared by top-level DDL splitting and by procedure-body statement splitting.
# --------------------------------------------------------------------------- #

def _mask_strings_and_comments(text: str) -> str:
    """Returns a same-length copy of `text` with string-literal and `--` comment
    content blanked out (newlines preserved), so keyword regexes run against the
    result never match text that only looks like code because it's inside a
    string or comment."""
    out = list(text)
    i, n = 0, len(text)
    in_single = False
    while i < n:
        c = text[i]
        if in_single:
            if c == "'" and not (i + 1 < n and text[i + 1] == "'"):
                in_single = False
            elif c != "\n":
                out[i] = " "
            i += 1
            continue
        if c == "-" and i + 1 < n and text[i + 1] == "-":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
            continue
        if c == "'":
            in_single = True
            i += 1
            continue
        i += 1
    return "".join(out)


def split_statements(text: str) -> List[Tuple[str, int]]:
    """
    Splits `text` on top-level `;` - outside string literals, quoted
    identifiers, `--` comments, and parentheses - returning
    (statement_text, start_offset) pairs. Used for a plain DDL file and,
    separately, for the inside of a procedure/trigger body.
    """
    statements: List[Tuple[str, int]] = []
    buf: List[str] = []
    start = 0
    depth = 0
    i, n = 0, len(text)
    in_single = in_double = False
    while i < n:
        c = text[i]
        if in_single:
            buf.append(c)
            if c == "'" and not (i + 1 < n and text[i + 1] == "'"):
                in_single = False
            i += 1
            continue
        if in_double:
            buf.append(c)
            if c == '"':
                in_double = False
            i += 1
            continue
        if c == "-" and i + 1 < n and text[i + 1] == "-":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "'":
            in_single = True
            buf.append(c)
            i += 1
            continue
        if c == '"':
            in_double = True
            buf.append(c)
            i += 1
            continue
        if c == "(":
            depth += 1
            buf.append(c)
            i += 1
            continue
        if c == ")":
            depth -= 1
            buf.append(c)
            i += 1
            continue
        if c == ";" and depth == 0:
            stmt = "".join(buf).strip()
            if stmt:
                statements.append((stmt, start))
            buf = []
            i += 1
            start = i
            continue
        buf.append(c)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append((tail, start))
    return statements


_BLOCK_KEYWORD_RE = re.compile(r"\b(BEGIN|CASE|IF|LOOP|END)\b", re.IGNORECASE)


def _find_matching_end(masked_text: str, search_from: int) -> int:
    """Given text already stripped of strings/comments, and an offset just past
    an opening BEGIN, returns the offset just past the balancing END, tracking
    nested BEGIN/CASE/IF/LOOP...END pairs (every opener has exactly one matching
    END regardless of what follows it - "END IF", "END LOOP", "END;", "END name;"
    all just close one level). Returns -1 if unbalanced."""
    depth = 1
    for m in _BLOCK_KEYWORD_RE.finditer(masked_text, search_from):
        kw = m.group(1).upper()
        if kw == "END":
            depth -= 1
            if depth == 0:
                return m.end()
        else:
            depth += 1
    return -1


def _extract_dollar_body(text: str, start: int) -> Optional[Tuple[str, int, int]]:
    """Postgres `$tag$ ... $tag$` body (tag is usually empty: `$$ ... $$`).
    Returns (body_text, body_start_offset, block_end_offset)."""
    m = re.search(r"\$(\w*)\$", text[start:])
    if not m:
        return None
    tag = m.group(1)
    open_end = start + m.end()
    close_re = re.compile(r"\$" + re.escape(tag) + r"\$")
    m2 = close_re.search(text, open_end)
    if not m2:
        return None
    body = text[open_end : m2.start()]
    end_offset = m2.end()
    trailing = re.match(r"\s*;", text[end_offset : end_offset + 10])
    if trailing:
        end_offset += trailing.end()
    return body, open_end, end_offset


def _extract_begin_end_body(text: str, header_end: int) -> Optional[Tuple[str, int, int]]:
    """Oracle/T-SQL/ANSI `[DECLARE ...] BEGIN ... END [name];` body.
    Returns (body_text, body_start_offset, block_end_offset).

    The body handed back starts right after this BEGIN, not at `header_end`:
    the params list and any DECLARE section sit between the two, and unlike
    Oracle/Postgres (whose params are parenthesized), T-SQL's `@param TYPE, ...`
    list has no enclosing parens and no `;` before `AS BEGIN`, so it would
    otherwise fuse with the body's first real statement and hide it from the
    per-statement verb check.
    """
    masked = _mask_strings_and_comments(text)
    m = re.search(r"\bBEGIN\b", masked[header_end:], re.IGNORECASE)
    if not m:
        return None
    search_from = header_end + m.end()
    end_pos = _find_matching_end(masked, search_from)
    if end_pos == -1:
        return None
    body = text[search_from:end_pos]
    trailing = re.match(r"[ \t]*[A-Za-z0-9_\"\.]*\s*;?\s*(GO\b)?\s*/?", text[end_pos : end_pos + 80], re.IGNORECASE)
    end_offset = end_pos + (trailing.end() if trailing else 0)
    return body, search_from, end_offset


def _extract_declaration_only_body(text: str, header_end: int) -> Optional[Tuple[str, int, int]]:
    """Body-less block (no BEGIN at all): plain statements up to the closing
    `END name;`. Returns (body_text, body_start_offset, block_end_offset)."""
    for stmt, offset in split_statements(text[header_end:]):
        if re.match(r"^END\b", stmt, re.IGNORECASE):
            end_offset = header_end + offset + len(stmt)
            trailing = re.match(r"\s*;", text[end_offset : end_offset + 5])
            end_offset += trailing.end() if trailing else 0
            return text[header_end : header_end + offset], header_end, end_offset
    return None


def _find_package_end(masked_text: str, start: int) -> int:
    """A PACKAGE (or PACKAGE BODY) has no wrapping BEGIN of its own - each
    member procedure/function inside it has its own independent, self-balancing
    BEGIN...END pair. So unlike `_find_matching_end`, this starts at depth 0:
    every complete member body nets back to depth 0 as it's scanned past, and
    the package's own closing END is simply the first END seen while nothing
    is still open."""
    depth = 0
    for m in _BLOCK_KEYWORD_RE.finditer(masked_text, start):
        kw = m.group(1).upper()
        if kw == "END":
            if depth == 0:
                return m.end()
            depth -= 1
        else:
            depth += 1
    return -1


def _extract_package_body(text: str, header_end: int) -> Optional[Tuple[str, int, int]]:
    masked = _mask_strings_and_comments(text)
    end_pos = _find_package_end(masked, header_end)
    if end_pos == -1:
        return None
    body = text[header_end:end_pos]
    trailing = re.match(r"[ \t]*[A-Za-z0-9_\"\.]*\s*;?\s*/?", text[end_pos : end_pos + 80], re.IGNORECASE)
    end_offset = end_pos + (trailing.end() if trailing else 0)
    return body, header_end, end_offset


def _extract_block_body(text: str, header_end: int, is_package: bool = False) -> Optional[Tuple[str, int, int]]:
    """Picks the right body-extraction strategy based on whichever marker (a
    Postgres `$tag$` or a `BEGIN`) appears first after the header; falls back
    to a bare declaration list for a body-less package spec.
    Returns (body_text, body_start_offset, block_end_offset)."""
    if is_package:
        return _extract_package_body(text, header_end)

    dollar_match = re.search(r"\$(\w*)\$", text[header_end:])
    dollar_idx = header_end + dollar_match.start() if dollar_match else None

    masked = _mask_strings_and_comments(text)
    begin_match = re.search(r"\bBEGIN\b", masked[header_end:], re.IGNORECASE)
    begin_idx = header_end + begin_match.start() if begin_match else None

    if dollar_idx is not None and (begin_idx is None or dollar_idx < begin_idx):
        result = _extract_dollar_body(text, header_end)
        if result is not None:
            return result
    if begin_idx is not None:
        result = _extract_begin_end_body(text, header_end)
        if result is not None:
            return result
    return _extract_declaration_only_body(text, header_end)


# --------------------------------------------------------------------------- #
# Finding procedural blocks (PROCEDURE / FUNCTION / TRIGGER / PACKAGE)
# --------------------------------------------------------------------------- #

_TOP_LEVEL_HEADER_RE = re.compile(
    r"CREATE\s+(?:OR\s+(?:REPLACE|ALTER)\s+)?"
    r"(?P<kind>PROCEDURE|PROC|FUNCTION|TRIGGER|PACKAGE\s+BODY|PACKAGE)\s+"
    r"(?P<name>[A-Za-z0-9_.\"]+)",
    re.IGNORECASE,
)
_MEMBER_HEADER_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<kind>PROCEDURE|FUNCTION)\s+(?P<name>[A-Za-z0-9_]+)\s*(?:\(|IS\b|AS\b)",
    re.IGNORECASE,
)
_TRIGGER_TARGET_RE = re.compile(
    r"\b(?P<timing>BEFORE|AFTER|INSTEAD\s+OF)\s+(?P<events>[A-Za-z, ]+?)\s+ON\s+(?P<table>[A-Za-z0-9_.\"]+)",
    re.IGNORECASE,
)
_PARAM_LIST_RE = re.compile(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)")


def _normalize_kind(kind_raw: str) -> str:
    kind = re.sub(r"\s+", " ", kind_raw.strip().upper())
    return "PROCEDURE" if kind == "PROC" else kind


def _parse_param_list(header_text_after_name: str) -> List[Dict[str, str]]:
    m = _PARAM_LIST_RE.search(header_text_after_name)
    if not m:
        return []
    params = []
    for raw in m.group(1).split(","):
        p = raw.strip()
        if not p:
            continue
        parts = p.split()
        params.append({"name": parts[0].lstrip("@") if parts else p, "raw": p})
    return params


def _find_top_level_blocks(text: str) -> List[Tuple[str, str, int, int, str, int, int]]:
    """Returns (kind, name, header_start, header_end, body_text, body_start, block_end)
    for every top-level CREATE PROCEDURE/FUNCTION/TRIGGER/PACKAGE(BODY) found, in
    order, with block_end already past the body and any trailing terminator."""
    blocks = []
    for m in _TOP_LEVEL_HEADER_RE.finditer(text):
        kind = _normalize_kind(m.group("kind"))
        name = m.group("name").strip('"')
        header_end = m.end()
        result = _extract_block_body(text, header_end, is_package=kind in ("PACKAGE", "PACKAGE BODY"))
        if result is None:
            continue
        body_text, body_start, block_end = result
        blocks.append((kind, name, m.start(), header_end, body_text, body_start, block_end))
    return blocks


# --------------------------------------------------------------------------- #
# Procedure-body statement lineage
# --------------------------------------------------------------------------- #

_BODY_VERB_RE = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|MERGE|CALL|EXEC(?:UTE)?)\b", re.IGNORECASE)
_INTO_BEFORE_FROM_RE = re.compile(r"\bINTO\s+[A-Za-z0-9_.,\s]+?(?=\bFROM\b)", re.IGNORECASE)
# A DML statement immediately following a control-flow keyword shares its split()
# chunk with that keyword, since BEGIN/THEN/ELSE/DECLARE aren't themselves
# semicolon-terminated (only the statement that ends them is): e.g. the chunk
# "BEGIN\n  SELECT ... FOR UPDATE" needs "BEGIN" peeled off before the verb
# check anchors at the start, or the first statement in every block is missed.
_LEADING_CONTROL_RE = re.compile(r"^\s*(BEGIN|THEN|ELSE|DECLARE)\s+", re.IGNORECASE)


def _strip_leading_control_keywords(stmt: str) -> str:
    prev = None
    while prev != stmt:
        prev = stmt
        stmt = _LEADING_CONTROL_RE.sub("", stmt)
    return stmt


def extract_body_sql_accesses(
    body_text: str, file_path: str, body_start_line: int, owner_symbol: str, dialect: str,
) -> List[SqlAccess]:
    """Splits a procedure/trigger body into statements and extracts real table
    lineage (and row-locking) from each SELECT/INSERT/UPDATE/DELETE/MERGE/CALL."""
    accesses = []
    for raw_stmt_text, offset in split_statements(body_text):
        stmt_text = _strip_leading_control_keywords(raw_stmt_text)
        if not _BODY_VERB_RE.match(stmt_text):
            continue  # DECLARE, IF/THEN, assignment (`:=`), END - not a SQL statement
        line = body_start_line + body_text[:offset].count("\n")
        cleaned = stmt_text
        if cleaned.lstrip().upper().startswith("SELECT") and re.search(r"\bINTO\b", cleaned, re.IGNORECASE):
            # PL/SQL and PL/pgSQL `SELECT ... INTO local_var FROM ...`: strip the
            # variable target before parsing, or sqlglot (and a naive regex) will
            # mistake the variable names for tables.
            cleaned = _INTO_BEFORE_FROM_RE.sub("", cleaned)
        access = embedded_sql.build_sql_access(cleaned, file_path, line, owner_symbol=owner_symbol, dialect=dialect)
        access.locking = bool(re.search(r"\bFOR\s+UPDATE\b", stmt_text, re.IGNORECASE))
        accesses.append(access)
    return accesses


# --------------------------------------------------------------------------- #
# The parser
# --------------------------------------------------------------------------- #

class SqlParser(LanguageParser):
    language = "sql"
    extensions = [".sql", ".ddl"]

    def parse(self, file_path: str, content: str) -> ParseResult:
        file_path = file_path.replace("\\", "/")
        dialect = sniff_dialect(content)
        result = ParseResult(file_path=file_path, language=self.language, parser_name=f"sqlglot_{dialect}")

        blocks = _find_top_level_blocks(content)
        cursor = 0
        total_stmts = 0
        parsed_stmts = 0

        for kind, name, h_start, h_end, body_text, body_start, b_end in blocks:
            # Everything between the cursor and this block's start is plain DDL.
            t, p = self._parse_plain_ddl(content, cursor, h_start, file_path, dialect, result)
            total_stmts += t
            parsed_stmts += p

            self._handle_procedural_block(
                kind, name, content, h_start, h_end, body_text, body_start, b_end, file_path, dialect, result,
            )
            cursor = b_end

        # Trailing plain DDL after the last procedural block (or the whole file
        # if there were none at all).
        t, p = self._parse_plain_ddl(content, cursor, len(content), file_path, dialect, result)
        total_stmts += t
        parsed_stmts += p

        result.parse_coverage = round(parsed_stmts / total_stmts, 4) if total_stmts else 1.0
        if result.parse_coverage < 1.0:
            result.diagnostics.append(
                ParseDiagnostic(
                    file_path=file_path, severity="WARNING",
                    message=f"{total_stmts - parsed_stmts} of {total_stmts} top-level statement(s) "
                    f"could not be parsed by sqlglot (dialect={dialect}) and were skipped.",
                )
            )
        return result

    # ------------------------------------------------------------------ #
    # Plain DDL: CREATE TABLE / INDEX / VIEW, ALTER TABLE
    # ------------------------------------------------------------------ #

    def _parse_plain_ddl(
        self, content: str, start: int, end: int, file_path: str, dialect: str, result: ParseResult,
    ) -> Tuple[int, int]:
        total = 0
        parsed = 0
        for stmt_text, offset in split_statements(content[start:end]):
            total += 1
            line = 1 + content[: start + offset].count("\n")
            try:
                expr = sqlglot.parse_one(stmt_text, read=dialect, error_level=sqlglot.ErrorLevel.IGNORE)
            except Exception:
                expr = None
            if expr is None:
                continue
            parsed += 1
            if isinstance(expr, exp.Create) and expr.kind == "TABLE" and isinstance(expr.this, exp.Schema):
                self._handle_create_table(expr, file_path, line, result)
            elif isinstance(expr, exp.Create) and expr.kind == "INDEX":
                self._handle_create_index(expr, file_path, line, result)
            elif isinstance(expr, exp.Create) and expr.kind == "VIEW":
                self._handle_create_view(expr, file_path, line, result)
            elif isinstance(expr, exp.Alter):
                self._handle_alter_table(expr, file_path, line, result)
        return total, parsed

    def _handle_create_table(self, expr, file_path: str, line: int, result: ParseResult) -> None:
        schema = expr.this
        table_name = schema.this.name.upper() if hasattr(schema.this, "name") else str(schema.this).upper()
        columns: List[str] = []
        pk_col: Optional[str] = None

        for col in schema.expressions:
            if isinstance(col, exp.ColumnDef):
                col_name = col.this.name if hasattr(col.this, "name") else str(col.this)
                columns.append(col_name)
                for c in col.constraints or []:
                    if isinstance(c.kind, exp.PrimaryKeyColumnConstraint):
                        pk_col = col_name
                result.symbols.append(
                    Symbol(
                        kind="COLUMN", name=col_name, qualified_name=f"{table_name}.{col_name}",
                        language=self.language, file_path=file_path, line_start=line, line_end=line,
                        parent=table_name, return_type=str(col.args.get("kind") or ""),
                    )
                )
            elif isinstance(col, exp.Constraint):
                self._handle_inline_fk(col, table_name, file_path, line, result)
            elif isinstance(col, exp.PrimaryKey):
                for e in col.expressions:
                    pk_col = e.name if hasattr(e, "name") else str(e)

        result.symbols.append(
            Symbol(
                kind="TABLE", name=table_name, qualified_name=table_name, language=self.language,
                file_path=file_path, line_start=line, line_end=line,
                properties={"primary_key": pk_col, "columns": columns},
            )
        )

    def _handle_inline_fk(self, constraint, table_name: str, file_path: str, line: int, result: ParseResult) -> None:
        for e in constraint.expressions:
            if not isinstance(e, exp.ForeignKey):
                continue
            ref = e.args.get("reference")
            if ref is None:
                continue
            ref_schema = ref.this
            target_table = ref_schema.this.name.upper() if hasattr(ref_schema.this, "name") else str(ref_schema.this).upper()
            fk_cols = [i.name for i in e.expressions]
            ref_cols = [i.name for i in ref_schema.expressions] if hasattr(ref_schema, "expressions") else []
            result.references.append(
                Reference(
                    from_symbol=table_name, target_name=target_table, kind="READS_FROM", file_path=file_path,
                    line=line, evidence=f"FOREIGN KEY ({', '.join(fk_cols)}) REFERENCES {target_table}({', '.join(ref_cols)})",
                    confidence=1.0,
                )
            )

    def _handle_create_index(self, expr, file_path: str, line: int, result: ParseResult) -> None:
        idx = expr.this
        idx_name = idx.this.name if hasattr(idx.this, "name") else str(idx.this)
        table = idx.args.get("table")
        table_name = table.this.name.upper() if table is not None and hasattr(table.this, "name") else ""
        result.symbols.append(
            Symbol(
                kind="TABLE", name=idx_name, qualified_name=idx_name, language=self.language,
                file_path=file_path, line_start=line, line_end=line, parent=table_name,
                properties={"index_on": table_name, "is_index": True},
            )
        )

    def _handle_create_view(self, expr, file_path: str, line: int, result: ParseResult) -> None:
        view_name = expr.this.name.upper() if hasattr(expr.this, "name") else str(expr.this).upper()
        select = expr.args.get("expression")
        source_tables = [t.name.upper() for t in select.find_all(exp.Table)] if select is not None else []
        result.symbols.append(
            Symbol(
                kind="VIEW", name=view_name, qualified_name=view_name, language=self.language,
                file_path=file_path, line_start=line, line_end=line, properties={"source_tables": source_tables},
            )
        )
        for src in source_tables:
            result.references.append(
                Reference(
                    from_symbol=view_name, target_name=src, kind="READS_FROM",
                    file_path=file_path, line=line, evidence=f"VIEW {view_name} selects from {src}",
                )
            )

    def _handle_alter_table(self, expr, file_path: str, line: int, result: ParseResult) -> None:
        table_name = expr.this.name.upper() if hasattr(expr.this, "name") else str(expr.this).upper()
        for action in expr.args.get("actions") or []:
            for fk in action.find_all(exp.ForeignKey):
                ref = fk.args.get("reference")
                if ref is None:
                    continue
                ref_schema = ref.this
                target = ref_schema.this.name.upper() if hasattr(ref_schema.this, "name") else str(ref_schema.this).upper()
                result.references.append(
                    Reference(
                        from_symbol=table_name, target_name=target, kind="READS_FROM",
                        file_path=file_path, line=line, evidence=f"ALTER TABLE {table_name} ADD FOREIGN KEY ... REFERENCES {target}",
                    )
                )

    # ------------------------------------------------------------------ #
    # Procedural blocks: PROCEDURE / FUNCTION / TRIGGER / PACKAGE
    # ------------------------------------------------------------------ #

    def _handle_procedural_block(
        self, kind: str, name: str, content: str, h_start: int, h_end: int,
        body_text: str, body_start: int, b_end: int,
        file_path: str, dialect: str, result: ParseResult, parent: Optional[str] = None,
        line_offset: int = 0,
    ) -> None:
        """`line_offset` is (the file's real line number at content[0]) - 1: zero
        for a top-level block, where `content` is the whole file, and non-zero
        when recursing into a PACKAGE BODY's members, where `content` is only
        the package's own body text and its line numbers must be re-based onto
        the real file."""
        name_upper = name.upper()
        qname = f"{parent}.{name_upper}" if parent else name_upper
        header_text = content[h_start:h_end]
        line_start = line_offset + 1 + content[:h_start].count("\n")
        line_end = line_offset + 1 + content[:b_end].count("\n")
        body_line_start = line_offset + 1 + content[:body_start].count("\n")

        symbol_kind = {"PROCEDURE": "PROCEDURE", "FUNCTION": "PROCEDURE", "TRIGGER": "TRIGGER"}.get(kind)

        if kind in ("PACKAGE", "PACKAGE BODY"):
            result.symbols.append(
                Symbol(
                    kind="PROCEDURE", name=name_upper, qualified_name=qname, language=self.language,
                    file_path=file_path, line_start=line_start, line_end=line_end,
                    properties={"package": True, "is_body": kind == "PACKAGE BODY"},
                )
            )
            for m in _MEMBER_HEADER_RE.finditer(body_text):
                member_kind = _normalize_kind(m.group("kind"))
                member_name = m.group("name")
                member_result = _extract_block_body(body_text, m.end())
                if member_result is None:
                    continue
                member_body_text, member_body_start, member_end = member_result
                self._handle_procedural_block(
                    member_kind, member_name, body_text, m.start(), m.end(),
                    member_body_text, member_body_start, member_end,
                    file_path, dialect, result, parent=qname, line_offset=body_line_start - 1,
                )
            return

        params = _parse_param_list(header_text)
        param_names = [p["name"] for p in params]

        symbol = Symbol(
            kind=symbol_kind or "PROCEDURE", name=name_upper, qualified_name=qname, language=self.language,
            file_path=file_path, line_start=line_start, line_end=line_end, parent=parent,
            signature=f"{name_upper}({', '.join(param_names)})",
        )

        if kind == "TRIGGER":
            # The AFTER/BEFORE ... ON table clause sits between the header and
            # BEGIN (e.g. "TRIGGER x\nAFTER UPDATE ON t\nFOR EACH ROW\nBEGIN"),
            # which is no longer part of body_text now that body_text starts
            # strictly after BEGIN (see _extract_begin_end_body).
            prologue = content[h_end:body_start]
            trig_match = _TRIGGER_TARGET_RE.search(header_text + prologue)
            if trig_match:
                target_table = trig_match.group("table").strip('"').upper()
                symbol.properties["timing"] = trig_match.group("timing").upper()
                symbol.properties["events"] = trig_match.group("events").strip().upper()
                symbol.properties["table"] = target_table
                result.references.append(
                    Reference(
                        from_symbol=qname, target_name=target_table, kind="EXECUTES", file_path=file_path,
                        line=line_start, evidence=f"TRIGGER {name_upper} ON {target_table}",
                    )
                )

        result.symbols.append(symbol)

        for access in extract_body_sql_accesses(body_text, file_path, body_line_start, qname, dialect):
            result.sql_accesses.append(access)
            edge_kind = "WRITES_TO" if access.verb in ("INSERT", "UPDATE", "DELETE", "MERGE") else "READS_FROM"
            for table in access.tables:
                result.references.append(
                    Reference(
                        from_symbol=qname, target_name=table, kind=edge_kind, file_path=file_path,
                        line=access.line, evidence=access.snippet, confidence=access.confidence,
                    )
                )
