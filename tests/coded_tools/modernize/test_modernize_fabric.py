# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Comprehensive Unit Tests for ModernizeAI Knowledge Fabric & Dynamic Engines.
Validates 5-tier memory, deterministic parsers, dynamic rules extraction,
provenance validation, mathematical readiness scoring, 6R classification, and CodedTools.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("coded_tools"))
sys.path.insert(0, os.path.abspath("."))

from coded_tools.modernize.advisor.modernization_scoring import ModernizationScoring
from coded_tools.modernize.graph.algorithms import GraphAlgorithms
from coded_tools.modernize.graph.graph_engine import KnowledgeGraphEngine
from coded_tools.modernize.graph.knowledge_graph_tool import KnowledgeGraphTool
from coded_tools.modernize.memory.memory_manager_tool import MemoryFabric, MemoryManagerTool
from coded_tools.modernize.parsers.ddl_parser import DdlParser
from coded_tools.modernize.parsers.doc_parser import DocParser
from coded_tools.modernize.parsers.java_parser import JavaParser
from coded_tools.modernize.parsers.rules_extractor import RulesExtractor
from coded_tools.modernize.qa.provenance_validator import ProvenanceValidator
from coded_tools.modernize.reports.report_generator import ReportGenerator
from coded_tools.modernize.swarm_coordinator import ModernizeSwarmCoordinator
from coded_tools.modernize.tools.business_rules_tool import BusinessRulesTool
from coded_tools.modernize.tools.discovery_tool import DiscoveryTool
from coded_tools.modernize.tools.modernization_advisor_tool import ModernizationAdvisorTool
from coded_tools.modernize.tools.validation_tool import ValidationTool


