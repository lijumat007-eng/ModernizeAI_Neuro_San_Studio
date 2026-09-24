# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Golden-fixture tests for GraphBuilder: source-qualified code nodes vs.
canonical shared-resource nodes (tables/procedures), edge aggregation
(weight + evidence_list instead of one edge per call site), external
placeholders for unresolved references, and the cross-source scenario this
whole layer exists for - a table referenced from one source before the
source that actually defines it is scanned must get upgraded in place, not
end up as two separate nodes.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))

from coded_tools.modernize.graph.graph_builder import GraphBuilder
from coded_tools.modernize.graph.graph_engine import KnowledgeGraphEngine
from coded_tools.modernize.memory.memory_manager_tool import MemoryFabric
from coded_tools.modernize.parsers.pipeline import parse_repository

JAVA_SOURCE = """package com.acme;
public class OrderService {
    private PaymentGateway gateway;
    public void charge(String id) {
        gateway.charge(id);
        gateway.charge(id);
        java.util.List<String> l = new java.util.ArrayList<>();
        String sql = "SELECT * FROM ORDERS WHERE id = ?";
    }
}
"""

GATEWAY_SOURCE = """package com.acme;
public class PaymentGateway {
    public void charge(String id) {}
}
"""

DDL_SOURCE = "CREATE TABLE ORDERS (id VARCHAR(50) PRIMARY KEY, amount DECIMAL(10,2));"


def _build_fabric(files: dict) -> MemoryFabric:
    fabric = MemoryFabric()
    for path, content in files.items():
        fabric.raw.ingest_file(path, path, content)
    return fabric


class TestGraphBuilderBasics(unittest.TestCase):
    def setUp(self):
        self.fabric = _build_fabric(
            {
                "OrderService.java": JAVA_SOURCE,
                "PaymentGateway.java": GATEWAY_SOURCE,
            }
        )
        parse_repository(self.fabric)
        self.kg = KnowledgeGraphEngine()
        self.stats = GraphBuilder.build(self.kg, self.fabric, source_id="repoA")

    def test_class_nodes_are_source_qualified(self):
        self.assertTrue(self.kg.graph.has_node("repoA::com.acme.OrderService"))
        self.assertTrue(self.kg.graph.has_node("repoA::com.acme.PaymentGateway"))

    def test_repeated_calls_merge_into_one_weighted_edge(self):
        edge = self.kg.graph.get_edge_data(
            "repoA::com.acme.OrderService",
            "repoA::com.acme.PaymentGateway",
            key="CALLS",
        )
        self.assertIsNotNone(edge)
        self.assertEqual(edge["weight"], 2)  # gateway.charge() called twice

    def test_unresolved_reference_gets_external_placeholder(self):
        # java.util.ArrayList is never defined in this fabric.
        external_nodes = [n for n, d in self.kg.graph.nodes(data=True) if d.get("node_type") == "External"]
        self.assertTrue(any("ArrayList" in n for n in external_nodes))

    def test_external_edge_has_low_confidence(self):
        external_node = next(n for n in self.kg.graph.nodes if n.startswith("external::") and "ArrayList" in n)
        edge = self.kg.graph.get_edge_data("repoA::com.acme.OrderService", external_node, key="INSTANTIATES")
        self.assertLessEqual(edge["confidence"], 0.3)

    def test_embedded_sql_creates_table_placeholder(self):
        self.assertTrue(self.kg.graph.has_node("ORDERS"))
        node = self.kg.graph.nodes["ORDERS"]
        self.assertEqual(node["extractor"], "inferred_from_reference")
        self.assertLess(node["confidence"], 1.0)

    def test_table_node_is_not_source_qualified(self):
        self.assertFalse(self.kg.graph.has_node("repoA::ORDERS"))


class TestCrossSourceTableUnification(unittest.TestCase):
    """The scenario this design exists for: Java repo A references ORDERS
    before the DB source that defines it is ever scanned; later the DB
    source is scanned and must upgrade the SAME node, not create a second."""

    def test_placeholder_table_is_upgraded_not_duplicated(self):
        kg = KnowledgeGraphEngine()

        # 1. Scan the Java repo first - ORDERS doesn't exist yet anywhere.
        fabric_a = _build_fabric({"OrderService.java": JAVA_SOURCE, "PaymentGateway.java": GATEWAY_SOURCE})
        parse_repository(fabric_a)
        GraphBuilder.build(kg, fabric_a, source_id="repoA")

        self.assertTrue(kg.graph.has_node("ORDERS"))
        self.assertEqual(kg.graph.nodes["ORDERS"]["extractor"], "inferred_from_reference")
        nodes_before = kg.graph.number_of_nodes()

        # 2. Now scan the DB source's DDL - the SAME table.
        fabric_db = _build_fabric({"schema.ddl": DDL_SOURCE})
        parse_repository(fabric_db)
        GraphBuilder.build(kg, fabric_db, source_id="dbsrc")

        # Still exactly one ORDERS node, now upgraded to the real definition.
        self.assertTrue(kg.graph.has_node("ORDERS"))
        self.assertEqual(kg.graph.number_of_nodes(), nodes_before)  # no duplicate created
        self.assertEqual(kg.graph.nodes["ORDERS"]["extractor"], "sql_parser")
        self.assertEqual(kg.graph.nodes["ORDERS"]["confidence"], 1.0)

        # And the edge from the Java code still points at that one real node.
        edge = kg.graph.get_edge_data("repoA::com.acme.OrderService", "ORDERS", key="READS_FROM")
        self.assertIsNotNone(edge)


if __name__ == "__main__":
    unittest.main()
