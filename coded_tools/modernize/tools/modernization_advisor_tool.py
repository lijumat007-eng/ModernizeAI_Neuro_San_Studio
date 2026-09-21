# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
ModernizationAdvisorTool: CodedTool for Modernization Advisor Agent.
Calculates mathematical readiness scores, formulates 6R cloud migration strategies,
and generates deliverable markdown reports.
"""

from coded_tools.modernize.tool_base import CodedTool
from coded_tools.modernize.advisor.modernization_scoring import ModernizationScoring
from coded_tools.modernize.graph.knowledge_graph_tool import get_knowledge_graph
from coded_tools.modernize.memory.memory_manager_tool import get_memory_fabric
from coded_tools.modernize.reports.report_generator import ReportGenerator


class ModernizationAdvisorTool(CodedTool):
    """
    CodedTool exposing dynamic modernization scoring, 6R classifications, and report generation.
    """

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        fabric = get_memory_fabric(sly_data)
        kg = get_knowledge_graph(sly_data)
        action = args.get("action", "calculate_readiness_score")
        repo_path = args.get("repo_path", "data/insurance_claims_app")

        # Ingest & build graph if empty
        if len(fabric.raw._files) == 0:
            fabric.raw.ingest_directory(repo_path)
        if kg.graph.number_of_nodes() == 0:
            from coded_tools.modernize.graph.knowledge_graph_tool import KnowledgeGraphTool
            KnowledgeGraphTool().invoke({"action": "build_graph", "repo_path": repo_path}, sly_data)

        if action in ("calculate_readiness_score", "readiness"):
            score_data = ModernizationScoring.calculate_readiness_score(kg, fabric)
            return {
                "status": "success",
                "readiness": score_data,
                "summary": f"Calculated Modernization Readiness Score: {score_data['overall_readiness_score']}/100 ({score_data['grade']})",
            }

        elif action in ("generate_6r_strategy", "recommend_strategies"):
            strategies = ModernizationScoring.generate_6r_strategies(kg, fabric)
            score_data = ModernizationScoring.calculate_readiness_score(kg, fabric)
            return {
                "status": "success",
                "readiness_score": score_data["overall_readiness_score"],
                "total_strategies": len(strategies),
                "strategies": strategies,
                "tier5_memory": fabric.transformation.to_dict(),
            }

        elif action == "generate_reports":
            output_dir = args.get("output_dir", "artifacts")
            # Populate 6R strategies and scores first
            ModernizationScoring.generate_6r_strategies(kg, fabric)
            paths = ReportGenerator.generate_all(kg, fabric, output_dir=output_dir)
            score_data = ModernizationScoring.calculate_readiness_score(kg, fabric)
            return {
                "status": "success",
                "readiness_score": score_data["overall_readiness_score"],
                "generated_reports": paths,
            }

        return {
            "status": "error",
            "message": f"Unknown action: {action}. Supported actions: calculate_readiness_score, generate_6r_strategy, generate_reports",
        }

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        return self.invoke(args, sly_data)
