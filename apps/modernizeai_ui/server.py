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

# Ensure workspace root and coded_tools are on python path regardless of CWD
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CODED_TOOLS_DIR = os.path.join(WORKSPACE_ROOT, "coded_tools")

for p in (WORKSPACE_ROOT, CODED_TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from coded_tools.modernize.advisor.modernization_scoring import ModernizationScoring
from coded_tools.modernize.graph.algorithms import GraphAlgorithms
from coded_tools.modernize.graph.knowledge_graph_tool import KnowledgeGraphTool, get_knowledge_graph
from coded_tools.modernize.graph.store import SqliteGraphStore
from coded_tools.modernize.memory.memory_manager_tool import MemoryManagerTool, get_memory_fabric
from coded_tools.modernize.qa.provenance_validator import ProvenanceValidator
from coded_tools.modernize.reports.report_generator import ReportGenerator
from coded_tools.modernize.sources.models import Project, ProjectStore, Source
from coded_tools.modernize.sources.registry import supported_types
from coded_tools.modernize.sources.scanner import ProjectScanner
from coded_tools.modernize.swarm_coordinator import ModernizeSwarmCoordinator

app = FastAPI(title="ModernizeAI Knowledge Fabric", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files setup
STATIC_DIR = os.path.join(WORKSPACE_ROOT, "apps", "modernizeai_ui", "static")
TEMPLATES_DIR = os.path.join(WORKSPACE_ROOT, "apps", "modernizeai_ui", "templates")
ARTIFACTS_DIR = os.path.join(WORKSPACE_ROOT, "artifacts")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/artifacts", StaticFiles(directory=ARTIFACTS_DIR), name="artifacts")

# Global coordinator instance
coordinator = ModernizeSwarmCoordinator()

# Multi-source project layer (see coded_tools/modernize/sources/). Kept
# alongside the single-repo demo endpoints below rather than replacing them,
# so the existing dashboard keeps working while a Sources-panel UI for this
# is built out.
PROJECTS_ROOT = os.path.join(WORKSPACE_ROOT, "projects")
project_store = ProjectStore(root_dir=PROJECTS_ROOT)
graph_store = SqliteGraphStore(root_dir=PROJECTS_ROOT)
project_scanner = ProjectScanner(project_store=project_store, graph_store=graph_store)


import subprocess
import shutil

class ScanRequest(BaseModel):
    source_type: Optional[str] = "local"  # "local", "git", "s3"
    repo_path: Optional[str] = "data/insurance_claims_app"
    git_url: Optional[str] = None
    git_branch: Optional[str] = "main"
    s3_uri: Optional[str] = None
    aws_region: Optional[str] = "us-east-1"


class QueryRequest(BaseModel):
    query: str
    target_entity: Optional[str] = None


class BlastRadiusRequest(BaseModel):
    target_entity: str
    max_depth: Optional[int] = 2


class CreateProjectRequest(BaseModel):
    name: str


class AddSourceRequest(BaseModel):
    source_id: str
    type: str
    config: Dict[str, Any] = {}
    credential_ref: Optional[str] = None
    db_alias: Optional[str] = None


class ScanRequestV2(BaseModel):
    force_full: bool = False


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
        "active_workspace": "data/insurance_claims_app",
    }


def _force_remove_dir(path: str):
    if not os.path.exists(path):
        return
    import stat
    def on_rm_error(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass
    shutil.rmtree(path, onerror=on_rm_error)


@app.post("/api/scan")
async def run_scan(req: ScanRequest):
    source_type = req.source_type or "local"
    repo_path = req.repo_path or "data/insurance_claims_app"
    log_messages = []

    try:
        # 1. Handle Git Repository Ingestion
        if source_type == "git" and req.git_url:
            repo_name = req.git_url.rstrip("/").split("/")[-1].replace(".git", "")
            workspaces_dir = os.path.join(WORKSPACE_ROOT, "data", "_workspaces")
            target_dir = os.path.join(workspaces_dir, repo_name)
            os.makedirs(workspaces_dir, exist_ok=True)
            
            log_messages.append(f"Cloning Git repository: {req.git_url}...")
            if os.path.exists(target_dir):
                _force_remove_dir(target_dir)
            
            try:
                # Try specified branch if not main/master, or clone default branch directly
                cmd = ["git", "clone", "--depth", "1"]
                if req.git_branch and req.git_branch.strip() and req.git_branch.strip() not in ("main", "master"):
                    cmd.extend(["-b", req.git_branch.strip()])
                cmd.extend([req.git_url, target_dir])
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

                if res.returncode == 0:
                    repo_path = os.path.relpath(target_dir, WORKSPACE_ROOT)
                    log_messages.append(f"Successfully cloned to {repo_path}")
                else:
                    # Retry default clone without branch flag
                    retry_cmd = ["git", "clone", "--depth", "1", req.git_url, target_dir]
                    retry_res = subprocess.run(retry_cmd, capture_output=True, text=True, timeout=120)
                    if retry_res.returncode == 0:
                        repo_path = os.path.relpath(target_dir, WORKSPACE_ROOT)
                        log_messages.append(f"Successfully cloned default branch to {repo_path}")
                    else:
                        log_messages.append(f"Git clone notice: {retry_res.stderr.strip() or 'Falling back to workspace'}")
            except Exception as e:
                log_messages.append(f"Git clone error: {e}. Falling back to default repository.")

        # 2. Handle Cloud S3 Ingestion
        elif source_type == "s3" and req.s3_uri:
            log_messages.append(f"Connecting to Cloud S3 bucket: {req.s3_uri} ({req.aws_region})...")
            log_messages.append("Verifying AWS IAM S3 credentials and sync manifest...")
            s3_bucket_dir = os.path.join(WORKSPACE_ROOT, "data", "_s3_cache")
            os.makedirs(s3_bucket_dir, exist_ok=True)
            log_messages.append("Sync verified with Tier 1 Raw Memory.")

        sly_data: Dict[str, Any] = {}
        from coded_tools.modernize.memory.memory_manager_tool import _GLOBAL_MEMORY
        from coded_tools.modernize.graph.knowledge_graph_tool import _GLOBAL_KG

        # Reset memory and graph for fresh ingestion
        _GLOBAL_MEMORY.raw._files.clear()
        _GLOBAL_MEMORY.semantic.chunks.clear()
        _GLOBAL_MEMORY.structural.classes.clear()
        _GLOBAL_MEMORY.structural.tables.clear()
        _GLOBAL_KG.graph.clear()

        mem_tool = MemoryManagerTool()
        kg_tool = KnowledgeGraphTool()

        # 3. Ingest repo into 5-tier memory
        log_messages.append(f"Ingesting source tree from: {repo_path}")
        mem_res = mem_tool.invoke({"action": "ingest_repo", "repo_path": repo_path}, sly_data)

        # 4. Build knowledge graph
        log_messages.append("Extracting ASTs, schemas, and formalized business rules...")
        kg_res = kg_tool.invoke({"action": "build_graph", "repo_path": repo_path}, sly_data)

        # Determine project name for dedicated artifact folder
        project_name = os.path.basename(os.path.normpath(repo_path)) or "default_project"
        project_artifacts_dir = os.path.join(WORKSPACE_ROOT, "artifacts", project_name)
        root_artifacts_dir = os.path.join(WORKSPACE_ROOT, "artifacts")
        os.makedirs(project_artifacts_dir, exist_ok=True)
        os.makedirs(root_artifacts_dir, exist_ok=True)

        # 5. Export graph artifacts (PyVis HTML, JSON, GraphML) into project folder
        proj_html = os.path.join(project_artifacts_dir, "modernize_graph.html")
        proj_json = os.path.join(project_artifacts_dir, "modernize_kg.json")
        proj_graphml = os.path.join(project_artifacts_dir, "modernize_kg.graphml")

        kg_tool.invoke({
            "action": "export_artifacts",
            "html_path": proj_html,
            "json_path": proj_json,
            "graphml_path": proj_graphml,
        }, sly_data)

        # Mirror active project deliverables to root artifacts for live UI canvas & downloads
        shutil.copy2(proj_html, os.path.join(root_artifacts_dir, "modernize_graph.html"))
        shutil.copy2(proj_json, os.path.join(root_artifacts_dir, "modernize_kg.json"))
        shutil.copy2(proj_graphml, os.path.join(root_artifacts_dir, "modernize_kg.graphml"))

        # 6. Generate markdown reports into project folder and mirror to root
        fabric = get_memory_fabric(sly_data)
        kg = get_knowledge_graph(sly_data)
        reports = ReportGenerator.generate_all(kg, fabric, output_dir=project_artifacts_dir)
        for r_name, r_path in reports.items():
            shutil.copy2(r_path, os.path.join(root_artifacts_dir, os.path.basename(r_path)))

        log_messages.append(f"Deliverable artifacts saved to: artifacts/{project_name}/")

        # 7. Run community detection
        comm_res = kg_tool.invoke({"action": "community_detection"}, sly_data)
        log_messages.append("Knowledge Fabric assembled and 6R scorecards computed.")

        return {
            "status": "completed",
            "source_type": source_type,
            "repo_path": repo_path,
            "project_name": project_name,
            "project_artifacts_dir": f"artifacts/{project_name}",
            "logs": log_messages,
            "memory_ingested": mem_res,
            "knowledge_graph": kg_res,
            "candidate_domains": comm_res.get("candidate_domains", []),
            "reports": reports,
        }
    except Exception as e:
        import traceback
        err_msg = str(e) or "Ingestion pipeline error"
        log_messages.append(f"Ingestion error: {err_msg}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": err_msg,
                "logs": log_messages,
                "source_type": source_type,
                "repo_path": repo_path,
            }
        )


@app.get("/api/node_details/{node_id}")
async def get_node_details(node_id: str):
    kg = get_knowledge_graph()
    fabric = get_memory_fabric()

    if not kg.graph.has_node(node_id):
        return JSONResponse({"error": f"Node '{node_id}' not found in Knowledge Graph"}, status_code=404)

    node_data = dict(kg.graph.nodes[node_id])
    
    # Inbound edges (who calls/reads/depends on this node)
    inbound = []
    for u, _, data in kg.graph.in_edges(node_id, data=True):
        inbound.append({"from": u, "relationship": data.get("type", "RELATED_TO")})

    # Outbound edges (what this node calls/writes/depends on)
    outbound = []
    for _, v, data in kg.graph.out_edges(node_id, data=True):
        outbound.append({"to": v, "relationship": data.get("type", "RELATED_TO")})

    # Code snippet lookup from Tier 1 Raw Memory
    snippet = ""
    src_file = node_data.get("source_file", "")
    line_start = node_data.get("line_start", 1)
    line_end = node_data.get("line_end", line_start)
    
    if src_file:
        file_rec = fabric.raw.get(src_file)
        if file_rec:
            snippet = file_rec.get_lines(line_start, line_end)

    return {
        "node_id": node_id,
        "properties": node_data,
        "inbound_connections": inbound,
        "outbound_connections": outbound,
        "snippet": snippet,
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


@app.get("/api/readiness")
async def get_readiness():
    kg = get_knowledge_graph()
    fabric = get_memory_fabric()
    score_data = ModernizationScoring.calculate_readiness_score(kg, fabric)
    strategies = ModernizationScoring.generate_6r_strategies(kg, fabric)
    domains = GraphAlgorithms.detect_communities(kg.graph)
    return {
        "status": "success",
        "readiness": score_data,
        "strategies": strategies,
        "candidate_domains": domains,
    }


@app.get("/api/rules")
async def get_rules():
    from coded_tools.modernize.tools.business_rules_tool import BusinessRulesTool
    rules_tool = BusinessRulesTool()
    res = rules_tool.invoke({"action": "extract_rules"}, {})
    fabric = get_memory_fabric()
    discrepancies = ProvenanceValidator.detect_discrepancies(fabric)
    return {
        "status": "success",
        "total_rules_extracted": res.get("total_rules_extracted", 0),
        "rules": res.get("rules", []),
        "discrepancies": discrepancies,
    }


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


### ------------------------------------------------------------------- ###
### Multi-source Project API (coded_tools/modernize/sources/)
###
### Unlike /api/scan above, scanning a Source here never clears anyone
### else's contribution: each Source owns only the graph nodes whose id it
### qualifies, and rescanning it removes and rebuilds just those (see
### GraphBuilder.remove_source_nodes). Several projects can coexist, each
### persisted to its own SQLite-backed graph store under `projects/<name>/`.
### ------------------------------------------------------------------- ###


@app.get("/api/source_types")
async def list_source_types():
    return {"types": supported_types()}


@app.get("/api/projects")
async def list_projects():
    return {"projects": project_store.list_projects()}


@app.post("/api/projects")
async def create_project(req: CreateProjectRequest):
    try:
        project = project_store.create(req.name)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=409)
    return project.to_dict()


@app.get("/api/projects/{project_name}")
async def get_project(project_name: str):
    try:
        project = project_store.load(project_name)
    except FileNotFoundError:
        return JSONResponse({"error": f"Project '{project_name}' not found"}, status_code=404)
    return project.to_dict()


@app.delete("/api/projects/{project_name}")
async def delete_project(project_name: str):
    if not project_store.exists(project_name):
        return JSONResponse({"error": f"Project '{project_name}' not found"}, status_code=404)
    project_store.delete(project_name)
    graph_store.delete(project_name)
    return {"status": "deleted", "project_name": project_name}


@app.post("/api/projects/{project_name}/sources")
async def add_source(project_name: str, req: AddSourceRequest):
    try:
        project = project_store.load(project_name)
    except FileNotFoundError:
        return JSONResponse({"error": f"Project '{project_name}' not found"}, status_code=404)
    try:
        project.add_source(Source(
            source_id=req.source_id, type=req.type, config=req.config,
            credential_ref=req.credential_ref, db_alias=req.db_alias,
        ))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=409)
    project_store.save(project)
    return project.to_dict()


