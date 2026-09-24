# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
DiscoveryTool: CodedTool for Discovery Agent.
Dynamically scans repository directories, catalogs legacy code, database schemas,
and specifications, and registers them into Tier 1 Raw Memory.
"""

from typing import Any
from typing import Dict
from typing import List

from coded_tools.modernize.memory.memory_manager_tool import get_memory_fabric
from coded_tools.modernize.tool_base import CodedTool


class DiscoveryTool(CodedTool):
    """
    CodedTool exposing repository scanning and artifact cataloging.
    """

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        fabric = get_memory_fabric(sly_data)
        action = args.get("action", "scan_repository")
        repo_path = args.get("repo_path", "data/insurance_claims_app")

        if action in ("scan_repository", "ingest_repo", "catalog"):
            records = fabric.raw.ingest_directory(repo_path)

            catalog: Dict[str, List[Dict[str, Any]]] = {
                "java_source_files": [],
                "sql_database_files": [],
                "architecture_specs": [],
                "sme_interview_notes": [],
                "other_files": [],
            }

            for p, r in fabric.raw._files.items():
                item = {
                    "path": r.rel_path,
                    "sha256": r.sha256[:16] + "...",
                    "line_count": r.line_count,
                    "size_bytes": getattr(r, "byte_size", 0),
                }
                if p.endswith(".java"):
                    catalog["java_source_files"].append(item)
                elif p.endswith((".sql", ".ddl")):
                    catalog["sql_database_files"].append(item)
                elif p.endswith(".md"):
                    catalog["architecture_specs"].append(item)
                elif "sme" in p.lower() or p.endswith(".txt"):
                    catalog["sme_interview_notes"].append(item)
                else:
                    catalog["other_files"].append(item)

            return {
                "status": "success",
                "repo_path": repo_path,
                "total_files_discovered": len(records),
                "catalog": catalog,
                "summary": (
                    f"Discovered and ingested {len(records)} assets: "
                    f"{len(catalog['java_source_files'])} Java files, "
                    f"{len(catalog['sql_database_files'])} SQL files, "
                    f"{len(catalog['architecture_specs'])} specs, "
                    f"{len(catalog['sme_interview_notes'])} SME notes."
                ),
            }

        elif action == "list_catalog":
            files = [
                {"path": r.rel_path, "lines": r.line_count, "sha256": r.sha256[:12]}
                for r in fabric.raw._files.values()
            ]
            return {"status": "success", "total_files": len(files), "files": files}

        return {
            "status": "error",
            "message": f"Unknown action: {action}. Supported actions: scan_repository, list_catalog",
        }

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Any:
        return self.invoke(args, sly_data)
