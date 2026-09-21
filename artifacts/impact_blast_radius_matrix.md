# ModernizeAI: Impact & Blast-Radius Matrix

This matrix provides quantitative impact assessments for critical proposed change scenarios across the legacy architecture.

## Scenario: Modifications to `CUSTOMER_ACCOUNT` (DatabaseTable)
- **Target Entity**: `CUSTOMER_ACCOUNT` (DatabaseTable)
- **Risk Classification**: **MEDIUM RISK**
- **Direct & Transitive Blast Radius**: 6 components (6 Upstream, 0 Downstream).

| Impacted Component | Direction | Hop Distance | Relationship | Source Code Citation |
| :--- | :--- | :---: | :--- | :--- |
| `ClaimCore_App` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `data/insurance_claims_app:1` |
| `POLICY_MASTER` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `schema.ddl:14` |
| `CLAIMS_RECORD` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `schema.ddl:27` |
| `ClaimService` | Upstream (Caller/Reader) | 1 | `READS_FROM` | `ClaimService.java:19` |
| `SP_PROCESS_CLAIM` | Upstream (Caller/Reader) | 2 | `READS_FROM` | `process_claim_sp.sql:4` |
| `CLAIM_AUDIT_LOG` | Upstream (Caller/Reader) | 2 | `DEPENDS_ON` | `schema.ddl:40` |

## Scenario: Modifications to `POLICY_MASTER` (DatabaseTable)
- **Target Entity**: `POLICY_MASTER` (DatabaseTable)
- **Risk Classification**: **MEDIUM RISK**
- **Direct & Transitive Blast Radius**: 6 components (5 Upstream, 1 Downstream).

| Impacted Component | Direction | Hop Distance | Relationship | Source Code Citation |
| :--- | :--- | :---: | :--- | :--- |
| `ClaimCore_App` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `data/insurance_claims_app:1` |
| `CLAIMS_RECORD` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `schema.ddl:27` |
| `SP_PROCESS_CLAIM` | Upstream (Caller/Reader) | 1 | `READS_FROM` | `process_claim_sp.sql:4` |
| `ClaimService` | Upstream (Caller/Reader) | 1 | `READS_FROM` | `ClaimService.java:19` |
| `CLAIM_AUDIT_LOG` | Upstream (Caller/Reader) | 2 | `DEPENDS_ON` | `schema.ddl:40` |
| `CUSTOMER_ACCOUNT` | Downstream (Dependency) | 1 | `DEPENDS_ON` | `schema.ddl:4` |

## Scenario: Modifications to `CLAIMS_RECORD` (DatabaseTable)
- **Target Entity**: `CLAIMS_RECORD` (DatabaseTable)
- **Risk Classification**: **MEDIUM RISK**
- **Direct & Transitive Blast Radius**: 6 components (4 Upstream, 2 Downstream).

| Impacted Component | Direction | Hop Distance | Relationship | Source Code Citation |
| :--- | :--- | :---: | :--- | :--- |
| `ClaimCore_App` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `data/insurance_claims_app:1` |
| `CLAIM_AUDIT_LOG` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `schema.ddl:40` |
| `SP_PROCESS_CLAIM` | Upstream (Caller/Reader) | 1 | `WRITES_TO` | `process_claim_sp.sql:4` |
| `ClaimService` | Upstream (Caller/Reader) | 1 | `WRITES_TO` | `ClaimService.java:19` |
| `POLICY_MASTER` | Downstream (Dependency) | 1 | `DEPENDS_ON` | `schema.ddl:14` |
| `CUSTOMER_ACCOUNT` | Downstream (Dependency) | 1 | `DEPENDS_ON` | `schema.ddl:4` |

## Scenario: Modifications to `CLAIM_AUDIT_LOG` (DatabaseTable)
- **Target Entity**: `CLAIM_AUDIT_LOG` (DatabaseTable)
- **Risk Classification**: **MEDIUM RISK**
- **Direct & Transitive Blast Radius**: 6 components (3 Upstream, 3 Downstream).

| Impacted Component | Direction | Hop Distance | Relationship | Source Code Citation |
| :--- | :--- | :---: | :--- | :--- |
| `ClaimCore_App` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `data/insurance_claims_app:1` |
| `SP_PROCESS_CLAIM` | Upstream (Caller/Reader) | 1 | `WRITES_TO` | `process_claim_sp.sql:4` |
| `ClaimService` | Upstream (Caller/Reader) | 2 | `CALLS` | `ClaimService.java:19` |
| `CLAIMS_RECORD` | Downstream (Dependency) | 1 | `DEPENDS_ON` | `schema.ddl:27` |
| `POLICY_MASTER` | Downstream (Dependency) | 2 | `DEPENDS_ON` | `schema.ddl:14` |
| `CUSTOMER_ACCOUNT` | Downstream (Dependency) | 2 | `DEPENDS_ON` | `schema.ddl:4` |


---
*Generated dynamically by ModernizeAI Hybrid Agentic Graph-RAG Knowledge Fabric.*
