# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Comprehensive Unit Tests for ModernizeAI Knowledge Fabric.
Validates 5-tier memory, deterministic parsers, graph algorithms, and artifact exports.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("coded_tools"))
sys.path.insert(0, os.path.abspath("."))

from modernize.graph.algorithms import GraphAlgorithms
from modernize.graph.graph_engine import KnowledgeGraphEngine
from modernize.graph.knowledge_graph_tool import KnowledgeGraphTool
from modernize.memory.memory_manager_tool import MemoryFabric, MemoryManagerTool
from modernize.parsers.ddl_parser import DdlParser
from modernize.parsers.doc_parser import DocParser
from modernize.parsers.java_parser import JavaParser
from modernize.reports.report_generator import ReportGenerator


class TestModernizeFabric(unittest.TestCase):

    def test_raw_and_semantic_memory(self):
        fabric = MemoryFabric()
        records = fabric.raw.ingest_directory("data/insurance_claims_app")
        self.assertGreaterEqual(len(records), 8, f"Expected at least 8 files, found {len(records)}")

        # Check SHA-256 and line count
        policy_file = fabric.raw.get("Policy.java")
        self.assertIsNotNone(policy_file)
        self.assertEqual(len(policy_file.sha256), 64)
        self.assertGreater(policy_file.line_count, 10)

        # Line snippet extraction (1-indexed)
        lines = policy_file.get_lines(1, 5)
        self.assertIn("package com.enterprise.claims.model;", lines)

        # Semantic search index
        fabric.semantic.add_chunk(
            content="Policy must be ACTIVE or within 30-day grace period to adjudicate claims.",
            source_file="Claims_Architecture_Spec.md",
            start_line=10,
            end_line=12,
        )
        fabric.semantic.add_chunk(
            content="Claims exceeding $50,000 are escalated to special fraud investigation unit.",
            source_file="Claims_Architecture_Spec.md",
            start_line=14,
            end_line=16,
        )
        fabric.semantic.build_index()

        search_res = fabric.semantic.search("grace period active policy", top_k=2)
        self.assertGreater(len(search_res), 0)
        self.assertIn("grace period", search_res[0]["content"].lower())

    def test_deterministic_parsers(self):
        # 1. Java Parser
        with open("data/insurance_claims_app/ClaimService.java", "r", encoding="utf-8") as f:
            claim_srv_src = f.read()
        parsed_java = JavaParser.parse_file("ClaimService.java", claim_srv_src)
        self.assertEqual(parsed_java["class_name"], "ClaimService")
        self.assertGreaterEqual(len(parsed_java["sql_statements"]), 3)
        self.assertTrue(any(s["table"] == "POLICY_MASTER" for s in parsed_java["sql_statements"]))
        self.assertTrue(any(s["table"] == "CLAIMS_RECORD" for s in parsed_java["sql_statements"]))

        # 2. DDL Parser
        with open("data/insurance_claims_app/schema.ddl", "r", encoding="utf-8") as f:
            ddl_src = f.read()
        parsed_ddl = DdlParser.parse_ddl("schema.ddl", ddl_src)
        tables = [t["table_name"] for t in parsed_ddl["tables"]]
        self.assertIn("CUSTOMER_ACCOUNT", tables)
        self.assertIn("POLICY_MASTER", tables)
        self.assertIn("CLAIMS_RECORD", tables)

        # Check foreign keys
        policy_tbl = next(t for t in parsed_ddl["tables"] if t["table_name"] == "POLICY_MASTER")
        self.assertEqual(len(policy_tbl["foreign_keys"]), 1)
        self.assertEqual(policy_tbl["foreign_keys"][0]["target_table"], "CUSTOMER_ACCOUNT")

        # 3. Stored Procedure Parser
        with open("data/insurance_claims_app/process_claim_sp.sql", "r", encoding="utf-8") as f:
            sp_src = f.read()
        parsed_sp = DdlParser.parse_stored_procedure("process_claim_sp.sql", sp_src)
        self.assertEqual(len(parsed_sp["procedures"]), 1)
        proc = parsed_sp["procedures"][0]
        self.assertEqual(proc["procedure_name"], "SP_PROCESS_CLAIM")
        self.assertIn("POLICY_MASTER", proc["tables_read"])
        self.assertIn("POLICY_MASTER", proc["tables_written"])
        self.assertIn("CLAIMS_RECORD", proc["tables_written"])

    def test_knowledge_graph_and_algorithms(self):
        sly_data = {}
        kg_tool = KnowledgeGraphTool()

        # Build Graph
        build_res = kg_tool.invoke({"action": "build_graph", "repo_path": "data/insurance_claims_app"}, sly_data)
        self.assertEqual(build_res["status"], "success")
        self.assertGreaterEqual(build_res["total_nodes"], 20)
        self.assertGreaterEqual(build_res["total_edges"], 25)

        # Blast Radius for POLICY_MASTER
        blast_res = kg_tool.invoke({"action": "blast_radius", "target_entity": "POLICY_MASTER"}, sly_data)
        self.assertIn(blast_res["risk_level"], ("CRITICAL / HIGH RISK", "MEDIUM RISK"))
        self.assertGreaterEqual(blast_res["total_affected_count"], 5)

        # Check that ClaimService or SP_PROCESS_CLAIM appear in impact
        upstream_ids = [item["node_id"] for item in blast_res["upstream_impact"]]
        downstream_ids = [item["node_id"] for item in blast_res["downstream_impact"]]
        all_impacted = set(upstream_ids + downstream_ids)
        self.assertTrue("ClaimService" in all_impacted or "SP_PROCESS_CLAIM" in all_impacted)

        # Community Detection
        comm_res = kg_tool.invoke({"action": "community_detection"}, sly_data)
        self.assertGreater(len(comm_res["candidate_domains"]), 0)

        # Hybrid Graph RAG
        rag_res = kg_tool.invoke({"action": "hybrid_graph_rag", "query": "What rules check policy status and dates?"}, sly_data)
        self.assertEqual(rag_res["status"], "success")
        self.assertGreater(len(rag_res["fused_evidence"]), 0)

        # Artifact Export
        export_res = kg_tool.invoke({"action": "export_artifacts", "html_path": "artifacts/modernize_graph.html"}, sly_data)
        self.assertTrue(os.path.exists(export_res["artifacts"]["html_visualization"]))
        self.assertTrue(os.path.exists(export_res["artifacts"]["json_knowledge_graph"]))


if __name__ == "__main__":
    unittest.main()
