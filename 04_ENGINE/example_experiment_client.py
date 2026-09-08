"""
Example Client - Experiment API Usage
Demonstrates submission, polling, and result retrieval
"""

import requests
import json
import time
import websocket
from typing import Dict, List

# API base URL
BASE_URL = "http://localhost:8001"

class ExperimentClient:
    """Client for interacting with Experiment API"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url

    def submit_strategy(
        self,
        name: str,
        strategy_code: str,
        description: str = None,
        parameters: Dict = None,
        priority: str = "normal"
    ) -> str:
        """Submit strategy and return experiment_id"""
        payload = {
            "name": name,
            "description": description or "",
            "strategy_code": strategy_code,
            "parameters": parameters or {},
            "priority": priority
        }
        resp = requests.post(f"{self.base_url}/experiment/submit", json=payload)
        resp.raise_for_status()
        data = resp.json()
        print(f"Submitted: {data['experiment_id']}")
        print(f"Queue position: {data['queue_position']}")
        return data["experiment_id"]

    def get_status(self, experiment_id: str) -> Dict:
        """Poll experiment status"""
        resp = requests.get(f"{self.base_url}/experiment/{experiment_id}/status")
        resp.raise_for_status()
        return resp.json()

    def get_results(self, experiment_id: str) -> Dict:
        """Get final results (blocks until complete)"""
        resp = requests.get(f"{self.base_url}/experiment/{experiment_id}/results")
        resp.raise_for_status()
        return resp.json()

    def poll_until_complete(self, experiment_id: str, interval: int = 5) -> Dict:
        """Poll status until experiment completes"""
        print(f"\nWaiting for {experiment_id} to complete...")
        while True:
            status = self.get_status(experiment_id)
            print(f"Status: {status['status']} | Progress: {status['progress_percent']}%")

            if status["status"] in ["completed", "failed"]:
                if status["status"] == "completed":
                    results = self.get_results(experiment_id)
                    return results
                else:
                    print(f"Failed: {status.get('error_message')}")
                    return None

            time.sleep(interval)

    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        resp = requests.get(f"{self.base_url}/experiment/queue/status")
        resp.raise_for_status()
        return resp.json()

# ============================================================================
# EXAMPLE STRATEGIES
# ============================================================================

STRATEGY_SMA_CROSSOVER = """
def execute_strategy(context):
    '''Simple Moving Average Crossover'''
    prices = context.get_prices()
    if len(prices) < 20:
        return {"action": "hold"}

    # Calculate SMAs
    sma_10 = sum(p.get("close", 100) for p in prices[-10:]) / 10
    sma_20 = sum(p.get("close", 100) for p in prices[-20:]) / 20

    # Signals
    if sma_10 > sma_20 and context.equity_curve[-1] > 10000:
        return {"action": "buy", "quantity": 100}
    elif sma_10 < sma_20:
        return {"action": "sell", "quantity": 100}
    return {"action": "hold"}
"""

STRATEGY_RSI = """
def execute_strategy(context):
    '''RSI (Relative Strength Index) based strategy'''
    prices = context.get_prices()
    if len(prices) < 14:
        return {"action": "hold"}

    # Calculate RSI
    closes = [p.get("close", 100) for p in prices[-14:]]
    gains = sum(max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))) / 14
    losses = sum(max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))) / 14

    if losses > 0:
        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
    else:
        rsi = 50

    # Signals
    if rsi < 30:
        return {"action": "buy", "quantity": 100}
    elif rsi > 70:
        return {"action": "sell", "quantity": 100}
    return {"action": "hold"}
"""

STRATEGY_MOMENTUM = """
def execute_strategy(context):
    '''Momentum-based strategy'''
    prices = context.get_prices()
    if len(prices) < 5:
        return {"action": "hold"}

    # Calculate momentum
    current = prices[-1].get("close", 100)
    prev = prices[-5].get("close", 100)
    momentum = ((current - prev) / prev) * 100

    # Trade on momentum
    if momentum > 2.0:
        return {"action": "buy", "quantity": 50}
    elif momentum < -2.0:
        return {"action": "sell", "quantity": 50}
    return {"action": "hold"}
