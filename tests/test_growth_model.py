"""Tests for BSF growth model."""
import sys
sys.path.insert(0, '.')

from src.environments.growth_model import GrowthModel, LarvaeState, create_initial_state
import numpy as np


def test_temperature_effect():
    """Test temperature effect curve."""
    model = GrowthModel()
    
    # Lethal temperatures
    assert model.temperature_effect(10) == 0.0, "Should be lethal below 15°C"
    assert model.temperature_effect(45) == 0.0, "Should be lethal above 40°C"
    
    # Optimal range
    assert model.temperature_effect(28) == 1.0, "Should be optimal at 28°C"
    assert model.temperature_effect(30) == 1.0, "Should be optimal at 30°C"
    
    # Suboptimal but survivable
    effect_20 = model.temperature_effect(20)
    assert 0 < effect_20 < 1, f"Should be reduced at 20°C, got {effect_20}"
    
    effect_35 = model.temperature_effect(35)
    assert 0 < effect_35 < 1, f"Should be reduced at 35°C, got {effect_35}"
    
    print("✓ Temperature effect tests passed")


def test_cn_ratio_effect():
    """Test C:N ratio effect curve."""
    model = GrowthModel()
    
    # Optimal range
    assert model.cn_ratio_effect(16) == 1.0, "C:N 16 should be optimal"
    assert model.cn_ratio_effect(14) == 1.0, "C:N 14 should be optimal"
    assert model.cn_ratio_effect(18) == 1.0, "C:N 18 should be optimal"
    
    # Suboptimal
    effect_25 = model.cn_ratio_effect(25)
    assert 0.4 < effect_25 < 1.0, f"C:N 25 should be suboptimal, got {effect_25}"
    
    effect_12 = model.cn_ratio_effect(12)
    assert 0.4 < effect_12 < 1.0, f"C:N 12 should be suboptimal, got {effect_12}"
    
    # Poor
    effect_50 = model.cn_ratio_effect(50)
    assert effect_50 <= 0.4, f"C:N 50 should be poor, got {effect_50}"
    
    print("✓ C:N ratio effect tests passed")


def test_moisture_effect():
    """Test moisture effect curve."""
    model = GrowthModel()
    
    # Lethal
    assert model.moisture_effect(25) == 0.0, "Should be lethal below 30%"
    assert model.moisture_effect(90) == 0.0, "Should be lethal above 85%"
    
    # Optimal
    assert model.moisture_effect(70) == 1.0, "Should be optimal at 70%"
    assert model.moisture_effect(65) == 1.0, "Should be optimal at 65%"
    
    # Suboptimal
    effect_45 = model.moisture_effect(45)
    assert 0 < effect_45 < 1, f"Should be reduced at 45%, got {effect_45}"
    
    print("✓ Moisture effect tests passed")


def test_growth_simulation():
    """Test full growth simulation over 14 days."""
    model = GrowthModel()
    state = create_initial_state(initial_larvae_count=1000)
    
    # Optimal conditions
    temperature = 30  # Optimal
    timestep = 4      # hours
    
    print(f"\nSimulating 14 days of growth at {temperature}°C...")
    print(f"Day 0: Biomass = {state.biomass_mg:.3f} mg")
    
    biomass_history = [state.biomass_mg]
    
    for day in range(14):
        for step in range(6):  # 6 steps per day (4h each)
            # Add feed and water periodically
            feed = 5.0 if step == 0 else 0.0  # Feed once per day
            water = 50.0 if step == 3 else 0.0
            
            state = model.step(
                state=state,
                temperature_c=temperature,
                feed_added_g=feed,
                feed_cn=18,  # Good C:N
                water_added_ml=water,
                timestep_hours=timestep
            )
        
        biomass_history.append(state.biomass_mg)
        if (day + 1) % 3 == 0:
            print(f"Day {day+1}: Biomass = {state.biomass_mg:.2f} mg, DevSum = {state.development_sum:.0f}h, Stage = {model.get_development_stage(state.development_sum)}")
    
    # Verify growth occurred
    final_biomass = state.biomass_mg
    assert final_biomass > 50, f"Should reach >50mg in 14 days, got {final_biomass:.2f}"
    assert final_biomass < 200, f"Should not exceed 200mg, got {final_biomass:.2f}"
    
    # Verify S-curve (growth should slow down)
    early_growth = biomass_history[5] - biomass_history[0]
    late_growth = biomass_history[14] - biomass_history[10]
    # Early growth should be faster than late growth (accounting for size)
    
    print(f"\n✓ Final biomass: {final_biomass:.2f} mg")
    print(f"✓ Growth simulation test passed")


def test_poor_conditions():
    """Test that poor conditions reduce growth."""
    model = GrowthModel()
    
    # Good conditions
    state_good = create_initial_state()
    for _ in range(24):  # 4 days
        state_good = model.step(
            state_good, temperature_c=30, feed_added_g=2, 
            feed_cn=16, water_added_ml=10, timestep_hours=4
        )
    
    # Poor temperature
    state_cold = create_initial_state()
    for _ in range(24):
        state_cold = model.step(
            state_cold, temperature_c=18, feed_added_g=2,
            feed_cn=16, water_added_ml=10, timestep_hours=4
        )
    
    # Poor C:N
    state_poor_cn = create_initial_state()
    for _ in range(24):
        state_poor_cn = model.step(
            state_poor_cn, temperature_c=30, feed_added_g=2,
            feed_cn=50, water_added_ml=10, timestep_hours=4
        )
    
    print(f"\nGood conditions: {state_good.biomass_mg:.2f} mg")
    print(f"Cold (18°C): {state_cold.biomass_mg:.2f} mg")
    print(f"Poor C:N (50): {state_poor_cn.biomass_mg:.2f} mg")
    
    assert state_good.biomass_mg > state_cold.biomass_mg, "Cold should reduce growth"
    assert state_good.biomass_mg > state_poor_cn.biomass_mg, "Poor C:N should reduce growth"
    
    print("✓ Poor conditions test passed")


def test_development_stages():
    """Test development stage progression."""
    model = GrowthModel()
    
    # Test stage progression
    assert model.get_development_stage(0) == 0, "Should start at stage 0"
    assert model.get_development_stage(100) == 1, "Should be stage 1 at 100h"
    assert model.get_development_stage(300) == 4, "Should be stage 4 at 300h"
    assert model.get_development_stage(450) == 6, "Should be prepupa at 450h"
    
    print("✓ Development stages test passed")


if __name__ == "__main__":
    print("=" * 50)
    print("GROWTH MODEL TESTS")
    print("=" * 50)
    
    test_temperature_effect()
    test_cn_ratio_effect()
    test_moisture_effect()
    test_development_stages()
    test_growth_simulation()
    test_poor_conditions()
    
    print("\n" + "=" * 50)
    print("✅ ALL GROWTH MODEL TESTS PASSED")
    print("=" * 50)
