# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
KnowledgeGraphTool: CodedTool interface for Neuro SAN Studio.
Builds, queries, traverses, and visualizes the Knowledge Graph Fabric.
"""

import os
from typing import Any
from typing import Dict
from typing import Optional

from coded_tools.modernize.graph.algorithms import GraphAlgorithms
from coded_tools.modernize.graph.graph_engine import KnowledgeGraphEngine
from coded_tools.modernize.graph.visualizer import GraphVisualizer
from coded_tools.modernize.memory.memory_manager_tool import get_memory_fabric
from coded_tools.modernize.parsers.ddl_parser import DdlParser
from coded_tools.modernize.parsers.java_parser import JavaParser
from coded_tools.modernize.parsers.rules_extractor import RulesExtractor
from coded_tools.modernize.qa.provenance_validator import ProvenanceValidator
from coded_tools.modernize.tool_base import CodedTool

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
            # Clear previous graph if rebuilding
            kg.graph.clear()

            # 1. Ingest into memory fabric if not already done
            if len(fabric.raw._files) == 0:
                fabric.raw.ingest_directory(repo_path)

            # 2. Add Top-Level Application Node
            if repo_path == "data/insurance_claims_app" or not repo_path:
                app_node_id = "ClaimCore_App"
                app_label = "ClaimCore Monolith v2.4"
            else:
                base_name = os.path.basename(os.path.normpath(repo_path)) or "Application"
                app_node_id = f"{base_name}_App"
                app_label = f"{base_name} Application"

            kg.add_node(
                node_id=app_node_id,
                node_type="Application",
                label=app_label,
                source_file=repo_path,
                line_start=1,
                line_end=100,
                extractor="manifest",
                evidence_snippet=f"Core application node for {app_label}.",
            )

            # 3. Parse and register DDL (Tables and Foreign Keys) across all DDL/SQL files
            for fpath, rec in fabric.raw._files.items():
                if fpath.endswith((".ddl", ".sql")):
                    content = rec.get_lines(1, rec.line_count)
                    try:
                        ddl_data = DdlParser.parse_ddl(fpath, content)
                        for tbl in ddl_data.get("tables", []):
                            t_name = tbl["table_name"]
                            if not kg.graph.has_node(t_name):
                                kg.add_node(
                                    node_id=t_name,
                                    node_type="DatabaseTable",
                                    label=f"Table: {t_name}",
                                    source_file=tbl.get("file_path", fpath),
                                    line_start=tbl.get("start_line", 1),
                                    line_end=tbl.get("end_line", 1),
                                    extractor="ddl_parser",
                                    evidence_snippet=(
                                        f"CREATE TABLE {t_name} with primary key {tbl.get('primary_key')}"
                                    ),
                                )
                                kg.add_edge(
                                    app_node_id,
                                    t_name,
                                    "DEPENDS_ON",
                                    source_file=tbl.get("file_path", fpath),
                                    line_start=tbl.get("start_line", 1),
                                    line_end=tbl.get("end_line", 1),
                                )
                            for fk in tbl.get("foreign_keys", []):
                                target = fk.get("target_table")
                                if target and kg.graph.has_node(target):
                                    kg.add_edge(
                                        t_name,
                                        target,
                                        "DEPENDS_ON",
                                        source_file=tbl.get("file_path", fpath),
                                        line_start=tbl.get("start_line", 1),
                                        line_end=tbl.get("end_line", 1),
                                        evidence_snippet=f"CONSTRAINT {fk.get('constraint_name')} REFERENCES {target}",
                                    )
                    except Exception:
                        pass

                    try:
                        sp_data = DdlParser.parse_stored_procedure(fpath, content)
                        for proc in sp_data.get("procedures", []):
                            p_name = proc["procedure_name"]
                            if not kg.graph.has_node(p_name):
                                kg.add_node(
                                    node_id=p_name,
                                    node_type="StoredProcedure",
                                    label=f"Procedure: {p_name}",
                                    source_file=proc.get("file_path", fpath),
                                    line_start=proc.get("start_line", 1),
                                    line_end=proc.get("end_line", 1),
                                    extractor="ddl_parser",
                                    evidence_snippet=f"CREATE PROCEDURE {p_name}",
                                )
                            for r_tbl in proc.get("tables_read", []):
                                if kg.graph.has_node(r_tbl):
                                    kg.add_edge(
                                        p_name,
                                        r_tbl,
                                        "READS_FROM",
                                        source_file=proc.get("file_path", fpath),
                                        line_start=proc.get("start_line", 1),
                                        line_end=proc.get("end_line", 1),
                                    )
                            for w_tbl in proc.get("tables_written", []):
                                if kg.graph.has_node(w_tbl):
                                    kg.add_edge(
                                        p_name,
                                        w_tbl,
                                        "WRITES_TO",
                                        source_file=proc.get("file_path", fpath),
                                        line_start=proc.get("start_line", 1),
                                        line_end=proc.get("end_line", 1),
                                    )
                    except Exception:
                        pass

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
                    kg.add_edge(app_node_id, c_name, "DEPENDS_ON", source_file=fpath)

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

            # 6. Dynamically Extract and Add Formalized Business Rules
            extracted_rules = RulesExtractor.extract_all(fabric)
            for r in extracted_rules:
                r_id = r["rule_id"]
                r_name = r["rule_name"]
                r_spec = r["specification"]
                src_f = r["source_file"]
                ls = r["line_start"]
                le = r["line_end"]

                kg.add_node(
                    node_id=r_id,
                    node_type="BusinessRule",
                    label=f"{r_id}: {r_name}",
                    source_file=src_f,
                    line_start=ls,
                    line_end=le,
                    extractor=r.get("extractor", "dynamic_rules_extractor"),
                    evidence_snippet=r_spec,
                )

                # Link implementing service/class to rule
                for node_candidate in kg.graph.nodes():
                    if node_candidate in src_f or node_candidate == "PolicyValidationService":
                        kg.add_edge(
                            node_candidate,
                            r_id,
                            "IMPLEMENTS_RULE",
                            source_file=src_f,
                            line_start=ls,
                            line_end=le,
                        )
                        break

            # 7. Dynamically Add Architecture Specs and SME Insights
            for path, rec in fabric.raw._files.items():
                if path.endswith(".md"):
                    doc_id = os.path.basename(path).replace(".md", "").replace(".", "_")
                    kg.add_node(
                        node_id=doc_id,
                        node_type="RequirementDocument",
                        label=f"Doc: {doc_id}",
                        source_file=rec.rel_path,
                        line_start=1,
                        line_end=min(50, rec.line_count),
                        extractor="doc_parser",
                        evidence_snippet=f"Specification document with {rec.line_count} lines.",
                    )
                elif "sme" in path.lower() or path.endswith(".txt"):
                    sme_id = os.path.basename(path).replace(".txt", "").replace(".", "_")
                    kg.add_node(
                        node_id=sme_id,
                        node_type="SMEInsight",
                        label=f"SME: {sme_id}",
                        source_file=rec.rel_path,
                        line_start=1,
                        line_end=min(50, rec.line_count),
                        extractor="doc_parser",
                        evidence_snippet=(
                            f"SME interview and operational tribal knowledge notes ({rec.line_count} lines)."
                        ),
                    )

            # 8. Dynamically Detect Architectural Risks and Discrepancies
            discrepancies = ProvenanceValidator.detect_discrepancies(fabric)
            ProvenanceValidator.inject_discrepancies_into_graph(kg, discrepancies)

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
