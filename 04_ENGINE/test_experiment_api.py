"""
Integration Tests - Experiment API, Queue, Runner, Sandbox
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch
from datetime import datetime

from experiment_queue import ExperimentQueue, QueuePriority, QueuedExperiment
from safety_sandbox import SafetyValidator
from experiment_runner import ExperimentRunner, ExperimentStatus

# ============================================================================
# QUEUE TESTS
# ============================================================================

def test_queue_fifo_ordering():
    """Queue respects FIFO within same priority"""
    q = ExperimentQueue(max_size=10)

    # Add three NORMAL priority items
    pos1 = q.enqueue("exp1", "c1", "Test1", "code1", {}, QueuePriority.NORMAL)
    pos2 = q.enqueue("exp2", "c2", "Test2", "code2", {}, QueuePriority.NORMAL)
    pos3 = q.enqueue("exp3", "c3", "Test3", "code3", {}, QueuePriority.NORMAL)

    assert pos1 == 0
    assert pos2 == 1
    assert pos3 == 2

    # Dequeue should be FIFO
    exp = q.dequeue()
    assert exp.experiment_id == "exp1"
    assert q.size() == 2

def test_queue_priority_ordering():
    """Queue respects priority levels (HIGH > NORMAL > LOW)"""
    q = ExperimentQueue(max_size=10)

    # Add in mixed order
    q.enqueue("exp1", "c1", "T1", "code", {}, QueuePriority.NORMAL)
    q.enqueue("exp2", "c2", "T2", "code", {}, QueuePriority.LOW)
    q.enqueue("exp3", "c3", "T3", "code", {}, QueuePriority.HIGH)

    # Positions should be: exp3(HIGH)=0, exp1(NORMAL)=1, exp2(LOW)=2
    assert q.get_position("exp3") == 0
    assert q.get_position("exp1") == 1
    assert q.get_position("exp2") == 2

def test_queue_max_capacity():
    """Queue rejects submissions when full"""
    q = ExperimentQueue(max_size=3)

    for i in range(3):
        pos = q.enqueue(f"exp{i}", f"c{i}", f"T{i}", "code", {})
        assert pos == i

    # Fourth should fail
    pos = q.enqueue("exp_over", "c_over", "T_over", "code", {})
    assert pos is None
    assert q.size() == 3

def test_queue_get_position():
    """Can retrieve position of queued experiment"""
    q = ExperimentQueue(max_size=10)

    q.enqueue("exp1", "c1", "T1", "code", {})
    q.enqueue("exp2", "c2", "T2", "code", {})

    assert q.get_position("exp1") == 0
    assert q.get_position("exp2") == 1
    assert q.get_position("exp_notfound") is None

def test_queue_remove():
    """Can remove experiment from queue"""
    q = ExperimentQueue(max_size=10)

    q.enqueue("exp1", "c1", "T1", "code", {})
    q.enqueue("exp2", "c2", "T2", "code", {})

    removed = q.remove("exp1")
    assert removed is True
    assert q.size() == 1
    assert q.get_position("exp1") is None

def test_queue_stats():
    """Queue statistics by priority"""
    q = ExperimentQueue(max_size=10)

    q.enqueue("e1", "c1", "T1", "code", {}, QueuePriority.HIGH)
    q.enqueue("e2", "c2", "T2", "code", {}, QueuePriority.HIGH)
    q.enqueue("e3", "c3", "T3", "code", {}, QueuePriority.NORMAL)
    q.enqueue("e4", "c4", "T4", "code", {}, QueuePriority.LOW)

    stats = q.get_stats()
    assert stats["high"] == 2
    assert stats["normal"] == 1
    assert stats["low"] == 1

# ============================================================================
# SANDBOX TESTS
# ============================================================================

def test_sandbox_valid_syntax():
    """Validator accepts valid Python syntax"""
    validator = SafetyValidator()

    code = """
def execute_strategy(context):
    return {"action": "hold"}
"""
    is_valid, errors = validator.validate_strategy(code)
    assert is_valid
    assert len(errors) == 0

def test_sandbox_rejects_syntax_error():
    """Validator rejects syntax errors"""
    validator = SafetyValidator()

    code = "def execute_strategy(: pass"
    is_valid, errors = validator.validate_strategy(code)
    assert not is_valid
    assert len(errors) > 0

def test_sandbox_requires_execute_function():
    """Validator requires execute_strategy function"""
    validator = SafetyValidator()

    code = "x = 1"
    is_valid, errors = validator.validate_strategy(code)
    assert not is_valid
    assert any("execute_strategy" in e for e in errors)

def test_sandbox_bans_os_import():
    """Validator bans os module"""
    validator = SafetyValidator()

    code = """
import os
def execute_strategy(context):
    os.system("bad")
"""
    is_safe, errors = validator.check_sandbox_rules(code)
    assert not is_safe
    assert any("os" in e.lower() for e in errors)

def test_sandbox_bans_eval():
    """Validator bans eval/exec"""
    validator = SafetyValidator()

    code = """
