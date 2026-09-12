"""
Migration Rollback Simulator for FlipFlop HQ
Simulate and preview rollback impact before execution
"""

from typing import Dict, List, Any
from schema_differ import SchemaDiffer
from schema_definitions import SCHEMA_0001, SCHEMA_0002, SCHEMA_0003, SCHEMA_0004


class RollbackSimulator:
    """Simulates rollback impact"""

    SCHEMAS = {
        1: SCHEMA_0001,
        2: SCHEMA_0002,
        3: SCHEMA_0003,
        4: SCHEMA_0004
    }

    @staticmethod
    def get_schema_before_migration(migration_number: int) -> Dict[str, Any]:
        """Get schema state before migration was applied"""
        if migration_number <= 1:
            return {}  # No schema before 0001
        return RollbackSimulator.SCHEMAS.get(migration_number - 1, {})

    @staticmethod
    def simulate_rollback(migration_number: int) -> Dict[str, Any]:
        """Simulate rollback of a migration"""
        current_schema = RollbackSimulator.SCHEMAS.get(migration_number, {})
        target_schema = RollbackSimulator.get_schema_before_migration(migration_number)

        if not current_schema:
            return {
                'migration': migration_number,
                'status': 'INVALID',
                'reason': 'Migration not found'
            }

        # Generate diff (what will be removed)
        diff = SchemaDiffer.diff_schemas(target_schema, current_schema)

        # Invert diff to show what will be removed
        rollback_impact = {
            'migration': migration_number,
            'migration_name': current_schema.get('name', 'unknown'),
            'tables_to_drop': diff['tables_added'],  # Were added in this migration
            'columns_to_drop': [],
            'indexes_to_drop': diff['indexes_added'],  # Were added in this migration
            'data_loss_risk': len(diff['tables_added']) > 0,
            'estimated_impact': {
                'tables_affected': len(diff['tables_added']),
                'rows_at_risk': 'Unknown (depends on data)',
                'recovery_possible': False  # Rollback loses data
            }
        }

        # Collect columns to drop from modified tables
        for mod in diff['tables_modified']:
            for col in mod['columns_added']:
                rollback_impact['columns_to_drop'].append(f"{mod['name']}.{col}")

        return rollback_impact

    @staticmethod
    def preview_rollback_chain(migration_number: int) -> List[Dict[str, Any]]:
        """Preview rollback of multiple migrations if needed"""
        previews = []
        for mig in range(migration_number, 0, -1):
            preview = RollbackSimulator.simulate_rollback(mig)
            previews.append(preview)
        return previews

    @staticmethod
    def rollback_risk_level(migration_number: int) -> str:
        """Estimate risk level of rollback"""
        impact = RollbackSimulator.simulate_rollback(migration_number)

        if not impact.get('tables_to_drop'):
            return 'LOW'  # No tables lost

        if len(impact['tables_to_drop']) <= 2:
            return 'MEDIUM'  # Small number of tables

        return 'HIGH'  # Many tables at risk

    @staticmethod
    def format_rollback_preview(impact: Dict[str, Any]) -> str:
        """Format rollback preview as human-readable text"""
        lines = []

        lines.append(f"Rollback Preview: Migration {impact['migration']} ({impact.get('migration_name', 'unknown')})")
        lines.append("=" * 60)
        lines.append("")

        lines.append("⚠ IMPACT:")
        lines.append(f"  Tables to drop: {len(impact['tables_to_drop'])}")
        for table in impact['tables_to_drop']:
            lines.append(f"    - {table} (DATA WILL BE LOST)")

        lines.append(f"  Columns to drop: {len(impact['columns_to_drop'])}")
        for col in impact['columns_to_drop'][:5]:  # Show first 5
            lines.append(f"    - {col} (DATA WILL BE LOST)")
        if len(impact['columns_to_drop']) > 5:
            lines.append(f"    ... and {len(impact['columns_to_drop']) - 5} more")

        lines.append(f"  Indexes to drop: {len(impact['indexes_to_drop'])}")
        for idx in impact['indexes_to_drop'][:5]:
            lines.append(f"    - {idx}")
        if len(impact['indexes_to_drop']) > 5:
            lines.append(f"    ... and {len(impact['indexes_to_drop']) - 5} more")

        lines.append("")
        lines.append(f"Data Loss Risk: {'YES' if impact['data_loss_risk'] else 'NO'}")
        lines.append(f"Recovery Possible: {'NO - Data permanently lost' if not impact['estimated_impact']['recovery_possible'] else 'YES'}")
        lines.append("")

        return "\n".join(lines)
