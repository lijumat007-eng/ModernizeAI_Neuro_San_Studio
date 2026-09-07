# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Upgraded Graph-RAG Algorithms for the Knowledge Fabric.
Includes:
- Personalized PageRank (PPR) / Random Walk with Restart
- Louvain Community Detection for Candidate Microservices
- Bidirectional Blast-Radius BFS & Transitive Closure
- Reciprocal Rank Fusion (RRF) Hybrid Retrieval
"""

from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx
from networkx.algorithms.community import louvain_communities


class GraphAlgorithms:
    """
    Advanced Graph-RAG and structural analysis algorithms.
    """

    @staticmethod
    def personalized_pagerank(
        graph: nx.MultiDiGraph,
        seed_nodes: List[str],
        alpha: float = 0.85,
        max_iter: int = 100,
    ) -> Dict[str, float]:
        """
        Runs Personalized PageRank biased toward seed nodes.
        Converts MultiDiGraph to weighted DiGraph for convergence.
        """
        if not seed_nodes:
            return {}

        valid_seeds = [s for s in seed_nodes if graph.has_node(s)]
        if not valid_seeds:
            return {}

        # Convert to simple directed graph with weights
        di_g = nx.DiGraph()
        for u, v, data in graph.edges(data=True):
            # Give higher weight to functional mutation edges
            edge_type = data.get("edge_type", "")
            w = 2.0 if edge_type in ("WRITES_TO", "CALLS") else 1.0
            if di_g.has_edge(u, v):
                di_g[u][v]["weight"] += w
            else:
                di_g.add_edge(u, v, weight=w)

        # Ensure all nodes exist
        for n in graph.nodes():
            if not di_g.has_node(n):
                di_g.add_node(n)

        personalization = {n: (1.0 / len(valid_seeds) if n in valid_seeds else 0.0) for n in di_g.nodes()}
        try:
            ppr = nx.pagerank(di_g, alpha=alpha, personalization=personalization, max_iter=max_iter, weight="weight")
            return {k: round(v, 5) for k, v in sorted(ppr.items(), key=lambda item: item[1], reverse=True)}
        except Exception:
            # Fallback if disconnected or ill-conditioned
            return {s: 1.0 for s in valid_seeds}

    @staticmethod
    def detect_communities(graph: nx.MultiDiGraph) -> List[Dict[str, Any]]:
        """
        Runs Louvain Community Detection to group coupled components into candidate microservices.
        """
        # Convert to undirected graph
        undirected = nx.Graph()
        for u, v in graph.edges():
            undirected.add_edge(u, v)
        for n in graph.nodes():
            if not undirected.has_node(n):
                undirected.add_node(n)

        if undirected.number_of_nodes() == 0:
            return []

        try:
            communities = louvain_communities(undirected, seed=42)
        except Exception:
            # Fallback to connected components
            communities = list(nx.connected_components(undirected))

        results = []
        for idx, comm in enumerate(communities):
            nodes_data = []
            node_types = {}
            for n in comm:
                data = graph.nodes.get(n, {})
                nt = data.get("node_type", "Unknown")
                node_types[nt] = node_types.get(nt, 0) + 1
                nodes_data.append({
                    "id": n,
                    "type": nt,
                    "label": data.get("label", n),
                })

            # Formulate domain label
            primary_type = max(node_types, key=node_types.get) if node_types else "Component"
            results.append({
                "community_id": f"Domain_{idx + 1}",
                "size": len(comm),
                "type_breakdown": node_types,
                "nodes": nodes_data,
            })

        return results

    @staticmethod
    def calculate_blast_radius(
        graph: nx.MultiDiGraph,
        target_entity: str,
        max_depth: int = 3,
    ) -> Dict[str, Any]:
        """
        Computes upstream and downstream blast radius with exact hop distances and risk classification.
        """
        if not graph.has_node(target_entity):
            # Try case-insensitive or partial match
            matched = [n for n in graph.nodes() if target_entity.lower() in n.lower()]
            if matched:
                target_entity = matched[0]
            else:
                return {"error": f"Target entity '{target_entity}' not found in Knowledge Graph."}

        # 1. Upstream Impact (Who depends on or calls target_entity?)
        # Incoming edges: A -> target_entity means A will break if target_entity changes
        upstream_impact: List[Dict[str, Any]] = []
        visited_up = {target_entity}
        queue_up = deque([(target_entity, 0, [])])

        while queue_up:
            curr, depth, path = queue_up.popleft()
            if depth >= max_depth:
                continue

            for pred in graph.predecessors(curr):
                for k, edge_data in graph.get_edge_data(pred, curr).items():
                    edge_type = edge_data.get("edge_type", k)
                    step = f"{pred} --({edge_type})--> {curr}"
                    new_path = path + [step]
                    
                    if pred not in visited_up:
                        visited_up.add(pred)
                        node_data = dict(graph.nodes[pred])
                        upstream_impact.append({
                            "node_id": pred,
                            "node_type": node_data.get("node_type", "Unknown"),
                            "hop_distance": depth + 1,
                            "edge_type": edge_type,
                            "path": " -> ".join(new_path),
                            "source_file": node_data.get("source_file", ""),
                            "line_start": node_data.get("line_start", 1),
                            "line_end": node_data.get("line_end", 1),
                        })
                        queue_up.append((pred, depth + 1, new_path))

        # 2. Downstream Impact (What does target_entity depend on or modify?)
        # Outgoing edges: target_entity -> B
        downstream_impact: List[Dict[str, Any]] = []
        visited_down = {target_entity}
        queue_down = deque([(target_entity, 0, [])])

        while queue_down:
            curr, depth, path = queue_down.popleft()
            if depth >= max_depth:
                continue

            for succ in graph.successors(curr):
                for k, edge_data in graph.get_edge_data(curr, succ).items():
                    edge_type = edge_data.get("edge_type", k)
                    step = f"{curr} --({edge_type})--> {succ}"
                    new_path = path + [step]
                    
                    if succ not in visited_down:
                        visited_down.add(succ)
                        node_data = dict(graph.nodes[succ])
                        downstream_impact.append({
                            "node_id": succ,
                            "node_type": node_data.get("node_type", "Unknown"),
                            "hop_distance": depth + 1,
                            "edge_type": edge_type,
                            "path": " -> ".join(new_path),
                            "source_file": node_data.get("source_file", ""),
                            "line_start": node_data.get("line_start", 1),
                            "line_end": node_data.get("line_end", 1),
                        })
                        queue_down.append((succ, depth + 1, new_path))

        # 3. Detect Cycles / Strongly Connected Components
        di_g = nx.DiGraph(graph)
        cycles = list(nx.simple_cycles(di_g))
        relevant_cycles = [c for c in cycles if target_entity in c]

        # Calculate blast radius risk level
        total_affected = len(upstream_impact) + len(downstream_impact)
        if total_affected > 8 or len(relevant_cycles) > 0:
            risk_level = "CRITICAL / HIGH RISK"
        elif total_affected > 3:
            risk_level = "MEDIUM RISK"
        else:
            risk_level = "LOW RISK"

        return {
            "target_entity": target_entity,
            "target_data": dict(graph.nodes[target_entity]),
            "risk_level": risk_level,
            "total_affected_count": total_affected,
            "upstream_count": len(upstream_impact),
            "downstream_count": len(downstream_impact),
            "upstream_impact": upstream_impact,
            "downstream_impact": downstream_impact,
            "cyclic_dependencies": relevant_cycles,
        }

    @staticmethod
    def hybrid_rrf_retrieval(
        semantic_results: List[Dict[str, Any]],
        ppr_scores: Dict[str, float],
        graph: nx.MultiDiGraph,
        k: int = 60,
        top_n: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF) combining semantic document results and graph structural centrality.
        """
        fused_scores: Dict[str, float] = {}
        entity_evidence: Dict[str, Dict[str, Any]] = {}

        # 1. Score from Semantic Memory
        for rank, sem in enumerate(semantic_results):
            cid = sem.get("chunk_id", str(rank))
            rrf = 1.0 / (k + rank + 1)
            fused_scores[cid] = fused_scores.get(cid, 0.0) + rrf
            entity_evidence[cid] = {
                "source": "semantic_doc",
                "label": sem.get("source_file", ""),
                "content": sem.get("content", ""),
                "line": f"L{sem.get('start_line')}-{sem.get('end_line')}",
                "raw_score": sem.get("score", 0.0),
            }

        # 2. Score from Graph PPR
        for rank, (node_id, ppr) in enumerate(ppr_scores.items()):
            rrf = 1.0 / (k + rank + 1)
            fused_scores[node_id] = fused_scores.get(node_id, 0.0) + rrf
            node_data = dict(graph.nodes.get(node_id, {}))
            entity_evidence[node_id] = {
                "source": "knowledge_graph",
                "label": f"[{node_data.get('node_type')}] {node_id}",
                "content": node_data.get("evidence_snippet") or f"{node_data.get('node_type')} entity in {node_data.get('source_file')}",
                "line": f"L{node_data.get('line_start', 1)}-{node_data.get('line_end', 1)}",
                "raw_score": ppr,
            }

        sorted_entities = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        results = []
        for entity_id, score in sorted_entities:
            ev = entity_evidence.get(entity_id, {})
            results.append({
                "entity_id": entity_id,
                "rrf_score": round(score, 5),
                "source": ev.get("source"),
                "label": ev.get("label"),
                "content": ev.get("content"),
                "citation": f"{ev.get('label')} ({ev.get('line')})",
            })
        return results
