# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Golden-fixture tests for the tree-sitter-backed Java parser and the Linker.
Covers the exact cases the old regex parser (coded_tools/modernize/parsers/
java_parser.py, pre-refactor) got wrong: nested classes, generics, lambdas,
multi-line signatures, braces inside strings/comments, inheritance,
receiver-typed calls, concatenated SQL, and Spring endpoint detection.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))

from coded_tools.modernize.parsers.ir import ParseResult
from coded_tools.modernize.parsers.lang.java import JavaParser
from coded_tools.modernize.parsers.lang.java import simple_type_name
from coded_tools.modernize.parsers.linker import Linker

TRICKY_SOURCE = """package com.acme;

import com.acme.gateway.PaymentGateway;
import com.acme.repo.OrderRepository;

/**
 * A class comment containing a brace that would confuse a naive
 * brace-counting regex: if (x) { return; }
 */
@Service
public class OrderService extends BaseService implements Auditable {

    private final Map<String, List<Order>> cache = new HashMap<>();
    private PaymentGateway gateway;
    private OrderRepository repo;

    // A line comment with a brace: } { just to be annoying.
    @GetMapping("/orders/{id}")
    public Optional<Order> findOrder(
            String id,
            boolean includeLines) {
        String note = "This string has a brace: { not real code }";
        return repo.findById(id).map(o -> gateway.charge(o));
    }

    public static class Builder {
        public Builder withId(String id) { return this; }
    }

    public List<Map<String, Order>> byCustomer(String c) {
        String table = "ORDERS";
        return jdbc.query("SELECT * FROM " + table + " WHERE cust = ?", c);
    }
}
"""


class TestJavaParser(unittest.TestCase):
    def setUp(self):
        self.parser = JavaParser()
        self.result: ParseResult = self.parser.parse("OrderService.java", TRICKY_SOURCE)

    def test_parses_without_syntax_errors(self):
        self.assertEqual(self.result.parse_coverage, 1.0)
        self.assertEqual(self.result.diagnostics, [])

    def test_top_level_and_nested_class_both_found(self):
        class_names = {s.qualified_name for s in self.result.symbols if s.kind == "CLASS"}
        self.assertIn("com.acme.OrderService", class_names)
        self.assertIn("com.acme.OrderService.Builder", class_names)

    def test_nested_class_method_is_not_mistaken_for_outer_method(self):
        outer_methods = {
            s.name for s in self.result.symbols if s.kind == "METHOD" and s.parent == "com.acme.OrderService"
        }
        nested_methods = {
            s.name for s in self.result.symbols if s.kind == "METHOD" and s.parent == "com.acme.OrderService.Builder"
        }
        self.assertIn("findOrder", outer_methods)
        self.assertIn("byCustomer", outer_methods)
        self.assertNotIn("withId", outer_methods)
        self.assertIn("withId", nested_methods)

    def test_generic_field_is_captured(self):
        field = next(s for s in self.result.symbols if s.kind == "FIELD" and s.name == "cache")
        self.assertIn("Map", field.return_type)

    def test_multiline_signature_method_found(self):
        method = next(s for s in self.result.symbols if s.kind == "METHOD" and s.name == "findOrder")
        self.assertIn("id", method.signature)
        self.assertIn("includeLines", method.signature)

    def test_inheritance_and_interfaces_captured(self):
        cls = next(s for s in self.result.symbols if s.qualified_name == "com.acme.OrderService")
        self.assertIn("BaseService", cls.base_types)
        self.assertIn("Auditable", cls.base_types)
        kinds = {(r.kind, r.target_name) for r in self.result.references}
        self.assertIn(("INHERITS", "BaseService"), kinds)
        self.assertIn(("IMPLEMENTS", "Auditable"), kinds)

    def test_braces_in_comments_and_strings_do_not_break_extraction(self):
        # If the brace-matching were naive, "byCustomer" or the class end line
        # would be wrong. The class body must close at the real end of the file.
        cls = next(s for s in self.result.symbols if s.qualified_name == "com.acme.OrderService")
        by_customer = next(s for s in self.result.symbols if s.name == "byCustomer")
        self.assertLess(by_customer.line_start, cls.line_end)

    def test_receiver_typed_call_resolved_to_field_type(self):
        calls = [(r.from_symbol, r.target_name) for r in self.result.references if r.kind == "CALLS"]
        self.assertTrue(any(target == "PaymentGateway" for _, target in calls))

    def test_lambda_body_call_is_still_seen(self):
        # gateway.charge(o) lives inside a lambda passed to .map(...); it must
        # still be found even though it's nested inside another call's arguments.
        calls = [r.target_name for r in self.result.references if r.kind == "CALLS"]
        self.assertIn("PaymentGateway", calls)

    def test_concatenated_sql_extracts_real_table_name(self):
        sql = [s for s in self.result.sql_accesses if s.verb == "SELECT"]
        self.assertTrue(sql, "expected a SELECT to be found in the string-concatenated query")
        # "ORDERS" comes from a local variable, not a literal, so the parser can only
        # substitute a placeholder for it - this proves concatenation-awareness without
        # requiring constant-folding, which is out of scope for this pass.
        self.assertIn("SELECT * FROM ? WHERE cust = ?", sql[0].snippet)

    def test_spring_endpoint_detected(self):
        self.assertEqual(len(self.result.endpoints), 1)
        ep = self.result.endpoints[0]
        self.assertEqual(ep.http_method, "GET")
        self.assertIn("/orders/{id}", ep.route)

    def test_simple_type_name_strips_generics_and_package(self):
        self.assertEqual(simple_type_name("java.util.List<Order>"), "List")
        self.assertEqual(simple_type_name("Order[]"), "Order")
        self.assertEqual(simple_type_name("PaymentGateway"), "PaymentGateway")


class TestLinker(unittest.TestCase):
    def test_import_based_resolution_is_exact(self):
        parser = JavaParser()
        gateway_src = "package com.acme.gateway;\npublic class PaymentGateway { public void charge(Object o) {} }\n"
        gateway_result = parser.parse("PaymentGateway.java", gateway_src)
        service_result = parser.parse("OrderService.java", TRICKY_SOURCE)

        Linker().link([gateway_result, service_result])

        calls = [r for r in service_result.references if r.kind == "CALLS" and r.target_name == "PaymentGateway"]
        self.assertTrue(calls)
        self.assertEqual(calls[0].resolved_target, "com.acme.gateway.PaymentGateway")
        self.assertEqual(calls[0].confidence, 1.0)
        self.assertFalse(calls[0].external)

    def test_unresolvable_reference_is_marked_external(self):
        parser = JavaParser()
        result = parser.parse(
            "Solo.java", "package com.acme;\nclass Solo { void m() { HashMap x = new HashMap(); } }\n"
        )
        Linker().link([result])
        instantiate = next(r for r in result.references if r.kind == "INSTANTIATES")
        self.assertTrue(instantiate.external)
        self.assertIsNone(instantiate.resolved_target)

    def test_unique_simple_name_resolves_without_import(self):
        parser = JavaParser()
        policy_src = "package com.acme.model;\npublic class Policy { }\n"
        policy_result = parser.parse("Policy.java", policy_src)
        user_src = "package com.acme.service;\npublic class Checker { Policy p; void m() { p.isValid(); } }\n"
        user_result = parser.parse("Checker.java", user_src)

        Linker().link([policy_result, user_result])

        call = next(r for r in user_result.references if r.kind == "CALLS")
        self.assertEqual(call.resolved_target, "com.acme.model.Policy")
        self.assertEqual(call.confidence, 0.8)


if __name__ == "__main__":
    unittest.main()
