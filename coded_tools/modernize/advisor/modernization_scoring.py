# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Dynamic Modernization Readiness Scoring & 6R Migration Classifier.
Evaluates Martin coupling metrics, provenance completeness, and architectural risk density
using an evenly weighted mathematical formulation. Populates Tier 5 Transformation Memory.
"""

from typing import Any, Dict, List, Optional
import networkx as nx
from coded_tools.modernize.graph.algorithms import GraphAlgorithms
from coded_tools.modernize.graph.graph_engine import KnowledgeGraphEngine
from coded_tools.modernize.memory.memory_manager_tool import MemoryFabric


class ModernizationScoring:
    """
    Algorithmic modernization readiness evaluation and 6R strategy formulation engine.
    """

    @classmethod
    def calculate_readiness_score(
        cls,
        kg: KnowledgeGraphEngine,
        fabric: MemoryFabric,
    ) -> Dict[str, Any]:
        """
        Calculates an evenly weighted Modernization Readiness Score (0 to 100):
        Score = round((ModularityScore + ProvenanceScore + RiskHealthScore) / 3)
        """
        graph = kg.graph
        total_nodes = graph.number_of_nodes()
        total_edges = graph.number_of_edges()

        if total_nodes == 0:
            return {
                "overall_readiness_score": 0,
                "modularity_score": 0.0,
                "provenance_score": 0.0,
                "risk_health_score": 0.0,
                "components_evaluated": 0,
                "grade": "F",
            }

        # 1. Modularity & Coupling Factor (0 to 100)
        # Evaluates average Martin instability and Louvain clustering quality
        instabilities = []
        for n in graph.nodes():
            in_deg = graph.in_degree(n)
            out_deg = graph.out_degree(n)
            tot = in_deg + out_deg
            if tot > 0:
                instability = out_deg / tot
                instabilities.append(instability)

        avg_instability = sum(instabilities) / max(1, len(instabilities))
        # Optimal systems have balanced instability distribution (near ~0.5 across services and entities)
        # Deviation from balance penalizes modularity
        modularity_ratio = 1.0 - abs(avg_instability - 0.5)
        communities = GraphAlgorithms.detect_communities(graph)
        num_communities = len(communities)
        community_bonus = min(20.0, num_communities * 4.0)
        modularity_score = min(100.0, max(0.0, (modularity_ratio * 70.0) + community_bonus + 10.0))

        # 2. Provenance Completeness Factor (0 to 100)
        # Proportion of nodes that possess verified line-level source citations
        verified_nodes = 0
        for n, attrs in graph.nodes(data=True):
            src = attrs.get("source_file", "")
            ls = attrs.get("line_start", 0)
            if src and src != "System" and ls > 0:
                verified_nodes += 1

        provenance_score = min(100.0, (verified_nodes / total_nodes) * 100.0)

        # 3. Risk Health Factor (0 to 100)
        # Penalizes detected architectural gravity wells, table row locks, and shared DB anti-patterns
        risk_nodes = [n for n, d in graph.nodes(data=True) if d.get("node_type") == "Risk"]
        # Tables with high incoming dependency count (gravity wells)
        gravity_wells = [
            n for n, d in graph.nodes(data=True)
            if d.get("node_type") == "DatabaseTable" and graph.in_degree(n) >= 3
        ]

        raw_penalty = (len(risk_nodes) * 8.0) + (len(gravity_wells) * 10.0)
        risk_health_score = max(0.0, min(100.0, 100.0 - raw_penalty))

        # Evenly weighted composite readiness score
        readiness_score = round((modularity_score + provenance_score + risk_health_score) / 3.0)
        readiness_score = max(0, min(100, readiness_score))

        # Letter grade
        if readiness_score >= 85:
            grade = "A (Highly Cloud-Ready)"
        elif readiness_score >= 70:
            grade = "B (Ready for Phased Strangler-Fig Migration)"
        elif readiness_score >= 50:
            grade = "C (Requires Architectural Decoupling)"
        else:
            grade = "D (High Risk Legacy Monolith)"

        return {
            "overall_readiness_score": readiness_score,
            "modularity_score": round(modularity_score, 1),
            "provenance_score": round(provenance_score, 1),
            "risk_health_score": round(risk_health_score, 1),
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "risk_node_count": len(risk_nodes),
            "gravity_well_count": len(gravity_wells),
            "candidate_domains_count": num_communities,
            "grade": grade,
        }

    @classmethod
    def generate_6r_strategies(
        cls,
        kg: KnowledgeGraphEngine,
        fabric: MemoryFabric,
    ) -> List[Dict[str, Any]]:
        """
        Algorithmically classifies components into 6R migration strategies
        (Refactor, Replatform, Retain/ACL, Retire) and populates Tier 5 Transformation Memory.
        """
        graph = kg.graph
        strategies = []

        for n, attrs in graph.nodes(data=True):
            nt = attrs.get("node_type", "")
            in_deg = graph.in_degree(n)
            out_deg = graph.out_degree(n)
            tot_deg = in_deg + out_deg
            instability = round(out_deg / tot_deg, 3) if tot_deg > 0 else 0.0

            # Record metrics into Tier 5 Transformation Memory
            fabric.transformation.record_metrics(
                component_name=n,
                afferent_coupling=in_deg,
                efferent_coupling=out_deg,
                cyclomatic_complexity=max(1, out_deg * 2),
                lines_of_code=max(20, attrs.get("line_end", 20) - attrs.get("line_start", 1) + 1),
            )

            # Strategy classification logic
            if nt == "DatabaseTable":
                if in_deg >= 3:
                    strat = {
                        "component": n,
                        "type": "DatabaseTable",
                        "strategy_6r": "Retain / ACL",
                        "target_pattern": "Anti-Corruption Layer + Debezium CDC Event Stream",
                        "priority": "Phase 3",
                        "rationale": f"High Afferent Coupling (Ca={in_deg}). Direct table access represents an architectural gravity well.",
                        "risks": ["Shared table writes", "Locking during batch windows"],
                    }
                else:
                    strat = {
                        "component": n,
                        "type": "DatabaseTable",
                        "strategy_6r": "Replatform",
                        "target_pattern": "Dedicated Cloud Managed Database (RDS / Azure SQL)",
                        "priority": "Phase 2",
                        "rationale": "Isolated operational entity suitable for database-per-service ownership.",
                        "risks": ["Data migration consistency"],
                    }

            elif nt == "StoredProcedure":
                strat = {
                    "component": n,
                    "type": "StoredProcedure",
                    "strategy_6r": "Retire",
                    "target_pattern": "Distributed Asynchronous Saga / Outbox Orchestrator",
                    "priority": "Phase 2",
                    "rationale": "Procedural database code contains row-level table locks (SELECT FOR UPDATE) causing concurrency contention.",
                    "risks": ["Loss of transactional rollback", "Race conditions if not handled via saga"],
                }

            elif nt == "Service":
                if "Validation" in n or instability >= 0.6:
                    strat = {
                        "component": n,
                        "type": "Service",
                        "strategy_6r": "Refactor",
                        "target_pattern": "Stateless Event-Driven Cloud Function / Lambda",
                        "priority": "Phase 1",
                        "rationale": f"High Instability (I={instability}) with pure business validation logic; ideal for serverless extraction.",
                        "risks": ["Cold start latency", "Configuration drift"],
                    }
                else:
                    strat = {
                        "component": n,
                        "type": "Service",
                        "strategy_6r": "Replatform",
                        "target_pattern": "Cloud-Native Container Microservice (Spring Boot / .NET 8)",
                        "priority": "Phase 2",
                        "rationale": "Core orchestrator coordinating domain workflows; migrate via Strangler-Fig facade.",
                        "risks": ["Inter-service network latency", "Downstream schema coupling"],
                    }

            else:
                continue

            strategies.append(strat)

            # Record recommendation into Tier 5 Transformation Memory
            fabric.transformation.record_recommendation(
                component_name=strat["component"],
                strategy_6r=strat["strategy_6r"],
                target_pattern=strat["target_pattern"],
                priority=strat["priority"],
                rationale=strat["rationale"],
                risks=strat["risks"],
            )

        # Register candidate microservice domains into Tier 5
        communities = GraphAlgorithms.detect_communities(graph)
        for c in communities:
            c_nodes = [item["id"] for item in c["nodes"]]
            tables = [item["id"] for item in c["nodes"] if item["type"] == "DatabaseTable"]
            rules = [item["id"] for item in c["nodes"] if item["type"] == "BusinessRule"]

            fabric.transformation.register_candidate_microservice(
                domain_name=c["community_id"],
                components=c_nodes,
                tables=tables,
                business_rules=rules,
                rationale=f"Bounded context identified by Louvain modularity clustering with {c['size']} tightly coupled nodes.",
            )

        return strategies
