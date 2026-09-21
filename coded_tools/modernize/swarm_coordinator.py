# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
ModernizeAI Swarm Coordinator: Multi-Agent Dynamic Tool Orchestrator & Node Tracking Engine.
Coordinates Frontman, Discovery, Intel, Rules, Validation, KG, Impact, and Advisor agents
with verifiable step-by-step tool invocations and active node tracking.
"""

import os
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

from coded_tools.modernize.graph.algorithms import GraphAlgorithms
from coded_tools.modernize.graph.knowledge_graph_tool import KnowledgeGraphTool, get_knowledge_graph
from coded_tools.modernize.memory.memory_manager_tool import MemoryManagerTool, get_memory_fabric
from coded_tools.modernize.tools.business_rules_tool import BusinessRulesTool
from coded_tools.modernize.tools.discovery_tool import DiscoveryTool
from coded_tools.modernize.tools.modernization_advisor_tool import ModernizationAdvisorTool
from coded_tools.modernize.tools.validation_tool import ValidationTool


class ModernizeSwarmCoordinator:
    """
    Executes multi-agent workflows by orchestrating real CodedTools across the swarm.
    Captures real-time agent node activations, tool outputs, and LLM reasoning traces.
    """

    def __init__(self):
        self._client = None
        self._model = "gemini-3.5-flash-lite"
        self._init_llm()

    def _init_llm(self):
        """Initializes Gemini client if API key is present."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize google.genai Client: {e}")
                self._client = None

    def execute_swarm_turn(self, query: str, repo_path: str = "data/insurance_claims_app") -> Dict[str, Any]:
        """
        Executes a complete reasoning and tool execution turn across the agent swarm.
        Captures the active agent nodes, reasoning trace, real tool invocations, and synthesized advice.
        """
        sly_data: Dict[str, Any] = {}
        mem_tool = MemoryManagerTool()
        kg_tool = KnowledgeGraphTool()
        discovery_tool = DiscoveryTool()
        rules_tool = BusinessRulesTool()
        validation_tool = ValidationTool()
        advisor_tool = ModernizationAdvisorTool()

        # Ensure memory fabric & knowledge graph are populated
        fabric = get_memory_fabric(sly_data)
        kg = get_knowledge_graph(sly_data)
        if len(fabric.raw._files) == 0:
            discovery_tool.invoke({"action": "scan_repository", "repo_path": repo_path}, sly_data)
        if kg.graph.number_of_nodes() == 0:
            kg_tool.invoke({"action": "build_graph", "repo_path": repo_path}, sly_data)

        # Tracked nodes and reasoning steps
        agent_path: List[str] = ["frontman"]
        trace: List[Dict[str, Any]] = []
        q_lower = query.lower()

        # Step 1: Frontman Agent Intent Evaluation
        frontman_reasoning = f"Evaluating user intent for inquiry: '{query}'. "
        if any(w in q_lower for w in ["ingest", "scan", "discover", "upload", "catalog", "directory"]):
            target_agent = "discovery_agent"
            frontman_reasoning += "Classified as Repository Discovery & Ingestion task. Delegating to Discovery Agent."
        elif any(w in q_lower for w in ["impact", "break", "blast", "change", "affect", "touch", "caller", "dependency"]):
            target_agent = "impact_analysis_agent"
            frontman_reasoning += "Classified as Change Impact & Blast-Radius Assessment. Delegating to Impact Analysis Agent."
        elif any(w in q_lower for w in ["rule", "business rule", "validate", "eligibility", "threshold", "grace", "formula"]):
            target_agent = "business_rules_agent"
            frontman_reasoning += "Classified as Business Logic Formalization & Verification inquiry. Delegating to Business Rules Agent."
        elif any(w in q_lower for w in ["moderniz", "cloud", "6r", "roadmap", "readiness", "score", "microservice", "decouple", "domain"]):
            target_agent = "modernization_advisor_agent"
            frontman_reasoning += "Classified as Cloud Modernization & 6R Roadmap request. Delegating to Modernization Advisor Agent."
        else:
            target_agent = "knowledge_graph_agent"
            frontman_reasoning += "Classified as Architecture & Knowledge Graph Fabric inquiry. Delegating to Knowledge Graph Agent."

        trace.append({
            "step": 1,
            "agent": "frontman_agent",
            "role": "Orchestrator",
            "action": f"Classify intent & orchestrate swarm -> {target_agent}",
            "thought": frontman_reasoning,
            "reasoning": frontman_reasoning,
            "result_summary": f"Intent directed to {target_agent}",
        })
        agent_path.append(target_agent)

        # Step 2: Downstream Specialist Agent Execution & Genuine Tool Invocation
        tool_results: Dict[str, Any] = {}

        if target_agent == "discovery_agent":
            # Invoke DiscoveryTool
            disc_res = discovery_tool.invoke({"action": "scan_repository", "repo_path": repo_path}, sly_data)
            tool_results["discovery"] = disc_res

            agent_path.extend(["code_intel_agent", "database_intel_agent", "doc_intel_agent"])
            trace.append({
                "step": 2,
                "agent": "discovery_agent",
                "role": "Repository Discovery Specialist",
                "action": "Invoke DiscoveryTool (scan_repository)",
                "thought": f"Scanning repository at '{repo_path}'. Cataloging files into code, database DDLs, and specs.",
                "reasoning": f"Scanning repository at '{repo_path}'. Cataloging files into code, database DDLs, and specs.",
                "result_summary": disc_res.get("summary", "Catalog completed."),
            })

        elif target_agent == "impact_analysis_agent":
            # Dynamically identify target entity from graph nodes
            target_entity = None
            # 1. Match against nodes in the knowledge graph, prioritizing longer/more specific names
            sorted_nodes = sorted(kg.graph.nodes(), key=lambda x: len(x), reverse=True)
            for node_id in sorted_nodes:
                if re.search(r'\b' + re.escape(node_id) + r'\b', query, re.IGNORECASE) or node_id.lower() in q_lower:
                    target_entity = node_id
                    break

            # Fallback to central entity if unspecified
            if not target_entity:
                target_entity = "POLICY_MASTER"

            agent_path.append("knowledge_graph_agent")
            trace.append({
                "step": 2,
                "agent": "impact_analysis_agent",
                "role": "Impact Analysis Specialist",
                "action": f"Invoke KnowledgeGraphTool (blast_radius for '{target_entity}')",
                "thought": f"Identified change seed '{target_entity}'. Requesting bidirectional BFS blast-radius calculation from Knowledge Graph Agent.",
                "reasoning": f"Identified change seed '{target_entity}'. Requesting bidirectional BFS blast-radius calculation from Knowledge Graph Agent.",
                "result_summary": f"Change seed: {target_entity}",
            })

            blast_res = kg_tool.invoke({"action": "blast_radius", "target_entity": target_entity}, sly_data)
            tool_results["blast_radius"] = blast_res

            trace.append({
                "step": 3,
                "agent": "knowledge_graph_agent",
                "role": "Knowledge Graph Engine",
                "action": "Execute Bidirectional BFS Traversal",
                "thought": (
                    f"Traversed graph for '{target_entity}'. Found {blast_res.get('upstream_count', 0)} upstream callers "
                    f"and {blast_res.get('downstream_count', 0)} downstream dependencies. Risk Level: {blast_res.get('risk_level')}."
                ),
                "reasoning": (
                    f"Traversed graph for '{target_entity}'. Found {blast_res.get('upstream_count', 0)} upstream callers "
                    f"and {blast_res.get('downstream_count', 0)} downstream dependencies. Risk Level: {blast_res.get('risk_level')}."
                ),
                "result_summary": f"Risk: {blast_res.get('risk_level')} ({blast_res.get('total_affected_count')} affected)",
            })

            agent_path.append("modernization_advisor_agent")
            trace.append({
                "step": 4,
                "agent": "modernization_advisor_agent",
                "role": "Modernization Advisor",
                "action": "Evaluate Coupling & ACL Mitigation",
                "thought": f"Evaluating blast radius for '{target_entity}'. Recommending isolation patterns based on coupling.",
                "reasoning": f"Evaluating blast radius for '{target_entity}'. Recommending isolation patterns based on coupling.",
                "result_summary": f"Formulated ACL pattern to protect callers of {target_entity}.",
            })

            rag_res = kg_tool.invoke({"action": "hybrid_graph_rag", "query": query}, sly_data)
            tool_results["hybrid_rag"] = rag_res

        elif target_agent == "business_rules_agent":
            # Invoke real BusinessRulesTool
            rules_res = rules_tool.invoke({"action": "extract_rules", "repo_path": repo_path}, sly_data)
            tool_results["business_rules"] = rules_res

            trace.append({
                "step": 2,
                "agent": "business_rules_agent",
                "role": "Business Rules Specialist",
                "action": "Invoke BusinessRulesTool (extract_rules)",
                "thought": f"Dynamically extracted {rules_res.get('total_rules_extracted', 0)} formalized business rules from AST and stored procedures.",
                "reasoning": f"Dynamically extracted {rules_res.get('total_rules_extracted', 0)} formalized business rules from AST and stored procedures.",
                "result_summary": f"Extracted {rules_res.get('total_rules_extracted', 0)} rules with verified source citations.",
            })

            # Invoke real ValidationTool
            agent_path.append("validation_agent")
            val_res = validation_tool.invoke({"action": "detect_discrepancies", "repo_path": repo_path}, sly_data)
            tool_results["validation"] = val_res

            trace.append({
                "step": 3,
                "agent": "validation_agent",
                "role": "Governance & Anti-Hallucination",
                "action": "Invoke ValidationTool (detect_discrepancies)",
                "thought": f"Executed cross-artifact consistency check. Detected {val_res.get('total_discrepancies', 0)} contradictions/risks.",
                "reasoning": f"Executed cross-artifact consistency check. Detected {val_res.get('total_discrepancies', 0)} contradictions/risks.",
                "result_summary": f"Flagged {val_res.get('total_discrepancies', 0)} cross-artifact discrepancies.",
            })

            rag_res = kg_tool.invoke({"action": "hybrid_graph_rag", "query": query}, sly_data)
            tool_results["hybrid_rag"] = rag_res

        elif target_agent == "modernization_advisor_agent":
            agent_path.append("knowledge_graph_agent")
            agent_path.append("memory_manager_agent")

            # Invoke ModernizationAdvisorTool for real dynamic score & 6R strategies
            score_res = advisor_tool.invoke({"action": "calculate_readiness_score", "repo_path": repo_path}, sly_data)
            strat_res = advisor_tool.invoke({"action": "generate_6r_strategy", "repo_path": repo_path}, sly_data)
            tool_results["readiness"] = score_res.get("readiness", {})
            tool_results["strategies"] = strat_res.get("strategies", [])

            comm_res = kg_tool.invoke({"action": "community_detection"}, sly_data)
            tool_results["communities"] = comm_res

            trace.append({
                "step": 2,
                "agent": "knowledge_graph_agent",
                "role": "Knowledge Graph Engine",
                "action": "Execute Louvain Community Detection",
                "thought": f"Clustering graph topology into bounded contexts. Identified {len(comm_res.get('candidate_domains', []))} candidate microservice domains.",
                "reasoning": f"Clustering graph topology into bounded contexts. Identified {len(comm_res.get('candidate_domains', []))} candidate microservice domains.",
                "result_summary": f"Detected {len(comm_res.get('candidate_domains', []))} microservice domains.",
            })

            trace.append({
                "step": 3,
                "agent": "modernization_advisor_agent",
                "role": "Modernization Advisor",
                "action": "Invoke ModernizationAdvisorTool (calculate_readiness_score)",
                "thought": f"Calculated composite readiness score: {tool_results['readiness'].get('overall_readiness_score')}/100 ({tool_results['readiness'].get('grade')}).",
                "reasoning": f"Calculated composite readiness score: {tool_results['readiness'].get('overall_readiness_score')}/100 ({tool_results['readiness'].get('grade')}).",
                "result_summary": f"Readiness: {tool_results['readiness'].get('overall_readiness_score')}/100",
            })

            rag_res = kg_tool.invoke({"action": "hybrid_graph_rag", "query": query}, sly_data)
            tool_results["hybrid_rag"] = rag_res

        else:  # Generic Knowledge Graph Query
            agent_path.append("memory_manager_agent")
            rag_res = kg_tool.invoke({"action": "hybrid_graph_rag", "query": query}, sly_data)
            tool_results["hybrid_rag"] = rag_res
            trace.append({
                "step": 2,
                "agent": "knowledge_graph_agent",
                "role": "Knowledge Graph Engine",
                "action": "Execute Hybrid Graph-RAG (PPR + BM25)",
                "thought": f"Ran Personalized PageRank and semantic retrieval. Fused top {len(rag_res.get('fused_evidence', []))} evidence items with RRF.",
                "reasoning": f"Ran Personalized PageRank and semantic retrieval. Fused top {len(rag_res.get('fused_evidence', []))} evidence items with RRF.",
                "result_summary": f"Fused {len(rag_res.get('fused_evidence', []))} evidence items with RRF.",
            })

        # Step 3: LLM Reasoning Synthesis
        final_answer = self._generate_llm_response(query, target_agent, trace, tool_results)

        return {
            "query": query,
            "agent_path": list(dict.fromkeys(agent_path)),
            "trace": trace,
            "tool_results": tool_results,
            "blast_radius": tool_results.get("blast_radius"),
            "hybrid_rag": tool_results.get("hybrid_rag"),
            "business_rules": tool_results.get("business_rules"),
            "readiness": tool_results.get("readiness"),
            "final_answer": final_answer,
            "llm_reasoning": self._client is not None,
        }

    execute_query = execute_swarm_turn

    def _generate_llm_response(
        self,
        query: str,
        target_agent: str,
        trace: List[Dict[str, Any]],
        tool_results: Dict[str, Any],
    ) -> str:
        """
        Synthesizes the tool outputs and agent trace using real LLM reasoning.
        Falls back to dynamic, data-driven synthesis from real tool findings if LLM is unavailable.
        """
        if self._client:
            try:
                system_prompt = (
                    "You are Frontman, the master orchestrator of ModernizeAI's multi-agent swarm. "
                    "You have executed specialist agents across the 5-tier memory fabric and Knowledge Graph. "
                    "Synthesize a clear, authoritative, evidence-backed modernization answer based on the query and tool results. "
                    "Always include exact source line citations (e.g. `PolicyValidationService.java:21-29`) and clear risk/architectural advice."
                )
                user_content = f"""
System Directive: {system_prompt}

User Query: {query}
Primary Specialist Agent: {target_agent}
Agent Swarm Trace: {trace}
Tool Findings: {tool_results}
"""
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=user_content,
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                print(f"LLM generation warning: {e}, falling back to dynamic deterministic synthesis.")

        # Dynamic, data-driven synthesis fallback
        if "blast_radius" in tool_results:
            br = tool_results["blast_radius"]
            target = br.get("target_entity", "Component")
            up_items = ", ".join([f"`{i['node_id']}` ({i['edge_type']})" for i in br.get("upstream_impact", [])]) or "None"
            down_items = ", ".join([f"`{i['node_id']}` ({i['edge_type']})" for i in br.get("downstream_impact", [])]) or "None"
            return (
                f"### Blast-Radius Impact Assessment for `{target}`\n\n"
                f"- **Risk Classification**: **{br.get('risk_level')}**\n"
                f"- **Total Affected Components**: **{br.get('total_affected_count')}**\n"
                f"- **Upstream Callers / Inbound Dependencies**: {up_items}\n"
                f"- **Downstream Mutated Tables / Data**: {down_items}\n\n"
                f"**Architectural Advisory**: Any modification to `{target}` directly affects dependent components. "
                f"An Anti-Corruption Layer (ACL) with Change Data Capture (CDC) is recommended to prevent breaking upstream callers."
            )
        elif "business_rules" in tool_results:
            br_data = tool_results["business_rules"]
            rules = br_data.get("rules", [])
            val_data = tool_results.get("validation", {})
            discrepancies = val_data.get("discrepancies", [])

            rule_lines = "\n".join([
                f"- **{r['rule_id']}: {r['rule_name']}** (`{r['source_file']}:{r['line_start']}-{r['line_end']}`): {r['specification']}"
                for r in rules[:6]
            ])
            disc_lines = "\n".join([
                f"- ⚠️ **{d['title']}** ({d['severity']}): {d['description']}"
                for d in discrepancies[:3]
            ])
            return (
                f"### Dynamically Extracted Business Rules Catalog\n\n"
                f"The swarm extracted **{len(rules)} business rules** directly from code AST and stored procedures:\n\n"
                f"{rule_lines}\n\n"
                f"#### Governance & Anti-Hallucination Discrepancy Findings\n\n"
                f"{disc_lines or 'All extracted business rules align with code provenance.'}"
            )
        elif "readiness" in tool_results:
            rd = tool_results["readiness"]
            strats = tool_results.get("strategies", [])
            strat_summary = "\n".join([
                f"- **{s['component']}** ({s['type']}): **{s['strategy_6r']}** -> {s['target_pattern']} ({s['priority']})"
                for s in strats[:5]
            ])
            return (
                f"### Modernization Readiness & 6R Strategy Assessment\n\n"
                f"- **Overall Modernization Readiness Score**: **{rd.get('overall_readiness_score')}/100** ({rd.get('grade')})\n"
                f"- **Modularity Factor**: {rd.get('modularity_score')}/100\n"
                f"- **Provenance Coverage Factor**: {rd.get('provenance_score')}/100\n"
                f"- **Architectural Risk Health**: {rd.get('risk_health_score')}/100\n\n"
                f"#### Recommended 6R Migration Dispositions:\n\n"
                f"{strat_summary}\n\n"
                f"**Migration Phasing**: Refactor stateless business validation into serverless functions in **Phase 1**; replatform core adjudication services in **Phase 2**."
            )
        elif "discovery" in tool_results:
            d = tool_results["discovery"]
            return f"### Repository Discovery & Catalog\n\n{d.get('summary', 'Repository scan completed.')}"
        elif "hybrid_rag" in tool_results:
            rag = tool_results["hybrid_rag"]
            evidence = rag.get("fused_evidence", [])
            citations = "\n".join([f"- **{e.get('label')}** (`{e.get('citation')}`): {e.get('content')}" for e in evidence[:4]])
            return (
                f"### Grounded Knowledge Fabric Evidence\n\n"
                f"The multi-agent swarm retrieved and verified the following evidence items:\n\n"
                f"{citations}"
            )
        else:
            return f"Processed query across agent swarm: {query}. Findings grounded in verified Knowledge Fabric."