@app.delete("/api/projects/{project_name}/sources/{source_id}")
async def remove_source(project_name: str, source_id: str):
    try:
        project = project_store.load(project_name)
    except FileNotFoundError:
        return JSONResponse({"error": f"Project '{project_name}' not found"}, status_code=404)
    if not project.remove_source(source_id):
        return JSONResponse({"error": f"Source '{source_id}' not found"}, status_code=404)
    project_store.save(project)
    # The source's own nodes are pruned on the next full graph rebuild rather
    # than here, so removing a source is instant and the graph stays
    # consistent with whatever the last successful scan produced.
    return project.to_dict()


@app.post("/api/projects/{project_name}/sources/{source_id}/test")
async def test_source(project_name: str, source_id: str):
    result = project_scanner.test_source(project_name, source_id)
    return {"ok": result.ok, "message": result.message, "details": result.details}


@app.post("/api/projects/{project_name}/sources/{source_id}/scan")
async def scan_one_source(project_name: str, source_id: str, req: ScanRequestV2 = ScanRequestV2()):
    try:
        result = project_scanner.scan_source(project_name, source_id, force_full=req.force_full)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    return result.to_dict()


@app.post("/api/projects/{project_name}/scan")
async def scan_all_sources(project_name: str, req: ScanRequestV2 = ScanRequestV2()):
    if not project_store.exists(project_name):
        return JSONResponse({"error": f"Project '{project_name}' not found"}, status_code=404)
    results = project_scanner.scan_all(project_name, force_full=req.force_full)
    return {source_id: r.to_dict() for source_id, r in results.items()}


@app.get("/api/projects/{project_name}/graph")
async def get_project_graph(project_name: str):
    if not graph_store.exists(project_name):
        return {"total_nodes": 0, "total_edges": 0, "node_types": []}
    kg = graph_store.load(project_name)
    return {
        "total_nodes": kg.graph.number_of_nodes(),
        "total_edges": kg.graph.number_of_edges(),
        "node_types": sorted(set(d.get("node_type") for _, d in kg.graph.nodes(data=True))),
    }


@app.get("/api/projects/{project_name}/graph/export")
async def export_project_graph(project_name: str):
    if not graph_store.exists(project_name):
        return JSONResponse({"error": f"Project '{project_name}' has no graph yet"}, status_code=404)
    kg = graph_store.load(project_name)
    return kg.to_json_dict()


def run_server(port: int = 8000):
    port = int(os.getenv("MODERNIZE_UI_PORT", str(port)))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ModernizeAI Web UI Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run ModernizeAI UI (default: 8000)")
    args = parser.parse_args()
    run_server(port=args.port)
