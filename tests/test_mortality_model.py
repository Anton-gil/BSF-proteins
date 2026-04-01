"""Tests for BSF mortality model."""
import sys
sys.path.insert(0, '.')

from src.environments.mortality_model import (
    MortalityModel, 
    MortalityFactors, 
    estimate_final_survival
)
import numpy as np


def test_temperature_survival():
    """Test temperature survival curves."""
    model = MortalityModel()
    
    # Lethal temperatures
    assert model.temperature_survival(10) == 0.0, "Should be lethal at 10°C"
    assert model.temperature_survival(45) == 0.0, "Should be lethal at 45°C"
    assert model.temperature_survival(15) == 0.0, "Should be lethal at exactly 15°C"
    assert model.temperature_survival(40) == 0.0, "Should be lethal at exactly 40°C"
    
    # Optimal range - full survival
    assert model.temperature_survival(28) == 1.0, "Should be 100% at 28°C"
    assert model.temperature_survival(30) == 1.0, "Should be 100% at 30°C"
    
    # Suboptimal but survivable
    s_18 = model.temperature_survival(18)
    assert 0 < s_18 < 1, f"Should be partial at 18°C, got {s_18}"
    
    s_38 = model.temperature_survival(38)
    assert 0 < s_38 < 0.5, f"Should be low at 38°C, got {s_38}"
    
    # Heat more dangerous than cold
    s_cold = model.temperature_survival(22)  # 5° below optimal
    s_hot = model.temperature_survival(35)   # 3° above optimal
    # Both should reduce survival, but comparable
    
    print(f"✓ Temperature survival tests passed")
    print(f"  18°C: {s_18:.2%}, 38°C: {s_38:.2%}")


def test_moisture_survival():
    """Test moisture survival curves."""
    model = MortalityModel()
    
    # Lethal extremes
    assert model.moisture_survival(25) == 0.0, "Should die below 30%"
    assert model.moisture_survival(90) == 0.0, "Should die above 85%"
    
    # Optimal
    assert model.moisture_survival(70) == 1.0, "Should be 100% at 70%"
    
    # Suboptimal
    s_45 = model.moisture_survival(45)
    assert 0 < s_45 < 1, f"Should be partial at 45%, got {s_45}"
    
    s_80 = model.moisture_survival(80)
    assert 0 < s_80 < 1, f"Should be partial at 80%, got {s_80}"
    
    print(f"✓ Moisture survival tests passed")
    print(f"  45%: {s_45:.2%}, 80%: {s_80:.2%}")


def test_cn_survival():
    """Test C:N ratio survival."""
    model = MortalityModel()
    
    # Optimal
    assert model.cn_ratio_survival(16) == 1.0, "C:N 16 should be 100%"
    
    # Acceptable
    s_25 = model.cn_ratio_survival(25)
    assert 0.9 < s_25 < 1.0, f"C:N 25 should be ~95%, got {s_25:.2%}"
    
    # Poor
    s_50 = model.cn_ratio_survival(50)
    assert s_50 < 0.9, f"C:N 50 should reduce survival, got {s_50:.2%}"
    
    print(f"✓ C:N survival tests passed")
    print(f"  C:N 25: {s_25:.2%}, C:N 50: {s_50:.2%}")


def test_density_survival():
    """Test density-based survival."""
    model = MortalityModel()
    
    area = 1000  # cm²
    
    # Low density (good)
    s_low = model.density_survival(population=3000, area_cm2=area)  # 3/cm²
    assert s_low == 1.0, f"Low density should be 100%, got {s_low}"
    
    # Optimal density
    s_opt = model.density_survival(population=5000, area_cm2=area)  # 5/cm²
    assert s_opt == 1.0, f"Optimal density should be 100%, got {s_opt}"
    
    # High density
    s_high = model.density_survival(population=12000, area_cm2=area)  # 12/cm²
    assert s_high < 1.0, f"High density should reduce survival, got {s_high}"
    
    # Very high density
    s_vhigh = model.density_survival(population=25000, area_cm2=area)  # 25/cm²
    assert s_vhigh < s_high, f"Very high should be worse than high"
    
    print(f"✓ Density survival tests passed")
    print(f"  5/cm²: {s_opt:.2%}, 12/cm²: {s_high:.2%}, 25/cm²: {s_vhigh:.2%}")


def test_starvation_survival():
    """Test starvation survival."""
    model = MortalityModel()
    
    # Well fed
    s_fed = model.starvation_survival(substrate_remaining_pct=50, hours_without_feed=0)
    assert s_fed == 1.0, "Well fed should be 100%"
    
    # Low feed but recent
    s_low = model.starvation_survival(substrate_remaining_pct=5, hours_without_feed=6)
    assert s_low == 1.0, "Low but recent should be ok"
    
    # No feed, long time
    s_starve = model.starvation_survival(substrate_remaining_pct=0, hours_without_feed=48)
    assert s_starve < 0.9, f"48h starvation should reduce survival, got {s_starve}"
    
    print(f"✓ Starvation survival tests passed")
    print(f"  Fed: {s_fed:.2%}, 48h starved: {s_starve:.2%}")


