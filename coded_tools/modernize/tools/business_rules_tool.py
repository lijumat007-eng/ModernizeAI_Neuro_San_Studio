# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
BusinessRulesTool: CodedTool for Business Rules Agent.
Dynamically extracts, formalizes, and catalogs enterprise business rules from source code,
SQL stored procedures, and specifications.
"""

from typing import Any
from typing import Dict

from coded_tools.modernize.memory.memory_manager_tool import get_memory_fabric
from coded_tools.modernize.parsers.rules_extractor import RulesExtractor
from coded_tools.modernize.tool_base import CodedTool


class BusinessRulesTool(CodedTool):
    """
    CodedTool exposing dynamic business rules extraction and querying.
    """

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        fabric = get_memory_fabric(sly_data)
        action = args.get("action", "extract_rules")
        repo_path = args.get("repo_path", "data/insurance_claims_app")

        # Ingest repo if raw memory is empty
        if len(fabric.raw._files) == 0:
            fabric.raw.ingest_directory(repo_path)

        if action in ("extract_rules", "list_rules"):
            rules = RulesExtractor.extract_all(fabric)
            return {
                "status": "success",
                "total_rules_extracted": len(rules),
                "rules": rules,
                "summary": (
                    f"Dynamically extracted {len(rules)} business rules from code AST, stored procedures, and specs."
                ),
            }

        elif action == "get_rule":
            rule_id = args.get("rule_id", "BR-01").upper()
            rules = RulesExtractor.extract_all(fabric)
            matched = next((r for r in rules if r["rule_id"] == rule_id), None)
            if matched:
                return {
                    "status": "success",
                    "rule": matched,
                }
            return {
                "status": "not_found",
                "message": f"Rule '{rule_id}' not found.",
                "available_rules": [r["rule_id"] for r in rules],
            }

        return {
            "status": "error",
            "message": f"Unknown action: {action}. Supported actions: extract_rules, list_rules, get_rule",
        }

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        return self.invoke(args, sly_data)
