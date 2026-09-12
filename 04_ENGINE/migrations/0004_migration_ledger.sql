-- Migration 0004: Migration Ledger + State Machine
-- Adds immutable audit trail and idempotent apply support

-- Migration ledger: immutable audit trail of all apply/rollback/error attempts
CREATE TABLE IF NOT EXISTS migration_ledger (
    ledger_id TEXT PRIMARY KEY,
    migration_number INTEGER NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    reason TEXT,
    checksum TEXT,
    previous_checksum TEXT,
    error_message TEXT,
    locked_by TEXT,
    locked_at TIMESTAMP,
    released_at TIMESTAMP
);

-- Migration state: atomic current state (one row per migration)
CREATE TABLE IF NOT EXISTS migration_state (
    migration_number INTEGER PRIMARY KEY,
    current_status TEXT NOT NULL,
    current_checksum TEXT,
    applied_at TIMESTAMP,
    rolled_back_at TIMESTAMP,
    failed_at TIMESTAMP,
    failure_reason TEXT,
    locked BOOLEAN DEFAULT FALSE,
    locked_by TEXT,
    locked_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Migration dependencies: enforce sequence
CREATE TABLE IF NOT EXISTS migration_dependencies (
    dependency_id TEXT PRIMARY KEY,
    migration_number INTEGER NOT NULL,
    depends_on_migration INTEGER NOT NULL,
    -- No FK to migration_state: dependencies are declared ahead of the
    -- migration they describe (0004 declares its own dep before it is recorded),
    -- and DuckDB enforces FKs eagerly. Ordering is checked in migration_ledger.py.
    UNIQUE(migration_number, depends_on_migration)
);

-- Migration checksums: track version history
CREATE TABLE IF NOT EXISTS migration_checksums (
    checksum_id TEXT PRIMARY KEY,
    migration_number INTEGER NOT NULL,
    checksum TEXT NOT NULL UNIQUE,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_current BOOLEAN DEFAULT FALSE
);

-- Initialize default migration state for 0001-0003
INSERT OR IGNORE INTO migration_state
(migration_number, current_status, current_checksum, applied_at)
SELECT migration_number, 'APPLIED', checksum, applied_at
FROM migrations
WHERE status = 'APPLIED';

INSERT OR IGNORE INTO migration_state
(migration_number, current_status, current_checksum, rolled_back_at)
SELECT migration_number, 'ROLLED_BACK', checksum, applied_at
FROM migrations
WHERE status = 'ROLLED_BACK';

-- Set up dependencies (linear: 0002 depends on 0001, 0003 on 0002, 0004 on 0003)
INSERT OR IGNORE INTO migration_dependencies
(dependency_id, migration_number, depends_on_migration)
VALUES
    ('dep_0002_0001', 2, 1),
    ('dep_0003_0002', 3, 2),
    ('dep_0004_0003', 4, 3);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ledger_migration ON migration_ledger(migration_number);
CREATE INDEX IF NOT EXISTS idx_ledger_action ON migration_ledger(action, status);
CREATE INDEX IF NOT EXISTS idx_ledger_attempted ON migration_ledger(attempted_at);
CREATE INDEX IF NOT EXISTS idx_state_status ON migration_state(current_status);
CREATE INDEX IF NOT EXISTS idx_state_locked ON migration_state(locked, locked_at);
CREATE INDEX IF NOT EXISTS idx_checksum_migration ON migration_checksums(migration_number, is_current);
CREATE INDEX IF NOT EXISTS idx_deps_migration ON migration_dependencies(migration_number);
CREATE INDEX IF NOT EXISTS idx_deps_depends_on ON migration_dependencies(depends_on_migration);
