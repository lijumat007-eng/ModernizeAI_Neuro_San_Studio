# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Golden-fixture tests for the SQL/PL-SQL parser: CREATE TABLE (columns, PK,
inline FK), CREATE INDEX, CREATE VIEW, and procedural bodies across all three
dialects this tool targets - Postgres (`$$...$$`), Oracle (`IS ... BEGIN ...
END;`, which sqlglot's own Oracle dialect cannot parse at all), and T-SQL
(`AS BEGIN ... END GO`, whose unparenthesized `@param` list would otherwise
fuse with the body's first statement). Also covers `SELECT ... INTO var FROM`
(PL/SQL's variable-target syntax, easily mistaken for real tables),
`FOR UPDATE` locking, triggers, and packages with nested member procedures.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))

from coded_tools.modernize.parsers.lang.sql import SqlParser, split_statements

TABLE_DDL = """
CREATE TABLE CUSTOMER_ACCOUNT (
    customer_id BIGINT PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);

CREATE TABLE POLICY_MASTER (
    policy_number VARCHAR(50) PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    CONSTRAINT fk_policy_customer FOREIGN KEY (customer_id) REFERENCES CUSTOMER_ACCOUNT(customer_id)
);

CREATE INDEX idx_policy_customer ON POLICY_MASTER(customer_id);
"""

POSTGRES_SP = """CREATE OR REPLACE PROCEDURE SP_PROCESS_CLAIM(
    p_claim_id IN VARCHAR,
    p_policy_number IN VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_deductible DECIMAL(10,2);
BEGIN
    SELECT deductible
    INTO v_deductible
    FROM POLICY_MASTER
    WHERE policy_number = p_policy_number
    FOR UPDATE;

    UPDATE POLICY_MASTER
    SET remaining_coverage = remaining_coverage - v_deductible
    WHERE policy_number = p_policy_number;

    INSERT INTO CLAIM_AUDIT_LOG (claim_id) VALUES (p_claim_id);
END;
$$;
"""

ORACLE_SP = """CREATE OR REPLACE PROCEDURE SP_PROCESS_CLAIM (
    p_claim_id IN VARCHAR2,
    p_policy_number IN VARCHAR2
) IS
    v_deductible NUMBER;
BEGIN
    SELECT deductible INTO v_deductible FROM POLICY_MASTER WHERE policy_number = p_policy_number FOR UPDATE;
    UPDATE POLICY_MASTER SET remaining_coverage = remaining_coverage - v_deductible WHERE policy_number = p_policy_number;
    INSERT INTO CLAIM_AUDIT_LOG (claim_id) VALUES (p_claim_id);
END SP_PROCESS_CLAIM;
/
"""

TSQL_SP = """CREATE PROCEDURE dbo.SP_PROCESS_CLAIM
    @p_claim_id VARCHAR(50),
    @p_policy_number VARCHAR(50)
AS
BEGIN
    UPDATE POLICY_MASTER SET remaining_coverage = remaining_coverage - 1 WHERE policy_number = @p_policy_number;
    INSERT INTO CLAIM_AUDIT_LOG (claim_id) VALUES (@p_claim_id);
END
GO
"""

TRIGGER_SQL = """CREATE OR REPLACE TRIGGER trg_claims_audit
AFTER UPDATE ON CLAIMS_RECORD
FOR EACH ROW
BEGIN
    INSERT INTO CLAIM_AUDIT_LOG (claim_id, action) VALUES (:NEW.claim_id, 'UPDATED');
END;
/
"""

PACKAGE_SQL = """CREATE OR REPLACE PACKAGE BODY claims_pkg IS

    PROCEDURE process_claim(p_claim_id IN VARCHAR2) IS
    BEGIN
        UPDATE CLAIMS_RECORD SET status = 'PROCESSED' WHERE claim_id = p_claim_id;
    END process_claim;

    FUNCTION get_status(p_claim_id IN VARCHAR2) RETURN VARCHAR2 IS
        v_status VARCHAR2(30);
    BEGIN
        SELECT status INTO v_status FROM CLAIMS_RECORD WHERE claim_id = p_claim_id;
        RETURN v_status;
    END get_status;

END claims_pkg;
/
"""


class TestTableDdl(unittest.TestCase):

    def setUp(self):
        self.result = SqlParser().parse("schema.ddl", TABLE_DDL)

    def test_parses_without_errors(self):
        self.assertEqual(self.result.parse_coverage, 1.0)

    def test_tables_and_columns_extracted(self):
        tables = {s.qualified_name: s for s in self.result.symbols if s.kind == "TABLE" and not s.properties.get("is_index")}
        self.assertEqual(set(tables), {"CUSTOMER_ACCOUNT", "POLICY_MASTER"})
        columns = {s.name for s in self.result.symbols if s.kind == "COLUMN" and s.parent == "POLICY_MASTER"}
        self.assertEqual(columns, {"policy_number", "customer_id"})

    def test_primary_key_detected(self):
        tables = {s.qualified_name: s for s in self.result.symbols if s.kind == "TABLE"}
        self.assertEqual(tables["POLICY_MASTER"].properties["primary_key"], "policy_number")

    def test_inline_foreign_key_becomes_reference(self):
        fk = [r for r in self.result.references if r.kind == "READS_FROM" and r.from_symbol == "POLICY_MASTER"]
        self.assertTrue(fk)
        self.assertEqual(fk[0].target_name, "CUSTOMER_ACCOUNT")

    def test_index_recorded_with_target_table(self):
        idx = next(s for s in self.result.symbols if s.properties.get("is_index"))
        self.assertEqual(idx.parent, "POLICY_MASTER")


class TestPostgresProcedure(unittest.TestCase):

    def setUp(self):
        self.result = SqlParser().parse("sp.sql", POSTGRES_SP)

    def test_parses_without_errors(self):
        self.assertEqual(self.result.parse_coverage, 1.0)

    def test_all_three_statements_found(self):
        verbs = sorted(a.verb for a in self.result.sql_accesses)
        self.assertEqual(verbs, ["INSERT", "SELECT", "UPDATE"])

    def test_select_into_variable_resolves_to_real_table_not_the_variable(self):
        select = next(a for a in self.result.sql_accesses if a.verb == "SELECT")
        # A naive parser would report "V_DEDUCTIBLE" (the INTO target) as the
        # table; it must report the real FROM table instead.
        self.assertEqual(select.tables, ["POLICY_MASTER"])

    def test_for_update_lock_detected(self):
        select = next(a for a in self.result.sql_accesses if a.verb == "SELECT")
        self.assertTrue(select.locking)
        other = [a for a in self.result.sql_accesses if a.verb != "SELECT"]
        self.assertTrue(all(not a.locking for a in other))

    def test_procedure_symbol_and_edges(self):
        proc = next(s for s in self.result.symbols if s.kind == "PROCEDURE")
        self.assertEqual(proc.name, "SP_PROCESS_CLAIM")
        writes = {r.target_name for r in self.result.references if r.kind == "WRITES_TO"}
        self.assertEqual(writes, {"POLICY_MASTER", "CLAIM_AUDIT_LOG"})


class TestOracleProcedure(unittest.TestCase):
    """sqlglot's own Oracle dialect cannot parse `IS ... BEGIN ... END;` at all -
    this exercises the parser's own BEGIN/END depth scanner instead."""

    def setUp(self):
        self.result = SqlParser().parse("sp_oracle.sql", ORACLE_SP)

    def test_parses_without_errors(self):
        self.assertEqual(self.result.parse_coverage, 1.0)

    def test_all_three_statements_found_with_correct_lines(self):
        by_verb = {a.verb: a for a in self.result.sql_accesses}
        self.assertEqual(set(by_verb), {"SELECT", "UPDATE", "INSERT"})
        # Lines 1-indexed within ORACLE_SP: the SELECT is on line 6.
        self.assertEqual(by_verb["SELECT"].line, 6)
        self.assertTrue(by_verb["SELECT"].locking)


class TestTsqlProcedure(unittest.TestCase):
    """T-SQL's unparenthesized `@param TYPE, ...` list has no `;` before
    `AS BEGIN`, so it fuses with the body's first statement unless the
    extractor starts the body strictly after BEGIN, not after the header."""

    def setUp(self):
        self.result = SqlParser().parse("sp_tsql.sql", TSQL_SP)

    def test_parses_without_errors(self):
        self.assertEqual(self.result.parse_coverage, 1.0)

    def test_both_statements_found_despite_unparenthesized_param_list(self):
        verbs = sorted(a.verb for a in self.result.sql_accesses)
        self.assertEqual(verbs, ["INSERT", "UPDATE"])


class TestTrigger(unittest.TestCase):

    def setUp(self):
        self.result = SqlParser().parse("trigger.sql", TRIGGER_SQL)

    def test_trigger_metadata_extracted(self):
        trig = next(s for s in self.result.symbols if s.kind == "TRIGGER")
        self.assertEqual(trig.properties["timing"], "AFTER")
        self.assertEqual(trig.properties["table"], "CLAIMS_RECORD")

    def test_trigger_body_lineage(self):
        writes = {r.target_name for r in self.result.references if r.kind == "WRITES_TO"}
        self.assertIn("CLAIM_AUDIT_LOG", writes)


class TestPackage(unittest.TestCase):
    """A PACKAGE BODY has no BEGIN of its own - only its members do - which
    means naive depth-1 BEGIN/END matching would misidentify the first
    member's END as the package's own closing END and silently drop everything
    after it (including the second member entirely)."""

    def setUp(self):
        self.result = SqlParser().parse("package.sql", PACKAGE_SQL)

    def test_parses_without_errors(self):
        self.assertEqual(self.result.parse_coverage, 1.0)

    def test_both_members_found_not_just_the_first(self):
        members = {s.qualified_name for s in self.result.symbols if s.kind == "PROCEDURE" and s.parent == "CLAIMS_PKG"}
        self.assertEqual(members, {"CLAIMS_PKG.PROCESS_CLAIM", "CLAIMS_PKG.GET_STATUS"})

    def test_member_bodies_have_correct_absolute_line_numbers(self):
        # Re-based onto the real file, not relative to the package body slice.
        process_claim = next(s for s in self.result.symbols if s.qualified_name == "CLAIMS_PKG.PROCESS_CLAIM")
        self.assertEqual(process_claim.line_start, 3)

    def test_each_member_owns_its_own_sql_access(self):
        by_owner = {a.owner_symbol: a for a in self.result.sql_accesses}
        self.assertIn("CLAIMS_PKG.PROCESS_CLAIM", by_owner)
        self.assertIn("CLAIMS_PKG.GET_STATUS", by_owner)


class TestSplitStatements(unittest.TestCase):

    def test_semicolon_inside_parens_does_not_split(self):
        stmts = split_statements("INSERT INTO t (a, b) VALUES (1, 2); SELECT 1")
        self.assertEqual(len(stmts), 2)

    def test_semicolon_inside_string_does_not_split(self):
        stmts = split_statements("INSERT INTO t (a) VALUES ('x;y'); SELECT 1")
        self.assertEqual(len(stmts), 2)
        self.assertIn("x;y", stmts[0][0])

    def test_line_comment_is_not_a_statement(self):
        stmts = split_statements("-- comment with ; a semicolon\nSELECT 1;")
        self.assertEqual(len(stmts), 1)
        self.assertNotIn("comment", stmts[0][0])


if __name__ == "__main__":
    unittest.main()
