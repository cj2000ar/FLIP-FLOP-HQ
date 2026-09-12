-- Migration 0001: Baseline
-- Initial schema for FlipFlop HQ
-- This migration records the baseline state before device-bound auth additions

-- Baseline migrations table (if not already present from pre-migration era)
CREATE SEQUENCE IF NOT EXISTS migrations_id_seq;
CREATE TABLE IF NOT EXISTS migrations (
    id INTEGER PRIMARY KEY DEFAULT nextval('migrations_id_seq'),
    migration_number INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'APPLIED',
    checksum TEXT NOT NULL
);

-- NOTE: Migration 0001 is a marker-only migration.
-- It documents that the database has reached a state where migrations are tracked.
-- No additional tables are created here; the database is assumed to have pre-existing data.
-- Rollback of 0001 (via 0001_rollback.sql) is a no-op for backward compatibility.
