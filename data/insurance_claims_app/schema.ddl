-- Legacy Insurance Claims Management Relational Schema
-- Dialect: ANSI SQL / Oracle / PostgreSQL Compatible

CREATE TABLE CUSTOMER_ACCOUNT (
    customer_id BIGINT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    ssn VARCHAR(11) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE POLICY_MASTER (
    policy_number VARCHAR(50) PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    policy_type VARCHAR(30) NOT NULL,
    coverage_amount DECIMAL(15,2) NOT NULL,
    deductible DECIMAL(10,2) NOT NULL,
    remaining_coverage DECIMAL(15,2) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    CONSTRAINT fk_policy_customer FOREIGN KEY (customer_id) REFERENCES CUSTOMER_ACCOUNT(customer_id)
);

CREATE TABLE CLAIMS_RECORD (
    claim_id VARCHAR(50) PRIMARY KEY,
    policy_number VARCHAR(50) NOT NULL,
    customer_id BIGINT NOT NULL,
    claim_amount DECIMAL(15,2) NOT NULL,
    approved_amount DECIMAL(15,2) DEFAULT 0.00,
    incident_description TEXT,
    filing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(30) NOT NULL,
    CONSTRAINT fk_claim_policy FOREIGN KEY (policy_number) REFERENCES POLICY_MASTER(policy_number),
    CONSTRAINT fk_claim_customer FOREIGN KEY (customer_id) REFERENCES CUSTOMER_ACCOUNT(customer_id)
);

CREATE TABLE CLAIM_AUDIT_LOG (
    log_id BIGINT PRIMARY KEY,
    claim_id VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    changed_by VARCHAR(50) NOT NULL,
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_claim FOREIGN KEY (claim_id) REFERENCES CLAIMS_RECORD(claim_id)
);

CREATE INDEX idx_policy_customer ON POLICY_MASTER(customer_id);
CREATE INDEX idx_claims_policy ON CLAIMS_RECORD(policy_number);
CREATE INDEX idx_claims_status ON CLAIMS_RECORD(status);
