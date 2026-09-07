#!/usr/bin/env python
"""
ModernizeAI CLI: Hybrid Agentic Graph-RAG Knowledge Fabric Runner
Allows direct CLI querying with real-time agent node tracking, 
step-by-step LLM reasoning traces, and interactive REPL mode.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure root workspace is on path
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)


load_dotenv()

from coded_tools.modernize.swarm_coordinator import ModernizeSwarmCoordinator

AGENT_ICONS = {
    "frontman": "👑",
    "frontman_agent": "👑",
    "discovery_agent": "🔍",
    "code_intel_agent": "☕",
    "database_intel_agent": "🗄️",
    "doc_intel_agent": "📄",
    "business_rules_agent": "⚖️",
    "validation_agent": "🛡️",
    "knowledge_graph_agent": "🌐",
    "memory_manager_agent": "💾",
    "impact_analysis_agent": "💥",
    "modernization_advisor_agent": "🧭",
}


def print_banner():
    print("=" * 76)
    print(" 🚀 ModernizeAI | Hybrid Agentic Graph-RAG Swarm Coordinator (CLI)")
    print("    Architecture: 80% Deterministic (KG + 5-Tier Memory) / 20% LLM Reasoning")
    print("=" * 76)


def run_query(query: str, coordinator: ModernizeSwarmCoordinator):
    print(f"\n💬 Query: \"{query}\"")
    print("-" * 76)
    print("⚙️  Invoking Multi-Agent Swarm...\n")

    res = coordinator.execute_query(query)

    # 1. Agent Traversal Pipeline
    agent_path = res.get("agent_path", [])
    path_str = " ➔ ".join([f"{AGENT_ICONS.get(a, '🤖')} {a.replace('_agent', '').title()}" for a in agent_path])
    print(f"⚡ Active Agent Traversal Pipeline ({len(agent_path)} Nodes Visited):")
    print(f"   {path_str}\n")

    # 2. Agent-by-Agent Reasoning Trace
    print("🔍 Step-by-Step Agent LLM Reasoning & Decision Trace:")
    trace = res.get("trace", [])
    for t in trace:
        agent_id = t.get("agent", "")
        icon = AGENT_ICONS.get(agent_id, "🤖")
        step_num = t.get("step", 1)
        action = t.get("action", "")
        thought = t.get("thought", "")
        summary = t.get("result_summary", "")

        print(f"   [{step_num}] {icon} {agent_id.replace('_agent', '').title()} ➔ {action}")
        print(f"       💭 Thought: {thought}")
        print(f"       🎯 Outcome: {summary}")

    # 3. Blast Radius Impact (if present)
    blast = res.get("blast_radius")
    if blast and blast.get("target_entity"):
        print(f"\n💥 Blast-Radius Impact Alert: {blast.get('target_entity')}")
        print(f"   Risk Level: {blast.get('risk_level')} | Total Affected Components: {blast.get('total_affected_count')}")
        print(f"   Upstream Callers: {blast.get('upstream_count')} | Downstream Dependencies: {blast.get('downstream_count')}")

    # 4. Final LLM Synthesized Answer
    print("\n" + "=" * 76)
    print("🧠 Gemini LLM Reasoning Synthesis:")
    print("=" * 76)
    print(res.get("final_answer", "").strip())
    print("=" * 76)

    # 5. Provenance Citations
    hybrid = res.get("hybrid_rag", {})
    evidence = hybrid.get("fused_evidence", [])
    if evidence:
        print("\n📜 Grounded Knowledge Fabric Evidence (RRF Fused):")
        for idx, ev in enumerate(evidence[:3], 1):
            print(f"   [{idx}] {ev.get('label')} (RRF: {ev.get('rrf_score')}) | Citation: {ev.get('citation')}")
            print(f"       \"{ev.get('content')[:120]}...\"")
    print("-" * 76 + "\n")


def main():
    parser = argparse.ArgumentParser(description="ModernizeAI Swarm CLI Runner")
    parser.add_argument("--query", "-q", type=str, help="Query to run directly")
    parser.add_argument("--interactive", "-i", action="store_true", help="Start interactive CLI loop")
    args = parser.parse_args()

    print_banner()
    coordinator = ModernizeSwarmCoordinator()

    if args.query:
        run_query(args.query, coordinator)
    else:
        print("\nEntering Interactive Query Loop. Type 'exit' or 'quit' to end.")
        sample_queries = [
            "What tables and procedures are affected if POLICY_MASTER is modified?",
            "What business rules govern insurance claim validation and deductibles?",
            "What candidate microservices are identified by community detection?"
        ]
        print("Sample Queries to try:")
        for idx, sq in enumerate(sample_queries, 1):
            print(f"  {idx}. {sq}")
        print("-" * 76)

        while True:
            try:
                user_input = input("\n[ModernizeAI-CLI] > ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    print("Exiting ModernizeAI CLI. Goodbye!")
                    break
                run_query(user_input, coordinator)
            except (KeyboardInterrupt, EOFError):
                print("\nSession terminated.")
                break


if __name__ == "__main__":
    main()
