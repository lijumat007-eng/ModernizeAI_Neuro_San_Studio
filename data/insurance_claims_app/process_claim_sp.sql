-- Stored Procedure: SP_PROCESS_CLAIM
-- Processes claim deduction, updates remaining policy coverage, and writes audit entry

CREATE OR REPLACE PROCEDURE SP_PROCESS_CLAIM(
    p_claim_id IN VARCHAR,
    p_policy_number IN VARCHAR,
    p_claim_amount IN DECIMAL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_deductible DECIMAL(10,2);
    v_remaining DECIMAL(15,2);
    v_net_approved DECIMAL(15,2);
BEGIN
    -- Read policy thresholds
    SELECT deductible, remaining_coverage
    INTO v_deductible, v_remaining
    FROM POLICY_MASTER
    WHERE policy_number = p_policy_number
    FOR UPDATE;

    -- Calculate approved payout after deductible
    IF p_claim_amount > v_deductible THEN
        v_net_approved := p_claim_amount - v_deductible;
    ELSE
        v_net_approved := 0.00;
    END IF;

    -- Ensure payout does not exceed remaining coverage
    IF v_net_approved > v_remaining THEN
        v_net_approved := v_remaining;
    END IF;

    -- Deduct remaining coverage in POLICY_MASTER
    UPDATE POLICY_MASTER
    SET remaining_coverage = remaining_coverage - v_net_approved
    WHERE policy_number = p_policy_number;

    -- Update approved amount in CLAIMS_RECORD
    UPDATE CLAIMS_RECORD
    SET approved_amount = v_net_approved,
        status = 'SETTLED'
    WHERE claim_id = p_claim_id;

    -- Insert audit log
    INSERT INTO CLAIM_AUDIT_LOG (log_id, claim_id, action, changed_by, action_timestamp)
    VALUES (
        nextval('claim_audit_seq'),
        p_claim_id,
        'SP_PROCESSED_PAYOUT_' || v_net_approved,
        'SYSTEM_SP',
        CURRENT_TIMESTAMP
    );
END;
$$;
