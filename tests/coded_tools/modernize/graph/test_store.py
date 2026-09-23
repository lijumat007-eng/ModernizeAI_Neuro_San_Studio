# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Tests for SqliteGraphStore (save/load round-trip, survives a fresh process -
simulated by a brand-new GraphStore instance against the same file) and for
GraphBuilder.remove_source_nodes, which is what makes an incremental
per-source rescan possible without touching other sources' nodes or shared
canonical tables.
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath("."))

from coded_tools.modernize.graph.graph_builder import GraphBuilder, remove_source_nodes
from coded_tools.modernize.graph.graph_engine import KnowledgeGraphEngine
from coded_tools.modernize.graph.store import SqliteGraphStore
from coded_tools.modernize.memory.memory_manager_tool import MemoryFabric
from coded_tools.modernize.parsers.pipeline import parse_repository

JAVA_A = "package com.a;\npublic class Foo { void m() { bar(); } }\n"
JAVA_B = "package com.b;\npublic class Baz { }\n"
DDL = "CREATE TABLE T1 (id INT PRIMARY KEY);"


def _fabric(files: dict) -> MemoryFabric:
    fabric = MemoryFabric()
    for path, content in files.items():
        fabric.raw.ingest_file(path, path, content)
    return fabric


class TestSqliteGraphStore(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="modernize_graphstore_")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _built_kg(self) -> KnowledgeGraphEngine:
        fabric = _fabric({"Foo.java": JAVA_A})
        parse_repository(fabric)
        kg = KnowledgeGraphEngine()
        GraphBuilder.build(kg, fabric, source_id="repoA")
        return kg

    def test_save_then_load_round_trips_nodes_and_edges(self):
        store = SqliteGraphStore(root_dir=self.tmp_dir)
        kg = self._built_kg()
        store.save("proj1", kg)

        reloaded = store.load("proj1")
        self.assertEqual(reloaded.graph.number_of_nodes(), kg.graph.number_of_nodes())
        self.assertEqual(reloaded.graph.number_of_edges(), kg.graph.number_of_edges())
        self.assertTrue(reloaded.graph.has_node("repoA::com.a.Foo"))

    def test_node_properties_survive_round_trip(self):
        store = SqliteGraphStore(root_dir=self.tmp_dir)
        kg = self._built_kg()
        store.save("proj1", kg)
        reloaded = store.load("proj1")
        original = kg.graph.nodes["repoA::com.a.Foo"]
        restored = reloaded.graph.nodes["repoA::com.a.Foo"]
        self.assertEqual(original["node_type"], restored["node_type"])
        self.assertEqual(original["confidence"], restored["confidence"])

    def test_survives_a_fresh_process_simulated_by_new_store_instance(self):
        SqliteGraphStore(root_dir=self.tmp_dir).save("proj1", self._built_kg())
        # A brand-new GraphStore object, as a fresh server process would create.
        fresh_store = SqliteGraphStore(root_dir=self.tmp_dir)
        self.assertTrue(fresh_store.exists("proj1"))
        reloaded = fresh_store.load("proj1")
        self.assertGreater(reloaded.graph.number_of_nodes(), 0)

    def test_load_nonexistent_project_returns_empty_graph_not_an_error(self):
        store = SqliteGraphStore(root_dir=self.tmp_dir)
        kg = store.load("never_scanned")
        self.assertEqual(kg.graph.number_of_nodes(), 0)

    def test_save_overwrites_previous_snapshot(self):
        store = SqliteGraphStore(root_dir=self.tmp_dir)
        store.save("proj1", self._built_kg())

        empty_kg = KnowledgeGraphEngine()
        store.save("proj1", empty_kg)

        reloaded = store.load("proj1")
        self.assertEqual(reloaded.graph.number_of_nodes(), 0)

    def test_delete_removes_the_project(self):
        store = SqliteGraphStore(root_dir=self.tmp_dir)
        store.save("proj1", self._built_kg())
        self.assertTrue(store.exists("proj1"))
        store.delete("proj1")
        self.assertFalse(store.exists("proj1"))


class TestRemoveSourceNodes(unittest.TestCase):

    def test_removes_only_the_given_sources_own_nodes(self):
        kg = KnowledgeGraphEngine()
        fabric_a = _fabric({"Foo.java": JAVA_A})
        parse_repository(fabric_a)
        GraphBuilder.build(kg, fabric_a, source_id="repoA")

        fabric_b = _fabric({"Baz.java": JAVA_B})
        parse_repository(fabric_b)
        GraphBuilder.build(kg, fabric_b, source_id="repoB")

        self.assertTrue(kg.graph.has_node("repoA::com.a.Foo"))
        self.assertTrue(kg.graph.has_node("repoB::com.b.Baz"))

        removed = remove_source_nodes(kg, "repoA")

        self.assertGreaterEqual(removed, 1)
        self.assertFalse(kg.graph.has_node("repoA::com.a.Foo"))
        self.assertTrue(kg.graph.has_node("repoB::com.b.Baz"))  # untouched

    def test_canonical_table_survives_removal_of_the_source_that_created_it(self):
        kg = KnowledgeGraphEngine()
        fabric_db = _fabric({"schema.ddl": DDL})
        parse_repository(fabric_db)
        GraphBuilder.build(kg, fabric_db, source_id="dbsrc")
        self.assertTrue(kg.graph.has_node("T1"))

        remove_source_nodes(kg, "dbsrc")

        # T1 is a canonical (bare-id) node, not source-qualified, so removing
        # "dbsrc"'s owned nodes must not delete it - another source might
        # still reference it, and only a full rebuild should prune it.
        self.assertTrue(kg.graph.has_node("T1"))

    def test_rescan_after_removal_rebuilds_cleanly(self):
        kg = KnowledgeGraphEngine()
        fabric_a = _fabric({"Foo.java": JAVA_A})
        parse_repository(fabric_a)
        GraphBuilder.build(kg, fabric_a, source_id="repoA")
        nodes_before = kg.graph.number_of_nodes()

        remove_source_nodes(kg, "repoA")
        self.assertLess(kg.graph.number_of_nodes(), nodes_before)

        fabric_a2 = _fabric({"Foo.java": JAVA_A})
        parse_repository(fabric_a2)
        GraphBuilder.build(kg, fabric_a2, source_id="repoA")

        self.assertEqual(kg.graph.number_of_nodes(), nodes_before)


if __name__ == "__main__":
    unittest.main()
