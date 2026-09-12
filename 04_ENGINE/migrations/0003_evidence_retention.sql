-- Migration 0003: Evidence Retention + Immutable Ledger
-- Adds cryptographic sealing, batch ledger, and retention policies

-- Evidence ledger: sealed batches with hash chain
CREATE TABLE IF NOT EXISTS evidence_ledger (
    batch_id TEXT PRIMARY KEY,
    batch_sequence INTEGER UNIQUE NOT NULL,
    start_log_id TEXT NOT NULL,
    end_log_id TEXT NOT NULL,
    log_count INTEGER NOT NULL,
    batch_hash TEXT NOT NULL UNIQUE,
    previous_batch_hash TEXT,
    sealed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    signature TEXT,
    FOREIGN KEY(start_log_id) REFERENCES auth_audit_log(log_id),
    FOREIGN KEY(end_log_id) REFERENCES auth_audit_log(log_id)
);

-- Evidence archival: compressed, signed batches
CREATE TABLE IF NOT EXISTS evidence_archival (
    archive_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL UNIQUE,
    archive_hash TEXT NOT NULL UNIQUE,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archive_location TEXT,
    compression_type TEXT DEFAULT 'gzip',
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    verification_hash TEXT,
    FOREIGN KEY(batch_id) REFERENCES evidence_ledger(batch_id)
);

-- Retention policies: per-event-type rules
CREATE TABLE IF NOT EXISTS retention_policies (
    policy_id TEXT PRIMARY KEY,
    event_type TEXT UNIQUE NOT NULL,
    retention_days INTEGER NOT NULL,
    archive_after_days INTEGER,
    deletion_allowed BOOLEAN DEFAULT FALSE,
    compliance_hold BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Batch status tracking
CREATE TABLE IF NOT EXISTS evidence_batch_status (
    batch_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    status_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(batch_id) REFERENCES evidence_ledger(batch_id)
);

-- Integrity verification log
CREATE TABLE IF NOT EXISTS evidence_verification_log (
    verification_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    verification_type TEXT,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN,
    failure_reason TEXT,
    FOREIGN KEY(batch_id) REFERENCES evidence_ledger(batch_id)
);

-- Default retention policies
INSERT OR IGNORE INTO retention_policies
(policy_id, event_type, retention_days, archive_after_days, deletion_allowed, compliance_hold)
VALUES
    ('policy_login', 'LOGIN', 365, 90, FALSE, FALSE),
    ('policy_logout', 'LOGOUT', 365, 90, FALSE, FALSE),
    ('policy_rotation', 'CREDENTIAL_ROTATION', 2555, 365, FALSE, TRUE),
    ('policy_recovery', 'RECOVERY_CODE_USED', 2555, 365, FALSE, TRUE),
    ('policy_device_reg', 'DEVICE_REGISTERED', 1825, 180, FALSE, TRUE),
    ('policy_mfa_fail', 'MFA_VERIFICATION_FAILED', 365, 90, FALSE, FALSE),
    ('policy_device_deact', 'DEVICE_DEACTIVATED', 1825, 180, FALSE, TRUE);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ledger_sequence ON evidence_ledger(batch_sequence);
CREATE INDEX IF NOT EXISTS idx_ledger_sealed ON evidence_ledger(sealed_at);
CREATE INDEX IF NOT EXISTS idx_ledger_hash ON evidence_ledger(batch_hash);
CREATE INDEX IF NOT EXISTS idx_archival_batch ON evidence_archival(batch_id);
CREATE INDEX IF NOT EXISTS idx_archival_verified ON evidence_archival(is_verified, verified_at);
CREATE INDEX IF NOT EXISTS idx_archival_archived ON evidence_archival(archived_at);
CREATE INDEX IF NOT EXISTS idx_policy_event ON retention_policies(event_type);
CREATE INDEX IF NOT EXISTS idx_policy_compliance ON retention_policies(compliance_hold);
CREATE INDEX IF NOT EXISTS idx_batch_status ON evidence_batch_status(status, status_changed_at);
CREATE INDEX IF NOT EXISTS idx_verification_batch ON evidence_verification_log(batch_id, verified_at);
