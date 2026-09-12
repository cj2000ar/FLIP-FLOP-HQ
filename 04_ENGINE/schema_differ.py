"""
Schema Differ for FlipFlop HQ
Generate human-readable diffs between two schemas
"""

import json
from typing import Dict, List, Any


class SchemaDiffer:
    """Generates diffs between schema versions"""

    @staticmethod
    def diff_schemas(old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate diff between two schemas"""
        diff = {
            'tables_added': [],
            'tables_removed': [],
            'tables_modified': [],
            'indexes_added': [],
            'indexes_removed': [],
            'constraints_added': [],
            'constraints_removed': []
        }

        old_tables = {t['name']: t for t in old_schema.get('tables', [])}
        new_tables = {t['name']: t for t in new_schema.get('tables', [])}

        # Find added/removed tables
        for table_name in new_tables:
            if table_name not in old_tables:
                diff['tables_added'].append(table_name)

        for table_name in old_tables:
            if table_name not in new_tables:
                diff['tables_removed'].append(table_name)

        # Find modified tables
        for table_name in set(old_tables.keys()) & set(new_tables.keys()):
            old_cols = {c['name']: c for c in old_tables[table_name].get('columns', [])}
            new_cols = {c['name']: c for c in new_tables[table_name].get('columns', [])}

            cols_added = [c for c in new_cols if c not in old_cols]
            cols_removed = [c for c in old_cols if c not in new_cols]

            if cols_added or cols_removed:
                diff['tables_modified'].append({
                    'name': table_name,
                    'columns_added': cols_added,
                    'columns_removed': cols_removed
                })

        # Find added/removed indexes
        old_indexes = {idx['name']: idx for idx in old_schema.get('indexes', [])}
        new_indexes = {idx['name']: idx for idx in new_schema.get('indexes', [])}

        for idx_name in new_indexes:
            if idx_name not in old_indexes:
                diff['indexes_added'].append(idx_name)

        for idx_name in old_indexes:
            if idx_name not in new_indexes:
                diff['indexes_removed'].append(idx_name)

        return diff

    @staticmethod
    def format_diff(diff: Dict[str, Any]) -> str:
        """Format diff as human-readable text"""
        lines = []

        lines.append("Schema Diff Report")
        lines.append("=" * 50)
        lines.append("")

        # Tables
        if diff['tables_added']:
            lines.append(f"+ ADDED {len(diff['tables_added'])} table(s):")
            for table in diff['tables_added']:
                lines.append(f"  + {table}")
            lines.append("")

        if diff['tables_removed']:
            lines.append(f"- REMOVED {len(diff['tables_removed'])} table(s):")
            for table in diff['tables_removed']:
                lines.append(f"  - {table}")
            lines.append("")

        if diff['tables_modified']:
            lines.append(f"~ MODIFIED {len(diff['tables_modified'])} table(s):")
            for mod in diff['tables_modified']:
                lines.append(f"  ~ {mod['name']}")
                for col in mod['columns_added']:
                    lines.append(f"    + {col}")
                for col in mod['columns_removed']:
                    lines.append(f"    - {col}")
            lines.append("")

        # Indexes
        if diff['indexes_added']:
            lines.append(f"+ ADDED {len(diff['indexes_added'])} index(es):")
            for idx in diff['indexes_added']:
                lines.append(f"  + {idx}")
            lines.append("")

        if diff['indexes_removed']:
            lines.append(f"- REMOVED {len(diff['indexes_removed'])} index(es):")
            for idx in diff['indexes_removed']:
                lines.append(f"  - {idx}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def is_breaking_change(diff: Dict[str, Any]) -> bool:
        """Determine if diff represents breaking changes"""
        # Breaking if tables or columns removed
        if diff['tables_removed']:
            return True
        if any(mod['columns_removed'] for mod in diff['tables_modified']):
            return True
        # Removing indexes is not breaking (can be recreated)
        return False

    @staticmethod
    def migration_impact(diff: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate impact of migration"""
        impact = {
            'is_breaking': SchemaDiffer.is_breaking_change(diff),
            'requires_backup': SchemaDiffer.is_breaking_change(diff),
            'requires_downtime': any(mod['columns_removed'] for mod in diff['tables_modified']),
            'data_loss_risk': diff['tables_removed'] or any(mod['columns_removed'] for mod in diff['tables_modified']),
            'changes_count': (
                len(diff['tables_added']) +
                len(diff['tables_removed']) +
                len(diff['tables_modified']) +
                len(diff['indexes_added']) +
                len(diff['indexes_removed'])
            )
        }
        return impact
