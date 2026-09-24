# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
ProjectScanner: the orchestrator that ties everything in this layer together.
For one Source: fetch its documents, ingest them into a fresh per-source
MemoryFabric, run the parser pipeline, remove that source's previous nodes
from the project's persisted graph, rebuild them, and save. For a whole
Project: do that for every Source without wiping anyone else's contribution -
the property the old single-repo `/api/scan` never had (it cleared the
entire global graph on every scan; see apps/modernizeai_ui/server.py).
"""

import time
import traceback
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict
from typing import Optional

from coded_tools.modernize.graph.graph_builder import GraphBuilder
from coded_tools.modernize.graph.graph_builder import remove_source_nodes
from coded_tools.modernize.graph.store import GraphStore
from coded_tools.modernize.graph.store import get_default_store
from coded_tools.modernize.parsers.pipeline import parse_repository
from coded_tools.modernize.sources.base import ConnectionTestResult
from coded_tools.modernize.sources.models import ProjectStore
from coded_tools.modernize.sources.registry import build_connector


@dataclass
class SourceScanResult:
    source_id: str
    status: str  # "scanned" | "unchanged" | "error"
    documents_ingested: int = 0
    message: str = ""
    parse_report: Dict[str, Any] = field(default_factory=dict)
    graph_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "documents_ingested": self.documents_ingested,
            "message": self.message,
            "parse_report": self.parse_report,
            "graph_stats": self.graph_stats,
        }


class ProjectScanner:
    def __init__(self, project_store: Optional[ProjectStore] = None, graph_store: Optional[GraphStore] = None):
        self.project_store = project_store or ProjectStore()
        self.graph_store = graph_store or get_default_store()

    def test_source(self, project_name: str, source_id: str) -> ConnectionTestResult:
        project = self.project_store.load(project_name)
        source = project.get_source(source_id)
        if source is None:
            return ConnectionTestResult(ok=False, message=f"Source '{source_id}' not found.")
        try:
            connector = build_connector(source)
            return connector.test_connection()
        except Exception as e:  # noqa: BLE001 - surface any connector failure as a clean test result
            return ConnectionTestResult(ok=False, message=str(e))

    def scan_source(self, project_name: str, source_id: str, force_full: bool = False) -> SourceScanResult:
        # Local import: MemoryFabric lives in the memory package, which itself
        # imports the parser shims - importing it at module load time would
        # create a cycle with coded_tools.modernize.parsers.pipeline.
        from coded_tools.modernize.memory.memory_manager_tool import MemoryFabric

        project = self.project_store.load(project_name)
        source = project.get_source(source_id)
        if source is None:
            raise ValueError(f"Source '{source_id}' not found in project '{project_name}'.")

        try:
            connector = build_connector(source)
            since = None if force_full else source.last_fingerprint
            documents, fingerprint = connector.fetch(since)
        except Exception as e:
            source.last_scan_status = "error"
            source.last_scan_message = str(e)
            source.last_scanned_at = time.time()
            self.project_store.save(project)
            traceback.print_exc()
            return SourceScanResult(source_id=source_id, status="error", message=str(e))

        if not force_full and fingerprint == source.last_fingerprint:
            source.last_scan_status = "success"
            source.last_scan_message = "No changes since last scan."
            source.last_scanned_at = time.time()
            self.project_store.save(project)
            return SourceScanResult(source_id=source_id, status="unchanged", message="No changes since last scan.")

        fabric = MemoryFabric()
        for doc in documents:
            fabric.raw.ingest_document(source_id, source.type, doc)
        report = parse_repository(fabric)

        kg = self.graph_store.load(project_name)
        remove_source_nodes(kg, source_id)
        graph_stats = GraphBuilder.build(kg, fabric, source_id=source_id)
        self.graph_store.save(project_name, kg)

        source.last_fingerprint = fingerprint
        source.last_scanned_at = time.time()
        source.last_scan_status = "success"
        source.last_scan_message = f"{len(documents)} document(s) ingested, {report.files_parsed} parsed."
        self.project_store.save(project)

        return SourceScanResult(
            source_id=source_id,
            status="scanned",
            documents_ingested=len(documents),
            message=source.last_scan_message,
            parse_report=report.to_dict(),
            graph_stats=graph_stats,
        )

    def scan_all(self, project_name: str, force_full: bool = False) -> Dict[str, SourceScanResult]:
        project = self.project_store.load(project_name)
        results: Dict[str, SourceScanResult] = {}
        for source in project.sources:
            results[source.source_id] = self.scan_source(project_name, source.source_id, force_full=force_full)
        return results