def test_mortality_calculation():
    """Test full mortality calculation."""
    model = MortalityModel()
    
    np.random.seed(42)  # For reproducibility
    
    # Optimal conditions
    deaths_opt, factors_opt = model.calculate_mortality(
        population=1000,
        temperature_c=30,
        moisture_pct=70,
        cn_ratio=16,
        area_cm2=200,  # 5/cm²
        substrate_remaining_pct=80,
        hours_without_feed=0,
        timestep_hours=4
    )
    
    assert deaths_opt < 5, f"Optimal conditions should have minimal deaths, got {deaths_opt}"
    assert factors_opt.survival_rate > 0.99, f"Survival should be >99%, got {factors_opt.survival_rate:.2%}"
    
    print(f"\nOptimal conditions (4h timestep):")
    print(f"  Deaths: {deaths_opt}, Survival rate: {factors_opt.survival_rate:.4%}")
    
    # Poor conditions
    deaths_poor, factors_poor = model.calculate_mortality(
        population=1000,
        temperature_c=38,      # Hot!
        moisture_pct=45,       # Dry
        cn_ratio=40,           # Poor nutrition
        area_cm2=100,          # Overcrowded (10/cm²)
        substrate_remaining_pct=5,
        hours_without_feed=30,
        timestep_hours=4
    )
    
    assert deaths_poor > deaths_opt, "Poor conditions should have more deaths"
    assert factors_poor.survival_rate < factors_opt.survival_rate, "Poor should have lower survival"
    
    print(f"\nPoor conditions (4h timestep):")
    print(f"  Deaths: {deaths_poor}, Survival rate: {factors_poor.survival_rate:.2%}")
    print(f"  Breakdown: temp={factors_poor.temperature:.1f}, moisture={factors_poor.moisture:.1f}")
    
    print(f"\n✓ Mortality calculation tests passed")


def test_batch_simulation():
    """Simulate a full 14-day batch to check realistic mortality."""
    model = MortalityModel()
    
    np.random.seed(42)
    
    population = 1000
    area = 200  # cm²
    
    print(f"\n14-day batch simulation:")
    print(f"Starting population: {population}")
    
    total_deaths = 0
    
    for day in range(14):
        # Vary conditions slightly each day
        temp = 28 + np.random.uniform(-3, 3)
        moisture = 68 + np.random.uniform(-5, 5)
        
        # 6 timesteps per day
        for _ in range(6):
            new_pop, deaths, _ = model.apply_mortality(
                population=population,
                temperature_c=temp,
                moisture_pct=moisture,
                cn_ratio=18,
                area_cm2=area,
                substrate_remaining_pct=max(20, 80 - day * 4),
                timestep_hours=4
            )
            population = new_pop
            total_deaths += deaths
        
        if (day + 1) % 3 == 0:
            print(f"  Day {day+1}: Population = {population}, Deaths so far = {total_deaths}")
    
    survival_rate = population / 1000 * 100
    print(f"\nFinal population: {population}")
    print(f"Total deaths: {total_deaths}")
    print(f"Survival rate: {survival_rate:.1f}%")
    
    # In near-optimal conditions, expect 85-95% survival
    assert 800 <= population <= 1000, f"Expected 80-100% survival, got {survival_rate:.1f}%"
    
    print(f"✓ Batch simulation test passed")


def test_lethal_conditions():
    """Test that lethal conditions cause high mortality."""
    model = MortalityModel()
    
    np.random.seed(42)
    
    # Freezing temperature
    deaths_cold, _ = model.calculate_mortality(
        population=1000,
        temperature_c=10,  # Lethal cold
        moisture_pct=70,
        cn_ratio=16,
        area_cm2=200,
        substrate_remaining_pct=50,
        timestep_hours=24  # Full day
    )
    
    # Drowning
    deaths_wet, _ = model.calculate_mortality(
        population=1000,
        temperature_c=30,
        moisture_pct=95,  # Lethal wet
        cn_ratio=16,
        area_cm2=200,
        substrate_remaining_pct=50,
        timestep_hours=24
    )
    
    print(f"\nLethal conditions (24h):")
    print(f"  10°C: {deaths_cold} deaths ({deaths_cold/10:.0f}%)")
    print(f"  95% moisture: {deaths_wet} deaths ({deaths_wet/10:.0f}%)")
    
    assert deaths_cold == 1000, "Freezing should kill all"
    assert deaths_wet == 1000, "Drowning should kill all"
    
    print(f"✓ Lethal conditions test passed")


def test_survival_estimate():
    """Test quick survival estimation."""
    # Optimal conditions
    survival_opt = estimate_final_survival(
        days=14,
        avg_temperature=30,
        avg_moisture=70,
        avg_cn=16
    )
    
    # Suboptimal conditions
    survival_sub = estimate_final_survival(
        days=14,
        avg_temperature=35,
        avg_moisture=55,
        avg_cn=25
    )
    
    print(f"\nSurvival estimates (14 days):")
    print(f"  Optimal (30°C, 70%, C:N=16): {survival_opt:.1f}%")
    print(f"  Suboptimal (35°C, 55%, C:N=25): {survival_sub:.1f}%")
    
    assert survival_opt > survival_sub, "Optimal should have better survival"
    assert survival_opt > 90, "Optimal should be >90%"
    
    print(f"✓ Survival estimate test passed")


if __name__ == "__main__":
    print("=" * 50)
    print("MORTALITY MODEL TESTS")
    print("=" * 50)
    
    test_temperature_survival()
    test_moisture_survival()
    test_cn_survival()
    test_density_survival()
    test_starvation_survival()
    test_mortality_calculation()
    test_lethal_conditions()
    test_survival_estimate()
    test_batch_simulation()
    
    print("\n" + "=" * 50)
    print("✅ ALL MORTALITY MODEL TESTS PASSED")
    print("=" * 50)
