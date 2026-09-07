package com.enterprise.claims.model;

import java.time.LocalDate;

/**
 * Customer entity representing the insured party.
 * Legacy POJO mapped to CUSTOMER_ACCOUNT table.
 */
public class Customer {
    private Long customerId;
    private String firstName;
    private String lastName;
    private String ssn;
    private String email;
    private String status; // ACTIVE, SUSPENDED, DECEASED
    private LocalDate joinedDate;

    public Customer() {}

    public Long getCustomerId() { return customerId; }
    public void setCustomerId(Long customerId) { this.customerId = customerId; }

    public String getFirstName() { return firstName; }
    public void setFirstName(String firstName) { this.firstName = firstName; }

    public String getLastName() { return lastName; }
    public void setLastName(String lastName) { this.lastName = lastName; }

    public String getSsn() { return ssn; }
    public void setSsn(String ssn) { this.ssn = ssn; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public LocalDate getJoinedDate() { return joinedDate; }
    public void setJoinedDate(LocalDate joinedDate) { this.joinedDate = joinedDate; }
}
