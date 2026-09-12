-- Rollback for Migration 0004: Migration Ledger
-- Drops ledger tables safely

DROP TABLE IF EXISTS migration_checksums;
DROP TABLE IF EXISTS migration_dependencies;
DROP TABLE IF EXISTS migration_state;
DROP TABLE IF EXISTS migration_ledger;
