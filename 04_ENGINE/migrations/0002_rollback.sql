-- Rollback for Migration 0002: Device-Bound Authentication
-- Drops all tables and indexes added in 0002

-- Drop indexes first (foreign key dependencies)
DROP INDEX IF EXISTS idx_audit_date;
DROP INDEX IF EXISTS idx_audit_type;
DROP INDEX IF EXISTS idx_audit_owner;
DROP INDEX IF EXISTS idx_session_active;
DROP INDEX IF EXISTS idx_session_device;
DROP INDEX IF EXISTS idx_session_owner;
DROP INDEX IF EXISTS idx_recovery_used;
DROP INDEX IF EXISTS idx_recovery_owner;
DROP INDEX IF EXISTS idx_rotation_date;
DROP INDEX IF EXISTS idx_rotation_owner;
DROP INDEX IF EXISTS idx_device_fingerprint;
DROP INDEX IF EXISTS idx_device_owner;

-- Drop tables (in reverse dependency order)
DROP TABLE IF EXISTS auth_audit_log;
DROP TABLE IF EXISTS auth_sessions;
DROP TABLE IF EXISTS recovery_codes;
DROP TABLE IF EXISTS credential_rotations;
DROP TABLE IF EXISTS device_registrations;
DROP TABLE IF EXISTS owner_credentials;

-- NOTE: migrations table is preserved for historical tracking
