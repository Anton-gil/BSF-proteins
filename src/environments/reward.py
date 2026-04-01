"""
BSF Reward Function

Calculates rewards for RL agent based on:
- Biomass gain (positive)
- Survival rate (positive for high, penalty for deaths)
- Feed efficiency (penalty for waste)
- Resource costs (penalty for water/energy use)
"""

import numpy as np
import yaml
from pathlib import Path
from typing import Dict, Tuple, Optional, NamedTuple
from dataclasses import dataclass


@dataclass
class RewardComponents:
    """Breakdown of reward for logging/debugging."""
    biomass_reward: float
    survival_reward: float
    feed_efficiency_reward: float
    resource_cost: float
    terminal_bonus: float
    total_reward: float

    def to_dict(self) -> Dict[str, float]:
        return {
            'biomass': self.biomass_reward,
            'survival': self.survival_reward,
            'feed_efficiency': self.feed_efficiency_reward,
            'resource_cost': self.resource_cost,
            'terminal_bonus': self.terminal_bonus,
            'total': self.total_reward
        }


class RewardCalculator:
    """
    Calculates step rewards for BSF environment.

    Usage:
        calc = RewardCalculator()
        reward, components = calc.calculate_reward(
            prev_biomass=50.0,
            curr_biomass=52.0,
            prev_population=1000,
            curr_population=998,
            feed_given=100,
            feed_consumed=80,
            water_used=50,
            is_terminal=False,
            harvest_success=False
        )
    """

    def __init__(self, config_path: str = "configs/training.yaml"):
        """Load reward weights from config."""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self.weights = config['reward']

        # Extract weights
        self.alpha = self.weights['biomass_gain']    # 1.0
        self.beta = self.weights['feed_waste']       # 0.3
        self.gamma = self.weights['mortality']       # 2.0
        self.delta = self.weights['resource_cost']   # 0.1

        # Load environment config for normalization bounds
        with open("configs/environment.yaml", 'r') as f:
            env_config = yaml.safe_load(f)

        self.max_biomass = env_config['larvae']['max_weight_mg']
        self.initial_biomass = env_config['larvae']['initial_weight_mg']
        self.harvest_target = env_config['larvae']['harvest_target_mg']

        # Normalization constants
        self.max_daily_growth = 20.0   # mg per day (rough max)
        self.max_feed_per_step = 500   # grams
        self.max_water_per_step = 200  # ml

    def biomass_reward(
        self,
        prev_biomass_mg: float,
        curr_biomass_mg: float,
        timestep_hours: float = 4.0
    ) -> float:
        """
        Calculate reward for biomass gain.

        Normalized to roughly 0-1 range for typical growth.

        Args:
            prev_biomass_mg: Previous average larva weight
            curr_biomass_mg: Current average larva weight
            timestep_hours: Duration of timestep

        Returns:
            Biomass reward (can be negative if weight lost)
        """
        # Raw gain
        gain = curr_biomass_mg - prev_biomass_mg

        # Normalize by expected max growth per timestep
        # Max daily growth ~20mg, so per 4h step ~3.3mg
        max_step_growth = self.max_daily_growth * (timestep_hours / 24.0)

        # Normalized gain (-1 to ~1 range)
        normalized_gain = gain / max_step_growth if max_step_growth > 0 else 0

        # Clip to reasonable range
        return float(np.clip(normalized_gain, -1.0, 1.5))

    def survival_reward(
        self,
        prev_population: int,
        curr_population: int,
        initial_population: int
    ) -> float:
        """
        Calculate reward based on survival.

        Two components:
        1. Penalty for deaths this timestep
        2. Bonus for maintaining high overall survival rate

        Args:
            prev_population: Population at start of timestep
            curr_population: Population at end of timestep
            initial_population: Starting population of batch

        Returns:
            Survival reward (negative for deaths, positive for good survival)
        """
        if prev_population <= 0:
            return -1.0  # All dead

        # Deaths this timestep
        deaths = prev_population - curr_population
        death_rate = deaths / prev_population

        # Penalty for deaths (scaled)
        # 1% death rate = -0.1 penalty, 10% = -1.0
        death_penalty = -10.0 * death_rate

        # Continuous survival bonus — every step, the agent gets rewarded
        # proportional to how many larvae are still alive. Previously this
        # only kicked in above 50% survival; now it's always positive so
        # the agent consistently associates keeping larvae alive with reward.
        # This is called "dense reward shaping" — giving signal every step
        # instead of waiting until the end of the 16-day cycle.
        overall_survival = curr_population / initial_population
        survival_bonus = 0.3 * overall_survival  # 0 to 0.3 every step

        return death_penalty + survival_bonus

    def feed_efficiency_reward(
        self,
        feed_given_g: float,
        feed_consumed_g: float,
        biomass_gain_mg: float,
        population: int
    ) -> float:
        """
        Calculate reward for feed efficiency.

        Penalize:
        - Giving too much feed (waste)
        - Giving too little (starvation risk)

        Reward:
        - Good conversion ratio

        Args:
            feed_given_g: Feed added this timestep (grams)
            feed_consumed_g: Feed actually consumed (grams)
            biomass_gain_mg: Total biomass gained (mg per larva)
            population: Current population

        Returns:
            Feed efficiency reward
        """
        if feed_given_g <= 0:
            # No feed given — raise penalty to break the starvation exploit.
            # Previously -0.1 was cheap enough that the agent preferred zero feed
            # over the waste penalty from overfeeding. Now it costs -0.5 per step,
            # which is 5x more expensive than a small waste, forcing the agent
            # to learn to feed optimally rather than not at all.
            if population > 0:
                return -0.5
            return 0.0

        # Feed waste ratio
        waste = max(0, feed_given_g - feed_consumed_g)
        waste_ratio = waste / feed_given_g

        # Waste penalty (0 to -1)
        waste_penalty = -waste_ratio

        # Feed Conversion Ratio (FCR) bonus
        # Good FCR for BSF is 2-4 (kg feed per kg weight gain)
        # Lower is better
        total_gain_g = (biomass_gain_mg * population) / 1000  # Convert to grams

        if total_gain_g > 0:
            fcr = feed_consumed_g / total_gain_g

            # FCR bonus: 2.0 = best (+0.3), 4.0 = ok (0), >6 = bad (-0.2)
            if fcr <= 2.0:
                fcr_bonus = 0.3
            elif fcr <= 4.0:
                fcr_bonus = 0.3 * (4.0 - fcr) / 2.0
            elif fcr <= 6.0:
                fcr_bonus = -0.1 * (fcr - 4.0) / 2.0
            else:
                fcr_bonus = -0.2
        else:
            fcr_bonus = 0.0

        return waste_penalty + fcr_bonus

    def resource_cost_penalty(
        self,
        water_used_ml: float,
        aeration_level: int
    ) -> float:
        """
        Calculate penalty for resource usage.

        Small penalty to encourage efficiency, but not dominate.

        Args:
            water_used_ml: Water added this timestep
            aeration_level: 0=low, 1=medium, 2=high

        Returns:
            Resource cost penalty (always <= 0)
        """
        # Water cost (normalized)
        water_cost = water_used_ml / self.max_water_per_step * 0.1

        # Aeration cost
        aeration_costs = {0: 0.0, 1: 0.02, 2: 0.05}
        aeration_cost = aeration_costs.get(aeration_level, 0.02)

        return -(water_cost + aeration_cost)

    def terminal_reward(
        self,
        final_biomass_mg: float,
        final_population: int,
        initial_population: int,
        days_elapsed: int,
        target_days: int = 14
    ) -> float:
        """
        Calculate terminal reward at end of episode.

        Bonus for:
        - Reaching harvest target biomass
        - High survival rate
        - Efficient timeline

        Args:
            final_biomass_mg: Final average larva weight
            final_population: Final population
            initial_population: Starting population
            days_elapsed: Days taken
            target_days: Target harvest day

        Returns:
            Terminal bonus (can be large positive or negative)
        """
        # Biomass achievement (0 to 2)
        biomass_ratio = final_biomass_mg / self.harvest_target
        if biomass_ratio >= 1.0:
            biomass_bonus = 1.0 + min(1.0, (biomass_ratio - 1.0))  # Max 2.0
        else:
            biomass_bonus = biomass_ratio  # 0 to 1

        # Survival achievement (0 to 1)
        survival_rate = final_population / initial_population if initial_population > 0 else 0
        survival_bonus = survival_rate

        # Time efficiency (small bonus for finishing on time)
        if days_elapsed <= target_days:
            time_bonus = 0.2
        else:
            # Small penalty for taking too long
            time_bonus = -0.1 * (days_elapsed - target_days)

        # Combined terminal reward
        terminal = (2.0 * biomass_bonus) + (1.5 * survival_bonus) + time_bonus

        # Scale up for significance
        return terminal * 2.0

    def calculate_reward(
        self,
        prev_biomass_mg: float,
        curr_biomass_mg: float,
        prev_population: int,
        curr_population: int,
        initial_population: int,
        feed_given_g: float,
        feed_consumed_g: float,
        water_used_ml: float,
        aeration_level: int = 1,
        timestep_hours: float = 4.0,
        is_terminal: bool = False,
        days_elapsed: int = 0
    ) -> Tuple[float, RewardComponents]:
        """
        Calculate total reward for a timestep.

        Args:
            prev_biomass_mg: Previous average larva weight
            curr_biomass_mg: Current average larva weight
            prev_population: Population at timestep start
            curr_population: Population at timestep end
            initial_population: Batch starting population
            feed_given_g: Feed added (grams)
            feed_consumed_g: Feed consumed (grams)
            water_used_ml: Water added (ml)
            aeration_level: 0/1/2
            timestep_hours: Timestep duration
            is_terminal: Whether episode ended
            days_elapsed: Days since batch start

        Returns:
            Tuple of (total_reward, RewardComponents)
        """
        # Calculate each component
        r_biomass = self.biomass_reward(prev_biomass_mg, curr_biomass_mg, timestep_hours)

        r_survival = self.survival_reward(prev_population, curr_population, initial_population)

        biomass_gain = curr_biomass_mg - prev_biomass_mg
        r_feed = self.feed_efficiency_reward(
            feed_given_g, feed_consumed_g, biomass_gain, curr_population
        )

        r_resource = self.resource_cost_penalty(water_used_ml, aeration_level)

        # Terminal bonus
        if is_terminal:
            r_terminal = self.terminal_reward(
                curr_biomass_mg, curr_population, initial_population, days_elapsed
            )
        else:
            r_terminal = 0.0

        # Weighted combination
        total_reward = (
            self.alpha * r_biomass          # Reward for growth
            + self.gamma * r_survival       # Reward/penalty for survival
            + self.beta * r_feed            # Feed efficiency (can be + or -)
            + self.delta * r_resource       # Resource cost (always -)
            + r_terminal                    # Terminal bonus
        )

        components = RewardComponents(
            biomass_reward=self.alpha * r_biomass,
            survival_reward=self.gamma * r_survival,
            feed_efficiency_reward=self.beta * r_feed,
            resource_cost=self.delta * r_resource,
            terminal_bonus=r_terminal,
            total_reward=total_reward
        )

        return total_reward, components


