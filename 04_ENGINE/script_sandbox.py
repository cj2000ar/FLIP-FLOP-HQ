"""Safe script execution with isolation and resource limits"""

import subprocess
import tempfile
import json
import os
import ast
import logging
import resource
import signal
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ScriptValidator:
    """AST-based script validation (banned imports/calls)"""

    BANNED_IMPORTS = {
        'os', 'sys', 'subprocess', 'socket', 'requests',
        'urllib', 'paramiko', 'ftplib', 'telnetlib', 'smtplib'
    }

    BANNED_CALLS = {
        'eval', 'exec', 'compile', '__import__', 'open',
        'input', 'raw_input', 'breakpoint', 'globals', 'locals'
    }

    BANNED_ATTRIBUTES = {
        '__dict__', '__class__', '__bases__', '__code__',
        '__globals__', '__builtins__', 'func_code'
    }

    def validate(self, script_text: str) -> Dict[str, Any]:
        """Validate script and return findings"""
        try:
            tree = ast.parse(script_text)
        except SyntaxError as e:
            return {
                'valid': False,
                'error': f"Syntax error: {e}"
            }

        findings = []

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module in self.BANNED_IMPORTS:
                        findings.append(
                            f"Banned import: {alias.name} (line {node.lineno})"
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module in self.BANNED_IMPORTS:
                        findings.append(
                            f"Banned import: from {node.module} (line {node.lineno})"
                        )

            # Check function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.BANNED_CALLS:
                        findings.append(
                            f"Banned function call: {node.func.id}() (line {node.lineno})"
                        )

            # Check attributes
            elif isinstance(node, ast.Attribute):
                if node.attr in self.BANNED_ATTRIBUTES:
                    findings.append(
                        f"Banned attribute: {node.attr} (line {node.lineno})"
                    )

        # Verify execute_strategy() exists
        functions = [
            n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
        ]

        if 'execute_strategy' not in functions:
            findings.append("Missing execute_strategy() function")

        if findings:
            return {
                'valid': False,
                'errors': findings
            }

        return {'valid': True}


class SafeScriptExecutor:
    """Subprocess isolation with resource limits"""

    def __init__(self, timeout_sec: int = 300, memory_limit_mb: int = 512):
        self.timeout_sec = timeout_sec
        self.memory_limit_mb = memory_limit_mb
        self.validator = ScriptValidator()

    def execute(self, script_text: str, market_data: Dict[str, Any],
               script_id: str = "unknown") -> Dict[str, Any]:
        """Execute script safely"""

        # Validate first
        validation = self.validator.validate(script_text)
        if not validation['valid']:
            return {
                'status': 'REJECTED',
                'script_id': script_id,
                'errors': validation.get('errors', [])
            }

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            wrapper = f"""
import json
import sys
import resource

# Set resource limits
resource.setrlimit(resource.RLIMIT_CPU, ({self.timeout_sec}, {self.timeout_sec}))
resource.setrlimit(resource.RLIMIT_AS, ({self.memory_limit_mb * 1024 * 1024}, {self.memory_limit_mb * 1024 * 1024}))

# User script
{script_text}

# Run strategy
try:
    trades = execute_strategy({json.dumps(market_data)})
    print(json.dumps({{"status": "OK", "trades": trades}}))
except Exception as e:
    print(json.dumps({{"status": "ERROR", "message": str(e)}}))
    sys.exit(1)
"""
            f.write(wrapper)
            temp_script = f.name

        try:
            # Run subprocess with timeout
            result = subprocess.run(
                ['python3', temp_script],
                capture_output=True,
                timeout=self.timeout_sec,
                text=True
            )

            if result.returncode != 0:
                return {
                    'status': 'FAILED',
                    'script_id': script_id,
                    'stderr': result.stderr[:500]  # Limit output
                }

            # Parse output
            try:
                output = json.loads(result.stdout)
                return {
                    'status': 'SUCCESS',
                    'script_id': script_id,
                    'trades': output.get('trades', []),
                    'execution_time_sec': result.returncode
                }
            except json.JSONDecodeError:
                return {
                    'status': 'FAILED',
                    'script_id': script_id,
                    'error': 'Invalid JSON output'
                }

        except subprocess.TimeoutExpired:
            return {
                'status': 'TIMEOUT',
                'script_id': script_id,
                'timeout_sec': self.timeout_sec
            }

        except Exception as e:
            return {
                'status': 'ERROR',
                'script_id': script_id,
                'error': str(e)
            }

        finally:
            os.unlink(temp_script)


class RedactedLogger:
    """Audit logging with credential redaction"""

    SECRETS_PATTERNS = [
        'API_KEY', 'API_SECRET', 'PASSWORD', 'TOKEN',
        'CREDENTIAL', 'SECRET', 'auth', 'password'
    ]

    @staticmethod
    def redact(text: str) -> str:
        """Redact potential secrets"""
        for pattern in RedactedLogger.SECRETS_PATTERNS:
            if pattern.lower() in text.lower():
                return "[REDACTED]"
        return text

    @staticmethod
    def safe_dict(data: Dict) -> Dict:
        """Return dict with secrets redacted"""
        safe = {}
        for k, v in data.items():
            if any(p.lower() in k.lower() for p in RedactedLogger.SECRETS_PATTERNS):
                safe[k] = "[REDACTED]"
            elif isinstance(v, dict):
                safe[k] = RedactedLogger.safe_dict(v)
            elif isinstance(v, str):
                safe[k] = RedactedLogger.redact(v)
            else:
                safe[k] = v
        return safe
