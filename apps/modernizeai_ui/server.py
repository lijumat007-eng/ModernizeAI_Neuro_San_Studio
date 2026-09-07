# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
ModernizeAI Interactive Web UI Server.
FastAPI backend powering the interactive agent pipeline, Graph-RAG explorer, and artifacts review center.
"""

import os
import sys
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Ensure coded_tools is on python path
sys.path.insert(0, os.path.abspath("coded_tools"))
sys.path.insert(0, os.path.abspath("."))

from modernize.graph.algorithms import GraphAlgorithms
from modernize.graph.knowledge_graph_tool import KnowledgeGraphTool, get_knowledge_graph
from modernize.memory.memory_manager_tool import MemoryManagerTool, get_memory_fabric
from modernize.reports.report_generator import ReportGenerator
from modernize.swarm_coordinator import ModernizeSwarmCoordinator

app = FastAPI(title="ModernizeAI Knowledge Fabric", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files setup
STATIC_DIR = os.path.abspath("apps/modernizeai_ui/static")
TEMPLATES_DIR = os.path.abspath("apps/modernizeai_ui/templates")
ARTIFACTS_DIR = os.path.abspath("artifacts")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/artifacts", StaticFiles(directory=ARTIFACTS_DIR), name="artifacts")

# Global coordinator instance
coordinator = ModernizeSwarmCoordinator()


class ScanRequest(BaseModel):
    repo_path: Optional[str] = "data/insurance_claims_app"


class QueryRequest(BaseModel):
    query: str
    target_entity: Optional[str] = None


class BlastRadiusRequest(BaseModel):
    target_entity: str
    max_depth: Optional[int] = 2


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>ModernizeAI UI Index not found</h1>"


@app.get("/api/status")
async def get_status():
    mem_tool = MemoryManagerTool()
    kg_tool = KnowledgeGraphTool()
    mem_stat = mem_tool.invoke({"action": "status"}, {})
    kg_stat = kg_tool.invoke({"action": "status"}, {})

    return {
        "status": "ready" if kg_stat.get("total_nodes", 0) > 0 else "idle",
        "memory": mem_stat,
        "knowledge_graph": kg_stat,
    }


@app.post("/api/scan")
async def run_scan(req: ScanRequest):
    repo_path = req.repo_path or "data/insurance_claims_app"
    sly_data: Dict[str, Any] = {}

    mem_tool = MemoryManagerTool()
    kg_tool = KnowledgeGraphTool()

    # 1. Ingest repo into 5-tier memory
    mem_res = mem_tool.invoke({"action": "ingest_repo", "repo_path": repo_path}, sly_data)

    # 2. Build knowledge graph
    kg_res = kg_tool.invoke({"action": "build_graph", "repo_path": repo_path}, sly_data)

    # 3. Export graph artifacts (PyVis HTML, JSON, GraphML)
    kg_tool.invoke({"action": "export_artifacts", "html_path": "artifacts/modernize_graph.html"}, sly_data)

    # 4. Generate markdown reports
    fabric = get_memory_fabric(sly_data)
    kg = get_knowledge_graph(sly_data)
    reports = ReportGenerator.generate_all(kg, fabric, output_dir="artifacts")

    # 5. Run community detection
    comm_res = kg_tool.invoke({"action": "community_detection"}, sly_data)

    return {
        "status": "completed",
        "repo_path": repo_path,
        "memory_ingested": mem_res,
        "knowledge_graph": kg_res,
        "candidate_domains": comm_res.get("candidate_domains", []),
        "reports": reports,
    }


@app.post("/api/query")
async def run_hybrid_query(req: QueryRequest):
    # Execute through Swarm Coordinator with LLM reasoning and active node tracking
    result = coordinator.execute_swarm_turn(req.query)
    return result


@app.post("/api/blast_radius")
async def run_blast_radius(req: BlastRadiusRequest):
    kg_tool = KnowledgeGraphTool()
    sly_data: Dict[str, Any] = {}
    return kg_tool.invoke(
        {"action": "blast_radius", "target_entity": req.target_entity, "max_depth": req.max_depth or 2},
        sly_data,
    )


@app.get("/api/artifacts/{artifact_name}")
async def get_artifact_content(artifact_name: str):
    file_map = {
        "readiness_report": "artifacts/modernization_readiness_report.md",
        "blast_radius": "artifacts/impact_blast_radius_matrix.md",
        "business_rules": "artifacts/business_rules_catalog.md",
        "knowledge_graph_json": "artifacts/modernize_kg.json",
    }
    rel_path = file_map.get(artifact_name)
    if not rel_path or not os.path.exists(rel_path):
        return JSONResponse({"error": "Artifact not found"}, status_code=404)

    with open(rel_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {"artifact_name": artifact_name, "content": content}


def run_server(port: int = 8000):
    port = int(os.getenv("MODERNIZE_UI_PORT", str(port)))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ModernizeAI Web UI Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run ModernizeAI UI (default: 8000)")
    args = parser.parse_args()
    run_server(port=args.port)
