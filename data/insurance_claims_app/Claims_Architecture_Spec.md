# Legacy Insurance Claims Architecture Specification

## 1. System Overview
The Insurance Claims Management System (ClaimCore v2.4) is a core legacy monolith responsible for adjudicating, tracking, and settling insurance claims across Auto, Home, Health, and Life lines of business.

## 2. Core Functional Workflows
- **Claim Ingestion**: Claims are received via web interface or legacy batch files and assigned a unique `claim_id`.
- **Policy Eligibility Verification**: The system verifies policy status against `POLICY_MASTER`. Policies must have status `ACTIVE` or `GRACE_PERIOD`.
- **Date Range Compliance**: Incident date must fall between `start_date` and `end_date`.
- **Deductible & Settlement Calculation**: Handled through database stored procedure `SP_PROCESS_CLAIM` to guarantee transactional locking.
- **Audit & Compliance**: Every payout triggers a mandatory audit logging entry in `CLAIM_AUDIT_LOG`.

## 3. Key Non-Functional Requirements & Constraints
- **Data Integrity**: Financial transactions lock `POLICY_MASTER` rows using `SELECT ... FOR UPDATE`.
- **High Risk Flagging**: Claims exceeding $50,000.00 or filed within 7 days of policy activation are flagged as `ESCALATED_FRAUD` for special investigation.
- **SLAs**: Straight-through claims under $2,500.00 must be auto-approved within 10 minutes.
