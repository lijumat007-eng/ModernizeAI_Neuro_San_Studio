package com.enterprise.claims.model;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * Policy entity representing an insurance coverage contract.
 * Maps to POLICY_MASTER table.
 */
public class Policy {
    private String policyNumber;
    private Long customerId;
    private String policyType; // AUTO, HOME, HEALTH, LIFE
    private BigDecimal coverageAmount;
    private BigDecimal deductible;
    private BigDecimal remainingCoverage;
    private LocalDate startDate;
    private LocalDate endDate;
    private String status; // ACTIVE, EXPIRED, CANCELLED, GRACE_PERIOD

    public Policy() {}

    public String getPolicyNumber() { return policyNumber; }
    public void setPolicyNumber(String policyNumber) { this.policyNumber = policyNumber; }

    public Long getCustomerId() { return customerId; }
    public void setCustomerId(Long customerId) { this.customerId = customerId; }

    public String getPolicyType() { return policyType; }
    public void setPolicyType(String policyType) { this.policyType = policyType; }

    public BigDecimal getCoverageAmount() { return coverageAmount; }
    public void setCoverageAmount(BigDecimal coverageAmount) { this.coverageAmount = coverageAmount; }

    public BigDecimal getDeductible() { return deductible; }
    public void setDeductible(BigDecimal deductible) { this.deductible = deductible; }

    public BigDecimal getRemainingCoverage() { return remainingCoverage; }
    public void setRemainingCoverage(BigDecimal remainingCoverage) { this.remainingCoverage = remainingCoverage; }

    public LocalDate getStartDate() { return startDate; }
    public void setStartDate(LocalDate startDate) { this.startDate = startDate; }

    public LocalDate getEndDate() { return endDate; }
    public void setEndDate(LocalDate endDate) { this.endDate = endDate; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
