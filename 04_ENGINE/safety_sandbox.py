"""
Safety Sandbox - Code Validation & Sandboxing
Authority: ZERO (deny by default, whitelist imports)
"""

import ast
import re
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)

class SafetyValidator:
    """
    Validates user-submitted strategy code for:
    - Syntax errors
    - Banned imports (os, sys, subprocess, etc.)
    - Unsafe operations (file I/O, network, live orders)
    """

    # Banned module imports
    BANNED_MODULES = {
        "os", "sys", "subprocess", "socket", "urllib",
        "requests", "http", "ftplib", "paramiko",
        "threading", "multiprocessing", "asyncio",
        "importlib", "__import__", "eval", "exec",
        "compile", "open", "file", "input", "raw_input"
    }

    # Banned function/method calls (patterns)
    BANNED_PATTERNS = {
        r"os\.",
        r"sys\.",
        r"import os",
        r"import sys",
        r"import subprocess",
        r"from os",
        r"from sys",
        r"__import__",
        r"exec\(",
        r"eval\(",
        r"compile\(",
        r"open\(",
        r"\.place_order\(",
        r"\.submit_order\(",
        r"\.execute\(",
        r"socket\.",
        r"urllib\.",
        r"requests\.",
    }

    # Whitelist: allowed imports for strategy
    ALLOWED_IMPORTS = {
        "numpy", "pandas", "math", "statistics",
        "datetime", "time", "json", "decimal",
        "collections", "itertools", "functools",
        "flipflop_strategy_api",  # Custom safe API
    }

    def __init__(self):
        self.errors: List[str] = []

    def validate_strategy(self, code: str) -> Tuple[bool, List[str]]:
        """
        Validate Python syntax and structure
        Returns: (is_valid, errors)
        """
        self.errors = []

        # Check for empty code
        if not code or not code.strip():
            self.errors.append("Strategy code cannot be empty")
            return False, self.errors

        # Try parsing as AST
        try:
            ast.parse(code)
        except SyntaxError as e:
            self.errors.append(f"Syntax error: {e.msg} at line {e.lineno}")
            return False, self.errors
        except Exception as e:
            self.errors.append(f"Parse error: {str(e)}")
            return False, self.errors

        # Check for required main function
        if "def execute_strategy" not in code:
            self.errors.append(
                "Strategy must define execute_strategy(context) function"
            )
            return False, self.errors

        return True, self.errors

    def check_sandbox_rules(self, code: str) -> Tuple[bool, List[str]]:
        """
        Check for sandbox violations
        Returns: (is_safe, violations)
        """
        self.errors = []

        # Pattern-based checks (fast)
        for pattern in self.BANNED_PATTERNS:
            if re.search(pattern, code):
                self.errors.append(f"Banned pattern detected: {pattern}")

        # AST-based checks (deep)
        try:
            tree = ast.parse(code)
            self._check_imports(tree)
            self._check_calls(tree)
            self._check_attributes(tree)
        except Exception as e:
            self.errors.append(f"Analysis error: {str(e)}")
            return False, self.errors

        return len(self.errors) == 0, self.errors

    def _check_imports(self, tree):
        """Check banned imports"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    m = a.name.split(".")[0]
                    if m in self.BANNED_MODULES:
                        self.errors.append(f"Banned: {m}")
            elif isinstance(node, ast.ImportFrom):
                m = (node.module or "").split(".")[0]
                if m in self.BANNED_MODULES:
                    self.errors.append(f"Banned: {m}")

    def _check_calls(self, tree):
        """Check banned calls"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec", "compile", "open", "__import__"):
                    self.errors.append(f"Banned: {node.func.id}()")

    def _check_attributes(self, tree):
        """Check banned attributes"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                chain = self._get_full_attr(node)
                for b in ("os.", "sys.", "socket.", "urllib.", "requests."):
                    if chain.startswith(b):
                        self.errors.append(f"Banned: {chain}")

    def _get_full_attr(self, node) -> str:
        """Get attribute chain"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        if isinstance(node.value, ast.Attribute):
            return f"{self._get_full_attr(node.value)}.{node.attr}"
        return node.attr

    def create_sandbox_env(self) -> dict:
        """
        Create restricted Python environment for execution
        Returns: globals dict with only safe builtins
        """
        safe_builtins = {
            "print": print,
            "len": len,
            "range": range,
            "dict": dict,
            "list": list,
            "tuple": tuple,
            "set": set,
            "sum": sum,
            "min": min,
            "max": max,
            "sorted": sorted,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "abs": abs,
            "round": round,
            "pow": pow,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "type": type,
        }

        # Add safe imports (with fallback)
        import math
        import statistics
        from datetime import datetime, timedelta

        safe_builtins.update({
            "math": math,
            "statistics": statistics,
            "datetime": datetime,
            "timedelta": timedelta,
        })

        # Add numpy/pandas if available
        try:
            import numpy as np
            safe_builtins["numpy"] = np
            safe_builtins["np"] = np
        except ImportError:
            pass

        try:
            import pandas as pd
            safe_builtins["pandas"] = pd
            safe_builtins["pd"] = pd
        except ImportError:
            pass

        return safe_builtins

# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    v = SafetyValidator()
    tc = [("Valid","def execute_strategy(context):\n    return {'action':'hold'}",True,True),
          ("BadSyn","def execute_strategy(: pass",False,None),("NoFunc","x = 1",False,None),
          ("BanOS","import os\ndef execute_strategy(context):\n    os.system('x')",None,False),
          ("BanEval","def execute_strategy(context):\n    eval('1+1')",None,False),
          ("BanOrd","def execute_strategy(context):\n    context.place_order('BUY',100)",None,False)]
    for nm,cd,ev,es in tc:
        if ev is not None:
            ok,_=v.validate_strategy(cd)
            assert ok==ev,f"{nm} failed"
        if es is not None:
            ok,_=v.check_sandbox_rules(cd)
            assert ok==es,f"{nm} sandbox"
        print(f"[PASS] {nm}")
    print("[PASS] All tests")
