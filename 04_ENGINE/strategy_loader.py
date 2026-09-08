"""Load custom strategy scripts into Evolution Loop"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class StrategyLoader:
    """Load and register custom trading strategies"""

    def __init__(self, strategies_dir: str = "strategies"):
        self.strategies_dir = Path(strategies_dir)
        self.strategies_dir.mkdir(exist_ok=True)
        self.registry = {}

    def load_all(self) -> Dict[str, Any]:
        """Load all .json strategy files from strategies/ directory"""
        strategies = {}

        for strategy_file in self.strategies_dir.glob("*.json"):
            try:
                with open(strategy_file) as f:
                    strategy = json.load(f)

                # Validate required fields
                if not all(k in strategy for k in ['name', 'description', 'parameters', 'indicators']):
                    logger.warning(f"Invalid strategy file {strategy_file}: missing required fields")
                    continue

                strategy_name = strategy['name']
                strategies[strategy_name] = strategy
                logger.info(f"Loaded strategy: {strategy_name}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse {strategy_file}: {e}")
            except Exception as e:
                logger.error(f"Failed to load {strategy_file}: {e}")

        self.registry = strategies
        logger.info(f"Loaded {len(strategies)} strategies")
        return strategies

    def register_strategy(self, strategy: Dict[str, Any]) -> bool:
        """Register strategy programmatically"""
        try:
            name = strategy['name']

            # Validate
            if not all(k in strategy for k in ['description', 'parameters', 'indicators']):
                logger.error(f"Strategy {name} missing required fields")
                return False

            self.registry[name] = strategy
            logger.info(f"Registered strategy: {name}")

            # Save to file
            strategy_file = self.strategies_dir / f"{name}.json"
            with open(strategy_file, 'w') as f:
                json.dump(strategy, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"Failed to register strategy: {e}")
            return False

    def get_strategy(self, name: str) -> Dict[str, Any] | None:
        """Get strategy by name"""
        return self.registry.get(name)

    def list_strategies(self) -> List[Dict[str, Any]]:
        """List all loaded strategies"""
        return list(self.registry.values())

    def export_for_evolution(self) -> Dict[str, Any]:
        """Export strategies for Evolution Loop"""
        return {
            'strategies': self.registry,
            'count': len(self.registry),
            'timestamp': None,  # Will be set by Evolution Loop
        }


# Example usage
if __name__ == '__main__':
    loader = StrategyLoader()

    # Load existing strategies from strategies/ directory
    loaded = loader.load_all()
    print(f"Loaded {len(loaded)} strategies:")
    for name, strategy in loaded.items():
        print(f"  - {name}: {strategy.get('description', 'N/A')}")

    # Example: Register a new strategy
    example_strategy = {
        'name': 'RR500/V03',
        'description': 'Baseline RR=500, stops=0.02, targets=0.05',
        'parameters': {
            'stop_loss': 0.02,
            'take_profit': 0.05,
            'lookback': 20,
            'atr_multiple': 2.0,
        },
        'indicators': ['ATR', 'RSI', 'SMA'],
        'constraints': {
            'max_position_size': 5,
            'max_daily_loss': 0.05,
        },
    }

    loader.register_strategy(example_strategy)
    print(f"\nTotal strategies: {len(loader.registry)}")
