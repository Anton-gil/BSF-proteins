"""
State Estimator

Estimates the RL observation vector from farmer inputs and sensor/weather data.
Bridges the gap between qualitative farmer observations and the numerical
10-dimensional state space the RL policy expects.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass, field

from src.translation.weather_client import WeatherClient, WeatherData
from src.translation.waste_translator import WasteTranslator


@dataclass
class FarmerObservation:
    """Qualitative observations recorded by the farmer during a check-in."""
    larvae_activity: str = "normal"      # sluggish | normal | very_active
    mortality_estimate: str = "none"     # none | few | some | many
    substrate_condition: str = "good"    # dry | good | wet | soggy
    smell: str = "normal"               # normal | ammonia | sour


@dataclass
class BatchInfo:
    """Tracking data for the current larvae batch."""
    start_date: datetime
    initial_count: int
    estimated_count: int
    container_area_cm2: float = 200.0
    last_feed_time: Optional[datetime] = None
    total_feed_kg: float = 0.0


class StateEstimator:
    """
    Estimates RL observation state from farmer inputs.

    Combines weather data, qualitative observations, and batch history
    to produce a 10-element observation array compatible with BSFEnv.

    Usage:
        estimator = StateEstimator()
        obs = estimator.estimate_state(batch_info, farmer_obs)
    """

    def __init__(
        self,
        weather_client: Optional[WeatherClient] = None,
        waste_translator: Optional[WasteTranslator] = None
    ):
        self.weather_client   = weather_client   or WeatherClient()
        self.waste_translator = waste_translator or WasteTranslator()

        # Pre-compute logistic growth curve (0 → 150 mg over 16 days)
        self._growth_curve = self._build_growth_curve()

        # Qualitative → quantitative mappings
        self._activity_to_modifier = {
            "sluggish":    0.85,
            "normal":      1.00,
            "very_active": 1.10,
        }
        self._mortality_to_rate = {
            "none": 0.995,
            "few":  0.980,
            "some": 0.950,
            "many": 0.850,
        }
        self._condition_to_moisture = {
            "dry":   45.0,
            "good":  70.0,
            "wet":   80.0,
            "soggy": 88.0,
        }
        self._smell_to_cn_offset = {
            "normal":  0.0,
            "ammonia": -5.0,   # Too much N → lower effective C:N
            "sour":    +5.0,   # Acidic / anaerobic → higher effective C:N
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_growth_curve() -> np.ndarray:
        """Logistic growth: ~0.04 mg on day 0 → ~150 mg on day 14."""
        days = np.arange(0, 17, dtype=float)
        K, r, t0 = 150.0, 0.5, 7.0
        curve = K / (1.0 + np.exp(-r * (days - t0)))
        curve[0] = 0.04
        return curve

    def _biomass_at_age(self, age_days: float, health: float = 1.0) -> float:
        """Linearly interpolate the growth curve and apply a health modifier."""
        age_days = max(0.0, min(16.0, age_days))
        idx = int(age_days)
        frac = age_days - idx
        if idx < len(self._growth_curve) - 1:
            biomass = (
                self._growth_curve[idx] * (1.0 - frac)
                + self._growth_curve[idx + 1] * frac
            )
        else:
            biomass = self._growth_curve[idx]
        return float(biomass * health)

    @staticmethod
    def _stage_at_age(age_days: float) -> int:
        """Map age (days) to discrete development stage 0–6."""
        breakpoints = [2, 4, 6, 8, 10, 12]
        for stage, bp in enumerate(breakpoints):
            if age_days < bp:
                return stage
        return 6

    # ------------------------------------------------------------------
    # Individual estimators
    # ------------------------------------------------------------------

    def estimate_survival_rate(
        self,
        batch_info: BatchInfo,
        farmer_obs: FarmerObservation
    ) -> float:
        """Weighted combination of count tracking and qualitative mortality."""
        if batch_info.initial_count > 0:
            count_based = batch_info.estimated_count / batch_info.initial_count
        else:
            count_based = 1.0

        obs_based = self._mortality_to_rate.get(farmer_obs.mortality_estimate, 0.98)
        return float(np.clip(0.7 * count_based + 0.3 * obs_based, 0.0, 1.0))

    def estimate_substrate_cn(
        self,
        recent_waste: Dict[str, float],
        farmer_obs: FarmerObservation
    ) -> float:
        """Derive C:N from the last feed mix and smell cue."""
        if recent_waste:
            base_cn, _ = self.waste_translator.calculate_mix_cn(recent_waste)
        else:
            base_cn = 25.0
        offset = self._smell_to_cn_offset.get(farmer_obs.smell, 0.0)
        return float(np.clip(base_cn + offset, 5.0, 100.0))

    def estimate_moisture(self, farmer_obs: FarmerObservation) -> float:
        """Map substrate condition label to a moisture percentage."""
        return float(self._condition_to_moisture.get(farmer_obs.substrate_condition, 70.0))

    # ------------------------------------------------------------------
    # Master estimator
    # ------------------------------------------------------------------

    def estimate_state(
        self,
        batch_info: BatchInfo,
        farmer_obs: Optional[FarmerObservation] = None,
        recent_waste: Optional[Dict[str, float]] = None,
        weather: Optional[WeatherData] = None
    ) -> np.ndarray:
        """
        Build a 10-element RL observation from farmer inputs.

        Observation layout (matches BSFEnv._get_observation):
            [0] age_days
            [1] biomass_mg
            [2] survival_rate
            [3] development_stage
            [4] cn_ratio
            [5] moisture_pct
            [6] substrate_remaining_pct
            [7] temperature_c
            [8] humidity_pct
            [9] hours_since_feed

        Args:
            batch_info: Current batch metadata
            farmer_obs: Qualitative check-in data (defaults to "all normal")
            recent_waste: {waste_name: kg} for the last feeding
            weather: Pre-fetched weather (fetched automatically if None)

        Returns:
            np.ndarray of shape (10,) and dtype float32
        """
        if farmer_obs is None:
            farmer_obs = FarmerObservation()
        if recent_waste is None:
            recent_waste = {}
        if weather is None:
            weather = self.weather_client.get_current_weather()

        # Age
        elapsed = (datetime.now() - batch_info.start_date).total_seconds()
        age_days = float(np.clip(elapsed / 86400.0, 0.0, 16.0))

        # Hours since last feed
        if batch_info.last_feed_time:
            hours_since = (datetime.now() - batch_info.last_feed_time).total_seconds() / 3600.0
        else:
            hours_since = 24.0

        # Health modifier from activity
        health = self._activity_to_modifier.get(farmer_obs.larvae_activity, 1.0)

        # Estimated substrate remaining (rough consumption proxy)
        if batch_info.total_feed_kg > 0:
            expected_g_consumed = age_days * 0.1 * batch_info.initial_count   # mg → g
            remaining = float(np.clip(
                100.0 - (expected_g_consumed / (batch_info.total_feed_kg * 1000)) * 50.0,
                0.0, 100.0
            ))
        else:
            remaining = 50.0

        obs = np.array([
            age_days,
            self._biomass_at_age(age_days, health),
            self.estimate_survival_rate(batch_info, farmer_obs),
            float(self._stage_at_age(age_days)),
            self.estimate_substrate_cn(recent_waste, farmer_obs),
            self.estimate_moisture(farmer_obs),
            remaining,
            float(weather.temperature_c),
            float(weather.humidity_pct),
            float(np.clip(hours_since, 0.0, 72.0)),
        ], dtype=np.float32)

        return obs
