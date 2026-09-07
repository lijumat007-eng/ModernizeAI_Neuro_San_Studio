package com.enterprise.claims.service;

import com.enterprise.claims.model.Claim;
import com.enterprise.claims.model.Policy;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * PolicyValidationService encapsulates core compliance and underwriting business rules.
 * Enforces business rules BR-01 through BR-05.
 */
public class PolicyValidationService {

    private static final BigDecimal HIGH_RISK_THRESHOLD = new BigDecimal("50000.00");
    private static final BigDecimal AUTO_APPROVAL_LIMIT = new BigDecimal("2500.00");

    /**
     * Rule BR-01: Policy Status Validation.
     * Verifies that the policy is ACTIVE or within legitimate 30-day grace period.
     */
    public boolean validatePolicyStatus(Policy policy) {
        if (policy == null) {
            return false;
        }
        String status = policy.getStatus();
        return "ACTIVE".equalsIgnoreCase(status) || "GRACE_PERIOD".equalsIgnoreCase(status);
    }

    /**
     * Rule BR-02: Date Eligibility Check.
     * Incident date must occur within policy start and end dates.
     */
    public boolean validateIncidentDate(Claim claim, Policy policy) {
        if (claim == null || policy == null || claim.getIncidentDate() == null) {
            return false;
        }
        LocalDate incident = claim.getIncidentDate().toLocalDate();
        return !incident.isBefore(policy.getStartDate()) && !incident.isAfter(policy.getEndDate());
    }

    /**
     * Rule BR-03: Coverage Limit Check.
     * Claim amount cannot exceed remaining policy coverage limit.
     */
    public boolean validateCoverageLimit(Claim claim, Policy policy) {
        if (claim == null || policy == null) {
            return false;
        }
        BigDecimal claimAmt = claim.getClaimAmount();
        BigDecimal remaining = policy.getRemainingCoverage();
        return claimAmt != null && remaining != null && claimAmt.compareTo(remaining) <= 0;
    }

    /**
     * Rule BR-04: High Risk Fraud Escalation.
     * Claims exceeding $50,000 or filed within 7 days of policy start date require special fraud escalation.
     */
    public boolean isHighRiskClaim(Claim claim, Policy policy) {
        if (claim.getClaimAmount().compareTo(HIGH_RISK_THRESHOLD) > 0) {
            return true;
        }
        LocalDate filingDate = claim.getFilingDate().toLocalDate();
        LocalDate startWindow = policy.getStartDate().plusDays(7);
        return filingDate.isBefore(startWindow);
    }

    /**
     * Rule BR-05: Auto Approval Eligibility.
     * Clean claims under $2,500 on active policies are eligible for straight-through auto-approval.
     */
    public boolean isEligibleForAutoApproval(Claim claim, Policy policy) {
        return validatePolicyStatus(policy)
            && validateIncidentDate(claim, policy)
            && validateCoverageLimit(claim, policy)
            && claim.getClaimAmount().compareTo(AUTO_APPROVAL_LIMIT) <= 0;
    }

    public List<String> evaluateAllRules(Claim claim, Policy policy) {
        List<String> violations = new ArrayList<>();
        if (!validatePolicyStatus(policy)) {
            violations.add("BR-01 VIOLATION: Policy is not active (Status: " + policy.getStatus() + ")");
        }
        if (!validateIncidentDate(claim, policy)) {
            violations.add("BR-02 VIOLATION: Incident date is outside coverage interval.");
        }
        if (!validateCoverageLimit(claim, policy)) {
            violations.add("BR-03 VIOLATION: Claim amount exceeds available coverage.");
        }
        return violations;
    }
}
