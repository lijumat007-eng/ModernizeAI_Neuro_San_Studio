# ModernizeAI: Impact & Blast-Radius Matrix

This matrix provides quantitative impact assessments for critical proposed change scenarios across the legacy architecture.

## Scenario A: Modifications to `POLICY_MASTER` Schema or Data Model
- **Target Entity**: `POLICY_MASTER` (DatabaseTable)
- **Risk Classification**: **MEDIUM RISK**
- **Direct & Transitive Blast Radius**: 7 components (5 Upstream, 2 Downstream).

| Impacted Component | Direction | Hop Distance | Relationship | Source Code Citation |
| :--- | :--- | :---: | :--- | :--- |
| `ClaimCore_App` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `data/insurance_claims_app:1` |
| `CLAIMS_RECORD` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `schema.ddl:27` |
| `SP_PROCESS_CLAIM` | Upstream (Caller/Reader) | 1 | `READS_FROM` | `process_claim_sp.sql:4` |
| `ClaimService` | Upstream (Caller/Reader) | 1 | `READS_FROM` | `ClaimService.java:19` |
| `CLAIM_AUDIT_LOG` | Upstream (Caller/Reader) | 2 | `DEPENDS_ON` | `schema.ddl:40` |
| `CUSTOMER_ACCOUNT` | Downstream (Dependency) | 1 | `DEPENDS_ON` | `schema.ddl:4` |
| `Risk_Shared_Database` | Downstream (Dependency) | 2 | `IMPACTS` | `schema.ddl:1` |

---

## Scenario B: Modifications to `ClaimService`
- **Target Entity**: `ClaimService` (Service)
- **Risk Classification**: **MEDIUM RISK**
- **Direct & Transitive Blast Radius**: 8 components (1 Upstream, 7 Downstream).

| Impacted Component | Direction | Hop Distance | Relationship | Source Code Citation |
| :--- | :--- | :---: | :--- | :--- |
| `ClaimCore_App` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `data/insurance_claims_app:1` |
| `POLICY_MASTER` | Downstream (Dependency) | 1 | `READS_FROM` | `schema.ddl:14` |
| `CUSTOMER_ACCOUNT` | Downstream (Dependency) | 1 | `READS_FROM` | `schema.ddl:4` |
| `CLAIMS_RECORD` | Downstream (Dependency) | 1 | `WRITES_TO` | `schema.ddl:27` |
| `SP_PROCESS_CLAIM` | Downstream (Dependency) | 1 | `CALLS` | `process_claim_sp.sql:4` |
| `Risk_Shared_Database` | Downstream (Dependency) | 2 | `IMPACTS` | `schema.ddl:1` |
| `CLAIM_AUDIT_LOG` | Downstream (Dependency) | 2 | `WRITES_TO` | `schema.ddl:40` |
| `Risk_Row_Locking` | Downstream (Dependency) | 2 | `IMPACTS` | `process_claim_sp.sql:1` |

---
*Generated automatically by ModernizeAI Hybrid Agentic Graph-RAG Knowledge Fabric.*
