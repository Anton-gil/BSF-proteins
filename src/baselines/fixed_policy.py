"""
Fixed schedule baseline policy.

Uses a constant feeding schedule regardless of conditions.
Represents what an inexperienced farmer might do.
"""

import numpy as np
from typing import Optional
from src.baselines.base_policy import BasePolicy


class FixedPolicy(BasePolicy):
    """
    Fixed schedule policy baseline.

    Always takes the same action regardless of observation.
    Represents a simple "feed the same amount every day" approach.

    Usage:
        policy = FixedPolicy()
        action = policy.predict(observation)

        # Custom fixed values
        policy = FixedPolicy(feed_cn=0.5, feed_amount=0.6, moisture=0.5, aeration=0.5)
    """

    def __init__(
        self,
        feed_cn: float = 0.5,       # Middle C:N (~20)
        feed_amount: float = 0.6,   # Slightly above-normal feeding
        moisture: float = 0.5,      # Medium moisture action
        aeration: float = 0.5,      # Medium aeration
        name: str = "FixedPolicy"
    ):
        """
        Args:
            feed_cn: Fixed C:N target (0–1 normalised)
            feed_amount: Fixed feed amount (0–1 normalised)
            moisture: Fixed moisture action (0–1 normalised)
            aeration: Fixed aeration level (0–1 normalised)
            name: Policy name
        """
        super().__init__(name=name)
        self.fixed_action = np.array(
            [feed_cn, feed_amount, moisture, aeration],
            dtype=np.float32
        )

    def predict(
        self,
        observation: np.ndarray,
        deterministic: bool = True
    ) -> np.ndarray:
        """
        Return fixed action regardless of observation.

        Args:
            observation: Ignored
            deterministic: Ignored

        Returns:
            Fixed action array
        """
        self.total_steps += 1
        return self.fixed_action.copy()

    def reset(self):
        """Reset for new episode."""
        self.episode_count += 1

    # ------------------------------------------------------------------
    # Preset variants
    # ------------------------------------------------------------------

    @classmethod
    def conservative(cls) -> 'FixedPolicy':
        """Conservative policy: low feeding, minimal interventions."""
        return cls(
            feed_cn=0.5,
            feed_amount=0.4,
            moisture=0.4,
            aeration=0.3,
            name="FixedPolicy-Conservative"
        )

    @classmethod
    def aggressive(cls) -> 'FixedPolicy':
        """Aggressive policy: high feeding and moisture management."""
        return cls(
            feed_cn=0.5,
            feed_amount=0.8,
            moisture=0.6,
            aeration=0.6,
            name="FixedPolicy-Aggressive"
        )

    @classmethod
    def balanced(cls) -> 'FixedPolicy':
        """Balanced policy: moderate feeding and mid-level interventions."""
        return cls(
            feed_cn=0.5,
            feed_amount=0.6,
            moisture=0.5,
            aeration=0.5,
            name="FixedPolicy-Balanced"
        )
