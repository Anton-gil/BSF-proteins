"""
Heuristic rule-based baseline policy.

Uses simple rules based on observations to make decisions.
Represents what a knowledgeable farmer might do intuitively.
"""

import numpy as np
from typing import Dict, Any
from src.baselines.base_policy import BasePolicy


class HeuristicPolicy(BasePolicy):
    """
    Heuristic rule-based policy.

    Uses simple if-then rules derived from the observation:
    - Adjust C:N feed toward optimal range
    - Scale feeding based on larval age and substrate level
    - Add water when too dry, ventilate when too wet
    - Raise aeration in hot or humid conditions

    This is the "smart farmer" baseline.

    Usage:
        policy = HeuristicPolicy()
        action = policy.predict(observation)
    """

    def __init__(self):
        super().__init__(name="HeuristicPolicy")

        # Observation space indices (must match BSFEnv._get_observation order)
        self.IDX_AGE = 0
        self.IDX_BIOMASS = 1
        self.IDX_SURVIVAL = 2
        self.IDX_STAGE = 3
        self.IDX_CN = 4
        self.IDX_MOISTURE = 5
        self.IDX_SUBSTRATE = 6
        self.IDX_TEMP = 7
        self.IDX_HUMIDITY = 8
        self.IDX_HOURS_SINCE_FEED = 9

    def predict(
        self,
        observation: np.ndarray,
        deterministic: bool = True
    ) -> np.ndarray:
        """
        Apply heuristic rules to determine action.

        Args:
            observation: Current state [10]
            deterministic: Ignored (rules are deterministic)

        Returns:
            Action array [4] in [0, 1]
        """
        self.total_steps += 1

        age_days = float(observation[self.IDX_AGE])
        current_cn = float(observation[self.IDX_CN])
        current_moisture = float(observation[self.IDX_MOISTURE])
        substrate_remaining = float(observation[self.IDX_SUBSTRATE])
        temperature = float(observation[self.IDX_TEMP])
        hours_since_feed = float(observation[self.IDX_HOURS_SINCE_FEED])

        # ---- RULE 1: Feed C:N target ----
        # Steer toward the 14–18 optimal window
        if current_cn < 14:
            feed_cn = 0.7    # High carbon feed → CN ↑
        elif current_cn > 22:
            feed_cn = 0.3    # High nitrogen feed → CN ↓
        else:
            feed_cn = 0.5    # Maintain current balance

        # ---- RULE 2: Feed amount ----
        # Base rate from larval age phase
        if age_days < 3:
            base_feed = 0.4   # Neonates eat little
        elif age_days < 8:
            base_feed = 0.7   # Peak exponential growth
        elif age_days < 12:
            base_feed = 0.8   # Heavy pre-prepupa feeding
        else:
            base_feed = 0.3   # Prepupa, appetite drops

        # Modulate for substrate level
        if substrate_remaining > 70:
            feed_amount = base_feed * 0.7   # Plenty left; ease off
        elif substrate_remaining < 20:
            feed_amount = min(1.0, base_feed * 1.3)   # Running low; top up
        else:
            feed_amount = base_feed

        # Emergency top-up if starving
        if hours_since_feed > 24 and substrate_remaining < 30:
            feed_amount = min(1.0, feed_amount + 0.2)

        # ---- RULE 3: Moisture action ----
        # Natural evaporation = -0.2%/step already; ventilating adds another -0.2%.
        # Only ventilate when genuinely near-lethal (>83%).
        # Pro-actively add water when drifting below the comfortable zone (<62%).
        if current_moisture < 62:
            moisture_action = 0.5    # Add water  → bucket 1
        elif current_moisture > 83:
            moisture_action = 0.85   # Ventilate  → bucket 2
        else:
            moisture_action = 0.15   # Do nothing → bucket 0

        # ---- RULE 4: Aeration level ----
        if temperature > 33 or current_moisture > 75:
            aeration = 0.8    # High — cool and oxygenate
        elif temperature < 25:
            aeration = 0.2    # Low — conserve heat
        else:
            aeration = 0.5    # Medium

        action = np.array(
            [feed_cn, feed_amount, moisture_action, aeration],
            dtype=np.float32
        )

        return np.clip(action, 0.0, 1.0)

    def reset(self):
        """Reset for new episode."""
        self.episode_count += 1
