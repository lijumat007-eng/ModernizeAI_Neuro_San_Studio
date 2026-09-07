# ModernizeAI: Hybrid Agentic Graph-RAG Knowledge Fabric Guide

## 1. Overview & Vision

**ModernizeAI** is an Agentic Knowledge Factory and Hybrid Agentic Graph-RAG platform engineered to solve enterprise legacy application modernization and reverse engineering.

Traditional legacy modernization efforts frequently suffer from a 70%+ failure or delay rate because teams attempt to migrate code before deeply understanding legacy business rules, implicit database locks, and distributed side effects. ModernizeAI solves this by strictly enforcing the **80/20 Principle**:
- **80% Deterministic Extraction**: AST code parsers, regex symbol extractors, SQL/DDL interpreters, and schema analyzers extract concrete facts, method signatures, foreign keys, and line provenance without LLM hallucination.
- **20% LLM Reasoning**: Large Language Models are applied strictly where semantic disambiguation is required—such as interpreting unstructured SME interview notes, resolving documentation-vs-code discrepancies, formulating 6R migration strategies, and answering natural-language architectural questions.

---

## 2. The Two User Interfaces

ModernizeAI provides two distinct user interfaces designed for different workflows:

### A. Neuro SAN Studio Client (`nsflow`)
- **Location**: Built-in Neuro SAN Studio Client
- **URL**: [http://localhost:4173/?network=generated%2Fmodernizeai](http://localhost:4173/?network=generated%2Fmodernizeai)
- **Primary Use Case**: Multi-Agent Orchestration & Network Topology Inspection
- **Features**:
  - **Live Topology Diagram**: Interactive React Flow visualizer rendering the 11 agent nodes, 5 coded tool nodes, and directed communication edges.
  - **Agent Swarm Chat**: Chat directly with `Frontman` and watch real-time task delegation across specialist agents.
  - **Internal Chat & Telemetry**: Live stream of inter-agent delegation protocols, reasoning traces, and token costs.
  - **Sly-Data Inspector**: View sensitive data structures exchanged safely outside LLM context windows.

```bash
# Start Neuro SAN Server + nsflow Studio UI:
ns run
```

---

### B. ModernizeAI Dedicated Web Application Dashboard
- **Location**: [apps/modernizeai_ui/server.py](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/apps/modernizeai_ui/server.py)
- **Default URL**: [http://localhost:8000](http://localhost:8000)
- **Primary Use Case**: End-to-End Modernization Workspace & Knowledge Fabric Explorer
- **Features**:
  - **Ingest & Rebuild Button**: One-click triggering of the deterministic parsing and ingestion pipeline (`/api/scan`).
  - **5-Tier Memory & Graph Metrics**: Real-time counter cards showing active memory tiers, knowledge nodes, structural edges, formalized rules, and candidate microservices.
  - **Swarm Live Status Visualizer**: Interactive chips showing real-time agent execution status.
  - **Interactive PyVis Knowledge Graph**: Embedded, zoomable 2D/3D graph visualization with physics simulation (`/artifacts/modernize_graph.html`).
  - **Blast Radius Explorer**: Interactive query box to calculate transitive dependency impacts for any class or table.
  - **Artifacts Review Center**: Live tabbed viewer for generated Modernization Readiness Reports, Business Rules Catalogs, and Impact Matrices.
  - **Swarm Coordinator Chat**: Direct conversational query engine with source code citation grounding.

```bash
# Start ModernizeAI Web Application:
python apps/modernizeai_ui/server.py --port 8000
```

---

## 3. Architecture & Swarm Specification

ModernizeAI operates as an 11-Agent Mixture-of-Experts Swarm backed by 5 Coded Tools and 5 Memory Tiers.

```mermaid
flowchart TD
    User([User / Architect]) <--> Frontman[Frontman: Swarm Router]
    
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
        KG --> KGTool[(KnowledgeGraphTool: NetworkX)]
        KG --> MemoryMgr[Memory Manager Agent]
        MemoryMgr --> MemTool[(MemoryManagerTool: 5-Tier Store)]
    end

    subgraph Strategy & Analysis Pipeline
        Frontman --> Impact[Impact Analysis Agent]
        Frontman --> Advisor[Modernization Advisor]
        Frontman --> KG
        
        Impact --> KG
        Impact --> KGTool
        Advisor --> KG
        Advisor --> MemoryMgr
    end
```

### Agent Roles

| Agent | Responsibility | Assigned Tools |
| :--- | :--- | :--- |
| **`frontman`** | Initial point of contact; classifies queries and orchestrates the swarm. | `discovery_agent`, `impact_analysis_agent`, `knowledge_graph_agent`, `modernization_advisor_agent` |
| **`discovery_agent`** | Scans legacy source trees, catalogs files, and coordinates parsing. | `code_intel_agent`, `database_intel_agent`, `doc_intel_agent` |
| **`code_intel_agent`** | Deterministic AST parsing of Java/SQL source code (80% rule). | `code_intel_tool`, `business_rules_agent` |
| **`database_intel_agent`** | Deterministic parsing of schema DDLs, tables, columns, and stored procedures. | `database_intel_tool`, `business_rules_agent` |
| **`doc_intel_agent`** | Semantic and structural extraction of architecture docs and SME notes. | `doc_intel_tool`, `business_rules_agent` |
| **`business_rules_agent`**| Formalizes and numbers cross-system enterprise business rules. | `validation_agent` |
| **`validation_agent`** | Quality assurance agent verifying line-level provenance and catching hallucinations. | `knowledge_graph_agent` |
| **`knowledge_graph_agent`**| Assembles and traverses the schema-enforced MultiDiGraph knowledge fabric. | `knowledge_graph_tool`, `memory_manager_agent` |
| **`memory_manager_agent`**| Oversees 5-tier memory persistence and hybrid vector/BM25 retrieval. | `memory_manager_tool` |
| **`impact_analysis_agent`**| Executes blast-radius traversals and risk-classified dependency tracing. | `knowledge_graph_agent`, `knowledge_graph_tool` |
| **`modernization_advisor_agent`** | Computes coupling metrics and generates phased 6R cloud migration strategies. | `knowledge_graph_agent`, `memory_manager_agent` |

---

## 4. Five-Tier Memory Architecture

| Tier | Name | Persistence & Purpose | Key Capabilities |
| :---: | :--- | :--- | :--- |
| **1** | **Raw Memory** | Ingested source files with SHA-256 hashes and line-offset indices. | 100% verifiable source citation; prevents hallucinated references. |
| **2** | **Structural Memory** | Deterministic symbol tables, AST nodes, DDL schemas, and method calls. | High-speed exact lookups of classes, interfaces, and tables. |
| **3** | **Semantic Memory** | In-house vector embeddings and BM25 search over documentation and SME notes. | Semantic concept matching, intent search, and terminology resolution. |
| **4** | **Procedural Memory** | Reusable extraction heuristics, regex recipes, and traversal algorithms. | Dynamic pattern reuse for legacy dialects and custom coding standards. |
| **5** | **Transformation Memory** | 6R migration classifications, coupling metrics ($C_a, C_e, I$), and roadmaps. | Phased cloud migration plans, architectural scorecards, and audit reports. |

---

## 5. Execution Modes & CLI

In addition to both web UIs, ModernizeAI includes an interactive terminal runner:

```bash
# Run ModernizeAI CLI Runner
python scripts/run_modernize_cli.py
```

### Sample CLI & Swarm Queries
- *"Scan and ingest the legacy application in `data/insurance_claims_app`"*
- *"What modules and tables are impacted if `POLICY_MASTER` changes?"*
- *"What business rules govern insurance claim validation and deductibles?"*
- *"What candidate microservices are identified by community detection?"*
- *"Generate modernization readiness report and interactive knowledge graph visualization"*
