"""
Experiment Queue - FIFO with Priority Levels
Authority: ZERO (audit all enqueue/dequeue)
"""

from enum import Enum
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
import logging
import threading

logger = logging.getLogger(__name__)

class QueuePriority(Enum):
    """Priority levels - NORMAL is default"""
    LOW = 3
    NORMAL = 2
    HIGH = 1

@dataclass
class QueuedExperiment:
    """Single experiment in queue"""
    experiment_id: str
    correlation_id: str
    name: str
    strategy_code: str
    parameters: dict
    priority: QueuePriority
    enqueued_at: datetime
    position: int = 0
    dequeued_at: Optional[datetime] = None

class ExperimentQueue:
    """
    FIFO queue with priority levels
    - Max 100 experiments queued
    - HIGH > NORMAL > LOW priority
    - Thread-safe operations
    """

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.queue: List[QueuedExperiment] = []
        self.lock = threading.RLock()
        self.experiment_map: Dict[str, QueuedExperiment] = {}

    def enqueue(
        self,
        experiment_id: str,
        correlation_id: str,
        name: str,
        strategy_code: str,
        parameters: dict,
        priority: QueuePriority = QueuePriority.NORMAL
    ) -> Optional[int]:
        """
        Add experiment to queue
        Returns: position in queue, or None if full
        """
        with self.lock:
            if len(self.queue) >= self.max_size:
                logger.error(f"Queue full at {self.max_size}")
                return None

            exp = QueuedExperiment(
                experiment_id=experiment_id,
                correlation_id=correlation_id,
                name=name,
                strategy_code=strategy_code,
                parameters=parameters,
                priority=priority,
                enqueued_at=datetime.now()
            )

            # Insert by priority: HIGH first, then NORMAL, then LOW
            insert_idx = len(self.queue)
            for idx, queued in enumerate(self.queue):
                if priority.value < queued.priority.value:  # Lower value = higher priority
                    insert_idx = idx
                    break

            self.queue.insert(insert_idx, exp)
            self.experiment_map[experiment_id] = exp

            # Update positions
            for idx, queued in enumerate(self.queue):
                queued.position = idx

            logger.info(f"Enqueued {experiment_id} at position {insert_idx}")
            return insert_idx

    def dequeue(self) -> Optional[QueuedExperiment]:
        """
        Remove and return first experiment (FIFO within same priority)
        """
        with self.lock:
            if not self.queue:
                return None

            exp = self.queue.pop(0)
            exp.dequeued_at = datetime.now()

            # Update positions
            for idx, queued in enumerate(self.queue):
                queued.position = idx

            logger.info(f"Dequeued {exp.experiment_id}")
            return exp

    def get_position(self, experiment_id: str) -> Optional[int]:
        """Get current queue position of experiment"""
        with self.lock:
            exp = self.experiment_map.get(experiment_id)
            if exp:
                return exp.position
            return None

    def get_experiment(self, experiment_id: str) -> Optional[QueuedExperiment]:
        """Get queued experiment by ID"""
        with self.lock:
            return self.experiment_map.get(experiment_id)

    def remove(self, experiment_id: str) -> bool:
        """Remove experiment from queue (e.g., on cancel)"""
        with self.lock:
            exp = self.experiment_map.pop(experiment_id, None)
            if exp and exp in self.queue:
                self.queue.remove(exp)
                # Update positions
                for idx, queued in enumerate(self.queue):
                    queued.position = idx
                logger.info(f"Removed {experiment_id} from queue")
                return True
            return False

    def size(self) -> int:
        """Current queue size"""
        with self.lock:
            return len(self.queue)

    def get_stats(self) -> dict:
        """Queue statistics by priority"""
        with self.lock:
            stats = {
                "high": sum(1 for e in self.queue if e.priority == QueuePriority.HIGH),
                "normal": sum(1 for e in self.queue if e.priority == QueuePriority.NORMAL),
                "low": sum(1 for e in self.queue if e.priority == QueuePriority.LOW),
            }
            return stats

    def clear(self):
        """Clear queue (testing only)"""
        with self.lock:
            self.queue.clear()
            self.experiment_map.clear()

# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    import sys

    q = ExperimentQueue(max_size=5)

    # Test 1: Enqueue normal priority
    pos1 = q.enqueue("exp1", "corr1", "Test1", "code1", {}, QueuePriority.NORMAL)
    assert pos1 == 0, f"Expected pos 0, got {pos1}"
    print("[PASS] Test 1: Normal enqueue")

    # Test 2: Enqueue high priority (should go first)
    pos2 = q.enqueue("exp2", "corr2", "Test2", "code2", {}, QueuePriority.HIGH)
    assert pos2 == 0, f"Expected pos 0 for HIGH, got {pos2}"
    assert q.get_position("exp1") == 1, "exp1 should now be at position 1"
    print("[PASS] Test 2: High priority inserted first")

    # Test 3: Dequeue order
    exp = q.dequeue()
    assert exp.experiment_id == "exp2", "Should dequeue high priority first"
    print("[PASS] Test 3: FIFO dequeue respects priority")

    # Test 4: Max size
    q.clear()
    for i in range(5):
        pos = q.enqueue(f"exp{i}", f"corr{i}", f"Test{i}", f"code{i}", {})
        assert pos is not None, f"Should enqueue exp{i}"

    pos_fail = q.enqueue("exp_over", "corr_over", "TestOver", "code_over", {})
    assert pos_fail is None, "Should reject when queue full"
    print("[PASS] Test 4: Max size enforcement")

    # Test 5: Remove
    q.clear()
    q.enqueue("exp_rem", "corr_rem", "TestRem", "code_rem", {})
    removed = q.remove("exp_rem")
    assert removed and q.size() == 0, "Should remove from queue"
    print("[PASS] Test 5: Remove from queue")

    print("\n[PASS] All queue tests passed")
