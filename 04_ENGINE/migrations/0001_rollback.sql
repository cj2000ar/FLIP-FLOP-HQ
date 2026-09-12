-- Rollback for Migration 0001: Baseline
-- No-op rollback: migrations table is preserved for tracking history
-- This is a marker migration, so rollback is intentionally empty

-- NOTE: Do NOT drop the migrations table on rollback.
-- The migrations table itself is part of the framework and persists across rollbacks.
-- This ensures we can always track what was applied and what was rolled back.
