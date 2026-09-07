# SQLite → PostgreSQL Migration Guide

## Why Migrate

**SQLite Limitations (current):**
- Single writer (concurrency issues)
- File-based locking
- Limited to local storage
- No replication
- Poor performance at scale (>1GB)

**PostgreSQL Advantages:**
- ACID transactions
- Full concurrency support
- Network accessible
- Streaming replication + backups
- JSON support (flexible schema)
- Full-text search
- Point-in-time recovery

## Migration Strategy

### Phase 1: Prepare (2 hours)

1. **Create PostgreSQL database + schema**
2. **Add SQLite→PostgreSQL migration code**
3. **Test migration on dev data**
4. **Validate data integrity**

### Phase 2: Execute (1 hour)

1. **Stop API (read-only maintenance)**
2. **Dump SQLite data**
3. **Load into PostgreSQL**
4. **Verify counts + checksums**
5. **Update connection strings**
6. **Restart API (now on PostgreSQL)**

### Phase 3: Cleanup (30 min)

1. **Archive SQLite backup (S3)**
2. **Setup PostgreSQL replication**
3. **Configure automated backups**

## Implementation

### Step 1: PostgreSQL Setup

```bash
# Docker
docker run -d \
  --name flipflop-db \
  -e POSTGRES_PASSWORD=secure_password \
  -e POSTGRES_DB=flipflop \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine

# Or systemd (production)
sudo systemctl start postgresql
sudo -u postgres createdb flipflop
sudo -u postgres createuser flipflop
```

### Step 2: Schema Definition

Create `schema.sql`:

```sql
-- Experiments table
CREATE TABLE experiments (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    hypothesis TEXT,
    parameters TEXT,
    dataset_role VARCHAR(50),
    runs INTEGER DEFAULT 0,
    status VARCHAR(50),
    result VARCHAR(50),
    rejection_reason VARCHAR(255),
    next_gate VARCHAR(255),
    event_time BIGINT,
    knowledge_time BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vault items table
CREATE TABLE vault_items (
    id VARCHAR(100) PRIMARY KEY,
    kind VARCHAR(20),
    title VARCHAR(255),
    source VARCHAR(255),
    extraction VARCHAR(50),
    evidence VARCHAR(50),
    family TEXT[], -- PostgreSQL array
    dna TEXT,
    data_needs TEXT[],
    event_time BIGINT,
    knowledge_time BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Queue items table
CREATE TABLE queue_items (
    id VARCHAR(100) PRIMARY KEY,
    title VARCHAR(255),
    state VARCHAR(50),
    why TEXT,
    event_time BIGINT,
    knowledge_time BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Token store (replaces in-memory dict)
CREATE TABLE tokens (
    token_id VARCHAR(36) PRIMARY KEY,
    machine_id VARCHAR(255) NOT NULL,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_tokens_machine_id ON tokens(machine_id);
CREATE INDEX idx_tokens_expires_at ON tokens(expires_at);

-- Audit log (structured JSON)
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    machine_id VARCHAR(255),
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INTEGER,
    request_id VARCHAR(10),
    duration_ms FLOAT,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_machine_id ON audit_log(machine_id);
```

### Step 3: Migration Code

Create `migrate_to_postgres.py`:

```python
import sqlite3
import psycopg2
import json
from datetime import datetime

def migrate_data(sqlite_path: str, postgres_conn_str: str):
    """Migrate data from SQLite to PostgreSQL"""
    
    # Connect to both databases
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg2.connect(postgres_conn_str)
    
    try:
        # Migrate tables
        migrate_experiments(sqlite_conn, postgres_conn)
        migrate_vault_items(sqlite_conn, postgres_conn)
        migrate_queue_items(sqlite_conn, postgres_conn)
        
        # Verify
        verify_migration(sqlite_conn, postgres_conn)
        
        print("✓ Migration successful!")
        postgres_conn.commit()
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        postgres_conn.rollback()
        return False
        
    finally:
        sqlite_conn.close()
        postgres_conn.close()

def migrate_experiments(sqlite_conn, postgres_conn):
    """Migrate experiments table"""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM experiments")
    
    pg_cursor = postgres_conn.cursor()
    for row in cursor.fetchall():
        pg_cursor.execute("""
            INSERT INTO experiments (id, name, hypothesis, parameters, 
                                   dataset_role, runs, status, result, 
                                   rejection_reason, next_gate, event_time, knowledge_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            row['id'], row['name'], row['hypothesis'], row['parameters'],
            row['dataset_role'], row['runs'], row['status'], row['result'],
            row['rejection_reason'], row['next_gate'], row['event_time'], row['knowledge_time']
        ))
    
    postgres_conn.commit()
    print(f"✓ Migrated {pg_cursor.rowcount} experiments")

def verify_migration(sqlite_conn, postgres_conn):
    """Verify row counts match"""
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = postgres_conn.cursor()
    
    for table in ['experiments', 'vault_items', 'queue_items']:
        sqlite_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        sqlite_count = sqlite_cursor.fetchone()['count']
        
        pg_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        pg_count = pg_cursor.fetchone()[0]
        
        if sqlite_count != pg_count:
            raise Exception(f"Row count mismatch for {table}: {sqlite_count} vs {pg_count}")
        
        print(f"✓ {table}: {pg_count} rows")
```

