"""
BSF Larvae Gymnasium Environment

A Gymnasium-compatible environment for training RL agents
to optimize BSF larvae feeding strategies.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import yaml
from pathlib import Path
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass, field

from src.environments.growth_model import GrowthModel, LarvaeState, create_initial_state
from src.environments.mortality_model import MortalityModel
from src.environments.reward import RewardCalculator, RewardComponents


@dataclass
class BatchState:
    """Complete state of a BSF batch."""
    # Larvae state
    larvae: LarvaeState

    # Environment conditions
    temperature_c: float = 28.0
    humidity_pct: float = 65.0

    # Tracking
    initial_population: int = 1000
    hours_since_feed: float = 0.0
    total_feed_g: float = 0.0
    total_water_ml: float = 0.0

    # Area (for density calculations)
    area_cm2: float = 200.0  # 10cm x 20cm default


class BSFEnv(gym.Env):
    """
    BSF Larvae Feed Optimization Environment.

    The agent learns to optimize feeding strategies by:
    - Choosing feed C:N ratio (waste mix selection)
    - Choosing feed amount
    - Managing moisture (add water or ventilate)
    - Setting aeration level

    The environment simulates larvae growth, mortality, and
    rewards efficient production of healthy, heavy larvae.

    Usage:
        env = BSFEnv()
        obs, info = env.reset()

        for _ in range(max_steps):
            action = agent.predict(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            if terminated or truncated:
                break
    """

    metadata = {"render_modes": ["human", "ansi"], "render_fps": 1}

    def __init__(
        self,
        config_path: str = "configs/environment.yaml",
        training_config_path: str = "configs/training.yaml",
        render_mode: Optional[str] = None,
        stochastic_weather: bool = True,
        initial_population: int = 1000,
        area_cm2: float = 200.0
    ):
        """
        Initialize BSF environment.

        Args:
            config_path: Path to environment config
            training_config_path: Path to training config
            render_mode: "human" or "ansi" for rendering
            stochastic_weather: Whether to vary temperature/humidity
            initial_population: Starting larvae count
            area_cm2: Growing area in cm²
        """
        super().__init__()

        # Load configs
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        with open(training_config_path, 'r', encoding='utf-8') as f:
            self.training_config = yaml.safe_load(f)

        self.render_mode = render_mode
        self.stochastic_weather = stochastic_weather
        self.initial_population = initial_population
        self.area_cm2 = area_cm2

        # Initialize models
        self.growth_model = GrowthModel(config_path)
        self.mortality_model = MortalityModel(config_path)
        self.reward_calculator = RewardCalculator(training_config_path)

        # Simulation parameters
        self.sim = self.config['simulation']
        self.timestep_hours = self.sim['timestep_hours']   # 4 hours
        self.steps_per_day = self.sim['steps_per_day']     # 6
        self.max_days = self.sim['episode_max_days']       # 16
        self.max_steps = self.max_days * self.steps_per_day

        # State bounds from config
        bounds = self.config['state_bounds']
        action_bounds = self.config['action_bounds']

        # Define observation space (10 variables)
        self.observation_space = spaces.Box(
            low=np.array([
                bounds['age_days'][0],                     # age_days
                bounds['biomass_mg'][0],                   # biomass_mg
                bounds['survival_rate'][0],                # survival_rate
                bounds['development_stage'][0],            # development_stage
                bounds['cn_ratio'][0],                     # cn_ratio
                bounds['moisture_pct'][0],                 # moisture_pct
                bounds['substrate_remaining_pct'][0],      # substrate_remaining
                bounds['temperature_c'][0],                # temperature_c
                bounds['humidity_pct'][0],                 # humidity_pct
                0.0                                        # hours_since_feed
            ], dtype=np.float32),
            high=np.array([
                bounds['age_days'][1],
                bounds['biomass_mg'][1],
                bounds['survival_rate'][1],
                bounds['development_stage'][1],
                bounds['cn_ratio'][1],
                bounds['moisture_pct'][1],
                bounds['substrate_remaining_pct'][1],
                bounds['temperature_c'][1],
                bounds['humidity_pct'][1],
                72.0  # max hours since feed
            ], dtype=np.float32),
            dtype=np.float32
        )

        # Define action space (4 continuous actions), all in [0, 1]
        self.action_space = spaces.Box(
            low=np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32),
            dtype=np.float32
        )

        # Action scaling parameters
        # feed_cn_adjustment: [-5, 5] → actual target = base 20 ± 5 → [15, 25]
        cn_adj = action_bounds['feed_cn_adjustment']
        base_cn = 20.0
        self.cn_range = (base_cn + cn_adj[0], base_cn + cn_adj[1])   # (15, 25)

        feed_mult = action_bounds['feed_amount_multiplier']
        self.feed_range = (feed_mult[0], feed_mult[1])                # (0.5, 2.0)

        # State tracking
        self.state: Optional[BatchState] = None
        self.current_step = 0
        self.episode_rewards = []

        # Weather simulation parameters
        self.base_temperature = 28.0
        self.base_humidity = 65.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_observation(self) -> np.ndarray:
        """Convert current state to observation array."""
        if self.state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")

        larvae = self.state.larvae

        obs = np.array([
            larvae.age_hours / 24.0,                                      # age_days
            larvae.biomass_mg,                                            # biomass_mg
            larvae.population / self.state.initial_population,           # survival_rate
            float(self.growth_model.get_development_stage(larvae.development_sum)),  # stage
            larvae.substrate_cn,                                          # cn_ratio
            larvae.substrate_moisture,                                    # moisture_pct
            larvae.substrate_remaining,                                   # substrate_remaining
            self.state.temperature_c,                                     # temperature_c
            self.state.humidity_pct,                                      # humidity_pct
            min(72.0, self.state.hours_since_feed)                        # hours_since_feed
        ], dtype=np.float32)

        # Clip to observation space bounds
        obs = np.clip(obs, self.observation_space.low, self.observation_space.high)
        return obs

    def _scale_action(self, action: np.ndarray) -> Tuple[float, float, int, int]:
        """
        Scale normalized action [0,1] to actual values.

        Returns:
            Tuple of (feed_cn, feed_multiplier, moisture_action, aeration_level)
        """
        # Feed C:N target (15-25)
        feed_cn = self.cn_range[0] + action[0] * (self.cn_range[1] - self.cn_range[0])

        # Feed amount multiplier (0.5-2.0; < 0.1 → no feed)
        if action[1] < 0.1:
            feed_multiplier = 0.0
        else:
            feed_multiplier = self.feed_range[0] + action[1] * (self.feed_range[1] - self.feed_range[0])

        # Moisture action  0=none | 1=add water | 2=ventilate
        if action[2] < 0.33:
            moisture_action = 0
        elif action[2] < 0.67:
            moisture_action = 1
        else:
            moisture_action = 2

        # Aeration level  0=low | 1=medium | 2=high
        if action[3] < 0.33:
            aeration_level = 0
        elif action[3] < 0.67:
            aeration_level = 1
        else:
            aeration_level = 2

        return float(feed_cn), float(feed_multiplier), int(moisture_action), int(aeration_level)

    def _simulate_weather(self) -> Tuple[float, float]:
        """
        Simulate temperature and humidity for the current step.

        Returns:
            Tuple of (temperature_c, humidity_pct)
        """
        if not self.stochastic_weather:
            return self.base_temperature, self.base_humidity

        # Sinusoidal daily variation (warmer midday)
        hour_of_day = (self.current_step * self.timestep_hours) % 24
        daily_temp_variation = 3.0 * np.sin(np.pi * (hour_of_day - 6) / 12)

        # Day-to-day variation seeded per day for consistency within a day
        day = self.current_step // self.steps_per_day
        rng = np.random.default_rng(day * 1000 + 7)
        random_variation = float(rng.uniform(-2, 2))

        temperature = self.base_temperature + daily_temp_variation + random_variation
        temperature = float(np.clip(temperature, 20, 38))

        # Humidity loosely anti-correlated with temperature
        humidity = self.base_humidity - (temperature - self.base_temperature) * 2
        humidity += float(rng.uniform(-5, 5))
        humidity = float(np.clip(humidity, 40, 85))

        return temperature, humidity

    def _calculate_feed_amount(self, multiplier: float) -> float:
        """
        Calculate actual feed amount (grams) based on multiplier and larvae state.
        """
        if multiplier <= 0 or self.state is None:
            return 0.0

        larvae = self.state.larvae

        # Base rate from config (mg per larva per day)
        base_rate = self.config['feeding']['baseline_rate_mg_per_larva']

        # Age-based multiplier
        age_days = larvae.age_hours / 24.0
        age_mult = self.growth_model.get_age_feeding_multiplier(age_days)

        # Scale to timestep and convert to grams for the whole population
        timestep_fraction = self.timestep_hours / 24.0
        feed_per_larva_mg = base_rate * age_mult * timestep_fraction * multiplier
        total_feed_g = (feed_per_larva_mg * larvae.population) / 1000.0

        return float(total_feed_g)

    def _calculate_water_amount(self, moisture_action: int) -> float:
        """
        Calculate water to add (ml) based on moisture action.

        Negative value = drying effect from ventilation.
        """
        if self.state is None:
            return 0.0

        if moisture_action == 0:
            return 0.0
        elif moisture_action == 1:
            # Add water proportional to moisture deficit from target 70%
            current = self.state.larvae.substrate_moisture
            deficit = max(0.0, 70.0 - current)
            return deficit * 2.0
        else:  # ventilate
            return -10.0

    # ------------------------------------------------------------------
    # Gymnasium API
    # ------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Reset environment to initial state.

        Returns:
            (observation, info)
        """
        super().reset(seed=seed)

        if seed is not None:
            np.random.seed(seed)

        # Randomise base weather for this episode
        if self.stochastic_weather:
            self.base_temperature = float(np.random.uniform(25, 32))
            self.base_humidity = float(np.random.uniform(55, 75))
        else:
            self.base_temperature = 28.0
            self.base_humidity = 65.0

        # Randomise initial substrate conditions slightly
        initial_cn = float(np.random.uniform(18, 22)) if self.stochastic_weather else 20.0
        initial_moisture = float(np.random.uniform(65, 75)) if self.stochastic_weather else 70.0

        larvae_state = create_initial_state(
            initial_larvae_count=self.initial_population,
            initial_moisture=initial_moisture,
            initial_cn=initial_cn
        )

        # Reset step counter first so _simulate_weather works correctly
        self.current_step = 0
        self.episode_rewards = []

        temp, humidity = self._simulate_weather()

        self.state = BatchState(
            larvae=larvae_state,
            temperature_c=temp,
            humidity_pct=humidity,
            initial_population=self.initial_population,
            hours_since_feed=0.0,
            total_feed_g=0.0,
            total_water_ml=0.0,
            area_cm2=self.area_cm2
        )

        observation = self._get_observation()
        info = {
            'day': 0,
            'population': self.initial_population,
            'biomass_mg': larvae_state.biomass_mg,
            'temperature_c': temp,
            'humidity_pct': humidity
        }

        return observation, info

    def step(
        self,
        action: np.ndarray
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Execute one 4-hour timestep.

        Returns:
            (observation, reward, terminated, truncated, info)
        """
        if self.state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")

        # Snapshot previous state for reward calculation
        prev_biomass = self.state.larvae.biomass_mg
        prev_population = self.state.larvae.population

        # Decode action
        feed_cn, feed_mult, moisture_action, aeration_level = self._scale_action(action)

        # Derive physical quantities
        feed_amount_g = self._calculate_feed_amount(feed_mult)
        water_amount_ml = self._calculate_water_amount(moisture_action)

        # Advance weather
        self.state.temperature_c, self.state.humidity_pct = self._simulate_weather()

        # ---- Growth model step ----
        new_larvae_state = self.growth_model.step(
            state=self.state.larvae,
            temperature_c=self.state.temperature_c,
            feed_added_g=feed_amount_g,
            feed_cn=feed_cn,
            water_added_ml=max(0.0, water_amount_ml),
            timestep_hours=self.timestep_hours
        )

        # ---- Mortality model step ----
        new_population, deaths, mortality_factors = self.mortality_model.apply_mortality(
            population=new_larvae_state.population,
            temperature_c=self.state.temperature_c,
            moisture_pct=new_larvae_state.substrate_moisture,
            cn_ratio=new_larvae_state.substrate_cn,
            area_cm2=self.state.area_cm2,
            substrate_remaining_pct=new_larvae_state.substrate_remaining,
            hours_without_feed=self.state.hours_since_feed if feed_amount_g == 0 else 0.0,
            timestep_hours=self.timestep_hours
        )

        # Commit updated population
        new_larvae_state.population = new_population

        # Update batch state
        self.state.larvae = new_larvae_state
        self.state.total_feed_g += feed_amount_g
        self.state.total_water_ml += max(0.0, water_amount_ml)

        if feed_amount_g > 0:
            self.state.hours_since_feed = 0.0
        else:
            self.state.hours_since_feed += self.timestep_hours

        self.current_step += 1

        # ---- Termination checks ----
        terminated = False
        truncated = False
        harvest_success = False

        if new_population <= 0:
            terminated = True

        target_biomass = self.config['larvae']['harvest_target_mg']
        if new_larvae_state.biomass_mg >= target_biomass:
            terminated = True
            harvest_success = True

        if self.current_step >= self.max_steps:
            truncated = True

        # ---- Reward ----
        days_elapsed = self.current_step // self.steps_per_day

        # Estimated feed consumed via feed-availability saturation curve
        feed_consumed = feed_amount_g * self.growth_model.feed_availability_effect(
            new_larvae_state.substrate_remaining
        )

        reward, reward_components = self.reward_calculator.calculate_reward(
            prev_biomass_mg=prev_biomass,
            curr_biomass_mg=new_larvae_state.biomass_mg,
            prev_population=prev_population,
            curr_population=new_population,
            initial_population=self.state.initial_population,
            feed_given_g=feed_amount_g,
            feed_consumed_g=feed_consumed,
            water_used_ml=max(0.0, water_amount_ml),
            aeration_level=aeration_level,
            timestep_hours=self.timestep_hours,
            is_terminal=terminated or truncated,
            days_elapsed=days_elapsed
        )

        self.episode_rewards.append(reward)

        # ---- Observation ----
        observation = self._get_observation()

        # ---- Info dict ----
        info = {
            'day': days_elapsed,
            'step': self.current_step,
            'population': new_population,
            'deaths': deaths,
            'biomass_mg': new_larvae_state.biomass_mg,
            'survival_rate': new_population / self.state.initial_population,
            'temperature_c': self.state.temperature_c,
            'moisture_pct': new_larvae_state.substrate_moisture,
            'cn_ratio': new_larvae_state.substrate_cn,
            'substrate_remaining': new_larvae_state.substrate_remaining,
            'feed_given_g': feed_amount_g,
            'total_feed_kg': self.state.total_feed_g / 1000.0,
            'reward_components': reward_components.to_dict(),
            'mortality_factors': {
                'temperature': mortality_factors.temperature,
                'moisture': mortality_factors.moisture,
                'starvation': mortality_factors.starvation
            },
            'harvest_success': harvest_success
        }

        if terminated or truncated:
            info['episode'] = {
                'total_reward': sum(self.episode_rewards),
                'length': self.current_step,
                'final_biomass_mg': new_larvae_state.biomass_mg,
                'final_survival_rate': new_population / self.state.initial_population,
                'total_feed_kg': self.state.total_feed_g / 1000.0,
                'harvest_success': harvest_success
            }

        return observation, float(reward), terminated, truncated, info

    def render(self) -> Optional[str]:
        """Render environment state to console."""
        if self.render_mode is None or self.state is None:
            return None

        larvae = self.state.larvae
        day = self.current_step // self.steps_per_day
        step_in_day = self.current_step % self.steps_per_day

        output = (
            f"\n{'='*54}\n"
            f"  BSF LARVAE BATCH - Day {day:2d}, Step {step_in_day + 1}/{self.steps_per_day}\n"
            f"{'='*54}\n"
            f"  Population:  {larvae.population:5d} / {self.state.initial_population}"
            f"  ({larvae.population / self.state.initial_population * 100:5.1f}% survival)\n"
            f"  Biomass:     {larvae.biomass_mg:6.2f} mg"
            f"  (target: {self.config['larvae']['harvest_target_mg']} mg)\n"
            f"  Dev Stage:   {self.growth_model.get_development_stage(larvae.development_sum)} / 6\n"
            f"{'-'*54}\n"
            f"  Temperature: {self.state.temperature_c:5.1f} C    "
            f"Humidity: {self.state.humidity_pct:5.1f}%\n"
            f"  Moisture:    {larvae.substrate_moisture:5.1f}%    "
            f"C:N Ratio: {larvae.substrate_cn:5.1f}\n"
            f"  Feed Left:   {larvae.substrate_remaining:5.1f}%    "
            f"Last Feed: {self.state.hours_since_feed:3.0f}h ago\n"
            f"{'-'*54}\n"
            f"  Total Feed:  {self.state.total_feed_g / 1000:.3f} kg    "
            f"Water: {self.state.total_water_ml:6.1f} ml\n"
            f"{'='*54}\n"
        )

        if self.render_mode == "human":
            print(output)

        return output

    def close(self):
        """Clean up resources."""
        pass


# ------------------------------------------------------------------
# Gymnasium registration helper
# ------------------------------------------------------------------

def register_bsf_env():
    """Register BSF environment with Gymnasium."""
    from gymnasium.envs.registration import register
    try:
        register(
            id='BSFLarvae-v0',
            entry_point='src.environments.bsf_env:BSFEnv',
            max_episode_steps=96,  # 16 days × 6 steps/day
        )
    except Exception:
        pass  # Already registered


# ------------------------------------------------------------------
# Quick smoke test
# ------------------------------------------------------------------

if __name__ == "__main__":
    env = BSFEnv(render_mode="human", stochastic_weather=False)
    obs, info = env.reset(seed=42)

    print("Initial observation:", obs)
    print("Initial info:", info)

    for i in range(5):
        action = env.action_space.sample()
        obs, reward, term, trunc, info = env.step(action)
        env.render()
        print(f"Step {i + 1}: reward={reward:.3f}")
        if term or trunc:
            break

    env.close()
