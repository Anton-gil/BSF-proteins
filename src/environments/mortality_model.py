"""
BSF Larvae Mortality Model

Calculates population mortality based on environmental stress factors.
Based on Chia et al. (2018), Shumo et al. (2019) research.
"""

import numpy as np
import yaml
from pathlib import Path
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MortalityFactors:
    """Breakdown of mortality causes for debugging/logging."""
    temperature: float      # Deaths from temperature stress
    moisture: float         # Deaths from moisture stress
    cn_ratio: float         # Deaths from poor nutrition
    density: float          # Deaths from overcrowding
    starvation: float       # Deaths from lack of feed
    total_deaths: int       # Total deaths this timestep
    survival_rate: float    # Survival rate (0-1)


class MortalityModel:
    """
    Simulates BSF larvae mortality based on environmental stress.
    
    Usage:
        model = MortalityModel()
        deaths, factors = model.calculate_mortality(
            population=1000,
            temperature_c=30,
            moisture_pct=70,
            ...
        )
    """
    
    def __init__(self, config_path: str = "configs/environment.yaml"):
        """Load parameters from config."""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.temp = self.config['temperature']
        self.moisture = self.config['moisture']
        self.cn = self.config['cn_ratio']
        self.density = self.config['density']
        self.mortality = self.config['mortality']
        
        # Base survival rate (per day in optimal conditions)
        self.base_daily_survival = 1.0 - self.mortality['base_daily_rate']
        
        # Stress coefficients
        self.stress_coef = self.mortality['stress_coefficients']
    
    def temperature_survival(self, temp_c: float) -> float:
        """
        Calculate survival factor based on temperature.
        
        Returns value between 0 (all die) and 1 (no extra mortality).
        
        Based on research:
        - 100% mortality below 15°C or above 40°C
        - ~34% survival at 40°C boundary
        - ~80% survival at 15°C boundary (if brief)
        - Optimal 27-32°C: no extra mortality
        
        Args:
            temp_c: Temperature in Celsius
            
        Returns:
            Survival factor (0-1)
        """
        t = self.temp
        
        # Lethal extremes
        if temp_c <= t['lethal_min_c']:
            return 0.0
        if temp_c >= t['lethal_max_c']:
            return 0.0
        
        # Optimal range - no stress
        if t['optimal_min_c'] <= temp_c <= t['optimal_max_c']:
            return 1.0
        
        # Below optimal
        if temp_c < t['optimal_min_c']:
            if temp_c <= t['suboptimal_min_c']:
                # Severe cold stress
                # Linear from 0 at lethal to 0.5 at suboptimal_min
                range_size = t['suboptimal_min_c'] - t['lethal_min_c']
                distance = temp_c - t['lethal_min_c']
                return 0.5 * (distance / range_size) if range_size > 0 else 0.0
            else:
                # Mild cold stress
                # Linear from 0.5 at suboptimal_min to 1.0 at optimal_min
                range_size = t['optimal_min_c'] - t['suboptimal_min_c']
                distance = temp_c - t['suboptimal_min_c']
                return 0.5 + 0.5 * (distance / range_size) if range_size > 0 else 0.5
        
        # Above optimal
        if temp_c > t['optimal_max_c']:
            if temp_c >= t['suboptimal_max_c']:
                # Severe heat stress (more dangerous than cold)
                # Linear from 0.34 at suboptimal_max to 0 at lethal_max
                range_size = t['lethal_max_c'] - t['suboptimal_max_c']
                distance = t['lethal_max_c'] - temp_c
                return 0.34 * (distance / range_size) if range_size > 0 else 0.0
            else:
                # Mild heat stress
                range_size = t['suboptimal_max_c'] - t['optimal_max_c']
                distance = t['suboptimal_max_c'] - temp_c
                return 0.34 + 0.66 * (distance / range_size) if range_size > 0 else 0.34
        
        return 1.0
    
    def moisture_survival(self, moisture_pct: float) -> float:
        """
        Calculate survival factor based on substrate moisture.
        
        - Below 30%: Desiccation (lethal)
        - Above 85%: Drowning (lethal)
        - 60-75%: Optimal
        
        Args:
            moisture_pct: Substrate moisture percentage
            
        Returns:
            Survival factor (0-1)
        """
        m = self.moisture
        
        # Lethal extremes
        if moisture_pct <= m['lethal_min_pct']:
            return 0.0
        if moisture_pct >= m['lethal_max_pct']:
            return 0.0
        
        # Optimal range
        if m['optimal_min_pct'] <= moisture_pct <= m['optimal_max_pct']:
            return 1.0
        
        # Below optimal (dry stress)
        if moisture_pct < m['optimal_min_pct']:
            if moisture_pct <= m['suboptimal_min_pct']:
                # Severe dry stress
                range_size = m['suboptimal_min_pct'] - m['lethal_min_pct']
                distance = moisture_pct - m['lethal_min_pct']
                return 0.3 * (distance / range_size) if range_size > 0 else 0.0
            else:
                # Mild dry stress
                range_size = m['optimal_min_pct'] - m['suboptimal_min_pct']
                distance = moisture_pct - m['suboptimal_min_pct']
                return 0.3 + 0.7 * (distance / range_size) if range_size > 0 else 0.3
        
        # Above optimal (wet stress / oxygen deprivation)
        if moisture_pct > m['optimal_max_pct']:
            range_size = m['lethal_max_pct'] - m['optimal_max_pct']
            distance = m['lethal_max_pct'] - moisture_pct
            return max(0.0, distance / range_size) if range_size > 0 else 0.0
        
        return 1.0
    
    def cn_ratio_survival(self, cn_ratio: float) -> float:
        """
        Calculate survival factor based on C:N ratio (nutrition quality).
        
        Poor nutrition causes gradual mortality, not immediate death.
        
        Args:
            cn_ratio: Carbon to Nitrogen ratio
            
        Returns:
            Survival factor (0-1)
        """
        cn = self.cn
        
        # Optimal range - no stress
        if cn['optimal_min'] <= cn_ratio <= cn['optimal_max']:
            return 1.0
        
        # Acceptable range - mild stress
        if cn['acceptable_min'] <= cn_ratio <= cn['acceptable_max']:
            # Calculate distance from optimal
            if cn_ratio < cn['optimal_min']:
                distance = cn['optimal_min'] - cn_ratio
                max_distance = cn['optimal_min'] - cn['acceptable_min']
            else:
                distance = cn_ratio - cn['optimal_max']
                max_distance = cn['acceptable_max'] - cn['optimal_max']
            
            # Mild mortality increase (0.95 to 1.0)
            return 1.0 - 0.05 * (distance / max_distance) if max_distance > 0 else 0.95
        
        # Outside acceptable - significant stress
        if cn_ratio < cn['acceptable_min']:
            # Too much nitrogen (potential ammonia toxicity)
            return 0.85
        else:
            # Too much carbon (starvation-like)
            # Higher C:N means less protein, worse outcomes
            excess = cn_ratio - cn['acceptable_max']
            return max(0.7, 0.9 - excess * 0.005)
    
    def density_survival(self, population: int, area_cm2: float) -> float:
        """
        Calculate survival factor based on larval density.
        
        High density causes:
        - Competition for feed
        - Oxygen depletion
        - Heat buildup
        - Disease spread
        
        Args:
            population: Current larvae count
            area_cm2: Growing area in cm²
            
        Returns:
            Survival factor (0-1)
        """
        if area_cm2 <= 0:
            return 0.0
        
        current_density = population / area_cm2
        optimal = self.density['optimal_per_cm2']
        max_density = self.density['max_per_cm2']
        
        if current_density <= optimal:
            return 1.0
        
        if current_density >= max_density * 2:
            # Extreme overcrowding
            return 0.7
        
        if current_density >= max_density:
            # High overcrowding
            excess = current_density - max_density
            return max(0.7, 0.85 - excess * 0.01)
        
        # Mild overcrowding (between optimal and max)
        progress = (current_density - optimal) / (max_density - optimal)
        return 1.0 - 0.15 * progress
    
    def starvation_survival(
        self, 
        substrate_remaining_pct: float, 
        hours_without_feed: float
    ) -> float:
        """
        Calculate survival factor based on feed availability.
        
        Args:
            substrate_remaining_pct: Percentage of substrate remaining
            hours_without_feed: Hours since last feeding
            
        Returns:
            Survival factor (0-1)
        """
        # If feed is available, no starvation
        if substrate_remaining_pct > 10:
            return 1.0
        
        # Low feed but some remaining
        if substrate_remaining_pct > 0:
            if hours_without_feed < 12:
                return 1.0
            elif hours_without_feed < 24:
                return 0.98
            elif hours_without_feed < 48:
                return 0.95
            else:
                return 0.90
        
        # No feed at all
        if hours_without_feed < 24:
            return 0.95
        elif hours_without_feed < 48:
            return 0.85
        elif hours_without_feed < 72:
            return 0.70
        else:
            # Severe starvation
            return max(0.5, 0.7 - (hours_without_feed - 72) * 0.01)
    
    def calculate_mortality(
        self,
        population: int,
        temperature_c: float,
        moisture_pct: float,
        cn_ratio: float,
        area_cm2: float,
        substrate_remaining_pct: float,
        hours_without_feed: float = 0,
        timestep_hours: float = 4.0
    ) -> Tuple[int, MortalityFactors]:
        """
        Calculate deaths for this timestep.
        
        Args:
            population: Current larvae count
            temperature_c: Temperature in Celsius
            moisture_pct: Substrate moisture %
            cn_ratio: Current C:N ratio
            area_cm2: Growing area (cm²)
            substrate_remaining_pct: Feed remaining %
            hours_without_feed: Hours since last feed added
            timestep_hours: Duration of timestep
            
        Returns:
            Tuple of (deaths_count, MortalityFactors breakdown)
        """
        if population <= 0:
            return 0, MortalityFactors(0, 0, 0, 0, 0, 0, 1.0)
        
        # Calculate individual survival factors
        s_temp = self.temperature_survival(temperature_c)
        s_moisture = self.moisture_survival(moisture_pct)
        s_cn = self.cn_ratio_survival(cn_ratio)
        s_density = self.density_survival(population, area_cm2)
        s_starvation = self.starvation_survival(substrate_remaining_pct, hours_without_feed)
        
        # Combined survival rate (multiplicative)
        # Scale to timestep (base rate is daily)
        timestep_fraction = timestep_hours / 24.0
        
        # Base survival for this timestep
        base_survival_timestep = self.base_daily_survival ** timestep_fraction
        
        # Combined survival (all factors)
        combined_survival = (
            base_survival_timestep 
            * (s_temp ** timestep_fraction)
            * (s_moisture ** timestep_fraction)
            * (s_cn ** timestep_fraction)
            * (s_density ** timestep_fraction)
            * (s_starvation ** timestep_fraction)
        )
        
        # Ensure bounds
        combined_survival = np.clip(combined_survival, 0.0, 1.0)
        
        # Lethal conditions: deterministically kill all
        if combined_survival == 0.0:
            factors = MortalityFactors(
                temperature=population * (1 - s_temp) / max((1 - s_temp) + (1 - s_moisture) + (1 - s_cn) + (1 - s_density) + (1 - s_starvation), 1e-9),
                moisture=population * (1 - s_moisture) / max((1 - s_temp) + (1 - s_moisture) + (1 - s_cn) + (1 - s_density) + (1 - s_starvation), 1e-9),
                cn_ratio=0,
                density=0,
                starvation=0,
                total_deaths=population,
                survival_rate=0.0
            )
            return population, factors
        
        # Calculate expected deaths
        expected_deaths = population * (1.0 - combined_survival)
        
        # Add stochasticity (binomial distribution)
        if expected_deaths > 0:
            # Use Poisson approximation for large populations
            if population > 100:
                actual_deaths = np.random.poisson(expected_deaths)
            else:
                # Binomial for small populations
                actual_deaths = np.random.binomial(population, 1 - combined_survival)
        else:
            actual_deaths = 0
        
        # Ensure we don't kill more than exist
        actual_deaths = min(actual_deaths, population)
        
        # Calculate factor-specific deaths (for logging/debugging)
        # Proportional attribution
        total_stress = (
            (1 - s_temp) + (1 - s_moisture) + (1 - s_cn) 
            + (1 - s_density) + (1 - s_starvation)
        )
        
        if total_stress > 0:
            deaths_temp = actual_deaths * (1 - s_temp) / total_stress
            deaths_moisture = actual_deaths * (1 - s_moisture) / total_stress
            deaths_cn = actual_deaths * (1 - s_cn) / total_stress
            deaths_density = actual_deaths * (1 - s_density) / total_stress
            deaths_starvation = actual_deaths * (1 - s_starvation) / total_stress
        else:
            # Base mortality only
            deaths_temp = actual_deaths * 0.2
            deaths_moisture = actual_deaths * 0.2
            deaths_cn = actual_deaths * 0.2
            deaths_density = actual_deaths * 0.2
            deaths_starvation = actual_deaths * 0.2
        
        factors = MortalityFactors(
            temperature=deaths_temp,
            moisture=deaths_moisture,
            cn_ratio=deaths_cn,
            density=deaths_density,
            starvation=deaths_starvation,
            total_deaths=actual_deaths,
            survival_rate=combined_survival
        )
        
        return actual_deaths, factors
    
    def apply_mortality(
        self,
        population: int,
        temperature_c: float,
        moisture_pct: float,
        cn_ratio: float,
        area_cm2: float = 1000.0,  # Default 10cm x 100cm
        substrate_remaining_pct: float = 50.0,
        hours_without_feed: float = 0,
        timestep_hours: float = 4.0
    ) -> Tuple[int, int, MortalityFactors]:
        """
        Apply mortality and return new population.
        
        Args:
            population: Current population
            ... (same as calculate_mortality)
            
        Returns:
            Tuple of (new_population, deaths, MortalityFactors)
        """
        deaths, factors = self.calculate_mortality(
            population=population,
            temperature_c=temperature_c,
            moisture_pct=moisture_pct,
            cn_ratio=cn_ratio,
            area_cm2=area_cm2,
            substrate_remaining_pct=substrate_remaining_pct,
            hours_without_feed=hours_without_feed,
            timestep_hours=timestep_hours
        )
        
        new_population = population - deaths
        return new_population, deaths, factors


def estimate_final_survival(
    days: int,
    avg_temperature: float,
    avg_moisture: float,
    avg_cn: float,
    initial_population: int = 1000
) -> float:
    """
    Quick estimate of survival rate over a batch period.
    
    Useful for planning/expectations.
    
    Args:
        days: Number of days
        avg_temperature: Average temperature
        avg_moisture: Average moisture
        avg_cn: Average C:N ratio
        initial_population: Starting population
        
    Returns:
        Estimated survival percentage
    """
    model = MortalityModel()
    
    # Calculate daily survival factors
    s_temp = model.temperature_survival(avg_temperature)
    s_moisture = model.moisture_survival(avg_moisture)
    s_cn = model.cn_ratio_survival(avg_cn)
    
    # Combined daily survival (assuming no density/starvation issues)
    daily_survival = model.base_daily_survival * s_temp * s_moisture * s_cn
    
    # Project over days
    final_survival = daily_survival ** days
    
    return final_survival * 100  # As percentage
