# ModernizeAI: Demo Data Points & Legacy Benchmark Inventory

This document details the concrete demo data points, extracted facts, and benchmark metrics for the legacy application analyzed by ModernizeAI.

---

## 1. Analyzed Application Profile

- **Application Name**: `ClaimCore v2.4`
- **Domain**: Enterprise Property & Casualty (P&C) Insurance Claims Processing
- **Source Repository Path**: [`data/insurance_claims_app`](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app)
- **Monolith Characteristics**: Monolithic Java service orchestrating claims, coupling business logic with direct JDBC queries and blocking stored procedures over a shared Oracle database schema.

### Inventory of Legacy Artifacts

| Artifact Name | Type | Size | Key Responsibilities & Logic |
| :--- | :--- | :--- | :--- |
| [`ClaimService.java`](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app/ClaimService.java) | Java Service | 6.1 KB | Core adjudication workflow; directly queries `POLICY_MASTER`, invokes `SP_PROCESS_CLAIM`, inserts into `CLAIMS_RECORD`. |
| [`PolicyValidationService.java`](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app/PolicyValidationService.java) | Java Service | 3.6 KB | Evaluates policy status, date coverage, deductibles, $2,500 auto-approval limits, and $50,000 fraud thresholds. |
| [`Claim.java`](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app/Claim.java) | Java Entity | 2.1 KB | Domain model representing claim requests, amounts, dates, and adjudication status. |
| [`Policy.java`](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app/Policy.java) | Java Entity | 1.9 KB | Domain model for policy coverage limits, effective/expiration dates, and customer bindings. |
| [`Customer.java`](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app/Customer.java) | Java Entity | 1.3 KB | Domain model for policyholder account data. |
| [`schema.ddl`](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app/schema.ddl) | SQL DDL | 1.9 KB | Relational definitions for `CUSTOMER_ACCOUNT`, `POLICY_MASTER`, `CLAIMS_RECORD`, and `CLAIM_AUDIT_LOG`. |
| [`process_claim_sp.sql`](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app/process_claim_sp.sql) | PL/SQL Procedure | 1.5 KB | `SP_PROCESS_CLAIM` with pessimistic row locking (`SELECT ... FOR UPDATE`), deductible deduction, and audit logging. |
| [`Claims_Architecture_Spec.md`](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app/Claims_Architecture_Spec.md) | Markdown Spec | 1.3 KB | High-level system architecture document detailing SLA targets, 30-day grace periods, and audit requirements. |
| [`SME_Interview_Notes.txt`](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app/SME_Interview_Notes.txt) | SME Notes | 1.2 KB | Tribal operational knowledge: reveals 15-day batch billing cutoff, row-lock database contention, and memory leak patterns. |

---

## 2. Knowledge Fabric Graph Metrics

The ModernizeAI Knowledge Graph Fabric constructs a schema-enforced MultiDiGraph saved at [artifacts/modernize_kg.json](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/artifacts/modernize_kg.json):

- **Total Verified Nodes**: 21
- **Total Structural & Semantic Edges**: 29
- **Readiness Score**: **78 / 100**

### Node Distribution by Type
| Entity Type | Node Count | Examples |
| :--- | :---: | :--- |
| `Application` | 1 | `ClaimCore_App` |
| `Service` | 2 | `ClaimService`, `PolicyValidationService` |
| `Model` | 3 | `Claim`, `Policy`, `Customer` |
| `DatabaseTable` | 4 | `POLICY_MASTER`, `CUSTOMER_ACCOUNT`, `CLAIMS_RECORD`, `CLAIM_AUDIT_LOG` |
| `StoredProcedure` | 1 | `SP_PROCESS_CLAIM` |
| `BusinessRule` | 5 | `BR-01`, `BR-02`, `BR-03`, `BR-04`, `BR-05` |
| `ArchitecturalRisk` | 3 | `Risk_Shared_Database`, `Risk_Row_Locking`, `Risk_Hardcoded_Rule` |
| `Document` | 2 | `Claims_Architecture_Spec`, `SME_Tribal_Notes` |

---

## 3. Formalized Business Rules Catalog

