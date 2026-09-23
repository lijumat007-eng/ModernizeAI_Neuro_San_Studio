# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Golden-fixture tests for the tree-sitter-backed C/C++ parser: namespaces,
classes/structs, out-of-line `Class::method` definitions (the pattern that
defeats a naive regex parser, since the method body is physically separate
from the field declarations it references), templates, inheritance,
adjacent-string-literal SQL concatenation (`"a" "b"`, distinct from Java's
`"a" + "b"`), plain C structs/functions, and the `.h` C-vs-C++ content sniff
in the registry.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))

from coded_tools.modernize.parsers.lang.cpp import CParser, CppParser, simple_type_name
from coded_tools.modernize.parsers.registry import ParserRegistry

CPP_SOURCE = '''#include <string>
#include "PaymentGateway.h"

namespace acme {

class OrderService : public BaseService, public Auditable {
public:
    OrderService();
    Order findOrder(std::string id, bool includeLines);

    template<typename T>
    T convert(T val) { return val; }

private:
    PaymentGateway* gateway;
    std::map<std::string, Order> cache;
};

Order OrderService::findOrder(std::string id, bool includeLines) {
    std::string sql = "SELECT * FROM " "ORDERS WHERE cust = ?";
    gateway->charge(id);
    PaymentGateway* pg = new PaymentGateway();
    pg->charge(id);
    return Order();
}

}  // namespace acme
'''

C_SOURCE = '''#include <stdio.h>
#include "db.h"

struct Order {
    int id;
    char* customer;
};

int findOrder(int id) {
    char sql[256];
    sprintf(sql, "SELECT * FROM ORDERS WHERE id = %d", id);
    execSql(sql);
    return 0;
}
'''


class TestCppParser(unittest.TestCase):

    def setUp(self):
        self.result = CppParser().parse("OrderService.cpp", CPP_SOURCE)

    def test_parses_without_syntax_errors(self):
        self.assertEqual(self.result.parse_coverage, 1.0)

    def test_namespaced_class_qualified_name(self):
        classes = {s.qualified_name for s in self.result.symbols if s.kind == "CLASS"}
        self.assertIn("acme::OrderService", classes)

    def test_inheritance_captured(self):
        cls = next(s for s in self.result.symbols if s.qualified_name == "acme::OrderService")
        self.assertIn("BaseService", cls.base_types)
        self.assertIn("Auditable", cls.base_types)
        kinds = {(r.kind, r.target_name) for r in self.result.references}
        self.assertIn(("INHERITS", "BaseService"), kinds)

    def test_out_of_line_method_attached_to_class(self):
        methods = [
            s for s in self.result.symbols
            if s.kind == "METHOD" and s.name == "findOrder" and s.parent == "acme::OrderService"
        ]
        self.assertTrue(methods, "out-of-line Class::method definition must be attached to its class")

    def test_template_method_extracted(self):
        convert = next(s for s in self.result.symbols if s.name == "convert")
        self.assertEqual(convert.parent, "acme::OrderService")

    def test_out_of_line_method_resolves_field_access_via_propagated_field_types(self):
        # `gateway->charge(id)` is inside the OUT-OF-LINE definition, physically
        # separate from the `PaymentGateway* gateway;` field declaration. The
        # parser must have propagated the class's field types to resolve this.
        calls = [r.target_name for r in self.result.references if r.kind == "CALLS"]
        self.assertIn("PaymentGateway", calls)

    def test_local_pointer_variable_call_resolved(self):
        instantiate = [r for r in self.result.references if r.kind == "INSTANTIATES"]
        self.assertTrue(any(r.target_name == "PaymentGateway" for r in instantiate))

    def test_adjacent_string_literal_sql_concatenation(self):
        # C/C++ concatenates adjacent literals with NO operator at all:
        # "SELECT * FROM " "ORDERS WHERE cust = ?" is one string, not two.
        sql = [s for s in self.result.sql_accesses if s.verb == "SELECT"]
        self.assertTrue(sql)
        self.assertIn("ORDERS", sql[0].tables)

    def test_includes_recorded(self):
        includes = [r.target_name for r in self.result.references if r.kind == "INCLUDES"]
        self.assertIn("string", includes)
        self.assertIn("PaymentGateway.h", includes)

    def test_simple_type_name_strips_pointers_and_templates(self):
        self.assertEqual(simple_type_name("std::shared_ptr<Order>"), "shared_ptr")
        self.assertEqual(simple_type_name("PaymentGateway*"), "PaymentGateway")
        self.assertEqual(simple_type_name("int"), "int")


class TestCParser(unittest.TestCase):

    def setUp(self):
        self.result = CParser().parse("legacy.c", C_SOURCE)

    def test_parses_without_syntax_errors(self):
        self.assertEqual(self.result.parse_coverage, 1.0)

    def test_struct_and_fields_extracted(self):
        struct = next(s for s in self.result.symbols if s.kind == "STRUCT")
        self.assertEqual(struct.name, "Order")
        field_names = {s.name for s in self.result.symbols if s.kind == "FIELD"}
        self.assertEqual(field_names, {"id", "customer"})

    def test_free_function_extracted(self):
        func = next(s for s in self.result.symbols if s.kind == "FUNCTION")
        self.assertEqual(func.name, "findOrder")

    def test_format_string_sql_literal_still_captured(self):
        # A dynamically-built SQL string (via sprintf into a buffer later passed
        # to execSql by variable name) can't be traced end-to-end without dataflow
        # analysis, but the literal itself must still be found.
        self.assertTrue(any(s.verb == "SELECT" for s in self.result.sql_accesses))


class TestHeaderSniffing(unittest.TestCase):

    def setUp(self):
        self.registry = ParserRegistry()

    def test_plain_c_header_dispatches_to_c_parser(self):
        parser = self.registry.parser_for("db.h", "struct Foo { int x; };\nint bar(void);\n")
        self.assertEqual(parser.language, "c")

    def test_cpp_header_dispatches_to_cpp_parser(self):
        parser = self.registry.parser_for(
            "Gateway.h", "namespace acme {\nclass Gateway {\npublic:\n  void charge();\n};\n}\n",
        )
        self.assertEqual(parser.language, "cpp")


if __name__ == "__main__":
    unittest.main()
