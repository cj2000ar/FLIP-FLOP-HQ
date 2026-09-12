-- Rollback for Migration 0003: Evidence Retention
-- Drops all evidence retention tables safely

DROP TABLE IF EXISTS evidence_verification_log;
DROP TABLE IF EXISTS evidence_batch_status;
DROP TABLE IF EXISTS evidence_archival;
DROP TABLE IF EXISTS evidence_ledger;
DROP TABLE IF EXISTS retention_policies;
