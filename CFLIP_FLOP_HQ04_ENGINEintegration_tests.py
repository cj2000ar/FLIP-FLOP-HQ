"""Integration tests for complete production system"""

import unittest
import tempfile
from pathlib import Path
import json
from datetime import datetime

from job_orchestrator import JobOrchestrator
from deterministic_replay import DeterministicReplayEngine
from audit_engine import AuditEngine, AuditLogger
from script_sandbox import SafeScriptExecutor, ScriptValidator
from evolution_loop_locked import EvolutionLoop, VariantAnalyzer
from backup_restore import BackupManager
from health_check import HealthChecker


class TestIdempotentJobs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = JobOrchestrator(self.temp_dir)

    def test_duplicate_detection(self):
        job_def = {
            'job_id': 'test_1',
            'strategy_hash': 'abc',
            'data_hash': 'def',
            'params': {'x': 1}
        }

        def handler(job_def, start_state, checkpoint_data):
            return {'result': 'ok'}

        result1 = self.orchestrator.run_job(job_def, handler)
        self.assertEqual(result1['status'], 'SUCCEEDED')

        result2 = self.orchestrator.run_job(job_def, handler)
        self.assertEqual(result2['status'], 'DUPLICATE_SKIPPED')


class TestAuditTrail(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.audit = AuditEngine(self.temp_dir)

    def test_chain_integrity(self):
        self.audit.append({'type': 'TEST', 'data': 'a'})
        self.audit.append({'type': 'TEST', 'data': 'b'})

        result = self.audit.verify_chain()
        self.assertEqual(result['status'], 'VALID')


class TestScriptSandbox(unittest.TestCase):
    def setUp(self):
        self.validator = ScriptValidator()

    def test_reject_os_import(self):
        script = "import os\n\ndef execute_strategy(data):\n    return []"
        result = self.validator.validate(script)
        self.assertFalse(result['valid'])

    def test_accept_safe_script(self):
        script = "def execute_strategy(data):\n    return []"
        result = self.validator.validate(script)
        self.assertTrue(result['valid'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
