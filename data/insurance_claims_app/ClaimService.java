package com.enterprise.claims.service;

import com.enterprise.claims.model.Claim;
import com.enterprise.claims.model.Customer;
import com.enterprise.claims.model.Policy;
import java.math.BigDecimal;
import java.sql.CallableStatement;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDateTime;
import java.util.List;

/**
 * Main application service orchestrating legacy claim processing.
 * Direct dependencies on PolicyValidationService, POLICY_MASTER, CLAIMS_RECORD, and SP_PROCESS_CLAIM.
 */
public class ClaimService {

    private final PolicyValidationService validationService;

    public ClaimService() {
        this.validationService = new PolicyValidationService();
    }

    /**
     * Ingests, validates, and persists a newly submitted claim.
     * Interacts with POLICY_MASTER and CLAIMS_RECORD tables.
     */
    public Claim processClaim(Connection conn, String policyNumber, BigDecimal amount, String description) throws SQLException {
        // 1. Fetch Policy from POLICY_MASTER
        Policy policy = fetchPolicy(conn, policyNumber);
        if (policy == null) {
            throw new IllegalArgumentException("Unknown policy: " + policyNumber);
        }

        // 2. Fetch Customer from CUSTOMER_ACCOUNT
        Customer customer = fetchCustomer(conn, policy.getCustomerId());

        // 3. Build preliminary Claim
        Claim claim = new Claim();
        claim.setClaimId("CLM-" + System.currentTimeMillis());
        claim.setPolicyNumber(policyNumber);
        claim.setCustomerId(customer.getCustomerId());
        claim.setClaimAmount(amount);
        claim.setIncidentDescription(description);
        claim.setFilingDate(LocalDateTime.now());
        claim.setIncidentDate(LocalDateTime.now().minusDays(2));

        // 4. Validate Business Rules via PolicyValidationService
        List<String> violations = validationService.evaluateAllRules(claim, policy);
        if (!violations.isEmpty()) {
            claim.setStatus("REJECTED");
            persistClaim(conn, claim);
            return claim;
        }

        // 5. Check High Risk / Fraud
        if (validationService.isHighRiskClaim(claim, policy)) {
            claim.setStatus("ESCALATED_FRAUD");
            persistClaim(conn, claim);
            return claim;
        }

        // 6. Execute SP_PROCESS_CLAIM to calculate deductible and update remaining balances
        executeClaimStoredProcedure(conn, claim.getClaimId(), policy.getPolicyNumber(), amount);

        claim.setStatus("APPROVED");
        claim.setApprovedAmount(amount.subtract(policy.getDeductible()));
        return claim;
    }

    private Policy fetchPolicy(Connection conn, String policyNumber) throws SQLException {
        String sql = "SELECT policy_number, customer_id, policy_type, coverage_amount, deductible, remaining_coverage, start_date, end_date, status FROM POLICY_MASTER WHERE policy_number = ?";
        try (PreparedStatement stmt = conn.prepareStatement(sql)) {
            stmt.setString(1, policyNumber);
            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    Policy p = new Policy();
                    p.setPolicyNumber(rs.getString("policy_number"));
                    p.setCustomerId(rs.getLong("customer_id"));
                    p.setPolicyType(rs.getString("policy_type"));
                    p.setCoverageAmount(rs.getBigDecimal("coverage_amount"));
                    p.setDeductible(rs.getBigDecimal("deductible"));
                    p.setRemainingCoverage(rs.getBigDecimal("remaining_coverage"));
                    p.setStartDate(rs.getDate("start_date").toLocalDate());
                    p.setEndDate(rs.getDate("end_date").toLocalDate());
                    p.setStatus(rs.getString("status"));
                    return p;
                }
            }
        }
        return null;
    }

    private Customer fetchCustomer(Connection conn, Long customerId) throws SQLException {
        String sql = "SELECT customer_id, first_name, last_name, ssn, email, status FROM CUSTOMER_ACCOUNT WHERE customer_id = ?";
        try (PreparedStatement stmt = conn.prepareStatement(sql)) {
            stmt.setLong(1, customerId);
            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    Customer c = new Customer();
                    c.setCustomerId(rs.getLong("customer_id"));
                    c.setFirstName(rs.getString("first_name"));
                    c.setLastName(rs.getString("last_name"));
                    c.setStatus(rs.getString("status"));
                    return c;
                }
            }
        }
        return null;
    }

    private void persistClaim(Connection conn, Claim claim) throws SQLException {
        String sql = "INSERT INTO CLAIMS_RECORD (claim_id, policy_number, customer_id, claim_amount, approved_amount, status, incident_description, filing_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)";
        try (PreparedStatement stmt = conn.prepareStatement(sql)) {
            stmt.setString(1, claim.getClaimId());
            stmt.setString(2, claim.getPolicyNumber());
            stmt.setLong(3, claim.getCustomerId());
            stmt.setBigDecimal(4, claim.getClaimAmount());
            stmt.setBigDecimal(5, claim.getApprovedAmount() != null ? claim.getApprovedAmount() : BigDecimal.ZERO);
            stmt.setString(6, claim.getStatus());
            stmt.setString(7, claim.getIncidentDescription());
            stmt.setTimestamp(8, java.sql.Timestamp.valueOf(claim.getFilingDate()));
            stmt.executeUpdate();
        }
    }

    private void executeClaimStoredProcedure(Connection conn, String claimId, String policyNumber, BigDecimal amount) throws SQLException {
        String call = "{call SP_PROCESS_CLAIM(?, ?, ?)}";
        try (CallableStatement cstmt = conn.prepareCall(call)) {
            cstmt.setString(1, claimId);
            cstmt.setString(2, policyNumber);
            cstmt.setBigDecimal(3, amount);
            cstmt.execute();
        }
    }
}
