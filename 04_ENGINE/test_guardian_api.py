"""
Guardian API Integration Test
Tests end-to-end flow: evaluate deployment candidate through 8 gates
"""

import requests
import json
import sys
from datetime import datetime
from uuid import uuid4

BASE_URL = "http://localhost:8000"

def test_guardian_evaluate():
    """Test POST /guardian/evaluate endpoint"""

    correlation_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    request_payload = {
        "correlation_id": correlation_id,
        "artifact_hashes": {
            "strategy": "sha256_strategy_valid_test",
            "engine": "sha256_engine_valid_test",
            "ui": "sha256_ui_valid_test"
        },
        "passport_hash": "sha256_passport_valid_test",
        "side": "BUY",
        "source_system": "TEST_SYSTEM",
        "evidence": [
            {
                "evidence_type": "HASH_MATCH",
                "source_system": "HP_INFRA",
                "observation": {
                    "strategy_sha256": "sha256_strategy_valid_test",
                    "engine_sha256": "sha256_engine_valid_test",
                    "ui_sha256": "sha256_ui_valid_test",
                    "passport_sha256": "sha256_passport_valid_test"
                },
                "observed_at": now,
                "recorded_at": now,
                "checksum": "checksum_test"
            },
            {
                "evidence_type": "POLICY_CHECK",
                "source_system": "GUARDIAN_POLICY",
                "observation": {
                    "authority": "ZERO",
                    "live_enabled": False,
                    "broker_orders_allowed": False,
                    "control_mutation_allowed": False
                },
                "observed_at": now,
                "recorded_at": now,
                "checksum": "checksum_policy"
            },
            {
                "evidence_type": "MACHINE_HEALTH",
                "source_system": "HP_INFRA",
                "observation": {
                    "health_status": "HEALTHY",
                    "error_count": 0,
                    "clock_offset": 0.1
                },
                "observed_at": now,
                "recorded_at": now,
                "checksum": "checksum_health"
            },
            {
                "evidence_type": "CANARY_RUN",
                "source_system": "CANARY_ENGINE",
                "observation": {
                    "canary_result": "PASS",
                    "error_rate": 0.02,
                    "latency_p99_ms": 150,
                    "rollback_triggered": False
                },
                "observed_at": now,
                "recorded_at": now,
                "checksum": "checksum_canary"
            }
        ]
    }

    try:
        print(f"POST {BASE_URL}/guardian/evaluate")
        print(f"Correlation ID: {correlation_id}")

        response = requests.post(
            f"{BASE_URL}/guardian/evaluate",
            json=request_payload,
            timeout=10
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\nOK: Evaluation complete")
            print(f"Final Verdict: {result['final_verdict']}")
            print(f"\nGate Results:")
            for gate in result['gate_verdicts']:
                print(f"  {gate['gate_id']}: {gate['verdict']} - {gate['reasoning']}")

            # Test GET /guardian/cartridge
            print(f"\nGET /guardian/cartridge/{correlation_id}")
            cart_response = requests.get(
                f"{BASE_URL}/guardian/cartridge/{correlation_id}",
                timeout=10
            )
            if cart_response.status_code == 200:
                cart = cart_response.json()
                print(f"OK: Retrieved cartridge {cart['cartridge_id']}")
            else:
                print(f"ERROR: {cart_response.status_code}")

            return True
        else:
            print(f"ERROR: {response.status_code}")
            print(response.text)
            return False

    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to {BASE_URL}")
        print("Is the server running? Start with: python hp_api.py")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_guardian_evaluate()
    sys.exit(0 if success else 1)
