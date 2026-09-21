# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
ValidationTool: CodedTool for Validation & Anti-Hallucination QA Agent.
Verifies source line citations, checks SHA-256 integrity, and algorithmically flags
cross-artifact discrepancies between documentation, code, and SME notes.
"""

from coded_tools.modernize.tool_base import CodedTool
from coded_tools.modernize.graph.knowledge_graph_tool import get_knowledge_graph
from coded_tools.modernize.memory.memory_manager_tool import get_memory_fabric
from coded_tools.modernize.qa.provenance_validator import ProvenanceValidator


class ValidationTool(CodedTool):
    """
    CodedTool exposing provenance verification and discrepancy detection.
    """

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        fabric = get_memory_fabric(sly_data)
        kg = get_knowledge_graph(sly_data)
        action = args.get("action", "detect_discrepancies")
        repo_path = args.get("repo_path", "data/insurance_claims_app")

        if len(fabric.raw._files) == 0:
            fabric.raw.ingest_directory(repo_path)

        if action == "verify_provenance":
            source_file = args.get("source_file", "")
            line_start = int(args.get("line_start", 1))
            line_end = int(args.get("line_end", line_start))
            expected_tokens = args.get("expected_tokens", [])

            result = ProvenanceValidator.verify_provenance(
                fabric=fabric,
                source_file=source_file,
                line_start=line_start,
                line_end=line_end,
                expected_tokens=expected_tokens,
            )
            return {"status": "success", "provenance": result}

        elif action in ("detect_discrepancies", "check_discrepancies"):
            discrepancies = ProvenanceValidator.detect_discrepancies(fabric)
            injected = 0
            if kg and kg.graph.number_of_nodes() > 0:
                injected = ProvenanceValidator.inject_discrepancies_into_graph(kg, discrepancies)

            return {
                "status": "success",
                "total_discrepancies": len(discrepancies),
                "injected_into_graph_count": injected,
                "discrepancies": discrepancies,
                "summary": f"Detected {len(discrepancies)} cross-artifact discrepancies and architectural risks.",
            }

        elif action == "validate_knowledge_fabric":
            discrepancies = ProvenanceValidator.detect_discrepancies(fabric)
            # Check sample node line numbers
            total_verified = 0
            sample_nodes = list(kg.graph.nodes(data=True)) if kg else []
            for n_id, attrs in sample_nodes:
                src = attrs.get("source_file")
                ls = attrs.get("line_start", 1)
                le = attrs.get("line_end", ls)
                if src and src != "System":
                    res = ProvenanceValidator.verify_provenance(fabric, src, ls, le)
                    if res.get("verified"):
                        total_verified += 1

            provenance_coverage = (total_verified / len(sample_nodes)) if sample_nodes else 1.0

            return {
                "status": "success",
                "provenance_coverage_score": round(provenance_coverage, 2),
                "total_nodes_evaluated": len(sample_nodes),
                "total_nodes_verified": total_verified,
                "discrepancies_count": len(discrepancies),
            }

        return {
            "status": "error",
            "message": f"Unknown action: {action}. Supported actions: detect_discrepancies, verify_provenance, validate_knowledge_fabric",
        }

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        return self.invoke(args, sly_data)
