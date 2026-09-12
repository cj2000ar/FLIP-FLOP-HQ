"""
Schema Definitions for FlipFlop HQ Migrations
Define expected schema as Python code (migrations-as-code)
"""


# Migration 0001: Baseline (migrations tracking table only)
SCHEMA_0001 = {
    'version': 1,
    'name': 'baseline',
    'tables': [
        {
            'name': 'migrations',
            'columns': [
                {'name': 'id', 'type': 'INTEGER', 'nullable': False},
                {'name': 'migration_number', 'type': 'INTEGER', 'nullable': False},
                {'name': 'name', 'type': 'TEXT', 'nullable': False},
                {'name': 'applied_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'status', 'type': 'TEXT', 'nullable': False},
                {'name': 'checksum', 'type': 'TEXT', 'nullable': False}
            ],
            'constraints': [
                {'type': 'PRIMARY_KEY', 'columns': ['id']},
                {'type': 'UNIQUE', 'columns': ['migration_number']}
            ]
        }
    ],
    'indexes': []
}

# Migration 0002: Device-Bound Auth (P3)
SCHEMA_0002 = {
    'version': 2,
    'name': 'device_bound_auth',
    'tables': [
        {
            'name': 'owner_credentials',
            'columns': [
                {'name': 'owner_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'password_hash', 'type': 'TEXT', 'nullable': False},
                {'name': 'password_set_at', 'type': 'TIMESTAMP', 'nullable': True},
                {'name': 'password_expires_at', 'type': 'TIMESTAMP', 'nullable': True},
                {'name': 'mfa_secret', 'type': 'TEXT', 'nullable': False},
                {'name': 'mfa_secret_set_at', 'type': 'TIMESTAMP', 'nullable': True},
                {'name': 'mfa_secret_expires_at', 'type': 'TIMESTAMP', 'nullable': True},
                {'name': 'created_at', 'type': 'TIMESTAMP', 'nullable': False}
            ]
        },
        {
            'name': 'device_registrations',
            'columns': [
                {'name': 'device_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'owner_id', 'type': 'TEXT', 'nullable': False},
                {'name': 'device_fingerprint', 'type': 'TEXT', 'nullable': False},
                {'name': 'device_type', 'type': 'TEXT', 'nullable': True},
                {'name': 'os_name', 'type': 'TEXT', 'nullable': True},
                {'name': 'browser_name', 'type': 'TEXT', 'nullable': True},
                {'name': 'last_ip_address', 'type': 'TEXT', 'nullable': True},
                {'name': 'last_seen_at', 'type': 'TIMESTAMP', 'nullable': True},
                {'name': 'registered_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'is_primary', 'type': 'BOOLEAN', 'nullable': False},
                {'name': 'is_active', 'type': 'BOOLEAN', 'nullable': False}
            ],
            'constraints': [
                {'type': 'FOREIGN_KEY', 'columns': ['owner_id'], 'references': {'table': 'owner_credentials', 'column': 'owner_id'}},
                {'type': 'UNIQUE', 'columns': ['device_fingerprint']},
                {'type': 'UNIQUE', 'columns': ['owner_id', 'device_fingerprint']}
            ]
        },
        {
            'name': 'credential_rotations',
            'columns': [
                {'name': 'rotation_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'owner_id', 'type': 'TEXT', 'nullable': False},
                {'name': 'rotation_type', 'type': 'TEXT', 'nullable': False},
                {'name': 'old_hash_prefix', 'type': 'TEXT', 'nullable': True},
                {'name': 'new_hash_prefix', 'type': 'TEXT', 'nullable': True},
                {'name': 'rotated_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'rotated_by', 'type': 'TEXT', 'nullable': True},
                {'name': 'reason', 'type': 'TEXT', 'nullable': True},
                {'name': 'device_id', 'type': 'TEXT', 'nullable': True},
                {'name': 'ip_address', 'type': 'TEXT', 'nullable': True}
            ],
            'constraints': [
                {'type': 'FOREIGN_KEY', 'columns': ['owner_id'], 'references': {'table': 'owner_credentials', 'column': 'owner_id'}}
            ]
        },
        {
            'name': 'recovery_codes',
            'columns': [
                {'name': 'recovery_code_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'owner_id', 'type': 'TEXT', 'nullable': False},
                {'name': 'code_hash', 'type': 'TEXT', 'nullable': False},
                {'name': 'code_sequence', 'type': 'INTEGER', 'nullable': True},
                {'name': 'generated_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'used_at', 'type': 'TIMESTAMP', 'nullable': True},
                {'name': 'used_by_device_id', 'type': 'TEXT', 'nullable': True},
                {'name': 'used_by_ip_address', 'type': 'TEXT', 'nullable': True},
                {'name': 'expires_at', 'type': 'TIMESTAMP', 'nullable': True}
            ],
            'constraints': [
                {'type': 'FOREIGN_KEY', 'columns': ['owner_id'], 'references': {'table': 'owner_credentials', 'column': 'owner_id'}},
                {'type': 'UNIQUE', 'columns': ['code_hash']}
            ]
        },
        {
            'name': 'auth_sessions',
            'columns': [
                {'name': 'session_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'owner_id', 'type': 'TEXT', 'nullable': False},
                {'name': 'device_id', 'type': 'TEXT', 'nullable': False},
                {'name': 'session_token_hash', 'type': 'TEXT', 'nullable': False},
                {'name': 'authenticated_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'expires_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'last_activity_at', 'type': 'TIMESTAMP', 'nullable': True},
                {'name': 'ip_address', 'type': 'TEXT', 'nullable': True},
                {'name': 'is_active', 'type': 'BOOLEAN', 'nullable': False}
            ],
            'constraints': [
                {'type': 'FOREIGN_KEY', 'columns': ['owner_id'], 'references': {'table': 'owner_credentials', 'column': 'owner_id'}},
                {'type': 'FOREIGN_KEY', 'columns': ['device_id'], 'references': {'table': 'device_registrations', 'column': 'device_id'}},
                {'type': 'UNIQUE', 'columns': ['session_token_hash']}
            ]
        },
        {
            'name': 'auth_audit_log',
            'columns': [
                {'name': 'log_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'event_type', 'type': 'TEXT', 'nullable': False},
                {'name': 'owner_id', 'type': 'TEXT', 'nullable': True},
                {'name': 'device_id', 'type': 'TEXT', 'nullable': True},
                {'name': 'ip_address', 'type': 'TEXT', 'nullable': True},
                {'name': 'status', 'type': 'TEXT', 'nullable': True},
                {'name': 'reason', 'type': 'TEXT', 'nullable': True},
                {'name': 'event_at', 'type': 'TIMESTAMP', 'nullable': False}
            ],
            'constraints': [
                {'type': 'FOREIGN_KEY', 'columns': ['owner_id'], 'references': {'table': 'owner_credentials', 'column': 'owner_id'}}
            ]
        }
    ],
    'indexes': [
        {'name': 'idx_device_owner', 'table': 'device_registrations', 'columns': ['owner_id']},
        {'name': 'idx_device_fingerprint', 'table': 'device_registrations', 'columns': ['device_fingerprint']},
        {'name': 'idx_rotation_owner', 'table': 'credential_rotations', 'columns': ['owner_id']},
        {'name': 'idx_rotation_date', 'table': 'credential_rotations', 'columns': ['rotated_at']},
        {'name': 'idx_recovery_owner', 'table': 'recovery_codes', 'columns': ['owner_id']},
        {'name': 'idx_recovery_used', 'table': 'recovery_codes', 'columns': ['used_at']},
        {'name': 'idx_session_owner', 'table': 'auth_sessions', 'columns': ['owner_id']},
        {'name': 'idx_session_device', 'table': 'auth_sessions', 'columns': ['device_id']},
        {'name': 'idx_session_active', 'table': 'auth_sessions', 'columns': ['is_active', 'expires_at']},
        {'name': 'idx_audit_owner', 'table': 'auth_audit_log', 'columns': ['owner_id']},
        {'name': 'idx_audit_type', 'table': 'auth_audit_log', 'columns': ['event_type']},
        {'name': 'idx_audit_date', 'table': 'auth_audit_log', 'columns': ['event_at']}
    ]
}

# Migration 0003: Evidence Retention (P4)
SCHEMA_0003 = {
    'version': 3,
    'name': 'evidence_retention',
    'tables': [
        {
            'name': 'evidence_ledger',
            'columns': [
                {'name': 'batch_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'batch_sequence', 'type': 'INTEGER', 'nullable': False},
                {'name': 'start_log_id', 'type': 'TEXT', 'nullable': False},
                {'name': 'end_log_id', 'type': 'TEXT', 'nullable': False},
                {'name': 'log_count', 'type': 'INTEGER', 'nullable': False},
                {'name': 'batch_hash', 'type': 'TEXT', 'nullable': False},
                {'name': 'previous_batch_hash', 'type': 'TEXT', 'nullable': True},
                {'name': 'sealed_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'signature', 'type': 'TEXT', 'nullable': True}
            ],
            'constraints': [
                {'type': 'UNIQUE', 'columns': ['batch_sequence']},
                {'type': 'UNIQUE', 'columns': ['batch_hash']},
                {'type': 'FOREIGN_KEY', 'columns': ['start_log_id'], 'references': {'table': 'auth_audit_log', 'column': 'log_id'}},
                {'type': 'FOREIGN_KEY', 'columns': ['end_log_id'], 'references': {'table': 'auth_audit_log', 'column': 'log_id'}}
            ]
        },
        {
            'name': 'evidence_archival',
            'columns': [
                {'name': 'archive_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'batch_id', 'type': 'TEXT', 'nullable': False},
                {'name': 'archive_hash', 'type': 'TEXT', 'nullable': False},
                {'name': 'archived_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'archive_location', 'type': 'TEXT', 'nullable': True},
                {'name': 'compression_type', 'type': 'TEXT', 'nullable': True},
                {'name': 'is_verified', 'type': 'BOOLEAN', 'nullable': False},
                {'name': 'verified_at', 'type': 'TIMESTAMP', 'nullable': True}
            ],
            'constraints': [
                {'type': 'FOREIGN_KEY', 'columns': ['batch_id'], 'references': {'table': 'evidence_ledger', 'column': 'batch_id'}},
                {'type': 'UNIQUE', 'columns': ['batch_id']},
                {'type': 'UNIQUE', 'columns': ['archive_hash']}
            ]
        },
        {
            'name': 'retention_policies',
            'columns': [
                {'name': 'policy_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'event_type', 'type': 'TEXT', 'nullable': False},
                {'name': 'retention_days', 'type': 'INTEGER', 'nullable': False},
                {'name': 'archive_after_days', 'type': 'INTEGER', 'nullable': True},
                {'name': 'deletion_allowed', 'type': 'BOOLEAN', 'nullable': False},
                {'name': 'compliance_hold', 'type': 'BOOLEAN', 'nullable': False},
                {'name': 'created_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'updated_at', 'type': 'TIMESTAMP', 'nullable': False}
            ],
            'constraints': [
                {'type': 'UNIQUE', 'columns': ['event_type']}
            ]
        },
        {
            'name': 'evidence_batch_status',
            'columns': [
                {'name': 'batch_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'status', 'type': 'TEXT', 'nullable': False},
                {'name': 'status_changed_at', 'type': 'TIMESTAMP', 'nullable': False}
            ],
            'constraints': [
                {'type': 'FOREIGN_KEY', 'columns': ['batch_id'], 'references': {'table': 'evidence_ledger', 'column': 'batch_id'}}
            ]
        },
        {
            'name': 'evidence_verification_log',
            'columns': [
                {'name': 'verification_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'batch_id', 'type': 'TEXT', 'nullable': False},
                {'name': 'verification_type', 'type': 'TEXT', 'nullable': True},
                {'name': 'verified_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'is_valid', 'type': 'BOOLEAN', 'nullable': True},
                {'name': 'failure_reason', 'type': 'TEXT', 'nullable': True}
            ],
            'constraints': [
                {'type': 'FOREIGN_KEY', 'columns': ['batch_id'], 'references': {'table': 'evidence_ledger', 'column': 'batch_id'}}
            ]
        }
    ]
}

# Migration 0004: Migration Ledger (P5)
SCHEMA_0004 = {
    'version': 4,
    'name': 'migration_ledger',
    'tables': [
        {
            'name': 'migration_ledger',
            'columns': [
                {'name': 'ledger_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'migration_number', 'type': 'INTEGER', 'nullable': False},
                {'name': 'action', 'type': 'TEXT', 'nullable': False},
                {'name': 'status', 'type': 'TEXT', 'nullable': False},
                {'name': 'attempted_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'completed_at', 'type': 'TIMESTAMP', 'nullable': True},
                {'name': 'reason', 'type': 'TEXT', 'nullable': True},
                {'name': 'checksum', 'type': 'TEXT', 'nullable': True},
                {'name': 'error_message', 'type': 'TEXT', 'nullable': True}
            ]
        },
        {
            'name': 'migration_state',
            'columns': [
                {'name': 'migration_number', 'type': 'INTEGER', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'current_status', 'type': 'TEXT', 'nullable': False},
                {'name': 'current_checksum', 'type': 'TEXT', 'nullable': True},
                {'name': 'applied_at', 'type': 'TIMESTAMP', 'nullable': True},
                {'name': 'rolled_back_at', 'type': 'TIMESTAMP', 'nullable': True},
                {'name': 'failed_at', 'type': 'TIMESTAMP', 'nullable': True},
                {'name': 'failure_reason', 'type': 'TEXT', 'nullable': True},
                {'name': 'locked', 'type': 'BOOLEAN', 'nullable': False},
                {'name': 'locked_by', 'type': 'TEXT', 'nullable': True},
                {'name': 'locked_at', 'type': 'TIMESTAMP', 'nullable': True},
                {'name': 'updated_at', 'type': 'TIMESTAMP', 'nullable': False}
            ]
        },
        {
            'name': 'migration_dependencies',
            'columns': [
                {'name': 'dependency_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'migration_number', 'type': 'INTEGER', 'nullable': False},
                {'name': 'depends_on_migration', 'type': 'INTEGER', 'nullable': False}
            ],
            'constraints': [
                {'type': 'FOREIGN_KEY', 'columns': ['migration_number'], 'references': {'table': 'migration_state', 'column': 'migration_number'}},
                {'type': 'UNIQUE', 'columns': ['migration_number', 'depends_on_migration']}
            ]
        },
        {
            'name': 'migration_checksums',
            'columns': [
                {'name': 'checksum_id', 'type': 'TEXT', 'nullable': False, 'key': 'PRIMARY'},
                {'name': 'migration_number', 'type': 'INTEGER', 'nullable': False},
                {'name': 'checksum', 'type': 'TEXT', 'nullable': False},
                {'name': 'recorded_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'is_current', 'type': 'BOOLEAN', 'nullable': False}
            ],
            'constraints': [
                {'type': 'UNIQUE', 'columns': ['checksum']}
            ]
        }
    ]
}

# Export all schemas
ALL_SCHEMAS = [SCHEMA_0001, SCHEMA_0002, SCHEMA_0003, SCHEMA_0004]
