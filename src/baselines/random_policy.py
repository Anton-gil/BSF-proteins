"""
Random baseline policy.

Takes random actions — serves as the lower bound for performance.
"""

import numpy as np
from typing import Optional
from src.baselines.base_policy import BasePolicy


class RandomPolicy(BasePolicy):
    """
    Random policy baseline.

    Samples random actions uniformly from [0, 1]^4.
    Represents the worst reasonable policy — a useful lower bound.

    Usage:
        policy = RandomPolicy(seed=42)
        action = policy.predict(observation)
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Args:
            seed: Random seed for reproducibility
        """
        super().__init__(name="RandomPolicy")
        self.rng = np.random.default_rng(seed)

    def predict(
        self,
        observation: np.ndarray,
        deterministic: bool = True
    ) -> np.ndarray:
        """
        Return a uniformly random action.

        Args:
            observation: Ignored
            deterministic: Ignored (always random)

        Returns:
            Random action in [0, 1]^4
        """
        self.total_steps += 1
        return self.rng.random(4).astype(np.float32)

    def reset(self):
        """Reset for new episode."""
        self.episode_count += 1
