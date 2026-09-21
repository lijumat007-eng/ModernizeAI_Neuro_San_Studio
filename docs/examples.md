# ModernizeAI Agent Swarm & Architectures

Welcome to the **ModernizeAI** multi-agent network showcase on Neuro SAN Studio.

ModernizeAI replaces legacy demo bots with a unified, production-grade 11-agent autonomous swarm tailored for enterprise cloud modernization, legacy code migration (.NET / Java / SQL monoliths to Cloud-Native microservices), and deterministic AST/DDL knowledge graph extraction.

---

## 🚀 Active Production Network: `modernizeai.hocon`

The primary network configuration is located at:
[`registries/generated/modernizeai.hocon`](../registries/generated/modernizeai.hocon)

You can launch and interact with the network directly:
```bash
# Interactive conversational session
ns chat modernizeai

# Run network server
ns run
```

---

## 🏛️ The 11 Specialized Modernization Agents

ModernizeAI coordinates 11 purpose-built agents operating over a shared 5-Tier Memory Hierarchy and MultiDiGraph Knowledge Fabric:

| # | Agent Name | Primary Specialty | Key Tools & Engines |
|---|:---|:---|:---|
| 1 | **System Architect** | Global orchestration, monolith decomposition topology, microservices boundary definition | Graph Visualizer, Memory Manager |
| 2 | **Code Modernization Advisor** | 6R cloud migration strategy formulation (`Refactor`, `Replatform`, `Retire`, `Retain`) | Modernization Scoring Engine, AST Parsers |
| 3 | **Code Quality & Compliance** | Provenance verification, SHA-256 line citation audit, discrepancy auto-injection | Provenance QA Validator |
| 4 | **Business Rules Extraction** | AST/DDL deterministic rule extraction from Java, PL/SQL, and markdown specs | Rules Extractor Tool |
| 5 | **Cloud Architecture & Sizing** | Target cloud topology sizing (AWS/Azure/GCP), containerization, event-driven streaming | Sizing Calculator Tool |
| 6 | **Target Tech Stack Evaluator** | Framework evaluation (Spring Boot, Quarkus, .NET 9, Cloud-Native messaging) | Compatibility Matrix Engine |
| 7 | **Migration Roadmap & Planning** | Wave planning, dependency blast radius sequencing, risk mitigation milestones | Graph Algorithms (PageRank, Betweenness) |
| 8 | **Test Modernization Strategy** | JUnit / TestNG test suite generation, boundary value testing, regression harness | Test Synthesis Engine |
| 9 | **Discovery Orchestrator** | Multi-source codebase ingestion (Java, DDL, PL/SQL, Architecture specs, SME notes) | Discovery Tool |
| 10 | **Discovery Analyzer** | Graph node classification, cyclomatic complexity profiling, coupling metrics | NetworkX Graph Engine |
| 11 | **Transformation Engine** | Code translation, stored procedure conversion to microservices logic, OpenAPI generation | Transformation Memory Manager |

---

## 📚 Comprehensive Documentation Links

- **[ModernizeAI Architectural Guide](./generated/MODERNIZE_AI_GUIDE.md)**: Deep dive into the 5-tier memory, 6R scoring, and zero-mock dynamic pipeline.
- **[Demo Benchmark Data Points](./generated/MODERNIZE_DEMO_DATA_POINTS.md)**: Detailed profile of the `ClaimCore v2.4` benchmark application.
- **[Developer Guide](./dev_guide.md)**: Setting up developer environments, linting, and running test harnesses.
- **[CLI Reference Guide](./cli.md)**: Complete guide to the `ns` CLI tool suite.
