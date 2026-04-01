"""Tests for translation layer (Phase 8)."""
import sys
sys.path.insert(0, '.')

import numpy as np
from datetime import datetime, timedelta

from src.translation.waste_translator import WasteTranslator
from src.translation.weather_client import WeatherClient, WeatherData
from src.translation.state_estimator import StateEstimator, BatchInfo, FarmerObservation
from src.translation.recommendation import RecommendationGenerator


def test_waste_translator():
    """Test waste translator."""
    translator = WasteTranslator()

    # C:N lookup
    cn = translator.get_cn_ratio("banana_peels")
    assert cn is not None, "Should find banana_peels"
    assert 20 <= cn <= 50, f"Banana peels C:N should be ~30, got {cn}"
    print(f"  Banana peels C:N: {cn}")

    # Mix calculation
    mix_cn, mix_moisture = translator.calculate_mix_cn({
        "banana_peels": 1.0,
        "rice_bran":    1.0
    })
    assert 15 <= mix_cn <= 40, f"Mix C:N should be between components, got {mix_cn}"
    print(f"  Mix C:N: {mix_cn:.1f}, moisture: {mix_moisture:.1f}%")

    # Mix suggestion: target C:N 18
    suggestion = translator.suggest_waste_mix(
        target_cn=18,
        available_wastes=["banana_peels", "rice_bran"],
        total_amount_kg=2.0
    )
    assert len(suggestion) > 0, "Should suggest something"
    total_suggested = sum(suggestion.values())
    assert total_suggested <= 2.1, f"Should not exceed total, got {total_suggested}"
    print(f"  Suggestion for C:N 18: {suggestion}")

    # Display name
    display = translator.get_display_name("banana_peels")
    assert "Banana" in display, "Should format nicely"
    print(f"  Display name: {display}")

    print("✓ Waste translator works")


def test_weather_client():
    """Test weather client defaults/fallback."""
    client = WeatherClient()

    # Offline fallback (use_cache=False and assume no API available in CI)
    weather = client.get_current_weather(use_cache=False)

    assert weather is not None
    assert 10 <= weather.temperature_c <= 50, f"Reasonable temp: {weather.temperature_c}"
    assert 10 <= weather.humidity_pct <= 100, f"Reasonable humid: {weather.humidity_pct}"
    assert weather.source in ('api', 'default'), f"Source: {weather.source}"

    print(f"✓ Weather: {weather.temperature_c}°C, {weather.humidity_pct}%  (source={weather.source})")


def test_state_estimator():
    """Test state estimator produces valid 10-element observation."""
    estimator = StateEstimator()

    batch = BatchInfo(
        start_date=datetime.now() - timedelta(days=7),
        initial_count=1000,
        estimated_count=950,
        container_area_cm2=600,
        last_feed_time=datetime.now() - timedelta(hours=12),
        total_feed_kg=0.5
    )

    farmer_obs = FarmerObservation(
        larvae_activity="normal",
        mortality_estimate="few",
        substrate_condition="good",
        smell="normal"
    )

    obs = estimator.estimate_state(
        batch_info=batch,
        farmer_obs=farmer_obs,
        recent_waste={"banana_peels": 0.5}
    )

    assert obs.shape == (10,), f"State should be (10,), got {obs.shape}"
    assert obs.dtype == np.float32
    assert 6.0 <= obs[0] <= 8.0, f"Age should be ~7 days, got {obs[0]}"
    assert obs[1] > 10.0,        f"Biomass should be growing, got {obs[1]}"
    assert 0.0 <= obs[2] <= 1.0, f"Survival rate in [0,1], got {obs[2]}"

    print(f"✓ State estimator: age={obs[0]:.1f}d, biomass={obs[1]:.1f}mg, survival={obs[2]:.2f}")


def test_recommendation_generator():
    """Test recommendation generator produces valid output."""
    gen = RecommendationGenerator()

    action = np.array([0.5, 0.7, 0.3, 0.5], dtype=np.float32)

    rec = gen.generate(
        action=action,
        available_wastes=["banana_peels", "rice_bran"],
        larvae_count=1000,
        age_days=7
    )

    assert rec is not None
    assert len(rec.feed_instruction) > 0
    assert rec.target_cn > 0
    assert 0.0 <= rec.confidence <= 1.0

    formatted = gen.format_recommendation(rec)
    assert "FEEDING" in formatted

    print(f"✓ Recommendation: {rec.feed_instruction}")
    print(f"  C:N target: {rec.target_cn:.0f},  moisture: {rec.moisture_action},  aeration: {rec.aeration_action}")
    print(f"  Confidence: {rec.confidence*100:.0f}%")
    print()
    print(formatted)


def test_full_pipeline():
    """End-to-end test of the complete translation pipeline."""
    waste_translator = WasteTranslator()
    weather_client   = WeatherClient()
    state_estimator  = StateEstimator(weather_client, waste_translator)
    rec_gen          = RecommendationGenerator(waste_translator)

    batch = BatchInfo(
        start_date=datetime.now() - timedelta(days=5),
        initial_count=1000,
        estimated_count=980,
        last_feed_time=datetime.now() - timedelta(hours=18),
        total_feed_kg=0.3
    )

    farmer_obs = FarmerObservation(
        larvae_activity="very_active",
        mortality_estimate="none",
        substrate_condition="good",
        smell="normal"
    )

    available = ["banana_peels", "rice_bran", "kitchen_waste_mixed"]

    state = state_estimator.estimate_state(
        batch_info=batch,
        farmer_obs=farmer_obs,
        recent_waste={"rice_bran": 0.3}
    )

    from src.baselines.heuristic_policy import HeuristicPolicy
    policy = HeuristicPolicy()
    action = policy.predict(state)

    rec = rec_gen.generate(
        action=action,
        available_wastes=available,
        larvae_count=batch.estimated_count,
        age_days=5.0
    )

    print("\n" + "=" * 52)
    print("FULL PIPELINE TEST")
    print("=" * 52)
    print(f"Batch  : Day 5, {batch.estimated_count} larvae")
    print(f"State  : age={state[0]:.1f}d, CN={state[4]:.1f}, moist={state[5]:.1f}%")
    print(f"Action : {action}")
    print()
    print(rec_gen.format_recommendation(rec))
    print("=" * 52)

    assert rec.feed_instruction != ""
    print("\n✓ Full pipeline works!")


if __name__ == "__main__":
    print("=" * 50)
    print("TRANSLATION LAYER TESTS")
    print("=" * 50)
    print()
    test_waste_translator()
    print()
    test_weather_client()
    print()
    test_state_estimator()
    print()
    test_recommendation_generator()
    print()
    test_full_pipeline()

    print("\n" + "=" * 50)
    print("✅ ALL TRANSLATION TESTS PASSED")
    print("=" * 50)
