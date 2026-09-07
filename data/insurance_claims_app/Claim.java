package com.enterprise.claims.model;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * Claim entity representing a claim filed against a policy.
 * Maps to CLAIMS_RECORD table.
 */
public class Claim {
    private String claimId;
    private String policyNumber;
    private Long customerId;
    private BigDecimal claimAmount;
    private BigDecimal approvedAmount;
    private String incidentDescription;
    private LocalDateTime incidentDate;
    private LocalDateTime filingDate;
    private String status; // SUBMITTED, IN_REVIEW, APPROVED, REJECTED, ESCALATED_FRAUD
    private String adjustedBy;

    public Claim() {}

    public String getClaimId() { return claimId; }
    public void setClaimId(String claimId) { this.claimId = claimId; }

    public String getPolicyNumber() { return policyNumber; }
    public void setPolicyNumber(String policyNumber) { this.policyNumber = policyNumber; }

    public Long getCustomerId() { return customerId; }
    public void setCustomerId(Long customerId) { this.customerId = customerId; }

    public BigDecimal getClaimAmount() { return claimAmount; }
    public void setClaimAmount(BigDecimal claimAmount) { this.claimAmount = claimAmount; }

    public BigDecimal getApprovedAmount() { return approvedAmount; }
    public void setApprovedAmount(BigDecimal approvedAmount) { this.approvedAmount = approvedAmount; }

    public String getIncidentDescription() { return incidentDescription; }
    public void setIncidentDescription(String incidentDescription) { this.incidentDescription = incidentDescription; }

    public LocalDateTime getIncidentDate() { return incidentDate; }
    public void setIncidentDate(LocalDateTime incidentDate) { this.incidentDate = incidentDate; }

    public LocalDateTime getFilingDate() { return filingDate; }
    public void setFilingDate(LocalDateTime filingDate) { this.filingDate = filingDate; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public String getAdjustedBy() { return adjustedBy; }
    public void setAdjustedBy(String adjustedBy) { this.adjustedBy = adjustedBy; }
}
