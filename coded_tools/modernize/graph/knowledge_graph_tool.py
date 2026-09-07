# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
KnowledgeGraphTool: CodedTool interface for Neuro SAN Studio.
Builds, queries, traverses, and visualizes the Knowledge Graph Fabric.
"""

import os
from typing import Any, Dict, List, Optional
from neuro_san.interfaces.coded_tool import CodedTool

from coded_tools.modernize.graph.algorithms import GraphAlgorithms
from coded_tools.modernize.graph.graph_engine import KnowledgeGraphEngine
from coded_tools.modernize.graph.visualizer import GraphVisualizer
from coded_tools.modernize.memory.memory_manager_tool import get_memory_fabric
from coded_tools.modernize.parsers.ddl_parser import DdlParser
from coded_tools.modernize.parsers.doc_parser import DocParser
from coded_tools.modernize.parsers.java_parser import JavaParser


# Global graph instance for shared local access
_GLOBAL_KG = KnowledgeGraphEngine()


def get_knowledge_graph(sly_data: Optional[Dict[str, Any]] = None) -> KnowledgeGraphEngine:
    global _GLOBAL_KG
    if sly_data is not None and "knowledge_graph" in sly_data:
        return sly_data["knowledge_graph"]
    if sly_data is not None:
        sly_data["knowledge_graph"] = _GLOBAL_KG
    return _GLOBAL_KG


class KnowledgeGraphTool(CodedTool):
    """
    CodedTool that provides Knowledge Graph operations to the Knowledge Graph Agent and Impact Analysis Agent.
    """

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        kg = get_knowledge_graph(sly_data)
        fabric = get_memory_fabric(sly_data)
        action = args.get("action", "status")

        if action == "build_graph":
            repo_path = args.get("repo_path", "data/insurance_claims_app")
            # 1. Ingest into memory fabric if not already done
            if len(fabric.raw._files) == 0:
                fabric.raw.ingest_directory(repo_path)

            # 2. Add Top-Level Application Node
            kg.add_node(
                node_id="ClaimCore_App",
                node_type="Application",
                label="ClaimCore Monolith v2.4",
                source_file="data/insurance_claims_app",
                line_start=1,
                line_end=100,
                extractor="manifest",
                evidence_snippet="Core insurance legacy application adjudicating claims.",
            )

            # 3. Parse and register DDL (Tables and Foreign Keys)
            ddl_file = fabric.raw.get("schema.ddl")
            if ddl_file:
                content = ddl_file.get_lines(1, ddl_file.line_count)
                ddl_data = DdlParser.parse_ddl("schema.ddl", content)
                for tbl in ddl_data["tables"]:
                    t_name = tbl["table_name"]
                    kg.add_node(
                        node_id=t_name,
                        node_type="DatabaseTable",
                        label=f"Table: {t_name}",
                        source_file=tbl["file_path"],
                        line_start=tbl["start_line"],
                        line_end=tbl["end_line"],
                        extractor="ddl_parser",
                        evidence_snippet=f"CREATE TABLE {t_name} with primary key {tbl['primary_key']}",
                    )
                    kg.add_edge(
                        "ClaimCore_App",
                        t_name,
                        "DEPENDS_ON",
                        source_file=tbl["file_path"],
                        line_start=tbl["start_line"],
                        line_end=tbl["end_line"],
                    )
                    # Foreign keys
                    for fk in tbl["foreign_keys"]:
                        target = fk["target_table"]
                        if kg.graph.has_node(target):
                            kg.add_edge(
                                t_name,
                                target,
                                "DEPENDS_ON",
                                source_file=tbl["file_path"],
                                line_start=tbl["start_line"],
                                line_end=tbl["end_line"],
                                evidence_snippet=f"CONSTRAINT {fk['constraint_name']} REFERENCES {target}",
                            )

            # 4. Parse Stored Procedure
            sp_file = fabric.raw.get("process_claim_sp.sql")
            if sp_file:
                sp_content = sp_file.get_lines(1, sp_file.line_count)
                sp_data = DdlParser.parse_stored_procedure("process_claim_sp.sql", sp_content)
                for proc in sp_data["procedures"]:
                    p_name = proc["procedure_name"]
                    kg.add_node(
                        node_id=p_name,
                        node_type="StoredProcedure",
                        label=f"Procedure: {p_name}",
                        source_file=proc["file_path"],
                        line_start=proc["start_line"],
                        line_end=proc["end_line"],
                        extractor="ddl_parser",
                        evidence_snippet=f"CREATE PROCEDURE {p_name} updating deductible and payout balances",
                    )
                    for r_tbl in proc["tables_read"]:
                        if kg.graph.has_node(r_tbl):
                            kg.add_edge(
                                p_name,
                                r_tbl,
                                "READS_FROM",
                                source_file=proc["file_path"],
                                line_start=proc["start_line"],
                                line_end=proc["end_line"],
                            )
                    for w_tbl in proc["tables_written"]:
                        if kg.graph.has_node(w_tbl):
                            kg.add_edge(
                                p_name,
                                w_tbl,
                                "WRITES_TO",
                                source_file=proc["file_path"],
                                line_start=proc["start_line"],
                                line_end=proc["end_line"],
                            )

            # 5. Parse Java Classes and Rules
            for fpath, rec in fabric.raw._files.items():
                if fpath.endswith(".java"):
                    content = rec.get_lines(1, rec.line_count)
                    parsed = JavaParser.parse_file(fpath, content)
                    c_name = parsed["class_name"]

                    kg.add_node(
                        node_id=c_name,
                        node_type="Service" if "Service" in c_name else "Module",
                        label=f"Class: {c_name}",
                        source_file=parsed["file_path"],
                        line_start=parsed["start_line"],
                        line_end=parsed["end_line"],
                        extractor="java_ast_parser",
                        evidence_snippet=f"Java component {c_name} with {len(parsed['methods'])} methods",
                    )
                    kg.add_edge("ClaimCore_App", c_name, "DEPENDS_ON", source_file=fpath)

                    # SQL references
                    for sql in parsed["sql_statements"]:
                        tbl = sql["table"]
                        verb = sql["verb"]
                        edge_type = "WRITES_TO" if verb in ("INSERT", "UPDATE", "DELETE") else "READS_FROM"
                        if verb == "{CALL":
                            edge_type = "CALLS"
                        if kg.graph.has_node(tbl):
                            kg.add_edge(
                                c_name,
                                tbl,
                                edge_type,
                                source_file=fpath,
                                line_start=sql["line"],
                                line_end=sql["line"],
                                evidence_snippet=sql["sql"],
                            )

                    # Service calls
                    for call in parsed["service_calls"]:
                        tgt = call["target_service"]
                        if kg.graph.has_node(tgt):
                            kg.add_edge(
                                c_name,
                                tgt,
                                "CALLS",
                                source_file=fpath,
                                line_start=call["line"],
                                line_end=call["line"],
                            )

            # 6. Add Formalized Business Rules
            rules = [
                ("BR-01", "Policy Status Check", "Policy must have ACTIVE or GRACE_PERIOD status to adjudicate claims.", "PolicyValidationService", 21),
                ("BR-02", "Date Range Eligibility", "Incident date must fall within policy start and end dates.", "PolicyValidationService", 32),
                ("BR-03", "Coverage Limit Adjudication", "Claim amount cannot exceed remaining policy coverage balance.", "PolicyValidationService", 43),
                ("BR-04", "High-Risk Fraud Escalation", "Claims exceeding $50k or filed within 7 days of inception require fraud review.", "PolicyValidationService", 54),
                ("BR-05", "Auto-Approval Limit ($2.5k)", "Clean claims under $2,500 on active policies are eligible for straight-through approval.", "PolicyValidationService", 66),
            ]
            for r_id, r_label, r_desc, impl_class, line_no in rules:
                kg.add_node(
                    node_id=r_id,
                    node_type="BusinessRule",
                    label=f"{r_id}: {r_label}",
                    source_file="data/insurance_claims_app/PolicyValidationService.java",
                    line_start=line_no,
                    line_end=line_no + 8,
                    extractor="deterministic_rule_extractor",
                    evidence_snippet=r_desc,
                )
                if kg.graph.has_node(impl_class):
                    kg.add_edge(
                        impl_class,
                        r_id,
                        "IMPLEMENTS_RULE",
                        source_file="data/insurance_claims_app/PolicyValidationService.java",
                        line_start=line_no,
                        line_end=line_no + 8,
                    )

            # 7. Add Architecture Docs and SME Insights
            kg.add_node(
                node_id="Claims_Architecture_Spec",
                node_type="RequirementDocument",
                label="Doc: Claims Architecture Spec",
                source_file="data/insurance_claims_app/Claims_Architecture_Spec.md",
                line_start=1,
                line_end=25,
                extractor="doc_parser",
                evidence_snippet="Monolith overview, SLA requirements, and deductible calculation workflows.",
            )
            kg.add_node(
                node_id="SME_Tribal_Notes",
                node_type="SMEInsight",
                label="SME: Bob Vance Interview",
                source_file="data/insurance_claims_app/SME_Interview_Notes.txt",
                line_start=1,
                line_end=15,
                extractor="doc_parser",
                evidence_snippet="Grace period mismatch, row locking in SP_PROCESS_CLAIM, and CUSTOMER_ACCOUNT sharing.",
            )

            # 8. Add Architectural Risks
            risks = [
                ("Risk_Row_Locking", "Database Row Locking Contention", "SP_PROCESS_CLAIM locks POLICY_MASTER rows during claim surges.", "process_claim_sp.sql"),
                ("Risk_Shared_Database", "Shared Database Anti-Pattern", "CUSTOMER_ACCOUNT table is shared across 3 other legacy systems.", "schema.ddl"),
                ("Risk_Hardcoded_Rule", "Hardcoded Auto-Approval Threshold", "$2,500 approval limit is hardcoded as constant in PolicyValidationService.", "PolicyValidationService.java"),
            ]
            for rk_id, rk_label, rk_desc, src_f in risks:
                kg.add_node(
                    node_id=rk_id,
                    node_type="Risk",
                    label=f"Risk: {rk_label}",
                    source_file=src_f,
                    extractor="architectural_analyzer",
                    evidence_snippet=rk_desc,
                )

            # Link risks
            if kg.graph.has_node("SP_PROCESS_CLAIM"):
                kg.add_edge("SP_PROCESS_CLAIM", "Risk_Row_Locking", "IMPACTS")
            if kg.graph.has_node("CUSTOMER_ACCOUNT"):
                kg.add_edge("CUSTOMER_ACCOUNT", "Risk_Shared_Database", "IMPACTS")
            if kg.graph.has_node("BR-05"):
                kg.add_edge("BR-05", "Risk_Hardcoded_Rule", "IMPACTS")

            return {
                "status": "success",
                "action": "build_graph",
                "total_nodes": kg.graph.number_of_nodes(),
                "total_edges": kg.graph.number_of_edges(),
            }
        elif action == "load_graph":
            json_path = args.get("json_path", "artifacts/modernize_kg.json")
            kg.load_json(json_path)
            return {
                "status": "success",
                "action": "load_graph",
                "total_nodes": kg.graph.number_of_nodes(),
                "total_edges": kg.graph.number_of_edges(),
            }

        elif action == "blast_radius":
            target = args.get("target_entity", "POLICY_MASTER")
            depth = int(args.get("max_depth", 3))
            return GraphAlgorithms.calculate_blast_radius(kg.graph, target, max_depth=depth)

        elif action == "community_detection":
            return {
                "status": "success",
                "action": "community_detection",
                "candidate_domains": GraphAlgorithms.detect_communities(kg.graph),
            }

        elif action == "hybrid_graph_rag":
            query = args.get("query", "")
            # 1. Get semantic chunks from memory fabric
            sem_results = fabric.semantic.search(query, top_k=4)
            # 2. Extract seeds from matching node names
            seeds = []
            for node_id in kg.graph.nodes():
                if any(term in node_id.lower() for term in query.lower().split() if len(term) > 3):
                    seeds.append(node_id)
            if not seeds and sem_results:
                # Use source files as fallback seeds
                for s in sem_results:
                    for n in kg.graph.nodes():
                        if n.lower() in s["content"].lower():
                            seeds.append(n)
            
            if not seeds:
                seeds = ["ClaimService", "POLICY_MASTER"]

            # 3. Compute Personalized PageRank
            ppr_scores = GraphAlgorithms.personalized_pagerank(kg.graph, seeds)
            
            # 4. Hybrid Reciprocal Rank Fusion
            hybrid_context = GraphAlgorithms.hybrid_rrf_retrieval(sem_results, ppr_scores, kg.graph, top_n=6)
            return {
                "status": "success",
                "query": query,
                "seeds": seeds,
                "fused_evidence": hybrid_context,
            }

        elif action == "query_entity":
            node_id = args.get("node_id", "")
            node_data = kg.get_node(node_id)
            if not node_data:
                return {"error": f"Node '{node_id}' not found"}
            neighbors = kg.get_neighbors(node_id)
            return {
                "node_id": node_id,
                "data": node_data,
                "neighbors": neighbors,
            }

        elif action == "export_artifacts":
            html_path = args.get("html_path", "artifacts/modernize_graph.html")
            json_path = args.get("json_path", "artifacts/modernize_kg.json")
            graphml_path = args.get("graphml_path", "artifacts/modernize_kg.graphml")

            kg.export_json(json_path)
            kg.export_graphml(graphml_path)
            html_abs = GraphVisualizer.render_html(kg.graph, html_path)

            return {
                "status": "success",
                "artifacts": {
                    "html_visualization": html_abs,
                    "json_knowledge_graph": os.path.abspath(json_path),
                    "graphml_export": os.path.abspath(graphml_path),
                },
                "total_nodes": kg.graph.number_of_nodes(),
                "total_edges": kg.graph.number_of_edges(),
            }

        elif action == "status":
            return {
                "total_nodes": kg.graph.number_of_nodes(),
                "total_edges": kg.graph.number_of_edges(),
                "node_types": list(set(d.get("node_type") for _, d in kg.graph.nodes(data=True))),
            }

        return {"error": f"Unknown knowledge graph action: {action}"}

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        return self.invoke(args, sly_data)