class TestModernizeFabric(unittest.TestCase):

    def setUp(self):
        self.fabric = MemoryFabric()
        self.fabric.raw.ingest_directory("data/insurance_claims_app")

    def test_raw_and_semantic_memory(self):
        records = self.fabric.raw._files
        self.assertGreaterEqual(len(records), 8, f"Expected at least 8 files, found {len(records)}")

        # Check SHA-256 and line count
        policy_file = self.fabric.raw.get("Policy.java")
        self.assertIsNotNone(policy_file)
        self.assertEqual(len(policy_file.sha256), 64)
        self.assertGreater(policy_file.line_count, 10)

        # Line snippet extraction (1-indexed)
        lines = policy_file.get_lines(1, 5)
        self.assertIn("package com.enterprise.claims.model;", lines)

        # Semantic search index
        self.fabric.semantic.add_chunk(
            content="Policy must be ACTIVE or within 30-day grace period to adjudicate claims.",
            source_file="Claims_Architecture_Spec.md",
            start_line=10,
            end_line=12,
        )
        self.fabric.semantic.add_chunk(
            content="Claims exceeding $50,000 are escalated to special fraud investigation unit.",
            source_file="Claims_Architecture_Spec.md",
            start_line=14,
            end_line=16,
        )
        self.fabric.semantic.build_index()

        search_res = self.fabric.semantic.search("grace period active policy", top_k=2)
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

    def test_dynamic_business_rules_extraction(self):
        # Dynamically extract all rules without hardcoding
        rules = RulesExtractor.extract_all(self.fabric)
        self.assertGreaterEqual(len(rules), 5, f"Expected at least 5 extracted rules, got {len(rules)}")

        rule_methods = [r.get("method_name") for r in rules]
        self.assertTrue(any("validatePolicyStatus" in m for m in rule_methods if m))
        self.assertTrue(any("isEligibleForAutoApproval" in m for m in rule_methods if m))

        # Check provenance details
        for r in rules:
            self.assertIn("rule_id", r)
            self.assertIn("line_start", r)
            self.assertIn("line_end", r)
            self.assertGreaterEqual(r["line_start"], 1)
            self.assertGreaterEqual(r["line_end"], r["line_start"])

        # Test BusinessRulesTool
        br_tool = BusinessRulesTool()
        tool_res = br_tool.invoke({"action": "extract_rules"}, {"memory_fabric": self.fabric})
        self.assertEqual(tool_res["status"], "success")
        self.assertEqual(tool_res["total_rules_extracted"], len(rules))

        rule_single = br_tool.invoke({"action": "get_rule", "rule_id": "BR-01"}, {"memory_fabric": self.fabric})
        self.assertEqual(rule_single["status"], "success")
        self.assertIn("rule", rule_single)

    def test_provenance_validation_and_discrepancies(self):
        # Test line verification
        v_res = ProvenanceValidator.verify_provenance(
            fabric=self.fabric,
            source_file="PolicyValidationService.java",
            line_start=20,
            line_end=35,
            expected_tokens=["validatePolicyStatus"],
        )
        self.assertTrue(v_res["verified"])
        self.assertGreaterEqual(v_res["confidence"], 0.7)
        self.assertEqual(len(v_res["sha256"]), 64)

        # Test out-of-bounds line detection
        invalid_res = ProvenanceValidator.verify_provenance(
            fabric=self.fabric,
            source_file="PolicyValidationService.java",
            line_start=9999,
            line_end=10000,
        )
        self.assertFalse(invalid_res["verified"])

        # Test cross-artifact discrepancy detection
        discrepancies = ProvenanceValidator.detect_discrepancies(self.fabric)
        self.assertGreaterEqual(len(discrepancies), 2)
        disc_ids = [d["discrepancy_id"] for d in discrepancies]
        # Must catch the 30-day vs 15-day grace period conflict
        self.assertIn("DISC-01", disc_ids)
        # Must catch row-locking stored procedure
        self.assertIn("DISC-02", disc_ids)

        # Test ValidationTool
        val_tool = ValidationTool()
        tool_res = val_tool.invoke({"action": "detect_discrepancies"}, {"memory_fabric": self.fabric})
        self.assertEqual(tool_res["status"], "success")
        self.assertGreaterEqual(tool_res["total_discrepancies"], 2)

    def test_dynamic_readiness_and_6r_scoring(self):
        sly_data = {"memory_fabric": self.fabric}
        kg_tool = KnowledgeGraphTool()
        kg_tool.invoke({"action": "build_graph", "repo_path": "data/insurance_claims_app"}, sly_data)
        kg = sly_data["knowledge_graph"]

        # Calculate dynamic readiness score
        score_data = ModernizationScoring.calculate_readiness_score(kg, self.fabric)
        self.assertIn("overall_readiness_score", score_data)
        self.assertTrue(0 <= score_data["overall_readiness_score"] <= 100)
        self.assertTrue(0 <= score_data["modularity_score"] <= 100)
        self.assertTrue(0 <= score_data["provenance_score"] <= 100)
        self.assertTrue(0 <= score_data["risk_health_score"] <= 100)
        self.assertIn("grade", score_data)

        # Generate 6R strategies
        strategies = ModernizationScoring.generate_6r_strategies(kg, self.fabric)
        self.assertGreaterEqual(len(strategies), 4)

        strat_types = {s["strategy_6r"] for s in strategies}
        self.assertTrue("Refactor" in strat_types or "Replatform" in strat_types)
        self.assertTrue("Retire" in strat_types or "Retain / ACL" in strat_types)

        # Verify Tier 5 Transformation Memory is populated
        t5_dict = self.fabric.transformation.to_dict()
        self.assertGreater(len(t5_dict["metrics"]), 0)
        self.assertGreater(len(t5_dict["recommendations"]), 0)
        self.assertGreater(len(t5_dict["candidate_microservices"]), 0)

        # Test ModernizationAdvisorTool
        adv_tool = ModernizationAdvisorTool()
        adv_res = adv_tool.invoke({"action": "calculate_readiness_score"}, sly_data)
        self.assertEqual(adv_res["status"], "success")
        self.assertEqual(adv_res["readiness"]["overall_readiness_score"], score_data["overall_readiness_score"])

    def test_discovery_tool(self):
        disc_tool = DiscoveryTool()
        res = disc_tool.invoke({"action": "scan_repository", "repo_path": "data/insurance_claims_app"}, {})
        self.assertEqual(res["status"], "success")
        self.assertGreaterEqual(res["total_files_discovered"], 8)
        self.assertIn("catalog", res)
        self.assertGreaterEqual(len(res["catalog"]["java_source_files"]), 3)

    def test_knowledge_graph_and_algorithms(self):
        sly_data = {}
        kg_tool = KnowledgeGraphTool()

        # Build Graph dynamically
        build_res = kg_tool.invoke({"action": "build_graph", "repo_path": "data/insurance_claims_app"}, sly_data)
        self.assertEqual(build_res["status"], "success")
        self.assertGreaterEqual(build_res["total_nodes"], 20)
        self.assertGreaterEqual(build_res["total_edges"], 25)

        # Blast Radius for POLICY_MASTER
        blast_res = kg_tool.invoke({"action": "blast_radius", "target_entity": "POLICY_MASTER"}, sly_data)
        self.assertIn(blast_res["risk_level"], ("CRITICAL / HIGH RISK", "MEDIUM RISK"))
        self.assertGreaterEqual(blast_res["total_affected_count"], 5)

        # Blast Radius for ClaimService (verifies arbitrary node support)
        claim_blast = kg_tool.invoke({"action": "blast_radius", "target_entity": "ClaimService"}, sly_data)
        self.assertGreaterEqual(claim_blast["total_affected_count"], 3)

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

    def test_swarm_coordinator_dynamic_resolution(self):
        coordinator = ModernizeSwarmCoordinator()

        # Query 1: Dynamic business rules extraction
        res_rules = coordinator.execute_swarm_turn("What business rules govern claim validation?")
        self.assertEqual(res_rules["agent_path"][0], "frontman")
        self.assertIn("business_rules_agent", res_rules["agent_path"])
        self.assertIn("validation_agent", res_rules["agent_path"])
        self.assertIn("business_rules", res_rules["tool_results"])
        self.assertGreaterEqual(res_rules["tool_results"]["business_rules"]["total_rules_extracted"], 5)

        # Query 2: Dynamic blast radius for ClaimService (arbitrary entity resolution)
        res_impact = coordinator.execute_swarm_turn("What breaks if ClaimService changes?")
        self.assertIn("impact_analysis_agent", res_impact["agent_path"])
        self.assertIn("blast_radius", res_impact["tool_results"])
        self.assertEqual(res_impact["tool_results"]["blast_radius"]["target_entity"], "ClaimService")

        # Query 3: Modernization readiness and 6R strategy
        res_adv = coordinator.execute_swarm_turn("What is our cloud modernization readiness score and 6R roadmap?")
        self.assertIn("modernization_advisor_agent", res_adv["agent_path"])
        self.assertIn("readiness", res_adv["tool_results"])
        self.assertTrue(0 <= res_adv["tool_results"]["readiness"]["overall_readiness_score"] <= 100)


if __name__ == "__main__":
    unittest.main()
