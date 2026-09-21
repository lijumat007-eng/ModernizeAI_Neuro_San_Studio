# ModernizeAI: Business Rules Catalog & Traceability Matrix

Every business rule extracted by the multi-agent swarm is formalized, numbered, and directly tied to verifiable source code lines and database structures (80% deterministic extraction).

| Rule ID | Rule Name | Description | Source File Citation | Implementation Method |
| :---: | :--- | :--- | :--- | :--- |
| **BR-01** | Process Claim Check | Method processClaim() validates: policy == null AND !violations.isEmpty( | `ClaimService.java:31-72` | `processClaim` |
| **BR-02** | Policy Status Check | Method validatePolicyStatus() validates: policy == null | `PolicyValidationService.java:23-29` | `validatePolicyStatus` |
| **BR-03** | Incident Date Check | Method validateIncidentDate() validates: claim == null || policy == null || claim.getIncidentDate( | `PolicyValidationService.java:35-41` | `validateIncidentDate` |
| **BR-04** | Coverage Limit Check | Method validateCoverageLimit() validates: claim == null || policy == null | `PolicyValidationService.java:47-54` | `validateCoverageLimit` |
| **BR-05** | High Risk Claim Check | Method isHighRiskClaim() validates: claim.getClaimAmount( | `PolicyValidationService.java:60-67` | `isHighRiskClaim` |
| **BR-06** | Eligible For Auto Approval Check | Method isEligibleForAutoApproval() validates: Enforces business condition. | `PolicyValidationService.java:73-78` | `isEligibleForAutoApproval` |
| **BR-07** | Stored Procedure Constraint #1 | Stored procedure validates: IF p_claim_amount > v_deductible | `process_claim_sp.sql:24-26` | `SP_PROCESS_CLAIM` |
| **BR-08** | Stored Procedure Constraint #2 | Stored procedure validates: IF v_net_approved > v_remaining | `process_claim_sp.sql:31-33` | `SP_PROCESS_CLAIM` |

## Cross-Artifact Rule Consistency Findings

> [!WARNING]
> **Grace Period Constraint Conflict (Documentation vs Tribal Reality)** (Severity: HIGH):
> - **Description**: Architecture specification claims a 30-day grace period (SME_Interview_Notes.txt:5), but operational SME notes (SME_Interview_Notes.txt:5) reveal the nightly billing batch job only enforces a 15-day cutoff, prematurely lapsing valid policies.
> - **Evidence**: SME_Interview_Notes.txt:5 -> "1. "The official spec says policy grace period is 30 days after missed premium, but in the Java code, PolicyValidationService actually allows claims if status is literally 'GRACE_PERIOD', which the batch billing job only sets for 15 days. So there is a mismatch between marketing documents and the code.""
> - **Recommendation**: Reconcile underwriting contract terms with the billing batch schedule. In the target cloud microservice, implement a deterministic policy expiration saga.

> [!WARNING]
> **Pessimistic Row Locking in High-Volume Adjudication Procedure** (Severity: CRITICAL):
> - **Description**: SP_PROCESS_CLAIM executes 'SELECT ... FOR UPDATE' on POLICY_MASTER rows. During claim surges, this creates blocking database locks across concurrent customer requests.
> - **Evidence**: process_claim_sp.sql:21 -> SELECT ... FOR UPDATE
> - **Recommendation**: Retire stored procedure; replace with optimistic concurrency or an asynchronous distributed Outbox saga.

> [!WARNING]
> **Hardcoded Threshold Constant ($2500) in Source Code** (Severity: MEDIUM):
> - **Description**: Financial threshold value $2500 is hardcoded in Java service logic instead of being configurable via enterprise rule engine.
> - **Evidence**: PolicyValidationService.java:17
> - **Recommendation**: Extract threshold into centralized cloud configuration service (AWS AppConfig or Spring Cloud Config).


---
*Generated dynamically by ModernizeAI Hybrid Agentic Graph-RAG Knowledge Fabric.*