"""

# ============================================================================
# EXAMPLES
# ============================================================================

def example_basic_submission():
    """Basic submission and polling"""
    client = ExperimentClient()

    # Check queue
    queue_status = client.get_queue_status()
    print(f"Queue depth: {queue_status['total_queued']}/{queue_status['max_capacity']}")

    # Submit strategy
    exp_id = client.submit_strategy(
        name="SMA Crossover v1",
        strategy_code=STRATEGY_SMA_CROSSOVER,
        description="10/20 SMA crossover with equity check",
        parameters={"sma_short": 10, "sma_long": 20},
        priority="normal"
    )

    # Poll until complete
    results = client.poll_until_complete(exp_id, interval=2)

    if results:
        print("\n=== RESULTS ===")
        print(f"Total Trades: {results['total_trades']}")
        print(f"Win Rate: {results['win_rate']:.2%}")
        print(f"Profit Factor: {results['profit_factor']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']:.2%}")
        print(f"Verification Status: {results['verification_status']}")

def example_multiple_strategies():
    """Submit multiple strategies at once"""
    client = ExperimentClient()

    strategies = [
        ("SMA Crossover", STRATEGY_SMA_CROSSOVER, "normal"),
        ("RSI Strategy", STRATEGY_RSI, "high"),
        ("Momentum", STRATEGY_MOMENTUM, "low"),
    ]

    exp_ids = []
    for name, code, priority in strategies:
        exp_id = client.submit_strategy(
            name=name,
            strategy_code=code,
            priority=priority
        )
        exp_ids.append(exp_id)

    # Poll all
    print("\nWaiting for all experiments...")
    for exp_id in exp_ids:
        results = client.poll_until_complete(exp_id)
        if results:
            print(f"{exp_id}: Win Rate={results['win_rate']:.2%}")

def example_high_priority():
    """Submit high-priority strategy (jumped queue)"""
    client = ExperimentClient()

    # Low priority first
    exp_id_low = client.submit_strategy(
        name="Low Priority",
        strategy_code=STRATEGY_MOMENTUM,
        priority="low"
    )

    # High priority (should jump queue)
    exp_id_high = client.submit_strategy(
        name="High Priority",
        strategy_code=STRATEGY_SMA_CROSSOVER,
        priority="high"
    )

    # High priority should execute first
    print("\nHigh priority should complete before low priority")
    results_high = client.poll_until_complete(exp_id_high, interval=2)
    results_low = client.poll_until_complete(exp_id_low, interval=2)

def example_error_handling():
    """Demonstrate error cases"""
    client = ExperimentClient()

    # Bad syntax
    bad_code = "def execute_strategy(context) pass"
    try:
        client.submit_strategy("Bad Syntax", bad_code)
    except requests.HTTPError as e:
        print(f"Expected error (bad syntax): {e.response.json()['detail']}")

    # Banned import
    banned_code = """
import os
def execute_strategy(context):
    os.system('rm -rf /')
"""
    try:
        client.submit_strategy("Banned Import", banned_code)
    except requests.HTTPError as e:
        print(f"Expected error (banned import): {e.response.json()['detail']}")

    # Live order attempt
    live_order_code = """
def execute_strategy(context):
    context.place_order('BUY', 1000)
"""
    try:
        client.submit_strategy("Live Order", live_order_code)
    except requests.HTTPError as e:
        print(f"Expected error (live order): {e.response.json()['detail']}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "errors":
        example_error_handling()
    elif len(sys.argv) > 1 and sys.argv[1] == "multi":
        example_multiple_strategies()
    elif len(sys.argv) > 1 and sys.argv[1] == "high":
        example_high_priority()
    else:
        example_basic_submission()
