"""
Base class for baseline policies.
"""

from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any, Optional


class BasePolicy(ABC):
    """
    Abstract base class for all policies (baselines and RL).

    Provides a common interface for evaluation.
    """

    def __init__(self, name: str = "BasePolicy"):
        self.name = name
        self.episode_count = 0
        self.total_steps = 0

    @abstractmethod
    def predict(
        self,
        observation: np.ndarray,
        deterministic: bool = True
    ) -> np.ndarray:
        """
        Predict action given observation.

        Args:
            observation: Current state (10,)
            deterministic: Whether to use deterministic policy

        Returns:
            Action array (4,)
        """
        pass

    def reset(self):
        """Reset policy state for new episode."""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Get policy information."""
        return {
            'name': self.name,
            'episode_count': self.episode_count,
            'total_steps': self.total_steps
        }