Every business rule is extracted deterministically with exact source code file and line numbers:

| Rule ID | Rule Name | Specification | Provenance (File & Line) | Implementing Method |
| :---: | :--- | :--- | :--- | :--- |
| **BR-01** | Policy Status Validation | Policy must be `ACTIVE` or within valid grace period. | `PolicyValidationService.java:21-29` | `validatePolicyStatus()` |
| **BR-02** | Incident Date Eligibility | Incident date must fall within `effectiveDate` and `expirationDate`. | `PolicyValidationService.java:32-40` | `validateIncidentDate()` |
| **BR-03** | Coverage Limit Adjudication | Claim amount cannot exceed remaining policy coverage limit. | `PolicyValidationService.java:43-51` | `validateCoverageLimit()` |
| **BR-04** | High-Risk Fraud Escalation | Claims $> \$50,000$ or filed within 7 days of inception trigger fraud review. | `PolicyValidationService.java:54-63` | `isHighRiskClaim()` |
| **BR-05** | Straight-Through Auto-Approval | Clean claims $< \$2,500$ on active policies qualify for instant auto-approval. | `PolicyValidationService.java:66-72` | `isEligibleForAutoApproval()` |

### Cross-Artifact Discrepancy (20% LLM Reasoning Finding)
- **Documented Rule**: [Claims_Architecture_Spec.md:12](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app/Claims_Architecture_Spec.md#L12) specifies a **30-day grace period**.
- **Code Reality**: [PolicyValidationService.java:27](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app/PolicyValidationService.java#L27) delegates status to database flag.
- **Tribal Truth**: [SME_Interview_Notes.txt:4](file:///c:/Users/lijum/OneDrive/Documents/Copilot%20Projects/cog_nuero/neuro-san-studio-main/data/insurance_claims_app/SME_Interview_Notes.txt#L4) notes the nightly billing cron job enforces a **15-day cutoff**, prematurely lapsing valid policies.

---

## 4. Blast-Radius & Impact Analysis Matrices

### Scenario A: Modifying `POLICY_MASTER` Table Schema
- **Target Entity**: `POLICY_MASTER` (`DatabaseTable`)
- **Direct & Transitive Blast Radius**: **7 Components** (5 Upstream Callers, 2 Downstream Dependencies)
- **Risk Rating**: **Medium-High (Architectural Gravity Well)**

| Impacted Component | Direction | Hop | Relationship | Source Evidence |
| :--- | :--- | :---: | :--- | :--- |
| `ClaimCore_App` | Upstream | 1 | `DEPENDS_ON` | `data/insurance_claims_app:1` |
| `CLAIMS_RECORD` | Upstream | 1 | `DEPENDS_ON` | `schema.ddl:27` |
| `SP_PROCESS_CLAIM` | Upstream | 1 | `READS_FROM` | `process_claim_sp.sql:4` |
| `ClaimService` | Upstream | 1 | `READS_FROM` | `ClaimService.java:19` |
| `CLAIM_AUDIT_LOG` | Upstream | 2 | `DEPENDS_ON` | `schema.ddl:40` |
| `CUSTOMER_ACCOUNT` | Downstream | 1 | `DEPENDS_ON` | `schema.ddl:4` |
| `Risk_Shared_Database` | Downstream | 2 | `IMPACTS` | `schema.ddl:1` |

---

### Scenario B: Refactoring `ClaimService`
- **Target Entity**: `ClaimService` (`Service`)
- **Direct & Transitive Blast Radius**: **8 Components** (1 Upstream Caller, 7 Downstream Dependencies)
- **Risk Rating**: **Medium**

| Impacted Component | Direction | Hop | Relationship | Source Evidence |
| :--- | :--- | :---: | :--- | :--- |
| `ClaimCore_App` | Upstream | 1 | `DEPENDS_ON` | `data/insurance_claims_app:1` |
| `POLICY_MASTER` | Downstream | 1 | `READS_FROM` | `schema.ddl:14` |
| `CUSTOMER_ACCOUNT` | Downstream | 1 | `READS_FROM` | `schema.ddl:4` |
| `CLAIMS_RECORD` | Downstream | 1 | `WRITES_TO` | `schema.ddl:27` |
| `SP_PROCESS_CLAIM` | Downstream | 1 | `CALLS` | `process_claim_sp.sql:4` |
| `Risk_Shared_Database` | Downstream | 2 | `IMPACTS` | `schema.ddl:1` |
| `CLAIM_AUDIT_LOG` | Downstream | 2 | `WRITES_TO` | `schema.ddl:40` |
| `Risk_Row_Locking` | Downstream | 2 | `IMPACTS` | `process_claim_sp.sql:1` |

---

## 5. Candidate Microservices (Louvain Modularity Clustering)

Graph community detection partitions the monolith into 5 bounded domains:

| Domain ID | Proposed Domain Name | Member Components | Recommended Target Architecture |
| :---: | :--- | :--- | :--- |
| **Domain 1** | **Core Domain Models** | `ClaimCore_App`, `Policy`, `Customer`, `Claim` | Shared Domain Library / TypeScript/Java DTOs |
| **Domain 2** | **Claim Settlement & Ledger** | `ClaimService`, `SP_PROCESS_CLAIM`, `CLAIMS_RECORD`, `CLAIM_AUDIT_LOG`, `CUSTOMER_ACCOUNT`, `POLICY_MASTER`, `Risk_Row_Locking`, `Risk_Shared_Database` | Event-Driven Adjudication Microservice with Saga Orchestrator |
| **Domain 3** | **Rules & Eligibility Engine** | `PolicyValidationService`, `BR-01`, `BR-02`, `BR-03`, `BR-04`, `BR-05`, `Risk_Hardcoded_Rule` | Serverless Stateless Rules Engine (AWS Lambda / Cloud Functions) |
| **Domain 4** | **Architecture Specifications** | `Claims_Architecture_Spec` | Architecture Decision Records (ADRs) |
| **Domain 5** | **Operational SME Knowledge** | `SME_Tribal_Notes` | Living Documentation / Confluence / Backlog Stories |

---

## 6. Architectural Coupling & Instability

$$I = \frac{C_e}{C_a + C_e}$$
Where $C_a$ is Afferent Coupling (incoming dependencies) and $C_e$ is Efferent Coupling (outgoing dependencies).

| Component / Entity | Afferent ($C_a$) | Efferent ($C_e$) | Instability Metric ($I$) | Architectural Verdict |
| :--- | :---: | :---: | :---: | :--- |
| `ClaimService` | 1 | 4 | **0.80** | Highly unstable / volatile; candidate for decomposition. |
| `PolicyValidationService` | 1 | 5 | **0.83** | High efferent coupling to rules; candidate for stateless extraction. |
| `POLICY_MASTER` | 5 | 1 | **0.17** | **Architectural Gravity Well**; highly stable but dangerous to modify directly. |
| `CLAIMS_RECORD` | 4 | 2 | **0.33** | Core transaction sink. |
| `SP_PROCESS_CLAIM` | 1 | 5 | **0.83** | Procedural lock-in bottleneck. |

---

## 7. 6R Migration Strategy & Roadmap

| Component | Strategy | Target Cloud Pattern | Phase | Rationale |
| :--- | :--- | :--- | :---: | :--- |
| **Claim Validation** | **Refactor** | Serverless / Cloud Run | **Phase 1** | Decouple pure business rules from monolithic persistence; eliminate hardcoded $2,500 limit. |
| **Claim Adjudication** | **Replatform** | Spring Boot 3.x / Quarkus Container | **Phase 2** | Decompose `ClaimService` and replace blocking `SP_PROCESS_CLAIM` with asynchronous Saga workflow. |
| **Stored Procedure** | **Retire** | Temporal / Step Functions Saga | **Phase 2** | Retire `SP_PROCESS_CLAIM` to eliminate row-locking database timeouts during claim spikes. |
| **Policy Master Data** | **Retain / ACL** | Debezium / Kafka CDC Event Stream | **Phase 3** | Shield shared `POLICY_MASTER` table using an Anti-Corruption Layer (ACL) with event streaming. |
