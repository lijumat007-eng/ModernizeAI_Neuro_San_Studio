# ModernizeAI: Enterprise Legacy Modernization Platform
### *Powered by Neuro SAN Studio (Cognizant Neuro® AI Multi-Agent Accelerator)*

[![Built with Neuro SAN Studio](https://img.shields.io/badge/Built%20with-Neuro%20SAN%20Studio-blue.svg)](https://github.com/cognizant-ai-lab/neuro-san-studio)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-brightgreen.svg)](https://www.python.org/)
[![Swarm Architecture](https://img.shields.io/badge/Swarm-11%20Agents%20%7C%205%20Coded%20Tools-orange.svg)](docs/generated/MODERNIZE_AI_GUIDE.md)
[![Memory Architecture](https://img.shields.io/badge/Memory-5--Tier%20Fabric-purple.svg)](docs/generated/MODERNIZE_AI_GUIDE.md)
[![Roadmap](https://img.shields.io/badge/Roadmap-Phase%202%3A%20Code%20Migration%20Agents-blueviolet.svg)](#-future-roadmap-phase-2-active-code-migration--cloud-transformation)
[![Codebase Map](https://img.shields.io/badge/Codebase-App%20vs%20Framework-teal.svg)](#️-modernizeai-codebase-map--file-manifest-application-vs-host-framework)
[![License](https://img.shields.io/badge/license-Apache%202.0-lightgrey.svg)](LICENSE.txt)

---

## 🌟 What is ModernizeAI?

**ModernizeAI** is an enterprise-grade **Agentic Knowledge Factory** and **Hybrid Agentic Graph-RAG platform** built on the **Neuro SAN Studio** multi-agent orchestration framework. It is specifically engineered to solve the complexity, risk, and high failure rates associated with enterprise legacy application reverse-engineering and cloud migration.

ModernizeAI is architected around a strategic two-phase lifecycle:
* **Phase 1: Deterministic Reverse Engineering & Knowledge Graph Creation (Current Focus)**: Extracts verified ground truth via AST parsers, SQL schema analyzers, and documentation NLP, synthesizing intelligence into an enriched 5-Tier Memory Fabric and schema-enforced MultiDiGraph.
* **Phase 2: Knowledge-Graph-Driven Code Migration Swarm (Future Scope)**: Deploys autonomous migration agents that ingest the Knowledge Graph to execute automated code transformation, transpilation (e.g., legacy .NET to cloud-native microservices), and provenance-grounded regression test generation.

Traditional legacy modernization projects experience a **70%+ failure or delay rate** because organizations attempt code migration before deeply understanding legacy business logic, transitive database locks, and hidden side effects. ModernizeAI solves this by strictly enforcing the **80/20 Principle**:

* **80% Deterministic Extraction**: Abstract Syntax Tree (AST) code parsers, regex symbol extractors, SQL/DDL interpreters, and database schema analyzers extract concrete facts, method signatures, foreign keys, and line-level provenance **without LLM hallucination**.
* **20% LLM Agent Reasoning**: Large Language Models orchestrated via Neuro SAN are applied strictly where semantic disambiguation is required—interpreting legacy documentation and SME notes, discovering implicit business rules, calculating blast radiuses, formulating 6R cloud migration strategies, and answering natural language architecture queries.

---

## 🧩 How ModernizeAI is Built from Neuro SAN Studio

ModernizeAI serves as a production-grade showcase of what can be built using **Neuro SAN Studio**:

1. **Declarative Multi-Agent Configuration**: ModernizeAI's entire 11-agent network is defined declaratively using HOCON in [`registries/generated/modernizeai.hocon`](registries/generated/modernizeai.hocon).
2. **Autonomous Agent Coordination ([AAOSA Protocol](https://arxiv.org/abs/cs/9812015))**: Agents dynamically collaborate, hand off subtasks, and route intelligence through an autonomous conversational network led by the `Frontman` agent.
3. **Custom Coded Tools Ecosystem**: Equipped with 5 high-speed deterministic tools located in [`coded_tools/modernize/`](coded_tools/modernize/) that execute AST parsing, DDL parsing, document NLP, NetworkX graph modeling, and 5-tier memory persistence.
4. **Sly-Data Protection**: Utilizes Neuro SAN's Sly-Data capabilities to safely handle sensitive database credentials, enterprise schemas, and source code without exposing raw proprietary data directly to LLM context windows.

---

## 🏛️ ModernizeAI Swarm Architecture

ModernizeAI coordinates an **11-Agent Mixture-of-Experts Swarm** supported by **5 Coded Tools** and a **5-Tier Memory Fabric**:

```mermaid
flowchart TD
    User([Enterprise Architect / Developer]) <--> Frontman[Frontman: Swarm Router]
    
    subgraph Ingestion & Intelligence Pipeline
        Frontman --> Discovery[Discovery Agent]
        Discovery --> CodeIntel[Code Intel Agent]
        Discovery --> DBIntel[Database Intel Agent]
        Discovery --> DocIntel[Doc Intel Agent]
        
        CodeIntel --> CodeTool[(CodeIntelTool: AST Parser)]
        DBIntel --> DBTool[(DatabaseIntelTool: DDL Parser)]
        DocIntel --> DocTool[(DocIntelTool: NLP Parser)]
        
        CodeIntel --> BusinessRules[Business Rules Agent]
        DBIntel --> BusinessRules
        DocIntel --> BusinessRules
    end

    subgraph Validation & Knowledge Assembly
        BusinessRules --> Validation[Validation QA Agent]
        Validation --> KG[Knowledge Graph Agent]
        KG --> KGTool[(KnowledgeGraphTool: NetworkX MultiDiGraph)]
        KG --> MemoryMgr[Memory Manager Agent]
        MemoryMgr --> MemTool[(MemoryManagerTool: 5-Tier Store)]
    end

    subgraph Strategy & Analysis Pipeline
        Frontman --> Impact[Impact Analysis Agent]
        Frontman --> Advisor[Modernization Advisor Agent]
        Frontman --> KG
        
        Impact --> KG
        Impact --> KGTool
        Advisor --> KG
        Advisor --> MemoryMgr
    end
```

### Swarm Agent Specification

| Agent Name | Role & Responsibility | Neuro SAN Tools & Downstream Agents |
| :--- | :--- | :--- |
| **`frontman`** | Main entry point; parses user intents and coordinates swarm workflows. | `discovery_agent`, `impact_analysis_agent`, `knowledge_graph_agent`, `modernization_advisor_agent` |
| **`discovery_agent`** | Catalogs file trees across code, SQL, and documentation directories. | `code_intel_agent`, `database_intel_agent`, `doc_intel_agent` |
| **`code_intel_agent`** | Deterministic AST parsing of Java and application source code. | `code_intel_tool`, `business_rules_agent` |
| **`database_intel_agent`** | Schema parsing of SQL DDLs, tables, constraints, and stored procedures. | `database_intel_tool`, `business_rules_agent` |
| **`doc_intel_agent`** | Semantic and structural extraction of architectural specs and SME notes. | `doc_intel_tool`, `business_rules_agent` |
| **`business_rules_agent`**| Formalizes and cataloges cross-system enterprise business logic. | `validation_agent` |
| **`validation_agent`** | Quality assurance agent verifying source provenance and eliminating hallucinations. | `knowledge_graph_agent` |
| **`knowledge_graph_agent`**| Traverses and enriches the schema-enforced MultiDiGraph knowledge fabric. | `knowledge_graph_tool`, `memory_manager_agent` |
| **`memory_manager_agent`**| Manages 5-tier memory persistence, vector search, and BM25 index retrieval. | `memory_manager_tool` |
| **`impact_analysis_agent`**| Computes dependency blast radiuses and risk-classified ripple effects. | `knowledge_graph_agent`, `knowledge_graph_tool` |
| **`modernization_advisor_agent`** | Analyzes system coupling ($C_a, C_e, I$) and recommends 6R cloud migration strategies. | `knowledge_graph_agent`, `memory_manager_agent` |

---

## 🧠 5-Tier Memory Fabric

ModernizeAI replaces standard single-prompt RAG with a structured five-tier memory fabric:

| Tier | Tier Name | Purpose & Persistence | Key Capabilities |
| :---: | :--- | :--- | :--- |
| **1** | **Raw Memory** | Ingested source files with SHA-256 hashes and line-offset indices. | 100% verifiable citations down to exact source line numbers. |
| **2** | **Structural Memory** | Deterministic symbol tables, AST nodes, DDL schemas, and call graphs. | Sub-millisecond exact queries for classes, methods, and foreign keys. |
| **3** | **Semantic Memory** | Vector embeddings and BM25 search over specifications and SME notes. | Semantic concept matching, synonym expansion, and intent lookup. |
| **4** | **Procedural Memory** | Reusable extraction recipes, regex patterns, and traversal algorithms. | Dynamic pattern reuse across different legacy frameworks and dialects. |
| **5** | **Transformation Memory**| 6R migration classifications, coupling metrics, and community detection. | Microservice candidate clustering, blast radius, and migration roadmaps. |

---

## 🚀 Future Roadmap: Phase 2 Active Code Migration & Cloud Transformation

While the **current architecture (Phase 1)** is centered on **reverse engineering, deterministic AST/schema extraction, and Knowledge Graph creation**, the **next phase (Phase 2)** introduces autonomous **Code Migration & Transformation Swarm Agents**.

Instead of stopping at architectural discovery and readiness reports, Phase 2 agents directly **ingest and traverse the verified Knowledge Graph and 5-Tier Memory Fabric** to perform end-to-end, automated code refactoring and cloud migration.

```mermaid
flowchart TD
    subgraph Phase 1: Reverse Engineering & Knowledge Graph [Current Architecture]
        LegacyCode[Legacy Source: .NET / Java / SQL] --> ParsingSwarm[Extraction & Intelligence Swarm]
        ParsingSwarm --> KG[(Knowledge Graph MultiDiGraph)]
        ParsingSwarm --> Memory5T[(5-Tier Memory Fabric)]
        ParsingSwarm --> RulesCatalog[Business Rules Catalog & Provenance]
    end

    subgraph Phase 2: Active Code Migration Swarm [Next Phase / Future Scope]
        KG --> KGReader[KG Reader & Extractor Agent]
        Memory5T --> KGReader
        RulesCatalog --> KGReader

        KGReader --> ArchScaffolder[Cloud Architecture Scaffolder Agent]
        KGReader --> CodeMigrator[Code Migrator Agent: .NET to Cloud]
        KGReader --> TestSynthesizer[Provenance Test Synthesizer Agent]

        ArchScaffolder --> TargetApp[Cloud-Native Microservices]
        CodeMigrator --> TargetApp
        TestSynthesizer --> TargetApp

        TargetApp --> StranglerGateway[Strangler-Fig Routing & Deployment]
    end
```

### Phase 2 Agent Network Specification

| Agent Name | Role & Responsibility | Upstream / Downstream Linkage |
| :--- | :--- | :--- |
| **`kg_reader_agent`** | Ingests, queries, and extracts subgraphs from the Knowledge Graph MultiDiGraph and 5-Tier Memory (AST symbol tables, call graphs, DDL schemas, formalized business rules). | Queries `knowledge_graph_tool` & `memory_manager_tool`; feeds `cloud_scaffolder_agent` & `code_migrator_agent`. |
| **`cloud_scaffolder_agent`** | Generates target cloud-native project scaffolding, dependency manifests, container configurations (Dockerfiles), and infrastructure blueprints (Kubernetes Helm charts, Terraform, serverless SAM templates). | Ingests candidate microservices from Louvain community detection (Domain 1–5). |
| **`code_migrator_agent`** | Executes deep syntax and semantic code transpilation and modernization. For example, converting legacy on-premise **.NET Framework (C# / WCF / ADO.NET)** applications to modern **cloud-native .NET 8/9, ASP.NET Core Minimal APIs, or Cloud Run / AWS Lambda services**. | Ingests AST symbol graphs and business rule specifications; produces modern modular code. |
| **`sql_to_cloud_agent`** | Decouples procedural stored procedures (e.g. PL/SQL / T-SQL row locks) and translates relational schemas into cloud-native data access layers (EF Core, Dapper, PostgreSQL, or DynamoDB/CosmosDB with Outbox/Saga patterns). | Modernizes database access based on DDL schemas and stored procedure ASTs. |
| **`test_synthesizer_agent`** | Automatically generates comprehensive unit, contract, and behavioral integration tests directly from formalized business rules (`BR-01` through `BR-05`) to mathematically guarantee zero behavioral regression. | Uses business rule source provenance to validate modernized code against legacy behavior. |
| **`strangler_deployer_agent`** | Orchestrates Strangler-Fig traffic migration, configuring API gateways (Azure APIM, AWS API Gateway, Envoy) to route traffic incrementally between legacy and modernized services. | Implements canary rollouts guided by the blast-radius dependency matrix. |

### Concrete Exemplar: Legacy .NET to Cloud Modernization

To illustrate how Phase 2 transforms enterprise legacy code:

1. **Legacy Input**: A monolithic on-premise .NET Framework 4.8 application utilizing legacy WCF endpoints, ADO.NET queries with hardcoded SQL, and synchronous stored procedures with table locks.
2. **Phase 1 Extraction (Completed)**: ModernizeAI extracts the C# AST, maps entity relationships to the Knowledge Graph, catalogs business rules with line-level provenance, and computes afferent/efferent coupling ($C_a, C_e$).
3. **Phase 2 Automated Migration**:
   * **Graph Extraction**: `kg_reader_agent` traverses the subgraphs corresponding to the isolated domain (e.g., Claim Settlement domain).
   * **Solution Scaffolding**: `cloud_scaffolder_agent` scaffolds a modern ASP.NET Core solution structured as containerized microservices with OpenTelemetry, health checks, and Dockerfile definitions.
   * **Code Transpilation**: `code_migrator_agent` translates legacy WCF controllers into RESTful OpenAPI/gRPC endpoints, replaces ADO.NET boilerplate with clean Entity Framework Core repositories, and re-implements validated business rules into modern domain logic.
   * **Automated Verification**: `test_synthesizer_agent` generates xUnit/NUnit test suites grounded in legacy provenance to prove functional parity before deployment.

---

## 🖥️ Two Interactive User Interfaces

ModernizeAI provides two integrated user interfaces depending on your workflow:

### 1. ModernizeAI Dedicated Web Application
* **Location**: [`apps/modernizeai_ui/server.py`](apps/modernizeai_ui/server.py)
* **URL**: `http://localhost:8000`
* **Features**:
  * **One-Click Ingestion Pipeline**: Scan source repositories with real-time progress.
  * **5-Tier Memory & Graph Metrics**: Live counters for nodes, edges, business rules, and microservices.
  * **Interactive PyVis Knowledge Graph**: Embedded, zoomable 2D/3D visualizer with physics simulation.
  * **Transitive Blast Radius Explorer**: Live dependency impact analysis for any class or table.
  * **Artifacts Review Center**: Integrated viewer for Modernization Readiness Reports, Business Rules Catalogs, and Impact Matrices.
  * **Grounded AI Copilot**: Chat interface backed by verified code provenance.

```bash
# Launch ModernizeAI Web Application:
python apps/modernizeai_ui/server.py --port 8000
```

### 2. Neuro SAN Studio Client (`nsflow`)
* **Location**: Built-in Neuro SAN Studio Client
* **URL**: `http://localhost:4173/?network=generated%2Fmodernizeai`
* **Features**:
  * **Live Network Topology Visualizer**: Interactive React Flow diagram showing the 11 agents and 5 tool nodes.
  * **Multi-Agent Swarm Chat**: Chat directly with `Frontman` and inspect real-time inter-agent delegation.
  * **Execution Telemetry & Traces**: View full message passing, prompt token costs, and internal logs.

```bash
# Launch Neuro SAN Server + nsflow Studio UI:
ns run
```

---

## ⚡ Quickstart

### Prerequisites
* Python 3.11+
* [`uv`](https://docs.astral.sh/uv/) (recommended) or standard `pip` / `venv`
* LLM API Key (OpenAI, Anthropic, Google Gemini, or local models via Ollama)

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/lijumat007-eng/ModernizeAI_Neuro_San_Studio.git
cd ModernizeAI_Neuro_San_Studio

# Using uv:
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

### 2. Configure Your API Key
Copy `.env.example` to `.env` and set your key:
```bash
cp .env.example .env
```
```env
OPENAI_API_KEY="your-api-key"
# or ANTHROPIC_API_KEY / GOOGLE_API_KEY
```

### 3. Run ModernizeAI

#### Option A: Dedicated Web Dashboard (Recommended)
```bash
python apps/modernizeai_ui/server.py --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

#### Option B: Neuro SAN Studio Swarm UI
```bash
ns run
```
Open [http://localhost:4173/?network=generated%2Fmodernizeai](http://localhost:4173/?network=generated%2Fmodernizeai).

#### Option C: Interactive CLI Runner
```bash
python scripts/run_modernize_cli.py
```

---

## 🗺️ ModernizeAI Codebase Map & File Manifest (Application vs. Host Framework)

Because **ModernizeAI** was built on top of the open-source **Neuro SAN Studio** multi-agent accelerator repository, this codebase contains two distinct layers:
1. **The ModernizeAI Agentic Application**: The enterprise legacy reverse-engineering platform (11-agent swarm HOCON, custom coded tools, 5-tier memory fabric, interactive web UI dashboard, benchmark dataset, generated artifacts, CLI scripts, and tests).
2. **The Neuro SAN Studio Host Framework**: The underlying multi-agent engine runtime (`ns`), agent middleware, protocol servers (A2A, MCP), and built-in framework templates developed by Cognizant AI Lab.

The sections below provide a structured, high-level manifest of which files, directories, HOCON configs, artifacts, and Python scripts belong to **ModernizeAI** versus the host framework.

---

### 📊 Quick Comparison: Application vs. Host Framework

| Layer / Dimension | ModernizeAI Application Components (Custom Built) | Neuro SAN Studio Framework (Underlying Host) |
| :--- | :--- | :--- |
| **Primary Directories** | [`apps/modernizeai_ui/`](apps/modernizeai_ui/), [`coded_tools/modernize/`](coded_tools/modernize/), [`registries/generated/`](registries/generated/), [`data/insurance_claims_app/`](data/insurance_claims_app/), [`artifacts/`](artifacts/), [`docs/generated/`](docs/generated/), [`scripts/`](scripts/), [`tests/coded_tools/modernize/`](tests/coded_tools/modernize/) | `neuro_san_studio/`, `middleware/`, `servers/`, `build_scripts/`, `deploy/`, other `apps/`, other `coded_tools/`, other `registries/` |
| **Agent Swarm Configs (`.hocon`)** | [`registries/generated/modernizeai.hocon`](registries/generated/modernizeai.hocon), [`manifest.hocon`](registries/generated/manifest.hocon) (11-Agent Swarm) | `registries/basic/`, `registries/industry/`, `registries/tools/`, `registries/agent_network_*.hocon` (Demo templates) |
| **Coded Tools (`.py`)** | Deterministic AST/DDL/Doc parsers, NetworkX MultiDiGraph engine, 5-Tier Memory Fabric, Report generator (`coded_tools/modernize/`) | ArXiv, Wikipedia, Google Serper, Jira, Slack, ServiceNow, MCP bridges (`coded_tools/basic/`, `industry/`, etc.) |
| **User Interfaces** | Dedicated ModernizeAI Web Application & Dashboard ([`apps/modernizeai_ui/server.py`](apps/modernizeai_ui/server.py)) | Neuro SAN Studio Client (`nsflow`) web interface & terminal runner (`ns chat`) |
| **Runner Scripts** | Standalone Terminal CLI Pipeline Runner ([`scripts/run_modernize_cli.py`](scripts/run_modernize_cli.py)) | Neuro SAN Studio CLI binary (`ns run`, `ns init`, `ns import`, `ns export`) |
| **Artifacts & Data** | MultiDiGraph exports (`.html`, `.json`, `.graphml`), Business Rules, Readiness Reports (`artifacts/`), Claims benchmark (`data/insurance_claims_app/`) | Temporary runtime execution logs (`logs/`), SQLite agent checkpoints (`nss_local.db`) |
| **Automated Tests** | Knowledge fabric unit test suite ([`tests/coded_tools/modernize/test_modernize_fabric.py`](tests/coded_tools/modernize/test_modernize_fabric.py)) | Core framework engine tests (`tests/neuro_san_studio/`, `tests/middleware/`, etc.) |

---

### 1. 📁 ModernizeAI Directories Overview

| Directory Path | Role & Architecture Responsibility in ModernizeAI |
| :--- | :--- |
| [`apps/modernizeai_ui/`](apps/modernizeai_ui/) | **Dedicated Web Application**: FastAPI backend server (`server.py`), HTML5 template (`templates/index.html`), dark glassmorphic stylesheet (`static/style.css`), and dynamic JS client (`static/app.js`). |
| [`coded_tools/modernize/`](coded_tools/modernize/) | **Coded Tools Ecosystem**: Core deterministic parsers, NetworkX knowledge graph engine, 5-tier memory fabric, markdown report generator, and swarm coordinator. |
| [`registries/generated/`](registries/generated/) | **Declarative Multi-Agent Registry**: HOCON definitions for the 11-agent network (`modernizeai.hocon`) and network discovery manifest (`manifest.hocon`). |
| [`artifacts/`](artifacts/) | **Synthesized Knowledge Artifacts**: Generated knowledge graph exports (interactive HTML, JSON, GraphML) and generated Markdown intelligence reports. |
| [`data/insurance_claims_app/`](data/insurance_claims_app/) | **Benchmark Enterprise Dataset**: `ClaimCore v2.4` legacy monolith (Java source, Oracle SQL DDL, architecture spec, adjuster notes). |
| [`docs/generated/`](docs/generated/) | **ModernizeAI Guides & Specifications**: Architectural deep dive (`MODERNIZE_AI_GUIDE.md`) and benchmark validation inventory (`MODERNIZE_DEMO_DATA_POINTS.md`). |
| [`scripts/`](scripts/) | **CLI Automation**: Standalone CLI runner script (`run_modernize_cli.py`) for terminal workflows and headless CI/CD execution. |
| [`tests/coded_tools/modernize/`](tests/coded_tools/modernize/) | **Unit Test Suite**: ModernizeAI test harness (`test_modernize_fabric.py`) validating parsers, memory tiers, graph algorithms, and reports. |

---

### 2. 📜 Declarative HOCON Agent Network Configurations (`.hocon`)

ModernizeAI uses Neuro SAN's declarative HOCON language to orchestrate its 11-agent collaborative network:

* [`registries/generated/modernizeai.hocon`](registries/generated/modernizeai.hocon):
  * **The Primary ModernizeAI Multi-Agent Swarm**: Declaratively defines all 11 agents (`frontman`, `discovery_agent`, `code_intel_agent`, `database_intel_agent`, `doc_intel_agent`, `business_rules_agent`, `validation_agent`, `knowledge_graph_agent`, `memory_manager_agent`, `impact_analysis_agent`, `modernization_advisor_agent`).
  * Specifies agent system instructions, LLM model parameters, downstream agent routing permissions (AAOSA protocol), and tool attachments (`code_intel_tool`, `database_intel_tool`, `doc_intel_tool`, `knowledge_graph_tool`, `memory_manager_tool`).
* [`registries/generated/manifest.hocon`](registries/generated/manifest.hocon):
  * **Network Registry Manifest**: Indexes the `modernizeai` network within the Neuro SAN network directory so that `ns run`, `ns chat`, and the studio visualizer can discover and load it.

> [!NOTE]
> All other `.hocon` files located under `registries/basic/`, `registries/industry/`, `registries/tools/`, or root `registries/agent_network_*.hocon` belong to the upstream Neuro SAN Studio library of sample templates and demo networks.

---

### 3. 🐍 Python Scripts, Tools & Source Files (`.py`)

ModernizeAI's Python codebase is organized into high-speed deterministic tools, orchestration logic, and web APIs:

#### A. Web Server & Standalone Runners
* [`apps/modernizeai_ui/server.py`](apps/modernizeai_ui/server.py): FastAPI/Starlette web server serving the ModernizeAI REST API (`/api/run-pipeline`, `/api/metrics`, `/api/chat`, `/api/artifacts`) and serving the dedicated dashboard interface.
* [`scripts/run_modernize_cli.py`](scripts/run_modernize_cli.py): Standalone CLI runner script executing the ingestion, parsing, graph assembly, and report generation pipeline directly from the terminal.

#### B. Swarm Coordinator
* [`coded_tools/modernize/swarm_coordinator.py`](coded_tools/modernize/swarm_coordinator.py): High-level Python orchestrator that coordinates extraction across all 11 agents and synchronizes intelligence into the 5-tier memory fabric and Knowledge Graph.

#### C. Deterministic Parsers ([`coded_tools/modernize/parsers/`](coded_tools/modernize/parsers/))
* [`java_parser.py`](coded_tools/modernize/parsers/java_parser.py): Deterministic AST parser extracting Java classes, methods, annotations, imports, method invocations, and inheritance hierarchies without LLM hallucination.
* [`ddl_parser.py`](coded_tools/modernize/parsers/ddl_parser.py): SQL schema parser extracting database tables, columns, data types, primary keys, foreign keys, and constraints.
* [`doc_parser.py`](coded_tools/modernize/parsers/doc_parser.py): Structural and NLP parser extracting headers, paragraphs, and business concepts from markdown architecture specs and SME interview text.
* [`parser_tools.py`](coded_tools/modernize/parsers/parser_tools.py): Tool wrappers (`CodeIntelTool`, `DatabaseIntelTool`, `DocIntelTool`) registering deterministic parsers as callable Neuro SAN tools.

#### D. Knowledge Graph Engine & Algorithms ([`coded_tools/modernize/graph/`](coded_tools/modernize/graph/))
* [`graph_engine.py`](coded_tools/modernize/graph/graph_engine.py): NetworkX-based `MultiDiGraph` maintaining heterogeneous nodes (classes, tables, rules, specs) and semantic directed edges (calls, queries, validates).
* [`algorithms.py`](coded_tools/modernize/graph/algorithms.py): Graph algorithms including Louvain community clustering (for microservice domain isolation), blast-radius transitive traversals, and Martin package coupling metrics ($C_a, C_e, I$).
* [`knowledge_graph_tool.py`](coded_tools/modernize/graph/knowledge_graph_tool.py): `KnowledgeGraphTool` wrapper providing graph querying, blast radius calculation, and coupling statistics to agents.
* [`visualizer.py`](coded_tools/modernize/graph/visualizer.py): PyVis exporter generating standalone interactive HTML 2D/3D visualizations and exporting GraphML / JSON graph models.

#### E. 5-Tier Memory Fabric ([`coded_tools/modernize/memory/`](coded_tools/modernize/memory/))
* [`raw_memory.py`](coded_tools/modernize/memory/raw_memory.py): **Tier 1 (Raw Memory)** — Ingests source files, tracks SHA-256 hashes, and provides exact line-level citation offsets.
* [`structural_memory.py`](coded_tools/modernize/memory/structural_memory.py): **Tier 2 (Structural Memory)** — Caches deterministic symbol tables, AST nodes, and DDL schema metadata for sub-millisecond retrieval.
* [`semantic_memory.py`](coded_tools/modernize/memory/semantic_memory.py): **Tier 3 (Semantic Memory)** — In-memory vector embeddings and BM25 search over architectural text and SME interview notes.
* [`procedural_memory.py`](coded_tools/modernize/memory/procedural_memory.py): **Tier 4 (Procedural Memory)** — Reusable extraction recipes, regex patterns, and traversal workflows.
* [`transformation_memory.py`](coded_tools/modernize/memory/transformation_memory.py): **Tier 5 (Transformation Memory)** — Stores 6R cloud migration classifications, coupling metrics, and candidate microservice boundaries.
* [`memory_manager_tool.py`](coded_tools/modernize/memory/memory_manager_tool.py): `MemoryManagerTool` tool wrapper unifying all 5 tiers into a single tool exposed to the `memory_manager_agent`.

#### F. Report Generation ([`coded_tools/modernize/reports/`](coded_tools/modernize/reports/))
* [`report_generator.py`](coded_tools/modernize/reports/report_generator.py): Synthesizes graph topology, business rules provenance, and coupling metrics into executive markdown reports.

#### G. Automated Unit Tests ([`tests/coded_tools/modernize/`](tests/coded_tools/modernize/))
* [`tests/coded_tools/modernize/test_modernize_fabric.py`](tests/coded_tools/modernize/test_modernize_fabric.py): Comprehensive unit test suite validating memory tiers, parsers, graph algorithms, blast radiuses, and report synthesis.

---

### 4. 📊 Output Artifacts ([`artifacts/`](artifacts/))

The `artifacts/` folder contains all outputs synthesized by the ModernizeAI pipeline:

* [`artifacts/modernize_graph.html`](artifacts/modernize_graph.html): Standalone interactive PyVis 2D/3D visualizer with physics simulation and node filtering.
* [`artifacts/modernize_kg.json`](artifacts/modernize_kg.json): JSON node-link serialization of the complete knowledge graph for web consumption.
* [`artifacts/modernize_kg.graphml`](artifacts/modernize_kg.graphml): Standard GraphML export for enterprise graph databases (Neo4j, Amazon Neptune) and Gephi.
* [`artifacts/business_rules_catalog.md`](artifacts/business_rules_catalog.md): Formalized enterprise business rules (`BR-01` to `BR-05`) with exact line-level source code and specification provenance.
* [`artifacts/impact_blast_radius_matrix.md`](artifacts/impact_blast_radius_matrix.md): Blast radius dependency matrix classifying downstream risks (Critical, High, Medium, Low).
* [`artifacts/modernization_readiness_report.md`](artifacts/modernization_readiness_report.md): Executive modernization readiness report with Martin coupling metrics, Louvain microservice candidates, and 6R cloud migration strategies.

---

### 5. ⚙️ Configuration Files & Dependencies

* [`.env`](.env) / [`.env.example`](.env.example): Contains API credentials (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`) used by ModernizeAI's LLM reasoning swarm.
* [`requirements.txt`](requirements.txt): Python dependency manifest. Includes standard Neuro SAN packages plus ModernizeAI-specific additions (`networkx`, `pyvis`, `jinja2`, `python-multipart`, `pydantic`, `fastapi`, `uvicorn`).
* `config/`: Configuration files in `config/` (`llm_config.hocon`, `plugins.hocon`, etc.) are Neuro SAN Studio framework configs that govern global LLM provider endpoints and plugin enablement.

---

### 6. 🏢 Benchmark Legacy Dataset ([`data/insurance_claims_app/`](data/insurance_claims_app/))

ModernizeAI includes an out-of-the-box legacy enterprise benchmark application (`ClaimCore v2.4`) to demonstrate reverse-engineering and graph synthesis:

* **Java Monolith**: `Claim.java`, `ClaimService.java`, `Customer.java`, `Policy.java`, `PolicyValidationService.java`
* **Relational Database**: `schema.ddl` (Oracle SQL DDL tables, constraints, foreign keys), `process_claim_sp.sql` (stored procedures with row locks)
* **Architecture & SME Specs**: `Claims_Architecture_Spec.md` (claims rules, escalation paths), `SME_Interview_Notes.txt` (undocumented adjuster workarounds)

---

### 7. 📚 ModernizeAI Documentation ([`docs/generated/`](docs/generated/))

* [`docs/generated/MODERNIZE_AI_GUIDE.md`](docs/generated/MODERNIZE_AI_GUIDE.md): Complete architecture specification, 11-agent breakdown, 5-tier memory guide, and deployment handbook.
* [`docs/generated/MODERNIZE_DEMO_DATA_POINTS.md`](docs/generated/MODERNIZE_DEMO_DATA_POINTS.md): Data inventory, graph nodes/edges metrics, and benchmark validation points.

---

### 8. 🏛️ Upstream Host Framework (Neuro SAN Studio — NOT ModernizeAI)

For developers and auditors reviewing the repository, the following components belong to the underlying **Neuro SAN Studio** framework:

* `neuro_san_studio/`: Core Neuro SAN framework engine (CLI commands `ns run`, `ns chat`, `ns init`, agent network assembler, plugin architecture, tool classifiers).
* `middleware/`: Framework-level middlewares (agent checklist middleware, agent skills middleware, persistent memory middleware).
* `servers/`: Framework communication bridges (Agent-to-Agent `a2a/` and Model Context Protocol `mcp/` servers).
* `apps/` (other subfolders): Built-in framework example apps (`conscious_assistant/`, `cruse/`, `log_analyzer/`, `slack/`, `wwaw/`).
* `coded_tools/` (other subfolders): Framework sample tools (`basic/`, `industry/`, `tools/`, `agent_network_architect/`, `agent_network_editor/`).
* `registries/` (other subfolders): Framework sample agent networks (`basic/`, `industry/`, `tools/`, `experimental/`).
* `docs/` (root docs): Upstream framework documentation (`dev_guide.md`, `tutorial.md`, `user_guide.md`, `examples.md`, etc.).
* `tests/` (excluding `tests/coded_tools/modernize/`): Framework unit and integration test harnesses.

---

## 🔬 About the Underlying Framework: Neuro SAN Studio

ModernizeAI is powered by [**Neuro SAN Studio**](https://github.com/cognizant-ai-lab/neuro-san-studio), the hands-on playground and reference implementation for the [**Cognizant Neuro® AI Multi-Agent Accelerator**](https://www.cognizant.com/us/en/ai-lab).

Neuro SAN Studio provides:
* **HOCON-driven Declarative Orchestration**: Define complex multi-agent behaviors without boilerplate glue code.
* **Agent Network Designer (AND)**: Built-in meta-agents capable of generating new agent networks from natural language prompts.
* **Extensible Tool Bridge**: Native support for Python Coded Tools, MCP (Model Context Protocol), LangChain tools, and external agent ecosystems (CrewAI, Agentforce).
* **Enterprise Observability**: End-to-end telemetry, OpenTelemetry / Phoenix logging, and token cost analytics.

### Full Command Reference

| Command | Purpose |
| :--- | :--- |
| `ns init` | Scaffold a new starter project with configured LLM providers. |
| `ns run` | Start the Neuro SAN backend server and `nsflow` visual client. |
| `ns chat <agent>` | Chat with any agent network directly from your terminal. |
| `ns import` | Discover and import ready-to-run agent networks from the library. |
| `ns export` | Package an agent network into a shareable bundle. |
| `ns check-llm-keys` | Verify API key connectivity and format across configured providers. |
| `ns check-config` | Validate HOCON agent configurations and test model responsiveness. |

For deep dives into the underlying engine:
* [Neuro SAN User Guide](docs/user_guide.md)
* [Tutorial](docs/tutorial.md)
* [Developer Guide](docs/dev_guide.md)
* [Example Networks Catalog](docs/examples.md)

---

## 📜 License & Acknowledgments

This project is licensed under the Apache 2.0 License - see the [LICENSE.txt](LICENSE.txt) file for details.

Built with ❤️ using [Cognizant AI Lab Neuro SAN](https://github.com/cognizant-ai-lab/neuro-san).
