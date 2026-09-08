"""
Canary Executor + Gate 5 Integration Tests
Tests Market Replay canary execution and Guardian Gate 5 evaluation.
"""

import pytest
import json
import os
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "RED_DRAGON"))

from canary_executor import CanaryExecutor, CanaryStatus, CanaryResult
from gate_5_canary import Gate5CanaryIntegration
from guardian_engine import VerdictType


class TestCanaryExecutor:
    """Test canary execution core functionality"""

    def test_canary_init(self):
        """Test canary executor initialization"""
        executor = CanaryExecutor("test_canary.db")
        assert os.path.exists("test_canary.db")
        os.remove("test_canary.db")

    def test_canary_pass(self):
        """Test canary passes with good trades"""
        executor = CanaryExecutor("test_canary_pass.db")
        correlation_id = str(uuid4())

        trades_data = [
            {
                "side": "BUY",
                "quantity": 1,
                "entry_price": 100.0,
                "exit_price": 101.0,
                "pnl_dollars": 50.0,
                "latency_ms": 50,
            },
            {
                "side": "SELL",
                "quantity": 1,
                "entry_price": 102.0,
                "exit_price": 101.0,
                "pnl_dollars": 75.0,
                "latency_ms": 48,
            },
        ]

        status, result = executor.run_canary(
            "RR500_V03",
            "NQ",
            trades_data,
            correlation_id
        )

        assert status == CanaryStatus.PASS
        assert result.error_rate == 0.0
        assert result.avg_latency_ms < 200
        assert not result.triggered_rollback

        os.remove("test_canary_pass.db")

    def test_canary_high_error_rate(self):
        """Test canary fails with high error rate"""
        executor = CanaryExecutor("test_canary_errors.db")
        correlation_id = str(uuid4())

        trades_data = [
            {
                "side": "BUY",
                "quantity": 1,
                "pnl_dollars": -500.0,  # Large loss triggers failure
                "latency_ms": 50,
            },
            {
                "side": "BUY",
                "quantity": 1,
                "pnl_dollars": -450.0,
                "latency_ms": 50,
            },
            {
                "side": "BUY",
                "quantity": 1,
                "pnl_dollars": -400.0,
                "latency_ms": 50,
            },
        ]

        status, result = executor.run_canary(
            "RR500_V03",
            "NQ",
            trades_data,
            correlation_id
        )

        assert status == CanaryStatus.HIGH_ERROR_RATE or status == CanaryStatus.CANARY_FAILED
        assert result.triggered_rollback
        assert result.error_rate > 0.0

        os.remove("test_canary_errors.db")

    def test_canary_high_latency(self):
        """Test canary fails with high latency"""
        executor = CanaryExecutor("test_canary_latency.db")
        correlation_id = str(uuid4())

        trades_data = [
            {
                "side": "BUY",
                "quantity": 1,
                "pnl_dollars": 50.0,
                "latency_ms": 250,  # Above 200ms threshold
            },
            {
                "side": "BUY",
                "quantity": 1,
                "pnl_dollars": 60.0,
                "latency_ms": 300,
            },
        ]

        status, result = executor.run_canary(
            "RR500_V03",
            "NQ",
            trades_data,
            correlation_id
        )

        assert status == CanaryStatus.HIGH_LATENCY
        assert result.triggered_rollback
        assert result.avg_latency_ms > 200

        os.remove("test_canary_latency.db")

    def test_canary_immutability(self):
        """Test CanaryResult is immutable"""
        executor = CanaryExecutor("test_canary_immutable.db")
        correlation_id = str(uuid4())

        trades_data = [
            {"side": "BUY", "quantity": 1, "pnl_dollars": 50.0, "latency_ms": 50},
        ]

        status, result = executor.run_canary(
            "RR500_V03",
            "NQ",
            trades_data,
            correlation_id
        )

        # Verify frozen (no modification)
        with pytest.raises(AttributeError):
            result.pnl_dollars = 0.0

        os.remove("test_canary_immutable.db")

    def test_canary_result_retrieval(self):
        """Test canary results are logged and retrievable"""
        executor = CanaryExecutor("test_canary_retrieve.db")
        correlation_id = str(uuid4())

        trades_data = [
            {"side": "BUY", "quantity": 1, "pnl_dollars": 100.0, "latency_ms": 50},
        ]

        status, result = executor.run_canary(
            "RR500_V03",
            "NQ",
            trades_data,
            correlation_id
        )

        # Retrieve result
        retrieved = executor.get_canary_result(result.canary_id)
        assert retrieved is not None
        assert retrieved["canary_id"] == result.canary_id
        assert retrieved["status"] == result.status.value

        os.remove("test_canary_retrieve.db")


class TestGate5CanaryIntegration:
    """Test Gate 5 + Canary integration"""

    def test_integration_pass_to_gate5(self):
        """Test passing canary result converts to Gate 5 PASS verdict"""
        integration = Gate5CanaryIntegration()
        correlation_id = str(uuid4())

        trades_data = [
            {"side": "BUY", "quantity": 1, "pnl_dollars": 50.0, "latency_ms": 50},
        ]

        result, evidence = integration.run_canary_and_generate_evidence(
            "RR500_V03",
            "NQ",
            trades_data,
            correlation_id
        )

        verdict = integration.get_canary_status_for_gate_5(result)
        assert verdict == VerdictType.PASS

        # Verify evidence record created
        assert evidence.evidence_type == "CANARY_RUN"
        assert evidence.source_system == "CANARY_EXECUTOR"

    def test_integration_fail_to_gate5(self):
        """Test failing canary result converts to Gate 5 BLOCKED verdict"""
        integration = Gate5CanaryIntegration()
        correlation_id = str(uuid4())

        trades_data = [
            {"side": "BUY", "quantity": 1, "pnl_dollars": -500.0, "latency_ms": 250},
        ]

        result, evidence = integration.run_canary_and_generate_evidence(
            "RR500_V03",
            "NQ",
            trades_data,
            correlation_id
        )

        verdict = integration.get_canary_status_for_gate_5(result)
        assert verdict == VerdictType.BLOCKED

    def test_gate5_reasoning_generation(self):
        """Test Gate 5 reasoning is human-readable"""
        integration = Gate5CanaryIntegration()
        correlation_id = str(uuid4())

        trades_data = [
            {"side": "BUY", "quantity": 1, "pnl_dollars": 50.0, "latency_ms": 50},
        ]

        result, _ = integration.run_canary_and_generate_evidence(
            "RR500_V03",
            "NQ",
            trades_data,
            correlation_id
        )

        reasoning = integration.generate_gate5_reasoning(result)
        assert "Canary Execution (Gate 5)" in reasoning
        assert "PASS" in reasoning
        assert result.canary_id in reasoning


class TestAuthorityConstraints:
    """Test Authority-ZERO constraints in canary execution"""

    def test_no_live_trading(self):
        """Verify canary executor cannot enable live trading"""
        executor = CanaryExecutor()
        assert executor.authority == "ZERO"
        assert executor.live_enabled is False
        assert executor.broker_orders_allowed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