class RewardShaper:
    """
    Optional reward shaping for faster learning.

    Adds potential-based shaping that doesn't change optimal policy.
    """

    def __init__(self, gamma: float = 0.99):
        """
        Args:
            gamma: Discount factor (must match PPO gamma)
        """
        self.gamma = gamma

    def potential(self, biomass_mg: float, survival_rate: float) -> float:
        """
        Calculate state potential.

        Higher potential = better state.
        """
        # Potential based on progress toward goal
        biomass_potential = biomass_mg / 150.0  # Normalized to target
        survival_potential = survival_rate

        return biomass_potential + survival_potential

    def shaping_reward(
        self,
        prev_biomass: float,
        curr_biomass: float,
        prev_survival: float,
        curr_survival: float
    ) -> float:
        """
        Calculate potential-based shaping reward.

        F(s, s') = γ × Φ(s') - Φ(s)

        This is guaranteed not to change the optimal policy.
        """
        prev_potential = self.potential(prev_biomass, prev_survival)
        curr_potential = self.potential(curr_biomass, curr_survival)

        return self.gamma * curr_potential - prev_potential


def calculate_batch_score(
    final_biomass_mg: float,
    final_population: int,
    initial_population: int,
    total_feed_kg: float,
    days_elapsed: int
) -> Dict[str, float]:
    """
    Calculate final batch performance metrics.

    Useful for evaluation and comparison.

    Args:
        final_biomass_mg: Final average larva weight
        final_population: Final population
        initial_population: Starting population
        total_feed_kg: Total feed used (kg)
        days_elapsed: Days elapsed

    Returns:
        Dict of performance metrics
    """
    # Total biomass produced (kg)
    total_biomass_kg = (final_biomass_mg * final_population) / 1_000_000

    # Survival rate
    survival_rate = final_population / initial_population if initial_population > 0 else 0

    # Feed Conversion Ratio (kg feed / kg biomass)
    fcr = total_feed_kg / total_biomass_kg if total_biomass_kg > 0 else float('inf')

    # Bioconversion rate (% of feed converted to biomass)
    bioconversion = (total_biomass_kg / total_feed_kg * 100) if total_feed_kg > 0 else 0

    # Daily growth rate (mg/day)
    daily_growth = final_biomass_mg / days_elapsed if days_elapsed > 0 else 0

    # Composite score (weighted combination)
    # Higher is better
    score = (
        0.4 * (final_biomass_mg / 150)                          # Biomass achievement
        + 0.3 * survival_rate                                    # Survival
        + 0.2 * (1 / fcr if fcr > 0 and fcr != float('inf') else 0)  # Feed efficiency
        + 0.1 * (14 / days_elapsed if days_elapsed > 0 else 0)  # Time efficiency
    )

    return {
        'total_biomass_kg': total_biomass_kg,
        'survival_rate': survival_rate,
        'fcr': fcr,
        'bioconversion_pct': bioconversion,
        'daily_growth_mg': daily_growth,
        'composite_score': score
    }