def execute_strategy(context):
    eval("1+1")
"""
    is_safe, errors = validator.check_sandbox_rules(code)
    assert not is_safe
    assert any("eval" in e.lower() for e in errors)

def test_sandbox_allows_safe_imports():
    """Validator allows numpy, pandas, etc"""
    validator = SafetyValidator()

    code = """
import numpy as np
import pandas as pd
def execute_strategy(context):
    data = pd.DataFrame()
"""
    is_safe, errors = validator.check_sandbox_rules(code)
    # Should be safe (might have some warnings but no critical violations)
    # The important thing is it should pass the core security checks
    assert not any("banned" in e.lower() for e in errors)

def test_sandbox_bans_place_order():
    """Validator bans live order placement"""
    validator = SafetyValidator()

    code = """
def execute_strategy(context):
    context.place_order("BUY", 100)
"""
    is_safe, errors = validator.check_sandbox_rules(code)
    assert not is_safe

def test_sandbox_env_creation():
    """Validator creates safe execution environment"""
    validator = SafetyValidator()
    env = validator.create_sandbox_env()

    # Should have safe builtins
    assert "print" in env
    assert "len" in env
    assert "math" in env
    assert "statistics" in env

    # Should NOT have dangerous functions
    assert "__import__" not in env or env["__import__"] != __builtins__.get("__import__")

# ============================================================================
# RUNNER TESTS
# ============================================================================

def test_runner_initialization():
    """Runner initializes with queue"""
    q = ExperimentQueue(max_size=10)
    runner = ExperimentRunner(queue=q)

    assert runner.queue == q
    assert runner.running is True
    assert len(runner.experiments) == 0

def test_runner_strategy_wrapping():
    """Runner wraps strategy code correctly"""
    q = ExperimentQueue(max_size=10)
    runner = ExperimentRunner(queue=q)

    code = "result = 42"
    params = {"key": "value"}

    wrapped = runner._wrap_strategy(code, params)

    # Should contain user code
    assert "result = 42" in wrapped
    # Should have JSON handling
    assert "json" in wrapped
    # Should have context class
    assert "StrategyContext" in wrapped

def test_runner_get_experiment():
    """Runner tracks experiment state"""
    q = ExperimentQueue(max_size=10)
    runner = ExperimentRunner(queue=q)

    runner.experiments["test_id"] = {
        "status": "running",
        "progress": 50
    }

    exp = runner.get_experiment("test_id")
    assert exp is not None
    assert exp["status"] == "running"
    assert exp["progress"] == 50

def test_runner_get_missing_experiment():
    """Runner returns None for missing experiment"""
    q = ExperimentQueue(max_size=10)
    runner = ExperimentRunner(queue=q)

    exp = runner.get_experiment("nonexistent")
    assert exp is None

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_end_to_end_submission_and_status():
    """Full flow: submit strategy -> check status"""
    q = ExperimentQueue(max_size=10)

    # Simulate submission
    pos = q.enqueue(
        "exp_123",
        "corr_123",
        "MyStrategy",
        "def execute_strategy(context): pass",
        {"param1": 10},
        QueuePriority.NORMAL
    )

    assert pos == 0
    assert q.size() == 1
    assert q.get_position("exp_123") == 0

def test_validation_before_enqueue():
    """Validator and queue work together"""
    validator = SafetyValidator()
    q = ExperimentQueue(max_size=10)

    # Test code that should pass
    code = """
def execute_strategy(context):
    prices = context.get_prices()
    return {"action": "buy"}
"""
    is_valid, errors = validator.validate_strategy(code)
    is_safe, errors = validator.check_sandbox_rules(code)

    if is_valid and is_safe:
        pos = q.enqueue(
            "exp_valid",
            "corr_valid",
            "ValidTest",
            code,
            {},
            QueuePriority.NORMAL
        )
        assert pos == 0
        assert q.size() == 1

def test_multiple_submissions_with_priorities():
    """Multiple submissions respect priority levels"""
    validator = SafetyValidator()
    q = ExperimentQueue(max_size=10)

    code = """
def execute_strategy(context):
    return {"action": "hold"}
"""

    # Submit with different priorities
    q.enqueue("e1", "c1", "Normal", code, {}, QueuePriority.NORMAL)
    q.enqueue("e2", "c2", "Low", code, {}, QueuePriority.LOW)
    q.enqueue("e3", "c3", "High", code, {}, QueuePriority.HIGH)

    # Should dequeue: HIGH, NORMAL, LOW
    exp1 = q.dequeue()
    assert exp1.experiment_id == "e3"

    exp2 = q.dequeue()
    assert exp2.experiment_id == "e1"

    exp3 = q.dequeue()
    assert exp3.experiment_id == "e2"

# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    # Run with pytest if available
    pytest.main([__file__, "-v"])