### Step 4: Update API for PostgreSQL

**Changes to `private_read_api.py`:**

```python
import psycopg2
from psycopg2.pool import SimpleConnectionPool
import os

# Database connection pool
db_pool = SimpleConnectionPool(
    1, 20,  # min/max connections
    dsn=os.getenv('DATABASE_URL', 'postgresql://flipflop:password@localhost/flipflop')
)

# Replace in-memory token store with database
class TokenStore:
    def __init__(self, pool):
        self.pool = pool
    
    def store_token(self, token: str, machine_id: str, ttl_seconds: int):
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            cursor.execute("""
                INSERT INTO tokens (token_id, machine_id, expires_at)
                VALUES (%s, %s, %s)
            """, (token, machine_id, expires_at))
            conn.commit()
        finally:
            self.pool.putconn(conn)
    
    def validate_token(self, token: str, machine_id: str) -> bool:
        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM tokens 
                WHERE token_id = %s AND machine_id = %s 
                  AND expires_at > NOW() AND NOT is_revoked
            """, (token, machine_id))
            return cursor.fetchone() is not None
        finally:
            self.pool.putconn(conn)

token_store = TokenStore(db_pool)
```

## Execution Plan

### Timing: 2-3 hours total

| Step | Time | Action |
|------|------|--------|
| 1 | 30 min | Setup PostgreSQL, create schema |
| 2 | 30 min | Test migration on dev data |
| 3 | 10 min | Stop API, dump SQLite |
| 4 | 10 min | Load data to PostgreSQL |
| 5 | 5 min | Update connection strings |
| 6 | 5 min | Restart API, verify |
| 7 | 20 min | Setup replication + backups |

### Downtime

**Total API downtime: ~30 minutes** (dump → load → restart)

## Rollback Plan

If migration fails:

1. Stop API
2. Revert connection string to SQLite
3. Restore from pre-migration backup
4. Restart API

**Rollback time: <5 minutes**

## Post-Migration

### Enable Replication

```bash
# Hot standby for HA
pg_basebackup -h primary -D /var/lib/postgresql/replica
```

### Automated Backups

```bash
# Daily backups to S3
pg_dump flipflop | gzip | aws s3 cp - s3://backups/pg/flipflop_$(date +%Y%m%d).sql.gz
```

### Connection Pool Tuning

```ini
# postgresql.conf
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
```

## Gotchas

⚠️ **Data Types:**
- SQLite arrays → PostgreSQL arrays (TEXT[])
- JSON strings → PostgreSQL jsonb

⚠️ **Sequences:**
- Ensure BIGSERIAL sequences start high enough

⚠️ **Concurrency:**
- Test under load (concurrent writes)
- Token validation now scales

⚠️ **Timezone:**
- All timestamps UTC (enforce in code)

## Validation Checklist

- [ ] Row counts match (all tables)
- [ ] No NULL constraint violations
- [ ] Foreign keys valid (if applicable)
- [ ] Checksums match (sample data)
- [ ] API responds to requests
- [ ] Token validation works
- [ ] Audit logging persists
- [ ] Backups working
- [ ] Replication syncing

## Next Steps

1. Schedule maintenance window
2. Notify users of expected downtime
3. Run migration in test environment first
4. Execute production migration
5. Monitor for 24h post-migration
6. Archive SQLite to S3
