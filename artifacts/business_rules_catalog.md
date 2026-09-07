# ModernizeAI: Business Rules Catalog & Traceability Matrix

Every business rule extracted by the multi-agent swarm is formalized, numbered, and directly tied to verifiable source code lines and database structures (80% deterministic extraction).

| Rule ID | Rule Name | Description | Source File Citation | Implementation Method |
| :---: | :--- | :--- | :--- | :--- |
| **BR-01** | Policy Status Validation | Policy must be ACTIVE or within legitimate 30-day grace period. | `PolicyValidationService.java:21-29` | `validatePolicyStatus()` |
| **BR-02** | Incident Date Range Eligibility | Incident date must occur within policy start and end dates. | `PolicyValidationService.java:32-40` | `validateIncidentDate()` |
| **BR-03** | Coverage Limit Adjudication | Claim amount cannot exceed remaining policy coverage limit. | `PolicyValidationService.java:43-51` | `validateCoverageLimit()` |
| **BR-04** | High Risk Fraud Escalation | Claims exceeding $50,000 or filed within 7 days of inception trigger fraud review. | `PolicyValidationService.java:54-63` | `isHighRiskClaim()` |
| **BR-05** | Straight-Through Auto Approval Limit | Clean claims under $2,500 on active policies qualify for instant auto-approval. | `PolicyValidationService.java:66-72` | `isEligibleForAutoApproval()` |

## Cross-Artifact Rule Consistency Findings

> [!WARNING]
> **Grace Period Discrepancy (Doc vs Code)**:
> - **Architecture Specification & Marketing**: Claims grace period is defined as **30 days**.
> - **Java Implementation (`PolicyValidationService.java:27`)**: Checks `policy.getStatus().equalsIgnoreCase("GRACE_PERIOD")`.
> - **SME Interview Finding (`SME_Interview_Notes.txt:4`)**: The nightly batch billing job sets `GRACE_PERIOD` for only **15 days**.
> - **Recommendation**: Align policy configuration table with official underwriting terms before migrating to cloud microservice.

---
*Generated automatically by ModernizeAI Hybrid Agentic Graph-RAG Knowledge Fabric.*
