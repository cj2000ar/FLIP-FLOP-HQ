-- Migration 0002: Device-Bound Auth + Credential Rotation + Root Recovery
-- Adds device binding, credential rotation, and root recovery codes
-- Backwards compatible: no existing tables modified, only new tables added

-- Track migrations applied to this database
CREATE TABLE IF NOT EXISTS migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_number INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'APPLIED', -- APPLIED | ROLLED_BACK
    checksum TEXT NOT NULL -- SHA256 of migration SQL for integrity
);

-- Owner credentials (persistent store)
CREATE TABLE IF NOT EXISTS owner_credentials (
    owner_id TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL, -- PBKDF2(SHA256, salt, 100000 iterations)
    password_set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    password_expires_at TIMESTAMP, -- NULL = no expiration, or 90 days from set_at
    mfa_secret TEXT NOT NULL, -- Base32-encoded TOTP secret
    mfa_secret_set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mfa_secret_expires_at TIMESTAMP, -- 180 days from set_at
    mfa_secret_backup_encrypted TEXT, -- Encrypted backup of secret for recovery
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Device fingerprints and registrations
CREATE TABLE IF NOT EXISTS device_registrations (
    device_id TEXT PRIMARY KEY, -- UUID
    owner_id TEXT NOT NULL,
    device_name TEXT, -- "My MacBook", "Windows PC", etc
    device_fingerprint TEXT NOT NULL UNIQUE, -- Hash of OS+HW ID+browser combo
    device_type TEXT, -- "desktop", "mobile", "tablet"
    os_name TEXT, -- "macOS", "Windows 11", "iOS"
    browser_name TEXT, -- "Chrome", "Safari", "Firefox"
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
    rotation_id TEXT PRIMARY KEY, -- UUID
    owner_id TEXT NOT NULL,
    rotation_type TEXT NOT NULL, -- "PASSWORD" | "MFA_SECRET" | "BOTH"
    old_hash_prefix TEXT, -- First 16 chars of old hash (for identification, not verification)
    new_hash_prefix TEXT, -- First 16 chars of new hash
    rotated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rotated_by TEXT, -- "OWNER" | "AUTOMATED" | "RECOVERY"
    reason TEXT, -- "SCHEDULED" | "FORCED" | "RECOVERY_CODE_USED"
    device_id TEXT, -- Device used to initiate rotation
    ip_address TEXT,
    FOREIGN KEY(owner_id) REFERENCES owner_credentials(owner_id)
);

-- Recovery codes for root recovery
CREATE TABLE IF NOT EXISTS recovery_codes (
    recovery_code_id TEXT PRIMARY KEY, -- UUID
    owner_id TEXT NOT NULL,
    code_hash TEXT NOT NULL UNIQUE, -- PBKDF2 hash of code
    code_sequence INTEGER, -- 1-10 (ten codes generated at setup)
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP, -- NULL = unused
    used_by_device_id TEXT, -- Device that used this code
    used_by_ip_address TEXT,
    expires_at TIMESTAMP, -- Optional: auto-expire after 1 year
    FOREIGN KEY(owner_id) REFERENCES owner_credentials(owner_id)
);

-- Authentication sessions (persistent, for audit trail)
CREATE TABLE IF NOT EXISTS auth_sessions (
    session_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    session_token_hash TEXT NOT NULL UNIQUE, -- Hash of token for storage
    authenticated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL, -- 8 hours from auth
    last_activity_at TIMESTAMP,
    ip_address TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY(owner_id) REFERENCES owner_credentials(owner_id),
    FOREIGN KEY(device_id) REFERENCES device_registrations(device_id)
);

-- Authentication audit log (immutable)
CREATE TABLE IF NOT EXISTS auth_audit_log (
    log_id TEXT PRIMARY KEY, -- UUID
    event_type TEXT NOT NULL, -- "LOGIN_SUCCESS" | "LOGIN_FAILED" | "LOGOUT" | "MFA_FAILED" | "DEVICE_NEW" | "PASSWORD_ROTATED" | "RECOVERY_CODE_USED"
    owner_id TEXT,
    device_id TEXT,
    ip_address TEXT,
    status TEXT, -- "SUCCESS" | "FAILED"
    reason TEXT, -- "bad_password" | "bad_mfa" | "device_unregistered" | "recovery_code_invalid"
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

-- Constraints & Triggers (if DuckDB supports)
-- On device_registrations: only 1 primary device per owner
-- On recovery_codes: only 1 unused code per sequence per owner
-- On auth_sessions: auto-cleanup expired sessions

-- Migration marker (inserted at END of this migration)
-- INSERT INTO migrations (migration_number, name, checksum, status)
-- VALUES (2, 'device_bound_auth', '<SHA256_OF_THIS_FILE>', 'APPLIED');
