"""
BSF Larvae Growth Model

Implements logistic growth with environmental modifiers.
Based on Padmanabha et al. (2020) and validated research parameters.
"""

import numpy as np
import yaml
from pathlib import Path
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class LarvaeState:
    """Current state of larvae population."""
    age_hours: float              # Hours since batch start
    biomass_mg: float             # Average individual dry weight (mg)
    population: int               # Number of alive larvae
    development_sum: float        # Accumulated development hours
    substrate_moisture: float     # Current moisture %
    substrate_cn: float           # Current C:N ratio
    substrate_remaining: float    # Feed remaining (%)


class GrowthModel:
    """
    Simulates BSF larvae growth based on environmental conditions.
    
    Usage:
        model = GrowthModel()
        new_state = model.step(current_state, temperature, feed_amount, feed_cn, timestep_hours)
    """
    
    def __init__(self, config_path: str = "configs/environment.yaml"):
        """Load parameters from config."""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Extract relevant configs
        self.larvae = self.config['larvae']
        self.growth = self.config['growth']
        self.temp = self.config['temperature']
        self.moisture = self.config['moisture']
        self.cn = self.config['cn_ratio']
        self.feeding = self.config['feeding']
        self.sim = self.config['simulation']
        
        # Growth parameters
        # k_inges is the max specific ingestion rate (0.02/h).
        # We scale by 2 to get ~0.04/h which matches observed BSF specific
        # growth rates of ~20-30%/day during exponential phase.  feed_efficiency
        # is used only for substrate accounting, NOT in the growth equation
        # (treating k_inges as the net assimilation rate avoids the situation
        # where k_inges * feed_efficiency < k_maint, i.e. larvae can never grow).
        self.k_inges = self.growth['max_specific_growth_rate'] * 2.0
        self.k_maint = self.growth['maintenance_rate']
        self.feed_efficiency = self.growth['feed_efficiency']
        
        # Development thresholds
        self.dev_sum = self.growth['development_sum']
    
    def temperature_effect(self, temp_c: float) -> float:
        """
        Calculate temperature effect on growth (0 to 1).
        
        Based on research:
        - Lethal below 15°C or above 40°C
        - Optimal between 27-32°C
        - Gradual decline outside optimal
        
        Args:
            temp_c: Temperature in Celsius
            
        Returns:
            Multiplier between 0 and 1
        """
        # Lethal boundaries
        if temp_c <= self.temp['lethal_min_c'] or temp_c >= self.temp['lethal_max_c']:
            return 0.0
        
        # Optimal range
        if self.temp['optimal_min_c'] <= temp_c <= self.temp['optimal_max_c']:
            return 1.0
        
        # Below optimal
        if temp_c < self.temp['optimal_min_c']:
            if temp_c <= self.temp['suboptimal_min_c']:
                # Linear decline from suboptimal_min to lethal_min
                range_size = self.temp['suboptimal_min_c'] - self.temp['lethal_min_c']
                distance = temp_c - self.temp['lethal_min_c']
                return 0.3 * (distance / range_size)
            else:
                # Gradual decline from optimal to suboptimal
                range_size = self.temp['optimal_min_c'] - self.temp['suboptimal_min_c']
                distance = temp_c - self.temp['suboptimal_min_c']
                return 0.3 + 0.7 * (distance / range_size)
        
        # Above optimal
        if temp_c > self.temp['optimal_max_c']:
            if temp_c >= self.temp['suboptimal_max_c']:
                # Steep decline from suboptimal_max to lethal_max
                range_size = self.temp['lethal_max_c'] - self.temp['suboptimal_max_c']
                distance = self.temp['lethal_max_c'] - temp_c
                return 0.2 * (distance / range_size)
            else:
                # Gradual decline from optimal to suboptimal
                range_size = self.temp['suboptimal_max_c'] - self.temp['optimal_max_c']
                distance = self.temp['suboptimal_max_c'] - temp_c
                return 0.2 + 0.8 * (distance / range_size)
        
        return 1.0  # Fallback
    
    def moisture_effect(self, moisture_pct: float) -> float:
        """
        Calculate moisture effect on growth (0 to 1).
        
        - Lethal below 30% (desiccation) or above 85% (drowning)
        - Optimal between 60-75%
        
        Args:
            moisture_pct: Substrate moisture percentage
            
        Returns:
            Multiplier between 0 and 1
        """
        m = self.moisture
        
        if moisture_pct <= m['lethal_min_pct'] or moisture_pct >= m['lethal_max_pct']:
            return 0.0
        
        if m['optimal_min_pct'] <= moisture_pct <= m['optimal_max_pct']:
            return 1.0
        
        # Below optimal
        if moisture_pct < m['optimal_min_pct']:
            if moisture_pct <= m['suboptimal_min_pct']:
                range_size = m['suboptimal_min_pct'] - m['lethal_min_pct']
                distance = moisture_pct - m['lethal_min_pct']
                return 0.2 * (distance / range_size) if range_size > 0 else 0.0
            else:
                range_size = m['optimal_min_pct'] - m['suboptimal_min_pct']
                distance = moisture_pct - m['suboptimal_min_pct']
                return 0.2 + 0.8 * (distance / range_size) if range_size > 0 else 0.2
        
        # Above optimal
        if moisture_pct > m['optimal_max_pct']:
            range_size = m['lethal_max_pct'] - m['optimal_max_pct']
            distance = m['lethal_max_pct'] - moisture_pct
            return max(0.0, distance / range_size) if range_size > 0 else 0.0
        
        return 1.0
    
    def cn_ratio_effect(self, cn_ratio: float) -> float:
        """
        Calculate C:N ratio effect on growth (0 to 1).
        
        - Optimal: 14-18 (returns 1.0)
        - Acceptable: 10-30 (returns 0.4-1.0)
        - Poor: outside acceptable (returns 0.2-0.4)
        
        Args:
            cn_ratio: Carbon to Nitrogen ratio
            
        Returns:
            Multiplier between 0 and 1
        """
        cn = self.cn
        
        # Optimal range
        if cn['optimal_min'] <= cn_ratio <= cn['optimal_max']:
            return cn['optimal_effect']  # 1.0
        
        # Below optimal
        if cn_ratio < cn['optimal_min']:
            if cn_ratio >= cn['acceptable_min']:
                # Gradual decline
                range_size = cn['optimal_min'] - cn['acceptable_min']
                distance = cn_ratio - cn['acceptable_min']
                return cn['suboptimal_effect'] + (cn['optimal_effect'] - cn['suboptimal_effect']) * (distance / range_size)
            else:
                # Poor range
                return cn['poor_effect']
        
        # Above optimal
        if cn_ratio > cn['optimal_max']:
            if cn_ratio <= cn['acceptable_max']:
                range_size = cn['acceptable_max'] - cn['optimal_max']
                distance = cn['acceptable_max'] - cn_ratio
                return cn['suboptimal_effect'] + (cn['optimal_effect'] - cn['suboptimal_effect']) * (distance / range_size)
            else:
                return cn['poor_effect']
        
        return 1.0
    
    def feed_availability_effect(self, substrate_remaining_pct: float) -> float:
        """
        Calculate feed availability effect (Monod-type saturation).
        
        Args:
            substrate_remaining_pct: Percentage of substrate remaining
            
        Returns:
            Multiplier between 0 and 1
        """
        if substrate_remaining_pct <= 0:
            return 0.0
        
        # Monod equation: S / (K + S)
        # Half-saturation at 20% remaining
        k_half = 20.0
        return substrate_remaining_pct / (k_half + substrate_remaining_pct)
    
    def development_stage_effect(self, development_sum: float) -> Tuple[float, float]:
        """
        Calculate development stage effect on assimilation and maturation.
        
        As larvae mature:
        - Assimilation rate decreases (stop eating)
        - Maturation rate increases (burning reserves)
        
        Args:
            development_sum: Accumulated development hours
            
        Returns:
            Tuple of (assimilation_multiplier, maturation_multiplier)
        """
        k_ts1 = self.dev_sum['feeding_reduction_start']  # 320h
        k_ts2 = self.dev_sum['feeding_stop']             # 400h
        k_ts3 = self.dev_sum['pupation']                 # 450h
        
        # Assimilation effect (feeding)
        if development_sum < k_ts1:
            # Full feeding
            assim_effect = 1.0
        elif development_sum < k_ts2:
            # Gradual reduction
            progress = (development_sum - k_ts1) / (k_ts2 - k_ts1)
            assim_effect = 1.0 - progress
        else:
            # Stop feeding
            assim_effect = 0.0
        
        # Maturation effect (burning reserves in prepupa stage)
        if development_sum < k_ts2:
            mat_effect = 0.5  # Base maintenance
        elif development_sum < k_ts3:
            # Increased maturation (prepupa)
            progress = (development_sum - k_ts2) / (k_ts3 - k_ts2)
            mat_effect = 0.5 + 0.5 * progress
        else:
            # Full maturation (pupation)
            mat_effect = 1.0
        
        return assim_effect, mat_effect
    
    def get_age_feeding_multiplier(self, age_days: float) -> float:
        """
        Get age-based feeding rate multiplier.
        
        Young larvae eat less, peak at day 4-7, then varies.
        
        Args:
            age_days: Age in days
            
        Returns:
            Feeding rate multiplier
        """
        multipliers = self.feeding['age_multipliers']
        
        if age_days <= 3:
            return multipliers['day_1_3']
        elif age_days <= 7:
            return multipliers['day_4_7']
        elif age_days <= 10:
            return multipliers['day_8_10']
        else:
            return multipliers['day_11_plus']
    
    def calculate_growth_rate(
        self,
        biomass_mg: float,
        temperature_c: float,
        moisture_pct: float,
        cn_ratio: float,
        substrate_remaining_pct: float,
        development_sum: float
    ) -> Tuple[float, float]:
        """
        Calculate instantaneous growth rate.
        
        Args:
            biomass_mg: Current average larva weight (mg)
            temperature_c: Temperature in Celsius
            moisture_pct: Substrate moisture %
            cn_ratio: Feed C:N ratio
            substrate_remaining_pct: Feed remaining %
            development_sum: Accumulated development hours
            
        Returns:
            Tuple of (growth_rate_mg_per_hour, new_development_rate)
        """
        # Get all effect multipliers
        f_temp = self.temperature_effect(temperature_c)
        f_moisture = self.moisture_effect(moisture_pct)
        f_cn = self.cn_ratio_effect(cn_ratio)
        f_feed = self.feed_availability_effect(substrate_remaining_pct)
        f_assim, f_mat = self.development_stage_effect(development_sum)
        
        # Combined assimilation rate modifier
        r_assim = f_temp * f_moisture * f_cn * f_feed * f_assim
        
        # Combined maturation rate modifier
        r_mat = f_temp * f_mat
        
        # Asymptotic growth limit (von Bertalanffy inspired)
        max_biomass = self.larvae['max_weight_mg']
        size_limit_factor = 1.0 - (biomass_mg / max_biomass)
        size_limit_factor = max(0.0, size_limit_factor)  # Can't be negative
        
        # Growth rate calculation.
        # feed_efficiency is NOT applied here — k_inges already represents the
        # net specific assimilation rate.  feed_efficiency is reserved for
        # substrate consumption accounting in the step() function.
        assimilation = self.k_inges * biomass_mg * r_assim * size_limit_factor
        maintenance = self.k_maint * biomass_mg * r_mat
        
        growth_rate = assimilation - maintenance  # mg per hour
        
        # Development rate (for tracking biological age)
        development_rate = f_temp * f_moisture * f_feed
        
        return growth_rate, development_rate
    
    def step(
        self,
        state: LarvaeState,
        temperature_c: float,
        feed_added_g: float,
        feed_cn: float,
        water_added_ml: float,
        timestep_hours: float = 4.0
    ) -> LarvaeState:
        """
        Advance simulation by one timestep.
        
        Args:
            state: Current larvae state
            temperature_c: Ambient temperature
            feed_added_g: Feed added this timestep (grams)
            feed_cn: C:N ratio of added feed
            water_added_ml: Water added (ml)
            timestep_hours: Duration of timestep
            
        Returns:
            New LarvaeState after timestep
        """
        # Update substrate C:N (weighted average if feed added)
        if feed_added_g > 0:
            # Assume substrate_remaining represents current feed mass
            current_feed_g = state.substrate_remaining * 10  # Rough scaling
            total_feed = current_feed_g + feed_added_g
            if total_feed > 0:
                new_cn = (current_feed_g * state.substrate_cn + feed_added_g * feed_cn) / total_feed
            else:
                new_cn = feed_cn
            # Update remaining (simple model: add feed, larvae consume some)
            new_remaining = min(100, state.substrate_remaining + feed_added_g * 2)
        else:
            new_cn = state.substrate_cn
            new_remaining = state.substrate_remaining
        
        # Update moisture (water addition increases, evaporation decreases).
        # Use small water coefficient (0.02) so 50 ml → +1% moisture, keeping
        # well below the lethal 85% threshold.  Evaporation is slow (0.05/h)
        # so moisture drifts down ~0.2%/day without additions.
        moisture_change = water_added_ml * 0.02 - timestep_hours * 0.05
        new_moisture = np.clip(state.substrate_moisture + moisture_change, 20, 95)
        
        # Calculate growth rate
        growth_rate, dev_rate = self.calculate_growth_rate(
            biomass_mg=state.biomass_mg,
            temperature_c=temperature_c,
            moisture_pct=new_moisture,
            cn_ratio=new_cn,
            substrate_remaining_pct=new_remaining,
            development_sum=state.development_sum
        )
        
        # Apply growth
        new_biomass = state.biomass_mg + growth_rate * timestep_hours
        new_biomass = np.clip(new_biomass, self.larvae['initial_weight_mg'], self.larvae['max_weight_mg'])
        
        # Update development sum
        new_dev_sum = state.development_sum + dev_rate * timestep_hours
        
        # Update age
        new_age = state.age_hours + timestep_hours
        
        # Substrate consumption (proportional to population and feeding)
        f_assim, _ = self.development_stage_effect(new_dev_sum)
        consumption_rate = 0.5 * f_assim * self.temperature_effect(temperature_c)
        new_remaining = max(0, new_remaining - consumption_rate * timestep_hours)
        
        return LarvaeState(
            age_hours=new_age,
            biomass_mg=float(new_biomass),
            population=state.population,  # Mortality handled separately
            development_sum=new_dev_sum,
            substrate_moisture=float(new_moisture),
            substrate_cn=new_cn,
            substrate_remaining=new_remaining
        )
    
    def get_development_stage(self, development_sum: float) -> int:
        """
        Get current instar/stage (0-6).
        
        Args:
            development_sum: Accumulated development hours
            
        Returns:
            Stage number (0=neonate, 5=late larva, 6=prepupa)
        """
        # Rough mapping based on development sum
        if development_sum < 50:
            return 0
        elif development_sum <= 100:
            return 1
        elif development_sum <= 180:
            return 2
        elif development_sum <= 260:
            return 3
        elif development_sum <= 320:
            return 4
        elif development_sum <= 400:
            return 5
        else:
            return 6  # Prepupa


def create_initial_state(
    initial_larvae_count: int = 1000,
    initial_moisture: float = 70.0,
    initial_cn: float = 20.0
) -> LarvaeState:
    """
    Create initial state for a new batch.
    
    Args:
        initial_larvae_count: Starting population
        initial_moisture: Initial substrate moisture %
        initial_cn: Initial substrate C:N ratio
        
    Returns:
        Initial LarvaeState
    """
    return LarvaeState(
        age_hours=0.0,
        biomass_mg=0.04,  # Neonate weight
        population=initial_larvae_count,
        development_sum=0.0,
        substrate_moisture=initial_moisture,
        substrate_cn=initial_cn,
        substrate_remaining=100.0
    )
