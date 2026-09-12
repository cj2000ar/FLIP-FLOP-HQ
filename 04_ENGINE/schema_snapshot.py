"""
Schema Snapshot for FlipFlop HQ
Captures current database schema to JSON for comparison and validation
"""

import json
import logging
import duckdb
from typing import Dict, List, Any
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class SchemaSnapshot:
    """Captures and serializes database schema"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def capture_schema(self) -> Dict[str, Any]:
        """Capture current schema from database"""
        try:
            conn = duckdb.connect(self.db_path)

            schema = {
                'captured_at': datetime.utcnow().isoformat(),
                'database': self.db_path,
                'tables': self._capture_tables(conn),
                'indexes': self._capture_indexes(conn),
                'constraints': self._capture_constraints(conn),
                'views': self._capture_views(conn)
            }

            # Add checksum
            schema['checksum'] = self._compute_schema_checksum(schema)

            conn.close()
            return schema

        except Exception as e:
            logger.error(f"Failed to capture schema: {e}")
            raise

    def _capture_tables(self, conn) -> List[Dict[str, Any]]:
        """Capture all tables and columns"""
        try:
            results = conn.execute("""
                SELECT table_name, column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                ORDER BY table_name, ordinal_position
            """).fetchall()

            tables = {}
            for row in results:
                table_name, col_name, data_type, nullable, default = row
                if table_name not in tables:
                    tables[table_name] = {
                        'name': table_name,
                        'columns': []
                    }

                tables[table_name]['columns'].append({
                    'name': col_name,
                    'type': data_type,
                    'nullable': nullable,
                    'default': default
                })

            return list(tables.values())

        except Exception as e:
            logger.error(f"Failed to capture tables: {e}")
            return []

    def _capture_indexes(self, conn) -> List[Dict[str, Any]]:
        """Capture all indexes"""
        try:
            results = conn.execute("""
                SELECT index_name, table_name, column_names, is_unique, is_primary
                FROM duckdb_indexes()
            """).fetchall()

            indexes = []
            for row in results:
                index_name, table_name, columns, is_unique, is_primary = row
                indexes.append({
                    'name': index_name,
                    'table': table_name,
                    'columns': columns if isinstance(columns, list) else [columns],
                    'unique': is_unique,
                    'primary': is_primary
                })

            return indexes

        except Exception as e:
            logger.error(f"Failed to capture indexes: {e}")
            return []

    def _capture_constraints(self, conn) -> List[Dict[str, Any]]:
        """Capture primary keys and foreign keys"""
        try:
            constraints = []

            # Primary keys
            pk_results = conn.execute("""
                SELECT table_name, column_name
                FROM information_schema.key_column_usage
                WHERE constraint_type = 'PRIMARY KEY'
            """).fetchall()

            for table_name, column_name in pk_results:
                constraints.append({
                    'type': 'PRIMARY_KEY',
                    'table': table_name,
                    'columns': [column_name]
                })

            # Foreign keys
            fk_results = conn.execute("""
                SELECT constraint_name, table_name, column_name,
                       referenced_table_name, referenced_column_name
                FROM information_schema.referential_constraints
            """).fetchall()

            for constraint_name, table_name, column_name, ref_table, ref_column in fk_results:
                constraints.append({
                    'type': 'FOREIGN_KEY',
                    'name': constraint_name,
                    'table': table_name,
                    'column': column_name,
                    'references': {
                        'table': ref_table,
                        'column': ref_column
                    }
                })

            return constraints

        except Exception as e:
            logger.error(f"Failed to capture constraints: {e}")
            return []

    def _capture_views(self, conn) -> List[Dict[str, Any]]:
        """Capture all views"""
        try:
            results = conn.execute("""
                SELECT table_name, view_definition
                FROM information_schema.views
            """).fetchall()

            views = []
            for table_name, view_def in results:
                views.append({
                    'name': table_name,
                    'definition': view_def
                })

            return views

        except Exception as e:
            logger.error(f"Failed to capture views: {e}")
            return []

    def _compute_schema_checksum(self, schema: Dict) -> str:
        """Compute checksum of schema (excluding captured_at and checksum fields)"""
        schema_copy = dict(schema)
        schema_copy.pop('captured_at', None)
        schema_copy.pop('checksum', None)

        schema_json = json.dumps(schema_copy, sort_keys=True, default=str)
        return hashlib.sha256(schema_json.encode()).hexdigest()

    def save_snapshot(self, schema: Dict, file_path: str) -> bool:
        """Save schema snapshot to JSON file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(schema, f, indent=2, default=str)

            logger.info(f"Schema snapshot saved: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return False

    def load_snapshot(self, file_path: str) -> Dict[str, Any]:
        """Load schema snapshot from JSON file"""
        try:
            with open(file_path, 'r') as f:
                schema = json.load(f)

            logger.info(f"Schema snapshot loaded: {file_path}")
            return schema

        except Exception as e:
            logger.error(f"Failed to load snapshot: {e}")
            return {}


class SchemaValidator:
    """Validates database schema against expected schema"""

    @staticmethod
    def validate_tables(actual: Dict[str, Any], expected: Dict[str, Any]) -> List[str]:
        """Validate tables exist and have correct columns"""
        errors = []

        expected_tables = {t['name']: t for t in expected.get('tables', [])}
        actual_tables = {t['name']: t for t in actual.get('tables', [])}

        # Check missing tables
        for table_name in expected_tables:
            if table_name not in actual_tables:
                errors.append(f"Missing table: {table_name}")

        # Check extra tables
        for table_name in actual_tables:
            if table_name not in expected_tables:
                errors.append(f"Extra table: {table_name}")

        # Check columns
        for table_name, expected_table in expected_tables.items():
            if table_name in actual_tables:
                expected_cols = {c['name']: c for c in expected_table.get('columns', [])}
                actual_cols = {c['name']: c for c in actual_tables[table_name].get('columns', [])}

                for col_name in expected_cols:
                    if col_name not in actual_cols:
                        errors.append(f"Missing column: {table_name}.{col_name}")

                for col_name in actual_cols:
                    if col_name not in expected_cols:
                        errors.append(f"Extra column: {table_name}.{col_name}")

        return errors

    @staticmethod
    def validate_schema(actual: Dict[str, Any], expected: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate actual schema matches expected"""
        errors = []

        # Validate tables
        errors.extend(SchemaValidator.validate_tables(actual, expected))

        # Validate indexes
        expected_indexes = {idx['name']: idx for idx in expected.get('indexes', [])}
        actual_indexes = {idx['name']: idx for idx in actual.get('indexes', [])}

        for idx_name in expected_indexes:
            if idx_name not in actual_indexes:
                errors.append(f"Missing index: {idx_name}")

        # Validate constraints
        expected_constraints = expected.get('constraints', [])
        actual_constraints = actual.get('constraints', [])

        if len(expected_constraints) != len(actual_constraints):
            errors.append(f"Constraint count mismatch: expected {len(expected_constraints)}, got {len(actual_constraints)}")

        return len(errors) == 0, errors
