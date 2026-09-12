-- Migration 0002: Device-Bound Authentication
-- Adds device binding, credential rotation, recovery codes, and persistent session tracking

-- Owner credentials (persistent store)
CREATE TABLE IF NOT EXISTS owner_credentials (
    owner_id TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    password_set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    password_expires_at TIMESTAMP,
    mfa_secret TEXT NOT NULL,
    mfa_secret_set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mfa_secret_expires_at TIMESTAMP,
    mfa_secret_backup_encrypted TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Device fingerprints and registrations
CREATE TABLE IF NOT EXISTS device_registrations (
    device_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    device_name TEXT,
    device_fingerprint TEXT NOT NULL UNIQUE,
    device_type TEXT,
    os_name TEXT,
    browser_name TEXT,
    last_ip_address TEXT,
    last_seen_at TIMESTAMP,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_primary BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY(owner_id) REFERENCES owner_credentials(owner_id),
    UNIQUE(owner_id, device_fingerprint)
);

-- Credential rotation history
CREATE TABLE IF NOT EXISTS credential_rotations (
    rotation_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    rotation_type TEXT NOT NULL,
    old_hash_prefix TEXT,
    new_hash_prefix TEXT,
    rotated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rotated_by TEXT,
    reason TEXT,
    device_id TEXT,
    ip_address TEXT,
    FOREIGN KEY(owner_id) REFERENCES owner_credentials(owner_id)
);

-- Recovery codes for root recovery
CREATE TABLE IF NOT EXISTS recovery_codes (
    recovery_code_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    code_hash TEXT NOT NULL UNIQUE,
    code_sequence INTEGER,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP,
    used_by_device_id TEXT,
    used_by_ip_address TEXT,
    expires_at TIMESTAMP,
    FOREIGN KEY(owner_id) REFERENCES owner_credentials(owner_id)
);

-- Authentication sessions (persistent, for audit trail)
CREATE TABLE IF NOT EXISTS auth_sessions (
    session_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    session_token_hash TEXT NOT NULL UNIQUE,
    authenticated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity_at TIMESTAMP,
    ip_address TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY(owner_id) REFERENCES owner_credentials(owner_id),
    FOREIGN KEY(device_id) REFERENCES device_registrations(device_id)
);

-- Authentication audit log (immutable)
CREATE TABLE IF NOT EXISTS auth_audit_log (
    log_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    owner_id TEXT,
    device_id TEXT,
    ip_address TEXT,
    status TEXT,
    reason TEXT,
    event_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(owner_id) REFERENCES owner_credentials(owner_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_device_owner ON device_registrations(owner_id);
CREATE INDEX IF NOT EXISTS idx_device_fingerprint ON device_registrations(device_fingerprint);
CREATE INDEX IF NOT EXISTS idx_rotation_owner ON credential_rotations(owner_id);
CREATE INDEX IF NOT EXISTS idx_rotation_date ON credential_rotations(rotated_at);
CREATE INDEX IF NOT EXISTS idx_recovery_owner ON recovery_codes(owner_id);
CREATE INDEX IF NOT EXISTS idx_recovery_used ON recovery_codes(used_at);
CREATE INDEX IF NOT EXISTS idx_session_owner ON auth_sessions(owner_id);
CREATE INDEX IF NOT EXISTS idx_session_device ON auth_sessions(device_id);
CREATE INDEX IF NOT EXISTS idx_session_active ON auth_sessions(is_active, expires_at);
CREATE INDEX IF NOT EXISTS idx_audit_owner ON auth_audit_log(owner_id);
CREATE INDEX IF NOT EXISTS idx_audit_type ON auth_audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_date ON auth_audit_log(event_at);
